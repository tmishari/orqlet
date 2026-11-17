"""`validate_model_policy`, the use case behind `orqlet validate model-policy` (task
dynamic-model-profiles, phase P-7).

Every test cites its `expected_behavior_source`. AC-1 to AC-6 are the acceptance criteria of phase
P-7 in docs/design/dynamic-model-profiles/plan.yaml. ADR-003, ADR-004 and ADR-005 and component.md
are the files under docs/design/dynamic-model-profiles/design/. R1 to R14 are the readings of the
acceptance criteria that the coder of the phase was given: R1 the states and the not-run text, R2
the base tree, R3 the grouping of field paths, R4 the forms of `approval_ref`, R5 what ORQ-E543,
ORQ-E545 and ORQ-W540 share, R6 the enabled clients, R7 ORQ-W541, R8 ORQ-W542, R9 the files of the
drift check and their expected value, R10 the exclusion in the drift check, R11 what a drift
finding prints, R12 ORQ-W544, R13 the PATH argument and R14 the order and the data of the result.

These tests were written first, by the Tester of phase P-7, before the use case existed. They run
on the fakes (`FixedClock`, `FakeVcs`, `MemoryFileSystem`, `PinnedWorkflow`) and the real strict
loader. A policy is a document built in code and written as JSON text, which is YAML. Credential
shaped text is assembled from parts at run time and never written as one literal
(ORQLET-SEC-003).

Unless a test says otherwise it validates against the explicit full commit id `BASE`: the fake
repository has one commit `HEAD`, and `BASE` is its merge base. A test of another base says so:
`HEAD`, a branch name, or the merge base through the profile's target branch.

Behaviour that the criteria and the readings leave open is deliberately not pinned here:
- the wording of any message beyond the fixed words that the readings give (`catalog id <id>`,
  `unmatched, <n> characters`, `missing-candidate`, `past`, `within 30 days`, `and N more`);
- the `path` of the findings of ORQ-E547, of ORQ-E544 and of the warnings;
- whether the command also prints ORQ-W545 and ORQ-W546 of `select_models`;
- whether an `excluded` entry of the base that was narrowed but kept its `id` is found: ORQ-E544
  compares by `id` (R2), so a test would pin a stated uncertainty;
- whether a generated file with no `model` key is a difference when `inherit` is the expected
  value (a Claude Code or Cursor role that follows no pin, or a skill that follows none);
- the letter case of the prefix of an `approval_ref` (`PR:1`) and non-ASCII digits after `pr:`;
- what a `--base` that is no accepted ref name does, and what a root that is no Git repository does;
- whether ORQ-E544 or ORQ-E546 stop ORQ-W540 and ORQ-W543 (only ORQ-E543 and ORQ-E545 do, R5);
- the exact wording of the not-run reason that says the generated files were not compared.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import socket
import time
import tomllib
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.clock import Clock
from orqlet.application.ports.documents import DocumentError
from orqlet.application.ports.filesystem import FileSystemError
from orqlet.application.ports.vcs import CommitSummary, RepoState, VcsError
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.binding_inputs import locate
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.model_policy_source import (
    PolicyInvalid,
    PolicyLoaded,
    load_model_policy,
)
from orqlet.application.usecases.model_selection import policy_problems, select_models
from orqlet.application.usecases.validate_model_policy import (
    ModelPolicyServices,
    validate_model_policy,
)
from orqlet.application.usecases.validation import (
    ValidateServices,
    ValidationResult,
    split_front_matter,
)
from orqlet.domain.errors import InvalidPath
from orqlet.domain.findings import Finding, Severity, Verdict
from orqlet.domain.model_identity import ExclusionRule, is_excluded
from orqlet.domain.paths import CanonicalPath
from tests.fakes.clock import FixedClock
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PinnedWorkflow

pytestmark = pytest.mark.unit

Doc = dict[str, Any]

POLICY = ".orqlet/model-policy.yaml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
OTHER = "docs/other-policy.yaml"
LIMIT = 256 * 1024  # a file of 262144 bytes is allowed; 262145 bytes is not
HEAD = "a" * 40
BASE = "b" * 40
TARGET = "c" * 40
NOTHING = "no model policy, nothing was checked"

E320 = "ORQ-E320"
E540 = "ORQ-E540"
E541 = "ORQ-E541"
E542 = "ORQ-E542"
E543 = "ORQ-E543"
E544 = "ORQ-E544"
E545 = "ORQ-E545"
E546 = "ORQ-E546"
E547 = "ORQ-E547"
E548 = "ORQ-E548"
W540 = "ORQ-W540"
W541 = "ORQ-W541"
W542 = "ORQ-W542"
W543 = "ORQ-W543"
W544 = "ORQ-W544"

CLAUDE = "claude-code"
CODEX = "codex"
CURSOR = "cursor"
CLIENTS = (CLAUDE, CODEX, CURSOR)
PROFILE_IDS = ("quality", "engineering", "economy")
# Item 4 of the interface: the roles and the skills of the packaged workflow.
ROLES = (
    "orqlet-arch-reviewer",
    "orqlet-inventory",
    "orqlet-security-reviewer",
    "orqlet-tester",
    "orqlet-tracer",
)
SKILLS = (
    "orqlet-design",
    "orqlet-implement",
    "orqlet-onboard",
    "orqlet-plan",
    "orqlet-research",
    "orqlet-review",
)
TESTER = "orqlet-tester"
DESIGN = "orqlet-design"

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
TODAY = NOW.date()
WORKFLOW = PinnedWorkflow(PackagedWorkflow(), version="0.4.0")
LOADER = StrictYamlLoader()
PROFILE_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "contracts"
    / "valid"
    / "orqlet.project-profile.v1.yaml"
)

ABSENT: Any = object()  # a file with no `model` key
FROM_STATE: Any = object()  # the approval field that fits the state of the entry


# --- fakes that watch what the command does ---------------------------------------------------


class Files(MemoryFileSystem):
    """The memory file system, which can refuse every write, fail a read and count what is read."""

    def __init__(self) -> None:
        super().__init__()
        self.sealed = False
        self.denied: dict[str, Exception] = {}
        self.reads: list[str] = []
        self.listed: list[str] = []

    def _refuse_when_sealed(self) -> None:
        if self.sealed:
            raise AssertionError("a validator never writes")

    def read_bytes(self, path: CanonicalPath) -> bytes:
        self.reads.append(str(path))
        if str(path) in self.denied:
            raise self.denied[str(path)]
        return super().read_bytes(path)

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        self.listed.append("" if path is None else str(path))
        return super().list_dir(path)

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:
        self._refuse_when_sealed()
        super().write_atomic(path, data)

    def delete(self, path: CanonicalPath) -> None:
        self._refuse_when_sealed()
        super().delete(path)

    def make_dir(self, path: CanonicalPath) -> None:
        self._refuse_when_sealed()
        super().make_dir(path)

    def remove_empty_dir(self, path: CanonicalPath) -> None:
        self._refuse_when_sealed()
        super().remove_empty_dir(path)


class WatchedVcs(FakeVcs):
    """A fake repository whose only write, `init_repository`, fails the test."""

    def init_repository(self, branch: str) -> None:
        raise AssertionError("a validator never writes to the repository")


class RaisingClock:
    """Proves that the clock is not read: any reading fails the test."""

    def now(self) -> datetime:
        raise AssertionError("the clock is read only when a route has a retirement date")


class CountingClock(FixedClock):
    def __init__(self, start: datetime | None = None) -> None:
        super().__init__(start)
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return super().now()


@dataclass(frozen=True, slots=True)
class Reader:
    """The three ports that `load_model_policy` needs, to ask the loader what it reports."""

    project: Files
    vcs: WatchedVcs
    loader: StrictYamlLoader


# --- policies built in code -------------------------------------------------------------------


def route(
    client: str,
    name: str | None,
    *,
    kind: str = "id",
    resolves_to: str | None = None,
    also_known_as: Sequence[str] = (),
    access: str = "unknown",
    retires_on: str | None = None,
) -> Doc:
    return {
        "client": client,
        "kind": kind,
        "name": name,
        "resolves_to": resolves_to,
        "also_known_as": list(also_known_as),
        "access": access,
        "retires_on": retires_on,
    }


def entry(
    model_id: str,
    *routes: Doc,
    family: str = "example-family",
    state: str = "approved",
    approved_by: Any = FROM_STATE,
    approval_ref: Any = FROM_STATE,
) -> Doc:
    """An entry of the catalog; an approved one carries an approver and `pr:42` unless told."""
    granted = state == "approved"
    by = ("example-approver" if granted else None) if approved_by is FROM_STATE else approved_by
    ref = ("pr:42" if granted else None) if approval_ref is FROM_STATE else approval_ref
    return {
        "id": model_id,
        "family": family,
        "approval": {"state": state, "approved_by": by, "approval_ref": ref},
        "documented": {"evidence": "docs/example/evidence/entry.md", "date": "2026-10-30"},
        "callable": "not-run",
        "evaluated": {"state": "none"},
        "routes": list(routes),
    }


def routes_of(prefix: str, clients: Sequence[str] = CLIENTS) -> list[Doc]:
    """One id route for each client, named `<prefix>-<client>`."""
    return [route(client, f"{prefix}-{client}") for client in clients]


def exclusion(
    rule_id: str,
    *,
    aliases: Sequence[str] = (),
    id_patterns: Sequence[str] = (),
    family_tags: Sequence[str] = (),
    reason: str = "Example reason.",
    source: str = "Example notice.",
) -> Doc:
    return {
        "id": rule_id,
        "reason": reason,
        "source": source,
        "aliases": list(aliases),
        "id_patterns": list(id_patterns),
        "family_tags": list(family_tags),
    }


def profile_doc(
    profile_id: str,
    *,
    mode: str = "manual",
    candidates: Sequence[str] = (),
    fallbacks: Sequence[str] = (),
    clients: Sequence[str] = CLIENTS,
    escalation: str | None = None,
) -> Doc:
    """A profile whose candidates and fallbacks are the same ordered ids for each client given."""
    return {
        "id": profile_id,
        "capability": "Example capability.",
        "mode": mode,
        "candidates": [{"client": c, "models": list(candidates)} for c in clients if candidates],
        "fallbacks": [{"client": c, "models": list(fallbacks)} for c in clients if fallbacks],
        "escalation": escalation,
    }


def assignment_doc(
    kind: str,
    name: str,
    *,
    profile: str | None = None,
    model: str | None = None,
    mode: str = "manual",
    client: str | None = None,
) -> Doc:
    return {
        "target": {"kind": kind, "name": name},
        "task": None,
        "client": client,
        "profile": profile,
        "model": model,
        "mode": mode,
        "effort": None,
    }


def policy_doc(
    models: Sequence[Doc],
    assignments: Sequence[Doc] = (),
    *,
    profiles: Sequence[Doc] = (),
    excluded: Sequence[Doc] = (),
    reviewed: str = "0.4.0",
) -> Doc:
    return {
        "schema": "orqlet.model-policy/v2",
        "policy_version": 1,
        "reviewed_for_release": reviewed,
        "models": list(models),
        "excluded": list(excluded),
        "profiles": list(profiles),
        "assignments": list(assignments),
    }


# Two approved models with an id route for each client: `example-a-claude-code` and so on.
MODEL_A = entry("example-a", *routes_of("example-a"))
MODEL_B = entry("example-b", *routes_of("example-b"))
# The exclusion that most tests use: an alias, an id pattern and a family tag.
BLOCKED = exclusion(
    "blocked-example",
    aliases=["blocked-alias"],
    id_patterns=["blocked-model-*"],
    family_tags=["blocked-family"],
)


def plain_policy(*, reviewed: str = "0.4.0", **changes: Any) -> Doc:
    """A sound policy that pins nothing: two approved models and one exclusion."""
    return {**policy_doc([MODEL_A, MODEL_B], excluded=[BLOCKED], reviewed=reviewed), **changes}


def pinned_policy() -> Doc:
    """A sound policy that pins the tester role for every client and the design skill for Claude."""
    return policy_doc(
        [MODEL_A, MODEL_B],
        [
            assignment_doc("role", TESTER, model="example-a"),
            assignment_doc("skill", DESIGN, model="example-a", client=CLAUDE),
        ],
        excluded=[BLOCKED],
    )


def raw_of(doc: Doc) -> bytes:
    return json.dumps(doc, indent=2).encode()


def compact(doc: Doc) -> bytes:
    """The smallest JSON text of `doc` that still has short lines.

    One line for the whole document would be refused by the reader of the policy (the `oversize`
    rule of its credential scan), which is not what the worst-case tests probe.
    """
    return json.dumps(doc, indent=0, separators=(",", ":")).encode()


def pad(content: bytes, size: int) -> bytes:
    """`content` and comment lines of at most 80 bytes, so that the file has exactly `size` bytes.

    The lines are short because the reader of the policy refuses a single line of thousands of
    characters (the `oversize` rule of its credential scan), which is not what these tests probe.
    """
    assert size >= len(content), "the content is longer than the size asked for"
    padded = bytearray(content)
    while len(padded) < size:
        width = min(80, size - len(padded))
        padded += b"\n" + b"#" + b"x" * (width - 2) if width >= 2 else b"\n"
    assert len(padded) == size
    return bytes(padded)


# --- the lock, the profile, the project and the repository -----------------------------------

SEEDED = {"path": POLICY, "owner": "seeded", "seeded_sha256": "0" * 64}
OTHER_SEEDED = {"path": ".orqlet/role-bindings.yaml", "owner": "seeded", "seeded_sha256": "1" * 64}


def generated(path: str) -> Doc:
    return {"path": path, "owner": "orqlet", "class": "protected", "rendered_sha256": "2" * 64}


def team_row(path: str) -> Doc:
    return {"path": path, "owner": "user", "rendered_sha256": "3" * 64}


def lock_bytes(*rows: Doc) -> bytes:
    data = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": "0.4.0"},
        "files": list(rows),
    }
    return json.dumps(data, indent=2).encode()


def profile_bytes(enabled: Sequence[str] = CLIENTS) -> bytes:
    """The valid profile fixture with these clients enabled; its target branch is `origin/main`."""
    data = LOADER.load(PROFILE_FIXTURE.read_bytes(), source=str(PROFILE_FIXTURE))
    assert isinstance(data, dict)
    data["clients"]["enabled"] = list(enabled)
    return json.dumps(data, indent=2, default=str).encode()


def put(tree: MemoryFileSystem, path: str, content: bytes | str | Doc) -> None:
    if isinstance(content, dict):
        data = raw_of(content)
    elif isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content
    tree.write_atomic(CanonicalPath.parse(path), data)


def project(
    policy: Doc | bytes | None = None,
    *,
    lock: Sequence[Doc] | bytes | None = None,
    files: Mapping[str, bytes | str] | None = None,
    enabled: Sequence[str] | None = None,
) -> Files:
    """A project with the policy, the lock rows, the profile (when `enabled` is given) and files."""
    tree = Files()
    if policy is not None:
        if isinstance(policy, dict):
            ModelPolicy.model_validate(policy)  # a document built in code is always a valid one
        put(tree, POLICY, policy)
    if lock is not None:
        put(tree, LOCK, lock if isinstance(lock, bytes) else lock_bytes(*lock))
    if enabled is not None:
        put(tree, PROFILE, profile_bytes(enabled))
    for path, content in (files or {}).items():
        put(tree, path, content)
    return tree


def vcs_of(at_base: Mapping[str, bytes] | None = None) -> WatchedVcs:
    """One commit `HEAD`, whose merge base with the explicit base `BASE` is `BASE`."""
    return WatchedVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEAD, "head"),),
        revisions={BASE: dict(at_base or {})},
        merge_bases={(HEAD, BASE): (BASE,)},
    )


def vcs_of_head(at_head: Mapping[str, bytes] | None = None) -> WatchedVcs:
    """The same repository for the base `HEAD`: the merge base of HEAD with itself is HEAD."""
    return WatchedVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEAD, "head"),),
        revisions={HEAD: dict(at_head or {})},
        merge_bases={(HEAD, "HEAD"): (HEAD,)},
    )


def vcs_of_target(
    at_base: Mapping[str, bytes] | None = None, *, ref: str = "origin/main"
) -> WatchedVcs:
    """The merge base through the profile's target branch: `ref` names TARGET, the base is BASE."""
    return WatchedVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEAD, "head"),),
        revisions={BASE: dict(at_base or {}), TARGET: {}},
        merge_bases={(HEAD, TARGET): (BASE,)},
        refs={ref: TARGET},
    )


