#!/usr/bin/env python3
"""AgentMeasure collector — consumption chain（Consumption / Result Consumed 检测）。

Claude Code 是 Consumption 的第一个实证平台（docs/adapters.md）：
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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
    pending: dict = {}  # tool_use_id -> tool（未消费结果；request 必须带精确 id 才能消费）
    ambiguous: dict = {}  # tool -> count（同名未决结果，无法精确关联）
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
                pending[tool_use_id] = tool
        elif ev.get("type") == "request":
            # 精确消费信号：request 带 consumed_tool_use_id → 精确配对
            target_id = str(ev.get("consumed_tool_use_id") or "")
            if target_id and target_id in pending:
                tool = pending.pop(target_id)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO consumption_links
                    (tool_use_id, project_id, tool, consumed_at, request_seq)
                    VALUES (?,?,?,?,?)
                    """,
                    (target_id, project_id, tool,
                     str(ev.get("ts") or ""), ev.get("seq")),
                )
                consumed += 1
            # 无精确 id 的 request（仅 mcp_tool 名）→ 不强行配对；同名未决结果计 ambiguous
            elif ev.get("mcp_tool"):
                tool = str(ev["mcp_tool"])
                matches = [k for k, v in pending.items() if v == tool]
                if len(matches) == 1:
                    tool_use_id = matches[0]
                    pending.pop(tool_use_id)
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
                elif len(matches) > 1:
                    ambiguous[tool] = ambiguous.get(tool, 0) + 1  # fail-closed：不配对
    conn.commit()
    return {"consumption_links": consumed, "ambiguous_matches": ambiguous}


def consumed_rate(conn, project_id: str, days: int = 30) -> dict:
    """M4.1：consumed links ÷ consumption-observable eligible invocations。

    分母纪律（不变量 17）：consumption 不可观察的 runtime 不进入分母——
    UNOBSERVABLE 绝不记为未消费。observable 判定：调用来自 consumption 可观察
    的 observer（本实现：claude-otel 主；其他 runtime 单列披露）。
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) FROM consumption_links WHERE project_id=? AND consumed_at>=?",
        (project_id, since),
    ).fetchone()
    consumed = row[0] or 0
    # 分母 = eligible invocations 中 consumption 可观察的部分
    # （Observer Capability Manifest 判定，不是 observer 名字猜测）
    from collector.manifest import is_observable, SIGNALS  # noqa: E402

    # 找出声明 consumed=OBSERVABLE 的 runtime（按 manifest，fail-closed）
    observable_runtimes = _consumption_observable_runtimes()
    # 分母：client 侧 observer 属于可观察 runtime 的 eligible invocation
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT i.invocation_id) FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.project_id=? AND i.eligible=1 AND o.observer_side='client'
          AND o.observer_principal LIKE ?
        """,
        (project_id,),
    ).fetchone() if not observable_runtimes else conn.execute(
        "SELECT COUNT(DISTINCT i.invocation_id) FROM invocations i WHERE i.project_id=? AND i.eligible=1 AND 0",
        (project_id,),
    ).fetchone()
    observable = _count_client_observable(conn, project_id, observable_runtimes)
    # 披露：不可观察的 eligible invocations（不并入分母，单独报告）
    unobservable = _count_client_unobservable(conn, project_id, observable_runtimes)
    return {
        "consumed_results": consumed,
        "consumption_observable_invocations": observable,
        "consumption_unobservable_invocations": unobservable,
        "consumed_rate": round(consumed / observable, 3) if observable else 0.0,
    }


def _consumption_observable_runtimes() -> set:
    """返回声明 consumed=OBSERVABLE 的 runtime 集合（manifest，fail-closed）。"""
    import json as _json

    out = set()
    manifests_dir = Path(__file__).resolve().parents[1] / "adapters"
    for mf in manifests_dir.glob("*/manifest.json"):
        try:
            data = _json.loads(mf.read_text(encoding="utf-8"))
            if data.get("signals", {}).get("consumed") == "OBSERVABLE":
                out.add(data["runtime"])
        except Exception:
            continue
    return out


def _observer_runtime(principal: str) -> str:
    """observer_principal → runtime 名（'claude-otel@t' → 'claude-code' 映射表；
    无映射用前缀；未知 → 不可观察（fail-closed））。"""
    prefix = (principal or "").split("@")[0]
    return {"claude-otel": "claude-code", "codex-hook": "codex",
            "dsh": "deepseek-harness", "mcp-wrapper": "mcp"}.get(prefix, prefix)


def _count_client_observable(conn, project_id: str, observable_runtimes: set) -> int:
    if not observable_runtimes:
        return 0
    rows = conn.execute(
        """
        SELECT DISTINCT i.invocation_id, o.observer_principal FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.project_id=? AND i.eligible=1 AND o.observer_side='client'
        """,
        (project_id,),
    ).fetchall()
    return sum(1 for r in rows if _observer_runtime(r["observer_principal"]) in observable_runtimes)


def _count_client_unobservable(conn, project_id: str, observable_runtimes: set) -> int:
    rows = conn.execute(
        """
        SELECT DISTINCT i.invocation_id, o.observer_principal FROM invocations i
        JOIN observation_links l ON l.invocation_id = i.invocation_id
        JOIN observations o ON o.observation_id = l.observation_id
        WHERE i.project_id=? AND i.eligible=1 AND o.observer_side='client'
        """,
        (project_id,),
    ).fetchall()
    seen = {r["invocation_id"] for r in rows
            if _observer_runtime(r["observer_principal"]) in observable_runtimes}
    return sum(1 for r in rows if r["invocation_id"] not in seen)
