# Evidence Model（证据模型）

> 回答：这条 usage 记录有多可信？二元"真/假"在开放生态里不成立，证据是分级的。

## 1. 证据等级

| 等级 | 名称 | 判定规则 | 可被什么攻击 | 公共统计用途 |
| --- | --- | --- | --- | --- |
| **E0** | Observed | 单边本地日志声称发生调用（无签名） | 任意一方伪造 | 不计入 verified 统计 |
| **E1** | Source-authenticated | 事件带合法签名（HMAC，key 归属已验证） | 持 key 方自刷 | 计入 source-verified |
| **E2** | Correlated | Agent 侧与 Tool 侧独立观测匹配（trace_id / tool_use_id / tool / 时间窗） | 双侧合谋 | **计入 corroborated usage（核心）** |
| **E3** | Platform-attested | Agent 平台 / trusted runtime 原生证明（如平台 API 确认） | 平台自身 | 最高可信 |

## 2. 判定规则

### E1：Source-authenticated

- 事件含 `signature`（HMAC-SHA256 over canonical fields）+ `key_id`
- `key_id` 在公开 key 目录中可解析
- 验签通过 → E1
- 注意：E1 不等于"真的有 Agent 调用"——持 key 方可以自签。E1 只证明来源与完整性。

### E2：Correlated（corroborated usage）

匹配条件（全部满足才算一次 corroborated usage）：

1. Agent 侧事件与 Tool 侧事件具有**相同 `trace_id`**（MCP `_meta` trace context 传播）
2. `tool` 标识一致（归一后）
3. 时间窗内（默认 ±5 分钟；可由 trace 父子 span 精确判定）
4. 两侧 observer 不同（client ≠ server）

关联后：
- 两侧各自的事件保留（来源可审计）
- 生成关联记录：`{correlation_id, trace_id, agent_event_id, tool_event_id, evidence: E2}`
- 去重：一次 E2 记录 = 一次 verified usage（raw calls 仍分别记录但不再叠加）

### E3：Platform-attested

- 事件由 agent 平台签名（平台私钥），或在平台官方 API 响应中确认
- 需要平台合作或平台开放 attestation 接口（升级路径，非前置）

## 3. 反合谋说明

E2 无法防御"工具作者与自己的另一个 agent 合谋刷量"。
缓解：身份图（identity.md）+ 行为异常检测 + 与独立信号交叉验证（GitHub API clone、npm 下载、registry 收录）。
E3 是唯一对抗合谋的强证据——这也是平台路径的长期价值所在。

## 4. 公开口径

| 口径 | 定义 | 展示 |
| --- | --- | --- |
| observed calls | E0+ | 不单独展示 |
| source-verified calls | E1+ | 明细（带 provenance 标注） |
| **corroborated usage** | E2+ | **默认首要展示** |
| platform-attested usage | E3 | 标记 ✅ |

徽章示例：

```
Agent Usage · 30d
18.4k verified calls     ← E1+
2.7k active sessions    ← Adoption 首要指标
96.2% success
71% corroborated        ← E2 占比
Codex · Claude Code · DSH
```
