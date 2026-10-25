"""`orqlet standards for`: the rules that apply to a path, a role or a phase (proposal 12.7).

Deterministic: the same repository, packs and query always give the same rules and the same
hash. Packs are layered from general to specific and the project's own additions come last;
the resolver refuses any layer that would relax an earlier one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.profile import ProjectProfile, Technology
from orqlet.application.contracts.standards_pack import PackManifest, Rule, RuleFile
from orqlet.application.ports.documents import DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem
from orqlet.application.ports.scanner import ProjectScanner, ScanResult, TechnologyScanner
from orqlet.application.ports.standards import LoadedPack, StandardsSource
from orqlet.application.usecases.discover import discover_technologies
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resolver import (
    Enforcement,
    Layer,
    Level,
    RuleSpec,
    Scope,
    Waiver,
    resolve,
    rules_hash,
    select,
)

PROJECT_RULES_PATH = ".orqlet/rules.yaml"
DEFAULT_PROMPTS_DIR = ".prompts"
PROFILE_PATH_TEXT = ".orqlet/project-profile.yaml"


@dataclass(frozen=True, slots=True)
class StandardsQuery:
    path: str | None = None
    role: str | None = None
    phase: str | None = None


@dataclass(frozen=True, slots=True)
class PackUse:
    id: str
    version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class StandardsAnswer:
    rules: tuple[RuleSpec, ...]
    rules_hash: str
    packs: tuple[PackUse, ...]
    skipped: tuple[tuple[str, str], ...]  # (pack id, reason)
    not_run: tuple[str, ...]
    language: str | None  # the language a scanner recognised, or None when none applies
    technologies: tuple[Technology, ...] = ()


def to_spec(rule: Rule, source: str) -> RuleSpec:
    return RuleSpec(
        id=rule.id,
        level=Level[rule.level],
        waiver=Waiver.NONE if rule.waiver == "none" else Waiver.REVIEWED,
        enforcement=Enforcement[rule.enforcement.upper()],
        scope=Scope(
            frozenset(rule.scope.paths), frozenset(rule.scope.roles), frozenset(rule.scope.phases)
        ),
        text=rule.text,
        source=source,
    )


@dataclass(frozen=True, slots=True)
class Stack:
    """What a pack's `applies_to` is compared with."""

    languages: frozenset[str]  # lower case: "python", "go", "rust"...
    kind: str
    technologies: frozenset[str]  # lower case names of every technology found


@dataclass(frozen=True, slots=True)
class Resolution:
    rules: dict[str, RuleSpec]
    used: tuple[PackUse, ...]
    loaded: tuple[LoadedPack, ...]
    skipped: tuple[tuple[str, str], ...]
    not_run: tuple[str, ...]


def stack_of(scan: ScanResult | None, technologies: Sequence[Technology] = ()) -> Stack:
    """The stack a pack is matched against: the Python scan plus every technology found."""
    languages = {t.name.lower() for t in technologies if t.kind == "language"}
    names = {t.name.lower() for t in technologies}
    if scan is None:
        return Stack(frozenset(languages), "unknown", frozenset(names))
    names |= {f.name.lower() for f in scan.facts.frameworks}
    return Stack(frozenset(languages | {scan.language}), scan.kind, frozenset(names))


def resolve_standards(
    packs: StandardsSource | None, own_layers: Sequence[Layer], stack: Stack
) -> Resolution:
    """Pick the packs that apply to `stack`, layer them in id order, then add the team's own.

    `own_layers` are the team's standards folder and the project's additions, most general first.
    """
    layers: list[Layer] = []
    used: list[PackUse] = []
    loaded: list[LoadedPack] = []
    skipped: list[tuple[str, str]] = []
    not_run: list[str] = []
    for pack_id in packs.available() if packs is not None else ():
        assert packs is not None
        pack = packs.load(pack_id)
        reason = _mismatch(pack.manifest, stack)
        if reason is not None:
            skipped.append((pack_id, reason))
            continue
        if pack.manifest.applies_to.python is not None:
            not_run.append(f"pack {pack_id}: applies_to.python is not evaluated yet")
        used.append(PackUse(pack_id, pack.manifest.version, pack.content_sha256))
        loaded.append(pack)
        layers.append(_layer(pack))
    layers.extend(own_layers)
    return Resolution(resolve(layers), tuple(used), tuple(loaded), tuple(skipped), tuple(not_run))


