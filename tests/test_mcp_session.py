"""Streamable HTTP 的会话过期了要自己重连 —— 不然后面**一直坏**。

真机上撞到的（lutopia 那台）：

    RuntimeError: HTTP 404: b'{"jsonrpc":"2.0","id":"server-error",
      "error":{"code":-32600,"message":"Session not found"}}'

Streamable HTTP 的规矩：`initialize` 时服务端在 `Mcp-Session-Id` 响应头里给一个会话，
之后每个请求都要带上它。**服务端一重启、或者会话闲置超时，这个 id 就作废了**。

原来的两条凑成「坏到进程重启为止」：
  ① `_post()` 碰到 404 直接 `raise`，一个字都不重试；
  ② `alive()` 只看 `self.cli is not None`（httpx 客户端还在）—— 会话早没了它照样说「活着」，
     于是 `start_all()` 那句 `if old.tools and old.spec == spec and old.alive(): continue`
     永远成立，**永远不去重连**。

MCP 规范对①有明文：收到 404 且请求里带着 session id 时，客户端**必须**丢掉旧 id、
重新发一次 initialize，而不是把这个 404 抛给人。
"""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from core import mcp_client as M  # noqa: E402

SESSION_BODY = {"jsonrpc": "2.0", "id": "server-error",
                "error": {"code": -32600, "message": "Session not found"}}


class _Resp:
    def __init__(self, status, payload, sid=None):
        self.status_code = status
        self._p = payload
        self.headers = {"mcp-session-id": sid} if sid else {}

    async def aread(self):
        return json.dumps(self._p).encode()

    async def aiter_lines(self):
        for line in ():
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakeServer:
    """一台最小的 Streamable HTTP 服务端：只认自己发出去的那个会话 id。"""

    def __init__(self):
        self.sid = ""
        self.n_init = 0
        self.n_calls = 0

    def _handle(self, headers, payload):
        hdr = {k.lower(): v for k, v in (headers or {}).items()}
        method = (payload or {}).get("method") or ""
        if method == "initialize":
            self.n_init += 1
            self.sid = "sid-%d" % self.n_init
            return _Resp(200, {"jsonrpc": "2.0", "id": payload.get("id"),
                               "result": {"protocolVersion": M.PROTO,
                                          "capabilities": {},
                                          "serverInfo": {"name": "fake", "version": "1"}}},
                         sid=self.sid)
        sent = hdr.get("mcp-session-id") or ""
        if sent != self.sid:
            return _Resp(404, SESSION_BODY)          # ★ 就是用户看到的那句
        self.n_calls += 1
        if method == "tools/list":
            return _Resp(200, {"jsonrpc": "2.0", "id": payload.get("id"),
                               "result": {"tools": [{"name": "ping", "description": "test",
                                                     "inputSchema": {"type": "object",
                                                                     "properties": {}}}]}})
        return _Resp(200, {"jsonrpc": "2.0", "id": payload.get("id"),
                           "result": {"content": [{"type": "text", "text": "pong"}]}})


class _FakeClient:
    def __init__(self, srv):
        self.srv = srv

    def stream(self, method, url, headers=None, json=None, timeout=None):  # noqa: A002
        return self.srv._handle(headers, json)

    async def post(self, url, headers=None, json=None, timeout=None):  # noqa: A002
        return self.srv._handle(headers, json)

    async def aclose(self):
        pass


_SPEC = {"url": "https://example.invalid/mcp", "type": "http"}


class _FakeTransport:
    """把 httpx.AsyncClient 换掉。★ `_connect()` 自己会 new 一个，
    所以只能打在模块上 —— 光给 s.cli 赋值会被它覆盖掉。"""

    def __init__(self):
        self.real = httpx.AsyncClient
        self.srv = _FakeServer()

    def __enter__(self):
        httpx.AsyncClient = lambda *a, **kw: _FakeClient(self.srv)
        return self.srv

    def __exit__(self, *a):
        httpx.AsyncClient = self.real
        return False

    def new(self):
        return M._HttpServer("fake", _SPEC)


