"""The bundled Graphify and Ponytail snapshots (task one-command-setup, phase P-2, AC-1, AC-2,
AC-4 and AC-11).

Every test cites its `expected_behavior_source`: AC-n is an acceptance criterion of phase P-2 in
docs/design/one-command-setup/plan.yaml, ADR-006 is
docs/design/one-command-setup/design/adr-006-bundled-skills-and-tool-preparation.md, Q-n are the
questions of docs/design/one-command-setup/questions.yaml, and "the interface" is the one that the
Coder gave for P-2 (the folders, the reference lists, the PROVENANCE.md line shapes and the
forbidden words below).

HOW THESE TESTS WERE WRITTEN. The Tester of P-2 wrote them before the snapshots existed, so each is
expected to fail until its files exist. A source file is read from the folder of the installed
`orqlet.workflow` package on disk, not through the manifest, so that a file that the manifest
misses is still scanned; a rendered file is what the three client adapters return for
`packaged_request()`.

Choices:
- AC-4 is checked case-insensitively on every source file of the seven bundled skills (skill.md,
  references/*.md, families/*.md) and on every file the adapters render for them, except
  PROVENANCE.md and the licence files: PROVENANCE.md names the removed text, and a licence is
  upstream text that is not an instruction.
- "Every `references/<name>.md` that the rendered skill body names exists beside it" (AC-11) is
  checked for the seven bundled skills, in the rendered SKILL.md and in each rendered reference
  other than PROVENANCE.md and the licence files.

Deliberately NOT pinned (the design leaves it open, or only a reviewer can tell):
- AC-3, that the hashes equal the upstream files and that a snapshot differs from upstream only by
  the listed adaptations: the security reviewer checks it against the upstream files;
- the wording of an adaptation beyond the names below, and whether graphify's PROVENANCE.md names
  the per-adapter dispatch references as an adaptation in a fixed phrase;
- that benchmark numbers stay attributed to the upstream (ADR-006 decision 2): no form is given;
- that ponytail-help lists the six delivered skills by a fixed name;
- the manifest (AC-9, the manifest check) and the golden files (tests/unit/render).
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
    GRAPHIFY_SHARED_REFERENCES,
    PONYTAIL_SKILL_NAMES,
    packaged_request,
)

pytestmark = pytest.mark.unit

SKILLS_DIR = Path(str(files("orqlet.workflow"))) / "skills"
ADAPTERS: tuple[InstructionAdapter, ...] = (ClaudeCodeAdapter(), CursorAdapter(), CodexAdapter())
CLIENT_BASES = {
    "claude-code": ".claude/skills",
    "cursor": ".agents/skills",
    "codex": ".agents/skills",
}
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
SHA256_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")
REVISION = re.compile(r"[0-9a-f]{40}")
GRAPHIFY_SOURCE = "https://github.com/Graphify-Labs/graphify"
GRAPHIFY_REVISION = "340268a70a83588d6b3c6de1fffb05326350ef1d"
PONYTAIL_SOURCE = "https://github.com/DietrichGebert/ponytail"
PONYTAIL_REVISION = "96608e078b2d5ea607c5c3b8b5a54d1c1fba6846"
PONYTAIL_COPYRIGHT = "Copyright (c) 2026 DietrichGebert"
# Not scanned for AC-4: upstream licence text, and the provenance that names the removed text.
UNSCANNED = frozenset({"PROVENANCE.md", "LICENSE.md", "LICENSE-MIT.md"})
MODEL_NAMES = ("gpt-", "claude-", "sonnet", "opus", "haiku", "gemini", "grok")
INSTALL_STEPS = ("pip install", "uv pip", "pipx install", "--upgrade")
BACKEND_SETTINGS = ("gemini_api_key", "google_api_key", "api_key")
FORBIDDEN = (*MODEL_NAMES, *INSTALL_STEPS, *BACKEND_SETTINGS)
REFERENCE_LINK = re.compile(r"references/([A-Za-z0-9_.-]+\.md)")
HOOK_TEXT = (
    "references/hooks.md",
    "graphify hook install",
    "graphify claude install",
    "graphify agents install",
)


def source_files(name: str) -> list[Path]:
    """skill.md, references/*.md and families/*.md of one skill folder, in path order."""
    folder = SKILLS_DIR / name
    found = [folder / "skill.md"]
    for sub in ("references", "families"):
        found += sorted((folder / sub).glob("*.md")) if (folder / sub).is_dir() else []
    return found


def read(name: str, relative: str) -> str:
    return (SKILLS_DIR / name / relative).read_text(encoding="utf-8")


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
    fields, _ = parse_source(name, read(name, "skill.md"), required=("name", "description"))

    assert set(fields) == {"name", "description"}
    assert fields["name"] == name
    assert NAME.fullmatch(name) is not None
    assert fields["description"] not in {">", "|", ">-", "|-", ">+", "|+"}
    assert len(fields["description"]) > 3


def test_ac1_load_skills_returns_the_bundled_skills_and_none_may_be_started_by_the_agent() -> None:
    """AC-1. expected_behavior_source: AC-1 (`load_skills` returns the seven skills beside the six
    phase skills, and none is marked as a skill the agent may start); ADR-006 decision 3."""
    skills = {skill.name: skill for skill in packaged_request().skills}

    assert set(BUNDLED_SKILL_NAMES) <= set(skills)
    for name in BUNDLED_SKILL_NAMES:
        assert not skills[name].agent_may_start, name


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


def test_ac2_graphify_provenance_names_source_revision_licence_and_notice() -> None:
    """AC-2. expected_behavior_source: AC-2 (Graphify 340268a70a83588d6b3c6de1fffb05326350ef1d;
    Apache-2.0 with the retained MIT terms and the NOTICE text); ADR-006 decision 1 (Graphify's
    NOTICE); the interface (`Source:`, `Revision:`, `Licence:` and `## NOTICE`)."""
    text = provenance("graphify")
    licence = field_line(text, "Licence")

    assert field_line(text, "Source") == GRAPHIFY_SOURCE
    assert field_line(text, "Revision") == GRAPHIFY_REVISION
    assert REVISION.fullmatch(field_line(text, "Revision")) is not None
    assert "Apache-2.0" in licence
    assert "MIT" in licence
    assert section(text, "## NOTICE").strip()


def test_ac2_graphify_provenance_lists_the_adaptations_of_decision_2_q51_and_q52() -> None:
    """AC-2, AC-11. expected_behavior_source: ADR-006 decision 2 (the install steps are replaced
    by a check that `graphify` is on `PATH`); Q-51 (hooks.md and the body section that links it
    are dropped, listed as an adaptation); Q-52 (the `--backend` hint and the
    `pip install 'graphifyy[video]'` step are removed); the interface (the bullets name
    `hooks.md`, `--backend` and `graphifyy[video]`)."""
    adaptations = section(provenance("graphify"), "## Adaptations")

    assert "hooks.md" in adaptations
    assert "--backend" in adaptations
    assert "graphifyy[video]" in adaptations
    assert "PATH" in adaptations


@pytest.mark.parametrize("name", PONYTAIL_SKILL_NAMES)
def test_ac2_ponytail_provenance_names_source_revision_and_the_mit_copyright(name: str) -> None:
    """AC-2. expected_behavior_source: AC-2 (Ponytail 96608e078b2d5ea607c5c3b8b5a54d1c1fba6846;
    MIT with its copyright line); ADR-006 context (MIT, copyright DietrichGebert); the interface
    (`Source:`, `Revision:`, `Licence:`)."""
    text = provenance(name)
    licence = field_line(text, "Licence")

    assert field_line(text, "Source") == PONYTAIL_SOURCE
    assert field_line(text, "Revision") == PONYTAIL_REVISION
    assert "MIT" in licence
    assert PONYTAIL_COPYRIGHT in licence


def test_ac2_graphify_carries_the_apache_licence_and_the_retained_mit_terms() -> None:
    """AC-2. expected_behavior_source: AC-2 ("Each has `references/LICENSE.md`; graphify also has
    `references/LICENSE-MIT.md`"); ADR-006 context (Apache-2.0, with retained MIT terms)."""
    assert "Apache License" in read("graphify", "references/LICENSE.md")
    assert "MIT License" in read("graphify", "references/LICENSE-MIT.md")


@pytest.mark.parametrize("name", PONYTAIL_SKILL_NAMES)
def test_ac2_each_ponytail_skill_carries_the_mit_licence_only(name: str) -> None:
    """AC-2. expected_behavior_source: AC-2 (each has `references/LICENSE.md`; only graphify has
    LICENSE-MIT.md); ADR-006 context (MIT, copyright DietrichGebert)."""
    licence = read(name, "references/LICENSE.md")

    assert "MIT License" in licence
    assert PONYTAIL_COPYRIGHT in licence
    assert not (SKILLS_DIR / name / "references" / "LICENSE-MIT.md").exists()


# --- AC-4: no model, no install step, no backend --------------------------------------------------


def scanned_sources() -> list[tuple[str, Path]]:
    return [
        (name, path)
        for name in BUNDLED_SKILL_NAMES
        for path in source_files(name)
        if path.name not in UNSCANNED
    ]


@pytest.mark.parametrize(
    ("name", "path"),
    scanned_sources() if SKILLS_DIR.joinpath("graphify").is_dir() else [],
    ids=lambda value: value.name if isinstance(value, Path) else str(value),
)
def test_ac4_no_bundled_source_file_names_a_model_an_install_step_or_a_backend(
    name: str, path: Path
) -> None:
    """AC-4. expected_behavior_source: AC-4 (no bundled skill file contains a model name, a
    dependency-install step `pip install`, `uv pip`, `pipx install`, `--upgrade`, or a model
    backend setting `gemini`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `api_key`); ADR-006 decision 2;
    ORQLET-MODEL-001; ORQLET-NOMODEL-001; the interface (the model words of the vendor check plus
    `grok`, case-insensitive, PROVENANCE.md and the licences apart)."""
    text = path.read_text(encoding="utf-8").lower()

    for word in FORBIDDEN:
        assert word not in text, f"{name}/{path.name}: {word}"


def test_ac4_every_bundled_skill_folder_exists_with_files_to_scan() -> None:
    """AC-4. expected_behavior_source: plan P-2 file operations (the seven folders with skill.md);
    this guards the parametrized scan above against scanning nothing."""
    for name in BUNDLED_SKILL_NAMES:
        assert (SKILLS_DIR / name / "skill.md").is_file(), name
    assert len(scanned_sources()) >= 7 + len(GRAPHIFY_SHARED_REFERENCES) + 3


@pytest.mark.parametrize("client", list(CLIENT_BASES))
def test_ac4_no_rendered_file_of_a_bundled_skill_names_a_model_an_install_step_or_a_backend(
    client: str,
) -> None:
    """AC-4. expected_behavior_source: AC-4 and ORQLET-MODEL-001 (a model name appears in a
    generated file only when the policy assigned it; the packaged request assigns none): the
    rendered skill, reference, dispatch and sidecar files, PROVENANCE.md and the licences apart."""
    base = CLIENT_BASES[client]
    checked = 0
    for path, text in rendered()[client].items():
        parts = path.split("/")
        if not path.startswith(base) or parts[2] not in BUNDLED_SKILL_NAMES:
            continue
        if parts[-1] in UNSCANNED:
            continue
        checked += 1
        for word in FORBIDDEN:
            assert word not in text.lower(), f"{path}: {word}"
    assert checked >= len(BUNDLED_SKILL_NAMES)


def test_ac4_graphify_checks_that_graphify_is_on_path_instead_of_installing_it() -> None:
    """AC-4. expected_behavior_source: AC-4 ("The graphify skill checks that `graphify` is on PATH
    instead of installing it; when it is missing, the skill tells the person to run Orqlet's
    install step in a terminal without naming a command, because `orqlet install` arrives in
    P-10"); Q-53; ADR-006 decision 2 and decision 4 (tool preparation happens in `install` only);
    the interface (`command -v graphify` and the phrase `Orqlet's install step`)."""
    body = body_of("graphify")

    assert "command -v graphify" in body
    assert "Orqlet's install step" in body
    assert "orqlet install" not in body.lower()
    assert "uv tool install" not in body


def test_ac4_ponytail_help_names_the_upstream_features_that_are_not_delivered() -> None:
    """AC-4. expected_behavior_source: AC-4 (`ponytail-help` names the status band, the plugin
    hooks and the persistent configuration as upstream features that this package does not
    deliver); ADR-006 decision 2; the interface (a section headed exactly `## Not delivered here`
    that names `band`, `plugin hooks` and `persistent configuration`)."""
    text = section(body_of("ponytail-help"), "## Not delivered here").lower()

    assert "band" in text
    assert "plugin hooks" in text
    assert "persistent configuration" in text


# --- AC-11: graphify's shared references ----------------------------------------------------------


@pytest.mark.parametrize("reference", GRAPHIFY_SHARED_REFERENCES)
def test_ac11_each_shared_reference_renders_once_with_the_same_bytes_for_every_client(
    reference: str,
) -> None:
    """AC-11. expected_behavior_source: AC-11 (the seven references ship once, rendered with the
    same bytes for every client); Q-52 ("Once under graphify/references/ for every client")."""
    texts = {
        client: rendered()[client][f"{base}/graphify/references/{reference}"]
        for client, base in CLIENT_BASES.items()
    }

    assert texts["claude-code"] == texts["cursor"] == texts["codex"]
    assert (SKILLS_DIR / "graphify" / "references" / reference).is_file()


def test_ac11_no_hooks_reference_is_shipped_or_rendered() -> None:
    """AC-11. expected_behavior_source: AC-11 ("No `references/hooks.md` is rendered"); Q-51
    ("Drop hooks.md")."""
    assert not (SKILLS_DIR / "graphify" / "references" / "hooks.md").exists()
    assert not list(SKILLS_DIR.glob("*/families/hooks.md"))
    for client, client_files in rendered().items():
        assert not [path for path in client_files if path.endswith("/hooks.md")], client


