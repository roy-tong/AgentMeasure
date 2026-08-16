#!/usr/bin/env python3
"""AgentMeasure collector — aggregator v3（Draft 0.4.2，基于 attempts + operations）。

核心修复（measurement-integrity review）：
  - 统计对象：attempt（一次真实执行）与 operation（逻辑使用，fail-closed 归并）
  - Operation Resolution Coverage（M3.5）：无证据的 attempt 不伪装成 operation
  - corroborated share = corroborated attempts / eligible attempts
    （100% 双边关联的数据 → 显示 100%，不再被 observation 双计拉低到 50%）
  - ACD（Active Client-Days）：某 project 某 UTC 日被某伪匿名 client
    产生 ≥1 次 eligible attempt = 1 client-day。跨 Codex/Claude/DSH 可比。

用法:
  python3 aggregator.py stats --project github.com/foo/bar
  python3 aggregator.py badge --project github.com/foo/bar
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from collector.correlator.correlator import connect  # noqa: E402
from collector.policy import describe  # noqa: E402
from collector.policy import MEASUREMENT_POLICY  # noqa: E402

DAYS = 30

# 单词证据等级（TRUST §4）：corroborated 及以上计入 corroborated share
CORROBORATED_LEVELS = ("corroborated", "independently-corroborated", "platform-attested")


def compute(conn, project_id: str, days: int = DAYS) -> dict:
    since_dt = datetime.now(timezone.utc) - timedelta(days=days)
    since = since_dt.isoformat()

    # ---- attempt 级（M3.2/M3.3 的计数单位；attempt = invocation，Core §2.4） ----
    row = conn.execute(
        """
        SELECT COUNT(*), SUM(eligible) FROM invocations
        WHERE project_id=? AND started_at>=?
        """,
        (project_id, since),
    ).fetchone()
    attempts = row[0] or 0
    eligible_attempts = row[1] or 0

    # ---- operation 级（M3.1 Operation Count；fail-closed 解析，Draft 0.4.2） ----
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT operation_id) FROM invocations
        WHERE project_id=? AND started_at>=? AND operation_id IS NOT NULL
        """,
        (project_id, since),
    ).fetchone()
    resolved_operations = row[0] or 0
    # Draft 0.4.3：M3.1 只计已解析 operation，无回退（不变量 25）
    # 0.3 数据如需兼容：提供 legacy_attempt_equivalent（独立字段，绝不命名 Operation Count）
    logical_invocations = resolved_operations
    legacy_attempt_equivalent = attempts if resolved_operations == 0 else 0

    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations
        WHERE project_id=? AND started_at>=? AND operation_id IS NOT NULL
        """,
        (project_id, since),
    ).fetchone()
    resolved_attempts = row[0] or 0
    unresolved_attempts = attempts - resolved_attempts
    operation_resolution_coverage = round(resolved_attempts / attempts, 3) if attempts else 0.0

    row = conn.execute(
        """
        SELECT COALESCE(NULLIF(operation_resolution, ''), 'unknown') AS r, COUNT(*) AS n
        FROM invocations
        WHERE project_id=? AND started_at>=?
        GROUP BY r
        """,
        (project_id, since),
    ).fetchall()
    operation_resolution = {r["r"]: r["n"] for r in row}

    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations
        WHERE project_id=? AND started_at>=? AND evidence IN ('corroborated', 'independently-corroborated')
        """,
        (project_id, since),
    ).fetchone()
    corroborated = row[0] or 0

    # ---- ACD：伪匿名 client × UTC 日（有 eligible invocation；口径由 Policy 限定） ----
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT substr(started_at, 1, 10) || '|' || client_day)
        FROM (
            SELECT i.started_at,
                   (SELECT o.session_key FROM observation_links l
                    JOIN observations o ON o.observation_id = l.observation_id
                    WHERE l.invocation_id = i.invocation_id
                      AND o.session_key != '' AND o.session_key IS NOT NULL
                    LIMIT 1) AS client_day
            FROM invocations i
            WHERE i.project_id=? AND i.started_at>=? AND i.eligible=1
        )
        """,
        (project_id, since),
    ).fetchone()
    acd = row[0] or 0

    # ---- 活跃 clients（30 天内有 eligible invocation 的伪匿名 client） ----
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT o.session_key)
        FROM observation_links l
        JOIN observations o ON o.observation_id = l.observation_id
        JOIN invocations i ON i.invocation_id = l.invocation_id
        WHERE i.project_id=? AND i.started_at>=? AND i.eligible=1
          AND o.session_key != '' AND o.session_key IS NOT NULL
        """,
        (project_id, since),
    ).fetchone()
    active_clients = row[0] or 0

    # ---- Qualified Usage（基于 derived_attempt_qualification，不变量 26） ----
    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations
        WHERE project_id=? AND started_at>=? AND eligible=1
          AND attempt_context='production' AND attempt_validity='normal'
        """,
        (project_id, since),
    ).fetchone()
    qualified_invocations = row[0] or 0
    qualified_rate = round(qualified_invocations / eligible_attempts, 3) if eligible_attempts else 0.0
    # 披露：partially_classified / inconsistent / unknown（激励漏洞防护）
    row = conn.execute(
        """
        SELECT qualification_status, COUNT(*) AS n FROM invocations
        WHERE project_id=? AND started_at>=? AND eligible=1
        GROUP BY qualification_status
        """,
        (project_id, since),
    ).fetchall()
    qualification_status = {r["qualification_status"] or "unknown": r["n"] for r in row}
    unknown_share_invocations = (qualification_status.get("unknown", 0)
                                 + qualification_status.get("partially_classified", 0)
                                 + qualification_status.get("inconsistent", 0))

    # ---- success rate（AgentMeasure-M3.3：Successful Completed ÷ Completed；
    #      unknown/inconsistent 不进分母，单列披露） ----
    row = conn.execute(
        """
        SELECT COUNT(*), SUM(outcome='success') FROM invocations
        WHERE project_id=? AND started_at>=? AND eligible=1
          AND outcome IN ('success', 'failure', 'denied')
        """,
        (project_id, since),
    ).fetchone()
    completed, success = row
    success_rate = round(success / completed, 3) if completed else 0.0
    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations
        WHERE project_id=? AND started_at>=? AND eligible=1
          AND outcome NOT IN ('success', 'failure', 'denied')
        """,
        (project_id, since),
    ).fetchone()
    unknown_or_inconsistent = row[0] or 0

    # ---- 证据分布 / 宿主分布（invocation 级） ----
    evidence = conn.execute(
        """
        SELECT evidence, COUNT(*) FROM invocations
        WHERE project_id=? AND started_at>=? AND eligible=1
        GROUP BY evidence ORDER BY 2 DESC
        """,
        (project_id, since),
    ).fetchall()

    hosts = conn.execute(
        """
        SELECT o.observer_principal, COUNT(DISTINCT i.invocation_id) FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.project_id=? AND i.started_at>=? AND i.eligible=1
        GROUP BY o.observer_principal ORDER BY 2 DESC
        """,
        (project_id, since),
    ).fetchall()

    corroborated_share = round(corroborated / eligible_attempts, 3) if eligible_attempts else 0.0
    attempts_per_operation = round(attempts / resolved_operations, 2) if resolved_operations else 0.0

    return {
        "project": project_id,
        "days": days,
        "policy": describe(MEASUREMENT_POLICY),
        "active_clients": active_clients,
        "acd": acd,
        "logical_invocations": logical_invocations,   # M3.1：已解析 Operation 数（0.3 回退时 = attempts）
        "attempts": attempts,                          # attempt 数（M3.2/M3.3 单位）
        "resolved_operations": resolved_operations,
        "legacy_attempt_equivalent": legacy_attempt_equivalent,  # 仅 0.3 迁移期披露
        "unresolved_attempts": unresolved_attempts,
        "qualification_status": qualification_status,
        "operation_resolution_coverage": operation_resolution_coverage,  # M3.5
        "attempts_per_operation": attempts_per_operation,
        "operation_resolution": operation_resolution,  # explicit | structural | unknown
        "eligible_invocations": eligible_attempts,
        "corroborated_invocations": corroborated,
        "corroborated_share": corroborated_share,
        "qualified_invocations": qualified_invocations,
        "qualified_rate": qualified_rate,
        "unknown_context_or_validity": unknown_share_invocations,
        "success_rate": success_rate,
        "unknown_or_inconsistent_outcomes": unknown_or_inconsistent,
        "evidence": [{"grade": e, "invocations": c} for e, c in evidence],
        "observers": [{"principal": p, "invocations": c} for p, c in hosts],
    }


def badge_svg(s: dict) -> str:
    label = f"{s['active_clients']:,} active clients · {s['acd']:,} client-days"
    sub = f"{s['logical_invocations']:,} operations · {int(s['corroborated_share'] * 100)}% corroborated"
    lw = 128
    rw = max(170, 40 + len(label) * 6.2)
    w = lw + rw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="agentmeasure: {label}">
  <title>agentmeasure: {label} · {sub}</title>
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
    <text x="{lw/2}" y="14">agentmeasure</text>
    <text x="{lw + rw/2}" y="14">{label}</text>
  </g>
</svg>"""


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    stats = sub.add_parser("stats")
    stats.add_argument("--project", required=True)
    stats.add_argument("--days", type=int, default=DAYS)
    badge = sub.add_parser("badge")
    badge.add_argument("--project", required=True)
    args = parser.parse_args(argv)

    conn = connect()
    if args.cmd == "stats":
        print(json.dumps(compute(conn, args.project, args.days), ensure_ascii=False, indent=2))
    else:
        print(badge_svg(compute(conn, args.project, args.days)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
