"""Vendor-rule drift watch — the monthly subscription ritual, made checkable.

BP r28 appendix A: the monthly subscription re-verifies "新账单和规则变化".
A vendor changing how it counts is exactly when last month's verdicts stop
being reproducible, so the rule change must be *named*, not absorbed. This
module diffs two vendor-rules registry documents and reports which vendors'
*material* fields moved: billing trigger, reopen deduction, silence behaviour,
price, currency, closure timers.

Local files only — the tool never fetches vendor docs on its own. The monthly
workflow keeps last month's registry snapshot beside the customer's exports
and runs `agentmeasure rules-diff` against it; a non-zero exit means the
change is material and the period must be re-verified under the new rule,
disclosed as a rule change, never silently mixed.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

# Fields whose movement changes what a recount means. Anything else
# (notes, sources) is informational.
MATERIAL_FIELDS = (
    "billing_trigger",
    "reopen_deduction",
    "silence_bills",
    "silence_window_hours",
    "closure_timers_hours",
    "unit_price",
    "currency",
)

INFORMATIONAL_FIELDS = ("name", "confidence", "source", "notes",
                        "no_reversal", "no_rollover", "operator_override",
                        "structural_risk", "export_fields")


class RulesDiffError(ValueError):
    pass


def load_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict) or "vendors" not in doc:
        raise RulesDiffError("%s is not a vendor-rules document" % path)
    return doc


def diff_rules(old_doc: Dict[str, Any], new_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Per-vendor semantic diff between two registry documents."""
    old_v = old_doc.get("vendors", {})
    new_v = new_doc.get("vendors", {})
    vendor_changes: List[Dict[str, Any]] = []

    for vid in sorted(set(old_v) | set(new_v)):
        changes: List[Dict[str, Any]] = []
        info_changes: List[str] = []
        if vid not in old_v:
            changes.append({"field": "(vendor)", "old": None,
                            "new": "added to the registry"})
        elif vid not in new_v:
            changes.append({"field": "(vendor)", "old": "was registered",
                            "new": "removed from the registry"})
        else:
            for field in MATERIAL_FIELDS:
                a, b = old_v[vid].get(field), new_v[vid].get(field)
                if a != b:
                    changes.append({"field": field, "old": a, "new": b})
            for field in INFORMATIONAL_FIELDS:
                a, b = old_v[vid].get(field), new_v[vid].get(field)
                if a != b:
                    info_changes.append(field)
        if changes or info_changes:
            vendor_changes.append({
                "vendor_id": vid,
                "material": bool(changes),
                "changes": changes,
                "informational": info_changes,
            })

    return {
        "old_version": old_doc.get("version"),
        "new_version": new_doc.get("version"),
        "vendors_changed": vendor_changes,
        "material": any(v["material"] for v in vendor_changes),
        "reading": "a material change means the period must be re-verified "
                   "under the new rule and disclosed as a rule change",
    }


def rules_diff_report(result: Dict[str, Any]) -> str:
    W = 58
    out = []
    out.append("Vendor-rule drift check")
    out.append("=" * W)
    out.append("registry %s -> %s" % (result["old_version"], result["new_version"]))
    out.append("")
    if not result["vendors_changed"]:
        out.append("No rule changes. Last period's verdicts stand.")
        return "\n".join(out)
    for v in result["vendors_changed"]:
        head = "MATERIAL" if v["material"] else "info only"
        out.append("%s — %s" % (v["vendor_id"], head))
        for ch in v["changes"]:
            out.append("  %-22s %r -> %r" % (ch["field"], ch["old"], ch["new"]))
        if v["informational"]:
            out.append("  (informational: %s)" % ", ".join(v["informational"]))
    out.append("")
    if result["material"]:
        out.append("A material rule change moves what the vendor's own rule")
        out.append("would bill. Re-verify the period under the new rule and")
        out.append("disclose the change — never mix rules inside one claim.")
    else:
        out.append("Only informational fields moved; verdicts stand.")
    return "\n".join(out)
