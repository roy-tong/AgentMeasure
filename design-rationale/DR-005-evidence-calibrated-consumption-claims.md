# DR-005 — Evidence-Calibrated Consumption Claims

- Status: Adopted as design rationale (Draft 0.4.4); tracked in #11
- Date: 2026-08-25 (revised same day — two-state + ranked-evidence reframing)
- External evidence: external reviewer Gunjan Jaswal (@gunjanjaswal) (OpenAI Agents SDK
  ecosystem — client-side taxonomy + estimator reframing + orchestration-determined influence,
  direct replies 2026-08-24/25 and 2026-09-14; named with consent, issue #11); external reviewer David Turner (@atomicdjt)
  (agent/runtime instrumentation — independent four-rung convergence + provider inference
  boundary, direct reply 2026-08-24; named with consent, 2026-09); external reviewer (hosted MCP provider —
  provider-side boundary, direct reply 2026-08-20); cross-validated from three
  observation points. Remaining attribution anonymous pending each reviewer's
  consent to public naming.

## Problem

What does "the agent consumed the tool result" mean, and what can telemetry prove?

A single trace can establish that a result was returned and entered the next model call's
context. It cannot establish that the result influenced the agent's next decision. Reviewers
converged on this from three independent observation points: the provider side cannot see
past `returned`; the client side cannot see past `available in context` without
counterfactual evidence; and even `available in context` splits into what the framework
serialized versus what reached provider inference. Collapsing these into one word —
"consumed" — overclaims causal knowledge from observational data.

## Decision

**There are exactly two semantic states. Everything between them is evidence, ranked by
strength.** (Reframing adopted from the client-side reviewer's second reply: the original
ladder wrongly treated `referenced` as a third state.)

```text
STATE 1 — Availability        (a fact about the context)
  Tool Invoked                ✅ observed
  Result Returned             ✅ observed
  Result Available to Agent   ✅ observed — certifiable from a single trace

STATE 2 — Influence           (a fact about the behavior)
  Result Influential          ✗ requires counterfactual evidence (ablation / rerun)

Evidence for State 2, ranked:
  ablation / rerun            strong (defining)
  result referenced in output weak estimator — two failure modes:
                                · cite-without-use  (restating ≠ depending on)
                                · use-without-cite  (silent use leaves no trace)
```

1. The trace layer certifies **availability** (State 1) and observes **reference** only as
   a weak estimator for influence — never as a state of its own.
2. **Influence (State 2) belongs to the experiment layer** (Lab: ablation / rerun), never
   to ordinary trace telemetry.
3. Normative claims MUST name the state they certify. `mcp_tool.name` present in the next
   request = availability signal, not consumption/influence.
4. Where the spec defines `referenced`, it MUST name both failure modes at the definition
   site, so reference cannot masquerade as causal.
5. **Orchestration-determined use: two evidence grades, not one** (client-side reviewer,
   third reply 2026-09-14, credited by name; refined 2026-09-18 by an external reviewer's
   distinction, attribution pending consent): when the orchestration layer, not the model,
   is involved, what the trace can prove splits into two grades:
   - **mandated use**: the call itself is forced or required by the harness. The behavior
     is the constraint, so the harness consummates the use and influence is provable by
     construction, ranked alongside ablation as strong evidence, certifier named (harness).
   - **dependency by construction**: programmatic piping of a tool's output into the next
     call, or a data dependency between tools (tool B's argument bound to tool A's output).
     The trace proves the value reached tool B, that is, propagation; it does not prove
     that B's behavior depended on it, since B can receive the value and ignore it. This
     grade certifies availability-plus-propagation and leaves the behavioral question to
     the experiment layer.
   This adds admissible evidence classes for State 2, it does not add a third state:
   model-side influence still requires the experiment layer (ablation / rerun).
   **Mixed case boundary** (open, per the same thread): when the harness constrains the
   choice set (tool B may only take A's output among several allowed inputs) and the model
   picks within it, the current reading is that the graph certifies availability of the
   constrained set while only an ablation certifies the selection, so the claim is split
   inside the evidence rank rather than becoming a third state.
6. **Inference boundary within availability** (agent/runtime instrumentation reviewer):
   client-side instrumentation
   proves what the framework serialized into the request — not what reached provider
   inference. Providers may truncate or transform context internally. Availability claims
   from client telemetry are therefore `serialized-as-sent`, one step short of
   `reached-inference`; the distinction is named rather than collapsed.
7. Profiles declare which state and which boundary they can observe (see PROFILES.md P2,
   scoped since db7fac4).

This also fixes the Core/Lab relationship: Core observes what telemetry can prove;
Lab estimates what only experiments can.

## Implications

- PROFILES.md P2: "Consumption signal" renamed to **Context Availability signal**, with
  explicit `available ≠ referenced ≠ counterfactually influential` boundary (#11).
- M4.1 rename decision tracked in #11 (candidate: Result Availability Rate); the metric
  family keeps reference observable only as a separately-labeled estimator field.
- Claude Code is the first platform where availability is empirically certifiable —
  a real capability, claimed at its true state.
- Example of the posture this standard takes:

```text
Tool invoked               ✅ observed
Result returned            ✅ observed
Result available next step ✅ observed (serialized-as-sent)
Result referenced          ~  weak estimator for influence — two failure modes named
Result influential         ✗  unproven — causal claim requires counterfactual evidence
```

## Rejected alternatives

- Grading evidence on a "consumed" boolean — rejected: the claim itself is wrong before
  the grade; grade the state, not the collapsed word.
- Treating `referenced` as a third semantic state — rejected (original Draft 0.4.4 ladder):
  reference is an estimator with two named failure modes, not a state; states are facts,
  estimators are evidence.
- Treating explicit reference as influence — rejected: a model restating a value is
  observable behavior, not proof the decision depended on it.
- Treating `serialized` and `reached-inference` as one claim — rejected: the provider
  boundary inside availability is real and cheap to name.
- Moving all consumption questions into Lab — rejected: availability is an ordinary,
  certifiable trace-layer fact and Core must keep saying it.
