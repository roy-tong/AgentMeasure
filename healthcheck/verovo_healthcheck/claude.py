"""Claude Code session JSONL adapter — defensive parsing with format feature detection.

Observed format envelope (Claude Code 1.x–2.x, ~/.claude/projects/<munged-cwd>/*.jsonl):

  {"type": "user"|"assistant"|"system"|"summary", "sessionId": "...", "cwd": "...",
   "timestamp": "...", "message": {...}, "isSidechain": false, "toolUseResult": ...}

Key message shapes:
  user       message.content = str | [ {type:"text"...} | {type:"tool_result",
             tool_use_id, content, is_error} ]
  assistant  message.model, message.content = [ {type:"text"} |
             {type:"tool_use", id, name, input} ], message.usage = per-request
             {input_tokens, output_tokens, cache_read_input_tokens,
              cache_creation_input_tokens}

Mapping decisions (grain discipline, mirrors standard/CORE.md):
- a tool_use block is one recorded execution (an Attempt); a tool_result with the
  same tool_use_id decides its outcome (is_error → failed, else ok); a missing
  result leaves status unknown — disclosed, never guessed;
- usage is PER-REQUEST (each assistant message is one API call; input includes
  the repeated context). Claude transcripts carry no session-cumulative counter,
  so nothing is written to tokens/thread_tokens: cumulative token accounting is
  UNPROVABLE by surface here, and per-request sums are deliberately not
  presented as session totals (the exact over-count HC audits elsewhere);
- byte-identical lines are deduplicated: Claude resume/fork rewrites prior turns
  into a new file, and an interrupted writer can re-emit lines.

Parsing rules:
- never raise on a bad line: account it corrupt and continue;
- every field access is defensive; missing fields become "" / None / 0;
- token subsets (cache_read/cache_creation) are recorded in anomalies count only.
"""
import hashlib
import os
from typing import Dict, List, Optional, Set

from .jsonl import iter_lines, parse_ts
from .model import CallRecord, ExecRecord, SessionRecord, TokenSnapshot

PER_FILE_LIMIT_BYTES = 400 * 1024 * 1024  # defensive cap; largest local sample ~60MB

FILE_EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}


def _clean_str(value) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return text.encode("utf-8", "replace").decode("utf-8")


