"""Dispute & Recovery Pack — the negotiable deliverable.

Combines the two lines defined in COMMERCIAL 5.1 into one artifact a buyer can
hand to a vendor:

  Tier 1  the vendor's own published rules, applied to the buyer's export
          (vendors.recount). This is the line the vendor cannot argue with:
          they can dispute the data, which is the buyer's, but not their own
          published rule.
  Tier 2  the AgentMeasure settlement standard, applied to the buyer's effect
          records when those are supplied.

The pack reports findings in BOTH directions and nets them before claiming a
dollar (D-2). Lines that cannot be evidenced are removed from the claim and
listed with what is missing (D-1). No message text is read.

Output: a machine-readable JSON bundle plus a Markdown pack whose first page is
a cover letter citing the vendor's own rule per finding.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from . import vendors as vendors_mod
from .vendors import (AGREES, BILLABLE_BUT_NOT_BILLED, BILLED_BUT_NOT_BILLABLE,
                      CANNOT_SETTLE)

PACK_SCHEMA = "agentmeasure.commercial/dispute-pack"
PACK_SCHEMA_VERSION = "0.1.0"

_VERDICT_LABEL = {
    BILLED_BUT_NOT_BILLABLE: "billed, not billable under your own rule",
    BILLABLE_BUT_NOT_BILLED: "billable under your own rule, not billed",
    CANNOT_SETTLE: "cannot settle from this export",
    AGREES: "agrees",
}


def _sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_pack(export_path: str,
               vendor_id: str,
               effects_path: Optional[str] = None,
               price: Optional[float] = None,
               audit_cost: Optional[float] = None,
               period_start: Optional[str] = None,
               period_end: Optional[str] = None,
               buyer_label: Optional[str] = None) -> Dict[str, Any]:
    """Build the pack from a counts-only export and, optionally, effect records."""
    export = vendors_mod.load_export(export_path)
    tier1 = vendors_mod.recount(export, vendor_id)
    vendor = vendors_mod.get_vendor(vendor_id)

    unit_price = price if price is not None else tier1.get("unit_price")

    pack: Dict[str, Any] = {
        "schema": PACK_SCHEMA,
        "schema_version": PACK_SCHEMA_VERSION,
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                                 .isoformat(timespec="seconds"),
        "vendor": {
            "id": vendor_id,
            "name": vendor["name"],
            "rule_confidence": vendor["confidence"],
            "rule_source": vendor["source"],
        },
        "buyer_label": buyer_label or "(unspecified)",
        "period": {"start": period_start, "end": period_end},
        "unit_price": unit_price,
        "currency": vendor.get("currency"),
        "audit_cost": audit_cost,
        "tier1": tier1,
        "inputs": {
            "export_file": os.path.basename(export_path),
            "export_sha256": _sha256_of(export_path),
            "export_columns": export["export_columns"],
            "columns_missing": export["columns_missing"],
        },
        "tier2": None,
    }

    if effects_path:
        from . import settle as settle_mod
        bundle = settle_mod.generate_bundle(
            effects_path=effects_path,
            output_path=os.path.join(
                os.path.dirname(os.path.abspath(export_path)) or ".",
                ".agentmeasure-tier2-tmp.json"),
            metadata={"provider": vendor["name"], "offering": vendor_id,
                      "period_start": period_start, "period_end": period_end,
                      "evidence_level": "none"})
        pack["tier2"] = {
            "metering_summary": bundle.get("metering_summary", {}),
            "outcome_lines": bundle.get("outcome_lines", []),
            "inputs": {
                "effects_file": os.path.basename(effects_path),
                "effects_sha256": _sha256_of(effects_path),
            },
        }
        # the temp bundle is an implementation detail, not a deliverable
        tmp = os.path.join(os.path.dirname(os.path.abspath(export_path)) or ".",
                           ".agentmeasure-tier2-tmp.json")
        if os.path.exists(tmp):
            os.unlink(tmp)

    # --- Claim arithmetic -------------------------------------------------
    c = tier1["counts"]
    over = c[BILLED_BUT_NOT_BILLABLE]
    under = c[BILLABLE_BUT_NOT_BILLED]
    cannot = c[CANNOT_SETTLE]
    net = over - under
    claim: Dict[str, Any] = {
        "billed_but_not_billable": over,
        "billable_but_not_billed": under,
        "net": net,
        "cannot_settle": cannot,
        "netting_rule": "under-billing is netted before any dollar is claimed",
        "cannot_settle_rule": "removed from the claim, not zeroed",
    }
    if unit_price:
        claim["dollars"] = {
            "overcharge": round(over * unit_price, 2),
            "undercharge": round(under * unit_price, 2),
            "net_variance": round(net * unit_price, 2),
            "cannot_settle_removed": round(cannot * unit_price, 2),
        }
        if audit_cost and net > 0:
            monthly = round(net * unit_price, 2)
            claim["payback"] = {
                "audit_cost": audit_cost,
                "monthly_variance": monthly,
                "months_to_payback": round(audit_cost / monthly, 1),
            }
    pack["claim"] = claim
    return pack


def render_cover_letter(pack: Dict[str, Any]) -> str:
    """The first page: a letter citing the vendor's own rule per finding."""
    v = pack["vendor"]
    claim = pack["claim"]
    dollars = claim.get("dollars", {})
    period = pack["period"]
    span = " to ".join(x for x in (period.get("start"), period.get("end")) if x) \
        or "the period in the attached export"

    lines = []
    lines.append("# Settlement enquiry — %s" % v["name"])
    lines.append("")
    lines.append("To the %s account team," % v["name"])
    lines.append("")
    lines.append(
        "We reviewed our %s invoice against our own helpdesk export for %s. "
        "The recount applies **your published rules**, not ours, line by line. "
        "We are writing because %d conversations appear to have been billed "
        "where your own rule does not bill them."
        % (v["name"], span, claim["billed_but_not_billable"]))
    lines.append("")
    if dollars:
        lines.append(
            "At the contracted rate this is %s %s. We are also reporting %d "
            "conversations that your rule appears to bill but which were not "
            "billed (%s %s), because a statement that only ever finds against "
            "you would not be a statement."
            % (pack["currency"], dollars["overcharge"],
               claim["billable_but_not_billed"],
               pack["currency"], dollars["undercharge"]))
        lines.append("")
        lines.append(
            "Net of those, the variance we would like to discuss is **%s %s**."
            % (pack["currency"], dollars["net_variance"]))
        lines.append("")
    if claim["cannot_settle"]:
        lines.append(
            "%d conversations could not be settled from our export. We have "
            "removed them from this claim rather than discounting them, and "
            "listed what is missing for each so that either side can supply "
            "the evidence." % claim["cannot_settle"])
        lines.append("")
    lines.append(
        "Every finding is listed in the appendix with the conversation id, the "
        "line number in our export, and the specific rule it rests on. The rule "
        "text we applied is at: %s" % v["rule_source"])
    lines.append("")
    lines.append("We would welcome a correction of any finding we have got wrong.")
    lines.append("")
    lines.append("— %s" % pack["buyer_label"])
    return "\n".join(lines)


