import test from "node:test";
import assert from "node:assert/strict";
import { AgentMeasure } from "../dist/index.js";
import { makeEventsDir, readEvents } from "./helpers.mjs";

test("concurrency: 2000 parallel calls → 4000 observations, zero loss, queue drained", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/conc", flushIntervalMs: 10 });
  const wrapped = am.wrapTool("t", async () => ({}));
  await Promise.all(
    Array.from({ length: 2000 }, (_, i) => wrapped(i)),
  );
  await am.shutdown();
  const lines = readEvents(dir);
  assert.equal(lines.length, 4000);
  assert.equal(am.bufferHealth.droppedTotal, 0);
  assert.equal(am.bufferHealth.flushFailures, 0);
  assert.equal(am.bufferHealth.queueDepth, 0);
  assert.equal(am.bufferHealth.flushedTotal, 4000);
  // pairing: every started call has exactly one completed with the same id
  const ids = lines.map((l) => l.payload.tool_call_id);
  assert.equal(new Set(ids).size, 2000);
});

test("concurrency: sequence numbers are monotonic across flushes", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/seq", flushIntervalMs: 1 });
  const wrapped = am.wrapTool("t", async () => ({}));
  await Promise.all(Array.from({ length: 500 }, (_, i) => wrapped(i)));
  await am.shutdown();
  const lines = readEvents(dir);
  const seqs = lines.map((l) => l.collection_health.source_sequence);
  const sorted = [...seqs].sort((a, b) => a - b);
  assert.deepEqual(seqs, sorted, "sequence must be written in order");
});
