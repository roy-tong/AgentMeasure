# Measuring Software Used by AI Agents

**A Measurement Foundation for Capability as a Service and the Agent Capability Economy**

*Whitepaper v0.2 · AgentMeasure Standard Draft 0.4*

> Roy Tong
> The reference implementation lives in the AgentMeasure repository.

## 0. Abstract

AI agents are becoming both software consumers and autonomous economic actors. As
interfaces such as Skills, MCP servers, APIs and CLIs become easier to create and
distribute, economic value increasingly shifts toward the scarce capabilities behind
them: proprietary data, compute, execution, permissions, transactions and real-world
fulfillment.

This creates a measurement problem before it creates a payment problem. A capability
cannot be reliably priced, compared, billed or optimized until the ecosystem agrees
on what constitutes a selection, an operation, a successful delivery, a consumed
result, an outcome and a billable unit.

AgentMeasure proposes an open measurement standard for this emerging capability
economy: a common data language — reach, choice, use, utility, value — plus the
measurement semantics that metering, marketplaces and payment rails can later build
on. The goal is not a dashboard. It is the measurement foundation that makes
Capability as a Service (CaaS) possible.

## 1. From SaaS to Capability Economy

Software distribution once had a readable chain: downloaded, installed, used. Each
era has had its own economic unit:

```text
SaaS
Human → Application → Seat / Month

API Economy
Software → API → Request / Token

Capability Economy
Agent → Capability → Operation / Outcome
```

Three forces are driving the shift to the third row.

**Interfaces are being absorbed by agents.** The UI and the workflow are increasingly
executed by the agent, not presented to a human. What remains for software is a
callable surface — a skill file, an MCP tool, a CLI, an endpoint.

**Distribution artifacts are commoditizing.** An open Skill, an open MCP adapter, an
open CLI can be authored and published by anyone in hours. Interfaces may become
cheap to create; capabilities remain scarce to deliver.

**Scarcity moved down the stack.** The scarce layer is no longer the app shell; it is
what the callable surface controls access to:

```text
Data · Compute · Action · Permission · Trust · Real-world fulfillment
```

A search capability is scarce because of its index; a booking capability because it
can confirm a reservation; a payment capability because it can move money. When
commercial value concentrates in the capability, the natural economic unit becomes
the operation, the quantity, the effect, the outcome — or a revenue share on any of
them.

**If capability becomes the economic unit, capability measurement becomes
infrastructure.** That is the thesis of this paper.

## 2. Measurement Before Monetization

Before CaaS can have pricing, billing and reputation, it needs common measurement
semantics. Four questions make the point:

```text
One user task → 1 Operation → 3 retries
Charge 1 time or 3?

Tool returned successfully → Agent ignored the result
Was value delivered?

Booking API executed → reservation was never confirmed
Was the capability fulfilled?

Task succeeded → would it succeed without the capability?
Can the provider claim value?
```

None of these questions can be answered by raw call counts, and none of them can be
answered by a payment rail. They require agreed definitions of *operation*, *attempt*,
*delivery*, *consumption*, *effect* and *outcome* — and agreed rules for turning
observations into those objects. That agreement is the wedge: **measurement before
monetization**.

## 3. Measurement Objects

An observation is an *evidence unit*, not a *business measurement unit*. AgentMeasure
defines the business units first:

```text
Provider
    ↓
Software Entity
    ↓
Capability
    ↓
Interaction Surface
```

> **Capability is the economic object. Interaction Surface is the delivery interface.
> Software Entity is the identity/container.**

| Object | Definition | Layer |
| --- | --- | --- |
| Software Entity | the software being measured: tool, skill, API, data source, agent, application, runtime capability | Market |
| Capability | a named function of an entity — the economic object | Market |
| Interaction Surface | the observable calling interface of a capability (mcp_tool, cli_command, http_endpoint, …) | Market |
| Decision Opportunity | one tool-choice decision | Behavior |
| Candidate Set | the set actually offered in that decision | Behavior |
| Presentation | a selectable appearing in the candidate set | Behavior |
| Selection | the agent choosing a selectable | Behavior |
| Operation | one logical use of a capability for a task | Behavior |
| Attempt | one execution of an operation (**retries = multiple attempts**) | Behavior |
| Result / Effect | what the capability returned / what changed in the world | Behavior |
| Task | the unit of work an operation serves | Behavior |
| Client | an independent agent runtime / installation | Market |
| Project | the software entity packages/tools/skills roll up to | Market |
| Category | a comparable capability class (search, booking, …) | Market |
| Observation | evidence of one of the above (a signed receipt) | Evidence |

Observation happens on **Interaction Surfaces**; attribution resolves to **Software
Entities** through a machine-readable registry — never guessed at observation time.

Pricing is deliberately **not** an object of the core model. An `Offering` — pricing
model, billable unit, price, SLA, commercial constraints — is defined in the
Commercial Extension (experimental, non-normative), so that measurement semantics
can evolve without being coupled to any payment design.

