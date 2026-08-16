# AUAS: An Open Protocol for Measuring Software Usage by AI Agents

**Agent Usage Attribution Standard — Draft 0.1**

> Roy Tong
> agent-used is the reference implementation of this standard.

## Abstract

Agents are becoming a principal distribution channel for software, yet tool authors
cannot observe how their software is used by agents: download counts show humans,
registry installs are self-reported, and platforms publish no adoption data. This
paper defines AUAS, an open protocol for producing *verifiable, privacy-preserving,
and comparable* measurements of software usage by AI agents.

The protocol's core mechanism is the **Usage Receipt**: a minimal, signed declaration
produced by an observer at a runtime boundary. Receipts never contain user content;
cross-party corroboration is achieved through a one-way **correlation commitment**
over attribution identifiers, so that independent runtimes can establish that they
observed the same invocation without exchanging raw data. Invocations are
reconstructed from receipts by deterministic rules, qualified by an explicit
evidence profile, and aggregated only under a declared **Measurement Policy**.

AUAS does not define who owns the truth. It defines what evidence, under what rules,
can support what conclusions.

## 1. Problem

Software distribution once had readable signals: downloads, stars, issues. In 2026
these signals no longer describe how software is used. A growing share of usage is
mediated by agents — Claude Code, Codex, DeepSeek Harness, and others — which select
tools, install skills, and call servers on behalf of users. Each existing signal
fails for a different reason:

- **Downloads and stars** measure humans, not agents.
- **Self-reported install counts** can be inflated by the author and are not
  independently verifiable.
- **Registries** publish discovery metadata but explicitly disclaim adoption data.
- **llms.txt declarations** are not requests; audits show the vast majority of
  declared files receive no AI traffic at all.

The consequence is that tool authors make maintenance, investment, and positioning
decisions about their software with no measurement of its actual use by agents. The
agent economy is being played without a scoreboard — and no party can build one
alone, because no single platform observes the whole ecosystem and no author can be
trusted to report their own numbers.

## 2. Goals and Non-goals

**Goals.** AUAS aims to enable:

1. **Verifiability** — usage claims can be traced to signed evidence produced at
   runtime boundaries, not to author self-reports.
2. **Comparability** — numbers produced by different parties are comparable because
   they are computed under the same protocol and the same declared policy.
3. **Privacy** — measurement is possible without collecting prompts, arguments,
   results, paths, or identities; raw telemetry stays local.
4. **Independence** — no single platform, author, or aggregator is trusted as the
   source of truth.

**Non-goals.**

1. We do **not** define a global source of truth or a single official database.
2. We do **not** rank tools by raw call counts.
3. We do **not** collect content under any circumstance.
4. We do **not** incentivize agents to star, follow, or otherwise inflate metrics.
5. We do **not** replace OpenTelemetry or MCP; AUAS sits above them as a semantic
   layer (Section 11).

## 3. System Model

| Actor | Responsibility | Trust assumption |
| --- | --- | --- |
| Agent Runtime | executes agents, initiates calls | untrusted (may be gamed) |
| Tool Runtime | executes tools, serves calls | untrusted (may self-report) |
| Observer | produces signed receipts at a runtime boundary | identity via public key |
| Verifier | checks signatures and receipt validity | honest execution of rules |
| Correlator | deterministically merges receipts into invocations | honest matching rules |
| Attestor | platform-level attestation (future) | trusted platform |
| Aggregator | aggregates under a policy | sees receipts/aggregates only |
| Registry | project and observer identity claims | authenticates claims |

**Trust minimization.** No single actor can fabricate "independently corroborated
usage": corroboration requires receipts from at least two *independently controlled*
observers (Section 7). The protocol is designed so that every claim carries its own
evidence; nothing is accepted on the say-so of the claimant.

## 4. Usage Model

**Install ≠ Usage.** Usage is a chain of stages, and observable facts are strictly
separated from inferred values — if a stage cannot be observed, it is `unknown`, never
assumed.

