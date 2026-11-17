"""Every existing review record and plan still loads (task dynamic-model-profiles, P-1).

Each test names in `expected_behavior_source` the criterion that it checks (AC-7 of phase P-1 in
docs/design/dynamic-model-profiles/plan.yaml) and then the sources that the criterion lists. BC-n
and C-n are the behaviour and constraint rows of design/component.md, and ADR-007 is the decision
record on independence and model identity.

These tests were written first, by the Tester of phase P-1, before the change existed. They read
the review records and the plans that are committed under docs/design and load each one with the
contract that the change replaces. The closed set of clients narrows what a record may say, so
this is the check that decision 2 of ADR-007 asks for: a test, not a promise.

A file that fails is named by its path in the failure, whatever the contract says about it.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.common import Contract
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.contracts.review_result import ReviewResult
from orqlet.application.ports.documents import DocumentError

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs" / "design"
LOADER = StrictYamlLoader()

CLOSED_CLIENTS = frozenset({"claude-code", "codex", "cursor"})
SIDES = ("agent", "coder_binding")
# The criterion counts 112 records at the base revision; a task may add records, never remove one.
RECORDS_AT_THE_BASE_REVISION = 112
THIS_TASKS_PLAN = DESIGN / "dynamic-model-profiles" / "plan.yaml"
VALID_RECORD = ROOT / "tests" / "fixtures" / "contracts" / "valid" / "orqlet.review-result.v1.yaml"


def review_records() -> list[Path]:
    return sorted(DESIGN.glob("**/reviews/*.yaml"))


def plans() -> list[Path]:
    return sorted(DESIGN.glob("*/plan.yaml"))


def failures(paths: Sequence[Path], model: type[Contract], root: Path = ROOT) -> list[str]:
    """One line for each file that the contract refuses; each line starts with the file's path."""
    found: list[str] = []
    for path in paths:
        source = path.relative_to(root).as_posix()
        try:
            load_contract(LOADER, model, path.read_bytes(), source=source)
        except DocumentError as error:
            found.append(str(error))
    return found


def clients_named_by(paths: Sequence[Path]) -> dict[str, list[str]]:
    """Each client value of `agent` and `coder_binding`, with the records and sides that name it."""
    found: dict[str, list[str]] = {}
    for path in paths:
        source = path.relative_to(ROOT).as_posix()
        document = LOADER.load(path.read_bytes(), source=source)
        assert isinstance(document, dict), source
        for side in SIDES:
            binding = document.get(side)
            client = binding.get("client") if isinstance(binding, dict) else None
            found.setdefault(str(client), []).append(f"{source} ({side})")
    return found


def test_every_review_record_of_the_repository_loads_with_the_review_result() -> None:
    """expected_behavior_source: AC-7; BC-20; BC-42; C-7; ADR-007 decision 2.

    Every `docs/design/**/reviews/*.yaml` of the repository loads with the new `ReviewResult`; a
    file that fails is reported by its path.
    """
    refused = failures(review_records(), ReviewResult)

    assert not refused, "\n".join(refused)


def test_the_scan_reaches_at_least_the_112_records_of_the_base_revision() -> None:
    """expected_behavior_source: AC-7; BC-20; BC-42; C-7; ADR-007 decision 2.

    The repository holds 112 review records at the base revision. A glob that reaches fewer would
    pass the other tests by checking too little.
    """
    assert len(review_records()) >= RECORDS_AT_THE_BASE_REVISION


def test_the_distinct_clients_of_the_records_lie_inside_the_closed_set() -> None:
    """expected_behavior_source: AC-7; BC-20; BC-42; C-7; ADR-007 decision 2.

    The distinct client values among the records, in `agent.client` and `coder_binding.client`,
    lie inside `claude-code`, `codex` and `cursor`. A value outside names the records that hold it.
    """
    named = clients_named_by(review_records())
    outside = {client: files for client, files in named.items() if client not in CLOSED_CLIENTS}
    report = [f"{client!r} in {', '.join(files)}" for client, files in outside.items()]

    assert named, "no client was found in any record"
    assert not report, "\n".join(report)


def test_every_plan_of_the_repository_loads_with_the_implementation_plan() -> None:
    """expected_behavior_source: AC-7; BC-20; BC-42; C-7; ADR-007 decision 2.

    Every `docs/design/*/plan.yaml` loads with the new `ImplementationPlan`; a file that fails is
    reported by its path. The plan of this task is among them.
    """
    found = plans()
    refused = failures(found, ImplementationPlan)

    assert THIS_TASKS_PLAN in found
    assert not refused, "\n".join(refused)


def test_a_file_that_fails_is_reported_by_its_path(tmp_path: Path) -> None:
    """expected_behavior_source: AC-7; BC-20; BC-42; C-7; ADR-007 decision 2.

    "A file that fails is reported by its path": a record that the contract refuses comes back
    from `failures` with its path first, and a valid one does not come back.
    """
    reviews = tmp_path / "docs" / "design" / "demo" / "reviews"
    reviews.mkdir(parents=True)
    bad = reviews / "architecture-reviewer-P-1-r1.yaml"
    bad.write_text("schema: orqlet.review-result/v1\n", encoding="utf-8")
    good = reviews / "architecture-reviewer-P-1-r2.yaml"
    good.write_bytes(VALID_RECORD.read_bytes())

    reported = failures([bad, good], ReviewResult, root=tmp_path)

    assert len(reported) == 1
    assert reported[0].startswith("docs/design/demo/reviews/architecture-reviewer-P-1-r1.yaml: ")
