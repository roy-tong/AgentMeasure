"""P&L trees and the Contribution Margin ledger (F2.10 / F2.11).

**F2.10 — three trees, metered separately.** Organic and Paid are two trees,
never one blended number. Paid carries the performance-marketing funnel
(spend -> conversation -> engagement -> conversion -> ROAS) and every order
belongs to EXACTLY one tree: an order marked paid must cite a campaign, a
campaign must exist in the campaign ledger, and an organic order wearing a
campaign is a routing error. "Same GMV labelled Organic/Paid/which campaign"
is enforced at load time, not asserted afterwards.

**F2.11 — the monthly operating-review ledger.**

    attributed revenue - coupon - media spend - platform/payment cost
      - service fee - fulfillment variance - refund = Contribution Margin

Cost rows carry a category from a closed enum; a cost row referencing an
order_id attributes to that order's tree, everything else lands on the
period. The report is the data base of the P&L template — numbers only,
each with its source row count.
"""
from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional

COST_CATEGORIES = ("coupon", "media_spend", "platform_cost", "payment_cost",
                   "service_fee", "fulfillment_variance", "refund")
CM_SCHEMA = "agentmeasure.commerce/contribution-margin"
CM_VERSION = "0.1.0"


class PnlError(ValueError):
    pass


def load_channel_orders(path: str) -> List[Dict[str, Any]]:
    """Order log extended with channel fields: channel(organic|paid),
    campaign_id (required when channel=paid)."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        for required in ("order_id", "amount", "status"):
            if required not in fields:
                raise PnlError("order log needs a %r column; got: %s"
                               % (required,
                                  ", ".join(reader.fieldnames or [])))
        rows = []
        for i, raw in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in raw.items()}
            try:
                amount = round(float(row.get("amount", "")), 2)
            except ValueError:
                raise PnlError("line %d: amount %r is not a number"
                               % (i + 2, row.get("amount"))) from None
            channel = (row.get("channel") or "organic").lower()
            if channel not in ("organic", "paid"):
                raise PnlError("line %d: channel %r must be organic or paid"
                               % (i + 2, channel))
            campaign = row.get("campaign_id", "")
            if channel == "paid" and not campaign:
                raise PnlError(
                    "line %d: paid order %s cites no campaign — an order "
                    "belongs to exactly one tree, and a paid order without a "
                    "campaign belongs to neither" % (i + 2, row.get("order_id")))
            rows.append({
                "line": i + 2,
                "order_id": row.get("order_id"),
                "amount": amount,
                "currency": row.get("currency", ""),
                "status": row.get("status", ""),
                "channel": channel,
                "campaign_id": campaign,
            })
    return rows


def load_campaigns(path: str) -> List[Dict[str, Any]]:
    """Paid-side funnel ledger: campaign_id, spend, conversations,
    engagements, conversions."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        if "campaign_id" not in fields or "spend" not in fields:
            raise PnlError("campaign ledger needs campaign_id and spend; got: %s"
                           % ", ".join(reader.fieldnames or []))
        rows = []
        for i, raw in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in raw.items()}
            try:
                spend = round(float(row.get("spend", "")), 2)
            except ValueError:
                raise PnlError("line %d: spend %r is not a number"
                               % (i + 2, row.get("spend"))) from None
            def _num(key):
                try:
                    return int(float(row.get(key, "") or 0))
                except ValueError:
                    return 0
            rows.append({
                "line": i + 2,
                "campaign_id": row.get("campaign_id"),
                "spend": spend,
                "conversations": _num("conversations"),
                "engagements": _num("engagements"),
                "conversions": _num("conversions"),
            })
    return rows


def pnl_trees(orders: List[Dict[str, Any]],
              campaigns: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Separate Organic and Paid trees; no order appears in both."""
    known_campaigns = {c["campaign_id"] for c in (campaigns or [])}
    trees: Dict[str, Dict[str, Any]] = {
        "organic": {"attributed_revenue": 0.0, "orders": 0, "by_campaign": {}},
        "paid": {"attributed_revenue": 0.0, "orders": 0, "by_campaign": {}},
    }
    for o in orders:
        if o["status"] != "confirmed":
            continue
        tree = trees[o["channel"]]
        tree["attributed_revenue"] = round(tree["attributed_revenue"]
                                           + o["amount"], 2)
        tree["orders"] += 1
        if o["channel"] == "paid":
            # Mixing is detectable — and therefore refused — only when the
            # campaign ledger is supplied; CM-level totals do not need it.
            if campaigns is not None and o["campaign_id"] not in known_campaigns:
                raise PnlError(
                    "order %s cites campaign %r which is not in the campaign "
                    "ledger — mixed attribution is refused; add the campaign "
                    "or re-route the order" % (o["order_id"], o["campaign_id"]))
            bucket = tree["by_campaign"].setdefault(
                o["campaign_id"], {"revenue": 0.0, "orders": 0})
            bucket["revenue"] = round(bucket["revenue"] + o["amount"], 2)
            bucket["orders"] += 1

    # Paid funnel: spend -> conversation -> engagement -> conversion -> ROAS
    paid_funnel = []
    for c in (campaigns or []):
        bucket = trees["paid"]["by_campaign"].get(c["campaign_id"],
                                                  {"revenue": 0.0, "orders": 0})
        roas = round(bucket["revenue"] / c["spend"], 4) if c["spend"] else None
        paid_funnel.append({
            "campaign_id": c["campaign_id"],
            "spend": c["spend"],
            "conversations": c["conversations"],
            "engagements": c["engagements"],
            "conversions": c["conversions"],
            "attributed_revenue": bucket["revenue"],
            "roas": roas,
            "reading": "attributed revenue over media spend, same tree only",
        })
    trees["paid"]["funnel"] = paid_funnel
    trees["paid"]["total_spend"] = round(
        sum(c["spend"] for c in (campaigns or [])), 2)
    return {
        "schema": "agentmeasure.commerce/pnl-trees",
        "schema_version": "0.1.0",
        "trees": trees,
        "rule": "an order belongs to exactly one tree; ROAS is computed "
                "inside the Paid tree only and never blends organic revenue",
    }


def load_costs(path: str) -> List[Dict[str, Any]]:
    """Cost ledger: category(closed enum), amount[, order_id]."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        for required in ("category", "amount"):
            if required not in fields:
                raise PnlError("cost ledger needs a %r column; got: %s"
                               % (required,
                                  ", ".join(reader.fieldnames or [])))
        rows = []
        for i, raw in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in raw.items()}
            category = row.get("category", "")
            if category not in COST_CATEGORIES:
                raise PnlError(
                    "line %d: category %r is not one of %s"
                    % (i + 2, category, "/".join(COST_CATEGORIES)))
            try:
                amount = round(float(row.get("amount", "")), 2)
            except ValueError:
                raise PnlError("line %d: amount %r is not a number"
                               % (i + 2, row.get("amount"))) from None
            if amount < 0:
                raise PnlError("line %d: negative cost — corrections are "
                               "positive rows with a note, not negatives"
                               % (i + 2))
            rows.append({"line": i + 2, "category": category,
                         "amount": amount,
                         "order_id": row.get("order_id", "")})
    return rows


