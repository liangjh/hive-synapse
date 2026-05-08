from __future__ import annotations

from pathlib import Path
from typing import Any

from .frontmatter import dump_markdown, read_markdown
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths, target_to_path_fragment

DEFAULT_SECTIONS = ["mission", "goals", "tone", "soul", "principles", "notes"]
SECTION_TITLES = {
    "mission": "Mission",
    "goals": "Goals",
    "tone": "Tone",
    "soul": "Soul",
    "principles": "Operating Principles",
    "notes": "Notes",
}


def charter_path(paths: WorkspacePaths, node_id: str) -> Path:
    return paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(node_id) / "CHARTER.md"


def charter_history_path(paths: WorkspacePaths, node_id: str) -> Path:
    return paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(node_id) / "CHARTER_HISTORY.md"


def default_charter_body(title: str, node_id: str) -> str:
    return "\n\n".join(
        [
            f"# Charter: {title}",
            "## Mission\n\nArticulate why this node exists and what it is accountable for.",
            "## Goals\n\n- Maintain a concise current list of goals and priorities.",
            "## Tone\n\nDescribe the communication style this node should preserve.",
            "## Soul\n\nCapture the durable personality, values, and cultural intent for this node.",
            "## Operating Principles\n\n- Prefer source-backed updates and explicit tradeoffs.",
            f"## Notes\n\nThis charter applies to `{node_id}` and is inherited by descendant context packs.",
        ]
    ) + "\n"


def _frontmatter(node_id: str, *, actor: str, title: str, source_refs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "id": f"charter_{node_id.replace('/', '_')}",
        "type": "charter",
        "scope": "node",
        "node": node_id,
        "authority": "charter",
        "status": "active",
        "created_at": now,
        "created_by": actor,
        "updated_at": now,
        "updated_by": actor,
        "title": title,
        "sections": DEFAULT_SECTIONS,
        "source_refs": source_refs or [],
        "tags": ["charter", "goals", "mission", "tone", "soul"],
    }


def ensure_charter(root: Path, node_id: str, *, actor: str, title: str | None = None) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    path = charter_path(paths, node_id)
    if path.exists():
        doc = read_markdown(path)
        return {"ok": True, "created": False, "path": str(path), "frontmatter": doc.frontmatter, "body": doc.body}
    title = title or node_id.split("/")[-1].replace("-", " ").title()
    frontmatter = _frontmatter(node_id, actor=actor, title=title)
    body = default_charter_body(title, node_id)
    atomic_write_text(path, dump_markdown(frontmatter, body))
    history = charter_history_path(paths, node_id)
    atomic_write_text(
        history,
        f"# Charter History: {title}\n\n## {frontmatter['created_at']} — created by {actor}\n\nInitial charter created.\n",
    )
    op = OperationLog(paths).append(
        operation_type="charter_init",
        actor=actor,
        targets=[str(paths.root), node_id],
        command="hive charter init",
        changed_files=[
            {"path": str(path.relative_to(paths.root))},
            {"path": str(history.relative_to(paths.root))},
        ],
        changed_records=[{"id": frontmatter["id"], "type": "charter"}],
        rollback={"supported": True, "strategy": "remove_created_charter"},
    )
    return {"ok": True, "created": True, "path": str(path), "frontmatter": frontmatter, "body": body, "operation": op.id}


def read_charter(root: Path, node_id: str) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    path = charter_path(paths, node_id)
    if not path.exists():
        return {"ok": False, "error": "charter.not_found", "node": node_id, "path": str(path)}
    doc = read_markdown(path)
    return {"ok": True, "node": node_id, "path": str(path), "frontmatter": doc.frontmatter, "body": doc.body}


def list_charters(root: Path) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    charters = []
    base = paths.root / "memory" / "records" / "nodes"
    for path in sorted(base.rglob("CHARTER.md")):
        doc = read_markdown(path)
        charters.append({"path": str(path.relative_to(paths.root)), "node": doc.frontmatter.get("node"), "title": doc.frontmatter.get("title")})
    return {"ok": True, "charters": charters}


def _replace_section(body: str, section: str, new_text: str, *, mode: str) -> str:
    title = SECTION_TITLES.get(section, section.replace("_", " ").title())
    heading = f"## {title}"
    lines = body.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().lower() == heading.lower():
            start = index
            break
    if start is None:
        addition = f"\n\n{heading}\n\n{new_text.strip()}\n"
        return body.rstrip() + addition
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    existing = "\n".join(lines[start + 1:end]).strip()
    if mode == "replace":
        section_body = new_text.strip()
    elif mode == "append":
        section_body = (existing + "\n\n" + new_text.strip()).strip() if existing else new_text.strip()
    else:
        raise ValueError("mode must be append or replace")
    replacement = [heading, "", section_body]
    return "\n".join([*lines[:start], *replacement, *lines[end:]]).rstrip() + "\n"


def update_charter(
    root: Path,
    node_id: str,
    *,
    section: str,
    text: str,
    mode: str,
    actor: str,
    source_ref: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    ensured = ensure_charter(paths.root, node_id, actor=actor)
    path = Path(ensured["path"])
    doc = read_markdown(path)
    source_refs = list(doc.frontmatter.get("source_refs") or [])
    if source_ref:
        source_refs.append({"source_id": f"manual:{new_id('source')}", "locator": source_ref})
    frontmatter = dict(doc.frontmatter)
    frontmatter.update(
        {
            "updated_at": utc_now_iso(),
            "updated_by": actor,
            "source_refs": source_refs,
            "last_update": {"section": section, "mode": mode, "actor": actor},
        }
    )
    body = _replace_section(doc.body, section, text, mode=mode)
    atomic_write_text(path, dump_markdown(frontmatter, body))
    history_path = charter_history_path(paths, node_id)
    existing_history = history_path.read_text(encoding="utf-8") if history_path.exists() else f"# Charter History: {node_id}\n"
    history_entry = (
        f"\n## {frontmatter['updated_at']} — {mode} `{section}` by {actor}\n\n"
        f"{text.strip()}\n"
    )
    atomic_write_text(history_path, existing_history.rstrip() + history_entry)
    op = OperationLog(paths).append(
        operation_type="charter_update",
        actor=actor,
        targets=[str(paths.root), node_id],
        command="hive charter update",
        changed_files=[
            {"path": str(path.relative_to(paths.root))},
            {"path": str(history_path.relative_to(paths.root))},
        ],
        changed_records=[{"id": frontmatter["id"], "type": "charter", "section": section}],
        rollback={"supported": True, "strategy": "restore_charter_from_backup_or_history"},
    )
    from .context import invalidate_context

    invalidation = invalidate_context(
        paths.root,
        node_id,
        reason=f"charter_update:{section}",
        actor=actor,
    )
    return {
        "ok": True,
        "node": node_id,
        "path": str(path),
        "history_path": str(history_path),
        "frontmatter": frontmatter,
        "operation": op.id,
        "invalidation": invalidation.get("invalidation") or invalidation.get("observation"),
    }