def run(
    tree: MemoryFileSystem,
    *,
    base: str | None = BASE,
    vcs: FakeVcs | None = None,
    at_base: Mapping[str, bytes] | None = None,
    clock: Clock | None = None,
    workflow: WorkflowSource = WORKFLOW,
    path: str = POLICY,
) -> ValidationResult:
    services = ModelPolicyServices(
        project=tree,
        vcs=vcs if vcs is not None else vcs_of(at_base),
        loader=LOADER,
        workflow=workflow,
        clock=clock if clock is not None else FixedClock(),
    )
    return validate_model_policy(services, path, base)


# --- reading a result ---------------------------------------------------------------------------

PATH_TOKEN = re.compile(
    r"\b(?:models|excluded|profiles|assignments)\[\d+\](?:\.[a-z_]+(?:\[\d+\])*)*"
)
MORE_TOKEN = re.compile(r"\band (\d+) more\b")


def codes(result: ValidationResult) -> list[str]:
    return [finding.code for finding in result.findings]


def by_code(result: ValidationResult, code: str) -> list[Finding]:
    return [finding for finding in result.findings if finding.code == code]


def only(result: ValidationResult, code: str) -> Finding:
    found = by_code(result, code)
    assert len(found) == 1, f"{code} x{len(found)} in {codes(result)}"
    return found[0]


def paths_in(finding: Finding) -> list[str]:
    """The field paths that a finding lists: `models[1].routes[0]`, `excluded[2]` and so on."""
    return PATH_TOKEN.findall(finding.message)


def more_in(finding: Finding) -> int | None:
    found = MORE_TOKEN.search(finding.message)
    return int(found[1]) if found else None


def names(finding: Finding, text: str) -> bool:
    """True when the finding names `text` in its path field or in its message."""
    return text in (finding.path or "") or text in finding.message


def shown(result: ValidationResult) -> str:
    """Everything that a result shows: every finding, the reasons not run and the data."""
    rows = [[f.code, f.severity.value, f.message, f.path, repr(f)] for f in result.findings]
    document = {"findings": rows, "not_run": list(result.not_run), "data": result.data}
    return json.dumps(document, ensure_ascii=False, sort_keys=True)


def leaked(text: str, secret: str, width: int = 8) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def marker(label: str) -> str:
    """A unique, valid model string for one field: the same value on every run."""
    return "zq7mk-" + hashlib.sha256(label.encode()).hexdigest()[:12]


def loader_findings(tree: Files) -> tuple[Finding, ...]:
    """What the loader of the default path reports for this project (an invalid state)."""
    state = load_model_policy(Reader(tree, vcs_of(), LOADER))
    assert isinstance(state, PolicyInvalid), state
    return state.findings


# --- files of the drift check -----------------------------------------------------------------


@dataclass(frozen=True)
class Kind:
    """One of the five kinds of file whose `model` value the drift check reads."""

    label: str
    folder: str
    template: str
    suffix: str
    client: str | None
    toml: bool
    skill: bool
    name: str

    def path(self, name: str | None = None) -> str:
        return self.template.format(name or self.name)

    def entry(self, name: str) -> str:
        """The name of the folder entry for `name`: a file name, or a skill folder."""
        return name + self.suffix

    def file(self, model: Any = ABSENT, *, raw: str | None = None) -> bytes:
        """A valid file; `model` is a text value and `raw` is the literal, as it is written."""
        if raw is None and model is not ABSENT:
            raw = json.dumps(model, ensure_ascii=False)
        if self.toml:
            lines = ['name = "example"', 'description = "An example role."']
            if raw is not None:
                lines.append(f"model = {raw}")
            lines.append('developer_instructions = "Do the work."')
        else:
            lines = ["---", "name: example", "description: An example."]
            if raw is not None:
                lines.append(f"model: {raw}")
            lines += ["---", "", "Do the work."]
        return ("\n".join(lines) + "\n").encode("utf-8")

    def duplicated(self, first: str, second: str) -> bytes:
        """Two `model` keys in one document: refused by the strict reading rules."""
        if self.toml:
            return f"model = {json.dumps(first)}\nmodel = {json.dumps(second)}\n".encode()
        text = f"---\nname: example\nmodel: {json.dumps(first)}\nmodel: {json.dumps(second)}\n---\n"
        return (text + "\nDo the work.\n").encode()

    def not_utf8(self) -> bytes:
        if self.toml:
            return b'model = "\xff"\n'
        return b"---\nname: example\nmodel: \xff\n---\n\nDo the work.\n"

    @property
    def not_text(self) -> tuple[str, ...]:
        """Literals of a `model` that is present and is not text."""
        if self.toml:
            return ("5", '["a", "b"]', '{ a = "b" }', "true")
        return ("5", "[a, b]", "{a: b}", "true")

    @property
    def inherits(self) -> bool:
        """True for the kinds whose generated file says `inherit` when no model is pinned."""
        return self.client in {CLAUDE, CURSOR} and not self.skill

    def unpinned(self) -> bytes:
        """The file that Orqlet writes when the policy pins nothing for this kind."""
        return self.file("inherit") if self.inherits else self.file()


KINDS = (
    Kind(
        "claude-agent",
        ".claude/agents",
        ".claude/agents/{}.md",
        ".md",
        CLAUDE,
        False,
        False,
        TESTER,
    ),
    Kind(
        "cursor-agent",
        ".cursor/agents",
        ".cursor/agents/{}.md",
        ".md",
        CURSOR,
        False,
        False,
        TESTER,
    ),
    Kind(
        "codex-agent", ".codex/agents", ".codex/agents/{}.toml", ".toml", CODEX, True, False, TESTER
    ),
    Kind(
        "claude-skill",
        ".claude/skills",
        ".claude/skills/{}/SKILL.md",
        "",
        CLAUDE,
        False,
        True,
        DESIGN,
    ),
    Kind(
        "agents-skill",
        ".agents/skills",
        ".agents/skills/{}/SKILL.md",
        "",
        None,
        False,
        True,
        DESIGN,
    ),
)
EVERY_KIND = pytest.mark.parametrize("kind", KINDS, ids=lambda kind: kind.label)
EXCLUDED_VALUES = {
    "alias": "blocked-alias",
    "alias-case-and-separators": "Blocked_Alias",
    "id-pattern": "blocked-model-9",
    "family-tag": "vendor-blocked-family-2",
    "bracketed": "blocked-alias[effort=high]",
}
OTHER_VALUE = "example-other-model"


def drift(
    kind: Kind,
    content: bytes,
    *,
    is_generated: bool = False,
    policy: Doc | None = None,
    enabled: Sequence[str] | None = None,
    name: str | None = None,
) -> ValidationResult:
    """The result for one agent or skill file, generated (a lock row) or team-authored."""
    path = kind.path(name)
    lock = [generated(path)] if is_generated else None
    tree = project(policy if policy is not None else plain_policy(), lock=lock, enabled=enabled)
    put(tree, path, content)
    return run(tree)


def model_of(kind: Kind, content: bytes) -> object:
    """The `model` value of a file as the readings define it: the top-level key, or nothing."""
    text = content.decode("utf-8")
    if kind.toml:
        return tomllib.loads(text).get("model")
    split = split_front_matter(text)
    assert split is not None
    data = LOADER.load(split[0].encode("utf-8"), source="front matter")
    assert isinstance(data, dict)
    return data.get("model")


# --- scenarios that several groups reuse ------------------------------------------------------

Scenario = tuple[Files, dict[str, Any]]


def sound() -> Scenario:
    return project(plain_policy()), {}


def never_present() -> Scenario:
    return project(), {}


def unlocated_base() -> Scenario:
    return project(plain_policy()), {"vcs": WatchedVcs(RepoState.UNBORN_EMPTY)}


def invalid_file() -> Scenario:
    return project(b"a: 1\na: 2\n"), {}


def deleted_by_lock() -> Scenario:
    return project(lock=[SEEDED]), {}


def deleted_by_base() -> Scenario:
    return project(), {"at_base": {POLICY: raw_of(plain_policy())}}


def everything_wrong() -> Scenario:
    """One finding of each class, in a scenario with problems: no ORQ-W540 and no ORQ-W543."""
    removed = exclusion("gone-rule", aliases=["gone-alias"])
    at_base = {POLICY: raw_of(plain_policy(excluded=[BLOCKED, removed]))}
    doc = policy_doc(
        [
            MODEL_A,
            entry("blocked-model-1"),  # ORQ-E543
            entry("example-c", *routes_of("example-c"), approved_by=None),  # ORQ-E546
            entry("example-d", route(CLAUDE, "example-d-claude-code", retires_on="2026-10-01")),
        ],
        [assignment_doc("role", "no-such-role", model="example-a")],  # ORQ-E545
        excluded=[BLOCKED],  # `gone-rule` is missing: ORQ-E544
        reviewed="0.3.0",  # ORQ-W541
    )
    files = {
        KINDS[0].path("team"): KINDS[0].file("blocked-alias"),  # ORQ-E548
        KINDS[1].path("gen"): KINDS[1].file(OTHER_VALUE),  # generated, but no ORQ-W543
        KINDS[2].path("odd"): KINDS[2].file(raw="[unclosed"),  # ORQ-W544
    }
    tree = project(doc, lock=[generated(KINDS[1].path("gen"))], files=files)
    return tree, {"at_base": at_base}


def warnings_only() -> Scenario:
    """A sound policy with warnings of every kind, and two errors of the drift check kind."""
    doc = policy_doc(
        [
            MODEL_A,
            MODEL_B,
            entry("example-c", route(CLAUDE, "example-c-claude-code", retires_on="2026-10-25")),
        ],
        profiles=[profile_doc("quality", candidates=["example-a"], clients=(CLAUDE,))],
        excluded=[BLOCKED],
        reviewed="0.3.0",
    )
    files = {
        KINDS[0].path("team"): KINDS[0].file("blocked-alias"),  # ORQ-E548
        KINDS[1].path("gen"): KINDS[1].file(OTHER_VALUE),  # ORQ-W543
        KINDS[2].path("odd"): KINDS[2].file(raw="[unclosed"),  # ORQ-W544
    }
    tree = project(doc, lock=[generated(KINDS[1].path("gen"))], files=files)
    return tree, {}


def unusable_path() -> Scenario:
    return project(plain_policy()), {"path": "../outside.yaml"}


SCENARIOS: dict[str, Callable[[], Scenario]] = {
    "sound": sound,
    "never-present": never_present,
    "unlocated-base": unlocated_base,
    "invalid-file": invalid_file,
    "deleted-by-lock": deleted_by_lock,
    "deleted-by-base": deleted_by_base,
    "everything-wrong": everything_wrong,
    "warnings-only": warnings_only,
    "unusable-path": unusable_path,
}
EVERY_SCENARIO = pytest.mark.parametrize("name", list(SCENARIOS))


def play(scenario: Scenario) -> ValidationResult:
    tree, options = scenario
    return run(tree, **options)


# --- premises: the data of these tests is what the tests say it is -------------------------------


def test_the_premise_the_policies_of_the_tests_are_valid_and_pin_what_the_tests_expect() -> None:
    """Not a behaviour of the command: the builders write the contract, and the oracle agrees.

    expected_behavior_source: the contract (src/orqlet/application/contracts/model_policy.py) and
    `select_models`, which the drift expectations of R9 are computed with.
    """
    for doc in (plain_policy(), pinned_policy()):
        policy = ModelPolicy.model_validate(doc)
        assert policy_problems(policy, ROLES, SKILLS) == ()
    selection = select_models(ModelPolicy.model_validate(pinned_policy()), ROLES, SKILLS, CLIENTS)
    assert selection.findings == ()
    assert selection.missing == ()
    assert {c: setting.name for c, setting in selection.roles[TESTER].items()} == {
        c: f"example-a-{c}" for c in CLIENTS
    }
    assert {c: setting.name for c, setting in selection.skills[DESIGN].items()} == {
        CLAUDE: "example-a-claude-code"
    }


def test_the_premise_the_fake_repository_locates_the_bases_the_way_validate_review_does() -> None:
    """Not a behaviour of the command: `locate` finds the merge base of each fake repository.

    expected_behavior_source: R2 (`binding_inputs.locate(ValidateServices(...), base, "HEAD")`).
    """

    def merge_base(vcs: FakeVcs, base: str | None, *, enabled: bool = False) -> str | None:
        tree = project(plain_policy(), enabled=CLIENTS if enabled else None)
        located = locate(ValidateServices(tree, vcs, LOADER, WORKFLOW), base, "HEAD")
        return None if located.target is None else located.target.base

    assert merge_base(vcs_of(), BASE) == BASE
    assert merge_base(vcs_of_head(), "HEAD") == HEAD
    assert merge_base(vcs_of_target(), None, enabled=True) == BASE
    assert merge_base(vcs_of_target(ref="main"), None, enabled=True) == BASE
    assert merge_base(vcs_of_target(ref="release/1"), "release/1") == BASE
    assert merge_base(vcs_of(), None) is None
    assert merge_base(vcs_of_target(ref="trunk"), None, enabled=True) is None
    assert merge_base(WatchedVcs(RepoState.UNBORN_EMPTY), BASE) is None


def test_the_premise_the_lock_rows_and_the_profile_are_valid_contracts() -> None:
    """Not a behaviour of the command: the rows and the profile are read by their contracts.

    expected_behavior_source: the contracts `GeneratedLock` and `ProjectProfile`, which R1, R6
    and R9 read through the loader.
    """
    rows = [SEEDED, OTHER_SEEDED, generated(KINDS[0].path()), team_row(KINDS[0].path())]
    lock = load_contract(LOADER, GeneratedLock, lock_bytes(*rows), source=LOCK)
    assert [row.owner.value for row in lock.files] == ["seeded", "seeded", "orqlet", "user"]
    for enabled in (CLIENTS, (CODEX,), (CLAUDE, CURSOR)):
        profile = load_contract(LOADER, ProjectProfile, profile_bytes(enabled), source=PROFILE)
        assert profile.clients.enabled == tuple(enabled)


@EVERY_KIND
def test_the_premise_the_files_of_every_kind_hold_the_model_the_tests_say(kind: Kind) -> None:
    """Not a behaviour of the command: the helper writes files that parse, and bad ones that do not.

    expected_behavior_source: R9 (the top-level `model` key of the front matter or the table) and
    R12 (the causes of ORQ-W544).
    """
    assert model_of(kind, kind.file("inherit")) == "inherit"
    assert model_of(kind, kind.file("blocked-alias[effort=high]")) == "blocked-alias[effort=high]"
    assert model_of(kind, kind.file()) is None
    assert model_of(kind, kind.file(raw=kind.not_text[0])) == 5
    for literal in kind.not_text:
        assert not isinstance(model_of(kind, kind.file(raw=literal)), str)
    refusals = (DocumentError, tomllib.TOMLDecodeError)  # the strict loader, and TOML
    with pytest.raises(refusals):
        model_of(kind, kind.file(raw="[unclosed"))
    with pytest.raises(refusals):
        model_of(kind, kind.duplicated("blocked-alias", "other"))
    with pytest.raises(UnicodeDecodeError):
        kind.not_utf8().decode("utf-8")


def test_the_premise_the_forms_of_approval_ref_split_as_the_contract_and_r4_say() -> None:
    """Not a behaviour of the command: every form is a valid `PolicyText`, so E546 is not E541.

    expected_behavior_source: R4 and the contract (`approval_ref` is a `PolicyText`).
    """
    for ref in (*ALLOWED_REFS, *REFUSED_REFS):
        doc = policy_doc([entry("example-a", *routes_of("example-a"), approval_ref=ref)])
        ModelPolicy.model_validate(doc)
    for ref in ALLOWED_REFS:
        if ref.startswith("adr:"):
            CanonicalPath.parse(ref.removeprefix("adr:"))
    for ref in REFUSED_REFS:
        if ref.startswith("adr:"):
            with pytest.raises(InvalidPath):
                CanonicalPath.parse(ref.removeprefix("adr:"))


def test_the_premise_a_marker_is_a_valid_model_string_that_is_unique_for_each_field() -> None:
    """Not a behaviour of the command: markers fit `ModelRef` and differ from one another.

    expected_behavior_source: AC-5 ("a unique marker placed in each model field").
    """
    labels = ("route-name", "resolves-to", "alias", "pattern", "tag", "candidate", "fallback")
    values = [marker(label) for label in labels]
    assert len(set(values)) == len(values)
    assert all(re.fullmatch(r"[A-Za-z0-9._:/@+-]{1,128}", value) for value in values)
    assert not any(leaked(a, b) for a in values for b in values if a != b)


