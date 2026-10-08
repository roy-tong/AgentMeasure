# Recompute — rksharma-001 cross-file replay enforcement

How to independently re-verify the claim on this card: that the fork/replay
disclosures of `cross-file-fork-replay-mixed-identity` are machine-checked,
and that this enforcement was absent before PR #27.

## A. Verify enforcement on current main

```bash
git clone https://github.com/roy-tong/AgentMeasure.git
cd AgentMeasure
python3 conformance/runners/run_metrics.py 2>&1 | tail -6
```

Expected tail (verified 2026-10-08 on commit `07e1a27`):

```
  ✓ [M3.1/M3.3 Execution Grain — Operation vs Attempt] cross-file-fork-replay-mixed-identity
  ...
22/22 vectors PASS
```

The `cross-file-fork-replay-mixed-identity` line is the enforcement this card
credits to rksharma-owg's PR #27.

## B. Verify the failure mode the PR fixed (historical)

```bash
git checkout dff5529990ffd2750f57ebc71227059b161e34a3   # PR #27 base commit
python3 conformance/runners/run_metrics.py
```

Expected: the job stops with `KeyError: 'invocations'` at 21/22 vectors,
because file-shaped (`files` + `expected`) vectors had no dispatch path.

## C. Verify the merge itself

- PR: https://github.com/roy-tong/AgentMeasure/pull/27
- Merge commit: `739d35a8f63f6e73569d724c2018d257e5a0a3ad` (2026-10-02)
- Changed file: `conformance/runners/run_metrics.py` (+48 lines)
- Contributor CI evidence:
  https://github.com/rksharma-owg/AgentMeasure/actions/runs/36085957579

## D. Check the fixture numbers by hand

Using `rksharma-001-cross-file-replay-fixture.json`:

- parent turns: 2 (`pc-1`, `pc-2` under `op-p`)
- child rows: 3 (2 verbatim replays + 1 new turn `cc-1` under `op-c`)
- unique turns = 2 (parent, counted once) + 1 (child-new) = **3**
- attempts retained = 2 + 3 = **5**
- replayed prefix contributes **no fresh cost**; only `cc-1` is new work
- identity across files is unstable → structural prefix detection required;
  identity is **UNPROVABLE**, never a confident single count

All recomputation is offline, deterministic, and uses only the public
repository. If your run disagrees with any number above, open an issue —
the card and the verdicts are separable, and the verdict wins.
