"""Export tests: OTel, Prometheus, and enriched JSON export."""
import json
import unittest

from am_healthcheck.export import to_json_export, to_otel, to_prometheus


def sample_report():
    """A minimal report shaped like `agentmeasure check --json` output."""
    return {
        "schema": 1,
        "tool": "agentmeasure-healthcheck",
        "version": "0.4.0",
        "mode": "own-data",
        "window": "last 7 day(s) of local sessions",
        "overview": {
            "sessions": 2,
            "exec_total": 20,
            "call_total": 25,
            "exec_failed": 3,
            "retry_chains": 2,
            "first_ts": "2026-09-01T00:00:00Z",
            "last_ts": "2026-09-07T00:00:00Z",
        },
        "checks": [
            {"check_id": "HC-01", "name": "Duplicate records",
             "status": "ok", "summary": "no duplicates", "findings": []},
            {"check_id": "HC-02", "name": "Retry amplification",
             "status": "finding", "summary": "2 chains", "findings": []},
            {"check_id": "HC-03", "name": "Tool error runs",
             "status": "ok", "summary": "none", "findings": []},
        ],
        "coverage": [],
    }


class TestOtelExport(unittest.TestCase):
    def test_to_otel_is_valid_json(self):
        out = to_otel(sample_report())
        parsed = json.loads(out)
        self.assertIsInstance(parsed, list)
        self.assertTrue(parsed, "OTel export must contain at least one metric")

    def test_to_otel_has_overview_counters(self):
        parsed = json.loads(to_otel(sample_report()))
        names = {m.get("name") for m in parsed}
        self.assertIn("attempts_total", names)
        self.assertIn("retry_chains_total", names)

    def test_to_otel_has_check_gauges(self):
        parsed = json.loads(to_otel(sample_report()))
        names = {m.get("name") for m in parsed}
        self.assertIn("hc_duplicate_records", names)
        self.assertIn("hc_retry_amplification", names)

    def test_to_otel_missing_audit_checks_encoded_as_unprovable(self):
        # HC-04/05/06 are absent from this report → must be -1, never a
        # silent zero that a dashboard would read as "healthy".
        parsed = json.loads(to_otel(sample_report()))
        hc04 = [m for m in parsed if m.get("name") == "hc_operation_resolution_coverage"]
        self.assertTrue(hc04, "HC-04 metric must still be emitted")
        points = hc04[0]["gauge"]["dataPoints"]
        self.assertEqual(points[0]["asDouble"], -1.0)


class TestPrometheusExport(unittest.TestCase):
    def test_to_prometheus_has_help_and_type(self):
        out = to_prometheus(sample_report())
        self.assertIn("# HELP", out)
        self.assertIn("# TYPE", out)
        self.assertTrue(out.endswith("\n"))

    def test_to_prometheus_contains_metric_names(self):
        out = to_prometheus(sample_report())
        self.assertIn("attempts_total", out)
        self.assertIn("hc_retry_amplification", out)

    def test_to_prometheus_labels_present(self):
        out = to_prometheus(sample_report())
        self.assertIn('window="', out)
        self.assertIn('mode="own-data"', out)

    def test_to_prometheus_gauge_type(self):
        out = to_prometheus(sample_report())
        self.assertIn("hc_duplicate_records", out)
        self.assertIn("# TYPE hc_duplicate_records gauge", out)


class TestJsonExport(unittest.TestCase):
    def test_json_export_adds_audit_summary(self):
        enriched = to_json_export(sample_report())
        self.assertIn("audit_summary", enriched)
        summary = enriched["audit_summary"]
        self.assertIn("overall_verdict", summary)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["total_checks"], 3)

    def test_json_export_adds_recommendations(self):
        enriched = to_json_export(sample_report())
        self.assertIn("recommendations", enriched)
        # HC-02 is a finding → at least one recommendation must mention it
        joined = " ".join(enriched["recommendations"])
        self.assertIn("HC-02", joined)

    def test_json_export_preserves_original_fields(self):
        enriched = to_json_export(sample_report())
        self.assertEqual(enriched["tool"], "agentmeasure-healthcheck")
        self.assertEqual(enriched["overview"]["exec_total"], 20)

    def test_json_export_does_not_mutate_input(self):
        original = sample_report()
        to_json_export(original)
        self.assertNotIn("audit_summary", original)

    def test_json_export_clean_report_verdict(self):
        report = sample_report()
        report["checks"] = [
            {"check_id": "HC-01", "name": "Duplicate records",
             "status": "ok", "summary": "", "findings": []},
        ]
        enriched = to_json_export(report)
        self.assertEqual(enriched["audit_summary"]["overall_verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
