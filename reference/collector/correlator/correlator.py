#!/usr/bin/env python3
"""agent-used collector — invocation matcher（观察 → 逻辑调用）。

数据模型（measurement-integrity review）：
  observations        adapter 观察事实（唯一输入）
  invocations         一次逻辑调用（由 observations 推导）
  observation_links   invocation ↔ observation 关联

匹配优先级（spec/evidence-model.md）：
  1. 精确 tool_call_id（同 project + tool）→ 强关联
  2. trace_id + tool + 时间窗 → 强关联（双侧独立观测）
  3. 兜底：无关联键 → 每条 observation 自成 invocation（概率关联不做，宁缺毋假）

时间解析 fail-closed：无法解析的时间戳不参与关联（绝不假设 now）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.usage import OBSERVATION_KEYS  # noqa: E402

DB_DEFAULT = Path(__file__).resolve().parents[2] / "collector.db"
WINDOW_SECONDS = 300


def connect(db_path: Path = DB_DEFAULT) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS observations (
            observation_id TEXT PRIMARY KEY,
            observed_at TEXT,
            observer_principal TEXT,
            observer_side TEXT,
            provenance TEXT,
            project_id TEXT,
            tool TEXT,
            tool_call_id TEXT,
            trace_id TEXT,
            session_key TEXT,
            outcome TEXT,
            duration_bucket TEXT,
            lifecycle_stage TEXT,
            signature TEXT,
            key_id TEXT,
            source_event_id TEXT,
            trust_domain TEXT,
            sampling TEXT,
            usage_context TEXT,
            validity TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invocations (
            invocation_id TEXT PRIMARY KEY,
            project_id TEXT,
            tool TEXT,
            started_at TEXT,
            outcome TEXT,
            lifecycle TEXT,
            evidence TEXT,
            eligible INTEGER DEFAULT 0,
            matched_by TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS observation_links (
            invocation_id TEXT NOT NULL,
            observation_id TEXT NOT NULL,
            UNIQUE(invocation_id, observation_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_callid ON observations(tool_call_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_trace ON observations(trace_id)")
    return conn


def store_observation(conn, obs: dict) -> bool:
    # fail-closed（AUAS-CORE 不变量）：无 observation_id 的观察拒绝入库
    if not obs.get("observation_id"):
        return False
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO observations
            (observation_id, observed_at, observer_principal, observer_side, provenance,
             project_id, tool, tool_call_id, trace_id, session_key, outcome,
             duration_bucket, lifecycle_stage, signature, key_id, source_event_id,
             trust_domain, sampling, usage_context, validity)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            tuple(obs.get(k) for k in OBSERVATION_KEYS),
        )
        return True
    except sqlite3.Error:
        return False


def _parse_ts(value) -> Optional[datetime]:
    """fail-closed：解析失败返回 None，绝不假设当前时间。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _grade(conn, obs_ids: list) -> str:
    from collector.verifier.verifier import grade_invocation

    rows = conn.execute(
        f"SELECT * FROM observations WHERE observation_id IN ({','.join('?' * len(obs_ids))})",
        obs_ids,
    ).fetchall()
    return grade_invocation([dict(r) for r in rows])


