from __future__ import annotations

from pathlib import Path

from . import simple_yaml as yaml

from .frontmatter import dump_markdown
from .fs import atomic_write_text
from .ids import new_id, utc_now_iso
from .models import WorkspaceConfig
from .operations import OperationLog
from .paths import REQUIRED_DIRS, WorkspacePaths, target_to_path_fragment
from .policies import ensure_operation_policy


def create_workspace(root: Path, *, fixture: str | None = None, force: bool = False) -> WorkspacePaths:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    paths = WorkspacePaths(root)
    paths.ensure_required_dirs()

    config = WorkspaceConfig(workspace_id=root.name or "hive-workspace")
    if paths.config.exists() and not force:
        # Existing workspace initialization should be idempotent.
        pass
    else:
        atomic_write_text(
            paths.config,
            yaml.safe_dump({"hive_workspace": config.model_dump(mode="json")}, sort_keys=False),
        )

    budget_path = paths.root / "policies" / "context-budget.yaml"
    if not budget_path.exists() or force:
        atomic_write_text(
            budget_path,
            yaml.safe_dump({"id": "context_budget_default", "budget_tokens": 24000, "warn_at_ratio": 0.8, "on_over_budget": "create_compaction_job"}, sort_keys=False),
        )
    operation_policy_path = ensure_operation_policy(paths, force=force)

    if fixture:
        if fixture != "basic-org":
            raise ValueError(f"Unknown fixture: {fixture}")
        write_basic_org_fixture(paths, force=force)

    OperationLog(paths).append(
        operation_type="workspace_init",
        actor="system:init",
        targets=[str(root)],
        command="hive init",
        changed_files=[
            {"path": str(paths.config.relative_to(root))},
            {"path": str(budget_path.relative_to(root))},
            {"path": str(operation_policy_path.relative_to(root))},
        ],
        rollback={"supported": False, "strategy": "backup_restore"},
    )
    return paths


def _node_path(paths: WorkspacePaths, node_id: str) -> Path:
    return paths.graph_nodes / target_to_path_fragment(node_id).with_suffix(".md")


def _edge_path(paths: WorkspacePaths, edge_id: str) -> Path:
    return paths.graph_edges / target_to_path_fragment(edge_id).with_suffix(".md")


def _node_memory_dir(paths: WorkspacePaths, node_id: str) -> Path:
    return paths.root / "memory" / "records" / "nodes" / target_to_path_fragment(node_id)


def _write_if_allowed(path: Path, text: str, *, force: bool) -> None:
    if path.exists() and not force:
        return
    atomic_write_text(path, text)


