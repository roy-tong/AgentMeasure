# Verovo Conformance Pack v0.1

**Does your agent metric actually mean what its label says?**

Turn measurement assumptions into CI checks. The pack reads *your* FMT-002
fixture and reports `PASS / FAIL / UNPROVABLE` per invariant — and
`UNPROVABLE` is a first-class result: when the evidence to decide is absent,
it is reported as a finding, never folded into a count or a zero.

## First run from an installed CLI

Use CLI **0.7.1 or newer**. The 0.7.0 wheel omitted a required module; upgrade
before running conformance. No repository clone is needed for this path:

```bash
python -m pip install --upgrade verovo
verovo conformance --new-vector my-sample --out ./vectors
verovo conformance --fixture ./vectors/my-sample-001/verovo_my_sample_fixture_001.events.jsonl --json result.json
```

The scaffold is synthetic and valid as generated: 4 PASS, 1 UNPROVABLE for its
zero-cost sample; token/cache checks are NOT-SUPPORTED. The output names the
actual fixture and metadata paths. Keep the synthetic label until you replace
it with real evidence. Default scaffolding writes under your current directory,
never into the Python installation. Existing names are refused rather than overwritten.

For your own data, use genuine session/operation/attempt identities. Without
`--claims`, results only concern the sample's internal consistency. For a free
fit review before a $20 check, send your native schema and redacted sample rows;
you do not have to perform the mapping first. [Service scope](https://roy-tong.github.io/Verovo/services.html#qa20).

## Use

```bash
python3 conformance/pack/verovo conformance --fixture my-fixture.jsonl
# optional: --metadata sidecar.json  --claims observed-claims.json
#            --json report.json      --require execution-grain,retry-reconciliation
python3 conformance/pack/verovo selftest   # repository fixtures, no caller input
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
- uses: roy-tong/Verovo@<commit-sha>
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
