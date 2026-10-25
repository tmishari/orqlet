"""Standards packs stored as directories: `<pack-id>/pack.yaml`, rule files and optional text."""

from __future__ import annotations

from orqlet.application.contracts.loading import load_contract
from orqlet.application.contracts.standards_pack import PackManifest, Rule, RuleFile
from orqlet.application.ports.documents import DocumentError, DocumentLoader
from orqlet.application.ports.filesystem import FileKind, FileSystem, FileSystemError
from orqlet.application.ports.standards import LoadedPack, PackError
from orqlet.domain.digest import digest_of, sha256_hex
from orqlet.domain.errors import InvalidPath
from orqlet.domain.paths import CanonicalPath

MAX_FILES = 500
MAX_FILE_BYTES = 1_048_576


class DirectoryPackSource:
    """Reads packs below the root of `fs`, one directory per pack."""

    def __init__(self, fs: FileSystem, loader: DocumentLoader, *, label: str = "directory") -> None:
        self._fs = fs
        self._loader = loader
        self._label = label

    def available(self) -> tuple[str, ...]:
        names = []
        for name in self._fs.list_dir(None):
            try:
                manifest = CanonicalPath.parse(name).child("pack.yaml")
            except InvalidPath:
                continue
            if self._fs.kind(manifest) is FileKind.FILE:
                names.append(name)
        return tuple(sorted(names))

    def load(self, pack_id: str) -> LoadedPack:
        try:
            return self._load(pack_id)
        except (DocumentError, FileSystemError, InvalidPath) as exc:
            raise PackError(f"pack {pack_id!r}: {exc}") from exc

    def _load(self, pack_id: str) -> LoadedPack:
        root = CanonicalPath.parse(pack_id)
        manifest = load_contract(
            self._loader,
            PackManifest,
            self._fs.read_bytes(root.child("pack.yaml")),
            source=f"{pack_id}/pack.yaml",
        )
        if manifest.id != pack_id:
            raise PackError(f"pack {pack_id!r}: the manifest names itself {manifest.id!r}")
        rules: list[Rule] = []
        for relative in manifest.rules:
            path = self._inside(root, relative)
            rule_file = load_contract(
                self._loader, RuleFile, self._fs.read_bytes(path), source=str(path)
            )
            rules.extend(rule_file.rules)
        baseline = None
        if manifest.baseline is not None:
            baseline = self._fs.read_bytes(self._inside(root, manifest.baseline)).decode("utf-8")
        return LoadedPack(
            manifest=manifest,
            rules=tuple(rules),
            baseline_text=baseline,
            content_sha256=self._content_hash(root),
            source=f"{self._label}:{pack_id}",
            asset_files=self._assets(root, manifest),
        )

    def _assets(self, root: CanonicalPath, manifest: PackManifest) -> tuple[tuple[str, bytes], ...]:
        """The files of the declared assets, each checked against the hash the manifest gives."""
        found = []
        for asset in manifest.assets:
            content = self._fs.read_bytes(self._inside(root, asset.path))
            if sha256_hex(content) != asset.sha256:
                raise PackError(f"asset {asset.id} does not match the hash in its manifest")
            found.append((asset.path, content))
        return tuple(found)

    @staticmethod
    def _inside(root: CanonicalPath, relative: str) -> CanonicalPath:
        """A path named by a manifest, which must stay inside its own pack."""
        target = CanonicalPath.parse(f"{root}/{relative}")
        if not target.is_inside(root):
            raise PackError(f"{relative!r} is outside the pack")
        return target

    def _content_hash(self, root: CanonicalPath) -> str:
        """Digest of every file of the pack, by relative path and content hash."""
        entries: list[list[str]] = []
        pending = [root]
        while pending:
            directory = pending.pop()
            for name in self._fs.list_dir(directory):
                path = directory.child(name)
                kind = self._fs.kind(path)
                if kind is FileKind.DIRECTORY:
                    pending.append(path)
                elif kind is FileKind.FILE:
                    content = self._fs.read_bytes(path)
                    if len(content) > MAX_FILE_BYTES:
                        raise PackError(f"{path} is larger than {MAX_FILE_BYTES} bytes")
                    entries.append([str(path)[len(str(root)) + 1 :], sha256_hex(content)])
                else:
                    raise PackError(f"{path} is not a regular file or directory")
                if len(entries) > MAX_FILES:
                    raise PackError(f"more than {MAX_FILES} files")
        return digest_of(sorted(entries))
