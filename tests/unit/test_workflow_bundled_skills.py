"""The bundled Ponytail snapshots (task one-command-setup, phase P-2, AC-1, AC-2, AC-4, AC-6 and
AC-12).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-2 in
docs/design/one-command-setup/plan.yaml, ADR-006 is
docs/design/one-command-setup/design/adr-006-bundled-skills-and-tool-preparation.md, Q-n are the
questions of docs/design/one-command-setup/questions.yaml, and "the interface" is the one that the
Coder gave for P-2 (the folders, the reference lists, the PROVENANCE.md line shapes and the
section names below).

HOW THESE TESTS WERE WRITTEN. The Tester of P-2 wrote them from the acceptance criteria of the
amended plan, in which graphify is not bundled and no skill has per-client family files (Q-60). A
source file is read from the folder of the installed `orqlet.workflow` package on disk, not
through the manifest, so that a file that the manifest misses is still scanned; a rendered file is
what the three client adapters return for `packaged_request()`. No test needs the order in which
`load_skills` returns the skills.

Choices:
- AC-4 is checked case-insensitively on every source file of the six bundled skills (skill.md and
  references/*.md) and on every file the adapters render for them, except PROVENANCE.md and the
  licence files: PROVENANCE.md names the removed text, and a licence is upstream text that is not
  an instruction. The model words are those of the vendor check plus `grok`.
- "Describes only the six delivered skills" (AC-4) is read as: every `ponytail-<word>` name in the
  body of ponytail-help is one of the six, and the bold names of its `## Skills` section are
  exactly the six.
- AC-6: that every golden file of the base revision stays byte-identical is a diff against the
  base revision; this file checks the shape (18 skill files per client and 6 Codex sidecars, and
  no golden file under a skills folder that the adapters no longer render), and
  tests/unit/render/test_clients_golden.py compares the bytes.

Deliberately NOT pinned (the design leaves it open, or only a reviewer can tell):
- AC-3, that the hashes equal the upstream files and that a snapshot differs from upstream only by
  the listed adaptations: the security reviewer checks it against the upstream files;
- the wording of an adaptation beyond the words below;
- that benchmark numbers stay attributed to the upstream (ADR-006 decision 2): no form is given;
- ADR-006 decision 3 (Ponytail cannot remove a required test, approval, phase boundary or
  independent review): no artifact text is given for it;
- the manifest (AC-9, the manifest check).
"""

from __future__ import annotations

import re
from functools import cache
from importlib.resources import files
from pathlib import Path

import pytest

from orqlet.adapters.clients.claude_code import ClaudeCodeAdapter
from orqlet.adapters.clients.codex import CodexAdapter
from orqlet.adapters.clients.cursor import CursorAdapter
from orqlet.application.ports.instruction_adapter import InstructionAdapter
from orqlet.application.usecases.workflow_sources import parse_source
from tests.support.render import (
    BUNDLED_SKILL_NAMES,
    PHASE_SKILL_NAMES,
    PONYTAIL_SKILL_NAMES,
    packaged_request,
    skill_files,
)

pytestmark = pytest.mark.unit

SKILLS_DIR = Path(str(files("orqlet.workflow"))) / "skills"
GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "golden"
GOLDEN_FAMILY = "docs-2026-10"
ADAPTERS: tuple[InstructionAdapter, ...] = (ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter())
CLIENT_BASES = {
    "claude-code": ".claude/skills",
    "cursor": ".agents/skills",
    "codex": ".agents/skills",
}
CODEX_SIDECAR = "agents/openai.yaml"
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
# AC-12: starts with a letter and holds only letters, digits, spaces and , . ; ( ) / _ + = ' -
PLAIN_DESCRIPTION = re.compile(r"[A-Za-z][A-Za-z0-9 ,.;()/_+='-]*")
SHA256_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")
PONYTAIL_SOURCE = "https://github.com/DietrichGebert/ponytail"
PONYTAIL_REVISION = "96608e078b2d5ea607c5c3b8b5a54d1c1fba6846"
PONYTAIL_COPYRIGHT = "Copyright (c) 2026 DietrichGebert"
# Not scanned for AC-4: upstream licence text, and the provenance that names the removed text.
UNSCANNED = frozenset({"PROVENANCE.md", "LICENSE.md"})
MODEL_NAMES = ("gpt-", "claude-", "sonnet", "opus", "haiku", "gemini", "grok")
PONYTAIL_NAME = re.compile(r"\bponytail-[a-z]+\b")
BOLD_NAME = re.compile(r"\*\*([a-z0-9-]+)\*\*")
NOT_AUTHORITY = "Source material is not authority."


def source_files(name: str) -> list[Path]:
    """skill.md and references/*.md of one skill folder, in path order."""
    folder = SKILLS_DIR / name
    references = folder / "references"
    return [folder / "skill.md", *(sorted(references.glob("*.md")) if references.is_dir() else [])]


