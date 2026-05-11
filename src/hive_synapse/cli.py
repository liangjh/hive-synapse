from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .backup import create_backup, rollback_preview
from .charters import ensure_charter, list_charters, read_charter, update_charter
from .compaction import compact_edge, compact_node
from .connectors import list_connectors
from .context import compile_context_pack, context_impact, invalidate_context
from .edges import archive_edge, create_edge as create_graph_edge, list_edges, restore_edge
from .errors import HiveError
from .guardrails import dirty_markers_for_target
from .imports import add_import, classify_import, compact_import, fetch_import, propose_import
from .archive import archive_sweep
from .jobs import claim_job, complete_job, enqueue_job, fail_job, list_jobs, run_next_job
from .llm import (
    add_credential,
    add_profile,
    assign_credential,
    assign_profile,
    ensure_llm_policy,
    list_llm_config,
    list_providers,
)
from .mcp import call_tool, list_tools, serve_json_lines
from .sessions import refresh_signin, sign_in_actor
from .lifecycle import archive_actor, archive_node, assign_actor, create_node, move_node, restore_node
from .promotion import apply_proposal, list_proposals, reject_proposal, review_proposal, sweep_promotability
from .skills import list_skills, register_skill, update_skill_status
from .upgrade import doctor, list_migrations, migration_apply, migration_dry_run, template_apply_new, template_diff
from .watchdog import watchdog_report
from .operations import list_operations, show_operation
from .paths import WorkspacePaths
from .persistence import list_backends
from .scheduler import install_scheduler
from .policies import explain_operation_policy
from .workspace import create_workspace
from .validator import validate_workspace


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _cmd_init(args: argparse.Namespace) -> int:
    paths = create_workspace(Path(args.path), fixture=args.fixture, force=args.force)
    result = {"ok": True, "workspace": str(paths.root), "fixture": args.fixture}
    if args.json:
        _print_json(result)
    else:
        print(f"Initialized workspace: {paths.root}")
    return 0


def _add_llm_selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--llm-profile", help="LLM profile id to use for this operation")
    parser.add_argument("--credential", help="Credential id to use for this operation, or 'none'")


