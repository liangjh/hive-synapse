"""Workspace repository helpers for raw and memory records.

Module guide:
- `WorkspaceRepository` preserves raw sources and loads memory records.
- `LoadedRecord` wraps a record path, frontmatter, and body.
- Path helpers locate node current/history files and relative paths.

Maintenance: update this guide when adding public functions/classes to this module.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .errors import WorkspaceError
from .frontmatter import MarkdownDocument, read_markdown, write_markdown
from .fs import atomic_write_text, ensure_within_root, sha256_file
from .ids import new_id, utc_now_iso
from .paths import WorkspacePaths, target_to_path_fragment


@dataclass(frozen=True)
class LoadedRecord:
    path: Path
    frontmatter: dict[str, Any]
    body: str

    @property
    def id(self) -> str | None:
        value = self.frontmatter.get("id")
        return str(value) if value is not None else None


class WorkspaceRepository:
    """Filesystem repository for canonical Hive workspace records."""

    def __init__(self, root: Path):
        self.paths = WorkspacePaths(root.resolve())
        self.paths.require_workspace()

    @property
    def root(self) -> Path:
        return self.paths.root

    def resolve(self, relative_path: str | Path) -> Path:
        return ensure_within_root(self.root / relative_path, self.root)

    def read_markdown(self, relative_path: str | Path) -> MarkdownDocument:
        return read_markdown(self.resolve(relative_path))

    def write_markdown(
        self,
        relative_path: str | Path,
        frontmatter: dict[str, Any],
        body: str,
        *,
        expected_sha256: str | None = None,
    ) -> Path:
        path = self.resolve(relative_path)
        if expected_sha256 is None:
            write_markdown(path, frontmatter, body)
        else:
            from .frontmatter import dump_markdown

            atomic_write_text(
                path, dump_markdown(frontmatter, body), expected_sha256=expected_sha256
            )
        return path

    def read_yaml(self, relative_path: str | Path) -> dict[str, Any]:
        path = self.resolve(relative_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise WorkspaceError(f"Expected YAML mapping: {path}")
        return data

    def write_yaml(
        self,
        relative_path: str | Path,
        data: dict[str, Any],
        *,
        expected_sha256: str | None = None,
    ) -> Path:
        path = self.resolve(relative_path)
        atomic_write_text(
            path,
            yaml.safe_dump(data, sort_keys=False),
            expected_sha256=expected_sha256,
        )
        return path

    def write_json(self, relative_path: str | Path, data: dict[str, Any]) -> Path:
        path = self.resolve(relative_path)
        atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
        return path

    def preserve_raw(self, relative_path: str | Path, content: bytes) -> Path:
        path = self.resolve(relative_path)
        if path.exists():
            raise WorkspaceError(f"Raw artifacts are append-only; refusing overwrite: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{new_id('raw')}.tmp")
        tmp.write_bytes(content)
        tmp.replace(path)
        return path

    def copy_raw_file(self, source: Path, destination_relative: str | Path) -> Path:
        if not source.exists() or not source.is_file():
            raise WorkspaceError(f"Import source is not a file: {source}")
        path = self.resolve(destination_relative)
        if path.exists():
            raise WorkspaceError(f"Raw artifacts are append-only; refusing overwrite: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)
        return path

    def load_markdown_records(self, relative_root: str | Path) -> list[LoadedRecord]:
        base = self.resolve(relative_root)
        if not base.exists():
            return []
        records: list[LoadedRecord] = []
        for path in sorted(base.rglob("*.md")):
            doc = read_markdown(path)
            if doc.frontmatter:
                records.append(LoadedRecord(path=path, frontmatter=doc.frontmatter, body=doc.body))
        return records

    def hash(self, relative_path: str | Path) -> str:
        return sha256_file(self.resolve(relative_path))

    def write_index(self, relative_path: str | Path, records: list[dict[str, Any]]) -> Path:
        return self.write_json(
            relative_path,
            {
                "generated_at": utc_now_iso(),
                "record_count": len(records),
                "records": records,
            },
        )


def record_relative_path(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def node_current_path(node_id: str) -> Path:
    return Path("memory") / "records" / "nodes" / target_to_path_fragment(node_id) / "CURRENT.md"


def node_history_path(node_id: str) -> Path:
    return Path("memory") / "records" / "nodes" / target_to_path_fragment(node_id) / "HISTORY.md"
