"""Ombre 读口：开场把该浮现的记忆取回来，拼成一段可以注入 system 的文本。

规矩（改这个文件前先读三遍）：
- 任何异常都不许往外冒：拿不到、超时、被限流、服务没开，一律返回 ""，聊天必须照常。
- 同一个窗口在 TTL 内只问 Ombre 一次：既是「开场浮现」的语义，
  也避开它每来源 60 秒 10 次的限流。
- `OMBRE_INJECT` 关掉就完全回到旧行为（这个文件立刻变成哑巴）。
- 注入前剥掉 Ombre 的工程外壳：标签行不进上下文，只留正文。
- 模型自己伸手时也走这儿：recall() 真去问一次（不吃 TTL 缓存），remember() 走 Ombre 自带的旁路 CLI 落一条。
"""

import asyncio
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


def _strip_scaffold(text: str) -> str:
    """把 Ombre 的工程外壳剥掉，只留下能当人话读的正文。"""
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip() in ("", "[Ombre Brain - 记忆浮现]"):
            continue
        if line.lstrip().startswith("💭"):
            continue
        if line.strip() == "---":
            kept.append("")
            continue
        if line.startswith("📌 [核心准则] "):
            line = line[len("📌 [核心准则] "):]
        kept.append(line)
    cleaned = "\n".join(kept).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned


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
    cleaned = _strip_scaffold(body)
    if not cleaned:
        return ""
    return cleaned[:_MAX_CHARS]


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

def recall() -> str:
    """给「手」用：真去问一次，不吃 TTL 缓存 —— 这次是模型自己伸手来问的。

    返回剥过壳、能当人话读的正文；没接上 / 拿不到一律返回 ""。
    """
    if not enabled():
        return ""
    return _fetch()


async def remember(content: str, name: str = "", domain: str = "", tags: str = "") -> tuple[bool, str]:
    """把一条记忆写进 Ombre —— 走它自带的旁路 CLI（直接落 .md，不经 HTTP、不碰它的配置）。

    ★ 为什么用 CLI：写口的正路是 MCP（要 OAuth），而它自己提供了这个
      「API 不可用时的底圈」小工具，文件格式由它自己维护，省得我们抄第二份。
    返回 (成功?, 一句说明)。
    """
    home = (os.environ.get("OMBRE_HOME") or "/root/Ombre-Brain").strip()
    py = (os.environ.get("OMBRE_PYTHON") or os.path.join(home, ".venv", "bin", "python")).strip()
    script = os.path.join(home, "src", "write_memory.py")
    if not (os.path.isfile(py) and os.path.isfile(script)):
        return False, "Ombre 的写入工具没找到（%s）" % script
    argv = [py, script,
            "--name", (name or content[:12]).strip() or "一条记忆",
            "--content", content,
            "--domain", (domain or "回忆").strip()]
    if tags:
        argv += ["--tags", tags]
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=home,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await asyncio.wait_for(proc.communicate(), timeout=20)
    except Exception as e:                     # noqa: BLE001
        return False, "写入没成功：%s" % e
    if proc.returncode != 0:
        return False, "写入没成功：%s" % (err or b"").decode("utf-8", "replace").strip()[:200]
    return True, (out or b"").decode("utf-8", "replace").strip()[:200]
