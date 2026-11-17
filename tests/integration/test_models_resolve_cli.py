"""`orqlet models resolve` through the real command line (task dynamic-model-profiles, phase P-8).

Every test cites its `expected_behavior_source`. AC-1 to AC-7 are the acceptance criteria of phase
P-8 in docs/design/dynamic-model-profiles/plan.yaml. R-1 to R-14 are the readings of the acceptance
criteria that the coder of the phase was given: R-2 the usage checks, R-3 the refusals, R-4 the
override, R-5 the hint, R-6 the data, R-7 the exit statuses, R-8 the text output, R-9 the markers,
R-10 no git, no process and no clock, R-13 the registration and R-14 the sizes. The business rules
of the use case (every reason, every precedence rule, every mapping of the data) are tested on fakes
in tests/unit/application/test_models_resolve.py; these tests pin what only the command line
shows: the usage checks, the exit statuses, the envelope `orqlet.cli-result/v1`, the ten lines of
text, what is never printed, the registration, and a folder that is not a git repository.

These tests were written first, by the Tester of phase P-8, before the command existed. The command
is run in the project folder (the current folder of the process is the root), as an agent runs it;
no test passes `--root`, because the criteria list no such option. Every run of the command is
guarded: `GitVcs`, `SubprocessRunner` and `SystemClock` of the wiring module, `subprocess.run` and
`subprocess.Popen` fail the test when they are called (R-10b). The project is written in a plain
temporary folder with no `.git` in it or in any folder above it, unless a test says it is a
repository. Credential-shaped text is assembled from parts at run time and never written as one
literal (ORQLET-SEC-003).

The wiring module and the use case are imported inside the tests that need them, so that the
tests are collected before the modules exist.

Behaviour that the criteria and the readings leave open is deliberately not pinned here:
- the wording of a usage message, of a finding and of the values after the labels of the text
  output beyond the values that the readings name (the punctuation, the order of the parts of a
  line, the text of an empty list or of an absent profile);
- the exit status of `orqlet models` with no arguments (it depends on the version of Click);
- the names of the parameters of `resolve_command` (the options are pinned by `--help`);
- the order of findings of different codes and how many findings one code has;
- the hint of a target that has both a pin and a profile assignment.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import re
import shutil
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

import pytest
import typer
from typer.testing import CliRunner

from orqlet.adapters.fs.local_fs import LocalFileSystem
from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.model_selection import policy_problems
from orqlet.application.usecases.workflow_sources import load_roles, load_skills
from orqlet.interface.cli.app import app
from orqlet.interface.cli.exit_codes import ExitCode
from tests.support.git import clean_environ, commit_file, make_repo

pytestmark = pytest.mark.integration

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")

RUNNER = CliRunner()
Doc = dict[str, Any]

POLICY = ".orqlet/model-policy.yaml"
LOCK = ".orqlet/generated.lock.yaml"
LIMIT = 256 * 1024

E540, E541, E542, E543, E545, E547 = (
    "ORQ-E540",
    "ORQ-E541",
    "ORQ-E542",
    "ORQ-E543",
    "ORQ-E545",
    "ORQ-E547",
)

CLAUDE, CODEX, CURSOR = "claude-code", "codex", "cursor"
CLIENTS = (CLAUDE, CODEX, CURSOR)
MODES = ("automatic", "manual", "automatic-with-fallbacks")
TESTER = "orqlet-tester"
INVENTORY = "orqlet-inventory"
DESIGN = "orqlet-design"

NO_POLICY = "no model policy; the client chooses"
NO_ASSIGNMENT = "no assignment for this target; the client chooses"
CHOOSES = "the client chooses"

# The ten lines of the text output, in order (AC-3, R-8).
LABELS = (
    "target",
    "policy",
    "profile",
    "source",
    "selected",
    "candidates",
    "fallbacks",
    "escalation",
    "rejected",
    "hint",
)
# The keys of `data` (AC-2).
DATA_KEYS = {
    "client",
    "target",
    "task",
    "policy",
    "profile",
    "mode",
    "source",
    "selection",
    "client_chooses",
    "candidates",
    "fallbacks",
    "escalation",
    "list_prices",
    "rejected",
    "hint",
    "result",
}

# A placeholder shaped like a source-host token, assembled at run time (ORQLET-SEC-003).
CREDENTIAL = "".join(("gh", "p_", ("aB3" * 13)[:36]))


def suggested(profile_id: str) -> str:
    """The hint of a target that has a profile (AC-4), word for word."""
    return (
        f"Suggested for this work: profile {profile_id}; "
        "the client keeps the choice and nothing here changes the model."
    )


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ORQLET_DATA_DIR", str(tmp_path / "userdata"))
    for name, value in clean_environ(home).items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def plain(tmp_path: Path) -> Path:
    """An empty project folder that is not a git repository, nor inside one."""
    root = tmp_path / "project"
    root.mkdir()
    assert not any((folder / ".git").exists() for folder in (root, *root.parents))
    return root


# --- policies built in code ----------------------------------------------------------------------


def route(
    client: str,
    name: str,
    *,
    kind: str = "id",
    resolves_to: str | None = None,
    also_known_as: Sequence[str] = (),
) -> Doc:
    return {
        "client": client,
        "kind": kind,
        "name": name,
        "resolves_to": resolves_to,
        "also_known_as": list(also_known_as),
        "access": "unknown",
        "retires_on": None,
    }


def routes_of(prefix: str, *, also: Mapping[str, Sequence[str]] | None = None) -> list[Doc]:
    """One id route for each client, named `<prefix>-<client>`, with the spellings `also` lists."""
    spellings = also or {}
    return [
        route(client, f"{prefix}-{client}", also_known_as=spellings.get(client, ()))
        for client in CLIENTS
    ]


def entry(
    model_id: str,
    *routes: Doc,
    family: str,
    state: str = "approved",
    price: tuple[str, str] | None = None,
    **extra: str,
) -> Doc:
    """A catalog entry; an approved one carries an approver and `pr:42`."""
    granted = state == "approved"
    document: Doc = {
        "id": model_id,
        "family": family,
        "approval": {
            "state": state,
            "approved_by": extra.get("approved_by", "example-approver" if granted else None),
            "approval_ref": extra.get("approval_ref", "pr:42" if granted else None),
        },
        "documented": {
            "evidence": extra.get("evidence", "docs/example/evidence/entry.md"),
            "date": "2026-10-30",
        },
        "callable": "not-run",
        "evaluated": {"state": "none"},
        "routes": list(routes),
    }
    if price is not None:
        document["list_price"] = {
            "input_per_million_usd": price[0],
            "output_per_million_usd": price[1],
            "source": extra.get("price_source", "docs/example/evidence/prices.md"),
        }
    return document


def exclusion(
    rule_id: str,
    *,
    aliases: Sequence[str] = (),
    reason: str = "Example reason.",
    source: str = "Example notice.",
) -> Doc:
    return {
        "id": rule_id,
        "reason": reason,
        "source": source,
        "aliases": list(aliases),
        "id_patterns": [],
        "family_tags": [],
    }


def profile_doc(
    profile_id: str,
    *,
    mode: str = "manual",
    candidates: Sequence[str] = (),
    fallbacks: Sequence[str] = (),
    escalation: str | None = None,
    capability: str = "Example capability.",
) -> Doc:
    """A profile whose lists are offered to every client."""

    def lists(models: Sequence[str]) -> list[Doc]:
        return [{"client": client, "models": list(models)} for client in CLIENTS if models]

    return {
        "id": profile_id,
        "capability": capability,
        "mode": mode,
        "candidates": lists(candidates),
        "fallbacks": lists(fallbacks),
        "escalation": escalation,
    }


def assignment_doc(
    kind: str,
    name: str,
    *,
    profile: str | None = None,
    model: str | None = None,
    mode: str = "manual",
    task: str | None = None,
    effort: str | None = None,
) -> Doc:
    return {
        "target": {"kind": kind, "name": name},
        "task": task,
        "client": None,
        "profile": profile,
        "model": model,
        "mode": mode,
        "effort": effort,
    }


def pinned(model_id: str, **fields: Any) -> Doc:
    """The tester role pinned to one model."""
    return assignment_doc("role", TESTER, model=model_id, **fields)


def via(profile_id: str, mode: str = "manual", **fields: Any) -> Doc:
    """The tester role assigned to a profile."""
    return assignment_doc("role", TESTER, profile=profile_id, mode=mode, **fields)


A, B, C, D = "example-a", "example-b", "example-c", "example-d"
PROPOSED, ALIAS, RENAMED = "example-proposed", "example-alias", "example-renamed"
ALSO_A = "example-a-claude-code-xhigh"  # a spelling that the Claude Code route of A lists

CATALOG = [
    entry(A, *routes_of(A, also={CLAUDE: [ALSO_A]}), family="family-one", price=("3", "15")),
    entry(B, *routes_of(B), family="family-two"),
    entry(
        RENAMED,
        *(route(client, f"renamed-route-{client}") for client in CLIENTS),
        family="family-six",
    ),
    entry(C, *routes_of(C), family="family-one", price=("0.25", "1.25")),
    entry(D, *routes_of(D), family="family-three"),
    entry(PROPOSED, *routes_of(PROPOSED), family="family-four", state="proposed"),
    entry(
        ALIAS,
        route(CLAUDE, f"{ALIAS}-{CLAUDE}", kind="alias", resolves_to="example-alias-target"),
        family="family-five",
    ),
]
EXCLUSION = exclusion("blocked-example", aliases=["blocked-alias"])
QUALITY = profile_doc("quality", mode="manual", candidates=[A, B])
ENGINEERING = profile_doc(
    "engineering",
    mode="automatic-with-fallbacks",
    candidates=[B, C],
    fallbacks=[D, A],
    escalation="quality",
)
ECONOMY = profile_doc("economy", mode="automatic", candidates=[C, D], escalation="engineering")
PROFILES = [QUALITY, ENGINEERING, ECONOMY]


def policy(
    *assignments: Doc,
    models: Sequence[Doc] = CATALOG,
    profiles: Sequence[Doc] = PROFILES,
    excluded: Sequence[Doc] = (EXCLUSION,),
) -> Doc:
    """A sound policy: the catalog above, the three profiles and one exclusion."""
    return {
        "schema": "orqlet.model-policy/v2",
        "policy_version": 1,
        "reviewed_for_release": "0.4.0",
        "models": list(models),
        "excluded": list(excluded),
        "profiles": list(profiles),
        "assignments": list(assignments),
    }


def mode_policy(mode: str) -> Doc:
    """The tester role assigned to a quality profile of the given mode."""
    both = profile_doc("quality", mode=mode, candidates=[A, B], fallbacks=[C])
    return policy(via("quality", mode), profiles=[both])


def raw_of(document: Doc) -> bytes:
    return json.dumps(document, indent=2).encode()


def pad(content: bytes, size: int) -> bytes:
    """`content` and comment lines of at most 80 bytes, so that the file has exactly `size` bytes.

    The lines are short because the reader of the policy refuses one line of thousands of
    characters (the `oversize` rule of its credential scan), which is not what these tests probe.
    """
    assert size >= len(content), "the content is longer than the size asked for"
    padded = bytearray(content)
    while len(padded) < size:
        width = min(80, size - len(padded))
        padded += b"\n" + b"#" + b"x" * (width - 2) if width >= 2 else b"\n"
    assert len(padded) == size
    return bytes(padded)


SEEDED = {"path": POLICY, "owner": "seeded", "seeded_sha256": "0" * 64}
OTHER_SEEDED = {"path": ".orqlet/role-bindings.yaml", "owner": "seeded", "seeded_sha256": "1" * 64}


def lock_bytes(*rows: Doc) -> bytes:
    document = {
        "schema": "orqlet.generated-lock/v1",
        "generator": {"orqlet": "0.4.0"},
        "files": list(rows),
    }
    return json.dumps(document, indent=2).encode()


def write_project(
    root: Path, content: Doc | bytes | None = None, *, lock: Sequence[Doc] | None = None
) -> Path:
    """The policy (a document, or the bytes of a file) and the lock, under `root`."""
    (root / ".orqlet").mkdir(parents=True, exist_ok=True)
    if content is not None:
        raw = raw_of(content) if isinstance(content, dict) else content
        (root / POLICY).write_bytes(raw)
    if lock is not None:
        (root / LOCK).write_bytes(lock_bytes(*lock))
    return root


def marker(label: str) -> str:
    """A unique, valid model string for one field: the same value on every run."""
    return "zq7mk-" + hashlib.sha256(label.encode()).hexdigest()[:12]


# --- running the command, guarded ----------------------------------------------------------------


@contextlib.contextmanager
def forbidden() -> Iterator[list[str]]:
    """What the command must not use (R-10b): a git call, a process, a clock. Each use is recorded
    and raises; the exception is caught by the command, so the tests read the record."""
    calls: list[str] = []

    def refusing(name: str) -> Callable[..., NoReturn]:
        def refuse(*args: object, **kwargs: object) -> NoReturn:
            calls.append(name)
            raise AssertionError(f"`models resolve` must not use {name}")

        return refuse

    with pytest.MonkeyPatch.context() as patch:
        for name in ("GitVcs", "SubprocessRunner", "SystemClock"):
            patch.setattr(f"orqlet.interface.cli.wiring.{name}", refusing(name))
        patch.setattr(subprocess, "run", refusing("subprocess.run"))
        patch.setattr(subprocess, "Popen", refusing("subprocess.Popen"))
        yield calls


@dataclass(frozen=True)
class Outcome:
    code: int
    stdout: str
    stderr: str

    @property
    def shown(self) -> str:
        """Everything the command printed."""
        return f"{self.stdout}\n{self.stderr}"

    def envelope(self) -> dict[str, Any]:
        document: dict[str, Any] = json.loads(self.stdout)
        return document

    def data(self) -> dict[str, Any]:
        data: dict[str, Any] = self.envelope()["data"]
        return data

    def codes(self) -> list[str]:
        return [finding["code"] for finding in self.envelope()["findings"]]


def invoke(root: Path, *args: str, as_json: bool = False) -> Outcome:
    """`orqlet models resolve ARGS` with `root` as the current folder; no git, process or clock."""
    argv = ["models", "resolve", *args, *(["--json"] if as_json else [])]
    with contextlib.chdir(root), forbidden() as calls:
        result = RUNNER.invoke(app, argv)
    assert calls == [], f"the command used {calls}"
    return Outcome(result.exit_code, result.stdout, result.stderr)


def resolve(root: Path, *args: str, as_json: bool = True) -> Outcome:
    """The tester role of the claude-code client, unless `args` says otherwise."""
    return invoke(root, "--client", CLAUDE, "--role", TESTER, *args, as_json=as_json)


def lines_of(outcome: Outcome) -> dict[str, str]:
    """The ten lines of the text output, by label (R-8); the values are stripped."""
    lines = outcome.stdout.strip().splitlines()
    assert [line.partition(":")[0] for line in lines] == list(LABELS), outcome.stdout
    return {label: value.strip() for label, _, value in (line.partition(":") for line in lines)}


def leaks(text: str, secret: str, width: int = 10) -> bool:
    """True when `text` shows `secret` or any `width` characters in a row of it."""
    needle = secret.lower()
    haystack = text.lower()
    size = min(width, len(needle))
    return any(needle[start : start + size] in haystack for start in range(len(needle) - size + 1))


def assert_sorted_keys(text: str) -> None:
    """Every object of the JSON text has its keys in sorted order."""

    def check(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in pairs]
        assert keys == sorted(keys), keys
        return dict(pairs)

    json.loads(text, object_pairs_hook=check)


def registered_names(group: typer.Typer, prefix: str = "") -> set[str]:
    """The commands of an application, named as `IMPLEMENTED_COMMANDS` names them."""
    names = set()
    for command in group.registered_commands:
        callback = command.callback
        name = command.name or (callback.__name__ if callback is not None else "")
        names.add(f"{prefix}{name.removesuffix('_command').replace('_', '-')}".strip())
    for sub in group.registered_groups:
        if sub.typer_instance is not None:
            names |= registered_names(sub.typer_instance, f"{prefix}{sub.name} ")
    return names


def group_named(name: str) -> typer.Typer:
    for group in app.registered_groups:
        if group.name == name and group.typer_instance is not None:
            return group.typer_instance
    raise AssertionError(f"the application has no group `{name}`")


# --- scenarios: one project and one question each ------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    content: Doc | bytes | None
    args: tuple[str, ...]
    code: int
    lock: tuple[Doc, ...] | None = None


TESTER_ARGS = ("--client", CLAUDE, "--role", TESTER)
NO_CANDIDATE = policy(via("quality"), profiles=[profile_doc("quality", candidates=[PROPOSED])])

# Every way that the command ends with 0: a selection or an automatic result.
SELECTED_SCENARIOS = {
    "pinned": Scenario(policy(pinned(A)), TESTER_ARGS, 0),
    "profile-manual": Scenario(policy(via("quality")), TESTER_ARGS, 0),
    "override": Scenario(policy(pinned(B)), (*TESTER_ARGS, "--override", f"{A}-{CLAUDE}"), 0),
    "profile-target": Scenario(policy(), ("--client", CLAUDE, "--profile", "quality"), 0),
    "skill-target": Scenario(
        policy(assignment_doc("skill", DESIGN, model=A)), ("--client", CODEX, "--skill", DESIGN), 0
    ),
}
AUTOMATIC_SCENARIOS = {
    "automatic": Scenario(mode_policy("automatic"), TESTER_ARGS, 0),
    "automatic-with-fallbacks": Scenario(mode_policy("automatic-with-fallbacks"), TESTER_ARGS, 0),
    "unassigned": Scenario(policy(pinned(A)), ("--client", CLAUDE, "--role", INVENTORY), 0),
    "empty-policy": Scenario(policy(), TESTER_ARGS, 0),
    "no-policy-file": Scenario(None, TESTER_ARGS, 0),
    "no-policy-file-and-a-lock-without-it": Scenario(None, TESTER_ARGS, 0, lock=(OTHER_SEEDED,)),
    "no-policy-file-a-profile-target": Scenario(
        None, ("--client", CURSOR, "--profile", "economy"), 0
    ),
}
# Every way that no candidate qualifies: exit 1 (R-7), with the data of the answer.
NONE_SCENARIOS = {
    "no-candidate": Scenario(NO_CANDIDATE, TESTER_ARGS, 1),
    "override-invalid": Scenario(policy(), (*TESTER_ARGS, "--override", f"{PROPOSED}-{CLAUDE}"), 1),
    "override-excluded": Scenario(policy(), (*TESTER_ARGS, "--override", "blocked-alias"), 1),
    "coder-model-unknown-no-policy": Scenario(
        None, (*TESTER_ARGS, "--different-family-from", "example-missing"), 1
    ),
    "coder-profile-no-policy": Scenario(None, (*TESTER_ARGS, "--coder-profile", "economy"), 1),
    **{
        f"coder-model-{kind}-{mode}": Scenario(
            mode_policy(mode), (*TESTER_ARGS, "--different-family-from", coder), 1
        )
        for mode in MODES
        for kind, coder in (("unknown", "example-missing"), ("proposed", PROPOSED))
    },
}
OK_SCENARIOS = {**SELECTED_SCENARIOS, **AUTOMATIC_SCENARIOS, **NONE_SCENARIOS}

# Every way that a policy is refused: exit 3 (R-3), with the code of the finding.
REFUSED_SCENARIOS = {
    "duplicate-key": (Scenario(b"a: 1\na: 2\n", TESTER_ARGS, 3), E540),
    "not-a-mapping": (Scenario(b"- a\n- b\n", TESTER_ARGS, 3), E541),
    "v1": (
        Scenario(raw_of({"schema": "orqlet.model-policy/v1", "models": []}), TESTER_ARGS, 3),
        E541,
    ),
    "unknown-key": (Scenario(raw_of({**policy(), marker("key"): 1}), TESTER_ARGS, 3), E541),
    "credential": (
        Scenario(raw_of(policy()) + f"\n# {CREDENTIAL}\n".encode(), TESTER_ARGS, 3),
        E542,
    ),
    "oversize": (Scenario(pad(raw_of(policy(pinned(A))), LIMIT + 1), TESTER_ARGS, 3), E540),
    "excluded-route": (
        Scenario(
            policy(
                models=[*CATALOG, entry("example-bad", route(CLAUDE, "blocked-alias"), family="x")]
            ),
            TESTER_ARGS,
            3,
        ),
        E543,
    ),
    "unknown-role": (
        Scenario(policy(assignment_doc("role", marker("role"), model=A)), TESTER_ARGS, 3),
        E545,
    ),
    "unknown-model": (
        Scenario(policy(assignment_doc("role", TESTER, model="example-missing")), TESTER_ARGS, 3),
        E545,
    ),
    "deleted": (Scenario(None, TESTER_ARGS, 3, lock=(SEEDED, OTHER_SEEDED)), E547),
}

EVERY_OK = pytest.mark.parametrize("name", list(OK_SCENARIOS))
EVERY_REFUSAL = pytest.mark.parametrize("name", list(REFUSED_SCENARIOS))


def stage(root: Path, scenario: Scenario) -> Path:
    return write_project(root, scenario.content, lock=scenario.lock)


# --- AC-7, R-13: the command group is part of the application ------------------------------------


def test_the_command_is_listed_as_implemented() -> None:
    """AC-7/R-13. expected_behavior_source: AC-7 ("`IMPLEMENTED_COMMANDS` lists `models
    resolve`")."""
    assert "models resolve" in IMPLEMENTED_COMMANDS


def test_the_commands_that_the_application_registers_are_the_implemented_commands() -> None:
    """AC-7/R-13. expected_behavior_source: R-13 (`registered_names(app) ==
    set(IMPLEMENTED_COMMANDS)` and it contains `models resolve`); the equality test of tests/
    integration/test_validate_cli.py."""
    assert registered_names(app) == set(IMPLEMENTED_COMMANDS)
    assert "models resolve" in registered_names(app)


def test_models_is_a_group_with_the_one_subcommand_resolve() -> None:
    """AC-7/R-13. expected_behavior_source: AC-7 ("`orqlet models` is a registered command group
    with the one subcommand `resolve`"); R-13 ("The `models` group has exactly one command,
    `resolve`")."""
    group = group_named("models")

    assert registered_names(group) == {"resolve"}
    assert group.registered_groups == []


def test_the_models_group_lists_resolve_in_its_help() -> None:
    """AC-7/R-13. expected_behavior_source: R-13 ("`orqlet models --help` lists it")."""
    result = RUNNER.invoke(app, ["models", "--help"])

    assert result.exit_code == 0
    assert "resolve" in result.stdout


def test_the_models_group_with_no_arguments_shows_its_help() -> None:
    """AC-7/R-13. expected_behavior_source: R-13 ("`orqlet models` with no args shows help"). The
    exit status is not pinned: Click 8.2 and later exit 2 for a group with no arguments."""
    result = RUNNER.invoke(app, ["models"])

    assert "No such command" not in result.output
    assert "resolve" in result.output


def test_the_help_of_the_command_names_every_option() -> None:
    """AC-1/R-13. expected_behavior_source: AC-1 (`orqlet models resolve --client C (--role R |
    --skill S | --profile P) [--task T] [--override MODEL] [--different-family-from CATALOG_ID]
    [--coder-profile P] [--json]`)."""
    result = RUNNER.invoke(app, ["models", "resolve", "--help"])

    plain_help = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)  # the help is coloured
    assert result.exit_code == 0
    for option in (
        "--client",
        "--role",
        "--skill",
        "--profile",
        "--task",
        "--override",
        "--different-family-from",
        "--coder-profile",
        "--json",
    ):
        assert option in plain_help, option


def test_the_group_and_the_command_have_the_names_that_the_plan_gives() -> None:
    """AC-7/R-13. expected_behavior_source: the interface of phase P-8 (`models_app` and
    `resolve_command` in `orqlet.interface.cli.commands.models`)."""
    module = importlib.import_module("orqlet.interface.cli.commands.models")

    assert isinstance(module.models_app, typer.Typer)
    assert callable(module.resolve_command)


def test_the_services_of_the_command_are_the_file_system_the_loader_and_the_workflow(
    tmp_path: Path,
) -> None:
    """AC-5/R-10. expected_behavior_source: AC-5 ("a services object with the project file system,
    the strict loader and the workflow package, and no VCS, process runner or clock"); the
    interface (`build_models_services(root)` builds these three and nothing else, so none of
    `GitVcs`, `SubprocessRunner` and `SystemClock` is built)."""
    wiring = importlib.import_module("orqlet.interface.cli.wiring")
    module = importlib.import_module("orqlet.application.usecases.models_resolve")

    with forbidden() as calls:
        services = wiring.build_models_services(tmp_path)

    assert calls == []
    assert isinstance(services, module.ModelsServices)
    assert isinstance(services.project, LocalFileSystem)
    assert isinstance(services.loader, StrictYamlLoader)
    assert isinstance(services.workflow, PackagedWorkflow)


def test_the_guards_of_these_tests_catch_a_git_call_a_process_and_a_clock() -> None:
    """Not a behaviour of the command: the guard of R-10b is live, so a run that passes under it
    used no git, process or clock. expected_behavior_source: R-10b (the names to patch:
    `wiring.GitVcs`, `wiring.SubprocessRunner`, `wiring.SystemClock`, `subprocess.Popen` and
    `subprocess.run`)."""
    wiring = importlib.import_module("orqlet.interface.cli.wiring")

    with forbidden() as calls:
        for name in ("GitVcs", "SubprocessRunner", "SystemClock"):
            with pytest.raises(AssertionError):
                getattr(wiring, name)()
        with pytest.raises(AssertionError):
            subprocess.run(["git", "--version"], check=False)
        with pytest.raises(AssertionError):
            subprocess.Popen(["git", "--version"])

    assert len(calls) == 5


def test_the_premise_the_policies_of_these_tests_are_valid_contracts() -> None:
    """Not a behaviour of the command: what the tests write is read by the contracts of the
    project and has no problem, so a refusal is never an accident of a fixture.
    expected_behavior_source: R-3 (the reader and `policy_problems` accept a sound policy)."""
    workflow = PackagedWorkflow()
    roles = {role.name for role in load_roles(workflow)}
    skills = {skill.name for skill in load_skills(workflow, frozenset())}
    documents = [
        scenario.content
        for scenario in OK_SCENARIOS.values()
        if isinstance(scenario.content, dict)
        and scenario.content["schema"] == "orqlet.model-policy/v2"
    ]
    assert documents
    for document in documents:
        loaded = load_contract(StrictYamlLoader(), ModelPolicy, raw_of(document), source=POLICY)
        assert policy_problems(loaded, roles, skills) == ()


# --- AC-1, R-2: the usage checks ------------------------------------------------------------------

# Every breach of a usage rule, as the arguments for one marker `m`. The marker is a value that
# would be valid if the check were missing, or one that only the check refuses; it must not be
# repeated in the usage message (AC-1, R-2).
BREACHES: dict[str, Callable[[str], list[str]]] = {
    "no-client": lambda m: ["--role", TESTER, "--task", m],
    "client-not-a-client": lambda m: ["--client", m, "--role", TESTER],
    "client-in-capitals": lambda m: ["--client", CLAUDE.upper(), "--role", TESTER, "--task", m],
    "client-empty": lambda m: ["--client", "", "--role", TESTER, "--task", m],
    "no-target": lambda m: ["--client", CLAUDE, "--task", m],
    "role-and-skill": lambda m: ["--client", CLAUDE, "--role", m, "--skill", f"{m}-two"],
    "role-and-profile": lambda m: ["--client", CLAUDE, "--role", m, "--profile", "quality"],
    "skill-and-profile": lambda m: ["--client", CLAUDE, "--skill", m, "--profile", "quality"],
    "all-three": lambda m: [
        "--client",
        CLAUDE,
        "--role",
        m,
        "--skill",
        f"{m}-two",
        "--profile",
        "quality",
    ],
    "role-in-capitals": lambda m: ["--client", CLAUDE, "--role", m.upper()],
    "role-with-a-space": lambda m: ["--client", CLAUDE, "--role", f"{m} x"],
    "role-too-long": lambda m: ["--client", CLAUDE, "--role", m + "a" * 64],
    "role-empty": lambda m: ["--client", CLAUDE, "--role", "", "--task", m],
    "role-ends-with-a-hyphen": lambda m: ["--client", CLAUDE, "--role", f"{m}-"],
    "skill-in-capitals": lambda m: ["--client", CLAUDE, "--skill", m.upper()],
    "skill-with-an-underscore": lambda m: ["--client", CLAUDE, "--skill", f"{m}_x"],
    "skill-too-long": lambda m: ["--client", CLAUDE, "--skill", m + "a" * 64],
    "skill-empty": lambda m: ["--client", CLAUDE, "--skill", "", "--task", m],
    "task-in-capitals": lambda m: [*TESTER_ARGS, "--task", m.upper()],
    "task-with-a-space": lambda m: [*TESTER_ARGS, "--task", f"{m} x"],
    "task-too-long": lambda m: [*TESTER_ARGS, "--task", m + "a" * 64],
    "task-empty": lambda _: [*TESTER_ARGS, "--task", ""],
    "task-with-a-double-hyphen": lambda m: [*TESTER_ARGS, "--task", f"{m}--x"],
    "profile-not-a-profile": lambda m: ["--client", CLAUDE, "--profile", m],
    "profile-in-capitals": lambda m: ["--client", CLAUDE, "--profile", "QUALITY", "--task", m],
    "profile-empty": lambda m: ["--client", CLAUDE, "--profile", "", "--task", m],
    "coder-profile-not-a-profile": lambda m: [*TESTER_ARGS, "--coder-profile", m],
    "coder-profile-in-capitals": lambda _: [*TESTER_ARGS, "--coder-profile", "ECONOMY"],
    "override-outside-the-alphabet": lambda m: [*TESTER_ARGS, "--override", f"{m}!"],
    "override-with-a-percent": lambda m: [*TESTER_ARGS, "--override", f"{m}%20"],
    "override-with-a-newline": lambda m: [*TESTER_ARGS, "--override", f"{m}\nx"],
    "override-too-long": lambda m: [*TESTER_ARGS, "--override", m + "a" * 128],
    "override-empty": lambda m: [*TESTER_ARGS, "--override", "", "--task", m],
    "coder-model-with-a-space": lambda m: [*TESTER_ARGS, "--different-family-from", f"{m} x"],
    "coder-model-with-a-bracket": lambda m: [*TESTER_ARGS, "--different-family-from", f"{m}[a]"],
    "coder-model-with-an-equal-sign": lambda m: [*TESTER_ARGS, "--different-family-from", f"{m}=1"],
    "coder-model-with-a-comma": lambda m: [*TESTER_ARGS, "--different-family-from", f"{m},x"],
    "coder-model-outside-the-alphabet": lambda m: [
        *TESTER_ARGS,
        "--different-family-from",
        f"{m}!",
    ],
    "coder-model-too-long": lambda m: [*TESTER_ARGS, "--different-family-from", m + "a" * 128],
    "coder-model-empty": lambda m: [*TESTER_ARGS, "--different-family-from", "", "--task", m],
}


@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("name", list(BREACHES))
def test_a_breach_of_a_usage_rule_exits_2_and_does_not_repeat_the_value(
    plain: Path, name: str, as_json: bool
) -> None:
    """AC-1/R-2. expected_behavior_source: AC-1 ("A breach of any of these exits 2 with a usage
    message that does not repeat the offending value"); R-2 (the checks raise `typer.BadParameter`
    with fixed text that never repeats the value, with and without `--json`); BC-33; BC-32."""
    mark = marker("usage")
    write_project(plain, policy(pinned(A)))

    outcome = invoke(plain, *BREACHES[name](mark), as_json=as_json)

    assert outcome.code == int(ExitCode.USAGE), outcome.shown
    assert "No such command" not in outcome.shown  # a missing command also exits 2
    assert not leaks(outcome.shown, mark), outcome.shown


@pytest.mark.parametrize("name", ["client-not-a-client", "role-with-a-space", "override-empty"])
def test_a_usage_error_is_found_before_the_policy_is_read(plain: Path, name: str) -> None:
    """AC-1/R-2. expected_behavior_source: R-2 ("usage checks are made in the command", before the
    use case): a breach exits 2, not 3, though the policy file is invalid."""
    write_project(plain, b"a: 1\na: 2\n")

    outcome = invoke(plain, *BREACHES[name](marker("usage")))

    assert outcome.code == int(ExitCode.USAGE), outcome.shown
    assert "No such command" not in outcome.shown


@pytest.mark.parametrize("client", CLIENTS)
def test_each_of_the_three_clients_is_accepted(plain: Path, client: str) -> None:
    """AC-1/R-2. expected_behavior_source: AC-1 ("`--client` is one of the three clients"); R-2
    (claude-code, codex, cursor). The name of the route is `<model>-<client>`."""
    write_project(plain, policy(pinned(A)))

    outcome = invoke(plain, "--client", client, "--role", TESTER, as_json=True)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["client"] == client
    assert outcome.data()["selection"]["name"] == f"{A}-{client}"


@pytest.mark.parametrize(
    "target",
    [
        ("--role", "a"),
        ("--role", "a" * 64),
        ("--role", "orqlet-code-reviewer"),
        ("--role", "some-unknown-slug"),
        ("--skill", "some-unknown-slug"),
        ("--skill", "a1-b2-c3"),
    ],
    ids=["one-char", "64-chars", "a-reviewer-role", "unknown-role", "unknown-skill", "digits"],
)
def test_a_role_or_a_skill_is_a_slug_and_is_not_checked_against_the_workflow(
    plain: Path, target: tuple[str, str]
) -> None:
    """AC-1/R-2. expected_behavior_source: R-2 ("`--role`, `--skill`, `--task` match `Slug`";
    "Role and skill names are NOT checked against the workflow: `--role orqlet-code-reviewer` and
    `--role some-unknown-slug` are accepted"). A target that no assignment names is automatic."""
    write_project(plain, policy(pinned(A)))

    outcome = invoke(plain, "--client", CLAUDE, *target, as_json=True)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["result"] == "automatic"
    assert outcome.data()["hint"] == NO_ASSIGNMENT


@pytest.mark.parametrize(
    "options",
    [
        ("--task", "a"),
        ("--task", "t-" + "a" * 62),
        ("--override", "a"),
        ("--override", "A" * 128),
        ("--override", "Example Model 1.2 [effort=high, mode=fast]"),
        ("--override", "vendor/model:1@2+3_4.5-6"),
        ("--different-family-from", "A" * 128),
        ("--different-family-from", "vendor/model:1@2+3_4.5-6"),
        ("--coder-profile", "quality"),
        ("--coder-profile", "engineering"),
        ("--coder-profile", "economy"),
    ],
    ids=[
        "task-1",
        "task-64",
        "override-1",
        "override-128",
        "override-display-text",
        "override-alphabet",
        "coder-model-128",
        "coder-model-alphabet",
        "coder-profile-quality",
        "coder-profile-engineering",
        "coder-profile-economy",
    ],
)
def test_the_boundary_values_of_the_options_are_accepted(
    plain: Path, options: tuple[str, str]
) -> None:
    """AC-1/R-2. expected_behavior_source: R-2 (`--override` matches `RecordedModel`, so a space,
    brackets, `=` and `,` are allowed; `--different-family-from` matches `ModelRef`; the profiles
    are one of quality, engineering, economy; a slug has at most 64 characters, a model string at
    most 128). The answer may be a selection or none: only a usage error is a failure here."""
    write_project(plain, policy(pinned(A)))

    outcome = resolve(plain, *options)

    assert outcome.code in (int(ExitCode.OK), int(ExitCode.PROBLEMS)), outcome.shown
    assert outcome.envelope()["command"] == "models resolve"


# --- AC-3, R-7: the exit statuses ----------------------------------------------------------------


@pytest.mark.parametrize("name", list(SELECTED_SCENARIOS) + list(AUTOMATIC_SCENARIOS))
def test_a_selection_or_an_automatic_result_exits_0(plain: Path, name: str) -> None:
    """AC-3/R-7. expected_behavior_source: AC-3 ("Exit status 0 means a selection or an automatic
    result exists, also when no policy file was ever present"); R-7 (selected/automatic is 0)."""
    scenario = OK_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args, as_json=True)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.envelope()["ok"] is True
    assert outcome.data()["result"] in ("selected", "automatic")


@pytest.mark.parametrize("name", list(NONE_SCENARIOS))
def test_no_candidate_that_qualifies_exits_1_and_still_prints_the_answer(
    plain: Path, name: str
) -> None:
    """AC-3/R-7. expected_behavior_source: AC-3 ("1 means that no candidate qualifies, also when
    `--different-family-from` leaves none that can be shown different, in every mode and with no
    policy"); R-7 (X not in the catalog and X `proposed` exit 1 in every mode and with no policy);
    R-3 (no policy with `--different-family-from` or `--coder-profile` is none-qualifies)."""
    scenario = NONE_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args, as_json=True)

    assert outcome.code == int(ExitCode.PROBLEMS), outcome.shown
    assert outcome.envelope()["ok"] is False
    assert outcome.data()["result"] == "none-qualifies"
    assert outcome.data()["selection"] is None
    assert outcome.data()["client_chooses"] is False
    assert outcome.envelope()["findings"] == []


@EVERY_REFUSAL
def test_a_policy_that_is_present_but_not_usable_exits_3_with_its_code(
    plain: Path, name: str
) -> None:
    """AC-3/R-3/R-7. expected_behavior_source: AC-3 ("3 means that a policy is present but
    invalid, deleted or a v1 file"); R-3 (an invalid file ORQ-E540, E541 or E542, a v1 file, a
    problem ORQ-E543 or E545, a deleted file ORQ-E547 is refused: exit 3, findings with codes);
    F-1; F-9."""
    scenario, code = REFUSED_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args, as_json=True)

    assert outcome.code == int(ExitCode.REFUSED), outcome.shown
    assert code in outcome.codes()
    for finding in outcome.envelope()["findings"]:
        assert finding["severity"] == "error"


@EVERY_REFUSAL
def test_a_refusal_prints_no_text_of_an_answer_and_its_codes_on_stderr(
    plain: Path, name: str
) -> None:
    """AC-3/R-3/R-8. expected_behavior_source: R-8 ("A refused run prints no ten-line text, exits
    3, and prints findings on stderr"); `execute` echoes each finding as `CODE: message`."""
    scenario, code = REFUSED_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args)

    assert outcome.code == int(ExitCode.REFUSED), outcome.shown
    assert "target:" not in outcome.stdout
    assert f"{code}" in outcome.stderr


@EVERY_REFUSAL
def test_a_refusal_in_json_is_the_envelope_with_ok_false_and_no_data(
    plain: Path, name: str
) -> None:
    """AC-3/R-3/R-8. expected_behavior_source: R-8 ("With `--json` it prints the envelope
    `orqlet.cli-result/v1` with command "models resolve", ok false, the findings and an empty
    data"); R-3 (`data` is empty when `status` is "refused")."""
    scenario, _ = REFUSED_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args, as_json=True)

    document = outcome.envelope()
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "models resolve"
    assert document["ok"] is False
    assert document["data"] == {}
    assert document["findings"]


@EVERY_REFUSAL
def test_a_refusal_does_not_tell_the_person_to_upgrade(plain: Path, name: str) -> None:
    """AC-3/R-3. expected_behavior_source: R-3 ("The wording of these refusals does not say "run
    orqlet upgrade" (the words `upgrade` must not appear in a finding message)")."""
    scenario, _ = REFUSED_SCENARIOS[name]
    stage(plain, scenario)

    as_text = invoke(plain, *scenario.args)
    as_json = invoke(plain, *scenario.args, as_json=True)

    assert as_text.code == as_json.code == int(ExitCode.REFUSED), as_text.shown
    assert "upgrade" not in as_text.shown.lower()
    assert "upgrade" not in as_json.shown.lower()


def test_a_refusal_names_the_field_and_not_the_value(plain: Path) -> None:
    """AC-3/R-3/R-9. expected_behavior_source: R-3 ("findings with codes and field paths such as
    `models[0]`, never a value of the file")."""
    mark = marker("role")
    document = policy(assignment_doc("role", mark, model=A))
    write_project(plain, document)

    outcome = resolve(plain)

    assert outcome.code == int(ExitCode.REFUSED), outcome.shown
    assert E545 in outcome.codes()
    assert not leaks(outcome.shown, mark)
    names_the_field = [
        "assignments[0]" in f"{finding.get('path') or ''} {finding['message']}"
        for finding in outcome.envelope()["findings"]
    ]
    assert any(names_the_field)


def test_a_policy_that_is_missing_while_the_lock_lists_it_as_seeded_exits_3_with_no_git_call(
    plain: Path,
) -> None:
    """AC-5/R-3/R-10c. expected_behavior_source: AC-5 ("A policy that is missing while the lock
    records it as seeded exits 3 without any git call"); R-10c (exit 3 with ORQ-E547 under the
    patches of `wiring.GitVcs`, `SubprocessRunner`, `SystemClock`, `subprocess.Popen` and
    `subprocess.run`: `invoke` fails on any of them); F-9."""
    write_project(plain, None, lock=[SEEDED, OTHER_SEEDED])
    assert not (plain / POLICY).exists()

    outcome = resolve(plain)

    assert outcome.code == int(ExitCode.REFUSED), outcome.shown
    assert outcome.codes() == [E547]


def test_a_policy_that_is_missing_and_not_in_the_lock_is_not_deleted(plain: Path) -> None:
    """AC-3/R-3. expected_behavior_source: R-3 ("No policy file and no lock row gives policy
    "absent", status "automatic", exit 0"); R-1 (the lock is read only when the policy file is
    missing)."""
    write_project(plain, None, lock=[OTHER_SEEDED])

    outcome = resolve(plain)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["policy"] == "absent"
    assert outcome.data()["result"] == "automatic"
    assert outcome.data()["hint"] == NO_POLICY


def test_a_folder_with_neither_a_policy_nor_a_lock_gives_the_automatic_result(
    plain: Path,
) -> None:
    """AC-3/R-3. expected_behavior_source: AC-3 ("also when no policy file was ever present ("no
    model policy; the client chooses")"); R-3 (no policy file and no lock row)."""
    outcome = resolve(plain)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["policy"] == "absent"
    assert outcome.data()["hint"] == NO_POLICY


# --- AC-2, R-6: the JSON result ------------------------------------------------------------------


@EVERY_OK
def test_the_json_result_is_the_envelope_with_exactly_the_keys_of_the_criterion(
    plain: Path, name: str
) -> None:
    """AC-2/R-6/R-8. expected_behavior_source: AC-2 ("The `data` of the JSON result has exactly
    these keys"); R-8 (the envelope `orqlet.cli-result/v1`, command "models resolve")."""
    scenario = OK_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args, as_json=True)

    document = outcome.envelope()
    assert document["schema"] == "orqlet.cli-result/v1"
    assert document["command"] == "models resolve"
    assert isinstance(document["orqlet_version"], str)
    assert document["not_run"] == []
    assert set(outcome.data()) == DATA_KEYS


@EVERY_OK
def test_the_keys_are_sorted_at_every_depth(plain: Path, name: str) -> None:
    """AC-2/R-6. expected_behavior_source: AC-2 ("Keys are sorted, so the same input gives the
    same bytes"); R-6 (JSON keys are sorted)."""
    scenario = OK_SCENARIOS[name]
    stage(plain, scenario)

    assert_sorted_keys(invoke(plain, *scenario.args, as_json=True).stdout)


@EVERY_OK
def test_two_runs_print_the_same_bytes(plain: Path, name: str) -> None:
    """AC-2/AC-5/R-6. expected_behavior_source: AC-5 ("Two runs print the same bytes"); AC-2
    (the same input gives the same bytes); R-6."""
    scenario = OK_SCENARIOS[name]
    stage(plain, scenario)

    for as_json in (False, True):
        first = invoke(plain, *scenario.args, as_json=as_json)
        second = invoke(plain, *scenario.args, as_json=as_json)
        assert first.code == scenario.code, first.shown
        assert first.stdout.strip()
        assert first == second


def test_a_selected_pin_is_the_data_of_the_criterion(plain: Path) -> None:
    """AC-2/R-6/R-12. expected_behavior_source: AC-2 (the keys and their meaning); R-6 (echoes of
    the query; `policy` is "present"; the selection is the route of the client; the list price is
    that of the catalog model)."""
    write_project(plain, policy(pinned(A, effort="high")))

    outcome = invoke(plain, "--client", CODEX, "--role", TESTER, "--task", "a-task", as_json=True)

    data = outcome.data()
    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert data["client"] == CODEX
    assert data["target"] == {"kind": "role", "name": TESTER}
    assert data["task"] == "a-task"
    assert data["policy"] == "present"
    assert data["result"] == "selected"
    assert data["client_chooses"] is False
    assert data["source"] == "role-assignment"
    assert data["selection"] == {"model": A, "name": f"{A}-{CODEX}", "kind": "id", "effort": "high"}
    assert data["list_prices"] == [
        {"model": A, "input_per_million_usd": "3", "output_per_million_usd": "15"}
    ]
    assert data["rejected"] == []


def test_a_profile_gives_the_candidates_the_fallbacks_and_the_escalation(plain: Path) -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`profile`, `mode` and `escalation` come from the
    resolution; `candidates` and `fallbacks` are lists of `{model, name, kind, effort,
    also_known_as}`, the `also_known_as` of the route of the queried client)."""
    write_project(plain, policy(via("engineering", "automatic-with-fallbacks")))

    outcome = resolve(plain)

    data = outcome.data()
    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert data["profile"] == "engineering"
    assert data["mode"] == "automatic-with-fallbacks"
    assert data["escalation"] == "quality"
    assert data["client_chooses"] is True
    assert data["selection"] is None
    assert [item["model"] for item in data["candidates"]] == [B, C]
    assert [item["model"] for item in data["fallbacks"]] == [D, A]
    for item in (*data["candidates"], *data["fallbacks"]):
        assert set(item) == {"model", "name", "kind", "effort", "also_known_as"}
    assert data["fallbacks"][1]["also_known_as"] == [ALSO_A]
    assert data["candidates"][0]["also_known_as"] == []


def test_the_data_of_a_run_with_no_policy_has_empty_lists_and_no_profile(plain: Path) -> None:
    """AC-2/R-6. expected_behavior_source: R-6 (`policy` is "absent"; `client_chooses` is true
    exactly for client-chooses; `result` is "automatic")."""
    outcome = resolve(plain)

    data = outcome.data()
    assert data["policy"] == "absent"
    assert (data["profile"], data["mode"], data["escalation"]) == (None, None, None)
    assert (data["candidates"], data["fallbacks"], data["list_prices"]) == ([], [], [])
    assert data["client_chooses"] is True
    assert data["result"] == "automatic"
    assert data["source"] == "automatic"


def test_a_profile_target_resolves_the_profile_itself(plain: Path) -> None:
    """AC-2/R-12. expected_behavior_source: R-12 ("A profile target resolves the profile itself");
    R-6 (the echo of the target)."""
    write_project(plain, policy())

    outcome = invoke(plain, "--client", CLAUDE, "--profile", "quality", as_json=True)

    data = outcome.data()
    assert data["target"] == {"kind": "profile", "name": "quality"}
    assert data["profile"] == "quality"
    assert data["selection"]["model"] == A


def test_an_undefined_profile_is_a_target_with_no_levels(plain: Path) -> None:
    """AC-2/R-12. expected_behavior_source: R-12 ("An undefined profile gives a target with no
    levels"): the answer is automatic."""
    document = policy(profiles=[profile_doc("economy", mode="automatic", candidates=[C, D])])
    write_project(plain, document)

    outcome = invoke(plain, "--client", CLAUDE, "--profile", "quality", as_json=True)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["result"] == "automatic"
    assert outcome.data()["candidates"] == []


def test_an_assignment_with_a_task_applies_only_to_that_task(plain: Path) -> None:
    """AC-4/R-11. expected_behavior_source: AC-4 ("An assignment that names a `task` appears only
    when `--task` names that task"); R-11."""
    write_project(plain, policy(via("quality", task="a-task")))

    named = resolve(plain, "--task", "a-task")
    other = resolve(plain, "--task", "another-task")
    absent = resolve(plain)

    assert named.data()["profile"] == "quality"
    assert named.data()["selection"]["model"] == A
    for unrelated in (other, absent):
        assert unrelated.data()["profile"] is None
        assert unrelated.data()["hint"] == NO_ASSIGNMENT


def test_a_valid_override_is_the_selection_and_the_override_is_not_printed(plain: Path) -> None:
    """AC-6/R-4/R-6. expected_behavior_source: R-4 ("A valid selected override gives source
    "task-override" and result "selected""); AC-6 (only catalog ids and fixed words are printed)."""
    write_project(plain, policy(pinned(A)))

    outcome = resolve(plain, "--override", f"{B}-{CLAUDE}[effort=high]")

    data = outcome.data()
    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert data["source"] == "task-override"
    assert data["result"] == "selected"
    assert data["selection"]["model"] == B
    assert "[effort=high]" not in outcome.shown


@pytest.mark.parametrize(
    "override", [f"{PROPOSED}-{CLAUDE}", "blocked-alias", "blocked-alias[effort=high]"]
)
def test_an_override_that_is_rejected_is_override_invalid(plain: Path, override: str) -> None:
    """AC-6/R-4. expected_behavior_source: AC-6 ("an override that matches an exclusion or fails a
    constraint is `override-invalid`"); R-4 (every rejection at the override level is shown with
    reason `override-invalid`; `model` is the matched catalog id, or null; the reason `excluded`
    never appears in `rejected`)."""
    write_project(plain, policy())

    outcome = resolve(plain, "--override", override)

    data = outcome.data()
    assert outcome.code == int(ExitCode.PROBLEMS), outcome.shown
    assert [item["reason"] for item in data["rejected"]] == ["override-invalid"]
    assert data["rejected"][0]["model"] in (PROPOSED, None)
    assert "excluded" not in outcome.shown
    # AC-6 allows a catalog id in the output. `PROPOSED` is a prefix of the first override, so it is
    # taken out before the check: the rest of the override must not show.
    assert not leaks(outcome.shown.replace(PROPOSED, ""), override, width=12)


def test_a_model_that_a_profile_lists_and_that_is_not_approved_is_rejected(plain: Path) -> None:
    """AC-2/R-6. expected_behavior_source: AC-2 (`rejected`: each `model` and `reason`, a reason of
    the closed set); R-6 (in the resolution's order)."""
    document = policy(via("quality"), profiles=[profile_doc("quality", candidates=[PROPOSED, A])])
    write_project(plain, document)

    outcome = resolve(plain)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["rejected"] == [{"model": PROPOSED, "reason": "not-approved"}]
    assert outcome.data()["selection"]["model"] == A


# --- AC-3, R-8: the text output ------------------------------------------------------------------


@EVERY_OK
def test_the_text_output_is_ten_lines_with_the_labels_in_order(plain: Path, name: str) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 ("The text output has one line each for `target`,
    `policy`, `profile`, `source`, `selected`, `candidates`, `fallbacks`, `escalation`, `rejected`
    and `hint`"); R-8 (ten lines, `label: value`, the labels in this order)."""
    scenario = OK_SCENARIOS[name]
    stage(plain, scenario)

    outcome = invoke(plain, *scenario.args)

    assert outcome.code == scenario.code, outcome.shown
    assert len(outcome.stdout.strip().splitlines()) == 10
    assert set(lines_of(outcome)) == set(LABELS)


def test_the_selected_line_has_the_name_the_kind_the_effort_and_the_catalog_id(
    plain: Path,
) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 ("`selected` (the name, its kind, its effort and
    the catalog id, or "the client chooses")"); R-8 (pin the presence of values, not the
    punctuation). The route of this model is not named after its id, so the two are told apart."""
    write_project(plain, policy(pinned(RENAMED, effort="xhigh")))

    selected = lines_of(resolve(plain, as_json=False))["selected"]

    assert f"renamed-route-{CLAUDE}" in selected
    assert RENAMED in selected
    assert re.search(r"\bid\b", selected)
    assert "xhigh" in selected
    assert CHOOSES not in selected


def test_the_selected_line_of_an_alias_route_says_alias(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 (the `selected` line holds the kind of the route);
    R-6 (`kind` is that of the route)."""
    write_project(plain, policy(pinned(ALIAS)))

    selected = lines_of(resolve(plain, as_json=False))["selected"]

    assert f"{ALIAS}-{CLAUDE}" in selected
    assert re.search(r"\balias\b", selected)


def test_the_text_output_names_the_target_the_policy_the_profile_and_the_source(
    plain: Path,
) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 (a line each for `target`, `policy`, `profile` and
    `source`); R-8 (the presence of values); R-6 (`profile` and `source` come from the
    resolution)."""
    write_project(plain, policy(via("quality")))

    values = lines_of(resolve(plain, as_json=False))

    assert TESTER in values["target"]
    assert "role" in values["target"]
    assert "present" in values["policy"]
    assert "quality" in values["profile"]
    assert "profile-assignment" in values["source"]


def test_the_text_output_of_a_target_of_another_kind_names_the_kind(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 (`target`); R-6 (`target` is `{kind, name}`)."""
    write_project(plain, policy(assignment_doc("skill", DESIGN, model=A)))

    values = lines_of(invoke(plain, "--client", CLAUDE, "--skill", DESIGN))

    assert DESIGN in values["target"]
    assert "skill" in values["target"]


def test_the_text_output_of_no_policy_says_absent(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: R-6 (`policy` is "present" or "absent"); AC-3 (exit 0
    and the hint "no model policy; the client chooses")."""
    outcome = resolve(plain, as_json=False)

    values = lines_of(outcome)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert "absent" in values["policy"]
    assert values["hint"] == NO_POLICY
    assert CHOOSES in values["selected"]


def test_the_lines_of_the_lists_name_the_models_and_the_escalation(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 (a line each for `candidates`, `fallbacks` and
    `escalation`); R-8 (the presence of values, not the punctuation); R-6 (the lists come from the
    resolution)."""
    write_project(plain, policy(via("engineering", "automatic-with-fallbacks")))

    values = lines_of(resolve(plain, as_json=False))

    for model in (B, C):
        assert model in values["candidates"]
    for model in (D, A):
        assert model in values["fallbacks"]
    assert "quality" in values["escalation"]
    assert CHOOSES in values["selected"]


def test_the_rejected_line_names_the_model_and_the_reason(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 (a line for `rejected`); R-8 (the presence of
    values); AC-2 (`rejected`: `model` and `reason`)."""
    document = policy(via("quality"), profiles=[profile_doc("quality", candidates=[PROPOSED, A])])
    write_project(plain, document)

    values = lines_of(resolve(plain, as_json=False))

    assert PROPOSED in values["rejected"]
    assert "not-approved" in values["rejected"]


def test_an_automatic_result_says_the_client_chooses(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: AC-3 (`selected` holds ... "the client chooses"); R-8
    (`selected` holds name, kind, effort and catalog id, or "the client chooses")."""
    write_project(plain, mode_policy("automatic"))

    outcome = resolve(plain, as_json=False)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert CHOOSES in lines_of(outcome)["selected"]


def test_a_result_with_no_candidate_does_not_say_the_client_chooses(plain: Path) -> None:
    """AC-3/R-8. expected_behavior_source: R-8 ("For none-qualifies pin only that it is not "the
    client chooses""); R-7 (none-qualifies is exit 1)."""
    write_project(plain, NO_CANDIDATE)

    outcome = resolve(plain, as_json=False)

    assert outcome.code == int(ExitCode.PROBLEMS), outcome.shown
    assert CHOOSES not in lines_of(outcome)["selected"]


def test_the_hint_of_a_profile_is_the_fixed_sentence(plain: Path) -> None:
    """AC-4/R-5. expected_behavior_source: AC-4 ("Suggested for this work: profile <id>; the client
    keeps the choice and nothing here changes the model." for a target that has a profile); R-5."""
    write_project(plain, policy(via("economy", "automatic")))

    as_json = resolve(plain)
    as_text = lines_of(resolve(plain, as_json=False))

    assert as_json.data()["hint"] == suggested("economy")
    assert as_text["hint"] == suggested("economy")


def test_the_hint_of_a_profile_target_is_the_fixed_sentence(plain: Path) -> None:
    """AC-4/R-5/R-12. expected_behavior_source: AC-4 (the sentence for a target that has a
    profile); R-12 (a profile target resolves the profile itself)."""
    write_project(plain, policy())

    outcome = invoke(plain, "--client", CLAUDE, "--profile", "economy", as_json=True)

    assert outcome.data()["hint"] == suggested("economy")


def test_the_hint_of_a_target_that_the_policy_does_not_assign(plain: Path) -> None:
    """AC-4/R-5. expected_behavior_source: AC-4 ("no assignment for this target; the client
    chooses" for a target that a present policy does not assign); R-5."""
    write_project(plain, policy(pinned(A)))

    as_json = invoke(plain, "--client", CLAUDE, "--role", INVENTORY, as_json=True)
    as_text = lines_of(invoke(plain, "--client", CLAUDE, "--role", INVENTORY))

    assert as_json.data()["hint"] == NO_ASSIGNMENT
    assert as_text["hint"] == NO_ASSIGNMENT


def test_the_hint_after_a_valid_override_is_that_of_the_same_request_without_it(
    plain: Path,
) -> None:
    """AC-4/R-5. expected_behavior_source: R-5 ("After a valid override, use the profile of the
    same request resolved without the override")."""
    write_project(plain, policy(via("economy", "automatic")))

    outcome = resolve(plain, "--override", f"{B}-{CLAUDE}")

    assert outcome.data()["source"] == "task-override"
    assert outcome.data()["hint"] == suggested("economy")


def test_the_hint_with_no_policy_does_not_depend_on_the_target(plain: Path) -> None:
    """AC-4/R-5. expected_behavior_source: AC-4 ("no model policy; the client chooses" when there
    is no policy); R-5."""
    for target in (("--role", TESTER), ("--skill", DESIGN), ("--profile", "quality")):
        outcome = invoke(plain, "--client", CODEX, *target, as_json=True)

        assert outcome.data()["hint"] == NO_POLICY, target


# --- AC-5, R-10: a folder that is not a git repository -------------------------------------------

SAME_OUTPUT_SCENARIOS = {
    "selected": Scenario(policy(via("quality")), TESTER_ARGS, 0),
    "automatic": Scenario(mode_policy("automatic"), TESTER_ARGS, 0),
    "no-candidate": NONE_SCENARIOS["no-candidate"],
    "override": SELECTED_SCENARIOS["override"],
    "refused": REFUSED_SCENARIOS["unknown-model"][0],
}


@needs_git
@pytest.mark.parametrize("name", list(SAME_OUTPUT_SCENARIOS))
def test_the_output_is_the_same_in_a_folder_that_is_not_a_git_repository(
    tmp_path: Path, name: str
) -> None:
    """AC-5/R-10b. expected_behavior_source: AC-5 ("the command runs in a folder that is not a git
    repository with the same output"); R-10b (a folder that is not a git repository (assert no
    `.git`) gives exit 0 and byte-identical output to the same project inside a `git init`
    repo). The repository has one commit that holds the policy; `invoke` fails the test on any
    git, process or clock use."""
    scenario = SAME_OUTPUT_SCENARIOS[name]
    plain_root = tmp_path / "plain"
    plain_root.mkdir()
    stage(plain_root, scenario)
    repository = make_repo(tmp_path / "repository")
    if isinstance(scenario.content, bytes | dict):
        raw = scenario.content if isinstance(scenario.content, bytes) else raw_of(scenario.content)
        commit_file(repository, POLICY, raw.decode("utf-8"))
    assert not any((folder / ".git").exists() for folder in (plain_root, *plain_root.parents))
    assert (repository / ".git").is_dir()

    for as_json in (False, True):
        outside = invoke(plain_root, *scenario.args, as_json=as_json)
        inside = invoke(repository, *scenario.args, as_json=as_json)

        assert outside.code == scenario.code, outside.shown
        assert outside == inside


@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
def test_a_folder_that_is_not_a_git_repository_gives_exit_0_and_an_answer(
    plain: Path, as_json: bool
) -> None:
    """AC-5/R-10b. expected_behavior_source: R-10b ("a folder that is not a git repo (assert no
    `.git`) gives exit 0"); AC-5."""
    write_project(plain, policy(via("quality")))
    assert not (plain / ".git").exists()

    outcome = resolve(plain, as_json=as_json)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert "git" not in outcome.shown.lower()


# --- R-9: what the output never prints -----------------------------------------------------------


def marked_policy() -> tuple[Doc, dict[str, str]]:
    """A policy whose every field that AC-2 does not print holds a marker, and its markers."""
    markers = {
        label: marker(label)
        for label in (
            "approved-by",
            "approval-ref",
            "evidence",
            "price-source",
            "exclusion-reason",
            "exclusion-source",
            "capability",
        )
    }
    priced = entry(
        A,
        *routes_of(A),
        family="family-one",
        price=("3", "15"),
        approved_by=markers["approved-by"],
        approval_ref=markers["approval-ref"],
        evidence=f"docs/{markers['evidence']}.md",
        price_source=f"docs/{markers['price-source']}.md",
    )
    document = policy(
        via("quality"),
        models=[priced, CATALOG[1]],
        profiles=[
            profile_doc(
                "quality", candidates=[A, B], fallbacks=[B], capability=markers["capability"]
            )
        ],
        excluded=[
            exclusion(
                "marked-rule",
                aliases=["blocked-alias"],
                reason=markers["exclusion-reason"],
                source=markers["exclusion-source"],
            )
        ],
    )
    return document, markers


@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize(
    ("client", "extra"),
    [
        (CLAUDE, ()),
        (CLAUDE, ("--override", f"{B}-{CLAUDE}")),
        (CLAUDE, ("--override", "blocked-alias")),
        (CLAUDE, ("--different-family-from", A)),
        (CLAUDE, ("--different-family-from", "example-missing")),
        (CODEX, ()),
    ],
    ids=["selected", "override", "excluded-override", "coder-constraint", "none", "codex"],
)
def test_a_value_of_the_file_that_the_criterion_does_not_print_is_never_printed(
    plain: Path, client: str, extra: tuple[str, ...], as_json: bool
) -> None:
    """AC-2/AC-6/R-9. expected_behavior_source: R-9 ("File values that AC-2 does not print must
    never appear either: `approval.approved_by`, `approval.approval_ref`, `documented.evidence`,
    `list_price.source`, an exclusion's `reason` and `source`, a profile's `capability`; check
    stdout and stderr, text and JSON"); BC-32."""
    document, markers = marked_policy()
    write_project(plain, document)

    outcome = invoke(plain, "--client", client, "--role", TESTER, *extra, as_json=as_json)

    assert outcome.code in (int(ExitCode.OK), int(ExitCode.PROBLEMS)), outcome.shown
    for label, value in markers.items():
        assert not leaks(outcome.shown, value), label


def test_a_value_that_the_criterion_prints_is_printed(plain: Path) -> None:
    """AC-2/R-9. expected_behavior_source: R-9 ("Values AC-2 does print (route name,
    also_known_as, catalog ids, prices) are printed")."""
    write_project(plain, policy(via("quality")))

    outcome = resolve(plain)
    text = resolve(plain, as_json=False)

    for printed in (A, f"{A}-{CLAUDE}", B, "3", "15"):
        assert printed in outcome.stdout, printed
    for printed in (A, f"{A}-{CLAUDE}", B):
        assert printed in text.stdout, printed
    assert ALSO_A in outcome.stdout


@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("name", ["whole", "in-an-alias", "valid-model", "invalid-model"])
def test_the_override_string_is_never_printed(plain: Path, name: str, as_json: bool) -> None:
    """AC-6/R-4/R-9. expected_behavior_source: AC-6 ("the output never prints the override string,
    only catalog ids that passed `ModelRef` and fixed words"); R-9 (the override as a whole, and
    inside `<excluded-alias>[<marker>=1]`, never appears in any output, text or JSON)."""
    mark = marker("override")
    overrides = {
        "whole": mark,
        "in-an-alias": f"blocked-alias[{mark}=1]",
        "valid-model": f"{B}-{CLAUDE}[{mark}=1]",
        "invalid-model": f"{PROPOSED}-{CLAUDE}[{mark}=1]",
    }
    write_project(plain, policy(pinned(A)))

    outcome = resolve(plain, "--override", overrides[name], as_json=as_json)

    assert outcome.code in (int(ExitCode.OK), int(ExitCode.PROBLEMS)), outcome.shown
    assert not leaks(outcome.shown, mark)


@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize(
    "name", ["unknown-key", "bad-value", "bad-state", "duplicate-key", "credential"]
)
def test_no_value_of_a_refused_file_is_printed(plain: Path, name: str, as_json: bool) -> None:
    """AC-3/R-3/R-9. expected_behavior_source: R-9 ("any value of a refused file"); BC-32;
    ORQLET-SEC-003 (a credential is never put in a message)."""
    mark = marker("value")
    files = {
        "unknown-key": raw_of({**policy(), mark: 1}),
        "bad-value": raw_of({**policy(), "policy_version": mark}),
        "bad-state": raw_of(policy(models=[entry(A, *routes_of(A), family="f", state=mark)])),
        "duplicate-key": f"{mark}: 1\n{mark}: 2\n".encode(),
        "credential": raw_of(policy()) + f"\n# {mark} {CREDENTIAL}\n".encode(),
    }
    write_project(plain, files[name])

    outcome = resolve(plain, as_json=as_json)

    assert outcome.code == int(ExitCode.REFUSED), outcome.shown
    assert not leaks(outcome.shown, mark)
    assert not leaks(outcome.shown, CREDENTIAL)


# --- R-14: the size limit of the policy ----------------------------------------------------------


def test_a_policy_of_exactly_256_kib_is_read(plain: Path) -> None:
    """AC-3/R-14. expected_behavior_source: R-14 ("a policy of exactly 262144 bytes is read")."""
    raw = pad(raw_of(policy(pinned(A))), LIMIT)
    assert len(raw) == LIMIT
    write_project(plain, raw)

    outcome = resolve(plain)

    assert outcome.code == int(ExitCode.OK), outcome.shown
    assert outcome.data()["selection"]["model"] == A


def test_a_policy_one_byte_over_256_kib_is_refused_and_not_printed(plain: Path) -> None:
    """AC-3/R-3/R-14. expected_behavior_source: R-14 ("262145 bytes is refused as ORQ-E540 with
    exit 3 and no content printed"); the reader checks 256 KiB before it parses."""
    raw = pad(raw_of(policy(pinned(A))), LIMIT + 1)
    assert len(raw) == LIMIT + 1
    write_project(plain, raw)

    as_json = resolve(plain)
    as_text = resolve(plain, as_json=False)

    assert as_json.code == int(ExitCode.REFUSED), as_json.shown
    assert as_json.codes() == [E540]
    assert as_text.code == int(ExitCode.REFUSED), as_text.shown
    for outcome in (as_json, as_text):
        assert "xxxxxxxx" not in outcome.shown
        assert A not in outcome.shown
