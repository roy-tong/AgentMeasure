"""Report rendering (LAB-008): self-contained offline HTML from report.json.

No external assets, no CDN, no JavaScript — the report is a static evidence
document. Every rate shows its confidence interval; every table row carries
its measurement label; the anti-fake-growth and honest-null disciplines are
visible in the layout, not buried in prose.
"""

import html
from typing import Any, Dict, Optional

_VERDICT_STYLE = {
    "adopt_candidate": ("adopt candidate", "ok"),
    "effective_not_qualified": ("effective, not qualified (guardrail breach)", "warn"),
    "unverified_growth": ("growth not verified — do not ship", "bad"),
    "regression_reject": ("significant regression — reject", "bad"),
    "null_result": ("honest null", "null"),
    "undetermined": ("undetermined — insufficient sample", "unknown"),
    "baseline": ("baseline", "baseline"),
    "significant": ("significant", "ok"),
}

_CSS = """
:root { --ink:#1a1d21; --muted:#5c6670; --line:#dfe3e8; --bg:#ffffff; --accent:#0f62fe;
  --ok-bg:#e8f5e9; --ok-ink:#1b5e20; --warn-bg:#fff8e1; --warn-ink:#8d6e00;
  --bad-bg:#fdecea; --bad-ink:#8f1f17; --null-bg:#f3f4f6; --null-ink:#4b5563; }
* { box-sizing: border-box; }
body { font-family: ui-sans-serif, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  color: var(--ink); background: var(--bg); margin: 0; padding: 2rem; line-height: 1.55; }
.wrap { max-width: 68rem; margin: 0 auto; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
h2 { font-size: 1.05rem; margin: 2.2rem 0 .6rem; padding-bottom:.3rem; border-bottom: 1px solid var(--line); }
.meta { color: var(--muted); font-size: .85rem; }
.meta code { background:#f5f6f8; padding:.1rem .35rem; border-radius:3px; font-size:.8rem; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0 1rem; font-size: .88rem; }
th, td { border: 1px solid var(--line); padding: .45rem .6rem; text-align: left; vertical-align: top; }
th { background: #f7f8fa; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.badge { display:inline-block; padding:.12rem .55rem; border-radius:999px; font-size:.78rem; font-weight:600; }
.ok { background:var(--ok-bg); color:var(--ok-ink); }
.warn { background:var(--warn-bg); color:var(--warn-ink); }
.bad { background:var(--bad-bg); color:var(--bad-ink); }
.null { background:var(--null-bg); color:var(--null-ink); }
.unknown { background:#e8f0fe; color:#1e3a8a; }
.baseline { background:#f3f4f6; color:#4b5563; }
.callout { border-left: 4px solid var(--accent); background:#f5f8ff; padding:.8rem 1rem; margin:1rem 0; font-size:.92rem; }
.callout.warn { border-color:#b28900; background:var(--warn-bg); }
.callout.bad { border-color:#c0392b; background:var(--bad-bg); }
.small { font-size:.82rem; color:var(--muted); }
.verdict-hero { display:flex; gap:.8rem; align-items:baseline; flex-wrap:wrap; margin:.5rem 0; }
"""


def _esc(x: Any) -> str:
    return html.escape(str(x), quote=True)


def _pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _ci(m: Dict[str, Any]) -> str:
    ci = m.get("ci95")
    if not ci or m.get("value") is None:
        return "—"
    return f"[{_pct(ci[0])}, {_pct(ci[1])}]"


def _badge(verdict: str) -> str:
    label, style = _VERDICT_STYLE.get(verdict, (verdict, "unknown"))
    return f'<span class="badge {style}">{_esc(label)}</span>'


def _certainty(cmp: Dict[str, Any]) -> str:
    """Boss-facing certainty phrasing, no statistics vocabulary required."""
    if cmp.get("verdict") == "significant":
        p = cmp.get("p_value")
        return f"high (p={p:.4f})" if p is not None else "high"
    if cmp.get("verdict") == "null_result":
        return "no measurable difference"
    if cmp.get("verdict") == "undetermined":
        return "not enough data"
    return "—"