def test_ac11_the_graphify_body_neither_links_hooks_md_nor_registers_graphify() -> None:
    """AC-11. expected_behavior_source: AC-11 (the skill body has no section that links
    hooks.md or tells the agent to run `graphify hook install`, `graphify claude install` or
    `graphify agents install`); Q-51; ADR-006 rejected alternative (Graphify's own installer writes
    registrations and hooks itself)."""
    body = body_of("graphify")
    families = "\n".join(read("graphify", f"families/{f}.md") for f in ("claude", "agents"))

    for text in HOOK_TEXT:
        assert text not in body, text
        assert text not in families, text


def test_ac11_github_and_merge_has_no_backend_hint_and_add_watch_no_install_step() -> None:
    """AC-11. expected_behavior_source: AC-11 (github-and-merge.md has no `--backend` hint and
    add-watch.md no `pip install 'graphifyy[video]'` step); Q-52."""
    assert "--backend" not in read("graphify", "references/github-and-merge.md")
    add_watch = read("graphify", "references/add-watch.md")
    assert "pip install" not in add_watch
    assert "graphifyy[video]" not in add_watch


@pytest.mark.parametrize("client", list(CLIENT_BASES))
def test_ac11_every_reference_that_a_rendered_bundled_file_names_exists_beside_it(
    client: str,
) -> None:
    """AC-11. expected_behavior_source: AC-11 ("Every `references/<name>.md` that the rendered
    skill body names exists beside it for each client"); Q-52 (without the references the
    rendered skill links files that do not exist). Checked in SKILL.md and in each rendered
    reference, dispatch.md included, for the seven bundled skills."""
    base = CLIENT_BASES[client]
    files = rendered()[client]
    for name in BUNDLED_SKILL_NAMES:
        folder = f"{base}/{name}"
        texts = {
            path: text
            for path, text in files.items()
            if path == f"{folder}/SKILL.md"
            or (path.startswith(f"{folder}/references/") and path.split("/")[-1] not in UNSCANNED)
        }
        assert f"{folder}/SKILL.md" in texts, folder
        for path, text in texts.items():
            for linked in REFERENCE_LINK.findall(text):
                assert f"{folder}/references/{linked}" in files, f"{path} -> {linked}"


def test_ac11_the_graphify_body_links_the_seven_shared_references() -> None:
    """AC-11. expected_behavior_source: Q-52 ("The graphify skill body links seven more
    references (add-watch, exports, extraction-spec, github-and-merge, query, transcribe,
    update)"): the rendered SKILL.md of each client names every one of them. Whether the body
    links `references/dispatch.md` is not sourced and is not pinned."""
    for client, base in CLIENT_BASES.items():
        linked = set(REFERENCE_LINK.findall(rendered()[client][f"{base}/graphify/SKILL.md"]))
        assert set(GRAPHIFY_SHARED_REFERENCES) <= linked, client
