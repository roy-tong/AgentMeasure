# @agentmeasure/mcp

**AgentMeasure Provider SDK** — observe-first capability usage measurement for MCP
servers. Emits Canonical Observations (AgentMeasure Draft 0.4.3); never on the
request critical path; no content captured.

```bash
npm install @agentmeasure/mcp
```

```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { agentmeasure } from "@agentmeasure/mcp";

const mw = agentmeasure({
  projectId: "github.com/acme/weather-service",
  caller: { type: "claimed_agent", runtime: "claude", identityStrength: "declared" },
});

const server = new McpServer({ name: "acme-weather", version: "1.0.0" });
const origTool = server.tool.bind(server);
const wrapped = {};
server.tool = (name, schema, handler) => {
  wrapped[name] = mw.wrapTool(name, handler);
  return origTool(name, schema, wrapped[name]);
};

server.tool("get_weather", { city: z.string() }, async ({ city }) => { /* ... */ });
// → every call emits attempt_started / attempt_completed (canonical observations)
```

## What you get (local, no cloud)

```bash
python3 product/local-analytics.py ~/.agentmeasure/events/agentmeasure-events.jsonl
```

```text
Observed attempts               : 42
Strict Qualified attempts      : 0 (0.0%)          # unknown by default — evidence only
Success / Failure              : success-rate 85.7%
Operation resolution           : resolved 0 / 42 attempts (coverage 0.0%)   # fail-closed
```

## Core promises

| Promise | Implementation |
| --- | --- |
| Observe first, qualify later | `usage_context` / `validity` default `unknown` |
| Fail-open | never throws into your handler; errors propagate normally |
| Not on critical path | async append to local buffer |
| No content | arguments/results/paths unreachable by design |
| Caller discipline | `declared` at most; UA/clientInfo never becomes `correlated` |
| Loss accounting | `source_sequence` + `dropped_since_last_report` |
| Canonical output | validated against `schemas/observation.schema.json` |

## Development

```bash
npm install && npm run build
node examples/server.js            # synthetic traffic → local JSONL
node examples/mcp-integration.js   # official MCP SDK integration
```

## Status

v0.1.0 — in development. Standard (Draft 0.4.3), reference collector and conformance
suite are stable; hosted ingestion and dashboard are next (product/MVP.md).
