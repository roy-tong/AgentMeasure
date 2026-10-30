# Run-book — a free measurement run, end to end

> The procedure the maintainers follow, open for anyone to run themselves.
> Two shapes: **A. local-log anomaly review** (one machine, one anomaly) and
> **B. metering QA** (one event sample, one ruleset, one question). Both free.

## 0. Intake — what to accept, in one look

**Shape A** accepts a `summary.json` produced by `verovo share`
(aggregate counts — enough for triage and evidence boundaries). Specific fix
steps need a manually redacted error excerpt (tool name + first error), always
optional. Never ask for raw logs.

**Shape B** accepts an event stream, native or mapped, judged in three ways
(the full table is in [fmt002-input-and-mapping.md](fmt002-input-and-mapping.md) §1):

- event grain with stable ids and outcomes → **acceptable**
- aggregate counts only, no event stream → **not acceptable** (operation/retry
  invariants would be all-UNPROVABLE; say so up front — that itself is a valid answer)
- half-events (calls without operation ownership) → **narrowed scope** or fix
  the ownership fields first

Sanitization is the requester's own call and is stated in the report verbatim:
what was redacted, what window, synthetic or production-derived.

## 1. Analysis — the actual commands

**Shape A (local anomaly)**:

```bash
pip install --upgrade verovo
verovo check --json report.json
verovo share report.json --out summary.json
verovo validate summary.json
```

The requester runs these locally and sends only `summary.json` (inspect it
before sending; nothing is auto-uploaded). The review then interprets: what
the counts support, what stays unknown, the next checks.

**Shape B (metering QA), four steps**:

```bash
# 1. Fill map.json from the requester's schema (envelope + event_rules + translate)
#    — see fmt002-input-and-mapping.md §3; first mapping ≈ 10 minutes
# 2. Convert (must print dropped=0; any defect refuses the whole input):
python3 scripts/map_to_fmt002.py --mapping map.json --input sample.jsonl --out fmt002.jsonl
# 3. Adjudicate (add --claims only if the requester reports a number):
python3 conformance/pack/run_pack.py conformance \
  --fixture fmt002.jsonl --claims claims.json --json res.json
# 4. Archive map.json — the requester's next sample reuses it
```

## 2. Report

Fill [report-template-healthcheck.md](report-template-healthcheck.md) or
[report-template-metering-qa.md](report-template-metering-qa.md). The
non-negotiables:

- every verdict binds to its invariant; NOT-SUPPORTED stated, not hidden
- UNPROVABLE is written where the sample cannot see, with the missing field named
- the exact rerun command line is included; exit codes explained
  (0 = no FAIL; 1 = FAIL or an unproven required invariant; 2 = input error)
- for operation-grain differences: the steps measure is **the sum over all
  attempts of the operation, retries included** — a requester reporting only
  the successful attempt's steps is the canonical retry-amplification
  undercount, not a median arithmetic error

## 3. After delivery

One clarification round is part of the run. New tasks start a new run with a
freshly agreed scope. If the run was useful, a star on the repo helps others
find it — never required, never a condition.
