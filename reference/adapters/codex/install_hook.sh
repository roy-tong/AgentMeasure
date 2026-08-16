#!/usr/bin/env bash
# agent-used — 安装 Codex PostToolUse hook（M0.5 PoC）
# 用法: bash install_hook.sh [--repo]   # 默认用户级 ~/.codex/hooks.json，--repo 装到当前仓库 .codex/
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
HOOK_SCRIPT="$BASE/hook_agent.py"
EVENT="PostToolUse"

if [[ "${1:-}" == "--repo" ]]; then
  TARGET_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/.codex"
else
  TARGET_DIR="$HOME/.codex"
fi
mkdir -p "$TARGET_DIR"
HOOKS_FILE="$TARGET_DIR/hooks.json"

cat > "$HOOKS_FILE" <<EOF
{
  "description": "agent-used: record agent tool calls (metadata only, privacy-first)",
  "hooks": {
    "$EVENT": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/env python3 $HOOK_SCRIPT",
            "statusMessage": "agent-used: recording tool call"
          }
        ]
      }
    ]
  }
}
EOF

echo "已写入 $HOOKS_FILE"
echo "Codex 会要求你 review + trust 这个 hook（/hooks 命令）。"
echo "事件写入 ~/.agent-used/events/agent-use-events.jsonl"
echo "环境变量: AGENTMEASURE_TARGET=<你的项目标识> AGENTMEASURE_HOST=codex DO_NOT_TRACK=1(禁用)"
