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


def cite(
    services: ValidateServices, raw_path: str, lines: str, revision: str | None = None
) -> ValidationResult:
    """The evidence entry for `lines` of `raw_path` at a revision (default: HEAD, as a full id)."""
    out = Collector()
    try:
        path = str(CanonicalPath.parse(raw_path))
        reference = EvidenceRef.parse(path, lines, "0" * 40, "0" * 64)
    except (InvalidPath, InvalidEvidence) as error:
        out.error("ORQ-E320", str(error), raw_path)
        return out.result()
    resolved = revision or services.vcs.head_commit()
    if resolved is None:
        out.skip("the repository has no commit yet, so there is no revision to cite")
        return out.result()
    if resolved == "HEAD":
        resolved = services.vcs.head_commit() or "HEAD"
    if not services.vcs.has_revision(resolved):
        out.skip(f"the revision {resolved[:12]} is not in this repository")
        return out.result()
    content = services.vcs.read_at(resolved, path)
    if content is None:
        out.error("ORQ-E333", f"{path} does not exist at revision {resolved[:12]}", path)
        return out.result()
    if _WEB_EVIDENCE.match(path.casefold()) and _web_evidence_refused(path, content, out):
        return out.result()
    try:
        digest = line_range_hash(content, reference.start, reference.end)
    except EvidenceError:
        out.error("ORQ-E334", f"{path} does not have lines {reference.lines}", path)
        return out.result()
    entry = {"path": path, "lines": reference.lines, "revision": resolved, "sha256": digest}
    snippet = "{" + ", ".join(f"{key}: {value}" for key, value in entry.items()) + "}"
    return out.result({**entry, "snippet": snippet})


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


def _web_evidence_refused(path: str, content: bytes, out: Collector) -> bool:
    """Refuse a page copied from the web that holds a credential, a hidden character or too much.

    The scan covers the exact bytes that `cite` hashes. It runs at cite time only (ADR-004
    decision 4): a file that is never cited is never scanned, and `evidence hash` is not guarded.
    The finding names the rule and the line, never the text.
    """
    shown = printable(path, 200)
    if len(content) > _MAX_WEB_EVIDENCE_BYTES:
        out.error("ORQ-E511", f"{shown} is larger than 256 KiB, so it cannot be cited", shown)
        return True
    text = content.replace(b"\r\n", b"\n").decode("utf-8", errors="replace")
    problems = (*hidden_text_problems(text), *credential_problems(text))
    if problems:
        out.error(
            "ORQ-E511",
            f"{shown} fails these checks for evidence from the web: "
            f"{', '.join(problems[:_MAX_LISTED_RULES])}"
            f"{' and more' if len(problems) > _MAX_LISTED_RULES else ''}. The file is already in a "
            "local commit: amend or reset it before anything is pushed, and treat a credential "
            "that it shows as exposed.",
            shown,
        )
        return True
    return False
