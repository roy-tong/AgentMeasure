# MANIFEST — live-codex-desc-clarity-001 (honest-provenance bundle)

**Evidence label: `stats-recomputable`** — downgraded from `bundle-verifiable`.
This is an honest downgrade, documented below, not a euphemism.

## What this experiment is

Live validation round of the AgentMeasure Lab experiment engine against a real
harness (codex-cli 0.149.0-alpha, 2026-08-22). Hypothesis: a clearer tool
description raises real-agent selection rate. Result: **honest null** —
`clear 1/4 (25%)` vs `control 0/4 (0%)`, difference +25.0pp,
CI95 [-0.2808, 0.6994], pooled z-test two-sided p = 0.285049, verdict
`null_result` at alpha = 0.05. The report's own power note: to resolve an
effect of the observed size, plan ≈31 per arm next round.

## What is in this bundle

| File | Role |
| --- | --- |
| `report.json` | The official engine report, verbatim (schema `agentmeasure.lab/report` v1.0.0, engine v0.4.0). Carries the preregistration `manifest_hash` (31c1c298…) and the `run_fingerprint` (d6b161fd…) inside it. |
| `recompute_stats.py` | Independent recomputation of the statistics layer from per-arm counts only (stdlib). Compares against the report's `primary_comparison`; exits non-zero on any disagreement. |
| `MANIFEST.md` | This file — provenance, limits, downgrade rationale. |

## What happened to the raw four-piece set

The canonical bundle-verifiable set is: preregistration manifest, raw events
(JSONL), run metadata, report. **The first three were not retained** for this
run: live execution wrote them under gitignored paths (`runs/`,
`.agentmeasure/`), and no export step existed at the time. They are **not
recoverable, and are not reconstructed** — fabricating them would be worse
than the gap.

## What a third party can and cannot verify

CAN, from this bundle alone:

- Recompute difference / z / p / Newcombe CI95 from per-arm counts and confirm
  they match the report exactly: `python3 recompute_stats.py` (9/9 checks).
- Confirm the recorded preregistration parameters (alpha = 0.05, primary
  metric = selection_rate, min 4/arm) match the analysis actually performed.
- Confirm the verdict logic: p = 0.285 ≥ 0.05 → `null_result`, and the report
  resists the tempting misread (CI width is reported; "honest null, not
  evidence of no effect").

CANNOT, from this bundle alone:

- Replay ingestion from raw events, or re-derive per-arm counts independently.
- Verify the run fingerprint against a retained run directory.
- Verify per-condition (per-harness) breakdowns beyond what the report states.

## Terminology note (provenance over retrofit)

`report.json` predates the two-state consumption reframing (DR-005 revised;
`consumption_rate` as named there is what the current spec calls
context-availability evidence at operation grain). The artifact is kept
verbatim; the spec moved on. Do not edit history to match vocabulary.

## Process fix (so this cannot recur)

1. `release.yml` now attaches every `bundles/<experiment-id>/` as release
   assets at tag time.
2. Release checklist (docs/RELEASE template + lab README): after a live run,
   copy the four-piece set from the run directory into
   `bundles/<experiment-id>/` **before** tagging. `am lab history` resolves
   the run directory.
3. CI (`conformance.yml`) executes `recompute_stats.py` on every push, so any
   future edit to the report or the recomputation trips the build.

— recorded 2026-08-25, resolving the last item of the 8/25–8/28 trust-debt
window (PRD v0.5 §6.1) ahead of schedule.
