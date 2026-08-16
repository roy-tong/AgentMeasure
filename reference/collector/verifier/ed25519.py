"""Pure-python Ed25519（public domain，基于 ref10 参考实现）。

保持 AgentMeasure 零依赖承诺；仅用于 E1 source-authenticated 的签名/验签。
生产建议：可用 libsodium/cryptography 替换（接口一致：sign/verify/publickey）。
"""
from __future__ import annotations

import hashlib

P = 2 ** 255 - 19
L = 2 ** 252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
I = pow(2, (P - 1) // 4, P)


def _inv(x):
    return pow(x, P - 2, P)


def _xrecover(y):
    xx = (y * y - 1) * _inv(D * y * y + 1)
    x = pow(xx, (P + 3) // 8, P)
    if (x * x - xx) % P:
        x = x * I % P
    if x % 2:
        x = P - x
    return x


By = 4 * _inv(5) % P
Bx = _xrecover(By)
B = (Bx, By, 1, (Bx * By) % P)


def _edwards_add(P_, Q_):
    x1, y1, z1, t1 = P_
    x2, y2, z2, t2 = Q_
    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = t1 * 2 * D * t2 % P
    dd = z1 * 2 * z2 % P
    e = b - a
    f = dd - c
    g = dd + c
    h = b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _scalarmult(P_, e):
    if e == 0:
        return (0, 1, 1, 0)
    Q_ = _scalarmult(P_, e // 2)
    Q_ = _edwards_add(Q_, Q_)
    if e & 1:
        Q_ = _edwards_add(Q_, P_)
    return Q_


def _encodepoint(P_):
    x, y, z, _ = P_
    zi = _inv(z)
    x = x * zi % P
    y = y * zi % P
    n = y | ((x & 1) << 255)
    return n.to_bytes(32, "little")


def _decodeint(s):
    return int.from_bytes(s, "little")


def _decodepoint(s):
    y = _decodeint(s) & ((1 << 255) - 1)
    x = _xrecover(y)
    if (x & 1) != ((_decodeint(s) >> 255) & 1):
        x = P - x
    return (x, y, 1, (x * y) % P)


def _hash(m):
    return hashlib.sha512(m).digest()


def publickey(seed: bytes) -> bytes:
    """seed(32) → 公钥(32)。"""
    h = _hash(seed)
    a = _decodeint(h[:32])
    a &= (1 << 254) - 8
    a |= 1 << 254
    return _encodepoint(_scalarmult(B, a))


def sign(seed: bytes, msg: bytes) -> bytes:
    """seed(32) → 签名(64)。"""
    h = _hash(seed)
    a = _decodeint(h[:32])
    a &= (1 << 254) - 8
    a |= 1 << 254
    r = _decodeint(_hash(h[32:] + msg)) % L
    R = _encodepoint(_scalarmult(B, r))
    hram = _decodeint(_hash(R + _encodepoint(_scalarmult(B, a)) + msg)) % L
    S = (r + hram * a) % L
    return R + S.to_bytes(32, "little")


def verify(public: bytes, msg: bytes, signature: bytes) -> bool:
    try:
        A = _decodepoint(public)
        R = _decodepoint(signature[:32])
        S = _decodeint(signature[32:])
        if S >= L:
            return False
        hram = _decodeint(_hash(signature[:32] + public + msg)) % L
        lhs = _scalarmult(B, S)
        rhs = _edwards_add(R, _scalarmult(A, hram))
        return _encodepoint(lhs) == _encodepoint(rhs)
    except Exception:
        return False
