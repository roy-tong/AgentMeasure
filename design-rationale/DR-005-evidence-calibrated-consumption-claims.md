# DR-005 — Evidence-Calibrated Consumption Claims

- Status: Adopted as design rationale (Draft 0.4.4); tracked in #11
- Date: 2026-08-25
- External evidence: Gunjan Jaswal (client-side taxonomy, direct reply 2026-08-25);
  Exa engineer (provider-side boundary, direct reply 2026-08-20) — cross-validated from
  both observation sides

## Problem

What does "the agent consumed the tool result" mean, and what can telemetry prove?

A single trace can establish that a result was returned and entered the next model call's
context. It cannot establish that the result influenced the agent's next decision. Two
independent reviewers converged on this from opposite observation points: the provider
side cannot see past `returned`; the client side cannot see past `available in context`
without counterfactual evidence. Collapsing the rungs into one word — "consumed" —
overclaims causal knowledge from observational data.

## Decision

**Consumption claims are calibrated to the highest rung the evidence supports.**

```text
Tool Invoked
    ↓
Result Returned            (execution / delivery)
    ↓
Result Available to Agent  (context exposure — certifiable from a single trace)
    ↓
Result Referenced          (behavioral evidence — observable sometimes, weak, not causal)
    ↓
Result Influential         (counterfactual — requires ablation / rerun)
    ↓
Task / World Effect
```

1. The trace layer certifies **availability**, and observes **reference** as weak evidence.
2. **Causal influence belongs to the experiment layer** (Lab: ablation / rerun), never to
   ordinary trace telemetry.
3. Normative claims MUST name the rung they observe. `mcp_tool.name` present in the next
   request = availability signal, not consumption/influence.
4. Profiles declare which rung they can observe (see PROFILES.md P2, scoped since db7fac4).

This also fixes the Core/Lab relationship: Core observes what telemetry can prove;
Lab estimates what only experiments can.

## Implications

- PROFILES.md P2: "Consumption signal" renamed to **Context Availability signal**, with
  explicit `available ≠ referenced ≠ counterfactually influential` boundary (#11).
- M4.1 rename decision tracked in #11 (candidate: Result Availability Rate).
- Claude Code is the first platform where availability is empirically certifiable —
  a real capability, claimed at its true rung.
- Example of the posture this standard takes:

```text
Tool invoked               ✅ observed
Result returned            ✅ observed
Result available next step ✅ observed
Result referenced          ?  unknown
Result influential         ?  unproven — causal claim requires counterfactual evidence
```

## Rejected alternatives

- Grading evidence on a "consumed" boolean — rejected: the claim itself is wrong before
  the grade; grade the rung, not the collapsed word.
- Treating explicit reference as influence — rejected: a model restating a value is
  observable behavior, not proof the decision depended on it.
- Moving all consumption questions into Lab — rejected: availability is an ordinary,
  certifiable trace-layer fact and Core must keep saying it.
