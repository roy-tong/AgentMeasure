import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { SDK_ROOT, makeEventsDir, readEvents } from "./helpers.mjs";

function runExample(name, dir) {
  return spawnSync("node", [join("examples", name)], {
    cwd: SDK_ROOT,
    encoding: "utf8",
    timeout: 180_000,
    env: { ...process.env, AGENTMEASURE_EVENTS_DIR: dir },
  });
}

function assertFixture(r, dir, label) {
  assert.equal(r.status, 0, `${label} failed:\n${r.stdout}\n${r.stderr}`);
  const lines = readEvents(dir);
  // 42 calls → exactly 84 observations; no invented result_consumed
  assert.equal(lines.length, 84, `${label}: expected 84 observations`);

  const types = new Set(lines.map((l) => l.observation_type));
  assert.deepEqual(
    [...types].sort(),
    ["attempt_completed", "attempt_started"],
    `${label}: provider side must not fabricate unobservable events`,
  );

  const started = lines.filter((l) => l.observation_type === "attempt_started");
  const completed = lines.filter((l) => l.observation_type === "attempt_completed");
  assert.equal(new Set(started.map((l) => l.payload.tool_call_id)).size, 42);
  assert.deepEqual(
    completed.map((l) => l.payload.tool_call_id).sort(),
    started.map((l) => l.payload.tool_call_id).sort(),
    `${label}: every attempt pair must share the call id`,
  );

  // caller claims per runtime: 14 claude (declared) / 14 codex (declared) / 14 unknown
  const byRuntime = {};
  for (const l of started) {
    byRuntime[l.caller.runtime] = (byRuntime[l.caller.runtime] ?? 0) + 1;
  }
  assert.deepEqual(byRuntime, { claude: 14, codex: 14, unknown: 14 }, `${label}: caller claims`);

  // fixture is labeled synthetic at the source — never production
  assert.equal(started.every((l) => l.usage_context === "synthetic"), true);
  assert.equal(started.every((l) => l.context_source === "provider_configuration"), true);
}

test("mcp-integration (v1 path): 42 calls → 84 canonical observations, per-request callers", () => {
  const dir = makeEventsDir();
  const r = runExample("mcp-integration.js", dir);
  assertFixture(r, dir, "v1");
});

test("mcp-integration-v2 (v2 path): same contract on the @modelcontextprotocol/server API", () => {
  const dir = makeEventsDir();
  const r = runExample("mcp-integration-v2.js", dir);
  assertFixture(r, dir, "v2");
});
