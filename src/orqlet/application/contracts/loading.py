"""Turning parsed documents into validated contracts with errors that never echo the input."""

from __future__ import annotations

from pydantic import ValidationError

from orqlet.application.contracts.common import Contract
from orqlet.application.ports.documents import DocumentError, DocumentLoader


def load_contract[T: Contract](
    loader: DocumentLoader, model: type[T], data: bytes, *, source: str
) -> T:
    """Parse `data` strictly, then validate it against `model`.

    A validation error names the fields and the rule that failed. It does not repeat the values,
    which may be secrets pasted into the wrong file.
    """
    parsed = loader.load(data, source=source)
    try:
        return model.model_validate(parsed)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or '(document)'}: {error['msg']}"
            for error in exc.errors(include_input=False, include_url=False)
        )
        raise DocumentError(f"{source}: {problems}") from exc
