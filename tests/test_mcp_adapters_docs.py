from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import ROOT, run_hive


class McpAdaptersDocsTests(unittest.TestCase):
    def test_mcp_tools_and_get_context_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            tools = run_hive("mcp", "tools", "--json")
            self.assertEqual(tools.returncode, 0, tools.stderr)
            names = {tool["name"] for tool in json.loads(tools.stdout)["tools"]}
            self.assertIn("get_context_pack", names)
            call = run_hive(
                "mcp",
                "call",
                "get_context_pack",
                "--workspace",
                str(workspace),
                "--args-json",
                json.dumps({"target": "departments/engineering"}),
            )
            self.assertEqual(call.returncode, 0, call.stderr)
            payload = json.loads(call.stdout)
            self.assertTrue(payload["ok"])
            self.assertIn("Context Pack: departments/engineering", payload["pack"])

    def test_adapter_and_user_docs_exist(self) -> None:
        required = [
            "adapters/codex/skills/hive-context/SKILL.md",
            "adapters/codex/hooks/context-status-check.json",
            "adapters/claude/commands/hive-context.md",
            "adapters/claude/hooks/context-status-check.json",
            "docs/getting-started.md",
            "docs/command-reference.md",
            "docs/workspace-layout.md",
            "docs/agent-onboarding.md",
            "docs/upgrade-guide.md",
            "docs/troubleshooting.md",
            "docs/mcp.md",
        ]
        for rel in required:
            self.assertTrue((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