def loaded_policy(tree: Files) -> ModelPolicy:
    """The policy that the loader reads from the working tree: the oracle of the premises."""
    state = load_model_policy(Reader(tree, vcs_of(), LOADER))
    assert isinstance(state, PolicyLoaded), state
    return state.policy


def test_the_premise_the_policies_of_the_scenarios_load_and_have_the_problems_they_name() -> None:
    """Not a behaviour of the command: the scenarios that the order tests reuse hold what their
    comments say.

    expected_behavior_source: R5 (`policy_problems`) and R14 (the scenarios of the order tests).
    """
    cases: list[tuple[Callable[[], Scenario], set[str]]] = [
        (sound, set()),
        (warnings_only, set()),
        (everything_wrong, {E543, E545}),
    ]
    for build, expected in cases:
        policy = loaded_policy(build()[0])
        found = {problem.code for problem in policy_problems(policy, ROLES, SKILLS)}
        assert found == expected, build.__name__
    selection = select_models(loaded_policy(warnings_only()[0]), ROLES, SKILLS, CLIENTS)
    assert len(selection.missing) == 2


def test_the_premise_the_spellings_of_an_excluded_value_are_excluded_and_others_are_not() -> None:
    """Not a behaviour of the command: the values that the drift tests call excluded are, and the
    values that they call different are not, by the one rule of `is_excluded`.

    expected_behavior_source: R10 (`is_excluded` of `orqlet.domain.model_identity`).
    """
    policy = ModelPolicy.model_validate(plain_policy())
    rules = [ExclusionRule(e.aliases, e.id_patterns, e.family_tags) for e in policy.excluded]
    fullwidth = "".join(chr(ord(c) + 0xFEE0) if "a" <= c <= "z" else c for c in "blocked-alias")

    for value in (*EXCLUDED_VALUES.values(), fullwidth):
        assert is_excluded(value, rules), value
    for value in (OTHER_VALUE, "blocked-alias-2", "example-a-claude-code", marker("other")):
        assert not is_excluded(value, rules), value


@pytest.mark.parametrize("name", ["no-commit", "unknown-commit-id", "unknown-branch"])
def test_the_premise_a_base_that_names_no_commit_is_not_located(name: str) -> None:
    """Not a behaviour of the command: `locate` gives a reason for each of these fake repositories.

    expected_behavior_source: R2 (`binding_inputs.locate`).
    """
    base, make_vcs, with_profile = UNLOCATED[name]
    tree = project(plain_policy(), enabled=CLIENTS if with_profile else None)

    located = locate(ValidateServices(tree, make_vcs(), LOADER, WORKFLOW), base, "HEAD")

    assert located.target is None
    assert located.problems


@pytest.mark.parametrize(
    "name",
    ["no-target-branch-known", "no-profile", "no-common-history", "several-merge-bases"],
)
def test_the_premise_a_missing_target_or_merge_base_is_not_located(name: str) -> None:
    """Not a behaviour of the command: `locate` gives a reason for each of these fake repositories.

    expected_behavior_source: R2 (`binding_inputs.locate`).
    """
    base, make_vcs, with_profile = UNLOCATED[name]
    tree = project(plain_policy(), enabled=CLIENTS if with_profile else None)

    located = locate(ValidateServices(tree, make_vcs(), LOADER, WORKFLOW), base, "HEAD")

    assert located.target is None
    assert located.problems


# --- AC-6: the services, the registered command, and a read-only command on fakes ----------------


def test_the_set_of_implemented_commands_lists_validate_model_policy() -> None:
    """AC-6. expected_behavior_source: AC-6 ("`IMPLEMENTED_COMMANDS` lists `validate
    model-policy`"); interface item 3."""
    assert "validate model-policy" in IMPLEMENTED_COMMANDS


def assign(target: object, name: str, value: object) -> None:
    """An assignment that the type checker does not see, to try a frozen object."""
    setattr(target, name, value)


def test_the_services_are_a_frozen_slotted_dataclass_of_the_five_ports_in_order() -> None:
    """AC-6. expected_behavior_source: AC-6 ("a services object that adds the Clock port to the
    ports of the other validators"); interface item 1 (the fields, in this order, all required)."""
    fields = dataclasses.fields(ModelPolicyServices)

    assert [f.name for f in fields] == ["project", "vcs", "loader", "workflow", "clock"]
    assert all(
        f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
        for f in fields
    )
    assert "__slots__" in vars(ModelPolicyServices)
    services = ModelPolicyServices(project(), vcs_of(), LOADER, WORKFLOW, FixedClock())
    with pytest.raises(dataclasses.FrozenInstanceError):
        assign(services, "clock", FixedClock())


def test_the_services_hold_the_ports_of_the_other_validators_and_the_clock() -> None:
    """AC-6. expected_behavior_source: AC-6 ("adds the Clock port to the ports of the other
    validators"); `ValidateServices` is the services object of the other validators."""
    others = {f.name for f in dataclasses.fields(ValidateServices)}
    ours = {f.name for f in dataclasses.fields(ModelPolicyServices)}

    assert ours == others | {"clock"}


def test_a_run_on_the_fakes_opens_no_socket() -> None:
    """AC-6. expected_behavior_source: AC-6 ("the unit tests ... open no socket"); pyproject.toml
    addopts `--disable-socket`: a socket opened by the command would fail the test."""
    # With `filterwarnings = error` the blocked-socket warning is what is raised.
    with pytest.raises((RuntimeError, UserWarning), match="socket"):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    assert run(project(plain_policy())).verdict is Verdict.PASS


@EVERY_SCENARIO
def test_the_command_never_writes_to_the_project_or_to_the_repository(name: str) -> None:
    """AC-1/AC-6. expected_behavior_source: interface item 1 ("It never writes"); AC-1 (read-only);
    plan P-7 objective ("reads files and git trees and starts no process of its own")."""
    tree, options = SCENARIOS[name]()
    before = tree.snapshot()
    tree.sealed = True

    play((tree, options))

    assert tree.snapshot() == before


@EVERY_SCENARIO
def test_the_result_is_deterministic(name: str) -> None:
    """R14. expected_behavior_source: R14 ("The result is deterministic: two calls give equal
    results")."""
    first = play(SCENARIOS[name]())
    second = play(SCENARIOS[name]())

    assert first == second


@EVERY_SCENARIO
def test_every_error_finding_is_an_e_code_and_every_warning_a_w_code(name: str) -> None:
    """AC-2/AC-3. expected_behavior_source: AC-2 ("FAIL findings: ORQ-E54x"); AC-3 ("Warnings,
    which do not change PASS: ORQ-W54x")."""
    result = play(SCENARIOS[name]())

    for finding in result.findings:
        expected = Severity.ERROR if finding.code.startswith("ORQ-E") else Severity.WARNING
        assert finding.severity is expected, finding
    assert (result.verdict is Verdict.FAIL) == bool(result.errors)


@EVERY_SCENARIO
def test_the_data_holds_only_counts_closed_words_and_clients(name: str) -> None:
    """R14/AC-5. expected_behavior_source: R14 ("`result.data` holds only counts, closed words and
    the clients; never a string from any file")."""
    result = play(SCENARIOS[name]())

    def leaves(node: object) -> list[object]:
        if isinstance(node, Mapping):
            return [leaf for value in node.values() for leaf in leaves(value)]
        if isinstance(node, list | tuple):
            return [leaf for value in node for leaf in leaves(value)]
        return [node]

    json.dumps(result.data)  # a plain value: the envelope prints it
    for leaf in leaves(result.data):
        assert leaf is None or isinstance(leaf, int | str), leaf
        if isinstance(leaf, str):
            assert re.fullmatch(r"[a-z][a-z0-9-]{0,39}", leaf), leaf


# --- AC-1: PASS, FAIL and NOT_RUN ------------------------------------------------------------


def test_a_sound_policy_with_a_located_base_passes_with_nothing_to_report() -> None:
    """AC-1. expected_behavior_source: AC-1 (exit 0 on PASS); the Collector rule (a PASS needs a
    located base). Base: the explicit id BASE, whose tree holds no policy."""
    result = run(project(plain_policy()))

    assert result.verdict is Verdict.PASS
    assert result.not_run == ()
    assert [f for f in result.findings if f.severity is not Severity.INFO] == []


@pytest.mark.parametrize(
    "variant",
    ["no-file", "other-seeded-row", "row-of-the-policy-owned-by-the-team", "invalid-lock"],
)
def test_a_policy_that_was_never_present_is_not_run_with_the_reason(variant: str) -> None:
    """AC-1/R1. expected_behavior_source: AC-1 ("no file, no seeded row in the lock, not in the
    base tree ... is NOT_RUN with the reason ..."); R1. Base: the explicit id BASE (no policy)."""
    locks: dict[str, Sequence[Doc] | bytes | None] = {
        "no-file": None,
        "other-seeded-row": [OTHER_SEEDED],
        "row-of-the-policy-owned-by-the-team": [team_row(POLICY)],
        "invalid-lock": b"files: not-a-list\n",
    }

    result = run(project(lock=locks[variant]))

    assert result.verdict is Verdict.NOT_RUN
    assert NOTHING in result.not_run
    assert result.findings == ()


def test_a_policy_that_was_never_present_and_a_base_that_is_not_located_list_both_reasons() -> None:
    """R1. expected_behavior_source: R1 ("when no base tree could be located, the reasons of that
    are listed too"). Base: the explicit id BASE in a repository with no commit."""
    result = run(project(), vcs=WatchedVcs(RepoState.UNBORN_EMPTY))

    assert result.verdict is Verdict.NOT_RUN
    assert NOTHING in result.not_run
    assert len(result.not_run) >= 2


@pytest.mark.parametrize("variant", ["no-file", "base-is-not-located", "custom-path"])
def test_a_policy_that_was_never_present_never_passes(variant: str) -> None:
    """AC-1/R1. expected_behavior_source: R1 ("A never-present policy never gives PASS")."""
    options: dict[str, dict[str, Any]] = {
        "no-file": {},
        "base-is-not-located": {"vcs": WatchedVcs(RepoState.UNBORN_EMPTY)},
        "custom-path": {"path": OTHER},
    }

    result = run(project(), **options[variant])

    assert result.verdict is not Verdict.PASS
    assert result.verdict is Verdict.NOT_RUN


def test_a_policy_recorded_as_seeded_in_the_lock_and_missing_is_orq_e547() -> None:
    """AC-1/R1. expected_behavior_source: AC-1 ("recorded as seeded in the lock, is FAIL with
    ORQ-E547"); R1. Base: the explicit id BASE (no policy), so the lock is the only evidence."""
    result = run(project(lock=[OTHER_SEEDED, SEEDED]))

    finding = only(result, E547)
    assert result.verdict is Verdict.FAIL
    assert finding.severity is Severity.ERROR


def test_a_lock_that_cannot_prove_a_deletion_leaves_the_policy_never_present() -> None:
    """AC-1/R1. expected_behavior_source: R1 (deleted needs a valid lock row with the owner
    `seeded`; a lock that cannot be read means absent). Base: the explicit id BASE."""
    result = run(project(lock=b"schema: orqlet.generated-lock/v1\nfiles: broken\n"))

    assert E547 not in codes(result)
    assert result.verdict is Verdict.NOT_RUN


@pytest.mark.parametrize("state", ["valid", "invalid"])
def test_a_policy_missing_from_the_working_tree_but_present_at_the_base_is_orq_e547(
    state: str,
) -> None:
    """AC-1/R1. expected_behavior_source: AC-1 ("missing from the working tree but present at the
    base tree ... is FAIL with ORQ-E547"); R1 ("loaded or invalid there"). Base: the explicit id
    BASE, which holds the policy."""
    raw = raw_of(plain_policy()) if state == "valid" else b"a: 1\na: 2\n"

    result = run(project(), at_base={POLICY: raw})

    finding = only(result, E547)
    assert result.verdict is Verdict.FAIL
    assert finding.severity is Severity.ERROR
    assert NOTHING not in result.not_run


def test_a_policy_missing_from_the_working_tree_but_present_at_head_is_orq_e547() -> None:
    """AC-1/R1. expected_behavior_source: AC-1; R2 (`HEAD` is an accepted base). Base: `HEAD`."""
    result = run(project(), base="HEAD", vcs=vcs_of_head({POLICY: raw_of(plain_policy())}))

    assert only(result, E547).severity is Severity.ERROR
    assert result.verdict is Verdict.FAIL


def test_a_policy_that_is_deleted_by_the_lock_and_present_at_the_base_is_still_a_fail() -> None:
    """AC-1/R1. expected_behavior_source: AC-1 (either evidence is FAIL with ORQ-E547); R1."""
    result = run(project(lock=[SEEDED]), at_base={POLICY: raw_of(plain_policy())})

    assert E547 in codes(result)
    assert result.verdict is Verdict.FAIL


def test_a_deleted_policy_fails_even_when_no_base_is_located() -> None:
    """AC-1/R1. expected_behavior_source: AC-1 (ORQ-E547 is an error: FAIL beats NOT_RUN); R1.
    Base: the explicit id BASE in a repository with no commit."""
    result = run(project(lock=[SEEDED]), vcs=WatchedVcs(RepoState.UNBORN_EMPTY))

    assert E547 in codes(result)
    assert result.verdict is Verdict.FAIL


def test_a_present_file_is_not_deleted_whatever_the_lock_says() -> None:
    """AC-1/R1. expected_behavior_source: R1 (deleted needs the file to be missing). Base: BASE."""
    result = run(project(plain_policy(), lock=[SEEDED]))

    assert E547 not in codes(result)
    assert result.verdict is Verdict.PASS


# --- AC-2: the loader's findings: ORQ-E540, ORQ-E541, ORQ-E542 ---------------------------------


def unreadable_by_the_rules() -> Files:
    return project(b"schema: a\nschema: b\n")  # a duplicate key


def refused_as_a_directory() -> Files:
    tree = Files()
    tree.add_dir(".orqlet")
    tree.add_dir(POLICY)
    return tree


def refused_as_a_link() -> Files:
    tree = project(raw_of(plain_policy()))
    tree.add_symlink(POLICY)
    return tree


def refused_when_the_read_fails() -> Files:
    tree = project(raw_of(plain_policy()))
    tree.denied[POLICY] = PermissionError("denied")
    return tree


def refused_when_the_read_is_unsafe() -> Files:
    tree = project(raw_of(plain_policy()))
    tree.denied[POLICY] = FileSystemError("refused")
    return tree


E540_PROJECTS: dict[str, Callable[[], Files]] = {
    "duplicate-key": unreadable_by_the_rules,
    "anchor": lambda: project(b"a: &x 1\nb: *x\n"),
    "not-utf8": lambda: project(b"\xff\xfe\x00"),
    "larger-than-256-kib": lambda: project(pad(raw_of(plain_policy()), LIMIT + 1)),
    "directory": refused_as_a_directory,
    "link": refused_as_a_link,
    "read-error": refused_when_the_read_fails,
    "unsafe-read": refused_when_the_read_is_unsafe,
}


@pytest.mark.parametrize("name", list(E540_PROJECTS))
def test_an_unreadable_file_is_the_loaders_orq_e540_and_nothing_else_is_checked(name: str) -> None:
    """AC-2/R1. expected_behavior_source: AC-2 ("ORQ-E540, ORQ-E541 and ORQ-E542 from the loader");
    R1 (invalid: its findings are reported, severity error, path = the PATH as given, nothing else
    is checked, FAIL). Base: BASE, which holds a policy that would give ORQ-E544 if it were read."""
    tree = E540_PROJECTS[name]()
    at_base = {POLICY: raw_of(plain_policy(excluded=[BLOCKED, exclusion("r2", aliases=["r2-a"])]))}
    expected = loader_findings(tree)
    assert {f.code for f in expected} == {E540}  # the premise, before the command is called

    result = run(tree, at_base=at_base)

    assert result.verdict is Verdict.FAIL
    assert [(f.code, f.severity, f.path) for f in result.findings] == [
        (f.code, f.severity, f.path) for f in expected
    ]
    assert all(f.path == POLICY for f in result.findings)


