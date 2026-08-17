#!/usr/bin/env node
/**
 * Integration example — MCP SDK v1 path (@modelcontextprotocol/sdk).
 *
 * Shows the provider-side pattern AgentMeasure is built for:
 *
 *   request → extract client identity (_meta.sessionId echo) → CallerClaim
 *           → attempt_started / attempt_completed observations
 *
 * Caller is resolved PER REQUEST from the session map populated at
 * initialize (clientInfo), not from server configuration. There is no
 * server-level caller claim here: unknown is the honest fallback.
 *
 * Run:   node examples/mcp-integration.js
 * Events: $AGENTMEASURE_EVENTS_DIR/agentmeasure-events.jsonl
 *         (defaults to ~/.agentmeasure/events/agentmeasure-events.jsonl)
 *
 * Output: 42 calls → 84 canonical observations (42 attempt_started +
 *         42 attempt_completed). No result_consumed: a provider-side server
 *         cannot observe whether the agent later consumed the result.
 *         UNOBSERVABLE is not fabricated as TRUE.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import {
  CallToolResultSchema,
  InitializeRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { z } from "zod";
import { agentmeasure } from "../dist/index.js";

const PROJECT = "demo/acme-weather";

/** sessionId → CallerClaim, populated from initialize clientInfo. */
const sessions = new Map();

const mw = agentmeasure({
  projectId: PROJECT,
  observerPrincipal: "am-sdk@acme",
  trustDomain: "acme",
  // fixture traffic is labeled synthetic at the source — never production
  usageContext: "synthetic",
  // no server-level caller: per-request resolution below (fallback = unknown)
});

// A fresh server instance per connection (one MCP server = one transport
// session), sharing the middleware and the session map.
let sessionSeq = 0;
function makeServer() {
  const server = new McpServer({ name: "acme-weather", version: "1.0.0" });

  // Assign a session id per connection and record the client's self-declared
  // identity (clientInfo is a claim, so identity strength stays "declared").
  server.server.setRequestHandler(InitializeRequestSchema, (req) => {
    const info = req.params.clientInfo ?? { name: "unknown" };
    const sid = `demo-${info.name}-${sessionSeq++}`;
    const claim =
      info.name === "claude" || info.name === "codex"
        ? { type: "claimed_agent", runtime: info.name, identityStrength: "declared" }
        : { type: "unknown", runtime: "unknown", identityStrength: "unknown" };
    sessions.set(sid, claim);
    console.log(`session ${sid} ← clientInfo ${info.name} → caller ${claim.identityStrength}`);
    return {
      protocolVersion: "2025-06-18",
      capabilities: { tools: {} },
      serverInfo: { name: "acme-weather", version: "1.0.0" },
    };
  });

  // Wrap at registration (official API path): any MCP server handler can be
  // wrapped without touching arguments or results.
  const origTool = server.tool.bind(server);
  server.tool = (name, schema, handler) =>
    origTool(name, schema, mw.wrapTool(name, handler, {
      getCaller: (ctx) =>
        sessions.get(String(ctx?._meta?.sessionId ?? ctx?.meta?.sessionId ?? ctx?.sessionId ?? "")),
    }));

  // Third-party style tool handler: takes args, returns results; zero content
  // captured by the middleware.
  server.tool("get_weather", { city: z.string() }, async ({ city }) => {
    await new Promise((r) => setTimeout(r, 20 + Math.random() * 300));
    if (Math.random() < 0.12) {
      return { content: [{ type: "text", text: "ERROR: upstream unavailable" }], isError: true };
    }
    return { content: [{ type: "text", text: `weather in ${city}: 22C partly cloudy` }] };
  });
  return server;
}

// Fixture clients: 3 identities × 14 calls = 42 attempts.
// Each client echoes its server-assigned session id in `_meta` per MCP spec.
const CLIENTS = [
  { name: "claude", version: "1.0" },
  { name: "codex", version: "2.0" },
  { name: "curl", version: "0.0" }, // no agent claim → unknown
];
const CITIES = ["beijing", "shanghai", "tokyo", "paris"];

const connected = [];
for (const [ci, info] of CLIENTS.entries()) {
  const server = makeServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.server.connect(serverTransport);
  const client = new Client({ name: info.name, version: info.version });
  await client.connect(clientTransport);
  const sid = `demo-${info.name}-${ci}`;
  connected.push({ client });
  for (let i = 0; i < 14; i++) {
    await client.request(
      {
        method: "tools/call",
        params: {
          name: "get_weather",
          arguments: { city: CITIES[(ci * 14 + i) % CITIES.length] },
          _meta: { sessionId: sid },
        },
      },
      CallToolResultSchema,
    );
  }
}
for (const { client } of connected) await client.close();

await mw.am.shutdown();

console.log("42 calls → 84 canonical observations (attempt_started + attempt_completed).");
console.log("Caller claims per session: 14× claude (declared) · 14× codex (declared) · 14× unknown");
console.log("Next: python3 product/local-analytics.py <events file> --project demo/acme-weather --days 365");
process.exit(0);
