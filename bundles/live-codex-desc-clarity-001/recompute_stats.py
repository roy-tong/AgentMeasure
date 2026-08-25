#!/usr/bin/env python3
"""Independent statistics-layer recomputation for the
live-codex-desc-clarity-001 honest-provenance bundle.

What this verifies
------------------
Starting ONLY from the per-arm counts (numerator / denominator) recorded in
the official report for the preregistered primary metric, recompute:

  - arm rates and the difference,
  - the pooled two-proportion z-test (two-sided p-value),
  - the Newcombe hybrid-score (method 10) CI95 for the difference,

and compare them against the report's own `primary_comparison` block.

What this does NOT verify
------------------------
Raw events, the preregistration manifest, and the run directory were not
retained when the live run executed (they lived under gitignored paths and
were not exported at tag time — see MANIFEST.md). This script therefore
verifies **statistical-layer consistency**, not full replay. The bundle's
evidence label is accordingly `stats-recomputable`, not `bundle-verifiable`.

Usage
-----
    python3 bundles/live-codex-desc-clarity-001/recompute_stats.py
    python3 bundles/live-codex-desc-clarity-001/recompute_stats.py --report <path>

Stdlib only. Exits 0 on full agreement, 1 on any mismatch.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

TOL = 5e-4  # reports round to 4-6 decimals; anything larger than this is a real disagreement


def wilson_interval(x: int, n: int, z: float = 1.959963985):
    """Wilson score interval for a single proportion."""
    p = x / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def newcombe_diff_ci(x_t: int, n_t: int, x_c: int, n_c: int):
    """Newcombe hybrid-score interval for a difference of independent proportions."""
    p_t, p_c = x_t / n_t, x_c / n_c
    lt, ut = wilson_interval(x_t, n_t)
    lc, uc = wilson_interval(x_c, n_c)
    low = (p_t - p_c) - math.sqrt((p_t - lt) ** 2 + (uc - p_c) ** 2)
    high = (p_t - p_c) + math.sqrt((ut - p_t) ** 2 + (p_c - lc) ** 2)
    return low, high


def pooled_z_two_sided(x_t: int, n_t: int, x_c: int, n_c: int):
    """Two-proportion z-test with pooled variance, no continuity correction."""
    p_pool = (x_t + x_c) / (n_t + n_c)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_t + 1 / n_c))
    if se == 0:
        return 0.0, 1.0
    z = (x_t / n_t - x_c / n_c) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, p


def close(a, b, tol=TOL):
    return abs(a - b) <= tol


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=os.path.join(here, "report.json"))
    args = ap.parse_args()

    rep = json.load(open(args.report, encoding="utf-8"))
    primary = rep["preregistration"]["primary_metric"]
    alpha = rep["preregistration"]["alpha"]

    variants = {v["variant_id"]: v for v in rep["variants"]}
    baseline_ids = [vid for vid, v in variants.items() if v.get("baseline")]
    treatment_ids = [vid for vid, v in variants.items() if not v.get("baseline")]
    if len(baseline_ids) != 1 or len(treatment_ids) != 1:
        print(f"FAIL: expected exactly one baseline and one treatment, got "
              f"{baseline_ids} vs {treatment_ids}")
        return 1
    c_id, t_id = baseline_ids[0], treatment_ids[0]

    def arm_counts(vid):
        m = variants[vid]["metrics"][primary]
        return m["numerator"], m["denominator"]

    x_c, n_c = arm_counts(c_id)
    x_t, n_t = arm_counts(t_id)
    comp = variants[t_id]["primary_comparison"]

    checks = []

    # --- recompute from counts only ---
    p_t, p_c = x_t / n_t, x_c / n_c
    diff = p_t - p_c
    z, p_value = pooled_z_two_sided(x_t, n_t, x_c, n_c)
    lo, hi = newcombe_diff_ci(x_t, n_t, x_c, n_c)

    # --- compare against the report ---
    checks.append(("arm n (treatment)", n_t, comp["candidate"]["n"], n_t == comp["candidate"]["n"]))
    checks.append(("arm n (control)", n_c, comp["control"]["n"], n_c == comp["control"]["n"]))
    checks.append(("treatment rate", p_t, comp["candidate"]["value"], close(p_t, comp["candidate"]["value"])))
    checks.append(("control rate", p_c, comp["control"]["value"], close(p_c, comp["control"]["value"])))
    checks.append(("difference", diff, comp["difference"], close(diff, comp["difference"])))
    checks.append(("z statistic", z, comp["z"], close(z, comp["z"], tol=5e-3)))
    checks.append(("p_value (pooled z, two-sided)", p_value, comp["p_value"], close(p_value, comp["p_value"])))
    ci = comp["diff_ci95"]
    checks.append(("diff CI95 low (Newcombe)", lo, ci[0], close(lo, ci[0])))
    checks.append(("diff CI95 high (Newcombe)", hi, ci[1], close(hi, ci[1])))

    print(f"experiment        : {rep['experiment_id']}")
    print(f"primary metric    : {primary}  (alpha={alpha})")
    print(f"arms              : {t_id} {x_t}/{n_t}  vs  {c_id} {x_c}/{n_c}")
    print(f"recomputed diff   : {diff:+.4f}")
    print(f"recomputed CI95   : [{lo:.4f}, {hi:.4f}]  (Newcombe hybrid-score)")
    print(f"recomputed z / p  : z={z:.4f}, p={p_value:.6f}  (pooled two-proportion z-test)")
    print()

    ok = True
    for name, got, want, passed in checks:
        mark = "PASS" if passed else "FAIL"
        ok &= passed
        print(f"  [{mark}] {name:34s} recomputed={got!r:<24} report={want!r}")

    verdict = comp.get("verdict") or variants[t_id].get("verdict")
    print()
    print(f"report verdict    : {verdict}  (alpha={alpha}: "
          f"{'significant' if p_value < alpha else 'not significant'} → "
          f"{'agrees' if (p_value < alpha) == (verdict not in ('null_result',)) else 'DISAGREES'})")
    print()
    if ok:
        print("RESULT: statistics layer fully reproduced from per-arm counts.")
        print("Evidence label: stats-recomputable (raw events not retained — see MANIFEST.md).")
        return 0
    print("RESULT: MISMATCH — statistics layer does not reproduce.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
