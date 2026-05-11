---
description: Import and summarize source material into Hive Synapse candidate memory
allowed-tools: Bash(hive import:*), Bash(hive promote:*), Bash(hive validate:*), Bash(hive connector:*)
---

Interpret `$ARGUMENTS` as a natural-language import/summarization request.

Use `$HIVE_WORKSPACE` unless another workspace is provided. Resolve target node/edge first.

Common mappings:
- local note/file/text: `hive import add <target> <source> --workspace "$HIVE_WORKSPACE" --json`
- URL/Notion/GDrive/GitHub reference: `hive import fetch <target> <url> --workspace "$HIVE_WORKSPACE" --connector <connector> --json`
- summarize import: `hive import classify <import-id> --workspace "$HIVE_WORKSPACE" --json` then `hive import compact <import-id> --workspace "$HIVE_WORKSPACE" --json`
- prepare for shared memory: `hive import propose <import-id> --workspace "$HIVE_WORKSPACE" --json`

Do not directly edit parent/org memory. Notion and Google Drive currently preserve references; authenticated fetch/watch requires future connector implementation.
