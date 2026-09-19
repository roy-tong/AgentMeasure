"""Vendor billing-rule registry and counts-only recount.

Tier 1 of the settlement statement (COMMERCIAL 5.1 D-3) is the audited party's
*own published rules*, applied line by line to the buyer's export. That tier is
the one the vendor cannot argue with: they can dispute the data, which is the
buyer's, but not their own published rule.

The rules live in `vendor-rules.json`, which is the SINGLE SOURCE OF TRUTH and
is also read by the browser-local recount at `website/recount.js`. A parity test
in CI fails if the two implementations disagree on the same fixture. Do not edit
the rules here; edit the JSON.

This module reads no message text.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List, Optional

_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "vendor-rules.json")

with open(_RULES_PATH, "r", encoding="utf-8") as _fh:
    _RULES = json.load(_fh)

RULES_VERSION: str = _RULES["version"]

# ---------------------------------------------------------------------------
# The canonical counts-only export shape.
#
# Deliberately small. Nothing here identifies a customer or carries a message.
# A vendor-specific reader maps that vendor's native export onto these columns;
# anything the vendor export does not carry stays absent, and an absent column
# lowers the verdict rather than being guessed.
# ---------------------------------------------------------------------------
CANONICAL_COLUMNS: List[str] = _RULES["canonical_columns"]
REQUIRED_COLUMNS: List[str] = _RULES["required_columns"]
COLUMN_ALIASES: Dict[str, List[str]] = _RULES["column_aliases"]
VENDORS: Dict[str, Dict[str, Any]] = _RULES["vendors"]

_TRUE = {"yes", "true", "1", "y", "t"}


def _as_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in {"no", "false", "0", "n", "f"}:
        return False
    return None


def get_vendor(vendor_id: str) -> Dict[str, Any]:
    key = (vendor_id or "").strip().lower()
    if key not in VENDORS:
        raise ValueError(
            "unknown vendor %r; known: %s" % (vendor_id, ", ".join(sorted(VENDORS)))
        )
    return VENDORS[key]


def list_vendors() -> List[Dict[str, Any]]:
    return [dict(v, id=k) for k, v in sorted(VENDORS.items())]


# ---------------------------------------------------------------------------
# Reading a counts-only export
# ---------------------------------------------------------------------------
def _map_columns(fieldnames: List[str]) -> Dict[str, str]:
    """Map our canonical names onto whatever the export actually calls them."""
    lowered = {f.strip().lower(): f for f in fieldnames or []}
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lowered:
                mapping[canonical] = lowered[alias]
                break
    return mapping


def load_export(path: str) -> Dict[str, Any]:
    """Read a counts-only CSV. Returns records plus what was and was not found."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        mapping = _map_columns(fieldnames)
        missing = [c for c in REQUIRED_COLUMNS if c not in mapping]
        records = []
        for row in reader:
            rec = {}
            for canonical, actual in mapping.items():
                rec[canonical] = row.get(actual)
            for canonical in REQUIRED_COLUMNS:
                rec.setdefault(canonical, None)
            records.append(rec)
    return {
        "records": records,
        "columns_found": sorted(mapping),
        "columns_missing": missing,
        "export_columns": fieldnames,
    }


# ---------------------------------------------------------------------------
# The recount
# ---------------------------------------------------------------------------
BILLED_BUT_NOT_BILLABLE = "billed_but_not_billable"
BILLABLE_BUT_NOT_BILLED = "billable_but_not_billed"
CANNOT_SETTLE = "cannot_settle"
AGREES = "agrees"


def _judge_one(rec: Dict[str, Any], vendor: Dict[str, Any]) -> str:
    """Apply the vendor's own published rules to one conversation."""
    billed = _as_bool(rec.get("vendor_billed"))
    human = _as_bool(rec.get("human_agent_participated"))
    addressed = _as_bool(rec.get("issue_addressed"))
    recontacted = _as_bool(rec.get("customer_recontacted_within_window"))

    # Absent evidence cannot be decided: it lowers the verdict, never fills it.
    if billed is None or human is None or addressed is None or recontacted is None:
        return CANNOT_SETTLE

    # A human finishing the conversation is not an AI resolution under any
    # vendor rule we have read.
    if human:
        should_bill = False
    elif not addressed:
        should_bill = False
    elif recontacted:
        # The customer came back inside the window. Intercom deducts, including
        # across billing periods. Zendesk does not document a deduction.
        should_bill = False if vendor["reopen_deduction"].startswith("documented") else None
        if should_bill is None:
            # Undocumented: we do not invent a rule in either direction.
            return CANNOT_SETTLE
    else:
        # No human, issue addressed, no recontact inside the window. Whether the
        # vendor's rules would bill this depends on its trigger.
        trigger = vendor["billing_trigger"]
        if trigger in ("confirmed_or_assumed", "assumed_with_lock",
                       "algorithmic_classification"):
            should_bill = True
        elif trigger == "llm_verified_only":
            # Zendesk: only an affirmative adjudication bills, and this export
            # cannot carry that verdict. The rule is the vendor's; the verdict
            # field is not in a counts-only export.
            return CANNOT_SETTLE
        else:
            return CANNOT_SETTLE

    if billed and not should_bill:
        return BILLED_BUT_NOT_BILLABLE
    if should_bill and not billed:
        return BILLABLE_BUT_NOT_BILLED
    return AGREES


