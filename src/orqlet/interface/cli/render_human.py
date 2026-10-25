"""Plain text output for people. No colour codes, so it reads the same in a log."""

from __future__ import annotations

from orqlet.application.usecases.diagnose import Diagnosis
from orqlet.application.usecases.explain import Explanation
from orqlet.application.usecases.init_project import InitResult
from orqlet.application.usecases.profile_edit import ProfileEditResult
from orqlet.application.usecases.release import ReleaseResult
from orqlet.application.usecases.rollback import RollbackResult
from orqlet.application.usecases.standards_for import StandardsAnswer
from orqlet.application.usecases.upgrade import UpgradeResult
from orqlet.application.usecases.validation import ValidationResult
from orqlet.domain.findings import Severity


def render_standards(answer: StandardsAnswer) -> str:
    lines = [f"{len(answer.rules)} rule(s) apply. applicable_rules_hash: {answer.rules_hash}", ""]
    for rule in answer.rules:
        where = ", ".join(sorted(rule.scope.paths | rule.scope.roles | rule.scope.phases))
        scope = f" [{where}]" if where else ""
        lines.append(f"{rule.level.name:<6} {rule.id}{scope} ({rule.enforcement.name.lower()})")
        lines.append(f"       {rule.text}")
    if answer.packs:
        lines += ["", "Packs: " + ", ".join(f"{p.id}@{p.version}" for p in answer.packs)]
    for pack_id, reason in answer.skipped:
        lines.append(f"Skipped {pack_id}: {reason}")
    for note in answer.not_run:
        lines.append(f"Not run: {note}")
    return "\n".join(lines)


def render_init(result: InitResult) -> str:
    """What `init` did or would do, in plain words."""
    headline = {
        "applied": "Applied.",
        "previewed": "Preview only. Nothing was written.",
        "already-initialised": "Already initialised. Nothing was written.",
        "needs-input": "Nothing was written: an answer or an approval is missing.",
        "refused": "Refused. Nothing was written.",
    }[result.status]
    lines = [headline]
    if result.plan is not None:
        lines.append("")
        lines += [f"  {write.kind:<6} {write.path}" for write in result.plan.writes] or [
            "  no file changes"
        ]
        stopped = list(result.plan.conflicts)
        lines += [f"  CONFLICT {item.path}: {item.reason or item.state.value}" for item in stopped]
    if result.change_id:
        lines += ["", _change_line(result.change_id)]
    if result.git_initialised:
        lines += ["", "A Git repository was created. Nothing was committed."]
    if result.open_questions:
        lines += ["", "Still unknown (answer with --answer KEY=VALUE or run init again):"]
        lines += [f"  {question.id}: {question.text}" for question in result.open_questions]
    return "\n".join(lines)


def _change_line(change_id: str) -> str:
    return f"Change id: {change_id}  (undo it with: orqlet rollback {change_id})"


def _plan_lines(plan: object) -> list[str]:
    writes = getattr(plan, "writes", ()) if plan is not None else ()
    return [f"  {w.kind:<6} {w.path}" for w in writes] or ["  no file changes"]


def render_upgrade(result: UpgradeResult) -> str:
    headline = {
        "up-to-date": "Already up to date.",
        "available": "An upgrade is available. Nothing was written.",
        "applied": "Upgraded.",
        "previewed": "Preview only. Nothing was written.",
        "needs-input": "Nothing was written: an approval is missing.",
        "refused": "Refused. Nothing was written.",
    }[result.status]
    lines = [headline]
    if result.installed is not None and result.candidate is not None:
        lines.append(f"Workflow {result.installed.version} -> {result.candidate.version}")
    if result.plan is not None and result.status != "up-to-date":
        lines += ["", *_plan_lines(result.plan)]
    if result.change_id:
        lines += ["", _change_line(result.change_id)]
    return "\n".join(lines)


def render_rollback(result: RollbackResult) -> str:
    headline = {
        "applied": "Rolled back.",
        "previewed": "Preview only. Nothing was written.",
        "needs-input": "Nothing was written: an approval is missing.",
        "refused": "Refused. Nothing was written.",
    }[result.status]
    return "\n".join([headline, "", *_plan_lines(result.plan)] if result.plan else [headline])


def render_release(result: ReleaseResult) -> str:
    headline = {
        "applied": "Released. The file is now the team's.",
        "previewed": "Preview only. Nothing was written.",
        "needs-input": "Nothing was written: an approval is missing.",
        "refused": "Refused. Nothing was written.",
    }[result.status]
    lines = [headline, "", *_plan_lines(result.plan)] if result.plan else [headline]
    if result.change_id:
        lines += ["", _change_line(result.change_id)]
    return "\n".join(lines)


