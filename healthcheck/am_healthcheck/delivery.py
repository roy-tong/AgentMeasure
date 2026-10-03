"""Delivery-reuse metrics — 附录 E made measurable (BP r28 p17 Q5).

附录 E's three numbers — first look ≤10h, third period ≤1h, reuse ≥70% — are
only checkable if engagements are logged as they happen, not recalled
afterwards. This module is a deliberately small local journal: one JSONL
append per work phase (`prepare`, judgment, recount, dispute, delivery…),
keyed by engagement, vendor, billing period index, and the *mapping
fingerprint* that `prepare` emits (which columns a native export really
carries — two engagements sharing it share the reusable part of the work).

The report derives the appendix numbers honestly:
- first-look hours = period-1 minutes per engagement, against the 10h bar;
- third-period minutes per engagement, against the 1h bar;
- reuse rate = engagements that came back for a later period ÷ engagements
  with any logged period (the 次月复用 proxy), plus which engagements share a
  mapping fingerprint with an earlier one (the mapping-reuse fact).

Local file only. No client data goes in a fingerprint — column provenance
names, not values.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PHASES = ("prepare", "mapping", "judgment", "recount", "dispute",
          "recovery", "delivery", "review")

_FIRST_LOOK_HOURS_BAR = 10.0
_THIRD_PERIOD_MINUTES_BAR = 60.0


class DeliveryError(ValueError):
    pass


def log_event(path: str, engagement: str, vendor: str, period_index: int,
              phase: str, minutes: float, fingerprint: str = "",
              note: str = "") -> Dict[str, Any]:
    if not engagement or not vendor:
        raise DeliveryError("engagement and vendor are both required")
    if not isinstance(period_index, int) or period_index < 1:
        raise DeliveryError("period-index must be a positive integer")
    if phase not in PHASES:
        raise DeliveryError("unknown phase %r; known: %s" % (phase, ", ".join(PHASES)))
    if minutes is None or minutes < 0:
        raise DeliveryError("minutes must be a non-negative number")
    event = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "engagement": engagement,
        "vendor": vendor,
        "period_index": period_index,
        "phase": phase,
        "minutes": round(float(minutes), 1),
        "fingerprint": fingerprint,
    }
    if note:
        event["note"] = note
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True) + "\n")
    return event


def load_events(path: str) -> List[Dict[str, Any]]:
    events = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                raise DeliveryError("line %d of %s is not valid JSONL"
                                    % (i + 1, path)) from None
    return events


def report(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    engagements: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        name = ev.get("engagement") or "(none)"
        e = engagements.setdefault(name, {
            "vendor": ev.get("vendor", ""),
            "fingerprint": ev.get("fingerprint", ""),
            "minutes_by_period": {},
            "total_minutes": 0.0,
        })
        p = str(ev.get("period_index"))
        e["minutes_by_period"][p] = round(
            e["minutes_by_period"].get(p, 0.0) + (ev.get("minutes") or 0.0), 1)
        e["total_minutes"] = round(e["total_minutes"] + (ev.get("minutes") or 0.0), 1)

    first_look = []
    third_period = []
    with_repeat = 0
    for name, e in sorted(engagements.items()):
        first = e["minutes_by_period"].get("1")
        if first is not None:
            first_look.append({
                "engagement": name,
                "hours": round(first / 60.0, 2),
                "within_10h_bar": first <= _FIRST_LOOK_HOURS_BAR * 60,
            })
        third = e["minutes_by_period"].get("3")
        if third is not None:
            third_period.append({
                "engagement": name,
                "minutes": third,
                "within_1h_bar": third <= _THIRD_PERIOD_MINUTES_BAR,
            })
        if any(int(p) >= 2 for p in e["minutes_by_period"]):
            with_repeat += 1

    fingerprint_groups: Dict[str, List[str]] = {}
    for name, e in sorted(engagements.items()):
        if e["fingerprint"]:
            fingerprint_groups.setdefault(e["fingerprint"], []).append(name)
    shared_fingerprints = {
        fp: names for fp, names in sorted(fingerprint_groups.items())
        if len(names) > 1
    }

    total = len(engagements)
    return {
        "engagements_total": total,
        "first_look": first_look,
        "third_period": third_period,
        "reuse": {
            "engagements_with_repeat": with_repeat,
            "engagements_total": total,
            "rate": round(with_repeat / total, 4) if total else None,
            "bar": 0.70,
            "shared_mapping_fingerprints": shared_fingerprints,
        },
        "bars": {"first_look_hours": _FIRST_LOOK_HOURS_BAR,
                 "third_period_minutes": _THIRD_PERIOD_MINUTES_BAR},
    }


def report_text(rep: Dict[str, Any]) -> str:
    W = 58
    out = []
    out.append("Delivery & reuse report — 附录 E metrics")
    out.append("=" * W)
    out.append("engagements logged: %d" % rep["engagements_total"])
    out.append("")
    out.append("First look (bar: ≤%.0fh)" % rep["bars"]["first_look_hours"])
    if rep["first_look"]:
        for f in rep["first_look"]:
            out.append("  %-28s %6.2fh  %s"
                       % (f["engagement"], f["hours"],
                          "within bar" if f["within_10h_bar"] else "OVER bar"))
    else:
        out.append("  (no period-1 work logged yet)")
    out.append("")
    out.append("Third billing period (bar: ≤%.0f min)"
               % rep["bars"]["third_period_minutes"])
    if rep["third_period"]:
        for f in rep["third_period"]:
            out.append("  %-28s %6.1fmin %s"
                       % (f["engagement"], f["minutes"],
                          "within bar" if f["within_1h_bar"] else "OVER bar"))
    else:
        out.append("  (no third-period work logged yet)")
    out.append("")
    r = rep["reuse"]
    if r["rate"] is not None:
        out.append("Repeat-period reuse: %d/%d = %.0f%% (bar ≥%.0f%%)"
                   % (r["engagements_with_repeat"], r["engagements_total"],
                      r["rate"] * 100, r["bar"] * 100))
    if r["shared_mapping_fingerprints"]:
        out.append("Mappings reused across engagements:")
        for fp, names in r["shared_mapping_fingerprints"].items():
            out.append("  %s… %s" % (fp[:12], ", ".join(names)))
    if not rep["first_look"] and not rep["third_period"] and r["rate"] is None:
        out.append("Nothing logged yet. Log phases as they happen:")
        out.append("  agentmeasure delivery --log delivery.jsonl --log-event \\")
        out.append("      --engagement ACME --vendor intercom \\")
        out.append("      --period-index 1 --phase mapping --minutes 45")
    return "\n".join(out)
