#!/usr/bin/env python3
"""AUAS Usage Receipt Protocol（AUAS-DATA/TRUST 的实现核心）。

Usage Receipt = 某个可验证 Observer 对一次 Agent-tool interaction 所做的
最小、签名、隐私安全声明。

核心机制：correlation_commitment
  client 与 server 各自只上传签名后的最小收据；公共 verifier 通过
  commitment = H(protocol_version || project_id || trace_id || tool_call_id)
  判断"两条收据是否关于同一次调用"——不需要看到 prompt/arguments/response。

承诺属性：
  - 隐私：commitment 是单向哈希，无法反推 trace_id/tool_call_id
  - 跨主体：两个独立 runtime 可计算相同 commitment（同一次调用）
  - 防重链：commitment 输入字段全部被签名（P0 修复后）

Receipt 字段（MUST NOT 包含）：prompt、tool input/output、path、conversation、user identity。
"""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collector.usage import pseudonymize, utc_now  # noqa: E402

PROTOCOL_VERSION = "agentmeasure-0.1"

RECEIPT_FIELDS = (
    "spec_version", "receipt_id", "observed_at",
    "observer_principal", "observer_side", "provenance", "trust_domain",
    "project_id", "tool", "tool_call_id", "trace_id",
    "session_key", "outcome", "lifecycle_stage",
    "correlation_commitment", "sampling",
    "signature", "key_id",
)

# 参与 commitment 的字段（任一不同 → 不同 commitment → 无法关联）
COMMITMENT_FIELDS = ("project_id", "trace_id", "tool_call_id")


def correlation_commitment(project_id: str, trace_id: str, tool_call_id: str):
    """H(protocol_version || project_id || trace_id || tool_call_id)。

    fail-closed：无 trace_id 且无 tool_call_id 时返回 None（关联材料不足，
    绝不生成"同项目全空 id"的统一 commitment——否则同项目缺失 id 的调用
    会被错误关联）。
    """
    if not trace_id and not tool_call_id:
        return None
    payload = "||".join([PROTOCOL_VERSION, str(project_id or ""),
                         str(trace_id or ""), str(tool_call_id or "")])
    return "c-" + hashlib.sha256(payload.encode()).hexdigest()[:32]


def build_receipt(observation: dict, *, observer_principal: str, observer_side: str,
                  provenance: str, project_id: str, trust_domain: str = "") -> dict:
    """由 observation 事实构建最小收据（未签名）。session 在内存内伪匿名。"""
    raw_session = observation.get("session_key")
    return {
        "spec_version": PROTOCOL_VERSION,
        "receipt_id": str(uuid.uuid4()),
        "observed_at": observation.get("observed_at") or utc_now(),
        "observer_principal": observer_principal,
        "observer_side": observer_side,
        "provenance": provenance,
        "trust_domain": trust_domain,
        "project_id": project_id,
        "tool": str(observation.get("tool") or "unknown")[:120],
        "tool_call_id": str(observation.get("tool_call_id") or "")[:120] or None,
        "trace_id": str(observation.get("trace_id") or "")[:64] or None,
        "session_key": pseudonymize(str(raw_session), observer_principal.split("@")[0]) if raw_session else None,
        "outcome": observation.get("outcome") or "unknown",
        "lifecycle_stage": observation.get("lifecycle_stage") or "L0",
        "correlation_commitment": correlation_commitment(
            project_id,
            str(observation.get("trace_id") or ""),
            str(observation.get("tool_call_id") or ""),
        ),
        "sampling": observation.get("sampling"),
        "signature": None,
        "key_id": None,
    }


def sign_receipt(receipt: dict, key_id: str) -> dict:
    """对收据签名（canonical over SIGNED_FIELDS——与 verifier 完全一致）。"""
    from collector.verifier.keygen import load_secret
    from collector.verifier.verifier import canonical
    from collector.verifier.ed25519 import sign
    import base64

    secret = load_secret(key_id)
    signed = dict(receipt)
    signed["signature"] = base64.b64encode(sign(secret, canonical(receipt))).decode()
    signed["key_id"] = key_id
    return signed


def verify_receipt(receipt: dict) -> bool:
    from collector.verifier.verifier import verify_signature
    return verify_signature(receipt)


def receipts_correspond(ra: dict, rb: dict) -> bool:
    """两条收据是否关于同一次调用（commitment 相等 = 可关联，无需原始数据）。"""
    a = ra.get("correlation_commitment")
    b = rb.get("correlation_commitment")
    if not a or not b:
        return False
    # 同侧收据不构成独立佐证（防同侧自关联）
    if ra.get("observer_side") == rb.get("observer_side"):
        return False
    return a == b


def to_json(receipt: dict) -> str:
    return json.dumps({k: receipt.get(k) for k in RECEIPT_FIELDS
                       if receipt.get(k) is not None}, ensure_ascii=False)