def _cmd_llm_init(args: argparse.Namespace) -> int:
    result = ensure_llm_policy(Path(args.workspace), actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print("Initialized LLM policy files")
        if result.get("operation"):
            print(f"Operation: {result['operation']}")
    return 0


def _cmd_llm_providers(args: argparse.Namespace) -> int:
    result = list_providers()
    if args.json:
        _print_json(result)
    else:
        for provider in result["providers"]:
            dependency = f" dependency={provider['requires_dependency']}" if provider.get("requires_dependency") else ""
            network = "network" if provider.get("network") else "offline"
            print(f"{provider['name']} ({network}{dependency}): {provider['description']}")
    return 0


def _cmd_llm_config(args: argparse.Namespace) -> int:
    result = list_llm_config(Path(args.workspace))
    if args.json:
        _print_json(result)
    else:
        policy = result["policy"]
        registry = result["credentials"]
        print(f"Enabled: {policy.get('enabled')}")
        print(f"Organization profile: {policy.get('organization_profile')}")
        print(f"Organization credential: {registry.get('organization_credential')}")
        print(f"Profiles: {len(policy.get('profiles') or [])}")
        print(f"Credentials: {len(registry.get('credentials') or [])}")
    return 0


def _cmd_llm_credential_add(args: argparse.Namespace) -> int:
    result = add_credential(
        Path(args.workspace),
        args.credential_id,
        provider=args.provider,
        api_key_env=args.api_key_env,
        actor=args.actor,
        assign_actor=args.assign_actor,
        organization_default=args.organization_default,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Upserted LLM credential: {result['credential']['id']}")
    return 0


def _cmd_llm_credential_assign(args: argparse.Namespace) -> int:
    result = assign_credential(
        Path(args.workspace),
        args.credential_id,
        actor=args.actor,
        assign_actor=args.assign_actor,
        organization_default=args.organization_default,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Assigned LLM credential: {args.credential_id}")
    return 0


def _cmd_llm_profile_add(args: argparse.Namespace) -> int:
    try:
        command = json.loads(args.command_json) if args.command_json else None
    except json.JSONDecodeError as exc:
        raise HiveError("--command-json must be a JSON array of command argv strings") from exc
    if command is not None and not isinstance(command, list):
        raise HiveError("--command-json must be a JSON array of command argv strings")
    result = add_profile(
        Path(args.workspace),
        args.profile_id,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        credential=args.credential,
        command=command,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        actor=args.actor,
        assign_actor=args.assign_actor,
        organization_default=args.organization_default,
        enable=args.enable,
        allow_network_models=args.allow_network_models,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Upserted LLM profile: {result['profile']['id']}")
    return 0


def _cmd_llm_profile_assign(args: argparse.Namespace) -> int:
    result = assign_profile(
        Path(args.workspace),
        args.profile_id,
        actor=args.actor,
        assign_actor=args.assign_actor,
        organization_default=args.organization_default,
        enable=args.enable,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Assigned LLM profile: {args.profile_id}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    report = validate_workspace(Path(args.path))
    data = report.model_dump(mode="json")
    if args.json:
        _print_json(data)
    else:
        if report.ok:
            print("Validation passed")
        else:
            print("Validation failed")
            for issue in report.errors:
                location = f" ({issue.path})" if issue.path else ""
                print(f"ERROR {issue.code}: {issue.message}{location}", file=sys.stderr)
        for issue in report.warnings:
            location = f" ({issue.path})" if issue.path else ""
            print(f"WARNING {issue.code}: {issue.message}{location}", file=sys.stderr)
    return 0 if report.ok else 1



def _cmd_charter_init(args: argparse.Namespace) -> int:
    result = ensure_charter(Path(args.workspace), args.target, actor=args.actor, title=args.title)
    if args.json:
        _print_json(result)
    else:
        action = "Created" if result.get("created") else "Found"
        print(f"{action} charter: {result['path']}")
    return 0


def _cmd_charter_show(args: argparse.Namespace) -> int:
    result = read_charter(Path(args.workspace), args.target)
    if args.json:
        _print_json(result)
    else:
        if not result.get("ok"):
            print(result.get("error", "charter error"), file=sys.stderr)
            return 1
        print(result["body"].rstrip())
    return 0 if result.get("ok") else 1


def _cmd_charter_list(args: argparse.Namespace) -> int:
    result = list_charters(Path(args.workspace))
    if args.json:
        _print_json(result)
    else:
        for charter in result["charters"]:
            print(f"{charter.get('node')} {charter.get('path')}")
    return 0


def _cmd_charter_update(args: argparse.Namespace) -> int:
    result = update_charter(
        Path(args.workspace),
        args.target,
        section=args.section,
        text=args.text,
        mode=args.mode,
        actor=args.actor,
        source_ref=args.source_ref,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Updated charter {args.target}: {args.section}")
    return 0

def _cmd_context_compile(args: argparse.Namespace) -> int:
    pack_path, manifest_path = compile_context_pack(Path(args.workspace), args.target)
    result = {"ok": True, "pack": str(pack_path), "manifest": str(manifest_path), "target": args.target}
    if args.json:
        _print_json(result)
    else:
        print(f"Compiled context pack: {pack_path}")
        print(f"Manifest: {manifest_path}")
    return 0



def _cmd_context_status(args: argparse.Namespace) -> int:
    paths = WorkspacePaths(Path(args.workspace).resolve())
    paths.require_workspace()
    markers = dirty_markers_for_target(paths, args.target)
    result = {
        "ok": not markers,
        "target": args.target,
        "stale": bool(markers),
        "dirty_markers": [str(path.relative_to(paths.root)) for path in markers],
    }
    if args.json:
        _print_json(result)
    else:
        if markers:
            print(f"Context stale for {args.target}")
            for marker in markers:
                print(f"- {marker.relative_to(paths.root)}")
        else:
            print(f"Context fresh for {args.target}")
    return 1 if markers else 0



def _cmd_context_impacted(args: argparse.Namespace) -> int:
    result = context_impact(Path(args.workspace), args.target)
    if args.json:
        _print_json(result)
    else:
        print(f"Impact for {args.target}")
        for key in ["descendants", "connected_edges", "assigned_actors", "affected_targets"]:
            print(f"{key}:")
            for item in result.get(key, []):
                print(f"- {item}")
    return 0


def _cmd_context_invalidate(args: argparse.Namespace) -> int:
    result = invalidate_context(
        Path(args.workspace),
        args.target,
        reason=args.reason,
        actor=args.actor,
        respect_policy=args.respect_policy,
    )
    if args.json:
        _print_json(result)
    else:
        if result.get("invalidation"):
            print(f"Invalidated context for {args.target}: {result['invalidation']['id']}")
        else:
            policy = result.get("policy", {})
            print(f"Observed context change for {args.target}: {policy.get('decision', 'policy')}")
    return 0


def _cmd_import_add(args: argparse.Namespace) -> int:
    result = add_import(Path(args.workspace), args.target, args.source, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Created import item: {result['import_id']}")
    return 0


def _cmd_import_fetch(args: argparse.Namespace) -> int:
    result = fetch_import(Path(args.workspace), args.target, args.url, connector=args.connector, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Created URL import item: {result['import_id']}")
    return 0


def _cmd_import_classify(args: argparse.Namespace) -> int:
    result = classify_import(
        Path(args.workspace),
        args.import_id,
        sensitivity=args.sensitivity,
        actor=args.actor,
        llm_profile=args.llm_profile,
        credential=args.credential,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Classified import item: {result['import_id']}")
    return 0


def _cmd_import_compact(args: argparse.Namespace) -> int:
    result = compact_import(
        Path(args.workspace),
        args.import_id,
        actor=args.actor,
        llm_profile=args.llm_profile,
        credential=args.credential,
    )
    if args.json:
        _print_json(result)
    else:
        if result.get("candidate_id"):
            print(f"Created candidate: {result['candidate_id']}")
        else:
            print(f"Import compact result: {result.get('status')}")
    return 0


def _cmd_import_propose(args: argparse.Namespace) -> int:
    result = propose_import(Path(args.workspace), args.import_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Created {len(result['proposals'])} proposal(s) for {result['import_id']}")
    return 0


def _cmd_promote_list(args: argparse.Namespace) -> int:
    result = list_proposals(Path(args.workspace), status=args.status)
    if args.json:
        _print_json(result)
    else:
        for proposal in result["proposals"]:
            print(f"{proposal['id']} {proposal.get('status')} {proposal.get('source_record')}")
    return 0


def _cmd_promote_review(args: argparse.Namespace) -> int:
    result = review_proposal(
        Path(args.workspace),
        args.proposal_id,
        decision=args.decision,
        actor=args.actor,
        rationale=args.rationale,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Reviewed proposal {args.proposal_id}: {args.decision}")
    return 0


def _cmd_promote_apply(args: argparse.Namespace) -> int:
    result = apply_proposal(Path(args.workspace), args.proposal_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Applied proposal {args.proposal_id}")
        print(f"Published: {result['published_path']}")
    return 0


def _cmd_promote_reject(args: argparse.Namespace) -> int:
    result = reject_proposal(Path(args.workspace), args.proposal_id, actor=args.actor, rationale=args.rationale)
    if args.json:
        _print_json(result)
    else:
        print(f"Rejected proposal {args.proposal_id}")
    return 0


def _cmd_promote_sweep(args: argparse.Namespace) -> int:
    result = sweep_promotability(
        Path(args.workspace),
        create_proposals=args.create_proposals,
        actor=args.actor,
        llm_profile=args.llm_profile,
        credential=args.credential,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Promotable: {len(result['promotable'])}")
        print(f"Needs more evidence: {len(result['needs_more_evidence'])}")
        print(f"Conflicts detected: {len(result['conflicts_detected'])}")
        print(f"Created proposals: {len(result['created_proposals'])}")
    return 0


def _cmd_job_enqueue(args: argparse.Namespace) -> int:
    result = enqueue_job(Path(args.workspace), args.type, args.target, reason=args.reason, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Enqueued job: {result['job']['id']}")
    return 0


def _cmd_job_list(args: argparse.Namespace) -> int:
    result = list_jobs(Path(args.workspace), status=args.status)
    if args.json:
        _print_json(result)
    else:
        for job in result["jobs"]:
            print(f"{job['id']} {job.get('queue')} {job.get('type')} {job.get('target')}")
    return 0


def _cmd_job_claim(args: argparse.Namespace) -> int:
    result = claim_job(Path(args.workspace), runner=args.runner)
    if args.json:
        _print_json(result)
    else:
        if result.get("job"):
            print(f"Claimed job: {result['job']['id']}")
        else:
            print("No jobs")
    return 0


def _cmd_job_complete(args: argparse.Namespace) -> int:
    result = complete_job(Path(args.workspace), args.job_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Completed job: {args.job_id}")
    return 0


def _cmd_job_fail(args: argparse.Namespace) -> int:
    result = fail_job(Path(args.workspace), args.job_id, reason=args.reason, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Failed job: {args.job_id}")
    return 0


def _cmd_job_run(args: argparse.Namespace) -> int:
    result = run_next_job(Path(args.workspace), runner=args.runner)
    if args.json:
        _print_json(result)
    else:
        if result.get("job"):
            print(f"Ran job: {result['job']['id']}")
        else:
            print("No jobs")
    return 0


def _cmd_job_watchdog(args: argparse.Namespace) -> int:
    result = watchdog_report(Path(args.workspace), enqueue=args.enqueue, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Watchdog findings: {result['finding_count']}")
        print(result["markdown_path"])
    return 0


def _cmd_node_create(args: argparse.Namespace) -> int:
    result = create_node(Path(args.workspace), args.node_id, kind=args.kind, title=args.title, parents=args.parent, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Created node: {args.node_id}")
    return 0


def _cmd_node_move(args: argparse.Namespace) -> int:
    result = move_node(Path(args.workspace), args.node_id, parents=args.parent, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Moved node: {args.node_id}")
    return 0


def _cmd_node_archive(args: argparse.Namespace) -> int:
    result = archive_node(Path(args.workspace), args.node_id, actor=args.actor, reason=args.reason, defer_compaction=args.defer_compaction)
    if args.json:
        _print_json(result)
    else:
        print(f"Archived node: {args.node_id}")
    return 0


def _cmd_node_restore(args: argparse.Namespace) -> int:
    result = restore_node(Path(args.workspace), args.node_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Restored node: {args.node_id}")
    return 0


def _cmd_node_compact(args: argparse.Namespace) -> int:
    result = compact_node(Path(args.workspace), args.node_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Compacted node: {args.node_id}")
        print(result["brief"])
    return 0


def _cmd_edge_create(args: argparse.Namespace) -> int:
    result = create_graph_edge(
        Path(args.workspace),
        args.edge_id,
        kind=args.kind,
        title=args.title,
        nodes=args.node,
        actor=args.actor,
        summary=args.summary,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Created edge: {args.edge_id}")
    return 0


def _cmd_edge_list(args: argparse.Namespace) -> int:
    result = list_edges(Path(args.workspace), node=args.node, include_archived=args.include_archived)
    if args.json:
        _print_json(result)
    else:
        for edge in result["edges"]:
            print(f"{edge['id']} {edge.get('status')} {', '.join(edge.get('nodes', []))}")
    return 0


def _cmd_edge_archive(args: argparse.Namespace) -> int:
    result = archive_edge(Path(args.workspace), args.edge_id, actor=args.actor, reason=args.reason)
    if args.json:
        _print_json(result)
    else:
        print(f"Archived edge: {args.edge_id}")
    return 0


def _cmd_edge_restore(args: argparse.Namespace) -> int:
    result = restore_edge(Path(args.workspace), args.edge_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Restored edge: {args.edge_id}")
    return 0


def _cmd_edge_compact(args: argparse.Namespace) -> int:
    result = compact_edge(Path(args.workspace), args.edge_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Compacted edge: {args.edge_id}")
        print(result["brief"])
    return 0


def _cmd_actor_assign(args: argparse.Namespace) -> int:
    result = assign_actor(Path(args.workspace), args.actor_id, home_node=args.home_node, role=args.role, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Assigned actor: {args.actor_id}")
    return 0


def _cmd_actor_archive(args: argparse.Namespace) -> int:
    result = archive_actor(Path(args.workspace), args.actor_id, actor=args.actor, reason=args.reason)
    if args.json:
        _print_json(result)
    else:
        print(f"Archived actor: {args.actor_id}")
    return 0


def _cmd_actor_signin(args: argparse.Namespace) -> int:
    result = sign_in_actor(
        Path(args.workspace),
        args.actor_id,
        home_node=args.home_node,
        role=args.role,
        instance=args.instance,
        operator=args.actor,
        require_assignment=args.require_assignment,
    )
    if args.json:
        _print_json(result)
    else:
        print(result["bootstrap"])
    return 0


def _cmd_actor_refresh(args: argparse.Namespace) -> int:
    result = refresh_signin(Path(args.workspace), args.signin_id, operator=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(result["bootstrap"])
    return 0


def _cmd_skill_register(args: argparse.Namespace) -> int:
    result = register_skill(Path(args.workspace), args.skill_id, title=args.title, scope=args.scope, trigger=args.trigger, permission_profile=args.permission_profile, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Registered skill: {args.skill_id}")
    return 0


def _cmd_skill_list(args: argparse.Namespace) -> int:
    result = list_skills(Path(args.workspace), scope=args.scope, include_archived=args.include_archived)
    if args.json:
        _print_json(result)
    else:
        for skill in result["skills"]:
            print(f"{skill['id']} {skill.get('status')} {skill.get('scope')}")
    return 0


def _cmd_skill_status(args: argparse.Namespace) -> int:
    result = update_skill_status(Path(args.workspace), args.skill_id, status=args.status, actor=args.actor, reason=args.reason)
    if args.json:
        _print_json(result)
    else:
        print(f"Updated skill {args.skill_id}: {args.status}")
    return 0


def _cmd_archive_sweep(args: argparse.Namespace) -> int:
    result = archive_sweep(Path(args.workspace), enqueue=args.enqueue, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Archive candidates: {len(result['candidates'])}")
    return 0


def _cmd_upgrade_doctor(args: argparse.Namespace) -> int:
    result = doctor(Path(args.workspace), require_generated=args.require_generated)
    if args.json:
        _print_json(result)
    else:
        print("Doctor passed" if result["ok"] else "Doctor found issues")
    return 0 if result["ok"] else 1


def _cmd_upgrade_migration_list(args: argparse.Namespace) -> int:
    result = list_migrations(Path(args.workspace))
    if args.json:
        _print_json(result)
    else:
        for migration in result["migrations"]:
            marker = "applied" if migration["applied"] else "pending"
            print(f"{migration['id']} {marker} - {migration['description']}")
    return 0


def _cmd_upgrade_migration_dry_run(args: argparse.Namespace) -> int:
    result = migration_dry_run(Path(args.workspace), args.migration_id)
    if args.json:
        _print_json(result)
    else:
        for change in result["changes"]:
            print(f"{change['action']} {change['path']}")
    return 0


def _cmd_upgrade_migration_apply(args: argparse.Namespace) -> int:
    result = migration_apply(Path(args.workspace), args.migration_id, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Applied migration: {args.migration_id}")
    return 0


def _cmd_upgrade_template_diff(args: argparse.Namespace) -> int:
    result = template_diff(Path(args.workspace), Path(__file__).resolve().parents[2])
    if args.json:
        _print_json(result)
    else:
        print(f"Template diffs: {len(result['diffs'])}")
    return 0


def _cmd_upgrade_template_apply_new(args: argparse.Namespace) -> int:
    result = template_apply_new(Path(args.workspace), Path(__file__).resolve().parents[2], actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Applied new template files: {len(result['changed_files'])}")
    return 0



def _cmd_connector_list(args: argparse.Namespace) -> int:
    result = list_connectors()
    if args.json:
        _print_json(result)
    else:
        for connector in result["connectors"]:
            print(f"{connector['name']}: {connector['description']}")
    return 0


def _cmd_persistence_list(args: argparse.Namespace) -> int:
    result = list_backends()
    if args.json:
        _print_json(result)
    else:
        for backend in result["backends"]:
            marker = "canonical" if backend["canonical"] else backend["status"]
            print(f"{backend['name']} ({marker}): {backend['description']}")
    return 0


def _cmd_policy_show(args: argparse.Namespace) -> int:
    result = explain_operation_policy(Path(args.workspace), target=args.target)
    if args.json:
        _print_json(result)
    else:
        policy = result["policy"]
        print(f"Operation policy: {result['path']}")
        print(f"Policy id: {policy.get('id')}")
        for name, settings in policy.get("operation_policies", {}).items():
            if isinstance(settings, dict):
                mode = settings.get("mode", settings.get("sweep_mode", "configured"))
                print(f"{name}: {mode}")
    return 0


def _cmd_scheduler_install(args: argparse.Namespace) -> int:
    result = install_scheduler(
        Path(args.workspace),
        args.kind,
        runtime_command=args.runtime_command,
        interval_minutes=args.interval_minutes,
        actor=args.actor,
    )
    if args.json:
        _print_json(result)
    else:
        print(f"Wrote scheduler template: {result['path']}")
        print(f"Install: {result['install_hint']}")
    return 0


def _cmd_operation_list(args: argparse.Namespace) -> int:
    result = list_operations(
        Path(args.workspace),
        limit=args.limit,
        operation_type=args.type,
        target=args.target,
    )
    if args.json:
        _print_json(result)
    else:
        for operation in result["operations"]:
            print(f"{operation['id']} {operation.get('type')} {operation.get('actor')} {operation.get('started_at')}")
    return 0


def _cmd_operation_show(args: argparse.Namespace) -> int:
    result = show_operation(Path(args.workspace), args.operation_id)
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            operation = result["operation"]
            print(f"{operation['id']} {operation.get('type')} {operation.get('status')}")
            for item in operation.get("changed_files", []):
                if isinstance(item, dict) and item.get("path"):
                    print(f"- {item['path']}")
        else:
            print(result.get("message", "Operation not found"), file=sys.stderr)
    return 0 if result.get("ok") else 1


def _cmd_mcp_tools(args: argparse.Namespace) -> int:
    result = list_tools()
    if args.json:
        _print_json(result)
    else:
        for tool in result["tools"]:
            print(f"{tool['name']}: {tool['description']}")
    return 0


def _cmd_mcp_call(args: argparse.Namespace) -> int:
    arguments = json.loads(args.args_json) if args.args_json else {}
    if args.workspace:
        arguments.setdefault("workspace", args.workspace)
    result = call_tool(args.tool, arguments)
    _print_json(result)
    return 0 if result.get("ok", False) else 1


def _cmd_mcp_serve(args: argparse.Namespace) -> int:
    del args
    return serve_json_lines()

def _cmd_backup_create(args: argparse.Namespace) -> int:
    backup_dir, manifest_path, operation = create_backup(Path(args.path), actor=args.actor)
    result = {
        "ok": True,
        "backup": str(backup_dir),
        "manifest": str(manifest_path),
        "operation": operation.id,
    }
    if args.json:
        _print_json(result)
    else:
        print(f"Created backup: {backup_dir}")
        print(f"Manifest: {manifest_path}")
    return 0


def _cmd_rollback_preview(args: argparse.Namespace) -> int:
    result = rollback_preview(Path(args.workspace), args.operation_id)
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            print(f"Rollback preview for {result['operation_id']}")
            for path in result.get("would_touch", []):
                print(f"- {path}")
        else:
            print(result.get("message", "Rollback preview failed"), file=sys.stderr)
    return 0 if result.get("ok") else 1

def _cmd_reserved(args: argparse.Namespace) -> int:
    message = f"Command group '{args.command}' is reserved and not implemented in this slice."
    if getattr(args, "json", False):
        _print_json({"ok": False, "error": "command.not_implemented", "message": message})
    else:
        print(message, file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hive", description="Hive Synapse memory runtime")
    parser.add_argument("--version", action="version", version=f"hive-synapse {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a Hive workspace")
    init_parser.add_argument("path")
    init_parser.add_argument("--fixture", choices=["basic-org"])
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(func=_cmd_init)

    validate_parser = subparsers.add_parser("validate", help="Validate a Hive workspace")
    validate_parser.add_argument("path", nargs="?", default=".")
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.set_defaults(func=_cmd_validate)

    llm_parser = subparsers.add_parser("llm", help="LLM provider, profile, and credential operations")
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command", required=True)

    llm_init = llm_subparsers.add_parser("init", help="Create default LLM policy and credential registry files")
    llm_init.add_argument("--workspace", default=".")
    llm_init.add_argument("--actor", default="system:llm")
    llm_init.add_argument("--json", action="store_true")
    llm_init.set_defaults(func=_cmd_llm_init)

    llm_providers = llm_subparsers.add_parser("providers", help="List supported LLM providers")
    llm_providers.add_argument("--json", action="store_true")
    llm_providers.set_defaults(func=_cmd_llm_providers)

    llm_config = llm_subparsers.add_parser("config", help="Show LLM policy and credential registry")
    llm_config.add_argument("--workspace", default=".")
    llm_config.add_argument("--json", action="store_true")
    llm_config.set_defaults(func=_cmd_llm_config)

    llm_credential = llm_subparsers.add_parser("credential", help="Manage LLM credentials")
    llm_credential_subparsers = llm_credential.add_subparsers(dest="llm_credential_command", required=True)
    llm_credential_add = llm_credential_subparsers.add_parser("add", help="Add or update an LLM credential")
    llm_credential_add.add_argument("credential_id")
    llm_credential_add.add_argument("--workspace", default=".")
    llm_credential_add.add_argument("--provider", required=True)
    llm_credential_add.add_argument("--api-key-env")
    llm_credential_add.add_argument("--actor", default="system:llm")
    llm_credential_add.add_argument("--assign-actor")
    llm_credential_add.add_argument("--organization-default", action="store_true")
    llm_credential_add.add_argument("--json", action="store_true")
    llm_credential_add.set_defaults(func=_cmd_llm_credential_add)

    llm_credential_assign = llm_credential_subparsers.add_parser("assign", help="Assign a credential to an actor or organization")
    llm_credential_assign.add_argument("credential_id", help="Credential id, or 'none'")
    llm_credential_assign.add_argument("--workspace", default=".")
    llm_credential_assign.add_argument("--actor", default="system:llm")
    llm_credential_assign.add_argument("--assign-actor")
    llm_credential_assign.add_argument("--organization-default", action="store_true")
    llm_credential_assign.add_argument("--json", action="store_true")
    llm_credential_assign.set_defaults(func=_cmd_llm_credential_assign)

    llm_profile = llm_subparsers.add_parser("profile", help="Manage LLM profiles")
    llm_profile_subparsers = llm_profile.add_subparsers(dest="llm_profile_command", required=True)
    llm_profile_add = llm_profile_subparsers.add_parser("add", help="Add or update an LLM profile")
    llm_profile_add.add_argument("profile_id")
    llm_profile_add.add_argument("--workspace", default=".")
    llm_profile_add.add_argument("--provider", required=True)
    llm_profile_add.add_argument("--model", required=True)
    llm_profile_add.add_argument("--base-url")
    llm_profile_add.add_argument("--credential")
    llm_profile_add.add_argument("--command-json", help="JSON argv array for command provider profiles")
    llm_profile_add.add_argument("--temperature", type=float)
    llm_profile_add.add_argument("--max-output-tokens", type=int)
    llm_profile_add.add_argument("--actor", default="system:llm")
    llm_profile_add.add_argument("--assign-actor")
    llm_profile_add.add_argument("--organization-default", action="store_true")
    llm_profile_add.add_argument("--enable", action="store_true")
    llm_profile_add.add_argument("--allow-network-models", action="store_true")
    llm_profile_add.add_argument("--json", action="store_true")
    llm_profile_add.set_defaults(func=_cmd_llm_profile_add)

    llm_profile_assign = llm_profile_subparsers.add_parser("assign", help="Assign a profile to an actor or organization")
    llm_profile_assign.add_argument("profile_id", help="Profile id, such as deterministic")
    llm_profile_assign.add_argument("--workspace", default=".")
    llm_profile_assign.add_argument("--actor", default="system:llm")
    llm_profile_assign.add_argument("--assign-actor")
    llm_profile_assign.add_argument("--organization-default", action="store_true")
    llm_profile_assign.add_argument("--enable", action="store_true")
    llm_profile_assign.add_argument("--json", action="store_true")
    llm_profile_assign.set_defaults(func=_cmd_llm_profile_assign)

    charter_parser = subparsers.add_parser("charter", help="Mission, goals, tone, and soul records")
    charter_subparsers = charter_parser.add_subparsers(dest="charter_command", required=True)
    charter_init = charter_subparsers.add_parser("init", help="Create a node charter if missing")
    charter_init.add_argument("target")
    charter_init.add_argument("--workspace", default=".")
    charter_init.add_argument("--title")
    charter_init.add_argument("--actor", required=True)
    charter_init.add_argument("--json", action="store_true")
    charter_init.set_defaults(func=_cmd_charter_init)

    charter_show = charter_subparsers.add_parser("show", help="Show a node charter")
    charter_show.add_argument("target")
    charter_show.add_argument("--workspace", default=".")
    charter_show.add_argument("--json", action="store_true")
    charter_show.set_defaults(func=_cmd_charter_show)

    charter_list = charter_subparsers.add_parser("list", help="List node charters")
    charter_list.add_argument("--workspace", default=".")
    charter_list.add_argument("--json", action="store_true")
    charter_list.set_defaults(func=_cmd_charter_list)

    charter_update = charter_subparsers.add_parser("update", help="Append or replace a charter section")
    charter_update.add_argument("target")
    charter_update.add_argument("--workspace", default=".")
    charter_update.add_argument("--section", choices=["mission", "goals", "tone", "soul", "principles", "notes"], required=True)
    charter_update.add_argument("--text", required=True)
    charter_update.add_argument("--mode", choices=["append", "replace"], default="append")
    charter_update.add_argument("--actor", required=True)
    charter_update.add_argument("--source-ref")
    charter_update.add_argument("--json", action="store_true")
    charter_update.set_defaults(func=_cmd_charter_update)

    context_parser = subparsers.add_parser("context", help="Context pack operations")
    context_subparsers = context_parser.add_subparsers(dest="context_command", required=True)
    compile_parser = context_subparsers.add_parser("compile", help="Compile a context pack")
    compile_parser.add_argument("target")
    compile_parser.add_argument("--workspace", default=".")
    compile_parser.add_argument("--json", action="store_true")
    compile_parser.set_defaults(func=_cmd_context_compile)

    status_parser = context_subparsers.add_parser("status", help="Check whether target context is fresh")
    status_parser.add_argument("target")
    status_parser.add_argument("--workspace", default=".")
    status_parser.add_argument("--json", action="store_true")
    status_parser.set_defaults(func=_cmd_context_status)

    impacted_parser = context_subparsers.add_parser("impacted", help="Compute impacted targets")
    impacted_parser.add_argument("target")
    impacted_parser.add_argument("--workspace", default=".")
    impacted_parser.add_argument("--json", action="store_true")
    impacted_parser.set_defaults(func=_cmd_context_impacted)

    invalidate_parser = context_subparsers.add_parser("invalidate", help="Write context dirty markers")
    invalidate_parser.add_argument("target")
    invalidate_parser.add_argument("--workspace", default=".")
    invalidate_parser.add_argument("--reason", required=True)
    invalidate_parser.add_argument("--actor", default="system:context")
    invalidate_parser.add_argument(
        "--respect-policy",
        action="store_true",
        help="Evaluate operations policy instead of forcing a dirty marker.",
    )
    invalidate_parser.add_argument("--json", action="store_true")
    invalidate_parser.set_defaults(func=_cmd_context_invalidate)

    import_parser = subparsers.add_parser("import", help="Import workspace operations")
    import_subparsers = import_parser.add_subparsers(dest="import_command", required=True)
    import_add = import_subparsers.add_parser("add", help="Add a local file or text import")
    import_add.add_argument("target")
    import_add.add_argument("source")
    import_add.add_argument("--workspace", default=".")
    import_add.add_argument("--actor", default="system:import")
    import_add.add_argument("--json", action="store_true")
    import_add.set_defaults(func=_cmd_import_add)

    import_fetch = import_subparsers.add_parser("fetch", help="Record a URL import")
    import_fetch.add_argument("target")
    import_fetch.add_argument("url")
    import_fetch.add_argument("--workspace", default=".")
    import_fetch.add_argument("--connector", choices=["local", "obsidian", "url", "git", "github", "notion", "gdrive"])
    import_fetch.add_argument("--actor", default="system:import")
    import_fetch.add_argument("--json", action="store_true")
    import_fetch.set_defaults(func=_cmd_import_fetch)

    import_classify = import_subparsers.add_parser("classify", help="Classify an import item")
    import_classify.add_argument("import_id")
    import_classify.add_argument("--workspace", default=".")
    import_classify.add_argument("--sensitivity")
    import_classify.add_argument("--actor", default="system:import")
    _add_llm_selection_args(import_classify)
    import_classify.add_argument("--json", action="store_true")
    import_classify.set_defaults(func=_cmd_import_classify)

    import_compact = import_subparsers.add_parser("compact", help="Compact an import into candidate memory")
    import_compact.add_argument("import_id")
    import_compact.add_argument("--workspace", default=".")
    import_compact.add_argument("--actor", default="system:import")
    _add_llm_selection_args(import_compact)
    import_compact.add_argument("--json", action="store_true")
    import_compact.set_defaults(func=_cmd_import_compact)

    import_propose = import_subparsers.add_parser("propose", help="Create promotion proposals for an import")
    import_propose.add_argument("import_id")
    import_propose.add_argument("--workspace", default=".")
    import_propose.add_argument("--actor", default="system:import")
    import_propose.add_argument("--json", action="store_true")
    import_propose.set_defaults(func=_cmd_import_propose)

    promote_parser = subparsers.add_parser("promote", help="Promotion and review operations")
    promote_subparsers = promote_parser.add_subparsers(dest="promote_command", required=True)
    promote_list = promote_subparsers.add_parser("list", help="List promotion proposals")
    promote_list.add_argument("--workspace", default=".")
    promote_list.add_argument("--status")
    promote_list.add_argument("--json", action="store_true")
    promote_list.set_defaults(func=_cmd_promote_list)

    promote_review = promote_subparsers.add_parser("review", help="Approve or reject a proposal")
    promote_review.add_argument("proposal_id")
    promote_review.add_argument("--workspace", default=".")
    promote_review.add_argument("--decision", choices=["approved", "rejected"], required=True)
    promote_review.add_argument("--actor", required=True)
    promote_review.add_argument("--rationale", required=True)
    promote_review.add_argument("--json", action="store_true")
    promote_review.set_defaults(func=_cmd_promote_review)

    promote_apply = promote_subparsers.add_parser("apply", help="Apply an approved proposal")
    promote_apply.add_argument("proposal_id")
    promote_apply.add_argument("--workspace", default=".")
    promote_apply.add_argument("--actor", required=True)
    promote_apply.add_argument("--json", action="store_true")
    promote_apply.set_defaults(func=_cmd_promote_apply)

    promote_reject = promote_subparsers.add_parser("reject", help="Reject a proposal")
    promote_reject.add_argument("proposal_id")
    promote_reject.add_argument("--workspace", default=".")
    promote_reject.add_argument("--actor", required=True)
    promote_reject.add_argument("--rationale", required=True)
    promote_reject.add_argument("--json", action="store_true")
    promote_reject.set_defaults(func=_cmd_promote_reject)

    promote_sweep = promote_subparsers.add_parser("sweep", help="Sweep candidates for promotability")
    promote_sweep.add_argument("--workspace", default=".")
    promote_sweep.add_argument("--create-proposals", action="store_true", default=None)
    promote_sweep.add_argument("--actor", default="system:sweep")
    _add_llm_selection_args(promote_sweep)
    promote_sweep.add_argument("--json", action="store_true")
    promote_sweep.set_defaults(func=_cmd_promote_sweep)

    job_parser = subparsers.add_parser("job", help="Filesystem job queue operations")
    job_subparsers = job_parser.add_subparsers(dest="job_command", required=True)
    job_enqueue = job_subparsers.add_parser("enqueue", help="Enqueue a filesystem job")
    job_enqueue.add_argument("type")
    job_enqueue.add_argument("target")
    job_enqueue.add_argument("--workspace", default=".")
    job_enqueue.add_argument("--reason", required=True)
    job_enqueue.add_argument("--actor", default="system:job")
    job_enqueue.add_argument("--json", action="store_true")
    job_enqueue.set_defaults(func=_cmd_job_enqueue)

    job_list = job_subparsers.add_parser("list", help="List jobs")
    job_list.add_argument("--workspace", default=".")
    job_list.add_argument("--status", choices=["pending", "claimed", "completed", "failed"])
    job_list.add_argument("--json", action="store_true")
    job_list.set_defaults(func=_cmd_job_list)

    job_claim = job_subparsers.add_parser("claim", help="Claim the next pending job")
    job_claim.add_argument("--workspace", default=".")
    job_claim.add_argument("--runner", default="runner:local")
    job_claim.add_argument("--json", action="store_true")
    job_claim.set_defaults(func=_cmd_job_claim)

    job_complete = job_subparsers.add_parser("complete", help="Complete a claimed job")
    job_complete.add_argument("job_id")
    job_complete.add_argument("--workspace", default=".")
    job_complete.add_argument("--actor", default="system:job")
    job_complete.add_argument("--json", action="store_true")
    job_complete.set_defaults(func=_cmd_job_complete)

    job_fail = job_subparsers.add_parser("fail", help="Fail a claimed job")
    job_fail.add_argument("job_id")
    job_fail.add_argument("--workspace", default=".")
    job_fail.add_argument("--reason", required=True)
    job_fail.add_argument("--actor", default="system:job")
    job_fail.add_argument("--json", action="store_true")
    job_fail.set_defaults(func=_cmd_job_fail)

    job_run = job_subparsers.add_parser("run", help="Run the next pending job")
    job_run.add_argument("--workspace", default=".")
    job_run.add_argument("--runner", default="runner:local")
    job_run.add_argument("--json", action="store_true")
    job_run.set_defaults(func=_cmd_job_run)

    job_watchdog = job_subparsers.add_parser("watchdog", help="Run watchdog checks")
    job_watchdog.add_argument("--workspace", default=".")
    job_watchdog.add_argument("--enqueue", action="store_true", default=None)
    job_watchdog.add_argument("--actor", default="system:watchdog")
    job_watchdog.add_argument("--json", action="store_true")
    job_watchdog.set_defaults(func=_cmd_job_watchdog)

    node_parser = subparsers.add_parser("node", help="Node lifecycle operations")
    node_subparsers = node_parser.add_subparsers(dest="node_command", required=True)
    node_create = node_subparsers.add_parser("create", help="Create a graph node")
    node_create.add_argument("node_id")
    node_create.add_argument("--workspace", default=".")
    node_create.add_argument("--kind", required=True)
    node_create.add_argument("--title", required=True)
    node_create.add_argument("--parent", action="append", default=[])
    node_create.add_argument("--actor", required=True)
    node_create.add_argument("--json", action="store_true")
    node_create.set_defaults(func=_cmd_node_create)

    node_move = node_subparsers.add_parser("move", help="Move a graph node")
    node_move.add_argument("node_id")
    node_move.add_argument("--workspace", default=".")
    node_move.add_argument("--parent", action="append", default=[])
    node_move.add_argument("--actor", required=True)
    node_move.add_argument("--json", action="store_true")
    node_move.set_defaults(func=_cmd_node_move)

    node_archive = node_subparsers.add_parser("archive", help="Archive a graph node")
    node_archive.add_argument("node_id")
    node_archive.add_argument("--workspace", default=".")
    node_archive.add_argument("--actor", required=True)
    node_archive.add_argument("--reason", required=True)
    node_archive.add_argument("--defer-compaction", action="store_true")
    node_archive.add_argument("--json", action="store_true")
    node_archive.set_defaults(func=_cmd_node_archive)

    node_restore = node_subparsers.add_parser("restore", help="Restore an archived graph node")
    node_restore.add_argument("node_id")
    node_restore.add_argument("--workspace", default=".")
    node_restore.add_argument("--actor", required=True)
    node_restore.add_argument("--json", action="store_true")
    node_restore.set_defaults(func=_cmd_node_restore)

    node_compact = node_subparsers.add_parser("compact", help="Compact a node into BRIEF.md")
    node_compact.add_argument("node_id")
    node_compact.add_argument("--workspace", default=".")
    node_compact.add_argument("--actor", default="system:compact")
    node_compact.add_argument("--json", action="store_true")
    node_compact.set_defaults(func=_cmd_node_compact)

    edge_parser = subparsers.add_parser("edge", help="Shared edge lifecycle operations")
    edge_subparsers = edge_parser.add_subparsers(dest="edge_command", required=True)
    edge_create = edge_subparsers.add_parser("create", help="Create a cross-node shared context edge")
    edge_create.add_argument("edge_id")
    edge_create.add_argument("--workspace", default=".")
    edge_create.add_argument("--kind", required=True)
    edge_create.add_argument("--title", required=True)
    edge_create.add_argument("--node", action="append", required=True)
    edge_create.add_argument("--summary")
    edge_create.add_argument("--actor", required=True)
    edge_create.add_argument("--json", action="store_true")
    edge_create.set_defaults(func=_cmd_edge_create)

    edge_list = edge_subparsers.add_parser("list", help="List shared context edges")
    edge_list.add_argument("--workspace", default=".")
    edge_list.add_argument("--node")
    edge_list.add_argument("--include-archived", action="store_true")
    edge_list.add_argument("--json", action="store_true")
    edge_list.set_defaults(func=_cmd_edge_list)

    edge_archive_cmd = edge_subparsers.add_parser("archive", help="Archive a shared context edge")
    edge_archive_cmd.add_argument("edge_id")
    edge_archive_cmd.add_argument("--workspace", default=".")
    edge_archive_cmd.add_argument("--actor", required=True)
    edge_archive_cmd.add_argument("--reason", required=True)
    edge_archive_cmd.add_argument("--json", action="store_true")
    edge_archive_cmd.set_defaults(func=_cmd_edge_archive)

    edge_restore_cmd = edge_subparsers.add_parser("restore", help="Restore an archived edge")
    edge_restore_cmd.add_argument("edge_id")
    edge_restore_cmd.add_argument("--workspace", default=".")
    edge_restore_cmd.add_argument("--actor", required=True)
    edge_restore_cmd.add_argument("--json", action="store_true")
    edge_restore_cmd.set_defaults(func=_cmd_edge_restore)

    edge_compact = edge_subparsers.add_parser("compact", help="Compact an edge into BRIEF.md")
    edge_compact.add_argument("edge_id")
    edge_compact.add_argument("--workspace", default=".")
    edge_compact.add_argument("--actor", default="system:compact")
    edge_compact.add_argument("--json", action="store_true")
    edge_compact.set_defaults(func=_cmd_edge_compact)

    actor_parser = subparsers.add_parser("actor", help="Actor assignment operations")
    actor_subparsers = actor_parser.add_subparsers(dest="actor_command", required=True)
    actor_assign_cmd = actor_subparsers.add_parser("assign", help="Assign an actor to a node")
    actor_assign_cmd.add_argument("actor_id")
    actor_assign_cmd.add_argument("--workspace", default=".")
    actor_assign_cmd.add_argument("--home-node", required=True)
    actor_assign_cmd.add_argument("--role", required=True)
    actor_assign_cmd.add_argument("--actor", required=True)
    actor_assign_cmd.add_argument("--json", action="store_true")
    actor_assign_cmd.set_defaults(func=_cmd_actor_assign)

    actor_archive_cmd = actor_subparsers.add_parser("archive", help="Archive an actor")
    actor_archive_cmd.add_argument("actor_id")
    actor_archive_cmd.add_argument("--workspace", default=".")
    actor_archive_cmd.add_argument("--actor", required=True)
    actor_archive_cmd.add_argument("--reason", required=True)
    actor_archive_cmd.add_argument("--json", action="store_true")
    actor_archive_cmd.set_defaults(func=_cmd_actor_archive)

    actor_signin_cmd = actor_subparsers.add_parser("signin", help="Sign an actor into a node and emit its context pack")
    actor_signin_cmd.add_argument("actor_id")
    actor_signin_cmd.add_argument("--workspace", default=".")
    actor_signin_cmd.add_argument("--home-node")
    actor_signin_cmd.add_argument("--role")
    actor_signin_cmd.add_argument("--instance")
    actor_signin_cmd.add_argument("--actor")
    actor_signin_cmd.add_argument("--require-assignment", action="store_true")
    actor_signin_cmd.add_argument("--json", action="store_true")
    actor_signin_cmd.set_defaults(func=_cmd_actor_signin)

    actor_refresh_cmd = actor_subparsers.add_parser("refresh", help="Refresh a sign-in context pack")
    actor_refresh_cmd.add_argument("signin_id")
    actor_refresh_cmd.add_argument("--workspace", default=".")
    actor_refresh_cmd.add_argument("--actor")
    actor_refresh_cmd.add_argument("--json", action="store_true")
    actor_refresh_cmd.set_defaults(func=_cmd_actor_refresh)

    skill_parser = subparsers.add_parser("skill", help="Shared skill registry operations")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_register_cmd = skill_subparsers.add_parser("register", help="Register a shared skill")
    skill_register_cmd.add_argument("skill_id")
    skill_register_cmd.add_argument("--workspace", default=".")
    skill_register_cmd.add_argument("--title", required=True)
    skill_register_cmd.add_argument("--scope", required=True)
    skill_register_cmd.add_argument("--trigger", required=True)
    skill_register_cmd.add_argument("--permission-profile", default="read_only")
    skill_register_cmd.add_argument("--actor", required=True)
    skill_register_cmd.add_argument("--json", action="store_true")
    skill_register_cmd.set_defaults(func=_cmd_skill_register)

    skill_list_cmd = skill_subparsers.add_parser("list", help="List shared skills")
    skill_list_cmd.add_argument("--workspace", default=".")
    skill_list_cmd.add_argument("--scope")
    skill_list_cmd.add_argument("--include-archived", action="store_true")
    skill_list_cmd.add_argument("--json", action="store_true")
    skill_list_cmd.set_defaults(func=_cmd_skill_list)

    skill_status_cmd = skill_subparsers.add_parser("status", help="Update skill status")
    skill_status_cmd.add_argument("skill_id")
    skill_status_cmd.add_argument("status", choices=["active", "deprecated", "archived", "restored"])
    skill_status_cmd.add_argument("--workspace", default=".")
    skill_status_cmd.add_argument("--actor", required=True)
    skill_status_cmd.add_argument("--reason", required=True)
    skill_status_cmd.add_argument("--json", action="store_true")
    skill_status_cmd.set_defaults(func=_cmd_skill_status)

    archive_parser = subparsers.add_parser("archive", help="Archive operations")
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", required=True)
    archive_sweep_cmd = archive_subparsers.add_parser("sweep", help="Find archive candidates")
    archive_sweep_cmd.add_argument("--workspace", default=".")
    archive_sweep_cmd.add_argument("--enqueue", action="store_true", default=None)
    archive_sweep_cmd.add_argument("--actor", default="system:archive")
    archive_sweep_cmd.add_argument("--json", action="store_true")
    archive_sweep_cmd.set_defaults(func=_cmd_archive_sweep)

    upgrade_parser = subparsers.add_parser("upgrade", help="Doctor, migration, and template operations")
    upgrade_subparsers = upgrade_parser.add_subparsers(dest="upgrade_command", required=True)
    upgrade_doctor = upgrade_subparsers.add_parser("doctor", help="Check workspace health")
    upgrade_doctor.add_argument("--workspace", default=".")
    upgrade_doctor.add_argument("--require-generated", action="store_true")
    upgrade_doctor.add_argument("--json", action="store_true")
    upgrade_doctor.set_defaults(func=_cmd_upgrade_doctor)

    upgrade_migration_list = upgrade_subparsers.add_parser("migration-list", help="List migrations")
    upgrade_migration_list.add_argument("--workspace", default=".")
    upgrade_migration_list.add_argument("--json", action="store_true")
    upgrade_migration_list.set_defaults(func=_cmd_upgrade_migration_list)

    upgrade_migration_dry = upgrade_subparsers.add_parser("migration-dry-run", help="Dry-run a migration")
    upgrade_migration_dry.add_argument("migration_id")
    upgrade_migration_dry.add_argument("--workspace", default=".")
    upgrade_migration_dry.add_argument("--json", action="store_true")
    upgrade_migration_dry.set_defaults(func=_cmd_upgrade_migration_dry_run)

    upgrade_migration_apply = upgrade_subparsers.add_parser("migration-apply", help="Apply a migration")
    upgrade_migration_apply.add_argument("migration_id")
    upgrade_migration_apply.add_argument("--workspace", default=".")
    upgrade_migration_apply.add_argument("--actor", default="system:migration")
    upgrade_migration_apply.add_argument("--json", action="store_true")
    upgrade_migration_apply.set_defaults(func=_cmd_upgrade_migration_apply)

    upgrade_template_diff = upgrade_subparsers.add_parser("template-diff", help="Diff runtime templates")
    upgrade_template_diff.add_argument("--workspace", default=".")
    upgrade_template_diff.add_argument("--json", action="store_true")
    upgrade_template_diff.set_defaults(func=_cmd_upgrade_template_diff)

    upgrade_template_apply = upgrade_subparsers.add_parser("template-apply-new", help="Apply missing runtime templates only")
    upgrade_template_apply.add_argument("--workspace", default=".")
    upgrade_template_apply.add_argument("--actor", default="system:upgrade")
    upgrade_template_apply.add_argument("--json", action="store_true")
    upgrade_template_apply.set_defaults(func=_cmd_upgrade_template_apply_new)

    connector_parser = subparsers.add_parser("connector", help="Connector registry operations")
    connector_subparsers = connector_parser.add_subparsers(dest="connector_command", required=True)
    connector_list = connector_subparsers.add_parser("list", help="List import connectors")
    connector_list.add_argument("--json", action="store_true")
    connector_list.set_defaults(func=_cmd_connector_list)

    persistence_parser = subparsers.add_parser("persistence", help="Persistence backend registry")
    persistence_subparsers = persistence_parser.add_subparsers(dest="persistence_command", required=True)
    persistence_list = persistence_subparsers.add_parser("list", help="List persistence backends")
    persistence_list.add_argument("--json", action="store_true")
    persistence_list.set_defaults(func=_cmd_persistence_list)

    policy_parser = subparsers.add_parser("policy", help="Inspect effective operation policy")
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_show = policy_subparsers.add_parser("show", help="Show workspace or target operation policy")
    policy_show.add_argument("--workspace", default=".")
    policy_show.add_argument("--target")
    policy_show.add_argument("--json", action="store_true")
    policy_show.set_defaults(func=_cmd_policy_show)

    mcp_parser = subparsers.add_parser("mcp", help="MCP-compatible tool surface")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", required=True)
    mcp_tools = mcp_subparsers.add_parser("tools", help="List available MCP tools")
    mcp_tools.add_argument("--json", action="store_true")
    mcp_tools.set_defaults(func=_cmd_mcp_tools)

    mcp_call = mcp_subparsers.add_parser("call", help="Call an MCP tool")
    mcp_call.add_argument("tool")
    mcp_call.add_argument("--workspace")
    mcp_call.add_argument("--args-json", default="{}")
    mcp_call.set_defaults(func=_cmd_mcp_call)

    mcp_serve = mcp_subparsers.add_parser("serve", help="Serve JSON-line MCP-compatible requests")
    mcp_serve.set_defaults(func=_cmd_mcp_serve)

    scheduler_parser = subparsers.add_parser("scheduler", help="External scheduler template operations")
    scheduler_subparsers = scheduler_parser.add_subparsers(dest="scheduler_command", required=True)
    scheduler_install = scheduler_subparsers.add_parser("install", help="Write cron or launchd scheduler templates")
    scheduler_install.add_argument("kind", choices=["cron", "launchd"])
    scheduler_install.add_argument("--workspace", default=".")
    scheduler_install.add_argument("--runtime-command")
    scheduler_install.add_argument("--interval-minutes", type=int, default=15)
    scheduler_install.add_argument("--actor", default="system:scheduler")
    scheduler_install.add_argument("--json", action="store_true")
    scheduler_install.set_defaults(func=_cmd_scheduler_install)

    operation_parser = subparsers.add_parser("operation", help="Audit operation visibility")
    operation_subparsers = operation_parser.add_subparsers(dest="operation_command", required=True)
    operation_list = operation_subparsers.add_parser("list", help="List audit operation records")
    operation_list.add_argument("--workspace", default=".")
    operation_list.add_argument("--limit", type=int, default=20)
    operation_list.add_argument("--type")
    operation_list.add_argument("--target")
    operation_list.add_argument("--json", action="store_true")
    operation_list.set_defaults(func=_cmd_operation_list)

    operation_show = operation_subparsers.add_parser("show", help="Show an audit operation record")
    operation_show.add_argument("operation_id")
    operation_show.add_argument("--workspace", default=".")
    operation_show.add_argument("--json", action="store_true")
    operation_show.set_defaults(func=_cmd_operation_show)

    backup_parser = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", required=True)
    backup_create = backup_subparsers.add_parser("create", help="Create a workspace backup")
    backup_create.add_argument("path", nargs="?", default=".")
    backup_create.add_argument("--actor", default="system:backup")
    backup_create.add_argument("--json", action="store_true")
    backup_create.set_defaults(func=_cmd_backup_create)

    rollback_parser = subparsers.add_parser("rollback", help="Rollback operations")
    rollback_subparsers = rollback_parser.add_subparsers(dest="rollback_command", required=True)
    rollback_preview_parser = rollback_subparsers.add_parser("preview", help="Preview rollback effects")
    rollback_preview_parser.add_argument("operation_id")
    rollback_preview_parser.add_argument("--workspace", default=".")
    rollback_preview_parser.add_argument("--json", action="store_true")
    rollback_preview_parser.set_defaults(func=_cmd_rollback_preview)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except HiveError as exc:
        if getattr(args, "json", False):
            _print_json({"ok": False, "error": exc.__class__.__name__, "message": str(exc)})
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
