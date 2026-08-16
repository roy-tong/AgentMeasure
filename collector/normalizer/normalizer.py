#!/usr/bin/env python3
"""agent-used collector — normalizer（跨 Agent 统一口径）。

把不同来源（codex hook / mcp wrapper / otel span / dsh plugin）的事件
映射为统一 Usage Model（spec/measurement-spec.md §4）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.usage import empty_unified, new_event_id, utc_now  # noqa: E402


def _bucket(seconds: float) -> str:
    for threshold, label in ((1, "<1s"), (10, "1s-10s"), (60, "10s-60s"), (600, "1m-10m")):
        if seconds < threshold:
            return label
    return ">10m"


def normalize_codex_hook(payload: dict, project_id: str, agent_host: str = "codex") -> dict:
    """Codex PostToolUse hook 载荷 → 统一记录（E1 起点，等待关联升级 E2）。"""
    r = empty_unified()
    r.update({
        "event_id": new_event_id(),
        "occurred_at": utc_now(),
        "project_id": project_id,
        "observer_side": "client",
        "agent_host": agent_host,
        "provenance": "hook",
        "evidence_level": "E1",
        "tool": str(payload.get("tool_name") or "unknown")[:120],
        "stage": "S2" if not (payload.get("is_error") or payload.get("error")) else "S1",
        "outcome": "failure" if (payload.get("is_error") or payload.get("error")) else "success",
        "duration_bucket": _bucket(0.0),
        "session_id": _pseudo(payload.get("session_id")),
        "tool_use_id": str(payload.get("tool_call_id") or payload.get("tool_use_id") or "")[:120],
        "trace_id": str(payload.get("trace_id") or "")[:64] or None,
    })
    return r


def normalize_mcp_wrapper_event(ev: dict, project_id: str) -> dict:
    """MCP wrapper 事件 → 统一记录（server 侧，E1 起点）。"""
    r = empty_unified()
    r.update({
        "event_id": new_event_id(),
        "occurred_at": utc_now(),
        "project_id": project_id,
        "observer_side": "server",
        "agent_host": str(ev.get("agent_host") or "unknown")[:80],
        "provenance": "wrapper",
        "evidence_level": "E1",
        "tool": str(ev.get("tool") or "unknown")[:120],
        "stage": "S2" if ev.get("outcome") == "success" else "S1",
        "outcome": str(ev.get("outcome") or "success"),
        "duration_bucket": str(ev.get("duration_bucket") or "1s-10s"),
        "session_id": None,
        "trace_id": str(ev.get("trace_id") or "")[:64] or None,
    })
    return r


def normalize_otel_span(span: dict, project_id: str, agent_host: str = "unknown") -> dict:
    """OTel execute_tool span 属性 → 统一记录（server 或 client 侧）。"""
    r = empty_unified()
    r.update({
        "event_id": new_event_id(),
        "occurred_at": utc_now(),
        "project_id": project_id,
        "observer_side": str(span.get("agentused.observer.side") or "server"),
        "agent_host": str(span.get("agentused.agent.host") or agent_host)[:80],
        "provenance": str(span.get("agentused.provenance") or "otel"),
        "evidence_level": str(span.get("agentused.evidence.level") or "E0"),
        "tool": str(span.get("gen_ai.tool.name") or span.get("mcp.method.name") or "unknown")[:120],
        "stage": "S2" if not span.get("error.type") else "S1",
        "outcome": "failure" if span.get("error.type") else "success",
        "duration_bucket": str(span.get("duration_bucket") or "1s-10s"),
        "trace_id": str(span.get("trace_id") or "")[:64] or None,
    })
    return r


def _pseudo(raw) -> str:
    """伪匿名会话：本地单向哈希，不落原始值。"""
    if not raw:
        return None
    import hashlib
    return "s-" + hashlib.sha256(str(raw).encode()).hexdigest()[:16]


def normalize_record(record: dict, source: str, project_id: str) -> dict:
    """通用入口：按 source 分发。"""
    if source == "codex-hook":
        return normalize_codex_hook(record, project_id)
    if source == "mcp-wrapper":
        return normalize_mcp_wrapper_event(record, project_id)
    if source == "otel-span":
        return normalize_otel_span(record, project_id)
    raise ValueError(f"unknown source: {source}")
