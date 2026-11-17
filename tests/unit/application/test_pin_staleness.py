"""The review records that a changed agent file makes stale (dynamic-model-profiles, P-6, AC-4).

It covers `orqlet.application.usecases.pin_staleness`: `stale_review_records`, which reads the
review records through the file system port and names the ones that a change plan makes stale, and
`stale_review_finding`, which turns a list of paths into the warning ORQ-W547.

Every test cites its `expected_behavior_source`. AC-4 is an acceptance criterion of phase P-6 in
docs/design/dynamic-model-profiles/plan.yaml. BC-n and F-n are the behaviour and failure rows of
design/component.md, C-8 its constraint, and ADR-3 decision 7 the decision record about a pin that
changes protected files. "The interface" is the interface that the Coder of this phase implements
and that the brief of this phase's Tester states, item 7: `STALE_REVIEW`, `MAX_LISTED`,
`stale_review_records(project, loader, writes)` and `stale_review_finding(paths)`.

These tests were written first, by the Tester of phase P-6, before the module existed. Records are
built in code from the valid fixture of the review result
(tests/fixtures/contracts/valid/orqlet.review-result.v1.yaml), with the task, role, phase and round
set to what the path says, and are written as JSON text, which is YAML. The file system is the
in-memory fake and two small subclasses of it in this file, which fail on purpose (tests/fakes is
not changed). No credential-shaped text is used.

Behaviour that the plan and the brief leave open is deliberately not pinned here:
- the wording of the warning: only its code, its severity, the paths it lists, the form `and N
  more` and a few key words are pinned (`protected_set_digest`, ORQ-W390, "pin", "person");
- whether the warning carries a `path` of its own;
- a record whose content names a task, role, phase or round that its path does not (every record
  here is consistent with its path);
- how a record whose `binding_ref` is no agent name is treated beyond "never raises, never stale".
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator, Sequence
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.ports.filesystem import (
    FileKind,
    FileSystemError,
    NotARegularFile,
    PathNotFound,
)
from orqlet.application.usecases.pin_staleness import (
    MAX_LISTED,
    STALE_REVIEW,
    stale_review_finding,
    stale_review_records,
)
from orqlet.domain.changeplan import PlannedWrite, proposal_path
from orqlet.domain.evidence_artifacts import MAX_EVIDENCE_BYTES
from orqlet.domain.findings import Severity
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.unit

CLAUDE = "claude-code"
CURSOR = "cursor"
CODEX = "codex"
ARCH = "orqlet-arch-reviewer"
SECURITY = "orqlet-security-reviewer"
FIXTURE = FIXTURES / "contracts" / "valid" / "orqlet.review-result.v1.yaml"
LOADER = StrictYamlLoader()
AGENT_PATH = {
    CLAUDE: ".claude/agents/{}.md",
    CURSOR: ".cursor/agents/{}.md",
    CODEX: ".codex/agents/{}.toml",
}
CLIENTS = (CLAUDE, CURSOR, CODEX)
MORE = re.compile(r"and (\d+) more")


# --- records and writes built in code ----------------------------------------------------


def base_record() -> dict[str, Any]:
    data = LOADER.load(FIXTURE.read_bytes(), source="fixture")
    assert isinstance(data, dict)
    return data


def record_data(
    *,
    task: str = "demo",
    role: str = "architecture-reviewer",
    phase: str = "P-1",
    round_no: int = 1,
    client: str = CLAUDE,
    ref: str = ARCH,
) -> dict[str, Any]:
    """The valid fixture record with the identity that a record path states and the given agent."""
    data = copy.deepcopy(base_record())
    data["task"] = task
    data["role"] = role
    data["phase"] = phase
    data["round"] = round_no
    data["agent"]["client"] = client
    data["agent"]["binding_ref"] = ref
    return data


def record_path(
    *,
    task: str = "demo",
    role: str = "architecture-reviewer",
    phase: str = "P-1",
    round_no: int = 1,
) -> str:
    return f"docs/design/{task}/reviews/{role}-{phase}-r{round_no}.yaml"


def document(data: dict[str, Any]) -> bytes:
    return json.dumps(data, indent=2).encode()


def put(project: MemoryFileSystem, path: str, content: bytes) -> None:
    project.write_atomic(CanonicalPath.parse(path), content)


def add_record(
    project: MemoryFileSystem,
    *,
    task: str = "demo",
    role: str = "architecture-reviewer",
    phase: str = "P-1",
    round_no: int = 1,
    client: str = CLAUDE,
    ref: str = ARCH,
) -> str:
    """Write a valid review record into the project and return its path."""
    path = record_path(task=task, role=role, phase=phase, round_no=round_no)
    data = record_data(task=task, role=role, phase=phase, round_no=round_no, client=client, ref=ref)
    put(project, path, document(data))
    return path


def write_of(path: str, kind: str = "update", *, proposal: bool = False) -> PlannedWrite:
    """One planned write of the given kind (`create`, `update` or `delete`) for `path`."""
    return PlannedWrite(
        path=CanonicalPath.parse(path),
        kind=kind,
        before_sha256=None if kind == "create" else "0" * 64,
        after_sha256=None if kind == "delete" else "1" * 64,
        content=None if kind == "delete" else b"changed\n",
        is_proposal=proposal,
    )


def stale(project: MemoryFileSystem, *writes: PlannedWrite) -> tuple[str, ...]:
    return stale_review_records(project, LOADER, writes)


class BrokenFiles(MemoryFileSystem):
    """A memory file system where some listed files report another kind or fail to be read."""

    def __init__(self) -> None:
        super().__init__()
        self.kinds: dict[str, FileKind] = {}
        self.read_errors: dict[str, Exception] = {}

    def kind(self, path: CanonicalPath) -> FileKind | None:
        forced = self.kinds.get(str(path))
        return forced if forced is not None else super().kind(path)

    def read_bytes(self, path: CanonicalPath) -> bytes:
        error = self.read_errors.get(str(path))
        if error is not None:
            raise error
        return super().read_bytes(path)


def padded(data: bytes, size: int) -> bytes:
    """The document with YAML comment lines appended, so that it is exactly `size` bytes."""
    filler = size - len(data) - len(b"\n#\n")
    assert filler >= 0
    return data + b"\n#" + b"x" * filler + b"\n"


# --- the premise ---------------------------------------------------------------------------


def test_the_records_of_these_tests_are_valid_review_results() -> None:
    """A control, not a rule: every record below is the valid fixture with an identity and an agent
    set, so a record that is skipped below is skipped for the fault that the test puts in it.
    """
    for client in CLIENTS:
        data = record_data(client=client, ref=SECURITY, role="security-reviewer", round_no=3)
        assert ReviewResult.model_validate(data).agent.client == client


def test_the_constants_are_the_ones_of_the_interface() -> None:
    """expected_behavior_source: plan P-6 AC-4 (ORQ-W547, at most 20 paths); the interface item 7
    (`STALE_REVIEW = "ORQ-W547"`, `MAX_LISTED = 20`).
    """
    assert STALE_REVIEW == "ORQ-W547"
    assert MAX_LISTED == 20


# --- stale_review_records: which record is stale ----------------------------------------------


@pytest.mark.parametrize("kind", ["create", "update", "delete"])
@pytest.mark.parametrize("client", CLIENTS)
def test_a_record_is_stale_when_a_write_changes_the_agent_file_it_names(
    client: str, kind: str
) -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("when the plan changes the bytes of an agent
    file that an earlier review record names (`agent.binding_ref` and `agent.client`)"); BC-37;
    F-12; the interface item 7 (a create, an update or a delete that is no proposal, on the path
    that `AGENT_FILES` gives for the client and the binding reference). The files are
    `.claude/agents/<ref>.md`, `.cursor/agents/<ref>.md` and `.codex/agents/<ref>.toml`.
    """
    project = MemoryFileSystem()
    path = add_record(project, client=client, ref=ARCH)

    result = stale(project, write_of(AGENT_PATH[client].format(ARCH), kind))

    assert result == (path,)


