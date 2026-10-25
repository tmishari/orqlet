import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.scan.python_scanner import PythonScanner
from orqlet.adapters.standards.pack_source import DirectoryPackSource
from orqlet.application.usecases.standards_for import StandardsAnswer, StandardsQuery, standards_for
from orqlet.domain.paths import CanonicalPath
from orqlet.domain.resolver import WeakeningError
from tests.fakes.memory_fs import MemoryFileSystem
from tests.support.trees import pack_dir, repo, tech_packs, with_files

pytestmark = pytest.mark.unit

LOADER = StrictYamlLoader()
SCANNERS = (PythonScanner(),)


def run(project: MemoryFileSystem, packs: MemoryFileSystem | None, **query: str) -> StandardsAnswer:
    source = DirectoryPackSource(packs, LOADER) if packs is not None else None
    return standards_for(project, LOADER, SCANNERS, source, StandardsQuery(**query))


def test_packs_that_match_the_stack_apply_and_later_packs_tighten_earlier_ones() -> None:
    answer = run(repo("uv_fastapi"), pack_dir())

    assert [p.id for p in answer.packs] == ["sample", "web"]
    levels = {r.id: r.level.name for r in answer.rules}
    assert levels["SAMPLE-002"] == "MUST"  # the web pack tightened SHOULD to MUST
    assert "WEB-001" in levels


def test_a_pack_for_a_framework_the_project_does_not_use_is_skipped_with_a_reason() -> None:
    answer = run(repo("poetry_cli"), pack_dir())

    assert [p.id for p in answer.packs] == ["sample"]
    assert answer.skipped[0][0] == "web"
    assert "technologies" in answer.skipped[0][1]


def test_a_project_with_no_scanner_gets_no_language_specific_packs() -> None:
    answer = run(repo("js_only"), pack_dir())

    assert answer.packs == ()
    assert answer.language is None
    assert {pack_id for pack_id, _ in answer.skipped} == {"sample", "web"}


def test_the_query_filters_by_phase_and_path() -> None:
    project = repo("uv_fastapi")

    design = {r.id for r in run(project, pack_dir(), phase="design").rules}
    docs = {r.id for r in run(project, pack_dir(), path="docs/readme.md").rules}

    build = {r.id for r in run(project, pack_dir(), phase="build").rules}

    assert "SAMPLE-003" in design
    assert "SAMPLE-003" not in build  # scoped to the design phase
    assert "SAMPLE-001" not in docs  # scoped to src/**


def test_the_same_inputs_give_the_same_hash_and_a_changed_pack_changes_it() -> None:
    first = run(repo("uv_fastapi"), pack_dir()).rules_hash
    again = run(repo("uv_fastapi"), pack_dir()).rules_hash
    changed_packs = pack_dir()
    changed_packs.write_atomic(
        CanonicalPath.parse("sample/rules/python.yaml"),
        b"schema: orqlet.rules/v1\nrules:\n  - {id: SAMPLE-001, level: MUST, text: other text}\n",
    )

    assert first == again
    assert run(repo("uv_fastapi"), changed_packs).rules_hash != first


def test_project_additions_can_tighten_but_never_relax_a_pack_rule() -> None:
    tighter = repo("uv_fastapi")
    tighter.write_atomic(
        CanonicalPath.parse(".orqlet/rules.yaml"),
        b"schema: orqlet.rules/v1\nrules:\n  - {id: SAMPLE-001, level: MUST, text: t,"
        b" enforcement: deterministic}\n  - {id: PROJ-1, level: MUST, text: project rule}\n",
    )
    assert "PROJ-1" in {r.id for r in run(tighter, pack_dir()).rules}

    relaxed = repo("uv_fastapi")
    relaxed.write_atomic(
        CanonicalPath.parse(".orqlet/rules.yaml"),
        b"schema: orqlet.rules/v1\nrules:\n  - {id: SAMPLE-001, level: SHOULD, text: weaker}\n",
    )
    with pytest.raises(WeakeningError, match="SAMPLE-001"):
        run(relaxed, pack_dir())


def test_without_packs_only_the_project_rules_remain() -> None:
    rules = "schema: orqlet.rules/v1\nrules:\n  - {id: P-1, level: MUST, text: x}\n"
    project = with_files({"pyproject.toml": "[project]\nname='x'\n", ".orqlet/rules.yaml": rules})

    answer = run(project, None)

    assert [r.id for r in answer.rules] == ["P-1"]
    assert answer.packs == ()


def test_an_unevaluated_python_constraint_is_reported_as_not_run() -> None:
    manifest = (
        "schema: orqlet.standards-pack/v1\nid: p\nversion: 1.0.0\nowner: o\n"
        "applies_to: {languages: [python], python: '>=3.12'}\n"
    )
    packs = with_files({"p/pack.yaml": manifest})

    answer = run(repo("uv_fastapi"), packs)

    assert any("applies_to.python" in item for item in answer.not_run)


