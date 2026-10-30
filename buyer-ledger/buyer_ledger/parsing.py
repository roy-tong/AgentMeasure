"""CSV/TSV 规格化解析：LLM 只生成待审草案，批准后才允许确定性重放。"""

import csv
import datetime
import io
import json
import re
from decimal import Decimal

from .llm import LLMClient, extract_json
from .model import ChargeLine, EvidenceRef, LedgerError, UsageEvent, sha

PARSEABLE_TIERS = ("bill_fact", "platform_usage")
FINANCIAL_SOURCE_FIELDS = {"amount", "quantity", "unit_price", "tax"}
TOTAL_LABELS = ("total", "amount due", "invoice total", "grand total", "总计", "合计")


def clean_amount(raw):
    """清洗常见货币格式；不明确的小数/千分位逗号拒绝猜测。"""
    if raw is None:
        return ""
    s = str(raw).strip()
    for symbol in ("$", "€", "¥", "£", " ", " "):
        s = s.replace(symbol, "")
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1].strip()
    if s in ("", "-", "—"):
        return ""
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        if re.fullmatch(r"[+-]?\d{1,3}(,\d{3}){2,}", s):
            s = s.replace(",", "")
        elif re.fullmatch(r"[+-]?\d+,\d{1,2}", s):
            s = s.replace(",", ".")
        else:
            # 1,234 既可为千分位也可为三位小数；没有 locale 时不猜。
            raise LedgerError("ambiguous numeric format: %r" % raw)
    try:
        value = Decimal(s)
    except Exception:
        raise LedgerError("unparseable numeric value: %r" % raw)
    if not value.is_finite():
        raise LedgerError("non-finite numeric value: %r" % raw)
    return str(-value if negative else value)


def format_fingerprint(file_name, text):
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    delim = _detect_delimiter(file_name, text)
    rows = _csv_rows(text, delim)
    header = rows[0] if rows else []
    sig = "|".join(_norm_header(h) for h in header)
    return sha(ext, delim, sig)


def _norm_header(value):
    return str(value).lstrip("\ufeff").strip().casefold()


def _detect_delimiter(file_name, text):
    if file_name.lower().endswith(".tsv"):
        return "\t"
    if file_name.lower().endswith(".csv"):
        return ","
    return "\t" if text.count("\t") > text.count(",") else ","


def _csv_rows(text, delim):
    if delim not in (",", "\t"):
        raise LedgerError("delimiter must be comma or tab")
    return [row for row in csv.reader(io.StringIO(text), delimiter=delim)]


def validate_spec(spec, header=None):
    errors = []
    if not isinstance(spec, dict) or not isinstance(spec.get("columns"), dict):
        return ["spec must be an object with an object 'columns'"]
    cols = spec["columns"]
    allowed = ("description", "quantity", "unit_price", "amount", "currency",
               "period", "charged_at", "unit", "tool", "billable_unit",
               "occurred_at", "capability", "agent", "project", "account_ref",
               "line_no", "tax")
    for key, rule in cols.items():
        if key not in allowed:
            errors.append("unknown field mapping: %s" % key)
        if not isinstance(rule, dict):
            errors.append("mapping %s must be an object" % key)
            continue
        if ("col" in rule) == ("const" in rule):
            errors.append("mapping %s needs exactly one of col or const" % key)
            continue
        if key in FINANCIAL_SOURCE_FIELDS and "const" in rule:
            errors.append("financial field %s must come from a source column" % key)
        if "col" in rule and (not isinstance(rule["col"], str) or not rule["col"].strip()):
            errors.append("mapping %s col must be a non-empty string" % key)
        if header is not None and "col" in rule:
            normalized = {_norm_header(h) for h in header}
            if _norm_header(rule["col"]) not in normalized:
                errors.append("mapping %s references missing header %s" % (key, rule["col"]))
    tier = spec.get("tier")
    if tier not in PARSEABLE_TIERS:
        errors.append("spec.tier must be bill_fact or platform_usage")
    if spec.get("delimiter", ",") not in (",", "\t"):
        errors.append("delimiter must be comma or tab")
    header_row = spec.get("header_row", 0)
    if isinstance(header_row, bool) or not isinstance(header_row, int) or header_row < 0:
        errors.append("header_row must be a non-negative integer")
    skip = spec.get("skip_rows_containing", [])
    if not isinstance(skip, list) or any(not isinstance(x, str) for x in skip):
        errors.append("skip_rows_containing must be a list of strings")
    if tier == "bill_fact":
        if "col" not in cols.get("amount", {}):
            errors.append("bill_fact requires amount from a source column")
        if "currency" not in cols:
            errors.append("bill_fact requires an explicit currency mapping")
    if tier == "platform_usage":
        if "col" not in cols.get("quantity", {}):
            errors.append("platform_usage requires quantity from a source column")
        if not any(k in cols for k in ("unit", "billable_unit")):
            errors.append("platform_usage requires an explicit unit mapping")
    return errors


