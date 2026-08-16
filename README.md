# AgentMeasure

**A proposed open measurement standard for software used by AI agents.**

> AgentMeasure is an open measurement standard that uses a unified data language to
> measure how AI agents discover, choose, and use software — and how much value that
> software ultimately creates.
>
> Traditional software metrics measure what humans download and use. AgentMeasure
> measures what agents see, what they choose, what they actually use, and whether
> those choices create value.

[Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [白皮书（中文）](whitepaper/agent-tool-economy-zh.md) · [Core Specification](standard/CORE.md) · [中文](README.zh-CN.md)

## Why

Agents are becoming software's new consumers, but every existing signal breaks down —
download counts measure humans, not agents; self-reported installs are gameable;
registries don't expose adoption data.

```text
Install ≠ Available
Available ≠ Presented
Presented ≠ Selected
Selected ≠ Used
Used ≠ Useful
Useful ≠ Incremental Value
```

AgentMeasure answers five questions: **Reach → Choice → Use → Utility → Value**

1. **Reach** — does my software enter an agent's selection range?
2. **Choice** — when an agent has the opportunity, does it pick me? (Observed Selection Rate / Conditional Choice Share)
3. **Use** — after being chosen, is it actually used?
4. **Utility** — does using it produce useful results? (Result Consumption)
5. **Value** — without me, would the agent's outcome be worse? (Incrementality)

## Five-layer measurement framework

| Layer | Question | Representative metrics |
| --- | --- | --- |
| Reach | Did it enter the agent world | Presented Opportunities、Active Clients |
| Choice | Would it be chosen when given the chance | Observed Selection Rate、Conditional Choice Share |
| Use | Is it usable once chosen | Logical Invocations、Completion Rate、Success Rate |
| Utility | Was the result used | Result Consumed Rate |
| Value | Did it create value | Incremental Task Success（Draft 0.5） |

## Core concepts

- **Decision Opportunity / Candidate Set / Presentation / Selection** — the four
  objects of choice behavior; the Observed Selection Rate denominator is Presented,
  not Available
- **Observed Selection Rate** = Observed Selected ÷ Presented — the probability an
  agent picks you when it truly has the chance
  (observed ≠ preference: a "choice" under required/forced constraint is not a preference)
- **Conditional Choice Share** — head-to-head preference when A and B actually compete
  in the same candidate set
- **Software Entity / Capability / Interaction Surface** — what exists, what it can
  do, and the observable interface; observation happens on surfaces, attribution
  resolves to entities (see [AgentMeasure Entity](standard/ENTITY.md))
- **Operation / Attempt** — a logical use vs. a single execution; retries are multiple
  attempts of one operation, not a validity class
- **Qualified Usage** — real production use after excluding benchmark / test /
  synthetic / retry
- **Result Consumption** — the result was actually used by the task (≠ successful return)
- **Incrementality** — would the outcome be worse without this software?
- **Measurement Label** — a nutrition label for every public number (coverage /
  sampling / policy / method)

## Who is this for?

| Audience | Entry |
| --- | --- |
| Tool / MCP developers | [Quickstart](#quickstart) · [Runtime Profiles](standard/PROFILES.md) |
| Agent runtime platforms | [Runtime Profile](standard/PROFILES.md) · Observability |
| Data researchers | [Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [Metrics](standard/METRICS.md) |
| Standard contributors | [Core](standard/CORE.md) · [Proposals](proposals/) |
| Third-party implementers | [Conformance](conformance/) |

## Repository map

```text
AgentMeasure/
├── standard/          # the standard itself (CORE / METRICS / QUALITY / DATA / ...)
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

**The standard is the artifact; the code is a reference implementation.** Using the
standard does not mean uploading data to any central server.

## Quickstart

```bash
git clone https://github.com/roy-tong/AgentMeasure && cd AgentMeasure
python3 conformance/runners/run_metrics.py   # run metric vectors (16/16 + M2.5/M4.1)
python3 verify_vectors.py                     # receipt / correlation / operation vectors
python3 registry/validate_entities.py         # validate machine-readable registry
```

After feeding in Decision Opportunity events, the reference implementation outputs:

```text
AgentMeasure Demo

Reach
Presented Opportunities    150

Choice
Observed Selection Rate   43.3%

Use
Invocations                  62
Completion Rate           96.8%

Utility
Observable Results           41
Consumed Results             28
Consumption Rate          68.3%

Measurement Quality
Usage Context        production
Coverage             partial
Sampling             none
```

Data stays local by default; public metrics must carry a
[Measurement Label](standard/QUALITY.md).

## Current status

**Draft 0.4（Measurement Objects & Verification Decoupling）** — measurement objects
are now entity-based (Software Entity → Capability → Interaction Surface), Core is
decoupled from the Verification Profile.

| Capability | Standard | Reference | Real Runtime |
| --- | --- | --- | --- |
| Observed Selection Rate | Defined | Implemented | Limited |
| Conditional Choice Share | Defined | Implemented | Experimental |
| Logical Invocations | Defined | Implemented | Yes |
| Result Consumption | Defined | Implemented | Claude partial |
| Incrementality | Defined (formula) | Planned | No |
| Qualified Usage | Defined | Implemented | Yes |

Defined ≠ fully measurable today. Capabilities are being validated one by one.

Roadmap: Draft 0.3 (semantics) → **0.4 (objects & quality)** → 0.5 (value) → 1.0
(graduation: 2 independent implementations + 3 runtime profiles + public conformance
+ 5-10 real projects).

## How to contribute

- **Discuss measurement semantics**: GitHub Discussions (Metric Semantics / Measurement Quality / Runtime Profiles / Proposals / Experiments / General)
- **Propose standard changes**: `proposals/` (AUP: Draft → Discussion → Accepted → Experimental → Stable)
- **Report measurement discrepancies**: `reports/` (Discrepancy Report template)
- **Fix the reference implementation**: PRs must pass all `conformance/` vectors

---

*AgentMeasure does not define who owns the truth. It defines what evidence, under
what rules, can support what conclusions.*
