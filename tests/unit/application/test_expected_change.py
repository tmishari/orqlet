"""Reading two trees and comparing them with the design (proposal 17.4.1, FM-A01 to FM-A06)."""

from __future__ import annotations

from typing import Any

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.expected_change import (
    ExpectedChangeReport,
    evaluate_expected_changes,
)
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.expected_change import Outcome
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED
from tests.support.artifacts import design, phase, plan

pytestmark = pytest.mark.unit

BASE, TREE = "1" * 40, "2" * 40
DECLARED = "def create_order(customer_id: str) -> Order"

PYPROJECT = '[project]\nname = "x"\ndependencies = ["requests>=2"]\n'
LOCK = '[[package]]\nname = "requests"\n[[package]]\nname = "idna"\n'
BASE_FILES = {
    "src/pkg/__init__.py": b"",
    "src/pkg/service.py": b"def existing() -> None: ...\n",
    "pyproject.toml": PYPROJECT.encode(),
    "uv.lock": LOCK.encode(),
    "src/auth/login.py": b"def login(): ...\n",
}


def services(files: dict[str, bytes]) -> ValidateServices:
    vcs = FakeVcs(
        RepoState.HAS_COMMITS,
        commits=(CommitSummary(TREE, "head"),),
        committed=files,
        revisions={BASE: BASE_FILES, TREE: files},
    )
    return ValidateServices(
        project=MemoryFileSystem(), vcs=vcs, loader=StrictYamlLoader(), workflow=PINNED
    )


def entry(
    identifier: str, surface: str, action: str, identity: str, kind: str, value: str, **kw: Any
) -> dict[str, Any]:
    return {
        "id": identifier,
        "surface": surface,
        "action": action,
        "identity": identity,
        "expected_after": {"kind": kind, "value": value},
        "verification": kw.get("verification", "extractor"),
        **({"stages": kw["stages"]} if "stages" in kw else {}),
    }


def build(changes: list[dict[str, Any]], **config: Any) -> DesignSet:
    return DesignSet.model_validate(
        design(
            expected_changes=changes,
            extractor_config={"public_api": {"packages": ["pkg"], "mode": "ast"}, **config},
        )
    )


def run(
    files: dict[str, bytes],
    changes: list[dict[str, Any]],
    *,
    selected: list[str] | None = None,
    lock: list[str] | None = None,
    **config: Any,
) -> ExpectedChangeReport:
    phases = [phase(implements=selected or [], expected_lock_packages=lock or [])]
    parsed = ImplementationPlan.model_validate(plan(phases=phases))
    return evaluate_expected_changes(
        services(files), build(changes, **config), parsed, "P-1", BASE, TREE
    )


def outcomes(report: ExpectedChangeReport) -> list[tuple[str | None, Outcome]]:
    return [(r.id, r.outcome) for r in report.results]


API_ADD = entry("EC-1", "public-api", "add", "pkg.service.create_order", "signature", DECLARED)


def with_service(extra: str) -> dict[str, bytes]:
    return {**BASE_FILES, "src/pkg/service.py": BASE_FILES["src/pkg/service.py"] + extra.encode()}


def test_fm_a01_adding_the_declared_signature_is_implemented_and_nothing_else_changed() -> None:
    report = run(with_service(DECLARED + ": ...\n"), [API_ADD], selected=["EC-1"])

    assert outcomes(report) == [("EC-1", Outcome.IMPLEMENTED)]
    assert report.notes == ()


def test_fm_a02_a_second_public_function_that_no_entry_covers_is_additional() -> None:
    files = with_service(f"{DECLARED}: ...\ndef refund(order: Order) -> None: ...\n")

    report = run(files, [API_ADD], selected=["EC-1"])

    assert outcomes(report) == [("EC-1", Outcome.IMPLEMENTED), (None, Outcome.ADDITIONAL)]
    assert "pkg.service.refund" in report.results[1].detail


def test_an_entry_nobody_has_implemented_yet_is_pending_or_not_delivered() -> None:
    assert outcomes(run(BASE_FILES, [API_ADD])) == [("EC-1", Outcome.PENDING)]
    assert outcomes(run(BASE_FILES, [API_ADD], selected=["EC-1"])) == [
        ("EC-1", Outcome.NOT_DELIVERED)
    ]


def test_a_package_init_is_the_package_and_a_private_module_adds_nothing() -> None:
    files = {
        **BASE_FILES,
        "src/pkg/__init__.py": b"def top() -> int: ...\n",
        "src/pkg/_internal.py": b"def helper() -> int: ...\n",
    }

    report = run(
        files,
        [entry("EC-1", "public-api", "add", "pkg.top", "signature", "def top() -> int")],
        selected=["EC-1"],
    )

    assert outcomes(report) == [("EC-1", Outcome.IMPLEMENTED)]  # `_internal` adds nothing public


def test_a_module_that_hides_its_surface_makes_the_whole_surface_manual_with_a_note() -> None:
    files = with_service("from os.path import *\n")

    report = run(files, [API_ADD], selected=["EC-1"])

    assert outcomes(report) == [("EC-1", Outcome.MANUAL)]
    assert "star import" in report.notes[0]