| Stage | Definition | Observable | Inference |
| --- | --- | --- | --- |
| D0 Available | tool enters an agent-visible set | fact | — |
| D1 Discovered | runtime loads the tool's definition | fact | — |
| S0 Selected | model/runtime emits a tool call | fact | — |
| S1 Executed | runtime begins execution | fact | — |
| S2 Completed | returns success/failure/denied | fact | — |
| S3 Delivered | result enters agent context | fact | — |
| S4 Consumed | a later model request uses the result | fact on some platforms | — |
| S5 Contribution | result influences the final task outcome | — | **inference (research)** |

Discovery is not selection; delivery is not consumption; consumption is not
contribution. A tool that is called but whose results are never consumed is
indistinguishable, at the measurement layer, from one that was never useful.

## 5. Usage Receipt Protocol

The unit that flows between parties is the **Usage Receipt**: a minimal, signed,
privacy-safe declaration by one observer about one agent–tool interaction.

```
UsageReceipt {
  spec_version, receipt_id, observed_at,
  observer_principal, observer_side, provenance, trust_domain,
  project_id, tool, tool_call_id?, trace_id?,
  session_key,            // pseudonymized in memory; never raw
  outcome, lifecycle_stage,
  correlation_commitment, // H(protocol ‖ project ‖ trace ‖ call_id)
  sampling?,              // if sampled
  signature, key_id       // Ed25519 over canonical(SIGNED_FIELDS)
}
```

Receipts **must not** contain prompts, inputs, outputs, paths, conversations, or
user identity.

**Canonical serialization.** Signature bytes must be identical across
implementations: canonical JSON (sorted keys, no whitespace, NFC-normalized strings)
over a fixed set of SIGNED_FIELDS — every field that affects attribution,
correlation, or qualification. Unsigned fields must not affect authenticated claims.

**Correlation commitment.** Two runtimes that observed the same invocation compute
the same commitment `H(protocol_version ‖ project_id ‖ trace_id ‖ tool_call_id)`
without exchanging any raw data. A verifier can therefore establish that a client
receipt and a server receipt refer to the same call, while learning nothing about
its content. Receipts from the same side never corroborate each other.

## 6. Invocation Reconstruction

Receipts are merged into **invocations** by deterministic rules, in priority order:

1. **Exact match** — identical `tool_call_id` (same project and tool).
2. **Structural match** — trace parent–child or span relations.
3. **Commitment match** — equal correlation commitments across sides.
4. Deterministic one-to-one assignment within a key.
5. **Ambiguous — do not corroborate.** Failure to match under 1–3 leaves
   observations independent; ambiguity fails closed.

Outcome conflicts are preserved: a client `success` with a server `failure` yields
`derived_outcome = inconsistent` rather than being flattened. Disagreement between
observation surfaces is measurement data, not noise.

**Standard invariants.** Any AUAS implementation must satisfy:

1. Same input + same policy → same result.
2. One invocation is counted at most once.
3. Duplicate observations never increase invocation counts.
4. Evidence is never self-declared.
5. Unsigned fields never affect authenticated claims.
6. Ambiguous observations are never promoted to corroborated.
7. `unknown` is never inferred as `success`.
8. Metrics always declare scope + policy + window.
9. Public receipts never contain user content.
10. Corroboration never assumes that different strings mean independent control.
11. Platform attestation is UNSUPPORTED until actually verified.
12. Outcome conflicts are preserved, never flattened.

## 7. Trust and Evidence

Evidence is **derived, never self-declared**. Adapters report facts; the verifier
computes an **evidence profile** over multiple axes, because authentication,
corroboration, independence, and attestation are not one scale:

| Axis | Values |
| --- | --- |
| Authentication | A0 none · A1 signed (Ed25519) · A2 identity-verified |
| Corroboration | C0 single · C1 multiple observers |
| Independence | I0 unknown · I1 distinct runtime · I2 distinct trust domain |
| Attestation | T0 none · T1 platform-attested (UNSUPPORTED until verified) |
| Match | M0 none · M1 heuristic · M2 exact call-id · M3 trace-verified |

Display classes are derived from the profile: *Observed → Authenticated →
Corroborated → Independently Corroborated → Platform Attested*. Independence is the
critical axis: two observer principals under the same trust domain are not
independent, no matter how different their strings are.

Signatures use Ed25519 — asymmetric, so verification keys can be public. A signature
proves origin and integrity, never that real usage occurred; signatures are evidence
of who said it, not of the truth of what was said.