def _hash_command(command) -> str:
    norm = command if isinstance(command, str) else __import__("json").dumps(
        command, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(norm.encode("utf-8", "replace")).hexdigest()[:12]


def _hash_value(value) -> str:
    try:
        norm = __import__("json").dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        norm = repr(value)
    return hashlib.sha256(norm.encode("utf-8", "replace")).hexdigest()[:12]


def _command_first_token(command) -> str:
    if isinstance(command, str) and command.strip():
        return _clean_str(command.split()[0])
    if isinstance(command, (list, tuple)):
        parts = [str(x) for x in command if x]
        return _clean_str(parts[0]) if parts else ""
    return ""


def _blocks(content) -> List[dict]:
    """message.content may be a plain string or a list of content blocks."""
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _project_from_cwd(cwd) -> str:
    if not isinstance(cwd, str) or not cwd.strip():
        return ""
    text = _clean_str(cwd.strip().rstrip("/\\"))
    return _clean_str(os.path.basename(text))[:80]


def parse_session(path: str, file_index: int = 0) -> SessionRecord:
    """Parse one Claude Code session file into a SessionRecord. Never raises on data."""
    rec = SessionRecord(path=path)
    stats = rec.line_stats
    seen_raw: Set[str] = set()
    exec_by_tool_use: Dict[str, ExecRecord] = {}
    call_by_tool_use: Dict[str, CallRecord] = {}
    last_ts = ""
    per_request_usage_events = 0

    try:
        if PER_FILE_LIMIT_BYTES and os.path.getsize(path) > PER_FILE_LIMIT_BYTES:
            rec.truncated = True
            rec.anomalies.append(
                "file exceeds the %d-byte read cap; counts are lower bounds" % PER_FILE_LIMIT_BYTES)
    except OSError:
        pass

    for lineno, obj, raw in iter_lines(path, limit_bytes=PER_FILE_LIMIT_BYTES):
        stats.total += 1
        if obj is None:
            if raw.strip():
                stats.corrupt += 1
                rec.corrupt_lines.append(lineno)
            else:
                stats.blank += 1
            continue
        stripped = raw.strip()
        if stripped:
            digest = hashlib.sha256(stripped.encode("utf-8", "replace")).hexdigest()
            if digest in seen_raw:
                rec.dup_lines.append([lineno, 2])
                # resume/fork rewrites and interrupted writers re-emit lines;
                # counting a byte-identical line twice inflates everything downstream
                stats.parsed += 1
                continue
            seen_raw.add(digest)
        stats.parsed += 1

        ts = parse_ts(obj.get("timestamp"))
        if ts:
            last_ts = ts
            if not rec.started_at:
                rec.started_at = ts

        if not rec.session_id:
            sid = obj.get("sessionId")
            if isinstance(sid, str) and sid:
                rec.session_id = _clean_str(sid)
        if not rec.project:
            rec.project = _project_from_cwd(obj.get("cwd"))

        etype = obj.get("type")
        if not isinstance(etype, str):
            stats.corrupt += 1
            stats.parsed -= 1
            rec.corrupt_lines.append(lineno)
            continue

        if obj.get("isSidechain") is True:
            rec.subagent_activity += 1

        if etype == "summary":
            continue  # known type: index line, carries no measurement facts

        if etype == "system":
            subtype = obj.get("subtype") or obj.get("subType") or ""
            if "compact" in str(subtype).lower() or obj.get("isCompactSummary") is True:
                rec.compactions += 1
            else:
                rec.unknown_types["system/" + _clean_str(subtype)[:24]] = \
                    rec.unknown_types.get("system/" + _clean_str(subtype)[:24], 0) + 1
            continue

        message = obj.get("message")
        if message is None and etype in ("user", "assistant"):
            message = {}
        if not isinstance(message, dict):
            if etype in ("user", "assistant"):
                rec.unknown_types[etype + "/no-message"] = \
                    rec.unknown_types.get(etype + "/no-message", 0) + 1
            else:
                rec.unknown_types[etype] = rec.unknown_types.get(etype, 0) + 1
            continue

        content = message.get("content")

        if etype == "user":
            blocks = _blocks(content)
            has_text = isinstance(content, str) and content.strip() or any(
                b.get("type") == "text" for b in blocks)
            only_tool_results = bool(blocks) and all(
                b.get("type") == "tool_result" for b in blocks)
            if has_text and not only_tool_results:
                rec.turns += 1
            for b in blocks:
                if b.get("type") != "tool_result":
                    continue
                tuid = _clean_str(b.get("tool_use_id") or "")
                if not tuid:
                    continue
                ex = exec_by_tool_use.get(tuid)
                if ex is not None:
                    ex.status = "failed" if b.get("is_error") is True else "ok"
                call = call_by_tool_use.get(tuid)
                if call is not None:
                    call.has_output = True
                    call.output_line = lineno
            continue

        if etype == "assistant":
            model = message.get("model")
            if isinstance(model, str) and model:
                model = _clean_str(model)
                if model not in rec.models:
                    rec.models.append(model)
            usage = message.get("usage")
            if isinstance(usage, dict) and usage:
                per_request_usage_events += 1
            for b in _blocks(content):
                btype = b.get("type")
                if btype == "tool_use":
                    tuid = _clean_str(b.get("id") or "")
                    name = _clean_str(b.get("name") or "")
                    tool_input = b.get("input")
                    call = CallRecord(
                        session_id=rec.session_id, file=path, line=lineno,
                        call_id=tuid, name=name, kind="claude_tool",
                        has_output=False, output_line=None)
                    rec.calls.append(call)
                    if tuid:
                        call_by_tool_use[tuid] = call
                    if name in FILE_EDIT_TOOLS:
                        rec.file_changes += 1
                    if name == "Bash" and isinstance(tool_input, dict):
                        command = tool_input.get("command")
                        ex = ExecRecord(
                            session_id=rec.session_id, file=path, line=lineno,
                            source="exec", kind=_command_first_token(command),
                            exec_id=tuid, status="unknown", exit_code=None,
                            duration=None, cmd_hash=_hash_command(command),
                            started_at=ts,
                            scope_hash=_hash_value(tool_input.get("cwd"))
                            if tool_input.get("cwd") is not None else "",
                            turn_index=rec.turns)
                    elif name.startswith("mcp__") and len(name) > 5:
                        parts = name.split("__", 2)
                        server = parts[1] if len(parts) > 2 else parts[1]
                        tool = parts[2] if len(parts) > 2 else ""
                        ex = ExecRecord(
                            session_id=rec.session_id, file=path, line=lineno,
                            source="mcp",
                            kind=("mcp:%s/%s" % (server, tool)) if tool else ("mcp:%s" % server),
                            exec_id=tuid, status="unknown", exit_code=None,
                            duration=None,
                            cmd_hash=_hash_command([name, tool_input]),
                            started_at=ts,
                            scope_hash=_hash_value(tool_input)
                            if tool_input is not None else "",
                            turn_index=rec.turns)
                    else:
                        ex = ExecRecord(
                            session_id=rec.session_id, file=path, line=lineno,
                            source="tool", kind=name or "(unnamed)",
                            exec_id=tuid, status="unknown", exit_code=None,
                            duration=None,
                            cmd_hash=_hash_command([name, tool_input]),
                            started_at=ts, scope_hash="",
                            turn_index=rec.turns)
                    rec.execs.append(ex)
                    if tuid:
                        exec_by_tool_use[tuid] = ex
            continue

        rec.unknown_types[etype] = rec.unknown_types.get(etype, 0) + 1

    rec.last_ts = last_ts
    if not rec.session_id:
        rec.session_id = os.path.splitext(os.path.basename(path))[0]
        rec.anomalies.append("no sessionId record; derived id from filename")
    if per_request_usage_events:
        rec.anomalies.append(
            "%d per-request usage record(s); Claude transcripts carry no cumulative "
            "counter — session token accounting is UNPROVABLE by surface" %
            per_request_usage_events)
    call_counts: Dict[str, int] = {}
    call_lines: Dict[str, List[int]] = {}
    for call in rec.calls:
        if call.call_id:
            call_counts[call.call_id] = call_counts.get(call.call_id, 0) + 1
            call_lines.setdefault(call.call_id, []).append(call.line)
    rec.dup_call_ids = {cid: n for cid, n in call_counts.items() if n > 1}
    rec.dup_call_lines = {cid: call_lines.get(cid, []) for cid in rec.dup_call_ids}
    return rec


def parse_files(paths: List[str]) -> List[SessionRecord]:
    return [parse_session(p, i) for i, p in enumerate(paths)]
