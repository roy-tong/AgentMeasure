"""Deterministic RNG and balanced assignment (LAB-010).

Every random stream is derived from (seed, *stream_parts) via SHA-256, so the
same seed, the same engine version and the same task set always replay to the
same result. Stream parts are stable identifiers (experiment, harness, task,
variant, replicate index) — never wall-clock or iteration order.
"""

import hashlib
import json
from typing import List, Sequence, Any

_MASK64 = (1 << 64) - 1


def _mix64(z: int) -> int:
    """splitmix64 finalizer."""
    z = (z + 0x9E3779B97F4A7C15) & _MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
    return z ^ (z >> 31)


class DetRng:
    """Counter-based deterministic RNG (splitmix64 core).

    Not a cryptographic primitive; chosen for exact cross-platform
    reproducibility of integer arithmetic and adequate statistical quality
    for simulation.
    """

    def __init__(self, *stream_parts: Any):
        material = json.dumps(
            [_stable(p) for p in stream_parts], sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        digest = hashlib.sha256(b"agentmeasure-lab/rng/v1|" + material).digest()
        self._state = int.from_bytes(digest[:8], "big")
        self._counter = int.from_bytes(digest[8:16], "big")
        self._bits = 0
        self._bit_buffer = 0

    # -- primitives ---------------------------------------------------------
    def next_u64(self) -> int:
        self._counter = (self._counter + 1) & _MASK64
        return _mix64(self._state ^ self._counter)

    def random(self) -> float:
        """Uniform float in [0, 1)."""
        return self.next_u64() / float(1 << 64)

    def bernoulli(self, p: float) -> bool:
        if p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return self.random() < p

    def below(self, n: int) -> int:
        """Uniform integer in [0, n)."""
        if n <= 0:
            raise ValueError("n must be positive")
        lim = (1 << 64) - ((1 << 64) % n)
        while True:
            x = self.next_u64()
            if x < lim:
                return x % n

    def choice(self, seq: Sequence[Any]) -> Any:
        return seq[self.below(len(seq))]

    def shuffle(self, seq: List[Any]) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = self.below(i + 1)
            seq[i], seq[j] = seq[j], seq[i]

    def unit_normal(self) -> float:
        """Standard normal draw via Box-Muller."""
        u1 = max(self.random(), 2.0 / (1 << 64))
        u2 = self.random()
        import math

        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    # -- discrete distributions used by the mock harness ---------------------
    def binomial(self, n: int, p: float) -> int:
        return sum(1 for _ in range(n) if self.bernoulli(p))


def _stable(value: Any) -> Any:
    """Normalize stream parts so (seed parts) hash independent of key order."""
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in sorted(value.items(), key=lambda kv: kv[0])}
    if isinstance(value, (list, tuple)):
        return [_stable(v) for v in value]
    return value


def balanced_variant_sequence(replicates: int, variant_ids: Sequence[str], rng: DetRng) -> List[str]:
    """Balanced, deterministic variant assignment (LAB-010).

    Each variant receives floor(replicates/len) or ceil(replicates/len)
    assignments; order is shuffled deterministically. Balance is verifiable
    from the emitted events (per-arm reach counts).
    """
    if not variant_ids:
        raise ValueError("variant_ids must be non-empty")
    if replicates < 0:
        raise ValueError("replicates must be >= 0")
    seq: List[str] = []
    base, extra = divmod(replicates, len(variant_ids))
    for i, v in enumerate(variant_ids):
        seq.extend([v] * (base + (1 if i < extra else 0)))
    rng.shuffle(seq)
    return seq