def test_a_file_of_exactly_256_kib_is_read_and_one_byte_more_is_orq_e540() -> None:
    """AC-2. expected_behavior_source: R1/the loader (`_MAX_BYTES`): 262144 bytes is not above the
    limit, 262145 is."""
    at_the_limit = pad(raw_of(plain_policy()), LIMIT)
    above = pad(raw_of(plain_policy()), LIMIT + 1)

    assert codes(run(project(at_the_limit))) == []
    assert codes(run(project(above))) == [E540]


E541_FILES: dict[str, bytes] = {
    "v1-file": b"schema: orqlet.model-policy/v1\nmodels: []\n",
    "policy-version-zero": raw_of({**plain_policy(), "policy_version": 0}),
    "unknown-key": raw_of({**plain_policy(), "surprise": True}),
    "bad-release": raw_of(plain_policy(reviewed="latest")),
    "empty-document": b"",
    "a-list": b"- a\n- b\n",
}


@pytest.mark.parametrize("name", list(E541_FILES))
def test_a_file_that_fails_the_contract_is_the_loaders_orq_e541(name: str) -> None:
    """AC-2/R1. expected_behavior_source: AC-2 (ORQ-E541 from the loader); R1 (the findings of the
    loader, severity error, path = the PATH as given, nothing else is checked). Base: BASE."""
    tree = project(E541_FILES[name])
    expected = loader_findings(tree)
    assert {f.code for f in expected} == {E541}  # the premise, before the command is called

    result = run(tree)

    assert result.verdict is Verdict.FAIL
    assert [(f.code, f.severity, f.path) for f in result.findings] == [
        (f.code, f.severity, f.path) for f in expected
    ]


def test_a_key_in_a_valid_file_is_the_loaders_orq_e542_and_the_key_is_not_shown() -> None:
    """AC-2/AC-5. expected_behavior_source: AC-2 (ORQ-E542 from the loader); R1; ORQLET-SEC-003
    (the placeholder is assembled at run time); BC-32. Base: BASE."""
    key = "".join(("gh", "p_", ("aB3" * 13)[:36]))
    tree = project(raw_of(plain_policy()) + f"\n# {key}\n".encode())
    expected = loader_findings(tree)
    assert {f.code for f in expected} == {E542}  # the premise, before the command is called

    result = run(tree)

    assert result.verdict is Verdict.FAIL
    assert codes(result) == [f.code for f in expected]
    assert not leaked(shown(result), key)


def test_an_invalid_file_checks_nothing_else_not_even_the_agent_files() -> None:
    """R1/R10. expected_behavior_source: R1 ("nothing else is checked"). Base: BASE."""
    files = {KINDS[0].path("team"): KINDS[0].file("blocked-alias")}

    result = run(project(b"a: 1\na: 2\n", files=files))

    assert codes(result) == [E540]


@pytest.mark.parametrize(
    ("path", "content"),
    [
        (OTHER, b"a: 1\na: 2\n"),
        ("docs/v1.yaml", E541_FILES["v1-file"]),
    ],
)
def test_a_custom_path_is_read_by_the_same_reader_and_the_findings_carry_that_path(
    path: str, content: bytes
) -> None:
    """R13. expected_behavior_source: R13 ("a custom path gives the same findings, with that PATH
    as `Finding.path`")."""
    result = run(project(files={path: content}), path=path)

    assert result.verdict is Verdict.FAIL
    assert {f.code for f in result.findings} <= {E540, E541}
    assert result.findings
    assert all(f.path == path for f in result.findings)


# --- AC-2: ORQ-E543, ORQ-E545 and the grouping of paths (R3, R5) ---------------------------------


def with_exclusion(*models: Doc, **extra: Any) -> Doc:
    """A policy of model A, then `models`, with the exclusion `BLOCKED`."""
    return policy_doc([MODEL_A, *models], excluded=[BLOCKED], **extra)


def oracle(doc: Doc, code: str) -> list[str]:
    """The field paths of `code` that `policy_problems` finds, in document order."""
    problems = policy_problems(ModelPolicy.model_validate(doc), ROLES, SKILLS)
    return [problem.path for problem in problems if problem.code == code]


def candidates_of(model_id: str, *, fallbacks: bool = False) -> Doc:
    models = [model_id]
    return profile_doc(
        "quality",
        clients=(CLAUDE,),
        candidates=() if fallbacks else models,
        fallbacks=models if fallbacks else (),
    )


E543_CASES: dict[str, tuple[Callable[[], Doc], list[str]]] = {
    "id-by-pattern": (lambda: with_exclusion(entry("blocked-model-1")), ["models[1]"]),
    "id-by-alias-in-another-spelling": (
        lambda: with_exclusion(entry("Blocked_Alias")),
        ["models[1]"],
    ),
    "family-by-tag": (
        lambda: with_exclusion(entry("example-c", family="vendor-blocked-family-2")),
        ["models[1]"],
    ),
    "route-name": (
        lambda: with_exclusion(entry("example-c", route(CLAUDE, "blocked-alias"))),
        ["models[1].routes[0]"],
    ),
    "route-also-known-as": (
        lambda: with_exclusion(
            entry(
                "example-c",
                route(CLAUDE, "example-c-claude-code", also_known_as=["blocked-model-7"]),
            )
        ),
        ["models[1].routes[0]"],
    ),
    "route-resolves-to": (
        lambda: with_exclusion(
            entry(
                "example-c",
                route(CLAUDE, "example-c-alias", kind="alias", resolves_to="blocked-alias"),
            )
        ),
        ["models[1].routes[0]"],
    ),
    "candidate": (
        lambda: with_exclusion(
            entry("blocked-model-1"), profiles=[candidates_of("blocked-model-1")]
        ),
        ["models[1]", "profiles[0].candidates[0].models[0]"],
    ),
    "fallback": (
        lambda: with_exclusion(
            entry("blocked-model-1"), profiles=[candidates_of("blocked-model-1", fallbacks=True)]
        ),
        ["models[1]", "profiles[0].fallbacks[0].models[0]"],
    ),
    "assignment": (
        lambda: with_exclusion(
            entry("blocked-model-1"),
            assignments=[assignment_doc("role", TESTER, model="blocked-model-1")],
        ),
        ["models[1]", "assignments[0].model"],
    ),
    "reference-to-a-model-with-an-excluded-route": (
        lambda: with_exclusion(
            entry("example-c", route(CLAUDE, "blocked-alias")),
            assignments=[assignment_doc("role", TESTER, model="example-c")],
        ),
        ["models[1].routes[0]", "assignments[0].model"],
    ),
}


@pytest.mark.parametrize("name", list(E543_CASES))
def test_a_model_route_candidate_fallback_or_assignment_that_an_exclusion_matches_is_orq_e543(
    name: str,
) -> None:
    """AC-2/R3/R5. expected_behavior_source: AC-2 ("ORQ-E543 for every model, route, candidate,
    fallback or assignment that matches an exclusion"); R3 (one finding, field paths only); R5
    (the paths of `policy_problems`). Base: BASE."""
    build, expected = E543_CASES[name]
    doc = build()
    assert oracle(doc, E543) == expected  # the premise, before the command is called

    result = run(project(doc))

    finding = only(result, E543)
    assert result.verdict is Verdict.FAIL
    assert finding.severity is Severity.ERROR
    assert paths_in(finding) == expected
    assert more_in(finding) is None


@pytest.mark.parametrize("state", ["proposed", "approved", "disabled", "retired"])
def test_an_excluded_model_is_orq_e543_in_every_approval_state(state: str) -> None:
    """AC-2/R5. expected_behavior_source: AC-2 ("matches an exclusion in any state"); R5."""
    result = run(project(with_exclusion(entry("blocked-model-1", state=state))))

    assert paths_in(only(result, E543)) == ["models[1]"]
    assert result.verdict is Verdict.FAIL


@pytest.mark.parametrize(
    "model_id", ["blocked-modelx", "example-blocked-model-1", "blocked-alias-2"]
)
def test_a_near_miss_of_an_exclusion_is_not_orq_e543(model_id: str) -> None:
    """AC-2/R5. expected_behavior_source: ADR-005 decision 1 / `model_identity.is_excluded` (an
    alias equals the normalised string; an id pattern matches the whole string)."""
    result = run(project(with_exclusion(entry(model_id))))

    assert E543 not in codes(result)


E545_CASES: dict[str, tuple[Callable[[], Doc], str]] = {
    "duplicate-model-id": (
        lambda: policy_doc([MODEL_A, entry("example-a", *routes_of("example-a2"))]),
        "models[1].id",
    ),
    "duplicate-exclusion-id": (
        lambda: policy_doc(
            [MODEL_A],
            excluded=[
                exclusion("rule-1", aliases=["x-alias"]),
                exclusion("rule-1", aliases=["y-alias"]),
            ],
        ),
        "excluded[1].id",
    ),
    "unknown-candidate": (
        lambda: policy_doc([MODEL_A], profiles=[candidates_of("no-such-model")]),
        "profiles[0].candidates[0].models[0]",
    ),
    "unknown-fallback": (
        lambda: policy_doc([MODEL_A], profiles=[candidates_of("no-such-model", fallbacks=True)]),
        "profiles[0].fallbacks[0].models[0]",
    ),
    "unknown-assignment-model": (
        lambda: policy_doc([MODEL_A], [assignment_doc("role", TESTER, model="no-such-model")]),
        "assignments[0].model",
    ),
    "undefined-profile": (
        lambda: policy_doc([MODEL_A], [assignment_doc("role", TESTER, profile="quality")]),
        "assignments[0].profile",
    ),
    "undefined-escalation": (
        lambda: policy_doc(
            [MODEL_A],
            profiles=[
                profile_doc("quality", candidates=["example-a"], escalation="engineering"),
            ],
        ),
        "profiles[0].escalation",
    ),
    "unknown-role": (
        lambda: policy_doc([MODEL_A], [assignment_doc("role", "no-such-role", model="example-a")]),
        "assignments[0].target.name",
    ),
    "unknown-skill": (
        lambda: policy_doc(
            [MODEL_A], [assignment_doc("skill", "no-such-skill", model="example-a")]
        ),
        "assignments[0].target.name",
    ),
    "a-skill-named-as-a-role": (
        lambda: policy_doc([MODEL_A], [assignment_doc("role", DESIGN, model="example-a")]),
        "assignments[0].target.name",
    ),
    "a-role-named-as-a-skill": (
        lambda: policy_doc([MODEL_A], [assignment_doc("skill", TESTER, model="example-a")]),
        "assignments[0].target.name",
    ),
    "two-models-claim-one-name": (
        lambda: policy_doc([MODEL_A, entry("example-c", route(CLAUDE, "example-a-claude-code"))]),
        "models[1]",
    ),
    "two-models-claim-one-name-by-also-known-as": (
        lambda: policy_doc(
            [
                MODEL_A,
                entry(
                    "example-c",
                    route(CLAUDE, "example-c-claude-code", also_known_as=["example-a-codex"]),
                ),
            ]
        ),
        "models[1]",
    ),
}


@pytest.mark.parametrize("name", list(E545_CASES))
def test_a_reference_or_a_name_problem_is_orq_e545_with_the_field_path(name: str) -> None:
    """AC-2/R3/R5. expected_behavior_source: AC-2 ("ORQ-E545 for the reference and name problems of
    `policy_problems`, where the known role and skill names are those of the packaged workflow");
    R3; R5. Base: BASE."""
    build, expected = E545_CASES[name]
    doc = build()
    assert oracle(doc, E545) == [expected]  # the premise, before the command is called

    result = run(project(doc))

    finding = only(result, E545)
    assert result.verdict is Verdict.FAIL
    assert finding.severity is Severity.ERROR
    assert paths_in(finding) == [expected]
    assert E543 not in codes(result)


def test_every_role_and_every_skill_of_the_packaged_workflow_is_a_known_name() -> None:
    """AC-2/R5. expected_behavior_source: AC-2 (the known names are those of the packaged
    workflow); interface item 4 (the five roles and the six skills). Base: BASE."""
    assignments = [assignment_doc("role", role, model="example-a") for role in ROLES]
    assignments += [
        assignment_doc("skill", skill, model="example-a", client=CLAUDE) for skill in SKILLS
    ]

    result = run(project(policy_doc([MODEL_A], assignments)))

    assert E545 not in codes(result)
    assert result.verdict is Verdict.PASS


def test_the_exclusion_and_the_reference_problems_are_two_findings_one_for_each_code() -> None:
    """AC-2/R3. expected_behavior_source: R3 ("For one code, ... ONE finding per code")."""
    doc = policy_doc(
        [MODEL_A, entry("blocked-model-1"), entry("blocked-model-2")],
        [assignment_doc("role", "no-such-role", model="example-a")] * 2,
        excluded=[BLOCKED],
    )

    result = run(project(doc))

    assert paths_in(only(result, E543)) == ["models[1]", "models[2]"]
    assert paths_in(only(result, E545)) == [
        "assignments[0].target.name",
        "assignments[1].target.name",
    ]


def many_excluded(count: int) -> Doc:
    return with_exclusion(*(entry(f"blocked-model-{i}") for i in range(count)))


def many_unknown_roles(count: int) -> Doc:
    return policy_doc(
        [MODEL_A], [assignment_doc("role", f"no-role-{i}", model="example-a") for i in range(count)]
    )


def many_unapproved(count: int) -> Doc:
    return policy_doc(
        [
            entry(f"example-{i}", *routes_of(f"example-{i}"), approval_ref="nope")
            for i in range(count)
        ]
    )


def many_removed(count: int) -> Doc:
    """The base policy: `count` exclusions that the file lacks."""
    return plain_policy(
        excluded=[exclusion(f"rule-{i}", aliases=[f"alias-{i}"]) for i in range(count)]
    )


GROUPED: dict[str, tuple[str, Callable[[int], Doc], Callable[[int], list[str]]]] = {
    "orq-e543": (E543, many_excluded, lambda n: [f"models[{i + 1}]" for i in range(n)]),
    "orq-e545": (
        E545,
        many_unknown_roles,
        lambda n: [f"assignments[{i}].target.name" for i in range(n)],
    ),
    "orq-e546": (
        E546,
        many_unapproved,
        lambda n: [f"models[{i}].approval.approval_ref" for i in range(n)],
    ),
    "orq-e544": (E544, many_removed, lambda n: [f"excluded[{i}]" for i in range(n)]),
}


@pytest.mark.parametrize("count", [1, 19, 20, 21, 25, 60])
@pytest.mark.parametrize("name", list(GROUPED))
def test_a_code_lists_at_most_20_field_paths_and_then_says_and_n_more(
    name: str, count: int
) -> None:
    """AC-2/R3. expected_behavior_source: R3 ("ONE finding per code listing at most 20 field paths
    ... and then `and N more`"); `model_selection._MAX_PATHS`. Base: BASE (for ORQ-E544 it holds the
    policy with `count` exclusions that the file lacks)."""
    code, build, expected = GROUPED[name]
    every = expected(count)
    if code in {E543, E545}:
        assert oracle(build(count), code) == every  # the premise, before the command is called
    if code == E544:
        result = run(project(plain_policy(excluded=[])), at_base={POLICY: raw_of(build(count))})
    else:
        result = run(project(build(count)))

    finding = only(result, code)
    assert finding.severity is Severity.ERROR
    assert paths_in(finding) == every[:20]
    assert more_in(finding) == (count - 20 if count > 20 else None)
    assert result.verdict is Verdict.FAIL


# --- AC-2: ORQ-E546 -----------------------------------------------------------------------------

ALLOWED_REFS = [
    "pr:1",
    "pr:42",
    "pr:1234567",
    "commit:" + "a" * 40,
    "commit:" + "0123456789abcdef" * 4,
    "adr:docs/design/dynamic-model-profiles/design/adr-003-example.md",
    "adr:adr-001.md",
]
REFUSED_REFS = [
    "pr:0",
    "pr:007",
    "pr:",
    "pr:4x",
    "pr:-1",
    "pr:1.5",
    "pr:42 ",
    "commit:" + "a" * 7,
    "commit:" + "A" * 40,
    "commit:" + "a" * 41,
    "commit:" + "a" * 63,
    "commit:" + "a" * 65,
    "commit:",
    "adr:../x",
    "adr:/x",
    "adr:",
    "adr:docs//x.md",
    "adr:docs\\x.md",
    "example-approval-ref-1",
    "https://example.com/pull/42",
    "42",
    "#42",
]


def one_approved(**approval: Any) -> Doc:
    return policy_doc([entry("example-a", *routes_of("example-a"), **approval)])


