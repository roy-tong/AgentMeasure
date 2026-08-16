# agent-used

**客观测量 Agent 调用工具的开放数据体系：标准 + 中间件 + 徽章。**

```bash
# 包装任意 MCP server，一行命令开始记录 Agent 调用
agent-used wrap -- npx @your/mcp-server

# 本地聚合 → README 徽章（"本月 N 次 Agent 调用"）
python3 aggregator.py import --events ~/.agent-used/events/agent-use-events.jsonl
python3 aggregator.py serve --port 8787   # GET /badge/{owner}/{repo}.svg
```

[白皮书：《工具经济需要客观数据》](https://roy-tong.github.io/) · [事件标准 v1](agent_event_schema.json) · [English](README.en.md)

## 问题

2026 年 Agent 正在成为软件分发最重要的新渠道，但工具作者对自己工具被 Agent 使用了多少次、成功与否、谁在用——一无所知。skills.sh 的计数是自报遥测（可刷、无 API）；MCP registry 明确不做采纳数据；GitHub 没有 repo 级 Agent 指标。**Agent 经济正在成为一场没有记分牌的比赛。**

## 三层测量标准

| 层 | 回答的问题 | 实现 |
| --- | --- | --- |
| L1 识别 | 谁在调用 | MCP `clientInfo` / HTTP `X-Agent-Name` / CLI `AGENT_HOST` |
| L2 证明 | 调用是真的 | 被调方签发 HMAC 签名回执（nonce 防重放） |
| L3 聚合 | 总量可信 | 开放事件格式 + 聚合 API + 徽章 + 异常检测 |

**核心差异**：计数发生在被调方（wrapper 在真实调用边界），调用方无法自报——这是与所有自报式遥测的本质区别。

## 组件

| 组件 | 状态 | 说明 |
| --- | --- | --- |
| `agent_event_schema.json` | ✅ v1 | 开放事件标准（JSONL，只含元数据） |
| `mcp_wrapper.py` | ✅ 已测试 | MCP server 包装：stdio 代理 + tools/call 拦截 + clientInfo 识别 + L2 签名 |
| `aggregator.py` | ✅ 已测试 | 事件导入/验签/统计/徽章 SVG（零依赖 stdlib） |
| CLI wrapper | 路线图 | `agent-used run -- <cmd>` |
| HTTP 中间件 | 路线图 | Web 服务计数 |
| 聚合云服务 | 路线图 | Cloudflare Workers |

## 隐私与合规（写进代码）

- 只记录：工具名、结果、粗粒度耗时、宿主、时间。**绝不记录参数、内容、路径、身份**
- `DO_NOT_TRACK=1` 全程生效；默认只写本地，opt-in 才上传聚合
- **永不激励 Agent star/follow**（GitHub AUP 明确禁止 automated starring）；数据来源是用户自有工具事件，不爬 GitHub

## 快速开始

```bash
# 1. 包装你的 MCP server（记录开始）
AGENT_USED_TARGET=github.com/you/your-repo \
  python3 mcp_wrapper.py wrap -- npx @your/mcp-server

# 2. 看本地事件
cat ~/.agent-used/events/agent-use-events.jsonl

# 3. 本地聚合 + 徽章
python3 aggregator.py import --events ~/.agent-used/events/agent-use-events.jsonl
python3 aggregator.py seed-demo        # 可选：演示数据
python3 aggregator.py serve --port 8787
open http://127.0.0.1:8787/badge/you/your-repo
```

## 测试

```bash
python3 -m py_compile mcp_wrapper.py aggregator.py
# 端到端已验证：JSON-RPC 全代理、事件精确（只记 tools/call）、
# clientInfo → agent_host、签名验签 PASS、伪造事件拒绝、参数零泄漏
```

## 路线图

- M0 ✅ 事件标准 + MCP wrapper（识别 + 签名）
- M1 ✅ 聚合引擎本地版 → ☁️ 云端（Workers）
- M2  CLI wrapper + HTTP 中间件 + SPEC.md
- M3  3 个外部项目接入实验 + Stage Gate
- 研究：Codex / Claude Code / DeepSeek Harness 的 hooks 原生集成（agent 平台路径）

## License

MIT
