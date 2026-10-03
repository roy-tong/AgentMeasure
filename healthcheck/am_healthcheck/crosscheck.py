"""Billing-ledger cross-check — the 计费流水 input (BP r28 p5).

The export says what the vendor's helpdesk counted; the billing ledger says
what actually left the buyer's money. P5's whole point is that these live in
different systems and are never put side by side ("计费系统：已扣费——钱已
出去了，事后无从对起"). This module puts them side by side.

The ledger is the buyer's own record (invoice line items, billing-system
export): one row per charged unit. The cross-check classifies every
disagreement instead of resolving it:

- ``flag_without_charge``  export says billed, ledger has no such line — the
  dispute claim stands on the export, but the billing evidence is absent and
  is named as missing;
- ``charge_without_export_flag``  ledger shows a charge on a line the export
  says was not billed (or that the export does not contain at all);
- ``amount_deviation``     charged amount differs from the vendor's published
  unit price (only checked when the registry carries a price).

Nothing here decides who is right. It names the disagreement so a human can.
"""
from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional

from . import vendors as vendors_mod


class LedgerError(ValueError):
    """Raised for unreadable or malformed billing-ledger input."""


def load_ledger(path: str) -> List[Dict[str, Any]]:
    """Read a buyer-side billing ledger CSV (conversation_id required)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        if "conversation_id" not in fields:
            raise LedgerError(
                "billing ledger needs a conversation_id column; got: %s"
                % ", ".join(reader.fieldnames or []))
        rows: List[Dict[str, Any]] = []
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            amount: Optional[float] = None
            text = row.get("amount", "")
            if text:
                try:
                    amount = round(float(text), 2)
                except ValueError:
                    raise LedgerError(
                        "line %d: amount %r is not a number" % (i + 2, text)
                    ) from None
            rows.append({
                "line": i + 2,
                "conversation_id": row.get("conversation_id"),
                "amount": amount,
                "billed_at": row.get("billed_at", ""),
                "currency": row.get("currency", ""),
            })
    return rows


def crosscheck(export: Dict[str, Any], ledger_rows: List[Dict[str, Any]],
               vendor_id: str) -> Dict[str, Any]:
    """Classify every disagreement between export and billing ledger."""
    vendor = vendors_mod.get_vendor(vendor_id)
    price = vendor.get("unit_price")

    export_by_id: Dict[str, Dict[str, Any]] = {}
    for rec in export["records"]:
        cid = rec.get("conversation_id")
        if cid is not None:
            export_by_id[str(cid)] = rec

    ledger_ids = set()
    flag_without_charge: List[Dict[str, Any]] = []
    amount_deviation: List[Dict[str, Any]] = []
    charged_total = 0.0
    charged_rows = 0

    ledger_by_id: Dict[str, List[Dict[str, Any]]] = {}
    for row in ledger_rows:
        cid = str(row["conversation_id"])
        ledger_ids.add(cid)
        ledger_by_id.setdefault(cid, []).append(row)
        if row["amount"] is not None:
            charged_total += row["amount"]
            charged_rows += 1

    # Export side: billed flags that the ledger does not confirm.
    for cid, rec in sorted(export_by_id.items()):
        billed = vendors_mod._as_bool(rec.get("vendor_billed"))
        if billed is not True:
            continue
        if cid not in ledger_by_id:
            flag_without_charge.append({
                "conversation_id": cid,
                "export_line": None,
                "reason": "export says billed; billing ledger has no such line",
            })
        elif price and any(r["amount"] is not None for r in ledger_by_id[cid]):
            for r in ledger_by_id[cid]:
                if r["amount"] is not None and abs(r["amount"] - price) > 0.005:
                    amount_deviation.append({
                        "conversation_id": cid,
                        "ledger_line": r["line"],
                        "expected": round(price, 2),
                        "charged": r["amount"],
                    })

    # Ledger side: charges the export does not flag or does not contain.
    charge_without_flag: List[Dict[str, Any]] = []
    not_in_export: List[Dict[str, Any]] = []
    for cid in sorted(ledger_by_id):
        rows = ledger_by_id[cid]
        rec = export_by_id.get(cid)
        if rec is None:
            not_in_export.append({
                "conversation_id": cid,
                "ledger_line": rows[0]["line"],
                "reason": "charged per ledger; id not present in the export",
            })
            continue
        billed = vendors_mod._as_bool(rec.get("vendor_billed"))
        if billed is None:
            continue  # export itself could not say; Tier 1 already UNPROVABLE
        if billed is False:
            charge_without_flag.append({
                "conversation_id": cid,
                "ledger_line": rows[0]["line"],
                "reason": "charged per ledger; export says not billed",
            })

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "ledger_rows": len(ledger_rows),
        "matched_billed": sum(
            1 for cid, rec in export_by_id.items()
            if vendors_mod._as_bool(rec.get("vendor_billed")) is True
            and cid in ledger_by_id),
        "flag_without_charge": flag_without_charge,
        "charge_without_export_flag": charge_without_flag,
        "not_in_export": not_in_export,
        "amount_deviation": amount_deviation,
        "totals": {
            "ledger_charged": round(charged_total, 2) if charged_rows else None,
            "ledger_charge_rows": charged_rows,
            "export_billed_lines": sum(
                1 for rec in export["records"]
                if vendors_mod._as_bool(rec.get("vendor_billed")) is True),
        },
        "reading": "disagreements are named, not resolved; each needs a human",
    }


def crosscheck_report(result: Dict[str, Any]) -> str:
    W = 58
    t = result["totals"]
    out = []
    out.append("Billing-ledger cross-check — 计费流水 vs 厂商口径")
    out.append("=" * W)
    out.append("Vendor: %s" % result["vendor_name"])
    out.append("ledger rows: %d · matched billed: %d"
               % (result["ledger_rows"], result["matched_billed"]))
    if t["ledger_charged"] is not None:
        out.append("ledger charged total: %.2f over %d row(s)"
                   % (t["ledger_charged"], t["ledger_charge_rows"]))
    out.append("")
    out.append("export says billed, ledger has no line:  %d"
               % len(result["flag_without_charge"]))
    out.append("ledger shows charge, export says not:    %d"
               % len(result["charge_without_export_flag"]))
    out.append("charged per ledger, absent from export:  %d"
               % len(result["not_in_export"]))
    out.append("amount deviates from published price:    %d"
               % len(result["amount_deviation"]))
    if result["flag_without_charge"] or result["charge_without_export_flag"] \
            or result["not_in_export"]:
        out.append("")
        out.append("These are named disagreements, not findings: the export")
        out.append("and the billing system are different witnesses, and a")
        out.append("discrepancy needs a human before it becomes a claim.")
    return "\n".join(out)
