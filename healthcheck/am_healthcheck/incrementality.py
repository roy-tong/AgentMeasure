"""Incrementality evidence — statistics, not verdicts (BP r28 p15 third question).

"没有 Agent，这笔交易是否本来也会发生？" is a causal question. Rules cannot
answer it; this module does not pretend to. What it supplies is the honest
statistical layer UNDER such a claim: treatment vs holdout rates, a pooled
two-proportion z-test, and a Newcombe hybrid-score confidence interval for
the difference — the same estimator family the lab's honest-statistics layer
uses, standard library only.

Hard claim boundary, printed on every output: this is evidence ABOUT a
difference, never a billing verdict. A PASS/FAIL is not produced here, by
design — that is the BP's line between 规则判定 and 因果推断, kept visible.

Guards: tiny or one-sided samples return `insufficient_evidence` rather than
a confident-looking p-value; groups are named, never imputed.
"""
from __future__ import annotations

import csv
import math
from typing import Any, Dict, List, Optional, Tuple


class IncrementalityError(ValueError):
    pass


def load_groups(path: str, group_col: str = "group",
                outcome_col: str = "converted") -> Dict[str, List[int]]:
    """rows: group in {treatment, holdout}, outcome 0/1."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        if group_col not in fields or outcome_col not in fields:
            raise IncrementalityError(
                "need %r and %r columns; got: %s"
                % (group_col, outcome_col, ", ".join(reader.fieldnames or [])))
        groups: Dict[str, List[int]] = {"treatment": [], "holdout": []}
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            group = row.get(group_col, "")
            if group not in groups:
                raise IncrementalityError(
                    "line %d: group %r is neither treatment nor holdout"
                    % (i + 2, group))
            outcome = row.get(outcome_col, "").lower()
            if outcome not in ("0", "1", "yes", "no", "true", "false"):
                raise IncrementalityError(
                    "line %d: outcome %r is not a 0/1 value" % (i + 2, outcome))
            groups[group].append(1 if outcome in ("1", "yes", "true") else 0)
    return groups


def _wilson_interval(successes: int, n: int,
                     z: float = 1.959963984540054) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _newcombe_diff_interval(s1: int, n1: int, s2: int, n2: int,
                            z: float = 1.959963984540054) -> Tuple[float, float]:
    """Newcombe hybrid-score interval for p1 - p2 (method 10)."""
    l1, u1 = _wilson_interval(s1, n1, z)
    l2, u2 = _wilson_interval(s2, n2, z)
    d = (s1 / n1 if n1 else 0.0) - (s2 / n2 if n2 else 0.0)
    lower = d - math.sqrt((s1 / n1 - l1) ** 2 + (u2 - s2 / n2) ** 2) if n1 and n2 else -1.0
    upper = d + math.sqrt((u1 - s1 / n1) ** 2 + (s2 / n2 - l2) ** 2) if n1 and n2 else 1.0
    return (max(-1.0, lower), min(1.0, upper))


def analyze(groups: Dict[str, List[int]]) -> Dict[str, Any]:
    t, h = groups["treatment"], groups["holdout"]
    n1, n2 = len(t), len(h)
    s1, s2 = sum(t), sum(h)
    result: Dict[str, Any] = {
        "schema": "agentmeasure.research/incrementality-evidence",
        "schema_version": "0.1.0",
        "treatment": {"n": n1, "converted": s1,
                      "rate": round(s1 / n1, 4) if n1 else None},
        "holdout": {"n": n2, "converted": s2,
                    "rate": round(s2 / n2, 4) if n2 else None},
        "claim_boundary": "statistical evidence about a difference; never a "
                          "billing verdict — rules judge billing, statistics "
                          "speak only here",
    }
    if n1 < 1 or n2 < 1:
        result["verdict_band"] = "insufficient_evidence"
        result["note"] = "one group has no observations; nothing is estimated"
        return result

    p1, p2 = s1 / n1, s2 / n2
    diff = p1 - p2
    pooled = (s1 + s2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z_value = (diff / se) if se > 0 else None
    p_value = (2 * (1 - 0.5 * (1 + math.erf(abs(z_value) / math.sqrt(2)))) 
               if z_value is not None else None)
    lo, hi = _newcombe_diff_interval(s1, n1, s2, n2)

    result["difference"] = {
        "rate_difference": round(diff, 4),
        "ci95_newcombe": [round(lo, 4), round(hi, 4)],
        "pooled_z": round(z_value, 4) if z_value is not None else None,
        "p_value_two_sided": (round(p_value, 6)
                              if p_value is not None else None),
    }
    if n1 < 30 or n2 < 30:
        result["verdict_band"] = "insufficient_evidence"
        result["note"] = ("n < 30 per arm: the interval is reported but no "
                          "confidence language is earned; plan the next round "
                          "before quoting this")
    elif lo > 0:
        result["verdict_band"] = "positive_difference"
    elif hi < 0:
        result["verdict_band"] = "negative_difference"
    else:
        result["verdict_band"] = "no_detectable_difference"
        result["note"] = "the interval covers zero — say exactly that, no more"
    return result


def report_text(result: Dict[str, Any]) -> str:
    W = 58
    out = ["Incrementality evidence — treatment vs holdout", "=" * W]
    for side in ("treatment", "holdout"):
        g = result[side]
        rate = ("%.1f%%" % (g["rate"] * 100)) if g["rate"] is not None else "—"
        out.append("%-11s n=%-5d converted=%-5d rate=%s"
                   % (side, g["n"], g["converted"], rate))
    out.append("")
    if "difference" in result:
        d = result["difference"]
        out.append("difference: %+.1fpp  CI95 [%+.1fpp, %+.1fpp] (Newcombe)"
                   % (d["rate_difference"] * 100,
                      d["ci95_newcombe"][0] * 100, d["ci95_newcombe"][1] * 100))
        if d.get("p_value_two_sided") is not None:
            out.append("two-sided p (pooled z): %.6f" % d["p_value_two_sided"])
    out.append("band: %s" % result["verdict_band"])
    if result.get("note"):
        out.append(result["note"])
    out.append("")
    out.append(result["claim_boundary"] + ".")
    return "\n".join(out)
