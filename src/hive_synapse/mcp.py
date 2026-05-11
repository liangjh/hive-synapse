from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .context import compile_context_pack, context_impact
from .guardrails import dirty_markers_for_target
from .imports import add_import
from .jobs import enqueue_job
from .paths import WorkspacePaths
from .validator import validate_workspace


def _workspace_from_args(args: dict[str, Any]) -> Path:
    return Path(str(args.get("workspace", "."))).resolve()


def get_context_pack(args: dict[str, Any]) -> dict[str, Any]:
    workspace = _workspace_from_args(args)
    target = str(args["target"])
    pack_path, manifest_path = compile_context_pack(workspace, target)
    return {
        "ok": True,
        "target": target,
        "pack_path": str(pack_path),
        "manifest_path": str(manifest_path),
        "pack": pack_path.read_text(encoding="utf-8"),
    }


def validate(args: dict[str, Any]) -> dict[str, Any]:
    return validate_workspace(_workspace_from_args(args)).model_dump(mode="json")


def context_status(args: dict[str, Any]) -> dict[str, Any]:
    workspace = _workspace_from_args(args)
    target = str(args["target"])
    paths = WorkspacePaths(workspace)
    paths.require_workspace()
    markers = dirty_markers_for_target(paths, target)
    return {
        "ok": not markers,
        "target": target,
        "stale": bool(markers),
        "dirty_markers": [str(path.relative_to(paths.root)) for path in markers],
    }


def import_add(args: dict[str, Any]) -> dict[str, Any]:
    return add_import(
        _workspace_from_args(args),
        str(args["target"]),
        str(args["source"]),
        actor=str(args.get("actor", "mcp:client")),
    )


def job_enqueue(args: dict[str, Any]) -> dict[str, Any]:
    return enqueue_job(
        _workspace_from_args(args),
        str(args["type"]),
        str(args["target"]),
        reason=str(args.get("reason", "mcp request")),
        actor=str(args.get("actor", "mcp:client")),
    )


def memory_search(args: dict[str, Any]) -> dict[str, Any]:
    workspace = _workspace_from_args(args)
    query = str(args.get("query", "")).lower()
    limit = int(args.get("limit", 20))
    matches: list[dict[str, Any]] = []
    for path in sorted((workspace / "memory" / "records").rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not query or query in text.lower():
            matches.append({"path": str(path.relative_to(workspace)), "snippet": text[:300]})
        if len(matches) >= limit:
            break
    return {"ok": True, "query": query, "matches": matches}


def graph_impact(args: dict[str, Any]) -> dict[str, Any]:
    return context_impact(_workspace_from_args(args), str(args["target"]))


TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "get_context_pack": get_context_pack,
    "validate_workspace": validate,
    "context_status": context_status,
    "import_add": import_add,
    "job_enqueue": job_enqueue,
    "memory_search": memory_search,
    "graph_impact": graph_impact,
}

TOOL_DESCRIPTIONS = {
    "get_context_pack": "Compile and return a generated context pack for a target node.",
    "validate_workspace": "Validate workspace graph, records, guardrails, and generated artifacts.",
    "context_status": "Check whether a target has dirty context markers.",
    "import_add": "Stage a local file or text import as evidence/candidate input.",
    "job_enqueue": "Enqueue a filesystem job for later processing.",
    "memory_search": "Search Markdown memory records with deterministic substring matching.",
    "graph_impact": "Compute descendants, edges, actors, and context packs impacted by a target.",
}


def list_tools() -> dict[str, Any]:
    return {
        "ok": True,
        "tools": [{"name": name, "description": TOOL_DESCRIPTIONS[name]} for name in sorted(TOOLS)],
    }


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return {"ok": False, "error": "mcp.tool_not_found", "tool": name}
    return TOOLS[name](arguments)


def serve_json_lines() -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("method") == "tools/list":
                response = list_tools()
            elif request.get("method") == "tools/call":
                params = request.get("params") or {}
                response = call_tool(str(params.get("name")), dict(params.get("arguments") or {}))
            else:
                response = {
                    "ok": False,
                    "error": "mcp.method_not_supported",
                    "method": request.get("method"),
                }
        except Exception as exc:
            response = {"ok": False, "error": exc.__class__.__name__, "message": str(exc)}
        sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0
