# External contribution card — rksharma-owg (001)

Date issued: 2026-10-08
Card series: AgentMeasure external contributor cards (public, named, opt-out)

## Who

[rksharma-owg](https://github.com/rksharma-owg) — external contributor. This card
uses only public data: the pull request text, its diff, and its CI records as
visible on GitHub. No private correspondence is quoted.

## What they contributed

[PR #27 — "fix: enforce cross-file replay conformance vector"](https://github.com/roy-tong/AgentMeasure/pull/27),
merged 2026-10-02 (merge commit `739d35a8f63f6e73569d724c2018d257e5a0a3ad`,
authored on branch `fix/conformance-cross-file-replay`).

Before the fix, the execution-grain runner dispatched every vector through the
invocation-shaped path, so the file-shaped `cross-file-fork-replay-mixed-identity`
vector crashed the conformance job with `KeyError: 'invocations'` at 21/22
vectors. The fix adds dispatch for file-shaped replay vectors to a
fixture-level checker that enforces the vector's published disclosures:

- `unique_turns` = 3 (the replayed prefix counts once, not per file)
- `replayed_prefix_counted` = 1
- `child_new_counted` = 1 (genuinely new child work counts)
- `attempts_retained` = 5 (attempts and cost for real work stay auditable)
- `unstable_identity_mode` (no stable cross-file id → structural prefix
  detection required; identity is UNPROVABLE, never a confident single)

The contributor ran the full workflow (spec-conformance,
reference-implementation, healthcheck on Python 3.9/3.11, lab-suite, sdk-gate,
documentation-consistency) on their fork before submitting —
[workflow run 36085957579](https://github.com/rksharma-owg/AgentMeasure/actions/runs/36085957579).

## Why it matters

This card is the enforcement half of a disclosure that was previously
"planned and disclosed as not-yet-machine-checked" (see the vector's
`external_evidence` note). With the merge, the fork/replay counting rules are
machine-checked on every CI run instead of trusted on paper.

## Claim boundary

- This card describes one merged pull request. It is not a statement about the
  contributor's views on AgentMeasure, an endorsement in either direction, or
  a claim of ongoing affiliation.
- Only public repository data is used. The contributor did not review this
  card before publication.
- **The contributor may request changes or removal of this card at any time**
  via a GitHub issue on this repository or a reply through the contact in the
  commit trail — no questions asked.

## Files in this card

- `rksharma-001-cross-file-replay-fixture.json` — standalone extract of the
  file-shaped vector input and expected disclosures (fixture).
- `RECOMPUTE.md` — how to re-run the enforcement locally and what output to
  expect (recomputation note).
