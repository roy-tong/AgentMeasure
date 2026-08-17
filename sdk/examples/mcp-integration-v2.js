#!/usr/bin/env node
/**
 * Integration example — MCP SDK v2 path (@modelcontextprotocol/server).
 *
 * v2 is the stable MCP TypeScript SDK line (2026-07-28 spec); the server
 * package is split out of the monolithic @modelcontextprotocol/sdk. Migrate
 * with the official guide:
 *   https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/migration/upgrade-to-v2.md
 *
 * This is the PRIMARY adapter path. Per-request caller resolution is native
 * to v2: clients attach their identity to every request (`_meta.clientInfo`),
 * so the middleware extracts the CallerClaim straight from the request
 * context — exactly the architecture:
 *
 *   request → extract clientInfo → CallerClaim → attempt observations
 *
 * Run:   node examples/mcp-integration-v2.js
 * Events: $AGENTMEASURE_EVENTS_DIR/agentmeasure-events.jsonl
 * Output: 42 calls → 84 canonical observations.
 */
import { McpServer, InMemoryTransport } from "@modelcontextprotocol/server";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { agentmeasure } from "../dist/index.js";

const PROJECT = "demo/acme-weather";

/** clientInfo (a self-claim) → CallerClaim; identity strength stays declared. */
function claimFromClientInfo(info) {
  const name = typeof info?.name === "string" ? info.name : "unknown";
  if (name === "claude" || name === "codex") {
    return { type: "claimed_agent", runtime: name, identityStrength: "declared" };
  }
  return { type: "unknown", runtime: "unknown", identityStrength: "unknown" };
}

const mw = agentmeasure({
  projectId: PROJECT,
  observerPrincipal: "am-sdk@acme",
  trustDomain: "acme",
  usageContext: "synthetic", // fixture traffic, labeled at the source
  // no server-level caller: per-request resolution below (fallback = unknown)
});

const server = new McpServer({ name: "acme-weather", version: "1.0.0" });

// registerTool (v2 API) wrapped through the same middleware. The v2 handler
// context carries the request (`ctx.mcpReq`) with per-request `_meta`.
server.registerTool(
  "get_weather",
  { inputSchema: z.object({ city: z.string() }) },
  mw.wrapTool("get_weather", async ({ city }) => {
    await new Promise((r) => setTimeout(r, 20 + Math.random() * 300));
    if (Math.random() < 0.12) {
      return { content: [{ type: "text", text: "ERROR: upstream unavailable" }], isError: true };
    }
    return { content: [{ type: "text", text: `weather in ${city}: 22C partly cloudy` }] };
  }, {
    getCaller: (ctx) =>
      claimFromClientInfo(ctx?.mcpReq?._meta?.clientInfo),
  }),
);

// Fixture clients. Each attaches its clientInfo to every request via `_meta`
// (v2 clients do this by default; here it is explicit for the fixture).
const CLIENTS = [
  { name: "claude", version: "1.0" },
  { name: "codex", version: "2.0" },
  { name: "curl", version: "0.0" }, // no agent claim → unknown
];
const CITIES = ["beijing", "shanghai", "tokyo", "paris"];

const connected = [];
for (const [ci, info] of CLIENTS.entries()) {
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await server.connect(serverTransport);
  const client = new Client({ name: info.name, version: info.version });
  await client.connect(clientTransport);
  connected.push({ client });
  for (let i = 0; i < 14; i++) {
    await client.request(
      {
        method: "tools/call",
        params: {
          name: "get_weather",
          arguments: { city: CITIES[(ci * 14 + i) % CITIES.length] },
          _meta: { clientInfo: { name: info.name, version: info.version } },
        },
      },
      CallToolResultSchema,
    );
  }
}
for (const { client } of connected) await client.close();

await mw.am.shutdown();

console.log("v2 path: 42 calls → 84 canonical observations.");
console.log("Caller claims per session: 14× claude (declared) · 14× codex (declared) · 14× unknown");
console.log("Next: python3 product/local-analytics.py <events file> --project demo/acme-weather --days 365");
process.exit(0);
