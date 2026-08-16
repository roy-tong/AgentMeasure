# agentmeasure-dsh — DeepSeek Harness Adapter

> DSH 是 AgentMeasure 的第一方深集成目标（E2/E3 证据能力的来源）。
> 本文件基于 DSH 实际源码（@deepseek-ai/dsh-agent-loop）确认的事件流编写。

## 1. 架构

```text
DSH session event stream（dsh-agent-loop 持久化事件流）
  ├─ tool/call     {turn, step, callId, name, arguments}   ← S1 起点
  ├─ tool/result   {turn, step, message, error, meta}      ← S2 + outcome（经 sourceEventSeqs 关联）
  ├─ turn/start / step/start / step/end / turn/end         ← session 级归一
  └─ agentmeasure plugin（Cordis）
        ├─ 监听 tool/call + tool/result
        ├─ 只提取: name / callId / turn / step / outcome / 时间差
        ├─ DROP: arguments / message 内容 / 路径
        └─ 伪匿名 session → 本地 collector → 统一 usage 记录
```

## 2. 已确认的事件结构（源码核实，`dsh-agent-loop/lib/index.js`）

| 事件 | 字段 | AgentMeasure 用途 | 处理 |
| --- | --- | --- | --- |
| `tool/call` | `turn, step, callId, name, arguments` | stage=S1, tool=name, tool_use_id=callId | `arguments` **DROP** |
| `tool/result` | `turn, step, message{content,isError}, error, meta` | stage=S2, outcome=isError?failure:success, 耗时=tool/call→tool/result 时间差 | `message.content` **DROP** |
| `turn/start` | `turn` | 会话内归一边界 | 计数用 |
| `step/start` | `{turn, step, ...}` | 同上 | 计数用 |

关联机制：`tool/result` 通过 `sourceEventSeqs: [callSeq]` 引用其 `tool/call` 事件——**DSH 原生提供配对关系**（agent-side 的 E2 半边）。

## 3. 事件映射（standard/BIND.md）

| DSH 字段 | agentmeasure.* |
| --- | --- |
| `name`（tool/call） | `gen_ai.tool.name` → unified `tool` |
| `callId` | `tool_use_id` |
| `session`（DSH session id） | 伪匿名 `session_id`（本地哈希） |
| — | `agentmeasure.agent.host = "deepseek-harness"` |
| — | `agentmeasure.observer.side = "client"` |
| — | `agentmeasure.provenance = "platform"`（harness 原生） |

## 4. 证据说明

- DSH 插件运行在 harness 内、事件来自持久化 session 流——**provenance=platform，天然强于 hooks 观察**
- `tool/call ↔ tool/result` 的 sourceEventSeqs 配对是 harness 原生证明；**证据等级由 verifier 派生（本 adapter 绝不自声明）**——verifier 可据此判 E2
- 若工具侧（MCP wrapper）同 trace_id 关联，构成真正的双边 E2（跨 harness 与工具）

## 5. 实现计划

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| P1 | Cordis plugin 骨架：订阅 session 事件（tool/call、tool/result） | 已实现（plugin.js） |
| P2 | 归一化 + 伪匿名 + 本地 JSONL（复用 collector/normalizer 模式） | 已实现 |
| P3 | sourceEventSeqs 配对 → verifier 派生 E2 | 已实现（lifecycle L2 配对） |
| P4 | 泄漏测试（arguments/message 零落盘）+ 与 collector 打通 | 待开发 |
| P5 | 公开 demo：DSH 真实使用数据 → 徽章 | 待开发 |

## 6. 验证标准

- [ ] 插件安装后每次工具调用产生 1 条 S1+S2 配对记录（含耗时）
- [ ] arguments / message 内容零泄漏（断言）
- [ ] 与 Codex / Claude 数据并入同一统计（跨宿主统一）
- [ ] 工具侧接入时升级为跨侧 E2
