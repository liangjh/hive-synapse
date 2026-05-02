from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .context import invalidate_context
from .frontmatter import dump_markdown, read_markdown
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths, target_to_path_fragment


def _node_file(paths: WorkspacePaths, node_id: str) -> Path:
    return paths.graph_nodes / target_to_path_fragment(node_id).with_suffix(".md")


def _memory_dir(paths: WorkspacePaths, node_id: str) -> Path:
    return paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(node_id)


def _write_import_workspace(paths: WorkspacePaths, node_id: str) -> Path:
    root = paths.root / "memory" / "imports" / target_to_path_fragment(node_id)
    for child in ["inbox", "fetched", "normalized", "compacted", "candidates", "processed", "rejected", "items", "reports"]:
        (root / child).mkdir(parents=True, exist_ok=True)
    workspace = {
        "id": f"import_workspace_{node_id.replace('/', '_')}",
        "target": node_id,
        "status": "active",
        "paths": {child: str((root / child).relative_to(paths.root)) + "/" for child in ["inbox", "fetched", "normalized", "compacted", "candidates", "processed", "rejected", "items", "reports"]},
    }
    output = root / "workspace.yaml"
    if not output.exists():
        atomic_write_text(output, yaml.safe_dump(workspace, sort_keys=False))
    return output


