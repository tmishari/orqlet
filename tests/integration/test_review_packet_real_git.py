"""`review prepare` and the patch exclusion on a real Git: no earlier conclusion reaches a packet.

These tests were written first, by the Tester of phase P-11 of the task dynamic-model-profiles,
before the implementation existed. Each cites its `expected_behavior_source`: AC-n of phase P-11
in docs/design/dynamic-model-profiles/plan.yaml, BC-n of design/component.md, and decision 8 of
ADR-007 (design/adr-007-independence-model-identity-and-fresh-context.md).

AC-5: this module runs on the Linux, macOS and Windows jobs of the CI matrix. Nothing in it
depends on the platform or on the presence of Git, and no test is marked as one that may fail, so
a platform whose Git does not honour the pathspecs fails here and the failure is not hidden. It
uses no symbolic link, and every file name is valid on Windows. Files are written as bytes with
LF endings and compared as bytes. The repository is built with the helpers of
tests/support/git.py and the environment of `clean_environ`: no global Git configuration.
"""

from __future__ import annotations

import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.git.vcs_git import GitVcs
from orqlet.adapters.process.subprocess_runner import SubprocessRunner
from orqlet.application.ports.process import ProcessResult, ProcessRunner
from orqlet.application.usecases.review_prepare import review_prepare
from orqlet.application.usecases.validation import ValidateServices, ValidationResult
from orqlet.domain.findings import Verdict
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.workflow import PINNED
from tests.support.artifacts import TASK_DIR, design, dump, phase, plan
from tests.support.git import clean_environ, git, make_repo

pytestmark = pytest.mark.integration

CONCLUSION = "SENTINEL-CONCLUSION-5c1e9a"  # the text of an earlier review, in records and notes
RECORD_NAME = "SENTINEL-NAME-8d2f41"  # a part of the file name of an earlier record
PATTERN = "docs/design/*/reviews/*"

SERVICE = "src/pkg/service.py"
GUIDE = "docs/guide/overview.md"
MANIFEST = f"{TASK_DIR}/design/manifest.yaml"
RECORD = f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r1.yaml"
OLD_RECORD = f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r0.yaml"
DEEP_RECORD = f"{TASK_DIR}/reviews/deep/security-reviewer-P-1-r1.yaml"
STAGED_RECORD = f"{TASK_DIR}/reviews/architecture-reviewer-P-1-r2-{RECORD_NAME}.yaml"
NOTE = "docs/notes/architecture-round-1.md"
BRACKETS = "docs/notes/[a-b].md"  # a literal name: read as a glob it would match a.md
PLAIN = "docs/notes/a.md"
NOTES = (NOTE, BRACKETS)
UNUSED = "docs/notes/unused.md"  # named by a later manifest, in no tree
COMMITTED_RECORDS = frozenset({RECORD, OLD_RECORD, DEEP_RECORD})  # changed between the commits
ALL_RECORDS = COMMITTED_RECORDS | {STAGED_RECORD}

EARLIER = f"verdict: FAIL\nclaim: {CONCLUSION}\n".encode()
SERVICE_SECOND = b"def existing() -> None: ...\ndef more() -> None: ...\n"
SERVICE_STAGED = SERVICE_SECOND + b"def staged() -> None: ...\n"
AGENT = b"---\nname: orqlet-arch-reviewer\n---\nReview.\n"
SECTION_START = b"diff --git "


def project_files(notes: tuple[str, ...]) -> dict[str, bytes]:
    """The plan, the design that names `notes`, and the standards that `review prepare` reads."""
    roles = ("architecture-reviewer", "security-reviewer")
    reviews = [{"role": roles[number % 2], "note": note} for number, note in enumerate(notes)]
    return {
        f"{TASK_DIR}/plan.yaml": dump(plan(phases=[phase()])).encode(),
        MANIFEST: dump(design(reviews=reviews)).encode(),
        ".orqlet/knowledge.yaml": b"schema: orqlet.knowledge/v2\n",
        ".prompts/rules.yaml": b"schema: orqlet.rules/v1\nrules: []\n",
        ".claude/agents/orqlet-arch-reviewer.md": AGENT,
        ".orqlet/standards.lock.yaml": (
            f"schema: orqlet.standards-lock/v1\napplicable_rules_hash: {'a' * 64}\n".encode()
        ),
        ".orqlet/workflow.lock": (
            "schema: orqlet.workflow-lock/v1\nworkflow_version: 0.2.0\n"
            f"workflow_digest: {'b' * 64}\ncontrols_level: 2\n".encode()
        ),
    }


