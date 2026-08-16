#!/usr/bin/env python3
"""agent-used — Codex/Claude Code PostToolUse hook adapter（v2，对齐 unified model）。

在 agent 的工具调用边界捕获原始元数据载荷（调用方观测），交给 collector 的
normalizer（source="codex-hook"）转换为统一 Usage Model 记录。

隐私红线（代码级）:
  - 只保留: hook_event_name / tool_name / outcome 相关 / 时间 / session / trace
  - 绝不写入: tool_input / tool_response / 提示词 / 路径 / 会话内容
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

EVENTS_DIR = Path(
    os.environ.get("AGENT_USED_EVENTS_DIR", str(Path.home() / ".agent-used" / "events"))
).expanduser()
DO_NOT_TRACK = os.environ.get("DO_NOT_TRACK", "0") == "1"

# 允许透传的键（白名单）——其余一律丢弃
ALLOWED_KEYS = (
    "hook_event_name", "event_name", "tool_name", "tool_call_id", "tool_use_id",
    "is_error", "error", "start_time", "end_time", "start", "end",
    "session_id", "trace_id",
)


def capture(payload: dict) -> dict:
    """白名单提取：只保留元数据键，内容键（input/response/content…）直接丢弃。"""
    return {k: payload[k] for k in ALLOWED_KEYS if k in payload and payload[k] is not None}


def main() -> int:
    if DO_NOT_TRACK:
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    event_name = payload.get("hook_event_name") or payload.get("event_name") or ""
    if event_name not in ("PostToolUse", "post_tool_use"):
        return 0  # 只对工具调用结果事件捕获

    record = capture(payload)
    record["captured_at"] = datetime.now(timezone.utc).isoformat()
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    with (EVENTS_DIR / "codex-hook-events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
