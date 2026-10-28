"""Kill `init` with links after a write, on real files, and run it again (task
team-conventions-resources, phase P-4; ORQLET-TEST-002, plan AC-5 and AC-6).

With a terminal and without `--yes`, `init` asks for links and writes the registry in its one plan,
after the profile and before the lock (ADR-002 decision 6; the interface decision of phase P-4,
which is the reading of the plan author that the Tester of phase P-4 was given). The link prompt
runs only when the profile is drafted in this run: a re-run with a profile on disk does not ask
and keeps the registry that is on disk. These tests stop the plan after a write, on the real file
system under `tmp_path`, as `test_apply_kill_after_k.py` does for `init` without links, and show:

- the files are whole: no temporary file, and no lock (the manifest is written last);
- a re-run converges. Killed before the profile was written, the re-run drafts the profile again
  and asks about the links again (a terminal and the same answers give the files of an
  uninterrupted run). Killed after the registry was written, the re-run asks nothing and keeps the
  file, and the files are those of an uninterrupted run;
- links typed in an interrupted init may be lost, and the tests say so. The plan writes the
  profile before the registry (ADR-002 decision 6), so a kill between the two leaves a profile and
  no registry; the re-run finds the profile on disk, does not ask, and writes the empty registry.
  The links exist only in the memory of the process that died; the person adds them again with
  `orqlet resources add`, and ADR-002 accepts this. The re-run converges all the same: every other
  file is the one of an uninterrupted run and the registry is valid and recorded in the lock;
- a re-run without a terminal (with `--yes`, as a script runs it) asks nothing, gives a valid
  registry recorded in the lock, and loses the links of the interrupted run in the same cases.

Kill points. The init of the fixture writes several dozen files and a real-file init takes about
half a second, so the tests stop after every write that carries links or the lock and their
neighbours (the profile, the registry, the lock, the write before and the write after each) and
after every seventh write of the rest. The other writes carry no link and are stopped one by one,
for the same plan, by `test_apply_kill_after_k.py`. The version control is the fake of tests/fakes
(the file system is the real one), so that no Git process is started.

Credential-shaped text is not used here: the addresses are placeholders.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.resources import Resources
from orqlet.application.ports.filesystem import FileSystem
from orqlet.application.ports.prompter import NoAnswerAvailable, Question
from orqlet.application.ports.vcs import RepoState
from orqlet.application.usecases.init_project import InitOptions, InitResult, init_project
from orqlet.application.usecases.resources_source import parse_resources
from orqlet.application.usecases.services import Services
from tests.fakes.faulty_fs import FaultyFileSystem, SimulatedCrash
from tests.fakes.ids import ReplayIds, SequentialIds
from tests.fakes.vcs import FakeVcs
from tests.support.real_env import real_services, snapshot
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.fault

REGISTRY = ".orqlet/resources.yaml"
LOCK = ".orqlet/generated.lock.yaml"
PROFILE = ".orqlet/project-profile.yaml"
LOADER = StrictYamlLoader()
ANSWERS = {
    "repository.target_branch": "main",
    "repository.branch_naming": "",
    "repository.commit_convention": "",
    # Phase P-5 adds seven convention questions; an empty answer keeps each one unknown.
    "repository.branch_model": "",
    "repository.release_flow": "",
    "repository.pull_requests.shape": "",
    "repository.pull_requests.merge_strategy": "",
    "repository.pull_requests.reviewers": "",
    "repository.pull_requests.required_checks": "",
    "reviewer": "Ada",
}
# With a terminal: no `--yes`, so that the link prompt runs; the plan is approved at the terminal.
ASKING = InitOptions(answers=ANSWERS)
# Without a terminal: `--yes`, as a script runs `init`; nothing is asked.
SCRIPTED = InitOptions(assume_yes=True, answers=ANSWERS)
LINKS = (
    {
        "resources.url": "https://docs.example.com/guides/alpha",
        "resources.id": "alpha",
        "resources.title": "Alpha guide",
        "resources.kind": "team-docs",
        "resources.note": "Read before changing the alpha module.",
    },
    {
        "resources.url": "https://wiki.example.com/spaces/team/beta",
        "resources.id": "beta",
        "resources.title": "Beta wiki",
        "resources.kind": "team-docs",
        "resources.note": "Working agreements of the team.",
        "resources.access": "login",
    },
)


class Links:
    """A `Prompter` that says yes to the link prompt and gives the same links every time.

    Every confirmation, the approval of the plan included, is answered yes. Without a terminal it
    records the attempt and raises, as the real one does.
    """

    def __init__(
        self, links: Sequence[Mapping[str, str]] = LINKS, *, terminal: bool = True
    ) -> None:
        self._queue = list(links)
        self._terminal = terminal
        self._current: Mapping[str, str] = {}
        self._addresses = 0
        self.link_prompts = 0
        self.attempts: list[str] = []

    @property
    def interactive(self) -> bool:
        return self._terminal

    def ask(self, question: Question) -> str:
        if not self._terminal:
            self.attempts.append(question.id)
            raise NoAnswerAvailable(question.id)
        if question.id == "resources.links":
            self.link_prompts += 1
            return "yes"
        if question.id == "resources.url":
            self._addresses += 1
            assert self._addresses <= 20, "the loop of links did not end"
            self._current = self._queue.pop(0) if self._queue else {}
            return self._current.get("resources.url", "")
        if question.id.startswith("resources."):
            return self._current.get(question.id, question.default or "")
        raise AssertionError(f"unscripted question: {question.id}")

    def confirm(self, text: str, *, default: bool = False) -> bool:
        if not self._terminal:
            self.attempts.append(text)
            raise NoAnswerAvailable(text)
        return True


def project(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name / "project"
    shutil.copytree(FIXTURES / "repos" / "uv_fastapi", root)
    return root


def crash_after(writes: int) -> Callable[[FileSystem], FileSystem]:
    def wrap(fs: FileSystem) -> FileSystem:
        return FaultyFileSystem(fs, crash_after_writes=writes)

    return wrap


def services_for(
    root: Path,
    data: Path,
    prompter: Links,
    *,
    crash: int | None = None,
    ids: ReplayIds | SequentialIds | None = None,
) -> Services:
    services = real_services(
        root, data, wrap_project=None if crash is None else crash_after(crash), ids=ids
    )
    return replace(services, vcs=FakeVcs(RepoState.HAS_COMMITS, branch="main"), prompter=prompter)


def registry_in(snapshot_of_files: dict[str, bytes]) -> Resources:
    resources, findings = parse_resources(LOADER, snapshot_of_files[REGISTRY], "the registry")
    assert resources is not None, findings
    return resources


def ids_in(snapshot_of_files: dict[str, bytes]) -> list[str]:
    return [item.id for item in registry_in(snapshot_of_files).resources]


def applied_order(result: InitResult) -> list[str]:
    """The paths of the plan in the order in which `apply_plan` writes them: the lock last."""
    assert result.plan is not None
    ordered = sorted(result.plan.writes, key=lambda w: (w.last, w.path.sort_key()))
    return [str(write.path) for write in ordered]


def kill_points(order: list[str]) -> list[int]:
    """Every write that carries links or the lock and its neighbours, and every seventh of the
    rest. `k` writes done means that the write at index `k` is the one that did not happen."""
    total = len(order)
    near = {
        index + shift
        for name in (PROFILE, REGISTRY, LOCK)
        for index in [order.index(name)]
        for shift in (-1, 0, 1)
    }
    return sorted(point for point in near | {0, *range(0, total, 7)} if 0 <= point < total)


def clean_run(
    tmp_path: Path, name: str, prompter: Links, options: InitOptions
) -> tuple[dict[str, bytes], list[str]]:
    """The files of an uninterrupted `init`, and the order in which its plan was written."""
    root = project(tmp_path, name)
    result = init_project(services_for(root, tmp_path / f"{name}-data", prompter), options)
    assert result.status == "applied", result.findings
    return snapshot(root), applied_order(result)


def killed(tmp_path: Path, crash_point: int) -> tuple[Path, Path, dict[str, bytes]]:
    """A project in which an `init` with a terminal and links was stopped after `crash_point`."""
    root = project(tmp_path, f"crash-{crash_point}")
    data = tmp_path / f"data-{crash_point}"
    with pytest.raises(SimulatedCrash):
        init_project(services_for(root, data, Links(), crash=crash_point), ASKING)
    partial = snapshot(root)
    assert LOCK not in partial, crash_point
    assert not any(".orqlet-tmp-" in name for name in partial), "a temporary file was left"
    return root, data, partial


def rerun_ids() -> ReplayIds:
    """A re-run gets the project id of the first run and a fresh change id."""
    return ReplayIds(SequentialIds().new_id())


def test_the_clean_run_writes_the_profile_then_the_registry_then_the_lock(tmp_path: Path) -> None:
    """AC-5. expected_behavior_source: the interface decision ("The registry bytes ... are written
    in the one plan of `init`, after the profile and before the lock") and ADR-002 decision 6.
    This fixes the order that the kill points below are chosen from."""
    expected, order = clean_run(tmp_path, "clean", Links(), ASKING)

    assert ids_in(expected) == ["alpha", "beta"]
    assert order.index(PROFILE) < order.index(REGISTRY) < order.index(LOCK) == len(order) - 1


def test_every_sampled_kill_point_converges_on_a_re_run_with_a_terminal(tmp_path: Path) -> None:
    """AC-5, AC-6. expected_behavior_source: AC-5 ("an interrupted init converges on a re-run"),
    ORQLET-TEST-002 (stop after each step; a re-run converges to the same state), ADR-002 decision
    6 ("a re-run after an interruption reads what is on disk, as `_load_existing_profile` does
    for the profile") and the interface decision (the link prompt runs only when the profile is
    drafted in this run; a re-run with a profile on disk does not ask and keeps the registry).

    Before the profile is written the links are asked again and the files are those of an
    uninterrupted run. After the registry is written nothing is asked and they are the same.
    Between the two writes the profile is on disk, nothing is asked, and the links are lost: see
    the next test."""
    expected, order = clean_run(tmp_path, "clean", Links(), ASKING)
    profile_at, registry_at = order.index(PROFILE), order.index(REGISTRY)

    for crash_point in kill_points(order):
        if profile_at < crash_point <= registry_at:
            continue  # the window of the next test
        root, data, partial = killed(tmp_path, crash_point)
        assert (REGISTRY in partial) == (crash_point > registry_at), crash_point
        prompter = Links()

        rerun = init_project(services_for(root, data, prompter, ids=rerun_ids()), ASKING)

        assert rerun.status == "applied", crash_point
        assert prompter.link_prompts == (1 if crash_point <= profile_at else 0), crash_point
        assert snapshot(root) == expected, f"kill after {crash_point} writes did not converge"


def test_links_typed_in_an_interrupted_init_may_be_lost_and_the_re_run_still_converges(
    tmp_path: Path,
) -> None:
    """AC-5, AC-6. expected_behavior_source: ADR-002 decision 6 ("The plan writes the profile before
    the registry, so links typed in an `init` that was interrupted between the two writes can be
    lost; the person adds them again with `orqlet resources add`, and this is accepted") and the
    interface decision ("a re-run with a profile on disk does not ask and keeps the registry on
    disk"). Killed after the profile and before the registry, the re-run asks nothing, so the links
    are lost on purpose: the registry is the empty one, valid and recorded in the lock, and every
    other file is that of an uninterrupted init without links."""
    _, order = clean_run(tmp_path, "clean", Links(), ASKING)
    without_links, _ = clean_run(tmp_path, "clean-none", Links([]), ASKING)
    profile_at, registry_at = order.index(PROFILE), order.index(REGISTRY)
    assert ids_in(without_links) == []

    for crash_point in range(profile_at + 1, registry_at + 1):
        root, data, partial = killed(tmp_path, crash_point)
        assert PROFILE in partial, crash_point
        assert REGISTRY not in partial, crash_point
        prompter = Links()

        rerun = init_project(services_for(root, data, prompter, ids=rerun_ids()), ASKING)

        assert rerun.status == "applied", crash_point
        assert prompter.link_prompts == 0, "a profile on disk is not asked about links again"
        final = snapshot(root)
        assert ids_in(final) == [], "the links typed in the interrupted run are lost"
        assert final == without_links, f"kill after {crash_point} writes did not converge"


def test_a_re_run_without_a_terminal_asks_nothing_and_ends_in_a_valid_registry(
    tmp_path: Path,
) -> None:
    """AC-5, AC-6. expected_behavior_source: AC-5 ("without a terminal it prints the hint and asks
    nothing; an interrupted init converges on a re-run"), ADR-002 decision 6 (the links can be
    lost; the person adds them with `orqlet resources add`) and the interface decision (without a
    terminal, or with `--yes`, nothing is asked). Killed after the registry was written, the
    re-run keeps it and the files are those of an uninterrupted run with the links. Killed
    before, the links are gone and the registry is the empty one: the files are those of an
    uninterrupted init without links. Either way the result is applied, valid and recorded."""
    expected, order = clean_run(tmp_path, "clean", Links(), ASKING)
    without_links, _ = clean_run(tmp_path, "clean-none", Links([]), ASKING)
    registry_at = order.index(REGISTRY)

    points = {0, order.index(PROFILE), registry_at, registry_at + 1, len(order) - 1}
    for crash_point in sorted(points):
        root, data, _ = killed(tmp_path, crash_point)
        quiet = Links(terminal=False)

        rerun = init_project(services_for(root, data, quiet, ids=rerun_ids()), SCRIPTED)

        assert rerun.status == "applied", crash_point
        assert quiet.attempts == [], "a prompter without a terminal must not be asked"
        final = snapshot(root)
        assert LOCK in final
        registry_in(final)  # loads: the registry is valid
        kept = crash_point > registry_at
        assert final == (expected if kept else without_links), crash_point
