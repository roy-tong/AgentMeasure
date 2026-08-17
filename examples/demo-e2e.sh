#!/usr/bin/env bash
# AgentMeasure 端到端 demo —— 2 分钟跑通：MCP server → canonical observations → metrics
#
# 可重复性保证（v0.1.1 External-Ready）：
#   - 每次运行创建独立 workspace（mktemp -d），绝不读写 ~/.agentmeasure
#   - 固定 fixture（42 calls / 3 callers）+ 固定窗口（--days 365）
#   - 相同 fixture + 相同 policy = 相同结果（42 calls → 84 observations）
#
# 前置: node >= 18, python3（无外部依赖）
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$(mktemp -d)"
EVENTS_DIR="$RUN_DIR/events"
export AGENTMEASURE_EVENTS_DIR="$EVENTS_DIR"
trap 'rm -rf "$RUN_DIR"' EXIT

echo "== 1/3 启动 mock MCP server（@agentmeasure/mcp 包装 42 次调用，3 类 caller）"
(cd "$REPO/sdk" && node examples/mcp-integration.js)

EVENTS_FILE="$EVENTS_DIR/agentmeasure-events.jsonl"
echo
echo "== 2/3 事件文件（隔离 workspace：${EVENTS_DIR}，未触碰 ~/.agentmeasure）"
ls -la "$EVENTS_FILE"

echo
echo "== 3/3 本地指标（observe-first：synthetic 标注、unknown 默认、fail-closed）"
python3 "$REPO/product/local-analytics.py" "$EVENTS_FILE" --project demo/acme-weather --days 365

echo
echo "Demo 完成。期望输出：84 条 canonical observations、0 rejected、42 attempts、"
echo "0% Strict Qualified（synthetic 不计入 production）、caller claude:14 codex:14 unknown:14。"
echo "下一步：把你的 MCP server 用 @agentmeasure/mcp 包一层（见 sdk/examples/mcp-integration.js 或 -v2.js）。"
