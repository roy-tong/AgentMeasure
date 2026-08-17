# Benchmark Run #001 — First Claim Audit（Draft 0.2 method）

**How the ecosystem evidences "agent usage" — 2026-08-16**

> Method: `benchmark/BENCHMARK-DRAFT.md` §2 (Draft 0.2). Claims collected from live
> public sources during launch week (X posts, registries, audits). Each claim is
> profiled with the multi-axis Evidence Profile (`standard/TRUST.md` §3) — no single
> ladder, no composite grade. Machine-readable records: `benchmark/claims/*.json`.
>
> 本版按 v0.1.1 External-Ready 收敛修订：废弃 E0–E5 单轴阶梯；修正
> "every ecosystem number is self-reported" 与 "Independence beats volume" 两处
> 过度声称；AgentMeasure 自身数字移出排名，仅作 Reference Fixture 附录。

---

## Claim Labels

### 1. "x402 settled its 162-millionth payment; average ticket $0.25"（X post, @33xp_, 2026-08-13）

```text
Metric unit      : "payment" (undefined)
Grain            : count
Surface          : provider-side ledger (claimed, not verifiable from the post)
Coverage basis   : unknown
Method disclosed : no
Authentication   : A0   Corroboration: C0   Independence: I0   Attestation: T0
Match            : none
Replayability    : no
```

Plausible and significant if true — but the unit and the ledger method are not
publicly replayable.

### 2. "48k active merchants on Base x402 in 30 days"（X post, @402Signal, 2026-08-16）

```text
Metric unit      : "merchant" (undefined)
Grain            : count
Surface          : provider-side aggregate (claimed)
Coverage basis   : unknown
Method disclosed : no
Authentication   : A0   Corroboration: C0   Independence: I0   Attestation: T0
Match            : none
Replayability    : no
```

Same pattern as #1: real-sounding aggregate, no disclosed counting method, no raw data.

### 3. "~39,000 llms.txt files; 97% had received zero AI requests"（third-party audit）

```text
Metric unit      : "AI request" (partially defined: request-detection semantics)
Grain            : rate over crawled files
Surface          : independent crawl
Coverage basis   : ~39k files of an unknown total universe (partial)
Method disclosed : yes (crawl method; request-detection not fully specified)
Authentication   : A1   Corroboration: C0   Independence: I2   Attestation: T0
Match            : heuristic
Replayability    : yes (method + tooling described)
```

The strongest claim in this batch: an independent observer with a replayable method.
Note that independence strengthens **corroboration value**; it does not substitute
for coverage or representativeness — the 39k universe itself is unstated.

### 4. "ClaudeBot impersonation up 400% this quarter"（security vendor post, @Ai_Trend_, 2026-08-13）

```text
Metric unit      : "impersonation" (undefined)
Grain            : rate (quarter-over-quarter)
Surface          : self-reported telemetry
Coverage basis   : unknown (denominator undisclosed)
Method disclosed : no
Authentication   : A1 (attributable vendor)   Corroboration: C0   Independence: I0   Attestation: T0
Match            : none
Replayability    : no
```

Marketing-grade: no method, no denominator, undefined unit.

### 5. glama.ai MCP server score badges（awesome-mcp-servers entries）

```text
Metric unit      : "score" (undefined per badge)
Grain            : score / count
Surface          : third-party registry (aggregating underlying data)
Coverage basis   : servers listed in the registry
Method disclosed : partial (per-badge disclosure missing)
Authentication   : A1   Corroboration: C0/C1 (mixes sources)   Independence: I0
Attestation      : T0   Match: heuristic
Replayability    : conditional
```

Infrastructure that *could* carry strong evidence, currently mixing self-reported
and observed data without per-badge disclosure — a badge with no disclosed method
looks stronger than its evidence.

### 6. (Reference fixture — NOT ranked) AgentMeasure Pipeline Validation #001

```text
Claim            : 42 synthetic calls → 84 canonical observations, 0 rejected, 0 qualified
Metric unit      : "attempt" (defined) / "observation" (defined)
Grain            : count
Surface          : provider-side (our own SDK + collector)
Coverage basis   : the fixture itself (no real usage)
Method disclosed : yes (full pipeline + demo script)
Authentication   : A1 (self-observed)   Corroboration: C0   Independence: I0   Attestation: T0
Match            : exact-call-id (internal pairing)
Replayability    : yes — ./examples/demo-e2e.sh, isolated workspace
```

Listed for transparency only, per `BENCHMARK-DRAFT.md` §3: the benchmark audits
external claims; AgentMeasure is the reference fixture, not a ranked claimant.
It proves pipeline integrity, and nothing about real usage, by design.

---

## Analysis

1. **The dominant pattern is self-reporting.** The difference between claims is not
   honesty but *replayability*. Claims 1–2 are probably true and impossible to verify;
   claim 4 is unverifiable and marketing-defined. Independent observation (claim 3)
   is the exception that demonstrates the alternative.
2. **Independence improves corroboration strength; it does not substitute for
   coverage or representativeness.** Claim 3 is strong *because* it pairs an
   independent surface with a disclosed method — not because independence alone
   beats volume. A platform with broad coverage and weak independence answers a
   different question than an auditor with narrow coverage and strong independence;
   both are needed, and they cannot be collapsed into one score.
3. **Badges are becoming the weak link.** Registry badges (5) inherit the evidence
   of their source; a badge without method disclosure outruns its evidence.
4. **Nobody publishes the unit definition.** None of these claims states what counts
   as "a payment", "a merchant", "an AI request", or "an impersonation". This is the
   definitional gap the AgentMeasure standard exists to close.

## What this means for the standard

- **Attributable-but-unreplayable is the industry default right now.** The standard's
  job is to make independent replay cheap, not to moralize about self-reporting.
- **Unit definitions must ship with every public metric** — the Core spec's
  `metrics.yaml` requires this; this audit shows why it is not optional.
- **Next run**: re-audit claim 1 against x402's public docs when available; onboard
  the first external provider (issue #2) and publish their first claim label with
  their pipeline (→ Measurement Report #001).

## Reproducibility

- Machine-readable claim records: `benchmark/claims/claim-001.json` … `claim-006.json`
  (source URL, retrieved_at, exact claim text, snapshot hash, profile, reviewer).
- Sources: X status IDs 2088915992336347639 (claim 1), 2089003333969154196 (claim 2),
  BENCHMARK-DRAFT citations (claim 3), 2087657972180643914 (claim 4),
  awesome-mcp-servers README (claim 5), reports/pipeline-validation-001.md (claim 6).
- All claims collected 2026-08-16; label schema in `benchmark/BENCHMARK-DRAFT.md` §2.
