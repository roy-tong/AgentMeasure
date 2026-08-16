# Changelog

All notable changes to AgentMeasure (standard, SDK, and reference product) are
documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

- **Product Gate A in progress**: first external Provider onboarding ([#2](https://github.com/roy-tong/AgentMeasure/issues/2)), first benchmark design discussion ([#3](https://github.com/roy-tong/AgentMeasure/discussions/3))

## [v0.1.0] - 2026-08-16

First public release: the measurement layer for the Agent Capability Economy.

### Added

- **Standard (Draft 0.4.3)**: canonical observation schema + 6 payload types, qualification resolution, metrics registry (14 metrics, single source of truth), observe-first policy with `unknown` defaults
- **SDK**: `@agentmeasure/mcp` v0.1.0 — TypeScript wrapper for official MCP SDK servers (fail-open, zero-content, registration-time wrapping)
- **Product**: canonical end-to-end pipeline (adapters → observations → collector → metrics); `local-analytics.py` with six classes of metrics
- **Measurement Report #001**: honest baseline (42 synthetic calls, 126 observations, 0 qualified usage by design)
- **Docs**: whitepaper (EN/ZH), core spec, quality dimensions, commercial semantics, roadmap, governance
- **Community**: Discussions with 5 categories; issue templates (Metric Semantics / Observation Gap / Discrepancy / Proposal)

### Notes

- `0 stars at launch` is a feature of the honesty-first posture, not a bug.
- Synthetic traffic only so far; every limitation is stated in the report.
