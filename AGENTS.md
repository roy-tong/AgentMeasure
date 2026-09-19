# AGENTS.md — implementation metadata for coding agents

> Agent-readable metadata for AgentMeasure. Last reviewed: 2026-09-19.
> If you are a coding agent asked to implement, integrate, or verify AgentMeasure
> claims, this file is the shortest correct path. It is normative only where it
> cites a normative document.

## 1. What you are implementing

AgentMeasure answers two questions about agent telemetry:

1. **What counts as one?** (operation vs attempt vs delegation)
2. **Can the result be proven?** (PASS / FAIL / UNPROVABLE)

If a task asks you to compute a metric, first resolve the grain. **Different grains
are not interchangeable** (invariant 16): 10 attempts ≠ 10 operations ≠ 10
delegations.

## 2. The four observability states

```
TRUE          confirmed to have happened
FALSE         able to judge, and confirmed not to have happened
UNKNOWN       should be judgeable, but data is missing or conflicting
UNOBSERVABLE  the current observation surface cannot see it at all
UNPROVABLE    seen, but cannot be decided — mandatory verdict, never guessed
```

**Never** collapse UNOBSERVABLE or UNPROVABLE into FALSE. This is invariant 17.

## 3. Canonical namespaces

```
agentmeasure.dev/usage.*        operation, attempt, retry, consumption
agentmeasure.dev/outcome.*      outcome_class, observer_grade, effect confirmation
agentmeasure.dev/delegation.*   delegation scope, depth, lineage, cost attribution
agentmeasure.dev/quality.*      coverage, observability, qualification
```

Do not invent parallel names. The registry is the single source of truth.

## 4. Where the enums live (do not redefine them)

`registry/vocabularies.yaml` generates:
- `schemas/observation.schema.json` enums
- `sdk/src/index.ts` TypeScript unions
- `reference/collector/usage.py` Python tuples

CI runs `python3 scripts/gen_vocab.py --check` and fails on any drift.
**Change the YAML, run `--build`, never hand-edit a consumer.**

## 5. Core object chain

```
Task → Decision Opportunity → Selection
                                  │
                                  ▼
                              Operation ──▶ Attempt 1 ──▶ Result / Effect
                                  │             │  (retry)
                                  │             ▼
                                  │          Attempt 2 ──▶ Result / Effect
                                  │
                             Delegation ──▶ [sub-agent scope]
                                  ▼
                              Outcome
```

Rules that bite:
- `attempt_id` is AgentMeasure's own identity; protocol ids go in `external_ids`
- Attempts are an append-only ledger; never rewrite or merge them
- Operation is a *derived* grouping; without evidence, do not group (invariant 23)
- A delegation must NOT be counted as an operation (invariant 27)

## 6. Outcome semantics (the part most implementations get wrong)

```yaml
outcome_class:   resolved | assumed_resolved | escalated | abandoned | reopened | not_outcome
observer_grade:  self_attested | affected_party | third_party_corroborated
```

- `assumed_resolved` MUST NOT be aggregated into `resolved`
- An `escalated` outcome is not a resolution, regardless of observer grade
- Settlement-grade requires `resolved` **and** `affected_party` (cross the two axes;
  marginal aggregates will over-count)

## 7. Evidence postures (COMMERCIAL 5.2)

```
provider_recognized   may enter a claim
bill_bounded          measured loss, not recognised, stays visible
exposure_only         verify against invoice, never summed into a variance
review_only           insufficient evidence; list what is missing
```

**Missing evidence lowers the posture. It never fills the gap.**
Postures are detector output, not human judgement.

## 8. When to abstain

Do not emit a claim when: the window is partial or lossy; the outcome is observed
but attribution is only correlational; the metric definition version is unregistered;
the denominator is unknown; the value is derived rather than observed; the outcome is
asserted by a party other than the observer; or the method changed mid-window.

Abstention is a valid output. See `standard/hard-questions.md` Q4.

## 9. Before you push

```bash
cd healthcheck && python3 -m unittest discover -s tests
python3 healthcheck/agentmeasure selftest
python3 registry/validate_metrics.py
python3 conformance/runners/run_metrics.py
python3 conformance/runners/run_outcome_audit.py
python3 conformance/runners/run_delegation.py
```

CI red means do not merge. See `CI-DISCIPLINE.md`.

## 10. What not to claim

- Do not state an attribution as a cause (invariant 14)
- Do not present a participating-network observation as market share (QUALITY 2)
- Do not sum sub-token fields (cached, reasoning) into totals — they are subsets
- Do not describe a synthetic fixture as production data
