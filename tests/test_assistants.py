"""助手 —— 一位助手下面挂几扇窗，各有各的口吻、工具。

★ 这一层的两条硬规矩（每一条都有真机上撞出来的理由）：
  ① **没配过助手＝老行为**：人设还是全局那份、工具照旧全给。老库升级不该被改脾气。
  ② **MCP 不同步**：第一位助手没勾过＝不限（老行为）；新建的助手＝一个都不给，
     要哪个在它的设置里手动勾。表筛过一遍还不够，执行那一步再拦一道。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import assistants as A                                    # noqa: E402
from core.store.sqlite import SqliteStore                           # noqa: E402


class _S:
    """够 assistants 用的最小 store（就是 get_setting / set_setting）。"""
    def __init__(self):
        self.d = {}

    def get_setting(self, k, default=None):
        return self.d.get(k, default)

    def set_setting(self, k, v):
        self.d[k] = v


class TestTheModel(unittest.TestCase):
    def setUp(self):
        self.s = _S()

    def test_nothing_configured_means_the_old_behaviour(self):
        self.assertEqual([], A.all_items(self.s))
        self.assertIsNone(A.assistant_of(self.s, "main"), "没配过＝这一层不生效")
        self.assertIsNone(A.mcp_allow(self.s, "main"), "没配过＝MCP 不限（老行为）")
        self.assertIsNone(A.persona_for(self.s, None), "没配过＝人设照旧读全局那份")

    def test_first_assistant_is_unlimited_second_one_gets_nothing(self):
        a = A.create(self.s, name="阿澈")
        self.assertIsNone(a["mcp"], "第一位＝不限（老行为一字不差）")
        b = A.create(self.s, name="小满")
        self.assertEqual([], b["mcp"], "新建的助手＝一个都不给，要哪个手动勾")
        self.assertIsNone(A.mcp_allow(self.s, "main"))
        A.attach_window(self.s, "t9", b["id"])
        self.assertEqual([], A.mcp_allow(self.s, "t9"))

    def test_windows_fall_back_to_the_first_assistant(self):
        a = A.create(self.s, name="阿澈")
        b = A.create(self.s, name="小满")
        self.assertEqual(a["id"], A.assistant_of(self.s, "main")["id"])
        self.assertEqual(a["id"], A.assistant_of(self.s, "从没挂过的窗口")["id"])
        A.attach_window(self.s, "t3", b["id"])
        self.assertEqual(b["id"], A.assistant_of(self.s, "t3")["id"])
        # 一个窗口只属于一位：挂到别处就从原来那位那儿摘掉
        A.attach_window(self.s, "t3", a["id"])
        self.assertEqual(a["id"], A.assistant_of(self.s, "t3")["id"])
        self.assertNotIn("t3", A.get(self.s, b["id"])["windows"])

    def test_removing_an_assistant_gives_his_windows_back_to_the_first(self):
        a = A.create(self.s, name="阿澈")
        b = A.create(self.s, name="小满")
        A.attach_window(self.s, "t3", b["id"])
        self.assertTrue(A.remove(self.s, b["id"]))
        self.assertEqual(a["id"], A.assistant_of(self.s, "t3")["id"],
                         "删了助手，窗口（和聊天记录）得留下 —— 退回第一位")
        self.assertEqual(1, len(A.all_items(self.s)))

    def test_persona_override_only_touches_the_ai_side(self):
        self.s.set_setting("persona", {"ai": {"name": "旧的", "text": "全局那份"},
                                       "human": {"name": "我", "text": "别动我"}})
        a = A.create(self.s, name="阿澈", prompt="你是阿澈")
        p = A.persona_for(self.s, A.get(self.s, a["id"]))
        self.assertEqual("阿澈", p["ai"]["name"])
        self.assertEqual("你是阿澈", p["ai"]["text"])
        self.assertEqual("别动我", p["human"]["text"], "「你在跟谁说话」跟换助手无关")
        # 没写提示词的助手 → 那条继承全局，别把人格清空
        b = A.create(self.s, name="小满")
        self.assertEqual("全局那份", A.persona_for(self.s, A.get(self.s, b["id"]))["ai"]["text"])

    def test_the_sign_is_real_not_decoration(self):
        a = A.create(self.s, name="阿澈", sign="今天也在")
        line = A.sign_line(A.get(self.s, a["id"]))
        self.assertIn("今天也在", line)
        self.assertEqual("", A.sign_line(None))

    def test_a_hand_edited_json_cannot_break_it(self):
        self.s.set_setting("assistants", {"items": [
            {"id": "x", "name": None, "mcp": "乱写的", "windows": "不是列表"},
            {"id": "x", "name": "重复 id"},          # 同一个 id 只留一条
            "根本不是对象",
        ]})
        items = A.all_items(self.s)
        self.assertEqual(1, len(items))
        self.assertEqual([], items[0]["windows"])
        self.assertEqual("", items[0]["name"])


class TestToolsAreFilteredPerAssistant(unittest.TestCase):
    def setUp(self):
        from core import mcp_client, hands
        self.hands, self.mcp = hands, mcp_client
        self.all = hands.TOOLS + [
            {"type": "function", "function": {"name": "games__play", "parameters": {}}},
            {"type": "function", "function": {"name": "notes__read", "parameters": {}}},
        ]
        self._orig = mcp_client.openai_tools

        def fake(only=None):
            pool = [t for t in self.all if "__" in t["function"]["name"]]
            if only is None:
                return pool
            want = {str(x) for x in only}
            return [t for t in pool if t["function"]["name"].split("__", 1)[0] in want]

        mcp_client.openai_tools = fake
        self.addCleanup(lambda: setattr(self.mcp, "openai_tools", self._orig))

    def names(self, tools):
        return [t["function"]["name"] for t in tools]

    def test_unlimited_keeps_everything(self):
        self.assertEqual(self.names(self.all), self.names(self.hands.tools_for(self.all, None)),
                         "不限＝老行为，一个都不许少")

    def test_empty_allow_keeps_the_builtin_hands(self):
        got = self.names(self.hands.tools_for(self.all, []))
        self.assertNotIn("games__play", got)
        self.assertNotIn("notes__read", got)
        self.assertIn("write_memory", got, "内置的手是这台机器自己的功能，不该被一起收走")
        self.assertIn("post_moment", got)

    def test_only_the_allowed_servers(self):
        got = self.names(self.hands.tools_for(self.all, ["games"]))
        self.assertIn("games__play", got)
        self.assertNotIn("notes__read", got)

    def test_execution_is_guarded_too(self):
        """★ 表是「发出去时」的样子 —— 跑着跑着用户把 MCP 关了，模型就不能再动它。"""
        import asyncio
        guard = self.hands.exec_guard([])
        out = asyncio.run(guard("games__play", {"game": "x"}))
        self.assertFalse(out["ok"])
        self.assertIn("没给这位助手开", out["err"])


class TestTheApiAndTheChatWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from starlette.testclient import TestClient
        import core.server as sv
        cls.sv = sv
        cls.c = TestClient(sv.app, client=("127.0.0.1", 43000))

    def setUp(self):
        from core.store.sqlite import SqliteStore as SS
        from core import views as V
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = self.sv.store
        self.old_views = V._store
        self.sv.store = SS(Path(self.tmp.name) / "lh.db")
        # ★ `/api/assistants` 那几条挂在 views 的 router 上，用的是 views._store ——
        #   只换 sv.store 的话，助手存在一个库、聊天读另一个库，测出来的全是假象。
        V.bind(self.sv.store)
        self.addCleanup(self._restore)

    def _restore(self):
        from core import views as V
        self.sv.store = self.old
        V._store = self.old_views

    def _ask(self, sid=None):
        from core.engines.base import Engine
        from core.protocol import sse, SAY, DONE
        cap = {}

        class Cap(Engine):
            name, label, ready, stub = "cap", "捕获", True, False

            async def stream(self, turn):
                cap["t"] = turn
                cap["tools"] = [t["function"]["name"] for t in (getattr(self, "tools", None) or [])]
                yield sse(SAY, text="好")
                yield sse(DONE, session_id=turn.session_id)

        old = self.sv.pick_engine
        self.sv.pick_engine = lambda: Cap()
        self.addCleanup(lambda: setattr(self.sv, "pick_engine", old))
        body = {"message": "在吗"}
        if sid:
            body["session_id"] = sid
        list(self.c.post("/chat", json=body).iter_lines())
        return cap["t"]

    def test_crud_and_windows(self):
        self.assertFalse(self.c.get("/api/assistants").json()["enabled"])
        a = self.c.post("/api/assistants/save", json={"name": "阿澈", "sign": "今天也在",
                                                      "prompt": "你是阿澈"}).json()["item"]
        self.assertTrue(self.c.get("/api/assistants").json()["enabled"])
        self.assertEqual("阿澈", self.c.get("/api/assistants/who?sid=main").json()["assistant"]["name"])
        b = self.c.post("/api/assistants/save", json={"name": "小满", "mcp": []}).json()["item"]
        self.assertTrue(self.c.post("/api/assistants/window",
                                    json={"sid": "t9", "id": b["id"]}).json()["ok"])
        self.assertEqual("小满", self.c.get("/api/assistants/who?sid=t9").json()["assistant"]["name"])
        th = self.c.get("/api/nest/threads?with_assistant=1").json()["items"]
        self.assertTrue(all("assistant" in x for x in th))
        # 改名字
        self.c.post("/api/assistants/save", json={"id": a["id"], "name": "阿澈澈"})
        self.assertEqual("阿澈澈", self.c.get("/api/assistants").json()["items"][0]["name"])
        self.assertEqual(404, self.c.post("/api/assistants/save", json={"id": "没有"}).status_code)
        self.assertTrue(self.c.post("/api/assistants/del", json={"id": b["id"]}).json()["ok"])
        self.assertEqual(404, self.c.post("/api/assistants/del", json={"id": "没有"}).status_code)

    def test_the_prompt_and_the_sign_reach_the_model(self):
        self.c.post("/api/assistants/save", json={"name": "阿澈", "prompt": "你是阿澈，说话短。",
                                                  "sign": "今天也在"})
        t = self._ask("main")
        self.assertIn("你是阿澈", t.system)
        self.assertIn("今天也在", t.system)

    def test_another_window_does_not_inherit_his_prompt(self):
        self.c.post("/api/assistants/save", json={"name": "阿澈", "prompt": "你是阿澈"})
        b = self.c.post("/api/assistants/save", json={"name": "小满"}).json()["item"]
        self.c.post("/api/assistants/window", json={"sid": "t9", "id": b["id"]})
        self.assertNotIn("你是阿澈", self._ask("t9").system)

    def test_mcp_is_per_assistant(self):
        """★ 用户点名的那条：为一位助手开 MCP，别的助手不同步。"""
        from core import hands, mcp_client
        fake_mcp = [{"type": "function", "function": {"name": "games__play", "parameters": {}}}]
        orig_open = mcp_client.openai_tools
        orig_exec = hands.execute

        def fake_openai_tools(only=None):
            if only is None:
                return list(fake_mcp)
            return [t for t in fake_mcp
                    if t["function"]["name"].split("__", 1)[0] in {str(x) for x in only}]

        mcp_client.openai_tools = fake_openai_tools
        self.addCleanup(lambda: (setattr(mcp_client, "openai_tools", orig_open),
                                 setattr(hands, "execute", orig_exec)))
        # pick_engine 里那一步走的是 hands.all_tools() —— 让 Cap 也带上手
        from core.engines.base import Engine
        from core.protocol import sse, SAY, DONE
        cap = {}

        class Cap(Engine):
            name, label, ready, stub = "cap", "捕获", True, False
            tools = []
            exec_tool = None

            async def stream(self, turn):
                cap["tools"] = [t["function"]["name"] for t in (self.tools or [])]
                yield sse(SAY, text="好")
                yield sse(DONE, session_id=turn.session_id)

        def pick():
            e = Cap()
            e.tools = hands.all_tools()          # 跟真 pick_engine 一样把手挂上
            return e
        old = self.sv.pick_engine
        self.sv.pick_engine = pick
        self.addCleanup(lambda: setattr(self.sv, "pick_engine", old))

        self.c.post("/api/assistants/save", json={"name": "阿澈"})          # 第一位＝不限
        b = self.c.post("/api/assistants/save", json={"name": "小满", "mcp": []}).json()["item"]
        self.c.post("/api/assistants/window", json={"sid": "t9", "id": b["id"]})
        list(self.c.post("/chat", json={"message": "在吗"}).iter_lines())
        self.assertIn("games__play", cap["tools"], "第一位不限 —— 老行为")
        list(self.c.post("/chat", json={"message": "在吗", "session_id": "t9"}).iter_lines())
        self.assertNotIn("games__play", cap["tools"], "小满没勾这个 MCP —— 一个都不给")
        self.assertIn("write_memory", cap["tools"], "内置的手不受影响")
        # 勾上之后就有了
        self.c.post("/api/assistants/save", json={"id": b["id"], "mcp": ["games"]})
        list(self.c.post("/chat", json={"message": "在吗", "session_id": "t9"}).iter_lines())
        self.assertIn("games__play", cap["tools"])


class TestTheProactiveAndOfflinePathsAreFilteredToo(unittest.TestCase):
    """主动消息 / 离线自由时段也会用手 —— 它们必须走**同一张许可表**。

    ★ 这一段是为了钉住一个真漏洞：那两条路 `pick_engine()` 拿到的是全量工具，
      不筛的话界面里没开的 MCP，半夜自己就用上了（静默越权）。
      写这段的时候还撞到一次「少了一行 import」—— 外面裹着 try/except，
      只会在 journalctl 里留一句话，功能静默失效。所以这里测的是**行为**，不是代码长啥样。
    """

    def test_the_active_window_assistant_filters_what_proactive_may_use(self):
        from core.store.sqlite import SqliteStore as SS
        from core.engines.base import Engine
        import core.server as sv

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        old_store, old_pick = sv.store, sv.pick_engine
        sv.store = SS(Path(tmp.name) / "lh.db")
        self.addCleanup(lambda: (setattr(sv, "store", old_store),
                                 setattr(sv, "pick_engine", old_pick)))

        class E(Engine):
            name, label, ready, stub = "e", "e", True, False
            tools = [{"type": "function", "function": {"name": "games__x", "parameters": {}}}]

            async def stream(self, turn):
                if False:
                    yield ""

        sv.pick_engine = lambda: E()
        self.assertEqual(["games__x"], [t["function"]["name"] for t in sv._pick_engine_for_active().tools],
                         "没配过助手＝不限（老行为）")
        sv.store.set_setting("assistants", {"version": 1, "items": [
            {"id": "a1", "name": "甲", "mcp": []}]})
        self.assertEqual([], [t["function"]["name"] for t in sv._pick_engine_for_active().tools],
                         "这位助手一个 MCP 都没给 —— 主动/离线也不许用")
        self.assertTrue(callable(sv._pick_engine_for_active().exec_tool))


class TestLettersBelongToAnAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        from optional.homelife import routes as hl
        cls.hl = hl
        cls.app = FastAPI()
        cls.app.include_router(hl.router)
        cls.c = TestClient(cls.app)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SqliteStore(Path(self.tmp.name) / "lh.db")

        async def _say(p):
            return ""
        self.hl.bind(self.store, _say)


class TestTheUiIsWired(unittest.TestCase):
    def _read(self, name):
        return (ROOT / "core" / "web" / name).read_text(encoding="utf-8")

    def test_the_settings_page_loads_the_assistant_module(self):
        self.assertIn('src="/nest-assistant.js', self._read("nest.html"))
        js = self._read("nest-assistant.js")
        for word in ("助手管理", "/api/assistants", "系统提示词", "头像", "那行小字"):
            self.assertIn(word, js, word)

    def test_the_settings_pane_asks_for_the_section(self):
        self.assertIn("nestAssistantSection", self._read("nest-setting.js"))

    def test_the_chat_bar_shows_who_is_speaking(self):
        js = self._read("nest-assistant.js")
        self.assertIn("/api/assistants/who", js)
        self.assertIn("nestAsstBadge", js)


if __name__ == "__main__":
    unittest.main()
