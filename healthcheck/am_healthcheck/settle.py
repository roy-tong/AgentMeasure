"""Settlement evidence bundle generator (V2 · settle --bundle).

Produces a verifiable evidence package for outcome-based billing disputes.
The bundle contains: metering policy reference, outcome lines with traceability,
incrementality evidence, and UNPROVABLE disclosures.

Format: single JSON file that can be independently re-computed by a third party.
"""

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