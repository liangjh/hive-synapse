from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .context import compile_context_pack
from .fs import atomic_write_text
from .graph import MemoryGraph
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths
from .prompts import SIGNIN_BOOTSTRAP_PROMPT


def _safe_actor_fragment(actor_id: str) -> str:
    return actor_id.replace(":", "_").replace("/", "_")


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _assignment_records(paths: WorkspacePaths, actor_id: str) -> list[tuple[Path, dict[str, Any]]]:
    assignments = []
    for path in sorted((paths.root / "org" / "assignments").glob("*.yaml")):
        data = _read_yaml(path)
        if data.get("actor") == actor_id and data.get("status", "active") == "active":
            assignments.append((path, data))
    return assignments


def _select_assignment(
    paths: WorkspacePaths,
    actor_id: str,
    *,
    home_node: str | None,
) -> tuple[Path, dict[str, Any]] | None:
    assignments = _assignment_records(paths, actor_id)
    if home_node:
        for path, data in assignments:
            if data.get("home_node") == home_node:
                return path, data
    return assignments[0] if assignments else None


def _personal_memory_home(actor_id: str, assignment: dict[str, Any] | None) -> str:
    if assignment and assignment.get("personal_memory_home"):
        return str(assignment["personal_memory_home"])
    return f"memory/records/agents/{_safe_actor_fragment(actor_id)}/"


def _context_entry(
    paths: WorkspacePaths, target: str, pack_path: Path, manifest_path: Path
) -> dict[str, Any]:
    manifest = _read_yaml(manifest_path)
    return {
        "target": target,
        "kind": "node_context_pack",
        "pack": str(pack_path.relative_to(paths.root)),
        "manifest": str(manifest_path.relative_to(paths.root)),
        "manifest_id": manifest.get("id"),
        "compiled_at": manifest.get("compiled_at"),
        "estimated_tokens": manifest.get("estimated_tokens"),
        "source_watermark": manifest.get("source_watermark"),
        "validation": manifest.get("validation") or {},
    }


def _bootstrap_markdown(record: dict[str, Any], context_entry: dict[str, Any]) -> str:
    return SIGNIN_BOOTSTRAP_PROMPT.render(
        signin_id=record["id"],
        actor=record["actor"],
        effective_node=record["effective_node"],
        role=record["role"],
        personal_memory_home=record["personal_memory_home"],
        context_pack=context_entry["pack"],
        manifest=context_entry["manifest"],
    )


