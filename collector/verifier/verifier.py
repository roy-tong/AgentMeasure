#!/usr/bin/env python3
"""agent-used collector — verifier（证据引擎）。

核心原则：**Evidence is derived, never self-declared.**
adapter 只报告观察事实；本引擎从事实计算证据等级：

  E0 Observed            有观察，但无认证
  E1 Source-authenticated  观察带有效 Ed25519 签名（非对称：验签公钥可公开）
  E2 Correlated          同一 invocation 有 ≥2 条独立 observer 的观察
  E3 Platform-attested   provenance=platform 且带平台 attestation（未来）

E1 密码学：Ed25519（私钥签名 / 公钥验证）。HMAC 是对称密钥，验签密钥公开即等于
公开签名密钥——不满足 public verification。E1 只证明"某个主体确实签发了这条观察"，
不证明真实使用（signature ≠ usage truth）。
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Optional

# Ed25519 签名验证。优先标准库（Python 3.13+ hashlib 支持），否则纯 Python 实现。
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

PUBLIC_KEYS_DIR = Path(__file__).resolve().parents[1] / "keys"


def load_public_key(key_id: str) -> Optional[bytes]:
    """从 keys/ 目录加载公钥（key_id → <key_id>.pub，base64 Ed25519）。"""
    path = PUBLIC_KEYS_DIR / f"{key_id}.pub"
    if not path.exists():
        return None
    return base64.b64decode(path.read_text().strip())


def verify_signature(observation: dict) -> bool:
    """验证 observation 的 Ed25519 签名（canonical fields）。"""
    sig = observation.get("signature")
    key_id = observation.get("key_id")
    if not sig or not key_id:
        return False
    if not _HAS_CRYPTO:
        return False  # 无密码学库时 fail-closed（宁缺毋假）
    pub = load_public_key(key_id)
    if pub is None:
        return False
    canonical = json.dumps(
        {
            k: observation.get(k)
            for k in ("observation_id", "observed_at", "observer_principal",
                      "observer_side", "project_id", "tool", "outcome")
        },
        sort_keys=True, separators=(",", ":"),
    ).encode()
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(
            base64.b64decode(sig), canonical
        )
        return True
    except (InvalidSignature, ValueError):
        return False


def grade_invocation(observations: list) -> str:
    """由 observations 计算 invocation 的证据等级（derived，不信任任何自声明）。"""
    if not observations:
        return "E0"
    authenticated = any(o.get("signature") and verify_signature(o) for o in observations)
    principals = {o.get("observer_principal") for o in observations if o.get("observer_principal")}
    independent = len(principals) >= 2
    platform = any(
        o.get("provenance") == "platform" and o.get("observer_side") == "platform"
        for o in observations
    )
    if platform:
        return "E3"  # 平台 attestation（未来：需平台签名验证）
    if independent:
        return "E2"
    if authenticated:
        return "E1"
    return "E0"
