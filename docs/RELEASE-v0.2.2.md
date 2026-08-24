# v0.2.2 — Conformance Hardening

> Released automatically from `docs/RELEASE-v0.2.2.md` by
> `.github/workflows/release.yml` (tag `v0.2.2`).
> Both fixes in this release were **found by the first external conformance
> pass** (Urusilla / @jaden3824, [langfuse#16383](https://github.com/langfuse/langfuse/discussions/16383))
> and were committed "before the next tag" per
> [#8](https://github.com/roy-tong/AgentMeasure/issues/8) and
> [#9](https://github.com/roy-tong/AgentMeasure/issues/9). This release is
> that commitment, delivered.

---

## The two trust-debt fixes

### #8 — Validator: root sibling constraints after `oneOf`

The bundled validator **returned after a `oneOf` branch matched**, so records
that matched a branch but were missing root-level required fields (siblings of
the root `oneOf` in FMT-002) validated successfully. Invalid records passed.
`oneOf`/`anyOf` are compositional keywords, not terminators: sibling keywords
are now always evaluated after a branch matches, and zero-match errors carry
the first branch error for diagnosis. The registry validator additionally
fails closed on unsupported composition keywords instead of silently ignoring
them. 6 regression tests added.

### #9 — Aggregator: reconcile declared operation summaries against attempt rows

The lab aggregator trusted `operation_result` declarations (`attempts`,
`outcome`) without checking the underlying `attempt` rows — a declared
"4 attempts, success" was taken at face value even if the rows said otherwise.
Now every declaration is reconciled per operation:

- declared attempt count vs actual attempt rows
- declared outcome vs the rows' derived outcome (rule op-success-any/1,
  last-attempt outcome disclosed for diagnosis)

Mismatches surface as an explicit `operation_reconciliation: failed` block
with per-operation reasons — **counts and outcomes use measured rows, never
declarations**. The canonical collector gained the same discipline:
`task_outcome` payloads persist `task_success`/`attempt_count` (optional,
never trusted) and `compute()` emits `operation_summary_reconciliation`.
Gate scenarios core-6/core-7 cover consistent, conflicting, and absent
declarations.

## First external conformance vector: `urusilla-001`

The conformance pass that found #8/#9 is now an upstream regression vector —
`conformance/vectors/external/urusilla-001/`:

- 8 project-authored synthetic events (FMT-002): one operation with a
  fail→fail→fail→success retry chain, fallback and cache roles preserved in a
  sidecar, unreduced token usage (25 units)
- `expected.json` pins every metric (reach 1, selected 1, operations 1,
  4 attempts/op, cost 25, success/consumption 1.0) and
  `schema_valid_under_fmt_002: true`
- the original mapping document ships alongside

`conformance/runners/run_external_fixture.py` guards four things:
schema validity, **#8** (stripping each root-required field must be rejected),
exact metric reproduction, and **#9** (tampered declarations must surface
`reconciliation: failed`, never silent trust).

**Claim boundary (unchanged from the source project):** this fixture is
synthetic, project-authored evidence. It is not an AgentMeasure endorsement,
a Langfuse adoption, an external reproduction, or a real provider-cost
observation.

## Conformance bundle (reproduce the pass)

Everything needed to reproduce the external pass against the fixed code:

```bash
git checkout v0.2.2
python3 conformance/runners/run_external_fixture.py
# URUSILLA-001 CONFORMANCE PASS: schema + #8 + metrics + #9 all guarded

python3 -m unittest discover -s lab/tests          # 84 tests OK
python3 scripts/canonical_core_gate.py             # 7 scenarios PASS
python3 verify_vectors.py                          # ALL VECTORS PASS
```

Bundle contents (all in-repo, versioned with this tag):

| Artifact | Path |
|---|---|
| Events (FMT-002) | `conformance/vectors/external/urusilla-001/agentmeasure_urusilla_fixture_001.events.jsonl` |
| Expected metrics | `…/agentmeasure_urusilla_fixture_001.expected.json` |
| Mapping / methodology | `…/AGENTMEASURE_URUSILLA_MAPPING_2026-08-23.md` |
| Guard runner | `conformance/runners/run_external_fixture.py` |
| Fixes | `lab/agentmeasure_lab/schemas.py`, `lab/agentmeasure_lab/analysis.py`, `reference/collector/aggregator/aggregator.py`, `reference/collector/correlator/correlator.py` |

## Also in this release

- CI runs the full lab test suite (`lab/**` previously did not trigger
  workflows) — *pending the workflow-scope commit; see repo activity for
  landing status*
- README (EN/中文) two-layer first fold: the measurement pain line first,
  the Capability Economy second
- Website hero: "Know what your agent usage metrics actually count."

**Verification at tag time:** 84 lab tests OK · core gate 7 scenarios PASS ·
all vectors PASS · registry + metric registry + canonical observation VALID ·
urusilla-001 guards PASS.
