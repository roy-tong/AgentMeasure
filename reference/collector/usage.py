#!/usr/bin/env python3
"""AgentMeasure collector — 数据模型 v3（Draft 0.4.2）。

核心原则（measurement-integrity review）：
  1. Observation ≠ Attempt ≠ Operation。adapter 只产生 observation（观察事实）；
     attempt（一次真实执行）由 correlator 匹配；operation（逻辑使用）由
     derive_operations 按证据归并（fail-closed，无证据不归并）。
  2. Evidence is derived, never self-declared。
     adapter 不设证据；verifier 从 observation 事实计算证据等级。
  3. Raw stays local：pseudonymization 在落盘前、内存内完成。
  4. usage_context / validity 默认 unknown；只有证据（部署配置 / collector 派生）
     才升级，且必须携带 context_source / validity_source。

实体：
  observations       adapter 观察事实（唯一的 ingestion 输入）
  invocations        推导的 attempt（由 observation 聚合）
  observation_links  attempt ↔ observation 多对多
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---- 观察事实字段（adapter 允许产生的全部字段，白名单） ----
OBSERVATION_KEYS = (
    "observation_id",
    "observed_at",
    "observer_principal",   # adapter 身份，如 codex-hook@roy-tong
    "observer_side",        # client | server | platform
    "provenance",           # hook | otel | wrapper | platform
    "project_id",           # 部署上下文标识（DATA §1 deployment_context），非实体权威
    "tool",                 # 归一 surface 工具名（观察发生在 surface 层）
    "surface_id",           # 具体调用界面标识（Core §2.3）
    "surface_namespace",    # surface 的注册/命名空间（尽力而为）
    "tool_call_id",         # 精确关联键（若 adapter 能提供）
    "trace_id",             # OTel trace（若 adapter 能提供）
    "session_key",          # 伪匿名会话（内存内生成，绝不落原始值）
    "outcome",              # success | failure | retry | denied | unknown
    "duration_bucket",      # <1s | 1s-10s | ... | None（未知）
    "lifecycle_stage",      # 生命周期阶段数据码：L0 选择 · L1 执行 · L2 完成 · L3 消费（非证据）
    "signature",            # Ed25519 签名（可选，Verified Profile）
    "key_id",               # 签名密钥标识（可选）
    "source_event_id",      # adapter 自身事件 id（去重用）
    "source_sequence",      # 单调递增序号；云端据此检出丢失缺口（Draft 0.4.2）
    "trust_domain",         # 观察者信任域（AgentMeasure-TRUST；独立佐证判定的关键）
    "sampling",             # {"method": "fixed", "probability": 0.1} 等（AgentMeasure-QUALITY）
    "usage_context",        # production|development|test|benchmark|evaluation|synthetic|ci|unknown
    "validity",             # normal|retry|duplicate|replay|agent_loop|health_check|load_test|suspected_invalid|unknown
    "context_source",       # none|provider_configuration|collector_derived|runtime_propagated（Draft 0.4.2）
    "validity_source",      # none|collector_derived|runtime_propagated（Draft 0.4.2）
    "operation_id",         # 逻辑使用（Core §2.4）；未知留 null（不变量 23：无证据不归并）
    "task_id",              # 任务单位（谱系起点）；未知留 null
)

USAGE_CONTEXTS = ("production", "development", "test", "benchmark",
                  "evaluation", "synthetic", "ci", "unknown")
# Strict Qualified Usage = production + validity=normal（Core §7）；unknown 单独披露
STRICT_QUALIFIED = {"context": "production", "validity": "normal"}
CONTEXT_SOURCES = ("none", "provider_configuration", "collector_derived", "runtime_propagated")
VALIDITY_SOURCES = ("none", "collector_derived", "runtime_propagated")

LIFECYCLE_STAGES = ("L0", "L1", "L2", "L3")
SIDES = ("client", "server", "platform")
PROVENANCES = ("hook", "otel", "wrapper", "platform")
OUTCOMES = ("success", "failure", "retry", "denied", "unknown")

# ---- 伪匿名（spec/privacy.md：HMAC(epoch_secret, host:raw) 按月轮换） ----
_SECRET_PATH = Path(os.environ.get("AGENTMEASURE_IDENTITY_DIR", str(Path.home() / ".agentmeasure"))) / "identity"


def _epoch() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _local_secret() -> bytes:
    _SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _SECRET_PATH.exists():
        return _SECRET_PATH.read_bytes()[:64]
    secret = os.urandom(32)
    _SECRET_PATH.write_bytes(secret)
    return secret


def pseudonymize(raw: str, host: str) -> str:
    """内存内伪匿名：pid = HMAC(epoch_secret, host:raw)，按月轮换（unlinkability）。"""
    if not raw:
        return ""
    epoch_secret = hmac.new(_local_secret(), _epoch().encode(), hashlib.sha256).digest()
    return "p-" + hmac.new(epoch_secret, f"{host}:{raw}".encode(), hashlib.sha256).hexdigest()[:20]


def new_observation_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_observation() -> dict:
    return {k: None for k in OBSERVATION_KEYS}


def to_jsonl(record: dict) -> str:
    return json.dumps(
        {k: record.get(k) for k in OBSERVATION_KEYS if record.get(k) is not None},
        ensure_ascii=False,
    )
