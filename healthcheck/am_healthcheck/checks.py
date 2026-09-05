"""Deterministic checks: coverage overview + three check families.

HC-01 duplicate-records  — byte-identical lines, duplicated call_ids, and the
                           format's by-design dual-stream recording disclosed.
HC-02 retry-amplification — same-command failure→retry chains (attempts vs
                           logical operations).
HC-03 tool-error-runs     — consecutive same-tool failures.

Verdicts: ok | finding | unprovable | info. A session whose logs cannot decide
a check makes the check UNPROVABLE for that session — never silently ok.
"""
from collections import defaultdict
import os
from typing import Dict, List, Tuple

from .model import (CheckResult, Evidence, Finding, Overview, RetryChain,
                    SessionRecord)

ERROR_RUN_MIN = 3          # consecutive same-tool failures needed for HC-03
MAX_EVIDENCE = 50


def _short(session_id: str) -> str:
    return session_id[:8] if session_id else "?"


def _session_key(s: SessionRecord) -> str:
    return s.session_id or s.path


def _exec_equivalent(a, b) -> bool:
    return (a.source, a.kind, a.exec_id, a.status, a.exit_code, a.cmd_hash,
            a.scope_hash, a.duration) == (b.source, b.kind, b.exec_id, b.status,
            b.exit_code, b.cmd_hash, b.scope_hash, b.duration)


def _canonical_execs(sessions: List[SessionRecord]):
    """Return one copy of each execution id across split/resumed files.

    The rollout format can write a session to more than one file. A repeated
    id with the same envelope is one execution; a repeated id with different
    outcomes is retained once as UNKNOWN so it cannot silently inflate or
    manufacture a success.
    """
    ordered = []
    seen = {}
    duplicates = []
    conflicts = []
    for s in sessions:
        skey = _session_key(s)
        for e in s.execs:
            key = (skey, e.exec_id) if e.exec_id else (skey, e.source, e.file, e.line)
            if key in seen:
                owner, old = seen[key]
                if _exec_equivalent(old, e):
                    duplicates.append((s, e))
                else:
                    old.status = "unknown"
                    old.exit_code = None
                    conflicts.append((s, e))
                continue
            seen[key] = (s, e)
            ordered.append((s, e))
    return ordered, duplicates, conflicts


def _canonical_calls(sessions: List[SessionRecord]):
    ordered = []
    seen = set()
    for s in sessions:
        skey = _session_key(s)
        for c in s.calls:
            key = (skey, c.kind, c.call_id) if c.call_id else (skey, c.kind, c.file, c.line)
            if key in seen:
                continue
            seen.add(key)
            ordered.append((s, c))
    return ordered


def _latest_snapshot(group: List[SessionRecord]):
    # A malformed cumulative snapshot makes the session total undecidable:
    # a later valid snapshot cannot prove what was omitted or reset before it.
    # Fail closed for the whole logical session instead of presenting a
    # partial number as if it were complete.
    if any(s.token_invalid for s in group):
        return None
    thread = [snap for s in group for snap in s.thread_tokens]
    event = [snap for s in group for snap in s.tokens]
    candidates = thread or event
    if not candidates:
        return None
    return max(candidates, key=lambda x: (x.timestamp or "", x.line, x.file))


