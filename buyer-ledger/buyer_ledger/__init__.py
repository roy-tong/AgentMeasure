"""Verovo Buyer Ledger — 买方侧统一费用账本与对账审查（M1）.

方向文档: 产品和技术/产品规划/Verovo-买方侧统一费用账本与对账-产品方向-20261029.md
（仓库外项目工作区）。三条硬纪律（对应方向文档 §3.1 / §3.2 / §4.2）：

INV-1 幂等: SourceDocument 按 content_hash + provider + tier + account +
     doc_type + period 标识；同一作用域只入账一次，同一内容可用于不同账户。
INV-2 修订不删史: 纠错走 revision/supersedes，冲销走 reversal_of（负额行），
     汇总只计未被取代的行。
INV-3 三级口径不混算: 账单事实 / 平台用量 / 复算估算在任何汇总中分别列示，
     估算不冒充事实，缺失不补零。
INV-6 不代填凭证: 配方动作白名单不含文本输入，系统无法代填密码；配方仍是
     可信代码，click 可能产生服务端副作用，不能宣称为只读沙箱。
"""

__version__ = "0.1.0"

from .model import (  # noqa: F401
    EvidenceRef,
    PricingPolicy,
    ProviderAccount,
    SourceDocument,
    ChargeLine,
    UsageEvent,
    TIER_BILL_FACT,
    TIER_PLATFORM_USAGE,
    TIER_REFERENCE,
    VERIFIED,
    PENDING,
    UNDETERMINABLE,
)
