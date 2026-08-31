---
name: agentmeasure
description: Check whether agent telemetry preserves measurement semantics. Use when a user asks whether retries inflate counted usage, whether an operation differs from an attempt, whether token metrics double count a subset (reasoning inside output), whether cache hits or cached replays distort counts, or wants conformance tests for agent metrics and observability claims. 中文触发：遥测语义核查、重试计数、用量口径、token 重复计数、Agent 用量指标一致性检验。
---

# AgentMeasure — Measurement Conformance

This Skill routes measurement-semantics questions to AgentMeasure's local runners. It does not move telemetry anywhere.

## First success (offline, deterministic)

```bash
git clone https://github.com/roy-tong/AgentMeasure && cd AgentMeasure
./examples/demo-e2e.sh                                  # 42 calls -> 84 canonical observations, deterministic
python3 conformance/runners/run_metrics.py              # 21/21 vectors PASS
python3 verify_vectors.py                               # receipts / correlation / operation grouping
```

If all three run locally, the Skill is working. No network, no cloud, no credentials.

## What to check, and where

| Question | Runner / artifact |
| --- | --- |
| Do retries inflate counted usage? (one operation vs N attempts) | `conformance/vectors/metric-execution-grain.json` |
| Does a selection rate claim hold at its grain? | `conformance/vectors/metric-selection-rate.json` |
| Do declared operation summaries reconcile against attempt rows? | `conformance/vectors/external/urusilla-001/` |
| Does an operation-grain metric aggregate at the wrong grain? | `conformance/vectors/external/urusilla-002/` |
| Can this trace safely support an operation count at all? | `conformance/evidence/langfuse-demo-traces/` (the 0%-coverage case) |

Verdict vocabulary: `PASS` / `FAIL` / `AMBIGUOUS` / `UNPROVABLE`. Report `UNPROVABLE` as a finding, never as zero.

## Boundaries

- Local by default. Nothing is uploaded; a sanitized sample is shared only with explicit authorization.
- A short sample check is not a full audit and claims no causal effect.
- The packaged `agentmeasure conformance` CLI and GitHub Action are in development; today the runners above are the interface.
- Provider-side usage questions (who called, how often, production traffic) start with the zero-install check described in the repository README.

Catalog entry: `https://raw.githubusercontent.com/roy-tong/roy-tong/main/agent-tools.json`
