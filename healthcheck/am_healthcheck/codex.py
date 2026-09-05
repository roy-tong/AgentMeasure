"""Codex rollout JSONL adapter — defensive parsing with format feature detection.

Observed format envelope (cli 0.142–0.153, verified against local samples):

  {"timestamp": "...", "type": "session_meta"|"turn_context"|"response_item"|
   "event_msg"|"token_usage_record"|"compacted"|"world_state"|
   "inter_agent_communication_metadata", "payload": {...}}

Key payloads:
  response_item.function_call           {name, arguments, call_id}
  response_item.function_call_output    {call_id, output}   (Desktop: plain text,
                                        often without exit codes)
  response_item.custom_tool_call        {name, input, call_id, status}
  event_msg.token_count                 {info: {total_token_usage, last_token_usage}}
  event_msg.item_completed              {item: {type: "CommandExecution", exit_code,
                                        duration, status, command, ...}}
                                        — the second, UI-side recording of the same
                                        executions; naive counting double-counts.

Parsing rules:
- never raise on a bad line: account it corrupt and continue;
- every field access is defensive; missing fields become "" / None / 0;
- token subsets (cached_input, reasoning_output) are stored but never summed.
"""
import hashlib
import json
import math
import os
from typing import Dict, List, Optional, Set, Tuple

from .jsonl import iter_lines, parse_ts
from .model import CallRecord, ExecRecord, LineStats, SessionRecord, TokenSnapshot

PER_FILE_LIMIT_BYTES = 400 * 1024 * 1024  # defensive cap; largest local sample ~10MB