def standards_for(
    project: FileSystem,
    loader: DocumentLoader,
    scanners: Sequence[ProjectScanner],
    packs: StandardsSource | None,
    query: StandardsQuery,
    technology_scanners: Sequence[TechnologyScanner] = (),
) -> StandardsAnswer:
    scan = _scan(project, scanners)
    discovery = discover_technologies(project, technology_scanners)
    layers = own_layers(project, loader, configured_prompts_dir(project, loader))
    resolution = resolve_standards(packs, layers, stack_of(scan, discovery.technologies))
    chosen = select(resolution.rules, path=query.path, role=query.role, phase=query.phase)
    return StandardsAnswer(
        rules=chosen,
        rules_hash=rules_hash(chosen),
        packs=resolution.used,
        skipped=resolution.skipped,
        not_run=resolution.not_run,
        language=scan.language if scan else next(iter(sorted(discovery.languages())), None),
        technologies=discovery.technologies,
    )


def _scan(project: FileSystem, scanners: Sequence[ProjectScanner]) -> ScanResult | None:
    for scanner in scanners:
        if scanner.applies(project):
            return scanner.scan(project)
    return None


def _mismatch(manifest: PackManifest, stack: Stack) -> str | None:
    """Why a pack does not apply to this stack, or `None` when it does."""
    wanted = manifest.applies_to
    if wanted.languages and not stack.languages & {name.lower() for name in wanted.languages}:
        return f"languages {list(wanted.languages)} do not include this project's"
    if wanted.project_types and stack.kind not in wanted.project_types:
        return f"project types {list(wanted.project_types)} do not include this project's"
    named = [*wanted.frameworks, *wanted.technologies]
    if named and not stack.technologies & {name.lower() for name in named}:
        return f"none of the technologies {named} was found"
    return None


def _layer(pack: LoadedPack) -> Layer:
    source = f"{pack.manifest.id}@{pack.manifest.version}"
    return Layer(source, tuple(to_spec(rule, source) for rule in pack.rules))


def own_layers(project: FileSystem, loader: DocumentLoader, prompts_dir: str) -> list[Layer]:
    """The team's own rules: the standards folder first, then the project's additions.

    Both are optional. A rules file that is present must be valid; a broken one is an error
    that names the file, never a rule that is silently skipped.
    """
    found: list[Layer] = []
    for name, source in (
        (f"{prompts_dir.strip('/')}/rules.yaml", "prompts"),
        (PROJECT_RULES_PATH, "project"),
    ):
        layer = _rules_layer(project, loader, name, source)
        if layer is not None:
            found.append(layer)
    return found


def configured_prompts_dir(project: FileSystem, loader: DocumentLoader) -> str:
    """The standards folder the profile names, or `.prompts` when there is no profile yet."""
    path = CanonicalPath.parse(PROFILE_PATH_TEXT)
    if project.kind(path) is not FileKind.FILE:
        return DEFAULT_PROMPTS_DIR
    profile = load_contract(
        loader, ProjectProfile, project.read_bytes(path), source=PROFILE_PATH_TEXT
    )
    return prompts_dir_of(profile)


def prompts_dir_of(profile: ProjectProfile) -> str:
    for source in profile.standards_sources:
        if source.kind == "prompts-dir" and source.path:
            return source.path
    return DEFAULT_PROMPTS_DIR


def _rules_layer(
    project: FileSystem, loader: DocumentLoader, name: str, source: str
) -> Layer | None:
    path = CanonicalPath.parse(name)
    if project.kind(path) is not FileKind.FILE:
        return None
    rule_file = load_contract(loader, RuleFile, project.read_bytes(path), source=name)
    return Layer(source, tuple(to_spec(rule, source) for rule in rule_file.rules))
