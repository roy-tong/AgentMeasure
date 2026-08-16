# Measuring Software Used by AI Agents

**An Industry Methodology — Agent Usage Attribution Standard (AgentMeasure), Draft 0.2**

> Roy Tong
> The reference implementation lives in the AgentMeasure repository.

## 0. Abstract

Agents are becoming a new class of software consumer, yet the industry has no
common method for measuring how agents discover, choose, use, and depend on
software. Existing signals — downloads, stars, self-reported installs — measure
neither agents nor value. This paper defines AgentMeasure, a measurement standard for the
agent software ecosystem: what counts as an opportunity, a selection, an
invocation, a consumption, and a contribution; how these are counted, compared,
and qualified; and what conclusions each level of evidence can support. The goal
is not a dashboard. It is a shared data language for tool developers, agent
platforms, model companies, registries, investors, and researchers.

## 1. Why Agent Usage Requires a New Measurement Model

Software distribution once had a readable chain: downloaded, installed, used. The
agent economy breaks every link:

```text
Install ≠ Available
Available ≠ Presented
Presented ≠ Selected
Selected ≠ Used
Used ≠ Useful
Useful ≠ Incremental Value
```

- *Install* and *available* describe the tool's presence, not the agent's behavior.
- *Presented* — entering the agent's decision context — is the true denominator for
  choice, and it is rarely observable today.
- *Selected* is a decision; *invoked* is an execution; *completed* is a result.
- *Consumed* means the result entered the task; *useful* means it mattered.
- *Incremental value* is the counterfactual: without the tool, would the outcome
  have been worse?

Advertising learned this lesson over decades: impressions are not conversions,
clicks are not value, and attribution is not incrementality. The agent software
ecosystem can adopt the discipline on day one. AgentMeasure answers five questions:

> **Reach** — did my tool enter the agent's choice set?
> **Choice** — when the agent had a chance, did it pick me?
> **Use** — after selection, was it actually used?
> **Utility** — did the use produce a usable result?
> **Value** — without me, would the agent's outcome have been worse?

## 2. Measurement Objects

An observation is an *evidence unit*, not a *business measurement unit*. AgentMeasure
defines the business units first:

| Object | Definition | Layer |
| --- | --- | --- |
| Opportunity | an agent had the tool in its decision context | Behavior |
| Invocation | the tool actually executed | Behavior |
| Task | the unit of work an invocation serves | Behavior |
| Client | an independent agent runtime / installation | Market |
| Project | the software entity packages/tools/skills roll up to | Market |
| Category | a comparable capability class (search, coding, …) | Market |
| Observation | evidence of one of the above (a signed receipt) | Evidence |

```
Evidence Layer:   Observation
                      ↓ reconstruct
Behavior Layer:   Opportunity · Invocation · Task
                      ↓ aggregate
Market Layer:     Client · Project · Category
```

Counting observations as usage double-counts every corroborated call; counting
invocations as value confuses behavior with utility. The layers are not
interchangeable.

## 3. Agent Tool Interaction Lifecycle

Each stage is defined by its numerator, its denominator, whether it is observable
or inferred, and the minimum evidence required.

| Stage | Definition | Observable | Minimum evidence |
| --- | --- | --- | --- |
| Presented | tool entered the agent's decision context (candidate set) | agent runtime (routing) | runtime-level observation |
| Selected | agent/runtime decided to call it | agent runtime | runtime-level observation |
| Invoked | execution began | both sides | any side observation |
| Completed | returned success/failure/denied | both sides | any side observation |
| Consumed | a later model request used the result | some platforms | platform signal |
| Contributed | result influenced the task outcome | — | **inference** |

*Discovered* is deliberately replaced by *Presented*. Discovery (`tools/list`,
registry search, skill lookup) says the tool exists; presentation says the tool
entered the agent's actual decision context — the difference between a billboard
that was rented and an ad that was shown. Three states with very different
business meaning:

```text
Available ✓ Presented ✓ Selected ✓   ← chosen
Available ✓ Presented ✓ Selected ✗   ← missed opportunity (Selection Rate denominator)
Available ✓ Presented ✗              ← never in the game (distribution gap)
```

## 4. Measurement Framework

AgentMeasure defines **metric families**, not a universal KPI. A search tool, a payment
tool, and an enterprise SaaS tool have different value structures; one north star
cannot serve all.

**M1 Distribution — Reach.** Is my tool in the agent world?
`Available Clients · Presented Opportunities · Presentation Rate · Agent Host
Coverage · Model/Runtime Coverage`

**M2 Choice — the most agent-native family.** When the agent had a chance, did it
choose me?
`Selections · Selection Rate (Selected ÷ Presented) · Share of Choice ·
First-choice Rate · Substitution Rate · Switch Rate`

**M3 Execution — Use.** Was it usable after selection?
`Logical Invocations · Completion Rate · Success Rate · Error/Retry Rate ·
Latency · Cost`

**M4 Utility — effective use.** Did the agent actually use what was returned?
`Result Delivered Rate · Result Consumed Rate · Continuation Rate · Correction
Rate · Fallback Rate`

**M5 Outcome — Value.** Did it improve the task?
`Task Success Association · Contribution · Incremental Lift · Time Saved · Cost
Saved · Human Intervention Reduced`

### Selection Rate

\[
Selection\ Rate = \frac{Selected\ Opportunities}{Presented\ Opportunities}
\]

Tool A: presented 100,000, selected 5,000 → 5%. Tool B: presented 10,000, selected
4,000 → 40%. Absolute calls favor A; agent preference strongly favors B. Selection
Rate answers the question developers actually care about: *when the agent had the
chance, how often did it choose me?*

