#!/usr/bin/env python3
"""AgentMeasure Choice 家族（Draft 0.4：Grain = Decision Opportunity）。

对象模型（AgentMeasure-CORE §2.4）：
  Decision Opportunity（decision_id）→ Candidate Set（candidate_set_id）
  → Tool Presentation（presentation_id）→ Selection（selection_id）

三轴（AgentMeasure-CORE §6）：
  Choice Mode（决策结构）× Decision Authority（谁决策）× Selection Constraint（多自由）

计数纪律：presentation 按 decision 计（同 decision 同 tool 只计 1）；
Agent 一天看到 Exa 10 次选 1 次 = 10 presentations / 1 selection = 10%。

指标（AgentMeasure-METRICS M2）：
  M2.1 Presented Opportunities
  M2.2 Observed Selection Rate = Observed Selected ÷ Presented
      （observed ≠ preference：required/forced 的"选择"不是偏好，须按轴披露）
  M2.5 Observed Head-to-Head Choice Share = A/(A+B)
      （观测到的同台竞争份额；preference 声称需满足 authority/constraint 条件）

M2.5 纪律（fail-closed）：
  - 同台竞争 = 同一 decision_id + 同一 candidate_set_id + 同一 choice_mode
    （candidate_set_id 或 choice_mode 缺失的 decision 不计入，防止跨组 ID 碰撞）
  - 两侧呈现与选择都必须 Strict Qualified（context=production, validity=normal）
  - project_id / category_id / choice_mode 作用于呈现面；
    decision_authority / selection_constraint 作用于选择面（三轴见 Core §6）；
    均为可选 scope 过滤；project_id 缺省时跨项目统计
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
            category_id TEXT,
            decision_authority TEXT,
            selection_constraint TEXT,
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
            category_id TEXT,
            decision_authority TEXT,
            selection_constraint TEXT,
            selected_at TEXT,
            context TEXT,
            validity TEXT,
            UNIQUE(decision_id, tool)
        )
        """
    )
    # 旧库迁移：补新列（CREATE TABLE IF NOT EXISTS 不会改已有表）
    extra = {
        "category_id": "TEXT",
        "decision_authority": "TEXT",
        "selection_constraint": "TEXT",
    }
    for table in ("presentations", "selections"):
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for col, ddl in extra.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
    conn.commit()
    return conn


