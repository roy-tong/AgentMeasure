#!/usr/bin/env python3
"""AUAS Choice 家族（Draft 0.3：Grain = Decision Opportunity）。

对象模型（AUAS-CORE §2.1）：
  Decision Opportunity（decision_id）→ Candidate Set（candidate_set_id）
  → Tool Presentation（presentation_id）→ Selection（selection_id）

计数纪律：presentation 按 decision 计（同 decision 同 tool 只计 1）；
Agent 一天看到 Exa 10 次选 1 次 = 10 presentations / 1 selection = 10%。

指标（AUAS-METRICS M2）：
  M2.1 Presented Opportunities
  M2.2 Selection Rate = Selected decisions ÷ Presented decisions
  M2.5 Conditional Choice Share = A/(A+B)（仅 A、B 同台竞争的 decisions）
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
        CREATE TABLE IF NOT EXISTS presentations (
            decision_id TEXT NOT NULL,
            candidate_set_id TEXT,
            project_id TEXT NOT NULL,
            tool TEXT NOT NULL,
            choice_mode TEXT,
            presented_at TEXT,
            context TEXT,
            validity TEXT,
            UNIQUE(decision_id, tool)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS selections (
            decision_id TEXT NOT NULL,
            candidate_set_id TEXT,
            project_id TEXT NOT NULL,
            tool TEXT NOT NULL,
            rank INTEGER,
            choice_mode TEXT,
            selected_at TEXT,
            context TEXT,
            validity TEXT,
            UNIQUE(decision_id, tool)
        )
        """
    )
    return conn


def ingest_choice_events(conn, path: Path) -> dict:
    """导入选择事件 JSONL（Draft 0.3 载荷）：
      {"type":"presented","decision_id":"d1","candidate_set_id":"c1","project_id":"p",
       "tool":"Exa","choice_mode":"exclusive","ts":"...","context":"production","validity":"normal"}
      {"type":"selected","decision_id":"d1","candidate_set_id":"c1","project_id":"p",
       "tool":"Exa","rank":1,"choice_mode":"exclusive","ts":"...","context":"production","validity":"normal"}
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
        decision = ev.get("decision_id")
        tool = ev.get("tool")
        project = ev.get("project_id")
        if not decision or not tool or not project:
            continue
        common = (decision, ev.get("candidate_set_id"), project, tool,
                  ev.get("choice_mode"), ev.get("ts"), ev.get("context"), ev.get("validity"))
        if ev.get("type") == "presented":
            conn.execute(
                """INSERT OR IGNORE INTO presentations
                   (decision_id, candidate_set_id, project_id, tool, choice_mode,
                    presented_at, context, validity) VALUES (?,?,?,?,?,?,?,?)""",
                common,
            )
            presented += 1
        elif ev.get("type") == "selected":
            conn.execute(
                """INSERT OR IGNORE INTO selections
                   (decision_id, candidate_set_id, project_id, tool, rank, choice_mode,
                    selected_at, context, validity) VALUES (?,?,?,?,?,?,?,?,?)""",
                (decision, ev.get("candidate_set_id"), project, tool,
                 ev.get("rank"), ev.get("choice_mode"), ev.get("ts"),
                 ev.get("context"), ev.get("validity")),
            )
            selected += 1
    conn.commit()
    return {"presented": presented, "selected": selected}


def _strict_filter(prefix: str, extra: str = "") -> str:
    return f" AND {prefix}.context='production' AND {prefix}.validity='normal' " + extra


def selection_metrics(conn, project_id: str, days: int = 30) -> dict:
    """M2.1/M2.2：Presented Opportunities 与 Selection Rate（Grain = decision）。"""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        f"""
        SELECT p.tool,
               COUNT(DISTINCT p.decision_id) AS presented_decisions,
               COUNT(DISTINCT s.decision_id) AS selected_decisions
        FROM presentations p
        LEFT JOIN selections s ON s.decision_id = p.decision_id AND s.tool = p.tool
        WHERE p.project_id=? AND p.presented_at>=? {_strict_filter('p')}
        GROUP BY p.tool
        """,
        (project_id, since),
    ).fetchall()
    tools = []
    for r in rows:
        presented = r["presented_decisions"]
        selected = r["selected_decisions"] or 0
        tools.append({
            "tool": r["tool"],
            "presented_opportunities": presented,
            "selections": selected,
            "selection_rate": round(selected / presented, 3) if presented else 0.0,
        })
    return {"project": project_id, "days": days, "grain": "decision-opportunity", "tools": tools}


def conditional_choice_share(conn, project_id: str, tool_a: str, tool_b: str, days: int = 30) -> dict:
    """M2.5：A、B 同台竞争时的选择份额（同 candidate_set + 同 decision）。"""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    both = conn.execute(
        f"""
        SELECT COUNT(DISTINCT p1.decision_id) AS n
        FROM presentations p1
        JOIN presentations p2 ON p2.decision_id = p1.decision_id
        WHERE p1.project_id=? AND p1.tool=? AND p2.tool=?
          AND p1.presented_at>=? AND p2.presented_at>=? {_strict_filter('p1')}
        """,
        (project_id, tool_a, tool_b, since, since),
    ).fetchone()["n"]
    sel_a = conn.execute(
        f"""
        SELECT COUNT(DISTINCT s.decision_id) AS n FROM selections s
        JOIN presentations p1 ON p1.decision_id = s.decision_id AND p1.tool = s.tool
        JOIN presentations p2 ON p2.decision_id = s.decision_id AND p2.tool = ?
        WHERE s.project_id=? AND s.tool=? AND p1.tool=?
          AND s.selected_at>=? {_strict_filter('s')}
        """,
        (tool_b, project_id, tool_a, tool_a, since),
    ).fetchone()["n"]
    sel_b = conn.execute(
        f"""
        SELECT COUNT(DISTINCT s.decision_id) AS n FROM selections s
        JOIN presentations p1 ON p1.decision_id = s.decision_id AND p1.tool = s.tool
        JOIN presentations p2 ON p2.decision_id = s.decision_id AND p2.tool = ?
        WHERE s.project_id=? AND s.tool=? AND p1.tool=?
          AND s.selected_at>=? {_strict_filter('s')}
        """,
        (tool_a, project_id, tool_b, tool_b, since),
    ).fetchone()["n"]
    total = sel_a + sel_b
    return {
        "tool_a": tool_a, "tool_b": tool_b,
        "co_presented_decisions": both,
        "a_selected": sel_a, "b_selected": sel_b,
        "conditional_choice_share_a": round(sel_a / total, 3) if total else 0.0,
    }
