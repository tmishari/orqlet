"""The workflow manifest lists every protected file, and its digest recomputes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.workflow_package import PackagedWorkflow
from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.standards_pack import RuleFile
from orqlet.application.contracts.workflow_package import (
    ExemptClasses,
    ManifestEntry,
    WorkflowIdentity,
    WorkflowManifest,
)
from orqlet.application.usecases.workflow_manifest import (
    build_manifest,
    manifest_digest,
    manifest_problems,
    normalised_hash,
)

pytestmark = pytest.mark.unit

WORKFLOW_DIR = Path(__file__).resolve().parents[2] / "src" / "orqlet" / "workflow"
LOADER = StrictYamlLoader()
IDENTITY = WorkflowIdentity(
    schema_id="orqlet.workflow-identity/v1", workflow_version="1.0.0", controls_level=1
)


def test_the_committed_manifest_matches_the_files_on_disk() -> None:
    assert PackagedWorkflow().problems() == ()


def test_the_committed_manifest_is_what_the_build_tool_would_write() -> None:
    from tools.build_manifest import render

    assert (WORKFLOW_DIR / "MANIFEST.json").read_text(encoding="utf-8") == render()


def test_the_digest_is_the_hash_of_the_canonical_manifest_and_is_stable() -> None:
    first = PackagedWorkflow().release
    second = PackagedWorkflow().release

    assert first == second
    assert len(first.digest) == 64
    identity = json.loads((WORKFLOW_DIR / "identity.json").read_text(encoding="utf-8"))
    assert str(first.version) == identity["workflow_version"]
    assert first.controls_level == identity["controls_level"]


def test_every_manifest_path_is_readable_and_sorted() -> None:
    workflow = PackagedWorkflow()
    paths = workflow.paths()

    assert list(paths) == sorted(paths)
    for path in paths:
        assert workflow.read_text(path)


def test_the_manifest_does_not_list_itself_the_release_history_or_python_files() -> None:
    paths = PackagedWorkflow().paths()

    assert "MANIFEST.json" not in paths
    assert "releases.json" not in paths
    assert not any(path.endswith((".py", ".pyc")) for path in paths)


def test_the_manifest_lists_the_committed_schemas() -> None:
    paths = PackagedWorkflow().paths()

    assert "schemas/orqlet.versions.v1.json" in paths


def test_a_changed_file_a_missing_file_and_an_extra_file_are_all_reported() -> None:
    files = {"a.md": b"one\n", "b.md": b"two\n"}
    manifest = build_manifest(IDENTITY, files)

    assert manifest_problems(manifest, files) == ()
    changed = manifest_problems(manifest, {**files, "a.md": b"ONE\n"})
    missing = manifest_problems(manifest, {"a.md": b"one\n"})
    extra = manifest_problems(manifest, {**files, "c.md": b"x"})
    assert changed == ("a.md differs from the manifest",)
    assert missing == ("b.md is listed but missing",)
    assert extra == ("c.md is present but not listed",)


def test_the_digest_changes_with_any_byte_and_with_the_version() -> None:
    files = {"a.md": b"one\n"}
    base = manifest_digest(build_manifest(IDENTITY, files))

    assert manifest_digest(build_manifest(IDENTITY, {"a.md": b"one!\n"})) != base
    other = WorkflowIdentity(
        schema_id="orqlet.workflow-identity/v1", workflow_version="1.0.1", controls_level=1
    )
    assert manifest_digest(build_manifest(other, files)) != base


def test_a_windows_checkout_with_crlf_gives_the_same_hash() -> None:
    assert normalised_hash(b"a\r\nb\r\n") == normalised_hash(b"a\nb\n")


def test_the_digest_does_not_depend_on_the_order_files_were_given() -> None:
    forward = {"a.md": b"1", "b.md": b"2"}
    backward = {"b.md": b"2", "a.md": b"1"}

    assert manifest_digest(build_manifest(IDENTITY, forward)) == manifest_digest(
        build_manifest(IDENTITY, backward)
    )


def test_manifest_entries_are_hashes_not_paths_outside_the_package() -> None:
    manifest = load_contract(
        LOADER, WorkflowManifest, (WORKFLOW_DIR / "MANIFEST.json").read_bytes(), source="m"
    )

    assert all(
        not entry.path.startswith(("/", "..")) and "\\" not in entry.path
        for entry in manifest.files
    )
    assert isinstance(manifest.files[0], ManifestEntry)


def test_the_manifest_json_is_valid_json_with_sorted_keys() -> None:
    text = (WORKFLOW_DIR / "MANIFEST.json").read_text(encoding="utf-8")
    data = json.loads(text)

    assert list(data) == sorted(data)
    assert text.endswith("}\n")


class TestWorkflowFiles:
    def test_the_exempt_classes_load_under_their_contract(self) -> None:
        exempt = load_contract(
            LOADER, ExemptClasses, (WORKFLOW_DIR / "exempt.yaml").read_bytes(), source="exempt"
        )

        assert exempt.precedence == ("maintenance", "workflow-artifact", "documentation-only")
        assert ".md" in exempt.classes["documentation-only"].extensions

    def test_the_seeded_rules_file_loads_and_is_empty(self) -> None:
        seed = (WORKFLOW_DIR / "seeds" / "prompts" / "rules.yaml").read_bytes()

        assert load_contract(LOADER, RuleFile, seed, source="seed").rules == ()

    def test_the_baseline_stays_small_enough_for_every_client(self) -> None:
        baseline = (WORKFLOW_DIR / "baseline" / "baseline.md").read_text(encoding="utf-8")

        assert len(baseline.splitlines()) <= 60  # well under the vendors' 200 line guidance
        assert len(baseline.encode()) <= 8 * 1024  # a small share of Codex's 32 KiB budget

    def test_workflow_texts_have_lf_endings_one_final_newline_and_no_tabs(self) -> None:
        for path in WORKFLOW_DIR.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".yaml", ".json"}:
                data = path.read_bytes()
                assert b"\r" not in data, path
                assert data.endswith(b"\n"), path
                assert not data.endswith(b"\n\n"), path
                assert b"\t" not in data, path