class TestTheDetector(unittest.TestCase):
    def test_it_recognises_the_real_body(self):
        self.assertTrue(M._session_gone(
            "HTTP 404: b'{\"jsonrpc\":\"2.0\",\"id\":\"server-error\","
            "\"error\":{\"code\":-32600,\"message\":\"Session not found\"}}'"))

    def test_it_does_not_fire_on_other_404s(self):
        """地址写错也是 404 —— 那种重连一百次也没用，别把它也当成会话过期。"""
        for other in ("HTTP 404: b'Not Found'",
                      "HTTP 404: b'{\"error\":\"no such endpoint\"}'",
                      "HTTP 500: b'Session not found'",     # 不是 404
                      "HTTP 401: b'unauthorized'"):
            self.assertFalse(M._session_gone(other), other)


class TestItReconnects(unittest.TestCase):
    def test_a_stale_session_heals_itself(self):
        async def run():
            with _FakeTransport() as srv:
                s = M._HttpServer("fake", _SPEC)
                await s.start()
                self.assertEqual(["ping"], [t["name"] for t in s.tools])
                self.assertEqual(1, srv.n_init)

                s.sid = "stale-session-id"        # 模拟服务端重启 / 空闲超时
                r = await s.call("ping", {})      # 以前这里直接抛 RuntimeError
                self.assertIn("pong", json.dumps(r, ensure_ascii=False))
                self.assertEqual(2, srv.n_init, "应该重新握了一次手")
                self.assertNotEqual("stale-session-id", s.sid, "会话 id 该换成新的了")
                # 换过之后接着用还是好的（不是只管一次）
                self.assertIn("pong", json.dumps(await s.call("ping", {}), ensure_ascii=False))
        asyncio.run(run())

    def test_it_refreshes_the_tool_list_too(self):
        """服务端重启之后工具可能变了 —— 顺手刷一遍，别拿着旧的。"""
        async def run():
            with _FakeTransport() as srv:
                s = M._HttpServer("fake", _SPEC)
                await s.start()
                s.tools = [{"name": "old_tool"}]
                s.sid = "stale"
                await s.call("ping", {})
                self.assertEqual(["ping"], [t["name"] for t in s.tools])
        asyncio.run(run())

    def test_it_retries_only_once(self):
        """重连之后还是 404 就得抛出去 —— 不能转圈转到天荒地老。"""
        async def run():
            with _FakeTransport() as srv:
                s = M._HttpServer("fake", _SPEC)
                await s.start()
                s.sid = "stale"
                orig = srv._handle

                def always_404(headers, payload):
                    r = orig(headers, payload)
                    if r.status_code == 200 and (payload or {}).get("method") not in (
                            "initialize", "notifications/initialized"):
                        return _Resp(404, SESSION_BODY)
                    return r
                srv._handle = always_404
                with self.assertRaises(RuntimeError) as cm:
                    await s.call("ping", {})
                self.assertIn("404", str(cm.exception))
                self.assertLessEqual(srv.n_init, 3, "别无限重连")
        asyncio.run(run())

    def test_a_fresh_connection_does_not_try_to_rehandshake(self):
        """还没握过手（sid 是空的）时碰到 404，那是真有问题（地址错了），别重连。"""
        async def run():
            with _FakeTransport() as srv:
                s = M._HttpServer("fake", _SPEC)
                s.cli = _FakeClient(srv)
                s.sid = ""
                srv._handle = lambda h, p: _Resp(404, SESSION_BODY)   # 一律 404
                with self.assertRaises(RuntimeError):
                    await s._rpc("tools/list", {})
                self.assertEqual(0, srv.n_init, "还没握过手就别去重连（地址错了重连也没用）")
        asyncio.run(run())


class TestTheOldBehaviourWouldHaveFailed(unittest.TestCase):
    def test_the_raw_error_is_what_the_user_saw(self):
        """把这次的报错原文钉住：以后谁再看到这句，能一眼找到这段注释。"""
        async def run():
            with _FakeTransport() as srv:
                s = M._HttpServer("fake", _SPEC)
                await s.start()
                s.sid = "stale"
                # 直接调底层那一步：老行为就是把这句原样抛出来
                try:
                    await s._once("tools/list", {})
                except RuntimeError as e:
                    self.assertIn("Session not found", str(e))
                    self.assertIn("404", str(e))
                    return
                self.fail("过期会话居然没报错？")
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
