# Examples

## 2-minute end-to-end demo（推荐先跑这个）

```bash
./examples/demo-e2e.sh
```

What you'll see: a mock MCP server instrumented with `@agentmeasure/mcp`
(42 calls → 252 canonical observations, 0 rejected), then the local metrics
report — with **Strict Qualified Usage defaulting to 0%** until evidence
upgrades it. That's the observe-first behavior by design, not a bug.

## SDK integration example

[`sdk/examples/mcp-integration.js`](../sdk/examples/mcp-integration.js) — wrap any
official-MCP-SDK server tool handler at registration time (arguments/results never
touched, nothing on the request critical path).

```bash
cd sdk && node examples/mcp-integration.js
```

## Onboarding your own MCP server (3 steps)

1. `npm install @agentmeasure/mcp`
2. Wrap your tool handlers as in `sdk/examples/mcp-integration.js`
3. Point the metrics tool at the events file:

```bash
python3 product/local-analytics.py ~/.agentmeasure/events/agentmeasure-events.jsonl
```

Questions? [Issue #2: First external Provider onboarding](https://github.com/roy-tong/AgentMeasure/issues/2)
is the front door — we'll add you to the conformance list.
