from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import run_hive


class ConnectorPersistenceTests(unittest.TestCase):
    def test_connector_and_persistence_registries(self) -> None:
        connectors = run_hive("connector", "list", "--json")
        self.assertEqual(connectors.returncode, 0, connectors.stderr)
        connector_names = {item["name"] for item in json.loads(connectors.stdout)["connectors"]}
        self.assertTrue({"local", "obsidian", "url", "git", "github", "notion", "gdrive"}.issubset(connector_names))
        persistence = run_hive("persistence", "list", "--json")
        self.assertEqual(persistence.returncode, 0, persistence.stderr)
        backends = {item["name"]: item for item in json.loads(persistence.stdout)["backends"]}
        self.assertTrue(backends["filesystem-markdown"]["canonical"])
        self.assertEqual(backends["vector-db"]["status"], "planned")

    def test_remote_fetch_records_connector_external_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            fetch = run_hive(
                "import",
                "fetch",
                "departments/engineering",
                "https://github.com/example/repo/issues/1",
                "--connector",
                "github",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(fetch.returncode, 0, fetch.stderr)
            item = json.loads(fetch.stdout)["item"]
            self.assertEqual(item["source_type"], "github")
            self.assertEqual(item["external_ref"]["owner"], "example")
            self.assertEqual(item["external_ref"]["repo"], "repo")


if __name__ == "__main__":
    unittest.main()
