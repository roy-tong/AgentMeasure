"""Recovery ledger — what the vendor actually conceded, not what we claimed.

The fourth row of the product page (BP r28 p8): 实际退款/抵扣 gets its own
table, linked back to the original disputed lines, with the confirmation date
and the evidence reference. Realized value is counted separately from the
claim: a dispute never becomes "recovered" because we argued well — only when
the vendor confirms, credits, or pays.

Input: a dispute pack (dispute.py output) plus a confirmations CSV the buyer
maintains as concessions arrive. Output: a ledger CSV + a Markdown summary.

Discipline enforced here:
- an amount larger than the claimed amount for that line is an input error,
  not an over-recovery — refused, never silently accepted;
- confirmation rows naming conversations the pack does not contain are listed
  as unmatched, never dropped and never counted;
- realized value counts only `credited` and `paid` rows; `accepted` is a
  concession on paper, not cash.
"""
from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List, Optional

PACK_SCHEMA = "agentmeasure.commercial/dispute-pack"

STATUS_REALIZED = ("credited", "paid")
STATUS_KNOWN = ("accepted", "credited", "paid", "rejected", "pending")

LEDGER_HEADER = ["conversation_id", "export_line", "original_finding",
                 "claimed_amount", "status", "confirmed_date",
                 "realized_amount", "evidence_ref", "note"]


class RecoveryError(ValueError):
    """Raised for input errors: better refused than mis-summed."""


