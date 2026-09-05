"""Local HTML report — self-contained, static, no external assets, no JS.

The report is personal: it may contain local file paths and evidence metadata so
the evidence is actionable. Raw commands are represented by hashes rather than
copied into the report. It carries a visible banner saying so, and the
sanitized share summary is rendered separately for anything leaving the machine.
"""
import html
import os
from datetime import datetime, timezone
from typing import List

from . import __version__
from .model import CheckResult, Finding, Overview, SessionRecord
from .share import share_markdown

VERDICT_LABEL = {
    "ok": "OK",
    "finding": "FINDING",
    "unprovable": "UNPROVABLE",
    "info": "INFO",
}


class _SafeMarkup(str):
    """Marker for the one internally generated HTML fragment below."""


def _e(s: str) -> str:
    # Replace lone surrogates from escaped/malformed JSON before writing UTF-8
    # HTML. This keeps the defensive parser's no-traceback guarantee intact.
    text = str(s).encode("utf-8", "replace").decode("utf-8")
    return html.escape(text, quote=True)


def _basename(path: str) -> str:
    return os.path.basename(path)


def _detail_cells(detail: dict) -> str:
    cells = []
    for key in sorted(detail.keys()):
        val = detail[key]
        if key == "exit_codes" and val is True:
            continue  # outcomes already carries the story
        if key == "exit_codes":
            val = ", ".join("?" if c is None else str(c) for c in (val or []))
        cells.append("<div class=\"kv\"><span class=\"k\">%s</span> "
                     "<span class=\"v\">%s</span></div>"
                     % (_e(key), _e(val)))
    return "".join(cells)


def _overview_grid(ov: Overview) -> str:
    span = "%s → %s" % (ov.first_ts[:19].replace("T", " ") or "?",
                        ov.last_ts[:19].replace("T", " ") or "?")
    if ov.token_provable:
        token_line = _SafeMarkup("input %s <span class=\"sub\">(cached %s ⊆ input)</span> · "
                  "output %s <span class=\"sub\">(reasoning %s ⊆ output)</span>"
                  % ("{:,}".format(ov.token_total_input),
                     "{:,}".format(ov.token_cached_input),
                     "{:,}".format(ov.token_output),
                     "{:,}".format(ov.token_reasoning_output)))
    elif ov.token_invalid_sessions:
        token_line = "UNPROVABLE — invalid/incomplete token events in %d session(s)" \
            % ov.token_invalid_sessions
        if ov.token_missing_sessions:
            token_line += "; missing in %d" % ov.token_missing_sessions
    elif ov.token_missing_sessions:
        token_line = "UNPROVABLE — token snapshots missing in %d session(s)" \
            % ov.token_missing_sessions
    else:
        token_line = "UNPROVABLE — no token events in this window"
    items = [
        ("Sessions / files", "%s / %s" % ("{:,}".format(ov.sessions),
                                          "{:,}".format(ov.files)),
         "unique session ids / rollout files"),
        ("Turns", "{:,}".format(ov.turns), "task_started events"),
        ("Command executions", "{:,}".format(ov.exec_total),
         "ok %s · failed %s · outcome unknown %s"
         % ("{:,}".format(ov.exec_ok), "{:,}".format(ov.exec_failed),
            "{:,}".format(ov.exec_unknown))),
        ("Model-side tool calls", "{:,}".format(ov.call_total),
         "response_item records — the format's second recording; never summed "
         "with executions"),
        ("Tokens (last cumulative snapshot per session)", token_line,
         "cached and reasoning are subsets; never added into totals"),
        ("Log window data", span,
         "corrupt lines %s of %s (%.2f%%) — counts are lower bounds where lines "
         "failed to parse" % (ov.corrupt_lines, ov.lines, ov.corrupt_ratio * 100)),
        ("Read cap", "{:,} truncated file(s)".format(ov.truncated_files),
         "all metrics for a truncated file are lower bounds" if ov.truncated_files
         else "no file exceeded the per-file safety cap"),
        ("Runtime versions", ", ".join(sorted(ov.cli_versions)) or "?",
         "models: %s" % (", ".join(ov.models) or "?")),
        ("Context compactions", "{:,}".format(ov.compactions),
         "token totals are not comparable across a compaction"
         if ov.compactions else "none observed"),
    ]
    if ov.subagent_activity:
        items.append(("Sub-agent activity records", "{:,}".format(ov.subagent_activity),
                      "spawn/resume activity in this window"))
    cells = "".join(
        "<div class=\"cell\"><div class=\"label\">%s</div><div class=\"value\">%s"
        "</div><div class=\"note\">%s</div></div>"
        % (_e(label), value if isinstance(value, _SafeMarkup) else _e(value),
           _e(note) if note else "")
        for label, value, note in items)
    return "<div class=\"grid\">%s</div>" % cells