def render_pack_markdown(pack: Dict[str, Any]) -> str:
    """The full pack: cover letter, both tiers, findings appendix."""
    out = [render_cover_letter(pack), ""]
    out.append("---")
    out.append("")
    out.append("# Appendix — findings")
    out.append("")

    t1 = pack["tier1"]
    out.append("## Tier 1 — %s's own published rules" % pack["vendor"]["name"])
    out.append("")
    out.append("Rule source: %s  " % t1["vendor_rule_source"])
    out.append("Confidence: %s" % t1["vendor_rule_confidence"])
    out.append("")
    out.append("| | conversations |")
    out.append("|---|---:|")
    out.append("| billed, not billable under the vendor's own rule | %d |"
               % t1["counts"][BILLED_BUT_NOT_BILLABLE])
    out.append("| billable under the vendor's own rule, not billed | %d |"
               % t1["counts"][BILLABLE_BUT_NOT_BILLED])
    out.append("| cannot settle from this export | %d |"
               % t1["counts"][CANNOT_SETTLE])
    out.append("| agrees | %d |" % t1["counts"][AGREES])
    out.append("| **net** | **%+d** |" % t1["net_findings"])
    out.append("")

    if t1["columns_missing"]:
        out.append("Missing required columns: `%s`. Every affected row is "
                   "cannot_settle, never guessed."
                   % "`, `".join(t1["columns_missing"]))
        out.append("")

    disputed = [v for v in t1["verdicts"]
                if v["verdict"] in (BILLED_BUT_NOT_BILLABLE, BILLABLE_BUT_NOT_BILLED)]
    if disputed:
        out.append("### Disputed conversations")
        out.append("")
        out.append("| conversation | export line | finding |")
        out.append("|---|---:|---|")
        for v in disputed:
            out.append("| `%s` | %d | %s |"
                       % (v["conversation_id"], v["line"],
                          _VERDICT_LABEL[v["verdict"]]))
        out.append("")

    unsettled = [v for v in t1["verdicts"] if v["verdict"] == CANNOT_SETTLE]
    if unsettled:
        out.append("### Cannot settle (removed from the claim)")
        out.append("")
        out.append("| conversation | export line |")
        out.append("|---|---:|")
        for v in unsettled:
            out.append("| `%s` | %d |" % (v["conversation_id"], v["line"]))
        out.append("")

    if pack.get("tier2"):
        t2 = pack["tier2"]
        summary = t2["metering_summary"]
        out.append("## Tier 2 — AgentMeasure settlement standard")
        out.append("")
        out.append("Applied to our own effect records, independent of the vendor's "
                   "counting.")
        out.append("")
        out.append("| outcome class | count |")
        out.append("|---|---:|")
        for cls, n in sorted(summary.get("by_outcome_class", {}).items()):
            out.append("| `%s` | %d |" % (cls, n))
        out.append("")
        out.append("| observer grade | count |")
        out.append("|---|---:|")
        for grade, n in sorted(summary.get("by_observer_grade", {}).items()):
            out.append("| `%s` | %d |" % (grade, n))
        out.append("")
        out.append("Tier 2 is renewal leverage, not a dispute line: it is our "
                   "standard, not the vendor's.")
        out.append("")

    if pack.get("claim", {}).get("payback"):
        p = pack["claim"]["payback"]
        out.append("## Payback")
        out.append("")
        out.append("At this rate, %s %s per month against an audit cost of "
                   "%s: **%s months**."
                   % (pack["currency"], p["monthly_variance"],
                      p["audit_cost"], p["months_to_payback"]))
        out.append("")

    out.append("---")
    out.append("")
    out.append("## Provenance")
    out.append("")
    inp = pack["inputs"]
    out.append("- export: `%s` sha256 `%s`" % (inp["export_file"],
                                               inp["export_sha256"][:16]))
    if pack.get("tier2"):
        ti = pack["tier2"]["inputs"]
        out.append("- effects: `%s` sha256 `%s`" % (ti["effects_file"],
                                                    ti["effects_sha256"][:16]))
    out.append("- pack schema: %s v%s" % (pack["schema"], pack["schema_version"]))
    out.append("- generated: %s" % pack["generated_at"])
    out.append("")
    out.append("No message text, customer content, or helpdesk credential is "
               "read to produce this pack.")
    return "\n".join(out)


def write_pack(pack: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    """Write the pack as JSON + Markdown. Returns the paths written."""
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "dispute-pack.json")
    md_path = os.path.join(out_dir, "dispute-pack.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(pack, fh, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_pack_markdown(pack) + "\n")
    return {"json": json_path, "markdown": md_path}
