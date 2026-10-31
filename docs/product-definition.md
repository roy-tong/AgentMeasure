# Verovo product definition

Baseline: 2026-10-30. Implementation alignment: 2026-10-31.

**Verovo is a buyer-side product for verifying AI service charges and delivery.**
It connects applicable charging rules, spending and usage records, delivery
evidence and buyer requirements to support payment, reconciliation, acceptance,
remediation and renewal decisions. Provider-side work extends from concrete
transactions rather than defining a second equal-priority market.

## Users and responsibilities

Business, engineering and team owners are accountable for AI spending or business
results. Finance and procurement help with payment, contracts and approval.
Identify the person who has the records, the person who uses the result and the
person who can commission work; these may be different people.

## Two independent workflows

| Workflow | Basis | Result |
|---|---|---|
| Charges | Applicable charging rules, account, period and records | Matching items, supported differences and unresolved items |
| Delivery | Explicit business acceptance criteria and observable results | Met, unmet and unprovable requirements, with remediation needs |

A correct charge can accompany inadequate delivery. A failed buyer requirement
does not automatically establish a billing violation. Delivery review can be
commissioned independently of a billing discrepancy. Every result is limited to
the criteria, observations and coverage actually reviewed.

## Objects and current focus

AI applications, coding agents, automation platforms, tools/APIs and model
services are the long-term object map. AI support is an initial application
scenario. Tool-period reconciliation is another concrete buyer task. Broader
coverage requires its own adapters, usable records and customer validation.

The first implementation combines existing local tools and scoped human review.
Review reports carry three separate conclusion levels: rule consistency (what a run
establishes), evidence credibility (explicitly not established by the tool: rule
applicability confirmation, third-party corroboration, coverage), and the buyer
business decision (outside the tool). The levels are never collapsed into a score
and Level 3 never becomes a tool output.
The [buyer review command](buyer-review.md) compares explicit criteria with local
JSON observations and produces separate charge/delivery reports. Supported
recounts and Buyer Ledger remain specialized input and calculation capabilities.
It is not a universal contract parser, autonomous quality judge or refund system.

## Keep these layers separate

- Buyer-first, charges and delivery: product boundary.
- Support, coding, automation, tools and models: objects and scenarios.
- Ledger, rules, SDK, browser access and evidence hashes: capabilities.
- A/B POCs, sample sizes and schedules: adjustable validation plans.
- Open source, scoped projects and possible repeat service: operating models.

Provider upstream spend is a buyer task. Provider downstream billing work needs
a specific dispute, revenue discrepancy or procurement requirement. Shared code
does not establish demand on both sides or a network effect.

## Scope changes

State the changed layer, previous scope, proposed scope, reason and review
condition. New engineering capabilities or a narrow experiment do not silently
replace this definition. Customer value, actual payment and repeat purchase are
separate from engineering tests and open-source use.

The current [free measurement runs](https://roy-tong.github.io/verovo/services.html)
remain free and limited to measurement samples. Enterprise review scope and any
fee are agreed for a concrete task; there is no fixed enterprise rate or recovery
guarantee. See [commercial scope](commercial-narrative.md).
