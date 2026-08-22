"""Connector tests (CAL-001): three-tier authorization, immediate revocation,
signed aggregate-only export, tamper detection."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab import connector
from agentmeasure_lab.connector import ConnectorError
from tests._support import TASK_SET_NAME, LabWorkspace, base_manifest, generate_production_events, load_json


class TestConnector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = LabWorkspace()
        cls.report, cls.run_dir, _ = cls.ws.run(
            base_manifest(experiment_id="conn-test", seed=7, replicates=8)
        )
        cls.tasks = load_json(os.path.join(cls.ws.tmp, TASK_SET_NAME))["tasks"]
        cls.events_path = os.path.join(cls.ws.tmp, "prod-events.jsonl")
        generate_production_events(
            cls.events_path,
            experiment_id="conn-test",
            seed=11,
            arm_selection_probs={"control": 0.4, "clear": 0.45},
            n_per_arm=300,
            task_ids=[t["id"] for t in cls.tasks],
        )

    @classmethod
    def tearDownClass(cls):
        cls.ws.close()

    def _workspace(self):
        tmp = tempfile.mkdtemp(prefix="am-connector-")
        config_path = os.path.join(tmp, "connector.json")
        connector.save_config(connector.default_config("conn-test"), config_path)
        return tmp, config_path

    def test_default_tiers_are_local_only(self):
        _, config_path = self._workspace()
        config = connector.load_config(config_path)
        self.assertEqual(set(config["authorization"].values()), {"local"})

    def test_off_tier_not_collected(self):
        _, config_path = self._workspace()
        config = connector.load_config(config_path)
        connector.set_tier(config, "choice", "off")
        events = [json.loads(l) for l in open(self.events_path, encoding="utf-8")]
        agg = connector.aggregate_local(events, config)
        for arm in agg["counts"].values():
            self.assertEqual(arm["reach"], 0, "choice=off must drop reach events before aggregation")
            self.assertEqual(arm["selected"], 0)
        # execution/consumption still local
        some_arm = next(iter(agg["counts"].values()))
        self.assertGreater(some_arm["operations"], 0)

    def test_export_signed_and_verifiable(self):
        tmp, config_path = self._workspace()
        key_path = os.path.join(tmp, "connector.key")
        config = connector.load_config(config_path)
        for c in ("choice", "execution", "consumption"):
            connector.set_tier(config, c, "export")
        connector.save_config(config, config_path)

        out_path = os.path.join(tmp, "export.json")
        payload = connector.export(config_path, self.events_path, out_path, key_path)
        self.assertEqual(payload["excluded_classes"], [])
        self.assertTrue(payload["signature"])

        result = connector.verify_export(out_path, key_path)
        self.assertTrue(result["signature_valid"])
        self.assertTrue(result["key_id_matches"])

    def test_export_contains_counts_only(self):
        tmp, config_path = self._workspace()
        config = connector.load_config(config_path)
        connector.set_tier(config, "choice", "export")
        connector.set_tier(config, "execution", "export")
        connector.save_config(config, config_path)
        out_path = os.path.join(tmp, "export.json")
        connector.export(config_path, self.events_path, out_path, os.path.join(tmp, "connector.key"))
        payload = load_json(out_path)
        raw = open(out_path, encoding="utf-8").read()
        self.assertNotIn("assignment_id", raw, "no per-assignment rows may appear in an export")
        self.assertNotIn("selected_id", raw, "no per-event choice detail may appear in an export")
        self.assertTrue(all(isinstance(v, int) for arm in payload["counts"].values() for v in arm.values()))

    def test_local_tier_excluded_from_export(self):
        tmp, config_path = self._workspace()
        config = connector.load_config(config_path)
        connector.set_tier(config, "choice", "export")
        connector.set_tier(config, "execution", "local")  # local: aggregated, never exported
        connector.save_config(config, config_path)
        out_path = os.path.join(tmp, "export.json")
        payload = connector.export(config_path, self.events_path, out_path, os.path.join(tmp, "connector.key"))
        self.assertIn("execution", payload["excluded_classes"])
        for arm in payload["counts"].values():
            self.assertEqual(arm["operations"], 0, "execution=local must not appear in export counts")

    def test_revocation_is_immediate(self):
        tmp, config_path = self._workspace()
        connector.revoke(config_path)
        with self.assertRaises(ConnectorError):
            connector.export(config_path, self.events_path, os.path.join(tmp, "x.json"),
                             os.path.join(tmp, "connector.key"))

    def test_tampered_export_fails_verification(self):
        tmp, config_path = self._workspace()
        key_path = os.path.join(tmp, "connector.key")
        config = connector.load_config(config_path)
        connector.set_tier(config, "choice", "export")
        connector.save_config(config, config_path)
        out_path = os.path.join(tmp, "export.json")
        connector.export(config_path, self.events_path, out_path, key_path)

        payload = load_json(out_path)
        arm = next(iter(payload["counts"]))
        payload["counts"][arm]["reach"] += 1000  # inflate a count after signing
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        result = connector.verify_export(out_path, key_path)
        self.assertFalse(result["signature_valid"])

    def test_invalid_tier_rejected(self):
        config = connector.default_config("x")
        with self.assertRaises(ConnectorError):
            connector.set_tier(config, "choice", "full-raw")
        with self.assertRaises(ConnectorError):
            connector.set_tier(config, "prompts", "export")


if __name__ == "__main__":
    unittest.main()
