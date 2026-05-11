#!/usr/bin/env sh
set -eu

SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/skills" && pwd)"
TARGET_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$TARGET_DIR"

for skill_dir in "$SOURCE_DIR"/hive-*; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  rm -rf "$TARGET_DIR/$skill_name"
  cp -R "$skill_dir" "$TARGET_DIR/$skill_name"
  printf 'installed %s -> %s\n' "$skill_name" "$TARGET_DIR/$skill_name"
done
