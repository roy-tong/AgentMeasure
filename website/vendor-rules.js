/* GENERATED FILE — do not edit.
 * Source: registry/vendor-rules.json (the single source of truth).
 * Regenerate with: python3 scripts/gen_web_rules.py --build
 * CI runs --check and fails if this file is out of date.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.AGENTMEASURE_VENDOR_RULES = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  return {
  "_comment": "AgentMeasure vendor billing rules — SINGLE SOURCE OF TRUTH. Read by the Python CLI (healthcheck/am_healthcheck/vendors.py) and by the browser-local recount (website/recount.js). A parity test in CI fails if the two disagree on the same fixture. Do not edit a consumer; edit this file.",
  "canonical_columns": [
    "conversation_id",
    "opened_at",
    "closed_at",
    "human_agent_participated",
    "issue_addressed",
    "customer_recontacted_within_window",
    "vendor_billed"
  ],
  "column_aliases": {
    "closed_at": [
      "closed_at",
      "closed_date",
      "solved_at",
      "resolved_at",
      "solved at",
      "closed at"
    ],
    "conversation_id": [
      "conversation_id",
      "conversation",
      "id",
      "ticket_id",
      "ticket",
      "ticket id",
      "conversation id"
    ],
    "customer_recontacted_within_window": [
      "customer_recontacted_within_window",
      "customer_recontacted",
      "reopened",
      "recontacted_within_window"
    ],
    "human_agent_participated": [
      "human_agent_participated",
      "human_agent_stepped_in",
      "human_agent",
      "teammate_replied",
      "agent_stepped_in"
    ],
    "issue_addressed": [
      "issue_addressed",
      "addressed",
      "solution_provided"
    ],
    "opened_at": [
      "opened_at",
      "opened_date",
      "created_at",
      "created",
      "created at",
      "conversation created at"
    ],
    "vendor_billed": [
      "vendor_billed",
      "billed",
      "vendor_billed_as_resolution",
      "billed_as_resolution",
      "resolution_billed"
    ]
  },
  "required_columns": [
    "conversation_id",
    "human_agent_participated",
    "issue_addressed",
    "customer_recontacted_within_window",
    "vendor_billed"
  ],
  "vendors": {
    "ada": {
      "billing_trigger": "algorithmic_classification",
      "closure_timers_hours": {
        "email": 72,
        "social": 24,
        "web": 24
      },
      "confidence": "S",
      "currency": null,
      "export_fields": [
        "automated_resolution_classification",
        "automated_resolution_classification_reason",
        "is_escalated",
        "csat.resolved"
      ],
      "name": "Ada",
      "operator_override": "operator feedback does not override the automatic classification",
      "reopen_deduction": "not_documented",
      "silence_bills": true,
      "silence_window_hours": 24,
      "source": "ada.cx pricing/terms returned 403; rule reported from public docs",
      "unit_price": null
    },
    "generic": {
      "billing_trigger": "unknown",
      "closure_timers_hours": {},
      "confidence": "U",
      "currency": null,
      "name": "Generic per-resolution vendor",
      "reopen_deduction": "not_documented",
      "silence_bills": null,
      "silence_window_hours": null,
      "source": "no vendor rules; only the AgentMeasure standard is applied",
      "unit_price": null
    },
    "hubspot": {
      "billing_trigger": "assumed_with_lock",
      "closure_timers_hours": {
        "email": 72,
        "messaging": 72
      },
      "confidence": "S",
      "currency": "USD",
      "name": "HubSpot Breeze",
      "reopen_deduction": "none_after_lock",
      "silence_bills": true,
      "silence_window_hours": 72,
      "source": "secondary; knowledge.hubspot.com is JS-only and could not be read",
      "structural_risk": "a reopen after the 72-hour lock starts a FRESH billable window instead of deducting the original, which is a double-billing risk rather than a protection",
      "unit_price": 0.5
    },
    "intercom": {
      "billing_trigger": "confirmed_or_assumed",
      "closure_timers_hours": {
        "email": 72,
        "messaging": 24
      },
      "confidence": "P",
      "currency": "USD",
      "name": "Intercom Fin",
      "notes": [
        "confirmed resolution rate and assumed resolution rate are separate published metrics, so a buyer can at least see the split",
        "resolution state is filterable and exposed via API v2.11+"
      ],
      "reopen_deduction": "documented_including_cross_period",
      "silence_bills": true,
      "silence_window_hours": 24,
      "source": "fin.ai pricing & outcomes; Intercom help centre (Fin AI Agent outcomes)",
      "unit_price": 0.99
    },
    "salesforce": {
      "billing_trigger": "autonomous_completion",
      "closure_timers_hours": {},
      "confidence": "U",
      "currency": null,
      "name": "Salesforce Agentforce Help Agent",
      "notes": [
        "no timer, no reopen rule, and no clawback are published",
        "the broader Agentforce product is billed whether or not the issue was resolved"
      ],
      "reopen_deduction": "not_documented",
      "silence_bills": null,
      "silence_window_hours": null,
      "source": "press release only; no official metering document is published",
      "unit_price": null
    },
    "zendesk": {
      "billing_trigger": "llm_verified_only",
      "closure_timers_hours": {
        "email": 72,
        "messaging": 2,
        "voice": 0
      },
      "confidence": "P",
      "currency": "USD",
      "name": "Zendesk AI Agents",
      "no_reversal": "deleting a ticket with Resolution type Automated does not undo the consumption of an automated resolution",
      "no_rollover": true,
      "notes": [
        "criteria, thresholds and error rate behind the LLM adjudication are not published",
        "unused allowance does not roll over to the next billing period"
      ],
      "reopen_deduction": "not_documented",
      "silence_bills": false,
      "silence_window_hours": null,
      "source": "Zendesk help centre: About the automated resolutions platform; About automated resolution tiers (edited 2026-08-25)",
      "unit_price": 2.0
    }
  },
  "version": "0.4.5"
};
});
