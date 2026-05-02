from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .backup import create_backup, rollback_preview
from .context import compile_context_pack, context_impact, invalidate_context
from .errors import HiveError
from .guardrails import dirty_markers_for_target
from .imports import add_import, classify_import, compact_import, fetch_import, propose_import
from .jobs import claim_job, complete_job, enqueue_job, fail_job, list_jobs, run_next_job
from .promotion import apply_proposal, list_proposals, reject_proposal, review_proposal, sweep_promotability
from .watchdog import watchdog_report
from .paths import WorkspacePaths
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
    result = invalidate_context(Path(args.workspace), args.target, reason=args.reason, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Invalidated context for {args.target}: {result['invalidation']['id']}")
    return 0


def _cmd_import_add(args: argparse.Namespace) -> int:
    result = add_import(Path(args.workspace), args.target, args.source, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Created import item: {result['import_id']}")
    return 0


def _cmd_import_fetch(args: argparse.Namespace) -> int:
    result = fetch_import(Path(args.workspace), args.target, args.url, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Created URL import item: {result['import_id']}")
    return 0


def _cmd_import_classify(args: argparse.Namespace) -> int:
    result = classify_import(Path(args.workspace), args.import_id, sensitivity=args.sensitivity, actor=args.actor)
    if args.json:
        _print_json(result)
    else:
        print(f"Classified import item: {result['import_id']}")
    return 0


def _cmd_import_compact(args: argparse.Namespace) -> int:
    result = compact_import(Path(args.workspace), args.import_id, actor=args.actor)
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
    import_fetch.add_argument("--actor", default="system:import")
    import_fetch.add_argument("--json", action="store_true")
    import_fetch.set_defaults(func=_cmd_import_fetch)

    import_classify = import_subparsers.add_parser("classify", help="Classify an import item")
    import_classify.add_argument("import_id")
    import_classify.add_argument("--workspace", default=".")
    import_classify.add_argument("--sensitivity")
    import_classify.add_argument("--actor", default="system:import")
    import_classify.add_argument("--json", action="store_true")
    import_classify.set_defaults(func=_cmd_import_classify)

    import_compact = import_subparsers.add_parser("compact", help="Compact an import into candidate memory")
    import_compact.add_argument("import_id")
    import_compact.add_argument("--workspace", default=".")
    import_compact.add_argument("--actor", default="system:import")
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
    promote_sweep.add_argument("--create-proposals", action="store_true")
    promote_sweep.add_argument("--actor", default="system:sweep")
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
    job_watchdog.add_argument("--enqueue", action="store_true")
    job_watchdog.add_argument("--actor", default="system:watchdog")
    job_watchdog.add_argument("--json", action="store_true")
    job_watchdog.set_defaults(func=_cmd_job_watchdog)

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

    for name in [
        "node",
        "actor",
        "skill",
        "archive",
        "operation",
        "upgrade",
    ]:
        reserved = subparsers.add_parser(name, help=f"Reserved {name} command group")
        reserved.add_argument("args", nargs="*")
        reserved.add_argument("--json", action="store_true")
        reserved.set_defaults(func=_cmd_reserved)

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
