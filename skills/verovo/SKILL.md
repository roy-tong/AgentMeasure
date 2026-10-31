---
name: verovo
description: Review AI service charges and delivery from the buyer side, with explicit criteria, local evidence and separate conclusions. Also route supported billing recounts and agent telemetry conformance checks. Task entries: verovo-review-charge (费用核验: does the invoice match the rules on independent recount), verovo-review-delivery (交付核验: did the service meet stated requirements), verovo-prepare-dispute (build the negotiable Dispute & Recovery Pack). 中文触发：AI 服务费用核验、交付验收、续约核验、账单复算、争议材料、遥测语义核查、重试计数、用量口径。
---

# Verovo — buyer charges and delivery

Verovo is buyer-first. Charges and delivery are independent tasks; read
`docs/product-definition.md` before interpreting product scope. AI support is an
initial scenario, while coding agents, automation and tools/APIs are broader
objects to validate task by task. Provider downstream work needs a concrete
transaction; provider upstream spend is a buyer task.

## Buyer review (main preview, after v0.9.0)

```bash
git clone https://github.com/roy-tong/verovo && cd verovo
python3 healthcheck/verovo review --sample --html buyer-review.html
```

The synthetic sample has matching charges, one unmet delivery requirement and
one unprovable observation. For real inputs follow `docs/buyer-review.md`: confirm
scope and decision owner, record separate rule references and business criteria,
and reference authorized local JSON observations. Do not invent rules or missing
facts. This compares supplied criteria; it does not independently certify sources,
parse arbitrary contracts, or decide refunds. Delivery review can run alone.

### Task entries (one skill — never separate installs)

| Task | User asks | Loop (stages: `docs/review-method/buyer-review-stages.md`) | Closing artifact |
| --- | --- | --- | --- |
| `verovo-review-charge` | “检查这笔 AI 服务费用是否该付” | Intake → Source Check → Rule Resolution (`basis.kind=billing_rule`) → `recount`/`crosscheck` → review charges lane | Review report, charges lane + Tier 1/2 recount |
| `verovo-review-delivery` | “交付是否达标，能否验收” | Intake → Source Check → Rule Resolution (`basis.kind=buyer_requirement`) → review delivery lane | Review report, delivery lane (runs alone) |
| `verovo-prepare-dispute` | “准备争议材料” | Review both lanes → `verovo dispute` (cover letter + Tier 1 vendor rules + Tier 2 settlement standard) → buyer decides | Dispute & Recovery Pack (`verovo.commercial/dispute-pack`) |

Every report carries three conclusion levels, kept separate: **Level 1** rule
consistency (what the run establishes), **Level 2** evidence credibility (rule
applicability confirmations, third-party corroboration — reported as not
established when absent), **Level 3** the buyer business decision (outside the
tool; record via `verovo decisions`). A rule-consistent invoice is not delivery
proof; a failed delivery check is not authorization to withhold payment.

Use `recount` for supported billing exports, `buyer-ledger/` for tool-period
reconciliation and the measurement runners below for technical questions. No
command here uploads data. `delivery` is the review team's effort journal,
not the buyer acceptance command.


## Technical measurement checks (offline, deterministic)

```bash
git clone https://github.com/roy-tong/verovo && cd verovo
python3 conformance/pack/verovo selftest          # Pack fixtures, PASS / FAIL / UNPROVABLE
python3 conformance/pack/verovo conformance \
  --fixture conformance/vectors/external/urusilla-001/agentmeasure_urusilla_fixture_001.events.jsonl
./examples/demo-e2e.sh                                  # 42 calls -> 84 canonical observations, deterministic
python3 conformance/runners/run_metrics.py              # metric conformance vectors
python3 verify_vectors.py                               # receipts / correlation / operation grouping
```

These commands run locally. The Pack reads the caller-supplied FMT-002 fixture;
`selftest` is deliberately separate and only checks repository fixtures. No
network, cloud, or credentials are required.

## What to check, and where

| Question | Runner / artifact |
| --- | --- |
| Do retries inflate counted usage? (one operation vs N attempts) | `conformance/vectors/metric-execution-grain.json` |
| Does a selection rate claim hold at its grain? | `conformance/vectors/metric-selection-rate.json` |
| Do declared operation summaries reconcile against attempt rows? | `conformance/vectors/external/urusilla-001/` |
| Does an operation-grain metric aggregate at the wrong grain? | `conformance/vectors/external/urusilla-002/` |
| Can this trace safely support an operation count at all? | `conformance/evidence/langfuse-demo-traces/` (the 0%-coverage case) |

Verdict vocabulary: `PASS` / `FAIL` / `UNPROVABLE`. Ambiguity is retained in
the reason for an `UNPROVABLE` finding; it is not a fourth public verdict.
Report `UNPROVABLE` as a finding, never as zero.

## Boundaries

- Local by default. Nothing is uploaded; a sanitized sample is shared only with explicit authorization.
- A short sample check is not a full audit and claims no causal effect.
- The Pack CLI and root GitHub Action are shipped on `main`. Until a release
  tag explicitly includes the Pack, pin the Action to the verified immutable
  commit `2cf476d6f7d0fc45401db5a822e1f12de009ac74` rather than a moving branch.
- Provider-side usage questions (who called, how often, production traffic) start with the zero-install check described in the repository README.

Catalog entry: `https://raw.githubusercontent.com/roy-tong/roy-tong/main/agent-tools.json`
