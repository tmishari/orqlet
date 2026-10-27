"""`orqlet explain`: what Orqlet declares, what it generated and what it cannot see (12.5)."""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.application.contracts.resources import Resources
from orqlet.application.usecases.diagnose import Drift, measure_drift
from orqlet.application.usecases.installation import load_installation
from orqlet.application.usecases.render_all import compose, resolve_for
from orqlet.application.usecases.resources_source import load_resources, resources_path
from orqlet.application.usecases.services import Services
from orqlet.application.usecases.standards_for import StandardsQuery
from orqlet.domain.findings import Finding
from orqlet.domain.resolver import RuleSpec, select

# Sources that shape what a client loads and that Orqlet cannot inspect from a repository.
UNINSPECTABLE = (
    "Cursor Team Rules and account User Rules",
    "Enterprise hooks and managed settings of any client",
    "Claude Code server-managed settings",
    "Codex cloud-managed requirements",
    "The state of Cursor's third-party instruction toggle",
)


@dataclass(frozen=True, slots=True)
class Explanation:
    declared: dict[str, object]
    generated: tuple[Drift, ...]
    limits: tuple[Finding, ...]
    rules: tuple[RuleSpec, ...]
    uninspectable: tuple[str, ...]
    not_run: tuple[str, ...]
    findings: tuple[Finding, ...] = ()


def explain(services: Services, query: StandardsQuery) -> Explanation:
    inst = load_installation(services)
    release = services.workflow.release
    resolution = resolve_for(services, inst.profile)
    resources, resource_findings = load_resources(
        services.project, services.loader, str(resources_path())
    )
    composition = compose(
        services,
        inst.profile,
        resolution,
        # An explanation builds no plan and so deletes nothing: it previews without the resource
        # files when the registry cannot be used, and prints the finding (ADR-002 decision 6).
        resources if resources is not None else Resources(schema_id="orqlet.resources/v1"),
        clients=inst.profile.clients.enabled,
        prompts_dir=".prompts",
        pr_targets=(),
        profile_bytes=b"",
        resources_bytes=b"",
    )
    limits = tuple(finding for finding in composition.findings if finding.code.startswith("ORQ-L"))
    declared: dict[str, object] = {
        "workflow_version": str(release.version),
        "workflow_digest": release.digest,
        "controls_level": release.controls_level,
        "installed_workflow_version": (
            None if inst.installed_release is None else str(inst.installed_release.version)
        ),
        "clients": list(inst.profile.clients.enabled),
        "technologies": [
            {"kind": t.kind, "name": t.name, "version": t.version, "scope": t.scope}
            for t in inst.profile.technologies
        ],
        "standards_sources": [
            {"kind": source.kind, "path": source.path} for source in inst.profile.standards_sources
        ],
        "released": sorted(inst.released),
    }
    packs_missing = (
        bool(inst.standards_lock and inst.standards_lock.packs) and services.packs is None
    )
    not_run = [
        "predicted-effective: a static emulation of each client's discovery rules is not part "
        "of this release",
    ]
    if packs_missing:
        not_run.append("pack rules: pass --packs-dir to include the rules of the pinned packs")
    not_run += [f"resource files: {finding.message}" for finding in resource_findings]
    return Explanation(
        declared=declared,
        generated=measure_drift(services.project, inst.recorded),
        limits=limits,
        rules=select(resolution.rules, path=query.path, role=query.role, phase=query.phase),
        uninspectable=UNINSPECTABLE,
        not_run=tuple(not_run),
        findings=resource_findings,
    )
