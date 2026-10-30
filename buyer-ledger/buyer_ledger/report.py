"""对账报告：账户/币种分列，待审与部分估算不形成正式差额。"""

CLASS_LABELS = {
    "matched": "账单与完整复算一致（容差内）",
    "overcharge_suspected": "实收高于完整复算——多收嫌疑（待证据）",
    "undercharge_observed": "实收低于完整复算",
    "estimate_only": "无账单事实，仅完整复算估算",
    "insufficient_evidence": "证据不足：无法复算（缺失不补零）",
    "usage_unpriced": "用量存在但无适用价格政策，未计估算",
    "estimate_incomplete": "仅部分用量已计价；小计不是完整复算，不出正式差额",
    "review_required": "存在待确认或无法判定记录；不出确定性差异结论",
}


def _value(value):
    return "—" if value in (None, "") else str(value)


def _money(value, currency):
    if value in (None, ""):
        return "—"
    return "%s %s" % (value, currency or "币种未知")


def _md(value):
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _unpriced(detail):
    by_unit = detail.get("unpriced_usage_by_unit") or {}
    if by_unit:
        return ", ".join("%s %s" % (v, k) for k, v in by_unit.items())
    return _value(detail.get("unpriced_usage_qty"))


def render_report(period, results, documents_count=0, ledger_path="",
                  catalog_coverage=None, perspective="buyer"):
    lines = []
    add = lines.append
    if perspective == "seller":
        add("# 卖方计量完整性审查 · %s" % period)
        add("")
        add("> 从卖家视角核对“实际计量 / 可计费用量 / 账单收入 / 未关联用量”。"
            "未关联只是证据缺口，不自动等于漏收或收入损失。")
    else:
        add("# 买方侧统一费用账本 · 对账报告 · %s" % period)
        add("")
        add("> **账单事实 / 平台用量 / 复算估算分列。**估算不冒充账单，缺失不补零；"
            "不同账户与币种不相加；待审核记录和部分复算不产生 matched 或正式差额。")
    add("")
    if ledger_path:
        add("- 账本：`%s`" % _md(ledger_path))
    add("- 本账期文档：%d 份" % documents_count)
    add("- 视角：%s" % ("卖家计量完整性" if perspective == "seller" else "买家费用核验"))
    add("")

    add("## 一、账单事实（平台记录）")
    add("")
    add("| 平台 | 账户 | 行数 | 合计 | 待确认 | 无法判定 |")
    add("|---|---|---:|---:|---:|---:|")
    for r in results:
        add("| %s | %s | %d | %s | %d | %d |" % (
            _md(r["provider"]), _md(r.get("account_ref")) or "—",
            r["detail"]["bill_fact_lines"], _money(r["bill_total"], r.get("currency")),
            r["detail"].get("review_pending_lines", 0),
            r["detail"].get("undeterminable_lines", 0)))
    add("")
    unparsed_all = []
    for r in results:
        for doc in r["detail"].get("unparsed_documents", []):
            unparsed_all.append((r["provider"], r.get("account_ref", ""), doc["id"],
                                 doc["tier"], doc.get("file_name", "")))
    if unparsed_all:
        add("### 未解析/待审文档（阻断确定性结论）")
        add("")
        add("| 平台 | 账户 | 文档 ID | 类型 | 文件 |")
        add("|---|---|---|---|---|")
        for row in unparsed_all:
            add("| %s | %s | `%s` | %s | %s |" % tuple(_md(x) for x in row))
        add("")

    add("## 二、复算估算（按价格政策推算）")
    add("")
    add("| 平台 | 账户 | 已计价事件 | 未计价用量（分单位） | 小计 | 完整性 |")
    add("|---|---|---:|---|---:|---|")
    for r in results:
        complete = r.get("recount_complete", r["detail"].get("recount_complete", True))
        add("| %s | %s | %d | %s | %s | %s |" % (
            _md(r["provider"]), _md(r.get("account_ref")) or "—",
            r["detail"]["priced_usage_events"], _md(_unpriced(r["detail"])),
            _money(r["recount_total"], r.get("currency")),
            "完整" if complete and r["recount_total"] is not None else "不完整/不可用"))
    add("")

    add("## 三、差异与结论")
    add("")
    add("| 平台 | 账户 | 实收 | 复算 | 正式差异 | 分类 |")
    add("|---|---|---:|---:|---:|---|")
    for r in results:
        add("| %s | %s | %s | %s | %s | %s |" % (
            _md(r["provider"]), _md(r.get("account_ref")) or "—",
            _money(r["bill_total"], r.get("currency")),
            _money(r["recount_total"], r.get("currency")),
            _money(r["variance"], r.get("currency")),
            CLASS_LABELS.get(r["variance_class"], r["variance_class"])))
    add("")

    unlinked_all = []
    for r in results:
        for c in r["detail"]["unlinked_charge_lines"]:
            unlinked_all.append((r["provider"], "账单行", c["id"],
                                 c.get("description", ""), c.get("amount", "")))
        for u in r["detail"]["unlinked_usage_events"]:
            unlinked_all.append((r["provider"], "用量", u["id"], u.get("tool", ""),
                                 "%s %s" % (u.get("quantity", ""), u.get("unit", ""))))
    add("## 四、无法关联项")
    add("")
    if unlinked_all:
        add("| 平台 | 类型 | ID | 说明 | 数量/金额 |")
        add("|---|---|---|---|---|")
        for row in unlinked_all:
            add("| %s | %s | `%s` | %s | %s |" % tuple(_md(x) for x in row))
    else:
        add("（本账期无无法关联项）")
    add("")
    add("## 五、工具支持与计量覆盖")
    add("")
    if catalog_coverage:
        add("- 能力目录版本：%s" % catalog_coverage["catalog_version"])
        add("- 账本中已编目工具：%d；未编目：%d" %
            (catalog_coverage["known_count"], catalog_coverage["unknown_count"]))
        add("")
        add("| 账本 provider | 目录工具 | 地区 | 计费类型 | Reader | 真实账单验证 |")
        add("|---|---|---|---|---|---|")
        for item in catalog_coverage["known"]:
            add("| %s | %s | %s | %s | %s | %s |" % (
                _md(item["input"]), _md(item["name"]), item["region"],
                _md(", ".join(item["billing_models"])), item["reader_status"],
                item["live_bill_status"]))
        if catalog_coverage["unknown"]:
            add("")
            add("未编目的 provider（不能据此声称格式或计费规则已支持）：")
            for name in catalog_coverage["unknown"]:
                add("- `%s`" % _md(name))
        if not catalog_coverage["known"]:
            add("（本账期没有已编目 provider）")
    else:
        add("（未启用能力目录）")
    add("")

    if perspective == "seller":
        add("### 卖方计量完整性")
        add("")
        add("| 平台 | 账户 | 用量事件 | 已计价 | 未计价 | 未关联用量事件 | 账单行 |")
        add("|---|---|---:|---:|---:|---:|---:|")
        for r in results:
            detail = r["detail"]
            add("| %s | %s | %d | %d | %s | %d | %d |" % (
                _md(r["provider"]), _md(r.get("account_ref")) or "—",
                detail["usage_events"], detail["priced_usage_events"],
                _md(_unpriced(detail)), len(detail["unlinked_usage_events"]),
                detail["bill_fact_lines"]))
        add("")
        add("> 未计价/未关联用量必须保留为缺口；不得直接宣称为漏收收入，"
            "也不得在没有账单事实时生成应收金额。")
        add("")

    add("## 六、下钻说明")
    add("")
    add("- 使用 `python3 -m buyer_ledger show <row-id>` 查看 SourceDocument、原始字段与证据定位。")
    add("- `audit verify` 仅检查审计链记录内部哈希一致性；不等于抗主动篡改或真实运行证明。")
    add("- `catalog coverage --period` 可单独查看已编目工具和未知 provider。")
    add("")
    return "\n".join(lines)
