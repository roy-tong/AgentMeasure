#!/usr/bin/env python3
"""AgentMeasure SSE usage conformance runner (SSE-001).

Pins the Anthropic Messages stream shape from issue #24: prompt-side usage
(input and cache buckets) arrives on message_start, and the final
message_delta carries the cumulative output count. A gateway that reads only
message_delta drops the input bucket.

Usage: python3 conformance/runners/run_sse_usage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VECTORS_DIR = ROOT / "conformance" / "vectors"

PASS, FAIL = "PASS", "FAIL"

INPUT_BUCKET_CHECK = "anthropic_message_start_input_bucket"
OUTPUT_BUCKET_CHECK = "anthropic_message_delta_output_bucket"

# Prompt-side fields live on message_start. They are not summed with anything
# on message_delta. output_tokens on message_start is a partial count; the
# final message_delta value replaces it.
_PROMPT_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_sse(transcript: str) -> list[dict]:
    """Parse a minimal SSE transcript into {event, data} records.

    `data` is the JSON object. The event name prefers the SSE `event:` line
    and falls back to the payload `type`.
    """
    events: list[dict] = []
    event_name = None
    data_lines: list[str] = []

    def flush() -> None:
        nonlocal event_name, data_lines
        if event_name is None and not data_lines:
            return
        raw = "\n".join(data_lines).strip()
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            raise ValueError("SSE data payload must be a JSON object")
        name = event_name or payload.get("type")
        if not isinstance(name, str) or not name:
            raise ValueError("SSE event has no event name")
        events.append({"event": name, "data": payload})
        event_name = None
        data_lines = []

    for line in transcript.splitlines():
        if line.endswith("\r"):
            line = line[:-1]
        if line == "":
            flush()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())
            continue
        raise ValueError(f"unexpected SSE line: {line!r}")
    flush()
    return events


def _message_start_usage(events: list[dict]) -> dict | None:
    for event in events:
        if event["event"] != "message_start":
            continue
        message = event["data"].get("message")
        if not isinstance(message, dict):
            return None
        usage = message.get("usage")
        return usage if isinstance(usage, dict) else None
    return None


def _final_message_delta_usage(events: list[dict]) -> dict | None:
    usage = None
    seen = False
    for event in events:
        if event["event"] != "message_delta":
            continue
        seen = True
        candidate = event["data"].get("usage")
        usage = candidate if isinstance(candidate, dict) else None
    return usage if seen else None


def evaluate(transcript: str) -> dict:
    """Run the named stream-usage checks against one SSE transcript."""
    events = parse_sse(transcript)
    start_usage = _message_start_usage(events)
    delta_usage = _final_message_delta_usage(events)

    input_present = (
        isinstance(start_usage, dict)
        and _is_number(start_usage.get("input_tokens"))
    )
    output_present = (
        isinstance(delta_usage, dict)
        and _is_number(delta_usage.get("output_tokens"))
    )

    checks = {
        INPUT_BUCKET_CHECK: PASS if input_present else FAIL,
        OUTPUT_BUCKET_CHECK: PASS if output_present else FAIL,
    }
    failing = [name for name, status in checks.items() if status == FAIL]
    passing = [name for name, status in checks.items() if status == PASS]

    recovered = {}
    for field in _PROMPT_FIELDS:
        value = start_usage.get(field) if isinstance(start_usage, dict) else None
        recovered[field] = value if _is_number(value) else None
    output = delta_usage.get("output_tokens") if isinstance(delta_usage, dict) else None
    recovered["output_tokens"] = output if _is_number(output) else None

    return {
        "verdict": FAIL if failing else PASS,
        "checks": checks,
        "failing_checks": failing,
        "passing_checks": passing,
        "usage": recovered,
    }


def _check_sse_001(vector: dict) -> bool:
    """Assert the transcript's computed verdict matches the vector."""
    result = evaluate(vector["input"]["sse"])
    exp = vector["expect"]
    if result["verdict"] != exp["verdict"]:
        return False

    for name in exp.get("passing_checks", []):
        if result["checks"].get(name) != PASS:
            return False

    if exp["verdict"] == PASS:
        return (
            not result["failing_checks"]
            and result["usage"] == exp["usage"]
        )

    failing_check = exp.get("failing_check")
    return (
        result["failing_checks"] == [failing_check]
        and failing_check == INPUT_BUCKET_CHECK
        and result["usage"]["input_tokens"] is None
        and isinstance(exp.get("failure_reason"), str)
        and failing_check in exp["failure_reason"]
    )


FAMILY_RUNNERS = {
    "SSE-001": _check_sse_001,
}


def main() -> int:
    vec_files = sorted(VECTORS_DIR.glob("sse-*.json"))
    if not vec_files:
        print(f"  ! no SSE vector files under {VECTORS_DIR}")
        return 1

    failed = 0
    total = 0
    for vec_file in vec_files:
        data = json.loads(vec_file.read_text(encoding="utf-8"))
        for group in data["vectors"]:
            gid = group["id"]
            runner = FAMILY_RUNNERS.get(gid)
            if runner is None:
                print(f"  ! no runner for {gid}")
                continue
            for vector in group.get("vectors", []):
                total += 1
                try:
                    ok = runner(vector)
                except Exception as exc:  # noqa: BLE001 — report and count as a miss
                    ok = False
                    print(f"    error: {exc}")
                if ok:
                    print(f"  ✓ [{gid}] {vector['id']}")
                else:
                    print(f"  ✗ [{gid}] {vector['id']}")
                    failed += 1

    print(
        f"\n{total - failed}/{total} SSE vectors PASS"
        + ("" if failed == 0 else f" ({failed} FAILED)")
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
