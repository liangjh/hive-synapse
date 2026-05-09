from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .compaction import compact_edge, compact_node
from .context import compile_context_pack
from .ids import new_id, utc_now_iso
from .imports import compact_import
from .operations import OperationLog
from .paths import WorkspacePaths
from .promotion import sweep_promotability


def enqueue_job(root: Path, job_type: str, target: str, *, reason: str, inputs: dict[str, Any] | None = None, actor: str = "system:job") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    job_id = new_id("job")
    job = {
        "id": job_id,
        "type": job_type,
        "target": target,
        "status": "pending",
        "reason": reason,
        "created_at": utc_now_iso(),
        "inputs": inputs or {},
    }
    path = paths.root / "memory" / "jobs" / "pending" / f"{job_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(job, sort_keys=False), encoding="utf-8")
    op = OperationLog(paths).append(
        operation_type="job_enqueue",
        actor=actor,
        targets=[str(paths.root), target],
        command="hive job enqueue",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": job_id, "type": "job"}],
        rollback={"supported": True, "strategy": "remove_pending_job"},
    )
    return {"ok": True, "job": job, "operation": op.id}


def _job_dirs(paths: WorkspacePaths) -> dict[str, Path]:
    base = paths.root / "memory" / "jobs"
    return {name: base / name for name in ["pending", "claimed", "completed", "failed"]}


def list_jobs(root: Path, *, status: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    dirs = _job_dirs(paths)
    statuses = [status] if status else ["pending", "claimed", "completed", "failed"]
    jobs = []
    for item_status in statuses:
        for path in sorted(dirs[item_status].glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            data["path"] = str(path.relative_to(paths.root))
            data["queue"] = item_status
            jobs.append(data)
    return {"ok": True, "jobs": jobs}


def claim_job(root: Path, *, runner: str = "runner:local") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    dirs = _job_dirs(paths)
    for pending_path in sorted(dirs["pending"].glob("*.yaml")):
        job_id = pending_path.stem
        lock_path = paths.root / "memory" / "state" / "leases" / f"{job_id}.lock"
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"runner: {runner}\nclaimed_at: {utc_now_iso()}\n")
        data = yaml.safe_load(pending_path.read_text(encoding="utf-8")) or {}
        data["status"] = "claimed"
        data["runner"] = runner
        data["claimed_at"] = utc_now_iso()
        claimed_path = dirs["claimed"] / pending_path.name
        claimed_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        pending_path.unlink()
        return {"ok": True, "job": data, "lease": str(lock_path.relative_to(paths.root))}
    return {"ok": True, "job": None, "status": "no_jobs"}


def _find_job(paths: WorkspacePaths, job_id: str) -> tuple[Path, dict[str, Any], str]:
    for status, directory in _job_dirs(paths).items():
        matches = [path for path in sorted(directory.glob("*.yaml")) if path.stem == job_id or job_id in path.stem]
        if matches:
            path = matches[0]
            return path, yaml.safe_load(path.read_text(encoding="utf-8")) or {}, status
    raise FileNotFoundError(job_id)


def complete_job(root: Path, job_id: str, *, result: dict[str, Any] | None = None, actor: str = "system:job") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    path, job, _status = _find_job(paths, job_id)
    job["status"] = "completed"
    job["completed_at"] = utc_now_iso()
    job["result"] = result or {"status": "completed"}
    output = _job_dirs(paths)["completed"] / path.name
    shutil.move(str(path), str(output))
    lease = paths.root / "memory" / "state" / "leases" / f"{Path(path).stem}.lock"
    if lease.exists():
        lease.unlink()
    op = OperationLog(paths).append(
        operation_type="job_complete",
        actor=actor,
        targets=[str(paths.root), job_id],
        command="hive job complete",
        changed_files=[{"path": str(output.relative_to(paths.root))}],
        changed_records=[{"id": job.get("id", job_id), "type": "job"}],
        rollback={"supported": False, "strategy": "manual_requeue"},
    )
    return {"ok": True, "job": job, "operation": op.id}


def fail_job(root: Path, job_id: str, *, reason: str, actor: str = "system:job") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    path, job, _status = _find_job(paths, job_id)
    job["status"] = "failed"
    job["failed_at"] = utc_now_iso()
    job["failure_reason"] = reason
    output = _job_dirs(paths)["failed"] / path.name
    output.write_text(yaml.safe_dump(job, sort_keys=False), encoding="utf-8")
    path.unlink()
    lease = paths.root / "memory" / "state" / "leases" / f"{Path(path).stem}.lock"
    if lease.exists():
        lease.unlink()
    op = OperationLog(paths).append(
        operation_type="job_fail",
        actor=actor,
        targets=[str(paths.root), job_id],
        command="hive job fail",
        changed_files=[{"path": str(output.relative_to(paths.root))}],
        changed_records=[{"id": job.get("id", job_id), "type": "job"}],
        rollback={"supported": True, "strategy": "manual_requeue"},
    )
    return {"ok": True, "job": job, "operation": op.id}


def run_next_job(root: Path, *, runner: str = "runner:local") -> dict[str, Any]:
    claimed = claim_job(root, runner=runner)
    job = claimed.get("job")
    if not job:
        return claimed
    job_id = job["id"]
    job_type = job["type"]
    target = job["target"]
    try:
        if job_type == "import_compact":
            result = compact_import(root, target, actor=runner)
        elif job_type == "context_rebuild":
            pack, manifest = compile_context_pack(root, target)
            result = {"pack": str(pack), "manifest": str(manifest)}
        elif job_type == "promotion_sweep":
            create_proposals = job.get("inputs", {}).get("create_proposals")
            result = sweep_promotability(root, create_proposals=create_proposals, actor=runner)
        elif job_type == "node_compact":
            result = compact_node(root, target, actor=runner)
        elif job_type == "edge_compact":
            result = compact_edge(root, target, actor=runner)
        elif job_type in {"archive_sweep", "active_signin_refresh_check"}:
            result = {"status": "no_changes", "handler": job_type}
        else:
            return fail_job(root, job_id, reason=f"No handler for job type {job_type}", actor=runner)
        return complete_job(root, job_id, result=result, actor=runner)
    except Exception as exc:
        return fail_job(root, job_id, reason=str(exc), actor=runner)
