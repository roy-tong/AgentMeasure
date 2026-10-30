"""L1 会话保持的浏览器自动化：受审配方、来源审计与人工交接。

凭证边界：配方没有 fill/type，登录由客户在有头浏览器中亲手完成。
安全边界：动作白名单不是只读沙箱；click 可能有服务端副作用，配方必须视为可信代码。
反自动化只降级不绕过。哈希链用于内部一致性检查，不是执行回放或抗主动篡改证明。

Playwright 为可选依赖：未安装时 validate / dry_run / 审计链校验仍然可用。
"""

import datetime
import hashlib
import ipaddress
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from typing import List, Optional

ALLOWED_ACTIONS = ("navigate", "click", "wait_for", "download", "read", "screenshot")
# 不代填凭证：不存在 fill/type/press；这不保证 click 在服务端只读。

BOTWALL_TEXTS = ("checking your browser", "unusual traffic", "verify you are human",
                 "are you a robot", "请完成安全验证", "访问行为异常")

DEFAULT_PROFILE_ROOT = os.path.join(os.path.expanduser("~"), ".verovo", "profiles")
DEFAULT_AUDIT_ROOT = os.path.join(os.path.expanduser("~"), ".verovo", "audit")
DEFAULT_CDP_ROOT = os.path.join(os.path.expanduser("~"), ".verovo", "cdp")


class RecipeError(ValueError):
    pass


class Handoff(Exception):
    """需人工交接：反自动化拦截或步骤失败。不重试、不绕过。"""


def _safe_name(value):
    return (bool(value) and not os.path.isabs(value) and
            value not in (".", "..") and "/" not in value and "\\" not in value and
            ".." not in value)


def _allowed_hosts(recipe):
    start = urllib.parse.urlsplit(recipe.get("start_url", ""))
    return set(recipe.get("allowed_hosts") or ([start.hostname] if start.hostname else []))


def _url_error(url, allowed_hosts):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return "URL must be HTTPS without userinfo: %s" % url
    if parsed.hostname not in allowed_hosts:
        return "URL host is outside allowed_hosts: %s" % parsed.hostname
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if not ip.is_global:
            return "non-public IP literals are refused"
    except ValueError:
        pass
    return ""


def _safe_url(url):
    """审计不保存 query/fragment/userinfo，避免写入会话令牌。"""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.hostname or "", p.path, "", ""))


def _validate_period(period):
    if not period:
        return
    try:
        datetime.date.fromisoformat(period + "-01")
    except ValueError:
        raise RecipeError("period must be YYYY-MM")
    if len(period) != 7:
        raise RecipeError("period must be YYYY-MM")


