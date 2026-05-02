from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths


def _skill_path(paths: WorkspacePaths, skill_id: str) -> Path:
    return paths.root / "memory" / "skills" / f"{skill_id}.yaml"


def register_skill(root: Path, skill_id: str, *, title: str, scope: str, trigger: str, permission_profile: str, actor: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    skill = {
        "id": skill_id,
        "title": title,
        "scope": scope,
        "trigger": trigger,
        "permission_profile": permission_profile,
        "review_state": "candidate",
        "status": "active",
        "registered_at": utc_now_iso(),
        "registered_by": actor,
    }
    path = _skill_path(paths, skill_id)
    if path.exists():
        raise ValueError(f"Skill already exists: {skill_id}")
    atomic_write_text(path, yaml.safe_dump(skill, sort_keys=False))
    op = OperationLog(paths).append(
        operation_type="skill_register",
        actor=actor,
        targets=[str(paths.root), skill_id, scope],
        command="hive skill register",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": skill_id, "type": "skill"}],
        rollback={"supported": True, "strategy": "archive_skill"},
    )
    return {"ok": True, "skill": skill, "operation": op.id}


def list_skills(root: Path, *, scope: str | None = None, include_archived: bool = False) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    skills = []
    for path in sorted((paths.root / "memory" / "skills").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if scope and data.get("scope") not in {scope, "org"}:
            continue
        if not include_archived and data.get("status") in {"archived", "deprecated"}:
            continue
        data["path"] = str(path.relative_to(paths.root))
        skills.append(data)
    return {"ok": True, "skills": skills}


def update_skill_status(root: Path, skill_id: str, *, status: str, actor: str, reason: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    path = _skill_path(paths, skill_id)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data["status"] = status
    data[f"{status}_at"] = utc_now_iso()
    data[f"{status}_by"] = actor
    data["status_reason"] = reason
    atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))
    op = OperationLog(paths).append(
        operation_type=f"skill_{status}",
        actor=actor,
        targets=[str(paths.root), skill_id],
        command=f"hive skill {status}",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": skill_id, "type": "skill"}],
        rollback={"supported": True, "strategy": "restore_previous_skill_status"},
    )
    return {"ok": True, "skill": data, "operation": op.id}
