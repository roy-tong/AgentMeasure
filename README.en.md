# AgentMeasure

**An open measurement standard for software used by AI agents.**

> Traditional software metrics measure human distribution. AgentMeasure measures
> agent decisions, usage, utility, and value.

[Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md) · [Core Specification](standard/CORE.md) · [中文](README.md)

## Why

Agents are becoming a new class of software consumer, and every existing signal fails:
downloads measure humans, self-reported installs are gameable, registries publish no
adoption data.

```text
Install ≠ Available
Available ≠ Presented
Presented ≠ Selected
Selected ≠ Used
Used ≠ Useful
Useful ≠ Incremental Value
```

**Reach → Choice → Use → Utility → Value.**

## Core concepts

- Decision Opportunity / Candidate Set / Presentation / Selection
- Selection Rate (Selected ÷ Presented)
- Conditional Choice Share (head-to-head agent preference)
- Qualified Usage (excludes benchmark/test/synthetic/retry)
- Result Consumption (≠ successful return)
- Incrementality (would the outcome be worse without this software?)
- Measurement Label (nutrition label for every public number)

## Who is this for?

| Audience | Entry |
|---|---|
| Tool / MCP developers | Quickstart · Runtime Profiles |
| Agent runtime platforms | Runtime Profile · Observability |
| Data researchers | Whitepaper · Metrics |
| Standard contributors | Core · Proposals |
| Third-party implementers | Conformance |

## Repository map

```text
AgentMeasure/
├── standard/          # the standard itself (CORE/METRICS/QUALITY/DATA/...)
├── whitepaper/        # methodology papers (EN/CN)
├── conformance/       # language-neutral test vectors + runners
├── reference/         # reference implementation (collector + adapters)
├── experiments/       # empirical experiment designs
├── reports/           # public reports (Discrepancy Report)
├── proposals/         # standard change proposals (AUP)
└── archive/           # retired early documents
```

**The standard is the本体; the code is a reference implementation.** Using the
standard does not mean uploading data to any central server.

## Status

Draft 0.3 — Metric Semantics & Denominator Discipline.

| Capability | Standard | Reference | Real Runtime |
| --- | --- | --- | --- |
| Selection Rate | Defined | Implemented | Limited |
| Conditional Choice Share | Defined | Implemented | Experimental |
| Logical Invocations | Defined | Implemented | Yes |
| Result Consumption | Defined | Implemented | Claude partial |
| Incrementality | Defined (formula) | Planned | No |
| Qualified Usage | Defined | Implemented | Yes |

## Contribute

Discussions: Metric Semantics / Measurement Quality / Runtime Profiles / Proposals /
Experiments / General. PRs must pass `conformance/` vectors.

---

*AgentMeasure does not define who owns the truth. It defines what evidence, under
what rules, can support what conclusions.*
