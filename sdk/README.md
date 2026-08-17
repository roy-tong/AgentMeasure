# @agentmeasure/mcp

**AgentMeasure Provider SDK** — observe-first capability usage measurement for MCP
servers. Emits Canonical Observations (AgentMeasure Draft 0.4.3); non-blocking
buffered spool; no content captured.

```bash
npm install @agentmeasure/mcp
```

## MCP SDK v2 (primary) — `@modelcontextprotocol/server`

```ts
import { McpServer } from "@modelcontextprotocol/server";
import { agentmeasure } from "@agentmeasure/mcp";

const mw = agentmeasure({ projectId: "github.com/acme/weather-service" });

const server = new McpServer({ name: "acme-weather", version: "1.0.0" });
server.registerTool(
  "get_weather",
  { inputSchema: z.object({ city: z.string() }) },
  mw.wrapTool("get_weather", handler, {
    // per-request caller: v2 clients attach clientInfo to every request
    getCaller: (ctx) => claimFrom(ctx.mcpReq?._meta?.clientInfo),
  }),
);
```

## MCP SDK v1 (compatibility) — `@modelcontextprotocol/sdk`

```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { agentmeasure } from "@agentmeasure/mcp";

const mw = agentmeasure({ projectId: "github.com/acme/weather-service" });
const server = new McpServer({ name: "acme-weather", version: "1.0.0" });
const origTool = server.tool.bind(server);
server.tool = (name, schema, handler) =>
  origTool(name, schema, mw.wrapTool(name, handler, {
    getCaller: (ctx) => sessions.get(ctx?._meta?.sessionId ?? ""),
  }));
```

Full runnable examples (v1 + v2): `sdk/examples/mcp-integration.js` and
`mcp-integration-v2.js` — each emits **42 calls → 84 canonical observations**
(attempt_started + attempt_completed only).

## What you get (local, no cloud)

```bash
python3 product/local-analytics.py ~/.agentmeasure/events/agentmeasure-events.jsonl --project github.com/acme/weather-service
```

```text
Canonical observations accepted : 84   rejected: 0
Observed attempts               : 42
Strict Qualified attempts      : 0 (0.0%)          # synthetic → never production
Success / Failure              : success-rate 90.5%
Latency (duration_ms)          : n=42 mean=168ms p50=165ms p95=297ms
Operation resolution           : resolved 0 / 42 attempts (coverage 0.0%)   # fail-closed
Caller attribution             : claude:14 codex:14 unknown:14 (declared=28 / unknown=14)
```

## Core promises

| Promise | Implementation |
| --- | --- |
| Observe first, qualify later | `usage_context` / `validity` default `unknown`; fixtures label themselves (`synthetic`) |
| Validity discipline | providers can only claim validity they can know (`health_check` / `load_test` / `suspected_invalid` / `duplicate`); `normal` is collector-derived and never claimable from config |
| Fail-open | `emit()` never throws into your handler; business errors propagate normally |
| Not on critical path | `emit()` only enqueues; background flusher batches writes (no sync IO in the request path) |
| Durable best-effort buffering | memory queue → batch flush → rotating spool files (default 5 MiB / keep 7); spool dir 0700, files 0600 |
| Loss accounting | `bufferHealth`: queueDepth · droppedTotal · droppedSinceLastFlush · flushFailures · spoolBytes · rotatedFiles |
| Crash boundary | up to one flush interval of in-memory observations may be lost on abrupt termination (SIGKILL/crash); `await am.shutdown()` drains; optional `handleSignals` hooks SIGTERM/SIGINT |
| No content | arguments/results/paths unreachable by design |
| Caller per-request | `getCaller(ctx)` resolves per request (v2 `_meta.clientInfo` / v1 `_meta.sessionId` echo); server-level claim is a fallback for fixtures only |
| Canonical output | validated against `schemas/observation.schema.json` (vocab driven by `registry/vocabularies.yaml`); lineage snake_case (`operation_id` / `task_id` / `retry_of`) |
| MCP-version-agnostic | the SDK imports no MCP package; v1/v2 adapters live in the examples (no peer dependency) |

## Buffer model

```text
Request
  │
  ├── enqueue Observation (emit() — no IO)
  ▼
Return

Background flusher
  ↓
memory queue → batch → rotating spool files
```

`bufferHealth` exposes the loss accounting the standard requires; the same numbers
are stamped into each persisted batch's `collection_health` block.

**Multi-process deployments**: `eventsDir` MUST NOT be shared between processes
in 0.1.x. Give each process its own file, e.g.
`agentmeasure({ spoolFileName: \`agentmeasure-events-${process.pid}.jsonl\` })`,
and point the collector at the `agentmeasure-events-*.jsonl` glob.

**Deterministic fixtures**: `wrapTool(..., { durationMs })` accepts a fixed value
or a function sampled at completion time — used by the demo fixture so that
same fixture + same policy = bitwise-identical semantic output. Production
deployments omit it; the middleware then records measured wall time.

## Development

```bash
npm install && npm run build
npm test                       # schema / fail-open / privacy / lineage / caller /
                               # concurrency / buffer / mcp-integration (v1+v2)
node examples/mcp-integration.js      # v1 path → local JSONL
node examples/mcp-integration-v2.js   # v2 path (primary) → local JSONL
```

## Status

v0.1.1 — External-Ready. Standard (Draft 0.4.3), reference collector, conformance
suite and canonical pipeline gates are stable; hosted ingestion and dashboard are
next (product/MVP.md). MIT licensed.
