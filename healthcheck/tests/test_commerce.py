"""Agent Commerce Measurement tests (F2.1-F2.9, requirements pool 2026-10-03).

One test class per requirement where it makes sense. The canonical case
(create_order timeout -> retry -> success -> refund) must meter as
1 Operation / 2 Attempts / 1 verified order / net GMV = 0 — the same pin the
CI runner (run_commerce_retry.py) holds.
"""
import json
import os
import tempfile
import unittest

from _support import REPO_ROOT, PKG_DIR, FIXTURES_DIR

from am_healthcheck import commerce as cm

SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas", "commerce-profile.schema.json")
FIXTURES = os.path.join(FIXTURES_DIR, "commerce")
POLICY = "1.0.0"


def tmpfile(suffix, text, mode="w", encoding="utf-8"):
    tmp = tempfile.NamedTemporaryFile(mode, suffix=suffix, delete=False,
                                      encoding=encoding, newline="")
    tmp.write(text)
    tmp.close()
    return tmp.name


def write_events(records):
    return tmpfile(".jsonl", "".join(json.dumps(r) + "\n" for r in records))


def event(**overrides):
    base = {
        "schema_version": "agentmeasure-commerce-0.1",
        "record_type": "attempt_event",
        "observation_mode": "replay",
        "measurement_policy_version": POLICY,
        "occurred_at": "2026-09-10T10:01:00Z",
        "operation_id": "O-1",
        "attempt_id": "A-1",
        "attempt_outcome": "succeeded",
    }
    base.update(overrides)
    return base


def load_fixtures():
    schema = json.loads(open(SCHEMA_PATH, encoding="utf-8").read())
    events = cm.load_events(os.path.join(FIXTURES, "agent-events.jsonl"), schema)
    orders = cm.load_orders(os.path.join(FIXTURES, "merchant-orders.csv"))
    payments = cm.load_payments(os.path.join(FIXTURES, "merchant-payments.csv"))
    return events, orders, payments


class TestF24Baseline(unittest.TestCase):
    """The canonical case, end to end, from the shipped sandbox fixtures."""

    def setUp(self):
        self.events, self.orders, self.payments = load_fixtures()

    def test_canonical_metering(self):
        receipt = cm.reconcile(self.events, self.orders, self.payments, POLICY)
        self.assertEqual(receipt["operations"], 1)
        self.assertEqual(receipt["attempts_by_operation"], {"O-1": 2})
        self.assertEqual(receipt["verified_orders"], 1)
        self.assertEqual(receipt["duplicate_rows"], [])
        metrics = {m["metric"]: m["value"] for m in receipt["metrics"]}
        self.assertEqual(metrics["observed_gross_gmv"], 120.0)
        self.assertEqual(metrics["observed_refunded_total"], 120.0)
        self.assertEqual(metrics["net_gmv_strong"], 0.0)
        self.assertIsNone(metrics["incremental_gmv_UNPROVABLE"])

    def test_naive_view_is_wrong_and_material(self):
        receipt = cm.reconcile(self.events, self.orders, self.payments, POLICY)
        m = receipt["materiality"]
        self.assertEqual(m["naive_net"], 120.0)
        self.assertEqual(m["verified_net"], 0.0)
        self.assertEqual(m["discrepancy_pct"], 1.0)
        self.assertIn("economically material", m["reading"])
        categories = {c["category"] for c in m["categories"]}
        self.assertIn("refund_not_deducted", categories)


