"""Decision-use journal — the third value bucket, made recordable.

BP r32 keeps three kinds of value in separate books: cash recovered
(recovery ledger), hours saved (delivery journal), and **decisions the
buyer made differently because of the verification**. This module is the
third book: a tiny append-only local journal where each entry records one
decision — a payment approved or held, a renewal signed, a vendor review —
linked back to the finding (or the whole review) that informed it.

Discipline carried over from the other books:
- an enum of decision types; anything else is refused;
- entries link to a finding (conversation id) or the review as a whole;
- outcomes are stated, never implied — "renewal signed at same terms" and
  "renewal signed with discount" are different records;
- amounts are informational context, never summed with recovered cash.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

DECISION_TYPES = ("payment_approved", "payment_held", "discount_requested",
                  "renewal_signed", "vendor_review", "vendor_changed",
                  "no_action")
OUTCOMES = ("pending", "resolved")


class DecisionError(ValueError):
    pass


def log_entry(path: str, engagement: str, vendor: str,
              decision_type: str, linked: str = "", outcome: str = "pending",
              amount: Optional[float] = None, note: str = "") -> Dict[str, Any]:
    if not engagement or not vendor:
        raise DecisionError("engagement and vendor are both required")
    if decision_type not in DECISION_TYPES:
        raise DecisionError("decision type %r must be one of: %s"
                            % (decision_type, ", ".join(DECISION_TYPES)))
    if outcome not in OUTCOMES:
        raise DecisionError("outcome %r must be one of: %s"
                            % (outcome, ", ".join(OUTCOMES)))
    if amount is not None and amount < 0:
        raise DecisionError("amount must be non-negative; it is context, "
                            "never a recovery claim")
    entry = {
        "date": date.today().isoformat(),
        "engagement": engagement,
        "vendor": vendor,
        "decision_type": decision_type,
        "linked": linked or "(whole review)",
        "outcome": outcome,
        "amount": round(amount, 2) if amount is not None else None,
    }
    if note:
        entry["note"] = note
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return entry


def load_entries(path: str) -> List[Dict[str, Any]]:
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                raise DecisionError("line %d of %s is not valid JSONL"
                                    % (i + 1, path)) from None
    return entries


def report(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_type: Dict[str, int] = {}
    by_vendor: Dict[str, int] = {}
    pending = 0
    for e in entries:
        by_type[e["decision_type"]] = by_type.get(e["decision_type"], 0) + 1
        by_vendor[e["vendor"]] = by_vendor.get(e["vendor"], 0) + 1
        if e.get("outcome") == "pending":
            pending += 1
    return {
        "entries_total": len(entries),
        "by_type": by_type,
        "by_vendor": by_vendor,
        "pending": pending,
        "reading": "decision records are evidence that verification changed "
                   "a business decision; amounts are context and are never "
                   "added to recovered cash",
    }


def report_text(rep: Dict[str, Any]) -> str:
    W = 58
    out = ["Decision-use journal — the third value book", "=" * W]
    out.append("entries: %d (%d still pending)" % (rep["entries_total"],
                                                   rep["pending"]))
    if rep["by_type"]:
        out.append("")
        out.append("by decision type:")
        for t, n in sorted(rep["by_type"].items()):
            out.append("  %-22s %d" % (t, n))
    if rep["by_vendor"]:
        out.append("")
        out.append("by vendor:")
        for v, n in sorted(rep["by_vendor"].items()):
            out.append("  %-22s %d" % (v, n))
    out.append("")
    out.append(rep["reading"] + ".")
    if not rep["entries_total"]:
        out.append("")
        out.append("Nothing recorded yet. Record a decision as it happens:")
        out.append("  agentmeasure decisions --log decisions.jsonl \\")
        out.append("      --log-event --engagement ACME --vendor intercom \\")
        out.append("      --type renewal_signed --linked C-1003 \\")
        out.append("      --outcome resolved --note \"same terms, after review\"")
    return "\n".join(out)
