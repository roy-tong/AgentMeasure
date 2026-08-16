#!/usr/bin/env python3
"""agent-used collector — verifier（证据引擎）。

核心原则：**Evidence is derived, never self-declared.**
adapter 只报告观察事实；本引擎从事实计算证据等级：

  E0 Observed            有观察，但无认证
  E1 Source-authenticated  观察带有效 Ed25519 签名（非对称：验签公钥可公开）
  E2 Correlated          同一 invocation 有 ≥2 条独立 observer 的观察
  E3 Platform-attested   provenance=platform 且带平台 attestation（未来）

E1 密码学：Ed25519（私钥签名 / 公钥验证）。HMAC 是对称密钥——验签密钥公开即等于
公开签名密钥，不满足 public verification。E1 只证明"某主体确实签发了这条观察"，
不证明真实使用（signature ≠ usage truth）。
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.verifier.ed25519 import verify  # noqa: E402

PUBLIC_KEYS_DIR = Path(__file__).resolve().parents[1] / "keys"

CANONICAL_FIELDS = ("observation_id", "observed_at", "observer_principal", "observer_side",
                    "project_id", "tool", "outcome")


def canonical(obs: dict) -> bytes:
    return json.dumps({k: obs.get(k) for k in CANONICAL_FIELDS},
                      sort_keys=True, separators=(",", ":")).encode()


def load_public_key(key_id: str) -> Optional[bytes]:
    """从 keys/ 目录加载公钥（key_id → <key_id>.pub，base64 Ed25519）。"""
    path = PUBLIC_KEYS_DIR / f"{key_id}.pub"
    if not path.exists():
        return None
    try:
        return base64.b64decode(path.read_text().strip())
    except (ValueError, OSError):
        return None


def verify_signature(observation: dict) -> bool:
    """验证 observation 的 Ed25519 签名（canonical fields）。fail-closed。"""
    sig = observation.get("signature")
    key_id = observation.get("key_id")
    if not sig or not key_id:
        return False
    pub = load_public_key(key_id)
    if pub is None:
        return False
    try:
        return verify(pub, canonical(observation), base64.b64decode(sig))
    except Exception:
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
