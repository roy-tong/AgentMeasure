"""Verified Ledger — one artifact that joins every lane (BP r28 p8).

Four inputs in, one judgement out, per line: Tier 1 (the vendor's own rules),
the buyer's outcome-standard lane, the billing-ledger cross-check, and Tier 2
(effect records) when supplied — plus realized recovery when concessions are
supplied. Each lane keeps its own status (claim / leverage / realized) and the
ledger never sums across lanes.

`dispute` stays the *negotiable* pack a buyer hands to a vendor. The Verified
Ledger is the *master record*: the same facts plus every internal lane, so a
finance reviewer can recompute the whole story from one file.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import crosscheck as crosscheck_mod
from . import dispute as dispute_mod
from . import recovery as recovery_mod
from . import vendors as vendors_mod

LEDGER_SCHEMA = "agentmeasure.commercial/verified-ledger"
LEDGER_SCHEMA_VERSION = "0.1.0"


def _sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_ledger_document(export_path: str,
                          vendor_id: str,
                          contract_path: Optional[str] = None,
                          effects_path: Optional[str] = None,
                          ledger_path: Optional[str] = None,
                          confirmations_path: Optional[str] = None,
                          price: Optional[float] = None,
                          audit_cost: Optional[float] = None,
                          period_start: Optional[str] = None,
                          period_end: Optional[str] = None,
                          buyer_label: Optional[str] = None) -> Dict[str, Any]:
    """Compose the Verified Ledger from every supplied input. Judges nothing new."""
    export = vendors_mod.load_export(export_path)
    tier1 = vendors_mod.recount(export, vendor_id)
    vendor = vendors_mod.get_vendor(vendor_id)
    unit_price = price if price is not None else tier1.get("unit_price")

    doc: Dict[str, Any] = {
        "schema": LEDGER_SCHEMA,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vendor": {
            "id": vendor_id,
            "name": vendor["name"],
            "rule_confidence": vendor["confidence"],
            "rule_source": vendor["source"],
            "rules_version": vendors_mod.RULES_VERSION,
        },
        "buyer_label": buyer_label or "(unspecified)",
        "period": {"start": period_start, "end": period_end},
        "unit_price": unit_price,
        "currency": vendor.get("currency"),
        "tier1": tier1,
        "outcome_lane": None,
        "billing_crosscheck": None,
        "tier2": None,
        "recovery": None,
        "inputs": {
            "export_file": os.path.basename(export_path),
            "export_sha256": _sha256_of(export_path),
            "columns_missing": export["columns_missing"],
        },
        "lane_rules": {
            "claim": "Tier 1 contract variance, netted both ways; cannot-settle removed",
            "leverage": "outcome-standard findings; never netted into the claim",
            "realized": "vendor concessions actually credited or paid",
        },
    }

    if contract_path:
        contract = vendors_mod.load_contract(contract_path)
        doc["outcome_lane"] = vendors_mod.outcome_lane(export, vendor_id, contract)
        doc["inputs"]["contract_file"] = os.path.basename(contract_path)
        doc["inputs"]["contract_sha256"] = _sha256_of(contract_path)
    if ledger_path:
        rows = crosscheck_mod.load_ledger(ledger_path)
        doc["billing_crosscheck"] = crosscheck_mod.crosscheck(
            export, rows, vendor_id)
        doc["inputs"]["ledger_file"] = os.path.basename(ledger_path)
        doc["inputs"]["ledger_sha256"] = _sha256_of(ledger_path)
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
        doc["tier2"] = {
            "metering_summary": bundle.get("metering_summary", {}),
            "inputs": {"effects_file": os.path.basename(effects_path),
                       "effects_sha256": _sha256_of(effects_path)},
        }
        tmp = os.path.join(os.path.dirname(os.path.abspath(export_path)) or ".",
                           ".agentmeasure-tier2-tmp.json")
        if os.path.exists(tmp):
            os.unlink(tmp)
    if confirmations_path:
        # The recovery join runs against the dispute-pack form of this ledger,
        # written beside it; the ledger and the pack must agree by construction.
        pack = {
            "schema": dispute_mod.PACK_SCHEMA,
            "unit_price": unit_price,
            "currency": vendor.get("currency"),
            "tier1": tier1,
        }
        doc["recovery"] = recovery_mod.build_ledger_from_pack(
            pack, confirmations_path)
        doc["inputs"]["confirmations_file"] = os.path.basename(confirmations_path)
    return doc


def ledger_markdown(doc: Dict[str, Any]) -> str:
    t1 = doc["tier1"]
    c = t1["counts"]
    t = t1["three_state_counts"]
    out = []
    out.append("# Verified Ledger — %s" % doc["vendor"]["name"])
    out.append("")
    period = doc["period"]
    span = " to ".join(x for x in (period.get("start"), period.get("end")) if x) \
        or "period as exported"
    out.append("%s · buyer: %s · generated %s"
               % (span, doc["buyer_label"], doc["generated_at"]))
    out.append("")
    out.append("Rules: %s (registry v%s, confidence %s)"
               % (doc["vendor"]["rule_source"], doc["vendor"]["rules_version"],
                  doc["vendor"]["rule_confidence"]))
    out.append("")
    out.append("## Line judgements (Tier 1)")
    out.append("")
    out.append("| PASS | FAIL | UNPROVABLE |")
    out.append("|---:|---:|---:|")
    out.append("| %d | %d | %d |" % (t["PASS"], t["FAIL"], t["UNPROVABLE"]))
    out.append("")
    out.append("| | conversations |")
    out.append("|---|---:|")
    out.append("| billed, not billable under the vendor's own rule | %d |"
               % c["billed_but_not_billable"])
    out.append("| billable under the vendor's own rule, not billed | %d |"
               % c["billable_but_not_billed"])
    out.append("| cannot settle (removed, not zeroed) | %d |"
               % c["cannot_settle"])
    if "variance" in t1:
        out.append("| **net variance (%s)** | **%.2f** |"
                   % (doc.get("currency") or "", t1["variance"]))
    out.append("")

    lane = doc.get("outcome_lane")
    if lane:
        lc = lane["counts"]
        out.append("## Outcome-standard lane — %s (leverage, not claim)" % lane["label"])
        out.append("")
        out.append("| fails | meets | unprovable | not reviewed |")
        out.append("|---:|---:|---:|---:|")
        out.append("| %d | %d | %d | %d |"
                   % (lc["fails_buyer_standard"], lc["meets_buyer_standard"],
                      lc["unprovable"], lc["not_reviewed"]))
        if "at_risk_amount" in lane:
            out.append("")
            out.append("At risk under our standard: %s %s (informational)."
                       % (doc.get("currency") or "", lane["at_risk_amount"]))
        out.append("")

    cc = doc.get("billing_crosscheck")
    if cc:
        out.append("## Billing-ledger cross-check (named, not resolved)")
        out.append("")
        out.append("| disagreements | count |")
        out.append("|---|---:|")
        out.append("| export billed, ledger has no line | %d |"
                   % len(cc["flag_without_charge"]))
        out.append("| ledger charged, export says not billed | %d |"
                   % len(cc["charge_without_export_flag"]))
        out.append("| charged per ledger, absent from export | %d |"
                   % len(cc["not_in_export"]))
        out.append("| amount deviates from published price | %d |"
                   % len(cc["amount_deviation"]))
        out.append("")

    rec = doc.get("recovery")
    if rec:
        rt = rec["totals"]
        out.append("## Recovery — realized, counted separately")
        out.append("")
        out.append("| claimed | realized | outstanding |")
        out.append("|---:|---:|---:|")
        out.append("| %s | %s | %s |"
                   % (rt["claimed"], rt["realized"], rt["outstanding"]))
        out.append("")

    out.append("---")
    out.append("")
    out.append("## Provenance")
    out.append("")
    inp = doc["inputs"]
    out.append("- export: `%s` sha256 `%s`"
               % (inp["export_file"], inp["export_sha256"][:16]))
    for key, sha_key, label in (
            ("contract_file", "contract_sha256", "contract overlay"),
            ("ledger_file", "ledger_sha256", "billing ledger"),
            ("confirmations_file", None, "confirmations")):
        if key in inp:
            line = "- %s: `%s`" % (label, inp[key])
            if sha_key and sha_key in inp:
                line += " sha256 `%s`" % inp[sha_key][:16]
            out.append(line)
    if doc.get("tier2"):
        ti = doc["tier2"]["inputs"]
        out.append("- effects: `%s` sha256 `%s`"
                   % (ti["effects_file"], ti["effects_sha256"][:16]))
    out.append("- ledger schema: %s v%s"
               % (doc["schema"], doc["schema_version"]))
    out.append("")
    out.append("No message text, customer content, or helpdesk credential is "
               "read to produce this ledger.")
    return "\n".join(out)


def write_ledger_document(doc: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "verified-ledger.json")
    md_path = os.path.join(out_dir, "verified-ledger.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(ledger_markdown(doc) + "\n")
    return {"json": json_path, "markdown": md_path}
