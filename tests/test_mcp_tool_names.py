"""MCP 工具名：中文 server 名不许把工具名碾成一串下划线。

真机上撞到的：用户把一台 MCP 起名叫「潮汐岛」，界面上开关是**开的**，
工具也确实发给了模型 —— 可模型一调就回「没打开」。

三处凑成的：
  ①  `_fn_name("潮汐岛", "relay_manual")` 把中文全压成 `_` → `_____relay_manual`；
      两台中文名的 MCP 压出来**一模一样**，工具名会撞（撞了就调错服务器）。
  ②  `exec_guard` 拿 `name.split("__")[0]` 猜是哪台服务器 → 切出来是**空字符串**
      → 「助手开了这台」也照样被拒，报错还写着「「」这个 MCP…」。
  ③  `list_my_tools` 报的是 MCP 的**原始工具名**（`relay_manual`），
      而模型真要调用的是压过的那个（`_____relay_manual`）—— 对不上，
      于是它被问「潮汐岛开着吗」时只能答「没打开」。
"""
from __future__ import annotations

import asyncio
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import hands, mcp_client  # noqa: E402

LEGAL = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class _FakeServer:
    """假的一台 MCP：只要 `.tools` 长得对，server_of / tools_by_server 就能用。"""

    def __init__(self, tools):
        self.tools = [{"name": t, "description": f"{t} 的说明",
                       "inputSchema": {"type": "object", "properties": {}}} for t in tools]


class TestFnName(unittest.TestCase):
    def test_ascii_names_are_untouched(self):
        """老用户（英文名）的工具名一个字都不许变。"""
        self.assertEqual("games__list_games", mcp_client._fn_name("games", "list_games"))
        self.assertEqual("besideyou__ping", mcp_client._fn_name("besideyou", "ping"))

    def test_the_result_is_always_legal_for_openai(self):
        for srv in ("潮汐岛", "花园", "AIsay小镇", "games", "带 空格 的名字", "x" * 80):
            for tool in ("play", "relay_manual", "带中文的工具", "y" * 90):
                got = mcp_client._fn_name(srv, tool)
                self.assertRegex(got, LEGAL, f"{srv}/{tool} -> {got!r} 不是合法函数名")

    def test_it_is_deterministic(self):
        """同一个 server+tool 每次算出来必须一样 —— execute() 靠重算来对上号。"""
        a = mcp_client._fn_name("潮汐岛", "relay_manual")
        b = mcp_client._fn_name("潮汐岛", "relay_manual")
        self.assertEqual(a, b)

    def test_two_chinese_names_do_not_collide(self):
        """★ 这是原来最危险的一条：两台中文名的 MCP，工具名撞了 → 调错服务器。"""
        pairs = [("潮汐岛", "小花园"), ("花园", "小园"), ("AIsay小镇", "AIsay小店")]
        for one, two in pairs:
            self.assertNotEqual(mcp_client._fn_name(one, "play"),
                                mcp_client._fn_name(two, "play"),
                                f"{one} 和 {two} 的工具名撞了")

    def test_long_names_do_not_collide_either(self):
        long_a = "s" * 60 + "甲"
        long_b = "s" * 60 + "乙"
        self.assertNotEqual(mcp_client._fn_name(long_a, "t"), mcp_client._fn_name(long_b, "t"))


class TestServerOf(unittest.TestCase):
    def setUp(self):
        self._bak = dict(mcp_client._servers)
        mcp_client._servers.clear()
        mcp_client._servers["潮汐岛"] = _FakeServer(["relay_manual", "tide_ops"])
        mcp_client._servers["games"] = _FakeServer(["list_games"])

    def tearDown(self):
        mcp_client._servers.clear()
        mcp_client._servers.update(self._bak)

    def test_it_resolves_a_chinese_server(self):
        fn = mcp_client._fn_name("潮汐岛", "relay_manual")
        self.assertEqual("潮汐岛", mcp_client.server_of(fn))

    def test_it_resolves_an_ascii_server(self):
        self.assertEqual("games", mcp_client.server_of("games__list_games"))

    def test_unknown_name_returns_none(self):
        self.assertIsNone(mcp_client.server_of("games__nope"))
        self.assertIsNone(mcp_client.server_of("凭空编的__x"))

    def test_tools_by_server_reports_callable_names(self):
        got = mcp_client.tools_by_server()
        self.assertEqual(["games__list_games"], got["games"])
        self.assertEqual([mcp_client._fn_name("潮汐岛", "relay_manual"),
                          mcp_client._fn_name("潮汐岛", "tide_ops")], got["潮汐岛"])
        for names in got.values():
            for n in names:
                self.assertRegex(n, LEGAL)


class TestThePermissionGate(unittest.TestCase):
    """开关开着、工具也发了，一调却被拒 —— 用户看到的就是「显示已打开，助手说没打开」。"""

    def setUp(self):
        self._bak = dict(mcp_client._servers)
        mcp_client._servers.clear()
        mcp_client._servers["潮汐岛"] = _FakeServer(["relay_manual"])
        mcp_client._servers["games"] = _FakeServer(["list_games"])
        self.fn = mcp_client._fn_name("潮汐岛", "relay_manual")

    def tearDown(self):
        mcp_client._servers.clear()
        mcp_client._servers.update(self._bak)

    def test_an_allowed_chinese_server_is_not_refused(self):
        r = asyncio.run(hands.exec_guard(["games", "潮汐岛"])(self.fn, {}))
        self.assertNotIn("没给这位助手开", str(r),
                         "助手开了这台，就不该被权限那道门拦下")

    def test_a_disallowed_server_is_still_refused_with_its_real_name(self):
        r = asyncio.run(hands.exec_guard(["games"])(self.fn, {}))
        self.assertFalse(r.get("ok"))
        self.assertIn("潮汐岛", r["err"], "报错里得写清是哪台，不能是空名字")
        self.assertNotIn("「」", r["err"], "不许再出现空的「」")


class TestListMyToolsTellsTheTruth(unittest.TestCase):
    def setUp(self):
        self._bak = dict(mcp_client._servers)
        mcp_client._servers.clear()
        mcp_client._servers["潮汐岛"] = _FakeServer(["relay_manual"])

    def tearDown(self):
        mcp_client._servers.clear()
        mcp_client._servers.update(self._bak)

    def test_it_reports_the_names_the_model_can_actually_call(self):
        """报原始工具名 = 模型照着调必然「没有这只手」。"""
        got = asyncio.run(hands.execute("list_my_tools", {}))
        names = got["mcp"]["潮汐岛"]
        self.assertEqual([mcp_client._fn_name("潮汐岛", "relay_manual")], names)
        self.assertNotIn("relay_manual", names,
                         "原始工具名不是能调用的名字 —— 不许再报它")
        # 每个名字都得是「这台服务器上真有的那只手」
        for n in names:
            self.assertEqual("潮汐岛", mcp_client.server_of(n))


if __name__ == "__main__":
    unittest.main()