def test_a_record_of_the_security_reviewer_is_stale_for_its_own_agent_file() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 (the agent file is the one that
    `agent.binding_ref` names, so two reviewers have two files); the interface item 7.
    """
    project = MemoryFileSystem()
    arch = add_record(project, ref=ARCH)
    security = add_record(project, role="security-reviewer", ref=SECURITY)

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(SECURITY))) == (security,)
    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (arch,)
    assert stale(
        project,
        write_of(AGENT_PATH[CLAUDE].format(ARCH)),
        write_of(AGENT_PATH[CLAUDE].format(SECURITY)),
    ) == tuple(sorted((arch, security)))


def test_a_proposal_changes_no_protected_bytes() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("changes the bytes of an agent file"); the
    interface item 7 ("a proposal ... makes none stale"): a proposal is a file under
    `.orqlet/proposals` and the agent file stays as it is. A write that is marked as a proposal
    does not count even when its path is the agent file.
    """
    project = MemoryFileSystem()
    add_record(project, client=CLAUDE, ref=ARCH)
    agent = CanonicalPath.parse(AGENT_PATH[CLAUDE].format(ARCH))

    assert stale(project, write_of(str(proposal_path(agent, None)), "create", proposal=True)) == ()
    assert stale(project, write_of(str(agent), "update", proposal=True)) == ()


