#!/usr/bin/env python3
"""agent-used collector — aggregator v3（基于 invocations，证据分级）。

核心修复（measurement-integrity review）：
  - 统计对象是 invocation（一次逻辑调用），不是 observation
  - corroborated share = corroborated invocations / eligible invocations
    （100% 双边关联的数据 → 显示 100%，不再被 observation 双计拉低到 50%）
  - VACD（Verified Active Client-Days）：某 project 某 UTC 日被某伪匿名 client
    产生 ≥1 次 eligible invocation = 1 client-day。跨 Codex/Claude/DSH 可比。

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
from collector.policy import CORE_POLICY_V1  # noqa: E402

DAYS = 30


def compute(conn, project_id: str, days: int = DAYS) -> dict:
    since_dt = datetime.now(timezone.utc) - timedelta(days=days)
    since = since_dt.isoformat()

    # ---- invocation 级指标（核心） ----
    row = conn.execute(
        """
        SELECT COUNT(*), SUM(eligible) FROM invocations
        WHERE project_id=? AND started_at>=?
        """,
        (project_id, since),
    ).fetchone()
    total_invocations = row[0] or 0
    eligible_invocations = row[1] or 0

    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations
        WHERE project_id=? AND started_at>=? AND evidence='E2'
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

    # ---- Qualified Usage（排除 benchmark/test/synthetic/ci） ----
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT i.invocation_id) FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.project_id=? AND i.started_at>=? AND i.eligible=1
          AND o.usage_context = 'production' AND o.validity = 'normal'
        """,
        (project_id, since),
    ).fetchone()
    qualified_invocations = row[0] or 0
    qualified_rate = round(qualified_invocations / eligible_invocations, 3) if eligible_invocations else 0.0
    # 披露：context/validity 未知份额（Strict 口径的激励漏洞防护）
    row = conn.execute(
        """
        SELECT COUNT(*) FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.project_id=? AND i.started_at>=? AND i.eligible=1
          AND (o.usage_context='unknown' OR o.validity IS NULL OR o.validity='unknown')
        """,
        (project_id, since),
    ).fetchone()
    unknown_share_invocations = row[0] or 0

    # ---- execution success（invocation 级） ----
    row = conn.execute(
        """
        SELECT COUNT(*), SUM(outcome='success') FROM invocations
        WHERE project_id=? AND started_at>=? AND eligible=1
        """,
        (project_id, since),
    ).fetchone()
    total, success = row
    success_rate = round(success / total, 3) if total else 0.0

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

    corroborated_share = round(corroborated / eligible_invocations, 3) if eligible_invocations else 0.0

    return {
        "project": project_id,
        "days": days,
        "policy": describe(CORE_POLICY_V1),
        "active_clients": active_clients,
        "acd": acd,
        "logical_invocations": total_invocations,
        "eligible_invocations": eligible_invocations,
        "corroborated_invocations": corroborated,
        "corroborated_share": corroborated_share,
        "qualified_invocations": qualified_invocations,
        "qualified_rate": qualified_rate,
        "unknown_context_or_validity": unknown_share_invocations,
        "success_rate": success_rate,
        "evidence": [{"grade": e, "invocations": c} for e, c in evidence],
        "observers": [{"principal": p, "invocations": c} for p, c in hosts],
    }


def badge_svg(s: dict) -> str:
    label = f"{s['active_clients']:,} active clients · {s['acd']:,} client-days"
    sub = f"{s['logical_invocations']:,} invocations · {int(s['corroborated_share'] * 100)}% corroborated"
    lw = 128
    rw = max(170, 40 + len(label) * 6.2)
    w = lw + rw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="agent-used: {label}">
  <title>agent-used: {label} · {sub}</title>
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