def render_diagnosis(diagnosis: Diagnosis) -> str:
    counts = {s: sum(1 for f in diagnosis.findings if f.severity is s) for s in Severity}
    lines = [
        f"{counts[Severity.ERROR]} error(s), {counts[Severity.WARNING]} warning(s), "
        f"{counts[Severity.INFO]} note(s)."
    ]
    lines += [f"{f.severity.value.upper():<7} {f.code} {f.message}" for f in diagnosis.findings]
    lines += [f"NOT RUN {item}" for item in diagnosis.not_run]
    if diagnosis.listed_names:
        lines += ["", "Personal names that were listed (names only, nothing was read):"]
        lines += [f"  {location}/{name}" for location, name in diagnosis.listed_names]
    return "\n".join(lines)


def render_explanation(explanation: Explanation) -> str:
    lines = ["Declared:"]
    lines += [f"  {key}: {value}" for key, value in explanation.declared.items()]
    lines += ["", "Generated (on disk, compared with the manifest):"]
    lines += [
        f"  {d.state:<10} {d.path}" + (f" [{d.block}]" if d.block else "")
        for d in explanation.generated
    ]
    lines += ["", f"{len(explanation.rules)} rule(s) apply:"]
    lines += [f"  {r.level.name:<6} {r.id}  ({r.source})" for r in explanation.rules]
    lines += ["", "Limits:"] + [f"  {f.code} {f.message}" for f in explanation.limits]
    lines += ["", "Cannot be inspected from the repository:"]
    lines += [f"  {item}" for item in explanation.uninspectable]
    lines += ["", "Not run:"] + [f"  {item}" for item in explanation.not_run]
    return "\n".join(lines)


def render_profile_edit(result: ProfileEditResult) -> str:
    headline = {
        "applied": "Profile updated.",
        "previewed": "Preview only. Nothing was written.",
        "needs-input": "Nothing was written: an approval is missing.",
        "refused": "Refused. Nothing was written.",
    }[result.status]
    lines = [headline]
    if result.plan is not None:
        lines += ["", *_plan_lines(result.plan)]
    if result.change_id:
        lines += ["", _change_line(result.change_id)]
    return "\n".join(lines)


def render_validation(result: ValidationResult, *, subject: str) -> str:
    """The verdict first, then what the check found, then why anything was not run."""
    lines = [f"{result.verdict.value}: {subject}"]
    summary = _data_summary(result.data)
    if summary:
        lines += ["", *summary]
    for finding in result.findings:
        where = f" ({finding.path})" if finding.path else ""
        lines.append(f"{finding.severity.value.upper():<7} {finding.code} {finding.message}{where}")
    lines += [f"NOT RUN {reason}" for reason in result.not_run]
    return "\n".join(lines)


def _data_summary(data: dict[str, object]) -> list[str]:
    """Counts that open the summary: an AS-IS file leads with its unknowns and contradictions."""
    lines = []
    if "unknowns" in data and "contradictions" in data:
        lines.append(
            f"{data['unknowns']} unknown(s) ({data.get('material_unknowns', 0)} material), "
            f"{data['contradictions']} contradiction(s), {data.get('facts', 0)} fact(s)"
        )
    if "effective_class" in data:
        lines.append(
            f"Change class {data['effective_class']} (the scope triggers {data['trigger_class']})"
        )
    candidates = data.get("candidates")
    if isinstance(candidates, list):
        lines.append(f"{len(candidates)} candidate(s)")
        lines += [
            f"  {item['id']} {item['kind']}: {item['subject']}"
            + (f" -> {item['knowledge']}" if item.get("knowledge") else "")
            for item in candidates
            if isinstance(item, dict)
        ]
    expected = data.get("expected_changes")
    if isinstance(expected, list):
        lines += [
            f"  {item['id'] or '(no entry)'} {item['surface']}: {item['outcome']}"
            for item in expected
            if isinstance(item, dict)
        ]
    if "snippet" in data:
        lines.append(str(data["snippet"]))
    files = data.get("files")
    if isinstance(files, list):
        lines += [str(item["reference"]) for item in files if isinstance(item, dict)]
    if "phases" in data:
        lines.append(f"{data['phases']} phase(s), {data['operations']} file operation(s)")
    return lines