def _cell(row, header_index, rule):
    if "const" in rule:
        return str(rule["const"])
    col = rule.get("col")
    if col is None:
        return ""
    idx = header_index.get(_norm_header(col))
    if idx is None or idx >= len(row):
        return ""
    return str(row[idx]).strip()


def _period(value):
    try:
        datetime.date.fromisoformat(value + "-01")
    except (ValueError, TypeError):
        raise LedgerError("period must be YYYY-MM, got %r" % value)
    if len(value) != 7:
        raise LedgerError("period must be YYYY-MM, got %r" % value)
    return value


def _date(value, field_name):
    if not value:
        return ""
    try:
        datetime.date.fromisoformat(value[:10])
    except ValueError:
        raise LedgerError("%s must start with an ISO date: %r" % (field_name, value))
    return value


def _is_total_row(row):
    cells = [c.strip().casefold() for c in row if c.strip()]
    return any(c in TOTAL_LABELS or c.startswith("total ") for c in cells)


def apply_spec(file_name, text, spec, document, provider, period="", review_status="pending"):
    """解析整份文档；任何结构/关键字段错误都失败关闭，由调用方原子入账。"""
    errors = validate_spec(spec)
    if errors:
        raise LedgerError("invalid parse spec: %s" % "; ".join(errors))
    if spec["tier"] != document.tier or provider != document.provider:
        raise LedgerError("parse rule provider/tier does not match source document")
    delim = spec.get("delimiter", _detect_delimiter(file_name, text))
    rows = _csv_rows(text, delim)
    header_row = spec.get("header_row", 0)
    if header_row >= len(rows):
        raise LedgerError("header_row %d is outside document" % header_row)
    header = rows[header_row]
    errors = validate_spec(spec, header=header)
    if errors:
        raise LedgerError("parse spec incompatible with header: %s" % "; ".join(errors))
    normalized = [_norm_header(h) for h in header]
    if len(set(normalized)) != len(normalized):
        raise LedgerError("duplicate normalized headers are not allowed")
    header_index = {h: i for i, h in enumerate(normalized)}
    body = rows[header_row + 1:]
    skip = spec.get("skip_rows_containing", [])
    out_lines, out_events, notes = [], [], []
    stated_total = None
    cols = spec["columns"]

    for n, row in enumerate(body, start=1):
        if not any(c.strip() for c in row):
            continue
        joined = " ".join(row)
        total_row = spec["tier"] == "bill_fact" and _is_total_row(row)
        if total_row or any(token and token in joined for token in skip):
            if total_row:
                raw_total = _cell(row, header_index, cols["amount"])
                if not raw_total:
                    raise LedgerError("total row %d has no parseable amount in mapped column" % n)
                stated_total = Decimal(clean_amount(raw_total))
            continue
        locator = "row %d (csv record %d)" % (n, header_row + 1 + n)
        evidence = [EvidenceRef(document_id=document.id, locator=locator,
                                quote=joined[:120])]
        common = dict(document_id=document.id, provider=provider,
                      evidence=evidence, review_status=review_status)
        row_period = _period(period or _cell(row, header_index, cols.get("period", {})))
        if spec["tier"] == "bill_fact":
            amount = clean_amount(_cell(row, header_index, cols["amount"]))
            if amount == "":
                raise LedgerError("row %d has empty amount" % n)
            currency = _cell(row, header_index, cols.get("currency", {}))
            if not currency:
                raise LedgerError("row %d has no currency; no default is allowed" % n)
            out_lines.append(ChargeLine(
                amount=amount, currency=currency,
                description=_cell(row, header_index, cols.get("description", {})),
                period=row_period, line_no=n,
                quantity=clean_amount(_cell(row, header_index, cols.get("quantity", {}))),
                unit=_cell(row, header_index, cols.get("unit", {})),
                unit_price=clean_amount(_cell(row, header_index, cols.get("unit_price", {}))),
                tax=clean_amount(_cell(row, header_index, cols.get("tax", {}))),
                charged_at=_date(_cell(row, header_index, cols.get("charged_at", {})),
                                 "charged_at"),
                tool=_cell(row, header_index, cols.get("tool", {})), **common))
        else:
            quantity = clean_amount(_cell(row, header_index, cols["quantity"]))
            if quantity == "":
                raise LedgerError("row %d has empty quantity" % n)
            unit_rule = cols.get("billable_unit", cols.get("unit", {}))
            billable_unit = _cell(row, header_index, unit_rule)
            if not billable_unit:
                raise LedgerError("row %d has empty billable unit" % n)
            out_events.append(UsageEvent(
                billable_unit=billable_unit, quantity=quantity,
                occurred_at=_date(_cell(row, header_index, cols.get("occurred_at", {})),
                                  "occurred_at"),
                period=row_period,
                account_ref=(_cell(row, header_index, cols.get("account_ref", {}))
                             or document.account_ref),
                currency=_cell(row, header_index, cols.get("currency", {})),
                tool=_cell(row, header_index, cols.get("tool", {})),
                capability=_cell(row, header_index, cols.get("capability", {})),
                agent=_cell(row, header_index, cols.get("agent", {})),
                project=_cell(row, header_index, cols.get("project", {})), **common))

    if not out_lines and not out_events:
        raise LedgerError("parse rule produced no ledger rows; review or regenerate it")
    constraint = None
    if stated_total is not None and out_lines:
        currencies = {line.currency for line in out_lines}
        line_sum = sum((line.amount_dec() for line in out_lines), Decimal("0"))
        constraint = {"stated_total": str(stated_total), "line_sum": str(line_sum),
                      "match": len(currencies) == 1 and line_sum == stated_total}
        if not constraint["match"]:
            for line in out_lines:
                line.review_status = "pending"
            notes.append("CONSTRAINT FAILED: Σ lines %s ≠ stated total %s — review required"
                         % (line_sum, stated_total))
    return {"charge_lines": out_lines, "usage_events": out_events,
            "notes": notes, "constraint": constraint}