def test_a_stage_selected_by_the_phase_is_the_expectation_that_applies() -> None:
    staged = entry(
        "EC-1",
        "public-api",
        "add",
        "pkg.service.create_order",
        "signature",
        DECLARED,
        stages=[
            {
                "id": "S-1",
                "expected_after": {"kind": "signature", "value": "def create_order() -> Order"},
            }
        ],
    )

    report = run(
        with_service("def create_order() -> Order: ...\n"), [staged], selected=["EC-1@S-1"]
    )

    assert outcomes(report) == [("EC-1", Outcome.IMPLEMENTED)]


DEPENDENCY = entry("EC-2", "dependency", "add", "httpx", "specifier", ">=0.27")


def dependency_files(spec: str = ">=0.27", lock_extra: str = "") -> dict[str, bytes]:
    return {
        **BASE_FILES,
        "pyproject.toml": PYPROJECT.replace(
            '"requests>=2"', f'"requests>=2", "httpx{spec}"'
        ).encode(),
        "uv.lock": (LOCK + lock_extra).encode(),
    }


def test_fm_a06_a_declared_dependency_and_its_lockfile_entry_are_implemented_as_designed() -> None:
    files = dependency_files(lock_extra='[[package]]\nname = "httpx"\n')

    report = run(
        files,
        [DEPENDENCY],
        selected=["EC-2"],
        dependency_manifests=["pyproject.toml"],
        lockfiles=["uv.lock"],
    )

    assert outcomes(report) == [("EC-2", Outcome.IMPLEMENTED)]


def test_fm_a06_a_different_specifier_deviates_and_an_extra_locked_package_is_additional() -> None:
    files = dependency_files(
        spec=">=0.20", lock_extra='[[package]]\nname = "httpx"\n[[package]]\nname = "h11"\n'
    )

    report = run(
        files,
        [DEPENDENCY],
        selected=["EC-2"],
        dependency_manifests=["pyproject.toml"],
        lockfiles=["uv.lock"],
    )

    assert outcomes(report) == [("EC-2", Outcome.DEVIATION), (None, Outcome.ADDITIONAL)]
    assert "h11" in report.results[1].detail


def test_a_lock_package_the_phase_lists_is_expected() -> None:
    files = dependency_files(lock_extra='[[package]]\nname = "httpx"\n[[package]]\nname = "h11"\n')

    report = run(
        files,
        [DEPENDENCY],
        selected=["EC-2"],
        lock=["h11"],
        dependency_manifests=["pyproject.toml"],
        lockfiles=["uv.lock"],
    )

    assert outcomes(report) == [("EC-2", Outcome.IMPLEMENTED)]


def test_a_manifest_this_release_cannot_read_and_a_lockfile_in_another_format_are_noted() -> None:
    files = {**BASE_FILES, "requirements.txt": b"requests==2\n", "uv.lock": b"not toml ["}

    report = run(files, [], dependency_manifests=["requirements.txt"], lockfiles=["uv.lock"])

    assert any("requirements.txt" in note and "by hand" in note for note in report.notes)
    assert any("uv.lock" in note for note in report.notes)


SECURITY = entry("EC-3", "security", "change", "login", "paths", "src/auth/login.py")


def test_fm_a04_a_change_on_a_security_path_the_design_declared_is_implemented() -> None:
    files = {**BASE_FILES, "src/auth/login.py": b"def login(): return 1\n"}

    report = run(files, [SECURITY], selected=["EC-3"], security_globs=["src/auth/**"])

    assert outcomes(report) == [("EC-3", Outcome.IMPLEMENTED)]


def test_fm_a04_an_unexpected_change_on_a_security_path_is_additional_or_a_deviation() -> None:
    files = {**BASE_FILES, "src/auth/crypto.py": b"def key(): ...\n"}

    additional = run(files, [], security_globs=["src/auth/**"])
    deviation = run(
        {**files, "src/auth/login.py": b"def login(): return 1\n"},
        [SECURITY],
        selected=["EC-3"],
        security_globs=["src/auth/**"],
    )

    assert outcomes(additional) == [(None, Outcome.ADDITIONAL)]
    assert outcomes(deviation) == [("EC-3", Outcome.DEVIATION)]


def test_fm_a03_a_migration_the_design_declared_is_not_a_surprise_and_a_new_one_is() -> None:
    files = {**BASE_FILES, "db/migrations/0002_orders.sql": b"create table t();\n"}

    declared = run(files, [], migration_paths=["db/migrations/**"])
    undeclared = run(files, [])

    assert outcomes(declared) == []
    assert outcomes(undeclared) == [(None, Outcome.ADDITIONAL)]


def test_without_a_plan_every_phase_counts_as_selecting() -> None:
    parsed = None
    report = evaluate_expected_changes(
        services(BASE_FILES), build([API_ADD]), parsed, None, BASE, TREE
    )

    assert outcomes(report) == [("EC-1", Outcome.PENDING)]