def _render_onepager(report: Dict[str, Any]) -> str:
    """Decision-first one-pager (POC finding: the payer must be able to read
    the conclusion without an engineer). Bilingual by design — the payer and
    the team may not share a working language."""
    decisions = {d["variant_id"]: d for d in report.get("decision", {}).get("recommendations", [])}
    rows = []
    for v in sorted(report["variants"], key=lambda x: (x.get("baseline") is False, x["variant_id"])):
        plain = v.get("plain_label") or ("", "")
        cmp = v.get("primary_comparison", {})
        diff = cmp.get("difference")
        diff_txt = "—" if diff is None else f"{diff * 100:+.1f}pp"
        margin = (v.get("value") or {}).get("incremental_margin_per_month")
        margin_txt = "—" if margin is None else f"${margin:,.0f}"
        action = decisions.get(v["variant_id"], {}).get("recommended_action", "—")
        badge = _badge("baseline") if v.get("baseline") else _badge(v["verdict"])
        fg = v.get("fake_growth") or {}
        warn = '<br><span class="badge bad">fake growth 假增长</span>' if fg.get("flagged") else ""
        dom = f'<br><span class="badge null">dominated by {_esc(v["dominated_by"])}</span>' if v.get("dominated_by") else ""
        rows.append(
            f"<tr><td><strong>{_esc(v['variant_id'])}</strong></td>"
            f"<td>{badge}<br><span class=small>{_esc(plain[0])}<br>{_esc(plain[1])}</span></td>"
            f"<td class=num>{_esc(diff_txt)}</td><td class=num>{_esc(margin_txt)}</td>"
            f"<td>{_esc(_certainty(cmp))}</td><td>{_esc(action)}{warn}{dom}</td></tr>"
        )
    status = (
        '<span class="badge ok">complete 完成</span>'
        if report["run"]["status"] == "complete"
        else f'<span class="badge warn">incomplete 未完成 — {_esc(report["run"].get("stopped_reason"))}</span>'
    )
    return (
        "<h2>For the decision maker · 给决策人的一页</h2>"
        f"{status}"
        "<table><tr><th>variant 方案</th><th>conclusion 结论</th><th class=num>uplift 提升</th>"
        "<th class=num>margin/月 毛利</th><th>certainty 把握</th><th>recommended 建议动作</th></tr>"
        + "".join(rows)
        + "</table>"
        '<p class="small">Margin uses measured factors from this experiment (success × consumption) '
        "and business parameters supplied by you (opportunities, conversion, unit margin). "
        "毛利 = 实验测量因子（成功率×消费率）× 你方提供的业务参数（机会量、转化、单次毛利）。"
        "This is a recommendation, not a decision — continue/scale/stop belongs to you. "
        "以上是建议而非决策——继续/加量/停止由你决定。</p>"
    )


