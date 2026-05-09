from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from tests.support import init_basic_workspace, json_from_stdout, run_hive


class SecondBrainMvpCliTests(unittest.TestCase):
    def test_edge_create_list_archive_restore_and_context_compile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            edge_id = "engineering__marketing__support"

            create = run_hive(
                "edge",
                "create",
                edge_id,
                "--workspace",
                str(workspace),
                "--kind",
                "collaboration",
                "--title",
                "Engineering / Marketing Support",
                "--node",
                "departments/engineering",
                "--node",
                "departments/marketing",
                "--actor",
                "steward:engineering",
                "--json",
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            create_payload = json_from_stdout(create)
            self.assertTrue(create_payload["ok"], create_payload)
            self.assertEqual(create_payload["edge"]["id"], edge_id)
            self.assertTrue((workspace / f"memory/graph/edges/{edge_id}.md").exists())

            listed = run_hive("edge", "list", "--workspace", str(workspace), "--json")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            listed_payload = json_from_stdout(listed)
            self.assertIn(edge_id, {edge["id"] for edge in listed_payload["edges"]})

            compile_result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            pack = workspace / "memory/generated/context-packs/nodes/departments/engineering/PACK.md"
            self.assertIn(f"Shared Edge Context: {edge_id}", pack.read_text(encoding="utf-8"))

            archived = run_hive(
                "edge",
                "archive",
                edge_id,
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--reason",
                "MVP lifecycle coverage",
                "--json",
            )
            self.assertEqual(archived.returncode, 0, archived.stderr)
            self.assertEqual(json_from_stdout(archived)["edge"]["status"], "archived")

            restored = run_hive(
                "edge",
                "restore",
                edge_id,
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(json_from_stdout(restored)["edge"]["status"], "active")

    def test_node_compact_writes_brief_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))

            compact = run_hive(
                "node",
                "compact",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )

            self.assertEqual(compact.returncode, 0, compact.stderr)
            payload = json_from_stdout(compact)
            self.assertTrue(payload["ok"], payload)
            brief = workspace / "memory/records/nodes/departments/engineering/BRIEF.md"
            self.assertTrue(brief.exists())
            self.assertIn("departments/engineering", brief.read_text(encoding="utf-8"))

            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

    def test_edge_compact_writes_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            edge_id = "engineering__marketing__project-launch-x"

            compact = run_hive(
                "edge",
                "compact",
                edge_id,
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )

            self.assertEqual(compact.returncode, 0, compact.stderr)
            payload = json_from_stdout(compact)
            self.assertTrue(payload["ok"], payload)
            brief = workspace / f"memory/records/edges/{edge_id}/BRIEF.md"
            self.assertTrue(brief.exists())
            self.assertIn(edge_id, brief.read_text(encoding="utf-8"))

    def test_scheduler_install_writes_cron_and_launchd_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            scheduler_dir = workspace / "local-overrides/schedulers"

            cron = run_hive("scheduler", "install", "cron", "--workspace", str(workspace), "--json")
            self.assertEqual(cron.returncode, 0, cron.stderr)
            self.assertTrue(json_from_stdout(cron)["ok"])

            launchd = run_hive("scheduler", "install", "launchd", "--workspace", str(workspace), "--json")
            self.assertEqual(launchd.returncode, 0, launchd.stderr)
            self.assertTrue(json_from_stdout(launchd)["ok"])

            self.assertTrue(scheduler_dir.is_dir())
            scheduler_files = {path.name for path in scheduler_dir.iterdir() if path.is_file()}
            self.assertTrue(any("cron" in name for name in scheduler_files), scheduler_files)
            self.assertTrue(any("launchd" in name or name.endswith(".plist") for name in scheduler_files), scheduler_files)

    def test_operation_list_and_show_expose_operation_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            compile_result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)

            listed = run_hive("operation", "list", "--workspace", str(workspace), "--json")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            operations = json_from_stdout(listed)["operations"]
            operation_ids = [operation["id"] for operation in operations]
            operation_types = {operation["type"] for operation in operations}
            self.assertIn("workspace_init", operation_types)
            self.assertIn("context_compile", operation_types)

            shown = run_hive("operation", "show", operation_ids[-1], "--workspace", str(workspace), "--json")
            self.assertEqual(shown.returncode, 0, shown.stderr)
            operation = json_from_stdout(shown)["operation"]
            self.assertEqual(operation["id"], operation_ids[-1])
            self.assertIn("command", operation)
            self.assertIn("rollback", operation)


if __name__ == "__main__":
    unittest.main()
