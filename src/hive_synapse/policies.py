from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .errors import WorkspaceError
from .fs import atomic_write_text
from .paths import WorkspacePaths, target_to_path_fragment

OPERATION_POLICY_FILE = "operations.yaml"


def default_operation_policy() -> dict[str, Any]:
    return {
        "id": "operations_default",
        "version": "0.1.0",
        "description": "Workspace-level defaults for automated memory maintenance.",
        "precedence": [
            "runtime_defaults",
            "workspace_policy",
            "node_policy",
            "explicit_command_flags",
        ],
        "operation_policies": {
            "context_invalidation": {
                "mode": "observe",
                "emit_dirty_markers": False,
                "manual_commands_apply": True,
                "always_emit_reasons": [
                    "runtime_schema_changed",
                    "policy_changed",
                    "permission_changed",
                ],
            },
            "compaction": {
                "mode": "threshold",
                "on_over_budget": "create_compaction_job",
                "warn_at_ratio": 0.8,
                "threshold_ratio": 1.0,
            },
            "promotion": {
                "sweep_mode": "manual",
                "create_proposals_by_default": False,
            },
            "watchdog": {
                "mode": "report_only",
                "enqueue_remediation": False,
            },
            "import_sync": {
                "mode": "manual",
                "recursive_default": False,
                "poll_interval_minutes": None,
            },
            "archive": {
                "mode": "manual",
                "enqueue_compaction": False,
            },
        },
    }


def operation_policy_path(paths: WorkspacePaths) -> Path:
    return paths.root / "policies" / OPERATION_POLICY_FILE


def node_policy_path(paths: WorkspacePaths, target: str) -> Path:
    return paths.root / "policies" / "nodes" / target_to_path_fragment(target).with_suffix(".yaml")


def ensure_operation_policy(paths: WorkspacePaths, *, force: bool = False) -> Path:
    path = operation_policy_path(paths)
    if force or not path.exists():
        atomic_write_text(path, yaml.safe_dump(default_operation_policy(), sort_keys=False))
    return path


def load_operation_policy(
    root: Path | WorkspacePaths, *, target: str | None = None
) -> dict[str, Any]:
    paths = _coerce_paths(root)
    policy = default_operation_policy()
    workspace_path = operation_policy_path(paths)
    if workspace_path.exists():
        policy = _deep_merge(policy, _load_mapping(workspace_path))
    if target:
        node_path = node_policy_path(paths, target)
        if node_path.exists():
            node_policy = _load_mapping(node_path)
            override = node_policy.get("operation_policies")
            if isinstance(override, dict):
                policy = _deep_merge(policy, {"operation_policies": override})
    return policy


def operation_policy(
    root: Path | WorkspacePaths,
    name: str,
    *,
    target: str | None = None,
) -> dict[str, Any]:
    policies = load_operation_policy(root, target=target).get("operation_policies")
    if not isinstance(policies, dict):
        return {}
    selected = policies.get(name) or {}
    return dict(selected) if isinstance(selected, dict) else {}


def explain_operation_policy(root: Path, *, target: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    workspace_path = operation_policy_path(paths)
    node_path = node_policy_path(paths, target) if target else None
    return {
        "ok": True,
        "path": str(workspace_path),
        "exists": workspace_path.exists(),
        "target": target,
        "node_policy_path": str(node_path) if node_path else None,
        "node_policy_exists": bool(node_path and node_path.exists()),
        "policy": load_operation_policy(paths, target=target),
    }


def context_invalidation_decision(
    root: Path | WorkspacePaths,
    *,
    target: str,
    reason: str,
    respect_policy: bool = True,
) -> dict[str, Any]:
    policy = operation_policy(root, "context_invalidation", target=target)
    mode = str(policy.get("mode", "observe")).lower()
    emit = bool(policy.get("emit_dirty_markers", False))
    reason_key = reason.split(":", 1)[0]
    always_emit = {str(item) for item in _as_list(policy.get("always_emit_reasons"))}

    if not respect_policy:
        decision = "manual_command"
        emit_dirty_marker = True
    elif reason in always_emit or reason_key in always_emit:
        decision = "always_emit_reason"
        emit_dirty_marker = True
    elif mode in {"strict", "auto", "automatic"}:
        decision = "automatic"
        emit_dirty_marker = True
    elif mode in {"off", "disabled"}:
        decision = "disabled"
        emit_dirty_marker = False
    else:
        decision = "policy_emit" if emit else "observed"
        emit_dirty_marker = emit

    return {
        "mode": mode,
        "respect_policy": respect_policy,
        "emit_dirty_marker": emit_dirty_marker,
        "decision": decision,
        "reason_key": reason_key,
        "policy": policy,
    }


def _coerce_paths(root: Path | WorkspacePaths) -> WorkspacePaths:
    if isinstance(root, WorkspacePaths):
        return root
    return WorkspacePaths(root.resolve())


def _load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise WorkspaceError(f"Expected YAML mapping: {path}")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
