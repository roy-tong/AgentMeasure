#!/usr/bin/env python3
"""agent-used collector — consumption chain（S4 Result Consumed 检测）。

Claude Code 是 S4 的第一个实证平台（docs/adapters.md）：
  - claude_code.tool_result span：{tool_name, tool_use_id, success, duration_ms}
  - API request telemetry：在实际消费了某个 MCP tool result 时才带
    {mcp_server.name, mcp_tool.name}

消费链：
  tool_result (tool_use_id=X, mcp_tool.name=search)
        ↓
  下一次模型 request (mcp_tool.name=search)      ← 属性存在 = 该结果被消费
        ↓
  consumed link: {tool_use_id, consumed_at}

本模块实现消费链检测，fixture 可测（不依赖真实 Claude runtime）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.correlator.correlator import connect  # noqa: E402


def create_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consumption_links (
            tool_use_id TEXT NOT NULL,
            project_id TEXT,
            tool TEXT,
            consumed_at TEXT,
            request_seq INTEGER,
            UNIQUE(tool_use_id)
        )
        """
    )


def ingest_consumption_events(conn, path: Path, project_id: str) -> dict:
    """导入消费信号 JSONL（两条事件类型）：
      {"type": "tool_result", "tool_use_id": "X", "tool": "foo.search", "ts": "..."}
      {"type": "request", "mcp_tool": "foo.search", "ts": "...", "seq": 12}
    规则：request 出现 mcp_tool 属性 = 该 tool 的结果被本次请求消费。
    同一 tool_use_id 只记一次消费（UNIQUE）。
    """
    create_tables(conn)
    pending: dict = {}  # tool -> tool_use_id（最近的未消费结果）
    consumed = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "tool_result":
            tool_use_id = str(ev.get("tool_use_id") or "")
            tool = str(ev.get("tool") or "unknown")
            if tool_use_id:
                pending[tool] = tool_use_id  # 最近结果
        elif ev.get("type") == "request" and ev.get("mcp_tool"):
            tool = str(ev["mcp_tool"])
            tool_use_id = pending.pop(tool, None)
            if tool_use_id:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO consumption_links
                    (tool_use_id, project_id, tool, consumed_at, request_seq)
                    VALUES (?,?,?,?,?)
                    """,
                    (tool_use_id, project_id, tool,
                     str(ev.get("ts") or ""), ev.get("seq")),
                )
                consumed += 1
    conn.commit()
    return {"consumption_links": consumed}


def consumed_rate(conn, project_id: str, days: int = 30) -> dict:
    """S4 rate：consumed links / 同 project 的 eligible invocations。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM consumption_links WHERE project_id=?",
        (project_id,),
    ).fetchone()
    consumed = row[0] or 0
    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations WHERE project_id=? AND eligible=1
        """,
        (project_id,),
    ).fetchone()
    invocations = row[0] or 0
    return {
        "consumed_results": consumed,
        "eligible_invocations": invocations,
        "consumed_rate": round(consumed / invocations, 3) if invocations else 0.0,
    }