def _finding_block(f: Finding, index: int) -> str:
    ev_rows = []
    for ev in f.evidence[:20]:
        ev_rows.append(
            "<tr><td>%s</td><td class=\"path\">%s</td><td>%s</td><td>%s</td></tr>"
            % (_e(ev.session), _e(_basename(ev.file)), _e(ev.line or "—"),
               _detail_cells(ev.detail)))
    more = ""
    if len(f.evidence) > 20:
        more = "<p class=\"note\">… and %d more evidence rows (see --json export).</p>" \
               % (len(f.evidence) - 20)
    ev_html = ""
    if ev_rows:
        ev_html = ("<table><thead><tr><th>session</th><th>file</th><th>line</th>"
                   "<th>detail</th></tr></thead><tbody>%s</tbody></table>%s"
                   % ("".join(ev_rows), more))
    return (
        "<div class=\"finding sev-%s\"><h4>#%d %s</h4>"
        "<p>%s</p><p><strong>Next step:</strong> %s</p>%s</div>"
        % (f.severity, index, _e(f.title), _e(f.explanation), _e(f.next_step), ev_html))


def _check_block(c: CheckResult) -> str:
    findings_html = "".join(_finding_block(f, i + 1)
                            for i, f in enumerate(c.findings))
    unprov = ""
    if c.unprovable_reason:
        unprov = "<p class=\"unprov\">UNPROVABLE part: %s</p>" % _e(c.unprovable_reason)
    return (
        "<section class=\"check\"><h3><span class=\"badge st-%s\">%s</span> %s · %s</h3>"
        "<p>%s</p>%s%s</section>"
        % (c.status, VERDICT_LABEL.get(c.status, c.status), _e(c.check_id),
           _e(c.name), _e(c.summary), unprov, findings_html))


def render_html(ov: Overview, checks: List[CheckResult], coverage: List[Finding],
                top3: List[Finding], sessions: List[SessionRecord], mode: str,
                window_label: str, command: str, share_summary: dict) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode_badge = "SYNTHETIC DEMO" if mode == "synthetic-demo" else "OWN DATA"
    top3_html = "".join(_finding_block(f, i + 1) for i, f in enumerate(top3)) or \
        "<p>No ranked findings in this window.</p>"
    checks_html = "".join(_check_block(c) for c in checks)
    coverage_html = "".join(_finding_block(f, i + 1) for i, f in enumerate(coverage)) or \
        "<p>No coverage anomalies.</p>"
    feature_by_session = {}
    for s in sessions:
        key = s.session_id or s.path
        flags = s.feature_flags()
        current = feature_by_session.setdefault(key, {})
        for k, v in flags.items():
            current[k] = current.get(k, False) or v
    session_count = len(feature_by_session)
    features = {}
    for flags in feature_by_session.values():
        for k, v in flags.items():
            features[k] = features.get(k, 0) + (1 if v else 0)
    feature_line = " · ".join("%s: %d/%d sessions" % (k, v, session_count)
                              for k, v in sorted(features.items())) or "—"

    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentMeasure Healthcheck · {window}</title>
