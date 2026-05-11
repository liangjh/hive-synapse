---
name: hive-ingest-summarize
description: Use when a user asks in natural language to add notes, documents, URLs, Notion links, Google Drive links, social posts, video links, or other source material into Hive Synapse and summarize it into candidate memory.
---

# Hive Ingest + Summarize

Translate user intent into the Hive import pipeline. Prefer `--json` for machine-readable output.

## Intent Mapping

- "add this note/doc/file" → `hive import add <target> <source> --workspace <workspace>`
- "fetch this link" → `hive import fetch <target> <url> --workspace <workspace>`
- "summarize this import" → `hive import classify <import-id>` then `hive import compact <import-id>`
- "make this available to the team" → `hive import propose <import-id>` then promotion review/apply
- "process everything new in this inbox" → list import items, classify/compact/propose each unprocessed item

## Required Inputs

Resolve these before mutating:

- `workspace`: use `$HIVE_WORKSPACE` if set; otherwise ask or infer from current directory.
- `target`: node or edge import target, e.g. `departments/research` or `edges/research__engineering`.
- `source`: local path, pasted text, URL, Notion URL, Google Drive URL, GitHub URL.

## Workflow

1. Validate workspace: `hive validate <workspace>`.
2. Create or record the import:
   - Local path/text: `hive import add <target> <source> --workspace <workspace> --actor <actor> --json`
   - External URL: `hive import fetch <target> <url> --workspace <workspace> --connector <connector> --actor <actor> --json`
3. Classify: `hive import classify <import-id> --workspace <workspace> --actor <actor> --json`.
4. Compact: `hive import compact <import-id> --workspace <workspace> --actor <actor> --json`.
5. If user asks for shared memory, propose: `hive import propose <import-id> --workspace <workspace> --actor <actor> --json`.
6. Validate again if shared files changed.

## Connector Limits

Current Notion and Google Drive connectors preserve external references. They do not yet fetch authenticated content or watch for remote changes. If asked to auto-sync Notion/GDrive, explain that this requires the future `source poll`/webhook connector work.

## Safety

Do not directly edit parent department/org memory. Imports should land in target import workspaces, candidate records, and proposals.