def recount(export: Dict[str, Any], vendor_id: str) -> Dict[str, Any]:
    """Apply the vendor's own rules line by line. Returns findings both ways."""
    vendor = get_vendor(vendor_id)
    price = vendor.get("unit_price")
    records = export["records"]

    counts = {BILLED_BUT_NOT_BILLABLE: 0, BILLABLE_BUT_NOT_BILLED: 0,
              CANNOT_SETTLE: 0, AGREES: 0}
    billed_count = 0
    verdicts = []
    for i, rec in enumerate(records):
        verdict = _judge_one(rec, vendor)
        counts[verdict] += 1
        if _as_bool(rec.get("vendor_billed")):
            billed_count += 1
        verdicts.append({
            "line": i + 2,  # 1-based with header
            "conversation_id": rec.get("conversation_id"),
            "verdict": verdict,
        })

    over = counts[BILLED_BUT_NOT_BILLABLE]
    under = counts[BILLABLE_BUT_NOT_BILLED]
    cannot = counts[CANNOT_SETTLE]
    net = over - under

    result = {
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "vendor_rule_confidence": vendor["confidence"],
        "vendor_rule_source": vendor["source"],
        "unit_price": price,
        "currency": vendor.get("currency"),
        "total_conversations": len(records),
        "billed_by_vendor": billed_count,
        "counts": counts,
        "net_findings": net,
        "cannot_settle_share": round(cannot / len(records), 4) if records else 0.0,
        "columns_missing": export["columns_missing"],
        "verdicts": verdicts,
    }
    if price:
        result["variance"] = round(net * price, 2)
        result["overcharge_amount"] = round(over * price, 2)
        result["undercharge_amount"] = round(under * price, 2)
        result["cannot_settle_amount"] = round(cannot * price, 2)
    return result


def recount_report(result: Dict[str, Any]) -> str:
    """Human-readable Tier-1 recount, both directions, netted before a dollar."""
    W = 58
    out = []
    out.append("Tier 1 Recount — the vendor's own published rules")
    out.append("=" * W)
    out.append("Vendor:      %s" % result["vendor_name"])
    out.append("Rule source: %s" % result["vendor_rule_source"])
    out.append("Confidence:  %s" % result["vendor_rule_confidence"])
    out.append("")
    out.append("Conversations:        %d" % result["total_conversations"])
    out.append("Billed by vendor:     %d" % result["billed_by_vendor"])
    out.append("")

    if result["columns_missing"]:
        out.append("Missing required columns: %s" % ", ".join(result["columns_missing"]))
        out.append("Every affected row is cannot_settle, never guessed.")
        out.append("")

    c = result["counts"]
    out.append("Findings, both directions (D-2)")
    out.append("-" * W)
    out.append("billed but not billable     %d" % c[BILLED_BUT_NOT_BILLABLE])
    out.append("billable but not billed     %d" % c[BILLABLE_BUT_NOT_BILLED])
    out.append("net                         %+d" % result["net_findings"])
    out.append("cannot settle               %d (%.1f%%)"
               % (c[CANNOT_SETTLE], result["cannot_settle_share"] * 100))
    out.append("agrees with the vendor      %d" % c[AGREES])
    out.append("")

    if "variance" in result:
        out.append("Dollars (at %s %s per resolution)"
                   % (result["currency"], result["unit_price"]))
        out.append("-" * W)
        out.append("overcharge identified       %.2f" % result["overcharge_amount"])
        out.append("undercharge (vendor favour) %.2f" % result["undercharge_amount"])
        out.append("net variance                %.2f" % result["variance"])
        out.append("cannot settle (removed)     %.2f" % result["cannot_settle_amount"])
        out.append("")
        out.append("Undercharge is netted before any dollar is claimed.")
        out.append("cannot_settle amounts are removed from the claim, not zeroed.")

    return "\n".join(out)
