#!/usr/bin/env python3
"""agent-used collector — redactor（隐私守卫）。

原则（spec/privacy.md）：Raw telemetry stays local；敏感字段代码级默认 DROP。
本模块在写入统一事件前强制执行：
  1. 只允许 UNIFIED_KEYS 字段通过（白名单）
  2. 明确拒绝的敏感键即使出现在输入中也绝不落盘
  3. 泄漏测试：敏感载荷 → 断言零泄漏
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.usage import UNIFIED_KEYS  # noqa: E402

# 敏感键（出现在输入中 → 直接拒绝该记录）
SENSITIVE_KEYS = (
    "prompt", "tool_input", "tool_response", "tool_output", "input",
    "output", "content", "file_path", "cwd", "command", "transcript",
    "email", "username", "api_key", "token", "password", "secret",
)


def redact(record: dict) -> dict:
    """白名单过滤 + 敏感键检查。返回净化后的记录；含敏感键则抛 ValueError。"""
    for key in record:
        lowered = str(key).lower()
        if lowered in SENSITIVE_KEYS:
            raise ValueError(f"sensitive key rejected at redactor: {key}")
    clean = {k: record[k] for k in UNIFIED_KEYS if k in record and record[k] is not None}
    return clean


def leak_test() -> bool:
    """泄漏测试：模拟含敏感内容的输入，断言净化后零泄漏。"""
    evil = {
        "event_id": "e1", "occurred_at": "2026-08-16T00:00:00Z",
        "project_id": "github.com/foo/bar", "observer_side": "client",
        "agent_host": "codex", "provenance": "hook", "evidence_level": "E1",
        "session_id": "s-abc", "tool": "Bash", "stage": "S2", "outcome": "success",
        "duration_bucket": "1s-10s", "trace_id": "t1",
        "prompt": "rm -rf /home/secret", "tool_input": {"command": "cat /etc/passwd"},
        "tool_response": "root:x:0:0:root", "cwd": "/private/secret",
        "api_key": "sk-live-1234567890",
    }
    try:
        clean = redact(evil)
        raise AssertionError("redactor accepted sensitive keys!")
    except ValueError:
        pass
    # 白名单输出里不得出现任何敏感内容
    allowed = {k: v for k, v in evil.items() if k in UNIFIED_KEYS}
    text = repr(allowed)
    for bad in ("sk-live-1234567890", "rm -rf", "/etc/passwd", "/private/secret"):
        assert bad not in text, f"leak: {bad}"
    return True
