"""Vendor billing-rule registry and counts-only recount.

Tier 1 of the settlement statement (COMMERCIAL 5.1 D-3) is the audited party's
*own published rules*, applied line by line to the buyer's export. That tier is
the one the vendor cannot argue with: they can dispute the data, which is the
buyer's, but not their own published rule.

This module holds those rules as data, with a source for each, and applies them
to a counts-only export. It reads no message text.

Rule confidence:
  P  read from the vendor's own published documentation
  S  secondary source (press, help-centre rendering, third-party summary)
  U  unverified; the rule is recorded but the recount says so

Sources are in the ``source`` field per vendor and per rule.
"""
from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# The canonical counts-only export shape.
#
# This is deliberately small. Nothing here identifies a customer or carries a
# message. A vendor-specific reader maps that vendor's native export onto these
# columns; anything the vendor export does not carry stays absent, and an absent
# column lowers the verdict rather than being guessed.
# ---------------------------------------------------------------------------
CANONICAL_COLUMNS = [
    "conversation_id",          # required
    "opened_at",                # optional
    "closed_at",                # optional
    "human_agent_participated",  # required
    "issue_addressed",          # required
    "customer_recontacted_within_window",  # required
    "vendor_billed",            # required
]

REQUIRED_COLUMNS = [
    "conversation_id",
    "human_agent_participated",
    "issue_addressed",
    "customer_recontacted_within_window",
    "vendor_billed",
]

# Column-name aliases: the names need not match ours.
COLUMN_ALIASES = {
    "conversation_id": ["conversation_id", "conversation", "id", "ticket_id", "ticket"],
    "opened_at": ["opened_at", "opened_date", "created_at", "created"],
    "closed_at": ["closed_at", "closed_date", "solved_at", "resolved_at"],
    "human_agent_participated": ["human_agent_participated", "human_agent_stepped_in",
                                 "human_agent", "teammate_replied", "agent_stepped_in"],
    "issue_addressed": ["issue_addressed", "addressed", "solution_provided"],
    "customer_recontacted_within_window": ["customer_recontacted_within_window",
                                           "customer_recontacted", "reopened",
                                           "recontacted_within_window"],
    "vendor_billed": ["vendor_billed", "billed", "vendor_billed_as_resolution",
                      "billed_as_resolution", "resolution_billed"],
}

_TRUE = {"yes", "true", "1", "y", "t"}


def _as_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in {"no", "false", "0", "n", "f", ""}:
        return False if text != "" else None
    return None


# ---------------------------------------------------------------------------
# Vendor rules
# ---------------------------------------------------------------------------
VENDORS: Dict[str, Dict[str, Any]] = {
    "intercom": {
        "name": "Intercom Fin",
        "unit_price": 0.99,
        "currency": "USD",
        "confidence": "P",
        "source": "fin.ai pricing & outcomes; Intercom help centre (Fin AI Agent outcomes)",
        # Intercom bills a resolution the customer confirmed OR one its own system
        # assumed after the disengagement window. It is the only vendor found with
        # a documented cross-billing-period reopen deduction.
        "billing_trigger": "confirmed_or_assumed",
        "silence_bills": True,
        "silence_window_hours": 24,
        "reopen_deduction": "documented_including_cross_period",
        "closure_timers_hours": {"messaging": 24, "email": 72},
        "notes": [
            "confirmed resolution rate and assumed resolution rate are separate "
            "published metrics, so a buyer can at least see the split",
            "resolution state is filterable and exposed via API v2.11+",
        ],
    },
    "zendesk": {
        "name": "Zendesk AI Agents",
        "unit_price": 2.00,          # PAYG; committed is 1.20-1.50
        "currency": "USD",
        "confidence": "P",
        "source": "Zendesk help centre: About the automated resolutions platform; "
                  "About automated resolution tiers (edited 2026-08-25)",
        # The most conservative published rule in the category: silence alone is
        # NOT billed. Only an affirmative LLM adjudication (Verified resolution)
        # bills. Contained resolution is the failed-verification tier and is free.
        "billing_trigger": "llm_verified_only",
        "silence_bills": False,
        "silence_window_hours": None,
        "reopen_deduction": "not_documented",
        "closure_timers_hours": {"email": 72, "messaging": 2, "voice": 0},
        "no_reversal": "deleting a ticket with Resolution type Automated "
                       "does not undo the consumption of an automated resolution",
        "no_rollover": True,
        "notes": [
            "criteria, thresholds and error rate behind the LLM adjudication are "
            "not published",
            "unused allowance does not roll over to the next billing period",
        ],
    },
    "hubspot": {
        "name": "HubSpot Breeze",
        "unit_price": 0.50,
        "currency": "USD",
        "confidence": "S",
        "source": "secondary; knowledge.hubspot.com is JS-only and could not be read",
        # Resolved = the agent shared a content source or performed an action AND
        # no human handoff within 72h; evaluated and locked 72h after the last reply.
        "billing_trigger": "assumed_with_lock",
        "silence_bills": True,
        "silence_window_hours": 72,
        "reopen_deduction": "none_after_lock",
        "closure_timers_hours": {"email": 72, "messaging": 72},
        "structural_risk": "a reopen after the 72-hour lock starts a FRESH "
                           "billable window instead of deducting the original, "
                           "which is a double-billing risk rather than a protection",
    },
    "ada": {
        "name": "Ada",
        "unit_price": None,
        "currency": None,
        "confidence": "S",
        "source": "ada.cx pricing/terms returned 403; rule reported from public docs",
        # Relevant + Accurate + Safe + Contained, assessed after the conversation.
        "billing_trigger": "algorithmic_classification",
        "silence_bills": True,
        "silence_window_hours": 24,
        "reopen_deduction": "not_documented",
        "closure_timers_hours": {"web": 24, "social": 24, "email": 72},
        "operator_override": "operator feedback does not override the automatic "
                             "classification",
        "export_fields": [
            "automated_resolution_classification",
            "automated_resolution_classification_reason",
            "is_escalated",
            "csat.resolved",
        ],
    },
    "salesforce": {
        "name": "Salesforce Agentforce Help Agent",
        "unit_price": None,
        "currency": None,
        "confidence": "U",
        "source": "press release only; no official metering document is published",
        "billing_trigger": "autonomous_completion",
        "silence_bills": None,
        "silence_window_hours": None,
        "reopen_deduction": "not_documented",
        "closure_timers_hours": {},
        "notes": [
            "no timer, no reopen rule, and no clawback are published",
            "the broader Agentforce product is billed whether or not the issue "
            "was resolved",
        ],
    },
    "generic": {
        "name": "Generic per-resolution vendor",
        "unit_price": None,
        "currency": None,
        "confidence": "U",
        "source": "no vendor rules; only the AgentMeasure standard is applied",
        "billing_trigger": "unknown",
        "silence_bills": None,
        "silence_window_hours": None,
        "reopen_deduction": "not_documented",
        "closure_timers_hours": {},
    },
}


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
