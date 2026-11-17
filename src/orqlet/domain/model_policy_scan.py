"""The credential scan of the model policy file (ADR-002 decision 3, BC-32).

`find_policy_credentials` is the scan of the integrations file (`find_literal_credentials`) plus the
key shapes of the vendors in the policy's catalog: `sk-`, `xai-` and `AIza` followed by key-length
text. The older scan is not touched, so the integrations reader and its tests keep their meaning;
the policy file alone gets the three extra rules.

Like the older scan it returns a line number and the name of a rule and nothing else: a finding
never carries the text that matched, so a key cannot reach a message or a log through it
(ORQLET-SEC-003). It scans text that a repository controls, so each shape is a fixed prefix and a
fixed number of key characters with no repetition to backtrack, and a line is looked at only up to
its first 4096 characters. A longer line already gets the `oversize` finding of the older scan, so
a key past the cap cannot hide behind it.
"""

from __future__ import annotations

import re

from orqlet.domain.mcp_credentials import CredentialFinding, find_literal_credentials

# The same window as the older scan: a line above it is a finding of its own there.
_MAX_LINE = 4096

_RULE_SK = "sk-key-prefix"
_RULE_XAI = "xai-key-prefix"
_RULE_AIZA = "aiza-key-prefix"

# A shape starts at a token boundary, so `risk-...` and `task-...` (which hold `sk-`) are not keys.
# It is case-sensitive, as the keys are. The key characters are the ASCII set `A-Za-z0-9_-`.
_BOUNDARY = r"(?<![A-Za-z0-9_])"
_KEY = r"[A-Za-z0-9_-]"
_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (_RULE_SK, re.compile(rf"{_BOUNDARY}sk-{_KEY}{{20}}")),
    (_RULE_XAI, re.compile(rf"{_BOUNDARY}xai-{_KEY}{{20}}")),
    (_RULE_AIZA, re.compile(rf"{_BOUNDARY}AIza{_KEY}{{35}}")),
)


def find_policy_credentials(text: str) -> tuple[CredentialFinding, ...]:
    """Line numbers and rule names for credential-shaped content; never a value.

    Every finding of `find_literal_credentials` for the same text, plus one for each line that
    holds a vendor key shape. The result has no duplicate and is sorted by line, then by rule.
    """
    found = set(find_literal_credentials(text))
    for number, raw in enumerate(text.split("\n"), start=1):
        window = raw.removesuffix("\r")[:_MAX_LINE]
        found.update(
            CredentialFinding(number, rule) for rule, shape in _SHAPES if shape.search(window)
        )
    return tuple(sorted(found, key=lambda item: (item.line, item.rule)))
