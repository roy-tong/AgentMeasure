# Benchmark Run #001 — First Claim Audit（Draft 0.3 method）

**How the ecosystem evidences "agent usage" — 2026-08-16**

> Method: `benchmark/BENCHMARK-DRAFT.md` §2 (Draft 0.3). Claims collected from live
> public sources during launch week. Each claim is profiled with the multi-axis
> Evidence Profile (`standard/TRUST.md` §3) plus the orthogonal Source Attribution
> axis — Authentication is applied strictly (A0 = no signature, even when the
> source is identified). Machine-readable records: `benchmark/claims/*.json`.
>
> 本版按 v0.1.1 RC → External Alpha 收敛修订：
> 1. `Authentication` 严格遵守 TRUST（A0/A1/A2），不再把 "attributable" 混入 A1；
> 2. 新增正交的 **Source Attribution** 轴；
> 3. Benchmark 的 `Qualification` 更名为 **Claim Completeness**（把 Qualification
>    归还给 Measurement Core）；
> 4. **Claim #003 归因错误已修正**：originality.ai 是 secondary source，primary
>    measurement source 是 Ahrefs（server-log / web-analytics telemetry，不是
>    independent crawl）——这个错误本身就是本基准存在的理由；
> 5. AgentMeasure 自身数字移出排名，仅作 Reference Fixture 附录。

---

## Claim Labels

### 1. "x402 settled its 162-millionth payment; average ticket $0.25"（X post, @33xp_, 2026-08-13）

```text
Metric unit      : "payment" (undefined)
Grain            : count
Surface          : provider-side ledger (claimed, not verifiable from the post)
Coverage basis   : unknown
Method disclosed : no
Authentication   : A0 (not signed)      Source Attribution: named
Corroboration    : C0   Independence: I0   Attestation: T0
Match            : none
Completeness     : definition undefined · method no · traceability unresolved
Replayability    : no
```

Plausible and significant if true — but the unit and the ledger method are not
publicly replayable. Being attributable to a handle does not make it A1.

### 2. "48k active merchants on Base x402 in 30 days"（X post, @402Signal, 2026-08-16）

```text
Metric unit      : "merchant" (undefined)
Grain            : count
Surface          : provider-side aggregate (claimed)
Coverage basis   : unknown
Method disclosed : no
Authentication   : A0 (not signed)      Source Attribution: named
Corroboration    : C0   Independence: I0   Attestation: T0
Match            : none
Completeness     : definition undefined · method no · traceability unresolved
Replayability    : no
```

Same pattern as #1: real-sounding aggregate, no disclosed counting method, no raw data.

### 3. "97% of llms.txt files never get read"（2026-08-16 检索时经 originality.ai 转述）

```text
Metric unit      : "AI request" (partially defined: request-detection semantics)
Grain            : rate over population
Surface          : server-log / web-analytics telemetry（Ahrefs Web Analytics + Bot Analytics）
Coverage basis   : 137,210 Ahrefs Web Analytics domains；~38,000 with valid llms.txt (28%)
Observed period  : May 2026
Method disclosed : yes（crawl 无涉：分析的是 server logs 与 live traffic）
Authentication   : A0 (not signed)      Source Attribution: verified_organization
Corroboration    : C0   Independence: I2（观测者与样本域不同 trust domain）   Attestation: T0
Match            : heuristic（UA 分类）
Completeness     : definition partial · method yes · traceability primary-resolved · coverage yes
Replayability    : partial (method described; raw logs not published)
```

**归因修正（本基准的示范案例）**：初审时该声称被标为 `surface = independent crawl`、
source = originality.ai。追溯后确认 primary measurement source 是 **Ahrefs** 的
研究（[ahrefs.com/blog/llmstxt-study/](https://ahrefs.com/blog/llmstxt-study/)，
2026-06-15，Louise Linehan）——基于 137K 个使用 Ahrefs Web Analytics 的域名的
server logs / live traffic，而非独立爬虫。Originality.ai 只是转述者。
这正是"永远追溯到 primary measurement source"规则要抓的错误：attribution error
会直接改变 evidence 语义（telemetry 的独立性与 crawl 不同、population 也完全不同）。

### 4. "ClaudeBot impersonation up 400% this quarter"（security vendor post, @Ai_Trend_, 2026-08-13）

```text
Metric unit      : "impersonation" (undefined)
Grain            : rate (quarter-over-quarter)
Surface          : self-reported telemetry
Coverage basis   : unknown (denominator undisclosed)
Method disclosed : no
Authentication   : A0 (not signed)      Source Attribution: named
Corroboration    : C0   Independence: I0   Attestation: T0
Match            : none
Completeness     : definition undefined · method no · traceability unresolved
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
Authentication   : A0 (not signed)      Source Attribution: verified_organization
Corroboration    : C0/C1 (mixes sources)   Independence: I0   Attestation: T0
Match            : heuristic
Completeness     : definition undefined · method partial · traceability primary-resolved · coverage partial
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
Method disclosed : yes (full pipeline + demo script, deterministic fixture)
Authentication   : A0 (not signed)      Source Attribution: verified_organization
Corroboration    : C0   Independence: I0   Attestation: T0
Match            : exact-call-id (internal pairing)
Completeness     : definition defined · method yes · traceability primary-resolved · coverage yes
Replayability    : yes — ./examples/demo-e2e.sh (isolated workspace, deterministic)
```

Listed for transparency only, per `BENCHMARK-DRAFT.md` §3: the benchmark audits
external claims; AgentMeasure is the reference fixture, not a ranked claimant.
It proves pipeline integrity, and nothing about real usage, by design.

---

## Analysis

1. **The dominant pattern is self-reporting.** The difference between claims is not
   honesty but *replayability*. Claims 1–2 are probably true and impossible to verify;
   claim 4 is unverifiable and marketing-defined. Claim 3 is the exception that
   demonstrates the alternative — and even it required a primary-source correction.
2. **Independence improves corroboration strength; it does not substitute for
   coverage or representativeness.** Claim 3 is strong *because* it pairs an
   independent observation surface (server-log telemetry over third-party domains)
   with a disclosed method — not because independence alone beats volume.
3. **Badges are becoming the weak link.** Registry badges (5) inherit the evidence
   of their source; a badge without method disclosure outruns its evidence.
4. **Nobody publishes the unit definition.** None of these claims states what counts
   as "a payment", "a merchant", "an AI request", or "an impersonation". This is the
   definitional gap the AgentMeasure standard exists to close.
5. **Attribution errors are real and this benchmark just caught one.** Claim #003
   changed meaning (surface, population, independence) once the primary measurement
   source was resolved. Secondary-source claims MUST resolve to primary sources.

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
  (source URL, primary_source resolution, retrieved_at, exact claim text,
  excerpt hash, profile, source attribution, completeness, reviewer).
- Sources: X status IDs 2088915992336347639 (claim 1), 2089003333969154196 (claim 2),
  [Ahrefs study](https://ahrefs.com/blog/llmstxt-study/) via
  [originality.ai](https://www.originality.ai/blog/llms-txt) (claim 3),
  2087657972180643914 (claim 4), awesome-mcp-servers README (claim 5),
  reports/pipeline-validation-001.md (claim 6).
- All claims collected 2026-08-16/17; label schema in `benchmark/BENCHMARK-DRAFT.md` §2.
