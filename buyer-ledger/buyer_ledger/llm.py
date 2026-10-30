"""LLM 客户端（仅用于首次格式适配与异常解释，不参与账目计算）.

配置（环境变量）：
  AM_LLM_BASE_URL  OpenAI 兼容端点，如 https://open.bigmodel.cn/api/paas/v4
  AM_LLM_API_KEY   密钥
  AM_LLM_MODEL     模型名

纪律（方向文档 §3.3）：Agent 负责"识别与映射"，确定性程序负责"计算"。
LLM 的输出只能是解析规格（spec），不是金额。
"""

import json
import os
import re
import urllib.request
import urllib.parse


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = (base_url or os.environ.get("AM_LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("AM_LLM_API_KEY", "")
        self.model = model or os.environ.get("AM_LLM_MODEL", "")

    @property
    def configured(self):
        return bool(self.base_url and self.api_key and self.model)

    def chat(self, system, user, temperature=0.0, timeout=60):
        if not self.configured:
            raise LLMError(
                "LLM not configured: set AM_LLM_BASE_URL / AM_LLM_API_KEY / AM_LLM_MODEL")
        parsed = urllib.parse.urlsplit(self.base_url)
        local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
        if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
            raise LLMError("LLM endpoint must use HTTPS (plain HTTP is allowed only on localhost)")
        payload = json.dumps({
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 — 统一转为受控错误
            raise LLMError("LLM request failed: %s" % exc)
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("unexpected LLM response shape: %s" % json.dumps(body)[:400])


def extract_json(text):
    """用 JSON 解析器处理字符串内花括号，而不是手工计数。"""
    text = re.sub(r"```(?:json)?", "", text).strip("` \n")
    start = text.find("{")
    if start < 0:
        raise LLMError("no JSON object in LLM reply")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
        return value
    except json.JSONDecodeError as exc:
        raise LLMError("invalid JSON in LLM reply: %s" % exc)
