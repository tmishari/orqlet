"""The shipped seed of the model policy and its guard tests (task dynamic-model-profiles, P-13).

The seed is `seeds/orqlet/model-policy.yaml` of the workflow package. Every test cites its
`expected_behavior_source`: AC-n is an acceptance criterion of phase P-13 in
docs/design/dynamic-model-profiles/plan.yaml, BC-n a behaviour of design/component.md, ADR-n a
decision record of design/, Q-n a question of questions.yaml, and "the interface" the section 4 of
the interface that the Coder of P-13 gave the Tester (the wording of the seed that the criteria
leave open).

These tests were written first, by the Tester of phase P-13, before the seed existed. They cover
AC-10 (what the seed holds and that it passes `orqlet validate model-policy`), AC-11 (the guard
tests, each shown to fail on a broken copy) and the identity part of AC-1 (`identity.json` states
workflow version 0.5.1 at controls level 3, and the seed's `reviewed_for_release` equals it).

Task workflow-efficiency, phase P-8 (release 0.5.1) moves the identity, the CLI version and the
`reviewed_for_release` marker of the seed and of the repository policy to 0.5.1. Those tests were
written first, by the Tester of P-8; each cites AC-n of P-8 in
docs/design/workflow-efficiency/plan.yaml, Q-n of docs/design/workflow-efficiency/questions.yaml,
or EC-n of docs/design/workflow-efficiency/design/manifest.yaml.

The guards of AC-11 live in `guard_problems`, one function that returns the set of problem codes
of a parsed seed. The guard tests of the shipped seed and the broken-copy tests call that same
function, so a guard that could never fail cannot pass for the shipped seed. A broken copy is the
parsed seed with one value changed; it is not written to a file.

The guards prove consistency with the cited evidence page and not the truth of the page (ADR-004
decision 4). Behaviour that the criteria and the interface leave open is not pinned: the order of
the routes of one model, the client order inside a profile's candidates, the order of the ten
assignments, the `also_known_as` and `retires_on` of a route, the list prices, and the wording of
the free texts beyond printable ASCII within 400 characters.

The file system is the in-memory fake, the repository is `FakeVcs`, and the clock is `FixedClock`
(ORQLET-TEST-001). No secret is written here (ORQLET-SEC-003).
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

import pytest

import orqlet
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.model_policy_source import PolicyLoaded, load_model_policy
from orqlet.application.usecases.model_selection import select_models
from orqlet.application.usecases.validate_model_policy import (
    ModelPolicyServices,
    validate_model_policy,
)
from orqlet.application.usecases.validation import ValidationResult
from orqlet.application.usecases.workflow_sources import load_roles, load_skills
from orqlet.domain.findings import Severity, Verdict
from orqlet.domain.model_identity import ExclusionRule, is_excluded, normalise
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs

pytestmark = pytest.mark.unit

Doc = dict[str, Any]

SEED_SOURCE = "seeds/orqlet/model-policy.yaml"
POLICY_PATH = ".orqlet/model-policy.yaml"
ROOT = Path(__file__).resolve().parents[2]
IDENTITY = ROOT / "src" / "orqlet" / "workflow" / "identity.json"
MANIFEST = ROOT / "src" / "orqlet" / "workflow" / "MANIFEST.json"
EVIDENCE_DIR = "docs/design/dynamic-model-profiles/evidence/web/"
LOADER = StrictYamlLoader()
CLIENTS = ("claude-code", "codex", "cursor")
HEAD = "a" * 40
BASE = "b" * 40

OPENAI = "openai-gpt-6-astra-and-pricing.md"
ANTHROPIC = "anthropic-models-overview.md"
GOOGLE = "google-gemini-4-argon-model-card.md"
XAI = "xai-models.md"
CURSOR_PAGE = "cursor-models-and-pricing.md"

# The catalog of the interface (section 4): id, family, evidence file, and the routes as
# (client, name). A Cursor route has no name (Q-35).
CATALOG: tuple[tuple[str, str, str, tuple[tuple[str, str | None], ...]], ...] = (
    ("gpt-6-astra", "openai", OPENAI, (("codex", "gpt-6-astra"),)),
    ("gpt-6.1-sol", "openai", OPENAI, (("codex", "gpt-6.1-sol"),)),
    ("gpt-6.1-terra", "openai", OPENAI, (("codex", "gpt-6.1-terra"),)),
    ("gpt-6-luna", "openai", OPENAI, (("codex", "gpt-6-luna"),)),
    (
        "claude-opus-5-5",
        "anthropic",
        ANTHROPIC,
        (("claude-code", "claude-opus-5-5"), ("cursor", None)),
    ),
    (
        "claude-sonnet-5-5",
        "anthropic",
        ANTHROPIC,
        (("claude-code", "claude-sonnet-5-5"), ("cursor", None)),
    ),
    (
        "claude-haiku-5-5",
        "anthropic",
        ANTHROPIC,
        (("claude-code", "claude-haiku-5-5"), ("cursor", None)),
    ),
    ("gemini-4-argon", "google", GOOGLE, (("cursor", None),)),
    ("grok-4.7", "xai", XAI, (("cursor", None),)),
    ("composer-2.5", "cursor", CURSOR_PAGE, (("cursor", None),)),
)

# The table of ADR-002 decision 7: the ordered candidates of each profile for each client.
PROFILES: dict[str, dict[str, tuple[str, ...]]] = {
    "quality": {
        "codex": ("gpt-6-astra", "gpt-6.1-sol"),
        "claude-code": ("claude-opus-5-5",),
        "cursor": ("claude-opus-5-5", "gemini-4-argon"),
    },
    "engineering": {
        "codex": ("gpt-6.1-sol", "gpt-6.1-terra"),
        "claude-code": ("claude-sonnet-5-5",),
        "cursor": ("claude-sonnet-5-5", "grok-4.7", "composer-2.5"),
    },
    "economy": {
        "codex": ("gpt-6-luna",),
        "claude-code": ("claude-haiku-5-5",),
        "cursor": ("claude-haiku-5-5", "composer-2.5"),
    },
}

# AC-10: the ten starting assignments, (kind, name) -> profile (ADR-002 decision 6).
ASSIGNMENTS: dict[tuple[str, str], str] = {
    ("skill", "orqlet-design"): "quality",
    ("skill", "orqlet-plan"): "quality",
    ("role", "orqlet-arch-reviewer"): "quality",
    ("role", "orqlet-security-reviewer"): "quality",
    ("skill", "orqlet-implement"): "engineering",
    ("role", "orqlet-tester"): "engineering",
    ("role", "orqlet-code-reviewer"): "engineering",
    ("role", "orqlet-inventory"): "economy",
    ("role", "orqlet-tracer"): "economy",
    ("role", "orqlet-pr-writer"): "economy",
}


# --- the seed, as the package ships it -----------------------------------------------------


@cache
def seed_text() -> str:
    return PackagedWorkflow().read_text(SEED_SOURCE)


def seed_data() -> Doc:
    """A fresh copy of the parsed seed, so a test can change it freely."""
    parsed = LOADER.load(seed_text().encode("utf-8"), source=SEED_SOURCE)
    assert isinstance(parsed, dict)
    return copy.deepcopy(parsed)


def seed_policy() -> ModelPolicy:
    return load_contract(LOADER, ModelPolicy, seed_text().encode("utf-8"), source=SEED_SOURCE)


def identity_version() -> str:
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    assert isinstance(identity["workflow_version"], str)
    return identity["workflow_version"]


def models_by_id(data: Doc) -> dict[str, Doc]:
    return {model["id"]: model for model in data["models"]}


def all_routes(data: Doc) -> Iterator[tuple[Doc, Doc]]:
    for model in data["models"]:
        for route in model["routes"]:
            yield model, route


# --- `orqlet validate model-policy` on a seed ---------------------------------------------


def vcs_with_a_base() -> FakeVcs:
    """One commit `HEAD` whose merge base with the explicit base `BASE` is `BASE` (no policy)."""
    return FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEAD, "head"),),
        revisions={BASE: {}},
        merge_bases={(HEAD, BASE): (BASE,)},
    )


def validate(raw: bytes) -> ValidationResult:
    """The use case behind `orqlet validate model-policy`, on a project that holds `raw`."""
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(POLICY_PATH), raw)
    services = ModelPolicyServices(
        project=project,
        vcs=vcs_with_a_base(),
        loader=LOADER,
        workflow=PackagedWorkflow(),
        clock=FixedClock(datetime(2026, 11, 19, 12, 0, tzinfo=UTC)),
    )
    return validate_model_policy(services, POLICY_PATH, BASE)


# =============================================================================================
# AC-10: what the seed holds
# =============================================================================================


def test_the_seed_passes_validate_model_policy() -> None:
    """AC-10. expected_behavior_source: AC-10 ("passes `orqlet validate model-policy` in a test");
    BC-11; R-2. The strict reader, the contract, the exclusion and reference checks of
    `select_models`, the approvals, the release review and the retirement dates all find nothing:
    PASS with no finding and nothing not run. The packaged workflow has the version of
    `identity.json`, so no warning says that the policy is older than the workflow.
    """
    result = validate(seed_text().encode("utf-8"))

    assert result.errors == ()
    assert result.verdict is Verdict.PASS
    assert result.not_run == ()
    assert [f for f in result.findings if f.severity is not Severity.INFO] == []


def test_the_validator_of_this_test_does_fail_on_an_unsound_seed() -> None:
    """AC-10. expected_behavior_source: AC-10 and ADR-004 decision 1 (an `approved` entry needs an
    approver, ORQ-E546). A control: the same call that passes the seed refuses a copy in which one
    model is approved with no approver, so "passes" above is not vacuous.
    """
    data = seed_data()
    data["models"][0]["approval"]["state"] = "approved"

    # Indented: the reader refuses a single line of thousands of characters (ORQ-E542).
    result = validate(json.dumps(data, indent=2).encode("utf-8"))

    assert result.verdict is Verdict.FAIL
    assert "ORQ-E546" in {f.code for f in result.errors}


def test_the_strict_reader_loads_the_seed_as_it_loads_a_team_file() -> None:
    """AC-10. expected_behavior_source: AC-10; ADR-002 decision 3 (the one reader of the policy:
    the size limit, the strict YAML rules, the contract and the credential scan, ORQLET-SEC-002,
    ORQLET-SEC-003). The seed carries no credential-shaped text.
    """
    project = MemoryFileSystem()
    project.write_atomic(CanonicalPath.parse(POLICY_PATH), seed_text().encode("utf-8"))
    services = ModelPolicyServices(
        project, vcs_with_a_base(), LOADER, PackagedWorkflow(), FixedClock()
    )

    state = load_model_policy(services)

    assert isinstance(state, PolicyLoaded)
    assert state.policy == seed_policy()


def test_the_header_is_schema_v2_version_1_and_reviewed_for_the_release() -> None:
    """AC-10, AC-1. expected_behavior_source: the interface section 4 (schema
    `orqlet.model-policy/v2`, `policy_version: 1`, `reviewed_for_release` equal to the workflow
    version); ADR-002 decision 1; AC-1 (the workflow version is 0.5.1 since P-8 of
    workflow-efficiency); Q-23 (the seed says `reviewed_for_release` 0.5.1).
    """
    policy = seed_policy()

    assert policy.schema_id == "orqlet.model-policy/v2"
    assert policy.policy_version == 1
    assert policy.reviewed_for_release == "0.5.1"


def test_the_catalog_holds_the_ten_models_with_their_families() -> None:
    """AC-10. expected_behavior_source: AC-10 ("Its catalog and profiles are the table of ADR-002
    decision 7"); the interface section 4 (ten models; the family is the vendor, the fail-safe
    reading while Q-38 is open).
    """
    policy = seed_policy()

    assert [(m.id, m.family) for m in policy.models] == [(c[0], c[1]) for c in CATALOG]


def test_the_catalog_has_no_model_gpt_6_sol() -> None:
    """AC-10. expected_behavior_source: AC-10 ("no model `gpt-6-sol`"); ADR-002 decision 7 (the
    Codex app's "GPT-6 Sol" has no documented model id and stays outside the starting catalog).
    No id, route name, alias target or other spelling of a model normalises to `gpt-6-sol`.
    """
    data = seed_data()
    spellings = [model["id"] for model in data["models"]]
    for _, route in all_routes(data):
        spellings += [route["name"], route.get("resolves_to"), *route.get("also_known_as", [])]

    assert "gpt-6-sol" not in {normalise(s) for s in spellings if s is not None}
    assert "gpt-6-sol" not in models_by_id(data)


def test_every_model_is_proposed_not_called_and_not_evaluated() -> None:
    """AC-10. expected_behavior_source: AC-10 ("Every model has `approval.state: proposed`,
    `callable: not-run`, `evaluated.state: none`"); ADR-004 decision 3 (everything Orqlet ships is
    `proposed`); ADR-002 decision 4 (the five states are separate); the interface section 4
    (`approved_by` and `approval_ref` null, no evaluation evidence).
    """
    for model in seed_policy().models:
        assert model.approval.state == "proposed", model.id
        assert model.approval.approved_by is None, model.id
        assert model.approval.approval_ref is None, model.id
        assert model.callable == "not-run", model.id
        assert model.evaluated.state == "none", model.id
        assert model.evaluated.evidence is None, model.id


def test_every_model_cites_one_evidence_file_of_the_release_research_dated_2026_11_04() -> None:
    """AC-10, AC-11. expected_behavior_source: the interface section 4 (a `documented` reference to
    one evidence file under docs/design/dynamic-model-profiles/evidence/web/, dated 2026-11-04);
    ADR-004 decision 4 (the evidence file of a release lives in the repository). The file of each
    entry exists, so the guards of AC-11 have a page to read.
    """
    for model in seed_policy().models:
        expected = next(c[2] for c in CATALOG if c[0] == model.id)

        assert model.documented.evidence == f"{EVIDENCE_DIR}{expected}", model.id
        assert model.documented.date == "2026-11-04", model.id
        assert (ROOT / model.documented.evidence).is_file(), model.id


def test_the_routes_are_the_ones_of_the_interface() -> None:
    """AC-10. expected_behavior_source: the interface section 4 (the four `gpt-*` models: one route
    for `codex`; each `claude-*` model: a route for `claude-code` named as its id and one for
    `cursor` with no name; `gemini-4-argon`, `grok-4.7` and `composer-2.5`: one `cursor` route
    with no name); AC-10 (every route `access: unknown`; `resolves_to` null on every id route).
    The order of the routes of one model is not pinned.
    """
    policy = seed_policy()

    for model, (model_id, _family, _page, expected) in zip(policy.models, CATALOG, strict=True):
        assert model.id == model_id
        assert len(model.routes) == len(expected), model_id
        assert sorted((r.client, r.name or "") for r in model.routes) == sorted(
            (client, name or "") for client, name in expected
        ), model_id
        for route in model.routes:
            assert route.kind == "id", model_id
            assert route.resolves_to is None, model_id
            assert route.access == "unknown", model_id


def test_no_cursor_route_has_a_name() -> None:
    """AC-10. expected_behavior_source: AC-10 ("no Cursor route `name` (all null, Q-35)"); Q-35
    (no fetched page states the Cursor model ids); ADR-002 decision 7 ("those routes ship with no
    `name` and stay `missing-candidate`"). Cursor has a route for six models.
    """
    cursor_routes = [r for m in seed_policy().models for r in m.routes if r.client == "cursor"]

    assert len(cursor_routes) == 6
    assert [r.name for r in cursor_routes] == [None] * 6


def test_every_route_access_is_unknown() -> None:
    """AC-10. expected_behavior_source: AC-10 ("every route `access: unknown`"); ADR-002 decision 7
    ("the shipped seed holds `access: unknown` for every route; a team records `confirmed` in its
    own file"); ADR-004 decision 4.
    """
    accesses = {r.access for m in seed_policy().models for r in m.routes}

    assert accesses == {"unknown"}


def test_the_fable_exclusion_is_one_entry_with_aliases_a_pattern_and_a_tag() -> None:
    """AC-10. expected_behavior_source: AC-10 ("the Fable exclusion (aliases `fable` and `best`, id
    pattern `claude-fable-*`, family tag `fable`)"); ADR-005 decision 1 (the shipped seed carries
    one entry for Fable); the interface section 4 (one entry, id `fable`); ADR-004 decision 4 ("a
    test keeps it in the seed").
    """
    (rule,) = seed_policy().excluded

    assert rule.id == "fable"
    assert sorted(rule.aliases) == ["best", "fable"]
    assert list(rule.id_patterns) == ["claude-fable-*"]
    assert list(rule.family_tags) == ["fable"]
    assert rule.reason.strip()
    assert rule.source.strip()


@pytest.mark.parametrize(
    "spelling",
    [
        "fable",
        "best",
        "claude-fable-5-1",
        "claude-fable-5",
        "Fable5",
        "x[model=fable]",
        "Fable 5.1",
    ],
)
def test_the_exclusion_of_the_seed_matches_every_spelling_of_fable(spelling: str) -> None:
    """AC-10. expected_behavior_source: ADR-005 decision 1 (the matching rule: an alias, an id
    pattern and a family tag, on the raw and the normalised string, so `Fable5`,
    `fable-5.1-xhigh` and `x[model=fable]` all match); ADR-005 decision 3 (`best` is never
    rendered).
    """
    (rule,) = seed_policy().excluded
    rules = [ExclusionRule(rule.aliases, rule.id_patterns, rule.family_tags)]

    assert is_excluded(spelling, rules)


def test_the_exclusion_of_the_seed_matches_no_model_of_the_catalog() -> None:
    """AC-10. expected_behavior_source: ADR-005 decision 2 (an exclusion applies to entries in every
    state, so a seed model that it matched would be refused, ORQ-E543); ADR-005 decision 1 ("Fable
    models are not candidates", ADR-002 decision 7).
    """
    policy = seed_policy()
    (rule,) = policy.excluded
    rules = [ExclusionRule(rule.aliases, rule.id_patterns, rule.family_tags)]
    strings = [m.id for m in policy.models] + [m.family for m in policy.models]
    strings += [r.name for m in policy.models for r in m.routes if r.name is not None]

    assert [s for s in strings if is_excluded(s, rules)] == []


def test_the_profiles_are_the_table_of_adr_002_decision_7_in_the_mode_automatic() -> None:
    """AC-10. expected_behavior_source: AC-10 ("Its catalog and profiles are the table of ADR-002
    decision 7, its profile modes are `automatic`"); ADR-002 decision 6 (the profiles are ordered
    `quality`, `engineering`, `economy`); the interface section 4 (no fallbacks, no escalation).
    """
    policy = seed_policy()

    assert [p.id for p in policy.profiles] == ["quality", "engineering", "economy"]
    for profile in policy.profiles:
        assert profile.mode == "automatic", profile.id
        assert profile.fallbacks == (), profile.id
        assert profile.escalation is None, profile.id
        assert profile.capability.strip(), profile.id
        assert {c.client: c.models for c in profile.candidates} == PROFILES[profile.id], profile.id
        assert len(profile.candidates) == 3, profile.id


def test_the_ten_assignments_are_the_starting_assignments_of_adr_002_decision_6() -> None:
    """AC-10. expected_behavior_source: AC-10 (the ten assignments, each skill or role on its
    profile); ADR-002 decision 6 (`quality` for design, plan, architecture review and security
    review; `engineering` for implement, test and code review; `economy` for inventory, trace and
    PR text); the interface section 4 (each `mode: automatic`, no client, no task, no model, no
    effort). The order of the assignments is not pinned.
    """
    assignments = seed_policy().assignments

    assert len(assignments) == 10
    assert {(a.target.kind, a.target.name): a.profile for a in assignments} == ASSIGNMENTS
    for assignment in assignments:
        assert assignment.mode == "automatic", assignment.target
        assert assignment.model is None, assignment.target
        assert assignment.client is None, assignment.target
        assert assignment.task is None, assignment.target
        assert assignment.effort is None, assignment.target


def test_the_roles_and_skills_that_the_seed_assigns_exist_in_the_packaged_workflow() -> None:
    """AC-10, AC-12. expected_behavior_source: AC-10 and AC-12 (the seed passes the checks of the
    selection, so no assignment names a role or skill that does not exist: ORQ-E545); ADR-006
    decisions 1 and 8 (the roles `orqlet-code-reviewer` and `orqlet-pr-writer` ship in the same
    release as the seed).
    """
    workflow = PackagedWorkflow()
    roles = {role.name for role in load_roles(workflow)}
    skills = {skill.name for skill in load_skills(workflow, IMPLEMENTED_COMMANDS)}

    for kind, name in ASSIGNMENTS:
        assert name in (roles if kind == "role" else skills), (kind, name)


def test_the_selection_refuses_nothing_warns_of_nothing_and_pins_nothing() -> None:
    """AC-10. expected_behavior_source: AC-10; ADR-002 consequences ("Seeded `proposed` entries make
    nothing render: a pin needs `approved`"); BC-11; ADR-003 (only a pin renders). Every mode is
    `automatic`, so there is no problem (ORQ-E543, ORQ-E545), no finding of an unrenderable
    setting, no missing candidate (ORQ-W540), and no role or skill is pinned for any client.
    """
    workflow = PackagedWorkflow()
    selection = select_models(
        seed_policy(),
        [role.name for role in load_roles(workflow)],
        [skill.name for skill in load_skills(workflow, IMPLEMENTED_COMMANDS)],
        CLIENTS,
    )

    assert selection.problems == ()
    assert selection.findings == ()
    assert selection.missing == ()
    assert dict(selection.roles) == {}
    assert dict(selection.skills) == {}


# =============================================================================================
# AC-1: the identity of the workflow
# =============================================================================================


def test_identity_states_workflow_version_0_5_1_at_controls_level_3() -> None:
    """AC-1 of P-8. expected_behavior_source: P-8 AC-1 (BC-24; "identity.json ... name
    workflow_version 0.5.1 ... controls_level stays 3"); Q-15 (both the CLI and the workflow
    package become 0.5.1); EC-6 (identity.json names workflow_version 0.5.1).
    """
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))

    assert identity["workflow_version"] == "0.5.1"
    assert identity["controls_level"] == 3


def test_the_cli_version_is_0_5_1_and_is_the_workflow_version() -> None:
    """AC-1 of P-8. expected_behavior_source: P-8 AC-1 (BC-24; "`orqlet --version` and every JSON
    result report 0.5.1"); Q-15 ("Both the CLI and the workflow package become 0.5.1"); EC-7
    (`orqlet --version` and the `orqlet_version` field of every JSON result: 0.5.1). Both read
    `orqlet.__version__`, so the one value is what they report.
    """
    assert orqlet.__version__ == "0.5.1"
    assert orqlet.__version__ == identity_version()


def test_the_manifest_names_workflow_version_0_5_1() -> None:
    """AC-1 of P-8. expected_behavior_source: P-8 AC-1 ("MANIFEST.json name[s] workflow_version
    0.5.1 and the manifest is rebuilt"); EC-6 ("MANIFEST.json is rebuilt from identity.json").
    That the manifest is the rebuild of the sources is checked by tests/unit/test_manifest.py.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["workflow_version"] == "0.5.1"
    assert manifest["controls_level"] == 3


def test_the_repository_policy_is_reviewed_for_the_release_and_raises_no_stale_review() -> None:
    """AC-2 of P-8. expected_behavior_source: Q-23 (answer: raise `reviewed_for_release` to 0.5.1
    in the seed and in `.orqlet/model-policy.yaml`, no other policy field changes; the repository
    policy warned ORQ-W541 while it stayed at 0.5.0); P-8 AC-2. Only the marker and its effect
    are asserted: the file is the team's, so no other field is compared with the seed.
    """
    raw = (ROOT / POLICY_PATH).read_bytes()
    parsed = LOADER.load(raw, source=POLICY_PATH)
    assert isinstance(parsed, dict)

    result = validate(raw)

    assert parsed["reviewed_for_release"] == "0.5.1"
    assert "ORQ-W541" not in {f.code for f in result.findings}


def test_the_shipped_seed_passes_the_release_guard_against_identity_0_5_1() -> None:
    """AC-2 of P-8. expected_behavior_source: P-8 AC-2 ("the seed guard passes against identity
    0.5.1"); Q-23; ADR-004 decision 4 of dynamic-model-profiles. The guard is called with the
    literal version, so the check does not follow `identity.json` by accident.
    """
    assert identity_version() == "0.5.1"
    assert guard_problems(seed_data(), "0.5.1") == set()


def test_the_package_manifest_carries_the_version_of_the_identity() -> None:
    """AC-1. expected_behavior_source: AC-1 ("`MANIFEST.json` is rebuilt"); ORQLET-DET-002. The
    release that the packaged workflow reports is the version of `identity.json`, which is also
    the version that the stale-review warning of the validator compares with.
    """
    release = PackagedWorkflow().release

    assert str(release.version) == identity_version()
    assert release.controls_level == 3


# =============================================================================================
# AC-11: the guard tests, and a broken copy for each
# =============================================================================================

REVIEWED = "reviewed-for-release-differs-from-the-identity"
EVIDENCE_MISSING = "evidence-file-is-missing"
ID_ABSENT = "id-is-not-in-the-evidence"
FAMILY_ABSENT = "family-is-not-in-the-evidence"
NAME_ABSENT = "route-name-is-not-in-the-evidence"
RESOLVES_ABSENT = "route-resolves-to-is-not-in-the-evidence"
ACCESS = "route-access-is-not-unknown"
NOT_ASCII = "text-is-not-printable-ascii"
TOO_LONG = "text-is-over-400-characters"
LIMIT = 400


@cache
def page_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@cache
def normalised_page(relative: str) -> str:
    """The page with each line in the identity form of ADR-005.

    The brackets are made spaces first: `normalise` drops a bracketed option list, which in a page
    is the text of a Markdown link and not an option of a model.
    """
    lines = (
        normalise(line.replace("[", " ").replace("]", " "))
        for line in page_text(relative).splitlines()
    )
    return "\n".join(lines)


def appears_after_normalisation(value: str, relative: str) -> bool:
    """`composer-2.5` is found in a page that writes "Composer 2.5"; a longer word is not."""
    wanted = normalise(value)
    pattern = rf"(?<![a-z0-9]){re.escape(wanted)}(?![a-z0-9])"
    return bool(wanted) and re.search(pattern, normalised_page(relative)) is not None


def strings_of(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_of(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_of(item)


def guard_problems(data: Doc, version: str) -> set[str]:
    """Every guard of AC-11 on a parsed seed: the set of the problems that it finds."""
    found: set[str] = set()
    if data.get("reviewed_for_release") != version:
        found.add(REVIEWED)
    for model in data["models"]:
        relative = model["documented"]["evidence"]
        if not (ROOT / relative).is_file():
            found.add(EVIDENCE_MISSING)
            continue
        if not appears_after_normalisation(model["id"], relative):
            found.add(ID_ABSENT)
        if not appears_after_normalisation(model["family"], relative):
            found.add(FAMILY_ABSENT)
        for route in model["routes"]:
            if route["access"] != "unknown":
                found.add(ACCESS)
            # Verbatim: the letter case and the separators of the page, with no normalisation.
            if route.get("name") is not None and route["name"] not in page_text(relative):
                found.add(NAME_ABSENT)
            if route.get("resolves_to") is not None and route["resolves_to"] not in page_text(
                relative
            ):
                found.add(RESOLVES_ABSENT)
    for text in strings_of(data):
        if re.fullmatch(r"[\x20-\x7e]*", text) is None:
            found.add(NOT_ASCII)
        if len(text) > LIMIT:
            found.add(TOO_LONG)
    return found


GUARDS: dict[str, frozenset[str]] = {
    "reviewed_for_release equals the identity version": frozenset({REVIEWED}),
    "every id and family appears in the evidence file": frozenset(
        {EVIDENCE_MISSING, ID_ABSENT, FAMILY_ABSENT}
    ),
    "every route name and resolves_to appears verbatim": frozenset({NAME_ABSENT, RESOLVES_ABSENT}),
    "every route access is unknown": frozenset({ACCESS}),
    "seed text is printable ASCII within 400 characters": frozenset({NOT_ASCII, TOO_LONG}),
}


@pytest.mark.parametrize("guard", list(GUARDS))
def test_the_shipped_seed_passes_each_guard(guard: str) -> None:
    """AC-11. expected_behavior_source: AC-11 (the five guards); ADR-004 decision 4 (a unit test
    fails when `reviewed_for_release` differs from the workflow version in `identity.json`; every
    seed `id`, `family`, route `name` and `resolves_to` appears in the evidence file that the
    entry's `documented` reference cites; every seed route has `access: unknown`; seed free text
    is printable ASCII within a length); Q-8 (the catalog is rechecked on every Orqlet release).
    """
    problems = guard_problems(seed_data(), identity_version())

    assert problems & GUARDS[guard] == set()


def test_the_shipped_seed_has_no_problem_at_all() -> None:
    """AC-11. expected_behavior_source: AC-11; ADR-004 decision 4. The five guards together find
    nothing; the guards in this file are only the five of the criteria.
    """
    assert guard_problems(seed_data(), identity_version()) == set()


def test_composer_2_5_is_found_in_a_page_that_writes_composer_2_5_with_a_space() -> None:
    """AC-11. expected_behavior_source: AC-11 ("after the normalisation of ADR-005, which is how
    `composer-2.5` is found in a page that writes 'Composer 2.5'"); ADR-005 decision 1 (the
    separators `-`, `_`, `.` and the space are one separator). The page of the entry has the
    words with a space and has no `composer-2.5` as written; the same page has no Composer 2.6.
    """
    cursor_page = f"{EVIDENCE_DIR}{CURSOR_PAGE}"

    assert "composer-2.5" not in page_text(cursor_page)
    assert "Composer 2.5" in page_text(cursor_page)
    assert appears_after_normalisation("composer-2.5", cursor_page)
    assert not appears_after_normalisation("composer-2.6", cursor_page)


def test_a_spelling_that_differs_only_in_letter_case_and_separators_passes_the_id_guard() -> None:
    """AC-11. expected_behavior_source: ADR-005 decision 1 (identity: NFKC, case-folding, one
    separator for `-`, `_`, `.` and the space). The id guard is the normalised one, and the route
    guard is not (the next test).
    """
    data = seed_data()
    data["models"][-1]["id"] = "Composer_2.5"

    assert guard_problems(data, identity_version()) == set()


def edited(change: Callable[[Doc], None]) -> Doc:
    data = seed_data()
    change(data)
    return data


def set_reviewed(value: str) -> Callable[[Doc], None]:
    return lambda data: data.__setitem__("reviewed_for_release", value)


def set_model(index: int, key: str, value: object) -> Callable[[Doc], None]:
    return lambda data: data["models"][index].__setitem__(key, value)


def set_route(model: int, key: str, value: object) -> Callable[[Doc], None]:
    return lambda data: data["models"][model]["routes"][0].__setitem__(key, value)


def make_alias(data: Doc) -> None:
    """The first route of the first model becomes an alias that resolves to a name no page holds."""
    route = data["models"][0]["routes"][0]
    route["kind"] = "alias"
    route["resolves_to"] = "gpt-6-astra-snapshot-zq7"


def set_reason(value: str) -> Callable[[Doc], None]:
    return lambda data: data["excluded"][0].__setitem__("reason", value)


def point_to_a_missing_file(data: Doc) -> None:
    data["models"][0]["documented"]["evidence"] = f"{EVIDENCE_DIR}no-such-page.md"


# (case, the change of one value, the one problem that the guards must find)
BROKEN_COPIES: tuple[tuple[str, Callable[[Doc], None], str], ...] = (
    ("reviewed for the previous release", set_reviewed("0.5.0"), REVIEWED),
    # Later than the current release 0.5.1 (Q-23: 0.5.1 is the identity now, so it is no longer a
    # broken copy), and 0.5.0 is the previous release.
    ("reviewed for a later release", set_reviewed("0.5.2"), REVIEWED),
    ("a model whose id no page holds", set_model(0, "id", "gpt-6-nova"), ID_ABSENT),
    ("an id that is only the start of a longer word", set_model(3, "id", "gpt-6-lun"), ID_ABSENT),
    ("a model whose family no page holds", set_model(0, "family", "zqfamily"), FAMILY_ABSENT),
    ("an evidence file that does not exist", point_to_a_missing_file, EVIDENCE_MISSING),
    (
        "a route name that no page holds",
        set_route(0, "name", "gpt-6-astra-preview-zq7"),
        NAME_ABSENT,
    ),
    (
        "a route name that differs from the page by letter case",
        set_route(0, "name", "GPT-6-ASTRA"),
        NAME_ABSENT,
    ),
    (
        "a route name that differs from the page by a separator",
        set_route(1, "name", "gpt-6-1-sol"),
        NAME_ABSENT,
    ),
    ("an alias that resolves to a name no page holds", make_alias, RESOLVES_ABSENT),
    ("a route with access confirmed", set_route(0, "access", "confirmed"), ACCESS),
    ("a route with access blocked", set_route(4, "access", "blocked"), ACCESS),
    ("a text with a non-ASCII letter", set_reason("a reason with a caf\u00e9"), NOT_ASCII),
    ("a text with a control character", set_reason("a reason with a bell \x07"), NOT_ASCII),
    ("a text with a line break", set_reason("a reason\nwith a second line"), NOT_ASCII),
    ("a text of 401 characters", set_reason("x" * (LIMIT + 1)), TOO_LONG),
)


@pytest.mark.parametrize(
    ("change", "problem"),
    [pytest.param(c[1], c[2], id=c[0]) for c in BROKEN_COPIES],
)
def test_a_broken_copy_of_the_seed_fails_exactly_the_guard_that_it_breaks(
    change: Callable[[Doc], None], problem: str
) -> None:
    """AC-11. expected_behavior_source: AC-11 ("A guard test fails when the seed's
    `reviewed_for_release` differs ...; when a seed `id` or `family` does not appear in the
    evidence file ...; when a route `name` or `resolves_to` does not appear in that file verbatim;
    when a route has an access other than `unknown`; or when seed text is not printable ASCII
    within 400 characters"); ADR-004 decision 4. One value changed, one problem found.
    """
    assert guard_problems(edited(change), identity_version()) == {problem}


def test_a_text_of_exactly_400_printable_characters_is_allowed() -> None:
    """AC-11. expected_behavior_source: AC-11 ("within 400 characters"); the contract `PolicyText`
    (1 to 400 printable ASCII characters). The edge is allowed and 401 is not.
    """
    data = edited(set_reason("x" * LIMIT))

    assert guard_problems(data, identity_version()) == set()


def test_the_guard_for_the_release_follows_the_identity_it_is_given() -> None:
    """AC-11. expected_behavior_source: ADR-004 decision 4 ("`reviewed_for_release` ... to the new
    workflow version in the release pull request. A unit test fails when the seed's
    `reviewed_for_release` differs from that version"). A seed reviewed for 0.5.1 is a problem
    when the identity says 0.6.0.
    """
    assert guard_problems(seed_data(), "0.6.0") == {REVIEWED}


def test_each_guard_has_a_broken_copy_in_this_file() -> None:
    """AC-11. expected_behavior_source: AC-11 (each guard "must be shown to fail"). Every problem
    code of every guard is the expected problem of at least one broken copy.
    """
    shown = {case[2] for case in BROKEN_COPIES}
    wanted = {code for codes in GUARDS.values() for code in codes}

    assert shown == wanted
