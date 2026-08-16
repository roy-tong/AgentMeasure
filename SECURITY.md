# Security

## 报告漏洞

不要公开披露。发邮件到 GitHub Security Advisories（Security → Report a vulnerability），
或开 private issue。

## 安全承诺

- 本项目不采集内容（prompt/input/output/path）；泄漏是 bug，不是特性
- 伪匿名标识按月轮换（unlinkability）；DO_NOT_TRACK=1 全程生效
- 验签 fail-closed：无法验证的签名视为无效
- 威胁模型：spec/threat-model.md（T1-T10 及缓解）

## 已知边界

- E1 签名只证明来源与完整性，不证明真实使用（signature ≠ usage truth）
- E2 无法防御双侧合谋（需要 E3 平台证明）
