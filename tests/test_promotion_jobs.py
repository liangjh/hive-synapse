from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import run_hive


class PromotionJobTests(unittest.TestCase):
    def test_promote_review_apply_updates_current_and_observes_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            dirty_before = set((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))
            proposal_id = "promotion_demo_001"
            review = run_hive(
                "promote",
                "review",
                proposal_id,
                "--workspace",
                str(workspace),
                "--decision",
                "approved",
                "--actor",
                "steward:engineering",
                "--rationale",
                "source backed",
                "--json",
            )
            self.assertEqual(review.returncode, 0, review.stderr)
            apply = run_hive(
                "promote",
                "apply",
                proposal_id,
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )
            self.assertEqual(apply.returncode, 0, apply.stderr)
            payload = json.loads(apply.stdout)
            self.assertTrue(Path(payload["published_path"]).exists())
            current = workspace / "memory/records/nodes/departments/engineering/CURRENT.md"
            self.assertIn("Published Memory: mem_demo_engineering_practice_001", current.read_text())
            self.assertIsNone(payload["invalidation"])
            dirty_after = set((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))
            self.assertEqual(dirty_after, dirty_before)
            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

    def test_unauthorized_promotion_apply_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            result = run_hive(
                "promote",
                "apply",
                "promotion_demo_001",
                "--workspace",
                str(workspace),
                "--actor",
                "agent:codex-engineering-001",
                "--json",
            )
            self.assertNotEqual(result.returncode, 0)

    def test_promotability_sweep_can_create_proposals_without_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            result = run_hive("promote", "sweep", "--workspace", str(workspace), "--create-proposals", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["promotable"])
            self.assertTrue(payload["created_proposals"])
            self.assertFalse((workspace / "memory/records/nodes/departments/engineering/published").exists())

    def test_job_queue_claim_run_and_watchdog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            enqueue = run_hive(
                "job",
                "enqueue",
                "context_rebuild",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--reason",
                "test rebuild",
                "--json",
            )
            self.assertEqual(enqueue.returncode, 0, enqueue.stderr)
            run = run_hive("job", "run", "--workspace", str(workspace), "--runner", "runner:test", "--json")
            self.assertEqual(run.returncode, 0, run.stderr)
            payload = json.loads(run.stdout)
            self.assertEqual(payload["job"]["status"], "completed")
            self.assertTrue(list((workspace / "memory/jobs/completed").glob("*.yaml")))
            watchdog = run_hive("job", "watchdog", "--workspace", str(workspace), "--json")
            self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
            self.assertIn("finding_count", json.loads(watchdog.stdout))


if __name__ == "__main__":
    unittest.main()
