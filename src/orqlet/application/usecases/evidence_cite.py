"""`orqlet evidence cite` and `orqlet evidence hash`: the hashes an artifact must carry.

A model cannot compute a SHA-256 reliably, and the hash of a line range follows its own rules
(LF line endings, no final line break). These two commands print the exact values to copy into
an artifact. The validators then check what was written against the same rules.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from orqlet.application.usecases.validation import (
    Collector,
    ValidateServices,
    ValidationResult,
    content_hash,
    read_file,
)
from orqlet.domain.conventions import printable
from orqlet.domain.errors import InvalidPath
from orqlet.domain.evidence import EvidenceRef, InvalidEvidence
from orqlet.domain.facts import EvidenceError, line_range_hash
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resources import credential_problems, hidden_text_problems

_WEB_EVIDENCE = re.compile(r"docs/design/[^/]+/evidence/web/")
_MAX_WEB_EVIDENCE_BYTES = 256 * 1024
_MAX_LISTED_RULES = 10
OVERSIZE_RULE = "larger-than-256-KiB"


def cite(
    services: ValidateServices, pairs: Sequence[tuple[str, str]], revision: str | None = None
) -> ValidationResult:
    """One evidence entry for each (path, lines) pair at a revision (default: HEAD, a full id).

    A pair that fails is reported and returned without a revision or hash, so a caller can never
    copy a hash that was not computed; the other pairs are still cited.
    """
    out = Collector()
    parsed = [_parse_pair(raw_path, lines, out) for raw_path, lines in pairs]
    resolved = _resolve_revision(services, revision, out)
    if resolved is None:
        return out.result()
    entries = [
        _cite_pair(services, reference, resolved, out)
        if reference
        else {"path": raw, "lines": lines}
        for reference, (raw, lines) in zip(parsed, pairs, strict=True)
    ]
    return out.result(_data_of(entries))


def _parse_pair(raw_path: str, lines: str, out: Collector) -> EvidenceRef | None:
    try:
        path = str(CanonicalPath.parse(raw_path))
        return EvidenceRef.parse(path, lines, "0" * 40, "0" * 64)
    except (InvalidPath, InvalidEvidence) as error:
        out.error("ORQ-E320", str(error), raw_path)
        return None


def _resolve_revision(
    services: ValidateServices, revision: str | None, out: Collector
) -> str | None:
    resolved = revision or services.vcs.head_commit()
    if resolved is None:
        out.skip("the repository has no commit yet, so there is no revision to cite")
        return None
    if resolved == "HEAD":
        resolved = services.vcs.head_commit() or "HEAD"
    if not services.vcs.has_revision(resolved):
        out.skip(f"the revision {resolved[:12]} is not in this repository")
        return None
    return resolved


def _cite_pair(
    services: ValidateServices, reference: EvidenceRef, revision: str, out: Collector
) -> dict[str, str]:
    path = reference.path
    entry = {"path": path, "lines": reference.lines}
    content = services.vcs.read_at(revision, path)
    if content is None:
        out.error("ORQ-E333", f"{path} does not exist at revision {revision[:12]}", path)
        return entry
    if _WEB_EVIDENCE.match(path.casefold()) and _web_evidence_refused(path, content, out):
        return entry
    try:
        digest = line_range_hash(content, reference.start, reference.end)
    except EvidenceError:
        out.error("ORQ-E334", f"{path} does not have lines {reference.lines}", path)
        return entry
    return {**entry, "revision": revision, "sha256": digest}


def _data_of(entries: list[dict[str, str]]) -> dict[str, object]:
    """`citations` always; a single cited pair also keeps the flat fields it had before pairs."""
    snippets = [_snippet(entry) for entry in entries if "sha256" in entry]
    data: dict[str, object] = {"citations": entries}
    if len(entries) == 1 and snippets:
        data.update(entries[0])
    if snippets:
        data["snippet"] = "\n".join(snippets)
    return data


def _snippet(entry: dict[str, str]) -> str:
    return "{" + ", ".join(f"{key}: {value}" for key, value in entry.items()) + "}"


def file_hashes(services: ValidateServices, raw_paths: Sequence[str]) -> ValidationResult:
    """`path#sha256` for each file in the working tree, to paste into a reference."""
    out = Collector()
    files: list[dict[str, str]] = []
    for raw in raw_paths:
        try:
            path = str(CanonicalPath.parse(raw))
        except InvalidPath as error:
            out.error("ORQ-E320", str(error), raw)
            continue
        data = read_file(services, path)
        if data is None:
            out.error("ORQ-E321", f"{path} is not a regular file in the project", path)
            continue
        digest = content_hash(data)
        files.append({"path": path, "sha256": digest, "reference": f"{path}#{digest}"})
    if not raw_paths:
        out.skip("no file was named")
    return out.result({"files": files})


def web_evidence_problems(content: bytes) -> tuple[str, ...]:
    """The rules that make a file unfit as evidence: too large, a hidden character or comment, a
    credential shape. A credential rule carries its line as `rule:line`; no text is ever returned.

    The scan covers the exact bytes that a citation hashes, with CRLF read as LF. `cite` runs it
    on a page under `evidence/web/` (ADR-004 decision 4) and `validate as-is` runs it again on
    task-owned evidence that it reads at HEAD (ADR-003 decision 3). A file that is never cited is
    never scanned, and `evidence hash` is not guarded.
    """
    if len(content) > _MAX_WEB_EVIDENCE_BYTES:
        return (OVERSIZE_RULE,)
    text = content.replace(b"\r\n", b"\n").decode("utf-8", errors="replace")
    return (*hidden_text_problems(text), *credential_problems(text))


def problem_list(problems: Sequence[str]) -> str:
    """At most ten rules, then `and more`, for a message."""
    more = " and more" if len(problems) > _MAX_LISTED_RULES else ""
    return f"{', '.join(problems[:_MAX_LISTED_RULES])}{more}"


def _web_evidence_refused(path: str, content: bytes, out: Collector) -> bool:
    """Refuse a page copied from the web that holds a credential, a hidden character or too much."""
    problems = web_evidence_problems(content)
    if not problems:
        return False
    shown = printable(path, 200)
    if problems == (OVERSIZE_RULE,):
        out.error("ORQ-E511", f"{shown} is larger than 256 KiB, so it cannot be cited", shown)
        return True
    out.error(
        "ORQ-E511",
        f"{shown} fails these checks for evidence from the web: {problem_list(problems)}. The "
        "file is already in a local commit: amend or reset it before anything is pushed, and "
        "treat a credential that it shows as exposed.",
        shown,
    )
    return True
