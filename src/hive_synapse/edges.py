from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .context import invalidate_context
from .frontmatter import dump_markdown, read_markdown
from .fs import atomic_write_text
from .graph import MemoryGraph
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths, target_to_path_fragment

EDGE_IMPORT_DIRS = [
    "inbox",
    "fetched",
    "normalized",
    "compacted",
    "candidates",
    "processed",
    "rejected",
    "items",
    "reports",
]


def _validate_graph_id(value: str, *, label: str) -> None:
    if not value or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"Invalid {label}: {value!r}")


def _edge_file(paths: WorkspacePaths, edge_id: str) -> Path:
    return paths.graph_edges / target_to_path_fragment(edge_id).with_suffix(".md")


def _edge_memory_dir(paths: WorkspacePaths, edge_id: str) -> Path:
    return paths.root / "memory" / "records" / "edges" / target_to_path_fragment(edge_id)


def _edge_import_dir(paths: WorkspacePaths, edge_id: str) -> Path:
    return paths.root / "memory" / "imports" / "edges" / target_to_path_fragment(edge_id)


def _write_import_workspace(
    paths: WorkspacePaths, edge_id: str, *, owner: str | None = None
) -> Path:
    root = _edge_import_dir(paths, edge_id)
    for child in EDGE_IMPORT_DIRS:
        (root / child).mkdir(parents=True, exist_ok=True)
    workspace = {
        "id": f"import_workspace_edge_{edge_id.replace('/', '_')}",
        "target": edge_id,
        "target_type": "edge",
        "status": "active",
        "owner": owner,
        "paths": {
            child: str((root / child).relative_to(paths.root)) + "/" for child in EDGE_IMPORT_DIRS
        },
    }
    output = root / "workspace.yaml"
    atomic_write_text(output, yaml.safe_dump(workspace, sort_keys=False))
    return output


