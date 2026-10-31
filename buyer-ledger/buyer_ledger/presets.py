"""内置导出格式预设（provider presets）。

目的：把「客户第一次交来的真实导出」接到已测试的解析路径上。每条预设是一份
在仓库里评审过、带测试的解析规则；表头（大小写不敏感、按列序）与真实导出
完全一致时，`preset apply` 登记的规则会被 `import` 直接确定性重放。

诚实边界（与 catalog 的 live_bill_validated=0 同口径）：
- 预设基于 2026-10 公开文档的导出表头模板 + 合成 fixture，**尚未用真实客户账单验收**；
- 真实导出表头与预设不一致时不会误解析——`import` 找不到匹配规则会提示走
  `parse --agent` 草案流程，人工批准后才解析；
- 预设不映射任何「猜测的」金额口径：usage 导出只取用量事实（platform_usage），
  账单金额一律来自账单事实层（bill_fact，invoice/账单导出或 CDP 采集）。
"""

from .parsing import format_fingerprint

PRESETS = {
    "openai/usage_csv": {
        "provider": "openai",
        "doc_type": "usage",
        "tier": "platform_usage",
        "status": "template — header shape per public export docs as of 2026-10; live_bill_validated=0",
        "file_name": "openai-usage.csv",
        "header": ["Date", "Requests", "Input tokens", "Cached input tokens",
                   "Output tokens", "Total tokens", "Cost (USD)"],
        "spec": {
            "tier": "platform_usage",
            "delimiter": ",",
            "header_row": 0,
            "skip_rows_containing": [],
            "columns": {
                "occurred_at": {"col": "Date"},
                "tool": {"const": "openai"},
                "quantity": {"col": "Total tokens"},
                "unit": {"const": "token"},
                "description": {"const": "openai usage export row"},
            },
        },
        "fixture": (
            "Date,Requests,Input tokens,Cached input tokens,Output tokens,Total tokens,Cost (USD)\n"
            "2026-10-02,120,24000,8000,9000,41000,0.42\n"
            "2026-10-03,98,19000,6000,7400,32400,0.33\n"
        ),
    },
    "anthropic/usage_csv": {
        "provider": "anthropic",
        "doc_type": "usage",
        "tier": "platform_usage",
        "status": "template — header shape per public export docs as of 2026-10; live_bill_validated=0",
        "file_name": "anthropic-usage.csv",
        "header": ["Date", "Model", "Input tokens", "Output tokens",
                   "Cache creation tokens", "Cache read tokens", "Cost (USD)"],
        "spec": {
            "tier": "platform_usage",
            "delimiter": ",",
            "header_row": 0,
            "skip_rows_containing": [],
            "columns": {
                "occurred_at": {"col": "Date"},
                "tool": {"col": "Model"},
                "quantity": {"col": "Input tokens"},
                "unit": {"const": "token"},
                "description": {"const": "anthropic usage export row"},
            },
        },
        "fixture": (
            "Date,Model,Input tokens,Output tokens,Cache creation tokens,Cache read tokens,Cost (USD)\n"
            "2026-10-02,claude-sonnet-4-5,51000,8200,4000,15000,0.51\n"
            "2026-10-03,claude-haiku-4-5,22000,3100,0,6000,0.12\n"
        ),
    },
}


def preset_fingerprint(name):
    """预设表头形状的指纹——与真实文件表头一致时规则才会命中。"""
    preset = PRESETS[name]
    return format_fingerprint(preset["file_name"], preset["fixture"])


def apply_preset(store, name):
    """把预设登记为已批准解析规则（created_via=preset，可用 rule show 复核）。"""
    preset = PRESETS[name]
    fingerprint = preset_fingerprint(name)
    store.put_parse_rule(fingerprint, preset["spec"], provider=preset["provider"],
                         doc_type=preset["doc_type"], tier=preset["tier"],
                         created_via="preset", golden=[])
    return fingerprint
