# FMT-004 — Mapping Core 0.4.4 Semantics to the Lab Experiment Formats

> How the experiment engine's formats (FMT-001/002/003, `lab/schemas/`) instantiate the
> AgentMeasure Core specification (`standard/CORE.md`, Draft 0.4.4). This document is the
> reference for third parties implementing runners or report consumers, and the OTel/AAIF
> reference scenario anchor. Status: **informational mapping** — where Lab rules are
> stricter than Core, the stricter rule is stated.

## 1. Object mapping (FMT-002 funnel events → Core objects)

| Lab event | Core object(s) (CORE §2) | Notes |
| --- | --- | --- |
| `reach` | **Decision Opportunity** + **Candidate Set** (+ N **Presentation**s) | one event materializes the decision: `candidate_ids` IS the candidate set actually offered; a Presentation is derived per candidate (`Presented` remains the choice denominator, CORE §2.4) |
| `choice` | **Selection** | `selected_subject` resolves the subject; selection of a competitor is recorded too — the losing side stays in the evidence (LAB-006) |
| `attempt` | **Attempt** (execution fact, immutable) | retries are additional Attempts of one Operation — never additional logical uses (CORE §7 qualification; Core invariant "facts survive interpretation") |
| `operation_result` | **Operation** (derived) | carries derivation provenance: rule `op-success-any/1` = "operation succeeds iff any attempt succeeded" — Derived facts carry provenance (CORE §9) |
| `consumption` | **Result Consumption** (M4 utility) | `signal` distinguishes `task_continuation` / `operation_failed` / `none`; absence of observability is `unknown`, never guessed (CORE §4 observability states) |

## 2. Grain (CORE §3)

The funnel's denominators ARE the grain discipline:

| Rate | Grain | Denominator |
| --- | --- | --- |
| selection_rate | decision | reach events |
| operation_success_rate | operation | subject operations |
| consumption_rate | operation | successful operations |

`10 attempts ≠ 10 operations ≠ 10 decisions` — the report refuses to mix them, and every
metric row states its grain in the Measurement Label.

## 3. Qualification axes (CORE §7)

Experiment events carry `qualification: controlled experiment environment (not production)`
in every Measurement Label. Production events (used by calibration, `am lab calibrate`)
carry `production (gradual rollout)`. The two are never pooled into one number — the
calibration report exists precisely to compare them **as two labeled environments**
(CAL-003). This instantiates Usage Context (`production` vs `synthetic`/`controlled`)
from the Core qualification model.

## 4. Evidence & uncertainty (CORE §4, §9)

- No event carries timestamps or content: determinism and privacy are schema-level, not
  policy-level.
- Unknown ≠ Zero: `operation_result.outcome` may be `unresolved`; consumption may be
  `unknown`; the report displays them as gaps, never as zeros.
- Every derived rate ships numerator/denominator/CI + rules_version (`Measurement Label`,
  QUALITY §5).

## 5. Reference scenario 1 — "description clarity A/B, controlled environment"

Scenario: a search-API provider preregisters one factor (`description_clarity`:
`control`/`clear`) over a 36-task synthetic corpus in one harness; primary metric
`selection_rate`; guardrails on consumption and steps.

Event trace for one assignment (variant `clear`, task `search-e1`):

```text
reach    {event: reach,    candidate_ids: [your-search-api, web-search-pro, ...], variant_id: clear}
choice   {event: choice,   selected_id: your-search-api, selected_subject: true}
attempt  {event: attempt,  attempt_index: 1, outcome: success, steps: 9, cost_units: 22.5}
operation_result {event: operation_result, outcome: success, attempts: 1}
consumption     {event: consumption, consumed: true, signal: task_continuation}
```

Core reading: 1 Decision Opportunity, 4 Presentations, 1 Selection, 1 Operation derived
from 1 Attempt (rule `op-success-any/1`, provenance recorded), Result consumed.
Aggregated per the FMT-003 report: `selection_rate = selections/reach` at decision grain
with a Wilson interval and Measurement Label.

External-validation hook (OTel GenAI / AAIF): the same trace maps onto `gen_ai.tool.call`
spans for attempts (Route B via `profiles/opentelemetry-genai.md`); the reference scenario
is the minimal corpus an external implementation can replay to check its numbers against
ours (conformance vectors live at repo root, `fixtures/`).

## 6. Reference scenario 2 — "production re-test, gradual rollout"

Scenario: the `clear` variant ships at 10% traffic; a holdout keeps `control`. The
runtime side (data-rights holder, BP §3) emits the SAME FMT-002 events labeled with the
rollout arm as `variant_id`. The calibration report then computes, per condition
(harness × task stratum): offline effect vs production effect vs **transfer**
(offline − production), each with intervals; conditions missing events on either side are
`not_comparable` with the gap named — never filled by assumption.
