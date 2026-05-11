#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILLS = REPO_ROOT / "skills" / "hive"
CODEX_SKILLS = CANONICAL_SKILLS
CLAUDE_COMMANDS = REPO_ROOT / "adapters" / "claude" / "commands"


def _default_target(adapter: str) -> Path:
    home = Path.home()
    if adapter == "codex":
        return Path(os.environ.get("CODEX_HOME", str(home / ".codex"))) / "skills"
    if adapter == "claude":
        return Path(os.environ.get("CLAUDE_HOME", str(home / ".claude"))) / "commands"
    if adapter == "generic":
        return Path.cwd() / "agent-skills"
    raise ValueError(f"Unsupported adapter: {adapter}")


def _copy_tree(source: Path, target: Path, *, dry_run: bool) -> None:
    if dry_run:
        print(f"would install {source} -> {target}")
        return
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print(f"installed {source.name} -> {target}")


def install_codex(target: Path, *, dry_run: bool) -> None:
    for skill_dir in sorted(CODEX_SKILLS.glob("hive-*")):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            _copy_tree(skill_dir, target / skill_dir.name, dry_run=dry_run)


def install_generic(target: Path, *, dry_run: bool) -> None:
    for skill_dir in sorted(CANONICAL_SKILLS.glob("hive-*")):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            _copy_tree(skill_dir, target / skill_dir.name, dry_run=dry_run)
    manifest = CANONICAL_SKILLS / "MANIFEST.yaml"
    if manifest.exists():
        if dry_run:
            print(f"would install {manifest} -> {target / 'MANIFEST.yaml'}")
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(manifest, target / "MANIFEST.yaml")
            print(f"installed MANIFEST.yaml -> {target / 'MANIFEST.yaml'}")


def install_claude(target: Path, *, dry_run: bool) -> None:
    for command_file in sorted(CLAUDE_COMMANDS.glob("hive-*.md")):
        destination = target / command_file.name
        if dry_run:
            print(f"would install {command_file} -> {destination}")
            continue
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(command_file, destination)
        print(f"installed {command_file.name} -> {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Hive Synapse agent skills/commands from repo-local definitions.")
    parser.add_argument("adapter", choices=["codex", "claude", "generic", "all"], help="Agent harness adapter to install for.")
    parser.add_argument("--target", help="Override install target directory. Not supported with adapter=all.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned installs without writing files.")
    args = parser.parse_args()

    adapters = ["codex", "claude", "generic"] if args.adapter == "all" else [args.adapter]
    if args.target and len(adapters) > 1:
        parser.error("--target can only be used with one adapter")

    for adapter in adapters:
        target = Path(args.target).expanduser() if args.target else _default_target(adapter)
        if not args.dry_run:
            target.mkdir(parents=True, exist_ok=True)
        print(f"== {adapter}: {target} ==")
        if adapter == "codex":
            install_codex(target, dry_run=args.dry_run)
        elif adapter == "claude":
            install_claude(target, dry_run=args.dry_run)
        elif adapter == "generic":
            install_generic(target, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