@pytest.mark.parametrize("ref", ALLOWED_REFS)
def test_an_approval_ref_of_an_allowed_form_is_accepted(ref: str) -> None:
    """AC-2/R4. expected_behavior_source: AC-2 ("an `approval_ref` of the allowed forms
    (`pr:<number>`, `commit:<full hex id>` or `adr:<repository path>`)"); R4. Base: BASE."""
    result = run(project(one_approved(approval_ref=ref)))

    assert E546 not in codes(result)
    assert result.verdict is Verdict.PASS


@pytest.mark.parametrize("ref", REFUSED_REFS)
def test_an_approval_ref_of_another_form_is_orq_e546_at_that_field(ref: str) -> None:
    """AC-2/R4. expected_behavior_source: R4 (`pr:0`, `pr:007`, `pr:`, `pr:4x`, a short, upper-case
    or 41-digit commit id, `adr:../x`, `adr:/x`, `adr:` are refused); AC-2. Base: BASE."""
    result = run(project(one_approved(approval_ref=ref)))

    finding = only(result, E546)
    assert paths_in(finding) == ["models[0].approval.approval_ref"]
    assert result.verdict is Verdict.FAIL


def test_an_approved_entry_without_an_approver_is_orq_e546_at_approved_by() -> None:
    """AC-2/R4. expected_behavior_source: AC-2 ("without `approved_by`"); R4 (a problem at
    `models[i].approval.approved_by`)."""
    result = run(project(one_approved(approved_by=None)))

    assert paths_in(only(result, E546)) == ["models[0].approval.approved_by"]


def test_an_approved_entry_without_either_field_lists_both_paths_in_one_finding() -> None:
    """AC-2/R3/R4. expected_behavior_source: R3 (one finding for one code); R4 (both fields)."""
    result = run(project(one_approved(approved_by=None, approval_ref=None)))

    assert sorted(paths_in(only(result, E546))) == [
        "models[0].approval.approval_ref",
        "models[0].approval.approved_by",
    ]


def test_the_entries_that_lack_the_approval_are_listed_in_the_order_of_the_document() -> None:
    """AC-2/R3/R4. expected_behavior_source: R3 (field paths, in order); R4."""
    models = [
        entry("example-a", *routes_of("example-a")),
        entry("example-b", *routes_of("example-b"), approved_by=None),
        entry("example-c", *routes_of("example-c")),
        entry("example-d", *routes_of("example-d"), approval_ref="nope"),
    ]

    found = paths_in(only(run(project(policy_doc(models))), E546))

    assert [p.split(".")[0] for p in found] == ["models[1]", "models[3]"]


@pytest.mark.parametrize("state", ["proposed", "disabled", "retired"])
def test_an_entry_that_is_not_approved_is_not_checked_for_the_approval(state: str) -> None:
    """AC-2/R4. expected_behavior_source: R4 ("States `proposed`, `disabled`, `retired` are not
    checked")."""
    doc = policy_doc(
        [entry("example-a", *routes_of("example-a"), state=state, approval_ref="nope")]
    )

    assert E546 not in codes(run(project(doc)))


# --- AC-2: ORQ-E544 and the base tree -------------------------------------------------------------


def rules(*ids: str) -> Doc:
    """A policy whose `excluded` list holds these ids (each with an alias that matches nothing)."""
    return plain_policy(excluded=[exclusion(i, aliases=[f"{i}-alias"]) for i in ids])


@pytest.mark.parametrize(
    ("at_base", "in_file", "expected"),
    [
        (("a", "b", "c"), ("a", "c"), ["excluded[1]"]),
        (("a", "b", "c"), ("b",), ["excluded[0]", "excluded[2]"]),
        (("a", "b", "c"), (), ["excluded[0]", "excluded[1]", "excluded[2]"]),
        (("a", "b"), ("a", "b"), []),
        (("a", "b"), ("b", "a"), []),
        (("a",), ("a", "z"), []),
        ((), ("a",), []),
        ((), (), []),
    ],
)
def test_an_excluded_entry_of_the_base_that_the_file_lacks_is_orq_e544_by_position(
    at_base: tuple[str, ...], in_file: tuple[str, ...], expected: list[str]
) -> None:
    """AC-2/R2/R3. expected_behavior_source: AC-2 ("ORQ-E544 for an `excluded` entry that the base
    tree holds and the file lacks"); R2 (compare by `id`; names positions in the base policy like
    `excluded[1]`, never an id). Base: the explicit id BASE, which holds the policy."""
    result = run(project(rules(*in_file)), at_base={POLICY: raw_of(rules(*at_base))})

    if not expected:
        assert E544 not in codes(result)
        assert result.verdict is Verdict.PASS
        return
    finding = only(result, E544)
    assert paths_in(finding) == expected
    assert finding.severity is Severity.ERROR
    assert result.verdict is Verdict.FAIL


def test_the_base_can_be_head() -> None:
    """AC-2/R2. expected_behavior_source: R2 (an explicit `--base` may be `HEAD`). Base: `HEAD`,
    whose tree holds two exclusions that the file lacks one of."""
    vcs = vcs_of_head({POLICY: raw_of(rules("a", "b"))})

    result = run(project(rules("a")), base="HEAD", vcs=vcs)

    assert paths_in(only(result, E544)) == ["excluded[1]"]


def test_the_base_can_be_a_branch_name() -> None:
    """AC-2/R2. expected_behavior_source: R2 (an explicit `--base` may be a branch name). Base: the
    branch `release/1`, which names TARGET, whose merge base with HEAD is BASE."""
    vcs = vcs_of_target({POLICY: raw_of(rules("a", "b"))}, ref="release/1")

    result = run(project(rules("a")), base="release/1", vcs=vcs)

    assert paths_in(only(result, E544)) == ["excluded[1]"]


@pytest.mark.parametrize("ref", ["origin/main", "main"])
def test_without_a_base_the_merge_base_with_the_target_branch_of_the_profile_is_used(
    ref: str,
) -> None:
    """AC-2/R2. expected_behavior_source: AC-2 ("otherwise the merge base that `validate review`
    uses"); R2 (the profile's target branch: `<remote>/<branch>`, then `<branch>`). Base: none
    given; the profile names `main` on `origin`, and only `ref` exists."""
    vcs = vcs_of_target({POLICY: raw_of(rules("a", "b"))}, ref=ref)

    result = run(project(rules("a"), enabled=CLIENTS), base=None, vcs=vcs)

    assert paths_in(only(result, E544)) == ["excluded[1]"]


def test_an_additive_change_against_the_merge_base_passes() -> None:
    """AC-2/R2. expected_behavior_source: R2 (only a missing id is found). Base: none given; the
    merge base through the profile's target branch."""
    vcs = vcs_of_target({POLICY: raw_of(rules("a"))})

    result = run(project(rules("a", "b"), enabled=CLIENTS), base=None, vcs=vcs)

    assert result.verdict is Verdict.PASS


def test_a_base_with_no_policy_leaves_nothing_to_compare_and_passes() -> None:
    """AC-2/R2. expected_behavior_source: R2 ("A base policy that is absent: nothing to compare").
    Base: BASE, whose tree holds no policy."""
    result = run(project(rules("a")))

    assert E544 not in codes(result)
    assert result.not_run == ()
    assert result.verdict is Verdict.PASS


def test_a_base_policy_that_cannot_be_loaded_is_a_reason_not_run_and_no_e544() -> None:
    """AC-2/R2. expected_behavior_source: R2 ("A base policy that cannot be loaded ... no E544 is
    possible and a not-run reason is added"). Base: BASE, whose policy breaks the reading rules."""
    result = run(project(rules("a")), at_base={POLICY: b"a: 1\na: 2\n"})

    assert E544 not in codes(result)
    assert result.not_run
    assert result.verdict is Verdict.NOT_RUN


UNLOCATED: dict[str, tuple[str | None, Callable[[], FakeVcs], bool]] = {
    "no-commit": (BASE, lambda: WatchedVcs(RepoState.UNBORN_EMPTY), False),
    "unknown-commit-id": ("d" * 40, lambda: vcs_of(), False),
    "unknown-branch": ("no-such-branch", lambda: vcs_of(), False),
    "no-target-branch-known": (None, lambda: vcs_of_target(ref="trunk"), True),
    "no-profile": (None, lambda: vcs_of_target(), False),
    "no-common-history": (
        BASE,
        lambda: WatchedVcs(
            RepoState.HAS_COMMITS,
            commits=(CommitSummary(HEAD, "head"),),
            revisions={BASE: {}},
        ),
        False,
    ),
    "several-merge-bases": (
        BASE,
        lambda: WatchedVcs(
            RepoState.HAS_COMMITS,
            commits=(CommitSummary(HEAD, "head"),),
            revisions={BASE: {}},
            merge_bases={(HEAD, BASE): ("d" * 40, "e" * 40)},
        ),
        False,
    ),
}


@pytest.mark.parametrize("name", list(UNLOCATED))
def test_a_base_that_cannot_be_located_is_a_reason_not_run_for_a_loaded_policy(name: str) -> None:
    """AC-2/R2. expected_behavior_source: R2 ("a base that cannot be located: no E544 is possible
    and a not-run reason is added (so the verdict is NOT_RUN unless an error exists)"); the reasons
    of `binding_inputs.locate` (no commit, unknown target branch, a base that names no commit, no
    or several merge bases)."""
    base, make_vcs, with_profile = UNLOCATED[name]

    result = run(
        project(rules("a"), enabled=CLIENTS if with_profile else None), base=base, vcs=make_vcs()
    )

    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run
    assert E544 not in codes(result)


@pytest.mark.parametrize("name", list(UNLOCATED))
def test_an_error_beats_a_base_that_cannot_be_located(name: str) -> None:
    """AC-2/R2. expected_behavior_source: R2 ("NOT_RUN unless an error exists"). The policy names
    an excluded model."""
    base, make_vcs, with_profile = UNLOCATED[name]
    tree = project(
        with_exclusion(entry("blocked-model-1")), enabled=CLIENTS if with_profile else None
    )

    result = run(tree, base=base, vcs=make_vcs())

    assert result.verdict is Verdict.FAIL
    assert E543 in codes(result)
    assert result.not_run


# --- AC-3: ORQ-W540 ---------------------------------------------------------------------------


def proposed(model_id: str = "example-p") -> Doc:
    return entry(model_id, *routes_of(model_id), state="proposed")


def missing(*, enabled: Sequence[str] = CLIENTS, doc: Doc) -> list[Finding]:
    return by_code(run(project(doc, enabled=enabled)), W540)


W540_CASES: dict[str, tuple[Callable[[], Doc], list[str]]] = {
    "manual-profile-with-no-candidate-for-two-clients": (
        lambda: policy_doc(
            [MODEL_A],
            profiles=[profile_doc("quality", candidates=["example-a"], clients=(CLAUDE,))],
        ),
        ["profile quality for codex", "profile quality for cursor"],
    ),
    "manual-pin-of-a-model-nobody-approved": (
        lambda: policy_doc([proposed()], [assignment_doc("role", TESTER, model="example-p")]),
        [f"role {TESTER} for {client}" for client in CLIENTS],
    ),
    "fallbacks-profile-with-no-fallback": (
        lambda: policy_doc(
            [MODEL_A],
            profiles=[
                profile_doc("economy", mode="automatic-with-fallbacks", candidates=["example-a"]),
            ],
        ),
        [f"profile economy for {client}" for client in CLIENTS],
    ),
    "each-assignment-is-judged-alone": (
        lambda: policy_doc(
            [MODEL_A, proposed()],
            [
                assignment_doc("role", TESTER, model="example-p"),
                assignment_doc("role", TESTER, model="example-a"),
            ],
        ),
        [f"role {TESTER} for {client}" for client in CLIENTS],
    ),
}


@pytest.mark.parametrize("name", list(W540_CASES))
def test_a_profile_or_assignment_with_nothing_to_give_is_orq_w540_and_does_not_fail(
    name: str,
) -> None:
    """AC-3/R5. expected_behavior_source: AC-3 ("ORQ-W540 (`missing-candidate`) for a `manual`
    profile or assignment with no eligible candidate and for an `automatic-with-fallbacks` one with
    no eligible fallback"); R5 (the P-6 readings: each assignment is judged alone; each profile is
    judged for every enabled client; they come from `select_models(...).missing`). Base: BASE."""
    build, expected = W540_CASES[name]
    doc = build()
    oracle_messages = [
        f.message
        for f in select_models(ModelPolicy.model_validate(doc), ROLES, SKILLS, CLIENTS).missing
    ]
    assert len(oracle_messages) == len(expected)  # the premise, before the command is called
    for message, text in zip(oracle_messages, expected, strict=True):
        assert text in message

    result = run(project(doc))

    found = by_code(result, W540)
    assert result.verdict is Verdict.PASS
    assert all(f.severity is Severity.WARNING for f in found)
    assert [f.message for f in found] == oracle_messages
    assert len(found) == len(expected)
    for finding, text in zip(found, expected, strict=True):
        assert "missing-candidate" in finding.message
        assert text in finding.message


@pytest.mark.parametrize(
    "doc",
    [
        policy_doc(
            [proposed()],
            [assignment_doc("role", TESTER, model="example-p", mode="automatic-with-fallbacks")],
        ),
        policy_doc(
            [proposed()], [assignment_doc("role", TESTER, model="example-p", mode="automatic")]
        ),
        policy_doc([MODEL_A], profiles=[profile_doc("quality", mode="automatic")]),
        policy_doc(
            [MODEL_A], profiles=[profile_doc("quality", mode="automatic", candidates=["example-a"])]
        ),
    ],
    ids=[
        "pin-in-fallbacks-mode",
        "pin-in-automatic-mode",
        "empty-automatic-profile",
        "automatic-profile",
    ],
)
def test_a_source_that_does_not_have_to_give_a_candidate_is_not_judged(doc: Doc) -> None:
    """AC-3/R5. expected_behavior_source: R5 ("a model-pin assignment in mode
    `automatic-with-fallbacks` is NOT judged"; mode `automatic` pins nothing, so it never lacks
    anything). Base: BASE."""
    assert W540 not in codes(run(project(doc)))


def test_a_finding_of_orq_w540_never_carries_a_model_id_or_a_route_name() -> None:
    """AC-3/AC-5/R5. expected_behavior_source: R5 ("a finding never carries a model id"); BC-32."""
    doc = policy_doc([proposed()], [assignment_doc("role", TESTER, model="example-p")])

    found = by_code(run(project(doc)), W540)

    assert found
    assert not any("example-p" in f.message or "example-p" in (f.path or "") for f in found)


def test_the_profile_is_judged_for_the_enabled_clients_of_the_project_profile_only() -> None:
    """AC-3/R6. expected_behavior_source: R6 (W540 uses the enabled clients of
    `.orqlet/project-profile.yaml`). The profile lists candidates for Claude Code only."""
    doc = policy_doc(
        [MODEL_A], profiles=[profile_doc("quality", candidates=["example-a"], clients=(CLAUDE,))]
    )

    assert missing(enabled=(CLAUDE,), doc=doc) == []
    codex_only = missing(enabled=(CODEX,), doc=doc)
    assert len(codex_only) == 1
    assert "profile quality for codex" in codex_only[0].message
    assert len(missing(enabled=(CODEX, CURSOR), doc=doc)) == 2


@pytest.mark.parametrize("profile", ["missing", "not-a-profile", "not-yaml"])
def test_when_the_profile_cannot_be_read_all_three_clients_are_used(profile: str) -> None:
    """AC-3/R6. expected_behavior_source: R6 ("when that file cannot be read or does not validate,
    all three clients are used")."""
    doc = policy_doc(
        [MODEL_A], profiles=[profile_doc("quality", candidates=["example-a"], clients=(CLAUDE,))]
    )
    tree = project(doc)
    if profile == "not-a-profile":
        put(tree, PROFILE, "clients: nope\n")
    if profile == "not-yaml":
        put(tree, PROFILE, b"a: 1\na: 2\n")

    found = by_code(run(tree), W540)

    assert len(found) == 2
    assert [
        f"profile quality for {client}" in f.message
        for client, f in zip((CODEX, CURSOR), found, strict=True)
    ] == [True, True]


