"""BrowserSkill error classification, sanitization, and bounded recovery primitives.

Disambiguates between:
1. Infrastructure failures (session dead, daemon lost, timeout, process crashed).
2. Platform access restrictions (login required, captcha/challenge, rate limiting).
3. Empty/unrelated content (search page read successfully, but 0 valid cards).
4. Item-level download/parsing failures (single card/image fails, session healthy).
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any

_SECRET_HEADER = re.compile(r"""(?im)\b(?:cookie|set-cookie|authorization|proxy-authorization)["']?\s*:\s*[^\r\n]+""")
_SECRET_VALUE = re.compile(r"""(?i)([\w-]*(?:token|key|secret|password|auth|credential)[\w-]*["']?\s*[=:]\s*["']?)[^\s"'&;,}]+""")
_PATH_HOME_PATTERN = re.compile(r'(?i)[a-z]:[\\/]+users[\\/]+[^\\/\s]+')
_MAX_RAW_OUTPUT = 4000


def sanitize_diagnostics(value: Any) -> Any:
    """Strip cookies, tokens, credentials, and user home paths from diagnostic data."""
    if isinstance(value, str):
        text = _SECRET_HEADER.sub('[REDACTED HEADER]', value)
        text = _SECRET_VALUE.sub(r'\1[REDACTED]', text)
        text = _PATH_HOME_PATTERN.sub('~', text)
        return text
    elif isinstance(value, dict):
        sanitized = {}
        for k, v in value.items():
            k_str = str(k).lower()
            if any(term in k_str for term in ('cookie', 'authorization', 'token', 'secret', 'password', 'key')):
                sanitized[k] = '[REDACTED]'
            else:
                sanitized[k] = sanitize_diagnostics(v)
        return sanitized
    elif isinstance(value, (list, tuple)):
        return [sanitize_diagnostics(item) for item in value]
    return value


def _bounded_diagnostics(value: Any) -> str:
    text = str(sanitize_diagnostics(value))
    if len(text) <= _MAX_RAW_OUTPUT:
        return text
    marker = "\n...[truncated]...\n"
    head = (_MAX_RAW_OUTPUT - len(marker)) // 2
    tail = _MAX_RAW_OUTPUT - len(marker) - head
    return text[:head] + marker + text[-tail:]


