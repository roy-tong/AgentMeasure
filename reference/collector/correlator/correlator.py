#!/usr/bin/env python3
"""AgentMeasure collector — invocation matcher（观察 → 逻辑调用）。

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
            observation_type TEXT,
            observer_principal TEXT,
            observer_side TEXT,
            provenance TEXT,
            project_id TEXT,
            tool TEXT,
            surface_id TEXT,
            surface_namespace TEXT,
            caller_type TEXT,
            caller_runtime TEXT,
            caller_identity_strength TEXT,
            tool_call_id TEXT,
            trace_id TEXT,
            session_key TEXT,
            outcome TEXT,
            duration_bucket TEXT,
            duration_ms INTEGER,
            lifecycle_stage TEXT,
            signature TEXT,
            key_id TEXT,
            source_event_id TEXT,
            source_sequence INTEGER,
            source_instance_id TEXT,
            sequence_epoch TEXT,
            dropped_since_last_report INTEGER,
            buffer_overflow INTEGER,
            trust_domain TEXT,
            sampling TEXT,
            usage_context TEXT,
            validity TEXT,
            context_source TEXT,
            validity_source TEXT,
            operation_id TEXT,
            task_id TEXT
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
            matched_by TEXT,
            operation_id TEXT,
            task_id TEXT,
            operation_resolution TEXT,
            attempt_context TEXT,
            attempt_validity TEXT,
            qualification_status TEXT
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_oper ON observations(operation_id)")
    # 旧库迁移：补谱系列与 0.4.2 字段（Draft 0.4，Core §2.4）
    for table, cols in (
        ("observations", {"operation_id": "TEXT", "task_id": "TEXT",
                          "surface_id": "TEXT", "surface_namespace": "TEXT",
                          "source_sequence": "INTEGER", "observation_type": "TEXT",
                          "caller_type": "TEXT", "caller_runtime": "TEXT",
                          "caller_identity_strength": "TEXT", "duration_ms": "INTEGER",
                          "source_instance_id": "TEXT", "sequence_epoch": "TEXT",
                          "dropped_since_last_report": "INTEGER", "buffer_overflow": "INTEGER",
                          "context_source": "TEXT", "validity_source": "TEXT"}),
        ("invocations", {"operation_id": "TEXT", "task_id": "TEXT",
                         "operation_resolution": "TEXT", "attempt_context": "TEXT",
                         "attempt_validity": "TEXT", "qualification_status": "TEXT"}),
    ):
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for col, ddl in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
    conn.commit()
    return conn


def store_observation(conn, obs: dict) -> bool:
    # fail-closed（AgentMeasure-CORE 不变量）：无 observation_id 的观察拒绝入库
    if not obs.get("observation_id"):
        return False
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO observations
            (observation_id, observed_at, observation_type, observer_principal,
             observer_side, provenance, project_id, tool, surface_id, surface_namespace,
             caller_type, caller_runtime, caller_identity_strength, tool_call_id, trace_id,
             session_key, outcome, duration_bucket, duration_ms, lifecycle_stage,
             signature, key_id, source_event_id, source_sequence, source_instance_id,
             sequence_epoch, dropped_since_last_report, buffer_overflow, trust_domain,
             sampling, usage_context, validity, context_source, validity_source,
             operation_id, task_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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

    derive_operations(conn)
    resolve_qualification(conn)
    conn.commit()
    return {"invocations_created": created}


RETRY_OUTCOMES = ("failure", "retry", "denied")


def derive_operations(conn, enable_structural: bool = False) -> dict:
    """Operation 归并（AgentMeasure-CORE §2.4 / CORR §3，fail-closed，Draft 0.4.3）。

    只处理 operation_resolution IS NULL 的 attempt（幂等）：
      1. explicit   观察自带 operation_id / idempotency / 精确关联 → 直接归组
      2. structural **默认关闭（experimental）**：同 (project, tool, task_id) 内
                    按 started_at 排序的连续 attempt 且前一次失败 → 同一 operation。
                    推断过头风险：Provider 看不到中间 decision，可能把两个独立调用
                    误归为一个 retry chain。宁可 Operation Resolution Coverage 低，
                    也不要错——启用前 MUST 显式声明
      3. unknown    其余：operation_id 保持 NULL，**不归并、不伪装**
                    （Provider-only 拓扑的默认结果；M3.5 披露解析覆盖率）
    """
    explicit = structural = unknown = 0

    # 1) explicit：任一关联观察携带 operation_id
    rows = conn.execute(
        """
        SELECT i.invocation_id, o.operation_id FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.operation_resolution IS NULL
          AND o.operation_id IS NOT NULL AND o.operation_id != ''
        GROUP BY i.invocation_id
        """
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE invocations SET operation_id=?, operation_resolution='explicit' WHERE invocation_id=?",
            (r["operation_id"], r["invocation_id"]),
        )
        explicit += 1

    # 2) structural（experimental，默认关闭）：同 (project, tool, task_id) 重试链
    if not enable_structural:
        rows = conn.execute(
            "SELECT invocation_id FROM invocations WHERE operation_resolution IS NULL"
        ).fetchall()
        for r in rows:
            conn.execute(
                "UPDATE invocations SET operation_resolution='unknown' WHERE invocation_id=?",
                (r["invocation_id"],),
            )
            unknown += 1
        conn.commit()
        return {"explicit": explicit, "structural": 0, "unknown": unknown}

    rows = conn.execute(
        """
        SELECT invocation_id, project_id, tool, task_id, started_at, outcome
        FROM invocations
        WHERE operation_resolution IS NULL AND task_id IS NOT NULL AND task_id != ''
          AND started_at IS NOT NULL
        ORDER BY project_id, tool, task_id, started_at
        """
    ).fetchall()
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["project_id"], r["tool"], r["task_id"]), []).append(r)
    for group in groups.values():
        chain = group[0]["invocation_id"]
        prev_outcome = None
        for cur in group:
            if prev_outcome is not None and prev_outcome not in RETRY_OUTCOMES:
                chain = cur["invocation_id"]  # 前一次成功 → 新链（无选择介入证据，fail-closed）
            conn.execute(
                "UPDATE invocations SET operation_id=?, operation_resolution='structural' WHERE invocation_id=?",
                (chain, cur["invocation_id"]),
            )
            structural += 1
            prev_outcome = cur["outcome"]

    # 3) unknown：其余 attempt 无 operation 证据（fail-closed，不归并）
    rows = conn.execute(
        "SELECT invocation_id FROM invocations WHERE operation_resolution IS NULL"
    ).fetchall()
    for r in rows:
        conn.execute(
            "UPDATE invocations SET operation_resolution='unknown' WHERE invocation_id=?",
            (r["invocation_id"],),
        )
        unknown += 1

    conn.commit()
    return {"explicit": explicit, "structural": structural, "unknown": unknown}


# validity 严重度（冲突时取最严，不取乐观值）
_VALIDITY_SEVERITY = {"normal": 0, "health_check": 1, "load_test": 2,
                      "duplicate": 3, "replay": 4, "suspected_invalid": 5}


def resolve_qualification(conn) -> dict:
    """Qualification Resolution（Draft 0.4.3，DATA §4）。

    一次 Attempt 可有多条 observation（runtime + provider），各自带
    context/validity。派生 attempt 级口径（幂等：只处理 attempt_context IS NULL）：
      - context：全部一致取该值；部分 unknown 取已知值（partial）；
        多个不同已知值 → inconsistent（不压平）
      - validity：全部一致取该值；unknown 混入 → partially_classified；
        多个不同已知值 → 取最严（suspected_invalid 优先）
      - qualification_status：qualified（production+normal）| partially_classified
        | inconsistent | unknown
    指标只查询派生列，禁止统计 SQL 临时 join 判定（不变量 26）。
    """
    rows = conn.execute(
        """
        SELECT i.invocation_id, o.usage_context, o.validity
        FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.attempt_context IS NULL
        """
    ).fetchall()
    grouped: dict = {}
    for r in rows:
        grouped.setdefault(r["invocation_id"], []).append((r["usage_context"], r["validity"]))
    counts = {"qualified": 0, "partially_classified": 0, "inconsistent": 0, "unknown": 0}
    for inv_id, pairs in grouped.items():
        ctxs = {c for c, _ in pairs if c and c != "unknown"}
        validities = {v for _, v in pairs if v and v != "unknown"}
        if len(ctxs) > 1:
            attempt_context, ctx_status = "inconsistent", "inconsistent"
        elif ctxs:
            attempt_context = next(iter(ctxs))
            ctx_status = "partially_classified" if len(ctxs) < len({c for c, _ in pairs if c}) else "qualified"
        else:
            attempt_context, ctx_status = "unknown", "unknown"
        if validities:
            attempt_validity = max(validities, key=lambda v: _VALIDITY_SEVERITY.get(v, 0))
            v_status = "partially_classified" if len(validities) < len({v for _, v in pairs if v}) else "qualified"
        else:
            attempt_validity, v_status = "unknown", "unknown"
        if "inconsistent" in (ctx_status, v_status):
            status = "inconsistent"
        elif "partially_classified" in (ctx_status, v_status):
            status = "partially_classified"
        elif attempt_context == "production" and attempt_validity == "normal":
            status = "qualified"
        else:
            status = "unknown"
        conn.execute(
            """UPDATE invocations SET attempt_context=?, attempt_validity=?, qualification_status=?
               WHERE invocation_id=?""",
            (attempt_context, attempt_validity, status, inv_id),
        )
        counts[status] = counts.get(status, 0) + 1
    conn.commit()
    return counts


def _make_invocation(conn, obs_list: list, matched_by: str) -> None:
    """由一组 observations 创建 invocation 并链接。"""
    invocation_id = str(uuid.uuid4())
    obs_ids = [o["observation_id"] for o in obs_list]
    # 谱系（Core §2.4）：显式 operation_id / task_id 透传；未知留 null
    # （不变量 23：无 Operation 证据时不得归并，由 derive_operations 按规则处理）
    operation_id = next((o.get("operation_id") for o in obs_list if o.get("operation_id")), None)
    task_id = next((o.get("task_id") for o in obs_list if o.get("task_id")), None)
    # outcome：冲突保留（AgentMeasure-CORE 不变量 12）——client success + server failure
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
        (invocation_id, project_id, tool, started_at, outcome, lifecycle, evidence,
         eligible, matched_by, operation_id, task_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            invocation_id,
            obs_list[0].get("project_id"),
            obs_list[0].get("tool"),
            started.isoformat() if started else None,
            outcome,
            lifecycle,
            evidence,
            1 if evidence != "none" else 0,  # 单边 Provider observed 数据可进入统计（0.4.3）
            matched_by,
            operation_id,
            task_id,
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
