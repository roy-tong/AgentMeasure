#!/usr/bin/env python3
"""AgentMeasure Measurement Policy v2（Draft 0.4.2）。

Metric 不能脱离 Policy：两个网站都显示 "Agent Usage = 12,000" 但一个只算
cross-side corroborated、另一个 observed 都算——不可比。v2 变化：
  - Policy **绑定具体 Metric**（metric_id），不再一个 CORE_POLICY 控制所有指标
  - 废弃遗留：eligible_evidence E1+/E2、VACD、agentmeasure-0.1 spec
  - 引入 Strict Qualified（production + normal）为 qualification 默认
  - 机器可读版见 registry/metrics.yaml（单一事实源，validator 校验一致性）

Policy 字段：
  policy_id / spec_version / metric_id
  time_window_days
  qualification_policy      context/validity 口径（默认 Strict Qualified）
  observability_policy      UNOBSERVABLE 不得视为负面；unknown 单列
  entity_resolution_policy  registry 解析（fail-closed）
  evidence_requirement      最低证据等级（单词等级：observed 起步）
  coverage_basis            census | probability_sample | participating_network | unknown
  sampling_policy           unsampled-only | weighted-estimate（后者必须报 uncertainty）
  dedup_policy              去重规则（operation-unique / attempt-unique）
  privacy_threshold         最小样本量门槛
"""
from __future__ import annotations

import json

STRICT_QUALIFIED = {"context": "production", "validity": "normal"}

# 基础口径（聚合输出默认携带）；具体指标覆盖见 METRIC_POLICIES 与 registry/metrics.yaml
MEASUREMENT_POLICY = {
    "policy_id": "AgentMeasure/Measurement-1",
    "spec_version": "agentmeasure-0.4",
    "metric_id": "aggregate-base",
    "time_window_days": 30,
    "qualification_policy": dict(STRICT_QUALIFIED),
    "observability_policy": {"unobservable_is_not_negative": True,
                             "unknown_disclosed": True},
    "entity_resolution_policy": {"registry_version": None, "fail_closed": True},
    "evidence_requirement": {"minimum": "observed",
                             "corroborated_disclosed": True},
    "coverage_basis": "participating_network",
    "sampling_policy": "unsampled-only",
    "dedup_policy": "operation-unique",
    "privacy_threshold": 10,
}

# Metric-bound 覆盖（与 registry/metrics.yaml 的 policy 段保持一致）
METRIC_POLICIES = {
    "M3.1": {"metric_id": "M3.1", "dedup_policy": "operation-unique",
             "qualification_policy": dict(STRICT_QUALIFIED)},
    "M3.3": {"metric_id": "M3.3", "dedup_policy": "attempt-unique",
             "qualification_policy": dict(STRICT_QUALIFIED)},
    "M3.5": {"metric_id": "M3.5", "dedup_policy": "attempt-unique",
             "qualification_policy": {"context": "production", "validity": "normal"},
             "observability_policy": {"resolution_disclosed": True}},
    "M2.2": {"metric_id": "M2.2", "dedup_policy": "decision-unique",
             "qualification_policy": dict(STRICT_QUALIFIED)},
    "M4.1": {"metric_id": "M4.1", "dedup_policy": "attempt-unique",
             "qualification_policy": dict(STRICT_QUALIFIED)},
    "M1.1": {"metric_id": "M1.1", "dedup_policy": "client-unique",
             "qualification_policy": dict(STRICT_QUALIFIED)},
}


def metric_policy(metric_id: str) -> dict:
    """metric 专属 policy：基础口径 + metric 覆盖。"""
    policy = dict(MEASUREMENT_POLICY)
    policy.update(METRIC_POLICIES.get(metric_id, {}))
    return policy


def validate_policy(policy: dict) -> bool:
    required = ("policy_id", "spec_version", "metric_id", "time_window_days",
                "qualification_policy", "observability_policy",
                "entity_resolution_policy", "evidence_requirement",
                "coverage_basis", "sampling_policy", "dedup_policy",
                "privacy_threshold")
    return all(k in policy for k in required)


def describe(policy: dict) -> str:
    q = policy.get("qualification_policy", {})
    return (f"{policy.get('policy_id', '?')} [{policy.get('metric_id', 'base')}] "
            f"(qualified={q.get('context', '?')}+{q.get('validity', '?')}, "
            f"evidence>={policy.get('evidence_requirement', {}).get('minimum', '?')}, "
            f"coverage={policy.get('coverage_basis', '?')}, "
            f"sampling={policy.get('sampling_policy', '?')}, "
            f"window={policy.get('time_window_days', '?')}d)")