def build_overview(sessions: List[SessionRecord], window_label: str) -> Overview:
    ov = Overview(window_label=window_label, files=len(sessions))
    ov.sessions = len({s.session_id or s.path for s in sessions})
    for s in sessions:
        ov.lines += s.line_stats.total
        ov.corrupt_lines += s.line_stats.corrupt
        ov.truncated_files += 1 if s.truncated else 0
        ov.unknown_type_lines += sum(s.unknown_types.values())
        if s.started_at and (not ov.first_ts or s.started_at < ov.first_ts):
            ov.first_ts = s.started_at
        if s.last_ts and (not ov.last_ts or s.last_ts > ov.last_ts):
            ov.last_ts = s.last_ts
        for m in s.models:
            if m not in ov.models:
                ov.models.append(m)
        if s.cli_version and s.cli_version not in ov.cli_versions:
            ov.cli_versions.append(s.cli_version)
        ov.turns += s.turns
        ov.compactions += s.compactions
        ov.subagent_activity += s.subagent_activity
        ov.file_changes += s.file_changes
    canonical, _duplicates, _conflicts = _canonical_execs(sessions)
    for _s, e in canonical:
        ov.exec_total += 1
        if e.status == "ok":
            ov.exec_ok += 1
        elif e.status == "failed":
            ov.exec_failed += 1
        else:
            ov.exec_unknown += 1
    ov.call_total = len(_canonical_calls(sessions))
    exec_by_session = {_session_key(s) for s, _e in canonical}
    all_session_keys = {_session_key(s) for s in sessions}
    ov.sessions_without_exec_events = len(all_session_keys - exec_by_session)

    if ov.lines:
        ov.corrupt_ratio = ov.corrupt_lines / ov.lines

    groups: Dict[str, List[SessionRecord]] = defaultdict(list)
    for s in sessions:
        groups[_session_key(s)].append(s)
    token_sessions = 0
    for group in groups.values():
        if any(s.token_invalid for s in group):
            ov.token_invalid_sessions += 1
        snap = _latest_snapshot(group)
        if snap is not None:
            token_sessions += 1
            ov.token_total_input += snap.input_tokens
            ov.token_cached_input += snap.cached_input
            ov.token_output += snap.output_tokens
            ov.token_reasoning_output += snap.reasoning_output
            ov.token_total_reported += snap.total_tokens
        elif not any(s.token_invalid for s in group):
            ov.token_missing_sessions += 1
    # An aggregate is complete only when every logical session contributes one
    # valid cumulative snapshot. Partial sums are useful for debugging but are
    # deliberately labelled UNPROVABLE for accounting.
    ov.token_provable = bool(ov.sessions and token_sessions == ov.sessions)

    chains = all_retry_chains(sessions)
    ov.retry_chains = len(chains)
    ov.retry_attempts_in_chains = sum(c.attempts for c in chains)
    ov.unresolved_chains = sum(1 for c in chains if not c.resolved)

    ov.projects = _project_breakdown(sessions, canonical, chains)
    return ov


def _project_breakdown(sessions, canonical, chains):
    """Per-project aggregates on canonical (deduplicated) executions."""
    project_by_key: Dict[str, str] = {}
    for s in sessions:
        key = _session_key(s)
        if key not in project_by_key or (not project_by_key[key] and s.project):
            project_by_key[key] = s.project or "(unknown)"
    agg: Dict[str, Dict[str, int]] = {}
    for key, project in project_by_key.items():
        entry = agg.setdefault(project, {"sessions": 0, "exec_total": 0,
                                         "exec_failed": 0, "retry_chains": 0})
        entry["sessions"] += 1
    for _s, e in canonical:
        project = project_by_key.get(_session_key(_s), "(unknown)")
        agg[project]["exec_total"] += 1
        if e.status == "failed":
            agg[project]["exec_failed"] += 1
    for c in chains:
        project = project_by_key.get(c.session_id or c.file, "(unknown)")
        if project in agg:
            agg[project]["retry_chains"] += 1
    rows = [{"project": name, **counts} for name, counts in agg.items()]
    rows.sort(key=lambda r: (-r["exec_total"], r["project"]))
    return rows[:8]


def session_summaries(sessions: List[SessionRecord]) -> List[Dict[str, object]]:
    """Canonical per-logical-session rows for snapshots (split files merged)."""
    canonical, _duplicates, _conflicts = _canonical_execs(sessions)
    groups: Dict[str, Dict[str, object]] = {}
    order: List[str] = []
    for s in sessions:
        key = _session_key(s)
        if key not in groups:
            groups[key] = {
                "session": s.session_id[:8] if s.session_id else "?",
                "file": os.path.basename(s.path),
                "project": s.project or "(unknown)",
                "started_at": s.started_at,
                "turns": 0, "exec_total": 0, "exec_failed": 0,
                "retry_chains": 0,
            }
            order.append(key)
        row = groups[key]
        row["turns"] += s.turns
        if not row["started_at"] and s.started_at:
            row["started_at"] = s.started_at
        if s.project and row["project"] == "(unknown)":
            row["project"] = s.project
    for _s, e in canonical:
        row = groups[_session_key(_s)]
        row["exec_total"] += 1
        if e.status == "failed":
            row["exec_failed"] += 1
    for c in all_retry_chains(sessions):
        row = groups.get(c.session_id or c.file)
        if row is not None:
            row["retry_chains"] += 1
    return [groups[key] for key in order]


# ---------------------------------------------------------------- HC-02 core

