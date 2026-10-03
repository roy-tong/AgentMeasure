"""Local dashboard — one static HTML page for a whole verification story.

Reads a verified-ledger.json (preferred) or a dispute-pack.json and renders
the lanes side by side: the PASS/FAIL/UNPROVABLE cards, the claim, the
outcome-standard lane, the billing-ledger cross-check, and realized recovery.
Same discipline as every report in this package: self-contained, no external
assets, no JavaScript, printable, every value html-escaped, works offline on
the buyer's machine because nothing is uploaded anywhere.

The dashboard renders; it never recomputes. If a number is not in the input
document it does not appear.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Optional


def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


_CSS = """
body{font-family:-apple-system,'Segoe UI',sans-serif;margin:0;background:#f6f7f9;color:#1a2233}
header{background:#101828;color:#fff;padding:18px 28px}
header h1{margin:0;font-size:19px}header .sub{color:#9aa7bd;font-size:12px;margin-top:5px}
main{max-width:980px;margin:22px auto;padding:0 16px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px}
.card{background:#fff;border:1px solid #e3e8ef;border-radius:9px;padding:14px 18px;min-width:128px}
.card .n{font-size:26px;font-weight:700}
.card .l{font-size:11px;color:#667085;text-transform:uppercase;letter-spacing:.4px;margin-top:3px}
.pass .n{color:#067647}.fail .n{color:#b42318}.unpr .n{color:#7a3e0d}
section{background:#fff;border:1px solid #e3e8ef;border-radius:9px;padding:16px 20px;margin-bottom:16px}
section h2{font-size:14px;margin:0 0 10px;color:#101828}
section .tag{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;padding:2px 7px;border-radius:9px;vertical-align:2px;margin-left:8px}
.tag.claim{background:#e0f2fe;color:#075985}.tag.leverage{background:#fef0c7;color:#7a3e0d}.tag.realized{background:#dcfae6;color:#067647}
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#667085;text-align:left;border-bottom:1px solid #e3e8ef;padding:6px 8px}
td{padding:6px 8px;border-bottom:1px solid #f0f2f5}td.num,th.num{text-align:right}
.bar{background:#eef2f6;border-radius:6px;height:14px;overflow:hidden;margin-top:8px}
.bar>span{display:block;height:100%;background:#12b76a}
.note{font-size:12px;color:#667085;margin-top:8px}
footer{max-width:980px;margin:0 auto 30px;padding:0 16px;font-size:11px;color:#98a2b3}
code{background:#f2f4f7;padding:1px 4px;border-radius:4px;font-size:11px}
"""


def _cards(t1: Dict[str, Any], currency: str) -> str:
    t = t1.get("three_state_counts", {})
    out = ['<div class="cards">']
    out.append('<div class="card pass"><div class="n">%s</div><div class="l">PASS</div></div>'
               % _e(t.get("PASS", 0)))
    out.append('<div class="card fail"><div class="n">%s</div><div class="l">FAIL</div></div>'
               % _e(t.get("FAIL", 0)))
    out.append('<div class="card unpr"><div class="n">%s</div><div class="l">Unprovable</div></div>'
               % _e(t.get("UNPROVABLE", 0)))
    c = t1.get("counts", {})
    out.append('<div class="card"><div class="n">%s</div><div class="l">Billed, not billable</div></div>'
               % _e(c.get("billed_but_not_billable", 0)))
    out.append('<div class="card"><div class="n">%s</div><div class="l">Cannot settle</div></div>'
               % _e(c.get("cannot_settle", 0)))
    if "variance" in t1:
        out.append('<div class="card fail"><div class="n">%s %s</div><div class="l">Net variance</div></div>'
                   % (_e(currency), _e(t1["variance"])))
    out.append("</div>")
    return "\n".join(out)


def _table(headers, rows, numeric_cols=()) -> str:
    out = ["<table>", "<tr>"]
    for i, h in enumerate(headers):
        cls = ' class="num"' if i in numeric_cols else ""
        out.append("<th%s>%s</th>" % (cls, _e(h)))
    out.append("</tr>")
    for row in rows:
        out.append("<tr>")
        for i, cell in enumerate(row):
            cls = ' class="num"' if i in numeric_cols else ""
            out.append("<td%s>%s</td>" % (cls, _e(cell)))
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def _section(title: str, tag: Optional[str], body: str,
             note: Optional[str] = None) -> str:
    tag_html = ' <span class="tag %s">%s</span>' % (tag, tag) if tag else ""
    out = ["<section><h2>%s%s</h2>" % (_e(title), tag_html), body]
    if note:
        out.append('<div class="note">%s</div>' % _e(note))
    out.append("</section>")
    return "\n".join(out)


def _three_state(t1: Dict[str, Any]) -> Dict[str, int]:
    """Three-state counts, computed from counts when absent.

    Packs produced before the three-state vocabulary existed carry only the
    directional counts; the dashboard renders those too instead of failing.
    """
    counts = t1.get("three_state_counts")
    if counts:
        return counts
    c = t1.get("counts", {})
    return {
        "PASS": c.get("agrees", 0),
        "FAIL": (c.get("billed_but_not_billable", 0)
                 + c.get("billable_but_not_billed", 0)),
        "UNPROVABLE": c.get("cannot_settle", 0),
    }


def render_dashboard(doc: Dict[str, Any]) -> str:
    schema = doc.get("schema", "")
    if schema in ("agentmeasure.commercial/verified-ledger",
                  "agentmeasure.commercial/dispute-pack"):
        title, sub, body = _billing_body(doc)
    elif schema == "agentmeasure.commerce/measurement-receipt":
        title, sub, body = _receipt_body(doc)
    elif schema == "agentmeasure.commerce/contribution-margin":
        title, sub, body = _cm_body(doc)
    elif schema == "agentmeasure.commerce/demand-audit":
        title, sub, body = _audit_body(doc)
    elif schema == "agentmeasure.commerce/decision-audit":
        title, sub, body = _decision_body(doc)
    else:
        raise ValueError("not a supported dashboard document: %r" % schema)

    out = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>%s</title><style>%s</style></head><body>" % (_e(title), _CSS),
        "<header><h1>%s</h1><div class='sub'>%s</div></header>" % (_e(title), _e(sub)),
        "<main>",
    ]
    out += body
    out.append("</main>")
    out.append("<footer>Rendered locally from %s · no data left this machine · "
               "AgentMeasure dashboard</footer>" % _e(schema))
    out.append("</body></html>")
    return "\n".join(out)


def _billing_body(doc: Dict[str, Any]):
    if doc["schema"] == "agentmeasure.commercial/verified-ledger":
        t1 = doc["tier1"]
        lane = doc.get("outcome_lane")
        cc = doc.get("billing_crosscheck")
        rec = doc.get("recovery")
        title = "Verified Ledger — %s" % doc["vendor"]["name"]
        sub = "%s · buyer %s · generated %s · rules registry v%s" % (
            doc.get("period", {}).get("start") or "—",
            doc.get("buyer_label"), doc.get("generated_at"),
            doc.get("vendor", {}).get("rules_version", "?"))
    else:
        t1 = doc["tier1"]
        lane = doc.get("outcome_lane")
        cc = None
        rec = None
        title = "Dispute Pack — %s" % doc["vendor"]["name"]
        sub = "buyer %s · generated %s" % (doc.get("buyer_label"),
                                           doc.get("generated_at"))

    currency = doc.get("currency") or ""
    out = []
    out.append(_cards(t1, currency))

    t = _three_state(t1)
    out.append(_section(
        "Line judgements — vendor's own published rules", "claim",
        _table(["PASS", "FAIL", "UNPROVABLE", "net"],
               [[t["PASS"], t["FAIL"], t["UNPROVABLE"], "%+d" % t1["net_findings"]]],
               numeric_cols={0, 1, 2, 3}),
        doc["vendor"].get("rule_source")))

    disputed = [v for v in t1.get("verdicts", [])
                if v["verdict"] != "cannot_settle" and v["verdict"] != "agrees"]
    if disputed:
        out.append(_section(
            "Disputed lines", "claim",
            _table(["conversation", "export line", "finding", "3-state"],
                   [[v["conversation_id"], v["line"], v["verdict"],
                     v.get("verdict_3state", "")] for v in disputed],
                   numeric_cols={1})))

    unsettled = [v for v in t1.get("verdicts", []) if v["verdict"] == "cannot_settle"]
    if unsettled:
        out.append(_section(
            "Cannot settle — removed from the claim, not zeroed", None,
            _table(["conversation", "export line"],
                   [[v["conversation_id"], v["line"]] for v in unsettled],
                   numeric_cols={1})))

    if lane:
        lc = lane["counts"]
        body = _table(
            ["fails our standard", "meets", "unprovable", "not reviewed"],
            [[lc["fails_buyer_standard"], lc["meets_buyer_standard"],
              lc["unprovable"], lc["not_reviewed"]]],
            numeric_cols={0, 1, 2, 3})
        if "at_risk_amount" in lane:
            body += ('<div class="note">At risk under our standard: %s %s '
                     "(informational only).</div>"
                     % (_e(currency), _e(lane["at_risk_amount"])))
        out.append(_section(
            "Outcome-standard lane — %s" % lane["label"], "leverage", body,
            "Renewal leverage only. Never netted into the claim."))

    failing = [l for l in (lane or {}).get("lines", [])
               if l["outcome_verdict"] == "fails_buyer_standard"]
    if failing:
        out.append(_section(
            "Outcome standard — failing lines", "leverage",
            _table(["conversation", "line", "reason"],
                   [[l["conversation_id"], l["line"], "; ".join(l["reasons"])]
                    for l in failing], numeric_cols={1})))

    if cc:
        body = _table(
            ["disagreement", "count"],
            [["export billed, ledger has no line", len(cc["flag_without_charge"])],
             ["ledger charged, export says not billed",
              len(cc["charge_without_export_flag"])],
             ["charged per ledger, absent from export", len(cc["not_in_export"])],
             ["amount deviates from published price", len(cc["amount_deviation"])]],
            numeric_cols={1})
        out.append(_section(
            "Billing-ledger cross-check", "claim", body,
            "Named disagreements, not resolved ones — each needs a human."))

    if rec:
        rt = rec["totals"]
        claimed = rt["claimed"] or 0
        realized = rt["realized"] or 0
        pct = (100.0 * realized / claimed) if claimed else 0
        body = (_table(["claimed", "realized", "outstanding"],
                       [[rt["claimed"], rt["realized"], rt["outstanding"]]],
                       numeric_cols={0, 1, 2})
                + '<div class="bar"><span style="width:%.1f%%"></span></div>'
                % max(0.0, min(100.0, pct)))
        out.append(_section(
            "Recovery — realized, counted separately", "realized", body,
            "Only credited/paid cash counts. Renewal savings are never added."))

    return title, sub, out


def _receipt_body(doc: Dict[str, Any]):
    """Measurement receipt (F2.5/F2.9): the agent-commerce story on one page."""
    g = doc.get("governance", {})
    title = "Measurement receipt — agent commerce (M1A merchant-side)"
    sub = "mode %s · policy v%s · metric definitions frozen under it" % (
        g.get("observation_mode") or "—",
        g.get("measurement_policy_version") or "—")
    out = []
    metrics = {m["metric"]: m for m in doc.get("metrics", [])}
    net = metrics.get("net_gmv_strong", {})
    orders = metrics.get("observed_verified_orders", {})
    inv = metrics.get("observed_invocations", {})
    attempts = sum((doc.get("attempts_by_operation") or {}).values())
    out.append('<div class="cards">'
               '<div class="card"><div class="n">%s</div><div class="l">Operations</div></div>'
               '<div class="card"><div class="n">%s</div><div class="l">Attempts</div></div>'
               '<div class="card pass"><div class="n">%s</div><div class="l">Verified orders</div></div>'
               '<div class="card fail"><div class="n">%s %s</div><div class="l">Net GMV (strong)</div></div>'
               '</div>'
               % (_e(inv.get("value", 0)), _e(attempts),
                  _e(orders.get("value", 0)), _e(doc.get("currency", "")),
                  _e(net.get("value", 0))))

    out.append(_section(
        "Metrics — value with its evidence, never above it", "claim",
        _table(["metric", "value", "evidence"],
               [[m["metric"], "—" if m["value"] is None else m["value"],
                 m["evidence"]] for m in doc.get("metrics", [])],
               numeric_cols={1}),
        doc.get("claim_rule")))

    if doc.get("duplicate_rows") or doc.get("double_charges"):
        rows = [[d["order_id"], d["line"], d.get("reason", "")]
                for d in doc.get("duplicate_rows", [])]
        rows += [[d["order_id"], d.get("charges"), d.get("reason", "")]
                 for d in doc.get("double_charges", [])]
        out.append(_section(
            "Collapsed rows and double charges (named, not summed)", "claim",
            _table(["order", "line/charges", "reason"], rows, numeric_cols={1})))

    m = doc.get("materiality", {})
    if m:
        pct = (m.get("discrepancy_pct") or 0) * 100
        body = _table(["naive net", "verified net", "discrepancy", "% of naive"],
                      [[m.get("naive_net"), m.get("verified_net"),
                        m.get("discrepancy"), "%.2f%%" % pct]],
                      numeric_cols={0, 1, 2, 3})
        rows = [[c["category"], c["amount"], c["rows"]]
                for c in m.get("categories", [])]
        if rows:
            body += _section("Discrepancy categories", None,
                             _table(["category", "amount", "rows"], rows,
                                    numeric_cols={1, 2}))
        out.append(_section(
            "Materiality — naive dashboard vs verified ledger", "claim", body,
            m.get("reading")))

    if doc.get("input_digests"):
        rows = [[name, digest[:16] + "…"]
                for name, digest in sorted(doc["input_digests"].items())]
        out.append(_section("Evidence anchors (immutable inputs)", "realized",
                            _table(["input", "sha256"], rows)))
    return title, sub, out


def _cm_body(doc: Dict[str, Any]):
    """Contribution Margin ledger (F2.11): the monthly operating page."""
    title = "Contribution Margin — %s" % doc.get("period", "")
    sub = doc.get("formula", "")
    out = []
    cm = doc.get("contribution_margin", 0)
    pct = doc.get("contribution_margin_pct")
    out.append('<div class="cards">'
               '<div class="card"><div class="n">%s</div><div class="l">Attributed revenue (organic %s / paid %s)</div></div>'
               '<div class="card fail"><div class="n">%s</div><div class="l">Total deductions</div></div>'
               '<div class="card pass"><div class="n">%s%s</div><div class="l">Contribution Margin</div></div>'
               '</div>'
               % (_e(doc.get("attributed_revenue")),
                  _e(doc.get("trees", {}).get("organic")),
                  _e(doc.get("trees", {}).get("paid")),
                  _e(doc.get("total_deductions")), _e(cm),
                  (" (%.1f%%)" % (pct * 100)) if pct is not None else ""))

    rows = [["− %s" % cat, b["amount"], b["rows"]]
            for cat, b in doc.get("deductions", {}).items()]
    out.append(_section(
        "Deductions — each with its source row count", "claim",
        _table(["category", "amount", "rows"], rows, numeric_cols={1, 2})))
    return title, sub, out


def _audit_body(doc: Dict[str, Any]):
    """Channel Demand Audit (F2.12): potential vs performance, one verdict."""
    title = "Channel Demand Audit — %s" % doc.get("channel", "")
    sub = "%s" % doc.get("reading", "")
    verdict = doc.get("verdict", "")
    cls = {"Launch": "pass", "Watch": "unpr", "Not ready": "fail"}.get(verdict, "")
    out = ['<div class="cards">'
           '<div class="card %s"><div class="n">%s</div><div class="l">Verdict</div></div>'
           '</div>' % (cls, _e(verdict))]
    rows = []
    for axis_name, axis in doc.get("axes", {}).items():
        for r in axis.get("rows", []):
            rows.append([axis_name, r["metric"],
                         "—" if r["value"] is None else r["value"],
                         r["threshold"],
                         ("yes" if r["meets"] else "NO")
                         if r["meets"] is not None else "not measured"])
    out.append(_section(
        "Thresholds — potential and performance, separate questions", None,
        _table(["axis", "metric", "value", "threshold", "meets"],
               rows, numeric_cols={2, 3}),
        doc.get("rule")))
    return title, sub, out


def _decision_body(doc: Dict[str, Any]):
    """Commercial decision audit (F2.14): every decision with its basis."""
    title = "Commercial decision audit — policy v%s" % doc.get("policy_version", "")
    sub = "risk policy link: %s" % doc.get("risk_policy_ref", "")
    c = doc.get("counts", {})
    out = []
    out.append('<div class="cards">'
               '<div class="card pass"><div class="n">%s</div><div class="l">Complies</div></div>'
               '<div class="card fail"><div class="n">%s</div><div class="l">Violates</div></div>'
               '<div class="card unpr"><div class="n">%s</div><div class="l">Outside policy</div></div>'
               '</div>'
               % (_e(c.get("complies", 0)), _e(c.get("violates", 0)),
                  _e(c.get("outside_policy", 0))))
    problems = [l for l in doc.get("lines", []) if l.get("grade") != "complies"]
    if problems:
        out.append(_section(
            "Findings — each with its policy basis", "claim",
            _table(["execution", "action", "grade", "basis"],
                   [[l["execution_id"], l["action_type"], l["grade"],
                     l["basis"]] for l in problems])))
    out.append(_section(
        "All executions", None,
        _table(["execution", "action", "grade", "basis"],
               [[l.get("execution_id"), l.get("action_type"), l.get("grade"),
                 l.get("basis")] for l in doc.get("lines", [])])))
    return title, sub, out


def load_document(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
