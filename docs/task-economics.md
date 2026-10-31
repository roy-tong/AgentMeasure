# Task economics: technical, financial and business ledgers

`verovo economics` is a local deterministic calculation over an explicit case
file. It does not parse contracts, call vendors, estimate missing invoices or
infer a task from timestamps.

## Input

The case contains:

- `tasks`: the business unit being costed (`task_id`);
- `runs`: agent executions linked by an explicit `task_id`;
- `usage`: technical usage rows, included as money only when
  `financialized=true` and a `cost`, `currency` and `source_ref` are present;
- `documents`: invoices/bills used for coverage and source traceability;
- `cost_items`: money rows; either directly linked to a task or shared and
  linked to an `allocation_rule`;
- `allocation_rules`: `equal`, `headcount` or `revenue`, each with a version;
- `outcomes`: success/failure/pending/reverted; success enters the denominator
  only when `verified=true` and `source_ref` is present;
- `loss_events`: separately reported confirmed losses, never mixed into ordinary
  task cost.

The machine-readable schema is
[`healthcheck/schemas/task-economics.schema.json`](../healthcheck/schemas/task-economics.schema.json).

## Output

For each task: direct cost, allocated shared cost, fully loaded cost, verified
success flag and verified value. At the case level: fully loaded cost, verified
success count, cost per verified success, verified value, ROI (or null with a
reason), loss events, coverage, duplicates and unallocated items.

## Hard boundaries

- No cross-currency aggregation or hidden FX conversion.
- Duplicate `cost_id` or `source_ref + amount + currency + period + vendor`
  rows are not summed twice.
- A run without a known `task_id` is unallocated; time proximity is not a link.
- Shared cost without a known allocation rule is unallocated, not smeared over
  tasks.
- Unverified outcomes and values stay out of the success denominator and ROI.
- Missing costs stay `unallocated`; they are not treated as zero.
- Historical allocation and ROI are not causal proof. Optimization suggestions
  require a controlled follow-up before any saving is called realized.

## CLI

```bash
verovo economics --case case.json --json out.json --markdown out.md
```

The command is read-only with respect to the case and writes only the requested
output paths.
