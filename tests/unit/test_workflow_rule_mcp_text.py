"""The workflow rule text about `.mcp.json` (task mcp-or-plugins, phase P-7).

Every case cites its `expected_behavior_source`: ADR-002 and ADR-003 are the files
`adr-002-*.md` and `adr-003-*.md` under docs/design/mcp-or-plugins/design/, AC-1 is the first
acceptance criterion of phase P-7 in docs/design/mcp-or-plugins/plan.yaml, and the interface
decision is the list of exact phrases that the Tester of P-7 was given (the ADR does not spell
them out).

HOW THESE TESTS WERE WRITTEN. They were written before the new text exists, from the acceptance
criterion and its sources only, and were run against the working tree of that time: the pins of the
new text fail there, the guards of the parts that must not change pass. They read the two files of
the package as they are on disk (`src/orqlet/workflow/rules/`), the way the tool that builds the
manifest does, and parse the YAML with the project's strict loader.

What is deliberately NOT pinned (the design leaves it open, or the phrase would only copy a file):
- the version of the workflow (0.3.3 is a proposal that the person may replace) and the manifest,
  which `tests/unit/test_manifest.py` already checks against `tools/build_manifest.py` (AC-2);
- the golden files (AC-3), which the Coder regenerates;
- the rest of the wording of the fourth bullet, among them the words "In a project that holds that
  declaration" and the statement that the declaration decides which servers exist;
- whether the first paragraph keeps the folder names that follow "the client configuration
  folders" in parentheses today;
- the order of the paths of the meta file, and any other field of it than `description`;
- the letter case of a phrase is pinned; white space is not (a phrase may be re-wrapped across
  lines).
"""

from __future__ import annotations

import re
from functools import cache

import pytest
from tools.build_manifest import WORKFLOW_DIR

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.workflow_package import WorkflowRuleMeta
from orqlet.domain.ownership import FileClass
from tests.support.render import packaged_request

pytestmark = pytest.mark.unit

RULES_DIR = WORKFLOW_DIR / "rules"
RULE = RULES_DIR / "orqlet-workflow.md"
META = RULES_DIR / "orqlet-workflow.meta.yaml"
LOADER = StrictYamlLoader()

# --- what the rule says today and must keep saying ---------------------------------------------
TITLE = "# Files that Orqlet writes"
THREE_BULLETS = (
    "- Do not edit them by hand. A protected file that differs from the render of the pinned "
    "Orqlet release fails review.",
    "- To change one, change its source (the profile, the policy or the standards) and ask a "
    "maintainer to run `orqlet upgrade`.",
    "- A file that Orqlet seeded once, such as `.prompts/`, belongs to the team. Edit it freely.",
)
TODAYS_PATHS = (
    ".orqlet/**",
    ".claude/**",
    ".cursor/**",
    ".agents/**",
    ".codex/**",
    ".mcp.json",
    "AGENTS.md",
)
TODAYS_DESCRIPTION = "Files that Orqlet writes are generated; change their source, not the file."

# The words of a sentence that would put a credential or a variable reference into an entry.
CREDENTIAL = re.compile(
    r"\b(?:credentials?|variable references?|secrets?|tokens?|passwords?)\b", re.IGNORECASE
)
PLACING = re.compile(
    r"\b(?:hold|holds|put|place|paste|store|write|add|contain|contains|carry|carries|include"
    r"|includes|embed|copy)\b",
    re.IGNORECASE,
)
NEGATION = re.compile(r"\b(?:no|not|never|nor|without|cannot)\b", re.IGNORECASE)
PERMISSION = re.compile(r"\b(?:may|can)\s+(?:hold|carry|contain|include)\b")
GENERATED = re.compile(r"\bgenerated\b")
CLAUSE_END = re.compile(r"[.;:!?](?=\s|$)")


def squash(text: str) -> str:
    """The text with every run of white space as one space, so a re-wrapped phrase still matches."""
    return " ".join(text.split())


@cache
def rule_text() -> str:
    return RULE.read_text(encoding="utf-8")


def parts_of(text: str) -> tuple[str, list[str], str]:
    """The text before the first bullet, the bullets, and any text that follows a bullet apart.

    A bullet is a line that starts with `- ` and the lines that continue it without a blank line.
    """
    lines = text.split("\n")
    first = next((n for n, line in enumerate(lines) if line.startswith("- ")), len(lines))
    bullets: list[str] = []
    tail: list[str] = []
    continuing = False
    for line in lines[first:]:
        if line.startswith("- "):
            bullets.append(line)
            continuing = True
        elif not line.strip():
            continuing = False
        elif continuing:
            bullets[-1] += "\n" + line
        else:
            tail.append(line)
    return "\n".join(lines[:first]), bullets, "\n".join(tail)


def first_paragraph() -> str:
    return parts_of(rule_text())[0]


def fourth_bullet() -> str:
    bullets = parts_of(rule_text())[1]
    assert len(bullets) >= 4, f"the rule text has {len(bullets)} bullets; the fourth is missing"
    return bullets[3]


