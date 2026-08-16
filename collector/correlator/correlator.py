#!/usr/bin/env python3
"""agent-used collector — correlator（双边关联 → E2 corroborated usage）。

匹配规则（spec/evidence-model.md §2 E2）：
  1. 相同 trace_id（MCP _meta trace context 传播）
  2. tool 标识一致（归一后）
  3. 时间窗内（默认 ±5 分钟）
  4. 两侧 observer 不同（client ≠ server）

关联成功 → 生成 E2 关联记录；双侧原始事件保留（可审计）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_DEFAULT = Path(__file__).resolve().parents[1] / "collector.db"
WINDOW_SECONDS = 300


def connect(db_path: Path = DB_DEFAULT) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS unified_events (
            event_id TEXT PRIMARY KEY,
            occurred_at TEXT,
            project_id TEXT,
            observer_side TEXT,
            agent_host TEXT,
            provenance TEXT,
            evidence_level TEXT,
            session_id TEXT,
            tool TEXT,
            stage TEXT,
            outcome TEXT,
            duration_bucket TEXT,
            trace_id TEXT,
            tool_use_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS correlations (
            correlation_id TEXT PRIMARY KEY,
            trace_id TEXT,
            client_event_id TEXT,
            server_event_id TEXT,
            tool TEXT,
            project_id TEXT,
            correlated_at TEXT,
            UNIQUE(trace_id, client_event_id, server_event_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_trace ON unified_events(trace_id)")
    return conn


def store_event(conn, rec: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO unified_events
        (event_id, occurred_at, project_id, observer_side, agent_host, provenance,
         evidence_level, session_id, tool, stage, outcome, duration_bucket,
         trace_id, tool_use_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            rec["event_id"], rec.get("occurred_at"), rec.get("project_id"),
            rec.get("observer_side"), rec.get("agent_host"), rec.get("provenance"),
            rec.get("evidence_level"), rec.get("session_id"), rec.get("tool"),
            rec.get("stage"), rec.get("outcome"), rec.get("duration_bucket"),
            rec.get("trace_id"), rec.get("tool_use_id"),
        ),
    )


def _parse_ts(value) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def correlate(conn, window_seconds: int = WINDOW_SECONDS) -> dict:
    """扫描未关联事件，按 trace_id 配对 client/server → E2。"""
    created = 0
    rows = conn.execute(
        "SELECT * FROM unified_events WHERE trace_id IS NOT NULL AND trace_id != ''"
    ).fetchall()
    by_trace: dict = {}
    for row in rows:
        by_trace.setdefault(row["trace_id"], []).append(row)

    for trace_id, evs in by_trace.items():
        clients = [e for e in evs if e["observer_side"] == "client"]
        servers = [e for e in evs if e["observer_side"] == "server"]
        if not clients or not servers:
            continue
        for c in clients:
            for s in servers:
                if c["tool"] != s["tool"]:
                    continue
                if abs((_parse_ts(c["occurred_at"]) - _parse_ts(s["occurred_at"])).total_seconds()) > window_seconds:
                    continue
                # 检查是否已关联
                exists = conn.execute(
                    "SELECT 1 FROM correlations WHERE trace_id=? AND client_event_id=? AND server_event_id=?",
                    (trace_id, c["event_id"], s["event_id"]),
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO correlations
                    (correlation_id, trace_id, client_event_id, server_event_id,
                     tool, project_id, correlated_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()), trace_id, c["event_id"], s["event_id"],
                        c["tool"], c["project_id"] or s["project_id"],
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                # 双侧事件升级为 E2
                for eid in (c["event_id"], s["event_id"]):
                    conn.execute(
                        "UPDATE unified_events SET evidence_level='E2' WHERE event_id=?",
                        (eid,),
                    )
                created += 1
    conn.commit()
    return {"correlations_created": created}


def ingest_jsonl(conn, path: Path, source: str, project_id: str) -> dict:
    """导入 adapter 事件并做归一化（normalizer 内联，避免循环依赖）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from collector.normalizer.normalizer import normalize_record  # noqa: E402

    accepted = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            rec = normalize_record(raw, source, project_id)
        except Exception:
            continue
        store_event(conn, rec)
        accepted += 1
    conn.commit()
    return {"accepted": accepted}
