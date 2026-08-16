# AUAS Conformance

## Conformance Levels（Draft 0.3）

一个平台可能根本观察不到 Presented——不能要求它支持全部标准。按能力分层认证：

| Level | 覆盖 | 要求 |
| --- | --- | --- |
| **AUAS Core Conformant** | 收据格式、签名、隐私、不变量 1-20 | core vectors 全过 |
| **AUAS Choice Conformant** | M2.1-M2.5 | choice vectors 全过 + presented 可观察 |
| **AUAS Execution Conformant** | M3.1-M3.3 | execution vectors 全过 |
| **AUAS Utility Conformant** | M4.1 | consumption vectors 全过 |
| **AUAS Reporting Conformant** | Measurement Label + 口径披露 | reporting fixtures 全过 |

认证声明示例：`agent-used compatible — AUAS Choice Conformant (Draft 0.3)`

## 运行

```bash
python3 conformance/runners/run_metrics.py    # 指标 vectors
python3 verify_vectors.py                      # receipt/correlation vectors
```

## 语言无关性

`conformance/vectors/*.json` 是语言无关契约：Go/Rust/TS 实现应对同一 vectors
产生同一结果。runner 只是参考实现的验证器。
