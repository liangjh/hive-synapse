from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .models import OperationRecord
from .paths import WorkspacePaths


class OperationLog:
    def __init__(self, paths: WorkspacePaths):
        self.paths = paths

    def append(
        self,
        *,
        operation_type: str,
        actor: str,
        targets: list[str],
        command: str,
        mode: str = "apply",
        status: str = "completed",
        changed_files: list[dict[str, Any]] | None = None,
        changed_records: list[dict[str, Any]] | None = None,
        rollback: dict[str, Any] | None = None,
    ) -> OperationRecord:
        record = OperationRecord(
            id=new_id("op"),
            type=operation_type,
            actor=actor,
            started_at=utc_now_iso(),
            status=status,
            targets=targets,
            command=command,
            mode=mode,
            changed_files=changed_files or [],
            changed_records=changed_records or [],
            rollback=rollback or {"supported": False, "strategy": "unsupported"},
        )
        path = self.paths.operations / f"{record.id}.yaml"
        atomic_write_text(path, yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False))
        return record


def _read_operation(path: Path, root: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("id", path.stem)
    data["path"] = str(path.relative_to(root))
    return data


def list_operations(
    root: Path,
    *,
    limit: int = 20,
    operation_type: str | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    operations = []
    for path in sorted(paths.operations.glob("*.yaml"), reverse=True):
        data = _read_operation(path, paths.root)
        if operation_type and data.get("type") != operation_type:
            continue
        if target and target not in [str(item) for item in data.get("targets", [])]:
            continue
        operations.append(data)
        if limit and len(operations) >= limit:
            break
    return {"ok": True, "operations": operations, "count": len(operations)}


def show_operation(root: Path, operation_id: str) -> dict[str, Any]:
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
    operation = _read_operation(sorted(matches)[0], paths.root)
    return {"ok": True, "operation": operation}
