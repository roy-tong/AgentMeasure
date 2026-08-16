#!/usr/bin/env python3
"""agent-used collector — aggregator（证据分级统计 + 徽章）。

数据源：collector.db（unified_events + correlations，由 correlator 写入）。
指标口径（spec/metrics.md）：
  - verified calls      = E1+ 事件数（supporting）
  - corroborated usage  = E2 关联数（核心可信度）
  - active sessions     = 30 天内有 verified usage 的伪匿名会话数（首要指标）
  - success rate / host 分布 / stage 分布

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

DAYS = 30


def compute(conn, project_id: str, days: int = DAYS) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    row = conn.execute(
        "SELECT COUNT(*) FROM unified_events WHERE project_id=? AND occurred_at>=? AND evidence_level!='E0'",
        (project_id, since),
    ).fetchone()
    verified_calls = row[0] or 0

    row = conn.execute(
        "SELECT COUNT(*) FROM correlations WHERE project_id=? AND correlated_at>=?",
        (project_id, since),
    ).fetchone()
    corroborated = row[0] or 0

    row = conn.execute(
        """
        SELECT COUNT(DISTINCT session_id) FROM unified_events
        WHERE project_id=? AND occurred_at>=? AND evidence_level!='E0'
          AND session_id IS NOT NULL AND session_id != ''
        """,
        (project_id, since),
    ).fetchone()
    active_sessions = row[0] or 0

    row = conn.execute(
        """
        SELECT COUNT(*), SUM(outcome='success') FROM unified_events
        WHERE project_id=? AND occurred_at>=? AND evidence_level!='E0'
        """,
        (project_id, since),
    ).fetchone()
    total, success = row
    success_rate = round(success / total, 3) if total else 0.0

    hosts = conn.execute(
        """
        SELECT agent_host, COUNT(*) FROM unified_events
        WHERE project_id=? AND occurred_at>=? AND evidence_level!='E0'
        GROUP BY agent_host ORDER BY 2 DESC
        """,
        (project_id, since),
    ).fetchall()

    stages = conn.execute(
        """
        SELECT stage, COUNT(*) FROM unified_events
        WHERE project_id=? AND occurred_at>=? AND evidence_level!='E0'
        GROUP BY stage ORDER BY 2 DESC
        """,
        (project_id, since),
    ).fetchall()

    corroborated_share = round(corroborated / verified_calls, 3) if verified_calls else 0.0

    return {
        "project": project_id,
        "days": days,
        "active_agent_sessions": active_sessions,
        "verified_calls": verified_calls,
        "corroborated_usage": corroborated,
        "corroborated_share": corroborated_share,
        "success_rate": success_rate,
        "agent_hosts": [{"host": h, "calls": c} for h, c in hosts],
        "stages": [{"stage": s, "calls": c} for s, c in stages],
    }


def badge_svg(s: dict) -> str:
    label = f"{s['verified_calls']:,} verified calls · {s['active_agent_sessions']:,} sessions"
    sub = f"{int(s['corroborated_share'] * 100)}% corroborated"
    lw = 128
    rw = max(150, 40 + len(label) * 6.5)
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
