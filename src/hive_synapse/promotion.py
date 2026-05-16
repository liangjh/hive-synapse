from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .context import invalidate_context
from .errors import WorkspaceError
from .frontmatter import read_markdown, write_markdown
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .llm import generate_structured, input_hash_for_path, should_use_model, write_model_run
from .operations import OperationLog
from .paths import WorkspacePaths, target_to_path_fragment
from .policies import operation_policy
from .prompts import PROMOTION_SWEEP_PROMPT

AUTHORIZED_REVIEW_PREFIXES = ("steward:", "human:admin", "system:")

PROMOTION_SCHEMA = {
    "type": "object",
    "required": ["recommended", "confidence", "rationale"],
    "properties": {
        "recommended": {"type": "boolean"},
        "confidence": {"type": "number"},
        "rationale": {"type": "string"},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "missing_evidence": {"type": "array", "items": {"type": "string"}},
        "recommended_target_scope": {"type": "string"},
    },
}


def _proposal_paths(paths: WorkspacePaths) -> list[Path]:
    return sorted((paths.root / "memory" / "proposals").glob("*.yaml"))


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise WorkspaceError(f"Expected YAML mapping: {path}")
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, yaml.safe_dump(data, sort_keys=False))


def _load_proposal(paths: WorkspacePaths, proposal_id: str) -> tuple[Path, dict[str, Any]]:
    matches = [
        path
        for path in _proposal_paths(paths)
        if path.stem == proposal_id or proposal_id in path.stem
    ]
    if not matches:
        raise WorkspaceError(f"Promotion proposal not found: {proposal_id}")
    path = matches[0]
    return path, _load_yaml(path)


def _find_memory_record(paths: WorkspacePaths, record_id: str) -> tuple[Path, dict[str, Any], str]:
    for path in sorted((paths.root / "memory" / "records").rglob("*.md")):
        if path.name in {"CURRENT.md", "HISTORY.md"}:
            continue
        doc = read_markdown(path)
        if doc.frontmatter.get("id") == record_id:
            return path, doc.frontmatter, doc.body
    raise WorkspaceError(f"Memory record not found: {record_id}")


def _target_from_scope(scope: str) -> str:
    if scope.endswith("/published"):
        return scope[: -len("/published")]
    if scope.endswith("/reviewed"):
        return scope[: -len("/reviewed")]
    return scope


def _authorized(actor: str) -> bool:
    return actor.startswith(AUTHORIZED_REVIEW_PREFIXES)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _confidence(value: Any, *, fallback: float = 0.6) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, parsed))


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "recommended"}
    return bool(value)


