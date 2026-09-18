# Assumed Resolution — Intercom Fin Case Study

## The Controversy

In 2024–2025, Intercom's AI chatbot **Fin** faced growing scrutiny from customers and industry analysts over its "resolution rate" metric. Fin's public-facing dashboard claimed resolution rates of **70–76%** across thousands of customers — a number widely cited in Intercom's marketing, pricing page, and investor materials.

The controversy erupted when independent auditors and customers discovered that **Fin counted "assumed resolutions" as equivalent to confirmed resolutions** in its headline metric.

### How Fin Defined "Resolution"

Per Intercom's own documentation:

> A resolution is a type of outcome that is counted when, following Fin's last answer in a conversation, the customer either **confirms the answer was satisfactory** (confirmed resolution), or **exits the conversation without requesting further assistance** (assumed resolution).

This single sentence was the root of the dispute. An "assumed resolution" meant the customer simply stopped replying — for any reason. They may have:

- Found the answer helpful (genuine resolution)
- Given up in frustration
- Been too busy to reply
- Switched to another channel (email, phone)
- **Not seen the message at all** (e.g. notification missed)

The system defaulted to a **3-day inactivity timeout** after which the ticket was automatically marked "resolved." This auto-close mechanism was the primary driver of inflated numbers.

### The Inflation Gap

| Metric | Value |
|---|---|
| Fin's customer-facing claim (public dashboard) | **70–76%** resolution rate |
| Actual confirmed resolution rate (audited) | **~30–45%** |
| Gap | **25–40 percentage points** |

Industry analysts (including DragApp's 2026 audit) found that when "assumed resolution" tickets were separated from the confirmed bucket, the real resolution rate landed at **42–50%** even in Fin's own published case studies — far below the headline figure.

### Why It Matters

The gap had a direct **financial impact**. Intercom charged **$0.99 per outcome** on a per-conversation basis. Customers paying for "70% resolution" were effectively subsidising assumed resolutions that, in many cases, represented failed customer experiences:

> "At $0.99 per outcome, a claimed 76% that lands at 45% in production nearly doubles your effective cost per genuinely resolved conversation." — DragApp, 2026

---

## Settlement Evidence Bundle

The dispute could have been avoided — or at least made transparently auditable — with a structured **settlement evidence bundle** that separates outcome classes at the protocol level.

Below is a synthetic fixture (`fixture.jsonl`) that models the exact shape of the Intercom controversy as a **conformance evidence bundle**.

### Record Distribution (10 tickets)

| Outcome Class | Count | Observer Grade | Notes |
|---|---|---|---|
| `resolved` | 4 | `affected_party` | Customer explicitly confirmed the answer worked |
| `assumed_resolved` | 3 | `self_attested` | Fin's system auto-closed after 3-day inactivity |
| `escalated` | 2 | `affected_party` / `system` | Customer asked for human or Fin escalated |
| `abandoned` | 1 | `system` | Customer left before receiving any answer |

### Analysis

```text
$ agentmeasure settle --bundle ./conformance/evidence/assumed-resolution/fixture.jsonl

═══ Settlement Evidence Report ═══

Bundle:        assumed-resolution
Records:       10

─── Outcome Breakdown ───
resolved          4  (40.0%)  ✓ affected_party observer
assumed_resolved  3  (30.0%)  ✗ self_attested observer
escalated         2  (20.0%)
abandoned         1  (10.0%)

─── Provider Claim ───
"We resolved 7 out of 10 (70%)"

─── Audit Result ───
Truly resolved:      4/10 (40%)
Assumed resolved:    3/10 (30%)  ← MUST NOT aggregate into resolved
Unresolved total:    6/10 (60%)

─── Verdict ────
INFLATED. Claim includes 30% assumed_resolved outcomes
that lack affected_party confirmation. Real resolution
rate is 40%, not 70%.

═══ End ═══
```

### Key Rules Enforced

1. **`resolved`** requires `observer_grade: "affected_party"` — the affected party (customer) must explicitly confirm the outcome.
2. **`assumed_resolved`** uses `observer_grade: "self_attested"` — the provider attests unilaterally. This class **MUST NOT** be aggregated into `resolved` for settlement purposes.
3. **`escalated`** and **`abandoned`** are distinct terminal states, not partial resolutions.
4. The `stability_window_seconds` field records the inactivity timeout (default 259200 = 3 days) that triggered the assumed-resolution classification.

---

## Relevance to AgentMeasure Conformance

This case study exercises three core conformance primitives:

| Primitive | File / Reference | Role in This Case |
|---|---|
| **Outcome Class Taxonomy** | [Registry: vocabularies.yaml](/registry/vocabularies.yaml) | Defines `resolved`, `assumed_resolved`, `escalated`, `abandoned` as distinct, non-mergeable classes |
| **Effect-Confirmed Schema** | [Schema: effect-confirmed.schema.json](/schemas/payloads/effect-confirmed.schema.json) | Validates every record in the bundle: required fields, observer_grade constraints, timestamp ordering |
| **Operation Records** | `OUT-001`, `OUT O2` | Track the lifecycle of each ticket from creation through outcome determination |

### What the Bundle Prevents

- A provider cannot inflate resolution rates by lumping assumed resolutions into the confirmed bucket.
- An auditor can replay the exact evidence, re-classify every outcome, and produce a verifiable settlement figure.
- The `observer_grade` field creates an auditable chain of who declared the outcome — the customer (`affected_party`) or the provider (`self_attested`).

---

## References

- Intercom Help: [Fin AI Agent outcomes](https://www.intercom.com/help/en/articles/8205718-fin-ai-agent-outcomes) (defines resolution = confirmed + assumed)
- DragApp Blog: [AI Support Agent Resolution Rates](https://www.dragapp.com/blog/ai-support-agent-resolution-rates/) (independent audit of vendor claims)
- AgentMeasure Registry: [vocabularies.yaml](/registry/vocabularies.yaml)
- AgentMeasure Schema: [effect-confirmed.schema.json](/schemas/payloads/effect-confirmed.schema.json)
- Operation Records: `OUT-001`, `OUT-002`

---

*This case study is a synthetic conformance fixture for the AgentMeasure framework. It does not contain real Intercom customer data.*