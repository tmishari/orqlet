"""Reviewer independence classes I0 to I3 (proposal 17.12.5).

The class is derived from recorded identifiers, which an approver attests and no tool verifies:
an unkeyed record can be written by anyone. A class says how independent a review *claims* to be.

* I0: the same agent context adopts a persona, the binding is not an approved one, or the record
    says that the context was not fresh. Never counts.
* I1: an approved binding, run in a fresh context that received only the packet.
* I2: I1 and a different client or a different model family from the Coder. A family counts only
    when both identities were observed, never from a model that was only requested (ADR-007).
* I3: a human code owner who is not the author, or a verified CI-executor job. No identifier in a
    record shows that, so it is never derived here; only the host evidence of `ci check` can.

Everything here is a pure function of the values it is given: it reads no clock and no file.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum
from fnmatch import fnmatchcase

from orqlet.domain.change_class import ChangeClass

# A model string is an identity only when a client reported it or the person saw it; `unknown`
# and a missing source mean that nobody can say which model ran.
OBSERVED_SOURCES = frozenset({"client-reported", "person-observed"})
# The one role whose record must say that its context was fresh, and that needs I2 at every class.
CODE_REVIEWER = "code-reviewer"
# The closed notes that keep a weak class visible, in the fixed order in which they are given.
IDENTITY_UNKNOWN = "identity-unknown"
SAME_MODEL_DIFFERENT_CLIENT = "same-model-different-client"
INDEPENDENCE_NOTES = (IDENTITY_UNKNOWN, SAME_MODEL_DIFFERENT_CLIENT)


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


def is_observed(identity_source: str | None, model_observed: str | None) -> bool:
    """True only for a model string that was observed and whose source says so.

    A requested-only model has no observed string; `unknown` and a missing source say nothing.
    """
    return model_observed is not None and identity_source in OBSERVED_SOURCES


def derive_independence(
    *,
    approved_binding: bool,
    agent_client: str,
    agent_family: str | None,
    coder_client: str,
    coder_family: str | None,
    agent_observed: bool = True,
    coder_observed: bool = True,
    fresh: bool | None = None,
    role: str | None = None,
) -> Independence:
    """I0, I1 or I2. A family that is unknown or unobserved on either side shows no difference.

    `fresh` is what the record says about the context of the review: `None` means that it says
    nothing, which is I0 for the code reviewer and as before for the other roles. The two
    `*_observed` flags default to true, so a call that gives only the older arguments is read as
    it was before identities were recorded.
    """
    if not approved_binding or fresh is False:
        return Independence.I0
    if role == CODE_REVIEWER and fresh is not True:
        return Independence.I0
    different_client = agent_client != coder_client
    different_family = (
        agent_observed
        and coder_observed
        and agent_family is not None
        and coder_family is not None
        and agent_family != coder_family
    )
    return Independence.I2 if different_client or different_family else Independence.I1


def independence_notes(
    *,
    agent_client: str,
    coder_client: str,
    agent_model: str | None,
    agent_family: str | None,
    agent_observed: bool,
    coder_model: str | None,
    coder_family: str | None,
    coder_observed: bool,
) -> tuple[str, ...]:
    """The notes that say why an I2 from a different client is weaker than it looks.

    Only a different client can rest on an unknown identity, so the same client gives none.
    """
    if agent_client == coder_client:
        return ()
    if not (
        _is_known(agent_observed, agent_model, agent_family)
        and _is_known(coder_observed, coder_model, coder_family)
    ):
        return (IDENTITY_UNKNOWN,)
    if agent_model is not None and agent_model == coder_model:
        return (SAME_MODEL_DIFFERENT_CLIENT,)
    return ()


def _is_known(observed: bool, model: str | None, family: str | None) -> bool:
    """An observed string that matched no catalog model and no family is still unknown."""
    return observed and (model is not None or family is not None)


def minimum_independence(change_class: ChangeClass, role: str | None = None) -> Independence:
    """I1 at D1 and D2; D3 requires I2. The code reviewer requires I2 at every class."""
    if role == CODE_REVIEWER:
        return Independence.I2
    return Independence.I2 if change_class is ChangeClass.D3 else Independence.I1


def satisfies(
    independence: Independence, change_class: ChangeClass, role: str | None = None
) -> bool:
    """I0 never satisfies a review gate."""
    return independence >= minimum_independence(change_class, role)
