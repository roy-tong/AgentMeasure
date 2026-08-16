# agent-used SPEC v1（草案）

> Agent 工具调用测量标准。目标：让"Agent 使用量"成为可信、可比、可验证的公共数据。
> 状态：草案（随白皮书 v0.2 与研究回填修订）。配套实现：`mcp_wrapper.py`、`aggregator.py`。

## 1. 范围

本标准定义三层机制，覆盖"agent 调用工具"从发生到展示的完整链路：

- **L1 识别**（Identification）：被调方如何知道调用方是谁
- **L2 证明**（Attestation）：调用事件如何被验证为真实
- **L3 聚合**（Aggregation）：事件如何被收集、统计、展示

**不在范围内**：调用内容、参数、提示词、用户身份、任何形式的 star/follow 激励。

## 2. 事件格式（Event v1）

文件：`agent_event_schema.json`。要点：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `schema_version` | const "1.0" | 版本 |
| `event_id` | uuid | 事件唯一 ID（兼作防重放 nonce） |
| `occurred_at` | ISO-8601 | 发生时间（UTC） |
| `target` | string | 被调项目，如 `github.com/owner/repo` |
| `surface` | enum | `mcp` / `cli` / `http` / `skill` |
| `tool` | string | 工具/命令名（≤120 字符） |
| `outcome` | enum | `success` / `failure` / `retry` / `denied` |
| `duration_bucket` | enum | `<1s` / `1s-10s` / `10s-60s` / `1m-10m` / `>10m` |
| `agent_host` | string | 调用方标识（见 L1）；未知为 `unknown` |
| `telemetry_mode` | enum | `local`（默认） / `opted-in` |
| `signature` | string | 可选，L2 签名（hex） |
| `key_id` | string | 可选，签名密钥标识 |

**隐私约束（规范性）**：事件不得包含参数、结果、内容、路径、IP、设备标识。实现必须测试该约束（禁止泄漏断言）。

## 3. L1 识别

| 载体 | 规范 |
| --- | --- |
| MCP | 使用协议自带 `initialize.clientInfo{name, version}`；被调方从 initialize 消息解析并缓存 |
| HTTP | `User-Agent`（必填，按惯例）；可选 `X-Agent-Name`、`X-Agent-Version`——服务端仅作提示性识别，不得依赖其做安全决策 |
| CLI | 环境变量 `AGENT_HOST`（可选）、`AGENT_SESSION_ID`（可选） |
| Harness | harness 在工具边界直接签发事件时，`agent_host` 填 harness 自身标识（`codex` / `claude-code` / `dsh` 等） |

**原则**：尽力而为。调用方不自报 → `agent_host: "unknown"`，不得拒绝服务。

## 4. L2 证明

被调方（wrapper/中间件/harness）签发签名回执：

```
canonical = JSON(sort_keys, separators=(",",":"), {
  event_id, occurred_at, target, surface, tool, outcome })
signature = HMAC_SHA256(secret, canonical)
```

- 密钥由被调方持有；`key_id` 指向公开可验证的密钥标识
- 聚合器必须拒绝：无签名且 `telemetry_mode != local` 的事件；签名验证失败的事件；`key_id` 未知的事件
- 防重放：`event_id` 唯一性（数据库主键）+ 可选时间窗（5 分钟）
- **安全边界**：验签只校验事件元数据；聚合器不得接触调用内容

## 5. L3 聚合

### 5.1 API

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/v1/events` | POST | 批量提交事件（JSON array），返回 `{accepted, rejected}` |
| `/v1/stats/{owner}/{repo}?days=30` | GET | 统计：calls / success_rate / agent_hosts / by_tool / by_day |
| `/badge/{owner}/{repo}.svg` | GET | shields 兼容徽章："agent-used · agent calls N/mo" |

### 5.2 可信度规则

- 只展示验签通过的事件（local 导入模式需标记来源）
- 异常检测：单日调用数 > 近 30 天中位数 ×10 → 标记 `suspicious`，徽章降级显示
- 交叉验证（可选）：与 GitHub API clone 数、Release 下载量对照

## 6. 合规红线（规范性）

1. 不得实现或鼓励任何形式的自动 star/follow（GitHub AUP rank abuse 条款）
2. 不得爬取 GitHub 网页采集数据（数据来自用户自有工具事件；交叉验证走官方 API）
3. 隐私默认最小化：local → opted-in 两级；`DO_NOT_TRACK=1` 全程生效
4. 公开文档须明示数据口径与"统计使用、不是好评"的定位

## 7. 未来方向（草案）

- 双向证明（agent 侧签名）——需 agent 厂商配合，纳入 AAIF/OTel 讨论
- `surface: skill` 事件（技能加载即"能力获取"）
- harness 原生签发（Codex/Claude Code hooks 集成，研究回填）
- 标准提交：AAIF / OpenTelemetry GenAI 工作组对齐
