"""Settlement bundle tests: effect-confirmed validation and bundle shape."""
import io
import json
import os
import tempfile
import unittest

from am_healthcheck.settle import (bundle_report, generate_bundle,
                                    settlement_csv, settlement_statement,
                                    statement_html, statement_markdown)


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


class TestStatementMarkdown(unittest.TestCase):
    """AMS-1 one-pager (standard/SETTLEMENT.md §2): provenance, two lines,
    both directions, cannot-settle, reproduce block."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _bundle(self, records):
        path = os.path.join(self.tmp.name, "effects.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        meta = {"provider": {"id": "acme"}, "offering": {"id": "fin"}}
        return generate_bundle(effects_path=path,
                               output_path=os.path.join(self.tmp.name, "b.json"),
                               metadata=meta), path

    def test_contains_all_ams1_sections_and_provenance(self):
        recs = [
            effect("e1", "resolved", "affected_party"),
            effect("e2", "assumed_resolved", "self_attested"),
            effect("e3", "escalated", "self_attested"),
        ]
        bundle, path = self._bundle(recs)
        md = statement_markdown(bundle, path, price_per_unit=0.99,
                                audit_cost=2500.0)
        for section in ("## 1. The claim, two ways (S-1)",
                        "## 2. Dollars",
                        "## 3. Both directions (S-3, D-2)",
                        "## 4. Cannot settle (S-2, D-1)",
                        "## 6. Reproduce (S-5)"):
            self.assertIn(section, md)
        self.assertIn("Input sha256", md)
        self.assertNotIn("{'id':", md)  # nested dicts must render as ids

    def test_escalated_never_counted_in_either_tier(self):
        bundle, path = self._bundle([
            effect("e1", "resolved", "affected_party"),
            effect("e2", "escalated", "affected_party"),
        ])
        md = statement_markdown(bundle, path)
        self.assertIn("| **Tier 1** | Provider's own count "
                      "(resolved + assumed) | **1 / 2** |", md)
        self.assertIn("not resolutions on any line and are excluded from both "
                      "tiers", md)

    def test_sha256_changes_with_input(self):
        bundle, path = self._bundle([effect("e1")])
        md1 = statement_markdown(bundle, path)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(effect("e2")) + "\n")
        bundle2, _ = self._bundle([effect("e1"), effect("e2")])
        md2 = statement_markdown(bundle2, path)
        h1 = md1.split("`")[1]
        h2 = md2.split("`")[1]
        self.assertNotEqual(h1, h2)


class TestStatementHtml(unittest.TestCase):
    """AMS-1 one-pager, attachable HTML form: offline, script-free,
    section-complete, and number-pinned to statement_markdown."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _bundle(self, records):
        path = os.path.join(self.tmp.name, "effects.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        meta = {"provider": {"id": "acme"}, "offering": {"id": "fin"}}
        return generate_bundle(effects_path=path,
                               output_path=os.path.join(self.tmp.name, "b.json"),
                               metadata=meta), path

    def test_offline_self_contained(self):
        bundle, path = self._bundle([effect("e1")])
        html = statement_html(bundle, path)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertNotIn("<script", html)          # no scripts
        self.assertNotIn('src="http', html)        # no remote resources
        self.assertNotIn('href="http', html)       # no remote links
        self.assertIn("@media print", html)        # print-friendly

    def test_contains_all_ams1_sections(self):
        recs = [
            effect("e1", "resolved", "affected_party"),
            effect("e2", "assumed_resolved", "self_attested"),
            effect("e3", "escalated", "self_attested"),
        ]
        bundle, path = self._bundle(recs)
        html = statement_html(bundle, path, price_per_unit=0.99,
                              audit_cost=2500.0)
        for section in ("1. The claim, two ways (S-1)",
                        "2. Dollars",
                        "3. Both directions (S-3, D-2)",
                        "4. Cannot settle (S-2, D-1)",
                        "5. Out of scope (S-6)",
                        "6. Reproduce (S-5)"):
            self.assertIn(section, html)
        self.assertIn("Input sha256", html)

    def test_numbers_pinned_to_markdown(self):
        """The HTML and markdown renderers must never drift: every tier,
        dollar and count figure that appears in both must be identical."""
        recs = [
            effect("e1", "resolved", "affected_party"),
            effect("e2", "resolved", "self_attested"),
            effect("e3", "assumed_resolved", "self_attested"),
            effect("e4", "escalated", "affected_party"),
        ]
        bundle, path = self._bundle(recs)
        md = statement_markdown(bundle, path, price_per_unit=0.99,
                                audit_cost=2500.0)
        html = statement_html(bundle, path, price_per_unit=0.99,
                              audit_cost=2500.0)
        for figure in ("3 / 4", "1 / 4", "$2.97", "$0.99", "$1.98"):
            self.assertIn(figure, md)
            self.assertIn(figure, html)

    def test_escapes_untrusted_values(self):
        bundle, path = self._bundle([effect("e1")])
        bundle["provider_id"] = {"id": '<script>alert("x")</script>'}
        html = statement_html(bundle, path)
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)