# --- the team's standards folder ---------------------------------------------------------------
PROMPTS_RULES = (
    "schema: orqlet.rules/v1\nrules:\n"
    "  - {id: TEAM-001, level: MUST, text: Services log with correlation ids.,\n"
    "     scope: {paths: ['src/**']}}\n"
)


def test_rules_in_the_standards_folder_are_served() -> None:
    project = repo("uv_fastapi")
    project.write_atomic(CanonicalPath.parse(".prompts/rules.yaml"), PROMPTS_RULES.encode())

    answer = run(project, None)

    assert [(r.id, r.source) for r in answer.rules] == [("TEAM-001", "prompts")]


def test_the_standards_folder_comes_after_the_packs_and_may_tighten_but_not_relax_them() -> None:
    tighter = repo("uv_fastapi")
    tighter.write_atomic(
        CanonicalPath.parse(".prompts/rules.yaml"),
        b"schema: orqlet.rules/v1\nrules:\n  - {id: SAMPLE-001, level: MUST, text: t,"
        b" enforcement: deterministic, scope: {paths: ['src/**']}}\n",
    )
    relaxed = repo("uv_fastapi")
    relaxed.write_atomic(
        CanonicalPath.parse(".prompts/rules.yaml"),
        b"schema: orqlet.rules/v1\nrules:\n  - {id: SAMPLE-001, level: SHOULD, text: weaker}\n",
    )

    assert "SAMPLE-001" in {r.id for r in run(tighter, pack_dir()).rules}
    with pytest.raises(WeakeningError, match="SAMPLE-001"):
        run(relaxed, pack_dir())


def test_project_additions_come_after_the_standards_folder() -> None:
    project = repo("uv_fastapi")
    project.write_atomic(CanonicalPath.parse(".prompts/rules.yaml"), PROMPTS_RULES.encode())
    project.write_atomic(
        CanonicalPath.parse(".orqlet/rules.yaml"),
        b"schema: orqlet.rules/v1\nrules:\n  - {id: TEAM-001, level: MUST, text: stricter,"
        b" enforcement: review, scope: {paths: ['src/**']}}\n",
    )

    (rule,) = run(project, None).rules

    assert (rule.source, rule.text) == ("project", "stricter")


def test_a_broken_rules_file_is_an_error_that_names_it_not_a_silent_skip() -> None:
    project = repo("uv_fastapi")
    project.write_atomic(CanonicalPath.parse(".prompts/rules.yaml"), b"rules: [oops")

    with pytest.raises(Exception, match=r"\.prompts/rules\.yaml"):
        run(project, None)


def test_a_standards_folder_without_a_rules_file_is_fine() -> None:
    project = repo("uv_fastapi")
    project.write_atomic(CanonicalPath.parse(".prompts/architecture.md"), b"# Notes\n")

    assert run(project, None).rules == ()


# --- technologies other than Python ---------------------------------------------------------------
def _run_with_technologies(project: MemoryFileSystem, packs: MemoryFileSystem) -> StandardsAnswer:
    from orqlet.adapters.scan.technology_scanners import (
        ContainerScanner,
        GoScanner,
        NodeScanner,
        PythonTechnologyScanner,
        RustScanner,
    )

    scanners = (
        PythonTechnologyScanner(),
        GoScanner(),
        RustScanner(),
        NodeScanner(),
        ContainerScanner(),
    )
    return standards_for(
        project, LOADER, SCANNERS, DirectoryPackSource(packs, LOADER), StandardsQuery(), scanners
    )


def test_a_go_pack_applies_to_a_go_project_and_a_python_pack_does_not() -> None:
    answer = _run_with_technologies(repo("go_service"), tech_packs())

    assert [p.id for p in answer.packs] == ["data", "go"]
    assert {pack_id for pack_id, _ in answer.skipped} == {"python-only"}
    assert {r.id for r in answer.rules} == {"GO-001", "DATA-001", "DATA-002"}
    assert answer.language == "Go"


def test_a_pack_matches_a_technology_by_name_whatever_the_language() -> None:
    answer = _run_with_technologies(repo("rust_cli"), tech_packs())

    assert [p.id for p in answer.packs] == ["data"]  # rdkafka is Kafka; no Go or Python here
    assert "DATA-001" in {r.id for r in answer.rules}


def test_a_monorepo_gets_every_pack_that_matches_any_of_its_services() -> None:
    answer = _run_with_technologies(repo("monorepo"), tech_packs())

    assert [p.id for p in answer.packs] == ["data", "go", "python-only"]


def test_a_project_with_no_matching_technology_gets_no_packs_and_says_why() -> None:
    answer = _run_with_technologies(repo("empty"), tech_packs())

    assert answer.packs == ()
    assert {pack_id for pack_id, _ in answer.skipped} == {"data", "go", "python-only"}
    assert all("do not include" in reason or "none of" in reason for _, reason in answer.skipped)