def render_html(report: Dict[str, Any]) -> str:
    r = report
    run = r["run"]
    prereg = r["preregistration"]
    parts: list = []

    status_badge = (
        f'<span class="badge ok">complete</span>'
        if run["status"] == "complete"
        else f'<span class="badge warn">incomplete — stopped: {_esc(run.get("stopped_reason"))}</span>'
    )

    parts.append(
        f"""<div class="wrap">
<h1>AgentMeasure Lab — Experiment Report</h1>
<div class="meta">
experiment <strong>{_esc(r['experiment_id'])}</strong> · {status_badge}
engine {_esc(r['engine_version'])} · funnel rules {_esc(r['funnel_rules_version'])} ·
seed {_esc(run['seed'])} · preregistration <code>{_esc(prereg['manifest_hash'][:16])}…</code> ·
fingerprint <code>{_esc(run['run_fingerprint'][:16])}…</code><br>
hypothesis: {_esc(r['hypothesis'])}
</div>"""
    )

    parts.append(_render_onepager(r))

    if r.get("decision"):
        parts.append("<h2>Decision summary</h2><table><tr><th>variant</th><th>verdict</th><th>recommended action</th></tr>")
        for rec in r["decision"]["recommendations"]:
            parts.append(
                f"<tr><td>{_esc(rec['variant_id'])}</td><td>{_badge(rec['verdict'])}</td>"
                f"<td>{_esc(rec['recommended_action'])}</td></tr>"
            )
        parts.append("</table>")
        parts.append(f'<p class="small">{_esc(r["decision"]["note"])}</p>')

    parts.append("<h2>Arms (with 95% Wilson intervals)</h2>")
    parts.append(
        "<table><tr><th>variant</th><th>levels</th><th class=num>reach</th>"
        "<th class=num>selection</th><th class=num>op success</th><th class=num>consumption</th>"
        "<th class=num>attempts/op</th><th class=num>median steps</th><th class=num>cost/op</th></tr>"
    )
    for v in r["variants"]:
        m = v["metrics"]
        parts.append(
            f"<tr><td>{_esc(v['variant_id'])}<br>{_badge(v['verdict'])}</td>"
            f"<td class=small>{_esc(', '.join(f'{k}={w}' for k, w in v['levels'].items()))}</td>"
            f"<td class=num>{m['reach']}</td>"
            f"<td class=num>{_pct(m['selection_rate']['value'])}<br><span class=small>{_ci(m['selection_rate'])}</span></td>"
            f"<td class=num>{_pct(m['operation_success_rate']['value'])}<br><span class=small>{_ci(m['operation_success_rate'])}</span></td>"
            f"<td class=num>{_pct(m['consumption_rate']['value'])}<br><span class=small>{_ci(m['consumption_rate'])}</span></td>"
            f"<td class=num>{m['attempts_per_operation']['value'] or '—'}</td>"
            f"<td class=num>{m['median_steps_per_operation']['value'] or '—'}</td>"
            f"<td class=num>{m['cost_units_per_operation']['value'] or '—'}</td></tr>"
        )
    parts.append("</table>")
    parts.append(f'<p class="small">{_esc(r["secondary_metrics_note"])} — consumption denominator: successful operations; selection denominator: decision opportunities (reach).</p>')

    for v in r["variants"]:
        cmp = v.get("primary_comparison")
        if not cmp:
            continue
        parts.append(f"<h2>Primary comparison — {_esc(v['variant_id'])} vs baseline</h2>")
        verdict_badge = _badge(
            "significant" if cmp["verdict"] == "significant" else cmp["verdict"]
        )
        direction = f" ({_esc(cmp['direction'])})" if cmp.get("direction") else ""
        diff = cmp.get("difference")
        diff_txt = "—" if diff is None else f"{diff * 100:+.1f}pp"
        dci = cmp.get("diff_ci95")
        dci_txt = "—" if not dci else f"[{dci[0]*100:+.1f}pp, {dci[1]*100:+.1f}pp]"
        p = cmp.get("p_value")
        p_txt = "—" if p is None else f"{p:.4f}"
        parts.append(
            f"<div class='verdict-hero'>{verdict_badge}"
            f"<span>Δ {_esc(cmp['metric'])}: <strong>{_esc(diff_txt)}</strong> {direction} · "
            f"CI95 {_esc(dci_txt)} · p={_esc(p_txt)} · α={_esc(cmp['alpha'])}</span></div>"
        )
        if cmp.get("reason"):
            parts.append(f'<p class="small">{_esc(cmp["reason"])}</p>')
        if cmp.get("power_note"):
            parts.append(
                f'<div class="callout"><strong>Next round sizing.</strong> {_esc(cmp["power_note"])}</div>'
            )
        if v.get("dominance_note"):
            parts.append(f'<div class="callout warn"><strong>Dominated.</strong> {_esc(v["dominance_note"])}</div>')
        if (v.get("fake_growth") or {}).get("note") and not (v.get("fake_growth") or {}).get("flagged"):
            parts.append(f'<p class="small">{_esc(v["fake_growth"]["note"])}</p>')
        if v.get("per_condition"):
            parts.append("<table><tr><th>condition (harness)</th><th class=num>Δ</th><th class=num>CI95</th><th class=num>p</th><th>verdict</th></tr>")
            for pc in v["per_condition"]:
                c = pc["comparison"]
                d = c.get("difference")
                d_txt = "—" if d is None else f"{d * 100:+.1f}pp"
                cci = c.get("diff_ci95")
                cci_txt = "—" if not cci else f"[{cci[0]*100:+.1f}, {cci[1]*100:+.1f}]pp"
                pp = c.get("p_value")
                pp_txt = "—" if pp is None else f"{pp:.4f}"
                parts.append(
                    f"<tr><td>{_esc(pc['condition'])}</td><td class=num>{_esc(d_txt)}</td>"
                    f"<td class=num>{_esc(cci_txt)}</td><td class=num>{_esc(pp_txt)}</td>"
                    f"<td>{_esc(c['verdict'])}</td></tr>"
                )
            parts.append("</table>")
            parts.append('<p class="small">Per-condition effect sizes are reported in their own right; a pooled coefficient alone would hide harness-level disagreement.</p>')

        if (v.get("fake_growth") or {}).get("flagged"):
            fg = v["fake_growth"]
            parts.append(
                f'<div class="callout bad"><strong>Fake-growth warning.</strong> '
                f"{_esc(fg['message'])} (consumption Δ {fg['consumption_delta'] * 100:+.1f}pp)</div>"
            )

        if v.get("guardrails"):
            parts.append("<table><tr><th>guardrail</th><th class=num>value</th><th>threshold</th><th>status</th></tr>")
            for g in v["guardrails"]:
                val = g["value"]
                val_txt = "—" if val is None else (
                    f"{val:.2f}" if g["metric"] == "attempts_per_operation" else (
                        f"{val * 100:.1f}%" if g["metric"] == "consumption_rate" else f"{val:.1f}"
                    )
                )
                thr = g["threshold"]
                thr_txt = "max " + str(thr["max"]) if "max" in thr else "min " + str(thr["min"])
                style = {"pass": "ok", "breach": "bad", "unknown": "unknown"}.get(g["status"], "unknown")
                parts.append(
                    f"<tr><td>{_esc(g['metric'])}</td><td class=num>{_esc(val_txt)}</td>"
                    f"<td>{_esc(thr_txt)}</td><td><span class='badge {style}'>{_esc(g['status'])}</span></td></tr>"
                )
            parts.append("</table>")

        if v.get("value"):
            val = v["value"]
            parts.append("<h3>Value formula</h3>")
            if val.get("computable"):
                parts.append(
                    f'<div class="callout">Incremental margin <strong>{_esc(val["incremental_margin_per_month"])}</strong> / month '
                    f"(Δselection {val['selection_rate_delta'] * 100:+.1f}pp; measured P(success)={val['measured_factors']['P_success_given_selected']['value']:.3f}, "
                    f"P(consumed)={val['measured_factors']['P_consumed_given_success']['value']:.3f}; parameters supplied by customer). "
                    f"Formula: {_esc(val['formula'])}"
                    + (" · fake-growth-adjusted: consumption taken from the candidate arm." if val.get("fake_growth_adjusted") else "")
                    + "</div>"
                )
            else:
                parts.append(
                    f'<p class="small">Value formula not computable (missing: {_esc(", ".join(val.get("missing_parameters", [])))}) — {_esc(val.get("note", ""))}</p>'
                )

    parts.append("<h2>Measurement discipline</h2><ul>")
    for lim in r["limitations"]:
        parts.append(f"<li>{_esc(lim)}</li>")
    parts.append("</ul>")

    b = run["budget"]
    parts.append(
        f"<h2>Budget usage</h2><table><tr><th>dimension</th><th class=num>spent</th><th class=num>limit</th></tr>"
        f"<tr><td>operations</td><td class=num>{b['spent_operations']}</td><td class=num>{b['max_operations']}</td></tr>"
        f"<tr><td>cost units</td><td class=num>{b['spent_cost_units']}</td><td class=num>{b['max_cost_units']}</td></tr>"
        f"<tr><td>wall clock (s)</td><td class=num>{b['spent_wall_clock_seconds']}</td><td class=num>{b['max_wall_clock_seconds']}</td></tr></table>"
    )
    parts.append(
        f'<p class="small">Determinism: {_esc(run["determinism_note"])}. Task set {_esc(run["task_set"]["path"])} '
        f'(<code>{_esc(run["task_set"]["sha256"][:16])}…</code>). '
        f'Assignments executed {run["assignments_executed"]}/{run["assignments_planned"]}; '
        f'plan balanced: {str(run["plan"]["balanced"]).lower()}.</p>'
    )
    for h in run["harnesses"]:
        if h.get("disclosure"):
            parts.append(f'<p class="small"><strong>Harness {_esc(h["runner_id"])}</strong>: {_esc(h["disclosure"])}</p>')
    parts.append("</div>")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{_esc(r['experiment_id'])} — Lab report</title><style>{_CSS}</style></head><body>{''.join(parts)}</body></html>"


