"""MCP server tests (LAB-009): protocol handshake, read-only tools,
evidence grades, no-ranking contract, calibration awareness."""

import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab import mcp_server
from agentmeasure_lab.mcp_server import handle_message, serve
from tests._support import LabWorkspace, base_manifest


def _call(name, arguments):
    return handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": name, "arguments": arguments}}
    )


def _result_text(response):
    return json.loads(response["result"]["content"][0]["text"])


class TestMcpServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = LabWorkspace()
        cls.report, cls.run_dir, _ = cls.ws.run(
            base_manifest(experiment_id="mcp-test", seed=20260822, replicates=10)
        )

    @classmethod
    def tearDownClass(cls):
        cls.ws.close()

    def test_initialize_handshake(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                               "params": {"protocolVersion": mcp_server.PROTOCOL_VERSION}})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "agentmeasure-lab")
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_tools_list(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, {"get_run_summary", "get_presentation_advice", "get_funnel_metrics"})

    def test_run_summary(self):
        payload = _result_text(_call("get_run_summary", {"run_dir": self.run_dir}))
        self.assertEqual(payload["experiment_id"], "mcp-test")
        self.assertIn("preregistration_hash", payload)
        self.assertIn("run_fingerprint", payload)

    def test_presentation_advice_has_evidence_and_no_ranking(self):
        payload = _result_text(_call("get_presentation_advice", {"run_dir": self.run_dir}))
        self.assertTrue(payload["advice"])
        for a in payload["advice"]:
            self.assertIn("grade", a["evidence"])
            self.assertEqual(a["evidence"]["production_verification"]["status"], "not_performed")
        variants = [a["variant_id"] for a in payload["advice"]]
        self.assertEqual(variants, sorted(variants), "variants must not be ranked")
        self.assertIn("no_ranking", payload)

    def test_funnel_metrics_with_labels(self):
        payload = _result_text(_call("get_funnel_metrics", {"run_dir": self.run_dir, "variant": "clear"}))
        self.assertIn("clear", payload)
        for rate in ("selection_rate", "operation_success_rate", "consumption_rate"):
            entry = payload["clear"][rate]
            self.assertIsNotNone(entry["label"])
            self.assertIn("denominator", entry)

    def test_unknown_tool_is_error(self):
        resp = _call("run_experiment", {"run_dir": self.run_dir})
        self.assertEqual(resp["error"]["code"], -32602)

    def test_missing_report_is_tool_error(self):
        resp = _call("get_run_summary", {"run_dir": "/nonexistent"})
        self.assertEqual(resp["error"]["code"], -32602)

    def test_calibration_report_changes_verification_status(self):
        # Write a minimal calibration report into the run dir, then advice must surface it.
        cal = {
            "schema": "agentmeasure.lab/calibration-report",
            "schema_version": "1.0.0",
            "engine_version": "test",
            "funnel_rules_version": "test",
            "experiment_id": "mcp-test",
            "preregistration": {"manifest_hash": "x", "primary_metric": "selection_rate"},
            "offline_run": {"environment": "controlled"},
            "production_source": {"environment": "production"},
            "variants": [
                {"variant_id": "clear", "calibration": {"calibration": "production_confirmed", "reason": "test"}}
            ],
            "limitations": [],
        }
        path = os.path.join(self.run_dir, "calibration-report.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cal, fh)
        try:
            payload = _result_text(_call("get_presentation_advice", {"run_dir": self.run_dir}))
            for a in payload["advice"]:
                if a["variant_id"] == "clear":
                    self.assertEqual(a["evidence"]["production_verification"]["status"], "production_confirmed")
        finally:
            os.unlink(path)

    def test_stdio_loop(self):
        lines = "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                "not json",
            ]
        )
        out = io.StringIO()
        serve(io.StringIO(lines), out)
        responses = [json.loads(l) for l in out.getvalue().strip().splitlines()]
        self.assertEqual(len(responses), 2, "notification produces no response; parse error does")
        self.assertEqual(responses[0]["id"], 1)
        self.assertEqual(responses[1]["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
