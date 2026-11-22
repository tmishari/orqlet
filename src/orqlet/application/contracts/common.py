"""Building blocks shared by every contract."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    StringConstraints,
    model_validator,
)

from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

SHA256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
LineRange = Annotated[str, StringConstraints(pattern=r"^\d+-\d+$")]
LineSpan = Annotated[str, StringConstraints(pattern=r"^[1-9]\d*(-[1-9]\d*)?$")]
GitOid = Annotated[str, StringConstraints(pattern=r"^([0-9a-f]{40}|[0-9a-f]{64})$")]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=64)]
Text = Annotated[str, StringConstraints(min_length=1, max_length=2000)]
Timestamp = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}(T[0-9:.]+(Z|[+-]\d{2}:\d{2})?)?$")
]
Client = str  # "claude-code", "codex" or "cursor"; validated where a closed set is needed
ClientId = Literal["claude-code", "codex", "cursor"]
# The clients that receive files in the user scope; `ClientId` stays the set of project adapters.
RenderClientId = Literal["claude-code", "codex", "cursor", "copilot"]
RENDER_CLIENT_IDS: tuple[RenderClientId, ...] = ("claude-code", "codex", "copilot", "cursor")

# The three string types below are a pattern and a length and nothing else. A custom validator
# message can repeat the offending value (see `loading.py`); a built-in pattern or length error
# never does, so a refused string is never echoed and never truncated (BC-32). The classes are
# written with explicit ASCII ranges, because `\w` and `\d` also match other scripts.
#
# ModelRef: a model name that Orqlet holds (a catalog id, a family, a route name).
ModelRef = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9._:/@+-]+$", min_length=1, max_length=128)
]
# RecordedModel: a model string that a client reported; it may be display text such as
# `Name 1.2 [a=b]`, so the space, brackets, `=` and `,` are allowed.
RecordedModel = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9 ._:/@+\-\[\]=,]+$", min_length=1, max_length=128)
]
# PolicyText: free text of the model policy, printable ASCII only, so a file that the team
# approves holds no hidden or foreign-script content.
PolicyText = Annotated[
    str, StringConstraints(pattern=r"^[\x20-\x7e]+$", min_length=1, max_length=400)
]


def _repository_path(value: str) -> str:
    """A path inside the repository in its canonical (NFC) spelling, or a validation error."""
    try:
        return str(CanonicalPath.parse(value))
    except InvalidPath as error:
        raise ValueError(str(error)) from None


def _glob(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError(f"not a repository-relative glob: {value!r}")
    if ".." in value.split("/"):
        raise ValueError(f"a glob may not climb out of the repository: {value!r}")
    return value


RepoPath = Annotated[str, AfterValidator(_repository_path)]
Glob = Annotated[str, AfterValidator(_glob)]


class Contract(BaseModel):
    """Frozen, closed model: an unknown field is an error, never silently dropped."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Evidence(Contract):
    path: str
    lines: LineRange
    sha256: SHA256Hex


class FactValue(Contract):
    """A value with evidence, or an unknown with a question. Nothing in between."""

    value: str | None = None
    evidence: tuple[Evidence, ...] = ()
    question: str | None = None
    answered_by: str | None = None

    @model_validator(mode="after")
    def _evidence_or_question(self) -> Self:
        if self.value is None:
            if not self.question:
                raise ValueError("an unknown fact needs a question")
        elif not self.evidence and self.answered_by is None:
            raise ValueError("a fact needs evidence or an answer from the maintainer")
        return self
