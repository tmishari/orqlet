"""`orqlet validate review` reads the model policy of the base tree and of the staged tree and
derives the identity of each record (task dynamic-model-profiles, phase P-10, AC-1 to AC-7).

The tests drive only the entry point `validate_review` that exists today, on `FakeVcs` (a base
tree and a staged tree) and the in-memory file system, and read the `ValidationResult`: finding
codes, severities and message prefixes, the `not_run` reasons, the verdict and the `data` dict.
They never import `review_identity`, whose internals the design leaves open. A review record is
bound to the staged tree with the `review_input` block that `review prepare` prints for it, as an
agent would write it, so a record is never stale unless a test says so.

Every test cites its `expected_behavior_source`: AC-n of phase P-10 in
docs/design/dynamic-model-profiles/plan.yaml, BC-n of design/component.md, and ADR-005, ADR-006
and ADR-007 of the design. These tests were written first, by the Tester of phase P-10, before
`review_identity` existed. AC-8 is a check of the gate and of CI, and the acceptance tests of
tests/e2e/test_s9_acceptance.py and tests/e2e/test_full_task.py are run by the Coder: neither is
tested here.

The criteria leave these open, so no test pins them:
- the order of the names in `independence_notes`: only sets are compared;
- whether `independence_notes` holds all six closed names or only the two identity notes: the
  tests read AC-4 literally, so the list holds exactly the closed names that start a message;
- the reason text of a code reviewer that is I0 (no context, or `context.fresh` false): only a
  non-empty `not_run` is asserted;
- the format of `unmatched` with a length: only the word and the absence of the recorded string;
- ORQ-E412 is unchanged, so a record whose class a test does not pin claims I0 and is NOT_RUN;
- ORQ-W410 can add `not_run` reasons, so a PASS is asserted only for a record that is bound;
- whether a record that names no model gets ORQ-E461 or ORQ-I460, and which tree gives
  `model_families` when the two trees differ: no test depends on either.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.binding_inputs import AGENT_FILES
from orqlet.application.usecases.review_prepare import DEFAULT_REVIEWERS, review_prepare
from orqlet.application.usecases.validate_records import RecordOptions, validate_review
from orqlet.application.usecases.validation import ValidateServices, ValidationResult, content_hash
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.artifacts import HASH, TASK, TASK_DIR, design, dump, phase, plan

pytestmark = pytest.mark.unit

BASE, HEADC, STAGED = "1" * 40, "2" * 40, "3" * 40
PHASE = "P-1"
POLICY_PATH = ".orqlet/model-policy.yaml"
BINDINGS_PATH = ".orqlet/role-bindings.yaml"
AGENT_FILE = b"---\nname: reviewer\n---\nReview.\n"
CLIENTS = tuple(AGENT_FILES)
ROLES = tuple(DEFAULT_REVIEWERS)
UNLOADABLE = b"{{{ not yaml"
LOCK_PATH = ".orqlet/generated.lock.yaml"
PHRASE = "read-only is not enforced by this client"
CODE_REVIEWER_TEXT = (
    "independence I1 is below I2, which the code reviewer requires at every change class"
)
D3_TEXT = "independence I1 is below I2, which a D3 change requires of a review"
MARKER = "zz-marker-7f3a91"
# The closed warnings of AC-4: the code of each finding and the name that starts its message.
WARNINGS = {
    "ORQ-W460": "identity-unknown",
    "ORQ-W461": "same-model-different-client",
    "ORQ-W462": "policy-changed-in-this-change",
    "ORQ-W463": "binding-added-in-this-change",
    "ORQ-W464": "model-requested-differs-from-observed",
    "ORQ-W465": "codex-read-only-not-stated",
}
STANDARDS_LOCK = f"schema: orqlet.standards-lock/v1\napplicable_rules_hash: {HASH}\n".encode()
WORKFLOW_LOCK = (
    f"schema: orqlet.workflow-lock/v1\nworkflow_version: 0.2.0\nworkflow_digest: {HASH}\n"
    "controls_level: 2\n"
).encode()
FRESH: dict[str, object] = {"fresh": True, "input": "packet-only"}
STALE: dict[str, object] = {"fresh": False, "input": "packet-only"}


# --- the documents of a repository ---------------------------------------------------------------


def route(client: str, name: str, **extra: object) -> dict[str, object]:
    return {"client": client, "kind": "id", "name": name, **extra}


def entry(
    model_id: str, family: str, *routes: Mapping[str, object], state: str = "approved"
) -> dict[str, Any]:
    return {
        "id": model_id,
        "family": family,
        "approval": {"state": state},
        "documented": {"evidence": "docs/example/evidence.md", "date": "2026-10-30"},
        "callable": "not-run",
        "evaluated": {"state": "none"},
        "routes": list(routes),
    }


def alpha(state: str = "approved") -> dict[str, Any]:
    routes = (route("cursor", "alpha-1"), route("claude-code", "alpha-1"))
    return entry("cat-alpha", "family-a", *routes, state=state)


def beta(state: str = "approved") -> dict[str, Any]:
    routes = (route("cursor", "beta-1"), route("claude-code", "beta-1"))
    return entry("cat-beta", "family-b", *routes, state=state)


def policy(
    *models: Mapping[str, object],
    excluded: Sequence[Mapping[str, object]] = (),
    version: int = 1,
    extra: Mapping[str, object] | None = None,
) -> bytes:
    """A model policy as JSON text, which the strict loader reads as YAML."""
    document = {
        "schema": "orqlet.model-policy/v2",
        "policy_version": version,
        "reviewed_for_release": "0.4.0",
        "models": list(models),
        "excluded": list(excluded),
        **(extra or {}),
    }
    return json.dumps(document, indent=2).encode()


def bindings(roles: Sequence[str] = ROLES, families: Sequence[tuple[str, str]] = ()) -> bytes:
    """The role bindings: one approved binding for each role, for every client."""
    document = {
        "schema": "orqlet.role-bindings/v1",
        "policy_role": "enforcement-baseline",
        "bindings": [
            {
                "role": role,
                "id": DEFAULT_REVIEWERS[role],
                "clients": list(CLIENTS),
                "independence_capability": "I1",
            }
            for role in roles
        ],
        "model_families": [{"match": match, "family": family} for match, family in families],
    }
    return json.dumps(document, indent=2).encode()


BANNED = {
    "id": "banned-rule",
    "reason": "Example reason, printable ASCII text.",
    "source": "Example notice of the team.",
    "aliases": ["banned-alias"],
    "id_patterns": ["banned-model-*"],
    "family_tags": ["zzbanned"],
}
BANNED_MODEL = "banned-model-9"
VALID = policy(alpha(), beta())
NEWER = policy(alpha(), beta(), version=2)
PROPOSED = policy(alpha("proposed"), beta("proposed"))
EXCLUDING = policy(alpha(), beta(), excluded=[BANNED])
APPROVED = bindings()
NO_BINDINGS = bindings(roles=())


def lock_bytes(*rows: Mapping[str, object], **extra: object) -> bytes:
    """A generated lock with these rows (JSON text, which is YAML)."""
    document = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": "0.4.0"},
        "files": list(rows),
        **extra,
    }
    return json.dumps(document, indent=2).encode()


SEEDED_POLICY_ROW = {"path": POLICY_PATH, "owner": "seeded", "seeded_sha256": "0" * 64}
SEEDED_LOCK = lock_bytes(SEEDED_POLICY_ROW)
# Strings that only the legacy `model_families` can place, strings that the policy places apart
# and a pair that `model_families` places together.
LEGACY = bindings(families=[("legacy-a-*", "family-x"), ("legacy-b-*", "family-y")])
SPLIT = bindings(families=[("alpha-*", "family-x"), ("beta-*", "family-y")])
SHARED = bindings(families=[("alpha-*", "shared"), ("beta-*", "shared")])


def tree(policy_bytes: bytes | None, bindings_bytes: bytes | None, klass: str) -> dict[str, bytes]:
    """A tree with a plan, a design of change class `klass`, the locks and every agent file."""
    classes = dict.fromkeys(("trigger", "declared", "effective"), klass)
    files: dict[str, bytes] = {
        "src/pkg/service.py": b"def existing() -> None: ...\n",
        f"{TASK_DIR}/plan.yaml": dump(plan(phases=[phase()])).encode(),
        f"{TASK_DIR}/design/manifest.yaml": dump(design(change_class=classes)).encode(),
        ".orqlet/knowledge.yaml": b"schema: orqlet.knowledge/v2\n",
        ".prompts/rules.yaml": b"schema: orqlet.rules/v1\nrules: []\n",
        ".orqlet/standards.lock.yaml": STANDARDS_LOCK,
        ".orqlet/workflow.lock": WORKFLOW_LOCK,
    }
    for reference in DEFAULT_REVIEWERS.values():
        for pattern in AGENT_FILES.values():
            files[pattern.format(ref=reference)] = AGENT_FILE
    if policy_bytes is not None:
        files[POLICY_PATH] = policy_bytes
    if bindings_bytes is not None:
        files[BINDINGS_PATH] = bindings_bytes
    return files


def services_for(base: dict[str, bytes], staged: dict[str, bytes]) -> ValidateServices:
    vcs = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEADC, "head"),),
        committed=base,
        revisions={BASE: base, HEADC: base},
        merge_bases={(HEADC, BASE): (BASE,)},
        staged=True,
        staged_tree=(STAGED, staged),
    )
    return ValidateServices(
        project=MemoryFileSystem(), vcs=vcs, loader=StrictYamlLoader(), workflow=PINNED
    )


# One review to validate: what each tree holds and what the record says. The default record
# claims I0, which no derivation can contradict (ORQ-E412), so a test that does not pin the class
# is not made to fail by it. A policy or a bindings file of `None` is a file that is not there.
@dataclass(frozen=True)
class Scene:
    base_policy: bytes | None = None
    staged_policy: bytes | None = None
    base_bindings: bytes | None = APPROVED
    staged_bindings: bytes | None = APPROVED
    change_class: str = "D1"
    role: str = "architecture-reviewer"
    client: str = "cursor"
    coder_client: str = "cursor"
    agent: Mapping[str, object] | None = None
    coder: Mapping[str, object] | None = None
    independence: str = "I0"
    limits: tuple[str, ...] = ("read-only is advisory",)
    working_policy: bytes | None = None
    base_lock: bytes | None = None
    staged_lock: bytes | None = None


def observed(model: str) -> dict[str, object]:
    return {"model_observed": model, "identity_source": "client-reported"}


def bound_input(services: ValidateServices, role: str, client: str) -> dict[str, object]:
    """The `review_input` block that `review prepare` prints for this reviewer and client."""
    prepared = review_prepare(
        services, MemoryFileSystem(), "abcdabcd", TASK, PHASE, base=BASE, head="staged"
    )
    inputs = prepared.data.get("review_inputs")
    assert isinstance(inputs, dict), prepared
    block = inputs.get("review", {}).get(role, {}).get(client)
    assert isinstance(block, dict), prepared
    return block


def record(services: ValidateServices, scene: Scene) -> dict[str, Any]:
    return {
        "schema": "orqlet.review-result/v1",
        "task": TASK,
        "phase": PHASE,
        "role": scene.role,
        "round": 1,
        "verdict": "NOT_RUN" if scene.independence == "I0" else "PASS",
        "assurance": "advisory",
        "review_input": bound_input(services, scene.role, scene.client),
        "agent": {
            "binding_ref": DEFAULT_REVIEWERS[scene.role],
            "definition_sha256": content_hash(AGENT_FILE),
            "client": scene.client,
            **(scene.agent or {}),
        },
        "coder_binding": {"client": scene.coder_client, **(scene.coder or {})},
        "independence": scene.independence,
        "capability_limits": list(scene.limits),
        "applicability": {"examined": ["src/pkg/service.py"], "conclusion": "findings"},
        "findings": [],
        "self_check": {
            "schema": "orqlet.self-check/v1",
            "checked_against": {"role": scene.role, "phase": "implement"},
            "checks": [{"what": "packet read", "how": "orqlet review prepare", "result": "pass"}],
        },
    }


def review(scene: Scene) -> ValidationResult:
    """Validate one record, bound to the staged tree, against a base tree and that tree."""
    base = tree(scene.base_policy, scene.base_bindings, scene.change_class)
    staged = tree(scene.staged_policy, scene.staged_bindings, scene.change_class)
    if scene.base_lock is not None:
        base[LOCK_PATH] = scene.base_lock
    if scene.staged_lock is not None:
        staged[LOCK_PATH] = scene.staged_lock
    services = services_for(base, staged)
    path = f"{TASK_DIR}/reviews/{scene.role}-{PHASE}-r1.yaml"
    document = dump(record(services, scene)).encode()
    services.project.write_atomic(CanonicalPath.parse(path), document)
    if scene.working_policy is not None:
        services.project.write_atomic(CanonicalPath.parse(POLICY_PATH), scene.working_policy)
    return validate_review(services, path, RecordOptions(base=BASE, head="staged"))


# --- reading a result ----------------------------------------------------------------------------


def codes(result: ValidationResult) -> set[str]:
    return {finding.code for finding in result.findings}


def found(result: ValidationResult, code: str) -> list[Finding]:
    return [finding for finding in result.findings if finding.code == code]


def derived(result: ValidationResult) -> object:
    return result.data["independence_derived"]


def notes_of(result: ValidationResult) -> set[str]:
    """The names in `independence_notes`; a result without the key lists none."""
    value = result.data.get("independence_notes", [])
    assert isinstance(value, list | tuple), value
    return {str(item) for item in value}


def prefixed_names(result: ValidationResult) -> set[str]:
    """The closed names that start the message of at least one finding."""
    return {
        name
        for finding in result.findings
        for name in WARNINGS.values()
        if finding.message.startswith(f"{name}:")
    }


def warned(result: ValidationResult, code: str) -> Finding:
    """The warning `code`: its closed name and a colon start the message, and the data lists it.

    The list of notes holds exactly the closed names that start a message of this result.
    """
    name = WARNINGS[code]
    matching = found(result, code)
    assert matching, sorted(codes(result))
    for finding in matching:
        assert finding.severity is Severity.WARNING
        assert finding.message.startswith(f"{name}:"), finding.message
    assert name in notes_of(result)
    assert notes_of(result) == prefixed_names(result)
    return matching[0]


# --- AC-1: the two trees, the union of the exclusions and where a family comes from --------------

WITH_POLICY = Scene(base_policy=VALID, staged_policy=VALID)
TWO_MODELS = replace(WITH_POLICY, agent=observed("alpha-1"), coder=observed("beta-1"))
WITH_EXCLUSION = Scene(base_policy=EXCLUDING, staged_policy=EXCLUDING)
NAMES_BANNED: dict[str, object] = {"model_observed": BANNED_MODEL}


@pytest.mark.parametrize(
    ("base", "staged"),
    [
        pytest.param(EXCLUDING, VALID, id="only-in-the-base-tree"),
        pytest.param(VALID, EXCLUDING, id="only-in-the-staged-tree"),
    ],
)
def test_exclusions_are_the_union_of_both_trees(base: bytes, staged: bytes) -> None:
    """expected_behavior_source: AC-1 ("Exclusions are the union of both trees"); BC-40;
    ADR-005 decision 2 ("so one change cannot remove an exclusion and pass a record against its
    own edit"); ADR-007 decision 1 ("Exclusions are the union of both trees").

    The exclusion stands in one tree only; a model that it matches is ORQ-E460 either way.
    """
    scene = Scene(base_policy=base, staged_policy=staged, agent=NAMES_BANNED)

    result = review(scene)

    assert "ORQ-E460" in codes(result)


def test_a_family_of_the_policy_wins_over_model_families() -> None:
    """expected_behavior_source: AC-1 ("where the policy matches a string its family wins");
    BC-40; ADR-007 decision 1 ("where the policy matches a string, the policy's family wins").

    `model_families` puts both strings in one family and the policy puts them in two, so the two
    models are of different families and the same client reaches I2.
    """
    scene = replace(
        TWO_MODELS,
        base_bindings=SHARED,
        staged_bindings=SHARED,
        independence="I2",
    )

    result = review(scene)

    assert derived(result) == "I2"
    assert not result.errors


def test_a_string_the_policy_cannot_match_keeps_the_family_of_model_families() -> None:
    """expected_behavior_source: AC-1 ("`model_families` of `role-bindings.yaml` still applies to
    a string that the policy cannot match"); BC-44; ADR-007 decision 1.

    A policy is in both trees and names neither string, so the legacy families place them in two
    families and the same client reaches I2, as it does today.
    """
    scene = replace(
        WITH_POLICY,
        base_bindings=LEGACY,
        staged_bindings=LEGACY,
        agent=observed("legacy-a-1"),
        coder=observed("legacy-b-1"),
        independence="I2",
    )

    result = review(scene)

    assert derived(result) == "I2"
    assert not result.errors


def test_without_a_policy_model_families_applies_to_every_string() -> None:
    """expected_behavior_source: AC-1 ("and to every string when the policy was never present");
    BC-31 ("with it absent, the legacy rules apply"); ADR-007 decision 1 ("so a project that
    populated it keeps its I2 on upgrade").
    """
    scene = Scene(
        base_bindings=LEGACY,
        staged_bindings=LEGACY,
        agent=observed("legacy-a-1"),
        coder=observed("legacy-b-1"),
        independence="I2",
    )

    result = review(scene)

    assert derived(result) == "I2"
    assert not result.errors


def test_an_entry_that_is_proposed_at_the_base_tree_gives_no_family() -> None:
    """expected_behavior_source: AC-1 ("A family is taken only from a catalog entry that is not
    `proposed` at the base tree"); BC-10; BC-40; ADR-007 decision 1 ("neither seed text that no
    team approved nor an entry added by the change under review can create a difference").

    Both entries are proposed at the base tree and approved at the staged tree, so the change
    cannot give itself a family difference: the same client stays at I1.
    """
    scene = Scene(
        base_policy=PROPOSED,
        staged_policy=VALID,
        agent=observed("alpha-1"),
        coder=observed("beta-1"),
        independence="I1",
    )

    result = review(scene)

    assert derived(result) == "I1"


def test_an_entry_that_is_approved_at_the_base_tree_gives_a_family() -> None:
    """expected_behavior_source: AC-1 ("A family is taken only from a catalog entry that is not
    `proposed` at the base tree"); BC-10; BC-40; ADR-007 decision 1 ("the family of a recorded
    model is the `family` of the catalog model that the matching rule of ADR-005 maps it to").

    The counterpart of the test above: approved at the base tree, the two families differ and the
    same client reaches I2, with no `model_families` at all.
    """
    result = review(replace(TWO_MODELS, independence="I2"))

    assert derived(result) == "I2"
    assert not result.errors


@pytest.mark.parametrize(
    "working",
    [policy(alpha(), beta(), excluded=[BANNED]), UNLOADABLE],
    ids=["excluding", "unloadable"],
)
def test_the_policy_of_the_working_tree_is_not_read(working: bytes) -> None:
    """expected_behavior_source: AC-1 ("reads `.orqlet/model-policy.yaml` from the base tree and
    from the staged tree"); ADR-007 decision 10 ("from the base and the staged git trees for
    `validate review`", so independence is derived from the snapshot that was reviewed).

    A file in the working tree only changes nothing: no ORQ-E460, no ORQ-E461, and the same codes
    as without the file. This guards the reading rule and holds before the change too.
    """
    plain = Scene(agent=NAMES_BANNED)

    without = review(plain)
    with_file = review(replace(plain, working_policy=working))

    assert not codes(with_file) & {"ORQ-E460", "ORQ-E461"}
    assert codes(with_file) == codes(without)


# --- AC-2: the tree matrix, the bindings -------------------------------------------------------

REFUSED_STAGED = [
    pytest.param(VALID, UNLOADABLE, id="unloadable-over-a-valid-base"),
    pytest.param(None, UNLOADABLE, id="unloadable-over-no-base"),
    pytest.param(UNLOADABLE, UNLOADABLE, id="unloadable-over-an-unloadable-base"),
    pytest.param(VALID, None, id="deleted-while-the-base-has-one"),
]
MISSING_OR_REFUSED_BASE = [
    pytest.param(None, id="absent"),
    pytest.param(UNLOADABLE, id="unloadable"),
]


def test_both_trees_valid_is_the_normal_case() -> None:
    """expected_behavior_source: AC-2 ("Both trees valid is the normal case"); BC-44; ADR-007
    decision 1 ("both trees valid is the normal case").

    The same valid policy in both trees gives none of the findings of the other cases.
    """
    result = review(TWO_MODELS)

    unexpected = {"ORQ-E460", "ORQ-E461", "ORQ-W462", "ORQ-W463", "ORQ-I460"}
    assert not codes(result) & unexpected


def test_two_valid_policies_that_differ_warn_that_the_policy_changed() -> None:
    """expected_behavior_source: BC-40 ("warns `policy-changed-in-this-change` when the two
    differ"); ADR-007 decision 1 ("when the policy differs between the base and the staged tree,
    `validate review` adds the closed finding `policy-changed-in-this-change`"); AC-4.

    Two valid policies that differ are not an error.
    """
    result = review(replace(TWO_MODELS, base_policy=VALID, staged_policy=NEWER))

    warned(result, "ORQ-W462")
    assert "ORQ-E461" not in codes(result)


@pytest.mark.parametrize(("base", "staged"), REFUSED_STAGED)
def test_a_refused_staged_policy_is_e461(base: bytes | None, staged: bytes | None) -> None:
    """expected_behavior_source: AC-2 ("A staged policy that is unloadable, or deleted while the
    base tree has one, gives ORQ-E461 for every record that names a model"); BC-31; BC-44;
    ADR-005 decision 2 (a deleted file is not an absent one, so it is an error and not the
    legacy rules).

    The record names a model. AC-2 states the rule for a staged policy alone, so the cases with no
    base policy and with an unloadable base policy are read as covered by it (a question).
    """
    result = review(replace(TWO_MODELS, base_policy=base, staged_policy=staged))

    refused = found(result, "ORQ-E461")
    assert refused
    assert all(finding.severity is Severity.ERROR for finding in refused)
    assert result.verdict is Verdict.FAIL


@pytest.mark.parametrize(("base", "staged"), REFUSED_STAGED)
def test_a_refused_staged_policy_never_falls_back_to_model_families(
    base: bytes | None, staged: bytes | None
) -> None:
    """expected_behavior_source: AC-2 ("and never falls back to `model_families`"); BC-31 ("never
    falls back to `model_families`"); ADR-005 decision 2.

    `model_families` would place the two strings in two families and give I2 to the same client.
    The class that a refused policy does give is not stated: only that it is not that I2.
    """
    scene = replace(
        TWO_MODELS,
        base_policy=base,
        staged_policy=staged,
        base_bindings=SPLIT,
        staged_bindings=SPLIT,
    )

    result = review(scene)

    assert "ORQ-E461" in codes(result)
    assert derived(result) != "I2"


@pytest.mark.parametrize("base", MISSING_OR_REFUSED_BASE)
def test_a_base_policy_that_is_missing_or_refused_warns_that_the_policy_changed(
    base: bytes | None,
) -> None:
    """expected_behavior_source: AC-2 ("A base policy that is absent or unloadable while the
    staged one is valid ... gives the warning `policy-changed-in-this-change` (ORQ-W462)");
    BC-44; ADR-007 decision 1 ("which avoids both a deadlock and a hole"); AC-4.

    The staged policy is valid, so the record is judged and is not an ORQ-E461 error.
    """
    result = review(replace(TWO_MODELS, base_policy=base, staged_policy=VALID))

    warned(result, "ORQ-W462")
    assert "ORQ-E461" not in codes(result)


@pytest.mark.parametrize("base", MISSING_OR_REFUSED_BASE)
def test_a_base_policy_that_is_missing_or_refused_leaves_the_exclusions_to_the_staged_tree(
    base: bytes | None,
) -> None:
    """expected_behavior_source: AC-2 ("is judged on the staged tree for exclusions"); BC-44;
    ADR-007 decision 1 ("judged on the staged tree for exclusions").

    The exclusion is in the staged policy only; the record that names it is ORQ-E460.
    """
    scene = Scene(base_policy=base, staged_policy=EXCLUDING, agent=NAMES_BANNED)

    result = review(scene)

    assert "ORQ-E460" in codes(result)


@pytest.mark.parametrize("base", MISSING_OR_REFUSED_BASE)
def test_a_base_policy_that_is_missing_or_refused_gives_no_policy_family(
    base: bytes | None,
) -> None:
    """expected_behavior_source: AC-2 ("with no policy family"); BC-44; ADR-007 decision 1
    ("with no policy family (so no difference can be established from it)").

    The staged policy would place the two strings in two families. With no `model_families`, the
    same client stays at I1: the change cannot give itself the difference.
    """
    scene = replace(TWO_MODELS, base_policy=base, staged_policy=VALID, independence="I1")

    result = review(scene)

    assert derived(result) == "I1"


def test_a_policy_that_was_never_present_gives_the_information_i460() -> None:
    """expected_behavior_source: AC-2 ("A policy that was never present in either tree gives the
    legacy rules and the information ORQ-I460 'no exclusion list was available'"); BC-31;
    ADR-005 decision 2 ("its report says no exclusion list was available").

    The record names models and neither tree holds a policy: an information, no error.
    """
    result = review(replace(TWO_MODELS, base_policy=None, staged_policy=None))

    infos = found(result, "ORQ-I460")
    assert infos
    for info in infos:
        assert info.severity is Severity.INFO
        assert "no exclusion list was available" in info.message
    assert not codes(result) & {"ORQ-E460", "ORQ-E461", "ORQ-W462"}


# --- AC-2, the lock leg of the deletion rule (rework round 1, finding F-1 of the review r1) ----
# These tests were added by the Coder after the architecture review r1 and before the code that
# they test: ADR-005 decision 2 treats a policy with a seeded row in the lock as deleted, and the
# first version of `review_identity` judged the two trees only.

SEEDED_BINDINGS_ROW = {"path": BINDINGS_PATH, "owner": "seeded", "seeded_sha256": "1" * 64}
USER_POLICY_ROW = {"path": POLICY_PATH, "owner": "user", "rendered_sha256": "3" * 64}
LOCK_PLACEMENTS = [
    pytest.param(SEEDED_LOCK, None, id="the-row-is-in-the-base-tree"),
    pytest.param(None, SEEDED_LOCK, id="the-row-is-in-the-staged-tree"),
    pytest.param(SEEDED_LOCK, SEEDED_LOCK, id="the-row-is-in-both-trees"),
]
LOCKS_THAT_SHOW_NO_DELETION = [
    pytest.param(None, id="no-lock"),
    pytest.param(UNLOADABLE, id="a-lock-that-cannot-be-loaded"),
    pytest.param(lock_bytes(SEEDED_POLICY_ROW, surprise=1), id="a-lock-that-fails-its-contract"),
    pytest.param(lock_bytes(SEEDED_BINDINGS_ROW), id="no-row-for-the-policy"),
    pytest.param(lock_bytes(USER_POLICY_ROW), id="a-row-of-the-policy-that-is-not-seeded"),
]
DELETED = replace(TWO_MODELS, base_policy=None, staged_policy=None)


@pytest.mark.parametrize(("base_lock", "staged_lock"), LOCK_PLACEMENTS)
def test_a_policy_that_both_trees_lack_but_the_lock_lists_as_seeded_is_e461(
    base_lock: bytes | None, staged_lock: bytes | None
) -> None:
    """expected_behavior_source: ADR-005 decision 2 ("a file that is missing from the staged tree
    but present at the base tree, or that has a seeded row in the lock, is treated as
    unloadable"); BC-39 ("recorded as seeded in the lock ... makes `validate review` error on every
    record that names a model"); BC-44; F-16; AC-2 (ORQ-E461 for every record that names a model,
    and the legacy rules only for a policy that was never present).

    An earlier change deleted the file and was merged, so neither tree has it, and the lock still
    says that it was seeded: the exclusions are gone, which is an error and not the information
    ORQ-I460. The row is read from either tree, so a change cannot drop the row to hide it.
    """
    result = review(replace(DELETED, base_lock=base_lock, staged_lock=staged_lock))

    refused = found(result, "ORQ-E461")
    assert refused
    assert all(finding.severity is Severity.ERROR for finding in refused)
    assert result.verdict is Verdict.FAIL
    assert "ORQ-I460" not in codes(result)


def test_a_seeded_policy_that_both_trees_lack_never_falls_back_to_model_families() -> None:
    """expected_behavior_source: ADR-005 decision 2 ("is treated as unloadable" and a file that is
    present but cannot be loaded "never falls back to `model_families`"); BC-31; BC-39.

    `model_families` would place the two strings in two families and give I2 to the same client.
    """
    scene = replace(
        DELETED,
        base_lock=SEEDED_LOCK,
        staged_lock=SEEDED_LOCK,
        base_bindings=SPLIT,
        staged_bindings=SPLIT,
    )

    result = review(scene)

    assert "ORQ-E461" in codes(result)
    assert derived(result) != "I2"


@pytest.mark.parametrize("lock", LOCKS_THAT_SHOW_NO_DELETION)
def test_a_lock_that_shows_no_deletion_leaves_the_policy_never_present(lock: bytes | None) -> None:
    """expected_behavior_source: ADR-005 decision 2 ("Only a project where the file was never
    present gets the legacy rules"); AC-2 (a policy never present gives the legacy rules and
    ORQ-I460); the premise of `load_model_policy`, which reads a lock that is missing, unreadable,
    invalid, without the row or with a row that is not seeded as saying nothing.

    The lock is the same in both trees, so only what it says decides.
    """
    result = review(replace(DELETED, base_lock=lock, staged_lock=lock))

    assert found(result, "ORQ-I460")
    assert not codes(result) & {"ORQ-E460", "ORQ-E461", "ORQ-W462"}


def test_a_seeded_row_does_not_refuse_a_record_that_names_no_model() -> None:
    """expected_behavior_source: AC-2 ("ORQ-E461 for every record that names a model"); BC-44.

    The default record names no model, so neither the error nor the information is printed.
    """
    scene = Scene(base_policy=None, staged_policy=None, base_lock=SEEDED_LOCK)

    result = review(scene)

    assert not codes(result) & {"ORQ-E461", "ORQ-I460"}


def test_a_restored_policy_is_judged_although_the_lock_lists_it_as_seeded() -> None:
    """expected_behavior_source: ADR-007 decision 1 ("a valid staged policy with an absent base is
    judged on the staged tree ... which avoids both a deadlock and a hole"); BC-44; AC-2.

    The change restores the deleted file, so it is the staged policy that is judged and the change
    is a warning that the policy changed, not an error.
    """
    scene = replace(
        TWO_MODELS,
        base_policy=None,
        staged_policy=VALID,
        base_lock=SEEDED_LOCK,
        staged_lock=SEEDED_LOCK,
    )

    result = review(scene)

    warned(result, "ORQ-W462")
    assert "ORQ-E461" not in codes(result)


def test_the_refusal_of_a_deleted_seeded_policy_prints_no_recorded_text() -> None:
    """expected_behavior_source: AC-6 ("No finding and no data field of `validate review` contains
    a recorded model string ... or a text of a record"); BC-32.

    The marker is in each model field of the record, and the policy is refused.
    """
    marked = {
        "model_requested": MARKER,
        "model_observed": MARKER,
        "identity_source": "client-reported",
    }
    scene = replace(
        DELETED, base_lock=SEEDED_LOCK, staged_lock=SEEDED_LOCK, agent=marked, coder=marked
    )

    result = review(scene)

    assert "ORQ-E461" in codes(result)
    assert MARKER not in repr(result)


@pytest.mark.parametrize(
    "base",
    [
        pytest.param(None, id="no-bindings-file-at-the-base-tree"),
        pytest.param(NO_BINDINGS, id="no-binding-for-the-role-at-the-base-tree"),
    ],
)
def test_a_binding_that_exists_only_in_the_staged_tree_is_a_warning(base: bytes | None) -> None:
    """expected_behavior_source: AC-2 ("A binding that exists only in the staged tree is the
    warning `binding-added-in-this-change` (ORQ-W463) and not ORQ-E415"); BC-44; ADR-007
    decision 1 ("so the change that introduces the role is not deadlocked"); AC-4.

    The class that such a record gets is not stated, so none is asserted.
    """
    result = review(Scene(base_bindings=base))

    warned(result, "ORQ-W463")
    assert "ORQ-E415" not in codes(result)


@pytest.mark.parametrize(
    ("base", "staged"),
    [
        pytest.param(None, None, id="no-bindings-file-in-either-tree"),
        pytest.param(NO_BINDINGS, NO_BINDINGS, id="no-binding-for-the-role-in-either-tree"),
    ],
)
def test_a_binding_in_neither_tree_is_orq_e415(base: bytes | None, staged: bytes | None) -> None:
    """expected_behavior_source: AC-2 ("a binding in neither tree is ORQ-E415 as today"); BC-44;
    A-54 (an unapproved binding is the error ORQ-E415).

    This holds before the change too.
    """
    result = review(Scene(base_bindings=base, staged_bindings=staged))

    assert "ORQ-E415" in codes(result)
    assert "ORQ-W463" not in codes(result)
    assert result.verdict is Verdict.FAIL


# --- AC-3: an excluded model --------------------------------------------------------------------

EXCLUDED_FIELDS = [
    pytest.param({"model_requested": BANNED_MODEL}, None, id="agent-requested"),
    pytest.param({"model_observed": BANNED_MODEL}, None, id="agent-observed"),
    pytest.param(None, {"model_requested": BANNED_MODEL}, id="coder-requested"),
    pytest.param(None, {"model_observed": BANNED_MODEL}, id="coder-observed"),
]


@pytest.mark.parametrize(("agent", "coder"), EXCLUDED_FIELDS)
def test_an_excluded_model_in_any_field_is_e460_and_i0(
    agent: Mapping[str, object] | None, coder: Mapping[str, object] | None
) -> None:
    """expected_behavior_source: AC-3 ("A record whose `model_requested` or `model_observed`, for
    the agent or the coder, matches an exclusion is ORQ-E460 and its class is I0"); BC-9; BC-31;
    ADR-005 decision 2; ADR-007 decision 7 ("a record naming one gives an error and I0").

    Each of the four model fields in turn. The record claims I0, so ORQ-E412 cannot be the error.
    """
    result = review(replace(WITH_EXCLUSION, agent=agent, coder=coder))

    excluded = found(result, "ORQ-E460")
    assert excluded
    assert all(finding.severity is Severity.ERROR for finding in excluded)
    assert derived(result) == "I0"
    assert result.verdict is Verdict.FAIL


@pytest.mark.parametrize(
    "model",
    ["banned-alias", BANNED_MODEL, "zzbanned-5"],
    ids=["alias", "id-pattern", "family-tag"],
)
def test_every_kind_of_exclusion_matches(model: str) -> None:
    """expected_behavior_source: AC-3 ("matches an exclusion"); BC-9; ADR-005 decision 1
    ("`excluded[]` entries match by alias name, by model-ID pattern and by family tag").

    One rule holds an alias, an id pattern and a family tag; a model of each kind is caught.
    """
    result = review(replace(WITH_EXCLUSION, agent={"model_observed": model}))

    assert "ORQ-E460" in codes(result)
    assert derived(result) == "I0"


def test_a_record_that_names_no_model_is_unaffected_by_the_exclusion_check() -> None:
    """expected_behavior_source: AC-3 ("A record that names no model is unaffected by the
    exclusion check"); BC-9; BC-31.

    This holds before the change too: no error, and the class the record claims.
    """
    result = review(replace(WITH_EXCLUSION, independence="I1"))

    assert "ORQ-E460" not in codes(result)
    assert not result.errors
    assert derived(result) == "I1"


def test_a_model_that_no_exclusion_matches_is_not_e460() -> None:
    """expected_behavior_source: AC-3 (only a model that "matches an exclusion" is ORQ-E460);
    BC-9; ADR-005 decision 1.

    This holds before the change too.
    """
    result = review(replace(WITH_EXCLUSION, agent=observed("alpha-1")))

    assert "ORQ-E460" not in codes(result)
    assert not result.errors


# --- AC-4: the closed warnings ---------------------------------------------------------------

UNKNOWN_IDENTITIES = [
    pytest.param(None, None, id="no-model-recorded"),
    pytest.param(
        {"model_requested": "alpha-1"},
        {"model_requested": "beta-1"},
        id="requested-only",
    ),
    pytest.param(
        {"model_observed": "alpha-1", "identity_source": "unknown"},
        {"model_observed": "beta-1", "identity_source": "unknown"},
        id="observed-with-the-source-unknown",
    ),
    pytest.param(observed("alpha-1"), None, id="only-the-coder-unknown"),
]


@pytest.mark.parametrize(("agent", "coder"), UNKNOWN_IDENTITIES)
def test_an_unknown_identity_on_two_clients_warns_identity_unknown(
    agent: Mapping[str, object] | None, coder: Mapping[str, object] | None
) -> None:
    """expected_behavior_source: AC-4 ("`identity-unknown` (ORQ-W460)"); BC-17 ("a different
    client with an unknown identity gives I2 with the `identity-unknown` warning"); BC-19
    ("a requested-only model, or `identity_source: unknown`, is an unknown identity"); ADR-007
    decisions 2 and 5.

    A different client is I2 whatever the identity; the warning says that it rests on the client.
    """
    scene = replace(
        WITH_POLICY,
        client="claude-code",
        coder_client="cursor",
        agent=agent,
        coder=coder,
        independence="I2",
    )

    result = review(scene)

    warned(result, "ORQ-W460")
    assert derived(result) == "I2"
    assert not result.errors


def test_two_equal_observed_identities_on_two_clients_warn_same_model() -> None:
    """expected_behavior_source: AC-4 ("`same-model-different-client` (ORQ-W461)"); BC-17 ("a
    different client with two equal observed identities gives I2 with the
    `same-model-different-client` warning"); ADR-007 decision 5.

    Both clients name the one catalog model `cat-alpha`, observed and client-reported.
    """
    scene = replace(
        WITH_POLICY,
        client="cursor",
        coder_client="claude-code",
        agent=observed("alpha-1"),
        coder=observed("alpha-1"),
        independence="I2",
    )

    result = review(scene)

    warned(result, "ORQ-W461")
    assert "ORQ-W460" not in codes(result)
    assert derived(result) == "I2"


def test_two_different_known_identities_on_two_clients_give_neither_note() -> None:
    """expected_behavior_source: AC-4 (the two notes are for an unknown identity and for equal
    identities); BC-17 ("Recording an identity is never worse than omitting it"); ADR-007
    decision 5.

    Two different observed models of two clients are I2 with neither warning. This holds before
    the change too.
    """
    scene = replace(
        WITH_POLICY,
        client="claude-code",
        coder_client="cursor",
        agent=observed("alpha-1"),
        coder=observed("beta-1"),
        independence="I2",
    )

    result = review(scene)

    assert not codes(result) & {"ORQ-W460", "ORQ-W461"}
    assert derived(result) == "I2"


def test_a_requested_model_that_differs_from_the_observed_one_names_catalog_ids() -> None:
    """expected_behavior_source: AC-4 ("`model-requested-differs-from-observed` (ORQ-W464,
    naming catalog ids or `unmatched`)"); BC-19 ("a warning that names catalog ids or
    `unmatched`, never the recorded string"); ADR-007 decision 2.

    Requested `alpha-1`, observed `beta-1`: the message names `cat-alpha` and `cat-beta`.
    """
    agent = {**observed("beta-1"), "model_requested": "alpha-1"}

    result = review(replace(WITH_POLICY, agent=agent))

    message = warned(result, "ORQ-W464").message
    assert "cat-alpha" in message
    assert "cat-beta" in message
    assert "alpha-1" not in message
    assert "beta-1" not in message


def test_a_requested_model_that_differs_from_an_unmatched_one_names_unmatched() -> None:
    """expected_behavior_source: AC-4 ("naming catalog ids or `unmatched`"); BC-19; ADR-007
    decision 2 ("names the catalog ids, or `unmatched`"); AC-6 (no recorded string is echoed).

    The observed string is in no catalog entry. The format of `unmatched` with a length is not
    given, so only the word and the absence of the recorded string are asserted.
    """
    agent = {**observed("some-other-model"), "model_requested": "alpha-1"}

    result = review(replace(WITH_POLICY, agent=agent))

    message = warned(result, "ORQ-W464").message
    assert "unmatched" in message
    assert "some-other-model" not in message


def test_the_same_identity_requested_and_observed_gives_no_warning() -> None:
    """expected_behavior_source: BC-18 ("a bracketed option list ... or a different effort,
    speed or context size is not a difference"); ADR-007 decision 3 ("Equal known identities
    never count as a difference"); AC-4 (ORQ-W464 is for a requested model that differs).

    This holds before the change too.
    """
    agent = {**observed("alpha-1"), "model_requested": "alpha-1[effort=high]"}

    result = review(replace(WITH_POLICY, agent=agent))

    assert "ORQ-W464" not in codes(result)


@pytest.mark.parametrize(
    "limits",
    [
        pytest.param((), id="no-limit-stated"),
        pytest.param(("read-only is advisory",), id="another-limit"),
        pytest.param(("read-only is not enforced",), id="a-part-of-the-phrase"),
    ],
)
def test_a_codex_record_that_lacks_the_phrase_gets_w465(limits: tuple[str, ...]) -> None:
    """expected_behavior_source: AC-4 ("A `codex` record whose `capability_limits` lack the phrase
    'read-only is not enforced by this client' gets ORQ-W465"); BC-22; ADR-007 decision 9
    ("`validate review` warns when a `codex` record omits it").
    """
    result = review(Scene(client="codex", limits=limits))

    warned(result, "ORQ-W465")


@pytest.mark.parametrize(
    "limits",
    [
        pytest.param((PHRASE,), id="the-phrase-alone"),
        pytest.param(("read-only is advisory", PHRASE), id="the-phrase-among-other-limits"),
    ],
)
def test_a_codex_record_that_holds_the_phrase_gets_no_w465(limits: tuple[str, ...]) -> None:
    """expected_behavior_source: AC-4 ("one that holds it gets none"); BC-22; ADR-007 decision 9
    ("a record's `capability_limits` holds the fixed phrase").

    This holds before the change too. A phrase inside a longer sentence is a question.
    """
    result = review(Scene(client="codex", limits=limits))

    assert "ORQ-W465" not in codes(result)


@pytest.mark.parametrize("client", ["cursor", "claude-code"])
def test_a_record_of_another_client_never_gets_w465(client: str) -> None:
    """expected_behavior_source: AC-4 and BC-22 (the warning is for "a `codex` review record");
    ADR-007 decision 9 ("Claude Code uses a tool allow-list. Cursor `readonly: true` blocks file
    edits").

    This holds before the change too.
    """
    result = review(Scene(client=client, limits=()))

    assert "ORQ-W465" not in codes(result)


# --- AC-5: the fresh context and the code reviewer -------------------------------------------

CODE = Scene(role="code-reviewer")


def test_a_code_reviewer_without_a_context_is_i0_and_not_run() -> None:
    """expected_behavior_source: AC-5 ("A record of role `code-reviewer` with no `context` ...
    derives I0 and the result is NOT_RUN with the reason, not an error"); BC-16; R-8; ADR-007
    decision 4 ("a missing or false value gives I0 for that role").

    The text of the reason is not given: only that there is one.
    """
    result = review(CODE)

    assert derived(result) == "I0"
    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run
    assert not result.errors


def test_a_code_reviewer_with_a_stale_context_is_i0_and_not_run() -> None:
    """expected_behavior_source: AC-5 ("... or with `context.fresh` false, derives I0 and the
    result is NOT_RUN with the reason, not an error"); BC-16; R-8; ADR-007 decision 4.

    The text of the reason is not given: only that there is one.
    """
    result = review(replace(CODE, agent={"context": STALE}))

    assert derived(result) == "I0"
    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run
    assert not result.errors


@pytest.mark.parametrize("klass", ["D1", "D2", "D3"])
def test_a_code_reviewer_below_i2_is_not_run_with_its_reason(klass: str) -> None:
    """expected_behavior_source: AC-5 ("a record below I2 is NOT_RUN with the text 'independence
    I1 is below I2, which the code reviewer requires at every change class'"); BC-16; R-10;
    ADR-006 decision 4 ("A class below the minimum is NOT_RUN with the exact reason");
    ADR-007 decision 4.

    A fresh context on the coder's own client is I1, at every change class.
    """
    result = review(replace(CODE, agent={"context": FRESH}, change_class=klass))

    assert derived(result) == "I1"
    assert result.verdict is Verdict.NOT_RUN
    assert any(CODE_REVIEWER_TEXT in reason for reason in result.not_run)
    assert not result.errors


def test_a_code_reviewer_at_i2_in_a_fresh_context_passes() -> None:
    """expected_behavior_source: AC-5 (the code reviewer requires I2, so I2 is not below it);
    BC-16; R-10; ADR-006 decision 4 ("The code reviewer needs at least I2 at every class").

    A different client in a fresh context is I2 and a bound record is a PASS. This holds before
    the change too.
    """
    scene = replace(
        CODE,
        agent={"context": FRESH},
        coder_client="claude-code",
        independence="I2",
    )

    result = review(scene)

    assert derived(result) == "I2"
    assert result.verdict is Verdict.PASS


@pytest.mark.parametrize("role", ["architecture-reviewer", "security-reviewer"])
def test_another_role_with_a_stale_context_is_i0(role: str) -> None:
    """expected_behavior_source: AC-5 ("a record of the other two roles with `context.fresh:
    false` is I0"); BC-16; ADR-007 decision 4 ("a `false` value gives I0").
    """
    result = review(Scene(role=role, agent={"context": STALE}))

    assert derived(result) == "I0"
    assert result.verdict is Verdict.NOT_RUN
    assert not result.errors


@pytest.mark.parametrize("role", ["architecture-reviewer", "security-reviewer"])
def test_another_role_without_a_context_is_as_before(role: str) -> None:
    """expected_behavior_source: AC-5 ("and one with no `context` is as before"); BC-16; ADR-007
    decision 4 ("For the other two roles it is optional so existing records stay valid").

    The same client, an approved binding and no context are I1 and a PASS. This holds before the
    change too.
    """
    result = review(Scene(role=role, independence="I1"))

    assert derived(result) == "I1"
    assert result.verdict is Verdict.PASS


# --- AC-6: no recorded string, no key of the policy, no text of a record ------------------------


def marked(field: str) -> str:
    return f"{MARKER}-{field}"


MARKED_ENTRY = entry(
    "cat-marked",
    marked("family"),
    route("cursor", marked("route-name"), also_known_as=[marked("also-known-as")]),
    {
        "client": "codex",
        "kind": "alias",
        "name": marked("alias-name"),
        "resolves_to": marked("route-name"),
    },
)
MARKED_RULE = {
    "id": "marked-rule",
    "reason": "Example reason, printable ASCII text.",
    "source": "Example notice of the team.",
    "aliases": [marked("excluded-alias")],
    "id_patterns": [marked("excluded-pattern-*")],
    "family_tags": [marked("excluded-tag")],
}
MARKED_ASSIGNMENT = {
    "target": {"kind": "role", "name": "example-role"},
    "model": marked("assignment-model"),
    "mode": "manual",
}
MARKED_POLICY = policy(
    MARKED_ENTRY, excluded=[MARKED_RULE], extra={"assignments": [MARKED_ASSIGNMENT]}
)
MARKED_AGENT: dict[str, object] = {
    "model_requested": marked("route-name"),
    "model_observed": marked("agent-observed"),
    "identity_source": "client-reported",
}
MARKED_CODER: dict[str, object] = {
    "model_requested": marked("coder-requested"),
    "model_observed": marked("coder-observed"),
    "identity_source": "client-reported",
}
MARKED = Scene(
    base_policy=MARKED_POLICY,
    staged_policy=MARKED_POLICY,
    agent=MARKED_AGENT,
    coder=MARKED_CODER,
    limits=(marked("limit"),),
)
MARKED_SCENES = [
    pytest.param(MARKED, "ORQ-W464", id="requested-differs-from-observed"),
    pytest.param(
        replace(MARKED, agent={**MARKED_AGENT, "model_observed": marked("excluded-alias")}),
        "ORQ-E460",
        id="excluded",
    ),
    pytest.param(
        replace(MARKED, staged_policy=policy(MARKED_ENTRY, extra={marked("key"): 1})),
        "ORQ-E461",
        id="staged-policy-with-an-unknown-key",
    ),
    pytest.param(
        replace(MARKED, base_policy=None),
        "ORQ-W462",
        id="base-policy-missing",
    ),
    pytest.param(
        replace(MARKED, base_policy=None, staged_policy=None),
        "ORQ-I460",
        id="no-policy",
    ),
    pytest.param(
        replace(MARKED, client="codex"),
        "ORQ-W465",
        id="codex-without-the-phrase",
    ),
]


@pytest.mark.parametrize(("scene", "code"), MARKED_SCENES)
def test_no_result_shows_a_marker_of_the_record_or_the_policy(scene: Scene, code: str) -> None:
    """expected_behavior_source: AC-6 ("A test places a unique marker in each model field of a
    record and of the policy and finds it nowhere in the result"); BC-32 ("no finding prints a
    recorded model string"); BC-19; ADR-002 decision 3.

    The marker is in the four model fields of the record, in a limit of the record, and in the
    route names, `also_known_as`, family, exclusion rule and assignment of the policy, or in an
    unknown key of a refused policy. The rule `code` of each case must be reached, so that the
    test cannot pass by a result that says nothing; the result is searched as a whole.
    """
    result = review(scene)

    assert code in codes(result)
    assert MARKER not in repr(result)


# --- AC-7: the records that exist today keep their verdict ------------------------------------


@dataclass(frozen=True)
class Shape:
    """One of the three shapes among the 112 records, and what it gives today and after."""

    scene: Scene
    derived: str
    verdict: Verdict
    reason: str | None
    warnings: frozenset[str]


SHAPES = {
    "cursor-with-cursor": Shape(
        scene=Scene(independence="I1"),
        derived="I1",
        verdict=Verdict.PASS,
        reason=None,
        warnings=frozenset(),
    ),
    "codex-with-cursor": Shape(
        scene=Scene(
            client="codex",
            independence="I2",
            limits=("The reviewer did not separately report its model identifier.",),
        ),
        derived="I2",
        verdict=Verdict.PASS,
        reason=None,
        warnings=frozenset({"identity-unknown", "codex-read-only-not-stated"}),
    ),
    "d3-below-i2": Shape(
        scene=Scene(change_class="D3", independence="I1"),
        derived="I1",
        verdict=Verdict.NOT_RUN,
        reason=D3_TEXT,
        warnings=frozenset(),
    ),
}
POLICY_STATES = pytest.mark.parametrize(
    "raw", [None, VALID], ids=["no-policy", "policy-in-both-trees"]
)


@POLICY_STATES
@pytest.mark.parametrize("shape", list(SHAPES.values()), ids=list(SHAPES))
def test_a_shape_keeps_its_verdict_and_errors(shape: Shape, raw: bytes | None) -> None:
    """expected_behavior_source: AC-7 ("shows, for the three shapes among the 112 records (cursor
    with cursor and null models, codex with cursor and null models, and a D3 change below I2),
    the same verdict and the same errors as before"); BC-20; C-7; A-65; A-53 (a class below the
    minimum is a skipped check and gives NOT_RUN).

    A characterisation test: every case passes on today's code. The three shapes hold null model
    fields; the policy is not in either tree, or the same valid policy is in both.
    """
    result = review(replace(shape.scene, base_policy=raw, staged_policy=raw))

    assert derived(result) == shape.derived
    assert result.verdict is shape.verdict
    assert not result.errors
    if shape.reason is not None:
        assert any(shape.reason in reason for reason in result.not_run)


@POLICY_STATES
@pytest.mark.parametrize("shape", list(SHAPES.values()), ids=list(SHAPES))
def test_a_shape_gets_only_the_warnings_that_apply(shape: Shape, raw: bytes | None) -> None:
    """expected_behavior_source: AC-7 ("with only the warnings of AC-4 that apply to them");
    BC-20 ("each record now also reports the new warnings that apply to its fields"); BC-17;
    BC-22; ADR-007 decisions 5 and 9.

    A different client with null models is `identity-unknown`; a `codex` record without the
    phrase is `codex-read-only-not-stated`; the same client and a D3 change give no warning.
    """
    result = review(replace(shape.scene, base_policy=raw, staged_policy=raw))

    assert {WARNINGS[code] for code in codes(result) if code in WARNINGS} == shape.warnings
    assert prefixed_names(result) == shape.warnings
    assert notes_of(result) == shape.warnings
