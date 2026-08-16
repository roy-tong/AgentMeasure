#!/usr/bin/env python3
"""agent-used — Ed25519 keygen（E1 source-authenticated 密钥管理）。

用法:
  python3 keygen.py <key_id>
    → 私钥: ~/.agent-used/keys/<key_id>.key（chmod 600，本地）
    → 公钥: <repo>/collector/keys/<key_id>.pub（base64，可公开提交）

签名工具（adapter 用）:
  from collector.verifier.keygen import sign_observation
  obs["signature"] = sign_observation(obs, key_id)
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.verifier.ed25519 import publickey, sign  # noqa: E402
from collector.verifier.verifier import canonical  # noqa: E402

KEYS_DIR = Path(os.environ.get("AGENT_USED_KEYS_DIR", str(Path.home() / ".agent-used" / "keys")))
PUBLIC_DIR = Path(__file__).resolve().parents[2] / "keys"

def load_secret(key_id: str) -> bytes:
    path = KEYS_DIR / f"{key_id}.key"
    if not path.exists():
        raise FileNotFoundError(f"no private key for {key_id} at {path}")
    return base64.b64decode(path.read_text().strip())


def sign_observation(obs: dict, key_id: str) -> dict:
    """给 observation 签名（canonical fields），返回带 signature/key_id 的副本。"""
    secret = load_secret(key_id)
    sig = sign(secret, canonical(obs))
    out = dict(obs)
    out["signature"] = base64.b64encode(sig).decode()
    out["key_id"] = key_id
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 keygen.py <key_id>", file=sys.stderr)
        return 2
    key_id = sys.argv[1]
    secret = os.urandom(32)
    pub = publickey(secret)

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    secret_path = KEYS_DIR / f"{key_id}.key"
    secret_path.write_text(base64.b64encode(secret).decode())
    os.chmod(secret_path, 0o600)

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    pub_path = PUBLIC_DIR / f"{key_id}.pub"
    pub_path.write_text(base64.b64encode(pub).decode() + "\n")

    print(f"private: {secret_path} (chmod 600, 本地)")
    print(f"public:  {pub_path} (base64, 可提交公开)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
