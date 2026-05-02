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
            rollback=rollback or {"supported": False, "strategy": "unsupported"},
        )
        path = self.paths.operations / f"{record.id}.yaml"
        atomic_write_text(path, yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False))
        return record
