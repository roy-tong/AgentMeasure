"""F2.10-F2.15 tests: P&L trees, CM ledger, demand audit, intent taxonomy,
decision policy audit, anonymous benchmark.

Common thread: separations are enforced (trees never blend, potential is not
performance, customer data never leaves), and every verdict carries its rule
basis.
"""
import json
import os
import tempfile
import unittest

from am_healthcheck import pnl as pnl_mod
from am_healthcheck import audit as audit_mod
from am_healthcheck import taxonomy as tax_mod
from am_healthcheck import policy as policy_mod
from am_healthcheck import benchmark as bench_mod


def tmpfile(suffix, text, mode="w", encoding="utf-8"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding=encoding, newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


def _orders_rows():
    return [
        {"order_id": "V-1", "amount": 100.0, "currency": "USD",
         "status": "confirmed", "channel": "organic", "campaign_id": "",
         "line": 2},
        {"order_id": "V-2", "amount": 80.0, "currency": "USD",
         "status": "confirmed", "channel": "paid", "campaign_id": "C-1",
         "line": 3},
        {"order_id": "V-3", "amount": 40.0, "currency": "USD",
         "status": "confirmed", "channel": "paid", "campaign_id": "C-1",
         "line": 4},
    ]


CAMPAIGNS = [{"campaign_id": "C-1", "spend": 30.0, "conversations": 500,
              "engagements": 120, "conversions": 2, "line": 2}]


class TestF210Trees(unittest.TestCase):
    def test_same_gmv_labelled_tree_and_campaign(self):
        report = pnl_mod.pnl_trees(_orders_rows(), CAMPAIGNS)
        self.assertEqual(report["trees"]["organic"]["attributed_revenue"], 100.0)
        self.assertEqual(report["trees"]["paid"]["attributed_revenue"], 120.0)
        self.assertEqual(report["trees"]["paid"]["by_campaign"]["C-1"]["orders"], 2)

    def test_paid_funnel_roas_inside_the_tree_only(self):
        report = pnl_mod.pnl_trees(_orders_rows(), CAMPAIGNS)
        funnel = report["trees"]["paid"]["funnel"][0]
        self.assertEqual(funnel["roas"], round(120.0 / 30.0, 4))
        # ROAS numerator is Paid-tree revenue only; organic never leaks in.
        self.assertNotEqual(funnel["attributed_revenue"], 220.0)

    def test_paid_order_without_campaign_refused(self):
        rows = [dict(_orders_rows()[1], campaign_id="")]
        with self.assertRaises(pnl_mod.PnlError):
            pnl_mod.pnl_trees(rows, CAMPAIGNS)

    def test_campaign_not_in_ledger_refused(self):
        rows = [dict(_orders_rows()[1], campaign_id="C-GHOST")]
        with self.assertRaises(pnl_mod.PnlError) as ctx:
            pnl_mod.pnl_trees(rows, CAMPAIGNS)
        self.assertIn("mixed attribution", str(ctx.exception))


class TestF211CmLedger(unittest.TestCase):
    def test_full_formula(self):
        costs = [
            {"category": "coupon", "amount": 10.0, "order_id": "V-1", "line": 2},
            {"category": "media_spend", "amount": 30.0, "order_id": "", "line": 3},
            {"category": "platform_cost", "amount": 5.0, "order_id": "", "line": 4},
            {"category": "payment_cost", "amount": 5.0, "order_id": "", "line": 5},
            {"category": "service_fee", "amount": 4.0, "order_id": "", "line": 6},
            {"category": "fulfillment_variance", "amount": 6.0, "order_id": "", "line": 7},
            {"category": "refund", "amount": 40.0, "order_id": "V-3", "line": 8},
        ]
        report = pnl_mod.contribution_margin(_orders_rows(), costs, "2026-09")
        # revenue 220 - (10+30+5+5+4+6+40) = 120
        self.assertEqual(report["attributed_revenue"], 220.0)
        self.assertEqual(report["contribution_margin"], 120.0)
        self.assertEqual(report["contribution_margin_pct"], round(120 / 220, 4))
        self.assertEqual(report["deductions"]["refund"]["rows"], 1)

    def test_unknown_category_refused(self):
        path = tmpfile(".csv", "category,amount\ngoodwill,5\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(pnl_mod.PnlError):
            pnl_mod.load_costs(path)

    def test_negative_cost_refused(self):
        path = tmpfile(".csv", "category,amount\nrefund,-5\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(pnl_mod.PnlError):
            pnl_mod.load_costs(path)


THRESHOLDS = {
    "agent_traffic": {"threshold": 1000},
    "brand_category_intent_share": {"threshold": 0.05},
    "paid_inventory_depth": {"threshold": 50},
    "commercial_task_frequency": {"threshold": 200},
    "conversion_rate": {"threshold": 0.03},
    "contribution_margin_pct": {"threshold": 0.10},
}


class TestF212Audit(unittest.TestCase):
    def _measurements(self, **overrides):
        base = {"agent_traffic": 5000, "brand_category_intent_share": 0.08,
                "paid_inventory_depth": 80, "commercial_task_frequency": 400,
                "conversion_rate": 0.05, "contribution_margin_pct": 0.18}
        base.update(overrides)
        return base

    def test_launch_when_both_axes_meet(self):
        result = audit_mod.audit_channel(self._measurements(), THRESHOLDS)
        self.assertEqual(result["verdict"], "Launch")

    def test_watch_when_potential_ok_performance_fails(self):
        result = audit_mod.audit_channel(
            self._measurements(conversion_rate=0.01,
                               contribution_margin_pct=0.02), THRESHOLDS)
        self.assertEqual(result["verdict"], "Watch")
        self.assertIn("operating is the gap", result["reading"])

    def test_not_ready_when_channel_empty(self):
        result = audit_mod.audit_channel(
            self._measurements(agent_traffic=10,
                               brand_category_intent_share=0.001,
                               paid_inventory_depth=1,
                               commercial_task_frequency=2), THRESHOLDS)
        self.assertEqual(result["verdict"], "Not ready")

    def test_unmeasured_counts_as_not_met_never_assumed(self):
        measurements = self._measurements()
        del measurements["paid_inventory_depth"]
        result = audit_mod.audit_channel(measurements, THRESHOLDS)
        row = [r for r in result["axes"]["channel_potential"]["rows"]
               if r["metric"] == "paid_inventory_depth"][0]
        self.assertIsNone(row["meets"])
        self.assertIn("never assumed", row["note"])

    def test_unknown_metric_refused(self):
        path = tmpfile(".json", json.dumps({"vibes": {"threshold": 1}}))
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(audit_mod.AuditError):
            audit_mod.load_thresholds(path)


class TestF213Taxonomy(unittest.TestCase):
    def test_seed_validates_and_counts_cells(self):
        path = tmpfile(".json", "")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        tax_mod.write_seed_template(path)
        stats = tax_mod.validate_taxonomy(tax_mod.load_taxonomy(path))
        self.assertEqual(stats["clusters_total"], 3)
        self.assertEqual(stats["active"], 2)
        self.assertGreaterEqual(stats["operating_cells"], 3)

    def test_duplicate_ids_break(self):
        doc = {"schema": tax_mod.TAXONOMY_SCHEMA,
               "clusters": [{"id": "IC-1", "task": "a"},
                            {"id": "IC-1", "task": "b"}]}
        with self.assertRaises(tax_mod.TaxonomyError):
            tax_mod.validate_taxonomy(doc)

    def test_retired_without_successor_is_flagged_not_deleted(self):
        doc = {"schema": tax_mod.TAXONOMY_SCHEMA,
               "clusters": [{"id": "IC-1", "task": "a", "status": "retired"}]}
        stats = tax_mod.validate_taxonomy(doc)
        self.assertIn("successor", stats["findings"][0]["finding"])

    def test_overdue_review_named(self):
        doc = {"schema": tax_mod.TAXONOMY_SCHEMA,
               "clusters": [{"id": "IC-1", "task": "a", "owner": "g",
                             "next_review": "2026-01-01"}]}
        import datetime
        stats = tax_mod.validate_taxonomy(
            doc, today=datetime.date(2026, 10, 3))
        self.assertIn("IC-1", stats["overdue_reviews"])


POLICY = {
    "schema": policy_mod.POLICY_SCHEMA,
    "policy_version": "2026.10",
    "risk_policy_ref": "agentic-ops/action-risk-policy#v3",
    "rules": [
        {"rule_id": "R-1", "action_type": "coupon", "tier": "auto",
         "max_value": 10.0},
        {"rule_id": "R-2", "action_type": "coupon", "tier": "approval",
         "max_value": 50.0},
        {"rule_id": "R-3", "action_type": "price_change", "tier": "forbidden"},
    ],
}


class TestF214DecisionPolicy(unittest.TestCase):
    def _executions(self, *rows):
        return rows

    def test_auto_within_bound_complies(self):
        result = policy_mod.audit_executions(
            POLICY, self._executions({"execution_id": "E-1",
                                      "action_type": "coupon", "value": 8.0}))
        self.assertEqual(result["counts"]["complies"], 1)
        self.assertIn("R-1", result["lines"][0]["basis"])

    def test_approval_without_approver_violates(self):
        result = policy_mod.audit_executions(
            POLICY, self._executions({"execution_id": "E-2",
                                      "action_type": "coupon", "value": 40.0}))
        self.assertEqual(result["counts"]["violates"], 1)
        self.assertIn("no approver", result["lines"][0]["basis"])

    def test_approval_with_approver_complies(self):
        result = policy_mod.audit_executions(
            POLICY, self._executions({"execution_id": "E-3",
                                      "action_type": "coupon", "value": 40.0,
                                      "approver": "ops-lead"}))
        self.assertEqual(result["counts"]["complies"], 1)

    def test_forbidden_action_violates_even_with_approver(self):
        result = policy_mod.audit_executions(
            POLICY, self._executions({"execution_id": "E-4",
                                      "action_type": "price_change",
                                      "value": 1.0, "approver": "ceo"}))
        self.assertEqual(result["counts"]["violates"], 1)
        self.assertIn("forbidden", result["lines"][0]["basis"])

    def test_uncovered_action_is_outside_policy_and_named(self):
        result = policy_mod.audit_executions(
            POLICY, self._executions({"execution_id": "E-5",
                                      "action_type": "refund", "value": 5.0}))
        self.assertEqual(result["counts"]["outside_policy"], 1)
        self.assertIn("finding about the policy", result["lines"][0]["basis"])

    def test_policy_without_risk_link_refused(self):
        bad = dict(POLICY, risk_policy_ref="")
        path = tmpfile(".json", json.dumps(bad))
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(policy_mod.PolicyError):
            policy_mod.load_policy(path)


class TestF215Benchmark(unittest.TestCase):
    def _rows(self, brands=6):
        rows = []
        for i in range(brands):
            rows.append({"brand_key": "pseudonym-%d" % i, "bucket": "IC-001",
                         "value": 10.0 + i})
        return rows

    def test_qualified_bucket_publishes_median_band(self):
        doc = bench_mod.export_benchmark(self._rows(), min_brands=5)
        self.assertEqual(len(doc["buckets"]), 1)
        self.assertEqual(doc["buckets"][0]["brands"], 6)
        self.assertEqual(doc["buckets"][0]["median"], 12.5)

    def test_under_populated_bucket_suppressed_without_value(self):
        rows = self._rows(brands=6) + [{"brand_key": "solo", "bucket": "IC-999",
                                        "value": 999.0}]
        doc = bench_mod.export_benchmark(rows, min_brands=5)
        self.assertEqual(len(doc["buckets"]), 1)
        self.assertEqual(doc["suppressed"][0]["bucket"], "IC-999")
        self.assertNotIn("value", doc["suppressed"][0])

    def test_identifier_columns_are_refused(self):
        doc = bench_mod.export_benchmark(self._rows(brands=5), min_brands=2)
        doc["buckets"][0]["brand"] = "Acme"  # someone injects an identifier
        violations = bench_mod.verify_benchmark(doc)
        self.assertTrue(any("brand" in v for v in violations))

    def test_audit_statement_present(self):
        doc = bench_mod.export_benchmark(self._rows(brands=5), min_brands=5)
        self.assertIn("never enters the shared pool", doc["audit_statement"])
        self.assertIn("contract", doc["audit_statement"])


class TestCliWave2(unittest.TestCase):
    def _run(self, *argv):
        import contextlib
        import io
        from am_healthcheck.cli import main
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_pnl_trees_cli(self):
        orders = tmpfile(".csv", "order_id,amount,status,channel,campaign_id\n"
                                 "V-1,100,confirmed,organic,\n"
                                 "V-2,80,confirmed,paid,C-1\n")
        camps = tmpfile(".csv", "campaign_id,spend,conversations,engagements,"
                                "conversions\nC-1,30,500,120,2\n")
        for p in (orders, camps):
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        rc, out, _ = self._run("pnl-trees", "--orders", orders,
                               "--campaigns", camps)
        self.assertEqual(rc, 0)
        self.assertIn("Paid funnel", out)
        self.assertIn("ROAS", out)

    def test_cm_ledger_cli(self):
        orders = tmpfile(".csv", "order_id,amount,status,channel,campaign_id\n"
                                 "V-1,100,confirmed,organic,\n")
        costs = tmpfile(".csv", "category,amount\nservice_fee,4\n")
        for p in (orders, costs):
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        rc, out, _ = self._run("cm-ledger", "--orders", orders,
                               "--costs", costs, "--period", "2026-09")
        self.assertEqual(rc, 0)
        self.assertIn("Contribution Margin", out)

    def test_benchmark_cli(self):
        rows = tmpfile(".csv", "brand_key,bucket,value\n" +
                       "".join("p-%d,IC-001,%d\n" % (i, 10 + i)
                               for i in range(5)))
        self.addCleanup(lambda: os.path.exists(rows) and os.unlink(rows))
        rc, out, _ = self._run("benchmark-export", "--rows", rows,
                               "--min-brands", "5")
        self.assertEqual(rc, 0)
        self.assertIn("safe to share", out)

    def test_decision_audit_cli(self):
        policy = tmpfile(".json", json.dumps(POLICY))
        execs = tmpfile(".jsonl", json.dumps(
            {"execution_id": "E-1", "action_type": "coupon", "value": 5.0})
            + "\n")
        for p in (policy, execs):
            self.addCleanup(lambda p=p: os.path.exists(p) and os.unlink(p))
        rc, out, _ = self._run("decision-audit", "--policy", policy,
                               "--executions", execs)
        self.assertEqual(rc, 0)
        self.assertIn("complies", out)


if __name__ == "__main__":
    unittest.main()