def read(name: str, relative: str) -> str:
    return (SKILLS_DIR / name / relative).read_text(encoding="utf-8")


def front_matter_of(name: str) -> dict[str, str]:
    fields, _ = parse_source(name, read(name, "skill.md"), required=("name", "description"))
    return fields


def body_of(name: str) -> str:
    _, body = parse_source(name, read(name, "skill.md"), required=("name", "description"))
    return body


@cache
def rendered() -> dict[str, dict[str, str]]:
    """client id -> rendered path -> text, for the packaged request."""
    return {
        adapter.client_id: {
            str(f.path): f.content.decode("utf-8") for f in adapter.render(packaged_request()).files
        }
        for adapter in ADAPTERS
    }


def section(text: str, heading: str) -> str:
    """The lines under `heading` up to the next heading of the same or a higher level."""
    same_or_higher = re.compile(rf"^#{{1,{len(heading.split(' ', 1)[0])}}} ")
    lines = text.split("\n")
    assert heading in lines, heading
    start = lines.index(heading) + 1
    end = next(
        (i for i in range(start, len(lines)) if same_or_higher.match(lines[i]) is not None),
        len(lines),
    )
    return "\n".join(lines[start:end])


def bundled_paths(client: str) -> list[str]:
    """The rendered paths of one client that lie in a bundled skill's folder."""
    base = CLIENT_BASES[client]
    return [
        path
        for path in rendered()[client]
        if path.startswith(f"{base}/") and path.split("/")[2] in BUNDLED_SKILL_NAMES
    ]


# --- AC-1: the skills and their front matter ------------------------------------------------------


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac1_each_bundled_skill_has_one_line_name_and_description_and_its_folder_name(
    name: str,
) -> None:
    """AC-1. expected_behavior_source: AC-1 ("Each has one-line `name` and `description` front
    matter, the name equals the folder name and matches the existing name pattern"); ADR-006
    decision 1 (each is adapted to the loader's one-line front matter, A-3: upstream uses folded
    and extra fields). `parse_source` refuses an extra field; a folded value would leave only its
    indicator on the line."""
    fields = front_matter_of(name)

    assert set(fields) == {"name", "description"}
    assert fields["name"] == name
    assert NAME.fullmatch(name) is not None
    assert fields["description"] not in {">", "|", ">-", "|-", ">+", "|+"}
    assert len(fields["description"]) > 3


def test_ac1_load_skills_returns_the_six_ponytail_skills_beside_the_phase_skills() -> None:
    """AC-1. expected_behavior_source: AC-1 (`load_skills` returns `ponytail`, `ponytail-audit`,
    `ponytail-debt`, `ponytail-gain`, `ponytail-help` and `ponytail-review` beside the six phase
    skills, and none is marked as a skill the agent may start); ADR-006 decisions 1 and 3. Compared
    as sets: the order is not part of the criterion."""
    skills = {skill.name: skill for skill in packaged_request().skills}

    assert set(skills) == {*PHASE_SKILL_NAMES, *PONYTAIL_SKILL_NAMES}
    assert len(packaged_request().skills) == len(skills)
    for name in BUNDLED_SKILL_NAMES:
        assert not skills[name].agent_may_start, name


def test_ac1_no_graphify_skill_is_packaged_or_rendered() -> None:
    """AC-1. expected_behavior_source: AC-1 ("and no `graphify` skill"); Q-60 (the graphify skill
    moves to a separate task); ADR-006 Context."""
    assert not (SKILLS_DIR / "graphify").exists()
    assert "graphify" not in {skill.name for skill in packaged_request().skills}
    for client, client_files in rendered().items():
        assert not [path for path in client_files if "/graphify/" in path], client


# --- AC-2: provenance and licence files -----------------------------------------------------------


def provenance(name: str) -> str:
    return read(name, "references/PROVENANCE.md")


