import test from "node:test";
import assert from "node:assert/strict";
import { chmodSync } from "node:fs";
import { AgentMeasure } from "../dist/index.js";
import { makeEventsDir, readEvents } from "./helpers.mjs";

test("fail-open: emit never throws, even when the spool is unwritable", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/failopen", flushIntervalMs: 60_000 });
  am.emit({ type: "attempt_started", payload: { tool_call_id: "x" } });
  chmodSync(dir, 0o500); // remove write permission
  am.emit({ type: "attempt_completed", payload: { tool_call_id: "x", outcome: "success" } });
  // flush fails internally; never throws into the caller
  await am.flush();
  assert.equal(am.bufferHealth.flushFailures >= 1, true);
  assert.equal(am.bufferHealth.droppedTotal, 0); // nothing lost — re-enqueued
  chmodSync(dir, 0o700);
  await am.flush(); // retry succeeds
  const lines = readEvents(dir);
  assert.equal(lines.length, 2);
  assert.equal(am.bufferHealth.droppedTotal, 0);
});

test("fail-open: handler errors propagate; failure attempt is observed", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/failopen2", flushIntervalMs: 60_000 });
  const wrapped = am.wrapTool("boom", async () => {
    throw new Error("business failure");
  });
  await assert.rejects(wrapped());
  await am.shutdown();
  const lines = readEvents(dir);
  assert.equal(lines.length, 2);
  assert.equal(lines[0].observation_type, "attempt_started");
  assert.equal(lines[1].observation_type, "attempt_completed");
  assert.equal(lines[1].payload.outcome, "failure");
  assert.equal(lines[1].payload.duration_ms !== undefined, true);
});

test("fail-open: isError metadata marks failure without reading content", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/failopen3", flushIntervalMs: 60_000 });
  const wrapped = am.wrapTool("t", async () => ({ content: "SECRET", isError: true }));
  const result = await wrapped();
  assert.equal(result.isError, true);
  await am.shutdown();
  const lines = readEvents(dir);
  assert.equal(lines[1].payload.outcome, "failure");
  assert.equal(JSON.stringify(lines).includes("SECRET"), false);
});
