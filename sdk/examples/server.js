#!/usr/bin/env node
/**
 * Example: wrap a real (synthetic) MCP tool handler with @agentmeasure/mcp.
 * Run: node examples/server.js  (after `npm install && npm run build`)
 * Output: ~/.agentmeasure/events/agentmeasure-events.jsonl (canonical observations)
 */
import { agentmeasure, AgentMeasure, fingerprint } from "../dist/index.js";

// --- a mock "remote MCP server" ---
const server = {
  tools: {},
  use(mw) {
    for (const [name, handler] of Object.entries(this.tools)) {
      this.tools[name] = mw.wrapTool(name, handler);
    }
  },
  register(name, handler) {
    this.tools[name] = handler;
  },
};

const am = new AgentMeasure({
  projectId: "github.com/acme/example-search",
  observerPrincipal: "am-sdk@acme",
  trustDomain: "acme",
  caller: { type: "claimed_agent", runtime: "claude", identityStrength: "declared" },
});

server.register("search", async (q) => {
  await new Promise((r) => setTimeout(r, 50 + Math.random() * 900));
  if (Math.random() < 0.18) throw new Error("upstream timeout"); // ~18% failure
  return { results: 10, query: q };
});
server.use(agentmeasure({
  projectId: "github.com/acme/example-search",
  observerPrincipal: "am-sdk@acme",
  trustDomain: "acme",
  caller: { type: "claimed_agent", runtime: "claude", identityStrength: "declared" },
}));

// --- simulate 200 agent calls (session 1: claude; session 2: codex) ---
const sessions = ["claude-sess-1", "codex-sess-2"];
for (let i = 0; i < 60; i++) {
  const sess = sessions[i % 2];
  const clientKey = fingerprint(sess);
  // the SDK does not know sessions (provider side); simulate by tagging caller runtime
  am.emit({
    type: "task_outcome",
    surfaceId: "runtime:task",
    payload: { task_id: `tk-${Math.floor(i / 5)}`, task_success: true },
  });
  try {
    await server.tools.search(`query ${i}`);
  } catch {
    // failure already observed by middleware
  }
  if (i % 50 === 0) console.log(`emitted ${i + 1} attempts (client ${clientKey.slice(0, 12)}…)`);
}
console.log("\nObservations written to ~/.agentmeasure/events/agentmeasure-events.jsonl");
console.log("Next: run `python3 product/local-analytics.py <events.jsonl>` for the local report.");
