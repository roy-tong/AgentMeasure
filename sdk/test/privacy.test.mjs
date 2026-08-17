import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { AgentMeasure, fingerprint } from "../dist/index.js";
import { makeEventsDir } from "./helpers.mjs";

test("privacy: secrets in arguments and results never reach the spool", async () => {
  const dir = makeEventsDir();
  const am = new AgentMeasure({ eventsDir: dir, projectId: "t/privacy", flushIntervalMs: 60_000 });
  const wrapped = am.wrapTool("search", async ({ q }) => ({
    results: [`result-for-${q}`],
    raw: "SECRET_RESULT_456",
  }));
  await wrapped({ q: "SUPER_SECRET_123", token: "TOKEN_789" });
  await am.shutdown();
  const raw = readFileSync(join(dir, "agentmeasure-events.jsonl"), "utf8");
  assert.equal(raw.includes("SUPER_SECRET_123"), false);
  assert.equal(raw.includes("SECRET_RESULT_456"), false);
  assert.equal(raw.includes("TOKEN_789"), false);
  // observations themselves exist (fingerprinted ids, never raw)
  assert.equal(raw.includes('"observation_type"'), true);
});

test("privacy: fingerprint is a content-free digest", () => {
  const a = fingerprint("RAW-SESSION-42");
  const b = fingerprint("RAW-SESSION-42");
  assert.equal(a, b);
  assert.equal(a.startsWith("p-"), true);
  assert.equal(a.includes("RAW-SESSION"), false);
  assert.notEqual(a, "RAW-SESSION-42");
});