@pytest.mark.parametrize(
    "other",
    [
        pytest.param(".claude/agents/orqlet-tester.md", id="another-role-of-the-same-client"),
        pytest.param(".cursor/agents/orqlet-arch-reviewer.md", id="the-same-agent-for-cursor"),
        pytest.param(".codex/agents/orqlet-arch-reviewer.toml", id="the-same-agent-for-codex"),
        pytest.param(".claude/agents/orqlet-arch-reviewer.toml", id="the-wrong-extension"),
        pytest.param(".claude/agents/orqlet-arch-reviewer.md.bak", id="a-longer-name"),
        pytest.param(".claude/agents/orqlet-arch-reviewer-2.md", id="a-similar-name"),
        pytest.param(".claude/skills/orqlet-review/SKILL.md", id="a-skill-file"),
        pytest.param(".orqlet/role-bindings.yaml", id="the-bindings-file"),
        pytest.param(".orqlet/generated.lock.yaml", id="the-lock"),
    ],
)
def test_a_write_to_any_other_path_makes_no_record_stale(other: str) -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 (only an agent file that a record names);
    the interface item 7 ("any other path ... makes none stale"). The record names the Claude Code
    file of `orqlet-arch-reviewer`.
    """
    project = MemoryFileSystem()
    add_record(project, client=CLAUDE, ref=ARCH)

    assert stale(project, write_of(other)) == ()


def test_a_record_is_listed_once_and_the_list_is_sorted() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("the path of each such record"); the
    interface item 7 ("returns the sorted record paths"). The records are written in an order
    that is not the sorted one, over two tasks, and two writes match the same record's agent.
    """
    project = MemoryFileSystem()
    paths = [
        add_record(project, task="zeta", round_no=2),
        add_record(project, task="alpha", role="security-reviewer", ref=SECURITY, round_no=10),
        add_record(project, task="alpha", round_no=2),
        add_record(project, task="alpha", round_no=1),
        add_record(project, task="alpha", client=CURSOR, round_no=3),
    ]
    writes = (
        write_of(AGENT_PATH[CLAUDE].format(ARCH)),
        write_of(AGENT_PATH[CLAUDE].format(SECURITY)),
        write_of(AGENT_PATH[CURSOR].format(ARCH)),
    )

    assert stale(project, *writes) == tuple(sorted(paths))


