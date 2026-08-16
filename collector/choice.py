#!/usr/bin/env python3
"""AUAS Choice 家族指标（Selection Rate / Share of Agent Choice）。

数据来源（Agent runtime routing 层观察）：
  - presented 事件：Tool 进入 Agent 的 decision context（candidate set）
  - selected 事件：Agent/runtime 决定调用该 Tool

指标（AUAS-CORE §4 M2）：
  Selection Rate = Selections ÷ Presented（同 project + tool + 窗口）
  Share of Choice = tool selections ÷ category selections（可替代能力类别）

注意：presented 是选择行为的真实分母（不是 available）。多数 runtime 尚未暴露
routing 层信号——能力矩阵如实声明，指标定义先立，数据面随平台能力扩展。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_DEFAULT = Path(__file__).resolve().parents[1] / "collector.db"


def connect(db_path: Path = DB_DEFAULT) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunities (
            opportunity_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            tool TEXT NOT NULL,
            client_day TEXT NOT NULL,     -- UTC 日（伪匿名 client × 日）
            presented_at TEXT,
            source TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS selections (
            selection_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            tool TEXT NOT NULL,
            client_day TEXT NOT NULL,
            selected_at TEXT,
            source TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_opp ON opportunities(project_id, tool)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sel ON selections(project_id, tool)")
    return conn


def ingest_choice_events(conn, path: Path) -> dict:
    """导入选择事件 JSONL：
      {"type": "presented", "project_id": "...", "tool": "...", "client_key": "...", "ts": "..."}
      {"type": "selected",  "project_id": "...", "tool": "...", "client_key": "...", "ts": "..."}
    """
    presented = selected = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        project = ev.get("project_id")
        tool = ev.get("tool")
        client = ev.get("client_key")
        ts = ev.get("ts")
        if not project or not tool or not client:
            continue
        client_day = f"{str(ts or '')[:10]}|{client}"  # UTC 日 × 伪匿名 client
        if ev.get("type") == "presented":
            conn.execute(
                "INSERT OR IGNORE INTO opportunities (opportunity_id, project_id, tool, client_day, presented_at, source) VALUES (?,?,?,?,?,?)",
                (f"o-{project}-{tool}-{client_day}", project, tool, client_day, ts, ev.get("source")),
            )
            presented += 1
        elif ev.get("type") == "selected":
            conn.execute(
                "INSERT OR IGNORE INTO selections (selection_id, project_id, tool, client_day, selected_at, source) VALUES (?,?,?,?,?,?)",
                (f"s-{project}-{tool}-{client_day}", project, tool, client_day, ts, ev.get("source")),
            )
            selected += 1
    conn.commit()
    return {"presented": presented, "selected": selected}


def selection_metrics(conn, project_id: str, days: int = 30) -> dict:
    """Selection Rate：同 project + tool，窗口内 Selections ÷ Presented。"""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT o.tool,
               COUNT(DISTINCT o.client_day) AS presented,
               COUNT(DISTINCT s.client_day) AS selected
        FROM opportunities o
        LEFT JOIN selections s ON s.project_id = o.project_id
                              AND s.tool = o.tool
                              AND s.client_day = o.client_day
        WHERE o.project_id=? AND o.presented_at>=?
        GROUP BY o.tool
        """,
        (project_id, since),
    ).fetchall()
    metrics = []
    for r in rows:
        presented = r["presented"]
        selected = r["selected"] or 0
        metrics.append({
            "tool": r["tool"],
            "presented_opportunities": presented,
            "selections": selected,
            "selection_rate": round(selected / presented, 3) if presented else 0.0,
        })
    return {"project": project_id, "days": days, "tools": metrics}


def share_of_choice(conn, project_id: str, category_map: dict, days: int = 30) -> dict:
    """Share of Agent Choice：给定 tool → category 映射，计算类别内选择份额。"""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT tool, COUNT(DISTINCT client_day) AS selected
        FROM selections WHERE project_id=? AND selected_at>=?
        GROUP BY tool
        """,
        (project_id, since),
    ).fetchall()
    by_category: dict = {}
    tool_sel = {r["tool"]: r["selected"] for r in rows}
    for tool, category in category_map.items():
        by_category.setdefault(category, 0)
        if tool in tool_sel:
            by_category[category] += tool_sel[tool]
    result = {}
    for tool, category in category_map.items():
        total = by_category.get(category, 0)
        result.setdefault(category, {"total_selections": total, "tools": []})
        result[category]["tools"].append({
            "tool": tool,
            "selections": tool_sel.get(tool, 0),
            "share": round(tool_sel.get(tool, 0) / total, 3) if total else 0.0,
        })
    return result