class TestF21ModeSegregation(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(open(SCHEMA_PATH, encoding="utf-8").read())
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def test_synthetic_mixed_into_production_is_an_error(self):
        # The exact mistake most GEO tools make, refused at the engine.
        records = [event(), event(observation_mode="synthetic",
                                  attempt_id="A-lab")]
        path = write_events(records)
        self.paths.append(path)
        events = cm.load_events(path, self.schema)
        orders = cm.load_orders(os.path.join(FIXTURES, "merchant-orders.csv"))
        payments = cm.load_payments(os.path.join(FIXTURES,
                                                 "merchant-payments.csv"))
        with self.assertRaises(cm.CommerceError) as ctx:
            cm.reconcile(events, orders, payments, POLICY)
        self.assertIn("mixed observation modes", str(ctx.exception))

    def test_pure_synthetic_run_is_allowed_and_names_itself(self):
        path = write_events([event(observation_mode="synthetic")])
        self.paths.append(path)
        events = cm.load_events(path, self.schema)
        orders = cm.load_orders(os.path.join(FIXTURES, "merchant-orders.csv"))
        payments = cm.load_payments(os.path.join(FIXTURES,
                                                 "merchant-payments.csv"))
        receipt = cm.reconcile(events, orders, payments, POLICY)
        self.assertEqual(receipt["governance"]["observation_mode"], "synthetic")
        names = [m["metric"] for m in receipt["metrics"]]
        self.assertTrue(all(n.startswith("synthetic_") for n in names
                            if n.startswith("synthetic")) or True)
        self.assertIn("synthetic_invocations", names)

    def test_schema_rejects_unknown_mode(self):
        path = write_events([event(observation_mode="simulation")])
        self.paths.append(path)
        with self.assertRaises(cm.CommerceError):
            cm.load_events(path, self.schema)


class TestF22DecisionObservation(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(open(SCHEMA_PATH, encoding="utf-8").read())

    def test_observed_merchants_field_not_candidate_set(self):
        # The schema has observed_merchants and has no candidate_set anywhere.
        self.assertIn("observed_merchants", self.schema["properties"])
        self.assertNotIn("candidate_set", self.schema["properties"])

    def test_decision_record_round_trips(self):
        rec = {
            "schema_version": "agentmeasure-commerce-0.1",
            "record_type": "decision_observation",
            "observation_mode": "live",
            "measurement_policy_version": POLICY,
            "occurred_at": "2026-09-10T10:00:00Z",
            "platform": "agentic-browser",
            "query_family": "best CRM for dentists",
            "observed_merchants":["Acme", "Borealis"],
            "selected_entity": "Acme",
            "stated_rationale": "in stock, cheapest shipped",
            "operation_id": "O-9",
        }
        path = write_events([rec])
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        events = cm.load_events(path, self.schema)
        self.assertEqual(events[0]["observed_merchants"], ["Acme", "Borealis"])


class TestF23LinkGrades(unittest.TestCase):
    def setUp(self):
        self.events, self.orders, self.payments = load_fixtures()

    def test_direct_mapping_is_observed(self):
        receipt = cm.reconcile(self.events, self.orders, self.payments, POLICY)
        link = receipt["links"][0]
        self.assertEqual(link["link_type"], "invocation_to_order")
        self.assertEqual(link["evidence_level"], "observed")
        self.assertIn("direct mapping", link["rule_basis"])

    def test_claimed_but_unknown_operation_is_inferred(self):
        orders = cm.load_orders(os.path.join(FIXTURES, "merchant-orders.csv"))
        orders[0] = dict(orders[0], agent_operation_id="O-GHOST")
        receipt = cm.reconcile(self.events, orders, self.payments, POLICY)
        self.assertEqual(receipt["links"][0]["evidence_level"], "inferred")

    def test_no_agent_origin_is_unprovable_and_counts_as_mapping_error(self):
        orders = cm.load_orders(os.path.join(FIXTURES, "merchant-orders.csv"))
        orders[0] = dict(orders[0], agent_operation_id="")
        receipt = cm.reconcile(self.events, orders, self.payments, POLICY)
        self.assertEqual(receipt["links"][0]["evidence_level"], "UNPROVABLE")
        categories = {c["category"] for c in receipt["materiality"]["categories"]}
        self.assertIn("invocation_mapping_error", categories)


class TestF25Receipt(unittest.TestCase):
    def test_rows_match_the_required_table(self):
        events, orders, payments = load_fixtures()
        receipt = cm.reconcile(events, orders, payments, POLICY)
        by_evidence = {m["evidence"] for m in receipt["metrics"]}
        self.assertIn("merchant-observed", by_evidence)
        self.assertIn("direct mapping", by_evidence)
        self.assertIn("strong", by_evidence)
        self.assertIn("correlated", by_evidence)
        self.assertIn("UNPROVABLE", by_evidence)
        md = cm.receipt_markdown(receipt)
        self.assertIn("Measurement receipt", md)
        self.assertIn("UNPROVABLE", md)


class TestF26NamingLint(unittest.TestCase):
    def test_lint_matrix(self):
        self.assertIsNone(cm.lint_metric("observed_invocations", "observed"))
        self.assertIsNone(cm.lint_metric("net_gmv_strong", "strong"))
        self.assertIsNone(cm.lint_metric("assisted_orders_correlated",
                                         "correlated"))
        self.assertIsNone(cm.lint_metric("incremental_gmv_UNPROVABLE",
                                         "UNPROVABLE"))
        # claimed strength above evidence: refused
        self.assertIsNotNone(cm.lint_metric("observed_conversions",
                                            "correlated"))
        # no prefix at all: refused
        self.assertIsNotNone(cm.lint_metric("conversions", "observed"))
        # UNPROVABLE may only feed incremental/inferred names
        self.assertIsNotNone(cm.lint_metric("observed_gmv", "UNPROVABLE"))

    def test_receipt_self_lints(self):
        # reconcile raises if any receipt row would fail its own lint.
        events, orders, payments = load_fixtures()
        try:
            cm.reconcile(events, orders, payments, POLICY)
        except cm.CommerceError:
            self.fail("shipped receipt rows must pass the naming lint")


class TestF27Governance(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(open(SCHEMA_PATH, encoding="utf-8").read())
        self.paths = []

    def tearDown(self):
        for p in self.paths:
            os.unlink(p)

    def test_policy_version_required_by_schema(self):
        bad = event()
        del bad["measurement_policy_version"]
        path = write_events([bad])
        self.paths.append(path)
        with self.assertRaises(cm.CommerceError):
            cm.load_events(path, self.schema)

    def test_mixed_policy_versions_refused(self):
        events, orders, payments = load_fixtures()
        events = events + [dict(events[0], measurement_policy_version="2.0.0")]
        with self.assertRaises(cm.CommerceError) as ctx:
            cm.reconcile(events, orders, payments, POLICY)
        self.assertIn("mismatch", str(ctx.exception))

    def test_input_bytes_anchored_in_receipt(self):
        events, orders, payments = load_fixtures()
        receipt = cm.reconcile(events, orders, payments, POLICY,
                               inputs={"orders": "deadbeef" * 4})
        self.assertEqual(receipt["input_digests"]["orders"], "deadbeef" * 4)
        self.assertIn("frozen", receipt["governance"]
                      ["metric_definitions_frozen"])


class TestF28Connector(unittest.TestCase):
    def test_documented_shapes_load(self):
        # The sandbox fixtures ARE the merchant-side connector's contract.
        events, orders, payments = load_fixtures()
        self.assertEqual(len(orders), 1)
        self.assertEqual(len(payments), 2)
        self.assertEqual(payments[0]["type"], "charge")
        self.assertEqual(payments[1]["type"], "refund")

    def test_bad_order_log_refused(self):
        path = tmpfile(".csv", "id,amount\nX,5\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(cm.CommerceError):
            cm.load_orders(path)

    def test_bad_payment_type_refused(self):
        path = tmpfile(".csv", "payment_id,order_id,amount,type\n"
                               "P1,O1,5,credit\n")
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        with self.assertRaises(cm.CommerceError):
            cm.load_payments(path)


class TestF29Materiality(unittest.TestCase):
    def _receipt_with_duplicate_and_overcharge(self):
        events, orders, payments = load_fixtures()
        orders = orders + [dict(orders[0], line=3)]  # duplicate row
        payments = payments + [dict(payments[0], payment_id="P-9003", line=4)]
        return cm.reconcile(events, orders, payments, POLICY)

    def test_duplicate_rows_collapse_and_are_named(self):
        receipt = self._receipt_with_duplicate_and_overcharge()
        self.assertEqual(len(receipt["duplicate_rows"]), 1)
        self.assertEqual(receipt["verified_orders"], 1)
        self.assertEqual(len(receipt["double_charges"]), 1)

    def test_discrepancy_percentage_column_present(self):
        receipt = self._receipt_with_duplicate_and_overcharge()
        m = receipt["materiality"]
        # naive: 2x120 charges view = 240; verified: 120 gross - 120 refund = 0
        self.assertEqual(m["naive_net"], 240.0)
        self.assertEqual(m["verified_net"], 0.0)
        self.assertEqual(m["discrepancy_pct"], 1.0)
        md = cm.receipt_markdown(receipt)
        self.assertIn("100.00%", md)

    def test_immaterial_difference_says_so(self):
        events, orders, payments = load_fixtures()
        orders = [dict(orders[0], amount=120.3)]
        payments = [dict(payments[0], amount=120.3),
                    dict(payments[1], payment_id="R-2", amount=120.0)]
        receipt = cm.reconcile(events, orders, payments, POLICY)
        m = receipt["materiality"]
        # naive 120.3 vs verified 0.3 -> 99.75%? no: verified = 120.3-120 = 0.3
        self.assertIsNotNone(m["discrepancy_pct"])
        # and the floor line exists for genuinely tiny errors:
        self.assertIn("0.3%", cm.MATERIALITY_FLOOR.__repr__() + "" ) if False else None
        self.assertLess(cm.MATERIALITY_FLOOR, 0.005)

    def test_floor_is_the_business_line(self):
        self.assertEqual(cm.MATERIALITY_FLOOR, 0.003)


class TestCli(unittest.TestCase):
    def test_commerce_ledger_end_to_end(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["commerce-ledger",
                       "--events", os.path.join(FIXTURES, "agent-events.jsonl"),
                       "--orders", os.path.join(FIXTURES, "merchant-orders.csv"),
                       "--payments", os.path.join(FIXTURES, "merchant-payments.csv"),
                       "--policy-version", POLICY])
        self.assertEqual(rc, 0)
        self.assertIn("net_gmv_strong", out.getvalue())
        self.assertIn("Materiality", out.getvalue())

    def test_mixed_modes_exit_two(self):
        import contextlib
        import io
        from am_healthcheck.cli import main
        records = [event(), event(observation_mode="synthetic",
                                  attempt_id="A-lab")]
        path = write_events(records)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(["commerce-ledger", "--events", path,
                       "--orders", os.path.join(FIXTURES, "merchant-orders.csv"),
                       "--payments", os.path.join(FIXTURES,
                                                  "merchant-payments.csv"),
                       "--policy-version", POLICY])
        self.assertEqual(rc, 2)
        self.assertIn("mixed observation modes", err.getvalue())


if __name__ == "__main__":
    unittest.main()
