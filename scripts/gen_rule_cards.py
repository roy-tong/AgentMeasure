#!/usr/bin/env python3
"""Generate the public vendor rule cards (website/rules/) from the registry.

Every vendor in registry/vendor-rules.json gets one linkable card: what the
vendor charges per, what its own published rules say (trigger, silence,
reopen deduction, closure timers), where each fact came from, and which
registry version it was read from. The cards are the hook asset for
claim-style outreach (variant E) and the public definition of the L0 rule
layer — the same JSON the CLI and the browser recount read.

  python3 scripts/gen_rule_cards.py --build   # regenerate
  python3 scripts/gen_rule_cards.py --check   # CI: fail if out of date

Deterministic by construction: no timestamps — the page states the registry
version, which is the only thing that should change when rules change.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "registry" / "vendor-rules.json"
DST = ROOT / "website" / "rules"

TRIGGER_TEXT = {
    "confirmed_or_assumed": "bills on confirmed <em>or assumed</em> resolutions (silence can bill)",
    "assumed_with_lock": "assumes resolution after a lock window; a reopen after the lock starts a fresh billable window",
    "algorithmic_classification": "an internal algorithm classifies the conversation as resolved",
    "llm_verified_only": "only an affirmative model adjudication counts — silence alone is free",
    "autonomous_completion": "bills on autonomous completion (no published timer or reopen rule)",
    "unknown": "no published rule — only the AgentMeasure standard applies",
}

REOPEN_TEXT = {
    "documented_including_cross_period": "documented reopen deduction, including across billing periods",
    "not_documented": "no documented reopen deduction",
    "none_after_lock": "none after the lock window",
}

_CSS = """
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.card{border:1px solid #e3e8ef;border-radius:12px;padding:20px 22px;background:#fff}
.card h2{margin:0 0 2px;font-size:18px}
.muted{color:#5c6575;font-size:13px}
.kv{display:grid;grid-template-columns:130px 1fr;gap:4px 12px;margin:12px 0;font-size:14px}
.kv dt{color:#5c6575}
.kv dd{margin:0}
.badge{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:10px;vertical-align:2px;margin-left:8px}
.P{background:#e5f4ec;color:#0c7a48}.S{background:#fbf1de;color:#8a5a0d}.U{background:#f0f2f5;color:#5c6575}
.notes{font-size:13px;color:#5c6575;margin:10px 0 0;padding-left:12px;border-left:3px solid #e3e8ef}
a{color:#3050c8}
body{font:15px/1.65 -apple-system,'Segoe UI','PingFang SC',sans-serif;color:#181f2c;background:#f6f7f9;margin:0}
.wrap{max-width:900px;margin:0 auto;padding:40px 24px 70px}
h1{font-size:24px;letter-spacing:-.3px}
"""

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="../styles.css">
<style>{css}</style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""


def _vendor_card(vendor_id: str, v: dict) -> str:
    price = ("%s %s per resolution" % (v.get("currency") or "",
                                       v.get("unit_price"))
             if v.get("unit_price") else "not published")
    timers = v.get("closure_timers_hours") or {}
    timer_html = (" · ".join("%s: %sh" % (k, val)
                             for k, val in sorted(timers.items()))
                  or "not published")
    notes = "".join("<li>%s</li>" % n for n in (v.get("notes") or []))
    extra = ""
    if v.get("structural_risk"):
        extra += ('<p class="notes">%s</p>' % v["structural_risk"])
    if v.get("operator_override"):
        extra += ('<p class="notes">%s</p>' % v["operator_override"])
    if v.get("no_reversal"):
        extra += ('<p class="notes">%s</p>' % v["no_reversal"])
    return f"""<div class="card" id="{vendor_id}">
<h2>{v['name']}<span class="badge {v['confidence']}">{v['confidence']}</span></h2>
<div class="muted">rule card · registry v{v['_registry_version']}</div>
<dl class="kv">
<dt>Price</dt><dd>{price}</dd>
<dt>Billing trigger</dt><dd>{TRIGGER_TEXT.get(v['billing_trigger'], v['billing_trigger'])}</dd>
<dt>Reopen handling</dt><dd>{REOPEN_TEXT.get(v['reopen_deduction'], v['reopen_deduction'])}</dd>
<dt>Silence bills</dt><dd>{'yes' if v.get('silence_bills') else ('no' if v.get('silence_bills') is False else 'unknown')}{(' — window %sh' % v['silence_window_hours']) if v.get('silence_window_hours') else ''}</dd>
<dt>Closure timers</dt><dd>{timer_html}</dd>
<dt>Source</dt><dd><a href="{v.get('source','')}" rel="noopener">{v.get('source','—')}</a></dd>
</dl>
{('<ul class="notes">%s</ul>' % notes) if notes else ''}
{extra}
<p class="muted">Re-run the recount yourself: <a href="../recount.html">in the browser</a> or <code>agentmeasure recount --vendor {vendor_id}</code>. Rules change; this card records the version it was read from.</p>
</div>"""


def render() -> dict:
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    version = doc["version"]
    cards = []
    for vendor_id, v in sorted(doc["vendors"].items()):
        v = dict(v)
        v["_registry_version"] = version
        cards.append(_vendor_card(vendor_id, v))
    body = f"""<h1>Vendor billing rules, in public</h1>
<p class="muted">One card per vendor: what the vendor charges per, what its own published
rules say, and where every fact came from. This is the same
<a href="https://github.com/roy-tong/AgentMeasure/blob/main/registry/vendor-rules.json">registry
file</a> the CLI and the browser recount read — a parity test in CI keeps the three from
drifting. Registry version <strong>v{version}</strong>.</p>
<p class="muted">Confidence: <span class="badge P">P</span> primary/official source ·
<span class="badge S">S</span> secondary source ·
<span class="badge U">U</span> unverified. A missing fact is never guessed — it shows as
"not published".</p>
<div class="cards">
{chr(10).join(cards)}
</div>
<p class="muted" style="margin-top:28px">Find a rule that changed, or one we read wrong?
<a href="https://github.com/roy-tong/AgentMeasure/edit/main/registry/vendor-rules.json">Edit the registry</a> —
pull requests welcome, every field carries its source.</p>"""
    return {"index.html": _PAGE.format(
        title="Vendor billing rules — AgentMeasure",
        desc="What AI support vendors charge per and what their own published rules say — versioned, sourced, re-runnable.",
        css=_CSS, body=body)}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv
    expected = render()
    if check:
        stale = []
        for name, content in expected.items():
            path = DST / name
            actual = path.read_text(encoding="utf-8") if path.exists() else ""
            if actual != content:
                stale.append(name)
        if stale:
            print("  ✗ website/rules/ out of date with registry/vendor-rules.json: %s"
                  % ", ".join(stale))
            print("    run: python3 scripts/gen_rule_cards.py --build")
            return 1
        print("  ✓ website/rules/ in sync with the registry")
        return 0
    DST.mkdir(parents=True, exist_ok=True)
    for name, content in expected.items():
        (DST / name).write_text(content, encoding="utf-8")
        print("  wrote %s" % (DST / name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