def load_confirmations(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        if "conversation_id" not in fields:
            raise RecoveryError(
                "confirmations CSV needs a conversation_id column; got: %s"
                % ", ".join(reader.fieldnames or []))
        if "status" not in fields:
            raise RecoveryError("confirmations CSV needs a status column "
                                "(accepted/credited/paid/rejected/pending)")
        rows = []
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            status = row.get("status", "").lower()
            if status not in STATUS_KNOWN:
                raise RecoveryError(
                    "line %d: unknown status %r (known: %s)"
                    % (i + 2, row.get("status"), "/".join(STATUS_KNOWN)))
            amount_text = row.get("amount", "")
            amount: Optional[float] = None
            if amount_text:
                try:
                    amount = round(float(amount_text), 2)
                except ValueError:
                    raise RecoveryError(
                        "line %d: amount %r is not a number"
                        % (i + 2, amount_text)) from None
                if amount < 0:
                    raise RecoveryError("line %d: negative amount" % (i + 2))
            rows.append({
                "line": i + 2,
                "conversation_id": row.get("conversation_id"),
                "status": status,
                "confirmed_date": row.get("confirmed_date", ""),
                "amount": amount,
                "evidence_ref": row.get("evidence_ref", ""),
                "note": row.get("note", ""),
            })
    return rows


def _claimed_by_conversation(pack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Claimed amount per disputed conversation, from the pack's own numbers."""
    price = pack.get("unit_price")
    claimed: Dict[str, Dict[str, Any]] = {}
    for v in pack.get("tier1", {}).get("verdicts", []):
        if v["verdict"] != "billed_but_not_billable":
            continue
        claimed[str(v["conversation_id"])] = {
            "export_line": v["line"],
            "finding": v["verdict"],
            "claimed_amount": round(price, 2) if price else None,
        }
    return claimed


def build_ledger_from_pack(pack: Dict[str, Any],
                           confirmations_path: str) -> Dict[str, Any]:
    """Join confirmations to an in-memory dispute pack. Refuses to guess."""
    if pack.get("schema") != PACK_SCHEMA:
        raise RecoveryError(
            "not a dispute pack (schema %r)" % pack.get("schema"))
    claimed = _claimed_by_conversation(pack)
    confirmations = load_confirmations(confirmations_path)

    events_by_conversation: Dict[str, List[Dict[str, Any]]] = {}
    unmatched: List[Dict[str, Any]] = []
    for ev in confirmations:
        cid = ev["conversation_id"]
        if cid in claimed:
            events_by_conversation.setdefault(cid, []).append(ev)
        else:
            unmatched.append(ev)

    # An over-claimed concession is an input error: refuse rather than absorb.
    for cid, events in sorted(events_by_conversation.items()):
        realized = sum(e["amount"] or 0.0 for e in events
                       if e["status"] in STATUS_REALIZED)
        ceiling = claimed[cid]["claimed_amount"]
        if ceiling is not None and realized > ceiling + 0.005:
            raise RecoveryError(
                "conversation %s: realized %.2f exceeds the claimed %.2f — "
                "fix the confirmations CSV before a ledger is produced"
                % (cid, realized, ceiling))

    rows: List[Dict[str, Any]] = []
    for cid, info in sorted(claimed.items()):
        events = events_by_conversation.get(cid, [])
        realized = round(sum(e["amount"] or 0.0 for e in events
                             if e["status"] in STATUS_REALIZED), 2)
        if events:
            latest = max(events, key=lambda e: (e["confirmed_date"], e["line"]))
            status = latest["status"]
            date = latest["confirmed_date"]
            refs = "; ".join(e["evidence_ref"] for e in events
                             if e["evidence_ref"])
            notes = "; ".join(e["note"] for e in events if e["note"])
        else:
            status, date, refs, notes = "no_concession", "", "", ""
        rows.append({
            "conversation_id": cid,
            "export_line": info["export_line"],
            "original_finding": info["finding"],
            "claimed_amount": info["claimed_amount"],
            "status": status,
            "confirmed_date": date,
            "realized_amount": realized if events else 0.0,
            "evidence_ref": refs,
            "note": notes,
        })

    total_claimed = round(sum(r["claimed_amount"] or 0.0 for r in rows), 2)
    total_realized = round(sum(r["realized_amount"] for r in rows), 2)
    rejected = sum(1 for r in rows if r["status"] == "rejected")
    pending = sum(1 for r in rows
                  if r["status"] in ("no_concession", "accepted", "pending"))
    return {
        "pack_file": "(pack)",
        "confirmations_file": os.path.basename(confirmations_path),
        "currency": pack.get("currency"),
        "rows": rows,
        "unmatched": unmatched,
        "totals": {
            "disputed_lines": len(rows),
            "claimed": total_claimed,
            "realized": total_realized,
            "outstanding": round(total_claimed - total_realized, 2),
            "rejected_lines": rejected,
            "pending_lines": pending,
        },
    }


def build_ledger(pack_path: str, confirmations_path: str) -> Dict[str, Any]:
    """Join confirmations to a dispute pack on disk. Refuses to guess."""
    with open(pack_path, "r", encoding="utf-8") as fh:
        pack = json.load(fh)
    ledger = build_ledger_from_pack(pack, confirmations_path)
    ledger["pack_file"] = os.path.basename(pack_path)
    return ledger


def ledger_csv(ledger: Dict[str, Any]) -> str:
    import io
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(LEDGER_HEADER)
    for r in ledger["rows"]:
        writer.writerow([r["conversation_id"], r["export_line"],
                         r["original_finding"], r["claimed_amount"],
                         r["status"], r["confirmed_date"],
                         r["realized_amount"], r["evidence_ref"], r["note"]])
    return buf.getvalue()


def ledger_markdown(ledger: Dict[str, Any]) -> str:
    t = ledger["totals"]
    currency = ledger.get("currency") or ""
    out = []
    out.append("# Recovery ledger — realized value, counted separately")
    out.append("")
    out.append("Source pack: `%s` · confirmations: `%s`"
               % (ledger["pack_file"], ledger["confirmations_file"]))
    out.append("")
    out.append("| | %s |" % currency)
    out.append("|---|---:|")
    out.append("| claimed on disputed lines | %s |" % t["claimed"])
    out.append("| **realized (credited + paid)** | **%s** |" % t["realized"])
    out.append("| outstanding | %s |" % t["outstanding"])
    out.append("")
    out.append("Disputed lines: %d · rejected: %d · awaiting concession: %d"
               % (t["disputed_lines"], t["rejected_lines"], t["pending_lines"]))
    if ledger["unmatched"]:
        out.append("")
        out.append("## Unmatched confirmation rows (listed, never counted)")
        out.append("")
        out.append("| confirmations line | conversation | status |")
        out.append("|---|---:|---|")
        for ev in ledger["unmatched"]:
            out.append("| %d | `%s` | %s |"
                       % (ev["line"], ev["conversation_id"], ev["status"]))
    out.append("")
    out.append("Realized value here is cash tied to a disputed line: a vendor "
               "confirmation, a credit note, or a payment, each with its "
               "evidence reference. Renewal savings and avoided cost live "
               "elsewhere and are never added to these numbers.")
    return "\n".join(out)


def write_ledger(ledger: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "recovery-ledger.csv")
    md_path = os.path.join(out_dir, "recovery-ledger.md")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(ledger_csv(ledger))
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(ledger_markdown(ledger) + "\n")
    return {"csv": csv_path, "markdown": md_path}
