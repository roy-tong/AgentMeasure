# Measuring Software Used by AI Agents

**A Measurement Foundation for Capability as a Service and the Agent Capability Economy**

*Whitepaper v0.3 · AgentMeasure Standard Draft 0.4.4*

> Roy Tong
> The reference implementation and the open experiment engine
> ([`lab/`](../lab/README.md)) live in the AgentMeasure repository.

## 0. Abstract

AI agents increasingly select, invoke, and transact with software on behalf of
users and organizations. As interfaces such as Skills, MCP servers, APIs and CLIs
become easier to create and distribute, economic value increasingly shifts toward
the scarce capabilities behind them: proprietary data, compute, execution,
permissions, transactions and real-world fulfillment.

This creates a measurement problem before it creates a payment problem. A capability
cannot be reliably priced, compared, billed or optimized until the ecosystem agrees
on what constitutes a selection, an operation, a successful delivery, a consumed
result, an outcome and a billable unit. And once money moves on those numbers, a
second problem appears: **telling real growth from fake growth** — retry inflation,
unconsumed results, circular transactions — before anyone budgets on them.

AgentMeasure proposes an open measurement standard for this emerging capability
economy: a common data language — reach, choice, use, utility, value — the
measurement semantics that metering, marketplaces and payment rails can later build
on, and the experiment semantics (preregistration, guardrails, per-condition effect
sizes) that turn measurement from passive observation into testable claims. The goal
is not a dashboard. It is the measurement foundation that makes Capability as a
Service (CaaS, as used in this paper) possible — and trustworthy.

## 0.2 Relationship to Observability

> **AgentMeasure assumes that telemetry may already exist. Its purpose is not to replace
> tracing, logging, or evaluation systems, but to define portable measurement objects and
> rules over their evidence.**

Different systems can observe the same agent behavior and report different usage
numbers:

```text
1 logical operation, 2 retries

System A: usage = 3
System B: usage = 1

Both telemetry systems are correct.
Their measurement semantics are not the same.
```

AgentMeasure does not re-collect observability data; it defines cross-system
comparable measurement objects, statistical units and derivation rules over existing
evidence (OTel / Langfuse / Logfire / Phoenix / runtime logs):

```text
Evidence → Measurement Semantics → Accounting → Settlement
```

## 0.5 Measurement Principles

> This section is the document's **inviolable data invariants** (Draft 0.4.4). The five
> below were shaped by repeated external engineering feedback (attempt ledger / cache
> attribution / reasoning-token subset / decision provenance / agent-assigned value).

**1. Facts survive interpretation.**
Base facts (attempts, consumption, evaluation evidence) stay immutable; semantics,
rollups, valuation, metering and decisions are built on top of facts — they never
overwrite them.

**2. Grain answers the question.**
Attempts answer consumption; Operations answer logical use; Tasks answer outcomes.
Different questions must not silently share a statistical unit
(10 attempts ≠ 10 operations ≠ 10 decisions).

**3. Uncertainty is data.**
```text
Unknown ≠ Zero
Unobservable ≠ False
Unresolved ≠ Operation
```

**4. Derived facts carry provenance.**
Every inferred operation / attribution / value claim must carry the evidence, rule
and version that produced it (rule_id / rule_version / source_attempt_ids).

**5. Settlement is not value.**
```text
Payment ≠ Utility
Reward ≠ Value
Settlement ≠ Incremental Value
Assigned ≠ Settled ≠ Realized ≠ Incremental
```

In one line: **Preserve facts. Derive semantics. Expose uncertainty.**

## 1. From SaaS to Capability Economy

Software distribution once had a readable chain: downloaded, installed, used. Each
era has had its own economic unit. The shift described below is **additive, not
replacement**: alongside seat-based SaaS and request-based APIs, callable
capabilities are emerging as a new economic unit for agent-mediated software
consumption.

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

### Thesis and assumptions

AgentMeasure is built on three trend judgments that are **not yet fully established**:

1. Agents will mediate a growing share of software selection and execution.
2. More software capabilities will be exposed independently of their human UI.
3. Usage-, effect-, and outcome-based commercial models will coexist with seat-based
   pricing.

The measurement standard remains useful even if these trends progress unevenly:
the objects, quality rules and claim discipline stand on their own as an agent
software measurement standard.

## 1.5 Harness-native Software and the Measurement Problem

