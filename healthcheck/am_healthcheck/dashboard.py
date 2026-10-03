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
    if schema == "agentmeasure.commercial/verified-ledger":
        t1 = doc["tier1"]
        lane = doc.get("outcome_lane")
        cc = doc.get("billing_crosscheck")
        rec = doc.get("recovery")
        title = "Verified Ledger — %s" % doc["vendor"]["name"]
        sub = "%s · buyer %s · generated %s · rules registry v%s" % (
            doc.get("period", {}).get("start") or "—",
            doc.get("buyer_label"), doc.get("generated_at"),
            doc.get("vendor", {}).get("rules_version", "?"))
    elif schema == "agentmeasure.commercial/dispute-pack":
        t1 = doc["tier1"]
        lane = doc.get("outcome_lane")
        cc = None
        rec = None
        title = "Dispute Pack — %s" % doc["vendor"]["name"]
        sub = "buyer %s · generated %s" % (doc.get("buyer_label"),
                                           doc.get("generated_at"))
    else:
        raise ValueError("not a verified ledger or dispute pack: %r" % schema)

    currency = doc.get("currency") or ""
    out = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>%s</title><style>%s</style></head><body>" % (_e(title), _CSS),
        "<header><h1>%s</h1><div class='sub'>%s</div></header>" % (_e(title), _e(sub)),
        "<main>",
    ]
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

    out.append("</main>")
    out.append("<footer>Rendered locally from %s · no data left this machine · "
               "AgentMeasure dashboard</footer>" % _e(schema))
    out.append("</body></html>")
    return "\n".join(out)


def load_document(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
