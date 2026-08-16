# AgentMeasure

**Open measurement infrastructure for the Agent Capability Economy.**

AgentMeasure defines a common language for measuring how AI agents discover, choose, use, and derive value from software capabilities.

**Today:** measure agent-facing capability usage.
**Next:** make capabilities comparable and meterable.
**Long term:** provide the measurement foundation for Capability as a Service (CaaS).

**Reach → Choice → Use → Utility → Value**

> AgentMeasure is **not** a payment protocol, marketplace, or universal ranking system.
> It standardizes the facts and measurement semantics those systems can build on.

[Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [白皮书（中文）](whitepaper/measuring-software-used-by-ai-agents.zh-CN.md) · [Core Specification](standard/CORE.md) · [中文](README.zh-CN.md)

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
| **Choice** | When the agent had the chance, did it choose it? | Observed Selection Rate · Conditional Choice Share |
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

Claim discipline throughout: *observed choice is not preference*. A selection can be made by the model, a router, a workflow, the user, a policy, or the platform; **Observed Selection Rate** reports what was observed, and **Conditional Choice Share** is an *observed head-to-head choice share under comparable candidate conditions* — comparable means the same candidate set, category, choice mode, and decision axes (Decision Authority / Selection Constraint) are declared.

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

## Product MVP — in development

The first product path is **Remote MCP / API Capability Measurement**: an AgentMeasure
Provider SDK that emits observations from the provider side (no agent-side install),
feeding a collector and hosted analytics. The SDK and hosted analytics are not
implemented yet — the standard, reference collector, and conformance suite are.

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

**Draft 0.4（Measurement Objects & Verification Decoupling）** — entity-based measurement objects, Operation/Attempt, Core decoupled from the Verification Profile.

| Capability | Standard | Reference | Real Runtime |
| --- | --- | --- | --- |
| Observed Selection Rate | Defined | Implemented | Limited |
| Conditional Choice Share | Defined | Implemented | Experimental |
| Operations / Attempts | Defined | Implemented | Yes |
| Result Consumption | Defined | Implemented | Claude partial |
| Incrementality | Defined (formula) | Planned | No |
| Qualified Usage | Defined | Implemented | Yes |

The roadmap runs on two tracks — the standard (0.4 objects & quality → 0.5 utility & economic semantics → 1.0) and the product (Remote Capability Analytics → Provider SDK + hosted analytics → metering). See [ROADMAP.md](ROADMAP.md).

## Contribute

- **Discuss measurement semantics**: GitHub Discussions (Metric Semantics / Measurement Quality / Runtime Profiles / Proposals / Experiments / General)
- **Propose standard changes**: `proposals/` (AUP: Draft → Discussion → Accepted → Experimental → Stable)
- **Report measurement discrepancies**: `reports/` (Discrepancy Report template)
- **Fix the reference implementation**: PRs must pass all `conformance/` vectors

---

*AgentMeasure does not define who owns the truth. It defines what evidence, under what rules, can support what conclusions.*
