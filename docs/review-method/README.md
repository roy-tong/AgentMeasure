# Review Method — how a free measurement run is actually done

> Since 2026-10-21 the project is entirely free and open source. The paid
> diagnostics previously offered ($10 healthcheck anomaly review, $20 metering
> QA) are retired — **their method is now open**. This directory is that
> method: the same intake checks, the same commands, the same report
> discipline the maintainers use when someone brings a sample to
> [issue #6](https://github.com/roy-tong/verovo/issues/6). Run it on
> your own data, or bring the sample and we run it with you — both are free.

## What is here

| File | What it is |
|---|---|
| [run-book.md](run-book.md) | The end-to-end procedure: intake → fit check → analysis commands → report → rerun instructions |
| [fmt002-input-and-mapping.md](fmt002-input-and-mapping.md) | Turning your arbitrary event stream into FMT-002 JSONL: the three intake verdicts, the mapping table format, known boundaries |
| [report-template-healthcheck.md](report-template-healthcheck.md) | Report template for one local-log anomaly review |
| [report-template-metering-qa.md](report-template-metering-qa.md) | Report template for one metering sample / ruleset / question |
| [`scripts/map_to_fmt002.py`](../scripts/map_to_fmt002.py) | The mapper itself — field moves and enum translation only, refuses whole-input on any defect (`scripts/test_map_to_fmt002.py`) |

## The discipline, in one paragraph

Only real identities, never invented defaults: missing evidence becomes
UNPROVABLE in the report, not a zero in the data. Every verdict binds to the
invariant that produced it (PASS / FAIL / UNPROVABLE — the same vocabulary as
the public claims index). "No finding" and "not enough evidence" are valid
results. The requester can rerun every check from the command line in the
report. If the check was useful, a star on the repo helps others find it —
never required, never a condition.

## Related

- Provider-facing runs (MCP/API providers, canonical observations):
  [provider-onboarding.md](provider-onboarding.md) and
  [registry/provider-mapping.md](../registry/provider-mapping.md)
- The public claims index these verdicts share vocabulary with:
  [claims.html](https://roy-tong.github.io/verovo/claims.html)
- Historical scope notes: [paid-review-scope.md](paid-review-scope.md)
  (superseded — kept for the record)
