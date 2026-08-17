import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

export const SDK_ROOT = fileURLToPath(new URL("..", import.meta.url));
export const REPO_ROOT = fileURLToPath(new URL("../../", import.meta.url));

export function makeEventsDir() {
  return mkdtempSync(join(tmpdir(), "am-sdk-test-"));
}

export function readEvents(dir, file = "agentmeasure-events.jsonl") {
  const p = join(dir, file);
  return readFileSync(p, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l));
}

export async function drain(am, dir) {
  await am.shutdown();
  return readEvents(dir);
}
