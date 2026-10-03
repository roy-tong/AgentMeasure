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
import datetime
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
# Optional columns are mapped when the export carries them and stay absent
# otherwise; an absent optional column lowers a verdict, it never blocks one.
OPTIONAL_COLUMNS: List[str] = _RULES.get("optional_columns", [])
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

# ---------------------------------------------------------------------------
# The three-state vocabulary of the standard (AMS-1 §judgement): every line is
# PASS, FAIL, or UNPROVABLE. The directional verdicts above carry the direction
# of a FAIL; the three-state carries the decision. Both always travel together.
# ---------------------------------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"
UNPROVABLE = "UNPROVABLE"

THREE_STATE: Dict[str, str] = {
    AGREES: PASS,
    BILLED_BUT_NOT_BILLABLE: FAIL,
    BILLABLE_BUT_NOT_BILLED: FAIL,
    CANNOT_SETTLE: UNPROVABLE,
}


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
    three_state_counts = {PASS: 0, FAIL: 0, UNPROVABLE: 0}
    billed_count = 0
    verdicts = []
    for i, rec in enumerate(records):
        verdict = _judge_one(rec, vendor)
        counts[verdict] += 1
        three_state_counts[THREE_STATE[verdict]] += 1
        if _as_bool(rec.get("vendor_billed")):
            billed_count += 1
        verdicts.append({
            "line": i + 2,  # 1-based with header
            "conversation_id": rec.get("conversation_id"),
            "verdict": verdict,
            "verdict_3state": THREE_STATE[verdict],
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
        "three_state_counts": three_state_counts,
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
    t = result["three_state_counts"]
    out.append("Findings, both directions (D-2)")
    out.append("-" * W)
    out.append("billed but not billable     %d" % c[BILLED_BUT_NOT_BILLABLE])
    out.append("billable but not billed     %d" % c[BILLABLE_BUT_NOT_BILLED])
    out.append("net                         %+d" % result["net_findings"])
    out.append("cannot settle               %d (%.1f%%)"
               % (c[CANNOT_SETTLE], result["cannot_settle_share"] * 100))
    out.append("agrees with the vendor      %d" % c[AGREES])
    out.append("three-state: PASS %d / FAIL %d / UNPROVABLE %d"
               % (t[PASS], t[FAIL], t[UNPROVABLE]))
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


# ---------------------------------------------------------------------------
# The buyer's outcome standard (contract overlay) — the second lane.
#
# Tier 1 asks "did the vendor follow its own rule". The outcome lane asks a
# different question: "did the outcome meet the buyer's contracted standard".
# Its findings are renewal leverage, NOT a billing claim: they are listed
# separately and never netted into the Tier 1 variance (BP r28 p2/p5/p8:
# 合同口径差异是钱，结果标准差异是筹码，分开列，不混算).
#
# An absent field lowers the verdict here too: an unevaluable criterion is
# UNPROVABLE with the missing field named, never guessed.
# ---------------------------------------------------------------------------
CONTRACT_KEYS = frozenset({
    "label", "reopen_window_hours",
    "human_takeover_disqualifies", "require_issue_addressed",
})


def load_contract(path: str) -> Dict[str, Any]:
    """Load and validate a buyer-side contract overlay (the outcome standard)."""
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict):
        raise ValueError("contract overlay must be a JSON object")
    unknown = sorted(set(doc) - CONTRACT_KEYS)
    if unknown:
        raise ValueError("unknown contract keys: %s; known: %s"
                         % (", ".join(unknown), ", ".join(sorted(CONTRACT_KEYS))))

    contract: Dict[str, Any] = {
        "label": doc.get("label") or "buyer contract overlay",
        "reopen_window_hours": None,
        "human_takeover_disqualifies": bool(doc.get("human_takeover_disqualifies",
                                                     False)),
        "require_issue_addressed": bool(doc.get("require_issue_addressed", False)),
    }
    window = doc.get("reopen_window_hours")
    if window is not None:
        if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
            raise ValueError("reopen_window_hours must be a positive integer")
        contract["reopen_window_hours"] = window

    if (contract["reopen_window_hours"] is None
            and not contract["human_takeover_disqualifies"]
            and not contract["require_issue_addressed"]):
        raise ValueError(
            "contract overlay is empty: set at least one of reopen_window_hours, "
            "human_takeover_disqualifies, require_issue_addressed")
    return contract


def _parse_ts(text: Any) -> Optional[datetime.datetime]:
    """Parse an ISO-8601 timestamp; naive values are read as UTC."""
    if text is None or not str(text).strip():
        return None
    raw = str(text).strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def outcome_lane(export: Dict[str, Any], vendor_id: str,
                 contract: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the buyer's outcome standard to the vendor-billed lines.

    Verdicts per line: fails_buyer_standard / meets_buyer_standard /
    unprovable / not_reviewed (the vendor did not bill the line, so there is
    no vendor outcome to contest). Each failing or unevaluable criterion names
    its reason; a missing timestamp is UNPROVABLE, never a guess.
    """
    vendor = get_vendor(vendor_id)
    price = vendor.get("unit_price")
    window = contract["reopen_window_hours"]

    fails = unprovables = meets = not_reviewed = 0
    at_risk = 0.0
    lines = []
    for i, rec in enumerate(export["records"]):
        billed = _as_bool(rec.get("vendor_billed"))
        reasons: List[str] = []
        missing: List[str] = []

        if billed is None:
            missing.append("vendor_billed")
        elif not billed:
            not_reviewed += 1
            lines.append({
                "line": i + 2,
                "conversation_id": rec.get("conversation_id"),
                "outcome_verdict": "not_reviewed",
                "reasons": ["vendor did not bill this line"],
            })
            continue

        if contract["human_takeover_disqualifies"]:
            human = _as_bool(rec.get("human_agent_participated"))
            if human is None:
                missing.append("human_agent_participated")
            elif human:
                reasons.append("human agent finished the conversation")

        if contract["require_issue_addressed"]:
            addressed = _as_bool(rec.get("issue_addressed"))
            if addressed is None:
                missing.append("issue_addressed")
            elif not addressed:
                reasons.append("issue not addressed under the buyer's standard")

        if window:
            closed = _parse_ts(rec.get("closed_at"))
            recontact = _parse_ts(rec.get("customer_recontacted_at"))
            if closed is None:
                missing.append("closed_at")
            elif recontact is None:
                # The exported within-window boolean is judged against the
                # vendor's window, not the contractual one. Using it here
                # would be a guess in either direction.
                missing.append("customer_recontacted_at")
            elif recontact >= closed:
                delta = (recontact - closed).total_seconds() / 3600.0
                if delta <= window:
                    reasons.append(
                        "customer recontacted %.1fh after close, inside the "
                        "contractual %dh window" % (delta, window))
            # recontact before close is not a reopen; the criterion passes.

        if reasons:
            fails += 1
            if billed and price:
                at_risk += price
            verdict = "fails_buyer_standard"
        elif missing:
            unprovables += 1
            verdict = "unprovable"
        else:
            meets += 1
            verdict = "meets_buyer_standard"

        entry: Dict[str, Any] = {
            "line": i + 2,
            "conversation_id": rec.get("conversation_id"),
            "outcome_verdict": verdict,
            "reasons": reasons,
        }
        if missing:
            entry["missing_evidence"] = missing
        lines.append(entry)

    lane: Dict[str, Any] = {
        "label": contract["label"],
        "criteria": {
            "reopen_window_hours": window,
            "human_takeover_disqualifies": contract["human_takeover_disqualifies"],
            "require_issue_addressed": contract["require_issue_addressed"],
        },
        "reviewed_scope": "vendor-billed lines only",
        "counts": {
            "fails_buyer_standard": fails,
            "meets_buyer_standard": meets,
            "unprovable": unprovables,
            "not_reviewed": not_reviewed,
        },
        "lines": lines,
        "claim_rule": "outcome findings are renewal leverage; they are not "
                      "netted into the Tier 1 billing claim",
    }
    if price:
        lane["at_risk_amount"] = round(at_risk, 2)
        lane["at_risk_note"] = "not part of the claim"
    return lane


def outcome_lane_report(lane: Dict[str, Any]) -> str:
    """Human-readable outcome-standard lane, kept visibly separate from Tier 1."""
    W = 58
    c = lane["counts"]
    out = []
    out.append("Outcome-standard lane — %s" % lane["label"])
    out.append("=" * W)
    criteria = lane["criteria"]
    active = []
    if criteria["reopen_window_hours"]:
        active.append("reopen window %dh" % criteria["reopen_window_hours"])
    if criteria["human_takeover_disqualifies"]:
        active.append("human takeover disqualifies")
    if criteria["require_issue_addressed"]:
        active.append("issue must be addressed")
    out.append("Criteria: %s" % "; ".join(active))
    out.append("")
    out.append("fails the buyer's standard    %d" % c["fails_buyer_standard"])
    out.append("meets the buyer's standard    %d" % c["meets_buyer_standard"])
    out.append("unprovable from this export   %d" % c["unprovable"])
    out.append("not reviewed (vendor didn't bill) %d" % c["not_reviewed"])
    if "at_risk_amount" in lane:
        out.append("at-risk amount (informational only): %s" % lane["at_risk_amount"])
    out.append("")
    out.append("These findings are renewal leverage. They are listed")
    out.append("separately and never netted into the billing claim.")
    return "\n".join(out)
