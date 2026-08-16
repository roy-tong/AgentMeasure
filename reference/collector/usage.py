#!/usr/bin/env python3
"""agent-used collector — 数据模型 v3。

核心原则（measurement-integrity review）：
  1. Observation ≠ Invocation。adapter 只产生 observation（观察事实）；
     invocation（一次逻辑调用）由 correlator 推导，usage aggregate 由 aggregator 计算。
  2. Evidence is derived, never self-declared。
     adapter 不设 evidence；verifier 从 observation 事实计算证据等级。
  3. Raw stays local：pseudonymization 在落盘前、内存内完成。

实体：
  observations       adapter 观察事实（唯一的 ingestion 输入）
  invocations        推导的逻辑调用（由 observation 聚合）
  observation_links  invocation ↔ observation 多对多
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
    "project_id",
    "tool",                 # 归一工具名
    "tool_call_id",         # 精确关联键（若 adapter 能提供）
    "trace_id",             # OTel trace（若 adapter 能提供）
    "session_key",          # 伪匿名会话（内存内生成，绝不落原始值）
    "outcome",              # success | failure | retry | denied | unknown
    "duration_bucket",      # <1s | 1s-10s | ... | None（未知）
    "lifecycle_stage",      # L0-L3（观察到的生命周期阶段，非证据）
    "signature",            # Ed25519 签名（可选）
    "key_id",               # 签名密钥标识（可选）
    "source_event_id",      # adapter 自身事件 id（去重用）
    "trust_domain",         # 观察者信任域（AUAS-TRUST；独立佐证判定的关键）
    "sampling",             # {"method": "fixed", "probability": 0.1} 等（AUAS-COVERAGE）
    "usage_context",        # production|development|test|benchmark|evaluation|synthetic|ci|unknown
    "validity",             # normal|retry|duplicate|replay|agent_loop|health_check|load_test|suspected_invalid|unknown
)

USAGE_CONTEXTS = ("production", "development", "test", "benchmark",
                  "evaluation", "synthetic", "ci", "unknown")
QUALIFIED_CONTEXTS = ("production", "unknown")  # 公开 adoption 默认口径

LIFECYCLE_STAGES = ("L0", "L1", "L2", "L3")
SIDES = ("client", "server", "platform")
PROVENANCES = ("hook", "otel", "wrapper", "platform")
OUTCOMES = ("success", "failure", "retry", "denied", "unknown")

# ---- 伪匿名（spec/privacy.md：HMAC(epoch_secret, host:raw) 按月轮换） ----
_SECRET_PATH = Path(os.environ.get("AGENT_USED_IDENTITY_DIR", str(Path.home() / ".agent-used"))) / "identity"


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
