from __future__ import annotations

from pathlib import Path
from typing import Any

from .frontmatter import read_markdown
from .ids import new_id, utc_now_iso
from .jobs import enqueue_job
from .operations import OperationLog
from .paths import WorkspacePaths
from .policies import operation_policy


def archive_sweep(root: Path, *, enqueue: bool | None = None, actor: str = "system:archive") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy = operation_policy(paths, "archive")
    if enqueue is None:
        enqueue = bool(policy.get("enqueue_compaction", False))
    candidates: list[dict[str, Any]] = []
    for path in sorted(paths.graph_nodes.rglob("*.md")):
        doc = read_markdown(path)
        if doc.frontmatter.get("status") in {"inactive", "archived"}:
            candidates.append({"target": doc.frontmatter.get("id"), "target_type": "node", "path": str(path.relative_to(paths.root))})
    for path in sorted((paths.root / "memory" / "skills").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if "status: deprecated" in text or "status: archived" in text:
            candidates.append({"target": path.stem, "target_type": "skill", "path": str(path.relative_to(paths.root))})
    jobs = []
    if enqueue:
        for candidate in candidates:
            jobs.append(enqueue_job(paths.root, "archive_sweep", str(candidate["target"]), reason="archive sweep candidate", actor=actor)["job"])
    report = {
        "ok": True,
        "id": new_id("archive_sweep"),
        "created_at": utc_now_iso(),
        "candidates": candidates,
        "jobs": jobs,
        "policy": {
            "mode": policy.get("mode", "manual"),
            "enqueue_compaction": enqueue,
        },
    }
    OperationLog(paths).append(
        operation_type="archive_sweep",
        actor=actor,
        targets=[str(paths.root)],
        command="hive archive sweep",
        changed_files=[],
        changed_records=[{"id": report["id"], "type": "archive_sweep_report"}],
        rollback={"supported": False, "strategy": "report_only"},
    )
    return report
