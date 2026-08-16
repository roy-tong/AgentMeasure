#!/usr/bin/env bash
# AgentMeasure 端到端 demo —— 2 分钟跑通：MCP server → canonical observations → metrics
# 前置: node >= 18, python3（无外部依赖）
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
EVENTS="${AGENTMEASURE_EVENTS:-$HOME/.agentmeasure/events/agentmeasure-events.jsonl}"

echo "== 1/3 启动 mock MCP server（@agentmeasure/mcp 包装 42 次调用）"
(cd "$REPO/sdk" && node examples/mcp-integration.js)

echo "== 2/3 事件文件"
ls -la "$EVENTS"

echo "== 3/3 本地指标（observe-first, unknown by default）"
python3 "$REPO/product/local-analytics.py" "$EVENTS"

echo
echo "Demo 完成。下一步：把你的 MCP server 用 @agentmeasure/mcp 包一层（见 sdk/examples/mcp-integration.js）。"
