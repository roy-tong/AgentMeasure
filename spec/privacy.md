# Privacy（隐私体系）

> 架构原则：**Raw telemetry stays local. Public infrastructure receives aggregates by default.**
> 云端默认拿不到：prompt、input、output、path、email、username、repo 私有名、raw session id。

## 1. 数据流

```text
Raw Events（Agent/prompt/trace/session）
        │
        ▼
本地 agent-used Collector
        ├─ identity resolution（本地）
        ├─ dedup
        ├─ redact（默认 DROP 敏感字段）
        ├─ aggregate
        └─ evidence calculation
        │
        ▼
SAFE AGGREGATES（计数/分布/比率）
        │
        ▼
agent-used cloud（公开 API/badge）
```

## 2. 默认 DROP 字段（adapter 代码级保证）

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| prompt | DROP | 永不采集 |
| tool_input | DROP | 参数内容 |
| tool_output / tool_response | DROP | 返回内容 |
| file_path / cwd | DROP | 路径 |
| raw session_id | DROP | 只保留伪匿名映射 |
| transcript / 会话文本 | DROP | 不采集 |

实现必须包含**泄漏测试**（敏感载荷 → 断言事件文件中零泄漏）。

## 3. 伪匿名标识（unique installations / repeat usage 的基础）

- 本地生成随机 secret，存于 `~/.agent-used/identity`
- 派生伪匿名标识：`pid = HMAC(local_secret, epoch_bucket)`，epoch 按月轮换
- 上传聚合时只带 `pid`，云端无法反推 installation 或用户
- 支持 `DO_NOT_TRACK=1`：完全禁用采集与上传

## 4. 聚合与展示

- 公开 API 只输出：计数、比率、分布、证据等级统计
- 最小展示单元 = 项目（project.id），不细到会话或用户
- 比率类指标（成功率/重复率/corroborated 占比）不暴露绝对量小的数据点（最小样本量门槛，默认 ≥10 sessions）

## 5. 法律与伦理

- agent-used 设计目标是**最小化个人数据收集**：原始内容默认留在本地、标识符
  伪匿名且按月轮换、公开基础设施只接收聚合数据
- **部署者仍自行承担适用的隐私与数据保护义务**（GDPR/CCPA 等）：EDPB 明确区分
  pseudonymisation 与 anonymisation——可通过额外信息重新关联的 pseudonymised
  data 仍可能属于 personal data（GDPR Recital 26 同原则）
- 本文件不做"GDPR 不适用"的法律判断；只承诺架构层面的最小化
- Claude Code 官方也提示 tool details 可能含敏感信息——collector 默认主动删除是合理设计而非过度设计

## 6. 内存内处理原则（代码级）

```text
stdin raw payload → 内存内 REDACT + PSEUDONYMIZE → safe observation → disk
```

禁止 `raw → disk → redact`。adapter 在落盘前完成：
1. 白名单提取（内容键一律不捕获）
2. session/identity 伪匿名（HMAC epoch，原始值只在内存中存在）