def load_recipe(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_recipe(recipe):
    """配方校验（CI 可测，无需浏览器）。返回错误列表；空列表 = 通过。"""
    errors = []
    for key in ("recipe_id", "provider", "version", "start_url", "steps"):
        if key not in recipe:
            errors.append("missing key: %s" % key)
    if errors:
        return errors
    if recipe.get("readonly") is not True:
        errors.append("recipe.readonly must be true (INV-6)")
    hosts = _allowed_hosts(recipe)
    start_error = _url_error(str(recipe.get("start_url", "")), hosts)
    if start_error:
        errors.append(start_error)
    if not hosts:
        errors.append("allowed_hosts must contain the start_url host")
    steps = recipe.get("steps", [])
    if not steps:
        errors.append("steps must not be empty")
    for i, step in enumerate(steps):
        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            errors.append("step %d: action %r not in whitelist %s"
                          % (i, action, ALLOWED_ACTIONS))
            continue
        if action in ("click", "wait_for", "read") and not step.get("selector"):
            errors.append("step %d: %s needs selector" % (i, action))
        if action == "navigate":
            if not step.get("url"):
                errors.append("step %d: navigate needs url" % i)
            else:
                url_error = _url_error(step["url"], hosts)
                if url_error:
                    errors.append("step %d: %s" % (i, url_error))
        if action == "download":
            if not step.get("link_selector"):
                errors.append("step %d: download needs link_selector" % i)
            if not _safe_name(step.get("save_as", "")):
                errors.append("step %d: download save_as must be a safe basename" % i)
        if action == "screenshot" and not _safe_name(str(step.get("name", i))):
            errors.append("step %d: screenshot name must be a safe basename" % i)
    if not recipe.get("logged_in_indicator", {}).get("url_pattern"):
        errors.append("logged_in_indicator.url_pattern required")
    if "://" in recipe.get("logged_in_indicator", {}).get("url_pattern", ""):
        errors.append("logged_in_indicator.url_pattern should be a path/host regex")
    return errors


def dry_run(recipe):
    """无浏览器演练：列出执行计划与预期产物。"""
    errors = validate_recipe(recipe)
    if errors:
        raise RecipeError("; ".join(errors))
    plan = []
    for i, step in enumerate(recipe["steps"]):
        plan.append({
            "seq": i + 1,
            "action": step["action"],
            "target": step.get("url") or step.get("selector") or step.get("link_selector") or "",
        })
    downloads = [s for s in recipe["steps"] if s["action"] == "download"]
    return {
        "recipe_id": recipe["recipe_id"],
        "provider": recipe["provider"],
        "steps": plan,
        "expected_downloads": [d.get("save_as") for d in downloads],
        "session_profile_dir": profile_dir_for(recipe["provider"]),
        "note": "dry-run only; no browser was launched",
    }


def profile_dir_for(provider, account_ref=""):
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", provider)
    if account_ref:
        safe += "-" + hashlib.sha256(account_ref.encode("utf-8")).hexdigest()[:12]
    path = os.path.join(DEFAULT_PROFILE_ROOT, safe)
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)
    return path


# ── 审计链 ──────────────────────────────────────────────────────────────

def audit_path_for(recipe_id, run_ts):
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", recipe_id)
    return os.path.join(DEFAULT_AUDIT_ROOT, "%s-%s.jsonl" % (safe, run_ts))


def chain_entry(prev_hash, record):
    """审计链条目：entry_hash = sha256(prev_hash + 规范化记录)。可独立验链。"""
    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True)
    entry_hash = hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()
    return {"record": record, "prev_hash": prev_hash, "entry_hash": entry_hash}


def verify_chain(entries):
    """仅验证内部一致性；无签名/外部信任锚，不声称抗主动篡改。"""
    if not entries:
        return False, "empty audit chain"
    prev = "GENESIS"
    for i, e in enumerate(entries):
        if e.get("prev_hash") != prev:
            return False, "entry %d: broken prev_hash link" % i
        canonical = json.dumps(e["record"], ensure_ascii=False, sort_keys=True)
        recomputed = hashlib.sha256(
            (prev + canonical).encode("utf-8")).hexdigest()
        if recomputed != e.get("entry_hash"):
            return False, "entry %d: hash mismatch" % i
        prev = e["entry_hash"]
    actions = [e.get("record", {}).get("action") for e in entries]
    if (not actions or actions[0] != "run_start" or actions.count("run_start") != 1 or
            actions.count("run_end") != 1 or actions[-1] != "run_end" or
            not entries[-1].get("record", {}).get("final")):
        return False, "incomplete or ambiguous run chain"
    return True, ""


class AuditTrail:
    def __init__(self, recipe_id, run_ts, root=None):
        self.path = audit_path_for(recipe_id, run_ts) if root is None \
            else os.path.join(root, "%s-%s.jsonl" % (recipe_id, run_ts))
        os.makedirs(os.path.dirname(self.path), mode=0o700, exist_ok=True)
        os.chmod(os.path.dirname(self.path), 0o700)
        self._prev = "GENESIS"
        self._entries = []

    def add(self, **record):
        entry = chain_entry(self._prev, record)
        self._prev = entry["entry_hash"]
        self._entries.append(entry)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.chmod(self.path, 0o600)
        return entry["entry_hash"]

    def entries(self):
        return list(self._entries)

    @property
    def final_hash(self):
        return self._prev if self._prev != "GENESIS" else ""


