#!/usr/bin/env node
/**
 * Minimal mock-server example: wrap a plain (non-MCP) handler with the
 * middleware. The server-level caller claim below is a FIXTURE fallback only —
 * real integrations resolve the caller per request (see mcp-integration*.js).
 *
 * Run: node examples/server.js  (after `npm install && npm run build`)
 * Events: $AGENTMEASURE_EVENTS_DIR/agentmeasure-events.jsonl
 *         (defaults to ~/.agentmeasure/events/agentmeasure-events.jsonl)
 */
import { agentmeasure } from "../dist/index.js";

// --- a mock "remote server" ---
const server = {
  tools: {},
  register(name, handler) {
    this.tools[name] = handler;
  },
  use(mw) {
    for (const [name, handler] of Object.entries(this.tools)) {
      this.tools[name] = mw.wrapTool(name, handler);
    }
  },
};

const mw = agentmeasure({
  projectId: "github.com/acme/example-search",
  observerPrincipal: "am-sdk@acme",
  trustDomain: "acme",
  usageContext: "synthetic", // fixture traffic, labeled at the source
  caller: { type: "claimed_agent", runtime: "claude", identityStrength: "declared" }, // fixture fallback
});

server.register("search", async (q, n) => {
  await new Promise((r) => setTimeout(r, 50 + ((n * 37) % 800)));
  if (n % 6 === 0) throw new Error("upstream timeout"); // deterministic ~17% failure
  return { results: 10, query: q };
});
server.use(mw);

// --- simulate 60 calls (synthetic, deterministic fixture) ---
for (let i = 0; i < 60; i++) {
  try {
    await server.tools.search(`query ${i}`, i);
  } catch {
    // failure already observed by middleware
  }
}
await mw.am.shutdown();

console.log(`60 synthetic calls → observations at: ${mw.am.bufferHealth.path}`);
console.log(`bufferHealth: flushed=${mw.am.bufferHealth.flushedTotal} dropped=${mw.am.bufferHealth.droppedTotal} failures=${mw.am.bufferHealth.flushFailures}`);
console.log("Next: run `python3 product/local-analytics.py <events.jsonl>` for the local report.");
