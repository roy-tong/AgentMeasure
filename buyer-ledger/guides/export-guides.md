# 导出与接入指南（Export & Intake Guides）

> 用途：收费/免费核验任务中，客户「给什么资料、我们怎么接」。配套能力：`python3 -m buyer_ledger preset list`。
> 状态口径与 `catalog/tools.json` 一致：**26 工具全部 cataloged，`live_bill_validated=0`** —— 本指南的表头模板基于 2026-10 公开文档，**尚未用真实客户账单验收**；首个真实导出到达时，先 `rule show` 核对表头命中情况，未命中走 `import --agent` 草案流程。

## 一个账期任务需要的材料（B 轨标准包）

| 材料 | 层 | 说明 |
|---|---|---|
| 账单/发票（PDF 或 CSV） | `bill_fact` 账单事实 | 金额、币种、账期；供应商官方出具 |
| 用量导出（CSV） | `platform_usage` 平台用量 | 平台控制台导出，逐日/逐模型 tokens 等 |
| 支付记录 | `reference` 参考 | 扣款凭证，用于对上账单事实 |
| 合同/订单/价格页 | `reference` 参考 | 判据来源，进判据清单（SOW 附件 A） |

## OpenAI

1. 用量导出：Platform → Usage → 选账期 → **Export CSV**（逐日聚合）。
2. 预设：`openai/usage_csv`（`platform_usage`，quantity=Total tokens）。
3. 接入：

```bash
python3 -m buyer_ledger preset apply openai/usage_csv --db ledger.db
python3 -m buyer_ledger import openai-usage.csv --provider openai \
  --tier platform_usage --doc-type usage --period 2026-10 --db ledger.db
```

4. 账单事实层：invoice PDF 暂无预设——PDF 导出物走 CDP 采集配方或人工登记后由 `--agent` 草案适配。
5. 若导出表头与预设不一致（列名/列序变化）：`import` 会提示无规则，改走
   `--agent` 草案 → `rule show` 人工核对 → `rule approve` → `parse`。**不要为凑命中改预设表头。**

## Anthropic

1. 用量导出：Console → Usage → 选账期 → **Export usage (CSV)**。
2. 预设：`anthropic/usage_csv`（`platform_usage`，quantity=Input tokens；如需按输出/缓存维度计量，复制预设改 quantity 列并另起 preset 名）。
3. 接入步骤同 OpenAI（provider 换 `anthropic`）。

## 国内线（火山方舟、阿里云百炼、Coze 等）

- 目录已编目 10 家的计费模型与计量单位（`catalog list --region cn`）；控制台导出物尚无预设与配方。
- 首个国内真实任务到达时：材料照「标准包」索要，格式走 `--agent` 草案流程；验收后将表头固化为此处新预设，并更新本指南。

## 纪律（与 README 账本纪律一致）

- usage 导出**只取用量事实**；金额一律来自 `bill_fact`（账单/发票），预设不映射供应商自述成本列（Cost 列留作交叉核对参考，不入账）。
- 预设规则 `created_via=preset`，可用 `rule show <fingerprint> --provider ... --doc-type usage --tier platform_usage` 复核与撤销。
- 每个新预设必须带合成 fixture 测试（`tests/test_provider_presets.py`），并在真实账单验收后更新 `status` 字段。
