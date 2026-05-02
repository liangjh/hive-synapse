from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .context import compile_context_pack
from .errors import HiveError
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