def clauses_of(text: str) -> list[str]:
    """The text cut into clauses at a full stop, a semicolon, a colon or the end of a bullet."""
    found: list[str] = []
    for block in re.split(r"\n\s*\n|\n(?=- )", text):
        found += [clause.strip() for clause in CLAUSE_END.split(squash(block)) if clause.strip()]
    return found


@cache
def raw_meta() -> dict[str, object]:
    loaded = LOADER.load(META.read_bytes(), source=META.name)
    assert isinstance(loaded, dict)
    return loaded


def meta_description() -> str:
    description = raw_meta()["description"]
    assert isinstance(description, str)
    return description


def meta_paths() -> list[str]:
    paths = raw_meta()["paths"]
    assert isinstance(paths, list)
    assert all(isinstance(path, str) for path in paths)
    return [str(path) for path in paths]


# --- the first paragraph: `.mcp.json` is no longer a generated file ---------------------------
def test_the_first_paragraph_does_not_name_mcp_json() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 ("the text stops listing it among the
    generated files"); plan P-7 AC-1 ("no longer lists .mcp.json among the files Orqlet
    generates"); interface decision (the first paragraph no longer contains `.mcp.json`)."""
    assert ".mcp.json" not in first_paragraph()


def test_the_first_paragraph_still_says_that_the_other_files_are_generated_by_orqlet() -> None:
    """AC-1. expected_behavior_source: interface decision (the first paragraph reads that the files
    under `.orqlet/`, the client configuration folders and the managed block in `AGENTS.md` are
    generated by Orqlet); ADR-003 decision 7 (the text only stops listing `.mcp.json`)."""
    head = squash(first_paragraph())

    assert head.startswith(f"{TITLE} ")
    assert "files under `.orqlet/`" in head
    assert "the client configuration folders" in head
    assert "the managed block in `AGENTS.md` are generated by Orqlet." in head
    assert (
        head.index("files under `.orqlet/`")
        < head.index("the client configuration folders")
        < head.index("the managed block in `AGENTS.md`")
    )


# --- the three bullets that stay --------------------------------------------------------------
def test_the_first_three_bullets_are_byte_identical_to_the_ones_of_today() -> None:
    """AC-1. expected_behavior_source: interface decision (the three existing bullets stay
    unchanged); ADR-003 decision 7 (the change adds a bullet and rewords nothing else)."""
    text = rule_text()

    assert parts_of(text)[1][:3] == list(THREE_BULLETS)
    assert "\n".join(THREE_BULLETS) + "\n" in text, "the three bullets are consecutive lines"


def test_the_rule_has_exactly_four_bullets() -> None:
    """AC-1. expected_behavior_source: interface decision (the three existing bullets stay and a
    fourth bullet is added); plan P-7 AC-1 ("a new bullet")."""
    head, bullets, _ = parts_of(rule_text())

    assert len(bullets) == 4
    assert head.startswith(TITLE)


# --- the fourth bullet: seeded, the team's, proposals, the declaration -------------------------
# label -> (phrase, expected_behavior_source). Every phrase must be in the fourth bullet.
BULLET_PHRASES: dict[str, tuple[str, str]] = {
    ".mcp.json was seeded and belongs to the team": (
        "`.mcp.json` was seeded by Orqlet and belongs to the team",
        "ADR-003 decision 7 (a new bullet says that `.mcp.json` was seeded by Orqlet and belongs "
        "to the team afterwards); ADR-003 decision 5 (owner `seeded`)",
    ),
    "the orqlet-* entries are named": (
        "`orqlet-*`",
        "ADR-003 decision 7 (`orqlet-*` entries follow the declaration); ADR-003 decision 4",
    ),
    "the declaration is named": (
        "`.orqlet/integrations.yaml`",
        "ADR-003 decision 7 (a project that holds `.orqlet/integrations.yaml`); ADR-003 decision 2",
    ),
    "a change arrives as a proposal": (
        "arrives as a proposal",
        "ADR-003 decision 7 (changes arrive as proposals); ADR-003 decision 5",
    ),
    "no orqlet-* entry may hold a reference or a credential": (
        "no `orqlet-*` entry may hold a variable reference or a credential value",
        "ADR-003 decision 7 (this release allows no variable reference and no credential value "
        "in an `orqlet-*` entry); ADR-002 decision 12 (no committed file may hold a credential)",
    ),
    "the check runs only in such a project": (
        "the check runs only in such a project",
        "ADR-003 decision 7 (the check runs only in such a project, and the text says so); "
        "ADR-002 decision 12 (a project that has no declaration, where no check runs)",
    ),
}


@pytest.mark.parametrize(
    ("phrase", "source"), list(BULLET_PHRASES.values()), ids=list(BULLET_PHRASES)
)
def test_the_fourth_bullet_holds_each_phrase_of_the_interface_decision(
    phrase: str, source: str
) -> None:
    """AC-1. expected_behavior_source: the source in the table (ADR-003 decision 7) and the
    interface decision, which fixes the phrase."""
    assert phrase in squash(fourth_bullet()), f"{phrase!r} is missing; source: {source}"


def test_the_declaration_is_named_before_the_scope_of_the_check() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 ("the check runs only in such a
    project"): "such a project" is the project that holds `.orqlet/integrations.yaml`, so the
    declaration is named before it, as the interface decision words it."""
    bullet = squash(fourth_bullet())
    declaration = "`.orqlet/integrations.yaml`"
    scope = "the check runs only in such a project"

    assert declaration in bullet
    assert scope in bullet
    assert bullet.index(declaration) < bullet.index(scope)


def test_mcp_json_is_named_only_in_the_fourth_bullet() -> None:
    """AC-1. expected_behavior_source: interface decision (the whole text contains `.mcp.json` only
    in the new bullet); ADR-003 decision 7 (the text stops listing it among the generated
    files)."""
    text = rule_text()
    _, bullets, tail = parts_of(text)

    assert ".mcp.json" not in first_paragraph(), "the first paragraph still names it"
    assert all(".mcp.json" not in bullet for bullet in bullets[:3])
    assert ".mcp.json" not in tail
    fourth = fourth_bullet()
    assert ".mcp.json" in fourth
    assert text.count(".mcp.json") == fourth.count(".mcp.json")


# --- negative guards: what the text must never say ---------------------------------------------
def test_no_sentence_calls_mcp_json_generated() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 (`.mcp.json` is seeded and the team's
    afterwards; the text stops listing it among the generated files); ADR-003 decision 5 (owner
    `seeded`, no file class)."""
    for clause in clauses_of(rule_text()):
        assert not (".mcp.json" in clause and GENERATED.search(clause)), (
            f"a clause that names `.mcp.json` says 'generated': {clause!r}"
        )


def test_no_sentence_allows_a_credential_or_a_variable_reference_in_an_entry() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 (this release allows no variable
    reference and no credential value in an `orqlet-*` entry); ADR-002 decision 12 (no committed
    file may hold a credential): a clause that names a credential or a variable reference together
    with holding or placing it must be a negation."""
    for clause in clauses_of(rule_text()):
        if CREDENTIAL.search(clause) and PLACING.search(clause):
            assert NEGATION.search(clause), f"a clause allows a credential in a file: {clause!r}"


def test_every_may_hold_of_the_text_belongs_to_the_negated_orqlet_entry_sentence() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 and the interface decision (the only
    permission-like phrase is inside "no `orqlet-*` entry may hold ..."); ADR-002 decision 12."""
    text = squash(rule_text())

    for match in PERMISSION.finditer(text):
        assert text[: match.start()].endswith("no `orqlet-*` entry "), (
            f"{text[max(0, match.start() - 40) : match.end() + 40]!r} grants what the design "
            "forbids"
        )


# --- the meta file: the rule still reaches an agent that edits the file ------------------------
def test_the_meta_file_keeps_mcp_json_and_every_other_path_of_today_in_paths() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 (`.mcp.json` stays in the meta `paths`, so
    the rule still reaches an agent that edits the file); interface decision (together with all the
    other paths that are there today)."""
    paths = meta_paths()

    assert ".mcp.json" in paths
    assert [path for path in TODAYS_PATHS if path not in paths] == []


def test_the_meta_description_names_both_kinds_of_file() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 (the `description` is reworded to cover
    both kinds of file); interface decision (it contains the words `generate` and `seeded`)."""
    description = meta_description()

    assert "generate" in description
    assert "seeded" in description


def test_the_meta_description_no_longer_says_only_that_files_are_generated() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 (the description is reworded); interface
    decision (it no longer says only that files are generated)."""
    assert meta_description() != TODAYS_DESCRIPTION


def test_the_meta_description_is_one_sentence() -> None:
    """AC-1. expected_behavior_source: interface decision (the description becomes one sentence);
    the description is one line of the front matter of the rule file of each client."""
    description = meta_description().strip()

    assert description
    assert "\n" not in description
    assert re.search(r"[.!?]\s+\S", description) is None, "more than one sentence"


# --- the package contract ----------------------------------------------------------------------
def test_the_meta_file_loads_under_the_workflow_rule_contract() -> None:
    """AC-1. expected_behavior_source: plan P-7 file list (the meta file keeps its contract
    `orqlet.workflow-rule/v1`); ADR-003 decision 7 (only the `description` is reworded, so the
    name of the rule file `orqlet-workflow` stays)."""
    meta = load_contract(LOADER, WorkflowRuleMeta, META.read_bytes(), source=META.name)

    assert meta.schema_id == "orqlet.workflow-rule/v1"
    assert meta.name == "workflow"
    assert ".mcp.json" in meta.paths
    assert meta.description == meta_description()


def test_the_render_request_of_the_packaged_workflow_carries_the_rule_as_a_protected_rule() -> None:
    """AC-1. expected_behavior_source: ADR-003 decision 7 (the rule is rendered from the two files
    of the package and stays a protected file); `build_render_request` is what reads the package
    for every client."""
    request = packaged_request()
    (rule,) = [rule for rule in request.scoped_rules if rule.name == "workflow"]

    assert rule.body == rule_text()
    assert rule.description == meta_description()
    assert ".mcp.json" in rule.paths
    assert rule.file_class is FileClass.PROTECTED
