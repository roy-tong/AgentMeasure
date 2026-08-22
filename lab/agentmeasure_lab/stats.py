"""Honest statistics for funnel comparisons (LAB-007/008, ATTR-001).

Design rules taken from the PRD's product discipline (§4.4):
- no bare point estimates: every rate ships with a confidence interval;
- insufficient sample => "undetermined" plus the required sample size,
  never a silently underpowered verdict;
- two-sided tests only; alpha comes from the preregistered analysis plan.
"""

import math
from typing import Optional, Tuple
from statistics import NormalDist

_ND = NormalDist()

# Common two-sided z values (z_{alpha/2}).
Z_FOR_ALPHA = {0.10: 1.6448536269514722, 0.05: 1.959963984540054, 0.01: 2.5758293035489004}


def z_two_sided(alpha: float) -> float:
    if alpha in Z_FOR_ALPHA:
        return Z_FOR_ALPHA[alpha]
    return _ND.inv_cdf(1.0 - alpha / 2.0)


def clamp01(p: float) -> float:
    return min(1.0, max(0.0, p))


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> Optional[Tuple[float, float]]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (clamp01(centre - half), clamp01(centre + half))


def two_proportion_z_test(k1: int, n1: int, k2: int, n2: int) -> Optional[Tuple[float, float]]:
    """Pooled two-sided z test for p2 - p1. Returns (z, p_value) or None."""
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1.0 / n1 + 1.0 / n2))
    if se == 0.0:
        return (0.0, 1.0)
    z = (p2 - p1) / se
    p_value = 2.0 * (1.0 - _ND.cdf(abs(z)))
    return (z, min(1.0, max(0.0, p_value)))


def newcombe_diff_interval(
    k1: int, n1: int, k2: int, n2: int, z: float = 1.959963984540054
) -> Optional[Tuple[float, float]]:
    """Newcombe (method 10) CI for the difference p2 - p1.

    Recommended over the Wald interval for proportions near 0 or 1; built
    from the two Wilson intervals.
    """
    if n1 <= 0 or n2 <= 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    w1 = wilson_interval(k1, n1, z)
    w2 = wilson_interval(k2, n2, z)
    if w1 is None or w2 is None:
        return None
    l1, u1 = w1
    l2, u2 = w2
    d = p2 - p1
    lower = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    upper = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return (max(-1.0, lower), min(1.0, upper))


def required_n_per_arm(p1: float, p2: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Minimum per-arm n to detect p2 - p1 at (alpha, power), normal approx."""
    if p1 == p2:
        raise ValueError("p1 == p2: no difference to detect")
    za = z_two_sided(alpha)
    zb = _ND.inv_cdf(power)
    d = abs(p2 - p1)
    varsum = p1 * (1 - p1) + p2 * (1 - p2)
    return int(math.ceil((za + zb) ** 2 * varsum / (d * d)))


def median(values) -> Optional[float]:
    vs = sorted(v for v in values)
    if not vs:
        return None
    m = len(vs) // 2
    if len(vs) % 2 == 1:
        return float(vs[m])
    return (vs[m - 1] + vs[m]) / 2.0
