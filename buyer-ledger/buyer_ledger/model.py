"""对象模型：三级口径、证据引用、指纹与十进制字符串纪律.

对象映射（方向文档 §3.2，COMMERCIAL.md v0.4.3 的买方镜像）：
  SourceDocument   新增            原始文件及哈希、来源
  ProviderAccount  Provider        平台与账户（provider 作用域）
  ChargeLine       invoice-grade   平台实际收费行（账单事实层）
  UsageEvent       measurement     调用记录及用量（平台用量层）
  PricingPolicy    Pricing Policy  版本化价格（金额一律字符串）
  EvidenceRef      evidence req.   字段级溯源（文档 + 定位符 + 引文）
  ReviewStatus     不变量 17       verified / pending / undeterminable
"""

import hashlib
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
from typing import List, Optional

TIER_BILL_FACT = "bill_fact"
TIER_PLATFORM_USAGE = "platform_usage"
TIER_REFERENCE = "reference"
TIERS = (TIER_BILL_FACT, TIER_PLATFORM_USAGE, TIER_REFERENCE)

VERIFIED = "verified"
PENDING = "pending"
UNDETERMINABLE = "undeterminable"
REVIEW_STATUSES = (VERIFIED, PENDING, UNDETERMINABLE)


class LedgerError(ValueError):
    """账本输入违反硬纪律。"""


def dec(value, field_name="value"):
    """十进制字符串纪律：入库字符串、计算 Decimal（COMMERCIAL：防浮点误差）。"""
    if value is None or value == "":
        return None
    if isinstance(value, float):
        raise LedgerError(
            "refuse float in %s: pass a str (COMMERCIAL §3 价格一律字符串)" % field_name
        )
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise LedgerError("not a decimal string in %s: %r" % (field_name, value))
    if not result.is_finite():
        raise LedgerError("non-finite decimal refused in %s: %r" % (field_name, value))
    return result


def sha(*parts):
    payload = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _require(cond, msg):
    if not cond:
        raise LedgerError(msg)


@dataclass
class EvidenceRef:
    """字段级证据：数字来自哪份材料的哪个位置。"""

    document_id: str
    locator: str = ""      # 行号/单元格/页码/选择器
    quote: str = ""        # 原文摘录（截断存储）

    def as_dict(self):
        return asdict(self)


@dataclass
class SourceDocument:
    """一份原始材料（账单/用量导出/合同/截图）。幂等键 = content_hash（INV-1）。"""

    content_hash: str
    provider: str
    tier: str                        # TIERS 之一
    account_ref: str = ""
    doc_type: str = "bill"           # bill | usage_export | contract | receipt | other
    period: str = ""                 # "YYYY-MM"
    file_path: str = ""
    file_name: str = ""
    fetched_via: str = "manual_import"   # manual_import | browser_recipe:<id> | api
    fetched_at: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        _require(self.tier in TIERS, "tier must be one of %s" % (TIERS,))
        _require(self.provider, "provider required")
        if not self.content_hash:
            raise LedgerError("content_hash required")

    @property
    def id(self):
        # 同一零账单/模板可合法属于多个账户；文档身份必须包含完整作用域。
        return "doc-" + sha(self.content_hash, self.provider, self.tier,
                            self.account_ref, self.doc_type, self.period)[:16]


@dataclass
class ProviderAccount:
    provider: str
    account_ref: str
    currency: str = ""

    def __post_init__(self):
        _require(self.provider and self.account_ref, "provider/account_ref required")

    @property
    def id(self):
        return "acct-" + sha(self.provider, self.account_ref)[:16]


@dataclass
class ChargeLine:
    """账单事实层：平台实际收取的一行费用。指纹去重（INV-1），修订不删史（INV-2）。"""

    document_id: str
    provider: str
    currency: str
    amount: str                       # 十进制字符串；冲销行为负
    description: str = ""
    period: str = ""
    line_no: Optional[int] = None
    quantity: str = ""
    unit: str = ""
    unit_price: str = ""
    tax: str = ""
    charged_at: str = ""
    tool: str = ""                    # 能归因到 Tool/Capability 时填
    review_status: str = PENDING
    evidence: List[EvidenceRef] = field(default_factory=list)
    revision: int = 1
    supersedes: str = ""              # 纠错：指向被取代行
    reversal_of: str = ""             # 冲销：指向被冲销行
    note: str = ""

    def __post_init__(self):
        _require(self.review_status in REVIEW_STATUSES,
                 "review_status must be %s" % (REVIEW_STATUSES,))
        _require(bool(self.currency), "currency required; never assume a default")
        _require(self.revision >= 1, "revision must be >= 1")
        _require(not (self.supersedes and self.reversal_of),
                 "a row cannot both supersede and reverse another row")
        dec(self.amount, "amount")    # 校验可解析
        if self.reversal_of:
            _require(dec(self.amount, "amount") < 0, "reversal row amount must be negative")

    @property
    def fingerprint(self):
        return sha(self.provider, self.document_id, self.period,
                   self.line_no, self.description, self.amount, self.currency,
                   self.revision)

    @property
    def id(self):
        return "cl-" + self.fingerprint[:16]

    def amount_dec(self):
        return dec(self.amount, "amount")