def _clean_str(value) -> str:
    """Return a UTF-8-safe string for reports and machine-readable exports."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return text.encode("utf-8", "replace").decode("utf-8")


def _hash_command(command) -> str:
    if isinstance(command, (list, tuple)):
        # MCP arguments can be dictionaries. Canonical JSON prevents key
        # insertion order from making two semantically identical retries look
        # like different commands.
        norm = json.dumps(list(command), sort_keys=True, separators=(",", ":"),
                          default=str)
    elif isinstance(command, str):
        norm = command
    else:
        norm = json.dumps(command, sort_keys=True, default=str)
    return hashlib.sha256(norm.encode("utf-8", "replace")).hexdigest()[:12]


def _hash_value(value) -> str:
    """Hash a scope or argument envelope without retaining user content."""
    try:
        norm = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        norm = repr(value)
    return hashlib.sha256(norm.encode("utf-8", "replace")).hexdigest()[:12]


def _command_first_token(command) -> str:
    if isinstance(command, (list, tuple)):
        parts = [str(x) for x in command if x]
        return _clean_str(parts[0]) if parts else ""
    if isinstance(command, str):
        parts = command.split()
        return _clean_str(parts[0]) if parts else ""
    return _clean_str(type(command).__name__)


def _num(value) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _float(value) -> Optional[float]:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _usage_snapshot(path: str, line: int, timestamp: str, usage) -> Optional[TokenSnapshot]:
    """Build a token snapshot only when its cumulative counters are complete."""
    if not isinstance(usage, dict):
        return None
    required = ("input_tokens", "output_tokens", "total_tokens")
    if any(_num(usage.get(key)) is None or _num(usage.get(key)) < 0 for key in required):
        return None
    input_tokens = _num(usage.get("input_tokens")) or 0
    output_tokens = _num(usage.get("output_tokens")) or 0
    cached_input = _num(usage.get("cached_input_tokens")) or 0
    reasoning_output = _num(usage.get("reasoning_output_tokens")) or 0
    optional = ("cached_input_tokens", "cache_write_input_tokens",
                "reasoning_output_tokens")
    if any(key in usage and
           (_num(usage.get(key)) is None or _num(usage.get(key)) < 0)
           for key in optional):
        return None
    if cached_input > input_tokens or reasoning_output > output_tokens:
        return None
    return TokenSnapshot(
        file=path, line=line, timestamp=timestamp,
        input_tokens=input_tokens,
        cached_input=cached_input,
        cache_write_input=_num(usage.get("cache_write_input_tokens")) or 0,
        output_tokens=output_tokens,
        reasoning_output=reasoning_output,
        total_tokens=_num(usage.get("total_tokens")) or 0)


def _exec_fingerprint(item: dict) -> Tuple[object, ...]:
    """Fields that should remain stable for one execution id."""
    return (item.get("type"), item.get("command"), item.get("cwd"),
            item.get("server"), item.get("tool"), item.get("arguments"),
            item.get("exit_code"), item.get("status"), item.get("duration"))


def parse_session(path: str, file_index: int = 0) -> SessionRecord:
    """Parse one rollout file into a SessionRecord. Never raises on data."""
    rec = SessionRecord(path=path)
    stats = rec.line_stats
    seen_call_lines: Dict[str, int] = {}
    seen_raw: Set[str] = set()
    seen_exec_ids: Dict[str, Tuple[object, ...]] = {}
    duplicate_call_occurrences: Dict[str, List[int]] = {}
    last_ts = ""
    current_turn = 0

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
                duplicate_payload = obj.get("payload")
                if (obj.get("type") == "response_item" and
                        isinstance(duplicate_payload, dict) and
                        duplicate_payload.get("type") in ("function_call", "custom_tool_call")):
                    duplicate_id = duplicate_payload.get("call_id")
                    if duplicate_id:
                        duplicate_call_occurrences.setdefault(_clean_str(duplicate_id), []).append(lineno)
                # Keep the line in coverage, but do not process a byte-identical
                # event a second time. Otherwise an interrupted writer can
                # inflate executions, tokens, and turns.
                stats.parsed += 1
                continue
            else:
                seen_raw.add(digest)
        stats.parsed += 1

        ts = parse_ts(obj.get("timestamp"))
        if ts:
            last_ts = ts
            if not rec.started_at:
                rec.started_at = ts

        etype = obj.get("type")
        if not isinstance(etype, str):
            stats.corrupt += 1
            stats.parsed -= 1
            rec.corrupt_lines.append(lineno)
            continue
        payload = obj.get("payload")
        if payload is None and etype not in ("compacted", "world_state"):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}

        if etype == "session_meta":
            sid = payload.get("id") or payload.get("session_id") or ""
            rec.session_id = _clean_str(sid)
            ver = payload.get("cli_version")
            rec.cli_version = _clean_str(ver)
            origin = payload.get("originator")
            rec.originator = _clean_str(origin)

        elif etype == "turn_context":
            model = payload.get("model")
            if isinstance(model, str):
                model = _clean_str(model)
                if model and model not in rec.models:
                    rec.models.append(model)

        elif etype == "response_item":
            ptype = payload.get("type")
            if ptype == "function_call":
                call_id = _clean_str(payload.get("call_id") or "")
                name = _clean_str(payload.get("name") or "")
                line = seen_call_lines.get("f:" + call_id)
                rec.calls.append(CallRecord(
                    session_id=rec.session_id, file=path, line=lineno,
                    call_id=_clean_str(call_id), name=_clean_str(name), kind="function",
                    has_output=line is not None,
                    output_line=line))
            elif ptype == "function_call_output":
                call_id = _clean_str(payload.get("call_id") or "")
                key = "f:" + call_id
                if key not in seen_call_lines:
                    seen_call_lines[key] = lineno
                for call in reversed(rec.calls):
                    if call.kind == "function" and call.call_id == _clean_str(call_id):
                        call.has_output = True
                        call.output_line = lineno
                        break
            elif ptype == "custom_tool_call":
                call_id = _clean_str(payload.get("call_id") or "")
                name = _clean_str(payload.get("name") or "")
                line = seen_call_lines.get("c:" + call_id)
                rec.calls.append(CallRecord(
                    session_id=rec.session_id, file=path, line=lineno,
                    call_id=_clean_str(call_id), name=_clean_str(name), kind="custom",
                    has_output=line is not None,
                    output_line=line))
            elif ptype == "custom_tool_call_output":
                call_id = _clean_str(payload.get("call_id") or "")
                key = "c:" + call_id
                if key not in seen_call_lines:
                    seen_call_lines[key] = lineno
                for call in reversed(rec.calls):
                    if call.kind == "custom" and call.call_id == _clean_str(call_id):
                        call.has_output = True
                        call.output_line = lineno
                        break
            elif ptype == "spawn_agent" or "spawn_agent" in str(payload.get("name", "")):
                rec.subagent_activity += 1
            # message / reasoning carry content — deliberately not stored.

        elif etype == "event_msg":
            ptype = payload.get("type")
            if ptype == "token_count":
                info = payload.get("info") or {}
                if not isinstance(info, dict):
                    rec.token_invalid = True
                    rec.anomalies.append("token_count info is not an object at line %d" % lineno)
                else:
                    total_usage = info.get("total_token_usage") or {}
                    snap = _usage_snapshot(path, lineno, ts, total_usage)
                    if snap is not None:
                        rec.tokens.append(snap)
                    else:
                        rec.token_invalid = True
                    if snap is None:
                        rec.anomalies.append(
                            "incomplete or invalid cumulative token counters at line %d" % lineno)
            elif ptype == "item_completed":
                item = payload.get("item") or {}
                if not isinstance(item, dict):
                    continue
                itype = item.get("type")
                if itype == "CommandExecution":
                    key = _clean_str(item.get("id") or "")
                    fp = _exec_fingerprint(item)
                    if key and key in seen_exec_ids:
                        if seen_exec_ids[key] == fp:
                            rec.anomalies.append("duplicate execution id %s at line %d" % (key, lineno))
                            continue
                        for old in reversed(rec.execs):
                            if old.exec_id == key:
                                old.status = "unknown"
                                old.exit_code = None
                                break
                        rec.anomalies.append("conflicting execution id %s at line %d" % (key, lineno))
                        continue
                    if key:
                        seen_exec_ids[key] = fp
                    rec.execs.append(_exec_from_command(rec.session_id, path, lineno, item,
                                                        current_turn))
                elif itype == "McpToolCall":
                    key = _clean_str(item.get("id") or "")
                    fp = _exec_fingerprint(item)
                    if key and key in seen_exec_ids:
                        if seen_exec_ids[key] == fp:
                            rec.anomalies.append("duplicate execution id %s at line %d" % (key, lineno))
                            continue
                        for old in reversed(rec.execs):
                            if old.exec_id == key:
                                old.status = "unknown"
                                old.exit_code = None
                                break
                        rec.anomalies.append("conflicting execution id %s at line %d" % (key, lineno))
                        continue
                    if key:
                        seen_exec_ids[key] = fp
                    rec.execs.append(_exec_from_mcp(rec.session_id, path, lineno, item,
                                                    current_turn, ts))
                elif itype == "FileChange":
                    rec.file_changes += 1
                elif itype == "SubAgentActivity":
                    rec.subagent_activity += 1
                elif itype == "ContextCompaction":
                    rec.compactions += 1
            elif ptype in ("task_started",):
                rec.turns += 1
                current_turn += 1
            elif ptype == "turn_aborted":
                rec.turns = max(0, rec.turns)  # aborted turn still counted as started

        elif etype == "token_usage_record":
            # thread_token_usage is the cumulative view. `usage` is often the
            # per-turn view and must not replace the thread total when both exist.
            if "thread_token_usage" in payload:
                usage = payload.get("thread_token_usage")
            elif "usage" in payload:
                usage = payload.get("usage")
            elif "turn_token_usage" in payload:
                usage = payload.get("turn_token_usage")
            else:
                usage = {}
            snap = _usage_snapshot(path, lineno, ts, usage)
            if snap is not None:
                rec.thread_tokens.append(snap)
            else:
                rec.token_invalid = True
            if snap is None:
                rec.anomalies.append(
                    "incomplete or invalid cumulative token counters at line %d" % lineno)

        elif etype == "compacted":
            rec.compactions += 1

        else:
            rec.unknown_types[etype] = rec.unknown_types.get(etype, 0) + 1

    rec.last_ts = last_ts
    if not rec.session_id:
        rec.anomalies.append("no session_meta record; session id unavailable")
    call_counts: Dict[str, int] = {}
    call_lines: Dict[str, List[int]] = {}
    for call in rec.calls:
        if call.call_id:
            call_counts[call.call_id] = call_counts.get(call.call_id, 0) + 1
            call_lines.setdefault(call.call_id, []).append(call.line)
    for call_id, lines in duplicate_call_occurrences.items():
        call_counts[call_id] = call_counts.get(call_id, 0) + len(lines)
        call_lines.setdefault(call_id, []).extend(lines)
    rec.dup_call_ids = {cid: n for cid, n in call_counts.items() if n > 1}
    rec.dup_call_lines = {cid: call_lines.get(cid, []) for cid in rec.dup_call_ids}
    return rec


def _exec_from_command(session_id: str, path: str, lineno: int, item: dict,
                       turn_index: int = 0) -> ExecRecord:
    command = item.get("command")
    exit_code = _num(item.get("exit_code"))
    status_field = item.get("status")
    if exit_code is not None:
        status = "ok" if exit_code == 0 else "failed"
    elif status_field in ("failed", "error", "errored"):
        status = "failed"
    else:
        # A completed envelope only says the client stopped running the
        # command; without an exit code it cannot prove command success.
        status = "unknown"
    return ExecRecord(
        session_id=session_id, file=path, line=lineno, source="exec",
        kind=_command_first_token(command),
        exec_id=_clean_str(item.get("id") or ""),
        status=status, exit_code=exit_code,
        duration=_float(item.get("duration")),
        cmd_hash=_hash_command(command),
        started_at=parse_ts(item.get("timestamp")) if item.get("timestamp") else "",
        scope_hash=_hash_value(item.get("cwd")) if item.get("cwd") is not None else "",
        turn_index=turn_index)


def _exec_from_mcp(session_id: str, path: str, lineno: int, item: dict,
                   turn_index: int = 0, timestamp: str = "") -> ExecRecord:
    server = _clean_str(item.get("server") or "")
    tool = _clean_str(item.get("tool") or "")
    status_field = item.get("status")
    result = item.get("result")
    result_error = (isinstance(result, dict) and
                    (result.get("isError") is True or "Err" in result))
    status = "failed" if status_field in ("failed", "error", "errored") or result_error else (
        "ok" if status_field == "completed" else "unknown")
    return ExecRecord(
        session_id=session_id, file=path, line=lineno, source="mcp",
        kind=("mcp:%s/%s" % (server, tool)) if tool else ("mcp:%s" % server),
        exec_id=_clean_str(item.get("id") or ""),
        status=status, exit_code=None,
        duration=_float(item.get("duration")),
        cmd_hash=_hash_command([server, tool, item.get("arguments")]),
        started_at=timestamp, scope_hash=_hash_value(item.get("arguments"))
        if item.get("arguments") is not None else "", turn_index=turn_index)


def parse_files(paths: List[str]) -> List[SessionRecord]:
    return [parse_session(p, i) for i, p in enumerate(paths)]
