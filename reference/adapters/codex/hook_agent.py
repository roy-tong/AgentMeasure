#!/usr/bin/env python3
"""agent-used — Codex PostToolUse hook adapter（v3，measurement-integrity）。

能力边界（诚实声明）：
  - 可可靠提供：tool_name / tool_use_id / session_id / model / turn_id
  - 不可靠提供（官方 PostToolUse schema 无）：trace_id / start_time / end_time / is_error
    → 不捕获、不推断。Bash 非零退出仍触发 PostToolUse，成败由 normalizer 记为 unknown。

隐私（代码级）：
  - 原始 session_id 只在内存中出现，落盘前伪匿名（HMAC epoch）
  - 绝不写入：tool_input / tool_response / prompt / 路径 / 内容
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.usage import pseudonymize  # noqa: E402

EVENTS_DIR = Path(
    os.environ.get("AGENT_USED_EVENTS_DIR", str(Path.home() / ".agent-used" / "events"))
).expanduser()
DO_NOT_TRACK = os.environ.get("DO_NOT_TRACK", "0") == "1"
AGENT_HOST = os.environ.get("AGENT_USED_HOST", "codex")

# 允许透传的键（官方 PostToolUse 稳定字段）——内容键一律不捕获
ALLOWED_KEYS = ("hook_event_name", "event_name", "tool_name", "tool_use_id",
                "session_id", "model", "turn_id")


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
        return 0

    safe = {k: payload[k] for k in ALLOWED_KEYS if k in payload and payload[k] is not None}
    # 内存内伪匿名：原始 session 不落盘
    raw_session = safe.pop("session_id", None)
    if raw_session:
        safe["session_id"] = pseudonymize(str(raw_session), AGENT_HOST)
    safe["captured_at"] = datetime.now(timezone.utc).isoformat()
    safe["agent_host"] = AGENT_HOST

    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    with (EVENTS_DIR / "codex-hook-events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
