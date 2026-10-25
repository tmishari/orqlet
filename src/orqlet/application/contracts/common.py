"""Building blocks shared by every contract."""

from __future__ import annotations

from typing import Annotated, Self

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
