# AgentMeasure

**Test whether your agent metrics mean what their labels claim.**

Conformance checks for AI-agent telemetry — a retry is one logical operation, not two requests; a reasoning-token subset must not be added into totals; a cache hit is not a new measurement. Every check reports **PASS / FAIL / UNPROVABLE**, and UNPROVABLE is a first-class result: when the evidence to decide is absent, it is disclosed, never zeroed.

```yaml
# .github/workflows/conformance.yml — turn measurement assumptions into CI checks
- uses: roy-tong/AgentMeasure@469bfc3
  with:
    fixture: fixtures/telemetry.jsonl   # your FMT-002 event fixture
```

[**Run conformance locally**](conformance/pack/README.md) · [**See real failures**](#external-provider-trials) · [Read the spec](standard/CORE.md) · [中文](README.zh-CN.md)

[![CI: conformance](https://github.com/roy-tong/AgentMeasure/actions/workflows/conformance.yml/badge.svg)](https://github.com/roy-tong/AgentMeasure/actions/workflows/conformance.yml)
[![Spec](https://img.shields.io/badge/spec-Draft_0.4-blue)](standard/CORE.md)
[![Release](https://img.shields.io/github/v/release/roy-tong/AgentMeasure?include_prereleases)](https://github.com/roy-tong/AgentMeasure/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](LICENSE)
[![Discussions](https://img.shields.io/github/discussions/roy-tong/AgentMeasure)](https://github.com/roy-tong/AgentMeasure/discussions)

> **AgentMeasure separates execution facts from logical operations, evidence
> from inference, and economic settlement from value** — an open measurement
> layer for the Agent Capability Economy. One number for your dashboards
> (logical operations), the evidence for what each number counts, and explicit
> disclosure for what it cannot prove.

**Today:** measure agent-facing capability usage — attempts, operations, retry
inflation, success rates with numerators you can audit.
**Next:** make capabilities comparable and meterable.
**Long term:** provide the measurement foundation for Capability as a Service (CaaS).

**Reach → Choice → Use → Utility → Value**

> AgentMeasure is **not** a payment protocol, marketplace, or universal ranking system.
> It standardizes the facts and measurement semantics those systems can build on.

[**Website**](https://roy-tong.github.io/AgentMeasure/) · [Send a trace → get a measurement check](mailto:tongroy18@gmail.com?subject=AgentMeasure%20measurement%20check%20-%20%5Byour%20capability%5D&body=Hi%2C%0A%0AI%27d%20like%20a%20zero-install%20measurement%20check.%0A%0A1.%20Data%3A%2020-100%20anonymized%20trace/log%20rows%2C%20or%20a%20link%20to%20a%20public%20export%20%28production%20or%20synthetic%20-%20please%20say%20which%29%3A%0A%0A2.%20Source%20and%20time%20window%3A%0A%0A3.%20The%20decision%20this%20should%20inform%3A%0A%0ANote%3A%20raw%20data%20stays%20local%20by%20default.%20If%20I%20share%20a%20sanitized%20sample%2C%20I%27ll%20state%20what%20may%20be%20done%20with%20it.) · [Free 7-day audit — apply](https://github.com/roy-tong/AgentMeasure/issues/new?template=5-provider-trial.yml) · [30 Projects / 30 Days campaign](campaigns/30-projects-30-days.md) · [Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [Core Specification](standard/CORE.md)

![AgentMeasure — The Measurement Stack](assets/agentmeasure-stack.svg)

**Start with the story:** [When the Software Consumer Becomes an Agent](https://roy-tong.github.io/en/notes/when-the-software-consumer-becomes-an-agent/) (EN) · [当软件的消费者变成 Agent](https://roy-tong.github.io/notes/when-the-software-consumer-becomes-an-agent/) (ZH)

## Try it in 2 minutes

```bash
./examples/demo-e2e.sh
```

Mock MCP server → canonical observations → local metrics, all on your machine, no
cloud. The demo is **reproducible**: it runs in an isolated workspace (never touches
`~/.agentmeasure`) — same fixture + same policy = same result (42 calls → 84
canonical observations, caller claims claude:14 · codex:14 · unknown:14).

Then read why we audit the ecosystem's usage claims:
[Benchmark Run #001](reports/benchmark-run-001.md) — six real claims profiled with
the Evidence Profile (multi-axis, no composite scores), and
[Pipeline Validation #001](reports/pipeline-validation-001.md) — our own fixture,
kept out of the ranking as a reference baseline.

---

## Run a preregistered experiment — AgentMeasure Lab

```bash
python3 lab/am lab selftest                                   # planted uplift recovered + honest null
python3 lab/am lab init                                       # workspace + example experiment
python3 lab/am lab preregister am-lab/experiments/example-manifest.json
python3 lab/am lab run am-lab/experiments/example-manifest.prereg.json
```

The open experiment engine ([lab/](lab/README.md)): task set × harness matrix × factor
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
Docs: [lab/README.md](lab/README.md) · formats:
[lab/schemas/](lab/schemas/) (experiment manifest / funnel events / report).

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

If the check pays for itself, AgentMeasure is looking for **3 MCP/API providers** for short external measurement runs.

The goal is not to prove the model works. It is to find where it breaks on real provider traffic.

A trial can stay fully local, requires no agent-side install, and can start with one capability.

**Best feedback:** a concrete trace, counterexample, or field that cannot be measured safely.

→ The formal offer, schedule, and FAQ live in **[product/AUDIT.md](product/AUDIT.md)** · apply in **[Issue #2 — Looking for 3 MCP/API providers for external measurement runs](https://github.com/roy-tong/AgentMeasure/issues/2)**.

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

If a capability is to become an economic unit that agents can discover, compare, and eventually purchase automatically, it must first be **identifiable, measurable, and comparable under a shared semantics**. That is what AgentMeasure provides.

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
> lives in [docs/CAPABILITY-ECONOMY.md](docs/CAPABILITY-ECONOMY.md).

## The measurement view: Reach → Choice → Use → Utility → Value

AgentMeasure defines **metric families**, not a universal KPI. A search capability, a booking API, and a compute job have different value structures.

| Layer | Question | Representative metrics |
| --- | --- | --- |
| **Reach** | Did the capability enter the agent's choice range? | Eligible Opportunities · Presentations · Presentation Rate · Distribution Coverage |
| **Choice** | When the agent had the chance, did it choose it? | Observed Selection Rate · Observed Head-to-Head Choice Share |
| **Use** | After selection, was it actually used? | Operations · Attempts · Completion Rate · Success Rate |
| **Utility** | Did it produce a usable result or confirmed effect? | Result Consumption · Effect Confirmation |
| **Value** | Did it improve the task outcome? | Incremental Task Success（Draft 0.5） |

The five layers are the **measurement view**. The same facts map onto an economic view:

| CaaS Domain | AgentMeasure |
| --- | --- |
| Demand | Reach + Choice |
| Delivery | Use + Utility |
| Outcome | Value |
| Economics | Metering / Attribution（future extension） |

Claim discipline throughout: *observed choice is not preference*. A selection can be made by the model, a router, a workflow, the user, a policy, or the platform; **Observed Selection Rate** reports what was observed, and **Observed Head-to-Head Choice Share** is an *observed head-to-head choice share under comparable candidate conditions* — comparable means the same candidate set, category, choice mode, and decision axes (Decision Authority / Selection Constraint) are declared.

## How AgentMeasure works in production

```text
Agent Runtime                     Capability Provider

Claude / Codex
      │
      │ MCP / API
      ▼
                         ┌──────────────────────┐
                         │ Customer Capability  │
                         │                      │
                         │ AgentMeasure SDK     │
                         │ Business Handler     │
                         └──────────┬───────────┘
                                    │
                               observations
                                    │
                                    ▼
                              Collector
                                    │
                                    ▼
                            AgentMeasure Cloud
```

Four things a real developer needs to know:

> Your software does **not** need to be open source.
>
> MCP is **not** required — it is the first reference surface.
>
> Third-party agents do **not** need AgentMeasure installed for provider-side usage measurement.
>
> AgentMeasure is **not** on the critical request path.

Product architecture (Provider SDK → local buffer → hosted ingestion → dashboard):
[product/ARCHITECTURE.md](product/ARCHITECTURE.md).

## What AgentMeasure measures today

- **Decision Opportunity / Candidate Set / Presentation / Selection** — the four objects of choice; the Observed Selection Rate denominator is Presented, not Available
- **Software Entity → Capability → Interaction Surface** — what exists, what it can do, and the observable interface; observation happens on surfaces, attribution resolves to entities through the machine-readable registry
- **Operation / Attempt** — one logical use vs. one execution; **retries are multiple attempts of one operation**, not a validity class (they are kept as reliability signals, not counted as distinct logical uses)
- **Qualified Usage** — production usage after excluding test, benchmark, synthetic, replay, duplicate and other invalid traffic according to policy
- **Result Consumption** — *defined, reference partial*: the result was used by the task
- **Effect Confirmation** — *domain model defined, metric planned for Draft 0.5*: the intended world-state change was confirmed
- **Measurement Label** — a nutrition label for every public number (coverage / sampling / policy / method)

The full model lives in the [Core Specification](standard/CORE.md), [Metrics](standard/METRICS.md), [Entity](standard/ENTITY.md), and [Quality](standard/QUALITY.md). The README is not a spec summary.

## From measurement to CaaS

AgentMeasure is **progressively standardizing** the measurement chain from discovery
and choice through execution, utility and value: core usage semantics are defined
today; utility/value and commercial metering remain active drafts. Metering and
commercial attribution are future extensions; payment rails can be provided by
existing payment infrastructure.

> **AgentMeasure standardizes economic facts, not money movement.**
>
> Extended thesis: [docs/CAPABILITY-ECONOMY.md](docs/CAPABILITY-ECONOMY.md) ·
> Economic semantics: [extensions/COMMERCIAL.md](extensions/COMMERCIAL.md)（Experimental）

## Harness profiles — what each runtime can (and cannot) observe

Portable semantics need a public record of observation blind spots. Per-harness
profiles map each runtime's native objects to AgentMeasure semantics:

| Harness | Profile | Highlights |
| --- | --- | --- |
| Codex | [profiles/codex.md](profiles/codex.md) | hook 观察，无 trace/精确时间戳；App Server 事件流为优先生效观察面 |
| Claude Code | [profiles/claude-code.md](profiles/claude-code.md) | 内置成败判定；第一个 Consumption 可实证平台 |
| DeepSeek Harness | [profiles/deepseek-harness.md](profiles/deepseek-harness.md) | append-only session log；subagent lineage/depth 是 Delegation 的首个真实数据源 |
| Pydantic AI | [profiles/pydantic-ai.md](profiles/pydantic-ai.md) | Logfire spans → attempt 语义 |
| OpenTelemetry GenAI | [profiles/opentelemetry-genai.md](profiles/opentelemetry-genai.md) | Route B mapping |

As harnesses compose software at runtime, one behavior gets described by
different objects and units in different runtimes. [Experiment
D](experiments/EXPERIMENT-D-cross-harness-compatibility.md) turns that into
evidence; [Proposal: Delegation](proposals/2026-08-21-delegation-graph.md)
defines the agent-to-agent boundary the object model was missing.

## What AgentMeasure is / is not

| AgentMeasure is | AgentMeasure is not |
| --- | --- |
| Measurement standard | Payment protocol |
| Usage analytics foundation | Marketplace |
| Metering semantics | Wallet |
| Comparable quality signals | Universal reputation score |
| Attribution framework | Single global source of truth |

## Who it is for

| Audience | Why |
| --- | --- |
| **Capability Provider** | measure and eventually meter agent usage of your capabilities |
| **Agent Runtime** | expose decision / usage signals consistently |
| **Registry / Marketplace** | compare capabilities using standardized signals |
| **Data / Measurement Provider** | produce comparable agent-usage analytics |
| **Commerce / Payment Infrastructure** | consume standardized billable events in future profiles |
| **Researchers / Standard Contributors** | evolve the methodology |

## Try the standard

```bash
git clone https://github.com/roy-tong/AgentMeasure && cd AgentMeasure
python3 conformance/runners/run_metrics.py   # metric vectors (M2.2 / M2.5 / M4.1)
python3 verify_vectors.py                     # verification / correlation / operation vectors
python3 registry/validate_entities.py         # validate the machine-readable registry
```

## Product MVP — first real measurement (in development)

The first product path is **Remote MCP / API Capability Measurement**: an
[AgentMeasure Provider SDK](sdk/) (`@agentmeasure/mcp`) that emits observations from
the provider side (no agent-side install), feeding a local collector. Local analytics
run without any cloud:

```bash
npm install https://github.com/roy-tong/AgentMeasure/releases/download/v0.1.1/agentmeasure-mcp-0.1.1.tgz
# (npm registry publish pending scope/token — tarball is the current install path)
# wrap your MCP server's tool handlers: server.tool = (name, schema, mw.wrapTool(name, handler))
node examples/mcp-integration.js          # synthetic traffic → local JSONL
python3 product/local-analytics.py ~/.agentmeasure/events/agentmeasure-events.jsonl
```

Status: SDK v0.1.1 — External-Ready (canonical output, non-blocking spool with
loss accounting, per-request caller, MCP v1/v2, 21 tests, deterministic fixture) +
local analytics implemented; hosted ingestion and dashboard next. First real
external Provider = Product Gate A ([ROADMAP.md](ROADMAP.md), [MVP.md](product/MVP.md)).

Scope and acceptance: [product/MVP.md](product/MVP.md) · SDK contract:
[product/PROVIDER-SDK.md](product/PROVIDER-SDK.md) · Deployment:
[product/DEPLOYMENT.md](product/DEPLOYMENT.md)

## Repository map

```text
AgentMeasure/
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

**Draft 0.4.4（Canonicalization & Reference Convergence）** — 唯一 Canonical
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

The roadmap runs on two tracks — the standard (0.4 objects & quality → 0.5 utility & economic semantics → 1.0) and the product (Remote Capability Analytics → Provider SDK + hosted analytics → metering). See [ROADMAP.md](ROADMAP.md).

## Contribute

- **Join the community**: [Discussions](https://github.com/roy-tong/AgentMeasure/discussions) — categories: Metric Semantics · Runtime Observation · Experiments · Capability Economy · Implementers; ground rules in [docs/DISCUSSIONS.md](docs/DISCUSSIONS.md)
- **Where to start**: the open debate on [Strict Qualified Usage as the default](https://github.com/roy-tong/AgentMeasure/discussions/1), or [onboard the first external Provider](https://github.com/roy-tong/AgentMeasure/issues/2)
- **Propose standard changes**: `proposals/` (AUP: Draft → Discussion → Accepted → Experimental → Stable)
- **Report measurement discrepancies**: `reports/` (Discrepancy Report template)
- **Fix the reference implementation**: PRs must pass all `conformance/` vectors

---

*AgentMeasure does not define who owns the truth. It defines what evidence, under what rules, can support what conclusions.*