@dataclass
class UsageEvent:
    """平台用量层：一次（或一批）调用记录。computed_charge 只有在适用价格后才有值。"""

    document_id: str
    provider: str
    billable_unit: str                # operation | token | record | gpu_second | ...
    quantity: str
    occurred_at: str = ""             # 时刻或账期
    period: str = ""
    account_ref: str = ""
    tool: str = ""
    capability: str = ""
    agent: str = ""
    project: str = ""
    currency: str = ""
    unit_price_applied: str = ""
    computed_charge: Optional[str] = None   # 复算估算层；无价格时必须为 None（INV-3）
    pricing_policy_id: str = ""
    review_status: str = PENDING
    evidence: List[EvidenceRef] = field(default_factory=list)
    revision: int = 1
    supersedes: str = ""
    reversal_of: str = ""
    note: str = ""

    def __post_init__(self):
        _require(self.review_status in REVIEW_STATUSES,
                 "review_status must be %s" % (REVIEW_STATUSES,))
        _require(self.revision >= 1, "revision must be >= 1")
        _require(not (self.supersedes and self.reversal_of),
                 "an event cannot both supersede and reverse another event")
        _require(dec(self.quantity, "quantity") is not None, "quantity required")
        if self.computed_charge is None and self.unit_price_applied:
            raise LedgerError("unit_price without computed_charge: apply via pricing, not by hand")
        if self.computed_charge is not None:
            dec(self.computed_charge, "computed_charge")
            _require(bool(self.currency), "currency required with computed_charge")
            _require(bool(self.pricing_policy_id),
                     "pricing_policy_id required with computed_charge")

    @property
    def fingerprint(self):
        source_locator = self.evidence[0].locator if self.evidence else ""
        return sha(self.provider, self.document_id, self.occurred_at, self.tool,
                   self.capability, self.billable_unit, self.quantity, self.period,
                   self.account_ref, self.agent, self.project, source_locator,
                   self.revision)

    @property
    def id(self):
        return "ue-" + self.fingerprint[:16]


@dataclass
class PricingPolicy:
    """版本化价格政策（镜像 COMMERCIAL Pricing Policy）。"""

    policy_id: str                    # 如 "com.example:pp-2026.1"
    version: str
    provider: str
    model: str                        # per_unit | flat | volume_tiered | free_quota | subscription
    currency: str = "USD"
    capability: str = ""              # 空表示该 provider 默认
    unit_price: str = ""              # per_unit/flat
    tiers: List[dict] = field(default_factory=list)   # [{unit_from, unit_price}]
    free_quota: str = ""              # free_quota 模式
    valid_from: str = ""
    valid_until: str = ""
    source_document_id: str = ""      # 价格证据（合同/价目页）
    note: str = ""

    MODELS = ("per_unit", "flat", "volume_tiered", "free_quota", "subscription")

    def __post_init__(self):
        _require(self.model in self.MODELS, "model must be %s" % (self.MODELS,))
        if self.model in ("per_unit", "flat"):
            _require(dec(self.unit_price, "unit_price") is not None,
                     "unit_price required for %s" % self.model)
        if self.model == "volume_tiered":
            _require(self.tiers, "tiers required for volume_tiered")
            for tier in self.tiers:
                _require(dec(tier.get("unit_from"), "tier.unit_from") is not None,
                         "tier.unit_from required")
                _require(dec(tier.get("unit_price"), "tier.unit_price") is not None,
                         "tier.unit_price required")
        if self.model == "free_quota":
            quota = dec(self.free_quota, "free_quota")
            _require(quota is not None and quota >= 0, "free_quota must be >= 0")
        for field_name in ("valid_from", "valid_until"):
            value = getattr(self, field_name)
            if value:
                try:
                    import datetime
                    datetime.date.fromisoformat(value + "-01" if len(value) == 7 else value)
                except ValueError:
                    raise LedgerError("%s must be YYYY-MM or YYYY-MM-DD" % field_name)
        if self.model == "subscription":
            # 订阅需分摊规则，M1 不自动计额 → 定价时标 pending（见 reconcile）
            pass

    def charge_for(self, quantity_dec):
        """按政策复算一笔用量；返回 (charge: Decimal|None, note: str)。

        无法确定性计算时返回 (None, 原因)——估算缺失不补零（INV-3）。
        """
        q = quantity_dec
        if self.model == "per_unit":
            return q * dec(self.unit_price, "unit_price"), ""
        if self.model == "flat":
            return None, "flat pricing needs an explicit event/period billing scope"
        if self.model == "volume_tiered":
            price = self.tier_unit_price(q)
            if price is None:
                return None, "quantity below first tier"
            return q * price, ""
        if self.model == "free_quota":
            quota = dec(self.free_quota, "free_quota")
            over = q - quota
            if over <= 0:
                return Decimal("0"), "within free quota"
            if dec(self.unit_price, "unit_price") is None:
                return None, "overage without unit_price"
            return over * dec(self.unit_price, "unit_price"), "overage beyond quota"
        if self.model == "subscription":
            return None, "subscription needs allocation rule (M1: manual review)"
        return None, "unknown model"

    def tier_unit_price(self, total_quantity):
        """按账期总用量选择 volume tier；不得对每个事件分别判档。"""
        if self.model != "volume_tiered":
            return None
        tiers = sorted(self.tiers, key=lambda t: dec(t["unit_from"], "tier.unit_from"))
        price = None
        for tier in tiers:
            if total_quantity >= dec(tier["unit_from"], "tier.unit_from"):
                price = dec(tier["unit_price"], "tier.unit_price")
        return price