def create_edge(
    root: Path,
    edge_id: str,
    *,
    kind: str,
    title: str,
    nodes: list[str],
    actor: str,
    summary: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    _validate_graph_id(edge_id, label="edge id")
    if len(set(nodes)) < 2:
        raise ValueError("Edges require at least two unique nodes")
    graph = MemoryGraph(paths.root)
    missing = [node_id for node_id in nodes if node_id not in graph.nodes]
    if missing:
        raise ValueError(f"Edge references missing node(s): {', '.join(missing)}")
    edge_path = _edge_file(paths, edge_id)
    if edge_path.exists():
        raise ValueError(f"Edge already exists: {edge_id}")
    memory_dir = _edge_memory_dir(paths, edge_id)
    record = {
        "id": edge_id,
        "kind": kind,
        "title": title,
        "nodes": nodes,
        "authority": "shared",
        "status": "active",
        "current_memory_file": str((memory_dir / "CURRENT.md").relative_to(paths.root)),
        "history_memory_file": str((memory_dir / "HISTORY.md").relative_to(paths.root)),
        "import_workspace": str(_edge_import_dir(paths, edge_id).relative_to(paths.root)) + "/",
    }
    atomic_write_text(
        edge_path, dump_markdown(record, f"# {title}\n\nShared graph edge for `{edge_id}`.\n")
    )
    current_body = summary or f"Shared operating context for `{edge_id}`."
    atomic_write_text(
        memory_dir / "CURRENT.md", f"# Current Edge Memory: {title}\n\n{current_body.strip()}\n"
    )
    atomic_write_text(
        memory_dir / "HISTORY.md",
        f"# Historical Edge Memory: {title}\n\nCreated {utc_now_iso()} by {actor}.\n",
    )
    import_workspace = _write_import_workspace(paths, edge_id, owner=actor)
    invalidations = [
        invalidate_context(paths.root, node_id, reason=f"edge_created:{edge_id}", actor=actor)
        for node_id in nodes
    ]
    op = OperationLog(paths).append(
        operation_type="edge_create",
        actor=actor,
        targets=[str(paths.root), edge_id, *nodes],
        command="hive edge create",
        changed_files=[
            {"path": str(edge_path.relative_to(paths.root))},
            {"path": str((memory_dir / "CURRENT.md").relative_to(paths.root))},
            {"path": str((memory_dir / "HISTORY.md").relative_to(paths.root))},
            {"path": str(import_workspace.relative_to(paths.root))},
        ],
        changed_records=[{"id": edge_id, "type": "edge"}],
        rollback={"supported": True, "strategy": "archive_or_remove_created_edge"},
    )
    return {"ok": True, "edge": record, "operation": op.id, "invalidations": invalidations}


def list_edges(
    root: Path, *, node: str | None = None, include_archived: bool = False
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    graph = MemoryGraph(paths.root)
    edges = []
    for edge in sorted(graph.edges.values(), key=lambda item: item.id):
        if not include_archived and edge.status != "active":
            continue
        if node and node not in edge.nodes:
            continue
        edge_path = _edge_file(paths, edge.id)
        edges.append(
            {**edge.model_dump(mode="json"), "path": str(edge_path.relative_to(paths.root))}
        )
    return {"ok": True, "edges": edges}


def update_edge_status(
    root: Path, edge_id: str, *, status: str, actor: str, reason: str | None = None
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    edge_path = _edge_file(paths, edge_id)
    if not edge_path.exists():
        raise ValueError(f"Edge not found: {edge_id}")
    doc = read_markdown(edge_path)
    record = dict(doc.frontmatter)
    old_status = str(record.get("status", "active"))
    record["status"] = status
    record[f"{status}_at"] = utc_now_iso()
    record[f"{status}_by"] = actor
    if reason:
        record[f"{status}_reason"] = reason
    atomic_write_text(edge_path, dump_markdown(record, doc.body))
    nodes = [str(item) for item in record.get("nodes", [])]
    for node_id in nodes:
        invalidate_context(paths.root, node_id, reason=f"edge_{status}:{edge_id}", actor=actor)
    archive_path: Path | None = None
    changed_records: list[dict[str, Any]] = [
        {"id": edge_id, "type": "edge", "old_status": old_status, "status": status}
    ]
    changed_files = [{"path": str(edge_path.relative_to(paths.root))}]
    if status == "archived":
        archive_record = {
            "id": new_id("archive"),
            "target": edge_id,
            "target_type": "edge",
            "reason": reason or "edge archived",
            "archived_at": record[f"{status}_at"],
            "archived_by": actor,
            "status": "archived",
            "excluded_from_startup_context": True,
            "archive_deferral": {"final_compaction_deferred": True},
        }
        archive_path = paths.root / "memory" / "audit" / f"{archive_record['id']}.yaml"
        atomic_write_text(archive_path, yaml.safe_dump(archive_record, sort_keys=False))
        changed_files.append({"path": str(archive_path.relative_to(paths.root))})
        changed_records.append({"id": archive_record["id"], "type": "archive"})
    op = OperationLog(paths).append(
        operation_type="edge_restore" if status == "active" else f"edge_{status}",
        actor=actor,
        targets=[str(paths.root), edge_id, *nodes],
        command="hive edge restore" if status == "active" else f"hive edge {status}",
        changed_files=changed_files,
        changed_records=changed_records,
        rollback={"supported": True, "strategy": f"restore_edge_status:{old_status}"},
    )
    return {
        "ok": True,
        "edge": record,
        "operation": op.id,
        "archive_path": str(archive_path) if archive_path else None,
    }


def archive_edge(root: Path, edge_id: str, *, actor: str, reason: str) -> dict[str, Any]:
    return update_edge_status(root, edge_id, status="archived", actor=actor, reason=reason)


def restore_edge(root: Path, edge_id: str, *, actor: str) -> dict[str, Any]:
    return update_edge_status(root, edge_id, status="active", actor=actor, reason=None)