def test_orq_w540_is_not_produced_when_the_policy_has_orq_e543_or_orq_e545() -> None:
    """AC-3/R5. expected_behavior_source: R5 ("Only when there are no such problems are ORQ-W540
    findings produced")."""
    gap = profile_doc("quality", candidates=["example-a"], clients=(CLAUDE,))
    unknown_role = assignment_doc("role", "no-such-role", model="example-a")
    excluded_model = with_exclusion(entry("blocked-model-1"), profiles=[gap])

    with_e545 = run(project(policy_doc([MODEL_A], [unknown_role], profiles=[gap])))
    with_e543 = run(project(excluded_model))

    assert E545 in codes(with_e545)
    assert W540 not in codes(with_e545)
    assert E543 in codes(with_e543)
    assert W540 not in codes(with_e543)


# --- AC-3: ORQ-W541 -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reviewed", "release", "warns"),
    [
        ("0.3.0", "0.4.0", True),
        ("0.4.0", "0.4.0", False),
        ("0.5.0", "0.4.0", False),
        ("0.3.9", "0.4.0", True),
        ("0.4.0", "0.4.1", True),
        ("0.9.0", "0.10.0", True),
        ("0.10.0", "0.9.0", False),
        ("1.0.0", "0.99.99", False),
        ("0.0.0", "0.0.1", True),
    ],
)
def test_orq_w541_is_one_warning_when_the_review_is_older_than_the_workflow(
    reviewed: str, release: str, warns: bool
) -> None:
    """AC-3/R7. expected_behavior_source: AC-3 ("ORQ-W541 when `reviewed_for_release` is older than
    the workflow version that the installed package states (a `Version` comparison, no clock)");
    R7 (equal or newer: none). The clock raises when it is read."""
    workflow = PinnedWorkflow(PackagedWorkflow(), version=release)

    result = run(project(plain_policy(reviewed=reviewed)), workflow=workflow, clock=RaisingClock())

    found = by_code(result, W541)
    assert len(found) == (1 if warns else 0)
    assert all(f.severity is Severity.WARNING for f in found)
    assert result.verdict is Verdict.PASS


# --- AC-3: ORQ-W542 -----------------------------------------------------------------------------


def retiring(retires_on: str, *, state: str = "approved") -> Doc:
    model = entry(
        "example-c", route(CLAUDE, "example-c-claude-code", retires_on=retires_on), state=state
    )
    return policy_doc([MODEL_A, model], excluded=[BLOCKED])


def clock_at(day: str, time_of_day: str = "12:00:00") -> FixedClock:
    return FixedClock(datetime.fromisoformat(f"{day}T{time_of_day}+00:00"))


DAYS = [
    (-400, "past"),
    (-1, "past"),
    (0, "within"),
    (1, "within"),
    (29, "within"),
    (30, "within"),
    (31, None),
    (32, None),
    (365, None),
]


@pytest.mark.parametrize("time_of_day", ["00:00:00", "12:00:00", "23:59:59"])
@pytest.mark.parametrize(("days", "expected"), DAYS)
def test_orq_w542_warns_for_a_past_date_and_for_one_within_30_days_of_today(
    days: int, expected: str | None, time_of_day: str
) -> None:
    """AC-3/R8. expected_behavior_source: AC-3 ("ORQ-W542 when a route's `retires_on` is past or
    within 30 days of today, read through the Clock port"); R8 (day 30 warns, day 31 does not, today
    warns; the date, not the time of day; the finding names `models[i].routes[j]`)."""
    day = (TODAY + timedelta(days=days)).isoformat()

    result = run(project(retiring(day)), clock=clock_at(TODAY.isoformat(), time_of_day))

    found = by_code(result, W542)
    assert result.verdict is Verdict.PASS
    if expected is None:
        assert found == []
        return
    assert len(found) == 1
    assert found[0].severity is Severity.WARNING
    assert names(found[0], "models[1].routes[0]")
    assert {"past": "past", "within": "within 30 days"}[expected] in found[0].message.lower()


def test_orq_w542_tells_a_past_date_from_one_within_30_days() -> None:
    """AC-3/R8. expected_behavior_source: R8 (the two cases are worded as "past" and "within 30
    days"); the two warnings must not say the same thing."""
    clock = clock_at(TODAY.isoformat())
    past = only(run(project(retiring("2026-09-01")), clock=clock), W542)
    soon = only(run(project(retiring("2026-10-25")), clock=clock), W542)

    assert past.message != soon.message


@pytest.mark.parametrize("state", ["proposed", "approved", "disabled", "retired"])
def test_orq_w542_is_reported_for_a_route_of_a_model_in_every_state(state: str) -> None:
    """AC-3/R8. expected_behavior_source: R8 ("every route of every model (any approval state)")."""
    result = run(project(retiring("2026-10-01", state=state)))

    assert names(only(result, W542), "models[1].routes[0]")


def test_orq_w542_names_each_route_in_the_order_of_the_document() -> None:
    """AC-3/R8/R14. expected_behavior_source: R8 (the field path `models[i].routes[j]`); R14."""
    doc = policy_doc(
        [
            entry(
                "example-a",
                route(CLAUDE, "example-a-claude-code", retires_on="2026-10-01"),
                route(CODEX, "example-a-codex"),
                route(CURSOR, "example-a-cursor", retires_on="2026-10-25"),
            ),
            entry("example-b", route(CLAUDE, "example-b-claude-code", retires_on="2030-01-01")),
            entry("example-c", route(CLAUDE, "example-c-claude-code", retires_on="2026-10-02")),
        ]
    )

    found = by_code(run(project(doc)), W542)

    expected = ("models[0].routes[0]", "models[0].routes[2]", "models[2].routes[0]")
    assert len(found) == len(expected)
    for finding, path in zip(found, expected, strict=True):
        assert names(finding, path)


def test_orq_w542_does_not_print_a_route_name() -> None:
    """AC-3/AC-5/R8. expected_behavior_source: R8 ("may print the date; no route name"); BC-32."""
    found = only(run(project(retiring("2026-10-01"))), W542)

    assert "example-c-claude-code" not in found.message
    assert "example-c-claude-code" not in (found.path or "")


def test_the_date_is_the_utc_date_of_the_clock() -> None:
    """AC-3/R8. expected_behavior_source: R8 ("today = `clock.now()` as a UTC date"). At 23:30 in
    UTC-5 it is already the next day in UTC, so a route that retires on the 20th is past."""
    late = datetime(2026, 10, 20, 23, 30, tzinfo=timezone(timedelta(hours=-5)))

    found = only(run(project(retiring("2026-10-20")), clock=FixedClock(late)), W542)

    assert "past" in found.message.lower()


def test_the_clock_is_read_when_a_route_has_a_retirement_date() -> None:
    """AC-3/R8. expected_behavior_source: AC-3 ("read through the Clock port"); R8."""
    clock = CountingClock()

    run(project(retiring("2030-01-01")), clock=clock)

    assert clock.calls >= 1


@pytest.mark.parametrize(
    "scenario",
    ["sound", "all-states", "invalid-file", "never-present", "w541-and-w540", "drift"],
)
def test_the_clock_is_not_read_when_no_route_has_a_retirement_date(scenario: str) -> None:
    """AC-3/AC-6/R8. expected_behavior_source: R8 ("The clock is read only when at least one route
    has `retires_on`"); AC-6 ("a fake whose `now()` raises proves the clock is not read"); AC-3
    ("selection itself never reads the date")."""
    gap = profile_doc("quality", candidates=["example-a"], clients=(CLAUDE,))
    trees: dict[str, Files] = {
        "sound": project(pinned_policy()),
        "all-states": project(
            policy_doc(
                [
                    entry(f"example-{s}", *routes_of(f"example-{s}"), state=s)
                    for s in ("proposed", "disabled", "retired")
                ]
            )
        ),
        "invalid-file": project(b"a: 1\na: 2\n"),
        "never-present": project(),
        "w541-and-w540": project(policy_doc([MODEL_A], profiles=[gap], reviewed="0.1.0")),
        "drift": project(
            plain_policy(),
            files={KINDS[0].path(): KINDS[0].file("blocked-alias")},
        ),
    }

    result = run(trees[scenario], clock=RaisingClock())

    assert W542 not in codes(result)
    assert isinstance(result.verdict, Verdict)


# --- AC-4: the drift check of the model values in the agent and skill files -------------------


@EVERY_KIND
@pytest.mark.parametrize("is_generated", [False, True], ids=["team-authored", "generated"])
@pytest.mark.parametrize("spelling", list(EXCLUDED_VALUES))
def test_a_value_that_matches_an_exclusion_is_orq_e548_in_any_file(
    kind: Kind, is_generated: bool, spelling: str
) -> None:
    """AC-4/R10. expected_behavior_source: AC-4 ("A value that matches an exclusion is ORQ-E548 in
    any file"); R10 (the raw string, NFKC and case-folded, bracket contents included, and the
    normalised form; a generated file with an excluded value gets both ORQ-E548 and ORQ-W543)."""
    content = kind.file(EXCLUDED_VALUES[spelling])

    result = drift(kind, content, is_generated=is_generated)

    finding = only(result, E548)
    assert finding.severity is Severity.ERROR
    assert names(finding, kind.path())
    assert result.verdict is Verdict.FAIL
    assert (W543 in codes(result)) == is_generated


@EVERY_KIND
@pytest.mark.parametrize(
    "value", ["inherit", "example-a-claude-code", "unknown-model", "blocked-alias-2"]
)
def test_a_value_that_matches_no_exclusion_is_nothing_in_a_team_authored_file(
    kind: Kind, value: str
) -> None:
    """AC-4/R9. expected_behavior_source: AC-4 ("nothing in a team-authored file"); R9 ("A
    team-authored file never gets W543")."""
    result = drift(kind, kind.file(value))

    assert result.findings == ()
    assert result.verdict is Verdict.PASS


@EVERY_KIND
@pytest.mark.parametrize(
    "value",
    [
        "claude-opus-5[effort=high]",
        "caf\u00e9-model",
        "x" * 200,
        "two words",
    ],
    ids=["bracketed-cursor-id", "non-ascii", "longer-than-128", "space"],
)
def test_a_value_that_fails_the_model_ref_type_is_never_skipped(kind: Kind, value: str) -> None:
    """AC-4/R10/R11. expected_behavior_source: AC-4 ("A value that fails `ModelRef` ... is tested
    for the exclusion on its raw NFKC string first and then reported as `unmatched`, never
    skipped"); R10; R11 (`unmatched, <n> characters`). The file is generated and differs."""
    result = drift(kind, kind.file(value), is_generated=True)

    finding = only(result, W543)
    assert f"unmatched, {len(value)} characters" in finding.message
    assert value not in shown(result)


@EVERY_KIND
def test_a_fullwidth_spelling_of_an_excluded_alias_is_excluded_after_nfkc(kind: Kind) -> None:
    """AC-4/R10. expected_behavior_source: AC-4 ("tested for the exclusion on its raw NFKC
    string"); R10 (NFKC and case-folded). The alias `blocked-alias`, in fullwidth letters."""
    fullwidth = "".join(chr(ord(c) + 0xFEE0) if "a" <= c <= "z" else c for c in "blocked-alias")

    result = drift(kind, kind.file(fullwidth))

    finding = only(result, E548)
    assert f"unmatched, {len(fullwidth)} characters" in finding.message
    assert fullwidth not in shown(result)


@EVERY_KIND
def test_a_generated_file_that_follows_the_policy_has_no_finding(kind: Kind) -> None:
    """AC-4/R9. expected_behavior_source: AC-4 ("A value that differs from the resolution is
    ORQ-W543 in a file that the lock records as generated"); R9 (a policy that pins nothing:
    `inherit` for Claude Code and Cursor roles, no model key for Codex roles and for skills)."""
    result = drift(kind, kind.unpinned(), is_generated=True)

    assert W543 not in codes(result)
    assert result.findings == ()


@EVERY_KIND
@pytest.mark.parametrize(
    "value", [OTHER_VALUE, "example-b-claude-code", "claude-opus-5[effort=high]"]
)
def test_a_generated_file_with_a_differing_value_is_orq_w543_and_still_passes(
    kind: Kind, value: str
) -> None:
    """AC-4/R9. expected_behavior_source: AC-4 ("ORQ-W543 in a file that the lock records as
    generated"); AC-3-style (a warning does not change PASS); R9."""
    result = drift(kind, kind.file(value), is_generated=True)

    finding = only(result, W543)
    assert finding.severity is Severity.WARNING
    assert names(finding, kind.path())
    assert result.verdict is Verdict.PASS


PINNED_FILES = (
    (KINDS[0], "example-a-claude-code"),
    (KINDS[1], "example-a-cursor"),
    (KINDS[2], "example-a-codex"),
    (KINDS[3], "example-a-claude-code"),
)


@pytest.mark.parametrize(
    ("kind", "pinned"), PINNED_FILES, ids=lambda item: getattr(item, "label", item)
)
def test_a_generated_file_follows_the_name_that_the_policy_pins(kind: Kind, pinned: str) -> None:
    """AC-4/R9. expected_behavior_source: R9 (for a generated role file the expected value is the
    pinned route name of the role for that client; for `.claude/skills/<name>/SKILL.md` the pinned
    name from `.skills[name]["claude-code"]`). The policy pins `example-a` for the tester role and,
    for Claude Code, the design skill."""
    followed = drift(kind, kind.file(pinned), is_generated=True, policy=pinned_policy())
    inherited = drift(kind, kind.unpinned(), is_generated=True, policy=pinned_policy())
    other = drift(kind, kind.file(OTHER_VALUE), is_generated=True, policy=pinned_policy())

    assert W543 not in codes(followed)
    assert W543 in codes(inherited)
    assert W543 in codes(other)


def test_a_generated_codex_file_with_no_model_key_differs_from_a_pin() -> None:
    """AC-4/R9. expected_behavior_source: R9 ("an absent key means 'no model value'", compared with
    the pinned route name)."""
    result = drift(KINDS[2], KINDS[2].file(), is_generated=True, policy=pinned_policy())

    assert W543 in codes(result)


@pytest.mark.parametrize("kind", KINDS[:4], ids=lambda kind: kind.label)
def test_orq_w543_says_only_whether_the_policy_pins_a_model_and_never_the_route_name(
    kind: Kind,
) -> None:
    """AC-4/AC-5/R11. expected_behavior_source: R11 ("For W543 the finding says only whether the
    policy pins a model for this file or pins none; it never prints the expected route name").
    The `.agents/skills` kind is left out: the skill pin of `pinned_policy` is for Claude Code
    only, so nothing is pinned for that folder."""
    value = kind.file(OTHER_VALUE)
    pinned = only(drift(kind, value, is_generated=True, policy=pinned_policy()), W543)
    none = only(drift(kind, value, is_generated=True, policy=plain_policy()), W543)

    assert pinned.message != none.message
    assert "example-a" not in pinned.message
    assert "example-a" not in (pinned.path or "")


@pytest.mark.parametrize("other", ["a-user-row", "another-path", "no-lock", "invalid-lock"])
def test_a_file_that_the_lock_does_not_record_as_generated_is_team_authored(other: str) -> None:
    """AC-4/R9. expected_behavior_source: R9 ("A file is 'generated' when the lock lists its path
    with owner `orqlet`; every other file (including every file when the lock is missing or
    invalid) is team-authored")."""
    kind = KINDS[0]
    path = kind.path()
    locks: dict[str, Sequence[Doc] | bytes | None] = {
        "a-user-row": [team_row(path)],
        "another-path": [generated(kind.path("someone-else"))],
        "no-lock": None,
        "invalid-lock": b"files: not-a-list\n",
    }
    tree = project(plain_policy(), lock=locks[other], files={path: kind.file(OTHER_VALUE)})

    result = run(tree)

    assert result.findings == ()


@pytest.mark.parametrize("enabled", [(CLAUDE,), (CODEX, CURSOR), (CLAUDE, CODEX, CURSOR)])
def test_a_file_of_a_client_that_is_not_enabled_is_never_compared(enabled: tuple[str, ...]) -> None:
    """AC-4/R6/R9. expected_behavior_source: R9 ("A file of a client that is not enabled is never
    compared (no W543) but is still tested for the exclusion"); R6 (the enabled clients of the
    profile)."""
    clients = {KINDS[0]: CLAUDE, KINDS[1]: CURSOR, KINDS[2]: CODEX}
    files = {kind.path(): kind.file(OTHER_VALUE) for kind in clients}
    lock = [generated(kind.path()) for kind in clients]
    tree = project(plain_policy(), lock=lock, files=files, enabled=enabled)

    result = run(tree)

    compared = {
        kind.path()
        for kind in clients
        if any(f.code == W543 and names(f, kind.path()) for f in result.findings)
    }
    assert compared == {kind.path() for kind, client in clients.items() if client in enabled}


