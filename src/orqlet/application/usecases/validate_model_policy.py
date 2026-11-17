"""`orqlet validate model-policy`: the model policy and the model values of the agent files.

`validate_model_policy` checks the policy file against its contract, its exclusions, its references,
its approvals and the base tree, and it reads the agent and skill files for a model value that an
exclusion names or that a generated file should not hold. It reads the working tree through the
`FileSystem` port, a git tree through the `Vcs` port and the date through the `Clock` port. It
writes nothing, starts no process and opens no socket.

The policy is read by `load_model_policy` and `read_model_policy_at`, the one reader, so the file is
refused for the same reasons here as in `upgrade`. The exclusion and reference problems and the
ORQ-W540 findings come from `select_models`, the one selection, so this command and `upgrade`
cannot disagree about them. Only the wording and the grouping of the problems are written here,
because the wording of `upgrade` tells the person to run `upgrade` again.

A finding never carries a string from a file. A problem is a field path (`models[1].routes[0]`), a
count or a closed word. A model value of an agent file is printed as the catalog id that it names,
as the word `inherit`, or as `unmatched` with its length (BC-32). Every file is read in full
before its size is checked, because the `FileSystem` port has no size query; each read site below
says so.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, timedelta
from typing import Final

from orqlet.application.contracts.generated_lock import GeneratedLock
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.model_policy import ModelPolicy
from orqlet.application.contracts.profile import ProjectProfile
from orqlet.application.ports.clock import Clock
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.ports.vcs import Vcs
from orqlet.application.ports.workflow import WorkflowSource
from orqlet.application.usecases.binding_inputs import locate
from orqlet.application.usecases.capabilities import IMPLEMENTED_COMMANDS
from orqlet.application.usecases.model_policy_source import (
    PolicyAbsent,
    PolicyDeleted,
    PolicyInvalid,
    PolicyLoaded,
    load_model_policy,
    model_policy_path,
    read_model_policy_at,
)
from orqlet.application.usecases.model_selection import (
    BAD_REFERENCE,
    EXCLUDED_MODEL,
    POLICY_DELETED,
    ModelSelection,
    select_models,
    to_resolver_policy,
)
from orqlet.application.usecases.render_all import LOCK_PATH, PROFILE_PATH
from orqlet.application.usecases.validation import (
    Collector,
    ValidateServices,
    ValidationResult,
    split_front_matter,
)
from orqlet.application.usecases.workflow_sources import SourceError, load_roles, load_skills
from orqlet.domain.conventions import printable
from orqlet.domain.errors import InvalidPath, InvalidVersion
from orqlet.domain.model_identity import CatalogEntry, ExclusionRule, is_excluded, match_entry
from orqlet.domain.model_resolution import catalog_entries
from orqlet.domain.ownership import OwnerMode
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.versions import Version

_UNUSABLE_PATH = "ORQ-E320"
_REMOVED_EXCLUSION = "ORQ-E544"
_BAD_APPROVAL = "ORQ-E546"
_EXCLUDED_VALUE = "ORQ-E548"
_STALE_REVIEW = "ORQ-W541"
_RETIRING_ROUTE = "ORQ-W542"
_DRIFT = "ORQ-W543"
_UNUSABLE_FILE = "ORQ-W544"

_NOTHING_CHECKED = "no model policy, nothing was checked"
_ALL_CLIENTS: Final = ("claude-code", "codex", "cursor")
_MAX_BYTES = 256 * 1024
# A refusal lists the field paths of a policy that is faulty in many places, and no more than this
# many: a file at the size limit can hold one problem for each of thousands of entries.
_MAX_PATHS = 20
_SOON = timedelta(days=30)
_SHOWN = 200
_SHOWN_REASON = 400
_INHERIT = "inherit"
_SKILL_FILE = "SKILL.md"

_PROBLEM_TEXT = {
    EXCLUDED_MODEL: (
        "An exclusion matches a model, a route, a candidate, a fallback or an assignment"
    ),
    BAD_REFERENCE: (
        "A reference, a name or an id of the policy does not resolve: a duplicate id, a name that "
        "nothing defines or two models that claim one name"
    ),
}
_PR_REF = re.compile(r"pr:[1-9][0-9]*")
_COMMIT_REF = re.compile(r"commit:(?:[0-9a-f]{40}|[0-9a-f]{64})")
_ADR_PREFIX = "adr:"


@dataclass(frozen=True, slots=True)
class ModelPolicyServices:
    """The ports of the other validators, and the clock that the retirement dates are read with."""

    project: FileSystem
    vcs: Vcs
    loader: DocumentLoader
    workflow: WorkflowSource
    clock: Clock


def validate_model_policy(
    services: ModelPolicyServices, raw_path: str, base: str | None = None
) -> ValidationResult:
    """Every finding about the policy at `raw_path`, or the reason that nothing was checked.

    The base is the tree that the removal of an exclusion is judged against: a branch name, a full
    commit id or `HEAD`, or by default the merge base with the target branch of the profile. A
    PATH other than the default policy is checked on its own: the deletion rule and the base rules
    belong to the default file.
    """
    out = Collector()
    try:
        path = CanonicalPath.parse(raw_path)
    except InvalidPath:
        out.error(_UNUSABLE_PATH, "the path is not a usable repository path", _shown(raw_path))
        return out.result({"policy": "not-read"})
    run = _Run(services, path, base)
    state = load_model_policy(run.view)
    if run.custom and isinstance(state, PolicyDeleted):
        state = PolicyAbsent()  # the lock names the default file only
    if isinstance(state, PolicyInvalid):
        out.findings.extend(replace(finding, path=run.shown) for finding in state.findings)
        return out.result({"policy": "invalid"})
    if isinstance(state, PolicyDeleted):
        _deleted(out, run.shown)
        return out.result({"policy": "deleted"})
    if isinstance(state, PolicyAbsent):
        return _absent(out, run)
    return _loaded(out, run, state.policy)


# --- what the checks share ----------------------------------------------------------------------


class _Redirected:
    """The project file system in which the default policy path names another file.

    `load_model_policy` reads one fixed path. A PATH argument is read by the same reader, so the
    two reasons that a file is refused can never differ, and the reader is not given a second way
    in. Nothing is written through it.
    """

    def __init__(self, inner: FileSystem, target: CanonicalPath) -> None:
        self._inner = inner
        self._target = target

    def _mapped(self, path: CanonicalPath) -> CanonicalPath:
        return self._target if path == model_policy_path() else path

    def kind(self, path: CanonicalPath) -> FileKind | None:
        return self._inner.kind(self._mapped(path))

    def read_bytes(self, path: CanonicalPath) -> bytes:
        return self._inner.read_bytes(self._mapped(path))

    def list_dir(self, path: CanonicalPath | None) -> tuple[str, ...]:
        return self._inner.list_dir(path)

    def write_atomic(self, path: CanonicalPath, data: bytes) -> None:  # noqa: ARG002
        raise FileSystemError("a validator never writes")

    def delete(self, path: CanonicalPath) -> None:  # noqa: ARG002
        raise FileSystemError("a validator never writes")

    def make_dir(self, path: CanonicalPath) -> None:  # noqa: ARG002
        raise FileSystemError("a validator never writes")

    def remove_empty_dir(self, path: CanonicalPath) -> None:  # noqa: ARG002
        raise FileSystemError("a validator never writes")


@dataclass(frozen=True, slots=True)
class _PolicyView:
    """The three ports that the one reader of the policy needs."""

    project: FileSystem
    vcs: Vcs
    loader: DocumentLoader


class _Run:
    """What one call knows: the ports, the path as shown, the base asked for and what it found."""

    def __init__(self, services: ModelPolicyServices, path: CanonicalPath, base: str | None):
        self.services = services
        self.shown = _shown(str(path))
        self.custom = path != model_policy_path()
        self.base = base
        project = _Redirected(services.project, path) if self.custom else services.project
        self.view = _PolicyView(project, services.vcs, services.loader)
        self.inputs = ValidateServices(
            services.project, services.vcs, services.loader, services.workflow
        )


def _shown(text: str) -> str:
    """A path or a reason as ASCII, so that a control character in it never reaches a terminal."""
    return printable(text, _SHOWN)


def _listed(paths: Sequence[str]) -> str:
    """At most 20 field paths, then how many more there are."""
    head = ", ".join(paths[:_MAX_PATHS])
    return head if len(paths) <= _MAX_PATHS else f"{head} and {len(paths) - _MAX_PATHS} more"


def _data(policy: str, base: str, out: Collector, clients: Sequence[str] = ()) -> dict[str, object]:
    """Counts and closed words only: never a string from a file."""
    errors = sum(1 for finding in out.findings if finding.code.startswith("ORQ-E"))
    return {
        "policy": policy,
        "base": base,
        "errors": errors,
        "warnings": len(out.findings) - errors,
        "clients": list(clients),
    }


# --- no policy file, or a deleted one -------------------------------------------------------------


def _deleted(out: Collector, shown: str) -> None:
    out.error(
        POLICY_DELETED,
        "The model policy file is missing, but the lock records it as seeded or the base tree "
        "holds it. A deleted policy drops every exclusion and pin that it held. Restore it from "
        "Git or write a valid policy file.",
        shown,
    )


def _absent(out: Collector, run: _Run) -> ValidationResult:
    """No file: deleted when the base tree holds one, and otherwise never present, so NOT_RUN."""
    reasons: list[str] = []
    base = "not-used"
    if not run.custom:
        located = locate(run.inputs, run.base, "HEAD")
        if located.target is None:
            reasons = located.problems
            base = "not-located"
        else:
            base = "located"
            if not isinstance(read_model_policy_at(run.view, located.target.base), PolicyAbsent):
                _deleted(out, run.shown)
                return out.result(_data("deleted", base, out))
    out.skip(_NOTHING_CHECKED)
    for reason in reasons:
        out.skip(printable(reason, _SHOWN_REASON))
    return out.result(_data("absent", base, out))


# --- a policy that was read -----------------------------------------------------------------------


def _loaded(out: Collector, run: _Run, policy: ModelPolicy) -> ValidationResult:
    clients = _enabled_clients(run.services)
    names = _workflow_names(run.services.workflow)
    selection = None if names is None else select_models(policy, names[0], names[1], clients)
    if selection is None:
        out.skip(
            "the roles and skills of the workflow could not be read, so the exclusions and the "
            "references were not checked"
        )
    else:
        _problems(out, run.shown, selection)
    _approvals(out, run.shown, policy)
    base = _removed_exclusions(out, run, policy)
    if selection is not None and not selection.problems:
        out.findings.extend(replace(finding, path=run.shown) for finding in selection.missing)
    _stale_review(out, run, policy)
    _retiring_routes(out, run, policy)
    _agent_files(out, run, policy, selection, clients)
    return out.result(_data("loaded", base, out, clients))


def _workflow_names(workflow: WorkflowSource) -> tuple[list[str], list[str]] | None:
    """The role and skill names of the packaged workflow, or `None` when it cannot be read."""
    try:
        roles = [role.name for role in load_roles(workflow)]
        skills = [skill.name for skill in load_skills(workflow, IMPLEMENTED_COMMANDS)]
    except SourceError:
        return None
    return roles, skills


def _enabled_clients(services: ModelPolicyServices) -> tuple[str, ...]:
    """The clients that the project profile enables; all three when it cannot be read.

    The profile is read in full and checked only by the strict loader's own limit.
    """
    try:
        if services.project.kind(PROFILE_PATH) is not FileKind.FILE:
            return _ALL_CLIENTS
        profile = load_contract(
            services.loader,
            ProjectProfile,
            services.project.read_bytes(PROFILE_PATH),
            source=str(PROFILE_PATH),
        )
    except (FileSystemError, OSError, DocumentError):
        return _ALL_CLIENTS
    return tuple(profile.clients.enabled)


def _problems(out: Collector, shown: str, selection: ModelSelection) -> None:
    """ORQ-E543 and ORQ-E545: one finding for each code, with the field paths."""
    for code, text in _PROBLEM_TEXT.items():
        paths = [problem.path for problem in selection.problems if problem.code == code]
        if paths:
            out.error(code, f"{text}: {_listed(paths)}.", shown)


def _approvals(out: Collector, shown: str, policy: ModelPolicy) -> None:
    """ORQ-E546: an approved entry needs an approver and a reference of an allowed form."""
    paths: list[str] = []
    for index, entry in enumerate(policy.models):
        if entry.approval.state != "approved":
            continue
        approver = entry.approval.approved_by
        if approver is None or not approver.strip():
            paths.append(f"models[{index}].approval.approved_by")
        if not _allowed_reference(entry.approval.approval_ref):
            paths.append(f"models[{index}].approval.approval_ref")
    if paths:
        out.error(
            _BAD_APPROVAL,
            "An approved model has no approver, or its approval reference is not `pr:<number>`, "
            f"`commit:<full hex id>` or `adr:<repository path>`: {_listed(paths)}.",
            shown,
        )


def _allowed_reference(reference: str | None) -> bool:
    if reference is None:
        return False
    if _PR_REF.fullmatch(reference) or _COMMIT_REF.fullmatch(reference):
        return True
    if not reference.startswith(_ADR_PREFIX):
        return False
    try:
        CanonicalPath.parse(reference.removeprefix(_ADR_PREFIX))
    except InvalidPath:
        return False
    return True


def _removed_exclusions(out: Collector, run: _Run, policy: ModelPolicy) -> str:
    """ORQ-E544 against the base tree; the word that says whether a base was used.

    A custom PATH has no base. The comparison is by `id`: an entry that kept its id and lost an
    alias, a pattern or a tag is not found. The base policy is read in full, and the reader checks
    its size before it parses it.
    """
    if run.custom:
        return "not-used"
    located = locate(run.inputs, run.base, "HEAD")
    if located.target is None:
        for reason in located.problems:
            out.skip(printable(reason, _SHOWN_REASON))
        return "not-located"
    at_base = read_model_policy_at(run.view, located.target.base)
    if isinstance(at_base, PolicyInvalid):
        out.skip(
            "the policy at the base cannot be loaded, so removed exclusions were not looked for"
        )
    elif isinstance(at_base, PolicyLoaded):
        kept = {rule.id for rule in policy.excluded}
        removed = [
            f"excluded[{index}]"
            for index, rule in enumerate(at_base.policy.excluded)
            if rule.id not in kept
        ]
        if removed:
            out.error(
                _REMOVED_EXCLUSION,
                "The base tree holds exclusions that this file lacks, by their position in the "
                f"base file: {_listed(removed)}. An exclusion is removed by a reviewed change "
                "only.",
                run.shown,
            )
    return "located"


def _stale_review(out: Collector, run: _Run, policy: ModelPolicy) -> None:
    """ORQ-W541: the policy was reviewed for an older release than the installed workflow."""
    release = run.services.workflow.release.version
    try:
        reviewed = Version.parse(policy.reviewed_for_release)
    except InvalidVersion:
        return
    if reviewed < release:
        out.warning(
            _STALE_REVIEW,
            f"The policy was last reviewed for release {reviewed}, which is older than the "
            f"installed workflow {release}. Review it and raise `reviewed_for_release`.",
            run.shown,
        )


def _retiring_routes(out: Collector, run: _Run, policy: ModelPolicy) -> None:
    """ORQ-W542: a route whose `retires_on` is past or within 30 days of today (UTC).

    The clock is read once, and only when a route has a date.
    """
    today: date | None = None
    for index, entry in enumerate(policy.models):
        for position, route in enumerate(entry.routes):
            if route.retires_on is None:
                continue
            if today is None:
                today = run.services.clock.now().astimezone(UTC).date()
            retires = date.fromisoformat(route.retires_on)
            where = f"models[{index}].routes[{position}]"
            if retires < today:
                out.warning(
                    _RETIRING_ROUTE,
                    f"{where} retired on {retires}, which is past. Update or remove the route.",
                    run.shown,
                )
            elif retires - today <= _SOON:
                out.warning(
                    _RETIRING_ROUTE,
                    f"{where} retires on {retires}, within 30 days of today. Plan its replacement.",
                    run.shown,
                )


# --- the model values of the agent and skill files ------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Kind:
    """One folder of agent or skill files and the clients that Orqlet writes it for."""

    folder: str
    suffix: str  # `.md` or `.toml`; empty for a folder of skills
    clients: frozenset[str]
    skill: bool
    toml: bool = False

    @property
    def inherits(self) -> bool:
        """True where a generated file says `inherit` when the policy pins nothing."""
        return not self.skill and "codex" not in self.clients


# The order is the order of the findings. Cursor and Codex both read `.agents/skills`.
_KINDS: Final = (
    _Kind(".claude/agents", ".md", frozenset({"claude-code"}), skill=False),
    _Kind(".cursor/agents", ".md", frozenset({"cursor"}), skill=False),
    _Kind(".codex/agents", ".toml", frozenset({"codex"}), skill=False, toml=True),
    _Kind(".claude/skills", "", frozenset({"claude-code"}), skill=True),
    _Kind(".agents/skills", "", frozenset({"codex", "cursor"}), skill=True),
)


class _Unusable(Exception):
    """A file that cannot be scanned, with the closed words that say why."""


@dataclass(frozen=True, slots=True)
class _Scan:
    """What the scan of the files needs from the policy."""

    run: _Run
    rules: tuple[ExclusionRule, ...]
    catalog: tuple[CatalogEntry, ...]
    generated: frozenset[str]
    selection: ModelSelection | None
    enabled: frozenset[str]
    # Generated files hold a few distinct values, and the exclusion test and the description cost
    # as much as the rules and the catalog are long, so each is worked out once for a value.
    excluded: dict[str, bool] = field(default_factory=dict)
    described: dict[str, str] = field(default_factory=dict)


def _agent_files(
    out: Collector,
    run: _Run,
    policy: ModelPolicy,
    selection: ModelSelection | None,
    clients: Sequence[str],
) -> None:
    """ORQ-E548, ORQ-W543 and ORQ-W544 for the five kinds of agent and skill file.

    Each folder is listed once and each file is read once. A policy with problems is not followed,
    so no generated file is compared with it, and the run says so.
    """
    resolver = to_resolver_policy(policy)
    compare = selection is not None and not selection.problems
    if not compare:
        out.skip("generated files were not compared, because the policy has problems")
    scan = _Scan(
        run,
        resolver.exclusions,
        catalog_entries(resolver.models),
        _generated_paths(run.services) if compare else frozenset(),
        selection,
        frozenset(clients),
    )
    for kind in _KINDS:
        _scan_folder(out, scan, kind)


def _generated_paths(services: ModelPolicyServices) -> frozenset[str]:
    """The paths that the lock records with the owner `orqlet`; none when the lock cannot be read.

    The lock is read in full and checked only by the strict loader's own limit.
    """
    try:
        if services.project.kind(LOCK_PATH) is not FileKind.FILE:
            return frozenset()
        lock = load_contract(
            services.loader,
            GeneratedLock,
            services.project.read_bytes(LOCK_PATH),
            source=str(LOCK_PATH),
        )
    except (FileSystemError, OSError, DocumentError):
        return frozenset()
    return frozenset(row.path for row in lock.files if row.owner is OwnerMode.ORQLET)


def _scan_folder(out: Collector, scan: _Scan, kind: _Kind) -> None:
    project = scan.run.services.project
    try:
        folder = CanonicalPath.parse(kind.folder)
        found = project.kind(folder)
        if found is None:
            return
        if found is not FileKind.DIRECTORY:
            raise _Unusable("it is not a folder")
        names = project.list_dir(folder)
    except (FileSystemError, OSError, _Unusable):
        out.warning(
            _UNUSABLE_FILE,
            f"{kind.folder} cannot be listed safely, so no file in it was scanned.",
            kind.folder,
        )
        return
    for name in names:
        if not kind.skill and not name.endswith(kind.suffix):
            continue
        _scan_entry(out, scan, kind, name)


def _scan_entry(out: Collector, scan: _Scan, kind: _Kind, name: str) -> None:
    project = scan.run.services.project
    relative = f"{kind.folder}/{name}"
    try:
        entry = CanonicalPath.parse(relative)
        target = entry
        if kind.skill:
            beside = project.kind(entry)
            if beside is FileKind.SYMLINK:
                raise _Unusable("it is a link, which is not followed")
            if beside is not FileKind.DIRECTORY:
                return  # a file beside the skills, or nothing
            target = CanonicalPath.parse(f"{relative}/{_SKILL_FILE}")
        found = project.kind(target)
        if found is None:
            return
        if found is not FileKind.FILE:
            raise _Unusable("it is not a regular file")
        value = _model_value(scan.run.services, kind, target)
    except InvalidPath:
        _unusable(out, relative, "its name is not a usable path name")
        return
    except _Unusable as reason:
        _unusable(out, str(target), str(reason))
        return
    except (FileSystemError, OSError):
        _unusable(out, str(target), "it cannot be read safely")
        return
    _judge(out, scan, kind, target, value)


def _unusable(out: Collector, path: str, reason: str) -> None:
    out.warning(_UNUSABLE_FILE, f"{_shown(path)} was not scanned: {reason}.", _shown(path))


def _model_value(services: ModelPolicyServices, kind: _Kind, target: CanonicalPath) -> str | None:
    """The top-level `model` of a file, or `None` when it has none.

    The file is read in full and then checked against 256 KiB, before it is parsed. A `model` that
    is present and is not text makes the file unusable.
    """
    data = services.project.read_bytes(target)
    if len(data) > _MAX_BYTES:
        raise _Unusable("it is larger than 256 KiB")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise _Unusable("it is not valid UTF-8") from None
    document = _front_matter(services.loader, text, target) if not kind.toml else _table(text)
    if not isinstance(document, dict) or "model" not in document:
        return None
    value = document["model"]
    if not isinstance(value, str):
        raise _Unusable("its model is not text")
    return value


def _table(text: str) -> object:
    try:
        return tomllib.loads(text)
    except (ValueError, RecursionError):
        raise _Unusable("it cannot be parsed") from None


def _front_matter(loader: DocumentLoader, text: str, target: CanonicalPath) -> object:
    split = split_front_matter(text)
    if split is None:
        return None  # a Markdown file with no front matter has no model value
    try:
        return loader.load(split[0].encode("utf-8"), source=str(target))
    except DocumentError:
        raise _Unusable("its front matter cannot be parsed") from None


def _judge(
    out: Collector,
    scan: _Scan,
    kind: _Kind,
    target: CanonicalPath,
    value: str | None,
) -> None:
    path = _shown(str(target))
    if value is not None and _is_excluded(scan, value):
        out.error(
            _EXCLUDED_VALUE,
            f"{path} holds a model that an exclusion matches "
            f"({_describe(scan, value)}). Replace it.",
            path,
        )
    if str(target) not in scan.generated or not (kind.clients & scan.enabled):
        return
    pin = _pinned_name(scan.selection, kind, target)
    expected = pin if pin is not None else (_INHERIT if kind.inherits else None)
    if value == expected:
        return
    pinned = "a model" if pin is not None else "no model"
    out.warning(
        _DRIFT,
        f"The generated file {path} holds {_describe(scan, value)}, which differs "
        f"from what the policy gives: the policy pins {pinned} for it. Run `orqlet upgrade`.",
        path,
    )


def _is_excluded(scan: _Scan, value: str) -> bool:
    if value not in scan.excluded:
        scan.excluded[value] = is_excluded(value, scan.rules)
    return scan.excluded[value]


def _pinned_name(
    selection: ModelSelection | None, kind: _Kind, target: CanonicalPath
) -> str | None:
    """The route name that the policy pins for this file, or `None` when it pins none.

    `.agents/skills` is read by Cursor and Codex and never carries a model, so it has no pin.
    """
    if selection is not None and len(kind.clients) == 1:
        (client,) = kind.clients
        table = selection.skills if kind.skill else selection.roles
        name = target.parts[-2] if kind.skill else target.parts[-1].removesuffix(kind.suffix)
        setting = table.get(name, {}).get(client)
        if setting is not None:
            return setting.name
    return None


def _describe(scan: _Scan, value: str | None) -> str:
    """The catalog id that `value` names, `inherit`, or `unmatched` with its length."""
    if value is None:
        return "no model"
    if value in scan.described:
        return scan.described[value]
    if value == _INHERIT:
        text = _INHERIT
    else:
        entry = match_entry(value, scan.catalog, skip_proposed=False)
        text = (
            f"catalog id {entry.id}" if entry is not None else f"unmatched, {len(value)} characters"
        )
    scan.described[value] = text
    return text
