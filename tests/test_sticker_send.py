"""表情包：发在主聊天界面里，助手也能发 —— 但**只准点缀，放在末尾**。

用户定的那几条规矩，这里一条一条钉住（含糊一条，模型就会拿一张图替代该说的话）：
  · 只用来点缀，放在话的末尾
  · 不许拿它替代该说的话（该说的先说全）
  · 一轮最多一张
  · 不是每句都带，挑不到合适的就不发
  · 挑哪张看名字和标签

★ 还有两条是「说话算话」那类：
  · 表里没有的名字**不发**（宁可这次没发，也不能在气泡里放个坏图标）
  · 没有地方放这张图的那两条路（主动消息 / 离线自由时段），**这只手根本不摆出去** ——
    答应了却什么都不出现，比不发还糟。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import hands                                                # noqa: E402
from core.store.sqlite import SqliteStore                             # noqa: E402


def _store_with_stickers(tmp: Path):
    from optional.homelife import routes as hl
    store = SqliteStore(tmp / "lh.db")

    async def _say(p):
        return ""
    hl.bind(store, _say)
    for nm, tg in (("猫猫歪头", "撒娇,猫,可爱"), ("好耶", "高兴,庆祝"),
                   ("无语", "无奈,吐槽")):
        store.db.execute("INSERT INTO stickers(name,tags,url,ts) VALUES(?,?,?,?)",
                         (nm, tg, "/uploads/" + nm + ".png", 1.0))
    store.db.commit()
    return store


class TestTheHandPicksByNameAndTag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = _store_with_stickers(Path(self.tmp.name))
        self.old = hands._store
        hands._store = self.store
        self.addCleanup(lambda: setattr(hands, "_store", self.old))

    def run_hand(self, args):
        import asyncio
        return asyncio.run(hands.execute("send_sticker", args))

    def test_by_exact_name(self):
        r = self.run_hand({"name": "猫猫歪头"})
        self.assertTrue(r["ok"], r)
        self.assertEqual("猫猫歪头", r["sticker"]["name"])
        self.assertEqual("/uploads/猫猫歪头.png", r["sticker"]["url"])

    def test_by_partial_name_and_by_tag(self):
        self.assertTrue(self.run_hand({"name": "猫猫"})["ok"], "名字记不全也该找得到")
        self.assertTrue(self.run_hand({"name": "庆祝"})["ok"], "报的是标签也该找得到")

    def test_a_name_that_is_not_in_the_table_is_refused_with_the_list(self):
        r = self.run_hand({"name": "不存在的表情"})
        self.assertFalse(r["ok"])
        self.assertIn("猫猫歪头", r["err"], "得把能发的告诉它，别让它瞎猜")

    def test_nothing_said_is_refused(self):
        self.assertFalse(self.run_hand({"name": "  "})["ok"])

    def test_an_empty_table_says_so(self):
        self.store.db.execute("DELETE FROM stickers")
        self.store.db.commit()
        r = self.run_hand({"name": "猫猫"})
        self.assertFalse(r["ok"])
        self.assertIn("空", r["err"])


class TestTheGuardKeepsItToOnePerTurn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = _store_with_stickers(Path(self.tmp.name))
        self.old = hands._store
        hands._store = self.store
        self.addCleanup(lambda: setattr(hands, "_store", self.old))

    def test_one_sticker_per_turn(self):
        import asyncio
        notes = {}
        guard = hands.exec_guard(None, None, notes)
        first = asyncio.run(guard("send_sticker", {"name": "猫猫歪头"}))
        self.assertTrue(first["ok"])
        self.assertEqual("猫猫歪头", notes["sticker"]["name"])
        second = asyncio.run(guard("send_sticker", {"name": "好耶"}))
        self.assertFalse(second["ok"], "一轮最多一张 —— 第二张不发")
        self.assertIn("一张", second["err"])
        self.assertEqual("猫猫歪头", notes["sticker"]["name"], "先发的那张不变")

    def test_without_a_collector_it_refuses_instead_of_pretending(self):
        """主动消息 / 离线那两条路：没有地方放这张图 —— 那就别答应。"""
        import asyncio
        guard = hands.exec_guard(None, None)
        r = asyncio.run(guard("send_sticker", {"name": "猫猫歪头"}))
        self.assertFalse(r["ok"])
        self.assertIn("发不了", r["err"])

    def test_that_path_does_not_even_offer_the_hand(self):
        tools = hands.TOOLS + [{"type": "function", "function": {"name": "games__x", "parameters": {}}}]
        left = {t["function"]["name"] for t in hands.without(tools, ["send_sticker"])}
        self.assertNotIn("send_sticker", left)
        self.assertIn("write_letter", left, "只摘这一只，别的手不动")


class TestThePromptSaysTheRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = _store_with_stickers(Path(self.tmp.name))

    def block(self):
        from core.memory.recall import sticker_block
        return sticker_block(self.store)

    def test_the_rules_are_all_there(self):
        b = self.block()
        for bit in ("末尾", "替代", "最多一张", "不是每句", "标签"):
            self.assertIn(bit, b, "规矩少一条，模型就会自己发明一条：" + bit)
        self.assertIn("挑不到合适的就不发", b)

    def test_the_table_rides_along_with_names_and_tags(self):
        b = self.block()
        self.assertIn("猫猫歪头", b)
        self.assertIn("撒娇,猫,可爱", b)
        self.assertIn("send_sticker", b, "得告诉它用什么姿势发")

    def test_no_stickers_no_block(self):
        self.store.db.execute("DELETE FROM stickers")
        self.store.db.commit()
        self.assertEqual("", self.block(), "表空着的时候别拿一段空规矩去占上下文")


class TestItLandsOnTheReply(unittest.TestCase):
    """走真 /chat：他调 send_sticker → 这张图得**真落在那条回复上**。"""

    @classmethod
    def setUpClass(cls):
        from starlette.testclient import TestClient
        import core.server as sv
        cls.sv = sv
        cls.c = TestClient(sv.app, client=("127.0.0.1", 46000))

    def setUp(self):
        from core import views as V
        from optional.homelife import routes as hl
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        store = _store_with_stickers(Path(self.tmp.name))
        self.old_store, self.old_views = self.sv.store, V._store
        self.old_hands = hands._store
        self.sv.store = store
        V.bind(store)
        hands.bind(store)            # ★ 那只手查的是 hands._store —— 不换它就会查真库

        async def _say(p):
            return ""
        hl.bind(store, _say)
        self.addCleanup(self._restore)

    def _restore(self):
        from core import views as V
        self.sv.store, V._store = self.old_store, self.old_views
        hands.bind(self.old_hands)

    def _chat_with_a_hand(self):
        """一个「真的会调那只手」的假引擎 —— 别用假引擎替掉 exec_tool 那一段，
        这里要测的正是「工具 → 落库」这条链。"""
        from core.engines.base import Engine
        from core.protocol import sse, SAY, DONE
        cap = {}
        events = []

        class Cap(Engine):
            name, label, ready, stub = "cap", "捕获", True, False
            tools = []              # 非 None —— /chat 才会挂上 exec_guard（真引擎也是）

            async def stream(self, turn):
                yield sse("tool_live", name="send_sticker")
                res = await self.exec_tool("send_sticker", {"name": "猫猫歪头"})
                cap["res"] = res
                yield sse("tool", name="send_sticker", args='{"name":"猫猫歪头"}')
                yield sse("tool_done", name="send_sticker", ok=res.get("ok", False),
                          err=res.get("err", ""), sticker=res.get("sticker"))
                yield sse(SAY, text="好，我记着了。")
                yield sse(DONE, session_id=turn.session_id)

        old = self.sv.pick_engine

        def pick():
            e = Cap()
            e.tools = hands.all_tools()      # 跟真 pick_engine 一样把手挂上
            return e
        self.sv.pick_engine = pick
        self.addCleanup(lambda: setattr(self.sv, "pick_engine", old))
        body = {"message": "今天有点累"}
        for line in self.c.post("/chat", json=body).iter_lines():
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except Exception:
                    pass
        return cap, events

    def _last_assistant(self):
        r = self.sv.store.db.execute(
            "SELECT * FROM turns WHERE role='assistant' ORDER BY id DESC LIMIT 1").fetchone()
        files = json.loads(r["files"]) if r["files"] else []
        return dict(r), files

    def test_the_sticker_is_stored_on_that_reply(self):
        cap, events = self._chat_with_a_hand()
        self.assertTrue(cap["res"]["ok"], cap["res"])
        row, files = self._last_assistant()
        self.assertEqual("好，我记着了。", row["content"], "话照样说全 —— 表情包不许顶替它")
        self.assertEqual(1, len(files))
        self.assertEqual("/uploads/猫猫歪头.png", files[0]["url"])
        self.assertTrue(files[0]["sticker"], "得标出来这是表情包（它的位置在末尾）")
        self.assertEqual("img", files[0]["kind"])

    def test_the_event_carries_it_so_the_screen_shows_it_right_away(self):
        _, events = self._chat_with_a_hand()
        done = [e for e in events if e.get("type") == "tool_done" and e.get("name") == "send_sticker"]
        self.assertTrue(done, "没发 tool_done")
        self.assertTrue(done[0]["ok"])
        self.assertEqual("/uploads/猫猫歪头.png", done[0]["sticker"]["url"],
                         "不带这张图的话，人得刷新一次才看得见 —— 而他刚被告知「贴上了」")

    def test_the_reply_still_works_when_it_does_not_send_one(self):
        from core.engines.base import Engine
        from core.protocol import sse, SAY, DONE

        class Quiet(Engine):
            name, label, ready, stub = "q", "安静", True, False
            tools = []

            async def stream(self, turn):
                yield sse(SAY, text="嗯。")
                yield sse(DONE, session_id=turn.session_id)

        old = self.sv.pick_engine
        self.sv.pick_engine = lambda: Quiet()
        self.addCleanup(lambda: setattr(self.sv, "pick_engine", old))
        list(self.c.post("/chat", json={"message": "在吗"}).iter_lines())
        row, files = self._last_assistant()
        self.assertEqual([], files, "没发就是没发，别塞一张空的进去")
        self.assertEqual("嗯。", row["content"])


class TestTheUi(unittest.TestCase):
    def setUp(self):
        p = ROOT / "core" / "web"
        self.html = (p / "nest.html").read_text(encoding="utf-8")
        self.js = (p / "nest-sticker.js").read_text(encoding="utf-8")

    def test_the_module_is_loaded(self):
        self.assertIn('src="/nest-sticker.js', self.html)
        self.assertTrue((ROOT / "core" / "web" / "nest-sticker.js").exists())

    def test_the_picker_sits_in_the_chat_composer(self):
        self.assertIn('#composer .row', self.js)
        self.assertIn("nestAttach", self.js, "发的时候走**同一条**附件路，不另起一套")
        self.assertIn("api/stickers", self.js)

    def test_his_sticker_goes_to_the_end_of_his_reply(self):
        # 人发的附件在正文前（那是他要说的），他发的表情包在正文后（点缀）
        self.assertIn("const mine=it.role===\"user\"", self.html)
        self.assertIn("stickerEl", self.html)
        after = self.html.split("splitSay(it.content).forEach")[1][:400]
        self.assertIn("stk.forEach(f=>w.append(stickerEl(f)))", after,
                      "表情包得画在气泡**后面**")

    def test_the_live_turn_shows_it_without_a_refresh(self):
        """★ 他发的表情包要**当场**贴出来，不能等刷新 —— 而他刚被告知「贴上了」。

        ★★ 这条原来只查「ev.sticker 这个词在不在文件里」—— 于是漏掉了一个真 bug：
        基础版 handle（function handle(ev,L)）里写着这段，可「第二批补丁」那句
        `window.handle=function(ev,L){…}` 把整个 handler **换掉了**，
        基础版成了死代码：词还在，功能没了，表情包要刷新一次才看得见。
        所以现在查的是「**生效的那个** handler 里有没有这一段」。
        """
        self.assertIn("ev.sticker", self.html)
        self.assertIn("L.sticker", self.html)
        # 生效的是后面那个 window.handle（补丁把它整个换掉了）
        live = self.html[self.html.index("window.handle=function(ev,L){"):]
        self.assertIn("ev.sticker", live,
                      "表情包那一段得在**生效的** handler 里，不能只在被覆盖掉的基础版里")
        self.assertIn("L.sticker", live)
        self.assertIn("stickerEl(", live)

    def test_a_sticker_that_will_not_load_says_so(self):
        """★ 真机上撞的：他说发了，屏幕上什么都没有 —— 因为图取不到时那块被**悄悄摘掉**了。
        悄悄失败比失败更糟：人只能说「没法显示」，我们这边看日志一切正常。"""
        import re as _re
        seg = self.html.split("function stickerEl")[1].split("function attachEl")[0]
        seg = _re.sub(r"/\*[\s\S]*?\*/", "", seg)      # 注释里提到过那句，不算
        self.assertIn("sticker-bad", seg, "取不到要留个看得见的条")
        self.assertNotIn("box.remove()", seg, "不许悄悄摘掉")

    def test_the_library_points_at_the_chat_picker(self):
        """★ 界面里不许有 emoji 了 —— 那一句改成「图标 + 文字」，认的是意思不是字形。"""
        notes = (ROOT / "core" / "web" / "nest-notes.js").read_text(encoding="utf-8")
        self.assertIn("要发的时候在聊天输入框边上点", notes)
        self.assertIn('nestIcon("sticker")', notes, "指的就是输入框边上那枚表情包键")


if __name__ == "__main__":
    unittest.main()
