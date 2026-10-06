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
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin

_servers: dict = {}          # name -> _Server

PROTO = "2025-06-18"         # 对 server 声明的协议版本；某个 server 不认就改这一行


# ────────────────────── 装配单 ──────────────────────

def _cfg_file() -> Path:
    return Path(os.environ.get("LIANHUAN_DB", "data/lianhuan.db")).parent / "mcp.json"


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

    async def _rpc(self, method: str, params: dict, timeout: float = 45) -> dict:
        async with self._lock:
            self._id += 1
            return await self._post({"jsonrpc": "2.0", "id": self._id,
                                     "method": method, "params": params}, timeout)

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
        out.append({
            "name": n,
            "type": (spec.get("type") or ("http" if spec.get("url") else "stdio")),
            "url": spec.get("url") or "",
            "command": spec.get("command") or "",
            "enabled": enabled_of(spec),
            "tools": [t.get("name") for t in (s.tools if s else [])],
            "ok": bool(s and s.tools),
            "err": (s.err if s else "") or "",
        })
    return out


def _fn_name(server: str, tool: str) -> str:
    """openai 函数名只许 [A-Za-z0-9_-] 64 字内。"""
    return re.sub(r"[^A-Za-z0-9_-]", "_", f"{server}__{tool}")[:64]


def openai_tools() -> list:
    out = []
    for n, s in _servers.items():
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