def write_basic_org_fixture(paths: WorkspacePaths, *, force: bool = False) -> None:
    now = utc_now_iso()
    nodes = [
        {
            "id": "org",
            "kind": "organization",
            "title": "Demo Organization",
            "parents": [],
            "owners": ["human:admin"],
        },
        {
            "id": "departments/engineering",
            "kind": "department",
            "title": "Engineering",
            "parents": ["org"],
            "owners": ["steward:engineering"],
        },
        {
            "id": "departments/marketing",
            "kind": "department",
            "title": "Marketing",
            "parents": ["org"],
            "owners": ["steward:marketing"],
        },
        {
            "id": "projects/project-launch-x",
            "kind": "project",
            "title": "Project Launch X",
            "parents": ["departments/engineering", "departments/marketing"],
            "owners": ["steward:engineering", "steward:marketing"],
        },
        {
            "id": "agents/codex-engineering-001",
            "kind": "agent",
            "title": "Codex Engineering Agent 001",
            "parents": ["departments/engineering"],
            "owners": ["steward:engineering"],
        },
    ]
    for node in nodes:
        node["status"] = "active"
        node["current_memory_file"] = (
            f"memory/records/nodes/{node['id']}/CURRENT.md"
        )
        node["history_memory_file"] = (
            f"memory/records/nodes/{node['id']}/HISTORY.md"
        )
        node["import_workspace"] = f"memory/imports/{node['id']}/"
        _write_if_allowed(
            _node_path(paths, node["id"]),
            dump_markdown(node, f"# {node['title']}\n\nGraph node for `{node['id']}`."),
            force=force,
        )
        mem_dir = _node_memory_dir(paths, node["id"])
        _write_if_allowed(
            mem_dir / "CURRENT.md",
            f"# Current Memory: {node['title']}\n\nThis is the current operating context for `{node['id']}`.\n",
            force=force,
        )
        _write_if_allowed(
            mem_dir / "HISTORY.md",
            f"# Historical Memory: {node['title']}\n\nHistorical context for `{node['id']}`.\n",
            force=force,
        )

    edge = {
        "id": "engineering__marketing__project-launch-x",
        "kind": "shared_project",
        "title": "Engineering / Marketing Launch X",
        "nodes": ["departments/engineering", "departments/marketing", "projects/project-launch-x"],
        "authority": "shared",
        "status": "active",
        "current_memory_file": "memory/records/edges/engineering__marketing__project-launch-x/CURRENT.md",
        "history_memory_file": "memory/records/edges/engineering__marketing__project-launch-x/HISTORY.md",
        "import_workspace": "memory/imports/edges/engineering__marketing__project-launch-x/",
    }
    _write_if_allowed(
        _edge_path(paths, edge["id"]),
        dump_markdown(edge, "# Engineering / Marketing Launch X\n\nShared launch context."),
        force=force,
    )
    edge_dir = paths.root / "memory" / "records" / "edges" / edge["id"]
    _write_if_allowed(edge_dir / "CURRENT.md", "# Current Edge Memory\n\nShared goals and handoffs.\n", force=force)
    _write_if_allowed(edge_dir / "HISTORY.md", "# Historical Edge Memory\n\nPast shared context.\n", force=force)

    raw_path = paths.root / "memory" / "raw" / "demo-source.md"
    _write_if_allowed(raw_path, "# Demo Source\n\nEngineering uses source-linked memory records.\n", force=force)

    record = {
        "id": "mem_demo_engineering_practice_001",
        "type": "procedure",
        "scope": "department",
        "node": "departments/engineering",
        "authority": "candidate",
        "confidence": 0.9,
        "sensitivity": "internal",
        "created_at": now,
        "created_by": "agent:codex-engineering-001",
        "source_refs": [{"source_id": "raw:demo-source", "locator": "memory/raw/demo-source.md"}],
        "tags": ["demo", "practice"],
    }
    _write_if_allowed(
        paths.root
        / "memory"
        / "records"
        / "nodes"
        / "departments"
        / "engineering"
        / "candidates"
        / "mem_demo_engineering_practice_001.md",
        dump_markdown(
            record,
            "Engineering memory records should include source references before promotion.",
        ),
        force=force,
    )

    import_root = paths.root / "memory" / "imports" / "departments" / "engineering"
    for child in ["inbox", "fetched", "normalized", "compacted", "candidates", "processed", "rejected", "items", "reports"]:
        (import_root / child).mkdir(parents=True, exist_ok=True)
    import_workspace = {
        "id": "import_workspace_departments_engineering",
        "target": "departments/engineering",
        "status": "active",
        "owner": "steward:engineering",
        "paths": {child: f"memory/imports/departments/engineering/{child}/" for child in ["inbox", "fetched", "normalized", "compacted", "candidates", "processed", "rejected", "items", "reports"]},
    }
    _write_if_allowed(
        import_root / "workspace.yaml",
        yaml.safe_dump(import_workspace, sort_keys=False),
        force=force,
    )
    import_item = {
        "id": "import_departments_engineering_demo_001",
        "workspace": "import_workspace_departments_engineering",
        "target": "departments/engineering",
        "source_type": "markdown",
        "state": "dropped",
        "created_at": now,
        "local_path": "memory/imports/departments/engineering/inbox/demo-source.md",
        "raw_preserved": True,
        "sensitivity": "internal",
    }
    _write_if_allowed(
        import_root / "inbox" / "demo-source.md",
        "# Imported Engineering Notes\n",
        force=force,
    )
    _write_if_allowed(import_root / "import-item-demo.yaml", yaml.safe_dump(import_item, sort_keys=False), force=force)

    assignment = {
        "id": "assignment_codex_engineering_001",
        "actor": "agent:codex-engineering-001",
        "actor_kind": "agent",
        "home_node": "departments/engineering",
        "role": "contributor",
        "status": "active",
        "assigned_at": now,
        "personal_memory_home": "memory/records/agents/codex-engineering-001/",
    }
    _write_if_allowed(
        paths.root / "org" / "assignments" / "assignment_codex_engineering_001.yaml",
        yaml.safe_dump(assignment, sort_keys=False),
        force=force,
    )
    signin = {
        "id": "signin_demo_001",
        "actor": "agent:codex-engineering-001",
        "instance": "agent-instance:demo-run",
        "assignment": "assignment_codex_engineering_001",
        "effective_node": "departments/engineering",
        "role": "contributor",
        "started_at": now,
        "status": "active",
        "context_pack": "memory/generated/context-packs/nodes/departments/engineering/PACK.md",
        "loaded_context_packs": [],
    }
    _write_if_allowed(paths.root / "org" / "signins" / "signin_demo_001.yaml", yaml.safe_dump(signin, sort_keys=False), force=force)

    proposal = {
        "id": "promotion_demo_001",
        "source_record": "mem_demo_engineering_practice_001",
        "source_scope": "departments/engineering/candidates",
        "target_scope": "departments/engineering/published",
        "promotion_type": "candidate_to_department",
        "rationale": "Demo source-linked reusable practice.",
        "status": "candidate",
    }
    _write_if_allowed(paths.root / "memory" / "proposals" / "promotion_demo_001.yaml", yaml.safe_dump(proposal, sort_keys=False), force=force)

    job = {
        "id": "job_demo_node_compact_001",
        "type": "node_compact",
        "target": "departments/engineering",
        "status": "pending",
        "reason": "Demo compaction job.",
        "created_at": now,
        "inputs": {"since": "beginning"},
    }
    _write_if_allowed(paths.root / "memory" / "jobs" / "pending" / "job_demo_node_compact_001.yaml", yaml.safe_dump(job, sort_keys=False), force=force)

    invalidation = {
        "id": "ctxinv_demo_001",
        "target": "departments/engineering",
        "reason": "fixture_created",
        "created_at": now,
        "severity": "low",
        "affected_context_packs": [],
        "affected_targets": ["departments/engineering", "agents/codex-engineering-001"],
        "status": "open",
    }
    _write_if_allowed(paths.root / "memory" / "state" / "context-dirty" / "ctxinv_demo_001.yaml", yaml.safe_dump(invalidation, sort_keys=False), force=force)

    archive = {
        "id": "archive_demo_001",
        "target": "agents/retired-demo-agent",
        "target_type": "node",
        "reason": "Demo archived agent.",
        "archived_at": now,
        "archived_by": "human:admin",
        "status": "archived",
        "excluded_from_startup_context": True,
    }
    _write_if_allowed(paths.root / "memory" / "audit" / "archive_demo_001.yaml", yaml.safe_dump(archive, sort_keys=False), force=force)