def sign_in_actor(
    root: Path,
    actor_id: str,
    *,
    home_node: str | None = None,
    role: str | None = None,
    instance: str | None = None,
    operator: str | None = None,
    require_assignment: bool = False,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    graph = MemoryGraph(paths.root)
    selected_assignment = _select_assignment(paths, actor_id, home_node=home_node)
    assignment_path: Path | None = None
    assignment: dict[str, Any] | None = None
    if selected_assignment:
        assignment_path, assignment = selected_assignment
    elif require_assignment:
        raise ValueError(f"No active assignment found for {actor_id}")

    effective_node = home_node or (
        str(assignment["home_node"]) if assignment and assignment.get("home_node") else None
    )
    if not effective_node:
        raise ValueError("actor signin requires --home-node when no active assignment exists")
    if effective_node not in graph.nodes:
        raise ValueError(f"Sign-in node not found: {effective_node}")
    if graph.nodes[effective_node].status != "active":
        raise ValueError(f"Sign-in node is not active: {effective_node}")

    effective_role = role or (
        str(assignment["role"]) if assignment and assignment.get("role") else "contributor"
    )
    operator_id = operator or actor_id
    instance_id = instance or f"agent-instance:{_safe_actor_fragment(actor_id)}:{new_id('run')}"
    now = utc_now_iso()
    pack_path, manifest_path = compile_context_pack(paths.root, effective_node)
    context = _context_entry(paths, effective_node, pack_path, manifest_path)
    personal_home = _personal_memory_home(actor_id, assignment)
    (paths.root / personal_home).mkdir(parents=True, exist_ok=True)

    signin_id = new_id("signin")
    record = {
        "id": signin_id,
        "actor": actor_id,
        "instance": instance_id,
        "effective_node": effective_node,
        "role": effective_role,
        "started_at": now,
        "status": "active",
        "assignment": assignment.get("id") if assignment else None,
        "assignment_path": str(assignment_path.relative_to(paths.root))
        if assignment_path
        else None,
        "context_pack": context["pack"],
        "loaded_context_packs": [context],
        "personal_memory_home": personal_home,
        "inherited_nodes": graph.parent_chain(effective_node),
        "connected_edges": graph.connected_edges(effective_node),
        "refresh_count": 0,
    }
    signin_path = paths.root / "org" / "signins" / f"{signin_id}.yaml"
    atomic_write_text(signin_path, yaml.safe_dump(record, sort_keys=False))
    op = OperationLog(paths).append(
        operation_type="actor_signin",
        actor=operator_id,
        targets=[
            str(paths.root),
            actor_id,
            effective_node,
            *record["inherited_nodes"],
            *record["connected_edges"],
        ],
        command="hive actor signin",
        changed_files=[{"path": str(signin_path.relative_to(paths.root))}],
        changed_records=[{"id": signin_id, "type": "signin", "actor": actor_id}],
        rollback={"supported": True, "strategy": "mark_signin_inactive"},
    )
    return {
        "ok": True,
        "signin": record,
        "signin_path": str(signin_path),
        "context_pack": str(pack_path),
        "manifest": str(manifest_path),
        "bootstrap": _bootstrap_markdown(record, context),
        "operation": op.id,
    }


def _find_signin(paths: WorkspacePaths, signin_id: str) -> tuple[Path, dict[str, Any]]:
    matches = list((paths.root / "org" / "signins").glob(f"{signin_id}.yaml"))
    if not matches:
        matches = list((paths.root / "org" / "signins").glob(f"*{signin_id}*.yaml"))
    if not matches:
        raise ValueError(f"Sign-in not found: {signin_id}")
    path = sorted(matches)[0]
    return path, _read_yaml(path)


def refresh_signin(root: Path, signin_id: str, *, operator: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    signin_path, record = _find_signin(paths, signin_id)
    effective_node = str(record.get("effective_node") or "")
    if not effective_node:
        raise ValueError(f"Sign-in has no effective node: {signin_id}")
    graph = MemoryGraph(paths.root)
    if effective_node not in graph.nodes:
        raise ValueError(f"Sign-in node not found: {effective_node}")
    pack_path, manifest_path = compile_context_pack(paths.root, effective_node)
    context = _context_entry(paths, effective_node, pack_path, manifest_path)
    record["context_pack"] = context["pack"]
    record["loaded_context_packs"] = [context]
    record["inherited_nodes"] = graph.parent_chain(effective_node)
    record["connected_edges"] = graph.connected_edges(effective_node)
    record["refreshed_at"] = utc_now_iso()
    record["refresh_count"] = int(record.get("refresh_count") or 0) + 1
    atomic_write_text(signin_path, yaml.safe_dump(record, sort_keys=False))
    operator_id = operator or str(record.get("actor") or "system:signin")
    op = OperationLog(paths).append(
        operation_type="actor_refresh",
        actor=operator_id,
        targets=[
            str(paths.root),
            str(record.get("actor")),
            effective_node,
            *record["inherited_nodes"],
            *record["connected_edges"],
        ],
        command="hive actor refresh",
        changed_files=[{"path": str(signin_path.relative_to(paths.root))}],
        changed_records=[
            {"id": record.get("id", signin_id), "type": "signin", "status": record.get("status")}
        ],
        rollback={"supported": True, "strategy": "restore_previous_signin_record_from_git"},
    )
    return {
        "ok": True,
        "signin": record,
        "signin_path": str(signin_path),
        "context_pack": str(pack_path),
        "manifest": str(manifest_path),
        "bootstrap": _bootstrap_markdown(record, context),
        "operation": op.id,
    }
