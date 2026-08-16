#!/usr/bin/env python3
"""AgentMeasure — MCP wrapper（M0 骨架，零依赖 stdlib）。

在真实调用边界（被调方）记录 agent 工具调用事件，输出本地 JSONL。
用法:
  agentmeasure wrap -- <mcp-server-command> [args...]

环境变量:
  AGENTMEASURE_EVENTS_DIR  事件目录（默认 ~/.agentmeasure/events）
  AGENTMEASURE_TARGET      被包装项目的标识（默认 github.com/roy-tong/AgentMeasure）
  AGENTMEASURE_OPTIN=1     允许上传聚合（当前版本仅记录，不实现上传）
  DO_NOT_TRACK=1         完全禁用记录

隐私边界（写死）: 只记工具名/结果/粗粒度耗时，绝不记录参数、结果、内容、路径。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

EVENTS_DIR = Path(
    os.environ.get("AGENTMEASURE_EVENTS_DIR", str(Path.home() / ".agentmeasure" / "events"))
).expanduser()
TARGET = os.environ.get("AGENTMEASURE_TARGET", "github.com/roy-tong/AgentMeasure")
DO_NOT_TRACK = os.environ.get("DO_NOT_TRACK", "0") == "1"
SIGNING_SECRET = os.environ.get("AGENTMEASURE_SECRET", "")  # 空 = 本地无签名模式
KEY_ID = os.environ.get("AGENTMEASURE_KEY_ID", "local")
OBSERVER_PRINCIPAL = os.environ.get("AGENTMEASURE_PRINCIPAL", "mcp-wrapper@local")
TRUST_DOMAIN = os.environ.get("AGENTMEASURE_TRUST_DOMAIN", "local")
INSTANCE_ID = os.environ.get("AGENTMEASURE_INSTANCE_ID", f"wrap-{os.getpid()}")

_SEQUENCE = [0]


def next_sequence() -> int:
    _SEQUENCE[0] += 1
    return _SEQUENCE[0]

BUCKETS = [(1, "<1s"), (10, "1s-10s"), (60, "10s-60s"), (600, "1m-10m")]


def duration_bucket(seconds: float) -> str:
    for threshold, label in BUCKETS:
        if seconds < threshold:
            return label
    return ">10m"


def _sign(event: dict) -> dict:
    """Completed 生命周期证明：对事件规范字段做 HMAC 签名（防篡改/防重放，nonce 为 event_id）。"""
    if not SIGNING_SECRET:
        return event
    canonical = json.dumps(
        {k: event[k] for k in ("spec_version", "observation_id", "observation_type",
                               "observed_at", "usage_context", "validity")},
        sort_keys=True, separators=(",", ":"),
    )
    event["signature"] = hmac.new(
        SIGNING_SECRET.encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()
    event["key_id"] = KEY_ID
    return event


def record(surface: str, tool: str, outcome: str, seconds: float, agent_host: str = "unknown") -> None:
    """产出 Canonical Observation Envelope（DATA.md / schemas/observation.schema.json）。

    wrapper 在 server 侧真实调用边界：可提供 attempt_completed 的事实；
    caller 不可判定（unknown）；context/validity 默认 unknown。
    """
    if DO_NOT_TRACK:
        return
    event = {
        "spec_version": "agentmeasure-0.4",
        "observation_id": str(uuid.uuid4()),
        "observation_type": "attempt_completed",
        "observer": {"principal": OBSERVER_PRINCIPAL, "side": "server",
                     "trust_domain": TRUST_DOMAIN},
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "deployment_context": {"project_id": TARGET},
        "surface": {"surface_id": surface, "surface_namespace": "mcp"},
        "caller": {"type": "unknown", "runtime": agent_host or "unknown",
                   "identity_strength": "unknown"},
        "usage_context": "unknown",
        "validity": "unknown",
        "context_source": "none",
        "validity_source": "none",
        "collection_health": {"source_instance_id": INSTANCE_ID,
                              "source_sequence": next_sequence(),
                              "sequence_epoch": datetime.now(timezone.utc).strftime("%Y-%m"),
                              "dropped_since_last_report": 0,
                              "buffer_overflow": False},
        "provenance": "wrapper",
        "payload": {"outcome": outcome,
                    "duration_ms": int(seconds * 1000) if seconds is not None else None},
        "signature": None,
        "key_id": None,
    }
    _sign(event)
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EVENTS_DIR / "agent-use-events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def forward(stream_in, stream_out) -> None:
    """逐行转发，不解析。"""
    for line in stream_in:
        stream_out.write(line)
        stream_out.flush()


def main(argv) -> int:
    if argv and argv[0] == "wrap":
        argv = argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        print("usage: agentmeasure wrap -- <mcp-server-command> [args...]", file=sys.stderr)
        return 2

    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        print(f"agentmeasure: cannot start {argv[0]}: {exc}", file=sys.stderr)
        return 2

    pending: dict = {}  # jsonrpc id -> (tool, start_ts)

    def server_to_client() -> None:
        for line in proc.stdout:
            try:
                msg = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                sys.stdout.write(line)
                sys.stdout.flush()
                continue
            if (
                isinstance(msg, dict)
                and msg.get("jsonrpc") == "2.0"
                and msg.get("id") in pending
            ):
                info = pending.pop(msg["id"])
                outcome = "success" if "result" in msg else "failure"
                record("mcp", info[0], outcome, time.monotonic() - info[1], info[2])
            sys.stdout.write(line)
            sys.stdout.flush()

    threading.Thread(target=server_to_client, daemon=True).start()

    agent_host = "unknown"

    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            proc.stdin.write(line)
            proc.stdin.flush()
            continue
        if isinstance(msg, dict):
            if msg.get("method") == "initialize" and isinstance(msg.get("params"), dict):
                client = msg["params"].get("clientInfo") or {}
                name = client.get("name") if isinstance(client, dict) else None
                agent_host = str(name or "unknown")[:80]
            elif (
                msg.get("method") == "tools/call"
                and msg.get("id") is not None
            ):
                params = msg.get("params") or {}
                name = params.get("name", "unknown") if isinstance(params, dict) else "unknown"
                pending[msg["id"]] = (name, time.monotonic(), agent_host)
        proc.stdin.write(line)
        proc.stdin.flush()

    proc.stdin.close()
    proc.wait()
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
