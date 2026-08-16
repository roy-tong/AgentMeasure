# agent-used

**An open usage attribution standard for software used by AI agents.**

> OpenTelemetry tells us how telemetry travels.
> **agent-used defines what counts as usage.**

agent-used is an open Usage Attribution standard and infrastructure for the AI-agent software ecosystem. It collects call evidence from both the agent side and the tool side, normalizes usage across Codex, Claude Code, DeepSeek Harness and MCP, correlates and deduplicates both sides, and publishes privacy-preserving aggregate metrics with explicit evidence levels.

**Not another observability tool.** Langfuse/Grafana answer "how is my agent running?"; agent-used answers "which third-party tools are actually used by agents across the ecosystem?"

[Whitepaper: How to Measure the Agent Tool Economy](whitepaper/agent-tool-economy-zh.md) · [Measurement Spec](spec/measurement-spec.md)

## Core concepts

### The usage funnel: Install != Usage
S0 Selected → S1 Executed → S2 Execution Success → S3 Result Consumed → S4 Task Contribution (S0-S2 MVP, S3 partial, S4 research).

### Evidence levels: signature != truth
E0 Observed (one-sided claim) · E1 Source-authenticated (signed) · **E2 Correlated (both sides, same trace_id — the core)** · E3 Platform-attested.
HMAC proves origin and integrity, not that a real agent called. `corroborated usage` (E2) is the credibility core; MCP 2026-07-28 RC makes trace context propagation protocol-level.

### Metrics: raw calls are not the north star
Adoption (Active Agent Sessions — primary) · Engagement (repeat usage) · Quality (success / consumption) · Trust (corroborated share). Rankings by sessions, never by raw calls.

## Architecture

```
Public Usage Layer (dashboard/api/badge/rankings)
        ▲  aggregated only
Attribution Layer (identity · dedup · correlation · evidence · privacy · normalization)
        ▲                    ▲
 Agent Adapters            Tool Adapters
  codex / claude / dsh       mcp / http / cli
        ▲                    ▲
   OTel / MCP existing standards
```

Standing **on top of OTel**: reuse `gen_ai.tool.name`, `mcp.method.name`, trace fields; add only 6 `agentused.*` extensions ([otel-mapping](spec/otel-mapping.md)).

## Privacy

**Raw telemetry stays local. Public infrastructure receives aggregates by default.**
prompt / tool_input / tool_output / path / raw session id — dropped at code level (leak tests). Pseudonymous installation ids (local secret, rotating epochs). `DO_NOT_TRACK=1` honored end-to-end.

## Roadmap

M0 Definition ✅ (spec + whitepaper + threat model) · M1 Cross-Agent Proof (codex/claude/dsh adapters) · M2 OTel Native (collector + mapping) · M3 Attribution (identity graph + correlation) · M4 Public Network (api/dashboard/badge) · M5 External Validation (real adopters + discrepancy report) · M6 Ecosystem (MCP/OTel/platform/registry cooperation)

**Explicitly not doing**: replacing OTel, automated starring, content collection, raw-call rankings, cloud aggregation before M3.

## License

MIT
