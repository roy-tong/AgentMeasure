"""The AgentMeasure console — one integrated page, written for the user.

The dashboards are analyst artifacts: every lane, every rule basis, every
internal label. This module is the layer a normal user actually opens. It
composes real verification documents (verified ledger, commerce receipt,
contribution margin, channel audit, decision audit) into ONE offline page
with a business flow:

  Billing:       your data -> the recount -> your own standard ->
                 does the money match -> the evidence pack -> what came back
  Agent channel: the honest count -> the month's margin -> channel
                 readiness -> offer guardrails

Three rules distinguish this from the dashboards:

1. **User language, final copy.** No "Tier 1", no schema names, no internal
   requirement ids, no developer notes. Every step answers what a normal
   person asks: what is this step, what happens here, how do I read the
   result. A banned-marker list is asserted by tests, so draft language
   cannot creep back in.
2. **The flow is the logic.** Steps are numbered and connected (each ends
   with a "Continue" link); a step renders only when its document exists,
   and the header always states what was reviewed.
3. **Renders, never recomputes.** Every number comes from a verification
   document produced by the engines. Same offline discipline as every page
   in this package: single file, no network, every value escaped.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

Section = Tuple[str, str, str, str, str, Optional[str]]
# (anchor, title, explain, action, body_html, note)


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

_CSS = """
:root{--ink:#141a26;--soft:#5b6472;--line:#e3e8ef;--panel:#f6f7f9;
--brand:#3b5bdb;--ok:#0e7a4d;--bad:#b42318;--warn:#8a5a0d}
*{box-sizing:border-box}
body{margin:0;background:var(--panel);color:var(--ink);
font:15px/1.65 -apple-system,'Segoe UI','PingFang SC',sans-serif}
header.top{background:#101828;color:#fff;padding:14px 28px;position:sticky;
top:0;z-index:5}
header.top .mark{font-size:17px;font-weight:700;letter-spacing:-.2px}
header.top .meta{color:#9aa7bd;font-size:12.5px;margin-top:2px}
nav.steps{background:#fff;border-bottom:1px solid var(--line);padding:10px 28px;
display:flex;gap:6px;flex-wrap:wrap;position:sticky;top:57px;z-index:4}
nav.steps a{font-size:12.5px;color:var(--soft);text-decoration:none;
padding:5px 11px;border-radius:15px;border:1px solid var(--line)}
nav.steps a:hover{color:var(--brand);border-color:var(--brand)}
main{max-width:960px;margin:26px auto 60px;padding:0 18px}
section.step{background:#fff;border:1px solid var(--line);border-radius:12px;
padding:24px 28px;margin-bottom:22px;scroll-margin-top:118px}
.stepno{font-size:11px;font-weight:700;letter-spacing:1.2px;color:var(--brand);
text-transform:uppercase}
h2{font-size:19px;margin:4px 0 6px}
p.explain{color:var(--soft);font-size:13.5px;margin:0 0 4px}
p.action{background:#eef3ff;border:1px solid #d6e0ff;border-radius:8px;
padding:9px 14px;font-size:13px;margin:12px 0}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:13px 17px;min-width:132px;flex:1}
.card .n{font-size:24px;font-weight:700}
.card .l{font-size:11.5px;color:var(--soft);margin-top:3px}
.ok .n{color:var(--ok)}.bad .n{color:var(--bad)}.warn .n{color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:10px 0}
th{font-size:11px;letter-spacing:.4px;text-transform:uppercase;color:var(--soft);
text-align:left;border-bottom:1px solid var(--line);padding:6px 8px}
td{padding:6px 8px;border-bottom:1px solid #f0f2f5;vertical-align:top}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.bar{background:#e9edf3;border-radius:7px;height:15px;overflow:hidden;margin:10px 0}
.bar>span{display:block;height:100%;background:var(--ok)}
.note{font-size:12.5px;color:var(--soft);margin-top:8px;border-left:3px solid
var(--line);padding-left:12px}
.continue{display:inline-block;margin-top:14px;font-size:13.5px;color:var(--brand);
text-decoration:none;font-weight:600}
footer{max-width:960px;margin:0 auto 40px;padding:0 18px;font-size:11.5px;
color:#98a2b3}
@media print{header.top,nav.steps{position:static}.continue{display:none}
section.step{break-inside:avoid;page-break-inside:avoid}}
"""


def _cards(items: List[Tuple[str, Any, str]]) -> str:
    out = ['<div class="cards">']
    for cls, value, label in items:
        out.append('<div class="card %s"><div class="n">%s</div>'
                   '<div class="l">%s</div></div>' % (cls, _e(value), _e(label)))
    out.append("</div>")
    return "\n".join(out)


def _table(headers: List[str], rows: List[List[Any]],
           numeric: Optional[List[int]] = None) -> str:
    numeric = numeric or []
    out = ["<table><tr>"]
    for i, h in enumerate(headers):
        out.append("<th%s>%s</th>" % (' class="num"' if i in numeric else "",
                                      _e(h)))
    out.append("</tr>")
    for row in rows:
        out.append("<tr>")
        for i, cell in enumerate(row):
            out.append("<td%s>%s</td>" % (' class="num"' if i in numeric
                                          else "", _e(cell)))
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def _step(no: int, key: str, title: str, explain: str, action: str,
          body: str, note: Optional[str], next_step: Optional[Tuple[str, str]]
          ) -> str:
    cont = ""
    if next_step:
        cont = ('<a class="continue" href="#%s">Continue: %s →</a>'
                % (_e(next_step[0]), _e(next_step[1])))
    return (
        '\n<section class="step" id="{id}">'
        '<div class="stepno">Step {no}</div>'
        "<h2>{title}</h2>"
        '<p class="explain">{explain}</p>'
        "{action}{body}"
        '<div class="note">{note}</div>'
        "{next_link}"
        "</section>"
        .format(id=_e(key), no=no, title=_e(title), explain=_e(explain),
                action=('<p class="action"><strong>What you do here:</strong> '
                        "%s</p>" % _e(action)) if action else "",
                body=body or "",
                note=_e(note) if note else "",
                next_link=cont))


# ---------------------------------------------------------------------------
# Billing flow
# ---------------------------------------------------------------------------
def _billing_sections(ledger: Dict[str, Any]) -> List[Section]:
    sections: List[Section] = []
    t1 = ledger.get("tier1", {})
    vendor = (ledger.get("vendor") or {}).get("name", "your vendor")
    period = ledger.get("period") or {}
    span = " to ".join(x for x in (period.get("start"), period.get("end"))
                       if x) or "the review period"
    c = t1.get("counts", {})
    over = c.get("billed_but_not_billable", 0)
    under = c.get("billable_but_not_billed", 0)
    cannot = c.get("cannot_settle", 0)
    agreed = c.get("agrees", 0)
    currency = ledger.get("currency") or ""

    inputs = ledger.get("inputs", {})
    missing = inputs.get("columns_missing") or []
    sections.append((
        "your-data", "Your data",
        "Everything below was computed from the export you provided — "
        "nothing was uploaded, and no customer conversations were read.",
        "Nothing. Read the header to confirm the vendor and period are the "
        "ones you expect, then continue.",
        _table(["What we worked from", "Detail"], [
            ["Export file", inputs.get("export_file", "—")],
            ["Vendor rulebook applied", (ledger.get("vendor") or {})
             .get("rule_source", "—")],
            ["Rows reviewed", t1.get("total_conversations", 0)],
            ["Rows that were charged", t1.get("billed_by_vendor", 0)],
        ]),
        ("Every input is fingerprinted when the review runs, so these "
         "numbers can always be tied back to the exact data."
         if not missing else
         "Some fields were missing (%s). Rows without them are marked "
         "cannot decide below — never guessed."
         % ", ".join(missing))))

    body = _cards([
        ("bad", over, "Charged, but their own rules say they shouldn't be"),
        ("ok", under, "Not charged, though their rules would allow it"),
        ("warn", cannot, "Cannot decide from this data — not guessed"),
        ("", agreed, "Charged correctly"),
    ])
    if t1.get("variance") is not None:
        body += _table(["The amounts (%s)" % currency, "Amount"], [
            ["Overcharged, by their own rulebook",
             "%.2f" % t1.get("overcharge_amount", 0)],
            ["Undercharged — reported too, in their favour",
             "%.2f" % t1.get("undercharge_amount", 0)],
            ["Net difference to raise with %s" % vendor,
             "%.2f" % t1["variance"]],
        ], numeric=[1])
    sections.append((
        "recount", "The recount",
        "We re-counted every conversation of %s using %s's own published "
        "billing rules — not ours. A finding only counts when their "
        "rulebook says so; that is what makes it hard to argue with."
        % (span, vendor),
        "Read the four numbers, then the amounts. If the net difference is "
        "worth raising, the following steps package it for you.",
        body,
        "A charge that cannot be decided is left out of the amounts and "
        "listed separately. A statement that guesses is not a statement."))

    lane = ledger.get("outcome_lane")
    if lane:
        lc = lane.get("counts", {})
        sections.append((
            "your-standard", "Your own service standard",
            "Separately from money: conversations the vendor counted as "
            "resolved that do not meet the standard written in YOUR "
            "contract — for example, a customer who came back within 72 "
            "hours of closing.",
            "Use this in renewal and vendor-review conversations. It is "
            "leverage about quality — never a refund claim.",
            _cards([
                ("bad", lc.get("fails_buyer_standard", 0),
                 "Counted as resolved, but miss your standard"),
                ("ok", lc.get("meets_buyer_standard", 0),
                 "Meet your standard"),
                ("warn", lc.get("unprovable", 0),
                 "Cannot judge from this data"),
            ]),
            "This list is never mixed into the money amounts. One is a "
            "claim; the other is leverage."))

    cc = ledger.get("billing_crosscheck")
    if cc:
        sections.append((
            "money", "Does the money match?",
            "Your helpdesk report and your billing system are two different "
            "witnesses. This step puts them side by side and lists every "
            "disagreement — it deliberately does not decide who is right.",
            "Walk the disagreements below with finance before raising "
            "anything with %s." % vendor,
            _table(["Disagreement", "Count"], [
                ["Report says charged; billing system has no record",
                 len(cc.get("flag_without_charge", []))],
                ["Billing system charged; report says it didn't",
                 len(cc.get("charge_without_export_flag", []))],
                ["Charged, but absent from the report entirely",
                 len(cc.get("not_in_export", []))],
                ["Charged at a different price than published",
                 len(cc.get("amount_deviation", []))],
            ], numeric=[1]),
            "Each disagreement needs a human. The review names it; it never "
            "quietly resolves it."))

    sections.append((
        "evidence-pack", "The evidence pack",
        "Everything above, packaged to send to %s: a short letter quoting "
        "their own rulebook for every finding, the conversation list, and "
        "the amounts — including what they got right." % vendor,
        "Generate the pack from the same data and send it to the vendor's "
        "account team. The refund is their decision; the evidence is yours.",
        _cards([
            ("", t1.get("net_findings", 0), "Net findings in the pack"),
            ("", cannot, "Rows excluded rather than guessed"),
        ]),
        "A statement that only ever finds against the vendor would not be "
        "a statement — undercharges are reported too."))

    rec = ledger.get("recovery")
    if rec:
        rt = rec.get("totals", {})
        claimed = rt.get("claimed") or 0
        realized = rt.get("realized") or 0
        pct = (100.0 * realized / claimed) if claimed else 0
        sections.append((
            "recovery", "What came back",
            "A finding is not money. This tracks what %s actually "
            "confirmed, credited, or repaid — each tied back to the original "
            "finding with a date and a reference." % vendor,
            "Record concessions as they arrive; the ledger keeps them "
            "connected to the findings they settle.",
            _table(["", "Amount (%s)" % currency], [
                ["Claimed on disputed lines", claimed],
                ["Actually recovered (credited or paid)", realized],
                ["Still outstanding", rt.get("outstanding", 0)],
            ], numeric=[1])
            + '<div class="bar"><span style="width:%.1f%%"></span></div>'
            % max(0.0, min(100.0, pct)),
            "Recovered cash is tracked separately from any renewal savings; "
            "the two are never added together."))
    return sections


# ---------------------------------------------------------------------------
# Agent channel flow
# ---------------------------------------------------------------------------
def _channel_sections(receipt: Optional[Dict[str, Any]],
                      margin: Optional[Dict[str, Any]],
                      channel: Optional[Dict[str, Any]],
                      decisions: Optional[Dict[str, Any]]) -> List[Section]:
    sections: List[Section] = []

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
        sections.append((
            "receipt", "Your agent channel, honestly counted",
            "One table for the agent-driven business: what agents did, what "
            "orders actually happened, what the money really is after "
            "refunds. Every number carries its evidence on its face.",
            "Quote the verified numbers to the business — the gap to the "
            "dashboard is quantified below it.",
            _cards([
                ("", metrics.get("observed_invocations", {}).get("value", 0),
                 "Agent-led purchases (observed)"),
                ("ok", metrics.get("observed_verified_orders", {})
                 .get("value", 0), "Verified orders"),
                ("bad", net.get("value", 0),
                 "Net revenue after refunds"),
            ]),
            note))

    if margin:
        rows = [["%s" % cat.replace("_", " "), b["amount"]]
                for cat, b in (margin.get("deductions") or {}).items()]
        cm = margin.get("contribution_margin")
        pct = margin.get("contribution_margin_pct")
        sections.append((
            "margin", "The month's real margin",
            "Revenue is not profit. This is the operating view: revenue "
            "minus coupons, media spend, platform and payment costs, service "
            "fees, fulfilment variances, and refunds.",
            "Bring this to the monthly review — it is the number the "
            "business can act on.",
            _table(["", "Amount"], [
                ["Attributed revenue (organic %s · paid %s)"
                 % (margin.get("trees", {}).get("organic"),
                    margin.get("trees", {}).get("paid")),
                 margin.get("attributed_revenue")],
            ], numeric=[1])
            + _table(["Deduction", "Amount"], rows, numeric=[1])
            + _cards([("ok", cm, "Contribution margin%s"
                       % (" (%.0f%%)" % (pct * 100) if pct is not None
                          else ""))]),
            None))

    if channel:
        verdict = channel.get("verdict", "")
        sections.append((
            "readiness", "Is the channel ready?",
            "Two different questions, answered separately: does this channel "
            "have real volume of its own (potential), and are we operating "
            "it well (performance)? Watch means the channel is real and our "
            "operating is the gap.",
            "Launch only on Launch. Invest in operating on Watch. Do not "
            "spend against a channel that is Not ready.",
            _cards([({"Launch": "ok", "Watch": "warn",
                      "Not ready": "bad"}.get(verdict, ""), verdict,
                     "Readiness verdict")])
            + _table(["Metric", "Value", "Bar", "Meets"],
                     [[r.get("metric"), r.get("value"), r.get("threshold"),
                       ("yes" if r.get("meets") else "no")
                       if r.get("meets") is not None else "not measured"]
                      for axis in (channel.get("axes") or {}).values()
                      for r in axis.get("rows", [])],
                     numeric=[1, 2]),
            None))

    if decisions:
        c = decisions.get("counts", {})
        problems = [l for l in decisions.get("lines", [])
                    if l.get("grade") != "complies"]
        sections.append((
            "guardrails", "Offer guardrails",
            "Every commercial action an agent took — discounts, offers, "
            "price changes — checked against the authorisation policy: what "
            "an agent may do alone, what required a named approval, and "
            "what is out of bounds entirely.",
            "Work the findings: either the action crossed the line, or the "
            "policy has a gap worth closing.",
            _cards([
                ("ok", c.get("complies", 0), "Within policy"),
                ("bad", c.get("violates", 0), "Violations"),
                ("warn", c.get("outside_policy", 0),
                 "Not covered by any rule yet"),
            ])
            + (_table(["Execution", "Action", "What happened"],
                      [[l.get("execution_id"), l.get("action_type"),
                        l.get("basis")] for l in problems])
               if problems else ""),
            "Commercial guardrails and operational risk share one policy "
            "language, so nothing falls between the two."))
    return sections


# ---------------------------------------------------------------------------
# The shell
# ---------------------------------------------------------------------------
def build_console(meta: Dict[str, Any],
                  ledger: Optional[Dict[str, Any]] = None,
                  receipt: Optional[Dict[str, Any]] = None,
                  margin: Optional[Dict[str, Any]] = None,
                  channel_audit: Optional[Dict[str, Any]] = None,
                  decisions: Optional[Dict[str, Any]] = None) -> str:
    """Compose the console page. All documents optional; a step appears only
    when its document exists."""
    title = meta.get("title") or "Bill verification"
    sections: List[Section] = []
    if ledger is not None:
        sections.append((
            "overview", "What this page tells you",
            "This is the review of %s against %s's own published billing "
            "rules. The steps below walk through what was found, what it "
            "means, and what you can do next — in order."
            % (meta.get("period") or "the period",
               (ledger.get("vendor") or {}).get("name", "your vendor")),
            None,
            "", None))
        sections += _billing_sections(ledger)

    channel_secs = _channel_sections(receipt, margin, channel_audit, decisions)
    if channel_secs:
        sections.append((
            "channel-intro", "Your agent channel",
            "The same discipline applied to your own agent-driven business: "
            "verified orders, real margin, channel readiness, and guardrails "
            "on what agents may decide alone.",
            None, "", None))
        sections += channel_secs

    out = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
           "<meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>%s — AgentMeasure</title><style>%s</style></head><body>"
           % (_e(title), _CSS),
           "<header class='top'><div class='mark'>AgentMeasure — %s</div>"
           "<div class='meta'>%s%s%s · computed locally, nothing uploaded, "
           "nothing tracked</div></header>"
           % (_e(title),
              _e(meta.get("vendor") + " · ") if meta.get("vendor") else "",
              _e(meta.get("period") + " · ") if meta.get("period") else "",
              _e(meta.get("buyer") or ""))]

    if sections:
        out.append("<nav class='steps'>")
        for i, (key, sec_title, _x, _a, _b, _n) in enumerate(sections):
            out.append("<a href='#%s'>%s</a>" % (_e(key), _e(sec_title)))
        out.append("</nav>")

    out.append("<main>")
    step_no = 0
    for i, (key, sec_title, explain, action, body, note) in enumerate(sections):
        if key in ("overview", "channel-intro"):
            out.append(
                '\n<section class="step" id="%s"><div class="stepno">%s</div>'
                "<h2>%s</h2><p class=\"explain\">%s</p></section>"
                % (_e(key), "Part one" if key == "overview" else "Part two",
                   _e(sec_title), _e(explain)))
            step_no = 0
            continue
        step_no += 1
        nxt = None
        for j in range(i + 1, len(sections)):
            if sections[j][0] not in ("overview", "channel-intro"):
                nxt = (sections[j][0], sections[j][1])
                break
        out.append(_step(step_no, key, sec_title, explain, action or "",
                         body or "", note, nxt))
    out.append("</main>")
    out.append("<footer>AgentMeasure · verification you can re-run · "
               "generated locally with no analytics, trackers, or network "
               "calls</footer>")
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