def match_invocations(conn, window_seconds: int = WINDOW_SECONDS) -> dict:
    """把未归类的 observations 匹配为 invocations。幂等：已链接的不重复处理。"""
    created = 0
    # 1) 精确 tool_call_id 分组（同 project + tool）
    rows = conn.execute(
        """
        SELECT o.* FROM observations o
        WHERE o.tool_call_id IS NOT NULL AND o.tool_call_id != ''
          AND NOT EXISTS (SELECT 1 FROM observation_links l WHERE l.observation_id = o.observation_id)
        ORDER BY o.observed_at
        """
    ).fetchall()
    groups: dict = {}
    for r in rows:
        key = (r["project_id"], r["tool"], r["tool_call_id"])
        groups.setdefault(key, []).append(dict(r))
    for key, obs_list in groups.items():
        _make_invocation(conn, obs_list, matched_by="tool_call_id")
        created += 1

    # 2) trace_id + tool + 时间窗（双侧独立观测，避免同侧自关联）
    rows = conn.execute(
        """
        SELECT o.* FROM observations o
        WHERE o.trace_id IS NOT NULL AND o.trace_id != ''
          AND NOT EXISTS (SELECT 1 FROM observation_links l WHERE l.observation_id = o.observation_id)
        ORDER BY o.observed_at
        """
    ).fetchall()
    by_trace: dict = {}
    for r in rows:
        by_trace.setdefault(r["trace_id"], []).append(dict(r))
    for trace_id, obs_list in by_trace.items():
        # 只允许 client+server 异侧配对；同侧多条不合并（不构成独立观测）
        sides = {o.get("observer_side") for o in obs_list}
        if len(sides) < 2:
            for o in obs_list:
                _make_invocation(conn, [o], matched_by="none")
                created += 1
            continue
        # 按 tool + 时间窗细分（同 trace 内连续同名调用不产生笛卡尔积）
        groups = {}
        for o in obs_list:
            ts = _parse_ts(o.get("observed_at"))
            if ts is None:
                groups.setdefault(("none", o["tool"]), []).append(o)
                continue
            bucket_key = (ts.timestamp() // window_seconds, o["tool"])
            groups.setdefault(bucket_key, []).append(o)
        for _, group in groups.items():
            sides_in = {o.get("observer_side") for o in group}
            if len(sides_in) >= 2:
                _make_invocation(conn, group, matched_by="trace+window")
                created += 1
            else:
                for o in group:
                    _make_invocation(conn, [o], matched_by="none")
                    created += 1

    # 3) 其余（无键）→ 每条自成 invocation
    rows = conn.execute(
        """
        SELECT o.* FROM observations o
        WHERE NOT EXISTS (SELECT 1 FROM observation_links l WHERE l.observation_id = o.observation_id)
        """
    ).fetchall()
    for r in rows:
        _make_invocation(conn, [dict(r)], matched_by="none")
        created += 1

    conn.commit()
    return {"invocations_created": created}


def _make_invocation(conn, obs_list: list, matched_by: str) -> None:
    """由一组 observations 创建 invocation 并链接。"""
    invocation_id = str(uuid.uuid4())
    obs_ids = [o["observation_id"] for o in obs_list]
    # outcome：冲突保留（AUAS-CORE 不变量 12）——client success + server failure
    # → derived_outcome = "inconsistent"，绝不压平为 success
    outcomes = set(o.get("outcome") for o in obs_list if o.get("outcome"))
    if len(outcomes) > 1:
        outcome = "inconsistent"
    elif outcomes:
        outcome = next(iter(outcomes))
    else:
        outcome = "unknown"
    lifecycle = "L0"
    for o in obs_list:
        ls = o.get("lifecycle_stage")
        if ls and LIFECYCLE_ORDER.get(ls, 0) > LIFECYCLE_ORDER.get(lifecycle, 0):
            lifecycle = ls
    evidence = _grade(conn, obs_ids)
    started = min(
        (_parse_ts(o.get("observed_at")) for o in obs_list if _parse_ts(o.get("observed_at"))),
        default=None,
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO invocations
        (invocation_id, project_id, tool, started_at, outcome, lifecycle, evidence, eligible, matched_by)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            invocation_id,
            obs_list[0].get("project_id"),
            obs_list[0].get("tool"),
            started.isoformat() if started else None,
            outcome,
            lifecycle,
            evidence,
            1 if evidence != "E0" else 0,
            matched_by,
        ),
    )
    for oid in obs_ids:
        conn.execute(
            "INSERT OR IGNORE INTO observation_links (invocation_id, observation_id) VALUES (?,?)",
            (invocation_id, oid),
        )


LIFECYCLE_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def ingest_jsonl(conn, path: Path, source: str, project_id: str, principal: str) -> dict:
    """导入 adapter 观察事实（JSONL）→ observations 表。

    source: codex-hook | mcp-wrapper | unified（DSH plugin 输出）
    principal: 观察者身份（如 codex-hook@roy-tong）——独立性的判定依据
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from collector.normalizer.normalizer import normalize_observation  # noqa: E402

    accepted = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            obs = normalize_observation(raw, source, project_id, principal)
        except Exception:
            continue
        if store_observation(conn, obs):
            accepted += 1
    conn.commit()
    return {"accepted": accepted}
