#!/usr/bin/env python3
"""agent-used collector — normalizer（adapter 原始载荷 → 观察事实）。

原则（measurement-integrity review）：
  - 只输出 observation 事实（无 evidence_level——证据由 verifier 计算）
  - 伪匿名在内存内完成（pseudonymize），原始 session id 绝不落盘
  - adapter 能力边界诚实：没有的字段不假设（unknown 优于错误的精确）
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.usage import (  # noqa: E402
    empty_observation,
    new_observation_id,
    pseudonymize,
    utc_now,
)


def _bucket(seconds) -> str:
    if seconds is None:
        return None  # 未知耗时：诚实为 None，不猜
    for threshold, label in ((1, "<1s"), (10, "1s-10s"), (60, "10s-60s"), (600, "1m-10m")):
        if seconds < threshold:
            return label
    return ">10m"


def _normalize_ts(value):
    """统一时间格式（Z → +00:00），保证 SQLite 字符串比较正确。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _to_observation(obs: dict, principal: str, side: str, provenance: str,
                    host: str, source_event_id: str = None) -> dict:
    obs["observation_id"] = new_observation_id()
    obs["observed_at"] = _normalize_ts(obs.get("observed_at")) or utc_now()
    obs["observer_principal"] = principal
    obs["observer_side"] = side
    obs["provenance"] = provenance
    obs["source_event_id"] = source_event_id
    # 内存内伪匿名：原始 session 只存在于本函数内
    raw_session = obs.get("session_key")
    if raw_session:
        obs["session_key"] = pseudonymize(str(raw_session), host)
    return obs


def normalize_observation(raw: dict, source: str, project_id: str, principal: str) -> dict:
    """按来源把 adapter 原始载荷转为观察事实。"""
    obs = empty_observation()
    obs["project_id"] = project_id

    if source == "codex-hook":
        # Codex 官方 PostToolUse 稳定字段：tool_name / tool_use_id / session_id / model / turn_id
        # 官方 schema 无 trace_id / start_time / end_time / is_error —— 不假设
        obs["tool"] = str(raw.get("tool_name") or "unknown")[:120]
        obs["tool_call_id"] = str(raw.get("tool_use_id") or "")[:120] or None
        obs["session_key"] = raw.get("session_id")
        obs["outcome"] = "unknown"  # hook 无法可靠判断成败（Bash 非零退出仍触发 PostToolUse）
        obs["duration_bucket"] = None
        obs["lifecycle_stage"] = "L1"  # 观察到执行发生
        obs["source_event_id"] = str(raw.get("tool_use_id") or "")[:120] or None
        return _to_observation(obs, principal, "client", "hook", "codex")

    if source == "mcp-wrapper":
        # wrapper 在 server 侧真实调用边界：outcome/duration 可信
        obs["tool"] = str(raw.get("tool") or "unknown")[:120]
        obs["tool_call_id"] = str(raw.get("tool_call_id") or "")[:120] or None
        obs["trace_id"] = str(raw.get("trace_id") or "")[:64] or None
        obs["session_key"] = raw.get("session_key") or raw.get("session_id")
        obs["outcome"] = str(raw.get("outcome") or "unknown")
        obs["duration_bucket"] = str(raw.get("duration_bucket") or "") or None
        obs["lifecycle_stage"] = "L2" if obs["outcome"] in ("success", "failure") else "L1"
        return _to_observation(obs, principal, "server", "wrapper", "mcp")

    if source == "dsh":
        # DSH plugin 输出（已归一）。lifecycle 来自 harness 事件，evidence 字段一律忽略
        obs["tool"] = str(raw.get("tool") or "unknown")[:120]
        obs["tool_call_id"] = str(raw.get("tool_use_id") or "")[:120] or None
        obs["trace_id"] = str(raw.get("trace_id") or "")[:64] or None
        obs["session_key"] = raw.get("session_id") or raw.get("session_key")
        obs["outcome"] = str(raw.get("outcome") or "unknown")
        obs["duration_bucket"] = str(raw.get("duration_bucket") or "") or None
        ls = str(raw.get("lifecycle_stage") or "")
        obs["lifecycle_stage"] = ls if ls in ("L0", "L1", "L2", "L3") else "L2"
        obs["source_event_id"] = str(raw.get("event_id") or "")[:120] or None
        return _to_observation(obs, principal, "client", "platform", "deepseek-harness")

    raise ValueError(f"unknown source: {source}")
