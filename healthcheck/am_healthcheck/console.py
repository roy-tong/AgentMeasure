"""The AgentMeasure console — the app shell users already know how to use.

Redesigned under Operate-mode discipline (impeccable): a verification tool
is an app, not a scrolled report. The familiar logic users bring with them —
**sidebar navigation, a content pane, an overview that recommends the next
action** — is the interface. The old long-scroll anchor page is treated as
the anti-reference.

Composition is unchanged where it was right:

- the page composes real verification documents (verified ledger, commerce
  receipt, contribution margin, channel audit, decision audit) and renders,
  never recomputes;
- user-language discipline is test-enforced: a banned-marker list is checked
  against the final page and the build refuses to ship draft language;
- single offline file, no network, every value escaped, works offline and
  in print.

What changed with the redesign:

- **App shell**: dark sidebar (second neutral layer) with grouped nav and
  drawn SVG icons; a top bar carrying the view title and the review meta;
  a content pane at reading density. Hash routing (#/view) so deep links,
  back, and refresh behave as users expect.
- **Overview as a workbench**: the first view states what was reviewed and
  lists the recommended next actions with their counts — the app tells the
  user where to go instead of hoping they scroll in order.
- **Views, not steps**: every section is a destination that can be
  revisited; the workflow lives in the sidebar order and the overview
  actions, not in numbered kickers.
- **Full component states**: hover, focus-visible, active nav, table row
  hover, badges with a standardised semantic palette, structural responsive
  behaviour (sidebar collapses to a top strip on narrow screens), and a
  print mode that flattens every view into the report.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

View = Dict[str, Any]
# {id, label, icon, title, description, body_html, note}


def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


# Visible copy must never contain draft/developer markers (test-enforced).
BANNED_MARKERS = (
    "agentmeasure.commerce/", "agentmeasure.commercial/", "schema_version",
    "observation_mode", "candidate_set", "measurement_policy_version",
    "F2.1", "F2.2", "F2.3", "F2.4", "F2.5", "F2.6", "F2.7", "F2.8", "F2.9",
    "F2.10", "risk_policy_ref", "Tier 1", "Tier 2", "tier1", "tier2",
    "outcome_lane", "billing_crosscheck",
)

_ICONS = {
    "overview": '<rect x="2.5" y="2.5" width="4.5" height="4.5" rx="1"/>'
                '<rect x="9" y="2.5" width="4.5" height="4.5" rx="1"/>'
                '<rect x="2.5" y="9" width="4.5" height="4.5" rx="1"/>'
                '<rect x="9" y="9" width="4.5" height="4.5" rx="1"/>',
    "data": '<path d="M4 2.5h5.5L13 6v7.5H4z"/><path d="M9.5 2.5V6H13"/>',
    "recount": ('<path d="M2.5 8a5.5 5.5 0 0 1 9.6-3.6L13.5 6"/>'
                '<path d="M13.5 2.5V6H10"/>'
                '<path d="M13.5 8a5.5 5.5 0 0 1-9.6 3.6L2.5 10"/>'
                '<path d="M2.5 13.5V10H6"/>'),
    "standard": '<path d="M8 2l4.5 2v3.5c0 3-1.9 5.1-4.5 6-2.6-.9-4.5-3-4.5-6V4z"/>',
    "money": ('<circle cx="8" cy="8" r="5.5"/>'
              '<path d="M8 4.8v6.4M6.2 6.4h2.7a1.4 1.4 0 1 1 0 2.8H7.1a1.4 1.4'
              ' 0 1 0 0 2.8h2.7"/>'),
    "pack": '<rect x="2.5" y="4" width="11" height="8.5" rx="1.2"/><path d="M2.5 5.5L8 9l5.5-3.5"/>',
    "recovery": '<path d="M2.5 6.5h7a3.5 3.5 0 1 1 0 7H6"/><path d="M5 3.5L2 6.5l3 3"/>',
    "receipt": ('<path d="M3 13.5V6h2.6v7.5M6.8 13.5V3h2.6v10.5M10.6 13.5V8h2.6v5.5"/>'
                '<path d="M2 13.5h12"/>'),
    "margin": '<rect x="2.5" y="4" width="11" height="8.5" rx="1.4"/><path d="M2.5 6.8h11"/>',
    "readiness": ('<circle cx="8" cy="8" r="5.5"/><circle cx="8" cy="8" r="1.6"/>'
                  '<path d="M8 2.5v2M8 11.5v2M2.5 8h2M11.5 8h2"/>'),
    "guardrails": ('<path d="M8 2l4.5 2v3.5c0 3-1.9 5.1-4.5 6-2.6-.9-4.5-3-4.5-6V4z"/>'
                   '<path d="M6 8l1.5 1.5L10.5 6.5"/>'),
}


def _icon(name: str) -> str:
    return ('<svg class="ic" viewBox="0 0 16 16" width="15" height="15" '
            'fill="none" stroke="currentColor" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true">%s</svg>' % _ICONS.get(name, _ICONS["data"]))


_CSS = """
:root{--canvas:#f3f5f9;--surface:#ffffff;--side:#111827;--side2:#1b2434;
--side-ink:#c3ccdb;--side-dim:#8b96ab;--ink:#181f2c;--soft:#5c6575;
--line:#e4e8ef;--line2:#eef1f5;--accent:#3050c8;--accent-soft:#e9edfb;
--ok:#0c7a48;--ok-bg:#e5f4ec;--bad:#b3261e;--bad-bg:#fbeae9;
--warn:#8a5a0d;--warn-bg:#fbf1de}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--canvas);color:var(--ink);
font:14px/1.6 -apple-system,'Segoe UI','PingFang SC',sans-serif}
.app{display:flex;min-height:100vh}

