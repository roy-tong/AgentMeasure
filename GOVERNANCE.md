# Governance（草案）

agent-used 的目标是成为社区标准。当前由 Roy Tong 发起并维护，向以下治理形态演进：

## 决策机制（AUP）

标准变更通过 **Agent Usage Proposal (AUP)** 流程：

```text
Draft → Discussion → Accepted → Experimental → Stable → Deprecated
```

- 任何人均可提 AUP（Discussion 分类 RFCs）
- 合入 `spec/` 需要：2 个独立实现方表示可实施 + 维护者同意
- Experimental 至少运行一个外部验证周期后才可转 Stable

## 角色（未来）

- Maintainers：合入权限、版本发布
- Spec editors：AUP 的语义完整性
- Adapter owners：各自 adapter 的能力矩阵责任

## 数据治理

- 公开聚合数据的口径变更必须发 Measurement Change Notice
- Identity graph 的认领争议由 maintainers 仲裁，可申诉
