from __future__ import annotations

from pathlib import Path
from typing import Any
from . import simple_yaml as yaml
from .connectors import classify_connector, external_ref_for
from .frontmatter import write_markdown
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths, target_to_path_fragment
from .repository import WorkspaceRepository, record_relative_path

IMPORT_STATES = {"dropped", "classified", "compacted", "proposed", "processed", "rejected"}


def _import_dir(paths: WorkspacePaths, target: str) -> Path:
    return paths.root / "memory" / "imports" / target_to_path_fragment(target)


def _items_dir(paths: WorkspacePaths, target: str) -> Path:
    return _import_dir(paths, target) / "items"


def _load_import_item(paths: WorkspacePaths, import_id: str) -> tuple[Path, dict[str, Any]]:
    matches = sorted((paths.root / "memory" / "imports").rglob(f"{import_id}.yaml"))
    if not matches:
        matches = sorted((paths.root / "memory" / "imports").rglob(f"*{import_id}*.yaml"))
    if not matches:
        raise FileNotFoundError(f"Import item not found: {import_id}")
    path = matches[0]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return path, data


def _write_import_item(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))


def _ensure_import_workspace(paths: WorkspacePaths, target: str) -> Path:
    root = _import_dir(paths, target)
    for child in ["inbox", "fetched", "normalized", "compacted", "candidates", "processed", "rejected", "items", "reports"]:
        (root / child).mkdir(parents=True, exist_ok=True)
    workspace = {
        "id": f"import_workspace_{target.replace('/', '_')}",
        "target": target,
        "status": "active",
        "paths": {
            child: str((root / child).relative_to(paths.root)) + "/"
            for child in ["inbox", "fetched", "normalized", "compacted", "candidates", "processed", "rejected", "items", "reports"]
        },
    }
    workspace_path = root / "workspace.yaml"
    if not workspace_path.exists():
        atomic_write_text(workspace_path, yaml.safe_dump(workspace, sort_keys=False))
    return root


def add_import(root: Path, target: str, source: str, *, actor: str = "system:import") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    repo = WorkspaceRepository(paths.root)
    import_root = _ensure_import_workspace(paths, target)
    import_id = new_id("import")
    source_path = Path(source).expanduser()
    now = utc_now_iso()
    item: dict[str, Any] = {
        "id": import_id,
        "workspace": f"import_workspace_{target.replace('/', '_')}",
        "target": target,
        "source_type": "markdown" if str(source_path).lower().endswith((".md", ".markdown")) else "file",
        "state": "dropped",
        "created_at": now,
        "raw_preserved": False,
        "sensitivity": "unknown",
    }
    changed_files: list[dict[str, Any]] = []
    if source_path.exists():
        raw_rel = Path("memory") / "raw" / "imports" / target_to_path_fragment(target) / import_id / source_path.name
        raw_path = repo.copy_raw_file(source_path, raw_rel)
        item["local_path"] = record_relative_path(raw_path, paths.root)
        item["raw_preserved"] = True
        item["source_ref"] = {"source_id": f"raw:{import_id}", "locator": item["local_path"]}
        changed_files.append({"path": item["local_path"]})
    else:
        text = source
        raw_rel = Path("memory") / "raw" / "imports" / target_to_path_fragment(target) / import_id / "dropped-text.md"
        raw_path = repo.preserve_raw(raw_rel, text.encode("utf-8"))
        item["source_type"] = "text"
        item["local_path"] = record_relative_path(raw_path, paths.root)
        item["raw_preserved"] = True
        item["source_ref"] = {"source_id": f"raw:{import_id}", "locator": item["local_path"]}
        changed_files.append({"path": item["local_path"]})
    item_path = import_root / "items" / f"{import_id}.yaml"
    _write_import_item(item_path, item)
    changed_files.append({"path": record_relative_path(item_path, paths.root)})
    operation = OperationLog(paths).append(
        operation_type="import_add",
        actor=actor,
        targets=[target],
        command="hive import add",
        changed_files=changed_files,
        changed_records=[{"id": import_id, "type": "import_item"}],
        rollback={"supported": False, "strategy": "raw_artifacts_append_only"},
    )
    return {"ok": True, "import_id": import_id, "item": item, "operation": operation.id}


def fetch_import(root: Path, target: str, url: str, *, connector: str | None = None, actor: str = "system:import") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    import_root = _ensure_import_workspace(paths, target)
    connector_name = classify_connector(url, connector)
    import_id = new_id("import")
    item = {
        "id": import_id,
        "workspace": f"import_workspace_{target.replace('/', '_')}",
        "target": target,
        "source_type": connector_name,
        "state": "dropped",
        "created_at": utc_now_iso(),
        "external_ref": external_ref_for(connector_name, url),
        "raw_preserved": False,
        "sensitivity": "unknown",
    }
    item_path = import_root / "items" / f"{import_id}.yaml"
    _write_import_item(item_path, item)
    operation = OperationLog(paths).append(
        operation_type="import_fetch",
        actor=actor,
        targets=[target, url],
        command="hive import fetch",
        changed_files=[{"path": record_relative_path(item_path, paths.root)}],
        changed_records=[{"id": import_id, "type": "import_item"}],
        rollback={"supported": False, "strategy": "delete_import_item_if_unprocessed"},
    )
    return {"ok": True, "import_id": import_id, "item": item, "operation": operation.id}