def retry_chains_for_session(s: SessionRecord) -> List[RetryChain]:
    """Maximal consecutive same-command blocks whose first attempt failed.

    A block of identical commands where the first execution failed and at
    least one more attempt followed is one retry chain = one logical
    operation executed N times.
    """
    chains: List[RetryChain] = []
    block: List = []
    blocks: List[List] = []

    def flush():
        if len(block) >= 2 and block[0].status == "failed":
            blocks.append(list(block))
        block.clear()

    for e in s.execs:
        if e.status == "unknown":
            flush()
            continue
        previous = block[-1] if block else None
        corrupt_gap = (previous is not None and any(previous.line < line < e.line
                                                     for line in s.corrupt_lines))
        file_boundary = previous is not None and previous.file != e.file
        same_scope = (previous is not None and
                      (previous.cmd_hash, previous.scope_hash, previous.kind,
                       previous.source, previous.turn_index) ==
                      (e.cmd_hash, e.scope_hash, e.kind, e.source, e.turn_index))
        if (not block) or corrupt_gap or file_boundary or not same_scope or previous.status == "ok":
            flush()
            block.append(e)
        else:
            block.append(e)
            # A successful retry closes the chain. A later identical command
            # is a separate operation, not an extension of the old one.
            if e.status == "ok":
                flush()
    flush()

    for blk in blocks:
        chains.append(RetryChain(
            session_id=s.session_id, file=s.path,
            cmd_hash=blk[0].cmd_hash, kind=blk[0].kind,
            attempts=len(blk),
            outcomes=[e.status for e in blk],
            first_line=blk[0].line, last_line=blk[-1].line,
            resolved=blk[-1].status == "ok"))
    return chains


def all_retry_chains(sessions: List[SessionRecord]) -> List[RetryChain]:
    canonical, _duplicates, _conflicts = _canonical_execs(sessions)
    grouped: Dict[str, SessionRecord] = {}
    execs_by_session: Dict[str, List] = defaultdict(list)
    for s, e in canonical:
        key = _session_key(s)
        if key not in grouped:
            grouped[key] = SessionRecord(path=s.path, session_id=s.session_id,
                                         corrupt_lines=list(s.corrupt_lines))
        elif s.corrupt_lines:
            grouped[key].corrupt_lines.extend(s.corrupt_lines)
        execs_by_session[key].append(e)
    out: List[RetryChain] = []
    for key, execs in execs_by_session.items():
        grouped[key].execs = execs
        out.extend(retry_chains_for_session(grouped[key]))
    return out