STAGED_MANIFEST = project_files((*NOTES, UNUSED, SERVICE))[MANIFEST]  # names the service as a note


def write_and_stage(repo: Path, files: Mapping[str, bytes], remove: Sequence[str] = ()) -> None:
    """Write the files as bytes, delete the removed ones, and stage everything."""
    for name in remove:
        (repo / name).unlink()
    for name, content in files.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    git(repo, "add", "-A")


def commit_all(repo: Path, message: str) -> str:
    git(repo, "commit", "--quiet", "-m", message)
    return git(repo, "rev-parse", "HEAD").strip()


@dataclass(frozen=True, slots=True)
class Repo:
    """A real repository: two commits, and an index that holds more than the second commit."""

    root: Path
    environ: dict[str, str]
    first: str  # the base commit, a full id
    second: str  # HEAD

    def vcs(self, runner: ProcessRunner | None = None) -> GitVcs:
        process = SubprocessRunner() if runner is None else runner
        return GitVcs(process, self.root, environ=self.environ)


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Repo:
    home = tmp_path_factory.mktemp("review-packet")
    root = make_repo(home / "repo")
    first_state = {
        **project_files(NOTES),  # the approved design: the base of the packet names the notes
        SERVICE: b"def existing() -> None: ...\n",
        RECORD: b"verdict: FAIL\n",
        OLD_RECORD: b"verdict: FAIL\n",
        NOTE: b"note one\n",
        PLAIN: b"a one\n",
        BRACKETS: b"brackets one\n",
    }
    write_and_stage(root, first_state)
    first = commit_all(root, "first")
    second_state = {
        # The design also names a note that no file has, so the manifest is a changed file.
        **project_files((*NOTES, UNUSED)),
        SERVICE: SERVICE_SECOND,
        RECORD: EARLIER,
        DEEP_RECORD: EARLIER,
        NOTE: EARLIER,
        PLAIN: b"a two\n",
        BRACKETS: b"brackets two\n",
        GUIDE: b"# Overview\n",
    }
    write_and_stage(root, second_state, remove=(OLD_RECORD,))
    second = commit_all(root, "second")
    # What is staged and not committed: a new record whose name holds a sentinel, a change of
    # the note, a change of the service, and a manifest that names the service as one more note
    # (an attempt to hide a changed file). The packet is built from this index.
    write_and_stage(
        root,
        {
            SERVICE: SERVICE_STAGED,
            STAGED_RECORD: EARLIER,
            NOTE: EARLIER + b"staged\n",
            MANIFEST: STAGED_MANIFEST,
        },
    )
    return Repo(root, clean_environ(home), first, second)


class RecordingRunner:
    """Passes each command to a real runner and remembers the command line."""

    def __init__(self, inner: ProcessRunner) -> None:
        self._inner = inner
        self.commands: list[tuple[str, ...]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str,
        env: Mapping[str, str],
        timeout_seconds: float,
        max_output_bytes: int,
        stdin: bytes | None = None,
    ) -> ProcessResult:
        self.commands.append(tuple(argv))
        return self._inner.run(
            argv,
            cwd=cwd,
            env=env,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            stdin=stdin,
        )

    def diff_tree_commands(self) -> list[tuple[str, ...]]:
        return [command for command in self.commands if "diff-tree" in command]


@dataclass(frozen=True, slots=True)
class Packet:
    result: ValidationResult
    files: dict[str, bytes]  # by path inside the packet


@pytest.fixture(scope="module")
def packet(repo: Repo) -> Packet:
    """`review prepare` with the real adapter, on the staged index, against the first commit."""
    packets = MemoryFileSystem()
    services = ValidateServices(
        project=MemoryFileSystem(), vcs=repo.vcs(), loader=StrictYamlLoader(), workflow=PINNED
    )
    result = review_prepare(
        services, packets, "pidpidpidpid", "demo", "P-1", base=repo.first, head="staged"
    )
    assert result.verdict is Verdict.PASS, [finding.message for finding in result.findings]
    prefix = f"{result.data['packet']}/"
    files = {path.removeprefix(prefix): data for path, data in packets.snapshot().items()}
    return Packet(result, files)


