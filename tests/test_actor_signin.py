from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.support import init_basic_workspace, json_from_stdout, load_yaml, run_hive


class ActorSigninTests(unittest.TestCase):
    def test_actor_signin_uses_assignment_and_compiles_inherited_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))

            result = run_hive(
                "actor",
                "signin",
                "agent:codex-engineering-001",
                "--workspace",
                str(workspace),
                "--require-assignment",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json_from_stdout(result)
            self.assertTrue(payload["ok"], payload)
            signin = payload["signin"]
            self.assertEqual(signin["actor"], "agent:codex-engineering-001")
            self.assertEqual(signin["effective_node"], "departments/engineering")
            self.assertEqual(signin["assignment"], "assignment_codex_engineering_001")
            self.assertIn("org", signin["inherited_nodes"])
            self.assertIn("engineering__marketing__project-launch-x", signin["connected_edges"])
            self.assertTrue(Path(payload["signin_path"]).exists())
            self.assertTrue(Path(payload["context_pack"]).exists())
            self.assertTrue(Path(payload["manifest"]).exists())

            pack_text = Path(payload["context_pack"]).read_text(encoding="utf-8")
            self.assertIn("Parent Context: org", pack_text)
            self.assertIn("Target Context", pack_text)
            self.assertIn("Shared Edge Context: engineering__marketing__project-launch-x", pack_text)
            self.assertIn("Load context pack", payload["bootstrap"])

            record = load_yaml(Path(payload["signin_path"]))
            self.assertEqual(record["context_pack"], signin["context_pack"])
            self.assertEqual(record["loaded_context_packs"][0]["target"], "departments/engineering")

    def test_actor_signin_can_use_explicit_home_node_without_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))

            result = run_hive(
                "actor",
                "signin",
                "agent:adhoc-research-001",
                "--workspace",
                str(workspace),
                "--home-node",
                "departments/marketing",
                "--role",
                "observer",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json_from_stdout(result)
            signin = payload["signin"]
            self.assertEqual(signin["effective_node"], "departments/marketing")
            self.assertEqual(signin["role"], "observer")
            self.assertIsNone(signin["assignment"])
            self.assertEqual(signin["personal_memory_home"], "memory/records/agents/agent_adhoc-research-001/")
            self.assertTrue((workspace / signin["personal_memory_home"]).is_dir())

    def test_actor_refresh_updates_existing_signin_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            signin_result = run_hive(
                "actor",
                "signin",
                "agent:codex-engineering-001",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(signin_result.returncode, 0, signin_result.stderr)
            signin_id = json_from_stdout(signin_result)["signin"]["id"]

            refresh = run_hive(
                "actor",
                "refresh",
                signin_id,
                "--workspace",
                str(workspace),
                "--json",
            )

            self.assertEqual(refresh.returncode, 0, refresh.stderr)
            payload = json_from_stdout(refresh)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["signin"]["id"], signin_id)
            self.assertEqual(payload["signin"]["refresh_count"], 1)
            self.assertIn("refreshed_at", payload["signin"])
            self.assertTrue(Path(payload["context_pack"]).exists())

            operations = run_hive("operation", "list", "--workspace", str(workspace), "--json")
            self.assertEqual(operations.returncode, 0, operations.stderr)
            operation_types = {item["type"] for item in json_from_stdout(operations)["operations"]}
            self.assertIn("actor_signin", operation_types)
            self.assertIn("actor_refresh", operation_types)


if __name__ == "__main__":
    unittest.main()