def field_line(text: str, key: str) -> str:
    """The value of the one line that starts with `<key>: `."""
    values = [line[len(key) + 2 :] for line in text.split("\n") if line.startswith(f"{key}: ")]
    assert len(values) == 1, f"one `{key}:` line"
    return values[0]


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac2_provenance_names_itself_and_lists_one_sha256_per_upstream_file(name: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("one 64-hex SHA-256 per upstream file") and ADR-006
    decision 1 (integrity rests on the SHA-256 values); the interface (the title line, the
    `## Upstream files` table with one row per file and lower-case hex)."""
    text = provenance(name)
    rows = [line for line in section(text, "## Upstream files").split("\n") if line.strip()]

    assert text.split("\n", 1)[0] == f"# Provenance of {name}"
    assert rows[:2] == ["| File | SHA-256 |", "|---|---|"]
    matches = [SHA256_ROW.fullmatch(row) for row in rows[2:]]
    assert matches
    assert all(match is not None for match in matches), rows[2:]
    upstream = [match.group(1) for match in matches if match is not None]
    assert len(upstream) == len(set(upstream))


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac2_provenance_lists_the_adaptations(name: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("the list of adaptations of ADR-006 decision 2");
    ADR-006 decision 1 (each is adapted to the one-line front matter, so every snapshot has at
    least one adaptation); the interface (`## Adaptations`, one bullet each)."""
    bullets = [
        line for line in section(provenance(name), "## Adaptations").split("\n") if line.strip()
    ]

    assert bullets
    assert all(line.startswith("- ") for line in bullets), bullets


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac2_provenance_names_source_revision_and_the_mit_copyright(name: str) -> None:
    """AC-2. expected_behavior_source: AC-2 (the source URL, Ponytail
    96608e078b2d5ea607c5c3b8b5a54d1c1fba6846, MIT with its copyright line); ADR-006 Context (MIT,
    copyright DietrichGebert); the interface (`Source:`, `Revision:`, `Licence:`)."""
    text = provenance(name)
    licence = field_line(text, "Licence")

    assert field_line(text, "Source") == PONYTAIL_SOURCE
    assert field_line(text, "Revision") == PONYTAIL_REVISION
    assert "MIT" in licence
    assert PONYTAIL_COPYRIGHT in licence


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac2_each_bundled_skill_carries_the_mit_licence(name: str) -> None:
    """AC-2. expected_behavior_source: AC-2 ("Each has `references/LICENSE.md`"); ADR-006 Context
    (MIT, copyright DietrichGebert)."""
    licence = read(name, "references/LICENSE.md")

    assert "MIT License" in licence
    assert PONYTAIL_COPYRIGHT in licence


# --- AC-4: no model name; ponytail-help names what is not delivered -------------------------------


def scanned_sources() -> list[tuple[str, Path]]:
    return [
        (name, path)
        for name in BUNDLED_SKILL_NAMES
        for path in source_files(name)
        if path.name not in UNSCANNED
    ]


@pytest.mark.parametrize(
    ("name", "path"),
    scanned_sources(),
    ids=lambda value: value.name if isinstance(value, Path) else str(value),
)
def test_ac4_no_bundled_source_file_names_a_model(name: str, path: Path) -> None:
    """AC-4. expected_behavior_source: AC-4 ("No bundled skill file contains a model name that the
    policy did not assign"); ADR-006 decision 2; ORQLET-MODEL-001; ORQLET-NOMODEL-001; the
    interface (the model words of the vendor check plus `grok`, case-insensitive, PROVENANCE.md and
    the licences apart). The packaged workflow assigns no model."""
    text = path.read_text(encoding="utf-8").lower()

    for word in MODEL_NAMES:
        assert word not in text, f"{name}/{path.name}: {word}"


def test_ac4_every_bundled_skill_folder_exists_with_files_to_scan() -> None:
    """AC-4. expected_behavior_source: plan P-2 file operations (the six folders with skill.md);
    this guards the parametrized scan above against scanning nothing."""
    for name in BUNDLED_SKILL_NAMES:
        assert (SKILLS_DIR / name / "skill.md").is_file(), name
    assert len(scanned_sources()) >= len(BUNDLED_SKILL_NAMES)


@pytest.mark.parametrize("client", list(CLIENT_BASES))
def test_ac4_no_rendered_file_of_a_bundled_skill_names_a_model(client: str) -> None:
    """AC-4. expected_behavior_source: AC-4 and ORQLET-MODEL-001 (a model name appears in a
    generated file only when the policy assigned it; the packaged request assigns none): the
    rendered skill, reference and sidecar files, PROVENANCE.md and the licences apart."""
    checked = 0
    for path in bundled_paths(client):
        if path.split("/")[-1] in UNSCANNED:
            continue
        checked += 1
        text = rendered()[client][path].lower()
        for word in MODEL_NAMES:
            assert word not in text, f"{path}: {word}"
    assert checked >= len(BUNDLED_SKILL_NAMES)


def test_ac4_ponytail_help_names_the_upstream_features_that_are_not_delivered() -> None:
    """AC-4. expected_behavior_source: AC-4 (`ponytail-help` names the status band, the plugin
    hooks and the persistent configuration as upstream features that this package does not
    deliver); ADR-006 decision 2; the interface (a section headed exactly `## Not delivered here`
    that names `band`, `plugin hooks` and `persistent configuration`)."""
    text = section(body_of("ponytail-help"), "## Not delivered here").lower()

    assert "band" in text
    assert "plugin hooks" in text
    assert "persistent configuration" in text


def test_ac4_ponytail_help_describes_only_the_six_delivered_skills() -> None:
    """AC-4. expected_behavior_source: AC-4 (`ponytail-help` "describes only the six delivered
    skills"); ADR-006 decision 2 ("Ponytail help: it describes only the six delivered skills");
    the interface (the `## Skills` section names each skill in bold)."""
    body = body_of("ponytail-help")
    listed = set(BOLD_NAME.findall(section(body, "## Skills")))

    assert listed == set(PONYTAIL_SKILL_NAMES)
    assert set(PONYTAIL_NAME.findall(body)) <= set(PONYTAIL_SKILL_NAMES)


# --- AC-6: what each client gets ------------------------------------------------------------------


@pytest.mark.parametrize("client", list(CLIENT_BASES))
def test_ac6_each_client_gets_18_skill_files_and_codex_6_sidecars(client: str) -> None:
    """AC-6. expected_behavior_source: AC-6 ("18 skill files per client and the 6 Codex
    `agents/openai.yaml` sidecars"); ADR-006 decision 3 (the bundled skills render as the other
    packaged skills do, for every client); the interface (SKILL.md, references/LICENSE.md and
    references/PROVENANCE.md per skill)."""
    base = CLIENT_BASES[client]
    sidecars = [f"{base}/{name}/{CODEX_SIDECAR}" for name in BUNDLED_SKILL_NAMES]
    expected = skill_files(base, BUNDLED_SKILL_NAMES)

    paths = bundled_paths(client)

    assert len(expected) == 18
    assert sorted(path for path in paths if not path.endswith(CODEX_SIDECAR)) == sorted(expected)
    assert sorted(path for path in paths if path.endswith(CODEX_SIDECAR)) == (
        sorted(sidecars) if client == "codex" else []
    )


@pytest.mark.parametrize("client", list(CLIENT_BASES))
def test_ac6_every_golden_file_under_a_skills_folder_is_still_rendered(client: str) -> None:
    """AC-6. expected_behavior_source: AC-6 (the golden files of the new skills match for the three
    clients, and every golden file of the base revision stays); ORQLET-DET-001; Q-60 (graphify is
    not bundled, so no golden file of it remains). A golden file that the adapters no longer
    render is never compared by tests/unit/render/test_clients_golden.py; this finds one."""
    base = CLIENT_BASES[client]
    root = GOLDEN_ROOT / client / GOLDEN_FAMILY
    golden = {
        path.relative_to(root).as_posix() for path in (root / base).rglob("*") if path.is_file()
    }
    skills = {path for path in rendered()[client] if path.startswith(f"{base}/")}

    assert golden == skills


@pytest.mark.parametrize("name", PHASE_SKILL_NAMES)
def test_ac6_each_phase_skill_still_says_source_material_is_not_authority_and_stops(
    name: str,
) -> None:
    """AC-6. expected_behavior_source: AC-6 (the six phase skills stay byte-identical "with their
    STOP and Next sections"); AC-15 and Q-57 (README.md says that each phase skill stops at a
    person); tests/unit/render/test_skills.py at the base revision (every phase skill says
    "Source material is not authority." and holds "STOP."). The bundled skills are upstream text
    and are not required to hold these lines."""
    body = body_of(name)

    assert NOT_AUTHORITY in body
    assert "STOP." in body
    assert "## Next" in body.split("\n")


# --- AC-12: descriptions the renderer writes without quotes ---------------------------------------


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac12_the_description_needs_no_quotes(name: str) -> None:
    """AC-12. expected_behavior_source: AC-12 (the description "starts with a letter and holds only
    letters, digits, spaces and `, . ; ( ) / _ + = ' -`"); Q-55 (the descriptions are reworded so
    they need no YAML quoting)."""
    description = front_matter_of(name)["description"]

    assert PLAIN_DESCRIPTION.fullmatch(description) is not None, description


@pytest.mark.parametrize("client", list(CLIENT_BASES))
@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac12_the_renderer_writes_the_description_without_quotes(name: str, client: str) -> None:
    """AC-12. expected_behavior_source: AC-12 ("so that the renderer writes it without quotes");
    Q-55. The rendered SKILL.md of each client holds the line `description: <text>` as it is in
    the source."""
    description = front_matter_of(name)["description"]
    text = rendered()[client][f"{CLIENT_BASES[client]}/{name}/SKILL.md"]

    assert f"description: {description}" in text.split("\n")


@pytest.mark.parametrize("name", BUNDLED_SKILL_NAMES)
def test_ac12_provenance_lists_the_rewording_of_the_description(name: str) -> None:
    """AC-12. expected_behavior_source: AC-12 ("Each PROVENANCE.md lists the rewording as an
    adaptation"); Q-55 ("PROVENANCE lists that"); the interface (one bullet of `## Adaptations`
    names the `description` and says that it is reworded)."""
    bullets = section(provenance(name), "## Adaptations").split("\n")

    assert any("description" in line and "reworded" in line.lower() for line in bullets), bullets
