"""Cross-language parity: the browser recount must agree with the Python CLI.

Two implementations of one rule set is exactly how standards drift. The browser
recount (website/recount.js) exists so a buyer can run the Tier 1 check with no
upload, and the CLI (healthcheck/am_healthcheck/vendors.py) exists so it can run
in CI. They read the same rules file and MUST produce the same verdicts.

These tests run the node implementation and compare it field by field with the
Python one on the same fixtures. They skip when node is unavailable, so the
suite still runs on a machine without it; CI installs node and therefore always
exercises them.
"""
import json
import os
import shutil
import subprocess
import unittest

from _support import REPO_ROOT, fixture

from am_healthcheck.vendors import load_export, recount

NODE_CANDIDATES = [
    "node",
    os.path.expanduser("~/.workbuddy/binaries/node/versions/22.22.2/bin/node"),
]

HARNESS = os.path.join(REPO_ROOT, "conformance", "runners", "parity_recount.js")

# The fields that must match exactly. Everything the statement prints comes
# from these, so a drift here is a drift in the deliverable.
COMPARED = [
    "vendor_id", "vendor_name", "vendor_rule_confidence", "vendor_rule_source",
    "unit_price", "currency", "total_conversations", "billed_by_vendor",
    "counts", "net_findings", "cannot_settle_share", "columns_missing",
    "variance", "overcharge_amount", "undercharge_amount",
    "cannot_settle_amount",
]


def _node():
    for candidate in NODE_CANDIDATES:
        found = shutil.which(candidate) if os.sep not in candidate else (
            candidate if os.path.isfile(candidate) else None)
        if found:
            return found
    return None


class TestRecountParity(unittest.TestCase):
    def setUp(self):
        self.node = _node()
        if not self.node:
            self.skipTest("node not available; parity runs in CI")

    def _js(self, export_path, vendor):
        proc = subprocess.run([self.node, HARNESS, export_path, vendor],
                              capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            self.fail("node harness failed: %s" % proc.stderr.strip())
        return json.loads(proc.stdout)

    def _assert_parity(self, export_path, vendor):
        py = recount(load_export(export_path), vendor)
        js = self._js(export_path, vendor)
        for field in COMPARED:
            if field not in py and field not in js:
                continue
            self.assertIn(field, js, "JS result missing %s" % field)
            self.assertIn(field, py, "Python result missing %s" % field)
            self.assertEqual(
                py[field], js[field],
                "parity drift on %r: python=%r js=%r" % (field, py[field], js[field]))
        # The per-conversation verdicts must line up too, not just the totals.
        self.assertEqual(len(py["verdicts"]), len(js["verdicts"]))
        for a, b in zip(py["verdicts"], js["verdicts"]):
            self.assertEqual(a, b, "verdict drift on line %s" % a.get("line"))

    def test_parity_intercom_fixture(self):
        self._assert_parity(fixture("vendor-export-intercom.csv"), "intercom")

    def test_parity_every_vendor(self):
        # The same fixture under each vendor's rules: the rule table itself is
        # part of what must not drift.
        for vendor in ("intercom", "zendesk", "hubspot", "ada", "salesforce", "generic"):
            with self.subTest(vendor=vendor):
                self._assert_parity(fixture("vendor-export-intercom.csv"), vendor)

    def test_parity_when_a_required_column_is_absent(self):
        import tempfile
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                          encoding="utf-8", newline="")
        tmp.write("conversation_id,issue_addressed,"
                  "customer_recontacted_within_window,vendor_billed\n")
        tmp.write("C1,yes,no,yes\n")
        tmp.close()
        self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
        self._assert_parity(tmp.name, "intercom")


if __name__ == "__main__":
    unittest.main()
