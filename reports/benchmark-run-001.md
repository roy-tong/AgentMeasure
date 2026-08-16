# Benchmark Run #001 — First Claim Audit

**How the ecosystem evidences "agent usage" — 2026-08-16**

> Method: benchmark/BENCHMARK-DRAFT.md §2. Claims collected from live public sources
> during launch week (X posts, registries, audits). Each claim graded E0–E5
> (evidence level) with Context × Validity qualification. No claim was altered;
> links/sources preserved for replay.

---

## Scorecard

| # | Claim (public source, 2026-08-16) | Evidence grade | Context | Validity | Notes |
|---|---|---|---|---|---|
| 1 | "x402 settled its 162-millionth payment; average ticket $0.25" (X post, @33xp_, 2026-08-13) | **E1** | Provider-side ledger (platform operator) | Unknown (no method disclosed for counting a "payment") | Plausible and significant if true; but the unit ("payment") and the ledger method are not publicly replayable |
| 2 | "48k active merchants on Base x402 in 30 days" (X post, @402Signal, 2026-08-16) | **E1** | Provider-side aggregate | Unknown | Same pattern: real-sounding aggregate, no disclosed counting method, no public raw data |
| 3 | "~39,000 llms.txt files; 97% had received zero AI requests" (third-party audit cited in BENCHMARK-DRAFT) | **E3** | Independent crawl | Partial (crawl method disclosed; request-detection semantics not fully specified) | The strongest claim in this batch: independent observer, replayable method |
| 4 | "ClaudeBot impersonation up 400% this quarter" (security vendor post, @Ai_Trend_, 2026-08-13) | **E0/E1** | Self-reported telemetry | Unknown | No method or denominator disclosed; "impersonation" is undefined. Marketing-grade |
| 5 | glama.ai MCP server score badges (awesome-mcp-servers entries) | **E2/E3** | Third-party registry | Partial (registry aggregates; underlying data self-reported by server owners) | Infrastructure that *could* carry E3, currently mixing self-reported and observed data without per-badge disclosure |
| 6 | AgentMeasure: "42 calls, 126 observations, 0 rejections (synthetic traffic, honestly labeled)" (our own report #001) | **E2** | Provider-side, our pipeline | Method fully disclosed; synthetic only | The only claim here that discloses its counting semantics — and it proves nothing about real usage, by design |

## Analysis

1. **The pattern is uniform: every ecosystem number is self-reported.** The difference
   between claims is not honesty but *replayability*. Claims 1-2 are probably true and
   impossible to verify; claim 4 is unverifiable and defined by marketing.

2. **The strongest claim (3) comes from the one independent observer.** Independence
   beats volume: an auditor with a disclosed crawl beats a platform with perfect data.

3. **Badges are becoming the weak link.** Registry badges (5) inherit the verification
   semantics of their source; a badge with no disclosed method is E0 wearing E3 colors.

4. **Nobody publishes the unit definition.** None of these claims states what counts as
   "a payment", "a merchant", "an AI request", or "an impersonation". This is the
   definitional gap the AgentMeasure standard exists to close.

## What this means for the standard

- **E1 is the default for the industry right now.** The standard's job is to make E3
  (independent replay) cheap, not to moralize about E1.
- **Unit definitions must ship with every public metric** — the Core spec's
  `metrics.yaml` requires this; this audit shows why it is not optional.
- **Next run**: re-audit claim 1 against x402's public docs when available; onboard
  the first external provider (issue #2) and grade their claim at E2→E3.

## Reproducibility

- Sources: X status IDs 2088915992336347639 (claim 1), 2089003333969154196 (claim 2),
  BENCHMARK-DRAFT citations (claim 3), 2087657972180643914 (claim 4),
  awesome-mcp-servers README (claim 5), reports/measurement-report-001.md (claim 6).
- All claims collected 2026-08-16; grading rubric in benchmark/BENCHMARK-DRAFT.md §2.
