from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import run_hive


class CharterTests(unittest.TestCase):
    def test_fixture_charters_validate_and_compile_into_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            charter = workspace / "memory/records/nodes/departments/engineering/CHARTER.md"
            self.assertTrue(charter.exists())
            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            compile_result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            pack = (
                workspace / "memory/generated/context-packs/nodes/departments/engineering/PACK.md"
            )
            text = pack.read_text()
            self.assertIn("Parent Charter: org", text)
            self.assertIn("Target Charter", text)
            self.assertIn("## Goals", text)
            self.assertIn("## Soul", text)

    def test_charter_update_appends_history_and_invalidates_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            update = run_hive(
                "charter",
                "update",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--section",
                "goals",
                "--text",
                "- Ship reliable agent memory primitives.",
                "--actor",
                "steward:engineering",
                "--source-ref",
                "manual:planning-session",
                "--json",
            )
            self.assertEqual(update.returncode, 0, update.stderr)
            payload = json.loads(update.stdout)
            self.assertTrue(payload["ok"])
            show = run_hive(
                "charter",
                "show",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(show.returncode, 0, show.stderr)
            body = json.loads(show.stdout)["body"]
            self.assertIn("Ship reliable agent memory primitives", body)
            history = workspace / "memory/records/nodes/departments/engineering/CHARTER_HISTORY.md"
            self.assertIn("steward:engineering", history.read_text())
            self.assertTrue(list((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml")))
            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

    def test_node_create_creates_charter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            result = run_hive(
                "node",
                "create",
                "departments/research",
                "--workspace",
                str(workspace),
                "--kind",
                "department",
                "--title",
                "Research",
                "--parent",
                "org",
                "--actor",
                "human:admin",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (workspace / "memory/records/nodes/departments/research/CHARTER.md").exists()
            )


if __name__ == "__main__":
    unittest.main()
