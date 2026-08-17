import test from "node:test";
import assert from "node:assert/strict";
import { AgentMeasure } from "../dist/index.js";
import { makeEventsDir, drain } from "./helpers.mjs";

const CLAUDE = { type: "claimed_agent", runtime: "claude", identityStrength: "declared" };
const CODEX = { type: "claimed_agent", runtime: "codex", identityStrength: "declared" };

test("caller: per-request resolver wins over server fallback (v1 meta shape)", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({
    eventsDir: dir,
    projectId: "t/caller1",
    caller: { type: "claimed_agent", runtime: "fallback", identityStrength: "declared" },
  });
  const sessions = new Map([
    ["sess-claude", CLAUDE],
    ["sess-codex", CODEX],
  ]);
  const wrapped = am.wrapTool("t", async () => ({}), {
    getCaller: (ctx) => sessions.get(String(ctx?.meta?.sessionId ?? "")),
  });
  await wrapped(undefined, { meta: { sessionId: "sess-claude" } });
  await wrapped(undefined, { meta: { sessionId: "sess-codex" } });
  await wrapped(undefined, { meta: { sessionId: "sess-nope" } }); // → fallback
  await wrapped(); // no context → fallback
  const lines = await drain(am, dir);
  const callers = lines
    .filter((l) => l.observation_type === "attempt_started")
    .map((l) => l.caller.runtime);
  assert.deepEqual(callers, ["claude", "codex", "fallback", "fallback"]);
});

test("caller: v2 request shape (ctx.mcpReq._meta.clientInfo) resolves per request", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/caller2" });
  const wrapped = am.wrapTool("t", async () => ({}), {
    getCaller: (ctx) => {
      const info = ctx?.mcpReq?._meta?.clientInfo;
      const name = typeof info?.name === "string" ? info.name : "unknown";
      return name === "claude"
        ? CLAUDE
        : name === "codex"
          ? CODEX
          : { type: "unknown", runtime: "unknown", identityStrength: "unknown" };
    },
  });
  await wrapped(undefined, { mcpReq: { _meta: { clientInfo: { name: "claude" } } } });
  await wrapped(undefined, { mcpReq: { _meta: { clientInfo: { name: "curl" } } } });
  const lines = await drain(am, dir);
  const callers = lines
    .filter((l) => l.observation_type === "attempt_started")
    .map((l) => l.caller);
  assert.deepEqual(
    callers.map((c) => c.runtime),
    ["claude", "unknown"],
  );
  assert.equal(callers[0].identity_strength, "declared");
  assert.equal(callers[1].identity_strength, "unknown");
});

test("caller: server-level claim is used only when no per-request context resolves", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({
    eventsDir: dir,
    projectId: "t/caller3",
    caller: { type: "claimed_agent", runtime: "fixture", identityStrength: "declared" },
  });
  const wrapped = am.wrapTool("t", async () => ({}));
  await wrapped(undefined, { meta: { sessionId: "sess-x" } });
  const lines = await drain(am, dir);
  const started = lines.find((l) => l.observation_type === "attempt_started");
  assert.equal(started.caller.runtime, "fixture");
});