/* sidebar */
.side{width:236px;flex:0 0 236px;background:var(--side);color:var(--side-ink);
padding:18px 12px;display:flex;flex-direction:column;gap:2px;position:sticky;
top:0;height:100vh;overflow:auto}
.side .mark{color:#fff;font-size:15.5px;font-weight:700;letter-spacing:-.2px;
padding:2px 10px 14px}
.side .grp{font-size:10.5px;font-weight:600;letter-spacing:1px;text-transform:
uppercase;color:var(--side-dim);padding:14px 10px 5px}
.nav-item{display:flex;align-items:center;gap:9px;padding:7px 10px;border-radius:8px;
color:var(--side-ink);text-decoration:none;font-size:13.5px}
.nav-item .ic{flex:0 0 15px;opacity:.75}
.nav-item:hover{background:var(--side2);color:#fff}
.nav-item:focus-visible{outline:2px solid #7d95f0;outline-offset:1px}
.nav-item.active{background:var(--accent);color:#fff}
.nav-item.active .ic{opacity:1}
.side .foot{margin-top:auto;padding:12px 10px 2px;font-size:11px;color:var(--side-dim)}

/* frame */
.frame{flex:1;min-width:0;display:flex;flex-direction:column}
.bar{background:var(--surface);border-bottom:1px solid var(--line);
padding:14px 30px;display:flex;align-items:center;justify-content:space-between;
gap:16px;position:sticky;top:0;z-index:4}
.bar h1{font-size:18px;margin:0;letter-spacing:-.2px}
.bar .sub{font-size:12px;color:var(--soft);margin-top:1px}
.chip{font-size:11.5px;color:var(--soft);border:1px solid var(--line);
border-radius:14px;padding:3px 11px;white-space:nowrap}
main{padding:24px 30px 56px;max-width:920px;width:100%}

/* views */
.view[hidden]{display:none}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;
padding:18px 22px;margin-bottom:16px}
.card h3{font-size:13px;margin:0 0 10px;color:var(--soft);font-weight:600}
.card .note{font-size:12.5px;color:var(--soft);margin-top:12px}
.stats{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:12px;
padding:14px 18px;flex:1;min-width:150px}
.stat .n{font-size:23px;font-weight:700;letter-spacing:-.3px;
font-variant-numeric:tabular-nums}
.stat .l{font-size:11.5px;color:var(--soft);margin-top:3px}
.ok .n{color:var(--ok)}.bad .n{color:var(--bad)}.warn .n{color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:4px 0 2px}
th{font-size:11px;letter-spacing:.4px;text-transform:uppercase;color:var(--soft);
text-align:left;border-bottom:1px solid var(--line);padding:7px 10px;font-weight:600}
td{padding:8px 10px;border-bottom:1px solid var(--line2);vertical-align:top}
tbody tr:hover td{background:#f8fafc}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;font-size:11px;font-weight:600;letter-spacing:.3px;
padding:2px 9px;border-radius:11px}
.b-ok{background:var(--ok-bg);color:var(--ok)}
.b-bad{background:var(--bad-bg);color:var(--bad)}
.b-warn{background:var(--warn-bg);color:var(--warn)}
.bar-track{background:#e9edf3;border-radius:7px;height:14px;overflow:hidden;margin:10px 0 4px}
.bar-track>span{display:block;height:100%;background:var(--ok)}
ul.actions{list-style:none;margin:0;padding:0}
ul.actions li{display:flex;align-items:center;gap:12px;padding:12px 6px;
border-bottom:1px solid var(--line2)}
ul.actions li:last-child{border-bottom:0}
ul.actions .ic{color:var(--accent);flex:0 0 15px}
ul.actions .what{font-size:13.5px}
ul.actions a{text-decoration:none;color:inherit}
ul.actions a:hover .what{color:var(--accent)}
ul.actions .go{margin-left:auto;font-size:12.5px;color:var(--accent);
text-decoration:none;font-weight:600;white-space:nowrap}
ul.actions .go:hover{text-decoration:underline}
footer{padding:0 30px 34px;font-size:11.5px;color:#98a2b3;max-width:920px}

/* responsive: the sidebar becomes a top strip */
@media (max-width:860px){
 .app{flex-direction:column}
 .side{position:static;width:auto;height:auto;flex:none;flex-direction:row;
 flex-wrap:wrap;align-items:center;padding:10px 14px}
 .side .mark{padding:0 10px 0 2px}
 .side .grp,.side .foot{display:none}
 .nav-item{width:auto;padding:6px 11px}
 main,.bar,footer{padding-left:18px;padding-right:18px}
}
@media print{
 .side,.chip{display:none}
 .app{display:block}.bar{position:static;border:0}
 .view[hidden]{display:block;page-break-before:always}
 body{background:#fff}
 main{max-width:none}
}
"""

_JS = """
(function () {
  "use strict";
  var views = Array.prototype.slice.call(document.querySelectorAll(".view"));
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav-item"));
  function show(id) {
    var target = document.getElementById("view-" + id);
    if (!target) { id = "overview"; target = document.getElementById("view-overview"); }
    views.forEach(function (v) { v.hidden = v !== target; });
    links.forEach(function (a) {
      var active = a.getAttribute("data-view") === id;
      a.classList.toggle("active", active);
      if (active) { a.setAttribute("aria-current", "page"); }
      else { a.removeAttribute("aria-current"); }
    });
    var head = target.querySelector("[data-head]");
    document.getElementById("view-title").textContent =
      head ? head.getAttribute("data-head") : "";
    document.getElementById("view-sub").textContent =
      head ? (head.getAttribute("data-sub") || "") : "";
    window.scrollTo(0, 0);
  }
  function route() {
    var id = decodeURIComponent((location.hash || "#/overview")
      .replace(/^#\\/?/, ""));
    show(id);
  }
  window.addEventListener("hashchange", route);
  route();
})();
"""


def _icon(name: str) -> str:
    return ('<svg class="ic" viewBox="0 0 16 16" width="15" height="15" '
            'fill="none" stroke="currentColor" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true">%s</svg>' % _ICONS.get(name, _ICONS["data"]))


def _stat(cls: str, value: Any, label: str) -> str:
    return ('<div class="stat %s"><div class="n">%s</div>'
            '<div class="l">%s</div></div>' % (cls, _e(value), _e(label)))


def _stats(items: List[Tuple[str, Any, str]]) -> str:
    return '<div class="stats">%s</div>' % "".join(_stat(*i) for i in items)


def _table(headers: List[str], rows: List[List[Any]],
           numeric: Optional[List[int]] = None) -> str:
    numeric = numeric or []
    out = ["<table><thead><tr>"]
    for i, h in enumerate(headers):
        out.append("<th%s>%s</th>" % (' class="num"' if i in numeric else "",
                                      _e(h)))
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for i, cell in enumerate(row):
            out.append("<td%s>%s</td>" % (' class="num"' if i in numeric
                                          else "", _e(cell)))
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _badge(kind: str, text: str) -> str:
    return '<span class="badge b-%s">%s</span>' % (kind, _e(text))


def _card(title: Optional[str], body: str, note: Optional[str] = None) -> str:
    return ("<div class=\"card\">%s%s%s</div>"
            % ('<h3>%s</h3>' % _e(title) if title else "", body,
               '<div class="note">%s</div>' % _e(note) if note else ""))


def _view(view_id: str, title: str, sub: str, body: str) -> str:
    return ('\n<section class="view" id="view-%s" hidden data-head="%s" '
            'data-sub="%s">%s</section>'
            % (_e(view_id), _e(title), _e(sub), body))


# ---------------------------------------------------------------------------
# Billing views (from a verified ledger document)
# ---------------------------------------------------------------------------
def _billing_views(ledger: Dict[str, Any]) -> List[View]:
    views: List[View] = []
    t1 = ledger.get("tier1", {})
    vendor = (ledger.get("vendor") or {}).get("name", "your vendor")
    c = t1.get("counts", {})
    over = c.get("billed_but_not_billable", 0)
    under = c.get("billable_but_not_billed", 0)
    cannot = c.get("cannot_settle", 0)
    agreed = c.get("agrees", 0)
    currency = ledger.get("currency") or ""
    inputs = ledger.get("inputs", {})
    missing = inputs.get("columns_missing") or []

    views.append({
        "id": "data", "label": "Data reviewed", "icon": "data",
        "title": "Data reviewed", "group": "billing",
        "description": "Everything was computed from the export you "
                       "provided — nothing was uploaded, and no customer "
                       "conversations were read.",
        "body": _stats([
            ("", t1.get("total_conversations", 0), "Rows reviewed"),
            ("", t1.get("billed_by_vendor", 0), "Rows charged"),
        ])
        + _card("What we worked from", _table(["Source", "Detail"], [
            ["Export file", inputs.get("export_file", "—")],
            ["Vendor rulebook applied",
             (ledger.get("vendor") or {}).get("rule_source", "—")],
            ["Fingerprint", (inputs.get("export_sha256", "") or "—")[:16]
             + "…"],
        ])),
        "note": ("Some fields were missing (%s). Rows without them are "
                 "counted under cannot decide — never guessed."
                 % ", ".join(missing)) if missing else
                ("Every input is fingerprinted when the review runs, so "
                 "these numbers can always be tied back to the exact data."),
    })

    body = _stats([
        ("bad", over, "Charged, but their own rules say no"),
        ("ok", under, "Not charged, though their rules allow it"),
        ("warn", cannot, "Cannot decide — not guessed"),
        ("", agreed, "Charged correctly"),
    ])
    if t1.get("variance") is not None:
        body += _card("The amounts", _table(
            ["", "Amount (%s)" % currency], [
                ["Overcharged, by their own rulebook",
                 "%.2f" % t1.get("overcharge_amount", 0)],
                ["Undercharged — reported too, in their favour",
                 "%.2f" % t1.get("undercharge_amount", 0)],
                ["Net difference to raise with %s" % vendor,
                 "%.2f" % t1["variance"]],
            ], numeric=[1]))
    views.append({
        "id": "recount", "label": "The recount", "icon": "recount",
        "title": "The recount", "group": "billing",
        "description": "Every conversation re-counted using %s's own "
                       "published billing rules — not ours. A finding only "
                       "counts when their rulebook says so; that is what "
                       "makes it hard to argue with." % vendor,
        "body": body,
        "note": "Charges that cannot be decided are left out of the amounts "
                "and listed separately. A statement that guesses is not a "
                "statement.",
    })

    lane = ledger.get("outcome_lane")
    if lane:
        lc = lane.get("counts", {})
        views.append({
            "id": "standard", "label": "Service standard", "icon": "standard",
            "title": "Your own service standard", "group": "billing",
            "description": "Separately from money: conversations the vendor "
                           "counted as resolved that do not meet the "
                           "standard written in YOUR contract — for example, "
                           "a customer back within 72 hours of closing.",
            "body": _stats([
                ("bad", lc.get("fails_buyer_standard", 0),
                 "Miss your standard"),
                ("ok", lc.get("meets_buyer_standard", 0),
                 "Meet your standard"),
                ("warn", lc.get("unprovable", 0),
                 "Cannot judge from this data"),
            ]),
            "note": "Use this in renewal and vendor-review conversations — "
                    "leverage about quality, never a refund claim. It is "
                    "never mixed into the money amounts.",
        })

    cc = ledger.get("billing_crosscheck")
    if cc:
        views.append({
            "id": "money", "label": "Money cross-check", "icon": "money",
            "title": "Does the money match?", "group": "billing",
            "description": "Your helpdesk report and your billing system "
                           "are two different witnesses. This puts them side "
                           "by side and lists every disagreement — it "
                           "deliberately does not decide who is right.",
            "body": _card("Disagreements, by kind", _table(
                ["Disagreement", "Count"], [
                    ["Report says charged; billing system has no record",
                     len(cc.get("flag_without_charge", []))],
                    ["Billing system charged; report says it didn't",
                     len(cc.get("charge_without_export_flag", []))],
                    ["Charged, but absent from the report entirely",
                     len(cc.get("not_in_export", []))],
                    ["Charged at a different price than published",
                     len(cc.get("amount_deviation", []))],
                ], numeric=[1])),
            "note": "Walk these with finance before raising anything with "
                    "%s. The review names each one; it never quietly "
                    "resolves it." % vendor,
        })

    views.append({
        "id": "pack", "label": "Evidence pack", "icon": "pack",
        "title": "The evidence pack", "group": "billing",
        "description": "Everything above, packaged to send to %s: a short "
                       "letter quoting their own rulebook for every finding, "
                       "the conversation list, and the amounts — including "
                       "what they got right." % vendor,
        "body": _stats([
            ("", t1.get("net_findings", 0), "Net findings in the pack"),
            ("", cannot, "Rows excluded rather than guessed"),
        ]),
        "note": "Generate the pack from the same data with one command. The "
                "refund is the vendor's decision; the evidence is yours. A "
                "statement that only ever finds against them would not be a "
                "statement — undercharges are reported too.",
    })

    rec = ledger.get("recovery")
    if rec:
        rt = rec.get("totals", {})
        claimed = rt.get("claimed") or 0
        realized = rt.get("realized") or 0
        pct = (100.0 * realized / claimed) if claimed else 0
        views.append({
            "id": "recovery", "label": "Recovery", "icon": "recovery",
            "title": "What came back", "group": "billing",
            "description": "A finding is not money. This tracks what %s "
                           "actually confirmed, credited, or repaid — each "
                           "tied back to the original finding with a date "
                           "and a reference." % vendor,
            "body": _card("Recovered so far", _table(
                ["", "Amount (%s)" % currency], [
                    ["Claimed on disputed lines", claimed],
                    ["Actually recovered (credited or paid)", realized],
                    ["Still outstanding", rt.get("outstanding", 0)],
                ], numeric=[1])
                + '<div class="bar-track"><span style="width:%.1f%%">'
                  "</span></div>" % max(0.0, min(100.0, pct))),
            "note": "Recovered cash is tracked separately from any renewal "
                    "savings; the two are never added together.",
        })
    return views


# ---------------------------------------------------------------------------
# Channel views
# ---------------------------------------------------------------------------
def _channel_views(receipt: Optional[Dict[str, Any]],
                   margin: Optional[Dict[str, Any]],
                   channel: Optional[Dict[str, Any]],
                   decisions: Optional[Dict[str, Any]]) -> List[View]:
    views: List[View] = []

    if receipt:
        metrics = {m["metric"]: m for m in receipt.get("metrics", [])}
        net = metrics.get("net_gmv_strong", {})
        mat = receipt.get("materiality") or {}
        note = None
        if mat:
            note = ("Your dashboard reports %s. The verified number is %s — "
                    "a difference of %s, or %.1f%% of what the dashboard "
                    "claims. %s"
                    % (mat.get("naive_net"), mat.get("verified_net"),
                       mat.get("discrepancy"),
                       abs(mat.get("discrepancy_pct") or 0) * 100,
                       mat.get("reading", "")))
        rows = [[m["metric"],
                 "—" if m["value"] is None else m["value"], m["evidence"]]
                for m in receipt.get("metrics", [])]
        views.append({
            "id": "receipt", "label": "Honest count", "icon": "receipt",
            "title": "Your agent channel, honestly counted",
            "group": "channel",
            "description": "One table for the agent-driven business: what "
                           "agents did, what orders actually happened, what "
                           "the money really is after refunds. Every number "
                           "carries its evidence on its face.",
            "body": _stats([
                ("", metrics.get("observed_invocations", {}).get("value", 0),
                 "Agent-led purchases (observed)"),
                ("ok", metrics.get("observed_verified_orders", {})
                 .get("value", 0), "Verified orders"),
                ("bad", net.get("value", 0), "Net revenue after refunds"),
            ])
            + _card("Metrics and the evidence behind them",
                    _table(["Metric", "Value", "Evidence"], rows,
                           numeric=[1])),
            "note": note,
        })

    if margin:
        rows = [[cat.replace("_", " "), b["amount"]]
                for cat, b in (margin.get("deductions") or {}).items()]
        pct = margin.get("contribution_margin_pct")
        views.append({
            "id": "margin", "label": "Month's margin", "icon": "margin",
            "title": "The month's real margin", "group": "channel",
            "description": "Revenue is not profit. The operating view: "
                           "revenue minus coupons, media spend, platform and "
                           "payment costs, service fees, fulfilment "
                           "variances, and refunds.",
            "body": _stats([
                ("", margin.get("attributed_revenue"),
                 "Attributed revenue (organic %s · paid %s)"
                 % (margin.get("trees", {}).get("organic"),
                    margin.get("trees", {}).get("paid"))),
                ("bad", margin.get("total_deductions"), "Deductions"),
                ("ok", margin.get("contribution_margin"),
                 "Contribution margin%s"
                 % (" (%.0f%%)" % (pct * 100) if pct is not None else "")),
            ])
            + _card("Deductions", _table(["Category", "Amount"], rows,
                                         numeric=[1])),
            "note": "Bring this to the monthly review — it is the number "
                    "the business can act on.",
        })

    if channel:
        verdict = channel.get("verdict", "")
        rows = []
        for axis in (channel.get("axes") or {}).values():
            for r in axis.get("rows", []):
                meets = r.get("meets")
                rows.append([r.get("metric"), r.get("value"),
                             r.get("threshold"),
                             _badge("ok" if meets else
                                    ("warn" if meets is None else "bad"),
                                    "yes" if meets else
                                    ("not measured"
                                     if meets is None else "no"))])
        views.append({
            "id": "readiness", "label": "Channel readiness",
            "icon": "readiness", "title": "Is the channel ready?",
            "group": "channel",
            "description": "Two different questions, answered separately: "
                           "does this channel have real volume of its own "
                           "(potential), and are we operating it well "
                           "(performance)? Watch means the channel is real "
                           "and our operating is the gap.",
            "body": _stats([({"Launch": "ok", "Watch": "warn",
                              "Not ready": "bad"}.get(verdict, ""), verdict,
                             "Readiness verdict")])
            + _card("Thresholds", _table(
                ["Metric", "Value", "Bar", "Meets"], rows, numeric=[1, 2])),
            "note": "Launch only on Launch. Invest in operating on Watch. "
                    "Do not spend against a channel that is Not ready.",
        })

    if decisions:
        c = decisions.get("counts", {})
        problems = [l for l in decisions.get("lines", [])
                    if l.get("grade") != "complies"]
        views.append({
            "id": "guardrails", "label": "Offer guardrails",
            "icon": "guardrails", "title": "Offer guardrails",
            "group": "channel",
            "description": "Every commercial action an agent took — "
                           "discounts, offers, price changes — checked "
                           "against the authorisation policy: what an agent "
                           "may do alone, what required a named approval, "
                           "and what is out of bounds entirely.",
            "body": _stats([
                ("ok", c.get("complies", 0), "Within policy"),
                ("bad", c.get("violates", 0), "Violations"),
                ("warn", c.get("outside_policy", 0),
                 "Not covered by any rule yet"),
            ])
            + (_card("Findings", _table(
                ["Execution", "Action", "What happened"],
                [[l.get("execution_id"), l.get("action_type"), l.get("basis")]
                 for l in problems])) if problems else ""),
            "note": "Commercial guardrails and operational risk share one "
                    "policy language, so nothing falls between the two.",
        })
    return views


# ---------------------------------------------------------------------------
# Overview — the workbench
# ---------------------------------------------------------------------------
def _overview_view(meta: Dict[str, Any],
                   ledger: Optional[Dict[str, Any]]) -> View:
    actions: List[Tuple[str, str, str]] = []
    if ledger:
        t1 = ledger.get("tier1", {})
        vendor = (ledger.get("vendor") or {}).get("name", "your vendor")
        over = t1.get("counts", {}).get("billed_but_not_billable", 0)
        cannot = t1.get("counts", {}).get("cannot_settle", 0)
        variance = t1.get("variance")
        if over:
            actions.append((
                "recount", "recount",
                "Review the %d conversation(s) %s charged against its own "
                "rulebook%s"
                % (over, vendor,
                   " — net difference %.2f %s" % (variance,
                                                  ledger.get("currency") or "")
                   if variance is not None else "")))
        actions.append((
            "pack", "pack", "Send the evidence pack to %s's account team"
            % vendor))
        rec = ledger.get("recovery")
        if rec:
            outstanding = (rec.get("totals", {}) or {}).get("outstanding") or 0
            if outstanding:
                actions.append((
                    "recovery", "recovery",
                    "Follow up %s still outstanding on disputed lines"
                    % outstanding))
        if cannot:
            actions.append((
                "data", "data",
                "Decide the %d row(s) that could not be judged — the export "
                "was missing fields" % cannot))

    items = "".join(
        '<li>%s<a href="#/%s"><span class="what">%s</span></a>'
        '<a class="go" href="#/%s">Open →</a></li>'
        % (_icon(icon), _e(vid), _e(text), _e(vid))
        for vid, icon, text in actions)
    body = _card("Recommended next steps",
                 '<ul class="actions">%s</ul>' % items
                 if actions else "<p>No action needed on this review.</p>")
    sub_parts = [meta.get(k) for k in ("vendor", "period", "buyer")
                 if meta.get(k)]
    return {
        "id": "overview", "label": "Overview", "icon": "overview",
        "title": "Overview", "group": None,
        "description": " · ".join(sub_parts),
        "body": body, "note": None,
    }


# ---------------------------------------------------------------------------
# The shell
# ---------------------------------------------------------------------------
def build_console(meta: Dict[str, Any],
                  ledger: Optional[Dict[str, Any]] = None,
                  receipt: Optional[Dict[str, Any]] = None,
                  margin: Optional[Dict[str, Any]] = None,
                  channel_audit: Optional[Dict[str, Any]] = None,
                  decisions: Optional[Dict[str, Any]] = None) -> str:
    """Compose the console app. All documents optional; nav items appear
    only when their document exists."""
    billing = _billing_views(ledger) if ledger else []
    channel = _channel_views(receipt, margin, channel_audit, decisions)
    all_views = ([_overview_view(meta, ledger)] + billing + channel)

    out = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
           "<meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>%s — AgentMeasure</title><style>%s</style></head><body>"
           % (_e(meta.get("title") or "Bill verification"), _CSS)]
    out.append("<div class='app'>")

    out.append("<aside class='side'><div class='mark'>AgentMeasure</div>")
    current_group = None
    for v in all_views:
        if v.get("group") != current_group:
            current_group = v.get("group")
            if current_group:
                out.append("<div class='grp'>%s</div>"
                           % _e("Bill verification"
                                if current_group == "billing"
                                else "Agent channel"))
        out.append("<a class='nav-item' data-view='%s' href='#/%s'>%s"
                   "<span>%s</span></a>"
                   % (_e(v["id"]), _e(v["id"]), _icon(v["icon"]),
                      _e(v["label"])))
    out.append("<div class='foot'>Computed locally.<br>Nothing uploaded, "
               "nothing tracked.</div></aside>")

    out.append("<div class='frame'><header class='bar'>"
               "<div><h1 id='view-title'></h1>"
               "<div class='sub' id='view-sub'></div></div>"
               "<div class='chip'>Offline · no upload</div>"
               "</header><main>")
    for v in all_views:
        body = v["body"]
        if v.get("note"):
            body += ('<div class="card"><div class="note">%s</div></div>'
                     % _e(v["note"]))
        out.append(_view(v["id"], v["title"],
                         v.get("description") or "", body))
    out.append("</main>")
    out.append("<footer>AgentMeasure · verification you can re-run · "
               "generated locally with no analytics, trackers, or network "
               "calls</footer>")
    out.append("</div></div>")
    out.append("<script>%s</script>" % _JS)
    out.append("</body></html>")

    page = "\n".join(out)
    for marker in BANNED_MARKERS:
        if marker in page:
            raise ValueError("console copy contains a draft marker: %r"
                             % marker)
    return page


def write_console(page: str, out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page + "\n")
    return out_path
