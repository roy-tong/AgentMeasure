# Contributing

agent-used 是一个 measurement 标准项目。**问题定义和测量严谨性优先于功能数量。**

## 参与方式

| 想做什么 | 入口 |
| --- | --- |
| 讨论测量语义（什么算 usage / evidence / identity） | GitHub Discussions |
| 提出标准变更 | 先 Discussion 形成共识，再提 PR 修改 `spec/` |
| 修 adapter bug | Issue（adapter-bug 模板）→ PR |
| 报告测量偏差 | Issue（measurement-discrepancy 模板）——不同观测面数据不一致的实证 |
| 认领项目身份 | registry/project-identity PR（identity-claim 模板） |

## 原则（不接受违反）

1. **Evidence is derived, never self-declared**——adapter 不得自设证据等级
2. **Observation ≠ Invocation**——adapter 只产生 observation
3. **Raw stays local**——伪匿名必须在落盘前、内存内完成
4. **能力声明诚实**——官方 schema 没有的字段，宁可 unknown 不推断
5. **fail-closed**——时间解析失败、验签失败 → 拒绝，不假设

## 提交规范

- PR 必须通过 `conformance.py` 与 CI（.github/workflows/conformance.yml）
- 新增 adapter 必须附 capability matrix 更新（docs/adapters.md）
- 隐私相关改动必须附泄漏测试
