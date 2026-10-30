# Buyer Ledger — 买方侧统一费用账本与对账审查

> **Status: pre-M1。核心机制与合成端到端流程已测试；真实平台、真实账期与跨周会话仍未验证。**
> 本目录是独立的买方侧产品线；`product/MVP.md` 的 Provider 侧范围不受影响。

**一句话**：把多平台账单与用量记录收进本地账本，按账户和币种分别回答“平台收了多少、按已确认价格应是多少、哪些记录还无法判断”。

## 已强制的账本纪律

| 机制 | 当前实现 |
|---|---|
| 幂等 | 同内容、同语义文档与源行重复导入不重复入账；不同账户/Agent/源行不会被误去重 |
| 原子导入 | 一份文档的全部行在一个事务内入账；中途失败可重试，不留半份数据 |
| 修订与冲销 | 修订必须递增且不可分叉/跨账户/跨平台；冲销不能超出原行，Usage 冲销必须等值反向 |
| 对账粒度 | `period + provider + account + currency`；不同账户和币种不相加 |
| 三级口径 | 账单事实、平台用量、复算估算分列；部分复算只显示小计，不出正式差额 |
| 审核阻断 | `pending / undeterminable` 记录存在时输出 `review_required`，不输出 matched 或经济差异 |
| 材料覆盖 | 已登记但未解析/待审的账期文档也阻断确定性结论；parseable 导入强制明确 YYYY-MM |
| 定价 | 只选覆盖事件日的唯一政策；免费额度/阶梯价按计费作用域聚合；同版本政策不可变；旧失效估算会撤回 |
| 快照 | 每次对账原子替换完整账期快照；重跑不会残留已失效金额 |
| 证据 | 文件哈希、SourceDocument、源行定位、采集 run/recipe/audit 元数据可下钻 |
| 工具能力目录 | 26 个国内外工具，记录买家/卖家角色、计费模型、计量单位、账单来源、审计能力和验证级别；报告自动披露未知 provider |
| 双视角 | 买家费用核验；卖家计量完整性。未计价/未关联用量不得直接宣称漏收收入 |
| CDP 采集 | 附着用户自行启动的本地 Chrome，复用受审配方、域名/下载校验和同一入账管线；不接收密码 |

## 安装与验证

```bash
cd buyer-ledger
python3 -m unittest discover -s tests -t .     # 当前 106 项测试

# 可选：真实浏览器采集
pip install playwright && playwright install chromium

# 可选：OpenAI 兼容 LLM，仅用于首次生成解析草案
export VEROVO_LLM_BASE_URL=... VEROVO_LLM_API_KEY=... VEROVO_LLM_MODEL=...
```

核心仅使用 Python ≥3.9 标准库。LLM 端点必须使用 HTTPS；仅本机端点允许 HTTP。

## 文件导入与 Agent 首次适配

```bash
B="python3 -m buyer_ledger --db ledger.db"

$B init

# 查看国内外工具支持矩阵（不会因为“已编目”就冒充已接通）
$B catalog summary
$B catalog list --region cn --role buyer
$B catalog list --region global --role seller
$B catalog show anthropic
$B catalog coverage --period 2026-10
# 字段含义与新增工具规则见 catalog/README.md

$B import bill.csv --provider X --tier bill_fact --period 2026-10 --account A

# 新版式需要 Agent 适配：只生成草案，不直接入账
$B import bill.csv --provider X --tier bill_fact --period 2026-10 --account A --agent

# 审核规格后显式批准，再解析原文件
$B rule show <fingerprint> --provider X --doc-type bill --tier bill_fact
$B rule approve <fingerprint> --provider X --doc-type bill --tier bill_fact
$B parse --document <doc-id>

$B policy policy.json
$B price --provider X --period 2026-10
$B reconcile --period 2026-10
$B report --period 2026-10 --out report.md
$B report --period 2026-10 --perspective seller --out seller-audit.md
$B show <row-id>
$B status

# 后续账期：资料和规则就绪后，一条命令完成复算、对账与报告
$B run --period 2026-10 --out report.md
```

Agent/程序边界：

- 默认**不向 LLM 发送原始数据行或文件名，仅发送表头及 provider/doc_type**；金额、数量、单价、税额禁止由 LLM 常量生成。
- 草案先经过 schema、真实表头和整份样例 dry-run，再存为 `pending`；必须显式 `rule approve` 才可重放。
- 规则按 `provider + doc_type + tier + format fingerprint` 隔离，不能跨平台或跨资料类型误用。
- 同版式后续重放不调用 LLM。重解析会核对文件哈希，源文件被替换后拒绝绑定到旧证据。
- 支持 UTF-8 CSV/TSV，单文件上限 20 MiB；其他编码需先无损转换。总额行从映射的金额列校验，不再按字符串长度猜数字。

## 支持案例（公开计费研究，不是客户案例）

- **扣子 Coze**：一个企业账单里同时有积分、模型、官方插件、三方插件现金、音视频和存储；积分页是预估值，最终以火山账单为准。适合验证“平台代收 + 积分 + 现金”混合账。
- **Anthropic**：Token、Web Search、Code Execution、Managed Agents session-hour 四项并列；搜索费不含处理结果的 Token。适合验证一个 Agent 任务对应多条费用。
- **高德 / 和风天气**：月配额、服务分组、阶梯价、流量包和最低计费并存。适合验证“按次/按万次 + 配额 + 阶梯”的复算。
- **Browserbase / E2B**：浏览器小时、代理流量、CPU/内存/运行秒数都是独立计量。适合验证时间型和资源型用量。
- **阿里云 OCR / 百度 OCR / AWS Textract / Azure Document Intelligence**：按成功调用或页数、免费额度、预置/自定义模型、预付费包混合。适合验证按页计费和资源包抵扣。

