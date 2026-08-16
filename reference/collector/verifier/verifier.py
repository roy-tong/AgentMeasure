#!/usr/bin/env python3
"""AgentMeasure collector — verifier（证据引擎 v2：Evidence Profile 方向）。

**Evidence is derived, never self-declared.** adapter 只报告观察事实。

显示等级由 evidence vector 派生（AgentMeasure-TRUST）：
  - Observed                有观察
  - Authenticated           至少一条观察带有效 Ed25519 签名
  - Corroborated            ≥2 条观察（独立 observer）
  - Independently Corroborated   ≥2 条独立 observer 且 trust domain 不同
  - Platform Attested       平台 attestation 验证通过（当前 UNSUPPORTED）

fail-closed 原则：
  - 验签失败/无法验证 → 不提升等级
  - provenance="platform" 字符串绝不授予 Platform Attested（未验证 = UNSUPPORTED）
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.verifier.canonical import canonical_json  # noqa: E402
from collector.verifier.ed25519 import verify  # noqa: E402

PUBLIC_KEYS_DIR = Path(__file__).resolve().parents[2] / "keys"

# 影响 attribution / correlation / qualification 的全部字段（MUST 被签名）。
# signature / key_id 除外（key_id 是验签密钥选择器，不影响归因语义）。
SIGNED_FIELDS = (
    "receipt_id", "spec_version", "observed_at", "observer_principal",
    "observer_side", "provenance", "project_id", "tool", "tool_call_id",
    "trace_id", "session_key", "outcome", "lifecycle_stage",
    "source_event_id", "sampling", "trust_domain",
)


def canonical(receipt: dict) -> bytes:  # receipt = signed observation（Verified Profile）
    return canonical_json({k: receipt.get(k) for k in SIGNED_FIELDS if receipt.get(k) is not None}).encode()


def load_public_key(key_id: str) -> Optional[bytes]:
    path = PUBLIC_KEYS_DIR / f"{key_id}.pub"
    if not path.exists():
        return None
    try:
        return base64.b64decode(path.read_text().strip())
    except (ValueError, OSError):
        return None


def verify_signature(receipt: dict) -> bool:
    """验证 Signed Observation 的 Ed25519 签名（canonical JSON over SIGNED_FIELDS）。fail-closed。"""
    sig = receipt.get("signature")
    key_id = receipt.get("key_id")
    if not sig or not key_id:
        return False
    pub = load_public_key(key_id)
    if pub is None:
        return False
    try:
        return verify(pub, canonical(receipt), base64.b64decode(sig))
    except Exception:
        return False


PLATFORM_ATTESTATION = "UNSUPPORTED"  # 平台 attestation 未实现前，不授予


def evidence_vector(observations: list) -> dict:
    """由 observations 计算多轴证据向量（底层模型，上层才压缩为显示等级）。"""
    if not observations:
        return {"class": "none"}
    authenticated = any(o.get("signature") and verify_signature(o) for o in observations)
    principals = {
        (o.get("observer_principal"), o.get("trust_domain"))
        for o in observations if o.get("observer_principal")
    }
    distinct_observers = len(principals)
    domains = {td for _, td in principals if td}
    independent_domains = len(domains) >= 2

    display = "observed"
    if authenticated:
        display = "authenticated"
    if distinct_observers >= 2:
        display = "corroborated"
    if distinct_observers >= 2 and independent_domains:
        display = "independently-corroborated"
    return {
        "class": display,
        "authentication": "signed" if authenticated else "none",
        "corroboration": f"{distinct_observers} observers",
        "independence": "distinct-domains" if independent_domains else (
            "single-domain" if domains else "unknown"),
        "attestation": PLATFORM_ATTESTATION,
    }


def grade_invocation(observations: list) -> str:
    """派生显示等级（TRUST §4 单词等级；替代遗留 E0-E3 码）。

    返回：none | observed | authenticated | corroborated | independently-corroborated
    （platform-attested 当前 UNSUPPORTED，永不返回）
    """
    return evidence_vector(observations)["class"]