A further shift is making the measurement problem harder, and more valuable:
agent harnesses are emerging as a reusable software runtime. DeepSeek Harness
treats models, tools, skills, sessions, sandboxes, storage, loops, scheduling
and UI as plugins composed at runtime; Codex exposes one harness through an App
Server to CLI, IDE, Web and desktop clients. One harness can already delegate
to another agent runtime as a subagent provider.

Three consequences follow:

**1. Software is becoming composable.** Harnesses compose model, skill, agent,
capability, data and execution at runtime, per task. The durable economic unit
is increasingly the capability that survives the task, not the packaged
application that produced it.

**2. Telemetry becomes fragmented.** Each harness has its own vocabulary — run,
turn, span, tool call, subagent, request — and its own blind spots (which
candidate capabilities were presented; whether a result was actually consumed).
The same behavior is described by different objects and units in different
harnesses, and agent-to-agent delegation crosses harness boundaries where no
single observer sees the whole task.

**3. Measurement must sit above them.** The more composable software becomes,
the more important portable measurement semantics become. This is why
AgentMeasure defines semantics (Operation, Attempt, Delegation, evidence
grades) over existing telemetry rather than another telemetry format, and why
harness profiles — a public record of what each runtime can and cannot observe
— are part of the standard itself.

We state this conservatively: as agent harnesses absorb more orchestration and
interaction logic, the economic unit of software may increasingly shift from
packaged applications toward independently callable capabilities. Whether, and
how far, this shift proceeds is an empirical question. The measurement standard
does not depend on the extreme outcome; it becomes *more* necessary with every
step toward it.

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

### Emerging evidence: commerce is arriving before measurement

The premise is not hypothetical — distribution and payment infrastructure for
agent-mediated commerce already exists:

- The MCP ecosystem has passed **10,000 published servers** (Linux Foundation / AAIF),
  and the A2A protocol is in production use across **150+ organizations**.
