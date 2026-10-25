"""Where standards packs come from. The first source is the local directory structure of a pack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from orqlet.application.contracts.standards_pack import PackManifest, Rule
from orqlet.domain.errors import OrqletError


class PackError(OrqletError):
    """A standards pack is missing, malformed or does not match its own manifest."""


@dataclass(frozen=True, slots=True)
class LoadedPack:
    manifest: PackManifest
    rules: tuple[Rule, ...]
    baseline_text: str | None
    content_sha256: str
    source: str
    asset_files: tuple[tuple[str, bytes], ...] = ()  # (pack-relative path, bytes) of each asset


class StandardsSource(Protocol):
    def available(self) -> tuple[str, ...]:
        """Pack ids this source can load, sorted by code point."""
        ...

    def load(self, pack_id: str) -> LoadedPack:
        """Load, validate and hash one pack."""
        ...