@EVERY_KIND
def test_an_excluded_value_is_found_even_when_the_client_of_the_file_is_not_enabled(
    kind: Kind,
) -> None:
    """AC-4/R9. expected_behavior_source: R9 ("still tested for the exclusion"); R10."""
    only_codex = (CODEX,) if kind.client != CODEX else (CLAUDE,)

    result = drift(kind, kind.file("blocked-alias"), is_generated=True, enabled=only_codex)

    assert E548 in codes(result)


@EVERY_KIND
def test_a_policy_with_problems_gives_no_orq_w543_and_says_the_files_were_not_compared(
    kind: Kind,
) -> None:
    """AC-4/R5/R9. expected_behavior_source: R9 ("When the policy has problems (R5) or no
    resolution is available, W543 is not produced and a not-run reason says the generated files
    were not compared")."""
    doc = plain_policy(assignments=[assignment_doc("role", "no-such-role", model="example-a")])

    result = drift(kind, kind.file(OTHER_VALUE), is_generated=True, policy=doc)

    assert E545 in codes(result)
    assert W543 not in codes(result)
    assert result.not_run


def test_an_excluded_value_is_still_found_when_the_policy_has_other_problems() -> None:
    """AC-4/R5/R10. expected_behavior_source: R10 (the exclusions of the loaded policy); R9."""
    doc = plain_policy(assignments=[assignment_doc("role", "no-such-role", model="example-a")])

    result = drift(KINDS[0], KINDS[0].file("blocked-alias"), policy=doc)

    assert {E545, E548} <= set(codes(result))


@pytest.mark.parametrize(
    "path",
    [
        ".claude/agents/notes.txt",
        ".claude/agents/README.markdown",
        ".claude/agents/team/nested.md",
        ".claude/agents/agent.toml",
        ".cursor/agents/agent.toml",
        ".codex/agents/agent.md",
        ".claude/commands/command.md",
        ".claude/skills/orqlet-design/other.md",
        ".claude/skills/orqlet-design/skill.md",
        ".agents/skills/orqlet-design/references/SKILL.md",
        ".agents/agents/agent.md",
        "agents/agent.md",
    ],
)
def test_a_file_outside_the_five_kinds_is_not_scanned(path: str) -> None:
    """AC-4/R9. expected_behavior_source: AC-4 (the five kinds of file) and R9 (found by listing
    those folders): any other file is not scanned."""
    content = (
        KINDS[2].file("blocked-alias") if path.endswith(".toml") else KINDS[0].file("blocked-alias")
    )
    tree = project(plain_policy(), files={path: content})

    assert run(tree).findings == ()


def test_the_findings_follow_the_folder_order_and_then_the_file_path() -> None:
    """AC-4/R14. expected_behavior_source: R14 ("the drift findings (by file path, folder order
    `.claude/agents`, `.cursor/agents`, `.codex/agents`, `.claude/skills`, `.agents/skills`)")."""
    claude, cursor, codex, claude_skill, agents_skill = KINDS
    expected = [
        claude.path("a"),
        claude.path("b"),
        cursor.path("a"),
        codex.path("a"),
        claude_skill.path("a"),
        claude_skill.path("b"),
        agents_skill.path("a"),
    ]
    kinds = [claude, claude, cursor, codex, claude_skill, claude_skill, agents_skill]
    files = {path: kind.file("blocked-alias") for path, kind in zip(expected, kinds, strict=True)}
    tree = project(plain_policy(), files=dict(reversed(files.items())))

    found = by_code(run(tree), E548)

    assert [next(p for p in expected if names(f, p)) for f in found] == expected


# AC-4/R12: ORQ-W544 ----------------------------------------------------------------------------


def unusable(kind: Kind, cause: str) -> tuple[Files, str]:
    """A project with one file of `kind` that cannot be used for `cause`, and the path of it."""
    path = kind.path()
    tree = project(plain_policy())
    value = "blocked-alias"
    if cause == "not-utf8":
        put(tree, path, kind.not_utf8())
    elif cause == "unparsable":
        put(tree, path, kind.file(raw="[unclosed"))
    elif cause == "duplicate-key":
        put(tree, path, kind.duplicated(value, "other"))
    elif cause.startswith("not-text-"):
        put(tree, path, kind.file(raw=kind.not_text[int(cause.removeprefix("not-text-"))]))
    elif cause == "above-256-kib":
        put(tree, path, pad(kind.file(value), LIMIT + 1))
    elif cause == "link":
        put(tree, path, kind.file(value))
        tree.add_symlink(path)
    elif cause == "read-error":
        put(tree, path, kind.file(value))
        tree.denied[path] = PermissionError("denied")
    elif cause == "unsafe-read":
        put(tree, path, kind.file(value))
        tree.denied[path] = FileSystemError("refused")
    else:
        raise AssertionError(cause)
    return tree, path


W544_CAUSES = [
    "not-utf8",
    "unparsable",
    "duplicate-key",
    "not-text-0",
    "not-text-1",
    "not-text-2",
    "not-text-3",
    "above-256-kib",
    "link",
    "read-error",
    "unsafe-read",
]


@EVERY_KIND
@pytest.mark.parametrize("cause", W544_CAUSES)
def test_a_team_authored_file_that_cannot_be_used_is_orq_w544_and_is_not_scanned_further(
    kind: Kind, cause: str
) -> None:
    """AC-4/R12. expected_behavior_source: AC-4 ("A team-authored file that cannot be parsed or is
    above 256 KiB is ORQ-W544 and is not scanned further"); R12 (a link, a read error, above 256
    KiB, not valid UTF-8, unparsable front matter or TOML, a `model` that is not text)."""
    tree, path = unusable(kind, cause)

    result = run(tree)

    finding = only(result, W544)
    assert finding.severity is Severity.WARNING
    assert names(finding, path)
    assert E548 not in codes(result)
    assert result.verdict is Verdict.PASS


@EVERY_KIND
@pytest.mark.parametrize(
    "cause", ["unparsable", "not-text-1", "above-256-kib", "link", "read-error"]
)
def test_a_generated_file_that_cannot_be_used_is_orq_w544_and_not_compared(
    kind: Kind, cause: str
) -> None:
    """AC-4/R12. expected_behavior_source: R12 ("for ANY scanned file (generated or
    team-authored)"); R12 (not scanned further, so no E548); the file is not compared."""
    tree, path = unusable(kind, cause)
    put(tree, LOCK, lock_bytes(generated(path)))

    result = run(tree)

    assert len(by_code(result, W544)) == 1
    assert {E548, W543}.isdisjoint(codes(result))


@EVERY_KIND
def test_a_file_of_exactly_256_kib_is_scanned_and_one_byte_more_is_orq_w544(kind: Kind) -> None:
    """AC-4/R12. expected_behavior_source: R12 ("larger than 256 KiB (262144 bytes; exactly 262144
    is allowed, one more byte is W544)")."""
    path = kind.path()
    at_the_limit = project(plain_policy(), files={path: pad(kind.file("blocked-alias"), LIMIT)})
    above = project(plain_policy(), files={path: pad(kind.file("blocked-alias"), LIMIT + 1)})

    scanned = run(at_the_limit)
    refused = run(above)

    assert codes(scanned) == [E548]
    assert codes(refused) == [W544]


@EVERY_KIND
def test_a_file_with_no_model_key_has_no_model_value_and_no_finding(kind: Kind) -> None:
    """AC-4/R9/R12. expected_behavior_source: R9 ("an absent key means 'no model value'"); R12 (only
    a `model` that is present and is not text is ORQ-W544)."""
    assert drift(kind, kind.file()).findings == ()


@pytest.mark.parametrize("kind", [KINDS[0], KINDS[1], KINDS[3], KINDS[4]], ids=lambda k: k.label)
def test_a_markdown_file_with_no_front_matter_has_no_model_value_and_no_finding(kind: Kind) -> None:
    """AC-4/R9. expected_behavior_source: R9 ("a Markdown file with no front matter has no model
    value")."""
    result = drift(kind, b"# An agent\n\nmodel: blocked-alias\n")

    assert result.findings == ()


@EVERY_KIND
def test_only_the_top_level_model_key_is_read(kind: Kind) -> None:
    """AC-4/R9. expected_behavior_source: R9 ("The `model` value is the top-level `model` key")."""
    if kind.toml:
        content = b'name = "x"\n\n[tools]\nmodel = "blocked-alias"\n'
    else:
        content = b"---\nname: x\ntools:\n  model: blocked-alias\n---\n\nBody.\n"

    assert drift(kind, content).findings == ()


@EVERY_KIND
def test_a_folder_entry_that_is_not_a_usable_path_name_is_orq_w544_and_is_shown_escaped(
    kind: Kind,
) -> None:
    """AC-4/R11/R12. expected_behavior_source: R12 ("A folder entry that is not a usable path name
    is also W544"); R11 (the file path, escaped for control characters)."""
    tree = project(plain_policy())
    tree.add_dir(kind.folder)
    tree.add_dir(f"{kind.folder}/{kind.entry('bad' + chr(7) + 'name')}")

    result = run(tree)

    assert len(by_code(result, W544)) == 1
    assert not any(chr(7) in f.message or chr(7) in (f.path or "") for f in result.findings)
    assert result.verdict is Verdict.PASS


# --- AC-4/AC-5/R11: what a drift finding prints ---------------------------------------------------


def test_a_value_that_names_one_catalog_entry_is_printed_as_its_catalog_id() -> None:
    """AC-5/R11. expected_behavior_source: AC-5 ("prints the catalog id that a string matched");
    R11 (`catalog id <id>`, never the value). The file is generated; the value is the Claude Code
    route of `example-b`."""
    result = drift(KINDS[0], KINDS[0].file("example-b-claude-code"), is_generated=True)

    finding = only(result, W543)
    assert "catalog id example-b" in finding.message
    assert "example-b-claude-code" not in finding.message


def test_a_value_that_is_a_known_alternative_name_is_printed_as_its_catalog_id() -> None:
    """AC-5/R11. expected_behavior_source: R11 (`match_entry` matches a route name,
    `also_known_as` and `resolves_to`)."""
    model = entry(
        "example-c",
        route(CLAUDE, "example-c-claude-code", also_known_as=["example-c-latest"]),
    )
    doc = policy_doc([MODEL_A, model], excluded=[BLOCKED])

    result = drift(KINDS[0], KINDS[0].file("example-c-latest"), is_generated=True, policy=doc)

    finding = only(result, W543)
    assert "catalog id example-c" in finding.message
    assert "example-c-latest" not in finding.message


def test_a_value_that_names_no_catalog_entry_is_printed_as_unmatched_with_its_length() -> None:
    """AC-5/R11. expected_behavior_source: AC-5 ("`unmatched` with the string's length, never the
    string"); R11 (`unmatched, <n> characters`)."""
    value = "unknown-model-name"

    finding = only(drift(KINDS[0], KINDS[0].file(value), is_generated=True), W543)

    assert f"unmatched, {len(value)} characters" in finding.message
    assert value not in finding.message
    assert value not in (finding.path or "")


def test_the_word_inherit_is_printed_as_the_fixed_word_when_the_policy_pins_a_model() -> None:
    """AC-5/R11. expected_behavior_source: R11 ("the fixed word `inherit` when the value is exactly
    `inherit`"); the policy pins the tester role, so an `inherit` file differs."""
    finding = only(
        drift(KINDS[0], KINDS[0].file("inherit"), is_generated=True, policy=pinned_policy()), W543
    )

    assert "inherit" in finding.message
    assert "example-a" not in finding.message


@pytest.mark.parametrize("spelling", list(EXCLUDED_VALUES))
def test_orq_e548_prints_the_description_and_never_the_excluded_value(spelling: str) -> None:
    """AC-5/R10/R11. expected_behavior_source: AC-5 ("never the string"); R11."""
    value = EXCLUDED_VALUES[spelling]

    finding = only(drift(KINDS[0], KINDS[0].file(value)), E548)

    assert value not in finding.message
    assert value not in (finding.path or "")
    assert re.search(r"unmatched, \d+ characters|catalog id ", finding.message)


# --- AC-5: a unique marker in every model field never appears in a result -------------------------


def marked(label: str, build: Callable[[str], Doc]) -> tuple[str, Doc]:
    value = marker(label)
    return value, build(value)


MARKER_FIELDS: dict[str, tuple[Callable[[str], Doc], str]] = {
    "route-name": (
        lambda m: (
            with_exclusion(entry("example-c", route(CLAUDE, m)))
            | {"excluded": [exclusion("rule-1", aliases=[m])]}
        ),
        E543,
    ),
    "route-resolves-to": (
        lambda m: (
            with_exclusion(
                entry("example-c", route(CLAUDE, "example-c-alias", kind="alias", resolves_to=m))
            )
            | {"excluded": [exclusion("rule-1", id_patterns=[m])]}
        ),
        E543,
    ),
    "route-also-known-as": (
        lambda m: (
            with_exclusion(
                entry("example-c", route(CLAUDE, "example-c-claude-code", also_known_as=[m]))
            )
            | {"excluded": [exclusion("rule-1", family_tags=[m])]}
        ),
        E543,
    ),
    "exclusion-alias": (
        lambda m: (
            with_exclusion(entry("example-c", family=m))
            | {"excluded": [exclusion("rule-1", aliases=[m])]}
        ),
        E543,
    ),
    "exclusion-id-pattern": (
        lambda m: (
            with_exclusion(entry("example-c", route(CLAUDE, f"{m}-x")))
            | {"excluded": [exclusion("rule-1", id_patterns=[f"{m}*"])]}
        ),
        E543,
    ),
    "exclusion-family-tag": (
        lambda m: (
            with_exclusion(entry("example-c", family=f"{m}-family"))
            | {"excluded": [exclusion("rule-1", family_tags=[m])]}
        ),
        E543,
    ),
    "profile-candidates": (
        lambda m: policy_doc([MODEL_A], profiles=[candidates_of(m)]),
        E545,
    ),
    "profile-fallbacks": (
        lambda m: policy_doc([MODEL_A], profiles=[candidates_of(m, fallbacks=True)]),
        E545,
    ),
    "assignment-model": (
        lambda m: policy_doc([MODEL_A], [assignment_doc("role", TESTER, model=m)]),
        E545,
    ),
    "approval-ref": (
        lambda m: policy_doc([entry("example-a", *routes_of("example-a"), approval_ref=m)]),
        E546,
    ),
}


@pytest.mark.parametrize("field", list(MARKER_FIELDS))
def test_a_marker_in_one_model_field_of_the_policy_never_appears_in_the_result(field: str) -> None:
    """AC-5/R3. expected_behavior_source: AC-5 ("a unique marker placed in each model field of the
    policy ... never appears in the text or the data of the result"); R3 (field paths and fixed
    words are the only content). The finding of the expected code proves the field is in play."""
    build, code = MARKER_FIELDS[field]
    value, doc = marked(field, build)
    policy = ModelPolicy.model_validate(doc)
    if code in {E543, E545}:  # the premise, before the command is called
        assert code in {problem.code for problem in policy_problems(policy, ROLES, SKILLS)}

    result = run(project(doc))

    assert code in codes(result)
    assert not leaked(shown(result), value)


def test_a_marker_in_the_excluded_id_of_the_base_policy_never_appears_in_the_result() -> None:
    """AC-5/R2. expected_behavior_source: AC-5; R2 ("A finding of E544 names positions in the base
    policy like `excluded[1]`, never an id"). Base: BASE, which holds the policy with the marker."""
    values = {
        label: marker(label)
        for label in (
            "base-id",
            "base-alias",
            "base-pattern",
            "base-tag",
            "base-reason",
            "base-source",
        )
    }
    removed = exclusion(
        values["base-id"],
        aliases=[values["base-alias"]],
        id_patterns=[values["base-pattern"] + "*"],
        family_tags=[values["base-tag"]],
        reason=values["base-reason"],
        source=values["base-source"],
    )
    at_base = {POLICY: raw_of(plain_policy(excluded=[BLOCKED, removed]))}

    result = run(project(plain_policy()), at_base=at_base)

    assert paths_in(only(result, E544)) == ["excluded[1]"]
    for value in values.values():
        assert not leaked(shown(result), value)


