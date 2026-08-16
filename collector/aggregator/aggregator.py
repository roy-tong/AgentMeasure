#!/usr/bin/env python3
"""agent-used — 聚合引擎（M1 骨架，零依赖 stdlib）。

职责:
  import    从本地 JSONL 导入事件（wrapper 产出）
  serve     本地 HTTP 服务：POST /v1/events、GET /v1/stats、GET /badge
  验签      事件带 signature 时按 key_id 校验 HMAC（防伪造）

用法:
  python3 aggregator.py import --events ~/.agent-used/events/agent-use-events.jsonl
  python3 aggregator.py serve --port 8787
  python3 aggregator.py seed-demo   # 造 30 天演示数据（验证徽章用）

隐私: 只存事件元数据（无内容）；DO_NOT_TRACK 事件跳过。
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "agent-used.db"
KEYS: dict = {}  # key_id -> secret（生产环境应换为公钥验签，key_id -> public key）


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            occurred_at TEXT NOT NULL,
            target TEXT NOT NULL,
            surface TEXT NOT NULL,
            tool TEXT NOT NULL,
            outcome TEXT NOT NULL,
            duration_bucket TEXT,
            agent_host TEXT,
            signature TEXT,
            key_id TEXT,
            ingested_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_target_day ON events(target, occurred_at)")
    return conn


def _canonical(ev: dict) -> str:
    return json.dumps(
        {k: ev[k] for k in ("event_id", "occurred_at", "target", "surface", "tool", "outcome")},
        sort_keys=True, separators=(",", ":"),
    )


def verify_signature(ev: dict) -> bool:
    """无签名事件视为本地导入（信任），有签名则必须验签通过。"""
    sig = ev.get("signature")
    if not sig:
        return True
    secret = KEYS.get(ev.get("key_id", ""))
    if not secret:
        return False  # 未知 key：拒绝
    expect = hmac.new(secret.encode(), _canonical(ev).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expect, sig)


def ingest_event(conn, ev: dict) -> bool:
    if ev.get("telemetry_mode") != "local" and ev.get("telemetry_mode") != "opted-in":
        return False
    if not verify_signature(ev):
        return False
    conn.execute(
        """
        INSERT OR IGNORE INTO events
        (event_id, occurred_at, target, surface, tool, outcome, duration_bucket,
         agent_host, signature, key_id, ingested_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            ev["event_id"], ev.get("occurred_at", ""), ev["target"], ev.get("surface", "mcp"),
            ev.get("tool", "unknown"), ev.get("outcome", "success"),
            ev.get("duration_bucket"), ev.get("agent_host", "unknown"),
            ev.get("signature"), ev.get("key_id"), datetime.now(timezone.utc).isoformat(),
        ),
    )
    return True


def stats(conn, target: str, days: int = 30) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        """
        SELECT COUNT(*), SUM(outcome='success'), COUNT(DISTINCT agent_host)
        FROM events WHERE target=? AND occurred_at >= ?
        """,
        (target, since),
    ).fetchone()
    total, success, hosts = row
    by_tool = conn.execute(
        """
        SELECT tool, COUNT(*) FROM events WHERE target=? AND occurred_at >= ?
        GROUP BY tool ORDER BY 2 DESC LIMIT 10
        """,
        (target, since),
    ).fetchall()
    by_day = conn.execute(
        """
        SELECT substr(occurred_at,1,10) AS d, COUNT(*) FROM events
        WHERE target=? AND occurred_at >= ? GROUP BY d ORDER BY d
        """,
        (target, since),
    ).fetchall()
    return {
        "target": target,
        "days": days,
        "calls": total or 0,
        "success_rate": round(success / total, 3) if total else 0.0,
        "agent_hosts": hosts or 0,
        "by_tool": [{"tool": t, "calls": c} for t, c in by_tool],
        "by_day": [{"date": d, "calls": c} for d, c in by_day],
    }


def badge_svg(s: dict) -> str:
    calls = s["calls"]
    label = f"agent calls {calls:,}/mo"
    # shields.io 风格两段徽章
    lw = 118
    rw = max(110, 60 + len(label) * 7)
    w = lw + rw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="agent-used: {label}">
  <title>agent-used: {label}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw}" height="20" fill="#555"/>
    <rect x="{lw}" width="{rw}" height="20" fill="#176b5a"/>
    <rect width="{w}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{lw/2}" y="14">agent-used</text>
    <text x="{lw + rw/2}" y="14">{label}</text>
  </g>
</svg>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path
        if path.startswith("/v1/stats/"):
            parts = path.split("/")
            if len(parts) >= 5:
                target = f"github.com/{parts[3]}/{parts[4]}"
                days = 30
                conn = db()
                self._json(200, stats(conn, target, days))
                return
        if path.startswith("/badge/"):
            parts = path.split("/")
            if len(parts) >= 4:
                target = f"github.com/{parts[2]}/{parts[3]}"
                conn = db()
                svg = badge_svg(stats(conn, target, 30))
                body = svg.encode()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/events":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"[]")
        except Exception as exc:
            self._json(400, {"error": str(exc)})
            return
        items = payload if isinstance(payload, list) else [payload]
        conn = db()
        accepted, rejected = 0, 0
        for ev in items:
            if isinstance(ev, dict) and ingest_event(conn, ev):
                accepted += 1
            else:
                rejected += 1
        conn.commit()
        self._json(200, {"accepted": accepted, "rejected": rejected})


def cmd_import(path: str) -> int:
    conn = db()
    accepted, skipped = 0, 0
    for line in Path(path).expanduser().read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if ingest_event(conn, ev):
            accepted += 1
        else:
            skipped += 1
    conn.commit()
    print(f"imported {accepted}, skipped {skipped} (target: {DB_PATH})")
    return 0


def cmd_seed_demo() -> int:
    conn = db()
    base = datetime.now(timezone.utc)
    for day in range(30):
        n = 3 + (day * 7) % 25
        for i in range(n):
            ev = {
                "schema_version": "1.0",
                "event_id": str(uuid.uuid4()),
                "occurred_at": (base - timedelta(days=day, hours=i % 12)).isoformat(),
                "target": "github.com/demo/agent-used-demo",
                "surface": "mcp",
                "tool": ["monitor", "search", "audit"][i % 3],
                "outcome": "success" if i % 10 != 0 else "failure",
                "duration_bucket": "10s-60s",
                "agent_host": ["claude-code", "codex", "cursor"][i % 3],
                "telemetry_mode": "opted-in",
            }
            ingest_event(conn, ev)
    conn.commit()
    print("seeded 30-day demo data for github.com/demo/agent-used-demo")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import")
    imp.add_argument("--events", required=True)
    sub.add_parser("seed-demo")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)

    if args.cmd == "import":
        return cmd_import(args.events)
    if args.cmd == "seed-demo":
        return cmd_seed_demo()
    if args.cmd == "serve":
        # 从环境变量加载 key（生产：AGENT_USED_KEYS='key1=secret1,key2=secret2'）
        for pair in __import__("os").environ.get("AGENT_USED_KEYS", "").split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                KEYS[k.strip()] = v.strip()
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
        print(f"agent-used aggregator on http://127.0.0.1:{args.port}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
