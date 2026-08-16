#!/usr/bin/env python3
"""AgentMeasure Measurement Policy（AgentMeasure-METRICS）。

Metric 不能脱离 Policy：两个网站都显示 "Agent Usage = 12,000" 但一个只算 E2、
另一个 E0 都算——不可比。本对象使指标携带完整口径：

  12,481 ACD @ policy=AgentMeasure/Core-1

Policy 字段（全部必填）：
  policy_id / spec_version
  eligible_evidence     哪些证据等级计入（如 ["E1+"] 或 ["E2"]）
  correlation_policy    关联规则版本（exact-only / exact+trace / full）
  coverage_scope        观察覆盖范围（hosts、observer population）
  sampling_policy       unsampled-only | weighted-estimate（后者必须报 uncertainty）
  dedup_policy          去重规则版本
  time_window           窗口（如 30d）
  privacy_threshold     最小样本量门槛
"""
from __future__ import annotations

import json

CORE_POLICY_V1 = {
    "policy_id": "AgentMeasure/Core-1",
    "spec_version": "agentmeasure-0.1",
    "eligible_evidence": ["E1+", "E2"],      # E0 不计入
    "correlation_policy": "exact-first",
    "coverage_scope": {"hosts": ["codex", "claude-code", "deepseek-harness"],
                       "observer_population": "participating"},
    "sampling_policy": "unsampled-only",      # 当前只接受未采样数据（保守）
    "dedup_policy": "invocation-unique",
    "time_window_days": 30,
    "privacy_threshold_sessions": 10,
}


def validate_policy(policy: dict) -> bool:
    required = ("policy_id", "spec_version", "eligible_evidence",
                "correlation_policy", "coverage_scope", "sampling_policy",
                "dedup_policy", "time_window_days", "privacy_threshold_sessions")
    return all(k in policy for k in required)


def describe(policy: dict) -> str:
    return (f"{policy['policy_id']} "
            f"(evidence={','.join(policy['eligible_evidence'])}, "
            f"sampling={policy['sampling_policy']}, "
            f"window={policy['time_window_days']}d)")