这些是 2026-10-29 公开价格与文档的研究样本；没有客户授权、实际账单或退款结果。

## 公开账单不满研究（探索性）

SURE 1.6 研究从 1,949 条公开发现中审读 150 条，得到 66 条严格证据；其中 credits 到期/清零 22、未预期扣费/硬上限失效 9、自动充值 8、计量不一致 6、退款受阻 5，涨价仅 2。审计 12 门中 3 门未过（仅 3/18 vendor、单一地区、反证 7 条），结论上限 **exploratory**。

这不是投诉率或市场验证。中文平台样本为 0；Coze/百炼/方舟/高德/和风不能据此下结论。发现层已扩展到 **50,000 条**唯一公开记录（HN 49,090）；严格证据仍为 66，审读仍为 150。50k 压力测试：H1 证据形状支持但提及量接近，H2 不支持，H4 关键词初筛降级率 71.6%。摘要见 [COMPLAINTS-20261029.md](COMPLAINTS-20261029.md)。

## L1 浏览器采集

```bash
$B recipe validate recipes/examples/*.json
$B recipe dryrun recipes/examples/*.json
$B session login --recipe recipe.json --account A
$B session status --recipe recipe.json --account A
$B fetch --recipe recipe.json --period 2026-10 --account A
$B audit verify <trail.jsonl>
```

- 客户在专用浏览器档案中亲手登录；同平台不同账户使用不同 profile。
- 配方限制 HTTPS 与 `allowed_hosts`，context 在导航请求前拦截越源跳转，每个动作前重查当前页；下载来源 URL 也在保存/入账前校验。
- 下载和截图只允许安全 basename，写入独立 run 目录。
- 下载记录关联 `run_id / recipe_sha256 / document_id / audit_path`；本地审计文件权限设为 `0600`，目录为 `0700`。
- 采集后若仍需解析，命令明确返回 `needs_parse`，不会把“0 条账本行”显示为完整成功。
- 反自动化或步骤失败转人工交接，不绕过防护。

### 附着现有 Chrome（CDP）

用于没有 API、但用户愿意在自己的浏览器会话中导出账单的平台。先由用户启动一个**专用** Chrome 档案并打开本地调试端口：

```bash
# macOS 示例；只在专用 profile 上使用，不要对日常浏览器启用
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.verovo/chrome-cdp"

# 用户亲手登录后，系统只检查 CDP 和设备信息
$B session cdp --endpoint http://127.0.0.1:9222

# 附着会话执行同一份受审配方，下载物仍进入账本
$B fetch --recipe recipe.json --period 2026-10 \
  --cdp http://127.0.0.1:9222 --account A

# 解析规则已批准时，下载后直接复算、对账并出报告
$B fetch --recipe recipe.json --period 2026-10 \
  --cdp http://127.0.0.1:9222 --account A --analyze --out report.md
```

- CDP endpoint 只允许 loopback，且拒绝 URL 中的账号、query、fragment；不会把调试端口暴露到网络。
- 附着时不复制密码、不代填、不关闭用户的整个浏览器；只创建并关闭本次运行自己的页面。
- `run_start` 审计记录包含 `transport=cdp`，配方、来源校验、下载来源校验和入账流程与独立 profile 相同。
- 任何能访问本地调试端口的进程都可以控制该浏览器；使用一次性专用 profile，运行后关闭。CDP 不是反自动化绕过手段。

**安全边界必须准确理解：**配方是可信代码，不是安全沙箱。`click` 可能产生服务端副作用，因此“动作白名单”不等于结构性只读。只使用经过审核的配方，并优先使用平台只读角色/专用账户。哈希链只检查审计记录内部一致性；没有签名或外部信任锚，不能证明抗主动篡改，也不是执行回放器。

## 当前验证状态

| 项目 | 状态 |
|---|---|
| 106 项单元/回归测试 | ✅ 通过，覆盖金额、账户、币种、修订、定价、解析审批、原子恢复、能力目录、双视角与浏览器运行时边界 |
| 合成 CSV 的 CLI 导入→复算→对账→报告 | ✅ 已端到端运行，重复导入幂等 |
| 26 个工具的账单/计量维度编目 | ✅ 目录与未知 provider 披露已测试；不代表已接通 |
| CDP loopback 附着、下载与自动分析 | ✅ 本机 Chrome 156 + 本地 HTTPS 合成账单：下载→入账→`--analyze` 出报告；未做真实平台账单后台验收 |
| 3–5 个真实平台、≥1 个无 API 平台 | ⬜ 未开始 |
| 真实平台跨周会话、过期交接 | ⬜ 机制存在，未做跨周验收 |
| 真实任务 ≥80% 步骤确定性执行 | ⬜ 尚无真实运行样本和分母 |
| 真实账单金额一致性与证据被供应商接受 | ⬜ 未验证 |
| 浏览器执行回放、抗主动篡改 | ⬜ 未实现；当前仅有配方重放与审计链一致性检查 |

## 明确不在当前范围

- XLSX/PDF 原生解析、多币种汇率换算、支付/退款执行。
- 通用自动接入所有平台；每个真实平台仍需配方、条款与账户确认。
- 把平台总账强行分摊到单次 Tool 调用；无法关联项必须保留。
