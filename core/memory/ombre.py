"""Ombre 读口：开场把该浮现的记忆取回来，拼成一段可以注入 system 的文本。

规矩（改这个文件前先读三遍）：
- 任何异常都不许往外冒：拿不到、超时、被限流、服务没开，一律返回 ""，聊天必须照常。
- 同一个窗口在 TTL 内只问 Ombre 一次：既是「开场浮现」的语义，
  也避开它每来源 60 秒 10 次的限流。
- `OMBRE_INJECT` 关掉就完全回到旧行为（这个文件立刻变成哑巴）。
"""

import os
import threading
import time
import urllib.request

_OK_TTL_SECONDS = 900.0
_FAIL_TTL_SECONDS = 60.0
_TIMEOUT_SECONDS = 4.0
_MAX_CHARS = 4000

_lock = threading.Lock()
_cache: dict[str, tuple[float, str]] = {}


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def enabled() -> bool:
    return _truthy(os.environ.get("OMBRE_INJECT"))


def _fetch() -> str:
    token = (os.environ.get("OMBRE_HOOK_TOKEN") or "").strip()
    if not token:
        return ""
    base = (os.environ.get("OMBRE_URL") or "http://127.0.0.1:18001").strip().rstrip("/")
    request = urllib.request.Request(
        base + "/breath-hook",
        headers={"X-Ombre-Hook-Token": token},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            if int(getattr(response, "status", 200)) != 200:
                return ""
            body = response.read().decode("utf-8", "replace")
    except Exception:
        return ""
    return body.strip()[:_MAX_CHARS]


def block(session_id: str | None = None) -> str:
    """返回要注入 system 的记忆文本；开关关着或拿不到就返回空串。"""
    if not enabled():
        return ""
    key = str(session_id or "main")
    now = time.monotonic()
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            ttl = _OK_TTL_SECONDS if cached[1] else _FAIL_TTL_SECONDS
            if now - cached[0] < ttl:
                return cached[1]
    text = _fetch()
    with _lock:
        _cache[key] = (now, text)
        if len(_cache) > 64:
            for old_key in list(_cache)[:-64]:
                _cache.pop(old_key, None)
    return text
