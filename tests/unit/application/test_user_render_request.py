"""The user-scope render request (task one-command-setup, phase P-7, AC-1 and AC-7's request half).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-7 in
docs/design/one-command-setup/plan.yaml; BC-n are the acceptance rows of
docs/design/one-command-setup/design/component.md section 6; ADR-002 is
design/adr-002-user-scope-root-journal-and-manifest.md (decision 7: a user request carries only the
packaged skills, roles and entry skill, the bundled skills and the foundation text as the baseline
body, and no model settings, conventions, integrations, scoped rules or resources); ADR-005 is
design/adr-005-behavioural-foundation.md (decision 2: one source for every global copy); and
component.md section 4 names `RenderRequest.scope: RenderScope` with the values `project` and
`user`.

HOW THESE TESTS WERE WRITTEN. The Tester of P-7 wrote them before the implementation existed. The
interface below is the Tester's reading of the design, which names no function; the Coder aligns
with it or raises it:
- `RenderScope` is an enum in `orqlet.application.ports.instruction_adapter` with the members
  `PROJECT` and `USER` (the member case follows the other enums of the code base; the design
  writes `RenderScope.project` and `RenderScope.user`);
- `RenderRequest.scope` defaults to `RenderScope.PROJECT`, so every existing request keeps its
  meaning (AC-8);
- `build_user_render_request(workflow)` in `orqlet.application.usecases.user_render_request` builds
  the request from the workflow package alone. `install` runs outside any repository, so there is no
  profile to pass, and AC-1's "a profile with a model policy, conventions and integrations gives
  the same user request as one without" is read as: the builder takes no profile, policy,
  selection, conventions, integrations, resources or rules at all.

Choices:
- "every packaged skill" and "the roles" are compared with the project request of an installation
  with no registry, no conventions and no model policy (`packaged_request`), which holds exactly
  the packaged skills and roles with no model setting. The entry skill joins `SKILL_NAMES` in
  tests/support/render.py when P-10 adds it.
- "the foundation as the baseline body" is `compose_foundation` of the same workflow (P-3).

Deliberately NOT pinned here:
- the `client_version` of a user request;
- any keyword argument the builder may take beyond `workflow` whose name is not one of the inputs
  that ADR-002 decision 7 excludes.
"""

from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.integrations import Integrations
from orqlet.application.contracts.loading import load_contract
from orqlet.application.ports.instruction_adapter import ModelSetting, RenderRequest, RenderScope
from orqlet.application.usecases.foundation import compose_foundation
from orqlet.application.usecases.model_selection import ModelSelection
from orqlet.application.usecases.render_request import build_render_request
from orqlet.application.usecases.resources_view import conventions_view
from orqlet.application.usecases.user_render_request import build_user_render_request
from tests.support.render import (
    ROLE_NAMES,
    SAMPLE_RESOURCES,
    SAMPLE_RULES,
    SKILL_NAMES,
    packaged_request,
    sample_profile,
)
from tests.support.trees import FIXTURES

pytestmark = pytest.mark.unit

INTEGRATIONS_FIXTURE = FIXTURES / "contracts" / "valid" / "orqlet.integrations.v1.yaml"
# Inputs that ADR-002 decision 7 keeps out of a user request; none may be a builder parameter.
EXCLUDED_INPUTS = frozenset(
    {
        "profile",
        "policy",
        "model_policy",
        "selection",
        "conventions",
        "integrations",
        "resources",
        "rules",
    }
)
# Placeholder model names, one per client, that a team's policy could assign.
EXAMPLE_SETTINGS = {
    "claude-code": ModelSetting("example-claude-model", "id", "high"),
    "cursor": ModelSetting("example-cursor-model", "id"),
    "codex": ModelSetting("example-codex-model", "id", "medium"),
}


def user_request() -> RenderRequest:
    return build_user_render_request(PackagedWorkflow())


def rich_project_request() -> RenderRequest:
    """A project request with a model policy, conventions, integrations, resources and rules."""
    conventions, _ = conventions_view(sample_profile(), SAMPLE_RESOURCES)
    selection = ModelSelection(
        roles=dict.fromkeys(ROLE_NAMES, EXAMPLE_SETTINGS),
        skills=dict.fromkeys(SKILL_NAMES, EXAMPLE_SETTINGS),
    )
    request = build_render_request(
        PackagedWorkflow(),
        StrictYamlLoader(),
        SAMPLE_RULES,
        SAMPLE_RESOURCES,
        conventions,
        selection=selection,
    )
    integrations = load_contract(
        StrictYamlLoader(),
        Integrations,
        INTEGRATIONS_FIXTURE.read_bytes(),
        source="fixture",
    )
    return replace(request, integrations=integrations)