def check_duplicate_records(sessions: List[SessionRecord]) -> CheckResult:
    res = CheckResult(check_id="HC-01", name="Duplicate records")
    dup_lines = sum(len(s.dup_lines) for s in sessions)
    dup_calls = sum(len(s.dup_call_ids) for s in sessions)
    _canonical, dup_execs, conflict_execs = _canonical_execs(sessions)

    by_session: Dict[str, int] = defaultdict(int)
    for s in sessions:
        by_session[s.session_id or s.path] += 1
    repeated_sessions = {sid: n for sid, n in by_session.items() if n > 1}

    if dup_lines:
        f = Finding(
            title="%d byte-identical duplicate line(s) inside session files" % dup_lines,
            severity="finding",
            explanation="The same JSON record appears twice. Any metric that "
                        "counts lines or events will count these twice.",
            next_step="Check whether the duplicated lines are re-writes after a crash "
                      "or a resume; if they are genuine re-emissions, deduplicate on "
                      "record id before counting anything.")
        for s in sessions:
            for line, _n in s.dup_lines[:MAX_EVIDENCE]:
                f.add(Evidence(session=_short(s.session_id), file=s.path, line=line,
                               detail={"kind": "identical line"}))
        res.findings.append(f)
    if dup_execs:
        f = Finding(
            title="%d execution id(s) repeated across split files" % len(dup_execs),
            severity="finding",
            explanation="The same session and execution id appeared in more than one "
                        "file with the same envelope. It is counted once in the "
                        "overview, otherwise resumed sessions would inflate totals.",
            next_step="Keep the execution id as the deduplication key and retain the "
                      "file split only as provenance.")
        for s, e in dup_execs[:MAX_EVIDENCE]:
            f.add(Evidence(session=_short(s.session_id), file=s.path, line=e.line,
                           detail={"execution_id_present": bool(e.exec_id)}))
        res.findings.append(f)
    if conflict_execs:
        f = Finding(
            title="%d execution id conflict(s) were fail-closed" % len(conflict_execs),
            severity="finding",
            explanation="One execution id appeared with different command or outcome "
                        "fields. The canonical record is UNKNOWN instead of choosing "
                        "a success or failure arbitrarily.",
            next_step="Inspect the runtime writer around the conflicting lines before "
                      "using the affected session for accounting.")
        for s, e in conflict_execs[:MAX_EVIDENCE]:
            f.add(Evidence(session=_short(s.session_id), file=s.path, line=e.line,
                           detail={"execution_id_present": bool(e.exec_id)}))
        res.findings.append(f)
    if dup_calls:
        f = Finding(
            title="%d call_id(s) recorded more than once" % dup_calls,
            severity="finding",
            explanation="A tool call id should identify one call; repeats break "
                        "attempt counting.",
            next_step="Inspect the evidence lines; treat the first occurrence as the "
                      "call and later ones as duplicates unless the runtime documents "
                      "otherwise.")
        for s in sessions:
            for cid, n in list(s.dup_call_ids.items())[:MAX_EVIDENCE]:
                lines = s.dup_call_lines.get(cid, [])
                f.add(Evidence(session=_short(s.session_id), file=s.path,
                               line=(lines[1] if len(lines) > 1 else (lines[0] if lines else 0)),
                               detail={"call_id": cid, "count": n,
                                       "lines": lines[:20]}))
        res.findings.append(f)
    if repeated_sessions:
        f = Finding(
            title="%d session id(s) appear in more than one file" % len(repeated_sessions),
            severity="info",
            explanation="Codex forks/resumes can write the same session id to a new "
                        "file. Counting files would over-count sessions; counting "
                        "unique ids would under-count runs.",
            next_step="For session counts use unique ids, and keep the file split "
                      "visible (this report does).")
        for sid, n in list(repeated_sessions.items())[:MAX_EVIDENCE]:
            f.add(Evidence(session=_short(sid), file="", line=0, detail={"files": n}))
        res.findings.append(f)

    exec_events = sum(1 for _s, e in _canonical if e.source == "exec")
    call_events = len(_canonical_calls(sessions))
    if exec_events and call_events:
        ratio = exec_events / max(1, call_events)
        f = Finding(
            title="Format records executions twice: %d model-side calls vs %d command events"
                  % (call_events, exec_events),
            severity="info",
            explanation="Codex writes tool calls as response_item records AND as "
                        "item_completed events. This is by design, but any tool that "
                        "sums both streams (or greps the file for command names) "
                        "double-counts executions. Ratio here: %.2fx." % ratio,
            next_step="Count executions from exactly one stream. This tool uses the "
                      "item_completed stream (it carries exit codes).")
        res.findings.append(f)

    res.status = "finding" if any(fl.severity == "finding" for fl in res.findings) else (
        "info" if res.findings else "ok")
    res.evidence_count = sum(len(fl.evidence) for fl in res.findings)
    res.summary = ("identical lines: %d; repeated call_ids: %d; repeated execution ids: %d; "
                   "conflicting execution ids: %d; multi-file sessions: %d"
                   % (dup_lines, dup_calls, len(dup_execs), len(conflict_execs),
                      len(repeated_sessions)))
    return res


