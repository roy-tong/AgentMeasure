"""Settlement bundle tests: effect-confirmed validation and bundle shape."""
import json
import os
import tempfile
import unittest

from am_healthcheck.settle import (bundle_report, generate_bundle,
                                    settlement_statement)


def effect(effect_id="eff-1", outcome_class="resolved",
           observer_grade="affected_party", **extra):
    rec = {
        "effect_id": effect_id,
        "operation_id": "op-1",
        "outcome_class": outcome_class,
        "observer_grade": observer_grade,
        "confirmed_at": "2026-09-18T10:00:00Z",
        "stability_window_seconds": 259200,
    }
    rec.update(extra)
    return rec


class TestGenerateBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write(self, records, name="effects.jsonl"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        return path

    def test_missing_file_raises(self):
        with self.assertRaises(ValueError):
            generate_bundle(
                effects_path=os.path.join(self.tmp.name, "nope.jsonl"),
                output_path=os.path.join(self.tmp.name, "out.json"),
                metadata={})

    def test_single_record_bundle(self):
        path = self._write([effect()])
        out = os.path.join(self.tmp.name, "out.json")
        bundle = generate_bundle(path, out, {"provider": "acme"})
        self.assertTrue(os.path.isfile(out))
        self.assertEqual(bundle["provider_id"], "acme")
        self.assertEqual(bundle["metering_summary"]["total_billable_events"], 1)
        self.assertEqual(len(bundle["outcome_lines"]), 1)

    def test_outcome_class_grouping(self):
        path = self._write([
            effect("e1", "resolved"),
            effect("e2", "resolved"),
            effect("e3", "assumed_resolved", "self_attested"),
            effect("e4", "escalated"),
        ])
        bundle = generate_bundle(
            path, os.path.join(self.tmp.name, "o.json"), {})
        by_class = bundle["metering_summary"]["by_outcome_class"]
        self.assertEqual(by_class["resolved"], 2)
        self.assertEqual(by_class["assumed_resolved"], 1)
        self.assertEqual(by_class["escalated"], 1)

    def test_observer_grade_grouping(self):
        path = self._write([
            effect("e1", "resolved", "affected_party"),
            effect("e2", "resolved", "self_attested"),
            effect("e3", "resolved", "affected_party"),
        ])
        bundle = generate_bundle(
            path, os.path.join(self.tmp.name, "o.json"), {})
        by_grade = bundle["metering_summary"]["by_observer_grade"]
        self.assertEqual(by_grade["affected_party"], 2)
        self.assertEqual(by_grade["self_attested"], 1)

    def test_unknown_outcome_class_rejected(self):
        path = self._write([effect("e1", "totally_made_up")])
        with self.assertRaises(ValueError):
            generate_bundle(path, os.path.join(self.tmp.name, "o.json"), {})

    def test_unknown_observer_grade_rejected(self):
        path = self._write([effect("e1", "resolved", "trust_me_bro")])
        with self.assertRaises(ValueError):
            generate_bundle(path, os.path.join(self.tmp.name, "o.json"), {})

    def test_missing_required_field_rejected(self):
        rec = effect()
        del rec["confirmed_at"]
        path = self._write([rec])
        with self.assertRaises(ValueError):
            generate_bundle(path, os.path.join(self.tmp.name, "o.json"), {})

    def test_incrementality_section_only_when_provided(self):
        path = self._write([effect()])
        plain = generate_bundle(
            path, os.path.join(self.tmp.name, "a.json"), {})
        self.assertNotIn("incrementality_section", plain)

        with_inc = generate_bundle(
            path, os.path.join(self.tmp.name, "b.json"),
            {"evidence_level": "v4_holdout",
             "incrementality_evidence": {
                 "m5_lift_table": {"overall": {"incremental_lift": 0.26}},
                 "unprovable_share": 0.12,
                 "unprovable_reason": "span-layer retry invisibility"}})
        self.assertIn("incrementality_section", with_inc)
        self.assertEqual(
            with_inc["incrementality_section"]["evidence_level"], "v4_holdout")

    def test_output_directory_created(self):
        path = self._write([effect()])
        nested = os.path.join(self.tmp.name, "deep", "dir", "out.json")
        generate_bundle(path, nested, {})
        self.assertTrue(os.path.isfile(nested))

    def test_bundle_is_json_serialisable(self):
        path = self._write([effect()])
        out = os.path.join(self.tmp.name, "o.json")
        generate_bundle(path, out, {})
        with open(out, encoding="utf-8") as fh:
            reloaded = json.load(fh)
        self.assertEqual(reloaded["schema"], "agentmeasure.commercial/settlement-bundle")


class TestBundleReport(unittest.TestCase):
    def test_bundle_report_contains_sections(self):
        bundle = {
            "schema": "agentmeasure.commercial/settlement-bundle",
            "schema_version": "0.1.0",
            "provider_id": "acme",
            "offering_id": "acme:support",
            "evidence_level": "none",
            "metering_summary": {
                "total_billable_events": 10,
                "by_outcome_class": {"resolved": 4, "assumed_resolved": 3,
                                     "escalated": 2, "abandoned": 1},
                "by_observer_grade": {"affected_party": 4, "self_attested": 3},
                "unprovable_count": 0,
            },
            "outcome_lines": [],
        }
        text = bundle_report(bundle)
        self.assertIn("acme", text)
        self.assertIn("resolved", text)
        self.assertIn("assumed_resolved", text)

    def test_bundle_report_handles_empty_summary(self):
        bundle = {
            "schema": "agentmeasure.commercial/settlement-bundle",
            "provider_id": "",
            "offering_id": "",
            "evidence_level": "none",
            "metering_summary": {
                "total_billable_events": 0,
                "by_outcome_class": {},
                "by_observer_grade": {},
                "unprovable_count": 0,
            },
            "outcome_lines": [],
        }
        text = bundle_report(bundle)
        self.assertIsInstance(text, str)
        self.assertTrue(text.strip())


class TestSettlementStatement(unittest.TestCase):
    """The two-line statement (COMMERCIAL 5.1): both directions, netted."""

    def _bundle(self, lines):
        by_class, by_grade = {}, {}
        for r in lines:
            by_class[r["outcome_class"]] = by_class.get(r["outcome_class"], 0) + 1
            by_grade[r["observer_grade"]] = by_grade.get(r["observer_grade"], 0) + 1
        return {
            "provider_id": "acme",
            "offering_id": "per-resolution",
            "evidence_level": "none",
            "metering_summary": {
                "total_billable_events": len(lines),
                "by_outcome_class": by_class,
                "by_observer_grade": by_grade,
                "unprovable_count": len(lines),
            },
            "outcome_lines": lines,
        }

    def _line(self, cls, grade):
        return {"outcome_class": cls, "observer_grade": grade}

    def test_tiers_cross_class_and_grade(self):
        # An escalated outcome the affected party attested is NOT a resolution:
        # the two lines must cross class and grade, not count them separately.
        b = self._bundle([
            self._line("resolved", "affected_party"),
            self._line("resolved", "affected_party"),
            self._line("assumed_resolved", "self_attested"),
            self._line("escalated", "affected_party"),
        ])
        text = settlement_statement(b, price_per_unit=1.0)
        self.assertIn("Tier 1  provider's own count (resolved + assumed)   3 of 4", text)
        self.assertIn("Tier 2  AgentMeasure settlement-grade (affected party) 2 of 4", text)
        self.assertIn("Disputed class (Tier 1 minus Tier 2)                1", text)

    def test_dollars_and_payback(self):
        b = self._bundle([
            self._line("resolved", "affected_party"),
            self._line("assumed_resolved", "self_attested"),
            self._line("assumed_resolved", "self_attested"),
            self._line("assumed_resolved", "self_attested"),
        ])
        text = settlement_statement(b, price_per_unit=0.99, audit_cost=2500)
        self.assertIn("$3.96", text)   # tier 1: 4 x 0.99
        self.assertIn("$0.99", text)   # tier 2: 1 x 0.99
        self.assertIn("$2.97", text)   # variance: 3 x 0.99
        self.assertIn("Payback at this rate", text)

    def test_states_underbilling_is_undeterminable(self):
        # D-2: never silently omit the favourable direction.
        b = self._bundle([self._line("resolved", "affected_party")])
        text = settlement_statement(b)
        self.assertIn("cannot determine from this input", text)
        self.assertIn("advocacy document", text)

    def test_statement_discloses_cannot_settle(self):
        b = self._bundle([self._line("resolved", "affected_party")])
        text = settlement_statement(b)
        self.assertIn("Cannot settle (D-1)", text)
        self.assertIn("removed from any outcome claim", text)

    def test_two_lines_never_blended(self):
        b = self._bundle([
            self._line("resolved", "affected_party"),
            self._line("assumed_resolved", "self_attested"),
        ])
        text = settlement_statement(b, price_per_unit=1.0)
        # Tier 1 and Tier 2 appear as separate figures.
        self.assertIn("Claimed by provider (Tier 1)", text)
        self.assertIn("Settlement-grade (Tier 2)", text)
        self.assertIn("Variance", text)


if __name__ == "__main__":
    unittest.main()
