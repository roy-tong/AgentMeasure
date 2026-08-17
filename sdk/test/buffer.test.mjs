import test from "node:test";
import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { AgentMeasure } from "../dist/index.js";
import { makeEventsDir, readEvents } from "./helpers.mjs";

test("buffer: limit enforced with explicit drop accounting", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({
    eventsDir: dir,
    projectId: "t/buf",
    flushIntervalMs: 60_000, // no background flush during the test
    bufferLimit: 5,
  });
  for (let i = 0; i < 5; i++) {
    am.emit({ type: "attempt_started", payload: { tool_call_id: `t${i}` } });
  }
  await am.flush(); // write the first 5; droppedSinceLastFlush resets
  assert.equal(am.bufferHealth.flushedTotal, 5);

  for (let i = 5; i < 15; i++) {
    am.emit({ type: "attempt_started", payload: { tool_call_id: `t${i}` } });
  }
  assert.equal(am.bufferHealth.queueDepth, 5);
  assert.equal(am.bufferHealth.droppedTotal, 5);

  await am.shutdown();
  const lines = readEvents(dir);
  assert.equal(lines.length, 10);
  assert.equal(lines[0].payload.tool_call_id, "t0"); // oldest kept, order preserved
  // envelopes built after the drops carry the loss accounting snapshot
  const last = lines[lines.length - 1];
  assert.equal(last.collection_health.buffer_overflow, true);
  assert.equal(last.collection_health.dropped_since_last_report, 5);
});

test("buffer: rotating spool files stay bounded", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({
    eventsDir: dir,
    projectId: "t/rot",
    flushIntervalMs: 60_000,
    maxSpoolBytes: 300,
    maxSpoolFiles: 3,
  });
  for (let i = 0; i < 30; i++) {
    am.emit({ type: "attempt_started", payload: { tool_call_id: `t${i}` } });
  }
  await am.flush(); // first flush writes the active file
  for (let i = 30; i < 60; i++) {
    am.emit({ type: "attempt_started", payload: { tool_call_id: `t${i}` } });
  }
  await am.flush(); // second flush exceeds maxSpoolBytes → rotation
  await am.shutdown();
  assert.equal(am.bufferHealth.rotatedFiles >= 1, true);
  const files = readdirSync(dir).filter(
    (n) => n.startsWith("agentmeasure-events") && n.endsWith(".jsonl"),
  );
  assert.equal(files.length <= 4, true, `files: ${files.join(", ")}`); // active + maxSpoolFiles
  const all = files.flatMap((f) => readEvents(dir, f));
  assert.equal(all.length, 60); // nothing lost across rotations
});

test("buffer: doNotTrack disables recording entirely", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/notrack", doNotTrack: true });
  am.emit({ type: "attempt_started", payload: { tool_call_id: "x" } });
  await am.shutdown();
  assert.equal(am.bufferHealth.queueDepth, 0);
  assert.equal(am.bufferHealth.exists, false);
});