def sections(patch: bytes) -> list[bytes]:
    """The patch cut into one piece for each file, at the lines that start with `diff --git `."""
    found: list[bytes] = []
    for line in io.BytesIO(patch):
        if line.startswith(SECTION_START):
            found.append(b"")
        assert found, "a patch starts with the header of a file"
        found[-1] += line
    return found


def path_of(section: bytes) -> str:
    """The path in the header of a section. There are no renames, so both sides name one path."""
    header = section.split(b"\n", 1)[0].decode("utf-8").removeprefix("diff --git ")
    length = (len(header) - len("a/ b/")) // 2
    return header[len("a/") : len("a/") + length]


def header_of(path: str) -> bytes:
    return f"diff --git a/{path} b/{path}".encode()


def leaks(files: Mapping[str, bytes], *needles: str) -> list[tuple[str, str]]:
    """Each (file, needle) where a needle shows in the name of a packet file or in its content."""
    return [
        (path, needle)
        for path, data in sorted(files.items())
        for needle in needles
        if needle in path or needle.encode() in data
    ]


def test_a_pattern_drops_matching_sections_and_keeps_the_rest_byte_for_byte(repo: Repo) -> None:
    """expected_behavior_source: P-11 AC-2 ("the patch of the adapter with the exclusion holds no
    header for an excluded path and holds the other sections byte for byte as the unfiltered
    patch holds them"); AC-1 (a pattern matches as `fnmatch` does, with `*` crossing `/`); BC-45;
    BC-21. Between the two commits one record is modified, one is deleted and one is added in a
    folder below the reviews folder, so every kind of section is covered. The exclusion alone,
    with no positive pathspec, is a patch of every other path."""
    vcs = repo.vcs()
    whole = sections(vcs.diff_patch(repo.first, repo.second))
    changed = {path_of(section): section for section in whole}
    assert set(changed) >= COMMITTED_RECORDS  # the records are in the unfiltered patch
    assert b"deleted file mode" in changed[OLD_RECORD]
    assert b"new file mode" in changed[DEEP_RECORD]

    kept = sections(vcs.diff_patch(repo.first, repo.second, exclude_patterns=(PATTERN,)))

    assert kept == [section for section in whole if path_of(section) not in COMMITTED_RECORDS]
    for path in COMMITTED_RECORDS:
        assert header_of(path) not in b"".join(kept)


def test_a_literal_path_with_glob_characters_is_excluded_only_as_that_path(repo: Repo) -> None:
    """expected_behavior_source: P-11 AC-2 ("a literal path with glob characters is excluded only
    as that path"); AC-1 (each path is passed as `:(exclude,literal)<path>`; "a path matches
    only itself"); BC-45. The file `[a-b].md` is dropped and the file `a.md` stays, which a glob
    reading of the entry would turn around."""
    vcs = repo.vcs()
    whole = sections(vcs.diff_patch(repo.first, repo.second))

    kept = sections(vcs.diff_patch(repo.first, repo.second, exclude_paths=(BRACKETS,)))

    assert kept == [section for section in whole if path_of(section) != BRACKETS]
    assert PLAIN in {path_of(section) for section in kept}
    assert BRACKETS in {path_of(section) for section in whole}


def test_a_pattern_and_note_paths_together_leave_only_the_other_sections(repo: Repo) -> None:
    """expected_behavior_source: P-11 AC-2 (no header for an excluded path; the other sections
    byte for byte as in the unfiltered patch); AC-1 (both parameters, as `review prepare` passes
    them); BC-45. The union of the records and the two notes is excluded."""
    vcs = repo.vcs()
    whole = sections(vcs.diff_patch(repo.first, repo.second))
    excluded = COMMITTED_RECORDS | set(NOTES)

    patch = vcs.diff_patch(
        repo.first, repo.second, exclude_patterns=(PATTERN,), exclude_paths=NOTES
    )

    kept = sections(patch)
    assert kept == [section for section in whole if path_of(section) not in excluded]
    assert {path_of(section) for section in kept} == {SERVICE, PLAIN, GUIDE, MANIFEST}


