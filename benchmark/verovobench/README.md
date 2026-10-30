# VerovoBench — 构造式 ground truth 计费错误基准（论文线卡 A）

按 taxonomy v2（16 类错误、四族：单位语义 / 价格应用 / 信用调整 / 承诺结构）生成
带确定性 ground truth 的对账基准实例。核心思路：**先算对，再埋错**——
`correct_invoice` 按 profile 规则算出唯一正确的账单，注入器对账单做自然形态变异，
变异位置与预期差异即 ground truth，因此不需要人工标注，也不依赖被测系统。

## 架构

```
┌──────────────────────────┐    ┌─────────────────────────────────┐
│ taxonomy.json（16 类 v2） │    │ SEED_PROFILES（7 厂商画像）       │
│ unit / pricing /          │    │ 参数已扰动去污染（单价一律不动）     │
│ credit / commitment       │    └───────────────┬─────────────────┘
└─────────────┬────────────┘                    │
              ▼                                 ▼
       ERROR_INJECTORS（16 个）◄────── generator.py ──► synth_events()
              │                   correct_invoice()    确定性事件流
              │                   build_instance()     （rng 由 profile+seed 派生）
              ▼                           │
   ┌──────────────────────────────────────┴─────────────────────┐
   │ verovobench-instances.jsonl（每行 1 实例）                       │
   │  = {invoice, profile_doc, ground_truth, seed_key, ...}      │
   └──────────┬──────────────────────────────────┬───────────────┘
              ▼                                  ▼
      eval_reconciler.py                  validate.py
      LLM 对账员评测接口 + 评分              seed_key 复现 / 无 NaN / 类分布校验
      （call_llm 为占位，不调外部模型）
```

- **profile → correct_invoice → inject → instance**：每个实例的 invoice 是"正确账单
  做了一次类语义变异"的结果；`profile_doc`（对账员可读的规则文档）随实例携带。
- **可独立复现**：实例仅由 `(seed_key, gen_seed, n_events)` 决定（rng 从
  `random.Random(f"inj|{seed_key}|{seed}")` 派生，不依赖生成顺序），validate.py
  据此逐实例重建比对。
- **ground_truth 结构**：`{class, family, status, line_refs[], expected, actual,
  direction(overcharge/undercharge/semantic_mislabel), delta_amount, note}`。

## 双实现隔离声明

- 本目录三个脚本（generator / validate / eval_reconciler）与仓库内 reconcile CLI、
  计费引擎**零共享代码**：不 import 其任何模块，仅用 Python 标准库。
- 评测与生成全程**不调用 subprocess**、不访问网络；`eval_reconciler.call_llm()`
  为 API 占位（返回 None 按空预测处理），接入真实模型时只替换该函数。
- **单价保持扰动值不动**：SEED_PROFILES 既有价格一律未改。v0.2 仅新增缺失的
  金额常数（EPSILON `price=0.29`、ZETA `price_per_credit=0.11`、ETA 语音
  `0.06/分钟`、聊天 `0.13/轮`、通行成本基数 `0.02/分钟`，均标注 `# added v0.2`）；
  非价格结构常数（BETA 承诺档容量 30、GAMMA 信用期初 200、ZETA 含额 150）集中在
  generator.py 的 `RULES`，与价格语义分离。

## 复现命令

```bash
cd 代码仓库/benchmark/verovobench

python3 generator.py --smoke                     # 冒烟：2 profile × 16 类 × 2
python3 generator.py --full --seed 42            # 全量：7 profile × 16 类 × 50 = 5600 实例
python3 validate.py                              # 校验（复现/NaN/类分布/结构）
python3 eval_reconciler.py --reconciler null     # 空预测基线，打通评测链路

# 调规模（每类总数 = per_class × 7）：
python3 generator.py --full --seed 7 --per-class 10 --n-events 120 --out bigger.jsonl
python3 validate.py --instances bigger.jsonl
```

v0.2 全量默认（seed 42）：**5600 实例 = 7 profile × 16 类 × 50**，每类 350 条、
类分布完全均匀；单实例约 15KB（含完整 invoice 与 profile_doc），文件约 90MB。

## 错误类适用矩阵

注入器在语义不成立的 profile 上返回 `not_applicable`（invoice 保持正确、不计分），
类计数仍保持均匀。v0.2 的适用范围：

| 类 | 适用 profile | 说明 |
|---|---|---|
| E01–E09、E11、E13–E16 | 全部 7 个 | 通用变异（含"机制不存在却出现该行"形态） |
| E10 取整错误 | 仅 ETA、EPSILON | 只有这两个 profile 有语音时长取整语义（60 秒向上取整） |
| E12 信用未应用 | 仅 ALPHA、BETA、ZETA | 只有这三个 profile 有信用/额度机制 |

seed 42 全量：5150 injected + 450 not_applicable（E10×250、E12×200）；
方向分布：3272 overcharge / 1216 undercharge / 662 semantic_mislabel。

## correct_invoice 覆盖的 profile 核心语义

| profile | 语义 |
|---|---|
| ALPHA | per_resolution、同会话重开冲减为 0、试用期不计、conditional handoff、最低承诺下限 41 |
| BETA | 每 agent 7 次免费额度、committed/PAYG 双价分层、messaging 2h / email 72h 切分、仅 AI 处理计费 |
| GAMMA | per_conversation、min_user_messages、无 AI 回复不计、15 分钟切分、同客户同渠道 15 分钟去重、自动充值信息行 |
| DELTA | ticket + ai_interaction 双单位、spam 过滤、email 10 天 / 其他 3 天切分、72h 转人工窗口 AI 费冲减 |
| EPSILON | inputs 每 50 次 1 会话、24h 窗口切段、语音每 10 分钟 1 会话（60 秒向上取整）、handoff 只计一次、Transformer 每 50 次折 1 会话 |
| ZETA | action 信用成本 basic 1 / advanced 3、150 含额内免费、额度过期不结转不退款 |
| ETA | 语音按分钟 60 秒向上取整、聊天按轮且欢迎轮免费、多 agent 分别计量、mark 渠道 15% 通行成本加价 |

## eval_reconciler 输出 schema（对账员契约）

```json
{"discrepancies": [
  {"error_class": "E01_unit_misclassification",
   "line_ref": {"line_index": 3, "event": "e00083"},
   "confidence": 0.0,
   "explanation": "..."}
]}
```

评分口径：类召回（预测类集合含 ground truth 类）、精确匹配率（且仅 1 条预测）、
预测精确率、行引用命中率（event 对上 ground_truth.line_refs）、命中置信度均值。
`not_applicable` 实例不计分。接入真实 LLM：实现 `call_llm(prompt)` 后用
`--reconciler llm` 运行。

## 已知限制（v0.2）

- 单计费周期（2031-01）；`cross_month_double_count`、多期账单待 v0.3。
- 对账员只看到 invoice + profile_doc，看不到原始事件流；错误可从账单内部一致性
  （如 qty 与行内 segments/duration/attempts 主张不一致）与规则文档推出，但
  E02/E03 在切分类 profile 上存在天然类间模糊（计入评分难度，非标注噪声）。
- oracle 判定偏差（llm_internal 边界）按 taxonomy notes 不作为生成类，由
  Oracle 探测实验独立测量（RQ6）。