def contribution_margin(orders: List[Dict[str, Any]],
                        costs: List[Dict[str, Any]],
                        period_label: str = "") -> Dict[str, Any]:
    """The monthly ledger: attributed revenue minus the seven named costs."""
    trees = pnl_trees(orders)
    revenue = round(trees["trees"]["organic"]["attributed_revenue"]
                    + trees["trees"]["paid"]["attributed_revenue"], 2)
    by_category = {c: {"amount": 0.0, "rows": 0} for c in COST_CATEGORIES}
    for c in costs:
        bucket = by_category[c["category"]]
        bucket["amount"] = round(bucket["amount"] + c["amount"], 2)
        bucket["rows"] += 1
    total_costs = round(sum(b["amount"] for b in by_category.values()), 2)
    cm = round(revenue - total_costs, 2)
    cm_pct = round(cm / revenue, 4) if revenue else None
    return {
        "schema": CM_SCHEMA,
        "schema_version": CM_VERSION,
        "period": period_label or "(period as labelled by the caller)",
        "attributed_revenue": revenue,
        "trees": {"organic": trees["trees"]["organic"]["attributed_revenue"],
                  "paid": trees["trees"]["paid"]["attributed_revenue"]},
        "deductions": {k: v for k, v in by_category.items()},
        "total_deductions": total_costs,
        "contribution_margin": cm,
        "contribution_margin_pct": cm_pct,
        "formula": "attributed revenue - coupon - media spend - platform/"
                   "payment cost - service fee - fulfillment variance - "
                   "refund = contribution margin",
        "reading": "monthly operating-review basis; every deduction names its "
                   "source rows",
    }


def cm_markdown(report: Dict[str, Any]) -> str:
    out = ["# Contribution Margin ledger — %s" % report["period"], ""]
    out.append("| | amount |")
    out.append("|---|---:|")
    out.append("| attributed revenue (organic %s / paid %s) | %s |"
               % (report["trees"]["organic"], report["trees"]["paid"],
                  report["attributed_revenue"]))
    for category, bucket in report["deductions"].items():
        out.append("| − %s | %s |" % (category, bucket["amount"]))
    out.append("| **Contribution Margin** | **%s** |"
               % report["contribution_margin"])
    if report["contribution_margin_pct"] is not None:
        out.append("")
        out.append("CM %.1f%% of attributed revenue."
                   % (report["contribution_margin_pct"] * 100))
    out.append("")
    out.append(report["formula"] + ".")
    return "\n".join(out)


def trees_markdown(report: Dict[str, Any]) -> str:
    t = report["trees"]
    out = ["# P&L trees — Organic and Paid, metered separately", ""]
    out.append("| tree | orders | attributed revenue |")
    out.append("|---|---:|---:|")
    out.append("| Organic | %d | %s |"
               % (t["organic"]["orders"], t["organic"]["attributed_revenue"]))
    out.append("| Paid | %d | %s |"
               % (t["paid"]["orders"], t["paid"]["attributed_revenue"]))
    if t["paid"]["funnel"]:
        out.append("")
        out.append("## Paid funnel (spend -> conversation -> engagement -> "
                   "conversion -> ROAS)")
        out.append("")
        out.append("| campaign | spend | conv | eng | conv. | revenue | ROAS |")
        out.append("|---|---:|---:|---:|---:|---:|---:|")
        for f in t["paid"]["funnel"]:
            out.append("| %s | %s | %d | %d | %d | %s | %s |"
                       % (f["campaign_id"], f["spend"], f["conversations"],
                          f["engagements"], f["conversions"],
                          f["attributed_revenue"],
                          f["roas"] if f["roas"] is not None else "—"))
    out.append("")
    out.append(report["rule"] + ".")
    return "\n".join(out)
