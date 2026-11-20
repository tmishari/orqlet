"""The two model rules of the team's `.prompts/rules.yaml` (task dynamic-model-profiles, P-13).

Acceptance criterion AC-13.

Every test cites its `expected_behavior_source`: AC-13 is an acceptance criterion of phase P-13 in
docs/design/dynamic-model-profiles/plan.yaml, BC-26 a behaviour of design/component.md, C-10 a
constraint, ADR-006 decision 9 the rule text of design/adr-006, and "the interface" the section 5
of the interface that the Coder of P-13 gave the Tester (the order and the wording that the
criterion leaves to the Coder).

These tests were written first, by the Tester of phase P-13, before the two rules existed. The file
is read with the strict loader and the `RuleFile` contract, as the standards resolver reads it.

The fifteen rules that the file held at the base commit fdb54a5 are pinned by their id, level,
enforcement, scope, `check_ref` and the SHA-256 of their text. The text is the one that the loader
gives (the folded text of a YAML `>-` scalar) with its white space squeezed to single spaces. The
hashes were computed from `git show HEAD:.prompts/rules.yaml` and are written here as literals, so
a rule that is reworded, weakened or moved to another level fails here and not silently.

Not pinned: the position of the new rules among the old ones beyond "after the existing ones" (the
interface), and the comments of the file.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.standards_pack import Rule, RuleFile

pytestmark = pytest.mark.unit

RULES_PATH = Path(__file__).resolve().parents[2] / ".prompts" / "rules.yaml"
LOADER = StrictYamlLoader()

# (id, level, enforcement, scope paths, check_ref, SHA-256 of the squeezed text), in file order.
EXISTING: tuple[tuple[str, str, str, tuple[str, ...], str | None, str], ...] = (
    (
        "ORQLET-ARCH-001",
        "MUST",
        "deterministic",
        ("src/orqlet/**",),
        "uv run lint-imports",
        "a97b21e954e6326ea64ad5048e3f215797e4bea31ac63550d4d5e842b54ea957",
    ),
    (
        "ORQLET-ARCH-002",
        "MUST",
        "deterministic",
        ("src/orqlet/domain/**", "src/orqlet/application/**"),
        "uv run lint-imports",
        "2de5ced29abe76d33bf326c2aeba31bcf53ae9771071de5b8df7d32b58c577c7",
    ),
    (
        "ORQLET-ARCH-003",
        "MUST",
        "deterministic",
        ("src/orqlet/adapters/clients/**", "src/orqlet/workflow/**"),
        "uv run lint-imports",
        "7abecda838453d3bc5e8fc0bafbd2a58edecadfe30ae8965afab2abcf9ae3c83",
    ),
    (
        "ORQLET-SEC-001",
        "MUST",
        "review",
        ("src/**",),
        None,
        "16fb70402c3ebcbca90f056039da99c7ae851c3dd49ece54e68099305e62a85c",
    ),
    (
        "ORQLET-SEC-002",
        "MUST",
        "review",
        ("src/orqlet/**",),
        None,
        "929640ac0699e2349ed6f7f91ed43efa8d7af42060c99471ef43e9ff275b359d",
    ),
    (
        "ORQLET-SEC-003",
        "MUST",
        "review",
        (),
        None,
        "b02c53772492e135926d6c2807de38f59a602e52ce20214ac12c7ab044b02876",
    ),
    (
        "ORQLET-SAFE-001",
        "MUST",
        "review",
        ("src/orqlet/application/**", "src/orqlet/adapters/**"),
        None,
        "f4d4e5739449e9fcf18bfe3cddb7e2c3cd091bbff043823a14e440f10118ef13",
    ),
    (
        "ORQLET-NOMODEL-001",
        "MUST",
        "review",
        (),
        None,
        "39bdb09cecd87ef92049526559bdd573ca2d30b2f460dbe65b28728a815acee4",
    ),
    (
        "ORQLET-DET-001",
        "MUST",
        "deterministic",
        ("src/orqlet/adapters/clients/**", "tests/golden/**"),
        "uv run pytest -m golden",
        "04ad7edab4f7f71f6ff0af4610202442697862734730dbbc8fd64c5e17e93baa",
    ),
    (
        "ORQLET-DET-002",
        "MUST",
        "deterministic",
        ("src/orqlet/workflow/**",),
        "uv run python tools/build_manifest.py --check",
        "0a474e2e4713405293d9ee4cdcb9fb16ace3ddd8c768e440e5aa0517f86c1ba1",
    ),
    (
        "ORQLET-DET-003",
        "MUST",
        "deterministic",
        ("src/orqlet/application/contracts/**",),
        "uv run python tools/export_schemas.py --check",
        "8b109fc4fbb94498f84d60feb289b645a6b12891691b274328b7c8857263561e",
    ),
    (
        "ORQLET-TEST-001",
        "MUST",
        "deterministic",
        ("src/**", "tests/**"),
        "uv run pytest",
        "6f4c235809573acbfb20218c09f0b4a44257499d675c0d667cc11fc0f4b9eece",
    ),
    (
        "ORQLET-TEST-002",
        "MUST",
        "deterministic",
        ("src/orqlet/application/usecases/apply_plan.py", "tests/fault/**"),
        "uv run pytest -m fault",
        "0adc5a82fb256bfbffa0eae61504f87c9866b3753333d5ca184c93b5de823514",
    ),
    (
        "ORQLET-QA-001",
        "MUST",
        "deterministic",
        (),
        ".github/workflows/ci.yml",
        "d91bd49bb687c513c2f2cb3c296e2187de378038d599933a51be64c65bc6a471",
    ),
    (
        "ORQLET-STYLE-001",
        "SHOULD",
        "guidance",
        ("src/**", "tests/**"),
        None,
        "f7c9fe9f885486e24c8d815b491fde8ab95c8dec293f86ff33f4b673767cbb2c",
    ),
)

MODEL_001_TEXT = (
    "A model name appears in a generated or packaged file only when the model policy assigned it, "
    "and never when the policy excludes it."
)
MODEL_002_TEXT = (
    "A review record for a gated role names the models that ran, or says they are unknown, and "
    "states the freshness of its context; a class below the role's minimum is NOT_RUN, never a "
    "pass."
)


def rules() -> tuple[Rule, ...]:
    return load_contract(LOADER, RuleFile, RULES_PATH.read_bytes(), source="rules.yaml").rules


def rule(rule_id: str) -> Rule:
    found = [item for item in rules() if item.id == rule_id]
    assert len(found) == 1, rule_id
    return found[0]


def squeezed(text: str) -> str:
    return " ".join(text.split())


def digest(text: str) -> str:
    return sha256(squeezed(text).encode("utf-8")).hexdigest()


def test_the_file_loads_with_the_strict_loader_and_the_rule_file_contract() -> None:
    """AC-13. expected_behavior_source: AC-13 ("the file loads with the strict loader"); the
    contract `orqlet.rules/v1` (`RuleFile`). The file has the seventeen rules, none twice.
    """
    loaded = load_contract(LOADER, RuleFile, RULES_PATH.read_bytes(), source="rules.yaml")

    assert loaded.schema_id == "orqlet.rules/v1"
    ids = [item.id for item in loaded.rules]
    assert len(ids) == 17
    assert len(set(ids)) == 17


def test_the_two_model_rules_come_after_the_existing_ones_in_this_order() -> None:
    """AC-13. expected_behavior_source: the interface section 5 ("`.prompts/rules.yaml` gains two
    rules after the existing ones": `ORQLET-MODEL-001`, then `ORQLET-MODEL-002`); AC-13.
    """
    ids = [item.id for item in rules()]

    assert ids == [row[0] for row in EXISTING] + ["ORQLET-MODEL-001", "ORQLET-MODEL-002"]


def test_model_001_is_a_deterministic_must_checked_by_the_test_suite() -> None:
    """AC-13. expected_behavior_source: AC-13 ("ORQLET-MODEL-001 (MUST, enforcement
    `deterministic`, `check_ref: uv run pytest`, scope paths `src/orqlet/**` and `tests/**`)");
    BC-26; C-10; ADR-006 decision 9.
    """
    found = rule("ORQLET-MODEL-001")

    assert found.level == "MUST"
    assert found.enforcement == "deterministic"
    assert found.check_ref == "uv run pytest"
    assert found.scope.paths == ("src/orqlet/**", "tests/**")
    assert found.scope.roles == ()
    assert found.scope.phases == ()
    assert found.waiver == "none"


def test_model_001_says_when_a_model_name_may_appear() -> None:
    """AC-13. expected_behavior_source: AC-13 (the text of ORQLET-MODEL-001, word for word);
    ADR-006 decision 9.
    """
    assert squeezed(rule("ORQLET-MODEL-001").text) == MODEL_001_TEXT


def test_model_002_is_a_review_must_for_the_design_documents() -> None:
    """AC-13. expected_behavior_source: AC-13 ("ORQLET-MODEL-002 (MUST, enforcement `review`, scope
    path `docs/design/**`)"); BC-26; C-10; ADR-006 decision 9. A review rule names no check.
    """
    found = rule("ORQLET-MODEL-002")

    assert found.level == "MUST"
    assert found.enforcement == "review"
    assert found.check_ref is None
    assert found.scope.paths == ("docs/design/**",)
    assert found.scope.roles == ()
    assert found.scope.phases == ()
    assert found.waiver == "none"


def test_model_002_says_what_a_review_record_of_a_gated_role_holds() -> None:
    """AC-13. expected_behavior_source: AC-13 (the text of ORQLET-MODEL-002, word for word);
    ADR-006 decision 9.
    """
    assert squeezed(rule("ORQLET-MODEL-002").text) == MODEL_002_TEXT


@pytest.mark.parametrize("row", EXISTING, ids=[row[0] for row in EXISTING])
def test_an_existing_rule_is_unchanged(
    row: tuple[str, str, str, tuple[str, ...], str | None, str],
) -> None:
    """AC-13. expected_behavior_source: AC-13 ("Every existing rule is unchanged"); BC-26; C-10.
    The id, the level, the enforcement, the scope paths, the `check_ref` and the SHA-256 of the
    text are those of the file at the base commit.
    """
    rule_id, level, enforcement, paths, check_ref, text_hash = row

    found = rule(rule_id)

    assert found.level == level
    assert found.enforcement == enforcement
    assert found.scope.paths == paths
    assert found.scope.roles == ()
    assert found.scope.phases == ()
    assert found.check_ref == check_ref
    assert found.waiver == "none"
    assert digest(found.text) == text_hash
