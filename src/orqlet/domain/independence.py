"""Reviewer independence classes I0 to I3 (proposal 17.12.5).

The class is derived from recorded identifiers, which an approver attests and no tool verifies:
an unkeyed record can be written by anyone. A class says how independent a review *claims* to be.

* I0: the same agent context adopts a persona, or the binding is not an approved one. Never counts.
* I1: an approved binding, run in a fresh context that received only the packet.
* I2: I1 and a different client or a different model family from the Coder.
* I3: a human code owner who is not the author, or a verified CI-executor job. No identifier in a
  record shows that, so it is never derived here; only the host evidence of `ci check` can.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum
from fnmatch import fnmatchcase

from orqlet.domain.change_class import ChangeClass


class Independence(IntEnum):
    I0 = 0
    I1 = 1
    I2 = 2
    I3 = 3


def family_of(model: str | None, families: Sequence[tuple[str, str]]) -> str | None:
    """The family of a model id by the first matching pattern, or `None` when unknown."""
    if model is None:
        return None
    for pattern, family in families:
        if fnmatchcase(model, pattern):
            return family
    return None


def derive_independence(
    *,
    approved_binding: bool,
    agent_client: str,
    agent_family: str | None,
    coder_client: str,
    coder_family: str | None,
) -> Independence:
    """I0, I1 or I2. A family that is unknown on either side cannot show a difference."""
    if not approved_binding:
        return Independence.I0
    different_client = agent_client != coder_client
    different_family = (
        agent_family is not None and coder_family is not None and agent_family != coder_family
    )
    return Independence.I2 if different_client or different_family else Independence.I1


def minimum_independence(change_class: ChangeClass) -> Independence:
    """I1 at D1 and D2; D3 requires I2."""
    return Independence.I2 if change_class is ChangeClass.D3 else Independence.I1


def satisfies(independence: Independence, change_class: ChangeClass) -> bool:
    """I0 never satisfies a review gate."""
    return independence >= minimum_independence(change_class)
