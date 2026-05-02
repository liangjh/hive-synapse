from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .backup import create_backup, rollback_preview
from .context import compile_context_pack
from .errors import HiveError
from .guardrails import dirty_markers_for_target
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
        "import",
        "promote",
        "job",
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
