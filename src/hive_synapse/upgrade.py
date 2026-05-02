from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__, simple_yaml as yaml
from .backup import create_backup
from .fs import atomic_write_text, sha256_file
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths
from .validator import validate_workspace

BUILTIN_MIGRATIONS = [
    {"id": "001_runtime_markers", "description": "Record runtime/schema marker files."},
]


def doctor(root: Path, *, require_generated: bool = False) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    validation = validate_workspace(paths.root)
    checks: list[dict[str, Any]] = []
    checks.append({"code": "validation", "ok": validation.ok, "errors": [issue.model_dump() for issue in validation.errors]})
    config = yaml.safe_load(paths.config.read_text(encoding="utf-8")) or {}
    workspace_config = config.get("hive_workspace", {}) if isinstance(config, dict) else {}
    checks.append({"code": "runtime_version", "ok": bool(workspace_config.get("runtime_version")), "runtime_version": workspace_config.get("runtime_version"), "current_runtime": __version__})
    if require_generated:
        generated = list((paths.root / "memory" / "generated" / "context-packs").rglob("MANIFEST.yaml"))
        checks.append({"code": "generated_context_packs", "ok": bool(generated), "count": len(generated)})
    ok = all(check.get("ok") for check in checks)
    return {"ok": ok, "checks": checks}


def list_migrations(root: Path) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    applied = set()
    migrations_dir = paths.root / "memory" / "migrations"
    for path in migrations_dir.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        applied.add(data.get("migration_id") or data.get("id"))
    return {"ok": True, "migrations": [{**migration, "applied": migration["id"] in applied} for migration in BUILTIN_MIGRATIONS]}


def migration_dry_run(root: Path, migration_id: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    if migration_id not in {migration["id"] for migration in BUILTIN_MIGRATIONS}:
        raise ValueError(f"Unknown migration: {migration_id}")
    changes = [
        {"path": "memory/migrations/%s.yaml" % migration_id, "action": "create"},
        {"path": "memory/generated/runtime-marker.yaml", "action": "create_or_update"},
    ]
    return {"ok": True, "migration_id": migration_id, "dry_run": True, "changes": changes, "mutates": False}


def migration_apply(root: Path, migration_id: str, *, actor: str = "system:migration") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    backup_dir, manifest_path, backup_op = create_backup(paths.root, actor=actor)
    dry = migration_dry_run(paths.root, migration_id)
    marker = {"id": "runtime_marker", "runtime_version": __version__, "schema_version": "0.1.0", "updated_at": utc_now_iso()}
    marker_path = paths.root / "memory" / "generated" / "runtime-marker.yaml"
    atomic_write_text(marker_path, yaml.safe_dump(marker, sort_keys=False))
    migration_record = {
        "id": new_id("migration"),
        "migration_id": migration_id,
        "workspace_id": paths.root.name,
        "from_schema_version": "0.1.0",
        "to_schema_version": "0.1.0",
        "status": "applied",
        "started_at": utc_now_iso(),
        "backup": str(backup_dir.relative_to(paths.root)),
    }
    migration_path = paths.root / "memory" / "migrations" / f"{migration_id}.yaml"
    atomic_write_text(migration_path, yaml.safe_dump(migration_record, sort_keys=False))
    op = OperationLog(paths).append(
        operation_type="migration_apply",
        actor=actor,
        targets=[str(paths.root), migration_id],
        command="hive upgrade migration-apply",
        changed_files=[
            {"path": str(marker_path.relative_to(paths.root))},
            {"path": str(migration_path.relative_to(paths.root))},
            {"path": str(manifest_path.relative_to(paths.root))},
        ],
        changed_records=[{"id": migration_record["id"], "type": "migration"}],
        rollback={"supported": True, "strategy": "restore_backup", "backup_operation": backup_op.id},
    )
    return {"ok": True, "migration": migration_record, "dry_run": dry, "backup": str(backup_dir), "operation": op.id}


def template_diff(root: Path, runtime_root: Path) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    templates_root = runtime_root / "templates"
    diffs = []
    for template in sorted(templates_root.rglob("*")):
        if template.is_dir():
            continue
        rel = template.relative_to(templates_root)
        dest = paths.root / rel
        if not dest.exists():
            diffs.append({"path": str(rel), "status": "missing", "template_sha256": sha256_file(template)})
        elif sha256_file(dest) != sha256_file(template):
            diffs.append({"path": str(rel), "status": "different", "template_sha256": sha256_file(template), "workspace_sha256": sha256_file(dest)})
    report_id = new_id("template_diff")
    report_path = paths.root / "memory" / "audit" / f"{report_id}.yaml"
    report = {"ok": True, "id": report_id, "diffs": diffs, "mutates_templates": False}
    atomic_write_text(report_path, yaml.safe_dump(report, sort_keys=False))
    report["report_path"] = str(report_path)
    return report


def template_apply_new(root: Path, runtime_root: Path, *, actor: str = "system:upgrade") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    templates_root = runtime_root / "templates"
    changed = []
    for template in sorted(templates_root.rglob("*")):
        if template.is_dir():
            continue
        rel = template.relative_to(templates_root)
        dest = paths.root / rel
        if dest.exists():
            continue
        atomic_write_text(dest, template.read_text(encoding="utf-8"))
        changed.append({"path": str(rel)})
    op = OperationLog(paths).append(
        operation_type="template_apply_new",
        actor=actor,
        targets=[str(paths.root)],
        command="hive upgrade template-apply-new",
        changed_files=changed,
        rollback={"supported": True, "strategy": "remove_new_template_files"},
    )
    return {"ok": True, "changed_files": changed, "operation": op.id}