## 4. Agent–Capability Interaction Model

**Reach → Value is a measurement view, not a universal execution state machine.**
Different classes of capabilities have different meaningful chains:

```text
Information   Operation → Result → Consumption
Action        Operation → Effect → Confirmation
Transaction   Operation → Authorization → Commit / Settlement
```

The Interaction Class (information / action / transaction / computation /
communication / control / storage / sensing) determines which chain applies and
therefore which Utility signals are meaningful. A search result is *consumed*; a
booking is *confirmed*; a payment is *settled*. Forcing every capability through one
pipeline would produce numbers that mean different things.

## 5. Measurement Framework

AgentMeasure defines **metric families**, not a universal KPI.

**M1 Distribution — Reach.** Is the capability in the agent world?
`Available Clients · Eligible Opportunities · Presentations · Presentation Rate ·
Distribution Coverage`

**M2 Choice — the most agent-native family.** When the agent had the chance, did it
choose the capability?
`Selections · Observed Selection Rate (Observed Selected ÷ Presented) · Conditional
Choice Share · First-choice Rate`

**M3 Execution — Use.** Was it usable after selection? The Draft 0.4 model counts
operations and attempts separately — the distinction that metering will eventually
need:

```text
Operations · Attempts · Attempts per Operation
Operation Completion Rate · Operation Success Rate
Attempt Failure Rate · Retry Rate · Latency
```

**M4 Utility — effective use.** Did the capability deliver usable information or
cause the intended effect?

```text
Result Utility      Delivered · Consumed · Accepted
Effect Utility      Applied · Confirmed · Reversed / Failed
```

**M5 Outcome — Value.** Did it improve the task?
`Task Success Association · Incremental Lift · Time Saved · Cost Saved`

**Relationships** (formerly a separate chapter, now a subsection): Trial → Active →
Repeated → Preferred → Dependent. Dependency — the least replaceable — remains the
long-term asset signal.

## 6. Measurement Quality & Claim Discipline

Evidence quality is not coverage quality; both are not qualification quality; none
is methodology. A set of perfectly attested events covering 2% of agents is not
market data.

```text
Measurement Quality
├── Provenance / Evidence Strength   where did this observation come from, and how
│                                    strongly is its origin supported?
├── Coverage                         how much of the world did we see?
├── Qualification                    does this count as real production use?
├── Sampling                         sampled? with what uncertainty?
├── Identity                         how well do identifiers resolve to entities?
└── Method/version                   which statistics, which spec version?
```

**Qualified usage.** Every observation carries two axes — Usage Context (where the
traffic came from) and Validity (whether the observation is genuine). **Strict
Qualified Usage** = `production` + `validity=normal`: the default for public metrics.
Unknown context/validity is disclosed separately, never silently included — no
"report unknown → make the leaderboard" incentive. A retry is an additional attempt
of the same operation, kept as a reliability signal, not as a distinct logical use.

**Claim discipline.** Every published metric carries a Measurement Label: numerator,
denominator, observable population, qualified population, runtime coverage, grain,
choice mode, decision authority, selection constraint. Observed choice is never
presented as preference; association is never presented as causation; unobservable is
never interpreted as negative.

## 7. Measurement and Metering

The bridge from measurement standard to CaaS is semantic: **measurement unit ≠
billable unit**.

| Capability | Measurement | Billable |
| --- | --- | --- |
| Search | Operation | Successful Search |
| Data | Query | 1,000 Records |
| Compute | Job | GPU-second |
| Action | Operation | Confirmed Effect |
| Booking | Transaction | Successful Booking |
| Lead Generation | Task | Qualified Lead |
| Commerce | Transaction | % of Transaction |

Metering semantics therefore define, per Offering:

```text
Billable Event       which measured fact triggers a charge
Billable Unit        the unit of quantity (operation, record, GPU-second, effect…)
Billable Quantity    how the unit is counted (per policy: attempts, confirmations…)
Pricing Model        per-operation · per-quantity · per-effect · per-outcome · revenue share
Metering Policy      how measurement facts map to billable facts (rules, exclusions)
Commercial Attribution  which parties contributed to discovery / selection / revenue
```

**Payment is out of scope.** AgentMeasure does not define payment rails, wallets,
settlement currencies, merchant-of-record relationships, or financial custody. It
produces the facts — qualified operation, confirmed effect, qualified outcome,
billable quantity, commercial attribution — that payment systems consume.

> **AgentMeasure standardizes economic facts, not money movement.**

## 8. Attribution and Incrementality

**A capability's participation in a successful task is not evidence that it caused
the success.**

- **Attribution measurement** is observational: which capabilities participated in
  the task chain. It supports claims of *association* and *contribution to the
  execution chain* — nothing more.
