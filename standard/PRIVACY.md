# AgentMeasure Privacy — Identifier、Retention、Aggregation、Redaction（Draft 0.1）

## 1. 架构原则

**Raw telemetry stays local. Public infrastructure receives aggregates by default.**
跨主体佐证只交换签名收据 + correlation_commitment（单向哈希），不交换原始数据。

## 2. Identifier 体系

| 标识 | 生成 | 生命周期 | 谁可见 |
| --- | --- | --- | --- |
| session_key | HMAC(epoch_secret, host:raw)，内存内 | 按月轮换（unlinkability） | 本地 collector |
| correlation_commitment | H(protocol‖project‖trace‖call_id) | 与调用同生命周期 | 公共 verifier |
| stable local key | 本地随机 secret | 永不出设备 | 仅本地 |

## 3. Retention 与 unlinkability 的冲突解法

伪匿名按月轮换 → 云端无法跨月关联同一 client → 30d retention 无法直接算。
解法：**稳定本地 key 永不出设备；retention 在本地聚合为 cohort 统计后上传**：

```text
Stable local key（永不离开设备）
        │
        ▼
本地聚合：D7 cohort = 100 → 43
        │
        ▼
上传 aggregate（无稳定 client id）
```

## 4. Redaction 管线（代码级）

```text
stdin raw payload → 内存内 REDACT + PSEUDONYMIZE → safe receipt → disk
```

禁止 `raw → disk → redact`。泄漏测试是 adapter 的必选项。

## 5. 法律边界

- agent-used 设计目标是最小化个人数据收集；**部署者自行承担适用的隐私与数据
  保护义务**（EDPB：pseudonymised data 仍可能属于 personal data）
- 本文件不做"GDPR 不适用"的法律判断
