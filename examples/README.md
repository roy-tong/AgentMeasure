# Examples

## 2-minute end-to-end demo（推荐先跑这个）

```bash
./examples/demo-e2e.sh
```

What you'll see: a mock MCP server instrumented with `@agentmeasure/mcp`
(**42 calls → 84 canonical observations, 0 rejected**), then the local metrics
report — with **Strict Qualified Usage defaulting to 0%** (the fixture is labeled
`synthetic`, never production) and **per-request caller attribution**
(claude:14 · codex:14 · unknown:14).

The demo runs in an isolated workspace (`mktemp -d`) and never touches
`~/.agentmeasure` — same fixture + same policy = same result, every run.

## SDK integration examples

- [`sdk/examples/mcp-integration.js`](../sdk/examples/mcp-integration.js) — **MCP SDK v1 path**
  (`@modelcontextprotocol/sdk`): wrap tool handlers at registration; per-request
  caller resolved from the `_meta.sessionId` echo against the initialize-time
  clientInfo map.
- [`sdk/examples/mcp-integration-v2.js`](../sdk/examples/mcp-integration-v2.js) — **MCP SDK v2 path**
  (`@modelcontextprotocol/server`, the stable 2026-07-28 spec line): per-request
  caller extracted from `_meta.clientInfo` directly in the request context.

Both paths emit the same contract: 42 calls → 84 canonical observations
(attempt_started + attempt_completed only; no invented result_consumed).

```bash
cd sdk && node examples/mcp-integration.js      # v1
cd sdk && node examples/mcp-integration-v2.js   # v2 (primary)
```

## Onboarding your own MCP server (3 steps)

1. `npm install @agentmeasure/mcp`
2. Wrap your tool handlers as in `sdk/examples/mcp-integration-v2.js` (v2) or
   `mcp-integration.js` (v1)
3. Point the metrics tool at the events file:

```bash
python3 product/local-analytics.py ~/.agentmeasure/events/agentmeasure-events.jsonl --project github.com/you/your-server
```

Questions? [Issue #2: First external Provider onboarding](https://github.com/roy-tong/AgentMeasure/issues/2)
is the front door — we'll add you to the conformance list.
