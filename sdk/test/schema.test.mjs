import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { AgentMeasure } from "../dist/index.js";
import { REPO_ROOT, makeEventsDir, drain } from "./helpers.mjs";

test("canonical schema: every emitted observation validates (python single source)", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({
    eventsDir: dir,
    projectId: "t/schema",
    usageContext: "synthetic",
    validity: "normal",
  });
  am.emit({
    type: "attempt_started",
    payload: { tool_call_id: "tc-1" },
    operation_id: "op-1",
    task_id: "tk-1",
    retry_of: "op-0",
  });
  am.emit({
    type: "attempt_completed",
    payload: { tool_call_id: "tc-1", outcome: "success" },
    durationMs: 123,
  });
  am.emit({ type: "result_consumed", payload: { tool_call_id: "tc-1" } });
  const lines = await drain(am, dir);
  assert.equal(lines.length, 3);

  // lineage is snake_case in the payload (per payload schemas)
  const started = lines.find((l) => l.observation_type === "attempt_started");
  assert.equal(started.payload.operation_id, "op-1");
  assert.equal(started.payload.task_id, "tk-1");
  assert.equal(started.payload.retry_of, "op-0");
  assert.equal("operationId" in started.payload, false);
  assert.equal("taskId" in started.payload, false);
  assert.equal("retryOf" in started.payload, false);

  // usage context labeled from config with its evidence source
  assert.equal(started.usage_context, "synthetic");
  assert.equal(started.context_source, "provider_configuration");
  assert.equal(started.validity, "normal");
  assert.equal(started.validity_source, "none"); // SDK never derives validity

  const file = join(dir, "agentmeasure-events.jsonl");
  const r = spawnSync(
    "python3",
    [join(REPO_ROOT, "schemas", "validate_jsonl.py"), file],
    { encoding: "utf8" },
  );
  assert.equal(r.status, 0, r.stdout + r.stderr);
});

test("defaults: observe first — usage_context/validity unknown, sources none", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/defaults" });
  am.emit({ type: "attempt_started", payload: { tool_call_id: "tc-1" } });
  const [env] = await drain(am, dir);
  assert.equal(env.usage_context, "unknown");
  assert.equal(env.validity, "unknown");
  assert.equal(env.context_source, "none");
  assert.equal(env.validity_source, "none");
  assert.equal(env.caller.type, "unknown");
  assert.equal(env.caller.identity_strength, "unknown");
});