# ── 浏览器运行时（可选依赖 Playwright）─────────────────────────────────

def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "L1 needs Playwright: pip install playwright && playwright install chromium"
        ) from exc
    from playwright.sync_api import sync_playwright
    return sync_playwright


def _logged_in(page, indicator):
    pattern = indicator.get("url_pattern", "")
    parsed = urllib.parse.urlsplit(page.url)
    # 只对 host+path 匹配；query 中的恶意 URL 不能伪造登录态。
    target = (parsed.hostname or "") + parsed.path
    try:
        matched = bool(re.search(pattern, target))
        logged_out = indicator.get("logged_out_patterns", [])
        return matched and not any(re.search(p, target) for p in logged_out)
    except re.error:
        return False


def _assert_runtime_url(recipe, url):
    error = _url_error(url, _allowed_hosts(recipe))
    if error:
        raise Handoff("navigation left approved origin: %s" % error)


def _install_request_guard(ctx, recipe):
    """在导航请求发出前阻断越源 top-level/frame/popup 跳转。"""
    def guard(route, request):
        try:
            if request.is_navigation_request():
                error = _url_error(request.url, _allowed_hosts(recipe))
                if error:
                    route.abort()
                    return
        except Exception:
            # 无法判断的导航不继续执行；非导航资源不受此导航守卫影响。
            try:
                if request.is_navigation_request():
                    route.abort()
                    return
            except Exception:
                pass
        route.continue_()
    ctx.route("**/*", guard)


def _botwalled(page):
    try:
        content = page.content().lower()
    except Exception:  # noqa: BLE001 — 页面崩溃交给上层 Handoff
        return False
    return any(t in content for t in BOTWALL_TEXTS)


def open_login_session(recipe, headed=True, poll_seconds=900, account_ref=""):
    """打开有头浏览器让客户亲手登录；模块轮询登录态，成功即收（不碰密码）。"""
    sync_playwright = _require_playwright()
    errors = validate_recipe(recipe)
    if errors:
        raise RecipeError("; ".join(errors))
    profile = profile_dir_for(recipe["provider"], account_ref)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, headless=not headed,
            accept_downloads=True,
            viewport={"width": 1280, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(recipe["start_url"])
        _assert_runtime_url(recipe, page.url)
        print("[buyer-ledger] 请在打开的浏览器中完成登录（含 2FA）。")
        print("[buyer-ledger] 系统不会读取或填写任何密码；检测到登录态后将自动继续。")
        import time
        deadline = time.time() + poll_seconds
        ok = False
        while time.time() < deadline:
            if _logged_in(page, recipe["logged_in_indicator"]):
                ok = True
                break
            if page.is_closed():
                break
            page.wait_for_timeout(2000)
        if ok:
            state_file = os.path.join(profile, ".session_ok")
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"provider": recipe["provider"], "account_ref": account_ref,
                           "checked_at": _now()}, f)
            os.chmod(state_file, 0o600)
            print("[buyer-ledger] 登录态已确认，会话保存在 %s" % profile)
        else:
            print("[buyer-ledger] 未检测到登录态（超时或窗口被关闭）。会话未标记。")
        ctx.close()
        return ok


