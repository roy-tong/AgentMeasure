# Evidence Case: langfuse-demo-traces

**Case type: External Fixture — coverage analysis on a public artifact.**
First published 2026-08-25. Numbers below describe the three analyzed traces
only; see [PROVENANCE.md](PROVENANCE.md) for source pinning and claim
boundary.

## What this case is

We ran three public, real framework-instrumented traces — published by
Langfuse as demo-environment seed data — through the AgentMeasure canonical
pipeline (ingest → match → derive → compute), using a one-off adapter
documented below. No customer data, no synthetic data invented by us.

The question: **what can these traces safely prove about logical operation
usage?**

## Coverage-first result

```
12 attempts observed  (4 tool calls, 8 model calls)

Operation grouping evidence
──────────────────────────────
Declared        0%
Correlated      0%
Inferred        0%
Ungrouped      100%

Safe operation coverage      0%
Inference-dependent          0%
Unmeasurable               100%

Resolved operations            0
Attempt success            100%  (12/12, by observed level)
Operation success       not computable
Retry inflation         not computable

Token usage in export         0%  (0 of 26 observations carry usage)
Attempt-as-operation count   12   (what attempt-counting tooling would print)
```

> **Logical operation count cannot be safely reported for this dataset.
> 100% of attempts lack grouping evidence.**

## Why: four indistinguishable patterns

Each trace contains at least one sibling pattern where a retry and a loop
step are observationally identical:

| Trace | Pattern | Why it matters |
|---|---|---|
| pydantic-ai-tools | 2× `joke_agent run` under same parent | pydantic-ai re-runs agents on validation failure — this *looks* like that, but the export declares nothing |
| pydantic-ai-tools | 2× `chat gpt-4o-mini` under same parent | same ambiguity at the model-call layer |
| langgraph | 2× `agent` under same parent | LangGraph node revisit or retry — same shape |
| openai-agents | 2× `response` under same parent | tool-turn + final-turn, or retry — same shape |

We also ran the structural grouping pass (same (tool, task) sequential-failure
rule, experimental and disclosed as such): it resolves **0** operations too —
every attempt succeeded, so the retry-chain rule never fires. The ambiguity is
not an artifact of conservative defaults; it is genuinely undecidable from the
export.

## What is / is not safely reportable

Safely reportable from this data:

- 12 attempts, their surfaces, durations (p50 1,150 ms), observed outcomes
- the fact that token usage is absent from the export entirely
- the count of indistinguishable sibling patterns (4 across 3 traces)

Not safely reportable from this data:

- any operation count (0% grouping evidence)
- any retry rate, retry inflation, or operation success rate
- any token/cost figure

A tool that reports "12 operations" from this data is printing the
attempt-as-operation count under the wrong name. That number is trivially
computable — which is exactly why it gets printed — but it is not a logical
operation count.

## Reproduce

```bash
cd conformance/evidence/langfuse-demo-traces/
python3 fetch_source.py     # downloads the 3 pinned source files (see PROVENANCE)
python3 run_case.py         # adapter + canonical validation + pipeline, both modes
```

Requires only Python 3.8+ (stdlib). Outputs land in `source/`, `canonical/`,
and `results.json`; the numbers above are regenerated verbatim by
`run_case.py`.

## Related

- [`conformance/vectors/external/urusilla-001/`](../vectors/external/urusilla-001/) —
  first external conformance vector (metric-reproduction guards)
- [The spec](../../../standard/CORE.md) — operation/attempt/charge, the
  three-tier model behind the grouping rules above
