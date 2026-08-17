import test from "node:test";
import assert from "node:assert/strict";
import { AgentMeasure } from "../dist/index.js";
import { makeEventsDir, drain } from "./helpers.mjs";

test("lineage: camelCase aliases map to snake_case payload fields", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/lineage" });
  am.emit({
    type: "attempt_started",
    payload: { tool_call_id: "t" },
    operationId: "op-a",
    taskId: "tk-a",
    retryOf: "op-b",
  });
  const [env] = await drain(am, dir);
  assert.equal(env.payload.operation_id, "op-a");
  assert.equal(env.payload.task_id, "tk-a");
  assert.equal(env.payload.retry_of, "op-b");
  assert.equal(Object.keys(env.payload).includes("operationId"), false);
  assert.equal(Object.keys(env.payload).includes("taskId"), false);
  assert.equal(Object.keys(env.payload).includes("retryOf"), false);
});

test("lineage: snake_case input passes through untouched", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/lineage2" });
  am.emit({
    type: "attempt_started",
    payload: { tool_call_id: "t" },
    operation_id: "op-z",
  });
  const [env] = await drain(am, dir);
  assert.equal(env.payload.operation_id, "op-z");
});

test("lineage: no lineage fields when none provided", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/lineage3" });
  am.emit({ type: "attempt_started", payload: { tool_call_id: "t" } });
  const [env] = await drain(am, dir);
  assert.equal("operation_id" in env.payload, false);
  assert.equal("task_id" in env.payload, false);
  assert.equal("retry_of" in env.payload, false);
});

test("lineage: duration_ms is rounded and integer", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/lineage4" });
  am.emit({ type: "attempt_completed", payload: { tool_call_id: "t", outcome: "success" }, durationMs: 1234.56 });
  const [env] = await drain(am, dir);
  assert.equal(env.payload.duration_ms, 1235);
});