def test_exclusions_reach_git_as_pathspecs_after_a_double_dash_only(repo: Repo) -> None:
    """expected_behavior_source: P-11 AC-1 ("The git adapter passes each pattern as
    `:(exclude)<pattern>` and each path as `:(exclude,literal)<path>`, only after `--`, to the
    allow-listed `diff-tree`, whose option check is unchanged"); AC-6 ("No git option beyond the
    pathspec after `--` is added"). The command line before the `--` is the one without any
    exclusion."""
    recorder = RecordingRunner(SubprocessRunner())
    vcs = repo.vcs(recorder)

    vcs.diff_patch(repo.first, repo.second)
    (plain,) = recorder.diff_tree_commands()
    recorder.commands.clear()
    vcs.diff_patch(repo.first, repo.second, exclude_patterns=(PATTERN,), exclude_paths=(BRACKETS,))
    (command,) = recorder.diff_tree_commands()

    cut = command.index("--")
    pathspecs = command[cut + 1 :]
    assert command.count("--") == 1
    assert len(pathspecs) == 2
    assert set(pathspecs) == {f":(exclude){PATTERN}", f":(exclude,literal){BRACKETS}"}
    assert command[:cut] == (plain[: plain.index("--")] if "--" in plain else plain)


def test_a_sentinel_from_earlier_records_is_found_in_no_file_of_the_packet(
    packet: Packet,
) -> None:
    """expected_behavior_source: P-11 AC-4 ("A sentinel string written into a review record and
    into a note path named by the manifest is found in no file of the packet"; run "against the
    real git adapter in the integration test"); BC-21; BC-45; ADR-007 decision 8. The sentinel is
    in the records and in the note, in the index and in the commits; another is in the file name
    of a staged record. The scan reads every path and every content of the packet, with
    `MANIFEST.json` and `diff.patch`, and the findings of the result."""
    files = packet.files

    assert {"MANIFEST.json", "diff.patch", "context/design-manifest.yaml"} <= set(files)
    assert f"snapshot/{SERVICE}" in files
    assert leaks(files, CONCLUSION, RECORD_NAME) == []
    messages = " ".join(finding.message for finding in packet.result.findings)
    assert CONCLUSION not in messages
    assert RECORD_NAME not in messages


def test_the_scan_finds_the_sentinels_in_the_unfiltered_repository(repo: Repo) -> None:
    """expected_behavior_source: P-11 AC-4 and ADR-007 decision 8 (a scan for a sentinel). A scan
    that cannot find a sentinel proves nothing. This control reads the same staged tree without
    any exclusion, its snapshot and its patch against the first commit, and requires the scan to
    find both sentinels there: in the content of records and notes, and in a file name."""
    vcs = repo.vcs()
    tree = vcs.staged_tree()
    unfiltered = {"diff.patch": vcs.diff_patch(repo.first, tree)}
    for entry in vcs.tree_at(tree):
        content = vcs.read_at(tree, entry.path)
        assert content is not None
        unfiltered[f"snapshot/{entry.path}"] = content

    places = {path for path, _ in leaks(unfiltered, CONCLUSION, RECORD_NAME)}

    expected = {
        "diff.patch",
        f"snapshot/{RECORD}",
        f"snapshot/{NOTE}",
        f"snapshot/{STAGED_RECORD}",
    }
    assert expected <= places
    assert CONCLUSION.encode() in unfiltered["diff.patch"]
    assert RECORD_NAME.encode() in unfiltered["diff.patch"]


def test_the_packet_holds_the_ordinary_files_and_no_record_or_note(packet: Packet) -> None:
    """expected_behavior_source: P-11 AC-3 ("leaves out of `snapshot/` ... every path that
    matches `docs/design/*/reviews/*` and every path that `reviews[].note` ... names"); BC-21;
    BC-45. The snapshot is the staged index: the staged service, the committed notes `a.md`,
    the guide and the design manifest stay; the records, the staged record and both notes
    (one of them `[a-b].md`) are left out."""
    files = packet.files

    for path in (RECORD, DEEP_RECORD, STAGED_RECORD, NOTE, BRACKETS):
        assert f"snapshot/{path}" not in files
    assert files[f"snapshot/{SERVICE}"] == SERVICE_STAGED
    assert files[f"snapshot/{PLAIN}"] == b"a two\n"
    assert files[f"snapshot/{GUIDE}"] == b"# Overview\n"
    assert files[f"snapshot/{MANIFEST}"] == STAGED_MANIFEST