class BrowserError(ValueError):
    """Base exception for all browser skill errors, inheriting from ValueError for backwards compatibility."""

    def __init__(
        self,
        message: str,
        *,
        action: str = "",
        code: str = "action_failed",
        category: str = "browser",
        details: str = "",
        raw_output: str = "",
        reason: str = "",
        dispatched: bool | None = None,
        effect_state: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.action = action
        self.code = code
        self.category = category
        self.details = sanitize_diagnostics(details)
        self.raw_output = sanitize_diagnostics(raw_output)
        self.reason = str(sanitize_diagnostics(reason))
        self.dispatched = dispatched
        self.effect_state = str(sanitize_diagnostics(effect_state))


class BrowserInfrastructureError(BrowserError):
    """Browser infrastructure failure: session not found/stopped, daemon down, browser closed, timeout, broken pipe."""

    def __init__(
        self,
        message: str,
        *,
        action: str = "",
        code: str = "infrastructure_failure",
        details: str = "",
        is_session_dead: bool = False,
        is_daemon_down: bool = False,
        is_timeout: bool = False,
        raw_output: str = "",
        reason: str = "",
        dispatched: bool | None = None,
        effect_state: str = "",
    ):
        super().__init__(
            message,
            action=action,
            code=code,
            category="infrastructure",
            details=details,
            raw_output=raw_output,
            reason=reason,
            dispatched=dispatched,
            effect_state=effect_state,
        )
        self.is_session_dead = is_session_dead
        self.is_daemon_down = is_daemon_down
        self.is_timeout = is_timeout


class PlatformRestrictionError(BrowserError):
    """Platform-level access restriction: login required, verification captcha/challenge, rate limiting, anti-bot."""

    def __init__(
        self,
        message: str,
        *,
        source: str = "",
        restriction: str = "blocked",
        details: str = "",
    ):
        super().__init__(
            message,
            action="access",
            code=restriction,
            category="platform_restriction",
            details=details,
        )
        self.source = source
        self.restriction = restriction


class DetailItemError(BrowserError):
    """Single detail post or image download error that does not invalidate the browser session or query."""

    def __init__(
        self,
        message: str,
        *,
        page_url: str = "",
        code: str = "detail_failed",
        details: str = "",
    ):
        super().__init__(
            message,
            action="detail",
            code=code,
            category="item_detail",
            details=details,
        )
        self.page_url = page_url


def classify_bsk_error(action: str, returncode: int, stdout: str, stderr: str) -> BrowserError:
    """Classify bsk CLI output into a typed, structured BrowserError."""
    combined = ((stdout or "") + "\n" + (stderr or "")).strip()

    # First, try parsing JSON response if present
    parsed = {}
    for text in (stdout, stderr):
        if text and text.strip().startswith("{") and text.strip().endswith("}"):
            try:
                data = json.loads(text.strip())
                if isinstance(data, dict):
                    parsed = data
                    break
            except (ValueError, TypeError):
                pass

    raw_code = str(parsed.get("code") or "")
    message = str(parsed.get("message") or parsed.get("hint") or "")
    lower_comb = combined.lower()
    data = parsed.get("data") if isinstance(parsed.get("data"), dict) else {}
    reason = str(data.get("reason") or parsed.get("reason") or "")
    dispatched = data.get("dispatched", parsed.get("dispatched"))
    dispatched = dispatched if isinstance(dispatched, bool) else None
    effect_state = str(data.get("effect_state") or parsed.get("effect_state") or "")
    lower_message = message.lower()
    lower_reason = reason.lower()
    lower_effect = effect_state.lower()
    semantic_text = " ".join((lower_comb, lower_message, lower_reason, lower_effect))
    semantic_key = semantic_text.replace("_", " ").replace("-", " ")

    def control_error(code: str, label: str) -> BrowserInfrastructureError:
        return BrowserInfrastructureError(
            label,
            action=action,
            code=code,
            details=message or _bounded_diagnostics(combined)[:1000],
            is_timeout=False,
            raw_output=_bounded_diagnostics(combined),
            reason=reason,
            dispatched=dispatched,
            effect_state=effect_state,
        )

    user_aborted = (
        raw_code == "user_aborted"
        or lower_reason in ("user_aborted", "user aborted")
        or any(term in semantic_key for term in ("aborted by user", "user aborted", "cancelled by user", "canceled by user"))
    )
    if user_aborted:
        return control_error("user_aborted", "用户已取消 BrowserSkill 操作")

    cancelled = any(term in semantic_key for term in ("cancel", "abort"))
    unknown_effect = lower_effect in ("unknown", "uncertain", "unconfirmed") or any(
        term in semantic_key for term in ("effect unknown", "outcome unknown", "effect state: unknown")
    )
    unknown_outcome_reason = lower_reason in (
        "operation_outcome_unknown",
        "effect_state_unknown",
        "effect_unknown",
    )
    if raw_code == "operation_outcome_unknown" or unknown_outcome_reason or (cancelled and (dispatched is True or unknown_effect)):
        return control_error("operation_outcome_unknown", "操作已取消，但副作用状态未知")

    ipc_context = any(term in semantic_key for term in ("ipc", "named pipe", "bsk.pipe", "rpc"))
    access_denied = "access denied" in semantic_key or "eacces" in semantic_key
    if (
        raw_code in ("ipc_access_denied", "ipc_denied", "ipc_eacces")
        or "ipc access denied" in semantic_key
        or (ipc_context and access_denied)
    ):
        return control_error("ipc_access_denied", "BrowserSkill IPC 访问被拒绝")

    if raw_code in ("protocol_mismatch", "protocol_incompatible", "version_skew") or any(
        term in semantic_key
        for term in ("protocol mismatch", "protocol incompatible", "unsupported protocol", "protocol version mismatch",
                     "below peer min compatible protocol")
    ):
        return control_error("protocol_mismatch", "BrowserSkill 协议版本不兼容")

    if raw_code == "cooperation_sync_required" or "cooperation sync required" in semantic_key:
        return control_error("cooperation_sync_required", "BrowserSkill 需要与页面协调状态")

    if raw_code == "cleanup_timeout" or "background execution cleanup timed out" in semantic_key:
        return BrowserInfrastructureError(
            "BrowserSkill 后台执行清理超时",
            action=action,
            code="cleanup_timeout",
            details=message or "background execution cleanup timed out",
            is_timeout=True,
            raw_output=_bounded_diagnostics(combined),
            reason=reason,
            dispatched=dispatched,
            effect_state=effect_state,
        )

    if raw_code == "session_busy" or any(
        term in semantic_key
        for term in (
            "session busy",
            "session is busy",
            "session unfinished",
            "session is unfinished",
            "session already has an unfinished command",
            "previous operation still settling",
            "previous operation is still settling",
            "operation still settling",
            "operation is still settling",
        )
    ):
        return control_error("session_busy", "BrowserSkill 会话仍在处理上一操作")

    if raw_code in ("renderer_not_answering", "renderer_read_timeout") or any(
        term in semantic_key
        for term in ("renderer is not answering", "renderer read timeout", "page.getframetree timed out")
    ):
        return BrowserInfrastructureError(
            "BrowserSkill 渲染器读取超时",
            action=action,
            code="renderer_not_answering",
            details=message or "renderer is not answering",
            is_timeout=True,
            raw_output=_bounded_diagnostics(combined),
            reason=reason,
            dispatched=dispatched,
            effect_state=effect_state,
        )

    # 1. Platform restrictions: 403, 429, captcha, challenge, rate limit, login
    if (raw_code in ("challenge", "captcha", "blocked", "http_403", "http_429", "rate_limited", "login_required")
            or "login_required" in lower_comb or "需要登录" in combined
            or re.search(r"\b(?:403|429|captcha|challenge|rate.limit)\b", lower_comb)):
        restriction = "login_required" if ("login" in lower_comb or "登录" in combined) else "blocked"
        return PlatformRestrictionError("来源需要验证或暂时限制访问", restriction=restriction, details=combined[:400])

    # 2. Daemon disconnected / process crashed / connection refused
    if (
        raw_code in ("browser_disconnected", "daemon_unreachable", "daemon_disconnected")
        or "connection refused" in lower_comb
        or "failed to connect to daemon" in lower_comb
        or "daemon is not running" in lower_comb
        or "broken pipe" in lower_comb
        or "connection reset" in lower_comb
        or "no browser connected" in lower_comb
        or "browser has been closed" in lower_comb
        or "target closed" in lower_comb
        or "browser process died" in lower_comb
    ):
        code = "daemon_disconnected" if ("daemon" in lower_comb or "connection" in lower_comb or "pipe" in lower_comb) else "browser_closed"
        return BrowserInfrastructureError(
            "BrowserSkill 守护进程或浏览器断开连接",
            action=action,
            code=code,
            details=message or "daemon disconnected or unreachable",
            is_daemon_down=True,
            raw_output=_bounded_diagnostics(combined),
        )

    # 3. Generic timeout after specific renderer and session states above.
    if raw_code == "timeout" or "timed out" in lower_comb or "timeoutexpired" in lower_comb:
        is_session_dead = (
            action in ("evaluate", "click", "hover", "session") or "tool rpc timed out" in lower_comb
        )
        return BrowserInfrastructureError(
            "BrowserSkill 命令执行或导航超时",
            action=action,
            code="timeout",
            details=message or "operation timed out",
            is_timeout=True,
            is_session_dead=is_session_dead,
            raw_output=_bounded_diagnostics(combined),
        )

    # 4. Session dead / not registered / stopped (normalized in session context)
    is_session_action = action in ("session", "navigate", "evaluate", "screenshot", "click", "hover", "wheel")
    is_session_dead = (
        raw_code in ("session_stopped", "session_not_found")
        or (raw_code == "not_found" and (is_session_action or "session" in lower_comb or "registered" in lower_comb))
        or "session is not registered" in lower_comb
        or "session not registered or already stopped" in lower_comb
        or "session is dead" in lower_comb
        or "invalid session" in lower_comb
        or "requested resource does not exist" in lower_comb
    )
    if is_session_dead:
        return BrowserInfrastructureError(
            "浏览器会话已失效或未注册",
            action=action,
            code="session_not_found",
            details=message or "session not registered or already stopped",
            is_session_dead=True,
            raw_output=_bounded_diagnostics(combined),
        )

    # CDP navigation rejection / underlying CDP call rejection
    if "page.navigate rejected" in lower_comb or "rejected the underlying cdp call" in lower_comb:
        return BrowserInfrastructureError(
            "浏览器拒绝底层 CDP 导航调用",
            action=action,
            code="cdp_navigate_rejected",
            details=message or "Page.navigate rejected by browser",
            is_session_dead=True,
            raw_output=_bounded_diagnostics(combined),
        )

    # 5. Item-level DOM / selector errors (DetailItemError)
    if (raw_code in ("selector_not_found", "element_not_found", "element_not_interactable")
            or "selector did not match" in lower_comb
            or "did not match any element" in lower_comb
            or "element not found" in lower_comb):
        return DetailItemError("当前页面元素不可用", code=raw_code or "selector_not_found", details=message or _bounded_diagnostics(combined)[:1000])

    # 6. Check for native input ready
    if "did not become ready for native input" in combined:
        return BrowserInfrastructureError(
            "浏览器页面元素未能就绪进行交互",
            action=action,
            code="native_input_not_ready",
            details="did not become ready for native input",
            raw_output=_bounded_diagnostics(combined),
        )

    # Fallback infrastructure error
    final_code = raw_code if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", raw_code) else "action_failed"
    return BrowserInfrastructureError(
        f"BrowserSkill 命令执行失败 ({final_code})",
        action=action,
        code=final_code,
        details=message or _bounded_diagnostics(combined)[:1000],
        raw_output=_bounded_diagnostics(combined),
    )


def is_infrastructure_error(exc: BaseException) -> bool:
    """Determine whether an exception represents a browser infrastructure failure."""
    if isinstance(exc, BrowserInfrastructureError):
        return True
    if isinstance(exc, subprocess.SubprocessError):
        return True
    text = str(exc)
    if text.startswith("BrowserSkill:"):
        code = text.split(":", 1)[1].strip()
        # Non-infrastructure codes (e.g. login / platform)
        if code in ("login_required", "challenge", "blocked"):
            return False
        return True
    return False
