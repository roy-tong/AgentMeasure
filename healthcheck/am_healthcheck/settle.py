"""Settlement evidence bundle generator (V2 · settle --bundle).

Produces the **AgentMeasure Dispute Bundle (ADB)** — a verifiable evidence
package for outcome-based billing disputes (AMS-1, standard/SETTLEMENT.md).
The ADB contains: metering policy reference, outcome lines with traceability,
incrementality evidence, and UNPROVABLE disclosures.

Format: single JSON file that can be independently re-computed by a third party.
Machine-readable clause manifest: standard/settlement.manifest.json.
"""

import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from . import jsonl as jsonl_mod

# Fields required by the effect-confirmed schema (v0.4.4)
_REQUIRED_EFFECT_FIELDS: frozenset = frozenset({
    "effect_id", "operation_id", "outcome_class",
    "observer_grade", "confirmed_at",
})

_KNOWN_OUTCOME_CLASSES: frozenset = frozenset({
    "resolved", "assumed_resolved", "escalated",
    "abandoned", "reopened", "not_outcome",
})

_KNOWN_OBSERVER_GRADES: frozenset = frozenset({
    "self_attested", "affected_party", "third_party_corroborated",
})

_EVIDENCE_LEVELS: frozenset = frozenset({
    "none", "v2_ablation", "v4_holdout",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_effect(record: dict, lineno: int) -> List[str]:
    """Return a list of validation errors for a single effect-confirmed record."""
    errors: List[str] = []

    for field in _REQUIRED_EFFECT_FIELDS:
        if field not in record:
            errors.append("line %d: missing required field %r" % (lineno, field))

    oc = record.get("outcome_class")
    if oc is not None and oc not in _KNOWN_OUTCOME_CLASSES:
        errors.append("line %d: unknown outcome_class %r" % (lineno, oc))

    og = record.get("observer_grade")
    if og is not None and og not in _KNOWN_OBSERVER_GRADES:
        errors.append("line %d: unknown observer_grade %r" % (lineno, og))

    ie = record.get("incrementality_evidence")
    if ie is not None and ie not in _EVIDENCE_LEVELS:
        errors.append("line %d: unknown incrementality_evidence %r" % (lineno, ie))

    return errors


def _build_outcome_line(rec: dict, index: int) -> dict:
    """Normalise a validated effect-confirmed record into an outcome line."""
    return {
        "line_id": "ol-%04d" % (index + 1),
        "effect_id": rec["effect_id"],
        "operation_id": rec["operation_id"],
        "outcome_class": rec["outcome_class"],
        "observer_grade": rec["observer_grade"],
        "confirmed_at": rec["confirmed_at"],
        "stability_window_seconds": rec.get("stability_window_seconds", 259200),
        "stability_deadline": rec.get("stability_deadline", ""),
        "incrementality_evidence": rec.get("incrementality_evidence", "none"),
        "task_id": rec.get("task_id", ""),
        "external_ids": rec.get("external_ids", {}),
        "reversal_of": rec.get("reversal_of"),
        "supersedes": rec.get("supersedes"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_bundle(effects_path: str, output_path: str,
                    metadata: dict) -> dict:
    """Read effect-confirmed JSONL and produce a settlement evidence bundle.

    Args:
        effects_path: Path to effect-confirmed JSONL records.
        output_path:  Path for the output JSON bundle (directory is created
                      if needed).
        metadata:     Dict with billing period, provider, offering info.
                      May contain ``incrementality_evidence`` (a dict with
                      ``m5_lift_table``, ``unprovable_share`` and
                      ``unprovable_reason``) to include the incrementality
                      section.

    Returns:
        The bundle dict (also written to *output_path*).

    Raises:
        ValueError: On input validation failures.
        OSError:    On file I/O errors.
    """
    if not os.path.isfile(effects_path):
        raise ValueError("effects file not found: %s" % effects_path)

    records: List[dict] = []
    validation_errors: List[str] = []

    for lineno, obj, _raw in jsonl_mod.iter_lines(effects_path):
        if obj is None:
            validation_errors.append("line %d: corrupt or empty JSON" % lineno)
            continue
        errs = _validate_effect(obj, lineno)
        if errs:
            validation_errors.extend(errs)
            continue
        records.append(obj)

    if validation_errors:
        preview = validation_errors[:5]
        remainder = len(validation_errors) - 5
        msg = "; ".join(preview)
        if remainder > 0:
            msg += " (and %d more)" % remainder
        raise ValueError("effect validation failed: %s" % msg)

    if not records:
        raise ValueError("no valid effect-confirmed records found in %s"
                         % effects_path)

    # --- Group & summarise -------------------------------------------------
    by_outcome_class: Dict[str, List[dict]] = defaultdict(list)
    by_observer_grade: Dict[str, int] = Counter()
    unprovable_count = 0

    for rec in records:
        by_outcome_class[rec["outcome_class"]].append(rec)
        by_observer_grade[rec["observer_grade"]] += 1
        if rec.get("incrementality_evidence") in (None, "none"):
            unprovable_count += 1

    total_by_outcome = {oc: len(lst) for oc, lst in by_outcome_class.items()}

    # --- Assemble bundle ---------------------------------------------------
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    bundle: Dict[str, Any] = {
        "schema": "agentmeasure.commercial/settlement-bundle",
        "schema_version": "0.1.0",
        "generated_at": now_iso,
        "billing_period": {
            "start": metadata.get("period_start", ""),
            "end": metadata.get("period_end", ""),
        },
        "provider_id": metadata.get("provider", ""),
        "offering_id": metadata.get("offering", ""),
        "evidence_level": metadata.get("evidence_level", "none"),
        "metering_summary": {
            "total_billable_events": len(records),
            "by_outcome_class": total_by_outcome,
            "by_observer_grade": dict(by_observer_grade),
            "unprovable_count": unprovable_count,
        },
        "outcome_lines": [
            _build_outcome_line(rec, i)
            for i, rec in enumerate(records)
        ],
    }

    # --- Incrementality section (only when metadata provides it) ----------
    inc_evidence = metadata.get("incrementality_evidence")
    if inc_evidence is not None:
        bundle["incrementality_section"] = {
            "evidence_level": metadata.get("evidence_level", "none"),
            "evidence_provider": metadata.get("provider", ""),
            "m5_lift_table": inc_evidence.get("m5_lift_table", {}),
            "unprovable_share": inc_evidence.get("unprovable_share", 0.0),
            "unprovable_reason": inc_evidence.get("unprovable_reason", ""),
        }

    # --- Write output ------------------------------------------------------
    dirpath = os.path.dirname(output_path)
    if dirpath and not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, ensure_ascii=False)

    return bundle


def bundle_report(bundle: dict) -> str:
    """Return a human-readable text report of the settlement bundle.

    Sections: header, outcome summary, by-class breakdown,
    incrementality (when present), and UNPROVABLE disclosure.
    """
    lines: List[str] = []
    _W = 50  # separator width

    meta = bundle.get("billing_period", {})
    lines.append("Settlement Evidence Bundle")
    lines.append("=" * _W)
    lines.append("Provider:  %s" % bundle.get("provider_id", "?"))
    lines.append("Offering:  %s" % bundle.get("offering_id", "?"))
    lines.append("Period:    %s  →  %s"
                 % (meta.get("start", "?"), meta.get("end", "?")))
    lines.append("Evidence:  %s" % bundle.get("evidence_level", "none"))
    lines.append("")

    summary = bundle.get("metering_summary", {})
    total = summary.get("total_billable_events", 0)
    lines.append("Outcome Summary")
    lines.append("-" * _W)
    lines.append("Total billable events:  %d" % total)
    lines.append("UNPROVABLE records:     %d" % summary.get("unprovable_count", 0))
    lines.append("")

    lines.append("By outcome class:")
    for oc, count in sorted(summary.get("by_outcome_class", {}).items()):
        lines.append("  %-20s  %d" % (oc, count))
    lines.append("")

    lines.append("By observer grade:")
    for og, count in sorted(summary.get("by_observer_grade", {}).items()):
        lines.append("  %-30s  %d" % (og, count))
    lines.append("")

    inc = bundle.get("incrementality_section")
    if inc is not None:
        lines.append("Incrementality Evidence")
        lines.append("-" * _W)
        lines.append("Evidence level:       %s" % inc.get("evidence_level", "?"))
        lines.append("Evidence provider:    %s" % inc.get("evidence_provider", "?"))
        m5 = inc.get("m5_lift_table", {})
        overall = m5.get("overall", {})
        if overall:
            lines.append("M5 Lift (overall):")
            lines.append("  Baseline rate:      %.3f"
                         % overall.get("baseline_resolution_rate", 0))
            lines.append("  Treatment rate:     %.3f"
                         % overall.get("treatment_resolution_rate", 0))
            lines.append("  Incremental lift:   %.3f"
                         % overall.get("incremental_lift", 0))
            lines.append("  Significant:        %s"
                         % overall.get("lift_significant", False))
            pv = overall.get("p_value")
            if pv is not None:
                lines.append("  p-value:            %.4f" % pv)
        for entry in m5.get("by_task_type", []):
            lines.append("  %-25s  base=%.3f  treat=%.3f  lift=%.3f  sig=%s"
                         % (entry.get("task_type", "?"),
                            entry.get("baseline", 0),
                            entry.get("treatment", 0),
                            entry.get("lift", 0),
                            entry.get("significant", False)))
        up_share = inc.get("unprovable_share", 0)
        if up_share:
            lines.append("UNPROVABLE share:     %.1f%%" % (up_share * 100))
            lines.append("UNPROVABLE reason:    %s"
                         % inc.get("unprovable_reason", ""))
        lines.append("")

    lines.append("UNPROVABLE Disclosure")
    lines.append("-" * _W)
    unprovable = summary.get("unprovable_count", 0)
    if total:
        lines.append("Records with incrementality_evidence=none:  %d (%.1f%%)"
                     % (unprovable, unprovable / total * 100))
    lines.append("These outcome lines carry no incrementality claim and")
    lines.append("are billed at operation basis per COMMERCIAL \u00a75.")
    lines.append("")
    lines.append("Generated at: %s" % bundle.get("generated_at", "?"))
    lines.append("=" * _W)

    return "\n".join(lines)


def settlement_statement(bundle: dict, price_per_unit: float = None,
                         audit_cost: float = None) -> str:
    """Produce the negotiable statement: two lines, both directions, netted.

    Structure follows COMMERCIAL 5.1 (D-1 remove-what-you-cannot-evidence,
    D-2 symmetric disclosure, D-3 two lines never blended).

    Tier 1 is what the provider's own counting would bill: every effect it
    recorded as resolved, including the ones only its own system attested.
    Tier 2 is what AgentMeasure will settle: an outcome the affected party
    attested. The gap is the disputed class, and it is not presented as one
    blended number.

    This bundle cannot detect under-billing, because it only carries the
    provider's effect records. That limitation is stated in the output rather
    than silently omitted: an audit that never looks in the audited party's
    favour is an advocacy document (D-2).
    """
    summary = bundle.get("metering_summary", {})
    by_class = summary.get("by_outcome_class", {})
    by_grade = summary.get("by_observer_grade", {})
    _W = 50  # separator width, same as bundle_report

    # Compute the two lines from the per-record lines, not from the marginal
    # aggregates: an escalated outcome attested by the affected party is not a
    # resolution, so class and grade must be crossed, not counted separately.
    lines_in = bundle.get("outcome_lines", [])
    resolved = sum(1 for r in lines_in if r.get("outcome_class") == "resolved")
    assumed = sum(1 for r in lines_in
                  if r.get("outcome_class") == "assumed_resolved")
    settled = sum(1 for r in lines_in
                  if r.get("outcome_class") == "resolved"
                  and r.get("observer_grade") == "affected_party")
    self_attested = sum(1 for r in lines_in
                        if r.get("observer_grade") == "self_attested")
    total = summary.get("total_billable_events", len(lines_in))

    # Tier 1: everything the provider counts as a successful outcome.
    tier1 = resolved + assumed
    # Tier 2: only resolutions the affected party affirmed.
    tier2 = settled
    disputed = max(tier1 - tier2, 0)

    lines = []
    lines.append("Settlement Statement (Advisory)")
    lines.append("=" * _W)
    lines.append("Provider:  %s" % (bundle.get("provider_id") or "(unspecified)"))
    lines.append("Offering:  %s" % (bundle.get("offering_id") or "(unspecified)"))
    lines.append("Evidence:  %s" % bundle.get("evidence_level", "none"))
    lines.append("")

    lines.append("The claim, two ways")
    lines.append("-" * _W)
    lines.append("Tier 1  provider's own count (resolved + assumed)   %d of %d"
                 % (tier1, total))
    lines.append("Tier 2  AgentMeasure settlement-grade (affected party) %d of %d"
                 % (tier2, total))
    lines.append("Disputed class (Tier 1 minus Tier 2)                %d" % disputed)
    lines.append("")
    lines.append("Tier 1 leads the negotiation: the provider cannot argue with")
    lines.append("its own rules, only with the data, which is yours. Tier 2 is")
    lines.append("renewal leverage, not a dispute line.")
    lines.append("")

    if price_per_unit is not None:
        lines.append("Dollars (at %s per unit)" % price_per_unit)
        lines.append("-" * _W)
        t1_amt = round(tier1 * price_per_unit, 2)
        t2_amt = round(tier2 * price_per_unit, 2)
        var_amt = round(disputed * price_per_unit, 2)
        lines.append("Claimed by provider (Tier 1)     $%.2f" % t1_amt)
        lines.append("Settlement-grade (Tier 2)        $%.2f" % t2_amt)
        lines.append("Variance                         $%.2f" % var_amt)
        lines.append("")
        if audit_cost is not None and var_amt > 0:
            months = audit_cost / var_amt
            lines.append("Payback at this rate: $%.2f / $%.2f = %.1f month(s)"
                         % (audit_cost, var_amt, months))
            breakeven = audit_cost / price_per_unit if price_per_unit else None
            if breakeven:
                lines.append("Breakeven: %.0f disputed resolutions cover the audit."
                             % breakeven)
            lines.append("")

    lines.append("Both directions (required, D-2)")
    lines.append("-" * _W)
    lines.append("Billed but not settlement-grade    %d" % disputed)
    lines.append("  of which self-attested only      %d" % self_attested)
    lines.append("Billable but not billed            cannot determine from this input")
    lines.append("")
    lines.append("This bundle carries only the provider's effect records, so it")
    lines.append("cannot search for charges the provider failed to bill. A complete")
    lines.append("audit needs the provider's counts-only export alongside these")
    lines.append("records. Stated here rather than omitted: a statement that never")
    lines.append("looks in the audited party's favour is an advocacy document.")
    lines.append("")

    lines.append("Cannot settle (D-1)")
    lines.append("-" * _W)
    unprovable = summary.get("unprovable_count", 0)
    lines.append("%d of %d lines carry no incrementality evidence and are"
                 % (unprovable, total))
    lines.append("removed from any outcome claim. They are listed with what is")
    lines.append("missing so the provider can supply it or credit them.")
    lines.append("")
    lines.append("=" * _W)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown one-pager (AMS-1 · standard/SETTLEMENT.md §2)
# ---------------------------------------------------------------------------

def _sha256_of(path: str) -> str:
    """sha256 of the input evidence file; the statement must be self-verifying."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def statement_markdown(bundle: dict, effects_path: str,
                       price_per_unit: float = None,
                       audit_cost: float = None,
                       spec_version: str = "AMS-1 Draft 0.1") -> str:
    """One-page Settlement Statement per standard/SETTLEMENT.md §2.

    The shareable artifact: a finance or support leader attaches this to the
    renewal negotiation. Section order is the spec's, section 7 is the
    reproduction block — anyone re-running the command must get these same
    numbers (S-5), which is the open-standard answer to a blind recount.
    """
    summary = bundle.get("metering_summary", {})
    lines_in = bundle.get("outcome_lines", [])
    total = summary.get("total_billable_events", len(lines_in))

    resolved = sum(1 for r in lines_in if r.get("outcome_class") == "resolved")
    assumed = sum(1 for r in lines_in if r.get("outcome_class") == "assumed_resolved")
    settled = sum(1 for r in lines_in
                  if r.get("outcome_class") == "resolved"
                  and r.get("observer_grade") == "affected_party")
    self_attested = sum(1 for r in lines_in
                        if r.get("observer_grade") == "self_attested")
    escalated = sum(1 for r in lines_in
                    if r.get("outcome_class") == "escalated")
    unprovable = summary.get("unprovable_count", 0)

    tier1 = resolved + assumed
    tier2 = settled
    disputed = max(tier1 - tier2, 0)

    def _id(value):
        if isinstance(value, dict):
            return value.get("id") or value.get("name") or "(unspecified)"
        return value or "(unspecified)"

    out = []
    out.append("# Settlement Statement (Advisory)")
    out.append("")
    out.append("| | |")
    out.append("|---|---|")
    out.append("| Provider | %s |" % _id(bundle.get("provider_id")))
    out.append("| Offering | %s |" % _id(bundle.get("offering_id")))
    out.append("| Evidence level | %s |" % bundle.get("evidence_level", "none"))
    out.append("| Standard | %s |" % spec_version)
    out.append("| Input sha256 | `%s` |" % _sha256_of(effects_path))
    out.append("| Generated | %s |" % datetime.now(timezone.utc)
               .strftime("%Y-%m-%d %H:%M UTC"))
    out.append("")

    out.append("## 1. The claim, two ways (S-1)")
    out.append("")
    out.append("| Line | Basis | Count |")
    out.append("|---|---|---|")
    out.append("| **Tier 1** | Provider's own count (resolved + assumed) | **%d / %d** |"
               % (tier1, total))
    out.append("| **Tier 2** | Settlement-grade (affected-party confirmed) | **%d / %d** |"
               % (tier2, total))
    out.append("| Disputed class | Tier 1 minus Tier 2 | **%d** |" % disputed)
    out.append("")
    out.append("Tier 1 leads the negotiation: the provider cannot argue with its own")
    out.append("rules, only with the data — which is yours. Tier 2 is renewal leverage,")
    out.append("not a dispute line (D-3: the two lines are never blended).")
    out.append("")

    if price_per_unit is not None:
        t1_amt = round(tier1 * price_per_unit, 2)
        t2_amt = round(tier2 * price_per_unit, 2)
        var_amt = round(disputed * price_per_unit, 2)
        out.append("## 2. Dollars (at %s per unit)" % price_per_unit)
        out.append("")
        out.append("| | |")
        out.append("|---|---|")
        out.append("| Claimed by provider (Tier 1) | $%.2f |" % t1_amt)
        out.append("| Settlement-grade (Tier 2) | $%.2f |" % t2_amt)
        out.append("| Variance | **$%.2f** |" % var_amt)
        out.append("")
        if audit_cost is not None and var_amt > 0:
            out.append("Payback: $%.2f audit / $%.2f monthly variance = **%.1f months**."
                       % (audit_cost, var_amt, audit_cost / var_amt))
            if price_per_unit:
                out.append("Breakeven: %.0f disputed resolutions cover the audit."
                           % (audit_cost / price_per_unit))
            out.append("")

    out.append("## 3. Both directions (S-3, D-2)")
    out.append("")
    out.append("| Direction | Count |")
    out.append("|---|---|")
    out.append("| Billed but not settlement-grade | %d |" % disputed)
    out.append("| — of which self-attested only | %d |" % self_attested)
    out.append("| Billable but not billed | cannot determine from this input |")
    out.append("")
    out.append("This bundle carries only the provider's effect records, so it cannot")
    out.append("search for charges the provider failed to bill. Stated here rather")
    out.append("than omitted: a statement that never looks in the audited party's")
    out.append("favour is an advocacy document.")
    out.append("")

    out.append("## 4. Cannot settle (S-2, D-1)")
    out.append("")
    out.append("**%d of %d** lines carry no incrementality evidence and are removed"
               % (unprovable, total))
    out.append("from any outcome claim; each is listed with what is missing so the")
    out.append("provider can supply it or credit them. Escalated outcomes (%d) are" % escalated)
    out.append("not resolutions on any line and are excluded from both tiers.")
    out.append("")

    out.append("## 5. Out of scope (S-6)")
    out.append("")
    out.append("Spam, vendor-initiated sessions, eligibility-only determinations, and")
    out.append("merged duplicates are excluded from this statement by definition; any")
    out.append("such exclusions are listed with their reason in the evidence bundle.")
    out.append("")

    out.append("## 6. Reproduce (S-5)")
    out.append("")
    out.append("```bash")
    out.append("# third-party reproduction: identical inputs must yield identical numbers")
    out.append("agentmeasure settle --effects effects.jsonl --format md \\")
    out.append("  --price %s --audit-cost %s" % (price_per_unit or "PRICE", audit_cost or "COST"))
    out.append("```")
    out.append("")
    out.append("Standard: [standard/SETTLEMENT.md](../../standard/SETTLEMENT.md) · open governance")
    out.append("(`GOVERNANCE.md`) · tool free and open source. Any conforming implementation")
    out.append("given the same inputs must produce these same numbers (implementation")
    out.append("disagreement = spec guilty).")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML one-pager (AMS-1 · same §2 sections as the markdown, attachable form)
#
# Self-contained: inline CSS only, no scripts, no network resources, no
# external links — the statement must render offline and print cleanly,
# because the person carrying it into a renewal negotiation may open it
# anywhere. Numbers are pinned to statement_markdown by a parity test;
# the two renderers must never drift.
# ---------------------------------------------------------------------------

_HTML_CSS = """\
body{font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;\
color:#1a1a1a;margin:0;padding:32px 16px;background:#fafafa}
.sheet{max-width:760px;margin:0 auto;background:#fff;padding:36px 44px;\
border:1px solid #e3e3e3;border-radius:6px}
h1{font-size:21px;margin:0 0 2px}
.sub{color:#666;font-size:13px;margin-bottom:20px}
table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:14px}
td,th{border:1px solid #e0e0e0;padding:7px 10px;text-align:left;vertical-align:top}
th{background:#f5f5f5;font-weight:600;width:38%}
h2{font-size:16px;margin:26px 0 6px;border-bottom:1px solid #e8e8e8;padding-bottom:6px}
p{margin:8px 0}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px}
.note{color:#555;font-size:13.5px}
pre{background:#f6f6f6;border:1px solid #e4e4e4;border-radius:4px;padding:10px 12px;\
overflow-x:auto;font-size:12.5px}
footer{margin-top:26px;color:#777;font-size:12.5px;border-top:1px solid #eee;padding-top:12px}
@media print{body{background:#fff;padding:0}.sheet{border:none;max-width:none;padding:0}}
"""


def statement_html(bundle: dict, effects_path: str,
                   price_per_unit: float = None,
                   audit_cost: float = None,
                   spec_version: str = "AMS-1 Draft 0.1") -> str:
    """One-page Settlement Statement as standalone HTML (AMS-1 §2 sections).

    The attachable form of :func:`statement_markdown`: a finance or support
    leader attaches this to a renewal thread. Offline, script-free,
    print-friendly; every rendered value is escaped.
    """
    import html as _html

    esc = _html.escape
    summary = bundle.get("metering_summary", {})
    lines_in = bundle.get("outcome_lines", [])
    total = summary.get("total_billable_events", len(lines_in))

    resolved = sum(1 for r in lines_in if r.get("outcome_class") == "resolved")
    assumed = sum(1 for r in lines_in
                  if r.get("outcome_class") == "assumed_resolved")
    settled = sum(1 for r in lines_in
                  if r.get("outcome_class") == "resolved"
                  and r.get("observer_grade") == "affected_party")
    self_attested = sum(1 for r in lines_in
                        if r.get("observer_grade") == "self_attested")
    escalated = sum(1 for r in lines_in
                    if r.get("outcome_class") == "escalated")
    unprovable = summary.get("unprovable_count", 0)

    tier1 = resolved + assumed
    tier2 = settled
    disputed = max(tier1 - tier2, 0)

    def _id(value):
        if isinstance(value, dict):
            return value.get("id") or value.get("name") or "(unspecified)"
        return value or "(unspecified)"

    prov = [("Provider", _id(bundle.get("provider_id"))),
            ("Offering", _id(bundle.get("offering_id"))),
            ("Evidence level", bundle.get("evidence_level", "none")),
            ("Standard", spec_version),
            ("Input sha256", _sha256_of(effects_path)),
            ("Generated", datetime.now(timezone.utc)
             .strftime("%Y-%m-%d %H:%M UTC"))]

    h = []
    h.append("<!DOCTYPE html>")
    h.append('<html lang="en"><head><meta charset="utf-8">')
    h.append('<meta name="viewport" content="width=device-width, '
             'initial-scale=1">')
    h.append("<title>Settlement Statement (Advisory)</title>")
    h.append("<style>%s</style></head><body><div class=\"sheet\">"
             % _HTML_CSS)
    h.append("<h1>Settlement Statement <small>(Advisory)</small></h1>")
    h.append('<div class="sub">AgentMeasure · the two-line statement · '
             "the provider’s own rules lead</div>")

    h.append("<table>")
    for label, value in prov:
        h.append("<tr><th>%s</th><td%s>%s</td></tr>"
                 % (esc(str(label)),
                    ' class="mono"' if label == "Input sha256" else "",
                    esc(str(value))))
    h.append("</table>")

    h.append("<h2>1. The claim, two ways (S-1)</h2>")
    h.append("<table><tr><th>Line</th><th>Basis</th><th>Count</th></tr>")
    h.append("<tr><td><b>Tier 1</b></td><td>Provider's own count "
             "(resolved + assumed)</td><td><b>%d / %d</b></td></tr>"
             % (tier1, total))
    h.append("<tr><td><b>Tier 2</b></td><td>Settlement-grade "
             "(affected-party confirmed)</td><td><b>%d / %d</b></td></tr>"
             % (tier2, total))
    h.append("<tr><td>Disputed class</td><td>Tier 1 minus Tier 2</td>"
             "<td><b>%d</b></td></tr>" % disputed)
    h.append("</table>")
    h.append('<p class="note">Tier 1 leads the negotiation: the provider '
             "cannot argue with its own rules, only with the data — which "
             "is yours. Tier 2 is renewal leverage, not a dispute line "
             "(D-3: the two lines are never blended).</p>")

    if price_per_unit is not None:
        t1_amt = round(tier1 * price_per_unit, 2)
        t2_amt = round(tier2 * price_per_unit, 2)
        var_amt = round(disputed * price_per_unit, 2)
        h.append("<h2>2. Dollars (at %s per unit)</h2>" % esc(str(price_per_unit)))
        h.append("<table>")
        h.append("<tr><th>Claimed by provider (Tier 1)</th><td>$%.2f</td></tr>"
                 % t1_amt)
        h.append("<tr><th>Settlement-grade (Tier 2)</th><td>$%.2f</td></tr>"
                 % t2_amt)
        h.append("<tr><th>Variance</th><td><b>$%.2f</b></td></tr>" % var_amt)
        h.append("</table>")
        if audit_cost is not None and var_amt > 0:
            h.append('<p class="note">Payback: $%.2f audit / $%.2f monthly '
                     "variance = <b>%.1f months</b>.</p>"
                     % (audit_cost, var_amt, audit_cost / var_amt))

    h.append("<h2>3. Both directions (S-3, D-2)</h2>")
    h.append("<table>")
    h.append("<tr><th>Billed but not settlement-grade</th><td>%d</td></tr>"
             % disputed)
    h.append("<tr><th>— of which self-attested only</th><td>%d</td></tr>"
             % self_attested)
    h.append("<tr><th>Billable but not billed</th><td>cannot determine from "
             "this input</td></tr>")
    h.append("</table>")
    h.append('<p class="note">This bundle carries only the provider\'s effect '
             "records, so it cannot search for charges the provider failed "
             "to bill. Stated here rather than omitted: a statement that "
             "never looks in the audited party's favour is an advocacy "
             "document.</p>")

    h.append("<h2>4. Cannot settle (S-2, D-1)</h2>")
    h.append("<p><b>%d of %d</b> lines carry no incrementality evidence and "
             "are removed from any outcome claim; each is listed with what "
             "is missing so the provider can supply it or credit them. "
             "Escalated outcomes (%d) are not resolutions on any line and "
             "are excluded from both tiers.</p>"
             % (unprovable, total, escalated))

    h.append("<h2>5. Out of scope (S-6)</h2>")
    h.append('<p class="note">Spam, vendor-initiated sessions, '
             "eligibility-only determinations, and merged duplicates are "
             "excluded by definition; any such exclusions are listed with "
             "their reason in the evidence bundle.</p>")

    h.append("<h2>6. Reproduce (S-5)</h2>")
    h.append("<pre># third-party reproduction: identical inputs must yield "
             "identical numbers\n"
             "agentmeasure settle --effects effects.jsonl --format html \\\n"
             "  --price %s --audit-cost %s</pre>"
             % (esc(str(price_per_unit or "PRICE")),
                esc(str(audit_cost or "COST"))))

    h.append("<footer>Standard: standard/SETTLEMENT.md · open governance "
             "(GOVERNANCE.md) · tool free and open source. Any conforming "
             "implementation given the same inputs must produce these same "
             "numbers (implementation disagreement = spec guilty).</footer>")
    h.append("</div></body></html>")
    return "\n".join(h)
