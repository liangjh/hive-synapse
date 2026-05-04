from __future__ import annotations

from pathlib import Path
from typing import Any
from . import simple_yaml as yaml
from .connectors import classify_connector, external_ref_for
from .errors import WorkspaceError
from .frontmatter import write_markdown
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .llm import generate_structured, input_hash_for_path, should_use_model, write_model_run
from .operations import OperationLog
from .paths import WorkspacePaths, target_to_path_fragment
from .repository import WorkspaceRepository, record_relative_path

IMPORT_STATES = {"dropped", "classified", "compacted", "proposed", "processed", "rejected"}
MODEL_INPUT_LIMIT = 12000

CLASSIFICATION_SCHEMA = {
    "type": "object",
    "required": ["topics", "temporal_status", "sensitivity"],
    "properties": {
        "topics": {"type": "array", "items": {"type": "string"}},
        "temporal_status": {"type": "string"},
        "sensitivity": {"type": "string"},
        "rationale": {"type": "string"},
    },
}

COMPACTION_SCHEMA = {
    "type": "object",
    "required": ["summary", "confidence", "tags"],
    "properties": {
        "summary": {"type": "string"},
        "confidence": {"type": "number"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "sensitivity": {"type": "string"},
        "rationale": {"type": "string"},
    },
}


def _import_dir(paths: WorkspacePaths, target: str) -> Path:
    return paths.root / "memory" / "imports" / target_to_path_fragment(target)


def _items_dir(paths: WorkspacePaths, target: str) -> Path:
    return _import_dir(paths, target) / "items"


def _load_import_item(paths: WorkspacePaths, import_id: str) -> tuple[Path, dict[str, Any]]:
    matches = sorted((paths.root / "memory" / "imports").rglob(f"{import_id}.yaml"))
    if not matches:
        matches = sorted((paths.root / "memory" / "imports").rglob(f"*{import_id}*.yaml"))
    if not matches:
        raise WorkspaceError(f"Import item not found: {import_id}")
    path = matches[0]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return path, data


def _write_import_item(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))


def _read_import_text(paths: WorkspacePaths, item: dict[str, Any]) -> str:
    local_path = item.get("local_path")
    if local_path and (paths.root / str(local_path)).exists():
        return (paths.root / str(local_path)).read_text(encoding="utf-8", errors="ignore")
    return ""


def _import_input_refs(item: dict[str, Any]) -> list[dict[str, Any]]:
    ref = item.get("source_ref") or item.get("external_ref") or {"source_id": f"import:{item.get('id')}"}
    return [ref] if isinstance(ref, dict) else [{"source_id": f"import:{item.get('id')}", "locator": str(ref)}]


def _string_list(value: Any, *, fallback: list[str] | None = None) -> list[str]:
    result = []
    if isinstance(value, list):
        for item in value:
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
    return result or list(fallback or [])


def _confidence(value: Any, *, fallback: float = 0.6) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, parsed))


def _model_descriptor(provider: str, model: str) -> str:
    return f"llm:{provider}:{model}"


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


def classify_import(
    root: Path,
    import_id: str,
    *,
    sensitivity: str | None = None,
    actor: str = "system:import",
    llm_profile: str | None = None,
    credential: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    item_path, item = _load_import_item(paths, import_id)
    text = _read_import_text(paths, item)
    model_run = None
    if should_use_model(root, task="import_classify", actor=actor, profile_id=llm_profile):
        request, response = generate_structured(
            root,
            task="import_classify",
            actor=actor,
            profile_id=llm_profile,
            credential_id=credential,
            expected_schema=CLASSIFICATION_SCHEMA,
            input_refs=_import_input_refs(item),
            input_hashes=input_hash_for_path(paths.root, item.get("local_path")),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify imported memory for a workspace. Return only JSON with "
                        "topics, temporal_status, sensitivity, and optional rationale. "
                        "Do not invent facts beyond the supplied text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Import id: {import_id}\n"
                        f"Target: {item.get('target')}\n"
                        f"Source type: {item.get('source_type')}\n\n"
                        f"Text:\n{text[:MODEL_INPUT_LIMIT]}"
                    ),
                },
            ],
        )
        output = response.output_json
        classification = {
            "target": item["target"],
            "topics": _string_list(output.get("topics"), fallback=["general"]),
            "temporal_status": str(output.get("temporal_status") or "current"),
            "sensitivity": sensitivity or str(output.get("sensitivity") or "internal"),
            "classified_at": utc_now_iso(),
            "classifier": _model_descriptor(response.provider, response.model),
            "model_profile": request.profile.get("id", "deterministic"),
            "credential": (request.credential or {}).get("id", "none"),
        }
        if output.get("rationale"):
            classification["rationale"] = str(output.get("rationale"))
        model_run = write_model_run(root, request=request, response=response, status="completed")
        classification["model_run"] = model_run["record"]["id"]
    else:
        lower = text.lower()
        topics = []
        for topic in ["policy", "practice", "project", "decision", "risk", "skill"]:
            if topic in lower:
                topics.append(topic)
        if not topics:
            topics.append("general")
        classification = {
            "target": item["target"],
            "topics": topics,
            "temporal_status": "current" if "deprecated" not in lower else "historical",
            "sensitivity": sensitivity or ("confidential" if "confidential" in lower else "internal"),
            "classified_at": utc_now_iso(),
            "classifier": "deterministic:v0",
        }
    item["classification"] = classification
    item["sensitivity"] = item["classification"]["sensitivity"]
    item["state"] = "classified"
    _write_import_item(item_path, item)
    changed_files = [{"path": record_relative_path(item_path, paths.root)}]
    changed_records = [{"id": import_id, "type": "import_item"}]
    if model_run:
        changed_files.append({"path": record_relative_path(model_run["path"], paths.root)})
        changed_records.append({"id": model_run["record"]["id"], "type": "llm_run"})
    operation = OperationLog(paths).append(
        operation_type="import_classify",
        actor=actor,
        targets=[import_id],
        command="hive import classify",
        changed_files=changed_files,
        changed_records=changed_records,
        rollback={"supported": True, "strategy": "restore_import_item_from_backup"},
    )
    return {"ok": True, "import_id": import_id, "classification": item["classification"], "operation": operation.id}