def list_proposals(root: Path, *, status: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    proposals = []
    for path in _proposal_paths(paths):
        data = _load_yaml(path)
        if status and data.get("status") != status:
            continue
        data["path"] = str(path.relative_to(paths.root))
        proposals.append(data)
    return {"ok": True, "proposals": proposals}


def review_proposal(
    root: Path, proposal_id: str, *, decision: str, actor: str, rationale: str
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    if decision not in {"approved", "rejected"}:
        raise WorkspaceError("decision must be approved or rejected")
    if not _authorized(actor):
        raise WorkspaceError(f"Actor {actor} is not authorized to review proposals")
    path, proposal = _load_proposal(paths, proposal_id)
    proposal["status"] = decision
    proposal["review"] = {
        "reviewer": actor,
        "decision": decision,
        "rationale": rationale,
        "reviewed_at": utc_now_iso(),
    }
    _write_yaml(path, proposal)
    operation = OperationLog(paths).append(
        operation_type="promotion_review",
        actor=actor,
        targets=[str(paths.root), proposal_id],
        command="hive promote review",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": proposal_id, "type": "promotion_proposal"}],
        rollback={"supported": True, "strategy": "restore_proposal_from_backup"},
    )
    return {"ok": True, "proposal": proposal, "operation": operation.id}


def apply_proposal(root: Path, proposal_id: str, *, actor: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    if not _authorized(actor):
        raise WorkspaceError(f"Actor {actor} is not authorized to apply proposals")
    proposal_path, proposal = _load_proposal(paths, proposal_id)
    if proposal.get("status") != "approved":
        raise WorkspaceError("Proposal must be approved before apply")
    source_path, source, body = _find_memory_record(paths, str(proposal["source_record"]))
    if not source.get("source_refs"):
        raise WorkspaceError("Cannot publish memory without source_refs")
    target = _target_from_scope(str(proposal.get("target_scope", "")))
    published = dict(source)
    source_id = str(source["id"])
    published_id = f"published_{source_id}"
    published["id"] = published_id
    published["derived_from"] = source_id
    published["authority"] = "published"
    published["status"] = "active"
    published["published_at"] = utc_now_iso()
    published["review"] = proposal.get("review") or {"reviewer": actor, "decision": "approved"}
    published["promotion"] = {
        "proposal_id": proposal_id,
        "source_record": source.get("id"),
        "applied_by": actor,
        "applied_at": utc_now_iso(),
    }
    output_dir = (
        paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(target) / "published"
    )
    output_path = output_dir / f"{published_id}.md"
    write_markdown(output_path, published, body)
    current_path = (
        paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(target) / "CURRENT.md"
    )
    current = (
        current_path.read_text(encoding="utf-8")
        if current_path.exists()
        else f"# Current Memory: {target}\n"
    )
    current_section = f"\n\n## Published Memory: {source['id']}\n\n{body.strip()}\n"
    if f"Published Memory: {source['id']}" not in current:
        atomic_write_text(current_path, current.rstrip() + current_section)
    proposal["status"] = "applied"
    proposal["applied_at"] = utc_now_iso()
    proposal["applied_by"] = actor
    _write_yaml(proposal_path, proposal)
    invalidation = invalidate_context(
        paths.root, target, reason=f"promotion_applied:{proposal_id}", actor=actor
    )
    operation = OperationLog(paths).append(
        operation_type="promotion_apply",
        actor=actor,
        targets=[str(paths.root), target, proposal_id],
        command="hive promote apply",
        changed_files=[
            {"path": str(output_path.relative_to(paths.root))},
            {"path": str(current_path.relative_to(paths.root))},
            {"path": str(proposal_path.relative_to(paths.root))},
        ],
        changed_records=[
            {"id": published_id, "type": "memory_record"},
            {"id": proposal_id, "type": "promotion_proposal"},
        ],
        rollback={"supported": True, "strategy": "restore_current_and_remove_published_record"},
    )
    return {
        "ok": True,
        "proposal": proposal,
        "published_path": str(output_path),
        "current_path": str(current_path),
        "invalidation": invalidation["invalidation"],
        "context_invalidation": invalidation,
        "operation": operation.id,
    }


def reject_proposal(root: Path, proposal_id: str, *, actor: str, rationale: str) -> dict[str, Any]:
    return review_proposal(root, proposal_id, decision="rejected", actor=actor, rationale=rationale)


def sweep_promotability(
    root: Path,
    *,
    create_proposals: bool | None = None,
    actor: str = "system:sweep",
    llm_profile: str | None = None,
    credential: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy = operation_policy(paths, "promotion")
    if create_proposals is None:
        create_proposals = bool(policy.get("create_proposals_by_default", False))
    use_model = should_use_model(root, task="promotion_sweep", actor=actor, profile_id=llm_profile)
    promotable = []
    needs_more_evidence = []
    conflicts_detected = []
    not_promotable = []
    created = []
    changed_files = []
    changed_records = []
    for path in sorted((paths.root / "memory" / "records").rglob("candidates/*.md")):
        doc = read_markdown(path)
        data = doc.frontmatter
        if not data:
            continue
        body_lower = doc.body.lower()
        record = {
            "id": data.get("id"),
            "path": str(path.relative_to(paths.root)),
            "node": data.get("node"),
        }
        if "conflict" in body_lower or "contradicts" in body_lower:
            conflict_id = new_id("conflict")
            conflict = {
                "id": conflict_id,
                "status": "open",
                "scope": data.get("node") or data.get("scope"),
                "conflict_type": "semantic_marker",
                "records": {"candidate": data.get("id")},
                "detected_at": utc_now_iso(),
                "reason": "Candidate text contains conflict marker.",
            }
            conflict_path = paths.root / "memory" / "conflicts" / f"{conflict_id}.yaml"
            atomic_write_text(conflict_path, yaml.safe_dump(conflict, sort_keys=False))
            changed_files.append({"path": str(conflict_path.relative_to(paths.root))})
            changed_records.append({"id": conflict_id, "type": "memory_conflict"})
            conflicts_detected.append({**record, "conflict_id": conflict_id})
            continue
        if not data.get("source_refs"):
            needs_more_evidence.append(record)
            continue
        if data.get("authority") != "candidate":
            not_promotable.append(record)
            continue
        advisory = None
        model_request = None
        model_response = None
        if use_model:
            try:
                model_request, model_response = generate_structured(
                    root,
                    task="promotion_sweep",
                    actor=actor,
                    profile_id=llm_profile,
                    credential_id=credential,
                    expected_schema=PROMOTION_SCHEMA,
                    input_refs=data.get("source_refs") or [],
                    input_hashes=input_hash_for_path(paths.root, str(path.relative_to(paths.root))),
                    prompt_id=PROMOTION_SWEEP_PROMPT.id,
                    prompt_version=PROMOTION_SWEEP_PROMPT.version,
                    messages=PROMOTION_SWEEP_PROMPT.render_messages(
                        candidate_metadata=yaml.safe_dump(data, sort_keys=False),
                        candidate_body=doc.body[:12000],
                    ),
                )
                output = model_response.output_json
                advisory = {
                    "recommended": _bool_value(output.get("recommended")),
                    "confidence": _confidence(output.get("confidence"), fallback=0.5),
                    "rationale": str(output.get("rationale") or ""),
                    "risk_flags": _string_list(output.get("risk_flags")),
                    "missing_evidence": _string_list(output.get("missing_evidence")),
                    "recommended_target_scope": output.get("recommended_target_scope")
                    or f"{data.get('node') or 'org'}/published",
                    "provider": model_response.provider,
                    "model": model_response.model,
                    "profile": model_request.profile.get("id", "deterministic"),
                    "credential": (model_request.credential or {}).get("id", "none"),
                }
                if not advisory["recommended"]:
                    run = write_model_run(
                        root, request=model_request, response=model_response, status="completed"
                    )
                    advisory["model_run"] = run["record"]["id"]
                    changed_files.append({"path": str(run["path"].relative_to(paths.root))})
                    changed_records.append({"id": run["record"]["id"], "type": "llm_run"})
                    blocked = {**record, "llm_advisory": advisory}
                    if advisory["missing_evidence"]:
                        needs_more_evidence.append(blocked)
                    else:
                        not_promotable.append(blocked)
                    continue
            except WorkspaceError as exc:
                run_request = model_request
                if run_request is not None:
                    run = write_model_run(
                        root, request=run_request, response=None, status="failed", error=str(exc)
                    )
                    changed_files.append({"path": str(run["path"].relative_to(paths.root))})
                    changed_records.append({"id": run["record"]["id"], "type": "llm_run"})
                not_promotable.append({**record, "llm_error": str(exc)})
                continue
        if advisory:
            record["llm_advisory"] = advisory
        promotable.append(record)
        if create_proposals:
            proposal_id = new_id("proposal")
            node = data.get("node") or "org"
            model_run = None
            if model_request and model_response and advisory:
                model_run = write_model_run(
                    root,
                    request=model_request,
                    response=model_response,
                    status="completed",
                    created_proposals=[proposal_id],
                )
                advisory["model_run"] = model_run["record"]["id"]
                record["llm_advisory"] = advisory
                changed_files.append({"path": str(model_run["path"].relative_to(paths.root))})
                changed_records.append({"id": model_run["record"]["id"], "type": "llm_run"})
            proposal = {
                "id": proposal_id,
                "source_record": data.get("id"),
                "source_scope": f"{node}/candidates",
                "target_scope": advisory.get("recommended_target_scope")
                if advisory
                else f"{node}/published",
                "promotion_type": "sweep_candidate_to_node",
                "rationale": advisory.get("rationale")
                if advisory and advisory.get("rationale")
                else "Promotability sweep found source-linked candidate memory.",
                "status": "candidate",
                "created_at": utc_now_iso(),
                "created_by": actor,
            }
            if advisory:
                proposal["llm_advisory"] = advisory
            proposal_path = paths.root / "memory" / "proposals" / f"{proposal_id}.yaml"
            atomic_write_text(proposal_path, yaml.safe_dump(proposal, sort_keys=False))
            changed_files.append({"path": str(proposal_path.relative_to(paths.root))})
            changed_records.append({"id": proposal_id, "type": "promotion_proposal"})
            created.append(proposal)
        elif model_request and model_response and advisory:
            model_run = write_model_run(
                root, request=model_request, response=model_response, status="completed"
            )
            advisory["model_run"] = model_run["record"]["id"]
            record["llm_advisory"] = advisory
            changed_files.append({"path": str(model_run["path"].relative_to(paths.root))})
            changed_records.append({"id": model_run["record"]["id"], "type": "llm_run"})
    status = (
        "no_changes"
        if not any([promotable, needs_more_evidence, conflicts_detected, created])
        else "completed"
    )
    report = {
        "ok": True,
        "status": status,
        "promotable": promotable,
        "needs_more_evidence": needs_more_evidence,
        "conflicts_detected": conflicts_detected,
        "not_promotable": not_promotable,
        "created_proposals": created,
        "policy": {
            "sweep_mode": policy.get("sweep_mode", "manual"),
            "create_proposals": create_proposals,
        },
    }
    report_id = new_id("promotability")
    report_path = paths.root / "memory" / "audit" / f"{report_id}.yaml"
    atomic_write_text(report_path, yaml.safe_dump({"id": report_id, **report}, sort_keys=False))
    changed_files.append({"path": str(report_path.relative_to(paths.root))})
    changed_records.append({"id": report_id, "type": "promotability_report"})
    OperationLog(paths).append(
        operation_type="promotion_sweep",
        actor=actor,
        targets=[str(paths.root)],
        command="hive promote sweep",
        changed_files=changed_files,
        changed_records=changed_records,
        rollback={"supported": False, "strategy": "report_only"},
    )
    return report
