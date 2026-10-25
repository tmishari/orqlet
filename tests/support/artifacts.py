"""Builders for workflow artifacts and a small repository to validate them against.

`happy_task` writes an AS-IS file, a design set, a plan and a ledger that all pass. A test changes
one thing in the document it builds and checks the finding that change should cause.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.ports.vcs import CommitSummary, RepoState
from orqlet.application.usecases.validate_ledger import question_key
from orqlet.application.usecases.validation import ValidateServices, content_hash
from orqlet.domain.facts import line_range_hash
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.fakes.vcs import FakeVcs
from tests.fakes.workflow import PINNED

BASE = "1" * 40
LATER = "2" * 40
HASH = "a" * 64
SOURCE = b"def create(a):\n    return a\n\n\nclass Thing:\n    pass\n"
TASK = "demo"
TASK_DIR = f"docs/design/{TASK}"
AS_IS = f"{TASK_DIR}/as-is.md"
DESIGN = f"{TASK_DIR}/design/manifest.yaml"
PLAN = f"{TASK_DIR}/plan.yaml"
LEDGER = f"{TASK_DIR}/questions.yaml"

REPO_FILES = {
    "src/pkg/__init__.py": b"",
    "src/pkg/mod.py": SOURCE,
    "docs/guide.md": b"# Guide\n",
    "pyproject.toml": b"[project]\nname = 'x'\n",
}


class _NoAliases(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def dump(document: dict[str, Any]) -> str:
    return yaml.dump(document, Dumper=_NoAliases, sort_keys=False, allow_unicode=True)


def with_front_matter(document: dict[str, Any], body: str = "") -> bytes:
    return f"---\n{dump(document)}---\n{body}".encode()


@dataclass
class World:
    project: MemoryFileSystem = field(default_factory=MemoryFileSystem)
    vcs: FakeVcs = field(default_factory=FakeVcs)

    def services(self) -> ValidateServices:
        return ValidateServices(
            project=self.project, vcs=self.vcs, loader=StrictYamlLoader(), workflow=PINNED
        )

    def put(self, path: str, data: bytes | str) -> None:
        raw = data.encode() if isinstance(data, str) else data
        self.project.write_atomic(CanonicalPath.parse(path), raw)

    def put_yaml(self, path: str, document: dict[str, Any]) -> None:
        self.put(path, dump(document))

    def read(self, path: str) -> bytes:
        return self.project.read_bytes(CanonicalPath.parse(path))


def make_world(
    files: dict[str, bytes] | None = None,
    *,
    commits: bool = True,
    other_revisions: dict[str, dict[str, bytes]] | None = None,
    **vcs_args: Any,
) -> World:
    tree = dict(REPO_FILES if files is None else files)
    vcs = FakeVcs(
        RepoState.HAS_COMMITS if commits else RepoState.UNBORN_EMPTY,
        branch="main",
        commits=(CommitSummary(BASE, "base"),) if commits else (),
        committed=tree if commits else {},
        revisions=({BASE: tree, **(other_revisions or {})}) if commits else {},
        **vcs_args,
    )
    world = World(vcs=vcs)
    for name, data in tree.items():
        world.put(name, data)
    return world


# --- documents ---------------------------------------------------------------------------------
def header(task: str = TASK, base: str = BASE, **bound: Any) -> dict[str, Any]:
    return {
        "schema": "orqlet.artifact-header/v1",
        "task": task,
        "status": "draft",
        "workflow_version": "0.1.0",
        "protected_set_digest": HASH,
        "bound": {
            "base_revision": base,
            "standards_lock_hash": HASH,
            "applicable_rules_hash": HASH,
            "profile_version": 1,
            **bound,
        },
    }


def self_check(role: str = "researcher", phase: str = "research") -> dict[str, Any]:
    return {
        "schema": "orqlet.self-check/v1",
        "checked_against": {"role": role, "phase": phase},
        "checks": [{"what": "the validator ran", "how": "orqlet validate", "result": "pass"}],
    }


def evidence(
    path: str = "src/pkg/mod.py",
    start: int = 1,
    end: int = 2,
    *,
    content: bytes = SOURCE,
    revision: str = BASE,
) -> dict[str, Any]:
    return {
        "path": path,
        "lines": f"{start}-{end}" if end != start else str(start),
        "revision": revision,
        "sha256": line_range_hash(content, start, end),
    }


def fact(
    number: int = 1, statement: str = "The module defines a function.", **kw: Any
) -> dict[str, Any]:
    return {
        "id": f"A-{number}",
        "kind": "structure",
        "statement": statement,
        "evidence": [evidence(**kw)],
    }


def as_is(task: str = TASK, base: str = BASE, **overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema": "orqlet.as-is/v1",
        "header": header(task, base),
        "base_revision": base,
        "scope": {"paths": ["src/pkg/**"], "request_ref": task},
        "research_mode": "sequential",
        "limitation": "The client has no subagents; one agent researched each area in turn.",
        "size_budget": {"max_words": 200},
        "facts": [fact(1), fact(2, "The module defines a class.", start=5, end=6)],
        "unknowns": [{"id": "U-1", "what": "Which Python versions run it", "material": True}],
        "contradictions": [],
        "self_check": self_check(),
    }
    document.update(overrides)
    return document


def design_files() -> dict[str, bytes]:
    flowchart = b"```mermaid\nflowchart LR\n  A --> B\n```\n"
    sequence = b"```mermaid\nsequenceDiagram\n  A->>B: call\n```\n"
    return {
        f"{TASK_DIR}/design/component.md": b"# Component\n\n" + flowchart,
        f"{TASK_DIR}/design/data-flow.md": b"# Flow\n\n" + flowchart,
        f"{TASK_DIR}/design/sequence.md": b"# Sequence\n\n" + sequence,
        f"{TASK_DIR}/design/adr-0001.md": (
            b"# ADR 1\n\n## Context\nx\n\n## Decision\ny\n\n## Consequences\nz\n\n"
            b"## Rejected alternatives\nw\n"
        ),
    }


def design(
    task: str = TASK, as_is_bytes: bytes | None = None, base: str = BASE, **overrides: Any
) -> dict[str, Any]:
    files = design_files()

    def artifact(kind: str, name: str, covers: str) -> dict[str, Any]:
        path = f"{TASK_DIR}/design/{name}"
        return {
            "id": name.removesuffix(".md"),
            "kind": kind,
            "path": path,
            "covers": covers,
            "sha256": content_hash(files[path]),
        }

    reference = content_hash(as_is_bytes) if as_is_bytes is not None else HASH
    document: dict[str, Any] = {
        "schema": "orqlet.design-set/v1",
        "header": header(task, base),
        "as_is_ref": f"{AS_IS}#{reference}",
        "change_class": {"trigger": "D1", "declared": "D1", "effective": "D1"},
        "scope": {"paths": ["src/pkg/mod.py"], "trust_boundaries": []},
        "extractor_config": {},
        "expected_changes": [],
        "artifacts": [
            artifact("c4-component", "component.md", "The module"),
            artifact("data-flow", "data-flow.md", "The call"),
            artifact("sequence", "sequence.md", "One call"),
            {"id": "adr", "kind": "adr-not-required", "covers": "No durable decision here"},
        ],
        "considerations": {
            key: {
                "state": "not-affected",
                "evidence_refs": ["src/pkg/mod.py:1-2"],
                "notes": "Nothing changes here.",
            }
            for key in ("security", "compatibility", "operations")
        },
        "standards_applied": [],
        "reviews": [],
        "self_check": self_check("architect", "design"),
    }
    document.update(overrides)
    return document


def plan(
    task: str = TASK, design_bytes: bytes | None = None, base: str = BASE, **overrides: Any
) -> dict[str, Any]:
    reference = content_hash(design_bytes) if design_bytes is not None else HASH
    document: dict[str, Any] = {
        "schema": "orqlet.implementation-plan/v1",
        "header": header(task, base),
        "design_ref": f"{DESIGN}#{reference}",
        "base_revision": base,
        "knowledge_scope": [],
        "phases": [phase()],
        "self_check": self_check("planner", "plan"),
    }
    document.update(overrides)
    return document


def phase(number: int = 1, **overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": f"P-{number}",
        "objective": "Add a service next to the module",
        "depends_on": [],
        "implements": [],
        "file_operations": [
            {"op": "create", "path": "src/pkg/service.py", "why": "The new service"},
            {"op": "modify", "path": "src/pkg/mod.py", "why": "Use the service"},
        ],
        "acceptance_criteria": [
            {
                "id": "AC-1",
                "text": "The service returns its input",
                "source": "Q-1",
                "check_ref": "tests",
            }
        ],
        "checks": ["tests"],
        "review_evidence": ["architecture-reviewer", "security-reviewer", "tester"],
        "knowledge_step": "required",
        "completion": ["The checks pass"],
        "expected_outputs": ["src/pkg/service.py"],
    }
    document.update(overrides)
    return document


def question(number: int = 1, **overrides: Any) -> dict[str, Any]:
    subject = overrides.pop("subject", f"Subject {number}")
    category = overrides.pop("category", "requirement")
    document: dict[str, Any] = {
        "id": f"Q-{number}",
        "key": question_key(category, subject),
        "subject": subject,
        "raised_by": "researcher",
        "phase": "research",
        "category": category,
        "text": f"What is subject {number}?",
        "why": "The design depends on it.",
        "status": "open",
    }
    document.update(overrides)
    return document


def ledger(task: str = TASK, **overrides: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema": "orqlet.question-ledger/v1",
        "task": task,
        "questions": [
            question(
                1,
                status="answered",
                answer={
                    "value": "Yes",
                    "answerer": "maintainer",
                    "time": "2026-10-22T10:00:00Z",
                    "scope": "task",
                },
            )
        ],
        "conflicts": [],
    }
    document.update(overrides)
    return document


def happy_task(world: World) -> None:
    """Write a task whose four artifacts all pass, in the folder the workflow expects."""
    as_is_bytes = with_front_matter(as_is())
    world.put(AS_IS, as_is_bytes)
    for path, data in design_files().items():
        world.put(path, data)
    design_text = dump(design(as_is_bytes=as_is_bytes))
    world.put(DESIGN, design_text)
    world.put(PLAN, dump(plan(design_bytes=design_text.encode())))
    world.put_yaml(LEDGER, ledger())