class TestSettlementCsv(unittest.TestCase):
    """F1.6: line-level finance CSV. One row per outcome line, tier flags as
    0/1, per-row verdict and amounts, no totals row inside the data."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = os.path.join(self.tmp.name, "effects.jsonl")
        records = [
            effect("e1", "resolved", "affected_party",
                   task_id="=SUM(A1:A9)", external_ids={"conversation_id": "cv-1"}),
            effect("e2", "resolved", "self_attested",
                   external_ids={"zendesk_ticket_id": "tk-2"}),
            effect("e3", "assumed_resolved", "self_attested"),
            effect("e4", "escalated", "affected_party"),
        ]
        with open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        self.bundle = generate_bundle(path, os.path.join(self.tmp.name, "b.json"),
                                      {"provider": "acme"})
        import csv as _csv
        self._csv = _csv

    def _rows(self, price=0.99):
        text = settlement_csv(self.bundle, price_per_unit=price)
        return list(self._csv.reader(io.StringIO(text)))

    def test_header_and_rowcount(self):
        rows = self._rows()
        self.assertEqual(rows[0][0], "line_id")
        self.assertIn("verdict", rows[0])
        self.assertIn("amount_disputed", rows[0])
        self.assertEqual(len(rows), 5)  # header + 4 lines

    def test_tier_math_matches_statement(self):
        rows = self._rows()[1:]
        t1 = sum(int(r[6]) for r in rows)
        t2 = sum(int(r[7]) for r in rows)
        self.assertEqual((t1, t2), (3, 1))  # escalated is not billed tier 1

    def test_verdicts(self):
        verdicts = sorted(r[8] for r in self._rows()[1:])
        self.assertEqual(verdicts,
                         ["DISPUTED", "DISPUTED", "NOT_BILLED", "SUPPORTED"])

    def test_amount_columns(self):
        rows = self._rows()[1:]
        disputed_sum = round(sum(float(r[12]) for r in rows), 2)
        self.assertEqual(disputed_sum, round(2 * 0.99, 2))

    def test_conversation_id_extraction(self):
        rows = self._rows()[1:]
        self.assertEqual(rows[0][1], "cv-1")
        self.assertEqual(rows[1][1], "tk-2")

    def test_formula_injection_guarded(self):
        rows = self._rows()[1:]
        self.assertTrue(rows[0][2].startswith("'"))  # '=SUM(...)' neutralised

    def test_no_price_leaves_amounts_blank(self):
        rows = self._rows(price=None)[1:]
        self.assertEqual(rows[0][9], "")   # unit_price
        self.assertEqual(rows[0][10], "")  # amount_billed


class TestStatementCoverage(unittest.TestCase):
    """F1.2: every statement format carries the coverage block and the
    provenance line, with numbers consistent with the bundle."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = os.path.join(self.tmp.name, "effects.jsonl")
        records = [
            effect("e1", "resolved", "affected_party"),
            effect("e2", "resolved", "affected_party"),
            effect("e3", "assumed_resolved", "self_attested"),
            effect("e4", "escalated", "self_attested"),
        ]
        with open(path, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r) + "\n")
        self.effects_path = path
        self.bundle = generate_bundle(
            path, os.path.join(self.tmp.name, "b.json"),
            {"provider": "acme", "period_start": "2026-09-01",
             "period_end": "2026-09-30"})

    def test_text_statement_coverage(self):
        text = settlement_statement(self.bundle)
        self.assertIn("Coverage (S-2 companion)", text)
        self.assertIn("Entered judgment", text)
        self.assertIn("100.0%", text)
        self.assertIn("Provenance: provider=acme period=2026-09-01..2026-09-30",
                      text)
        self.assertIn("invisible to it (D-2)", text)

    def test_markdown_coverage(self):
        md = statement_markdown(self.bundle, self.effects_path)
        self.assertIn("Coverage (S-2 companion)", md)
        self.assertIn("Settlement-grade (Tier 2) | 2 (50.0%)", md)
        self.assertIn("Provenance: provider=acme, period=2026-09-01..2026-09-30",
                      md)

    def test_html_coverage(self):
        html = statement_html(self.bundle, self.effects_path)
        self.assertIn("Coverage (S-2 companion)", html)
        self.assertIn("50.0%", html)
        self.assertIn("Provenance: provider=acme", html)
        self.assertNotIn("<script", html)  # still offline-safe
