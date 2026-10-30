# Tool-billing complaints: SURE exploratory study (2026-10-29)

This is a bounded, reproducible study of public complaints about agent-tool
billing. It is **not** a market survey, a complaint rate, or evidence that any
vendor systematically overcharges.

A discovery expansion now holds **50,000** unique public records (HN 49,090;
2024-11 to 2026-10). It is a discovery layer, not strict evidence; the 66 records
below remain the admissible subset after full/window review. The earlier CDP
pass contributed 2,437 curated discussions and 26 official pricing pages.

## What was done

- Method: SURE 1.6 — pre-registered gates, source plan, dedupe, codebook,
  evidence grading, counterevidence, audit.
- Raw hits: **2,027**; deduped discovery corpus: **1,949**.
- Full/window reads: **150**.
- Strict evidence records: **66** from 66 unique URLs; core complaints: **42**.
- Buyers: **62**; sellers/promotion: **4**; behavioural records (E2/E3/E4-/E5): **16**.
- Counterevidence: **7**.
- Time window: 2024-12 to 2026-10; 71% in the last 12 months.
- Sources with evidence: Hacker News 31, OpenAI Community 24, Cursor 7, Make 2,
  n8n 1, Vercel 1. GitHub contributed **0** evidence records because the
  unauthenticated core API returned 403 for issue bodies.
- Regions (vendor primary market, not user residence): US 60, EU 2, GLOBAL 4,
  CN 0.

## Audit status

**9/12 gates pass; study status: FAIL → conclusion ceiling is exploratory.**

Failed gates:

1. Counterevidence 7 < 8.
2. Only 3/18 required vendors have strict evidence (OpenAI, Anthropic,
   ElevenLabs) < 10.
3. Only one region with evidence < 2 (CN = 0).

These failures are retained, not waived. Chinese platforms were unreachable
during collection; no synthetic Chinese data was added.

## What the evidence actually says

| Theme | Strict records | Mechanism |
|---|---:|---|
| Prepaid credits expire / reset / become unusable | 22 | User paid, but the right to use the balance has a deadline or condition |
| Unexpected charges / hard limit failure | 9 | Spending cap or expected charge did not hold |
| Auto-recharge / automatic debit | 8 | Default-on or invisible recurring charge |
| Metering mismatch | 6 | Usage panel, invoice and actual consumption disagree |
| Refund / dispute blocked | 5 | Support path fails; user escalates to chargeback |
| Quota/speed decoupled from paid tier | 5 | Payment did not restore usable capacity |
| Price increase / plan shrink | 2 | Price is present, but not the dominant complaint |

**The dominant conflict is not absolute price. It is ownership, visibility and
control of prepaid balances.** Small amounts still produced strong reactions
when the rule was unexpected or undisclosed.

Representative public patterns (paraphrased, not verbatim):

- Credits expiring with no notice despite substantial unused balance.
- A configured spending cap being exceeded anyway.
- An auto-recharge or debit after the user believed it was disabled.
- A usage dashboard that cannot reproduce the invoice.
- A refund path that only works after a chargeback.

## What this supports

- A product need to model **credits, expiry dates, auto-recharge, hard caps,
  included quota and actual cash billing** as separate objects.
- A need for **line-item traceability** between usage, charge and invoice.
- A useful buyer feature: “what will expire / what can still be recovered /
  which charge is still unexplained.”
- A useful seller feature: “is metered usage represented in billing?” without
  calling every gap leakage revenue.

## What this does not support

- ❌ “X% of users are unhappy with billing.”
- ❌ “Chinese platforms are worse / better” — CN evidence = 0.
- ❌ “Tavily / Firecrawl / E2B / Browserbase billing is broken” — those were
  discovery hits only, without admissible source text.
- ❌ “Users will pay for a billing-audit product” — E4+ purchase evidence = 0.
- ❌ “Price increases are the main issue” — 2/66.

## Product implications

The ledger already separates bill facts, platform usage and recomputation.
This study adds a concrete backlog:

1. Credit entitlement ledger: purchase date, expiry, remaining balance, source.
2. Auto-recharge and hard-cap controls as evidence objects.
3. Reconciliation between usage dashboard, invoice and payment.
4. Expiry/notice timeline and “unexplained charge” queue.
5. Refund/chargeback outcome tracking, separate from findings.

The data remains exploratory until vendor coverage, counterevidence and
non-US evidence improve. The raw corpus and per-record audit live outside this
public repo; this summary intentionally omits copyrighted full text and
personal identifiers.

## 50k discovery stress test (2026-10-30)

A pre-registered screen of the 50,000-record discovery layer tested H1–H5. It did
**not** add strict evidence or upgrade the study.

| Hypothesis | Result |
|---|---|
| H1: credits/usage dominates price | Evidence shape supported: manual core rate 30% for credits vs 6% for price. Raw mentions are near parity (15.3% vs 14.9%), so this is not a prevalence claim. |
| H2: credit/subscription bills cause more surprises than token APIs | Not supported as stated: the full-sample difference reverses within Hacker News (0.8% vs 2.1% unexpected), showing source/vendor confounding. |
| H3: Chinese platforms are invisible in English sources | Supported only as source visibility: 37/50,000 labeled records (0.074%), 24 text mentions. CN strict evidence remains 0. |
| H4: ≥20% of screened negatives are downgraded | Supported in the stratified sample: 214/299 downgraded = 71.6% (95% CI 66.2–76.4%); double-coded 40: 85% agreement, κ=0.75. |
| H5: complaints produce behavioural consequences | Suggestive only: 8.4% contain action words; verified strict behaviour records remain 16. |

The 71.6% downgrade rate is a warning about keyword screening, not a claim that
only 28.4% of users are dissatisfied. The parent study remains **exploratory**.