def test_a_note_that_only_the_staged_manifest_names_hides_nothing(packet: Packet) -> None:
    """expected_behavior_source: finding F-1 of the security review r2 of P-11 (a staged manifest
    named a changed file as a note and hid it from the packet, while the review binding still
    covers it); ADR-007 decision 8 ("The design-manifest copy lists note paths"). Written by the
    Coder after that finding, not by the Tester. The manifest staged here names the service as
    one more note; the manifest of the base, the approved one, does not. With the real adapter,
    the staged service is in the snapshot and in the diff, and the manifest copy lists it."""
    files = packet.files

    assert files[f"snapshot/{SERVICE}"] == SERVICE_STAGED
    assert header_of(SERVICE) in files["diff.patch"]
    assert header_of(MANIFEST) in files["diff.patch"]
    assert SERVICE.encode() in files["context/design-manifest.yaml"]
    assert files["context/design-manifest.yaml"] == STAGED_MANIFEST


def test_the_diff_of_the_packet_is_the_filtered_patch_of_the_staged_tree(
    repo: Repo, packet: Packet
) -> None:
    """expected_behavior_source: P-11 AC-3 (`diff.patch` leaves out the same paths as the
    snapshot); AC-2 (the other sections byte for byte as the unfiltered patch holds them); BC-45.
    The diff of the packet is the patch of the first commit against the staged tree, without the
    records and the notes, and it is byte for byte the patch that the adapter gives for them."""
    vcs = repo.vcs()
    tree = vcs.staged_tree()
    whole = sections(vcs.diff_patch(repo.first, tree))
    filtered = vcs.diff_patch(repo.first, tree, exclude_patterns=(PATTERN,), exclude_paths=NOTES)
    excluded = ALL_RECORDS | set(NOTES)
    kept = sections(filtered)

    assert packet.files["diff.patch"] == filtered
    assert kept == [section for section in whole if path_of(section) not in excluded]
    assert {path_of(section) for section in kept} == {SERVICE, PLAIN, GUIDE, MANIFEST}
    assert excluded <= {path_of(section) for section in whole}  # all of them were in the patch


def test_no_excluded_path_is_reported_as_omitted_or_listed_in_the_manifest(
    packet: Packet,
) -> None:
    """expected_behavior_source: P-11 AC-3 ("Excluded paths appear in neither the `omitted` list
    nor `MANIFEST.json`"); BC-45; ADR-007 decision 8 (they "would reveal that earlier rounds
    exist"). The repository has no link and no oversize file, so nothing at all is omitted."""
    raw = packet.files["MANIFEST.json"]
    manifest: dict[str, Any] = json.loads(raw)
    listed = {name for name, _ in manifest["files"]}

    assert manifest["omitted"] == []
    assert [f for f in packet.result.findings if f.code == "ORQ-I440"] == []
    for path in ALL_RECORDS | set(NOTES):
        assert f"snapshot/{path}" not in listed
        assert path.encode() not in raw


def test_an_entry_that_is_a_file_at_one_end_and_a_directory_at_the_other_hides_nothing(
    tmp_path: Path,
) -> None:
    """expected_behavior_source: P-11 AC-1 ("a path matches only itself"; an entry that names a
    directory matches nothing below it) and the measurement of the Coder with git 2.56.1 (a
    literal pathspec that names a directory also drops everything below it). Here `docs/x` is a
    file in the first commit and a directory in the second. Written by the Coder, not the Tester:
    the adapter reads the trees at both ends, so what is below the directory stays in the patch."""
    root = make_repo(tmp_path / "repo")
    write_and_stage(root, {"docs/x": b"a file\n", SERVICE: b"one\n"})
    first = commit_all(root, "first")
    write_and_stage(root, {"docs/x/inner.md": b"inside\n"}, remove=("docs/x",))
    second = commit_all(root, "second")
    vcs = GitVcs(SubprocessRunner(), root, environ=clean_environ(tmp_path))

    patch = vcs.diff_patch(first, second, exclude_paths=("docs/x",))

    assert header_of("docs/x/inner.md") in vcs.diff_patch(first, second)
    assert header_of("docs/x/inner.md") in patch