<style>
:root{{--ink:#1d1b17;--soft:#5b5548;--line:#ddd3c2;--panel:#faf7f0;--accent:#a4511f;
--ok:#2c6e49;--find:#a4511f;--unprov:#7a6a2f;--info:#4a5d82;--bg:#f4efe5}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}}
main{{max-width:980px;margin:0 auto;padding:34px 26px 60px}}
h1{{font-size:26px;margin:0 0 6px;letter-spacing:-.3px}}
h2{{font-size:19px;margin:34px 0 12px;border-bottom:2px solid var(--ink);padding-bottom:6px}}
h3{{font-size:16px;margin:22px 0 8px}}h4{{font-size:15px;margin:14px 0 6px}}
.meta{{color:var(--soft);font-size:13px}}.banner{{background:#f3e3c8;border:1px solid
#d8bf92;border-radius:6px;padding:10px 14px;font-size:13px;margin:14px 0}}
.badge{{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.6px;
padding:2px 8px;border-radius:4px;margin-right:8px;vertical-align:1px}}
.st-ok{{background:#dcebe1;color:var(--ok)}}.st-finding{{background:#f4ddcc;color:var(--find)}}
.st-unprovable{{background:#efe7c6;color:var(--unprov)}}.st-info{{background:#dee5f0;color:var(--info)}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:14px 0}}
.cell{{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:10px 13px}}
.cell .label{{font-size:11.5px;letter-spacing:.4px;color:var(--soft);
text-transform:uppercase;font-weight:600}}
.cell .value{{font-size:16px;margin:3px 0 2px}}.cell .note{{font-size:12px;color:var(--soft)}}
.sub{{color:var(--soft);font-size:12px}}
.finding{{border:1px solid var(--line);border-left:4px solid var(--find);
border-radius:6px;background:var(--panel);padding:12px 16px;margin:12px 0}}
.finding.sev-info{{border-left-color:var(--info)}}
.finding h4{{margin-top:2px}}.finding p{{margin:6px 0;font-size:14px}}
.unprov{{background:#efe7c6;border-radius:4px;padding:8px 12px;font-size:13px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0}}
th,td{{border-bottom:1px solid var(--line);padding:6px 9px;text-align:left;
vertical-align:top}}th{{background:#ece5d6;font-size:11px;
text-transform:uppercase;letter-spacing:.4px}}
td.path{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;max-width:220px;
overflow-wrap:anywhere}}
.kv{{display:inline-block;margin-right:14px}}.kv .k{{color:var(--soft)}}
.kv .v{{font-family:ui-monospace,Menlo,monospace}}
pre{{background:var(--panel);border:1px solid var(--line);border-radius:6px;
padding:14px 16px;overflow-x:auto;font-size:12.5px;line-height:1.6;white-space:pre-wrap}}
.sharebox{{background:#eef0e9;border:1px solid #c9d1bd;border-radius:6px;padding:4px 14px}}
.note{{color:var(--soft);font-size:12.5px}}ol,ul{{padding-left:22px}}li{{margin:6px 0}}
footer{{margin-top:40px;border-top:1px solid var(--line);padding-top:14px;
font-size:12px;color:var(--soft)}}
@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}}main{{max-width:none}}}}
</style></head><body><main>
<h1>AgentMeasure Healthcheck <span class="badge st-{mode_class}">{mode_badge}</span></h1>
<p class="meta">v{version} · generated {generated} · window: {window} ·
{files} file(s), {sessions_ct} session(s)</p>
<div class="banner"><strong>This file is personal.</strong> It may contain local
paths and evidence metadata. Raw commands are represented by hashes.
To share results, use the sanitized
summary at the bottom of this page — never upload this file as-is.</div>

<h2>Overview</h2>
{overview}

<h2>Worth checking first</h2>
{top3}

<h2>Checks</h2>
{checks}

<h2>Coverage &amp; format notes</h2>
{coverage}
<p class="note">Format features detected: {features}</p>

<h2>Methodology &amp; limits</h2>
<ul>
<li><strong>Execution vs logical operation.</strong> One command execution is one
attempt. A maximal block of consecutive executions of the same command
(first one failed) is one retry chain = one logical operation executed N times.
Executions are counted from the <code>item_completed</code> stream; the
<code>response_item</code> stream is reported separately and never summed with it.</li>
<li><strong>Token subsets.</strong> <code>cached_input</code> ⊆ input and
<code>reasoning_output</code> ⊆ output in Codex logs. Subsets are displayed,
never added into totals. Token totals use the last cumulative snapshot per
session; they are not per-turn sums.</li>
<li><strong>UNPROVABLE is a result.</strong> When the logs cannot decide a check
(outcomes absent, records missing), the check reports UNPROVABLE for that part —
it is never counted as zero or OK.</li>
<li><strong>Corrupt lines lower every count.</strong> All counts are lower bounds
where lines failed to parse; the corrupt count is reported per file.</li>
<li><strong>Local only.</strong> This tool contains no network code; nothing is
uploaded. Run history stays in <code>~/.agentmeasure/history.jsonl</code>.</li>
</ul>

<h2>Sanitized share summary</h2>
<div class="sharebox"><pre>{share_md}</pre></div>
<p class="note">Aggregate counts only — no prompts, paths, commands, repo names,
or session ids. Export with <code>--share summary.md</code> after reviewing.</p>

<h2>Reproduce</h2>
<pre>{command}</pre>

<footer>AgentMeasure Healthcheck v{version} · PASS / FINDING / UNPROVABLE discipline ·
Deterministic metrics: same logs + same version → same counts and findings.</footer>
</main></body></html>""".format(
        window=_e(window_label), mode_badge=mode_badge,
        mode_class="info" if mode == "synthetic-demo" else "finding",
        version=_e(__version__), generated=generated,
        files="{:,}".format(ov.files), sessions_ct="{:,}".format(ov.sessions),
        overview=_overview_grid(ov), top3=top3_html, checks=checks_html,
        coverage=coverage_html, features=_e(feature_line),
        share_md=_e(share_markdown(share_summary)), command=_e(command))