_CAL_VERDICT_STYLE = {
    "production_confirmed": ("production confirmed", "ok"),
    "direction_mismatch": ("direction mismatch — do not scale", "bad"),
    "transfer_not_established": ("not established in production", "warn"),
    "undetermined": ("undetermined — insufficient production sample", "unknown"),
    "not_comparable": ("not comparable — data gap", "null"),
}


def _pp(diff: Optional[float]) -> str:
    return "—" if diff is None else f"{diff * 100:+.1f}pp"


def _pp_ci(ci: Optional[list]) -> str:
    if not ci:
        return "—"
    return f"[{ci[0] * 100:+.1f}pp, {ci[1] * 100:+.1f}pp]"


def render_calibration_html(cal: Dict[str, Any]) -> str:
    """Offline-vs-production calibration report (CAL-002/003)."""
    parts: list = []
    parts.append(
        f"""<div class="wrap">
<h1>AgentMeasure Lab — Calibration Report</h1>
<div class="meta">
experiment <strong>{_esc(cal['experiment_id'])}</strong> ·
preregistration <code>{_esc(cal['preregistration']['manifest_hash'][:16])}…</code> ·
primary metric <strong>{_esc(cal['preregistration']['primary_metric'])}</strong> ·
offline fingerprint <code>{_esc((cal['offline_run'].get('run_fingerprint') or '')[:16])}…</code><br>
production source: {_esc(cal['production_source'].get('events_file', ''))} — {_esc(cal['production_source'].get('environment', ''))}
</div>"""
    )
    parts.append(
        f'<p class="small">{_esc(cal["production_source"].get("note", ""))}</p>'
    )

    for v in cal["variants"]:
        verdict = v.get("calibration", {})
        key = verdict.get("calibration", "not_comparable")
        label, style = _CAL_VERDICT_STYLE.get(key, (key, "unknown"))
        parts.append(
            f"<h2>Variant {_esc(v['variant_id'])} <span class='badge {style}'>{_esc(label)}</span></h2>"
        )
        if "reason" in verdict:
            parts.append(f'<p class="small">{_esc(verdict["reason"])}</p>')
        if "offline_comparison" in v:
            off, prod = v["offline_comparison"], v["production_comparison"]
            parts.append(
                "<table><tr><th>side</th><th class=num>Δ</th><th class=num>CI95</th><th class=num>p</th><th>verdict</th></tr>"
                f"<tr><td>offline (controlled)</td><td class=num>{_esc(_pp(off.get('difference')))}</td>"
                f"<td class=num>{_esc(_pp_ci(off.get('diff_ci95')))}</td>"
                f"<td class=num>{_esc(off.get('p_value'))}</td><td>{_esc(off.get('verdict'))}</td></tr>"
                f"<tr><td><strong>production (rollout)</strong></td><td class=num>{_esc(_pp(prod.get('difference')))}</td>"
                f"<td class=num>{_esc(_pp_ci(prod.get('diff_ci95')))}</td>"
                f"<td class=num>{_esc(prod.get('p_value'))}</td><td>{_esc(prod.get('verdict'))}</td></tr></table>"
            )
            tr = v.get("transfer_overall")
            if tr:
                parts.append(
                    f'<div class="callout">Transfer (offline − production): <strong>{_esc(_pp(tr["offline_minus_production"]))}</strong> '
                    f"{_esc(_pp_ci(tr.get('ci95_approx')))} · {_esc(tr['method'])} — reported per condition below; never a single global coefficient.</div>"
                )
        if v.get("per_condition"):
            parts.append("<table><tr><th>condition</th><th class=num>offline Δ</th><th class=num>production Δ</th><th class=num>transfer</th><th>production verdict</th></tr>")
            for row in v["per_condition"]:
                if row.get("status") == "not_comparable":
                    parts.append(
                        f"<tr><td>{_esc(row['condition'])}</td><td colspan=3><span class='badge null'>{_esc(row['status'])}</span> "
                        f"<span class=small>{_esc(row.get('gap', ''))}</span></td></tr>"
                    )
                    continue
                prod = row["comparison"]
                off = row.get("offline", {})
                tr = row.get("transfer", {})
                parts.append(
                    f"<tr><td>{_esc(row['condition'])}</td>"
                    f"<td class=num>{_esc(_pp(off.get('difference')))}</td>"
                    f"<td class=num>{_esc(_pp(prod.get('difference')))}</td>"
                    f"<td class=num>{_esc(_pp(tr.get('offline_minus_production')))}</td>"
                    f"<td>{_esc(prod.get('verdict'))}</td></tr>"
                )
            parts.append("</table>")
        if v.get("reweighting_suggestions"):
            parts.append("<h3>Matrix reweighting suggestions (next experiment)</h3><ul>")
            for s in v["reweighting_suggestions"]:
                parts.append(
                    f"<li><strong>{_esc(s['condition'])}</strong>: transfer {_esc(_pp(s['transfer']))} — {_esc(s['suggestion'])}</li>"
                )
            parts.append("</ul>")

    parts.append("<h2>Limitations</h2><ul>")
    for lim in cal["limitations"]:
        parts.append(f"<li>{_esc(lim)}</li>")
    parts.append("</ul></div>")
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{_esc(cal['experiment_id'])} — calibration</title>"
        f"<style>{_CSS}</style></head><body>{''.join(parts)}</body></html>"
    )
