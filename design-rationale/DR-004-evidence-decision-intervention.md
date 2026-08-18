# DR-004 — Evidence, Decision, Intervention

- Status: Adopted as design rationale (Draft 0.4.4); governance concepts stay out of Core
- Date: 2026-08-18
- External evidence: Leo / UdayDolas (Razorpay Sentinel — evaluation records persisted before
  circuit breaker); The Upsider (agent-assigned value)

## Problem

Control systems (policy engines, circuit breakers) make decisions based on measurement.
If the final control outcome overwrites the evidence that caused it, the audit trail dies:
"the agent was blocked" is observable, but *why* is reconstruction.

## Decision

1. **Measurement must precede intervention.** A control decision MUST NOT overwrite the
   evidence that caused the decision.
2. Three data classes stay distinct: Evidence (what happened) / Decision (how it was
   interpreted) / Intervention (what action was taken). Never collapse into `outcome = failed`.
3. **Decision Provenance:** decisions reference the exact evidence that triggered them via
   stable IDs (`decision.based_on: [eval_1]`).
4. AgentMeasure boundary: measurement records evidence; it observes decisions and interventions
   but MUST NOT define policy decisions. AgentMeasure is not a governance engine.

## Implications

- Draft 0.5 research direction: Decision Provenance / Measurement Receipt (Payment Receipt ≠
  Measurement Receipt) in the Commercial Extension.
- README non-goals may add "policy / governance engine".

## Rejected alternatives

- AgentMeasure deciding whether an agent may run — rejected: expands the project into
  governance; measurement stays observational.