### Share of Agent Choice

For a capability category (say, web search) with several substitutable tools:

\[
SoC = \frac{tool\ selections}{all\ selections\ in\ comparable\ capability}
\]

A developer would then see not "1.2M calls" but:

```text
Search category
Exa       Presented Share 31% · Selection Share 44% · Selection Rate 58% · Repeat Selection 71%
```

This is agent-software market data, not telemetry.

## 5. Relationship Measurement

Across-time relationships, defined agent-natively:

| Relationship | Definition |
| --- | --- |
| Trial | first use |
| Active | eligible usage within the period |
| Repeated | usage across multiple windows |
| Preferred | sustained first choice within comparable candidate sets |
| Dependent | task performance degrades significantly when the tool is removed |

Dependency is the long-term asset metric: the most valuable tool is not the most
called — it is the least replaceable. `Adoption → Preference → Utility →
Dependency` is an agent-native tool relationship model.

## 6. Attribution vs Incrementality

**A tool's participation in a successful task is not evidence that it caused the
success.**

- **Attribution measurement** is observational: which tools participated in the
  task chain. It supports claims of *association* and *contribution to the
  execution chain* — nothing more.
- **Incrementality measurement** is counterfactual: how much additional value did
  the tool create? The method is randomized comparison — treatment (tool
  available) vs control (tool invisible) — across task success, time, token cost,
  total tool calls, human intervention, and quality:

```text
Incremental Task Success = P(Success | Tool) − P(Success | No Tool)
Time Lift   = Time(control) − Time(tool)
Cost Lift   = Cost(control) − Cost(tool)
```

Advertising moved from last-click attribution to holdout groups and incrementality
testing for exactly this reason. Agent tools inherit the lesson. AgentMeasure separates
the two measurement regimes from the first day.

## 7. Measurement Quality

Evidence quality is not coverage quality; both are not qualification quality; none
is methodology. A set of perfectly attested events covering 2% of agents is not
market data.

```text
Measurement Quality
├── Evidence        is this event real? (signature, corroboration)
├── Coverage        how much of the world did we see?
├── Qualification   does this count as real production use?
├── Sampling        sampled? with what uncertainty?
├── Identity        how well do identifiers resolve to projects?
└── Method/version  which statistics, which spec version?
```

### Qualified Agent Usage

Raw invocations are not qualified usage. A large share of future tool traffic
will not represent adoption: developer self-testing, CI, benchmarks, evals,
synthetic agents, health checks, retry storms, agent loops, replays, load tests,
demos. AgentMeasure requires a **Usage Context** on every observation:

```text
production · development · test · benchmark · evaluation · synthetic · ci · unknown
```

Public adoption metrics default to `production` plus separately disclosed
`unknown`; benchmark, eval, test, CI, and synthetic usage are never mixed into
qualified usage. Context qualification may matter more than evidence grading in
deciding whether a leaderboard is believable.

## 8. Standard Reporting

### Measurement Label

Every published metric carries a label — a nutrition label for numbers, not a
quality score:

```text
Agent Usage Measurement Label
Standard version:   0.2
Window:             30 days
Usage context:      production
Agent hosts:        Claude Code, Codex
Coverage:           partial
Collection:         client + server
Corroborated:       68%
Sampling:           none
Unknown context:    12%
Synthetic excluded: yes
Identity coverage:  91%
```

The label does not grade the data; it discloses how the number was produced so
that the reader can judge its applicability.

### Measurement Profiles

AgentMeasure defines standard profiles instead of a universal north star:

| Profile | North Star | Guardrails | Diagnostics |
| --- | --- | --- | --- |
| Adoption | Active Clients | Qualified Usage Rate, Coverage | Presented, Selection Rate, Repeat |
| Reliability | Successful Completed Invocations | p95 latency, cost, retry | error type, host, version |
| Utility | Consumed Results | Correction Rate, Fallback Rate | completion→consumption conversion |
| Value | Incremental Task Success | Cost, Latency, Safety | task type, model, alternatives |

Organizations choose a profile by use case; the standard defines the families, not
the winner.

## 9. Interoperability

The standard is transport-neutral and vendor-neutral. Current infrastructure binds
to it as implementation examples, not as preconditions: MCP carries lifecycle
events and trace context; OpenTelemetry carries tool spans; Codex, Claude Code,
and DeepSeek Harness expose observation points with declared capability matrices.
Technical choices — signature algorithms, collection formats, storage — live in
the reference implementation and its profiles, so that the methodology does not
expire when the technology changes.

## 10. Open Questions

1. **Task boundaries.** What is the unit of a "task," and who defines it?
2. **Contribution.** How to measure result contribution beyond consumption?
3. **Incrementality.** How to run counterfactual experiments at ecosystem scale
   without disturbing production?
4. **Candidate-set observability.** Presentation is the key denominator; most
   runtimes do not expose it yet.
5. **Privacy.** How far can correlation and retention go under pseudonymity?
6. **Cross-agent identity.** Same client across Codex, Claude, and DSH — when is
   that knowable?

---

*The normative specification (Measurement Objects, Lifecycle, Metric Families,
Quality, Reporting) and the reference implementation (AgentMeasure) are published
openly. Graduation to AgentMeasure 1.0 requires two independent implementations, three
runtime profiles, two tool-side implementations, a public conformance suite with
canonical test vectors, 5–10 real projects, a published discrepancy report, and
security and privacy reviews.*
