# Review charges and delivery as a buyer

`review` is a main-branch preview added after v0.9.0. It runs locally with no
network calls and emits an offline HTML report and/or a structured JSON record.
Existing `delivery` records the review team's work phases and effort; it is not
the buyer acceptance command. Use `review` for buyer-defined acceptance checks.

## First result

From the repository root, using Python 3.9+:

```bash
python3 healthcheck/verovo review --sample --html buyer-review.html --json buyer-review.json
```

The bundled **synthetic** example has a matching charge, a failed delivery
criterion and a missing delivery observation. It returns:

```text
CHARGES: PASS (1 checks; 0 evidence gaps)
DELIVERY: FAIL (2 checks; 1 evidence gaps)
```

`FAIL` means at least one supplied criterion was not met; other checks can still
be unprovable. `PASS` means all listed checks in that lane passed, not that every
possible charge or delivery condition was examined. A selected lane with no checks
is UNPROVABLE. An unselected lane is NOT_REVIEWED. Findings exit 0; invalid input
or output errors exit 2, following the CLI convention.

## Your own task

Copy both [buyer-review.json](../healthcheck/verovo_healthcheck/demo/buyer-review.json)
and [buyer-observations.json](../healthcheck/verovo_healthcheck/demo/buyer-observations.json)
into a private local directory. Replace the synthetic scope, criteria and facts
with your actual authorized records. Or create a deliberately incomplete template:

```bash
python3 healthcheck/verovo review --init task.json
python3 healthcheck/verovo review --task task.json --html review.html --json review.json
```

Fill the template before the second command; empty fields/criteria are rejected.
To install the main preview rather than run from the checkout, use
`python3 -m pip install ./healthcheck` from the repository root. This does not
publish a package or change the tagged release.

### Task fields

| Field | Meaning |
|---|---|
| `schema_version` | `1.0` for this buyer task format; not a telemetry vocabulary version |
| `workflow` | `charges`, `delivery` or `both` |
| `scope` | Nonempty `buyer`, `service`, `account_or_task`, `period_or_window`, `decision`, `owner`; optional `due_date` |
| `criteria` | Nonempty list with unique `id`, selected `lane`, `statement`, `basis`, `operator`, `expected`, `source` |
| `basis` | `kind`: `billing_rule` for charges or `buyer_requirement` for delivery; nonempty `ref` and `version` |
| `operator` | `equals`, `at_least`, `at_most`; ordering accepts finite numbers only |
| `expected` | String, boolean or finite number; null is not an acceptance criterion |
| `source` | Relative local JSON `path` and RFC 6901 `pointer` to the observation |

For example:

```json
{
  "id": "artifact-present",
  "lane": "delivery",
  "statement": "The agreed artifact was recorded as delivered",
  "basis": {"kind": "buyer_requirement", "ref": "Acceptance checklist item 3", "version": "2026-10-31"},
  "operator": "equals",
  "expected": true,
  "source": {"path": "observations.json", "pointer": "/task/artifact_delivered"}
}
```

The command reads the referenced JSON field; it does not independently inspect an
artifact merely because a record asserts delivery. A reviewer must establish the
record's origin and trustworthiness. Label supplier assertions and buyer-owned
observations in the references and criterion statements. For billing, confirm
currency, unit, account, date window and rule applicability before comparison.
There is no cross-currency aggregation, automatic rounding or recovery estimate.

Missing files, fields, null values, malformed observations and incompatible types
produce UNPROVABLE, never zero or FALSE. Evidence paths must stay inside the task
directory, including after resolving symlinks. Duplicate JSON keys and duplicate
criterion IDs are rejected. The tool reads each source once per run and records
its SHA-256, the task hash and generation time. Hashes bind the input snapshot;
they do not prove provenance or prevent a reviewer from choosing poor criteria.

## Use the result

1. Review the separate charge/delivery conclusions and coverage.
2. Check each rule reference, version, observation and source hash.
3. Obtain missing evidence or revise a disputed criterion with a new version.
4. Record the buyer's actual acceptance, remediation or renewal decision using
   the existing `decisions` workflow; do not infer it from a generated report.

Use existing `prepare`, `recount`, `verify` and Buyer Ledger commands when their
supported inputs fit the task. A value from their local JSON output can be an
observation in this task after confirming its meaning and scope. This command
does not automatically normalize all their schemas or replace their calculations.

Keep the reports local: JSON includes local input paths and both reports may
contain confidential business facts. Inspect and redact before choosing to share.
Reports cannot overwrite the task or evidence input files.
