#!/usr/bin/env python3
"""agent-used collector — 统一使用模型（Unified Usage Model）。

所有 adapter（hook / wrapper / otel）的事件经 normalizer 映射为统一记录。
字段语义见 spec/measurement-spec.md；OTel 映射见 spec/otel-mapping.md。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

# 统一模型字段（agentused.* 扩展 + 复用 OTel 字段）
UNIFIED_KEYS = (
    "event_id", "occurred_at", "project_id", "project_version",
    "observer_side",   # client | server | platform
    "agent_host",      # codex | claude-code | deepseek-harness | other
    "provenance",      # otel | hook | wrapper | platform
    "evidence_level",  # E0 | E1 | E2 | E3
    "session_id",      # 伪匿名（本地映射）
    "tool",            # 归一工具名
    "stage",           # S0 | S1 | S2 | S3 | S4
    "outcome",         # success | failure | retry | denied
    "duration_bucket",
    "trace_id",
    "tool_use_id",
)

# 已有 OTel/MCP 标准字段的映射表（复用，不重复发明）
STANDARD_FIELD_MAP = {
    "gen_ai.tool.name": "tool",
    "mcp.method.name": "method",
    "error.type": "error_type",
    "service.name": "service_name",
    "trace_id": "trace_id",
    "span_id": "span_id",
}


def new_event_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_unified() -> dict:
    return {k: None for k in UNIFIED_KEYS}


def to_jsonl(record: dict) -> str:
    return json.dumps({k: record.get(k) for k in UNIFIED_KEYS if record.get(k) is not None},
                      ensure_ascii=False)


def from_jsonl(line: str) -> dict:
    return json.loads(line)
