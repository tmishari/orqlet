"""A render request built from the real packaged workflow, for golden and renderer tests."""

from __future__ import annotations

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.ports.instruction_adapter import RenderRequest
from orqlet.application.usecases.render_request import build_render_request
from orqlet.domain.resolver import Enforcement, Level, RuleSpec, Scope, Waiver

# The commands the packaged workflow ships, in name order.
COMMAND_NAMES = ("doctor", "profile", "standards", "upgrade")
# The skills and roles the packaged workflow ships in this release.
SKILL_NAMES = (
    "orqlet-design",
    "orqlet-implement",
    "orqlet-onboard",
    "orqlet-plan",
    "orqlet-research",
    "orqlet-review",
)
SKILL_REFERENCES = {
    "orqlet-design": ("design-format.md",),
    "orqlet-plan": ("plan-format.md",),
    "orqlet-research": ("as-is-format.md",),
    "orqlet-review": ("review-format.md",),
}
ROLE_NAMES = (
    "orqlet-arch-reviewer",
    "orqlet-inventory",
    "orqlet-security-reviewer",
    "orqlet-tester",
    "orqlet-tracer",
)
READ_ONLY_ROLES = tuple(name for name in ROLE_NAMES if name != "orqlet-tester")


def skill_files(base: str) -> list[str]:
    """Every file of every skill under `base` (`.claude/skills` or `.agents/skills`)."""
    paths = []
    for name in SKILL_NAMES:
        paths.append(f"{base}/{name}/SKILL.md")
        paths += [f"{base}/{name}/references/{ref}" for ref in SKILL_REFERENCES.get(name, ())]
    return paths


SAMPLE_RULES = (
    RuleSpec(
        id="SAMPLE-001",
        level=Level.MUST,
        waiver=Waiver.NONE,
        enforcement=Enforcement.DETERMINISTIC,
        scope=Scope(paths=frozenset({"src/**"})),
        text="Public functions have type annotations.",
        source="sample@1.0.0",
    ),
    RuleSpec(
        id="SAMPLE-002",
        level=Level.SHOULD,
        waiver=Waiver.REVIEWED,
        enforcement=Enforcement.GUIDANCE,
        scope=Scope(paths=frozenset({"src/**"})),
        text="Prefer small functions.",
        source="sample@1.0.0",
    ),
    RuleSpec(
        id="SAMPLE-003",
        level=Level.MUST,
        waiver=Waiver.NONE,
        enforcement=Enforcement.REVIEW,
        scope=Scope(roles=frozenset({"architect"}), phases=frozenset({"design"})),
        text="Designs are reviewed before implementation.",
        source="sample@1.0.0",
    ),
)


def packaged_request(rules: tuple[RuleSpec, ...] = SAMPLE_RULES) -> RenderRequest:
    return build_render_request(PackagedWorkflow(), StrictYamlLoader(), rules)
