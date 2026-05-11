#!/usr/bin/env sh
set -eu

SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/commands" && pwd)"
TARGET_DIR="${CLAUDE_HOME:-$HOME/.claude}/commands"
mkdir -p "$TARGET_DIR"

for command_file in "$SOURCE_DIR"/hive-*.md; do
  [ -f "$command_file" ] || continue
  command_name="$(basename "$command_file")"
  cp "$command_file" "$TARGET_DIR/$command_name"
  printf 'installed %s -> %s\n' "$command_name" "$TARGET_DIR/$command_name"
done