def ingest_choice_events(conn, path: Path) -> dict:
    """导入选择事件 JSONL（Draft 0.4 载荷）：
      {"type":"presented","decision_id":"d1","candidate_set_id":"c1","project_id":"p",
       "tool":"Exa","choice_mode":"exclusive","category_id":"search","ts":"...",
       "context":"production","validity":"normal"}
      {"type":"selected","decision_id":"d1","candidate_set_id":"c1","project_id":"p",
       "tool":"Exa","rank":1,"choice_mode":"exclusive","category_id":"search",
       "decision_authority":"model","selection_constraint":"autonomous","ts":"...",
       "context":"production","validity":"normal"}
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
                  ev.get("choice_mode"), ev.get("category_id"),
                  ev.get("decision_authority"), ev.get("selection_constraint"),
                  ev.get("ts"), ev.get("context"), ev.get("validity"))
        if ev.get("type") == "presented":
            conn.execute(
                """INSERT OR IGNORE INTO presentations
                   (decision_id, candidate_set_id, project_id, tool, choice_mode,
                    category_id, decision_authority, selection_constraint,
                    presented_at, context, validity)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                common,
            )
            presented += 1
        elif ev.get("type") == "selected":
            conn.execute(
                """INSERT OR IGNORE INTO selections
                   (decision_id, candidate_set_id, project_id, tool, rank, choice_mode,
                    category_id, decision_authority, selection_constraint,
                    selected_at, context, validity)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (decision, ev.get("candidate_set_id"), project, tool,
                 ev.get("rank"), ev.get("choice_mode"), ev.get("category_id"),
                 ev.get("decision_authority"), ev.get("selection_constraint"),
                 ev.get("ts"), ev.get("context"), ev.get("validity")),
            )
            selected += 1
    conn.commit()
    return {"presented": presented, "selected": selected}


def _strict_filter(prefix: str, extra: str = "") -> str:
    return f" AND {prefix}.context='production' AND {prefix}.validity='normal' " + extra


def selection_metrics(conn, project_id: str, days: int = 30) -> dict:
    """M2.1/M2.2：Presented Opportunities 与 Observed Selection Rate（Grain = decision）。

    三轴披露：choice_mode / decision_authority / selection_constraint 的分布
    由调用方从原始事件统计；本函数返回工具级聚合（observed ≠ preference）。
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        f"""
        SELECT p.tool,
               COUNT(DISTINCT p.decision_id) AS presented_decisions,
               COUNT(DISTINCT s.decision_id) AS selected_decisions
        FROM presentations p
        LEFT JOIN selections s
          ON s.decision_id = p.decision_id AND s.tool = p.tool
         AND s.candidate_set_id IS p.candidate_set_id
         AND s.project_id = p.project_id
         {_strict_filter('s')}
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
            "observed_selection_rate": round(selected / presented, 3) if presented else 0.0,
        })
    return {"project": project_id, "days": days, "grain": "decision-opportunity", "tools": tools}


def conditional_choice_share(conn, tool_a: str, tool_b: str, project_id=None,
                             days: int = 30, choice_mode=None, category_id=None,
                             decision_authority=None, selection_constraint=None) -> dict:
    """M2.5：A、B 同台竞争时的选择份额 A/(A+B)。

    同台竞争（fail-closed）：同一 decision_id 的同一 candidate_set_id 内，
    A、B 以同一 choice_mode 呈现；任一侧 candidate_set_id / choice_mode 缺失、
    或两侧 context/validity 非 Strict Qualified 的 decision 一律不计。
    project_id 为空时跨项目统计；choice_mode / category_id 作用于呈现面；
    decision_authority / selection_constraint 作用于选择面（三轴见 Core §6）。
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pres_scope = []
    sel_scope = []
    pres_params: list = []
    sel_params: list = []
    if project_id is not None:
        pres_scope.append("AND p1.project_id=? AND p2.project_id=?")
        pres_params += [project_id, project_id]
    if choice_mode is not None:
        pres_scope.append("AND p1.choice_mode=? AND p2.choice_mode=?")
        pres_params += [choice_mode, choice_mode]
    if category_id is not None:
        pres_scope.append("AND p1.category_id=? AND p2.category_id=?")
        pres_params += [category_id, category_id]
    if decision_authority is not None:
        sel_scope.append("AND s.decision_authority=?")
        sel_params.append(decision_authority)
    if selection_constraint is not None:
        sel_scope.append("AND s.selection_constraint=?")
        sel_params.append(selection_constraint)
    pres_sql = " ".join(pres_scope)
    sel_sql = " ".join(sel_scope)

    both = conn.execute(
        f"""
        SELECT COUNT(DISTINCT p1.decision_id) AS n
        FROM presentations p1
        JOIN presentations p2
          ON p2.decision_id = p1.decision_id
         AND p2.candidate_set_id = p1.candidate_set_id
         AND p2.choice_mode = p1.choice_mode
        WHERE p1.tool=? AND p2.tool=?
          AND p1.candidate_set_id IS NOT NULL AND p1.choice_mode IS NOT NULL
          AND p1.presented_at>=? AND p2.presented_at>=?
          {_strict_filter('p1')} {_strict_filter('p2')}
          {pres_sql}
        """,
        [tool_a, tool_b, since, since] + pres_params,
    ).fetchone()["n"]

    def _selected(selected_tool: str, other_tool: str) -> int:
        return conn.execute(
            f"""
            SELECT COUNT(DISTINCT s.decision_id) AS n
            FROM selections s
            JOIN presentations p1
              ON p1.decision_id = s.decision_id AND p1.tool = s.tool
             AND p1.candidate_set_id = s.candidate_set_id
             AND p1.choice_mode = s.choice_mode
             AND p1.project_id = s.project_id
            JOIN presentations p2
              ON p2.decision_id = s.decision_id AND p2.tool = ?
             AND p2.candidate_set_id = s.candidate_set_id
             AND p2.choice_mode = s.choice_mode
             AND p2.project_id = s.project_id
            WHERE s.tool=? AND s.candidate_set_id IS NOT NULL AND s.choice_mode IS NOT NULL
              AND s.selected_at>=?
              AND p1.candidate_set_id IS NOT NULL AND p1.choice_mode IS NOT NULL
              AND p2.candidate_set_id IS NOT NULL AND p2.choice_mode IS NOT NULL
              {_strict_filter('s')} {_strict_filter('p1')} {_strict_filter('p2')}
              {pres_sql} {sel_sql}
            """,
            [other_tool, selected_tool, since] + pres_params + sel_params,
        ).fetchone()["n"]

    sel_a = _selected(tool_a, tool_b)
    sel_b = _selected(tool_b, tool_a)
    total = sel_a + sel_b
    return {
        "tool_a": tool_a, "tool_b": tool_b,
        "scope": {"project_id": project_id, "choice_mode": choice_mode,
                  "category_id": category_id, "decision_authority": decision_authority,
                  "selection_constraint": selection_constraint},
        "days": days,
        "co_presented_decisions": both,
        "a_selected": sel_a, "b_selected": sel_b,
        "conditional_choice_share_a": round(sel_a / total, 3) if total else 0.0,
    }