AGENT_SYSTEM = (
    "你是账单解析规格生成器。根据 CSV 表头输出 JSON 解析规格，只映射列，不计算金额。"
    "可用字段：description, quantity, unit_price, amount, currency, period, charged_at, "
    "unit, tool, billable_unit, occurred_at, capability, agent, project, account_ref, tax。"
    "每个字段只能是 {\"col\": \"原表头\"}；currency/unit 等非金额字段可用 const。"
    "amount/quantity/unit_price/tax 禁止 const。bill_fact 必须映射 amount/currency；"
    "platform_usage 必须映射 quantity/unit。输出含 tier,delimiter,header_row,columns。"
)


def agent_generate_spec(file_name, text, provider, doc_type, client: LLMClient,
                        sample_rows=0):
    """默认仅发送表头；sample_rows>0 是调用方对原始样例外发的显式选择。"""
    delim = _detect_delimiter(file_name, text)
    rows = _csv_rows(text, delim)
    if not rows:
        raise LedgerError("empty CSV")
    preview_rows = rows[:1 + max(0, sample_rows)]
    preview = json.dumps(preview_rows, ensure_ascii=False)
    reply = client.chat(
        AGENT_SYSTEM,
        "provider=%s doc_type=%s\nCSV 表头%s：\n%s" %
        (provider, doc_type,
         "及已授权样例" if sample_rows else "（无原始数据行）", preview))
    spec = extract_json(reply)
    spec.setdefault("delimiter", delim)
    spec.setdefault("header_row", 0)
    spec.setdefault("skip_rows_containing", [])
    errors = validate_spec(spec)
    if errors:
        raise LedgerError("agent spec invalid: %s" % "; ".join(errors))
    header_row = spec["header_row"]
    errors = validate_spec(spec, header=rows[header_row] if header_row < len(rows) else None)
    if header_row >= len(rows):
        errors.append("header_row is outside document")
    if errors:
        raise LedgerError("agent spec invalid: %s" % "; ".join(errors))
    # 完整 dry-run 在保存草案前执行；pending 状态不会生成权威结论。
    from .model import SourceDocument
    probe_doc = SourceDocument(content_hash=sha(text), provider=provider,
                               tier=spec["tier"], period="2000-01")
    apply_spec(file_name, text, spec, probe_doc, provider, period="2000-01")
    golden = preview_rows[1:3] if sample_rows else []
    return spec, golden


def replay_golden(text, spec, golden):
    rows = _csv_rows(text, spec.get("delimiter", ","))
    header_line = rows[spec.get("header_row", 0)] if rows else None
    return delim_join([header_line] + golden if header_line else golden,
                      spec.get("delimiter", ","))


def delim_join(rows, delim):
    out = io.StringIO()
    writer = csv.writer(out, delimiter=delim)
    for row in rows:
        writer.writerow(row)
    return out.getvalue()
