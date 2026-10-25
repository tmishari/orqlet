import pytest

from orqlet.domain.resolver import (
    Enforcement,
    Layer,
    Level,
    RuleSpec,
    Scope,
    Waiver,
    WeakeningError,
    dominates,
    resolve,
    rules_hash,
    select,
)

pytestmark = pytest.mark.unit


def rule(
    rule_id: str = "R1",
    level: Level = Level.MUST,
    *,
    waiver: Waiver = Waiver.NONE,
    enforcement: Enforcement = Enforcement.GUIDANCE,
    paths: tuple[str, ...] = (),
    roles: tuple[str, ...] = (),
    phases: tuple[str, ...] = (),
    text: str = "text",
    source: str = "layer",
) -> RuleSpec:
    scope = Scope(frozenset(paths), frozenset(roles), frozenset(phases))
    return RuleSpec(rule_id, level, waiver, enforcement, scope, text, source)


def test_layers_add_rules_and_the_result_is_sorted_by_id() -> None:
    result = resolve([Layer("company", (rule("B"),)), Layer("project", (rule("A"),))])

    assert list(result) == ["A", "B"]


def test_a_later_layer_may_restate_a_rule_at_the_same_or_higher_strictness() -> None:
    base = rule("R", Level.SHOULD, waiver=Waiver.REVIEWED, source="company")
    tighter = rule("R", Level.MUST, waiver=Waiver.NONE, enforcement=Enforcement.REVIEW)

    result = resolve([Layer("company", (base,)), Layer("project", (tighter,))])

    assert result["R"].level is Level.MUST
    assert result["R"].enforcement is Enforcement.REVIEW


@pytest.mark.parametrize(
    "weaker",
    [
        rule("R", Level.SHOULD),
        rule("R", Level.MUST, waiver=Waiver.REVIEWED),
        rule("R", Level.MUST, enforcement=Enforcement.GUIDANCE),
        rule("R", Level.MUST, paths=("src/**",)),
    ],
)
def test_a_later_layer_cannot_relax_a_rule(weaker: RuleSpec) -> None:
    strong = rule("R", Level.MUST, enforcement=Enforcement.REVIEW, source="company")

    with pytest.raises(WeakeningError, match="relax rule R"):
        resolve([Layer("company", (strong,)), Layer("project", (weaker,))])


def test_a_rule_repeated_inside_one_layer_is_an_error() -> None:
    with pytest.raises(WeakeningError, match="twice"):
        resolve([Layer("pack", (rule("R"), rule("R")))])


def test_widening_the_scope_is_allowed_and_narrowing_is_not() -> None:
    narrow = rule("R", paths=("src/**",))
    wide = rule("R")

    assert resolve([Layer("a", (narrow,)), Layer("b", (wide,))])["R"].scope.paths == frozenset()
    with pytest.raises(WeakeningError):
        resolve([Layer("a", (wide,)), Layer("b", (narrow,))])


def test_dominates_is_reflexive_and_detects_a_missing_rule() -> None:
    both = resolve([Layer("a", (rule("A"), rule("B")))])
    only_a = resolve([Layer("a", (rule("A"),))])

    assert dominates(both, both)
    assert dominates(both, only_a)
    assert not dominates(only_a, both)


def test_select_filters_by_scope_and_orders_must_first() -> None:
    rules = resolve(
        [
            Layer(
                "x",
                (
                    rule("A-should", Level.SHOULD),
                    rule("B-must", Level.MUST),
                    rule("C-src", paths=("src/**",)),
                    rule("D-design", phases=("design",)),
                    rule("E-arch", roles=("architect",)),
                ),
            )
        ]
    )

    assert [r.id for r in select(rules)] == ["B-must", "C-src", "D-design", "E-arch", "A-should"]
    assert [r.id for r in select(rules, path="docs/x.md")] == [
        "B-must",
        "D-design",
        "E-arch",
        "A-should",
    ]
    assert [r.id for r in select(rules, phase="build", role="dev")] == [
        "B-must",
        "C-src",
        "A-should",
    ]


def test_rules_hash_ignores_the_source_pack_and_the_input_order() -> None:
    first = [rule("A", source="pack-1"), rule("B", source="pack-1")]
    second = [rule("B", source="pack-2"), rule("A", source="pack-2")]

    assert rules_hash(first) == rules_hash(second)


def test_rules_hash_changes_when_the_text_or_the_level_changes() -> None:
    base = rules_hash([rule("A")])

    assert rules_hash([rule("A", text="other")]) != base
    assert rules_hash([rule("A", Level.SHOULD)]) != base
