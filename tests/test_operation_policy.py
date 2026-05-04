from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hive_synapse import simple_yaml

from tests.support import init_basic_workspace, json_from_stdout, load_yaml, run_hive


class OperationPolicyTests(unittest.TestCase):
    def test_init_creates_low_noise_operation_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            policy_path = workspace / "policies" / "operations.yaml"

            policy = load_yaml(policy_path)
            context_policy = policy["operation_policies"]["context_invalidation"]
            self.assertEqual(context_policy["mode"], "observe")
            self.assertFalse(context_policy["emit_dirty_markers"])

            show = run_hive("policy", "show", "--workspace", str(workspace), "--json")
            self.assertEqual(show.returncode, 0, show.stderr)
            payload = json_from_stdout(show)
            self.assertEqual(payload["policy"]["id"], "operations_default")

    def test_automatic_promotion_invalidation_observes_default_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            before = set((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))

            self._approve_demo_proposal(workspace)
            apply = run_hive(
                "promote",
                "apply",
                "promotion_demo_001",
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )

            self.assertEqual(apply.returncode, 0, apply.stderr)
            payload = json_from_stdout(apply)
            self.assertIsNone(payload["invalidation"])
            after = set((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))
            self.assertEqual(after, before)

    def test_strict_invalidation_policy_emits_automatic_dirty_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            policy_path = workspace / "policies" / "operations.yaml"
            policy = load_yaml(policy_path)
            policy["operation_policies"]["context_invalidation"]["mode"] = "strict"
            policy_path.write_text(simple_yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
            before = set((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))

            self._approve_demo_proposal(workspace)
            apply = run_hive(
                "promote",
                "apply",
                "promotion_demo_001",
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )

            self.assertEqual(apply.returncode, 0, apply.stderr)
            payload = json_from_stdout(apply)
            self.assertIsNotNone(payload["invalidation"])
            after = set((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))
            self.assertGreater(len(after), len(before))

    def test_compaction_policy_can_disable_over_budget_job_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            budget_path = workspace / "policies" / "context-budget.yaml"
            budget = load_yaml(budget_path)
            budget["budget_tokens"] = 1
            budget_path.write_text(simple_yaml.safe_dump(budget, sort_keys=False), encoding="utf-8")

            policy_path = workspace / "policies" / "operations.yaml"
            policy = load_yaml(policy_path)
            policy["operation_policies"]["compaction"]["mode"] = "off"
            policy_path.write_text(simple_yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
            before = set((workspace / "memory/jobs/pending").glob("job_*.yaml"))

            result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            after = set((workspace / "memory/jobs/pending").glob("job_*.yaml"))
            self.assertEqual(after, before)

    def _approve_demo_proposal(self, workspace: Path) -> None:
        review = run_hive(
            "promote",
            "review",
            "promotion_demo_001",
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


if __name__ == "__main__":
    unittest.main()