## 8. Measurement

Metrics are computed from invocations, not from observations. Counting observations
would double-count every corroborated call.

The primary adoption metric is **ACD — Active Client-Days**: a project–day pair
with at least one eligible invocation by a pseudonymous client. ACD is robust to
retries, session-lifecycle differences across runtimes, and tool API granularity.
Supporting metrics: active clients, attributed invocations, corroborated share,
execution success rate, and result-consumed rate (S4), where observable.

**Measurement Policy.** Every published metric must be qualified by a policy:

```
ACD(project=X, window=30d, qualification=AUAS/Core-1)
```

The policy declares eligible evidence, correlation rules, coverage scope, sampling
treatment, dedup rules, window, and privacy thresholds. Two dashboards displaying
"12,000" under different policies are not comparable; the policy is part of the
number.

## 9. Privacy and Security

**Raw telemetry stays local; public infrastructure receives aggregates by default.**
Cross-party corroboration exchanges signed receipts and commitments only.
Pseudonymous session keys rotate monthly (HMAC over an epoch secret); a stable local
key never leaves the device, and retention is computed locally as cohort aggregates
so that unlinkability and cross-period retention do not conflict.

**Fail-closed rules:** verification failure invalidates; unparseable timestamps do
not correlate; ambiguous matches do not corroborate; unverified attestation is
unsupported; receipts without identifiers are rejected.

**Adversarial model.** Authors can self-sign arbitrary receipts (E1 does not defend
against this; corroboration requires independent domains). Two colluding parties
under one controller cannot be fully defended without platform attestation; anomaly
detection and cross-checks with independent signals mitigate. Aggregators are
constrained by public rules and test vectors; future public auditability may use
signed aggregate statements with Merkle commitments in an append-only transparency
log — deliberately without any blockchain or token.

## 10. Limitations

1. **Collusion.** E2-level corroboration cannot be defended against two parties
   under the same controller. Only platform attestation (T1) is strong against it.
2. **Coverage.** Real data is not representative data. Metrics must declare their
   scope; partial coverage cannot support ecosystem-wide inference.
3. **Sampling.** Sampled telemetry requires declared probabilities and uncertainty;
   unsampled-only is the conservative default.
4. **S5 causal attribution.** Whether a tool result *contributed* to a task outcome
   is causal inference, not observation; it is a research direction, not a metric.
5. **S4 consumption** is observable only on platforms that expose it.
6. **Identity graph** resolution across repos, packages, registries, and tools is
   approximate until claims are verified.

## 11. Interoperability

AUAS is transport-neutral and vendor-neutral. Existing infrastructure binds to it:

- **MCP** is a transport binding: `tools/call` carries lifecycle events, `_meta`
  trace context carries structural correlation, `clientInfo` carries observer hints.
- **OpenTelemetry** is a telemetry binding: tool spans carry semantic fields; AUAS
  adds only six `agentused.*` extension attributes; evidence is a derived property
  of invocation records, never of instrumentation spans.
- **Agent runtimes** (Codex, Claude Code, DeepSeek Harness, others) are profiles
  with declared capability matrices; the core protocol does not depend on any of
  them.

Bindings are replaceable; the receipt and its commitment are the only non-negotiable
interface.

## 12. Conclusion

AUAS establishes a public capability that no single actor can provide alone: the
ability to measure, verify, and compare agent usage of software without trusting any
author's self-report, any single platform, or any central database — and without
collecting user content.

The protocol's contribution is not a dashboard or a badge. It is a definitional
layer: **what evidence, under what rules, can support what conclusions about agent
usage of software.** Two independent implementations that produce the same numbers
from the same receipts under the same policy are the test of the standard; the first
such implementation, agent-used, is published alongside this paper.

---

*References and the full normative specification (AUAS-CORE, DATA, TRUST, CORR,
METRICS, COVERAGE, PRIVACY, SECURITY, BIND, PROFILE) live in the agent-used
repository. Graduation criteria to AUAS 1.0: two independent implementations, three
agent-runtime profiles, two tool-side implementations, a public conformance suite
with canonical test vectors, 5–10 real projects, a published discrepancy report, and
security and privacy reviews.*
