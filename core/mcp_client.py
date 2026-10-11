"""薄 MCP 客户端 —— 让 AI 用上用户配好的 MCP 工具。

三种连接方式，都写在 data/mcp.json 里（格式沿用 Claude 的 .mcp.json）：
  · stdio          {"command": "npx", "args": [...], "env": {...}}
  · Streamable HTTP{"url": "https://.../mcp", "headers": {...}}
  · 老的 HTTP+SSE  {"url": "https://.../sse", "type": "sse", "headers": {...}}
`"enabled": false` 的 server 不会被连上，工具也不会出现在 AI 手里（前端开关就用这个字段）。

★ 安全边界：server 的命令/地址是用户自己贴的（等于用户自己运行程序）。
AI 只能用已登记的 server，不能自己添加。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

from . import datadir as _dd
from urllib.parse import urljoin

_servers: dict = {}          # name -> _Server

PROTO = "2025-06-18"         # 对 server 声明的协议版本；某个 server 不认就改这一行


# ────────────────────── 装配单 ──────────────────────

def _cfg_file() -> Path:
    return _dd.home_dir() / "mcp.json"


def load_cfg() -> dict:
    try:
        return json.loads(_cfg_file().read_text(encoding="utf-8")).get("mcpServers") or {}
    except Exception:
        return {}


def _write_cfg(value: dict) -> None:
    f = _cfg_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(f)


def enabled_of(spec: dict) -> bool:
    v = spec.get("enabled", True)
    if isinstance(v, str):
        return v.strip().lower() not in ("0", "false", "off", "no")
    return bool(v)


def save_server(name: str, command: str = "", args: list | None = None,
                env: dict | None = None, url: str = "",
                headers: dict | None = None, type_: str = "") -> None:
    """登记一个 server。老的调用 save_server(name, command, args, env) 照旧能用。"""
    f = _cfg_file()
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    if url:
        spec: dict = {"url": url}
        if type_:
            spec["type"] = type_
        if headers:
            spec["headers"] = headers
    else:
        spec = {"command": command, "args": args or [], "env": env or {}}
    cfg.setdefault("mcpServers", {})[name] = spec
    _write_cfg(cfg)


def set_enabled(name: str, on: bool) -> bool:
    """前端那个开关拨的就是它（改完要 start_all() 才生效）。"""
    f = _cfg_file()
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return False
    if name not in (cfg.get("mcpServers") or {}):
        return False
    cfg["mcpServers"][name]["enabled"] = bool(on)
    _write_cfg(cfg)
    return True


def _mask(v: str) -> str:
    """请求头给人看的那一点 —— **不回显明文**（里面往往就是 Bearer token）。"""
    v = str(v or "")
    if not v:
        return ""
    return ("…" + v[-4:]) if len(v) > 8 else "…"


def save_http(name: str, url: str, kind: str = "http",
              headers: dict | None = None) -> None:
    """登记 / 更新一条 HTTP(S) 的 MCP（Streamable HTTP 或老的 HTTP+SSE）。

    ★ 请求头的合并规矩（跟「引擎那把 key」同一条）：**值传空串＝沿用已经存着的那把**。
      前端不回显密文，编辑时那一格本来就是空的 —— 拿空串去覆盖，等于把人家的
      Bearer token 抹掉，而且他看不出来。传了名字才会覆盖/新增；这次没带的名字＝删掉。
    """
    f = _cfg_file()
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    servers = cfg.setdefault("mcpServers", {})
    old = servers.get(name) or {}
    old_h = dict(old.get("headers") or {}) if isinstance(old.get("headers"), dict) else {}
    h: dict = {}
    for k, v in (headers or {}).items():
        k = str(k or "").strip()
        if not k:
            continue
        v = str(v or "").strip()
        h[k] = v if v else str(old_h.get(k) or "")
    spec: dict = {"url": (url or "").strip()}
    k = (kind or "http").strip().lower()
    if k in ("sse", "http+sse", "eventsource"):
        spec["type"] = "sse"
    else:
        spec["type"] = "http"          # ★ 明说，别让它再靠地址猜
    if h:
        spec["headers"] = h
    if "enabled" in old:                # 拨过的开关别被一次编辑重置
        spec["enabled"] = old["enabled"]
    servers[name] = spec
    _write_cfg(cfg)


def spec_of(name: str) -> dict:
    return dict(load_cfg().get(name) or {})


def drop_server(name: str) -> None:
    f = _cfg_file()
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
        cfg.get("mcpServers", {}).pop(name, None)
        _write_cfg(cfg)
    except Exception:
        pass
    s = _servers.pop(name, None)
    if s:
        try:
            asyncio.ensure_future(s.close())
        except Exception:
            pass


# ────────────────────── 三种传输 ──────────────────────

class _Server:
    def __init__(self, name: str, spec: dict):
        self.name, self.spec = name, spec
        self.tools: list = []
        self.err = ""
        self._id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        try:
            await self._connect()
            await self._rpc("initialize", {
                "protocolVersion": PROTO, "capabilities": {},
                "clientInfo": {"name": "lianhuan", "version": "0.2"}}, timeout=20)
            await self._notify("notifications/initialized")
            r = await self._rpc("tools/list", {}, timeout=20)
            self.tools = (r or {}).get("tools") or []
        except Exception as e:
            self.err = f"{type(e).__name__}: {e}"[:160]
            await self.close()

    async def call(self, tool: str, args: dict) -> dict:
        r = await self._rpc("tools/call", {"name": tool, "arguments": args})
        out = []
        for c in (r or {}).get("content") or []:
            if c.get("type") == "text":
                out.append(c.get("text") or "")
        txt = "\n".join(out)[:4000] or json.dumps(r, ensure_ascii=False)[:2000]
        return {"ok": not (r or {}).get("isError"), "result": txt}

    # 子类实现
    async def _connect(self) -> None: ...
    async def _rpc(self, method: str, params: dict, timeout: float = 45) -> dict: ...
    async def _notify(self, method: str) -> None: ...
    async def close(self) -> None: ...
    def alive(self) -> bool: return True


class _StdioServer(_Server):
    """原来的那条路：起子进程，拿 stdin/stdout 走 JSON-RPC。"""

    def __init__(self, name: str, spec: dict):
        super().__init__(name, spec)
        self.proc = None

    async def _connect(self) -> None:
        env = dict(os.environ)
        env.update(self.spec.get("env") or {})
        self.proc = await asyncio.create_subprocess_exec(
            self.spec["command"], *(self.spec.get("args") or []),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, env=env,
            limit=8 * 1024 * 1024)

    async def _send(self, msg: dict) -> None:
        self.proc.stdin.write((json.dumps(msg, ensure_ascii=False) + "\n").encode())
        await self.proc.stdin.drain()

    async def _rpc(self, method: str, params: dict, timeout: float = 45) -> dict:
        async with self._lock:                    # 一条管道，请求要排队
            self._id += 1
            rid = self._id
            await self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
            loop = asyncio.get_running_loop()
            end = loop.time() + timeout
            while True:
                left = end - loop.time()
                if left <= 0:
                    raise TimeoutError(method)
                line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=left)
                if not line:
                    raise RuntimeError("server 退出了")
                try:
                    d = json.loads(line)
                except Exception:
                    continue                      # 有的 server 往 stdout 混日志，跳过
                if d.get("id") == rid:
                    if "error" in d:
                        raise RuntimeError(str(d["error"])[:200])
                    return d.get("result") or {}

    async def _notify(self, method: str) -> None:
        await self._send({"jsonrpc": "2.0", "method": method})

    def alive(self) -> bool:
        return bool(self.proc and self.proc.returncode is None)

    async def close(self) -> None:
        p, self.proc = self.proc, None
        if p and p.returncode is None:
            try:
                p.kill()
                await p.wait()
            except Exception:
                pass


class _HttpServer(_Server):
    """Streamable HTTP：一个端点，POST JSON-RPC；回包可能是 JSON，也可能是一条 SSE 流。"""

    def __init__(self, name: str, spec: dict):
        super().__init__(name, spec)
        self.url = (spec.get("url") or "").strip()
        self.headers = dict(spec.get("headers") or {})
        self.sid = ""
        self.cli = None

    def _hdr(self) -> dict:
        h = {"Content-Type": "application/json",
             "Accept": "application/json, text/event-stream"}
        h.update(self.headers)
        if self.sid:
            h["Mcp-Session-Id"] = self.sid
            h["MCP-Protocol-Version"] = PROTO
        return h

    async def _connect(self) -> None:
        import httpx
        self.cli = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0),
                                     follow_redirects=True)

    async def _post(self, msg: dict, timeout: float = 45) -> dict:
        rid = msg.get("id")
        async with self.cli.stream("POST", self.url, headers=self._hdr(),
                                   json=msg, timeout=timeout) as r:
            if sid := r.headers.get("mcp-session-id"):
                self.sid = sid
            if r.status_code >= 400:
                body = await r.aread()
                raise RuntimeError(f"HTTP {r.status_code}: {body[:160]!r}")
            ct = (r.headers.get("content-type") or "").lower()
            if "text/event-stream" in ct:
                data: list = []
                async for line in r.aiter_lines():
                    if line.startswith("data:"):
                        data.append(line[5:].strip())
                        continue
                    if line.strip() == "" and data:
                        d = _json("\n".join(data))
                        data = []
                        if not d:
                            continue
                        if rid is None or d.get("id") == rid:
                            if "error" in d:
                                raise RuntimeError(str(d["error"])[:200])
                            return d.get("result") or d
                return {}
            body = await r.aread()
            d = _json(body)
            if not isinstance(d, dict):
                return {}
            if "error" in d:
                raise RuntimeError(str(d["error"])[:200])
            return d.get("result") or {}

    async def _once(self, method: str, params: dict, timeout: float = 45) -> dict:
        async with self._lock:
            self._id += 1
            return await self._post({"jsonrpc": "2.0", "id": self._id,
                                     "method": method, "params": params}, timeout)

    async def _rehandshake(self) -> None:
        """丢掉过期的会话，重新握手（并把工具表刷一遍）。

        ★ 先把 `self.sid` 清空再 initialize —— 带着旧 id 去 initialize 会被
          同一个 404 再打回来，那就成了死循环。
        """
        self.sid = ""
        async with self._lock:
            self._id += 1
            await self._post({"jsonrpc": "2.0", "id": self._id, "method": "initialize",
                              "params": {"protocolVersion": PROTO, "capabilities": {},
                                         "clientInfo": {"name": "lianhuan", "version": "0.2"}}},
                             20)
        await self._notify("notifications/initialized")
        try:                                  # 顺手刷新工具表：服务端重启后工具可能变了
            ts = (await self._once("tools/list", {}, 20) or {}).get("tools") or []
            if ts:
                self.tools = ts
        except Exception:
            pass

    async def _rpc(self, method: str, params: dict, timeout: float = 45) -> dict:
        try:
            return await self._once(method, params, timeout)
        except RuntimeError as e:
            # ★ 服务端重启 / 会话超时之后，旧 id 就作废了。原来这里直接把
            #   `HTTP 404 … Session not found` 抛出去 —— 那台 MCP 在**整个进程重启
            #   之前**一直是坏的：`alive()` 只看 httpx 客户端还在不在，永远说「活着」，
            #   `start_all()` 也就永远不去重连。现在按规范就地重连一次。
            if not (self.sid and _session_gone(e)):
                raise
            self.err = ""
            await self._rehandshake()
            return await self._once(method, params, timeout)

    async def _notify(self, method: str) -> None:
        try:
            r = await self.cli.post(self.url, headers=self._hdr(),
                                    json={"jsonrpc": "2.0", "method": method}, timeout=20)
            if sid := r.headers.get("mcp-session-id"):
                self.sid = sid
        except Exception:
            pass

    def alive(self) -> bool:
        return self.cli is not None

    async def close(self) -> None:
        if self.cli:
            try:
                await self.cli.aclose()
            except Exception:
                pass
            self.cli = None


class _SseServer(_Server):
    """老的 HTTP+SSE：GET 一条流，第一个事件给出 message 端点；POST 到那儿，回包从流里来。"""

    def __init__(self, name: str, spec: dict):
        super().__init__(name, spec)
        self.url = (spec.get("url") or "").strip()
        self.headers = dict(spec.get("headers") or {})
        self.endpoint = ""
        self.cli = None
        self._pump_task = None
        self._wait: dict = {}                     # id -> Future

    async def _connect(self) -> None:
        import httpx
        self.cli = httpx.AsyncClient(timeout=httpx.Timeout(None, connect=15.0),
                                     follow_redirects=True)
        self._pump_task = asyncio.create_task(self._pump())
        for _ in range(150):                      # 最多等 15 秒
            if self.endpoint:
                return
            if self.err:
                raise RuntimeError(self.err)
            await asyncio.sleep(0.1)
        raise RuntimeError("没等到 SSE 的 message 端点")

    async def _pump(self) -> None:
        h = {"Accept": "text/event-stream"}
        h.update(self.headers)
        try:
            async with self.cli.stream("GET", self.url, headers=h) as r:
                ev, data = "", []
                async for line in r.aiter_lines():
                    if line.startswith("event:"):
                        ev = line[6:].strip()
                    elif line.startswith("data:"):
                        data.append(line[5:].strip())
                    elif line.strip() == "" and data:
                        self._on_event(ev, "\n".join(data))
                        ev, data = "", []
        except Exception as e:
            self.err = f"{type(e).__name__}: {e}"[:160]
            for f in list(self._wait.values()):
                if not f.done():
                    f.set_exception(RuntimeError("SSE 断了"))
            self._wait.clear()

    def _on_event(self, ev: str, payload: str) -> None:
        if ev == "endpoint" or (not self.endpoint and payload.startswith("/")):
            self.endpoint = urljoin(self.url, payload)
            return
        d = _json(payload)
        if not isinstance(d, dict):
            return
        f = self._wait.pop(d.get("id"), None)
        if f and not f.done():
            if "error" in d:
                f.set_exception(RuntimeError(str(d["error"])[:200]))
            else:
                f.set_result(d.get("result") or {})

    def _post_hdr(self) -> dict:
        h = {"Content-Type": "application/json"}
        h.update(self.headers)
        return h

    async def _rpc(self, method: str, params: dict, timeout: float = 45) -> dict:
        async with self._lock:
            self._id += 1
            rid = self._id
            fut = asyncio.get_running_loop().create_future()
            self._wait[rid] = fut
            await self.cli.post(self.endpoint, headers=self._post_hdr(),
                                json={"jsonrpc": "2.0", "id": rid,
                                      "method": method, "params": params})
            return await asyncio.wait_for(fut, timeout=timeout)

    async def _notify(self, method: str) -> None:
        try:
            await self.cli.post(self.endpoint, headers=self._post_hdr(),
                                json={"jsonrpc": "2.0", "method": method})
        except Exception:
            pass

    def alive(self) -> bool:
        return bool(self._pump_task and not self._pump_task.done())

    async def close(self) -> None:
        if self._pump_task:
            self._pump_task.cancel()
            self._pump_task = None
        if self.cli:
            try:
                await self.cli.aclose()
            except Exception:
                pass
            self.cli = None


def _json(raw) -> dict:
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", "replace")
        return json.loads(raw)
    except Exception:
        return {}


def _make(name: str, spec: dict) -> _Server:
    t = (spec.get("type") or "").strip().lower()
    if spec.get("url"):
        if t in ("sse", "http+sse", "eventsource"):
            return _SseServer(name, spec)
        if not t and spec["url"].rstrip("/").endswith("/sse"):
            return _SseServer(name, spec)      # 没写 type，但地址像老的 SSE
        return _HttpServer(name, spec)
    return _StdioServer(name, spec)


# ────────────────────── 起停 / 对外 ──────────────────────

async def start_all() -> None:
    for name, spec in load_cfg().items():
        if not enabled_of(spec):
            old = _servers.pop(name, None)
            if old:
                await old.close()              # 关掉：断开连接，工具一起消失
            continue
        old = _servers.get(name)
        if old and old.tools and old.spec == spec and old.alive():
            continue                           # 没变、还活着，不动它
        if old:
            await old.close()
        s = _make(name, spec)
        _servers[name] = s
        await s.start()


def status() -> list:
    cfg = load_cfg()
    out = []
    for n, spec in cfg.items():
        s = _servers.get(n)
        hh = spec.get("headers") if isinstance(spec.get("headers"), dict) else {}
        hh = hh or {}
        out.append({
            "name": n,
            "type": (spec.get("type") or ("http" if spec.get("url") else "stdio")),
            "url": spec.get("url") or "",
            "command": spec.get("command") or "",
            "enabled": enabled_of(spec),
            # ★ 只有名字和前四位尾巴 —— 请求头里往往就是 Bearer token，界面不回显明文
            "header_names": sorted(hh.keys()),
            "headers_masked": {k: _mask(v) for k, v in hh.items()},
            "tools": [t.get("name") for t in (s.tools if s else [])],
            "ok": bool(s and s.tools),
            "err": (s.err if s else "") or "",
        })
    return out


async def probe(spec: dict, timeout: float = 75.0) -> dict:
    """拿一份**还没保存**的配置试连一次：不写文件、不进 _servers、不留连接。

    ★ 跟「引擎那把 key 认一下」同一个道理：填好就想知道通不通，不该逼人先存一遍
      （存了才发现连不上，还得回来改）。连上了就把它认到几个工具一起报出来。
    """
    s = _make("probe", spec)
    try:
        await asyncio.wait_for(s.start(), timeout=timeout)
    except asyncio.TimeoutError:
        await s.close()
        return {"ok": False, "err": f"连了 {int(timeout)} 秒没连上（超时）", "tools": []}
    except Exception as e:                                     # noqa: BLE001
        await s.close()
        return {"ok": False, "err": f"{type(e).__name__}: {e}"[:200], "tools": []}
    try:
        return {"ok": not s.err, "err": s.err or "",
                "tools": [t.get("name") for t in s.tools]}
    finally:
        await s.close()


def _slug(s: str) -> str:
    """把一段名字压成 openai 肯收的 ASCII；**压过了就接一小段哈希**。

    ★ 为什么非接哈希不可：中文 server 名（「潮汐岛」）被压出来是一串下划线 ——
      两台中文名的 MCP 压出来**一模一样**，工具名就撞了。撞了以后 `execute()`
      会命中先注册的那台：你调「潮汐岛」的动作，落到别人地头上。
      接一段 sha1 前 6 位，既不撞、又跟原名一一对应（同一个名字永远同一串）。
    """
    s = str(s or "")
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", s)
    if s and safe == s:
        return safe                       # 本来就是 ASCII：一个字都不动（老用户的工具名不变）
    h = hashlib.sha1(s.encode("utf-8")).hexdigest()[:6]
    return (safe[:24] or "") + "_" + h


def _session_gone(err) -> bool:
    """这个报错是不是「你那边的会话已经没了」。

    Streamable HTTP 的规矩：`initialize` 时服务端在 `Mcp-Session-Id` 里给一个会话，
    之后每个请求都要带上它。**服务端一重启、或者会话闲置超时，这个 id 就作废了** ——
    再拿它去问，回的是一句
      `HTTP 404 {"code":-32600,"message":"Session not found"}`。
    ★ MCP 规范对此有明文：收到 404 且请求里带着 session id 时，客户端**必须**
      丢掉旧 id、重新发一次 initialize，而不是把这个 404 直接抛给人。
    """
    t = str(err or "").lower()
    if "404" not in t:
        return False
    return ("session not found" in t) or ("-32600" in t) or ("session" in t and "not found" in t)


def _fn_name(server: str, tool: str) -> str:
    """openai 函数名只许 [A-Za-z0-9_-] 64 字内（超了整条请求会被 400 打回来）。"""
    head, tail = _slug(server), _slug(tool)
    name = f"{head}__{tail}"
    if len(name) <= 64:
        return name
    # 太长要截：**头尾都截**，哈希挂在尾巴上 —— 否则两个长名字截成同一个，
    # 又回到「调错服务器」那条老路上。（头不截的话，光一个长 server 名就超了。）
    h = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
    # 64 里要扣掉：`__` 2 位 + 哈希前那个 `_` 1 位 + 哈希 6 位 = 9
    budget = 64 - 9
    hh = min(len(head), max(1, budget // 2))
    tt = max(1, budget - hh)
    return f"{head[:hh]}__{tail[:tt]}_{h}"


def server_of(fn_name: str) -> str | None:
    """这个函数名是哪台 MCP 的；认不出来回 None。

    ★ 别拿 `name.split("__")[0]` 去猜服务器 —— 中文名的 server 压出来是一串下划线，
      切出来是**空字符串**，于是权限那道门认不出是谁，把整台服务器的工具全拒了：
      界面上开关是开的、工具也发给了模型，可模型一调就回
      「「」这个 MCP 没给这位助手开」—— 它只能跟人说「没打开」。
    """
    for n, s in _servers.items():
        for t in s.tools:
            if _fn_name(n, t["name"]) == fn_name:
                return n
    return None


def tools_by_server() -> dict:
    """每台 MCP **真正能调用的**函数名，按 server 分组。

    ★ 给模型看的必须是这一份：`status()` 里那些是**原始工具名**，
      而它真正要写在 tool_call 里的是 `_fn_name()` 压过的那个。
      报原始名它就对不上，一调就「没有这只手」。
    """
    out = {}
    for n, s in _servers.items():
        if s.tools:
            out[n] = [_fn_name(n, t["name"]) for t in s.tools]
    return out


def openai_tools(only=None) -> list:
    """给模型的 MCP 工具。`only` 给一组 server 名字 ＝ 只要这几个的（助手那一层用）。

    `only=None` ＝ 不限（老行为）；`only=[]` ＝ 一个都不给。"""
    want = None if only is None else {str(x) for x in only}
    out = []
    for n, s in _servers.items():
        if want is not None and n not in want:
            continue
        if not s.tools:
            continue
        for t in s.tools:
            out.append({"type": "function", "function": {
                "name": _fn_name(n, t["name"]),
                "description": f"[{n}] " + (t.get("description") or "")[:400],
                "parameters": t.get("inputSchema") or {"type": "object", "properties": {}}}})
    return out


async def execute(fn_name: str, args: dict) -> dict | None:
    """认领得了就执行，认领不了返回 None（让内置的手接着试）。"""
    for n, s in _servers.items():
        for t in s.tools:
            if _fn_name(n, t["name"]) == fn_name:
                try:
                    return await s.call(t["name"], args)
                except Exception as e:
                    return {"ok": False, "err": f"{type(e).__name__}: {e}"[:200]}
    return None


async def call_tool(server: str, tool: str, args: dict) -> dict | None:
    """按名字直接调一个 MCP 工具，不把内部 server 对象暴露给路由。"""
    s = _servers.get(server)
    if not s or not any(t.get("name") == tool for t in s.tools):
        return None
    try:
        return await s.call(tool, args)
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {e}"[:200]}
# ── 补丁：装配单编码兜底（手写文件里混进非 UTF-8 字符时不至于整个读不出来）
def _read_text_any(f) -> str:
    raw = f.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def load_cfg() -> dict:          # 覆盖上面那版，其余逻辑不变
    import json as _j
    try:
        return _j.loads(_read_text_any(_cfg_file())).get("mcpServers") or {}
    except Exception:
        return {}