def classify_import(root: Path, import_id: str, *, sensitivity: str | None = None, actor: str = "system:import") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    item_path, item = _load_import_item(paths, import_id)
    local_path = item.get("local_path")
    text = ""
    if local_path and (paths.root / local_path).exists():
        text = (paths.root / local_path).read_text(encoding="utf-8", errors="ignore")
    lower = text.lower()
    topics = []
    for topic in ["policy", "practice", "project", "decision", "risk", "skill"]:
        if topic in lower:
            topics.append(topic)
    if not topics:
        topics.append("general")
    item["classification"] = {
        "target": item["target"],
        "topics": topics,
        "temporal_status": "current" if "deprecated" not in lower else "historical",
        "sensitivity": sensitivity or ("confidential" if "confidential" in lower else "internal"),
        "classified_at": utc_now_iso(),
        "classifier": "deterministic:v0",
    }
    item["sensitivity"] = item["classification"]["sensitivity"]
    item["state"] = "classified"
    _write_import_item(item_path, item)
    operation = OperationLog(paths).append(
        operation_type="import_classify",
        actor=actor,
        targets=[import_id],
        command="hive import classify",
        changed_files=[{"path": record_relative_path(item_path, paths.root)}],
        changed_records=[{"id": import_id, "type": "import_item"}],
        rollback={"supported": True, "strategy": "restore_import_item_from_backup"},
    )
    return {"ok": True, "import_id": import_id, "classification": item["classification"], "operation": operation.id}


def compact_import(root: Path, import_id: str, *, actor: str = "system:import") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    item_path, item = _load_import_item(paths, import_id)
    if "classification" not in item:
        classify_import(root, import_id, actor=actor)
        item_path, item = _load_import_item(paths, import_id)
    local_path = item.get("local_path")
    text = ""
    if local_path and (paths.root / local_path).exists():
        text = (paths.root / local_path).read_text(encoding="utf-8", errors="ignore")
    summary = " ".join(text.strip().split())[:600]
    if not summary:
        result = {"id": new_id("import_result"), "import_id": import_id, "status": "no_changes", "created_at": utc_now_iso()}
        result_path = _import_dir(paths, item["target"]) / "compacted" / f"{result['id']}.yaml"
        atomic_write_text(result_path, yaml.safe_dump(result, sort_keys=False))
        return {"ok": True, "import_id": import_id, "status": "no_changes", "result": result}
    memory_id = new_id("mem")
    target = item["target"]
    candidate = {
        "id": memory_id,
        "type": "import_summary",
        "scope": "node",
        "node": target,
        "authority": "candidate",
        "confidence": 0.6,
        "sensitivity": item.get("sensitivity", "internal"),
        "created_at": utc_now_iso(),
        "created_by": actor,
        "source_refs": [item.get("source_ref") or item.get("external_ref") or {"source_id": f"import:{import_id}"}],
        "tags": ["import", *item.get("classification", {}).get("topics", [])],
        "import_id": import_id,
    }
    candidate_path = paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(target) / "candidates" / f"{memory_id}.md"
    write_markdown(candidate_path, candidate, f"# Import Candidate\n\n{summary}\n")
    item["state"] = "compacted"
    item.setdefault("candidate_records", []).append(memory_id)
    _write_import_item(item_path, item)
    operation = OperationLog(paths).append(
        operation_type="import_compact",
        actor=actor,
        targets=[import_id, target],
        command="hive import compact",
        changed_files=[
            {"path": record_relative_path(candidate_path, paths.root)},
            {"path": record_relative_path(item_path, paths.root)},
        ],
        changed_records=[{"id": memory_id, "type": "memory_record"}, {"id": import_id, "type": "import_item"}],
        rollback={"supported": True, "strategy": "remove_candidate_restore_import_item"},
    )
    return {"ok": True, "import_id": import_id, "candidate_id": memory_id, "candidate_path": str(candidate_path), "operation": operation.id}


def propose_import(root: Path, import_id: str, *, actor: str = "system:import") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    item_path, item = _load_import_item(paths, import_id)
    candidates = item.get("candidate_records") or []
    if not candidates:
        compact_import(root, import_id, actor=actor)
        item_path, item = _load_import_item(paths, import_id)
        candidates = item.get("candidate_records") or []
    proposals = []
    changed_files = []
    for candidate_id in candidates:
        proposal_id = new_id("proposal")
        proposal = {
            "id": proposal_id,
            "source_record": candidate_id,
            "source_scope": f"{item['target']}/candidates",
            "target_scope": f"{item['target']}/published",
            "promotion_type": "candidate_to_node",
            "rationale": "Import compaction produced source-linked candidate memory.",
            "status": "candidate",
            "created_at": utc_now_iso(),
            "created_by": actor,
            "import_id": import_id,
        }
        proposal_path = paths.root / "memory" / "proposals" / f"{proposal_id}.yaml"
        report_path = _import_dir(paths, item["target"]) / "reports" / f"{proposal_id}.md"
        atomic_write_text(proposal_path, yaml.safe_dump(proposal, sort_keys=False))
        atomic_write_text(report_path, f"# Promotion Proposal: {proposal_id}\n\nCandidate: `{candidate_id}`\n\nTarget: `{item['target']}`\n")
        proposals.append(proposal)
        changed_files.extend([
            {"path": record_relative_path(proposal_path, paths.root)},
            {"path": record_relative_path(report_path, paths.root)},
        ])
    item["state"] = "proposed"
    item["proposal_ids"] = [proposal["id"] for proposal in proposals]
    _write_import_item(item_path, item)
    operation = OperationLog(paths).append(
        operation_type="import_propose",
        actor=actor,
        targets=[import_id],
        command="hive import propose",
        changed_files=changed_files + [{"path": record_relative_path(item_path, paths.root)}],
        changed_records=[{"id": proposal["id"], "type": "promotion_proposal"} for proposal in proposals],
        rollback={"supported": True, "strategy": "remove_proposals_restore_import_item"},
    )
    return {"ok": True, "import_id": import_id, "proposals": proposals, "operation": operation.id}