def kitchen_sink() -> tuple[ValidationResult, list[str]]:
    """A marker in every model field of the policy and of the files, and a finding of each kind."""
    m = {
        label: marker(label)
        for label in (
            "alias",
            "pattern",
            "tag",
            "resolves",
            "candidate",
            "fallback",
            "assignment",
            "approver",
            "ref",
            "reason",
            "source",
            "rule",
            "base-id",
            "base-alias",
            "file-value",
            "file-excluded",
            "file-bracket",
            "file-key",
        )
    }
    base_rule = exclusion(m["base-id"], aliases=[m["base-alias"]])
    rule = exclusion(
        m["rule"],
        aliases=[m["alias"], m["file-excluded"]],
        id_patterns=[m["pattern"] + "*"],
        family_tags=[m["tag"]],
        reason=m["reason"],
        source=m["source"],
    )
    models = [
        MODEL_A,
        entry(
            "example-c",
            route(CLAUDE, m["alias"], retires_on="2026-10-01"),
            route(CODEX, "example-c-codex", also_known_as=[m["pattern"] + "-x"]),
            route(CURSOR, "example-c-cursor-alias", kind="alias", resolves_to=m["resolves"]),
            family=m["tag"] + "-family",
            approved_by=m["approver"],
            approval_ref=m["ref"],
        ),
    ]
    profiles = [
        profile_doc("quality", candidates=[m["candidate"]], fallbacks=[m["fallback"]]),
    ]
    assignments = [assignment_doc("role", TESTER, model=m["assignment"])]
    doc = policy_doc(models, assignments, profiles=profiles, excluded=[rule], reviewed="0.3.0")
    problems = policy_problems(ModelPolicy.model_validate(doc), ROLES, SKILLS)
    assert {E543, E545} <= {problem.code for problem in problems}  # the premise
    files = {
        KINDS[0].path("one"): KINDS[0].file(m["file-excluded"]),
        KINDS[1].path("two"): KINDS[1].file(m["file-bracket"] + "[effort=high]"),
        KINDS[2].path("three"): KINDS[2].duplicated(m["file-value"], m["file-key"]),
        KINDS[3].path("four"): KINDS[3].file(raw=f"[{m['file-value']}, {m['file-key']}]"),
        KINDS[4].path("five"): KINDS[4].file(m["file-value"] * 12),
    }
    at_base = {POLICY: raw_of(plain_policy(excluded=[base_rule, rule]))}
    tree = project(doc, files=files, lock=[generated(path) for path in files])
    result = run(tree, at_base=at_base)
    return result, list(m.values())


def test_a_marker_in_every_model_field_never_appears_in_any_finding_reason_or_datum() -> None:
    """AC-5. expected_behavior_source: AC-5 ("for every finding of this command, a unique marker
    placed in each model field of the policy and of the agent files never appears in the text or
    the data of the result"). The policy has findings of the codes ORQ-E543, ORQ-E545, ORQ-E546,
    ORQ-E544, ORQ-W541 and ORQ-W542 and the files have ORQ-E548 and ORQ-W544. Base: BASE."""
    result, values = kitchen_sink()

    assert {E543, E544, E545, E546, W541, W542, E548, W544} <= set(codes(result))
    for value in values:
        assert not leaked(shown(result), value), value


MARKED_FILES: dict[str, Callable[[Kind, str], bytes]] = {
    "excluded-value": lambda kind, m: kind.file(m),
    "excluded-bracketed-value": lambda kind, m: kind.file(f"{m}[effort=high]"),
    "differing-value": lambda kind, m: kind.file(m),
    "non-ascii-value": lambda kind, m: kind.file(m + "\u00e9"),
    "long-value": lambda kind, m: kind.file(m * 12),
    "duplicate-key": lambda kind, m: kind.duplicated(m, m + "-2"),
    "not-text": lambda kind, m: kind.file(
        raw=f'["{m}", "{m}-2"]' if kind.toml else f"[{m}, {m}-2]"
    ),
}


@EVERY_KIND
@pytest.mark.parametrize("case", list(MARKED_FILES))
def test_a_marker_in_the_model_value_of_a_file_never_appears_in_the_result(
    kind: Kind, case: str
) -> None:
    """AC-5/R11. expected_behavior_source: AC-5 ("a unique marker placed in each model field of
    ... the agent files never appears in the text or the data of the result"); R11 (a description
    of the value, never the value). The policy excludes the marker for the `excluded-*` cases."""
    value = marker(f"{kind.label}-{case}")
    excluded = case.startswith("excluded")
    doc = plain_policy(excluded=[exclusion("rule-1", aliases=[value])]) if excluded else None
    expected = {
        "excluded-value": E548,
        "excluded-bracketed-value": E548,
        "differing-value": W543,
        "non-ascii-value": W543,
        "long-value": W543,
        "duplicate-key": W544,
        "not-text": W544,
    }[case]

    result = drift(kind, MARKED_FILES[case](kind, value), is_generated=True, policy=doc)

    assert expected in codes(result)
    assert not leaked(shown(result), value)


# --- AC-5/AC-1: PATH (R13) ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw", ["", "/etc/orqlet-policy.yaml", "../outside.yaml", "a/../b.yaml", "a//b.yaml"]
)
def test_an_unusable_path_is_one_orq_e320_and_fail(raw: str) -> None:
    """R13. expected_behavior_source: R13 ("An unusable PATH (absolute, `..`, empty) gives one
    ORQ-E320 error and FAIL")."""
    result = run(project(plain_policy()), path=raw)

    assert codes(result) == [E320]
    assert result.verdict is Verdict.FAIL
    assert result.findings[0].severity is Severity.ERROR


def test_a_custom_path_is_checked_and_needs_no_located_base() -> None:
    """R13. expected_behavior_source: R13 (the base rules are then NOT applied and not reported as
    not run). The repository has no commit, and the file is sound."""
    result = run(
        project(files={OTHER: raw_of(plain_policy())}),
        path=OTHER,
        vcs=WatchedVcs(RepoState.UNBORN_EMPTY),
    )

    assert result.verdict is Verdict.PASS
    assert result.not_run == ()


def test_a_custom_path_gets_the_same_checks_with_that_path_on_the_findings() -> None:
    """R13/AC-2. expected_behavior_source: R13 ("the same findings, with that PATH as
    `Finding.path`"). The file excludes a model and names an unknown role."""
    doc = policy_doc(
        [MODEL_A, entry("blocked-model-1")],
        [assignment_doc("role", "no-such-role", model="example-a")],
        excluded=[BLOCKED],
    )

    result = run(project(files={OTHER: raw_of(doc)}), path=OTHER)

    assert {E543, E545} <= set(codes(result))
    assert all(f.path == OTHER for f in by_code(result, E543) + by_code(result, E545))


def test_a_custom_path_does_not_apply_the_base_rules() -> None:
    """R13. expected_behavior_source: R13 ("the deletion rule and the base rules (E544, and E547
    through the base tree) are then NOT applied"). Base: BASE, which holds the default policy with
    a rule that the custom file lacks."""
    at_base = {POLICY: raw_of(rules("a", "b"))}

    result = run(project(files={OTHER: raw_of(rules("a"))}), path=OTHER, at_base=at_base)

    assert E544 not in codes(result)
    assert result.verdict is Verdict.PASS


def test_a_custom_path_that_is_missing_is_never_present_not_a_deletion() -> None:
    """R13/R1. expected_behavior_source: R13 (the deletion rule is not applied to a custom PATH).
    The lock records the default policy as seeded, and the base holds it."""
    result = run(project(lock=[SEEDED]), path=OTHER, at_base={POLICY: raw_of(plain_policy())})

    assert E547 not in codes(result)
    assert result.verdict is Verdict.NOT_RUN


# --- R14: the order of the findings -----------------------------------------------------------


def test_the_findings_of_a_policy_with_problems_follow_the_order_of_the_readings() -> None:
    """R14. expected_behavior_source: R14 ("loader/state findings, then E543, E545, E546, E544, then
    W540, W541, W542, then the drift findings"). Problems exist, so no ORQ-W540 and no ORQ-W543."""
    result = play(everything_wrong())

    assert codes(result) == [E543, E545, E546, E544, W541, W542, E548, W544]
    assert result.not_run  # the generated file was not compared


def test_the_findings_of_a_sound_policy_with_warnings_follow_the_order_of_the_readings() -> None:
    """R14. expected_behavior_source: R14 (W540, W541, W542, then the drift findings by folder and
    file path). The generated Cursor file follows the unmatched team file of `.claude/agents`."""
    result = play(warnings_only())

    assert codes(result) == [W540, W540, W541, W542, E548, W543, W544]
    assert result.verdict is Verdict.FAIL


# --- worst cases: the size limit and many files -------------------------------------------------


def largest_within_the_limit(build: Callable[[int], Doc]) -> bytes:
    """The compact JSON of `build(n)` for the largest `n` whose file is not above 256 KiB."""
    low, high = 1, 2
    while len(compact(build(high))) <= LIMIT:
        low, high = high, high * 2
    while high - low > 1:
        middle = (low + high) // 2
        if len(compact(build(middle))) <= LIMIT:
            low = middle
        else:
            high = middle
    return compact(build(low))


UNKNOWN_ROLES = 400
MODELS_AT_THE_LIMIT = 150


def faulty_to_the_limit(count: int) -> Doc:
    """Many models, three long profiles and unknown roles; `count` exclusions fill the file."""
    ids = [f"m-{i}" for i in range(MODELS_AT_THE_LIMIT)]
    models = [entry(i, *routes_of(i)) for i in ids]
    profiles = [profile_doc(p, candidates=ids, fallbacks=ids) for p in PROFILE_IDS]
    assignments = [
        assignment_doc("role", f"no-role-{i}", model="m-0") for i in range(UNKNOWN_ROLES)
    ]
    excluded = [
        exclusion(f"rule-{i}", aliases=[f"alias-{i}"], reason="r" * 380) for i in range(count)
    ]
    return policy_doc(models, assignments, profiles=profiles, excluded=excluded)


def sound_to_the_limit(count: int) -> Doc:
    """`count` models and three profiles that list all of them for each client."""
    ids = [f"m-{i}" for i in range(count)]
    models = [entry(i, *routes_of(i)) for i in ids]
    profiles = [profile_doc(p, candidates=ids, fallbacks=ids) for p in PROFILE_IDS]
    return policy_doc(
        models, [assignment_doc("role", TESTER, profile="quality")], profiles=profiles
    )


def test_a_policy_at_the_size_limit_with_many_problems_is_checked_in_one_pass() -> None:
    """AC-2/R3. expected_behavior_source: AC-2 and R3 ("at most 20 field paths ... and then `and N
    more`": a file at the size limit can hold one problem for each of thousands of entries); the
    plan objective (a worst-case file is checked). The bound is far above any plausible time."""
    raw = largest_within_the_limit(faulty_to_the_limit)
    assert LIMIT // 2 < len(raw) <= LIMIT
    ModelPolicy.model_validate(LOADER.load(raw, source=POLICY))  # the premise: the file is valid

    started = time.monotonic()
    result = run(project(raw))
    elapsed = time.monotonic() - started

    finding = only(result, E545)
    assert paths_in(finding) == [f"assignments[{i}].target.name" for i in range(20)]
    assert more_in(finding) == UNKNOWN_ROLES - 20
    assert result.verdict is Verdict.FAIL
    assert elapsed < 30


def test_a_sound_policy_at_the_size_limit_passes() -> None:
    """AC-2/AC-3. expected_behavior_source: the plan objective ("a worst-case policy at the 256 KiB
    cap (many models and profiles) finishes in a few seconds"); AC-2. Base: BASE."""
    raw = largest_within_the_limit(sound_to_the_limit)
    assert LIMIT // 2 < len(raw) <= LIMIT
    ModelPolicy.model_validate(LOADER.load(raw, source=POLICY))

    started = time.monotonic()
    result = run(project(raw))
    elapsed = time.monotonic() - started

    assert result.errors == ()
    assert result.verdict is Verdict.PASS
    assert elapsed < 30


def test_hundreds_of_small_files_are_scanned_in_one_pass() -> None:
    """AC-4/R9. expected_behavior_source: the plan objective (a folder with several hundred small
    agent files is scanned); R9 (found by listing the folders): each folder is listed once and each
    file is read once. The bound is far above any plausible time."""
    count = 300
    claude, cursor, _codex, claude_skill, _agents_skill = KINDS
    names_ = [f"agent-{i:03}" for i in range(count)]
    files = {claude.path(n): claude.file("blocked-alias") for n in names_}
    files |= {cursor.path(n): cursor.file(OTHER_VALUE) for n in names_}
    files |= {claude_skill.path(n): claude_skill.file("blocked-alias") for n in names_}
    lock = [generated(cursor.path(n)) for n in names_]
    tree = project(plain_policy(), lock=lock, files=files)

    started = time.monotonic()
    result = run(tree)
    elapsed = time.monotonic() - started

    assert len(by_code(result, E548)) == 2 * count
    assert len(by_code(result, W543)) == count
    assert max(Counter(tree.listed).values()) == 1
    assert max(Counter(p for p in tree.reads if p in files).values()) == 1
    assert elapsed < 30


def test_a_failing_version_control_read_of_the_base_never_raises() -> None:
    """AC-2/R2. expected_behavior_source: interface item 1 ("never raises for a bad file"); R2 ("A
    base policy that cannot be loaded ... a not-run reason is added"). Base: BASE, whose read
    fails."""

    class FailingRead(WatchedVcs):
        def read_at(self, revision: str, path: str) -> bytes | None:
            raise VcsError("the object cannot be read")

    vcs = FailingRead(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(HEAD, "head"),),
        revisions={BASE: {}},
        merge_bases={(HEAD, BASE): (BASE,)},
    )

    result = run(project(plain_policy()), vcs=vcs)

    assert result.verdict is Verdict.NOT_RUN
    assert result.not_run


# --- readings that the coder of P-7 chose and the tester left open ----------------------------
# These four tests were added by the coder, after the code, for the readings in the report. The
# tester's tests above do not pin them.


@pytest.mark.parametrize("kind", [KINDS[0], KINDS[1], KINDS[3], KINDS[4]], ids=lambda k: k.label)
def test_a_model_key_that_is_present_and_empty_is_orq_w544_and_not_a_missing_key(
    kind: Kind,
) -> None:
    """AC-4/R12. expected_behavior_source: R12 ("a `model` that is present and is not text"); an
    empty value is `null`, which is not text. TOML has no null, so its kind is left out."""
    result = drift(kind, kind.file(raw="null"))

    assert codes(result) == [W544]
    assert result.verdict is Verdict.PASS


def test_a_skill_folder_that_is_a_link_is_orq_w544_and_not_followed() -> None:
    """AC-4/R12. expected_behavior_source: R12 ("a link"); the port does not follow a link, so a
    skill folder that is one cannot be scanned and says so. The file inside is never read."""
    kind = KINDS[3]
    tree = project(plain_policy(), files={kind.path(): kind.file("blocked-alias")})
    tree.add_symlink(f"{kind.folder}/{kind.name}")

    result = run(tree)

    assert codes(result) == [W544]
    assert kind.path() not in tree.reads


def test_a_file_that_lies_beside_the_skill_folders_is_not_a_skill_and_gives_nothing() -> None:
    """AC-4/R9. expected_behavior_source: R9 (a skill is `<folder>/<name>/SKILL.md`); a file in the
    folder of skills is no skill folder, so it is not read and is no finding."""
    kind = KINDS[3]
    tree = project(plain_policy(), files={f"{kind.folder}/README.md": b"model: blocked-alias\n"})

    result = run(tree)

    assert result.findings == ()
    assert f"{kind.folder}/README.md" not in tree.reads


def test_a_workflow_whose_roles_cannot_be_read_skips_the_references_and_still_checks_the_rest() -> (
    None
):
    """AC-2/R5. expected_behavior_source: interface item 1 ("never raises"); R5 (the names are those
    of the packaged workflow: when they cannot be read, the references cannot be checked, and the
    run says so instead of passing)."""

    class BrokenWorkflow:
        release = WORKFLOW.release

        def paths(self) -> tuple[str, ...]:
            return ("roles/broken.md",)

        def read_text(self, path: str) -> str:
            return "no front matter here"

        def problems(self) -> tuple[str, ...]:
            return ()

    doc = plain_policy(
        models=[MODEL_A, entry("example-c", *routes_of("example-c"), approved_by=None)]
    )

    result = run(project(doc), workflow=BrokenWorkflow())

    assert result.verdict is Verdict.FAIL
    assert codes(result) == [E546]  # the approval is still checked
    assert result.not_run
