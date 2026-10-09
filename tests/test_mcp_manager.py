"""MCP 总管理：两种 HTTP 连接方式 + 自定义请求头。

★ 这一页要真的能连上东西，所以这儿起的是**两个真的上游**（一个 Streamable HTTP、
  一个老的 HTTP+SSE），真的收 TCP、真的解 JSON-RPC —— 不是替掉 httpx 那种假。
  它证明得了「我们发得对、认得出工具、头带上了」，证明不了「某某家的 MCP 真这么回」。

★ 另一条硬线：**请求头里往往就是 Bearer token，界面只回名字和末四位**；
  编辑时值留空＝沿用已经存着的那把（跟引擎那把 key 一个规矩）。
"""
from __future__ import annotations

import json
import os
import queue
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import mcp_client                                          # noqa: E402

TOOLS = [{"name": "ping", "description": "回一声", "inputSchema": {"type": "object"}},
         {"name": "echo", "description": "原样退回", "inputSchema": {"type": "object"}}]


def _result_for(method: str, msg: dict):
    if method == "initialize":
        return {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-mcp", "version": "1"}}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        return {"content": [{"type": "text", "text": "pong"}]}
    return {}


class _HttpMcp(BaseHTTPRequestHandler):
    """Streamable HTTP：一个端点，POST JSON-RPC，回 JSON（也认 SSE 那条，见下）。"""
    protocol_version = "HTTP/1.1"
    seen: list = []

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        msg = json.loads(self.rfile.read(n) or b"{}")
        type(self).seen.append(dict(self.headers))
        rid = msg.get("id")
        if rid is None:                                   # notification
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send({"jsonrpc": "2.0", "id": rid,
                    "result": _result_for(msg.get("method") or "", msg)})


class _SseMcp(BaseHTTPRequestHandler):
    """老的 HTTP+SSE：GET /sse 给一个端点，POST 到端点，回包从那条流里来。"""
    protocol_version = "HTTP/1.1"
    box: "queue.Queue" = None
    seen: list = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        if not self.path.startswith("/sse"):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        type(self).seen.append(dict(self.headers))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b"event: endpoint\ndata: /messages\n\n")
        self.wfile.flush()
        box = queue.Queue()
        type(self).box = box
        while True:
            item = box.get()
            if item is None:
                break
            self.wfile.write(("event: message\ndata: " + json.dumps(item) + "\n\n").encode())
            self.wfile.flush()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        msg = json.loads(self.rfile.read(n) or b"{}")
        type(self).seen.append(dict(self.headers))
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()
        if msg.get("id") is not None and type(self).box is not None:
            type(self).box.put({"jsonrpc": "2.0", "id": msg["id"],
                                "result": _result_for(msg.get("method") or "", msg)})


