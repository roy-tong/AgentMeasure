> Technical reference retained from the previous README. For current offers and priorities, see the [project overview](../README.md).

# For developers and standard contributors

Everything below this line is the open measurement layer: the conformance pack,
the experiment engine, the core specification and the provider SDK. It supports the local checks and diagnostics, and stays free. Commands below run from the repository root.

## Try it in 2 minutes

```bash
./examples/demo-e2e.sh
```

Mock MCP server → canonical observations → local metrics, all on your machine, no
cloud. The demo is **reproducible**: it runs in an isolated workspace (never touches
`~/.verovo`) — same fixture + same policy = same result (42 calls → 84
canonical observations, caller claims claude:14 · codex:14 · unknown:14).

Then read why we audit the ecosystem's usage claims:
[Benchmark Run #001](../reports/benchmark-run-001.md) — six real claims profiled with
the Evidence Profile (multi-axis, no composite scores), and
[Pipeline Validation #001](../reports/pipeline-validation-001.md) — our own fixture,
kept out of the ranking as a reference baseline.

---

## Run a preregistered experiment — Verovo Lab

```bash
python3 lab/verovo lab selftest                                   # planted uplift recovered + honest null
python3 lab/verovo lab init                                       # workspace + example experiment
python3 lab/verovo lab preregister verovo-lab/experiments/example-manifest.json
python3 lab/verovo lab run verovo-lab/experiments/example-manifest.prereg.json
```

The open experiment engine ([lab/](../lab/README.md)): task set × harness matrix × factor
variants → Reach → Choice → Success → Consumption funnel → effect sizes with
confidence intervals, guardrails, honest nulls, and an offline HTML report that opens
with a bilingual decision-maker one-pager. Preregistration is enforced (hypothesis /
primary metric / guardrails / analysis plan hashed before the run — with a scale /
power / budget preview), seeds replay deterministically, and a budget circuit breaker
stops safely with the data it has. Selection uplift that loses consumption is
**rejected at the decision exit** (`unverified_growth` — do not ship), and candidates
that make no more money at higher cost are flagged as dominated.

The shipped demo runs on a **synthetic harness** (planted ground truth at realistic,
literature-scale amplitudes, disclosed in every report) — it validates the engine,
not real-agent claims. Real harness adapters (Claude Code / Codex) are runner plugins
against the same interface; that is the highest-value contribution right now.
Docs: [lab/README.md](../lab/README.md) · formats:
[lab/schemas/](../lab/schemas/) (experiment manifest / funnel events / report).

---

## Why the split matters, in one line

```text
1 user intent
2 provider attempts
1 final success
```

That is **1 operation**, **2 attempts**, operation success **100%**, attempt success **50%**,
attempts per operation **2**.

It is *not* "2 operations with 50% success".

Attempts are execution facts. Operations are logical intents. Mixing the two is how agent
reliability reports get distorted.

---

## External provider trials

Start smaller than a trial: **send a trace, get a measurement check** — 20–100 anonymized trace/log rows (or a public export), mapped locally, with a short report of what safely counts as attempts vs operations, where retries may inflate usage, and what the telemetry cannot prove. No SDK, no integration; raw data stays local unless you explicitly authorize sharing a sanitized sample. A sample check is not a full audit and claims no causal effect.

If the check pays for itself, Verovo is looking for **3 MCP/API providers** for short external measurement runs.

The goal is not to prove the model works. It is to find where it breaks on real provider traffic.

A trial can stay fully local, requires no agent-side install, and can start with one capability.

**Best feedback:** a concrete trace, counterexample, or field that cannot be measured safely.

→ The formal offer, schedule, and FAQ live in **[product/AUDIT.md](../product/AUDIT.md)** · apply in **[Issue #2 — Looking for 3 MCP/API providers for external measurement runs](https://github.com/roy-tong/verovo/issues/2)**.

---

## Why capabilities need a new measurement layer

The software consumer is changing from humans to agents, and the economic unit is shifting from software seats toward callable capabilities.

```text
Skill / MCP / CLI / SDK
        ↓
Describe / expose / distribute a capability

Capability
        ↓
Data / Compute / Action / Permission / Transaction
        ↓
Creates scarce economic value
```

**Interfaces may become cheap to create; capabilities remain scarce to deliver.**

The first generation of capability distribution is already here — open Skills, open MCP adapters, open CLIs. The scarce layer underneath them is what the next economy is built on: proprietary data, compute, execution, permissions, and real-world fulfillment.

## From software to capability economy

```text
Human Software Economy
User → UI → SaaS → Seat / Month

             ↓

Agent Capability Economy
Agent → Capability → Execution → Outcome
                       ↓
              Usage / Value / Transaction
```

If a capability is to become an economic unit that agents can discover, compare, and eventually purchase automatically, it must first be **identifiable, measurable, and comparable under a shared semantics**. That is what Verovo provides.

Traditional usage metrics cannot support this economy — the old chain breaks at every link, and the last link is new:

```text
Install ≠ Available
Available ≠ Presented
Presented ≠ Selected
Selected ≠ Used
Used ≠ Useful
Useful ≠ Incremental Value
Measured Usage ≠ Billable Usage
```

The last inequality is why the Operation/Attempt model matters commercially: 3 attempts of one operation are not 3 billable operations — unless the metering policy says so.

> The extended thesis — economic units, scarcity, measurement before monetization,
> metering semantics, and the evidence that commerce is arriving before measurement —
> lives in [docs/CAPABILITY-ECONOMY.md](../docs/CAPABILITY-ECONOMY.md).

## The measurement view: Reach → Choice → Use → Utility → Value

Verovo defines **metric families**, not a universal KPI. A search capability, a booking API, and a compute job have different value structures.

| Layer | Question | Representative metrics |
| --- | --- | --- |
| **Reach** | Did the capability enter the agent's choice range? | Eligible Opportunities · Presentations · Presentation Rate · Distribution Coverage |
| **Choice** | When the agent had the chance, did it choose it? | Observed Selection Rate · Observed Head-to-Head Choice Share |
| **Use** | After selection, was it actually used? | Operations · Attempts · Completion Rate · Success Rate |
| **Utility** | Did it produce a usable result or confirmed effect? | Result Consumption · Effect Confirmation |
| **Value** | Did it improve the task outcome? | Incremental Task Success（Draft 0.5） |

The five layers are the **measurement view**. The same facts map onto an economic view:

| CaaS Domain | Verovo |
| --- | --- |
| Demand | Reach + Choice |
| Delivery | Use + Utility |
| Outcome | Value |
| Economics | Metering / Attribution（future extension） |

Claim discipline throughout: *observed choice is not preference*. A selection can be made by the model, a router, a workflow, the user, a policy, or the platform; **Observed Selection Rate** reports what was observed, and **Observed Head-to-Head Choice Share** is an *observed head-to-head choice share under comparable candidate conditions* — comparable means the same candidate set, category, choice mode, and decision axes (Decision Authority / Selection Constraint) are declared.

## How Verovo works in production

```text
Agent Runtime                     Capability Provider

Claude / Codex
      │
      │ MCP / API
      ▼
                         ┌──────────────────────┐
                         │ Customer Capability  │
                         │                      │
                         │ Verovo SDK     │
                         │ Business Handler     │
                         └──────────┬───────────┘
                                    │
                               observations
                                    │
                                    ▼
                              Collector
                                    │
                                    ▼
                            Verovo Cloud
```

Four things a real developer needs to know:

> Your software does **not** need to be open source.
>
> MCP is **not** required — it is the first reference surface.
>
> Third-party agents do **not** need Verovo installed for provider-side usage measurement.
>
> Verovo is **not** on the critical request path.

Product architecture (Provider SDK → local buffer → hosted ingestion → dashboard):
[product/ARCHITECTURE.md](../product/ARCHITECTURE.md).

## What Verovo measures today

- **Decision Opportunity / Candidate Set / Presentation / Selection** — the four objects of choice; the Observed Selection Rate denominator is Presented, not Available
- **Software Entity → Capability → Interaction Surface** — what exists, what it can do, and the observable interface; observation happens on surfaces, attribution resolves to entities through the machine-readable registry
- **Operation / Attempt** — one logical use vs. one execution; **retries are multiple attempts of one operation**, not a validity class (they are kept as reliability signals, not counted as distinct logical uses)
- **Qualified Usage** — production usage after excluding test, benchmark, synthetic, replay, duplicate and other invalid traffic according to policy
- **Result Consumption** — *defined, reference partial*: the result was used by the task
- **Effect Confirmation** — *domain model defined, metric planned for Draft 0.5*: the intended world-state change was confirmed
- **Measurement Label** — a nutrition label for every public number (coverage / sampling / policy / method)

The full model lives in the [Core Specification](../standard/CORE.md), [Metrics](../standard/METRICS.md), [Entity](../standard/ENTITY.md), and [Quality](../standard/QUALITY.md). The README is not a spec summary.

## From measurement to CaaS

Verovo is **progressively standardizing** the measurement chain from discovery
and choice through execution, utility and value: core usage semantics are defined
today; utility/value and commercial metering remain active drafts. Metering and
commercial attribution are future extensions; payment rails can be provided by
existing payment infrastructure.

> **Verovo standardizes economic facts, not money movement.**
>
> Extended thesis: [docs/CAPABILITY-ECONOMY.md](../docs/CAPABILITY-ECONOMY.md) ·
> Economic semantics: [extensions/COMMERCIAL.md](../extensions/COMMERCIAL.md)（Experimental）

## Harness profiles — what each runtime can (and cannot) observe

Portable semantics need a public record of observation blind spots. Per-harness
profiles map each runtime's native objects to Verovo semantics:

| Harness | Profile | Highlights |
| --- | --- | --- |
| Codex | [profiles/codex.md](../profiles/codex.md) | hook 观察，无 trace/精确时间戳；App Server 事件流为优先生效观察面 |
| Claude Code | [profiles/claude-code.md](../profiles/claude-code.md) | 内置成败判定；第一个 Consumption 可实证平台 |
| DeepSeek Harness | [profiles/deepseek-harness.md](../profiles/deepseek-harness.md) | append-only session log；subagent lineage/depth 是 Delegation 的首个真实数据源 |
| Pydantic AI | [profiles/pydantic-ai.md](../profiles/pydantic-ai.md) | Logfire spans → attempt 语义 |
| OpenTelemetry GenAI | [profiles/opentelemetry-genai.md](../profiles/opentelemetry-genai.md) | Route B mapping |

As harnesses compose software at runtime, one behavior gets described by
different objects and units in different runtimes. [Experiment
D](../experiments/EXPERIMENT-D-cross-harness-compatibility.md) turns that into
evidence; [Proposal: Delegation](../proposals/2026-08-21-delegation-graph.md)
defines the agent-to-agent boundary the object model was missing.

## What Verovo is / is not

| Verovo is | Verovo is not |
| --- | --- |
| Measurement standard | Payment protocol |
| Usage analytics foundation | Marketplace |
| Metering semantics | Wallet |
| Comparable quality signals | Universal reputation score |
| Attribution framework | Single global source of truth |

## Who it is for

| Audience | Why |
| --- | --- |
| **Teams billed per outcome** (AI support: Intercom Fin, Zendesk, Salesforce Agentforce) | re-run the bill locally; VSS-1 settlement statements for renewals and disputes |
| **Teams billed per task / compute** (Copilot premium requests, Cursor, Devin ACU) | one semantics for "what counts as one task" when retries and loops keep billing |
| **Teams billed per usage** (APIs and gateways, multiple vendors) | align incommensurable meters into one auditable statement |
| **Capability Provider** | measure and eventually meter agent usage of your capabilities |
| **Agent Runtime** | expose decision / usage signals consistently |
| **Registry / Marketplace** | compare capabilities using standardized signals |
| **Data / Measurement Provider** | produce comparable agent-usage analytics |
| **Commerce / Payment Infrastructure** | consume standardized billable events in future profiles |
| **Researchers / Standard Contributors** | evolve the methodology |

## Try the standard

```bash
git clone https://github.com/roy-tong/verovo && cd Verovo
python3 conformance/runners/run_metrics.py   # metric vectors (M2.2 / M2.5 / M4.1)
python3 verify_vectors.py                     # verification / correlation / operation vectors
python3 registry/validate_entities.py         # validate the machine-readable registry
```

## Product MVP — first real measurement (in development)

The first product path is **Remote MCP / API Capability Measurement**: an
[Verovo Provider SDK](../sdk/) (`@verovo/mcp`) that emits observations from
the provider side (no agent-side install), feeding a local collector. Local analytics
run without any cloud:

```bash
npm install @verovo/mcp
# SDK 0.2.0 on npm; verified 2026-10-14
# wrap your MCP server's tool handlers: server.tool = (name, schema, mw.wrapTool(name, handler))
node examples/mcp-integration.js          # synthetic traffic → local JSONL
python3 product/local-analytics.py ~/.verovo/events/verovo-events.jsonl
```

Status: SDK v0.2.0 — External-Ready (canonical output, non-blocking spool with
loss accounting, per-request caller, MCP v1/v2, 21 tests, deterministic fixture) +
local analytics implemented; hosted ingestion and dashboard deferred. First real
external Provider = Product Gate A ([ROADMAP.md](../ROADMAP.md), [MVP.md](../product/MVP.md)).

Scope and acceptance: [product/MVP.md](../product/MVP.md) · SDK contract:
[product/PROVIDER-SDK.md](../product/PROVIDER-SDK.md) · Deployment:
[product/DEPLOYMENT.md](../product/DEPLOYMENT.md)

## Repository map

```text
Verovo/
├── standard/          # the normative standard (CORE / METRICS / QUALITY / DATA / ...)
├── extensions/        # experimental, non-normative profiles (COMMERCIAL.md)
├── product/           # product architecture (SDK / hosted analytics, in development)
├── whitepaper/        # methodology papers (EN/CN)
├── conformance/       # language-neutral test vectors + runners
├── reference/         # reference implementation (collector + adapters)
│   ├── collector/     #   normalization, correlation, aggregation, evidence
│   └── adapters/      #   codex / claude / dsh / mcp observation adapters
├── schemas/           # machine-readable schemas (entity registry)
├── registry/          # machine-readable registries (entities / project identity)
├── experiments/       # empirical experiment designs
├── reports/           # public reports (Discrepancy Report)
├── proposals/         # standard change proposals (AUP)
└── archive/           # retired early documents
```

**The standard is the artifact; the code is a reference implementation.** Using the standard does not mean uploading data to any central server.

## Current status & roadmap

**Draft 0.4.5** — 唯一 Canonical
Observation（schemas/observation.schema.json，6 类 payload）；Choice/Execution 从同一
Envelope 派生；M3.1 只计已解析 operation（无回退）；Attempt 级 qualification 派生；
metrics.yaml 单一事实源；四维正交（Evidence/Caller/Use Profile/Billing）。

| Capability | Standard | Reference | Real Runtime |
| --- | --- | --- | --- |
| Observed Selection Rate | Defined | Implemented | Limited |
| Observed Head-to-Head Choice Share | Defined | Implemented | Experimental |
| Operations / Attempts | Defined | Implemented | Yes |
| Operation Resolution Coverage | Defined | Implemented | No |
| Result Consumption | Defined | Implemented | Claude partial |
| Incrementality | Defined (formula) | Planned | No |
| Qualified Usage (Strict) | Defined | Implemented | Yes |

The roadmap runs on two tracks — the standard (0.4 objects & quality → 0.5 utility & economic semantics → 1.0) and the product (Remote Capability Analytics → Provider SDK + hosted analytics → metering). See [ROADMAP.md](../ROADMAP.md).

## Contribute

- **Join the community**: [Discussions](https://github.com/roy-tong/verovo/discussions) — categories: Metric Semantics · Runtime Observation · Experiments · Capability Economy · Implementers; ground rules in [docs/DISCUSSIONS.md](../docs/DISCUSSIONS.md)
- **Where to start**: the open debate on [Strict Qualified Usage as the default](https://github.com/roy-tong/verovo/discussions/1), or [onboard the first external Provider](https://github.com/roy-tong/verovo/issues/2)
- **Propose standard changes**: `proposals/` (AUP: Draft → Discussion → Accepted → Experimental → Stable)
- **Report measurement discrepancies**: `reports/` (Discrepancy Report template)
- **Fix the reference implementation**: PRs must pass all `conformance/` vectors

---

*Verovo does not define who owns the truth. It defines what evidence, under what rules, can support what conclusions.*