- **Incrementality measurement** is counterfactual: how much additional value did the
  capability create? The method is randomized comparison — treatment (capability
  available) vs control (capability invisible) — across task success, time, cost,
  and quality.

Commercial attribution extends the observational side along the distribution chain:

```text
GitHub Skill → Registry → Agent Recommendation → Capability → Payment
```

Who contributed to discovery, selection and revenue? This is the future basis for
agent affiliate and revenue-sharing models — and it must never be conflated with
causal incrementality.

## 9. Capability Trust and Comparability

A capability consumer (agent, marketplace, or human) compares signals, not brands:

```text
Capability Signals
Reliability · Latency · Price · Freshness · Consumption · Effect Success
Outcome · Safety · Measurement Coverage
```

AgentMeasure **does not calculate a universal AgentMeasure Score**. Agent A cares
about price, Agent B about latency, Agent C about privacy. Ranking is a product
decision for agents and marketplaces; the standard defines only comparable signals
and the labels that make them comparable. The Measurement Label is the foundation of
this comparability.

## 10. Observation & Deployment Architecture

Measurement surfaces differ in what they can see; single-sided adoption has value,
but the claim must match the surface:

```text
Distribution Side → Agent Runtime Side → Provider Side → Effect / Outcome Side
```

| Surface | Can see |
| --- | --- |
| Registry | discovery / availability |
| Agent runtime | presentation / choice / consumption |
| Capability provider | operation / attempts / result |
| Target system | effect / transaction |
| Experiment layer | incrementality |

Two-sided observations (agent runtime + provider) enable corroboration (E2); the
provider side alone is sufficient for provider-scoped usage metrics. The standard is
not on the critical request path: observations are emitted asynchronously, metadata
only, pseudonymized before persistence.

## 11. Interoperability

The standard is transport-neutral and vendor-neutral. Current infrastructure binds
to it as implementation examples, not as preconditions: MCP carries lifecycle events
and trace context; OpenTelemetry carries tool spans; Codex, Claude Code, and DeepSeek
Harness expose observation points with declared capability matrices; registries
provide entity identity. Payment rails, when they arrive, consume the standard's
facts rather than extending its core.

## 12. Non-goals and Governance

AgentMeasure is **not** a payment protocol, a marketplace, a wallet, or a universal
reputation system. The standard does not:

- move money or custody funds;
- rank capabilities or score providers;
- define what a "good" capability is;
- require any central server, agent-side install, or open-source provider.

The standard itself is community-governed (AUP process, `proposals/`); commercial
products built on it must not control the standard's definitions.

## 13. Open Questions

1. **Task boundaries.** What is the unit of a "task," and who defines it?
2. **Effect verification.** How to confirm an effect (booking confirmed, payment
   settled) without deep integration into every target system?
3. **Incrementality at scale.** How to run counterfactual experiments across the
   ecosystem without disturbing production?
4. **Candidate-set observability.** Presentation is the key denominator; most
   runtimes do not expose it yet.
5. **Cross-agent identity.** Same client across Codex, Claude, and DSH — when is
   that knowable?
6. **Billable-unit consensus.** Which measurement facts will providers and payment
   rails actually agree on, and at what cost of mis-measurement?
7. **Privacy.** How far can correlation and retention go under pseudonymity?

## 14. Conclusion

The software consumer is changing from humans to agents, and the economic unit is
shifting from seats to callable capabilities. Before capabilities can be priced,
billed and compared, the ecosystem needs a shared measurement language — what a
selection is, what an operation is, what a delivery, a consumption, an effect and an
outcome are, and which numbers can support which conclusions.

AgentMeasure is that proposal: measurement semantics as infrastructure, commercial
semantics as a future extension, payment as someone else's rails. **Measure how
agents use software capabilities today; make capabilities comparable and meterable
next; build the measurement foundation for Capability as a Service in the long
term.**

## References

1. RFC 2119 / BCP 14 — *Key words for use in RFCs to Indicate Requirement Levels*.
2. OpenTelemetry GenAI semantic conventions — `gen_ai.*` tool-call telemetry fields.
3. Model Context Protocol (MCP) specification — tool discovery and invocation surfaces.
4. MCP Registry — server identity as the entry point for entity resolution.
5. EDPB — guidance on pseudonymisation (pseudonymised data may still be personal data).
6. AgentMeasure specification — Core, Metrics, Data, Entity, Quality, Correlation
   (`standard/`); Commercial Extension (`extensions/COMMERCIAL.md`, experimental);
   machine-readable registry (`schemas/`, `registry/`); reference implementation and
   conformance vectors in the same repository.

---

*The normative specification (Measurement Objects, Lifecycle, Metric Families,
Quality, Reporting) and the reference implementation (AgentMeasure) are published
openly. Graduation to AgentMeasure 1.0 requires two independent implementations, three
runtime profiles, two tool-side implementations, a public conformance suite with
canonical test vectors, 5–10 real projects, a published discrepancy report, and
security and privacy reviews.*