class _Live:
    """起一个假上游，跑完关掉。"""
    def __init__(self, handler):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class TestBothTransportsReallyConnect(unittest.TestCase):
    def setUp(self):
        # MCP 的装配单落在「家」里 —— 指到临时目录，别碰真的
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = str(Path(self.home.name) / "lianhuan.db")

        def restore():
            if self.old is None:
                os.environ.pop("LIANHUAN_DB", None)
            else:
                os.environ["LIANHUAN_DB"] = self.old
        self.addCleanup(restore)

    def _run(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_streamable_http_lists_tools_and_sends_our_headers(self):
        srv = _Live(_HttpMcp)
        self.addCleanup(srv.close)
        _HttpMcp.seen = []
        out = self._run(mcp_client.probe({
            "url": f"http://127.0.0.1:{srv.port}/mcp", "type": "http",
            "headers": {"Authorization": "Bearer sk-secret-token-1234",
                        "X-Custom": "hello"}}))
        self.assertTrue(out["ok"], out)
        self.assertEqual(["ping", "echo"], out["tools"])
        hdrs = _HttpMcp.seen[0]
        self.assertEqual("Bearer sk-secret-token-1234", hdrs.get("Authorization"),
                         "自定义请求头得真的发出去")
        self.assertEqual("hello", hdrs.get("X-Custom"))

    def test_the_old_sse_short_link_works_too(self):
        srv = _Live(_SseMcp)
        self.addCleanup(srv.close)
        _SseMcp.box = None
        out = self._run(mcp_client.probe({
            "url": f"http://127.0.0.1:{srv.port}/sse", "type": "sse",
            "headers": {"X-Api-Key": "k-9876"}}))
        self.assertTrue(out["ok"], out)
        self.assertEqual(["ping", "echo"], out["tools"], "SSE 那条也得把工具列出来")
        self.assertEqual("k-9876", _SseMcp.seen[0].get("X-Api-Key"))

    def test_a_wrong_address_says_why_instead_of_pretending(self):
        out = self._run(mcp_client.probe({"url": "http://127.0.0.1:1/mcp", "type": "http"}))
        self.assertFalse(out["ok"])
        self.assertTrue(out["err"], "连不上得说出原因，不能只说「失败」")


class TestTheConfigNeverEchoesSecrets(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = str(Path(self.home.name) / "lianhuan.db")
        self.addCleanup(lambda: (os.environ.pop("LIANHUAN_DB", None) if self.old is None
                                 else os.environ.__setitem__("LIANHUAN_DB", self.old)))

    def test_status_masks_header_values(self):
        mcp_client.save_http("games", "https://example.com/mcp", "http",
                             {"Authorization": "Bearer sk-abcdefgh1234", "X-Empty": ""})
        st = next(x for x in mcp_client.status() if x["name"] == "games")
        self.assertEqual(["Authorization", "X-Empty"], st["header_names"])
        self.assertEqual("…1234", st["headers_masked"]["Authorization"])
        self.assertNotIn("sk-abcdefgh", json.dumps(st), "明文一个字节都不许回给界面")

    def test_an_empty_value_keeps_the_stored_secret(self):
        """编辑时那一格是空的（不回显）—— 拿空串覆盖＝把人家的 token 抹了，而他还看不出来。"""
        mcp_client.save_http("games", "https://example.com/mcp", "http",
                             {"Authorization": "Bearer sk-abcdefgh1234"})
        mcp_client.save_http("games", "https://example.com/mcp2", "http",
                             {"Authorization": "", "X-New": "1"})
        spec = mcp_client.spec_of("games")
        self.assertEqual("Bearer sk-abcdefgh1234", spec["headers"]["Authorization"])
        self.assertEqual("1", spec["headers"]["X-New"])
        self.assertEqual("https://example.com/mcp2", spec["url"], "地址改了就是改了")

    def test_a_header_that_is_not_sent_any_more_is_dropped(self):
        mcp_client.save_http("g", "https://e/mcp", "http", {"A": "1", "B": "2"})
        mcp_client.save_http("g", "https://e/mcp", "http", {"A": "1"})
        self.assertEqual(["A"], list(mcp_client.spec_of("g")["headers"].keys()))

    def test_the_transport_is_written_down_not_guessed(self):
        """★ 明说 type —— 别再靠「地址是不是以 /sse 结尾」猜（自建代理一猜就错）。"""
        mcp_client.save_http("a", "https://e/api", "sse", None)
        mcp_client.save_http("b", "https://e/sse", "http", None)
        self.assertEqual("sse", mcp_client.spec_of("a")["type"])
        self.assertEqual("http", mcp_client.spec_of("b")["type"])


class TestTheApiLayer(unittest.TestCase):
    """接口那一层：校验、本机限制、删。"""

    @classmethod
    def setUpClass(cls):
        from starlette.testclient import TestClient
        import core.server as sv
        cls.sv = sv
        # ★ TestClient 默认的对端叫 "testclient"，那不是本机 —— 本机那一条得显式给回环地址，
        #   不然测的就不是「本机页面能用」这件事了。
        cls.c = TestClient(sv.app, client=("127.0.0.1", 51000))
        cls.c_remote = TestClient(sv.app, client=("192.168.1.20", 51234))

    def setUp(self):
        import core.gate as gate
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = str(Path(self.tmp.name) / "lh.db")
        self.sv._mcp._cfg_file = lambda: Path(self.tmp.name) / "mcp.json"
        self._gate_state = dict(gate._state)
        gate._state["on"] = False              # 这一段测的是本机/远程那条线，不是门口令
        self.addCleanup(self._restore)

    def _restore(self):
        import core.gate as gate
        gate._state.clear()
        gate._state.update(self._gate_state)
        if self.old is None:
            os.environ.pop("LIANHUAN_DB", None)
        else:
            os.environ["LIANHUAN_DB"] = self.old

    def test_add_an_http_server_with_headers(self):
        r = self.c.post("/api/mcp/save", json={
            "name": "games", "kind": "http", "url": "https://example.invalid/mcp",
            "headers": [{"name": "Authorization", "value": "Bearer xyz1234567890"}]})
        self.assertEqual(200, r.status_code)
        cfg = json.loads((Path(self.tmp.name) / "mcp.json").read_text(encoding="utf-8"))
        spec = cfg["mcpServers"]["games"]
        self.assertEqual("http", spec["type"])
        self.assertEqual("Bearer xyz1234567890", spec["headers"]["Authorization"])
        # 列出来的时候只给名字和末四位
        st = self.c.get("/api/mcp").json()["servers"][0]
        self.assertEqual("…7890", st["headers_masked"]["Authorization"])

    def test_an_sse_server_is_remembered_as_sse(self):
        self.c.post("/api/mcp/save", json={"name": "old1", "kind": "sse",
                                           "url": "https://example.invalid/stream"})
        cfg = json.loads((Path(self.tmp.name) / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual("sse", cfg["mcpServers"]["old1"]["type"],
                         "地址里没有 /sse 也得按选的走")

    def test_bad_input_says_what_is_missing(self):
        for body, word in (
            ({"name": "", "kind": "http", "url": "https://x/mcp"}, "名字"),
            ({"name": "a", "kind": "http", "url": ""}, "地址"),
            ({"name": "a", "kind": "http", "url": "ftp://x"}, "http"),
            ({"name": "a", "kind": "没这个", "url": "https://x"}, "三种"),
            ({"name": "a", "kind": "stdio", "command": ""}, "命令"),
        ):
            r = self.c.post("/api/mcp/save", json=body)
            self.assertEqual(400, r.status_code, body)
            self.assertIn(word, r.json()["error"], body)

    def test_a_local_command_cannot_be_added_from_another_device(self):
        """★ 起进程那条线不放松：手机上想加 MCP，用 Streamable HTTP 或 SSE 那种地址。"""
        r = self.c_remote.post("/api/mcp/save", json={"name": "x", "kind": "stdio",
                                                      "command": "npx -y something"})
        self.assertEqual(403, r.status_code)
        self.assertIn("本机", r.json()["error"])
        r2 = self.c_remote.post("/api/mcp/probe", json={"name": "x", "kind": "stdio",
                                                        "command": "npx -y something"})
        self.assertEqual(403, r2.status_code)

    def test_an_http_server_can_be_added_from_the_phone(self):
        """HTTP/SSE 不发命令，只是这台机器往外连一个你填的地址 —— 手机上也能加。"""
        r = self.c_remote.post("/api/mcp/save", json={
            "name": "phone", "kind": "http", "url": "https://example.invalid/mcp"})
        self.assertEqual(200, r.status_code, r.text)

    def test_listing_tells_the_page_whether_it_is_local(self):
        self.assertTrue(self.c.get("/api/mcp").json()["local"])
        self.assertFalse(self.c_remote.get("/api/mcp").json()["local"],
                         "界面拿它决定「本机命令」那一档能不能选")

    def test_remove_and_rename(self):
        self.c.post("/api/mcp/save", json={"name": "a", "kind": "http", "url": "https://x/mcp"})
        self.c.post("/api/mcp/save", json={"name": "b", "kind": "http", "url": "https://x/mcp",
                                           "old_name": "a"})
        names = {s["name"] for s in self.c.get("/api/mcp").json()["servers"]}
        self.assertEqual({"b"}, names, "改了名字就不该留下一条僵尸")
        r = self.c.post("/api/mcp/save", json={"name": "b", "kind": "http", "remove": True})
        self.assertTrue(r.json()["ok"])
        self.assertEqual([], self.c.get("/api/mcp").json()["servers"])


if __name__ == "__main__":
    unittest.main()
