"""Console tests — the app-shell surface.

The console is an Operate-mode app: sidebar navigation, views, an overview
that recommends next actions. The tests pin four things: the shell behaves
like the app users know (nav groups, hash-routed views, overview actions);
the flow renders from real verification documents; draft/developer markers
stay banned (and the guard actually fires); and hostile values are escaped.
"""
import json
import os
import tempfile
import unittest

from _support import FIXTURES_DIR, REPO_ROOT

from am_healthcheck import console as console_mod
from am_healthcheck import ledger as ledger_mod
from am_healthcheck import commerce as cm
from am_healthcheck import pnl as pnl_mod
from am_healthcheck import audit as audit_mod
from am_healthcheck import policy as policy_mod

EXPORT = os.path.join(FIXTURES_DIR, "vendor-export-intercom.csv")
CFIX = os.path.join(FIXTURES_DIR, "commerce")


def tmpfile(suffix, text, mode="w", encoding="utf-8"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding=encoding, newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


def build_ledger():
    contract = tmpfile(".json", json.dumps({"reopen_window_hours": 72}))
    billing = tmpfile(".csv", "conversation_id,amount\nC-1001,0.99\n")
    confirmations = tmpfile(".csv", "conversation_id,status,amount\n"
                                    "C-1003,credited,0.99\n")
    paths = [contract, billing, confirmations]
    doc = ledger_mod.build_ledger_document(
        EXPORT, "intercom", contract_path=contract, ledger_path=billing,
        confirmations_path=confirmations)
    return doc, paths


class TestBillingShell(unittest.TestCase):
    def setUp(self):
        self.doc, self.paths = build_ledger()
        for p in self.paths:
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        self.page = console_mod.build_console(
            meta={"title": "Bill verification", "vendor": "Intercom Fin",
                  "period": "August 2026", "buyer": "ACME CX"},
            ledger=self.doc)

    def test_sidebar_with_groups_and_hash_routes(self):
        self.assertIn("AgentMeasure", self.page)
        self.assertIn("Bill verification", self.page)  # group label
        for view in ("overview", "data", "recount", "standard", "money",
                     "pack", "recovery"):
            self.assertIn('id="view-%s"' % view, self.page)
            self.assertIn("href='#/%s'" % view, self.page)
        self.assertIn("nav-item", self.page)

    def test_overview_recommends_next_actions(self):
        self.assertIn("Recommended next steps", self.page)
        over = self.doc["tier1"]["counts"]["billed_but_not_billable"]
        self.assertIn("Review the %d conversation(s)" % over, self.page)
        self.assertIn("Send the evidence pack", self.page)
        outstanding = self.doc["recovery"]["totals"]["outstanding"]
        self.assertIn("Follow up %s" % outstanding, self.page)

    def test_numbers_come_from_the_document(self):
        variance = self.doc["tier1"]["variance"]
        self.assertIn("%.2f" % variance, self.page)

    def test_no_js_network_and_hash_router_present(self):
        self.assertIn("hashchange", self.page)
        self.assertNotIn("fetch(", self.page)
        self.assertNotIn("XMLHttpRequest", self.page)
        stripped = self.page.replace("http://www.w3.org", "")
        self.assertNotIn("http://", stripped)
        self.assertNotIn("https://", stripped)

    def test_draft_markers_banned(self):
        for marker in console_mod.BANNED_MARKERS:
            self.assertNotIn(marker, self.page)

    def test_marker_guard_actually_fires(self):
        doc = json.loads(json.dumps(self.doc))
        doc["vendor"]["name"] = "Intercom Tier 1"
        with self.assertRaises(ValueError):
            console_mod.build_console(meta={"title": "x"}, ledger=doc)

    def test_hostile_buyer_escaped(self):
        doc = json.loads(json.dumps(self.doc))
        page = console_mod.build_console(
            meta={"title": "Bill verification",
                  "buyer": "<script>alert(1)</script>"},
            ledger=doc)
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)


class TestChannelShell(unittest.TestCase):
    def setUp(self):
        schema = json.loads(open(os.path.join(
            REPO_ROOT, "schemas", "commerce-profile.schema.json"),
            encoding="utf-8").read())
        events = cm.load_events(os.path.join(CFIX, "agent-events.jsonl"),
                                schema)
        orders = cm.load_orders(os.path.join(CFIX, "merchant-orders.csv"))
        payments = cm.load_payments(os.path.join(CFIX, "merchant-payments.csv"))
        self.receipt = cm.reconcile(events, orders, payments, "1.0.0")
        self.margin = pnl_mod.contribution_margin([
            {"order_id": "V-1", "amount": 100.0, "status": "confirmed",
             "channel": "organic", "campaign_id": "", "line": 2}], [
            {"category": "coupon", "amount": 10.0, "order_id": "", "line": 2}],
            "2026-09")
        self.audit = audit_mod.audit_channel(
            {"agent_traffic": 5000, "brand_category_intent_share": 0.08,
             "paid_inventory_depth": 80, "commercial_task_frequency": 400,
             "conversion_rate": 0.01, "contribution_margin_pct": 0.02},
            {m: {"threshold": t} for m, t in [
                ("agent_traffic", 1000), ("conversion_rate", 0.03)]})

    def test_channel_group_only_when_documents_exist(self):
        doc, paths = build_ledger()
        for p in paths:
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        billing_only = console_mod.build_console(meta={"title": "t"},
                                                 ledger=doc)
        self.assertNotIn("Agent channel", billing_only)
        self.assertNotIn("Offer guardrails", billing_only)

        full = console_mod.build_console(
            meta={"title": "Operations review"},
            receipt=self.receipt, margin=self.margin,
            channel_audit=self.audit)
        self.assertIn("Agent channel", full)
        for view in ("receipt", "margin", "readiness"):
            self.assertIn('id="view-%s"' % view, full)

    def test_receipt_materiality_in_plain_language(self):
        page = console_mod.build_console(meta={"title": "t"},
                                         receipt=self.receipt)
        self.assertIn("The verified number is", page)
        self.assertIn("Net revenue after refunds", page)


class TestDecisionGuardrails(unittest.TestCase):
    def test_findings_render_with_policy_basis(self):
        policy_path = tmpfile(".json", json.dumps({
            "schema": "agentmeasure.commerce/decision-policy",
            "policy_version": "2026.10",
            "risk_policy_ref": "agentic-ops/action-risk-policy#v3",
            "rules": [{"rule_id": "R-1", "action_type": "coupon",
                       "tier": "auto", "max_value": 10.0},
                      {"rule_id": "R-2", "action_type": "coupon",
                       "tier": "approval", "max_value": 50.0}]}))
        self.addCleanup(lambda: os.path.exists(policy_path)
                        and os.unlink(policy_path))
        policy = policy_mod.load_policy(policy_path)
        result = policy_mod.audit_executions(policy, [
            {"execution_id": "E-9", "action_type": "coupon", "value": 40.0}])
        page = console_mod.build_console(meta={"title": "t"}, decisions=result)
        self.assertIn("Offer guardrails", page)
        self.assertIn("Violations", page)
        self.assertIn("no approver", page)


class TestWriteConsole(unittest.TestCase):
    def test_write_round_trips(self):
        doc, paths = build_ledger()
        for p in paths:
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        page = console_mod.build_console(meta={"title": "t"}, ledger=doc)
        out = tmpfile(".html", "")
        self.addCleanup(lambda: os.path.exists(out) and os.unlink(out))
        written = console_mod.write_console(page, out)
        with open(written, encoding="utf-8") as fh:
            self.assertIn("AgentMeasure", fh.read())


if __name__ == "__main__":
    unittest.main()