def test_the_writes_may_be_a_one_pass_iterable() -> None:
    """AC-4. expected_behavior_source: the interface item 7 (`writes: Iterable[PlannedWrite]`):
    an iterable that can be read once gives the same answer for two records as a tuple does.
    """
    project = MemoryFileSystem()
    first = add_record(project, round_no=1)
    second = add_record(project, round_no=2)
    writes = iter([write_of(AGENT_PATH[CLAUDE].format(ARCH))])

    assert stale_review_records(project, LOADER, writes) == (first, second)


def test_every_stale_record_is_returned_and_only_the_finding_is_limited() -> None:
    """AC-4. expected_behavior_source: the interface item 7 (`stale_review_records` returns the
    sorted paths; the cap of 20 belongs to `stale_review_finding`).
    """
    project = MemoryFileSystem()
    paths = [add_record(project, round_no=n) for n in range(1, MAX_LISTED + 6)]

    result = stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH)))

    assert result == tuple(sorted(paths))
    assert len(result) == MAX_LISTED + 5


def test_a_project_without_records_and_a_plan_without_writes_give_nothing() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 (a path for each record that exists); the
    interface item 7 (reads through the port, never raises): no `docs/design` directory is a
    normal project.
    """
    project = MemoryFileSystem()
    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == ()

    add_record(project)
    assert stale(project) == ()


# --- stale_review_records: which files are read ------------------------------------------------


def test_only_files_that_are_review_record_paths_are_read() -> None:
    """AC-4. expected_behavior_source: the interface item 7 ("every
    `docs/design/<task>/reviews/<file>.yaml` that `parse_evidence_path` accepts as a REVIEW
    record"). Each of these files holds a valid record of the Claude Code agent whose file is
    written, and none of them is listed; the one record at the right path is.
    """
    project = MemoryFileSystem()
    body = document(record_data())
    good = add_record(project, task="right")
    for path in (
        "docs/design/demo/reviews/notes.yaml",
        "docs/design/demo/reviews/architecture-reviewer-P-1-r1.yml",
        "docs/design/demo/reviews/architecture-reviewer-P-1-r0.yaml",
        "docs/design/demo/reviews/architecture-reviewer-P-0-r1.yaml",
        "docs/design/demo/reviews/architecture-reviewer-P-1-r1.yaml.bak",
        "docs/design/demo/tests/P-1.yaml",
        "docs/design/demo/architecture-reviewer-P-1-r1.yaml",
        "docs/design/demo/extra/reviews/architecture-reviewer-P-1-r1.yaml",
        "docs/other/demo/reviews/architecture-reviewer-P-1-r1.yaml",
        "docs/design/Demo/reviews/architecture-reviewer-P-1-r1.yaml",
        "reviews/architecture-reviewer-P-1-r1.yaml",
    ):
        put(project, path, body)

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (good,)


def test_a_binding_ref_that_is_no_agent_name_is_never_stale_and_never_raises() -> None:
    """AC-4. expected_behavior_source: the interface item 7 (a record is stale only when a write
    has the path that the client and the binding reference give; reads nothing but the port). A
    reference that is no file name gives no path that any write can have. The scan goes on to the
    record that is stale. Not stated by the plan: how such a path is built is the implementation's.
    """
    project = MemoryFileSystem()
    good = add_record(project, round_no=1)
    for number, ref in enumerate(
        ("../../orqlet-arch-reviewer", "a/b", "{ref}", "x" * 300, "..", "\x00"), start=2
    ):
        add_record(project, round_no=number, ref=ref)

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (good,)


# --- stale_review_records: what is skipped, without raising ---------------------------------


def damaged_projects() -> Iterator[tuple[str, MemoryFileSystem, str]]:
    """A project with one good record, and one more record that is damaged in one way."""
    bad_path = record_path(round_no=2)

    def project_with(content: bytes) -> MemoryFileSystem:
        project = MemoryFileSystem()
        put(project, bad_path, content)
        return project

    good = record_data(round_no=1)
    without_agent = record_data(round_no=2)
    del without_agent["agent"]
    odd_client = record_data(round_no=2)
    odd_client["agent"]["client"] = "windsurf"
    extra_key = record_data(round_no=2)
    extra_key["unknown_key"] = "x"
    cases: dict[str, bytes] = {
        "not-yaml": b"{ this is: [not closed",
        "binary": b"\xff\xfe\x00\x01 not text",
        "a-list": b"- one\n- two\n",
        "empty": b"",
        "a-repeated-key": b'{"schema": "a", "schema": "b"}',
        "no-agent": document(without_agent),
        "an-unknown-client": document(odd_client),
        "an-unknown-key": document(extra_key),
    }
    for name, content in cases.items():
        project = project_with(content)
        put(project, record_path(round_no=1), document(good))
        yield name, project, record_path(round_no=1)


DAMAGED = list(damaged_projects())


@pytest.mark.parametrize(
    ("project", "good"),
    [pytest.param(project, good, id=name) for name, project, good in DAMAGED],
)
def test_a_record_that_does_not_validate_is_skipped(project: MemoryFileSystem, good: str) -> None:
    """AC-4. expected_behavior_source: the interface item 7 ("skips without raising any file
    that ... does not validate", parsed with the strict loader as `ReviewResult`): one broken
    record beside a good one does not stop the good one from being listed.
    """
    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (good,)


@pytest.mark.parametrize("kind", [FileKind.SYMLINK, FileKind.OTHER, FileKind.DIRECTORY])
def test_a_record_that_is_no_regular_file_is_skipped(kind: FileKind) -> None:
    """AC-4. expected_behavior_source: the interface item 7 ("skips ... any file that is not
    regular"; ORQLET-SEC-002, a record is untrusted input). The file system says that the path
    holds a link, something else or a directory, and the good record is still listed.
    """
    project = BrokenFiles()
    good = add_record(project, round_no=1)
    odd = add_record(project, round_no=2)
    project.kinds[odd] = kind

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (good,)


def test_a_directory_with_the_name_of_a_record_is_skipped() -> None:
    """AC-4. expected_behavior_source: the interface item 7 ("skips ... any file that is not
    regular"): a real directory named like a record, in the memory file system.
    """
    project = MemoryFileSystem()
    good = add_record(project, round_no=1)
    project.make_dir(CanonicalPath.parse(record_path(round_no=2)))

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (good,)


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(PathNotFound("gone"), id="the-file-vanished"),
        pytest.param(NotARegularFile("odd"), id="not-a-regular-file"),
        pytest.param(FileSystemError("refused"), id="a-port-error"),
        pytest.param(PermissionError(13, "denied"), id="the-os-refuses"),
        pytest.param(OSError(5, "input output error"), id="an-os-error"),
    ],
)
def test_a_record_that_cannot_be_read_is_skipped(error: Exception) -> None:
    """AC-4. expected_behavior_source: the interface item 7 ("skips without raising any file that
    ... cannot be read"): the read of one record fails with a port or an OS error, and the good
    record is still listed.
    """
    project = BrokenFiles()
    good = add_record(project, round_no=1)
    broken = add_record(project, round_no=2)
    project.read_errors[broken] = error

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (good,)


def test_a_record_of_exactly_the_largest_size_is_read_and_a_larger_one_is_skipped() -> None:
    """AC-4. expected_behavior_source: the interface item 7 ("skips ... any file that ... is
    larger than `MAX_EVIDENCE_BYTES`"); `MAX_EVIDENCE_BYTES` is 64 KiB. The records are valid and
    the size is made with YAML comment lines, so only the size differs.
    """
    project = MemoryFileSystem()
    body = document(record_data(round_no=1))
    exact = record_path(round_no=1)
    put(project, exact, padded(body, MAX_EVIDENCE_BYTES))
    too_big = record_path(round_no=2)
    put(project, too_big, padded(document(record_data(round_no=2)), MAX_EVIDENCE_BYTES + 1))
    assert len(project.read_bytes(CanonicalPath.parse(exact))) == MAX_EVIDENCE_BYTES
    assert len(project.read_bytes(CanonicalPath.parse(too_big))) == MAX_EVIDENCE_BYTES + 1

    assert stale(project, write_of(AGENT_PATH[CLAUDE].format(ARCH))) == (exact,)


# --- stale_review_finding ----------------------------------------------------------------


def paths_of(count: int) -> list[str]:
    return [record_path(task=f"t{n:02d}") for n in range(1, count + 1)]


@pytest.mark.parametrize("empty", [(), []], ids=["tuple", "list"])
def test_no_stale_record_gives_no_finding(empty: Sequence[str]) -> None:
    """AC-4. expected_behavior_source: the interface item 7 (`stale_review_finding` "returns None
    for no path"); plan P-6 AC-4 (the warning is for a plan that makes a record stale).
    """
    assert stale_review_finding(empty) is None


def test_the_finding_is_a_warning_with_the_code_and_the_path() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("`upgrade` prints ORQ-W547 with the path of
    each such record"); the interface item 7 (a WARNING with the code `STALE_REVIEW`).
    """
    path = record_path(task="demo")

    finding = stale_review_finding([path])

    assert finding is not None
    assert finding.code == STALE_REVIEW
    assert finding.severity is Severity.WARNING
    assert path in finding.message
    assert MORE.search(finding.message) is None


def test_the_finding_says_what_a_pin_does_and_that_the_person_decides() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("The text says that a pin changes protected
    files and `protected_set_digest`, that approvals of designs and plans in flight then show
    ORQ-W390 and that the person decides"); ADR-003 decision 7; C-8. Pinned by key words only.
    """
    finding = stale_review_finding(paths_of(1))

    assert finding is not None
    text = finding.message
    assert "pin" in text.lower()
    assert "protected" in text
    assert "protected_set_digest" in text
    assert "ORQ-W390" in text
    assert "person" in text
    assert "decide" in text


def test_exactly_the_most_listed_paths_are_all_listed() -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("at most 20, then the count"); the
    interface item 7 (at most 20 paths, then `and N more`): 20 paths are all there and there is no
    count.
    """
    paths = paths_of(MAX_LISTED)

    finding = stale_review_finding(paths)

    assert finding is not None
    assert all(path in finding.message for path in paths)
    assert MORE.search(finding.message) is None


@pytest.mark.parametrize("extra", [1, 5, 40])
def test_more_than_the_most_listed_paths_gives_the_first_ones_in_the_order_given_and_a_count(
    extra: int,
) -> None:
    """AC-4. expected_behavior_source: plan P-6 AC-4 ("at most 20, then the count"); the interface
    item 7 ("lists at most 20 paths in the order given, then `and N more`"). The paths are given
    in reverse order, so that the first 20 given are not the first 20 sorted.
    """
    paths = list(reversed(paths_of(MAX_LISTED + extra)))

    finding = stale_review_finding(paths)

    assert finding is not None
    assert all(path in finding.message for path in paths[:MAX_LISTED])
    assert not any(path in finding.message for path in paths[MAX_LISTED:])
    counts = MORE.findall(finding.message)
    assert counts == [str(extra)]


def test_the_finding_accepts_a_tuple_and_a_list_alike() -> None:
    """AC-4. expected_behavior_source: the interface item 7 (`paths: Sequence[str]`)."""
    paths = paths_of(MAX_LISTED + 2)

    assert stale_review_finding(tuple(paths)) == stale_review_finding(list(paths))