def compact_import(
    root: Path,
    import_id: str,
    *,
    actor: str = "system:import",
    llm_profile: str | None = None,
    credential: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    item_path, item = _load_import_item(paths, import_id)
    if "classification" not in item:
        classify_import(root, import_id, actor=actor, llm_profile=llm_profile, credential=credential)
        item_path, item = _load_import_item(paths, import_id)
    text = _read_import_text(paths, item)
    model_run = None
    model_response = None
    model_request = None
    model_output: dict[str, Any] = {}
    if should_use_model(root, task="import_compact", actor=actor, profile_id=llm_profile):
        model_request, model_response = generate_structured(
            root,
            task="import_compact",
            actor=actor,
            profile_id=llm_profile,
            credential_id=credential,
            expected_schema=COMPACTION_SCHEMA,
            input_refs=_import_input_refs(item),
            input_hashes=input_hash_for_path(paths.root, item.get("local_path")),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize imported source text into concise candidate memory. "
                        "Return only JSON with summary, confidence, tags, optional sensitivity, "
                        "and optional rationale. Preserve source-grounded facts and avoid invention."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Import id: {import_id}\n"
                        f"Target node: {item.get('target')}\n"
                        f"Classification: {yaml.safe_dump(item.get('classification') or {}, sort_keys=False)}\n\n"
                        f"Text:\n{text[:MODEL_INPUT_LIMIT]}"
                    ),
                },
            ],
        )
        model_output = model_response.output_json
        summary = " ".join(str(model_output.get("summary") or "").strip().split())
        if not summary:
            raise WorkspaceError("Model compaction response did not include a summary")
    else:
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
        "confidence": _confidence(model_output.get("confidence"), fallback=0.6),
        "sensitivity": model_output.get("sensitivity") or item.get("sensitivity", "internal"),
        "created_at": utc_now_iso(),
        "created_by": actor,
        "source_refs": [item.get("source_ref") or item.get("external_ref") or {"source_id": f"import:{import_id}"}],
        "tags": _string_list(
            ["import", *item.get("classification", {}).get("topics", []), *_string_list(model_output.get("tags"))],
            fallback=["import"],
        ),
        "import_id": import_id,
    }
    if model_request and model_response:
        model_run = write_model_run(
            root,
            request=model_request,
            response=model_response,
            status="completed",
            created_records=[memory_id],
        )
        candidate["generated_by"] = {
            "type": "llm",
            "run_id": model_run["record"]["id"],
            "provider": model_response.provider,
            "model": model_response.model,
            "profile": model_request.profile.get("id", "deterministic"),
            "credential": (model_request.credential or {}).get("id", "none"),
        }
        if model_output.get("rationale"):
            candidate["generation_rationale"] = str(model_output.get("rationale"))
    candidate_path = paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(target) / "candidates" / f"{memory_id}.md"
    write_markdown(candidate_path, candidate, f"# Import Candidate\n\n{summary}\n")
    item["state"] = "compacted"
    item.setdefault("candidate_records", []).append(memory_id)
    _write_import_item(item_path, item)
    changed_files = [
        {"path": record_relative_path(candidate_path, paths.root)},
        {"path": record_relative_path(item_path, paths.root)},
    ]
    changed_records = [{"id": memory_id, "type": "memory_record"}, {"id": import_id, "type": "import_item"}]
    if model_run:
        changed_files.append({"path": record_relative_path(model_run["path"], paths.root)})
        changed_records.append({"id": model_run["record"]["id"], "type": "llm_run"})
    operation = OperationLog(paths).append(
        operation_type="import_compact",
        actor=actor,
        targets=[import_id, target],
        command="hive import compact",
        changed_files=changed_files,
        changed_records=changed_records,
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
