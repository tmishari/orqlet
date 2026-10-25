"""A change of the workflow digest without a change of the workflow version is a release defect."""

from __future__ import annotations

import pytest

from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.domain.versions import check_release_history

pytestmark = pytest.mark.contract


def test_the_current_workflow_is_consistent_with_the_release_history() -> None:
    workflow = PackagedWorkflow()

    problems = check_release_history(workflow.release, workflow.history())

    assert problems == (), (
        "The workflow changed after its version was released. "
        "Raise workflow_version in identity.json (and controls_level if a control was added), "
        "then run: uv run python tools/build_manifest.py"
    )


def test_the_release_history_is_readable_and_well_formed() -> None:
    history = PackagedWorkflow().history()

    assert len({release.version for release in history}) == len(history)