# --- AC-1: packaged content only ------------------------------------------------------------------


def test_ac1_the_user_request_has_the_user_scope() -> None:
    """AC-1. expected_behavior_source: ADR-002 decision 7 ("Adapters receive a `RenderScope` of
    `project` or `user`"); component.md section 4 (`RenderRequest.scope: RenderScope`)."""
    assert user_request().scope is RenderScope.USER


def test_ac1_the_user_request_carries_every_packaged_skill_with_no_model_setting() -> None:
    """AC-1. expected_behavior_source: AC-1 ("carries every packaged skill (the phase and bundled
    skills here; the entry skill once P-10 adds it)"); ADR-002 decision 7 (the packaged skills,
    the entry skill and the bundled skills); ORQLET-MODEL-001."""
    skills = user_request().skills

    assert tuple(skill.name for skill in skills) == SKILL_NAMES
    assert skills == packaged_request().skills
    assert all(not skill.model_settings for skill in skills)


def test_ac1_the_user_request_carries_the_roles_with_no_model_setting() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the roles"); ADR-002 decision 7 ("the packaged
    skills, roles and entry skill"); ORQLET-MODEL-001; ADR-002 Consequences ("User-scope agents
    carry no model setting")."""
    roles = user_request().roles

    assert tuple(role.name for role in roles) == ROLE_NAMES
    assert roles == packaged_request().roles
    assert all(not role.model_settings for role in roles)


def test_ac1_the_baseline_body_of_the_user_request_is_the_composed_foundation() -> None:
    """AC-1. expected_behavior_source: AC-1 ("the foundation as the baseline body"); ADR-002
    decision 7 ("the foundation text, as the baseline body"); ADR-005 decision 2 (one source)."""
    workflow = PackagedWorkflow()

    request = build_user_render_request(workflow)

    assert request.baseline_body == compose_foundation(workflow)
    assert request.workflow_version == str(workflow.release.version)


def test_ac1_the_user_request_has_no_conventions_integrations_rules_resources_or_commands() -> None:
    """AC-1. expected_behavior_source: AC-1 ("no model settings, conventions, integrations, scoped
    rules, resources or commands"); ADR-002 decision 7; BC-26. The team's resources would reach a
    request as scoped rules and as tool and catalogue skills; the skill list above holds only the
    packaged skills."""
    request = user_request()

    assert request.conventions is None
    assert request.integrations is None
    assert request.scoped_rules == ()
    assert request.commands == ()


def test_ac1_the_builder_takes_no_profile_policy_or_team_input() -> None:
    """AC-1. expected_behavior_source: AC-1 ("a profile with a model policy, conventions and
    integrations gives the same user request as one without"); ADR-002 decision 7 and its
    rejected alternative ("Applying the project's model policy to user-scope agents"); component.md
    section 3 (`install` runs from any directory). Read as: no such input can reach the builder."""
    parameters = inspect.signature(build_user_render_request).parameters
    empty = inspect.Parameter.empty

    required = [name for name, item in parameters.items() if item.default is empty]

    assert not EXCLUDED_INPUTS & set(parameters)
    assert required == ["workflow"]


def test_ac1_building_twice_gives_equal_requests() -> None:
    """AC-1. expected_behavior_source: AC-1 ("gives the same user request"); ORQLET-DET-001."""
    assert user_request() == user_request()


# --- AC-7, request side: nothing of the project request reaches the user request ------------------


def test_ac7_a_rich_project_request_leaves_nothing_in_the_user_request() -> None:
    """AC-7. expected_behavior_source: AC-7 ("even when the project request had them"); BC-26 ("No
    user-scope file contains a model name, a model setting, a convention, an integration or a
    resource link"); ADR-002 decision 7. The project request is built first, in the same process,
    with a model policy, conventions, integrations, the sample registry and the sample rules."""
    project = rich_project_request()
    assert project.conventions is not None
    assert project.integrations is not None
    assert any(role.model_settings for role in project.roles)
    assert len(project.skills) > len(SKILL_NAMES)

    user = user_request()

    assert user == build_user_render_request(PackagedWorkflow())
    assert user.conventions is None
    assert user.integrations is None
    assert user.scoped_rules == ()
    assert tuple(skill.name for skill in user.skills) == SKILL_NAMES
    assert all(not item.model_settings for item in (*user.skills, *user.roles))