- **Cloudflare Agents SDK** allows MCP tools to be priced per call and charged via
  x402 ([Charge for MCP tools](https://developers.cloudflare.com/agents/agentic-payments/x402/charge-for-mcp-tools/));
  **Coinbase x402 Bazaar** is a discovery layer where agents search services with
  price and schema and complete paid calls over MCP
  ([x402 Bazaar](https://docs.cdp.coinbase.com/x402/bazaar)).
- **AWS Bedrock AgentCore Payments** reached general availability (2026-08) and
  **Google AP2** outlines an agent-payments protocol stack — payment rails are no
  longer the bottleneck.
- **OpenAI and Stripe's Agentic Commerce Protocol (ACP)** is being used in real
  agentic commerce flows ([announcement coverage](https://www.digitaltransactions.net/openai-and-stripe-are-the-latest-fintechs-to-enable-agentic-commerce/)).

### Evidence that measurement must be trustworthy: fake growth is already here

Payment infrastructure arriving *before* measurement has a predictable side effect:
metrics that can be gamed will be gamed. Recent on-chain analyses of x402-style
payment flows report that a substantial share of headline transaction volume appears
to be internal loops or manufactured transactions rather than genuine demand. We read
that not as a reason to dismiss machine payments, but as the clearest possible signal
for the thesis of this paper: **machine-consumed commerce needs machine-verifiable
measurement**, or every downstream decision — pricing, ranking, budgeting, revenue
share — inherits fabricated inputs.

This is why "qualified usage" (§6) is not a refinement bolted on top of the standard;
in an economy where both traffic and transactions can be manufactured, the
qualification axis (is this real production use?) and the consumption axis (was the
result actually used?) are the difference between a channel and a slot machine.

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

> **Capability is the primary functional and measurement object. An Offering is the
> commercial packaging of one or more capabilities** — defined in the Commercial
> Extension (experimental), never inserted into the core measurement lineage.

| Object | Definition | Layer |
| --- | --- | --- |
| Software Entity | the software being measured: tool, skill, API, data source, agent, application, runtime capability | Market |
| Capability | a named function of an entity — the primary functional and measurement object | Market |
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
| Observation | an evidence record of a measurement fact (authentication and signatures are optional, defined by verification profiles) | Evidence |

Observation happens on **Interaction Surfaces**; attribution resolves to **Software
Entities** through a machine-readable registry — never guessed at observation time.

Pricing is deliberately **not** an object of the core model. An `Offering` —
commercial packaging referencing one or more capabilities, with permitted surfaces,
pricing policy, service level objectives and commercial constraints — is defined in
the Commercial Extension (experimental, non-normative), so that measurement
semantics can evolve without being coupled to any payment design.

### Distribution events

With commercial attribution in scope, discovery regains business meaning — without
becoming the choice denominator:

```text
Published → Listed → Retrieved / Discovered → Presented
```

`Presented` remains the denominator of choice metrics; `Discovered` is a
distribution-attribution event, answering *which Skill / Registry / Marketplace
brought capability usage*.

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

AgentMeasure defines **metric families**, not a universal KPI. Metric status is
marked explicitly — **Defined** (formal metric contract), **Draft**, **Research** —
a concept paper does not pretend the standard is fully defined.

**M1 Adoption & Relationship.** (Active Clients is an adoption metric, not Reach;
Reach is expressed by M2 Presented / Eligibility.)
`Active Clients (Defined) · Repeat Clients (Draft) · Active Client-Days (Defined)`

**M2 Choice — the most agent-native family.** When the agent had the chance, did it
choose the capability?
`Observed Selection Rate (Defined) · Observed Head-to-Head Choice Share (Defined) ·
First-choice Rate (Proposed)`

**M3 Execution — Use.** Was it usable after selection? Draft 0.4 counts operations
and attempts separately — the distinction that metering will eventually need:

```text
Operation Count (Defined) · Attempt Completion (Defined) · Attempt Success (Defined)
Operation Success Rate (Defined) · Operation Resolution Coverage (Defined)
Attempts per Operation (Defined)
```

**M4 Utility — effective use.** Did the capability deliver usable information or
cause the intended effect?

```text
Result Consumption (Defined) · Effect Confirmation (Draft 0.5)
```

**M5 Outcome — Value.** Did it improve the task?
`Task Success Association (Draft) · Incremental Lift (Research / Draft 0.5) ·
Time Saved (Research) · Cost Saved (Research)`

**Relationships**: Trial → Active → Repeated → Preferred → Dependent. Dependency —
the least replaceable — remains the long-term asset signal.

In the experiment engine (`lab/`), these families reduce to an operational funnel —
**Reach → Choice → Success → Consumption** — where every stage is a countable event
and every rate carries its denominator. The families are the vocabulary; the funnel
is how the vocabulary is exercised under controlled conditions (§8).

## 6. Measurement Quality & Claim Discipline

Evidence quality is not coverage quality; both are not qualification quality; none
is methodology. A set of perfectly attested events covering 2% of agents is not
market data.

```text
Measurement Quality
├── Provenance Strength             where did this observation come from, and how
│                                    strongly is its origin supported?
├── Coverage                         how much of the world did we see?
├── Qualification                    does this count as real production use?
├── Sampling                         sampled? with what uncertainty?
├── Identity Resolution              how well do identifiers resolve to entities?
└── Method & Version                 which statistics, which spec version?

Quality is assessed per **Measurement Use Profile** (first_party_analytics /
comparative / cross_side_attribution / billable_audit) — the same data may be
fit for internal trends but not for billing (see QUALITY §4).
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
never interpreted as negative. **Selection-rate growth is never presented as margin
growth until the consumption and qualification axes verify it** — the anti-fake-growth
rule that runs from this section through the experiment reports of §8.

## 7. Measurement and Metering

The bridge from measurement standard to CaaS is semantic: **measurement unit ≠
billable unit**, and the three metering concepts must stay separated — **Event** is
why billing triggers, **Unit** is what is counted, **Quantity** is how many:

| Capability | billable_event | billable_unit | billable_quantity |
| --- | --- | --- | --- |
| Search | `operation_succeeded` | operation | 1 |
| Data | `result_delivered` | record | 1,382 |
| Compute | `compute_completed` | gpu_second | 47.2 |
| Action | `effect_confirmed` | operation | 1 |
| Booking | `effect_confirmed` | booking | 1 |
| Lead Generation | `outcome_qualified` | qualified_lead | 5 |
| Commerce | `transaction_settled` | transaction | 0.03 (revenue share) |

Metering semantics therefore define, per Offering:

```text
Billable Event       which measured fact triggers a charge
Billable Unit        the unit of quantity (operation, record, GPU-second, effect…)
Billable Quantity    how the unit is counted (per policy: attempts, confirmations…)
Pricing Model        per-operation · per-quantity · per-effect · per-outcome · revenue share
Pricing Policy       versioned price rules (flat, volume tiers, enterprise agreement, surge…)
Quote                the terms actually applicable to one call (quote_id, policy version, unit price)
Metering Policy      how measurement facts map to billable facts (rules, exclusions), versioned
Metering Ledger      replayable, correctable record of metered facts (revision / supersedes / reversal)
Commercial Attribution  which parties contributed to discovery / selection / revenue
```

**Payment is out of scope.** AgentMeasure does not define payment rails, wallets,
settlement currencies, merchant-of-record relationships, or financial custody. It
produces the facts — qualified operation, confirmed effect, qualified outcome,
billable quantity, commercial attribution — that payment systems consume.

> **AgentMeasure standardizes economic facts, not money movement.**

### 7.5 From measurement to margin: the value formula

For a capability provider, the measured quantities compose into one economic
statement — the value formula the reference implementation ships in its report
generator:

```text
incremental margin / month
  = opportunities × Δ selection rate
    × P(operation succeeds | selected)        ← measured (M3)
    × P(result consumed | succeeded)          ← measured (M4)
    × pay conversion
    × margin per billed event
    − serving cost
```

Every measured factor on the right-hand side is a labeled metric, not an
assumption; every business factor must be supplied and labeled by the party making
the claim. Two disciplines apply. First, **no unverified uplift enters the
formula**: a selection-rate gain that loses consumption (§2) or breaches a
guardrail (§8.2) is excluded or recomputed at the measured (lower) factors. Second,
**the formula is honest about its own economics**: at low margin per billed event
(search-class capabilities at fractions of a cent), even large relative uplifts
produce absolute margins that cannot fund measurement or experimentation — which is
a fact about the business, not a reason to distort the numbers.

## 8. Attribution, Incrementality — and Experimentation

**A capability's participation in a successful task is not evidence that it caused
the success.** And a capability's observed selection rate is not a fixed property of
the capability — it is a property of the *system* (descriptions, schemas,
candidate-set composition, harness, model), most of whose knobs the provider can
change. Both facts push measurement from observation toward experiment.

### 8.1 Attribution and the Value Evidence Ladder

- **Attribution measurement** is observational: which capabilities participated in
  the task chain. It supports claims of *association* and *contribution to the
  execution chain* — nothing more.
- **Incrementality measurement** is counterfactual: how much additional value did the
  capability create? Randomized comparison is the strongest evidence, but many
  capabilities cannot be randomly switched off. Claims therefore follow a **Value
  Evidence Ladder**:

```text
V0 Association             participated when the task succeeded
V1 Matched / Observational known confounders controlled
V2 Offline Ablation        replay tasks with the capability removed
V3 Quasi-experiment        switchback / natural variation
V4 Randomized Holdout      strongest causal evidence
```

Only the evidence actually produced may support the corresponding causal claim
strength — the same discipline as measurement quality.

### 8.2 The optimization surface is real — and it has teeth

Recent evidence establishes that agent choice responds to provider-controllable
variables, and that naive optimization can backfire:

- **Hasan et al. (arXiv 2602.14878)**: across 103 MCP servers and 856 tools, 97.1%
  of tool descriptions carry at least one quality issue; enriched descriptions
  raised task success by +5.85pp — while increasing execution steps by +67.46%, and
  with 16.67% of combinations *degrading* performance.
- **Microsoft BiasBusters (ICLR 2026)**: small description changes significantly
  shift agent tool selection, and providers benefit from systematic pretraining
  biases — choice is contestable, and biased.
- **Arcade ToolBench**: of 41,900+ indexed MCP servers (~219k tools), only 0.5%
  rate A or above and 76.6% rate F — metadata quality is poor at ecosystem scale,
  so the post-candidate-set optimization surface is enormous.

Read together: choice can be moved (the opportunity is real), effects have side
effects (steps, cost, consumption), and a nontrivial share of changes make things
*worse*. That is precisely the regime where **running controlled experiments is not
optional** — and where every experiment needs guardrails, because the headline
metric will happily improve while the capability gets worse.

### 8.3 The preregistered experiment loop

The reference experiment engine (`lab/` in this repository) operationalizes the
loop:

```text
Test        preregistered experiment: task set × harness matrix × factor variants
Recommend   effect sizes with confidence intervals + guardrail checks
Ship        gradual rollout through the provider's own release process
Verify      production re-measurement against a holdout
Learn       adopt / roll back / iterate — a recorded business decision
```

Its non-negotiable semantics, inherited from §0.5 and §6:

1. **Preregistration.** Hypothesis, primary metric, guardrails, sample size and
   analysis plan are hashed and locked before the run; the report draws confirmatory
   conclusions only from the locked plan; changing the plan means a new experiment.
   This is the line between an experiment engine and a conclusion generator.
2. **Honest nulls.** A non-significant result is reported as a null with its
   interval width — not mined for a flattering secondary metric. Insufficient
   sample yields "undetermined" plus the required n, never an underpowered verdict.
3. **Guardrails.** Effects are evaluated against preregistered thresholds (cost,
   steps/latency, consumption, retry rate); a significant win that breaches a
   guardrail is reported *effective, not qualified* — exactly the +5.85pp-with-
   +67.46%-steps pattern of §8.2.
4. **Anti-fake growth.** Selection uplift that loses consumption raises a warning
   and is excluded from margin claims (§7.5).
5. **Per-condition effects.** Effect sizes are reported per harness and per task
   distribution alongside any pooled number — never a single global coefficient,
   because the next section is about exactly the error that produces.

### 8.4 Offline-to-production transfer is a measurement problem

An experiment measures a *controlled* environment; production is not one. The gap
between the two is not noise to be averaged away — it is a first-class measured
quantity: the **transfer effect**, estimated per condition (harness × task
distribution), with its own confidence interval, reported honestly when it is
small, zero, or negative. A measured offline effect plus an honestly-reported
transfer gap is a decision-grade claim; an offline effect with an assumed "roughly
carries over" is a gamble wearing a lab coat. Production verification (gradual
rollout against a holdout, cross-side joined to the provider's billing data) is the
strongest form — V4 on the ladder — and it requires the data rights of §10.

### 8.5 Commercial attribution (observational, separate)

Commercial attribution extends the observational side along the distribution chain:

```text
GitHub Skill → Registry → Agent Recommendation → Capability → Payment
```

Who contributed to discovery, selection and revenue? This is the future basis for
agent affiliate and revenue-sharing models — and it must never be conflated with
causal incrementality.

## 9. Capability Trust and Comparability

A capability consumer's choice is shaped by many factors. Agents and marketplaces
can increasingly compare machine-readable performance signals **alongside** brand,
policy, price, user preference, and platform constraints — exactly the axes
AgentMeasure's Decision Authority / Selection Constraint model describes:

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

## 10. Observation Surfaces and Data Rights

Measurement surfaces differ in what they can see; single-sided adoption has value,
but the claim must match the surface — and in the agent channel, **who holds the
data decides the ceiling of every claim**, not what features exist:

```text
Distribution Side → Agent Runtime Side → Provider Side → Effect / Outcome Side
```

| Funnel stage | Data | Usually held by | Provider-side alone |
| --- | --- | --- | --- |
| Discovery | opportunities, candidate-set composition, presentation | Runtime / Registry / Agent app | ✗ |
| Choice | experiment arms, selection events | Harness / Agent app | ✗ |
| Execution | calls, outcomes, billing, cost | Provider | ✓ |
| Consumption | result usage, task results | Agent app / end user | usually ✗ |

This is an architectural fact, not a product gap to be engineered away. It yields
three claim tiers that sales language and contracts must respect:

| Data posture | What can honestly be claimed |
| --- | --- |
| **Provider-only** | controlled-environment performance + diagnosis of calls that already happened (dedup, success, cost, retry structure); no production selection-rate or incrementality claims |
| **+ Buyer-side / customer-owned agent apps** | full verified-lift loop: selection attribution, gradual-rollout re-test, incremental margin verification |
| **+ Runtime / Registry cooperation** | opportunity attribution, presentation optimization, full-funnel measurement |

Two-sided observations (agent runtime + provider) enable cross-side corroboration;
the provider side alone is sufficient for provider-scoped usage metrics. The
standard is not on the critical request path: observations are emitted
asynchronously, metadata only, pseudonymized before persistence.

## 11. Interoperability

The standard is transport-neutral and vendor-neutral. Current infrastructure binds
to it as implementation examples, not as preconditions: MCP carries lifecycle events
and trace context; OpenTelemetry carries tool spans; Codex, Claude Code, and DeepSeek
Harness expose observation points with declared capability matrices; registries
provide entity identity. Payment rails, when they arrive, consume the standard's
facts rather than extending its core. The experiment formats — preregistration
manifest, funnel events, report schema — are published as open JSON Schemas
(`lab/schemas/`) so third parties can implement runners and produce mutually
recognizable results, and the reference implementation ships a read-only MCP query
interface (`am mcp serve`) so agents and CI consume the same evidence engineers see —
with evidence grades, without rankings.

## 12. Non-goals and Governance

AgentMeasure is **not** a payment protocol, a marketplace, a wallet, or a universal
reputation system. The standard does not:

- move money or custody funds;
- rank capabilities or score providers;
- define what a "good" capability is;
- require any central server, agent-side install, or open-source provider.

The standard itself is community-governed (AUP process, `proposals/`); commercial
products built on it must not control the standard's definitions. The open substrate
(CLI engine, formats, runners, report renderer) stays open; commercial value may
only accrue on top of it — through proprietary data and delivery, never by
re-licensing or reclaiming what was open.

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
8. **Transfer heterogeneity.** When offline effects transfer unevenly across
   harnesses and task distributions, what is the minimal per-condition reporting
   standard that keeps pooled claims honest?
9. **Data rights.** Under what terms will runtimes and buyer-side applications
   authorize the choice-side observations that incrementality claims require —
   and what claims remain honest if they never do?

## 14. Conclusion

The software consumer is changing from humans to agents, and the economic unit is
shifting from seats to callable capabilities. Before capabilities can be priced,
billed and compared, the ecosystem needs a shared measurement language — what a
selection is, what an operation is, what a delivery, a consumption, an effect and an
outcome are, and which numbers can support which conclusions. And once money and
budgets move on those numbers, it equally needs the discipline that separates
verified value from manufactured growth: qualification, consumption evidence,
preregistered experiments, guardrails, honestly-reported transfer effects.

AgentMeasure is that proposal: measurement semantics as infrastructure, experiment
semantics as their proof procedure, commercial semantics as a future extension,
payment as someone else's rails. **Measure how agents use software capabilities
today; make capabilities comparable, meterable — and experimentally improvable —
next; build the measurement foundation for Capability as a Service in the long
term.**

## References

1. RFC 2119 / BCP 14 — *Key words for use in RFCs to Indicate Requirement Levels*.
2. OpenTelemetry GenAI semantic conventions — `gen_ai.*` tool-call telemetry fields.
3. Model Context Protocol (MCP) specification — tool discovery and invocation surfaces.
4. MCP Registry — server identity as the entry point for entity resolution.
5. EDPB — guidance on pseudonymisation (pseudonymised data may still be personal data).
6. Linux Foundation — [AAIF formation (MCP ecosystem, 10,000+ servers)](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) ·
   [A2A surpassing 150 organizations](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year).
7. Cloudflare — [Charge for MCP tools (x402 / Agentic Payments)](https://developers.cloudflare.com/agents/agentic-payments/x402/charge-for-mcp-tools/).
8. Coinbase — [x402 Bazaar: discover & pay over MCP](https://docs.cdp.coinbase.com/x402/bazaar).
9. AWS — [Bedrock AgentCore Payments GA (2026-08)](https://aws.amazon.com/about-aws/whats-new/2026/08/bedrock-agentcore-payments-ga/) ·
   Google — [A developer's guide to AI agent protocols (AP2)](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/).
10. OpenAI / Stripe — Agentic Commerce Protocol (ACP), announced September 2025; see [Digital Transactions coverage](https://www.digitaltransactions.net/openai-and-stripe-are-the-latest-fintechs-to-enable-agentic-commerce/).
11. Hasan et al. — *MCP Tool Descriptions Are Smelly* ([arXiv 2602.14878](https://arxiv.org/abs/2602.14878)): 97.1% of tool descriptions with quality issues; +5.85pp success with +67.46% steps; 16.67% of combinations degrade.
12. Microsoft Research — [BiasBusters: tool-selection bias in LLMs (ICLR 2026)](https://www.microsoft.com/en-us/research/publication/biasbusters-uncovering-and-mitigating-tool-selection-bias-in-large-language-models/).
13. Arcade — [ToolBench: MCP server quality benchmark (41,900+ servers; 0.5% grade A)](https://www.arcade.dev/blog/introducing-toolbench-quality-benchmark-mcp-servers/).
14. AgentMeasure specification — Core, Metrics, Data, Entity, Quality, Correlation
   (`standard/`); Commercial Extension (`extensions/COMMERCIAL.md`, experimental);
   machine-readable registry (`schemas/`, `registry/`); open experiment engine
   (`lab/` — preregistration, funnel capture, honest statistics, guardrails);
   reference implementation and conformance vectors in the same repository.

---

*The normative specification (Measurement Objects, Lifecycle, Metric Families,
Quality, Reporting), the open experiment engine (`lab/`), and the reference
implementation are published openly. Graduation to AgentMeasure 1.0 requires two
independent implementations, three runtime profiles, two tool-side implementations,
a public conformance suite with canonical test vectors, 5–10 real projects, a
published discrepancy report, and security and privacy reviews.*
