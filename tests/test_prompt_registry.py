from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from hive_synapse.prompts import (
    IMPORT_CLASSIFY_PROMPT,
    PROMOTION_SWEEP_PROMPT,
    SESSION_OUTBOX_README_PROMPT,
    prompt_catalog,
)
from tests.support import init_basic_workspace, json_from_stdout, load_yaml, run_hive


class PromptRegistryTests(unittest.TestCase):
    def test_prompt_catalog_is_unique_and_auditable(self) -> None:
        catalog = prompt_catalog()
        full_ids = [item["full_id"] for item in catalog]
        self.assertEqual(len(full_ids), len(set(full_ids)))
        self.assertIn("import_classify.v1", full_ids)
        self.assertIn("import_compact.v1", full_ids)
        self.assertIn("promotion_sweep.v1", full_ids)
        self.assertIn("session_bootstrap.v1", full_ids)
        for item in catalog:
            self.assertTrue(item["purpose"])
            self.assertIn(item["kind"], {"chat", "text"})

    def test_chat_and_text_prompts_render_from_registry(self) -> None:
        messages = IMPORT_CLASSIFY_PROMPT.render_messages(
            import_id="import_123",
            target="departments/research",
            source_type="markdown",
            text="Research policy note.",
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Return only JSON", messages[0]["content"])
        self.assertIn("departments/research", messages[1]["content"])

        sweep = PROMOTION_SWEEP_PROMPT.render_messages(
            candidate_metadata="id: mem_123",
            candidate_body="Candidate body",
        )
        self.assertIn("risk_flags", sweep[0]["content"])
        self.assertIn("Candidate body", sweep[1]["content"])

        readme = SESSION_OUTBOX_README_PROMPT.render(
            actor_id="agent:bethesda",
            session_id="signin_123",
            target="departments/consumer-marketing",
        )
        self.assertIn("memory-delta.jsonl", readme)
        self.assertIn('"target":"departments/consumer-marketing"', readme)

    def test_model_run_records_prompt_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            add = run_hive(
                "import",
                "add",
                "departments/engineering",
                "Durable policy decision for prompt metadata.",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            import_id = json_from_stdout(add)["import_id"]

            classify = run_hive(
                "import",
                "classify",
                import_id,
                "--workspace",
                str(workspace),
                "--llm-profile",
                "deterministic",
                "--json",
            )
            self.assertEqual(classify.returncode, 0, classify.stderr)
            payload = json_from_stdout(classify)
            run_id = payload["classification"]["model_run"]
            run_path = workspace / "memory" / "generated" / "llm-runs" / f"{run_id}.yaml"
            record = load_yaml(run_path)
            self.assertEqual(record["prompt_id"], IMPORT_CLASSIFY_PROMPT.id)
            self.assertEqual(record["prompt_version"], IMPORT_CLASSIFY_PROMPT.version)

    def test_generate_structured_does_not_use_inline_message_literals(self) -> None:
        root = Path(__file__).resolve().parents[1] / "src" / "hive_synapse"
        offenders: list[str] = []
        for path in sorted(root.rglob("*.py")):
            if "prompts" in path.parts or path.name == "llm.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
                if name != "generate_structured":
                    continue
                for keyword in node.keywords:
                    if keyword.arg == "messages" and isinstance(keyword.value, ast.List):
                        offenders.append(f"{path}:{node.lineno}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
