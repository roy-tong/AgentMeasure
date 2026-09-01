# AgentMeasure Conformance Pack v0.1

**Does your agent metric actually mean what its label says?**

Turn measurement assumptions into CI checks. The pack reads *your* FMT-002
fixture and reports `PASS / FAIL / UNPROVABLE` per invariant — and
`UNPROVABLE` is a first-class result: when the evidence to decide is absent,
it is reported as a finding, never folded into a count or a zero.

## Use

```bash
python3 conformance/pack/agentmeasure conformance --fixture my-fixture.jsonl
# optional: --metadata sidecar.json  --claims observed-claims.json
#            --json report.json      --require execution-grain,retry-reconciliation
python3 conformance/pack/agentmeasure selftest   # repository fixtures, no caller input
```

- Without `--claims`: data-consistency checks and reference computation only.
  No statement is made about any implementation's reported metrics.
- With `--claims`: claimed values are compared against computation; a
  mismatch (e.g. an operation-grain metric actually aggregated at assignment
  grain — the AM-U-007 class) is a `FAIL`.
- Exit codes: `0` no FAIL · `1` FAIL present, or a `--require`d invariant
  not PROVEN · `2` usage/input error (invalid JSON, schema violation).

## GitHub Action

```yaml
- uses: roy-tong/AgentMeasure@<commit-sha>
  with:
    fixture: fixtures/telemetry.jsonl   # relative to YOUR workspace
    # claims: fixtures/claims.json      # optional
    # require: execution-grain          # optional: make UNPROVABLE blocking
```

The Action reads the fixture from the calling workspace, never from this
repository, and appends the report to the job summary.

## v0.1 invariants

| id | status | checks |
| --- | --- | --- |
| execution-grain | supported | retry chain under one declared operation resolves to one operation |
| retry-reconciliation | supported | declared attempt counts reconcile against attempt rows |
| cost-preservation | supported | grouping never removes attempt-level cost |
| operation-grain | supported | operation-grain metrics aggregate at operation grain |
| evidence-boundary | supported | undecidable quantities are disclosed, not zeroed |
| token-subset | **not-supported** | needs a token-evidence contract (core FMT-002 has no token fields) |
| cache-distinction | **not-supported** | needs a cache-evidence contract (no cache-hit signal) |

`not-supported` is reported explicitly. We do not pass rules we cannot check.

## Input contract

- **events**: FMT-002 funnel-event JSONL (`lab/schemas/funnel-event.schema.json`)
- **metadata** (optional sidecar): `source`, `time_window`,
  `observation_surface`, `data_class: production|synthetic`
- **claims** (optional): your reported metric values, e.g.
  `{"median_steps_per_operation": 2.5}`

Raw data stays local; a fixture is only shared where you choose to.
