from __future__ import annotations

import shutil
from pathlib import Path

from . import simple_yaml as yaml
from .fs import atomic_write_text, sha256_file
from .ids import new_id, utc_now_iso
from .models import OperationRecord
from .operations import OperationLog
from .paths import WorkspacePaths


def _workspace_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.parts[-1].endswith(".tmp"):
            continue
        files.append(path)
    return files


def create_backup(
    root: Path, *, actor: str = "system:backup"
) -> tuple[Path, Path, OperationRecord]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    backup_id = new_id("backup")
    backup_dir = paths.root / "memory" / "backups" / backup_id
    files_dir = backup_dir / "files"
    manifest_files = []
    for source in _workspace_files(paths.root):
        if backup_dir in [source, *source.parents]:
            continue
        rel = source.relative_to(paths.root)
        dest = files_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        manifest_files.append(
            {
                "path": str(rel),
                "sha256": sha256_file(source),
                "bytes": source.stat().st_size,
            }
        )
    manifest = {
        "id": backup_id,
        "created_at": utc_now_iso(),
        "workspace": str(paths.root),
        "file_count": len(manifest_files),
        "files": manifest_files,
    }
    manifest_path = backup_dir / "MANIFEST.yaml"
    atomic_write_text(manifest_path, yaml.safe_dump(manifest, sort_keys=False))
    operation = OperationLog(paths).append(
        operation_type="backup_create",
        actor=actor,
        targets=[str(paths.root)],
        command="hive backup create",
        changed_files=[{"path": str(manifest_path.relative_to(paths.root))}],
        rollback={"supported": False, "strategy": "backup_is_recovery_source"},
    )
    return backup_dir, manifest_path, operation


def rollback_preview(root: Path, operation_id: str) -> dict:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    matches = list(paths.operations.glob(f"{operation_id}.yaml"))
    if not matches:
        matches = list(paths.operations.glob(f"*{operation_id}*.yaml"))
    if not matches:
        return {
            "ok": False,
            "operation_id": operation_id,
            "error": "operation.not_found",
            "message": f"No operation record found for {operation_id}",
        }
    operation_path = matches[0]
    data = yaml.safe_load(operation_path.read_text(encoding="utf-8")) or {}
    changed_files = data.get("changed_files") or []
    return {
        "ok": True,
        "operation_id": data.get("id", operation_id),
        "operation_path": str(operation_path),
        "operation_type": data.get("type"),
        "status": data.get("status"),
        "changed_files": changed_files,
        "rollback": data.get("rollback") or {},
        "would_touch": [item.get("path") for item in changed_files if isinstance(item, dict)],
        "mutates": False,
    }
