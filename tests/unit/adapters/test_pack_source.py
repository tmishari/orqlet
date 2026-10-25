import pytest

from orqlet.adapters.fs.yaml_loader import StrictYamlLoader
from orqlet.adapters.standards.pack_source import DirectoryPackSource
from orqlet.application.ports.standards import PackError
from orqlet.domain.paths import CanonicalPath
from tests.fakes.memory_fs import MemoryFileSystem
from tests.support.trees import pack_dir

pytestmark = pytest.mark.unit

PACK = b"schema: orqlet.standards-pack/v1\nid: p\nversion: 1.0.0\nowner: o\nrules: [rules/r.yaml]\n"
RULES = b"schema: orqlet.rules/v1\nrules:\n  - {id: P-1, level: MUST, text: do it}\n"


def source(fs: MemoryFileSystem) -> DirectoryPackSource:
    return DirectoryPackSource(fs, StrictYamlLoader())


def write(fs: MemoryFileSystem, path: str, data: bytes) -> None:
    fs.write_atomic(CanonicalPath.parse(path), data)


def valid_pack() -> MemoryFileSystem:
    fs = MemoryFileSystem()
    write(fs, "p/pack.yaml", PACK)
    write(fs, "p/rules/r.yaml", RULES)
    return fs


def test_available_lists_directories_that_hold_a_manifest() -> None:
    fs = pack_dir()
    write(fs, "not-a-pack/readme.txt", b"x")

    assert source(fs).available() == ("sample", "web")


def test_a_pack_loads_with_its_rules_and_a_content_hash() -> None:
    loaded = source(pack_dir()).load("sample")

    assert loaded.manifest.version == "1.0.0"
    assert [r.id for r in loaded.rules] == ["SAMPLE-001", "SAMPLE-002", "SAMPLE-003"]
    assert len(loaded.content_sha256) == 64


def test_the_content_hash_changes_when_any_file_of_the_pack_changes() -> None:
    fs = valid_pack()
    before = source(fs).load("p").content_sha256

    write(fs, "p/rules/r.yaml", RULES.replace(b"do it", b"do that"))

    assert source(fs).load("p").content_sha256 != before


def test_the_content_hash_does_not_depend_on_the_order_files_were_written() -> None:
    first, second = MemoryFileSystem(), MemoryFileSystem()
    for fs, order in (
        (first, ("p/pack.yaml", "p/rules/r.yaml")),
        (second, ("p/rules/r.yaml", "p/pack.yaml")),
    ):
        for name in order:
            write(fs, name, PACK if name.endswith("pack.yaml") else RULES)

    assert source(first).load("p").content_sha256 == source(second).load("p").content_sha256


def test_a_manifest_that_names_another_id_is_refused() -> None:
    fs = valid_pack()
    write(fs, "p/pack.yaml", PACK.replace(b"id: p", b"id: other"))

    with pytest.raises(PackError, match="names itself"):
        source(fs).load("p")


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        (PACK + b"surprise: 1\n", "surprise"),
        (PACK.replace(b"rules/r.yaml", b"../outside.yaml"), "outside"),
        (PACK.replace(b"rules/r.yaml", b"rules/missing.yaml"), "missing"),
    ],
)
def test_a_broken_manifest_is_a_pack_error(manifest: bytes, message: str) -> None:
    fs = valid_pack()
    write(fs, "p/pack.yaml", manifest)

    with pytest.raises(PackError, match=message):
        source(fs).load("p")


def test_a_rule_file_with_an_unknown_field_is_refused_without_echoing_values() -> None:
    fs = valid_pack()
    write(fs, "p/rules/r.yaml", RULES + b"  - {id: P-2, level: MUST, text: x, secret: hunter2}\n")

    with pytest.raises(PackError) as raised:
        source(fs).load("p")

    assert "hunter2" not in str(raised.value)
