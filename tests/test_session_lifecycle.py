from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from tests.support import init_basic_workspace, json_from_stdout, load_yaml, run_hive


class SessionLifecycleTests(unittest.TestCase):
    def test_session_start_materializes_codex_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = init_basic_workspace(root)
            mount = root / "bethesda-mount"

            result = run_hive(
                "session",
                "start",
                "agent:codex-engineering-001",
                "--workspace",
                str(workspace),
                "--adapter",
                "codex",
                "--output",
                str(mount),
                "--require-assignment",
                "--purpose",
                "Verify Codex session materialization",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json_from_stdout(result)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["adapter"], "codex")
            self.assertEqual(payload["effective_node"], "departments/engineering")
            self.assertEqual(Path(payload["mount"]), mount.resolve())

            agents = mount / "AGENTS.md"
            context = mount / ".hive" / "context"
            outbox = mount / ".hive" / "outbox"
            self.assertTrue(agents.exists())
            self.assertTrue((context / "SOUL.md").exists())
            self.assertTrue((context / "CONTEXT.md").exists())
            self.assertTrue((context / "USER.md").exists())
            self.assertTrue((context / "MEMORY.md").exists())
            self.assertTrue((context / "SCOPE.yaml").exists())
            self.assertTrue((context / "manifest.yaml").exists())
            self.assertTrue((outbox / "README.md").exists())

            self.assertIn("read-only", agents.read_text(encoding="utf-8"))
            self.assertFalse(agents.stat().st_mode & stat.S_IWUSR)
            manifest = load_yaml(context / "manifest.yaml")
            self.assertEqual(manifest["adapter"], "codex")
            self.assertEqual(manifest["actor"], "agent:codex-engineering-001")
            self.assertEqual(manifest["effective_node"], "departments/engineering")
            scope = load_yaml(context / "SCOPE.yaml")
            self.assertEqual(scope["write_scope"]["shared_memory_policy"], "submit_memory_delta_then_promote")

    def test_session_finish_collects_private_and_shared_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = init_basic_workspace(root)
            mount = root / "session-mount"
            start = run_hive(
                "session",
                "start",
                "agent:codex-engineering-001",
                "--workspace",
                str(workspace),
                "--adapter",
                "codex",
                "--output",
                str(mount),
                "--require-assignment",
                "--json",
            )
            self.assertEqual(start.returncode, 0, start.stderr)
            start_payload = json_from_stdout(start)
            outbox = Path(start_payload["outbox"])
            delta_path = outbox / "memory-delta.jsonl"
            delta_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "observation",
                                "summary": "Bethesda private preference should persist.",
                                "body": "Keep this as actor-private session memory.",
                                "target_scope": "private",
                                "confidence": 0.8,
                                "tags": ["private", "session"],
                            }
                        ),
                        json.dumps(
                            {
                                "type": "decision",
                                "summary": "Marketing session deltas should become candidates.",
                                "body": "Shared reusable knowledge should enter import, compaction, and proposal workflows.",
                                "target_scope": "node_candidate",
                                "target": "departments/engineering",
                                "confidence": 0.9,
                                "tags": ["shared", "session"],
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            finish = run_hive(
                "session",
                "finish",
                str(mount),
                "--workspace",
                str(workspace),
                "--json",
            )

            self.assertEqual(finish.returncode, 0, finish.stderr)
            payload = json_from_stdout(finish)
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["delta_count"], 2)
            self.assertEqual(payload["private_delta_count"], 1)
            self.assertEqual(payload["shared_delta_count"], 1)
            self.assertEqual(len(payload["imports"]), 1)
            self.assertEqual(len(payload["proposals"]), 1)

            private_memory = Path(payload["private_memory"])
            self.assertIn("Bethesda private preference", private_memory.read_text(encoding="utf-8"))
            session_dir = Path(payload["session_dir"])
            self.assertTrue((session_dir / "SESSION.md").exists())
            self.assertTrue((session_dir / "finish.yaml").exists())
            self.assertTrue((session_dir / "memory-delta.normalized.jsonl").exists())
            self.assertTrue((session_dir / "outbox" / "memory-delta.jsonl").exists())

            proposal = payload["proposals"][0]
            proposal_path = workspace / "memory" / "proposals" / f"{proposal['id']}.yaml"
            self.assertTrue(proposal_path.exists())
            candidate_path = Path(payload["imports"][0]["compaction"]["candidate_path"])
            self.assertTrue(candidate_path.exists())
            self.assertIn("Marketing session deltas", candidate_path.read_text(encoding="utf-8"))

    def test_session_finish_can_collect_without_processing_shared_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = init_basic_workspace(root)
            mount = root / "session-mount"
            start = run_hive(
                "session",
                "start",
                "agent:codex-engineering-001",
                "--workspace",
                str(workspace),
                "--adapter",
                "codex",
                "--output",
                str(mount),
                "--require-assignment",
                "--json",
            )
            self.assertEqual(start.returncode, 0, start.stderr)
            outbox = Path(json_from_stdout(start)["outbox"])
            (outbox / "memory-delta.jsonl").write_text(
                json.dumps(
                    {
                        "type": "observation",
                        "summary": "Collect but do not compact.",
                        "target_scope": "node_candidate",
                        "target": "departments/engineering",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            finish = run_hive(
                "session",
                "finish",
                str(mount),
                "--workspace",
                str(workspace),
                "--no-process",
                "--json",
            )

            self.assertEqual(finish.returncode, 0, finish.stderr)
            payload = json_from_stdout(finish)
            self.assertEqual(len(payload["imports"]), 1)
            self.assertIn("import", payload["imports"][0])
            self.assertNotIn("compaction", payload["imports"][0])
            self.assertEqual(payload["proposals"], [])


if __name__ == "__main__":
    unittest.main()
