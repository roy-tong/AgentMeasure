"""Buyer MCP: safe local review and invoice extraction tools."""
import json
import unittest

import _support  # noqa: F401  (puts the package root on sys.path)

from verovo_healthcheck import mcp_server as mcp


def call(name, arguments=None):
    response = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": name, "arguments": arguments or {}}})
    assert "error" not in response, response
    return json.loads(response["result"]["content"][0]["text"])


class McpServerTests(unittest.TestCase):
    def test_initialize_and_tool_list(self):
        init = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual("verovo-mcp", init["result"]["serverInfo"]["name"])
        tools = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(["verovo_invoice_intake", "verovo_review", "verovo_review_template", "verovo_recount"],
                         [t["name"] for t in tools["result"]["tools"]])

    def test_review_sample_returns_lanes_levels_and_boundary(self):
        payload = call("verovo_review", {"sample": True})
        result = payload["result"]
        self.assertTrue(result["synthetic"])
        self.assertEqual("PASS", result["lanes"]["charges"]["verdict"])
        self.assertEqual("FAIL", result["lanes"]["delivery"]["verdict"])
        self.assertIn("level_1_rule_consistency", result["conclusion_levels"])
        self.assertIn("verovo decisions", result["conclusion_levels"]["level_3_buyer_decision"])
        self.assertIn("not proof of incorrect billing", result["boundary"])
        self.assertIn("Conclusion levels", payload["report_text"])

    def test_review_template_is_deliberately_incomplete(self):
        template = call("verovo_review_template")
        self.assertEqual([], template["criteria"])
        self.assertEqual("", template["scope"]["buyer"])

    def test_review_requires_exactly_one_source(self):
        for arguments in ({}, {"sample": True, "task_path": "x.json"}):
            response = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                   "params": {"name": "verovo_review", "arguments": arguments}})
            self.assertTrue(response["result"].get("isError"), arguments)
            self.assertIn("mutually exclusive" if arguments else "provide task_path",
                          response["result"]["content"][0]["text"])

    def test_recount_sample_applies_vendor_rules(self):
        payload = call("verovo_recount", {"sample": True})
        self.assertEqual("zendesk", payload["vendor"])
        self.assertIn("Tier 1 Recount", payload["report_text"])

    def test_invoice_intake_mcp_is_unreviewed(self):
        from unittest.mock import patch
        with patch.object(mcp.invoice_intake, "extract_invoice",
                          return_value={"kind": "verovo.invoice-extraction-draft",
                                        "review_status": "unreviewed",
                                        "cost_ledger_status": "not_imported"}):
            payload = call("verovo_invoice_intake", {"file": "invoice.pdf"})
        self.assertEqual("unreviewed", payload["review_status"])
        self.assertEqual("not_imported", payload["cost_ledger_status"])
        response = mcp.handle({"jsonrpc": "2.0", "id": 12, "method": "tools/call",
                               "params": {"name": "verovo_invoice_intake", "arguments": {}}})
        self.assertTrue(response["result"]["isError"])

    def test_unknown_tool_is_a_tool_error_not_a_crash(self):
        response = mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                               "params": {"name": "verovo_nope", "arguments": {}}})
        self.assertTrue(response["result"].get("isError"))
        self.assertIn("unknown tool", response["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
