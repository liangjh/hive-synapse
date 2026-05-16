"""Materialized agent session lifecycle.

Module guide:
- `start_session` creates a harness-ready session mount with context and outbox files.
- `finish_session` collects memory deltas back into actor/private and shared workflows.

Maintenance: update this guide when adding public functions/classes to this module.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .compaction import compact_node
from .errors import WorkspaceError
from .fs import atomic_write_text, ensure_within_root, sha256_file
from .ids import utc_now_iso
from .imports import add_import, classify_import, compact_import, propose_import
from .operations import OperationLog
from .paths import WorkspacePaths
from .prompts import (
    OPENCLAW_TOOLS_PROMPT,
    SESSION_BOOTSTRAP_PROMPT,
    SESSION_OUTBOX_README_PROMPT,
    SESSION_SOUL_PROMPT,
    SESSION_USER_PROMPT,
)
from .sessions import sign_in_actor

SUPPORTED_ADAPTERS = {"generic", "codex", "claude", "hermes", "openclaw"}
DELTA_SCOPES = {"private", "node_candidate", "edge_candidate", "org_candidate"}
GENERATED_MODE = 0o444


def _safe_fragment(value: str) -> str:
    safe = []
    for char in value:
        if char.isalnum() or char in {"-", "_", "."}:
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "item"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise WorkspaceError(f"Expected YAML mapping: {path}")
    return data


def _relative_or_external(path: Path, root: Path) -> dict[str, str]:
    try:
        return {"path": str(path.resolve().relative_to(root.resolve()))}
    except ValueError:
        return {"external_path": str(path.resolve())}


def _write_generated(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip() + "\n")
    path.chmod(GENERATED_MODE)


def _source_entry(path: Path, root: Path) -> dict[str, Any]:
    entry: dict[str, Any] = _relative_or_external(path, root)
    if path.exists() and path.is_file():
        entry["sha256"] = sha256_file(path)
    return entry


def _actor_memory_path(paths: WorkspacePaths, personal_memory_home: str) -> Path:
    memory_dir = ensure_within_root(paths.root / personal_memory_home, paths.root)
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir / "MEMORY.md"


def _ensure_actor_memory(paths: WorkspacePaths, actor_id: str, personal_memory_home: str) -> Path:
    memory_path = _actor_memory_path(paths, personal_memory_home)
    if not memory_path.exists():
        atomic_write_text(
            memory_path,
            (
                f"# Agent Memory: {actor_id}\n\n"
                "Durable private memory for this actor. Session summaries append here; "
                "shared memory still requires candidate/proposal workflows.\n"
            ),
        )
    return memory_path


def _session_outbox_readme(actor_id: str, session_id: str, target: str) -> str:
    return SESSION_OUTBOX_README_PROMPT.render(
        actor_id=actor_id,
        session_id=session_id,
        target=target,
    )


def _bootstrap_markdown(
    adapter: str, record: dict[str, Any], context_dir: Path, outbox_dir: Path
) -> str:
    adapter_title = adapter.capitalize()
    if adapter == "codex":
        title = "Codex Agent Instructions"
    elif adapter == "claude":
        title = "Claude Agent Instructions"
    else:
        title = f"{adapter_title} Agent Instructions"
    context_rel = context_dir.relative_to(context_dir.parents[1])
    outbox_rel = outbox_dir.relative_to(outbox_dir.parents[1])
    return SESSION_BOOTSTRAP_PROMPT.render(
        title=title,
        context_rel=context_rel,
        outbox_rel=outbox_rel,
        actor=record["actor"],
        effective_node=record["effective_node"],
        role=record["role"],
        signin_id=record["id"],
        personal_memory_home=record["personal_memory_home"],
    )


def _soul_text(record: dict[str, Any], purpose: str | None) -> str:
    return SESSION_SOUL_PROMPT.render(
        actor=record["actor"],
        role=record["role"],
        effective_node=record["effective_node"],
        purpose=purpose or "No explicit session purpose supplied.",
    )


def _user_text(record: dict[str, Any], adapter: str, purpose: str | None) -> str:
    return SESSION_USER_PROMPT.render(
        adapter=adapter,
        signin_id=record["id"],
        instance=record["instance"],
        purpose=purpose or "No explicit session purpose supplied.",
    )


def _scope_record(record: dict[str, Any], mount_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "hive.session.scope.v0",
        "actor": record["actor"],
        "signin_id": record["id"],
        "effective_node": record["effective_node"],
        "role": record["role"],
        "mount": str(mount_path),
        "read_scope": {
            "context_snapshot": ".hive/context/",
            "inherited_nodes": record.get("inherited_nodes", []),
            "connected_edges": record.get("connected_edges", []),
            "personal_memory_snapshot": ".hive/context/MEMORY.md",
        },
        "write_scope": {
            "session_outbox": ".hive/outbox/",
            "private_memory_target": record.get("personal_memory_home"),
            "shared_memory_policy": "submit_memory_delta_then_promote",
        },
        "forbidden_writes": [
            "AGENTS.md",
            "CLAUDE.md",
            ".hive/context/",
            "parent_node_memory",
            "department_memory_direct_write",
            "organization_memory_direct_write",
        ],
    }


def _copy_adapter_aliases(adapter: str, mount_path: Path, bootstrap_text: str) -> list[Path]:
    files: list[Path] = []
    if adapter == "claude":
        claude_path = mount_path / "CLAUDE.md"
        _write_generated(claude_path, bootstrap_text)
        files.append(claude_path)
    elif adapter == "hermes":
        agents_path = mount_path / "AGENTS.md"
        bootstrap_path = mount_path / "BOOTSTRAP.md"
        _write_generated(agents_path, bootstrap_text)
        _write_generated(bootstrap_path, bootstrap_text)
        files.extend([agents_path, bootstrap_path])
    elif adapter == "openclaw":
        agents_path = mount_path / "AGENTS.md"
        tools_path = mount_path / "TOOLS.md"
        bootstrap_path = mount_path / "BOOTSTRAP.md"
        _write_generated(agents_path, bootstrap_text)
        _write_generated(tools_path, OPENCLAW_TOOLS_PROMPT.render())
        _write_generated(bootstrap_path, bootstrap_text)
        files.extend([agents_path, tools_path, bootstrap_path])
    else:
        agents_path = mount_path / "AGENTS.md"
        _write_generated(agents_path, bootstrap_text)
        files.append(agents_path)
    return files


def start_session(
    root: Path,
    actor_id: str,
    *,
    adapter: str = "generic",
    output: Path | None = None,
    home_node: str | None = None,
    role: str | None = None,
    instance: str | None = None,
    operator: str | None = None,
    require_assignment: bool = False,
    purpose: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    adapter = adapter.lower().strip()
    if adapter not in SUPPORTED_ADAPTERS:
        raise WorkspaceError(f"Unsupported adapter: {adapter}")
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    signin = sign_in_actor(
        paths.root,
        actor_id,
        home_node=home_node,
        role=role,
        instance=instance,
        operator=operator,
        require_assignment=require_assignment,
    )
    record = signin["signin"]
    session_id = str(record["id"])
    if output is None:
        mount_path = (
            Path.cwd()
            / ".hive-sessions"
            / _safe_fragment(actor_id)
            / f"{_safe_fragment(record['effective_node'])}-{session_id}"
        )
    else:
        mount_path = output.expanduser()
    mount_path = mount_path.resolve()
    if mount_path.exists() and any(mount_path.iterdir()):
        if not force:
            raise WorkspaceError(f"Mount output already exists and is not empty: {mount_path}")
        shutil.rmtree(mount_path)
    mount_path.mkdir(parents=True, exist_ok=True)

    hive_dir = mount_path / ".hive"
    context_dir = hive_dir / "context"
    outbox_dir = hive_dir / "outbox"
    artifacts_dir = outbox_dir / "artifacts"
    context_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    pack_path = Path(signin["context_pack"])
    pack_text = _read_text(pack_path)
    manifest_path = Path(signin["manifest"])
    actor_memory_path = _ensure_actor_memory(paths, actor_id, str(record["personal_memory_home"]))
    actor_memory_text = _read_text(actor_memory_path)

    scope = _scope_record(record, mount_path)
    context_manifest = {
        "schema_version": "hive.session.materialization.v0",
        "session_id": session_id,
        "signin_id": session_id,
        "actor": actor_id,
        "adapter": adapter,
        "workspace": str(paths.root),
        "mount": str(mount_path),
        "effective_node": record["effective_node"],
        "role": record["role"],
        "purpose": purpose,
        "generated_at": utc_now_iso(),
        "context_pack": str(pack_path),
        "source_manifest": str(manifest_path),
        "personal_memory_home": record["personal_memory_home"],
        "inherited_nodes": record.get("inherited_nodes", []),
        "connected_edges": record.get("connected_edges", []),
        "generated_files": [
            ".hive/context/SOUL.md",
            ".hive/context/CONTEXT.md",
            ".hive/context/USER.md",
            ".hive/context/MEMORY.md",
            ".hive/context/SCOPE.yaml",
            ".hive/context/manifest.yaml",
        ],
        "sources": [
            _source_entry(pack_path, paths.root),
            _source_entry(manifest_path, paths.root),
            _source_entry(actor_memory_path, paths.root),
        ],
        "outbox": ".hive/outbox/",
    }

    generated_context_files = {
        context_dir / "SOUL.md": _soul_text(record, purpose),
        context_dir / "CONTEXT.md": pack_text or "# CONTEXT\n\nNo context pack content was available.",
        context_dir / "USER.md": _user_text(record, adapter, purpose),
        context_dir / "MEMORY.md": actor_memory_text or f"# Agent Memory: {actor_id}\n",
        context_dir / "SCOPE.yaml": yaml.safe_dump(scope, sort_keys=False),
        context_dir / "manifest.yaml": yaml.safe_dump(context_manifest, sort_keys=False),
    }
    for path, text in generated_context_files.items():
        _write_generated(path, text)

    atomic_write_text(outbox_dir / "README.md", _session_outbox_readme(actor_id, session_id, record["effective_node"]))
    bootstrap_text = _bootstrap_markdown(adapter, record, context_dir, outbox_dir)
    adapter_files = _copy_adapter_aliases(adapter, mount_path, bootstrap_text)

    record_dir = paths.root / "memory" / "generated" / "session-mounts" / _safe_fragment(actor_id)
    record_dir.mkdir(parents=True, exist_ok=True)
    materialization_record_path = record_dir / f"{session_id}.yaml"
    materialization_record = {
        "id": session_id,
        "type": "session_mount",
        "actor": actor_id,
        "adapter": adapter,
        "mount": str(mount_path),
        "workspace": str(paths.root),
        "effective_node": record["effective_node"],
        "signin_path": signin["signin_path"],
        "context_pack": signin["context_pack"],
        "manifest": str(context_dir / "manifest.yaml"),
        "created_at": utc_now_iso(),
        "status": "active",
    }
    atomic_write_text(materialization_record_path, yaml.safe_dump(materialization_record, sort_keys=False))

    changed_files = [
        _relative_or_external(path, paths.root)
        for path in [
            *generated_context_files.keys(),
            outbox_dir / "README.md",
            *adapter_files,
            materialization_record_path,
            actor_memory_path,
        ]
    ]
    op = OperationLog(paths).append(
        operation_type="session_start",
        actor=operator or actor_id,
        targets=[str(paths.root), actor_id, record["effective_node"], str(mount_path)],
        command="hive session start",
        changed_files=changed_files,
        changed_records=[{"id": session_id, "type": "session_mount", "actor": actor_id}],
        rollback={"supported": True, "strategy": "remove_mount_and_mark_signin_inactive"},
    )
    return {
        "ok": True,
        "session_id": session_id,
        "actor": actor_id,
        "adapter": adapter,
        "mount": str(mount_path),
        "workspace": str(paths.root),
        "effective_node": record["effective_node"],
        "signin": record,
        "signin_path": signin["signin_path"],
        "context_pack": signin["context_pack"],
        "context_dir": str(context_dir),
        "outbox": str(outbox_dir),
        "bootstrap_files": [str(path) for path in adapter_files],
        "finish_command": f"hive session finish {mount_path} --workspace {paths.root}",
        "operation": op.id,
    }


def _normalize_source_refs(value: Any, *, session_id: str, index: int) -> list[dict[str, Any]]:
    if value is None:
        return [
            {
                "source_id": f"session:{session_id}:delta:{index}",
                "locator": ".hive/outbox/memory-delta.jsonl",
            }
        ]
    refs = value if isinstance(value, list) else [value]
    normalized = []
    for ref in refs:
        if isinstance(ref, dict):
            source_id = str(ref.get("source_id") or ref.get("id") or f"session:{session_id}")
            item = {"source_id": source_id}
            if ref.get("locator"):
                item["locator"] = str(ref["locator"])
            normalized.append(item)
        else:
            normalized.append({"source_id": f"session:{session_id}", "locator": str(ref)})
    return normalized or [
        {"source_id": f"session:{session_id}:delta:{index}", "locator": ".hive/outbox/memory-delta.jsonl"}
    ]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.6
    return max(0.0, min(1.0, parsed))


def _normalize_delta(
    raw: dict[str, Any], *, index: int, session_id: str, actor_id: str, default_target: str
) -> dict[str, Any]:
    delta_type = str(raw.get("type") or "observation").strip() or "observation"
    summary = str(raw.get("summary") or raw.get("title") or "").strip()
    body = str(raw.get("body") or raw.get("details") or summary).strip()
    if not summary and body:
        summary = " ".join(body.split())[:160]
    if not summary:
        raise WorkspaceError(f"Memory delta line {index} is missing summary/body")
    target_scope = str(raw.get("target_scope") or raw.get("scope") or "private").strip()
    if target_scope not in DELTA_SCOPES:
        raise WorkspaceError(
            f"Memory delta line {index} has invalid target_scope {target_scope!r}; "
            f"expected one of {sorted(DELTA_SCOPES)}"
        )
    if target_scope == "private":
        target = str(raw.get("target") or actor_id)
    elif target_scope == "org_candidate":
        target = str(raw.get("target") or "org")
    else:
        target = str(raw.get("target") or default_target)
    return {
        "type": delta_type,
        "summary": summary,
        "body": body or summary,
        "target_scope": target_scope,
        "target": target,
        "confidence": _confidence(raw.get("confidence")),
        "sensitivity": str(raw.get("sensitivity") or "internal"),
        "source_refs": _normalize_source_refs(raw.get("source_refs"), session_id=session_id, index=index),
        "tags": _string_list(raw.get("tags")),
    }


def _read_deltas(outbox_dir: Path, *, session_id: str, actor_id: str, default_target: str) -> list[dict[str, Any]]:
    delta_path = outbox_dir / "memory-delta.jsonl"
    if delta_path.exists():
        deltas = []
        for index, line in enumerate(delta_path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise WorkspaceError(f"Invalid JSON in memory-delta.jsonl line {index}: {exc}") from exc
            if not isinstance(raw, dict):
                raise WorkspaceError(f"Memory delta line {index} must be a JSON object")
            deltas.append(
                _normalize_delta(
                    raw,
                    index=index,
                    session_id=session_id,
                    actor_id=actor_id,
                    default_target=default_target,
                )
            )
        return deltas
    summary_path = outbox_dir / "session-summary.md"
    summary = _read_text(summary_path)
    if summary:
        return [
            _normalize_delta(
                {
                    "type": "summary",
                    "summary": "Session summary",
                    "body": summary,
                    "target_scope": "private",
                    "source_refs": [str(summary_path)],
                    "tags": ["session-summary"],
                },
                index=1,
                session_id=session_id,
                actor_id=actor_id,
                default_target=default_target,
            )
        ]
    return []


def _canonical_session_dir(
    paths: WorkspacePaths, actor_id: str, session_id: str, personal_memory_home: str | None
) -> Path:
    if personal_memory_home:
        base = ensure_within_root(paths.root / personal_memory_home, paths.root)
    else:
        base = paths.root / "memory" / "records" / "agents" / _safe_fragment(actor_id)
    return base / "sessions" / _safe_fragment(session_id)


def _copy_outbox(outbox_dir: Path, session_dir: Path) -> list[Path]:
    copied: list[Path] = []
    if not outbox_dir.exists():
        return copied
    archive_dir = session_dir / "outbox"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(outbox_dir.rglob("*")):
        if source.is_dir():
            continue
        relative = source.relative_to(outbox_dir)
        target = archive_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def _delta_markdown(delta: dict[str, Any]) -> str:
    tags = ", ".join(delta.get("tags") or []) or "none"
    refs = ", ".join(
        ref.get("locator") or ref.get("source_id") or "unknown" for ref in delta.get("source_refs", [])
    )
    return (
        f"### {delta['summary']}\n\n"
        f"- Type: `{delta['type']}`\n"
        f"- Scope: `{delta['target_scope']}`\n"
        f"- Target: `{delta['target']}`\n"
        f"- Confidence: `{delta['confidence']}`\n"
        f"- Tags: {tags}\n"
        f"- Sources: {refs}\n\n"
        f"{delta['body'].strip()}\n"
    )


def _write_session_report(
    session_dir: Path,
    *,
    manifest: dict[str, Any],
    actor_id: str,
    deltas: list[dict[str, Any]],
) -> Path:
    parts = [
        f"# Hive Session: {manifest['session_id']}",
        f"Actor: `{actor_id}`",
        f"Effective node: `{manifest['effective_node']}`",
        f"Adapter: `{manifest.get('adapter', 'unknown')}`",
        f"Finished at: `{utc_now_iso()}`",
        "## Memory Deltas",
    ]
    if deltas:
        parts.extend(_delta_markdown(delta) for delta in deltas)
    else:
        parts.append("No durable memory deltas were submitted.")
    path = session_dir / "SESSION.md"
    atomic_write_text(path, "\n\n".join(parts).rstrip() + "\n")
    return path


def _append_private_memory(memory_path: Path, *, session_id: str, actor_id: str, deltas: list[dict[str, Any]]) -> bool:
    private = [delta for delta in deltas if delta["target_scope"] == "private"]
    if not private:
        return False
    current = _read_text(memory_path) or f"# Agent Memory: {actor_id}\n"
    addition = [f"## Session {session_id} — {utc_now_iso()}"]
    for delta in private:
        addition.append(
            f"- **{delta['type']}**: {delta['summary']} "
            f"(confidence: {delta['confidence']})\n\n"
            f"  {delta['body'].replace(chr(10), chr(10) + '  ')}"
        )
    atomic_write_text(memory_path, current.rstrip() + "\n\n" + "\n".join(addition).rstrip() + "\n")
    return True


def _write_normalized_jsonl(session_dir: Path, deltas: list[dict[str, Any]]) -> Path:
    path = session_dir / "memory-delta.normalized.jsonl"
    lines = [json.dumps(delta, sort_keys=True) for delta in deltas]
    atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""))
    return path


def _write_shared_delta_file(session_dir: Path, target: str, deltas: list[dict[str, Any]]) -> Path:
    path = session_dir / f"shared-{_safe_fragment(target)}.md"
    parts = [f"# Shared Candidate Memory: {target}"]
    parts.extend(_delta_markdown(delta) for delta in deltas)
    atomic_write_text(path, "\n\n".join(parts).rstrip() + "\n")
    return path


def finish_session(
    mount: Path,
    *,
    root: Path | None = None,
    actor: str | None = None,
    process: bool = True,
    propose: bool = True,
    compact_target: bool = False,
    llm_profile: str | None = None,
    credential: str | None = None,
) -> dict[str, Any]:
    mount_path = mount.expanduser().resolve()
    manifest_path = mount_path / ".hive" / "context" / "manifest.yaml"
    if not manifest_path.exists():
        raise WorkspaceError(f"Missing session manifest: {manifest_path}")
    manifest = _read_yaml(manifest_path)
    workspace_path = root.expanduser().resolve() if root else Path(str(manifest.get("workspace"))).expanduser().resolve()
    paths = WorkspacePaths(workspace_path)
    paths.require_workspace()

    session_id = str(manifest.get("session_id") or manifest.get("signin_id") or mount_path.name)
    actor_id = actor or str(manifest.get("actor") or "system:session")
    target = str(manifest.get("effective_node") or "org")
    outbox_dir = mount_path / ".hive" / "outbox"
    deltas = _read_deltas(outbox_dir, session_id=session_id, actor_id=actor_id, default_target=target)

    personal_home = str(manifest.get("personal_memory_home") or f"memory/records/agents/{_safe_fragment(actor_id)}/")
    session_dir = _canonical_session_dir(paths, actor_id, session_id, personal_home)
    session_dir.mkdir(parents=True, exist_ok=True)
    copied_files = _copy_outbox(outbox_dir, session_dir)
    normalized_path = _write_normalized_jsonl(session_dir, deltas)
    report_path = _write_session_report(session_dir, manifest=manifest, actor_id=actor_id, deltas=deltas)

    memory_path = _ensure_actor_memory(paths, actor_id, personal_home)
    private_updated = _append_private_memory(memory_path, session_id=session_id, actor_id=actor_id, deltas=deltas)

    shared_deltas = [delta for delta in deltas if delta["target_scope"] in {"node_candidate", "org_candidate"}]
    edge_deltas = [delta for delta in deltas if delta["target_scope"] == "edge_candidate"]
    imports: list[dict[str, Any]] = []
    import_results: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    shared_by_target: dict[str, list[dict[str, Any]]] = {}
    for delta in shared_deltas:
        shared_by_target.setdefault(str(delta["target"]), []).append(delta)
    for shared_target, target_deltas in sorted(shared_by_target.items()):
        source_path = _write_shared_delta_file(session_dir, shared_target, target_deltas)
        import_result = add_import(paths.root, shared_target, str(source_path), actor=actor_id)
        imports.append(import_result)
        if process:
            classify_result = classify_import(
                paths.root,
                import_result["import_id"],
                actor=actor_id,
                llm_profile=llm_profile,
                credential=credential,
            )
            compact_result = compact_import(
                paths.root,
                import_result["import_id"],
                actor=actor_id,
                llm_profile=llm_profile,
                credential=credential,
            )
            proposal_result = None
            if propose and compact_result.get("candidate_id"):
                proposal_result = propose_import(paths.root, import_result["import_id"], actor=actor_id)
                proposals.extend(proposal_result.get("proposals") or [])
            import_results.append(
                {
                    "target": shared_target,
                    "import": import_result,
                    "classification": classify_result,
                    "compaction": compact_result,
                    "proposal": proposal_result,
                }
            )
        else:
            import_results.append({"target": shared_target, "import": import_result})

    compaction_result = None
    if compact_target:
        compaction_result = compact_node(paths.root, target, actor=actor_id)

    status = "completed" if deltas else "no_changes"
    finish_record_path = session_dir / "finish.yaml"
    finish_record = {
        "id": session_id,
        "type": "session_finish",
        "actor": actor_id,
        "mount": str(mount_path),
        "workspace": str(paths.root),
        "effective_node": target,
        "finished_at": utc_now_iso(),
        "status": status,
        "delta_count": len(deltas),
        "private_delta_count": len([delta for delta in deltas if delta["target_scope"] == "private"]),
        "shared_delta_count": len(shared_deltas),
        "edge_delta_count": len(edge_deltas),
        "imports": [item["import_id"] for item in imports],
        "proposals": [item["id"] for item in proposals],
        "edge_delta_note": "edge_candidate deltas are collected but not promoted in this MVP" if edge_deltas else None,
    }
    atomic_write_text(finish_record_path, yaml.safe_dump(finish_record, sort_keys=False))

    changed = [normalized_path, report_path, finish_record_path, *copied_files]
    if private_updated:
        changed.append(memory_path)
    op = OperationLog(paths).append(
        operation_type="session_finish",
        actor=actor_id,
        targets=[str(paths.root), actor_id, target, str(mount_path)],
        command="hive session finish",
        changed_files=[_relative_or_external(path, paths.root) for path in changed],
        changed_records=[
            {"id": session_id, "type": "session_finish", "actor": actor_id},
            *[{"id": item["import_id"], "type": "import_item"} for item in imports],
            *[{"id": item["id"], "type": "promotion_proposal"} for item in proposals],
        ],
        rollback={"supported": True, "strategy": "restore_from_git_or_remove_session_artifacts"},
    )
    return {
        "ok": True,
        "status": status,
        "session_id": session_id,
        "actor": actor_id,
        "mount": str(mount_path),
        "workspace": str(paths.root),
        "effective_node": target,
        "session_dir": str(session_dir),
        "delta_count": len(deltas),
        "private_delta_count": finish_record["private_delta_count"],
        "shared_delta_count": finish_record["shared_delta_count"],
        "edge_delta_count": finish_record["edge_delta_count"],
        "private_memory": str(memory_path),
        "imports": import_results,
        "proposals": proposals,
        "compaction": compaction_result,
        "edge_delta_note": finish_record["edge_delta_note"],
        "operation": op.id,
    }
