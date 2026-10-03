"""Channel Demand Audit (F2.12) — potential and performance, never blended.

Two different questions two different people ask:
- **Channel Potential**: does this channel have volume at all? (agent
  traffic, brand-category intent share, paid inventory depth, commercial
  task frequency)
- **Operator Performance**: are WE operating it well? (conversion rate,
  contribution margin %)

A channel can be worth launching and badly operated; a well-operated channel
with no volume is still not ready. The audit scores the two axes from
thresholded metrics — every metric names its threshold and which axis it
feeds — and lands on exactly one verdict:

  Launch    potential AND performance both meet the bar
  Watch     potential meets the bar, performance does not — the channel is
            real, our operating is the problem
  Not ready potential does not meet the bar — no operating skill fixes an
            empty channel
"""
from __future__ import annotations

import csv
import json
from typing import Any, Dict, List

AXIS_METRICS = {
    "channel_potential": ("agent_traffic", "brand_category_intent_share",
                          "paid_inventory_depth", "commercial_task_frequency"),
    "operator_performance": ("conversion_rate", "contribution_margin_pct"),
}
VERDICTS = ("Launch", "Watch", "Not ready")


class AuditError(ValueError):
    pass


def load_thresholds(path: str) -> Dict[str, Dict[str, float]]:
    """JSON: {metric: {"axis": ..., "threshold": ...}} — or with defaults."""
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    known = set()
    for axis, metrics in AXIS_METRICS.items():
        known.update(metrics)
    out: Dict[str, Dict[str, float]] = {}
    for metric, spec in doc.items():
        if metric not in known:
            raise AuditError("unknown audit metric %r; known: %s"
                             % (metric, ", ".join(sorted(known))))
        axis = spec.get("axis") or next(
            a for a, ms in AXIS_METRICS.items() if metric in ms)
        out[metric] = {"axis": axis,
                       "threshold": float(spec["threshold"])}
    return out


def load_measurements(path: str) -> Dict[str, float]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        if "metric" not in fields or "value" not in fields:
            raise AuditError("measurements need metric and value columns")
        out = {}
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            try:
                out[row["metric"]] = float(row["value"])
            except ValueError:
                raise AuditError("line %d: value %r is not a number"
                                 % (i + 2, row.get("value"))) from None
    return out


def audit_channel(measurements: Dict[str, float],
                  thresholds: Dict[str, Dict[str, float]],
                  channel: str = "") -> Dict[str, Any]:
    axes = {"channel_potential": {"met": 0, "total": 0, "rows": []},
            "operator_performance": {"met": 0, "total": 0, "rows": []}}
    for metric, spec in sorted(thresholds.items()):
        axis_name = spec.get("axis") or next(
            (a for a, ms in AXIS_METRICS.items() if metric in ms), None)
        if axis_name not in axes:
            raise AuditError("metric %r: unknown axis %r"
                             % (metric, spec.get("axis")))
        axis = axes[axis_name]
        axis["total"] += 1
        value = measurements.get(metric)
        if value is None:
            axis["rows"].append({"metric": metric, "value": None,
                                 "threshold": spec["threshold"],
                                 "meets": None,
                                 "note": "not measured — counts as NOT met, "
                                         "never assumed"})
            continue
        meets = value >= spec["threshold"]
        if meets:
            axis["met"] += 1
        axis["rows"].append({"metric": metric, "value": value,
                             "threshold": spec["threshold"], "meets": meets})

    potential = axes["channel_potential"]
    performance = axes["operator_performance"]
    potential_ok = (potential["total"] > 0
                    and potential["met"] >= (potential["total"] + 1) // 2)
    performance_ok = (performance["total"] > 0
                      and performance["met"] >= (performance["total"] + 1) // 2)
    if potential_ok and performance_ok:
        verdict = "Launch"
        reading = "channel has volume and our operating meets the bar"
    elif potential_ok:
        verdict = "Watch"
        reading = ("the channel is real; OUR operating is the gap — launch "
                   "decisions wait for the operator metrics, not the market")
    else:
        verdict = "Not ready"
        reading = "no volume to operate on; no skill fixes an empty channel"

    return {
        "schema": "agentmeasure.commerce/demand-audit",
        "schema_version": "0.1.0",
        "channel": channel or "(channel under audit)",
        "axes": {k: {kk: vv for kk, vv in v.items()} for k, v in axes.items()},
        "verdict": verdict,
        "reading": reading,
        "rule": "potential and performance are different questions from "
                "different owners; the verdict names which axis failed",
    }


def audit_markdown(result: Dict[str, Any]) -> str:
    out = ["# Channel Demand Audit — %s" % result["channel"], ""]
    out.append("**Verdict: %s** — %s." % (result["verdict"], result["reading"]))
    out.append("")
    out.append("| axis | metric | value | threshold | meets |")
    out.append("|---|---|---:|---:|---|")
    for axis_name, axis in result["axes"].items():
        for row in axis["rows"]:
            out.append("| %s | %s | %s | %s | %s |"
                       % (axis_name, row["metric"],
                          "—" if row["value"] is None else row["value"],
                          row["threshold"],
                          ("yes" if row["meets"] else "NO")
                          if row["meets"] is not None else "not measured"))
    out.append("")
    out.append(result["rule"] + ".")
    return "\n".join(out)