def check_retry_amplification(sessions: List[SessionRecord]) -> CheckResult:
    res = CheckResult(check_id="HC-02", name="Retry amplification")
    chains = all_retry_chains(sessions)
    canonical, _duplicates, _conflicts = _canonical_execs(sessions)

    all_session_keys = {_session_key(s) for s in sessions}
    exec_session_keys = {_session_key(s) for s, _e in canonical}
    no_exec_sessions = all_session_keys - exec_session_keys
    if no_exec_sessions:
        res.unprovable_reason = (
            "%d session(s) have no command events with outcomes; "
            "their retry behaviour cannot be decided from these logs."
            % len(no_exec_sessions))
    corrupt_sessions = [s for s in sessions if s.corrupt_lines]
    if corrupt_sessions:
        reason = ("%d session(s) contain corrupt lines between or around execution "
                  "events; retry chains crossing the gap are not decidable."
                  % len(corrupt_sessions))
        res.unprovable_reason = (res.unprovable_reason + " " + reason).strip()
    unknown_execs = sum(1 for _s, e in canonical if e.status == "unknown")
    if unknown_execs:
        reason = ("%d execution(s) have no decidable outcome; retry boundaries "
                  "around them are UNKNOWN." % unknown_execs)
        res.unprovable_reason = (res.unprovable_reason + " " + reason).strip()

    if chains:
        attempts = sum(c.attempts for c in chains)
        resolved = sum(1 for c in chains if c.resolved)
        f = Finding(
            title="%d retry chain(s): %d executions carry %d logical operation(s)"
                  % (len(chains), attempts, len(chains)),
            severity="finding",
            explanation="Each chain is one command that failed and was re-run. "
                        "%d chain(s) eventually succeeded; %d ended unresolved. "
                        "Amplification: %.2f executions per logical operation."
                        % (resolved, len(chains) - resolved, attempts / len(chains)),
            next_step="Open the worst chain below: repeated failures of the same "
                      "command usually mean a flaky check, a wrong path, or a task "
                      "the agent could not finish — worth fixing once instead of "
                      "paying the retries every run.")
        for c in sorted(chains, key=lambda c: -c.attempts)[:MAX_EVIDENCE]:
            f.add(Evidence(session=_short(c.session_id), file=c.file, line=c.first_line,
                           detail={"command_hash": c.cmd_hash, "tool": c.kind,
                                   "attempts": c.attempts,
                                   "outcomes": "→".join(c.outcomes),
                                   "exit_codes": True,
                                   "lines": "%d–%d" % (c.first_line, c.last_line),
                                   "resolved": c.resolved}))
        res.findings.append(f)
        res.status = "finding"
    elif res.unprovable_reason:
        res.status = "unprovable"
    else:
        res.status = "ok"

    res.evidence_count = sum(len(fl.evidence) for fl in res.findings)
    res.summary = ("chains: %d; attempts inside chains: %d; unresolved: %d"
                   % (len(chains), sum(c.attempts for c in chains),
                      sum(1 for c in chains if not c.resolved)))
    return res


def check_tool_error_runs(sessions: List[SessionRecord]) -> CheckResult:
    res = CheckResult(check_id="HC-03", name="Tool error runs")
    runs: List[Tuple[SessionRecord, List]] = []

    canonical, _duplicates, _conflicts = _canonical_execs(sessions)
    grouped: Dict[str, SessionRecord] = {}
    for s, e in canonical:
        key = _session_key(s)
        if key not in grouped:
            grouped[key] = SessionRecord(path=s.path, session_id=s.session_id,
                                         corrupt_lines=list(s.corrupt_lines))
        grouped[key].execs.append(e)
    for s in grouped.values():
        current: List = []
        runs_local: List[List] = []
        for e in s.execs:
            if e.status == "failed" and e.kind:
                previous = current[-1] if current else None
                corrupt_gap = (previous is not None and any(previous.line < line < e.line
                                                             for line in s.corrupt_lines))
                same_file = previous is None or previous.file == e.file
                if (current and same_file and not corrupt_gap and
                        current[0].kind == e.kind and current[0].source == e.source):
                    current.append(e)
                else:
                    if len(current) >= ERROR_RUN_MIN:
                        runs_local.append(list(current))
                    current = [e]
            else:
                if len(current) >= ERROR_RUN_MIN:
                    runs_local.append(list(current))
                current = []
        if len(current) >= ERROR_RUN_MIN:
            runs_local.append(list(current))
        for r in runs_local:
            runs.append((s, r))

    all_session_keys = {_session_key(s) for s in sessions}
    exec_session_keys = {_session_key(s) for s, _e in canonical}
    no_exec_sessions = all_session_keys - exec_session_keys
    corrupt_sessions = [s for s in sessions if s.corrupt_lines]
    if no_exec_sessions:
        res.unprovable_reason = (
            "%d session(s) have no command events with outcomes; error runs there "
            "cannot be checked." % len(no_exec_sessions))
    if corrupt_sessions:
        reason = ("%d session(s) contain corrupt lines; a complete consecutive error "
                  "run cannot be proven across those gaps." % len(corrupt_sessions))
        res.unprovable_reason = (res.unprovable_reason + " " + reason).strip()
    unknown_execs = sum(1 for _s, e in canonical if e.status == "unknown")
    if unknown_execs:
        reason = ("%d execution(s) have no decidable outcome; a complete error run "
                  "cannot be proven around them." % unknown_execs)
        res.unprovable_reason = (res.unprovable_reason + " " + reason).strip()

    if runs:
        f = Finding(
            title="%d run(s) of ≥%d consecutive failures of the same tool"
                  % (len(runs), ERROR_RUN_MIN),
            severity="finding",
            explanation="The agent kept hitting the same tool failure back-to-back "
                        "without a success in between. These are the most expensive "
                        "failure modes: each attempt costs a model turn plus the tool "
                        "run, and none of them moved the task forward.",
            next_step="Take the longest run and read its first error: usually a "
                      "missing dependency, a wrong working directory, or an "
                      "authentication problem the agent could not self-heal.")
        for s, r in sorted(runs, key=lambda sr: -len(sr[1]))[:MAX_EVIDENCE]:
            f.add(Evidence(session=_short(s.session_id), file=s.path, line=r[0].line,
                           detail={"tool": r[0].kind, "failures": len(r),
                                   "exit_codes": [e.exit_code for e in r],
                                   "lines": "%d–%d" % (r[0].line, r[-1].line)}))
        res.findings.append(f)
        res.status = "finding"
    elif res.unprovable_reason:
        res.status = "unprovable"
    else:
        res.status = "ok"

    res.evidence_count = sum(len(fl.evidence) for fl in res.findings)
    failed = sum(1 for _s, e in canonical if e.status == "failed")
    res.summary = ("failed executions: %d; same-tool runs ≥%d: %d"
                   % (failed, ERROR_RUN_MIN, len(runs)))
    return res


