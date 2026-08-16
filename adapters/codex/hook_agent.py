#!/usr/bin/env python3
"""agent-used — Codex/Claude Code PostToolUse hook（M0.5 PoC）。

在 agent 的工具调用边界记录使用事件（调用方计数，与 wrapper 的被调方计数交叉验证）。
从 stdin 读取 hook JSON，只提取元数据，丢弃全部内容。

隐私红线（代码级）:
  - 只读取: tool_name / outcome 相关字段 / 时间
  - 绝不写入: tool_input / tool_response / 提示词 / 路径 / 会话内容
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

EVENTS_DIR = Path(
    os.environ.get("AGENT_USED_EVENTS_DIR", str(Path.home() / ".agent-used" / "events"))
).expanduser()
TARGET = os.environ.get("AGENT_USED_TARGET", "github.com/roy-tong/agent-used")
DO_NOT_TRACK = os.environ.get("DO_NOT_TRACK", "0") == "1"
AGENT_HOST = os.environ.get("AGENT_USED_HOST", "codex")

SENSITIVE_KEYS = ("tool_input", "tool_response", "input", "response", "content")


def _bucket(seconds: float) -> str:
    for threshold, label in ((1, "<1s"), (10, "1s-10s"), (60, "10s-60s"), (600, "1m-10m")):
        if seconds < threshold:
            return label
    return ">10m"


def emit(tool: str, outcome: str, seconds: float) -> None:
    if DO_NOT_TRACK:
        return
    event = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "target": TARGET,
        "surface": "hook",
        "tool": tool[:120],
        "outcome": outcome,
        "duration_bucket": _bucket(seconds),
        "agent_host": AGENT_HOST,
        "telemetry_mode": "local",
    }
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    with (EVENTS_DIR / "agent-use-events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0  # 不是 hook 载荷，静默退出
    if not isinstance(payload, dict):
        return 0

    event_name = payload.get("hook_event_name") or payload.get("event_name") or ""
    tool = str(payload.get("tool_name") or "unknown")
    # outcome：PostToolUse 正常返回视为 success；有 error/is_error 字段视为 failure
    outcome = "failure" if payload.get("is_error") or payload.get("error") else "success"
    start = payload.get("start_time") or payload.get("start")
    end = payload.get("end_time") or payload.get("end")
    seconds = 0.0
    if start and end:
        try:
            seconds = max(0.0, float(end) - float(start))
        except (TypeError, ValueError):
            seconds = 0.0

    # 只对工具调用事件记录；SessionStart 等直接忽略
    if event_name not in ("PostToolUse", "post_tool_use"):
        return 0
    emit(tool, outcome, seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