def session_health(recipe, headless=True, account_ref=""):
    """会话健康检查：加载账单页，看是否被重定向到登录页。"""
    errors = validate_recipe(recipe)
    if errors:
        raise RecipeError("; ".join(errors))
    sync_playwright = _require_playwright()
    profile = profile_dir_for(recipe["provider"], account_ref)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(profile, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(recipe["start_url"], wait_until="domcontentloaded")
        _assert_runtime_url(recipe, page.url)
        page.wait_for_timeout(1500)
        if _botwalled(page):
            ctx.close()
            return "botwall"
        ok = _logged_in(page, recipe["logged_in_indicator"])
        ctx.close()
        return "ok" if ok else "needs_relogin"


def _execute_recipe(page, recipe, period, export_dir, record, provenance,
                    on_document, downloads):
    """在已建立或已附着的浏览器页面上执行受审配方。"""
    page.goto(recipe["start_url"], wait_until="domcontentloaded")
    _assert_runtime_url(recipe, page.url)
    record("navigate", url=_safe_url(recipe["start_url"]),
           result_url=_safe_url(page.url))
    if _botwalled(page):
        record("botwall_detected", url=page.url)
        raise Handoff("bot wall detected at %s — manual export needed" % page.url)
    if not _logged_in(page, recipe["logged_in_indicator"]):
        record("session_expired", url=page.url)
        raise Handoff("session expired — run `session login` first")
    for i, step in enumerate(recipe["steps"]):
        # 每个动作前都检查，防止 wait_for 期间跳转后在越源页面点击。
        _assert_runtime_url(recipe, page.url)
        action = step["action"]
        if action == "navigate":
            page.goto(step["url"], wait_until="domcontentloaded")
            _assert_runtime_url(recipe, page.url)
            record("navigate", url=_safe_url(step["url"]),
                   result_url=_safe_url(page.url))
        elif action == "wait_for":
            page.wait_for_selector(step["selector"],
                                   timeout=step.get("timeout_ms", 10000))
            _assert_runtime_url(recipe, page.url)
            record("wait_for", selector=step["selector"])
        elif action == "click":
            page.click(step["selector"], timeout=step.get("timeout_ms", 10000))
            _assert_runtime_url(recipe, page.url)
            record("click", selector=step["selector"],
                   result_url=_safe_url(page.url))
        elif action == "read":
            text = page.inner_text(step["selector"],
                                   timeout=step.get("timeout_ms", 10000))
            record("read", selector=step["selector"], chars=len(text))
        elif action == "screenshot":
            shot = os.path.join(export_dir, "%s.png" % step.get("name", i))
            page.screenshot(path=shot, full_page=step.get("full_page", False))
            record("screenshot", path=shot, sha256=_file_hash(shot))
        elif action == "download":
            with page.expect_download(timeout=step.get("timeout_ms", 30000)) as dl:
                page.click(step["link_selector"])
            download = dl.value
            _assert_runtime_url(recipe, page.url)
            _assert_runtime_url(recipe, download.url)
            name = (step.get("save_as") or "download").format(period=period or "latest")
            if not _safe_name(name):
                raise Handoff("formatted download name is not a safe basename")
            target = os.path.abspath(os.path.join(export_dir, name))
            if os.path.commonpath([os.path.abspath(export_dir), target]) != os.path.abspath(export_dir):
                raise Handoff("download target escaped export directory")
            download.save_as(target)
            os.chmod(target, 0o600)
            if os.path.getsize(target) > 20 * 1024 * 1024:
                raise Handoff("download exceeds 20 MiB safety limit")
            downloads.append(target)
            document_id = ""
            if on_document:
                result = on_document(target, os.path.basename(target), dict(provenance))
                document_id = (result or {}).get("document_id", "")
            record("download", path=target, sha256=_file_hash(target),
                   suggested=download.suggested_filename, document_id=document_id,
                   run_id=provenance["run_id"])
        if _botwalled(page):
            record("botwall_detected", url=page.url)
            raise Handoff("bot wall detected mid-recipe at %s" % page.url)


def _validate_cdp_endpoint(endpoint):
    parsed = urllib.parse.urlsplit(endpoint or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise RecipeError("CDP endpoint must be an http(s) URL")
    if parsed.username or parsed.password:
        raise RecipeError("CDP endpoint must not contain credentials")
    if parsed.query or parsed.fragment:
        raise RecipeError("CDP endpoint must not contain query/fragment secrets")
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise RecipeError("CDP endpoint must be loopback (localhost/127.0.0.1/::1)")
    return endpoint.rstrip("/")


def cdp_health(endpoint):
    """本地 CDP 健康检查；返回 Browser 版本与 endpoint，不建立页面。"""
    endpoint = _validate_cdp_endpoint(endpoint)
    with urllib.request.urlopen(endpoint + "/json/version", timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {"endpoint": endpoint, "browser": payload.get("Browser", ""),
            "protocol_version": payload.get("Protocol-Version", "")}


def _run_recipe_with_context(ctx, recipe, period, export_dir, trail, provider,
                             provenance, on_document, transport, use_new_page=False):
    """在给定 BrowserContext 上跑一次配方；不关闭调用方提供的 context。"""
    downloads = []

    def record(action, **kw):
        trail.add(ts=_now(), action=action, provider=provider, **kw)

    record("run_start", period=period, recipe=recipe["recipe_id"],
           version=recipe.get("version"), recipe_sha256=provenance["recipe_sha256"],
           run_id=provenance["run_id"], transport=transport, action_whitelist=True)
    _install_request_guard(ctx, recipe)
    page = ctx.new_page() if use_new_page or not getattr(ctx, "pages", None) else ctx.pages[0]
    try:
        _execute_recipe(page, recipe, period, export_dir, record, provenance,
                        on_document, downloads)
    except Handoff as h:
        record("handoff", reason=str(h))
        h.audit_path = trail.path
        h.final_hash = trail.final_hash
        raise
    except Exception as exc:  # noqa: BLE001 — 步骤失败一律转人工，不重试
        record("step_failed", error=str(exc)[:300])
        handoff = Handoff("recipe step failed: %s — manual export needed" % exc)
        handoff.audit_path = trail.path
        handoff.final_hash = trail.final_hash
        raise handoff
    finally:
        try:
            page.close()
        except Exception:
            pass
    record("run_end", downloads=len(downloads), run_id=provenance["run_id"], final=True)
    return {"downloads": downloads, "audit": trail.path,
            "run_id": provenance["run_id"], "final_hash": trail.final_hash,
            "transport": transport}


def run_recipe(recipe, period="", headless=True, on_document=None, account_ref="",
               cdp_endpoint=""):
    """重放受审配方；支持独立 Playwright profile 或附着本地 CDP Chrome。"""
    _validate_period(period)
    sync_playwright = _require_playwright()
    errors = validate_recipe(recipe)
    if errors:
        raise RecipeError("; ".join(errors))
    provider = recipe["provider"]
    if cdp_endpoint:
        cdp_endpoint = _validate_cdp_endpoint(cdp_endpoint)
        base_dir = os.path.join(DEFAULT_CDP_ROOT, provider)
    else:
        base_dir = profile_dir_for(provider, account_ref)
    run_id = _now().replace(":", "") + "-" + uuid.uuid4().hex[:12]
    export_dir = os.path.join(base_dir, "exports", period or "latest", run_id)
    os.makedirs(export_dir, mode=0o700, exist_ok=True)
    os.chmod(export_dir, 0o700)
    trail = AuditTrail(re.sub(r"[^a-zA-Z0-9._-]", "_", recipe["recipe_id"]), run_id)
    recipe_hash = hashlib.sha256(
        json.dumps(recipe, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    provenance = {"run_id": run_id, "audit_path": trail.path,
                  "recipe_sha256": recipe_hash, "fetched_at": _now(),
                  "transport": "cdp" if cdp_endpoint else "playwright_profile"}
    transport = provenance["transport"]

    with sync_playwright() as p:
        if cdp_endpoint:
            browser = p.chromium.connect_over_cdp(cdp_endpoint)
            if not browser.contexts:
                raise RecipeError("CDP browser has no default context; open Chrome first")
            return _run_recipe_with_context(
                browser.contexts[0], recipe, period, export_dir, trail, provider,
                provenance, on_document, transport, use_new_page=True)
        ctx = p.chromium.launch_persistent_context(
            profile_dir_for(provider, account_ref), headless=headless,
            accept_downloads=True, viewport={"width": 1280, "height": 800})
        try:
            return _run_recipe_with_context(
                ctx, recipe, period, export_dir, trail, provider, provenance,
                on_document, transport)
        finally:
            ctx.close()


def _now():
    import datetime
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