def coverage_findings(ov: Overview) -> List[Finding]:
    out: List[Finding] = []
    if ov.truncated_files:
        out.append(Finding(
            title="%d file(s) exceeded the read cap" % ov.truncated_files,
            severity="finding",
            explanation="The adapter stopped reading at its per-file safety cap. "
                        "All metrics for those files are lower bounds.",
            next_step="Split the runtime log or raise the cap only after reviewing "
                      "the memory and privacy implications."))
    if ov.corrupt_ratio >= 0.01:
        out.append(Finding(
            title="%.1f%% of log lines could not be parsed" % (ov.corrupt_ratio * 100),
            severity="finding",
            explanation="%d of %d lines are not valid JSON objects. Metrics computed "
                        "from these files are lower bounds for those lines."
                        % (ov.corrupt_lines, ov.lines),
            next_step="If the corrupt lines cluster in one file, that file may be a "
                      "crashed or in-flight session — exclude it and re-run.",
            evidence=[Evidence(session="*", file="", line=0, detail={})]))
    if ov.token_invalid_sessions:
        out.append(Finding(
            title="%d session(s) contain invalid or incomplete token snapshots"
                  % ov.token_invalid_sessions,
            severity="finding",
            explanation="At least one cumulative token record in these sessions "
                        "was missing counters or had invalid subset values. Token "
                        "totals are UNPROVABLE for the affected sessions, even if "
                        "another snapshot in the same session was valid.",
            next_step="Use a newer runtime format or inspect the raw token event "
                      "before using token totals for accounting."))
    if ov.token_missing_sessions:
        out.append(Finding(
            title="%d session(s) have no valid token snapshot" % ov.token_missing_sessions,
            severity="finding",
            explanation="The aggregate token number would omit these sessions, so it "
                        "is not a complete total even when other sessions have valid "
                        "cumulative records.",
            next_step="Use a wider window or a runtime export that includes one "
                      "cumulative token snapshot per session."))
    if (not ov.token_provable and ov.sessions and not ov.token_invalid_sessions and
            not ov.token_missing_sessions):
        out.append(Finding(
            title="Token usage not provable from these logs",
            severity="info",
            explanation="No token_count / token_usage_record events in the window. "
                        "Consumption stays UNPROVABLE rather than zero.",
            next_step="If the runtime normally emits token events, the window may "
                      "predate a format change — try --all."))
    if ov.compactions:
        out.append(Finding(
            title="%d context compaction event(s)" % ov.compactions,
            severity="info",
            explanation="Compaction resets the context; token counts before and "
                        "after a compaction are not comparable, and cached-input "
                        "savings are lost at each reset.",
            next_step="Nothing to fix — keep it in mind when comparing token "
                      "totals across long sessions."))
    return out


def run_checks(sessions: List[SessionRecord], window_label: str):
    ov = build_overview(sessions, window_label)
    checks = [
        check_duplicate_records(sessions),
        check_retry_amplification(sessions),
        check_tool_error_runs(sessions),
    ]
    coverage = coverage_findings(ov)

    ranked = []
    for c in checks:
        for f in c.findings:
            if f.severity == "finding":
                ranked.append((c.check_id, f))
    for f in coverage:
        ranked.append(("COV", f))
    top3 = [f for _cid, f in ranked[:3]]
    return ov, checks, coverage, top3
