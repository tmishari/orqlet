"""The commands this release provides, so a skill never calls one that does not exist yet.

A skill text marks a step that needs a command with `requires: <command>`. The renderer drops a
step whose command is not listed here (proposal 17.10). A test compares this set with the commands
the command-line application registers, so the two cannot drift.
"""

from __future__ import annotations

# Commands that skill texts already mention and that a later slice provides. A marker naming
# anything outside both sets is a typo, and a test says so. Nothing is planned at the moment.
PLANNED_COMMANDS: frozenset[str] = frozenset()

IMPLEMENTED_COMMANDS: frozenset[str] = frozenset(
    {
        "init",
        "upgrade",
        "rollback",
        "sync",
        "doctor",
        "explain",
        "release",
        "profile answer",
        "profile approve",
        "resources add",
        "resources update",
        "resources remove",
        "resources attach",
        "resources list",
        "conventions check",
        "standards for",
        "validate as-is",
        "validate design",
        "validate plan",
        "validate ledger",
        "validate integrations",
        "validate resources",
        "gate status",
        "evidence cite",
        "evidence hash",
        "knowledge impact",
        "review prepare",
        "validate review",
        "validate test",
        "validate knowledge",
    }
)
