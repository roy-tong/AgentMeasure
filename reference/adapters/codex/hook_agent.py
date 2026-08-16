#!/usr/bin/env python3
"""AgentMeasure — Codex PostToolUse hook adapter（v3，measurement-integrity）。

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
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.usage import pseudonymize  # noqa: E402

EVENTS_DIR = Path(
    os.environ.get("AGENTMEASURE_EVENTS_DIR", str(Path.home() / ".agentmeasure" / "events"))
).expanduser()
DO_NOT_TRACK = os.environ.get("DO_NOT_TRACK", "0") == "1"
AGENT_HOST = os.environ.get("AGENTMEASURE_HOST", "codex")
TARGET = os.environ.get("AGENTMEASURE_TARGET", "github.com/roy-tong/AgentMeasure")
OBSERVER_PRINCIPAL = os.environ.get("AGENTMEASURE_PRINCIPAL", "codex-hook@local")
TRUST_DOMAIN = os.environ.get("AGENTMEASURE_TRUST_DOMAIN", "local")
INSTANCE_ID = os.environ.get("AGENTMEASURE_INSTANCE_ID", f"hook-{os.getpid()}")

_SEQUENCE = [0]


def next_sequence() -> int:
    _SEQUENCE[0] += 1
    return _SEQUENCE[0]

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

    # ---- Canonical Observation Envelope（DATA.md / schemas/observation.schema.json） ----
    tool_name = payload.get("tool_name") or "unknown"
    tool_use_id = payload.get("tool_use_id")
    raw_session = payload.get("session_id")
    # 内存内伪匿名：原始 session 只出现在本函数内；落盘为 client_key
    client_key = pseudonymize(str(raw_session), AGENT_HOST) if raw_session else None
    envelope = {
        "spec_version": "agentmeasure-0.4",
        "observation_id": str(uuid.uuid4()),
        "observation_type": "attempt_completed",   # PostToolUse = 执行已结束（outcome 不可判）
        "observer": {"principal": OBSERVER_PRINCIPAL, "side": "client",
                     "trust_domain": TRUST_DOMAIN},
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "deployment_context": {"project_id": TARGET},
        "surface": {"surface_id": f"codex:{tool_name}"[:120],
                    "surface_namespace": "codex"},
        "caller": {"type": "claimed_agent", "runtime": "codex",
                   "identity_strength": "declared"},
        "client_key": client_key,
        "usage_context": "unknown",
        "validity": "unknown",
        "context_source": "none",
        "validity_source": "none",
        "collection_health": {"source_instance_id": INSTANCE_ID,
                              "source_sequence": next_sequence(),
                              "sequence_epoch": datetime.now(timezone.utc).strftime("%Y-%m"),
                              "dropped_since_last_report": 0,
                              "buffer_overflow": False},
        "provenance": "hook",
        "payload": {"tool_call_id": tool_use_id, "outcome": "unknown"},
    }
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    with (EVENTS_DIR / "codex-hook-events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(envelope, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