def create_node(root: Path, node_id: str, *, kind: str, title: str, parents: list[str], actor: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    node_path = _node_file(paths, node_id)
    if node_path.exists():
        raise ValueError(f"Node already exists: {node_id}")
    record = {
        "id": node_id,
        "kind": kind,
        "title": title,
        "parents": parents,
        "status": "active",
        "owners": [actor],
        "current_memory_file": f"memory/records/nodes/{node_id}/CURRENT.md",
        "history_memory_file": f"memory/records/nodes/{node_id}/HISTORY.md",
        "import_workspace": f"memory/imports/{node_id}/",
    }
    atomic_write_text(node_path, dump_markdown(record, f"# {title}\n\nGraph node for `{node_id}`.\n"))
    memory_dir = _memory_dir(paths, node_id)
    atomic_write_text(memory_dir / "CURRENT.md", f"# Current Memory: {title}\n\nStartup context for `{node_id}`.\n")
    atomic_write_text(memory_dir / "HISTORY.md", f"# Historical Memory: {title}\n\nHistorical context for `{node_id}`.\n")
    import_workspace = _write_import_workspace(paths, node_id)
    policy_path = paths.root / "policies" / "nodes" / target_to_path_fragment(node_id).with_suffix(".yaml")
    atomic_write_text(policy_path, yaml.safe_dump({"id": f"policy_{node_id.replace('/', '_')}", "target": node_id, "created_at": utc_now_iso()}, sort_keys=False))
    for parent in parents:
        invalidate_context(paths.root, parent, reason=f"node_created:{node_id}", actor=actor)
    op = OperationLog(paths).append(
        operation_type="node_create",
        actor=actor,
        targets=[str(paths.root), node_id, *parents],
        command="hive node create",
        changed_files=[
            {"path": str(node_path.relative_to(paths.root))},
            {"path": str((memory_dir / "CURRENT.md").relative_to(paths.root))},
            {"path": str((memory_dir / "HISTORY.md").relative_to(paths.root))},
            {"path": str(import_workspace.relative_to(paths.root))},
            {"path": str(policy_path.relative_to(paths.root))},
        ],
        changed_records=[{"id": node_id, "type": "node"}],
        rollback={"supported": True, "strategy": "archive_or_remove_created_node"},
    )
    return {"ok": True, "node": record, "operation": op.id}


def move_node(root: Path, node_id: str, *, parents: list[str], actor: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    node_path = _node_file(paths, node_id)
    doc = read_markdown(node_path)
    record = dict(doc.frontmatter)
    old_parents = list(record.get("parents", []))
    record["parents"] = parents
    record["moved_at"] = utc_now_iso()
    record["moved_by"] = actor
    atomic_write_text(node_path, dump_markdown(record, doc.body))
    for target in sorted(set(old_parents + parents + [node_id])):
        invalidate_context(paths.root, target, reason=f"node_moved:{node_id}", actor=actor)
    op = OperationLog(paths).append(
        operation_type="node_move",
        actor=actor,
        targets=[str(paths.root), node_id, *old_parents, *parents],
        command="hive node move",
        changed_files=[{"path": str(node_path.relative_to(paths.root))}],
        changed_records=[{"id": node_id, "type": "node"}],
        rollback={"supported": True, "strategy": "restore_previous_parents"},
    )
    return {"ok": True, "node": record, "old_parents": old_parents, "operation": op.id}


def archive_node(root: Path, node_id: str, *, actor: str, reason: str, defer_compaction: bool = False) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    if not defer_compaction:
        history = _memory_dir(paths, node_id) / "HISTORY.md"
        if not history.exists():
            raise ValueError("Node archive requires final compaction or --defer-compaction")
    node_path = _node_file(paths, node_id)
    doc = read_markdown(node_path)
    record = dict(doc.frontmatter)
    record["status"] = "archived"
    record["archived_at"] = utc_now_iso()
    record["archived_by"] = actor
    archive_record = {
        "id": new_id("archive"),
        "target": node_id,
        "target_type": "node",
        "reason": reason,
        "archived_at": record["archived_at"],
        "archived_by": actor,
        "status": "archived",
        "excluded_from_startup_context": True,
        "archive_deferral": {"final_compaction_deferred": True} if defer_compaction else None,
    }
    atomic_write_text(node_path, dump_markdown(record, doc.body))
    archive_path = paths.root / "memory" / "audit" / f"{archive_record['id']}.yaml"
    atomic_write_text(archive_path, yaml.safe_dump(archive_record, sort_keys=False))
    invalidate_context(paths.root, node_id, reason=f"node_archived:{node_id}", actor=actor)
    op = OperationLog(paths).append(
        operation_type="node_archive",
        actor=actor,
        targets=[str(paths.root), node_id],
        command="hive node archive",
        changed_files=[{"path": str(node_path.relative_to(paths.root))}, {"path": str(archive_path.relative_to(paths.root))}],
        changed_records=[{"id": node_id, "type": "node"}, {"id": archive_record["id"], "type": "archive"}],
        rollback={"supported": True, "strategy": "restore_node_status"},
    )
    return {"ok": True, "node": record, "archive": archive_record, "operation": op.id}


def restore_node(root: Path, node_id: str, *, actor: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    node_path = _node_file(paths, node_id)
    doc = read_markdown(node_path)
    record = dict(doc.frontmatter)
    record["status"] = "active"
    record["restored_at"] = utc_now_iso()
    record["restored_by"] = actor
    atomic_write_text(node_path, dump_markdown(record, doc.body))
    invalidate_context(paths.root, node_id, reason=f"node_restored:{node_id}", actor=actor)
    op = OperationLog(paths).append(
        operation_type="node_restore",
        actor=actor,
        targets=[str(paths.root), node_id],
        command="hive node restore",
        changed_files=[{"path": str(node_path.relative_to(paths.root))}],
        changed_records=[{"id": node_id, "type": "node"}],
        rollback={"supported": True, "strategy": "restore_archived_status"},
    )
    return {"ok": True, "node": record, "operation": op.id}


def assign_actor(root: Path, actor_id: str, *, home_node: str, role: str, actor: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    assignment_id = f"assignment_{actor_id.replace(':', '_').replace('/', '_')}"
    assignment = {
        "id": assignment_id,
        "actor": actor_id,
        "actor_kind": "agent" if actor_id.startswith("agent:") else "human",
        "home_node": home_node,
        "role": role,
        "status": "active",
        "assigned_at": utc_now_iso(),
        "assigned_by": actor,
        "personal_memory_home": f"memory/records/agents/{actor_id.split(':')[-1]}/",
    }
    path = paths.root / "org" / "assignments" / f"{assignment_id}.yaml"
    atomic_write_text(path, yaml.safe_dump(assignment, sort_keys=False))
    invalidate_context(paths.root, home_node, reason=f"actor_assigned:{actor_id}", actor=actor)
    op = OperationLog(paths).append(
        operation_type="actor_assign",
        actor=actor,
        targets=[str(paths.root), actor_id, home_node],
        command="hive actor assign",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": assignment_id, "type": "actor_assignment"}],
        rollback={"supported": True, "strategy": "deactivate_assignment"},
    )
    return {"ok": True, "assignment": assignment, "operation": op.id}


def archive_actor(root: Path, actor_id: str, *, actor: str, reason: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    changed = []
    for path in (paths.root / "org" / "assignments").glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("actor") == actor_id and data.get("status") == "active":
            data["status"] = "archived"
            data["archived_at"] = utc_now_iso()
            data["archived_by"] = actor
            atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))
            changed.append(str(path.relative_to(paths.root)))
    archive_record = {
        "id": new_id("archive"),
        "target": actor_id,
        "target_type": "actor",
        "reason": reason,
        "archived_at": utc_now_iso(),
        "archived_by": actor,
        "status": "archived",
        "excluded_from_startup_context": True,
        "archive_deferral": {"final_compaction_deferred": True},
    }
    archive_path = paths.root / "memory" / "audit" / f"{archive_record['id']}.yaml"
    atomic_write_text(archive_path, yaml.safe_dump(archive_record, sort_keys=False))
    op = OperationLog(paths).append(
        operation_type="actor_archive",
        actor=actor,
        targets=[str(paths.root), actor_id],
        command="hive actor archive",
        changed_files=[{"path": path} for path in changed] + [{"path": str(archive_path.relative_to(paths.root))}],
        changed_records=[{"id": archive_record["id"], "type": "archive"}],
        rollback={"supported": True, "strategy": "restore_assignments"},
    )
    return {"ok": True, "archive": archive_record, "changed_assignments": changed, "operation": op.id}
