"""Reading what an implementation changed on the watched surfaces, and comparing it with the design.

Every extractor parses blobs of two trees (the merge base and the tree under review) as text. It
never imports or runs repository code. A surface for which this release has no extractor, or one
that cannot be read, is reported as `manual`: the Architecture Reviewer compares it by hand and the
approval record marks it unverifiable by CI (proposal 17.4.1).
"""

from __future__ import annotations

from dataclasses import dataclass

from orqlet.application.contracts.design_set import DesignSet
from orqlet.application.contracts.plan import ImplementationPlan
from orqlet.application.usecases.validation import ValidateServices
from orqlet.domain.dependencies import (
    Dependencies,
    DependencyDelta,
    dependency_delta,
    lock_packages,
    parse_pyproject,
)
from orqlet.domain.expected_change import (
    Actual,
    ApiDelta,
    Expectation,
    Result,
    api_delta,
    compare,
)
from orqlet.domain.globs import glob_match
from orqlet.domain.python_api import Symbol, extract_module_api

CONTRACT_GLOBS = (
    "**/openapi*.yaml",
    "**/openapi*.yml",
    "**/openapi*.json",
    "**/asyncapi*.yaml",
    "**/asyncapi*.yml",
    "**/asyncapi*.json",
    "**/*.proto",
    "**/migrations/**",
    "**/alembic/versions/**",
)


@dataclass(frozen=True, slots=True)
class ExpectedChangeReport:
    results: tuple[Result, ...]
    notes: tuple[str, ...] = ()


def evaluate_expected_changes(
    services: ValidateServices,
    design: DesignSet,
    plan: ImplementationPlan | None,
    phase_id: str | None,
    base: str,
    tree: str,
) -> ExpectedChangeReport:
    notes: list[str] = []
    expectations = [
        Expectation(
            id=change.id,
            surface=change.surface,
            action=change.action,
            identity=change.identity,
            value=change.expected_after.value,
            verification=change.verification,
            stages={stage.id: stage.expected_after.value for stage in change.stages},
        )
        for change in design.expected_changes
    ]
    phases = [p for p in (plan.phases if plan else ()) if phase_id in {None, p.id}]
    selected = frozenset(item for phase in phases for item in phase.implements)
    lock_names = tuple(name for phase in phases for name in phase.expected_lock_packages)
    config = design.extractor_config
    vcs = services.vcs
    changed = [c.path for c in vcs.diff_tree(base, tree)]
    actual = Actual(
        api=public_api_delta(
            services, config.public_api.packages if config.public_api else (), base, tree, notes
        ),
        dependencies=_dependencies(services, config.dependency_manifests, base, tree, notes),
        security_paths=tuple(
            sorted(p for p in changed if any(glob_match(g, p) for g in config.security_globs))
        ),
        undeclared_files=tuple(
            sorted(
                p
                for p in changed
                if any(glob_match(g, p) for g in CONTRACT_GLOBS)
                and p not in {*config.contract_files, *config.schema_files}
                and not any(glob_match(g, p) for g in config.migration_paths)
            )
        ),
    )
    added, removed = _lock_delta(services, config.lockfiles, base, tree, notes)
    actual = Actual(
        api=actual.api,
        dependencies=actual.dependencies,
        lock_added=added,
        lock_removed=removed,
        security_paths=actual.security_paths,
        undeclared_files=actual.undeclared_files,
    )
    return ExpectedChangeReport(compare(expectations, selected, actual, lock_names), tuple(notes))


# --- the public Python API ------------------------------------------------------------------
def _module_name(path: str, package: str) -> str | None:
    """`src/pkg/sub/mod.py` is `pkg.sub.mod`; `__init__` is the package; `_x` is private."""
    if not path.endswith(".py"):
        return None
    parts = path.removesuffix(".py").split("/")
    wanted = package.split(".")
    for start in (0, 1):
        if start == 1 and parts[0] != "src":
            continue
        if parts[start : start + len(wanted)] == wanted:
            rest = parts[start + len(wanted) :]
            if rest and rest[-1] == "__init__":
                rest = rest[:-1]
            if any(part.startswith("_") for part in rest):
                return None  # a module with a leading underscore is private, whatever it defines
            return ".".join([*wanted, *rest])
    return None


def _symbols(
    services: ValidateServices, tree: str, packages: tuple[str, ...], notes: list[str]
) -> dict[str, Symbol] | None:
    found: dict[str, Symbol] = {}
    manual = False
    wanted = [
        (file.path, module)
        for file in services.vcs.tree_at(tree)
        for package in packages
        if (module := _module_name(file.path, package)) is not None
    ]
    contents = services.vcs.read_many_at(tree, [path for path, _ in wanted])
    for path, module in wanted:
        api = extract_module_api(
            (contents.get(path) or b"").decode("utf-8", errors="replace"),
            is_package_init=path.endswith("__init__.py"),
        )
        for reason in (*api.manual, *api.errors):
            notes.append(f"{path}: {reason}")
        manual = manual or bool(api.manual or api.errors)
        for name, symbol in api.symbols.items():
            found[f"{module}.{name}"] = symbol
    return None if manual else found


def public_api_delta(
    services: ValidateServices, packages: tuple[str, ...], base: str, tree: str, notes: list[str]
) -> ApiDelta | None:
    if not packages:
        return None
    before = _symbols(services, base, packages, notes)
    after = _symbols(services, tree, packages, notes)
    if before is None or after is None:
        return None
    return api_delta(before, after)


# --- dependencies and lockfiles -------------------------------------------------------------
def _dependencies(
    services: ValidateServices,
    manifests: tuple[str, ...],
    base: str,
    tree: str,
    notes: list[str],
) -> DependencyDelta | None:
    paths = [m for m in manifests if m.rsplit("/", 1)[-1] == "pyproject.toml"]
    for other in sorted(set(manifests) - set(paths)):
        notes.append(f"{other}: this release reads `pyproject.toml` only; compare it by hand")
    if not paths:
        return None
    before = _merge([_parse(services, base, p, notes) for p in paths])
    after = _merge([_parse(services, tree, p, notes) for p in paths])
    return dependency_delta(before, after)


def _parse(services: ValidateServices, tree: str, path: str, notes: list[str]) -> Dependencies:
    data = services.vcs.read_at(tree, path)
    parsed = parse_pyproject(data.decode("utf-8", errors="replace") if data is not None else "")
    notes += [f"{path}: {problem}" for problem in parsed.problems]
    return parsed


def _merge(parts: list[Dependencies]) -> Dependencies:
    direct: dict[str, str] = {}
    sources: dict[str, str] = {}
    for part in parts:
        direct.update(part.direct)
        sources.update(part.sources)
    return Dependencies(direct, sources)


def _lock_delta(
    services: ValidateServices, lockfiles: tuple[str, ...], base: str, tree: str, notes: list[str]
) -> tuple[frozenset[str] | None, frozenset[str] | None]:
    if not lockfiles:
        return None, None
    before: set[str] = set()
    after: set[str] = set()
    for path in lockfiles:
        names = []
        for revision in (base, tree):
            data = services.vcs.read_at(revision, path)
            found = lock_packages(data.decode("utf-8", errors="replace")) if data else frozenset()
            if found is None:
                notes.append(f"{path}: not a TOML lockfile; compare its packages by hand")
                return None, None
            names.append(found)
        before |= names[0]
        after |= names[1]
    return frozenset(after - before), frozenset(before - after)
