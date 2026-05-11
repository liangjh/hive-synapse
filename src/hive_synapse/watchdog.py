from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .jobs import enqueue_job
from .paths import WorkspacePaths
from .policies import operation_policy


def watchdog_report(
    root: Path, *, enqueue: bool | None = None, actor: str = "system:watchdog"
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy = operation_policy(paths, "watchdog")
    if enqueue is None:
        enqueue = bool(policy.get("enqueue_remediation", False))
    findings: list[dict[str, Any]] = []
    dirty = sorted(paths.context_dirty.glob("*.yaml"))
    pending_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (paths.root / "memory" / "jobs" / "pending").glob("*.yaml")
    )
    for marker in dirty:
        data = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
        target = data.get("target", "unknown")
        if target not in pending_text:
            findings.append(
                {
                    "code": "dirty_context_without_job",
                    "target": target,
                    "path": str(marker.relative_to(paths.root)),
                }
            )
            if enqueue:
                enqueue_job(
                    paths.root,
                    "context_rebuild",
                    str(target),
                    reason="watchdog dirty context",
                    actor=actor,
                )
    for path in paths.root.rglob("*"):
        lower = path.name.lower()
        if any(marker in lower for marker in ["conflict", "conflicted copy", "sync conflict"]):
            if "memory/conflicts" in str(path):
                continue
            findings.append(
                {"code": "sync_conflict_file", "path": str(path.relative_to(paths.root))}
            )
    imports_root = paths.root / "memory" / "imports"
    for item in imports_root.rglob("*.yaml"):
        if item.name == "workspace.yaml":
            continue
        data = yaml.safe_load(item.read_text(encoding="utf-8")) or {}
        if data.get("state") in {"dropped", "classified"}:
            findings.append(
                {
                    "code": "unprocessed_import",
                    "target": data.get("target"),
                    "path": str(item.relative_to(paths.root)),
                }
            )
    report_id = new_id("watchdog")
    report = {
        "ok": True,
        "id": report_id,
        "created_at": utc_now_iso(),
        "findings": findings,
        "finding_count": len(findings),
        "policy": {
            "mode": policy.get("mode", "report_only"),
            "enqueue_remediation": enqueue,
        },
    }
    report_path = paths.root / "memory" / "audit" / f"{report_id}.yaml"
    atomic_write_text(report_path, yaml.safe_dump(report, sort_keys=False))
    markdown_path = paths.root / "memory" / "audit" / f"{report_id}.md"
    lines = [f"# Watchdog Report: {report_id}", ""]
    if findings:
        for finding in findings:
            lines.append(f"- `{finding['code']}`: {finding.get('target') or finding.get('path')}")
    else:
        lines.append("No findings.")
    atomic_write_text(markdown_path, "\n".join(lines) + "\n")
    report["report_path"] = str(report_path)
    report["markdown_path"] = str(markdown_path)
    return report
