"""巢 · 记事剩下的页面 ＋ 每扇窗那两枚开关。

两块都是后加的，各钉几条，免得以后改着改着漂回去：

  · 「窗口」＝会话（turns.session_id）。每扇窗两枚开关默认都开；主动消息只会往
    「你最近待的那扇窗」说，关掉你最近这扇它就安静 —— 不许绕到别的窗口去打扰。
  · 书房小窗走 book_chat，永远不进这套开关（纯粹的读书助手）。
  · 记事七块：日记 · 碎碎念 · 心情 · 日历 · 梗库 · 表情包 · 健康，都得有增删改。
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.store.base import Turn                       # noqa: E402
from core.store.sqlite import SqliteStore              # noqa: E402
from core import windows                               # noqa: E402


class TestWindowFlags(unittest.TestCase):
    """core/windows.py：默认值、拨动、以及「哪扇窗算你现在这扇」。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = SqliteStore(Path(self.tmp.name) / "w.db")

    def test_defaults_are_both_on(self):
        f = windows.flags(self.s, "t1")
        self.assertTrue(f["push"], "没拨过的窗口默认允许主动消息")
        self.assertTrue(f["offline"], "没拨过的窗口默认允许离线时段")

    def test_turn_one_off_leaves_the_other_alone(self):
        f = windows.set_flags(self.s, "t1", push=False)
        self.assertFalse(f["push"])
        self.assertTrue(f["offline"], "拨一枚不该动另一枚")
        self.assertFalse(windows.allows(self.s, "t1", "push"))
        self.assertTrue(windows.allows(self.s, "t1", "offline"))
        # 别的窗口不受影响
        self.assertTrue(windows.allows(self.s, "t2", "push"))

    def test_active_window_is_where_you_actually_spoke_last(self):
        self.s.add_turn(Turn(role="user", content="在 t1 说的", session_id="t1"))
        self.s.add_turn(Turn(role="assistant", content="它答的", session_id="t1"))
        self.assertEqual("t1", windows.active_sid(self.s))
        self.s.add_turn(Turn(role="user", content="换窗口了", session_id="t2"))
        self.assertEqual("t2", windows.active_sid(self.s))

    def test_machine_prompts_do_not_count_as_you_sitting_there(self):
        """★ 翻空间 / 重新生成那类机器拼的指令 spoken=0 —— 那是后台自己动，
        不代表人这会儿待在那扇窗前，不能拿它改「你最近在哪」。"""
        self.s.add_turn(Turn(role="user", content="真人说的", session_id="t1"))
        self.s.add_turn(Turn(role="user", content="机器指令", session_id="t9",
                             spoken=0, hidden=1))
        self.assertEqual("t1", windows.active_sid(self.s))

    def test_empty_house_is_the_main_window(self):
        self.assertEqual("main", windows.active_sid(self.s))

    def test_the_window_you_are_looking_at_wins(self):
        """★ 真机上撞出来的：切到另一扇窗、还没开口就走了 —— 这时候「最后说话的地方」
        还停在上上扇窗。关掉手上这扇的开关，别的窗跟着失灵，反之亦然。
        界面报一声自己现在在哪（focus），那两枚开关才真的按这一扇算。"""
        self.s.add_turn(Turn(role="user", content="我在 t1 说的", session_id="t1"))
        self.assertEqual("t1", windows.active_sid(self.s))
        windows.set_focus(self.s, "t2")
        self.assertEqual("t2", windows.active_sid(self.s),
                         "人明明站在 t2，就该按 t2 的开关算")
        windows.set_focus(self.s, "")
        self.assertEqual("t1", windows.active_sid(self.s),
                         "focus 清掉就退回按最后说话的地方猜")

    def test_the_two_windows_do_not_drag_each_other_down(self):
        """一扇关掉，另一扇必须原样开着 —— 这是「两个窗口独立」那句话的字面意思。"""
        self.s.add_turn(Turn(role="user", content="主窗口说的", session_id="main"))
        self.s.add_turn(Turn(role="user", content="t2 说的", session_id="t2"))
        windows.set_flags(self.s, "main", push=False, offline=False)
        windows.set_focus(self.s, "t2")
        self.assertTrue(windows.allows_active(self.s, "push"),
                        "主窗口关了，t2 的主动消息还得是开的")
        self.assertTrue(windows.allows_active(self.s, "offline"))
        windows.set_focus(self.s, "main")
        self.assertFalse(windows.allows_active(self.s, "push"))
        self.assertFalse(windows.allows_active(self.s, "offline"))

    def test_the_switches_travel_with_the_move(self):
        """搬家（导出）必须带上这两枚开关 —— 换台机器还得是这个脾气。"""
        windows.set_flags(self.s, "t1", push=False)
        dump = self.s.export_all()
        self.assertIn("nest_window_flags", dump["settings"])
        self.assertEqual(False, dump["settings"]["nest_window_flags"]["t1"]["push"])


class TestNestWindowApi(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from core import views
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = SqliteStore(Path(self.tmp.name) / "api.db")
        views.bind(self.s)
        app = FastAPI()
        app.include_router(views.router)
        self.c = TestClient(app)

    def test_get_reports_defaults_and_where_you_are(self):
        self.s.add_turn(Turn(role="user", content="你好", session_id="t7"))
        j = self.c.get("/api/nest/window?sid=t7").json()
        self.assertTrue(j["ok"])
        self.assertTrue(j["push"] and j["offline"])
        self.assertEqual("t7", j["active"])

    def test_post_round_trips(self):
        self.assertEqual(200, self.c.post("/api/nest/window",
                         json={"sid": "t3", "offline": False}).status_code)
        j = self.c.get("/api/nest/window?sid=t3").json()
        self.assertFalse(j["offline"])
        self.assertTrue(j["push"], "没传的那一枚不该被顺手关掉")

    def test_post_without_any_switch_is_rejected(self):
        r = self.c.post("/api/nest/window", json={"sid": "t3"})
        self.assertEqual(400, r.status_code)

    def test_all_windows_endpoint_lists_what_was_touched(self):
        self.c.post("/api/nest/window", json={"sid": "t4", "push": False})
        items = self.c.get("/api/nest/windows").json()["items"]
        self.assertIn("t4", items)
        self.assertFalse(items["t4"]["push"])

    def test_focus_endpoint_decides_which_window_counts(self):
        self.s.add_turn(Turn(role="user", content="主窗口说的", session_id="main"))
        self.assertEqual(200, self.c.post("/api/nest/focus", json={"sid": "t9"}).status_code)
        self.assertEqual("t9", self.c.get("/api/nest/window?sid=t9").json()["active"])
        self.assertEqual("t9", self.c.get("/api/offline").json()["active_window"])
        self.assertEqual(400, self.c.post("/api/nest/focus", json={}).status_code)


class TestProactiveAndOfflineRespectTheSwitch(unittest.TestCase):
    """关掉某扇窗的开关，它就该真的安静 —— 不是界面翻过去了、后台照说。"""

    def setUp(self):
        from core import proactive
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = SqliteStore(Path(self.tmp.name) / "p.db")
        self.old_store, self.old_deps = proactive._store, dict(proactive._deps)

        def _restore():
            proactive._store = self.old_store
            proactive._deps.clear()
            proactive._deps.update(self.old_deps)
        self.addCleanup(_restore)
        self.pa = proactive

    def test_push_off_means_it_will_not_open_its_mouth(self):
        self.s.set_setting("whisper_freq", {"level": 100})   # 总闸开满
        self.s.add_turn(Turn(role="user", content="我在 t1", session_id="t1"))
        self.pa.bind(self.s, engine_turn=lambda **k: None, pick_engine=lambda: None,
                     add_turn=lambda *a, **k: None)
        self.assertTrue(self.pa.may_speak(), "默认开着、总闸也开，就该能说话")
        windows.set_flags(self.s, "t1", push=False)
        self.assertFalse(self.pa.may_speak(), "你最近这扇窗关了主动消息，就不许开口")

    def test_the_proactive_line_lands_in_your_window(self):
        """★ 关键：它说的话得落在「你最近待的那扇窗」里，不然那枚开关是假的。"""
        from core.engines.base import Engine
        from core.protocol import DONE, SAY, sse
        cap = {}

        class Cap(Engine):
            name, label, ready, stub = "cap", "捕获", True, False

            async def stream(self, turn):
                yield sse(SAY, text="（假装说了一句）")
                yield sse(DONE)

        self.s.add_turn(Turn(role="user", content="我在 t1", session_id="t1"))
        self.pa.bind(self.s, engine_turn=lambda **k: None, pick_engine=lambda: Cap(),
                     add_turn=lambda *a, **k: cap.update(k))
        asyncio.run(self.pa.speak_once())
        self.assertEqual("t1", cap.get("session_id"),
                         "主动消息该落在你最近待的那扇窗，不是永远的主窗口")

    def test_offline_window_switch_gates_the_free_time(self):
        from core import offline
        self.s.add_turn(Turn(role="user", content="我在 t1", session_id="t1"))
        self.pa.bind(self.s, engine_turn=lambda **k: None, pick_engine=lambda: None,
                     add_turn=lambda *a, **k: None)
        self.assertTrue(offline.window_ok())
        windows.set_flags(self.s, "t1", offline=False)
        self.assertFalse(offline.window_ok(), "这扇窗关了离线模式，这一拍就不该起")

    def test_a_stub_engine_never_opens_its_mouth(self):
        """★ 真机上撞到的：引擎还是回声（出厂默认），滑钮一拧它就开始主动说话 ——
        发出去的是「这是回声引擎，你刚说的是：（主动说一句）……去设置里挑一个引擎」，
        而且被当成它自己想说的话存进对话、还推了一下手机。那是给写代码的人看的诊断。"""
        from core import offline
        from core.engines.echo import EchoEngine
        self.s.set_setting("whisper_freq", {"level": 100})
        self.pa.bind(self.s, engine_turn=lambda **k: None,
                     pick_engine=lambda: EchoEngine(), add_turn=lambda *a, **k: None)
        self.assertFalse(self.pa.may_speak())
        self.assertFalse(offline.engine_ok())
        self.assertFalse(self.pa.engine_can_speak())

    def test_a_due_reminder_is_not_burned_while_the_engine_is_a_stub(self):
        import time as _t
        from core.engines.echo import EchoEngine
        self.pa.bind(self.s, engine_turn=lambda **k: None,
                     pick_engine=lambda: EchoEngine(), add_turn=lambda *a, **k: None)
        self.pa.set_reminder("问问他推送稳不稳", _t.time() - 60)
        self.assertEqual(0, asyncio.run(self.pa.fire_due_reminders()))
        row = self.s.db.execute("SELECT fired_ts FROM reminders").fetchone()
        self.assertIsNone(row["fired_ts"], "没响就绝不能盖 fired_ts —— 盖了这条提醒就永远丢了")

    def test_the_proactive_line_lands_in_the_window_you_are_looking_at(self):
        """焦点窗优先：站在 t2（哪怕还没在 t2 说过话），它就往 t2 说。"""
        from core.engines.base import Engine
        from core.protocol import DONE, SAY, sse
        cap = {}

        class Cap(Engine):
            name, label, ready, stub = "cap", "捕获", True, False

            async def stream(self, turn):
                yield sse(SAY, text="（假装说了一句）")
                yield sse(DONE)

        self.s.add_turn(Turn(role="user", content="这句在 main", session_id="main"))
        windows.set_focus(self.s, "t2")
        self.pa.bind(self.s, engine_turn=lambda **k: None, pick_engine=lambda: Cap(),
                     add_turn=lambda *a, **k: cap.update(k))
        asyncio.run(self.pa.speak_once())
        self.assertEqual("t2", cap.get("session_id"))


class TestNotesRemainingPages(unittest.TestCase):
    """心情 / 日历 / 梗库 / 表情包 / 健康 —— 都要能读、能写、能收拾。"""

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from optional.homelife import routes as homelife_routes
        from optional.homeplus.routes import bind as hp_bind, router as hp_router

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # ★ 表情包那条接口要核「图真的在盘上」—— 它按 LIANHUAN_DB 找 uploads。
        #   钉到临时目录，别去碰仓库里那份真 data/。
        old_db = os.environ.get("LIANHUAN_DB")

        def _restore_env():
            if old_db is None:
                os.environ.pop("LIANHUAN_DB", None)
            else:
                os.environ["LIANHUAN_DB"] = old_db
        self.addCleanup(_restore_env)
        os.environ["LIANHUAN_DB"] = str(Path(self.tmp.name) / "h.db")
        self.s = SqliteStore(Path(self.tmp.name) / "h.db")

        async def _say(prompt):
            return "（测试不真说话）"

        homelife_routes.bind(self.s, _say)
        app = FastAPI()
        app.include_router(homelife_routes.router)
        hp_bind(self.s)
        app.include_router(hp_router)
        self.c = TestClient(app)

    # ── 心情 ──
    def test_mood_bump_and_undo_one_entry(self):
        self.assertEqual(12, len(self.c.get("/api/mood").json()["mood"]))
        r = self.c.post("/api/mood/bump", json={"dimension": "想念", "delta": 6,
                                                "reason": "测试"})
        self.assertTrue(r.json()["ok"])
        log = self.c.get("/api/mood").json()["log"]
        self.assertEqual("想念", log[0]["dimension"])
        self.assertIn("id", log[0], "带 id 才删得掉记错的那一笔")
        self.assertTrue(self.c.post("/api/mood/log/%d/del" % log[0]["id"]).json()["ok"])
        self.assertEqual([], self.c.get("/api/mood").json()["log"])

    def test_mood_bump_refuses_a_dimension_that_does_not_exist(self):
        r = self.c.post("/api/mood/bump", json={"dimension": "发疯", "delta": 6})
        self.assertEqual(400, r.status_code)

    # ── 日历 ──
    def test_calendar_add_toggle_and_delete(self):
        self.assertTrue(self.c.post("/api/calendar/add", json={
            "title": "体检", "date": "2026-03-01", "time": "09:30",
            "kind": "待办"}).json()["ok"])
        it = self.c.get("/api/calendar").json()["items"][0]
        self.assertEqual("体检", it["title"])
        self.assertTrue(self.c.post("/api/calendar/toggle", json={"id": it["id"]}).json()["ok"])
        self.assertTrue(self.c.get("/api/calendar").json()["items"][0]["done"])
        self.assertTrue(self.c.post("/api/calendar/del", json={"id": it["id"]}).json()["ok"])
        self.assertEqual([], self.c.get("/api/calendar").json()["items"])

    def test_anniversary_is_a_negative_id_and_deletes_too(self):
        self.c.post("/api/calendar/add", json={"title": "在一起", "date": "2020-05-20",
                                               "kind": "纪念日"})
        it = self.c.get("/api/calendar").json()["items"][0]
        self.assertEqual("纪念日", it["kind"])
        self.assertLess(it["id"], 0, "纪念日那条是负数 id（anniversaries 表）")
        self.assertTrue(self.c.post("/api/calendar/del", json={"id": it["id"]}).json()["ok"])
        self.assertEqual([], self.c.get("/api/calendar").json()["items"])

    # ── 梗库 ──
    def test_meme_add_edit_by_id_and_delete(self):
        self.c.post("/api/memes", json={"word": "纯棉", "meaning": "又软又好捏"})
        m = self.c.get("/api/memes").json()["items"][0]
        self.assertTrue(self.c.post("/api/memes/%d/edit" % m["id"], json={
            "word": "纯棉棉", "meaning": "更软了"}).json()["ok"])
        m2 = self.c.get("/api/memes").json()["items"][0]
        self.assertEqual("纯棉棉", m2["word"], "梗本身写错了字也得改得动")
        self.assertTrue(self.c.post("/api/memes/%d/del" % m2["id"]).json()["ok"])
        self.assertEqual([], self.c.get("/api/memes").json()["items"])

    def test_meme_rename_refuses_a_duplicate(self):
        self.c.post("/api/memes", json={"word": "甲", "meaning": "一"})
        self.c.post("/api/memes", json={"word": "乙", "meaning": "二"})
        items = self.c.get("/api/memes").json()["items"]
        b = [x for x in items if x["word"] == "乙"][0]
        r = self.c.post("/api/memes/%d/edit" % b["id"], json={"word": "甲"})
        self.assertEqual(409, r.status_code)

    # ── 表情包 ──
    def test_sticker_only_accepts_local_uploads(self):
        r = self.c.post("/api/stickers", json={"url": "https://example.com/a.png"})
        self.assertEqual(400, r.status_code, "不收外链，也不信前端随口编的路径")
        self.assertEqual(400, self.c.post("/api/stickers",
                         json={"url": "/etc/passwd"}).status_code)
        self.assertEqual(400, self.c.post("/api/stickers",
                         json={"url": "/uploads/没传过.png"}).status_code,
                         "盘上没有这张图就别存 —— 存了卡上就是个破图标")

    def _put_upload(self, name):
        d = Path(self.tmp.name) / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(b"\x89PNG\r\n\x1a\n")
        return "/uploads/" + name

    def test_sticker_add_edit_delete(self):
        self.c.post("/api/stickers", json={"url": self._put_upload("abc.png"),
                                           "name": "点头", "tags": "开心"})
        s = self.c.get("/api/stickers").json()["items"][0]
        self.assertEqual("点头", s["name"])
        self.assertTrue(self.c.post("/api/stickers/%d/edit" % s["id"],
                                    json={"name": "使劲点头"}).json()["ok"])
        self.assertEqual("使劲点头",
                         self.c.get("/api/stickers").json()["items"][0]["name"])
        self.assertTrue(self.c.post("/api/stickers/%d/del" % s["id"]).json()["ok"])
        self.assertEqual([], self.c.get("/api/stickers").json()["items"])

    # ── 健康 ──
    def test_health_is_one_row_per_day_and_merges_partial_updates(self):
        self.assertTrue(self.c.post("/api/health", json={"day": "2026-02-02",
                                                         "steps": 8000,
                                                         "note": "走到公园"}).json()["ok"])
        # 晚上回来补心率：白天那 8000 步不许被抹掉
        self.c.post("/api/health", json={"day": "2026-02-02", "resting_hr": 58})
        items = self.c.get("/api/health_recent?days=30").json()["items"]
        self.assertEqual(1, len(items), "一天一条，不能攒出两条打架的账")
        p = items[0]["payload"]
        self.assertEqual(8000, p["steps"])
        self.assertEqual(58.0, p["resting_hr"])
        self.assertEqual("走到公园", p["note"])

    def test_health_rejects_an_empty_day_and_a_bad_date(self):
        self.assertEqual(400, self.c.post("/api/health", json={"day": "2026-02-02"}).status_code)
        self.assertEqual(400, self.c.post("/api/health",
                         json={"day": "2/2", "steps": 100}).status_code)

    def test_health_delete(self):
        self.c.post("/api/health", json={"steps": 100})
        it = self.c.get("/api/health_recent").json()["items"][0]
        self.assertTrue(self.c.post("/api/health/%d/del" % it["id"]).json()["ok"])
        self.assertEqual([], self.c.get("/api/health_recent").json()["items"])

    def test_health_shape_matches_the_old_page(self):
        """原项目那页读的是 {t, payload:{steps,resting_hr,hrv_ms,menstrual}}。"""
        self.c.post("/api/health", json={"steps": 1})
        it = self.c.get("/api/health_recent").json()["items"][0]
        self.assertIn("t", it)
        for k in ("steps", "resting_hr", "hrv_ms", "menstrual"):
            self.assertIn(k, it["payload"])


class TestNestFrontendWiring(unittest.TestCase):
    """前端那半边：页面确实接上了，书房小窗确实没被沾上。"""

    def _read(self, name):
        return (ROOT / "core" / "web" / name).read_text(encoding="utf-8")

    def test_the_page_loads_the_switch_module(self):
        self.assertIn('src="/nest-window.js', self._read("nest.html"))

    def test_all_seven_notes_sections_are_real(self):
        js = self._read("nest-notes.js")
        for fn in ("secDiary", "secNotes", "secMood", "secCal",
                   "secMemes", "secSticker", "secHealth"):
            self.assertIn("function " + fn, js, fn + " 还没写")
        self.assertNotIn("下一批接上", js, "记事里不该再留「下一批」的占位")

    def test_the_book_window_has_no_switches(self):
        """★ 书房小窗是纯粹的读书助手 —— 不许沾主动消息和离线模式。"""
        js = self._read("nest-bookchat.js")
        self.assertNotIn("nestWinFlags", js)
        self.assertNotIn("winFlags", js)

    def test_the_thread_list_shows_both_switches(self):
        """每一行右边那两枚开关（主动消息 / 离线模式）。

        ★ 这个列表原来在 nest-threads.js 里，后来统一到了 nest-tabs.js 的
          threadsInto()（抽屉 / 主界面那颗 HOME /「巢」那一格走的都是它）。
          意图不变，只是换了地方 —— 所以这条也跟过去。"""
        self.assertIn("nestWinFlags.row", self._read("nest-tabs.js"))

    def test_the_bar_switches_are_not_plain_buttons(self):
        """顶栏那两枚不能带 .ibtn —— 那个类是顶栏动作按钮的记号，
        开关混进去会被当成一个「动作」，点一下就不是拨开关了。"""
        js = self._read("nest-window.js")
        self.assertIn('el("button","wf")', js)
        self.assertNotIn('"wf ibtn"', js)
        self.assertNotIn("'wf ibtn'", js)

    def test_reading_a_window_cannot_borrow_the_last_ones_state(self):
        """★ 真机上撞到的：「关掉主对话的开关，另一个对话也跟着关」。

        病根：切窗口之后那一问失败了（服务端是旧版本，没有这个接口），
        代码把**上一扇窗**的开关状态留着照画 —— 两扇窗看着就一样了。
        读不到必须是「未知」（画 ❓），绝不能用别的窗口的数字冒充。"""
        js = self._read("nest-window.js")
        seg = js[js.index("async function load"):js.index("async function set")]
        self.assertIn("known=false", seg)
        self.assertIn("cur={push:true,offline:true}", seg, "读不到就退回默认值，别留着旧的")
        self.assertIn('data-on="?"', js, "未知状态要画得出来")

    def test_a_bad_status_code_is_a_failure_not_a_success(self):
        """老服务端回 404 {"error":"没有这个东西"} —— 没有 ok 字段。
        只看 body 就会当成「存上了」，界面翻过去、库里一个字没有。"""
        for f in ("nest-window.js", "nest-notes.js"):
            self.assertIn("if(!r.ok||!d||d.ok===false)", self._read(f), f)

    def test_the_page_tells_the_backend_which_window_is_open(self):
        js = self._read("nest-window.js")
        self.assertIn("/api/nest/focus", js)
        self.assertIn("reportFocus", js)

    def test_it_says_which_kind_of_failure_it_is(self):
        """★ 真机上撞到的：手机上的提示把「连不上」和「服务端是旧版本」混成一句话，
        人会照着错的方向折腾（明明要重启服务端，却去查网络；或者反过来白重启）。"""
        js = self._read("nest-window.js")
        self.assertIn("whyKind", js)
        self.assertIn("服务端是旧版本", js)
        self.assertIn("连不上服务端", js)
        self.assertIn("throw new Error(\"连不上服务器\")", js, "网络层的失败要单独认出来")

    def test_the_page_loads_the_settings_module(self):
        self.assertIn('src="/nest-setting.js', self._read("nest.html"))
        js = self._read("nest-setting.js")
        for sec in ("secEngine", "secWhisper", "secOffline", "secPush"):
            self.assertIn("function " + sec, js)

    def test_the_frequency_words_follow_the_backend_not_Math_round(self):
        """★ 50 的时候 Python 的 round 取偶 → 4 句，JS 的 Math.round → 5 句。

        老界面（index.html）用的是 Math.round —— 在这一个点上说的比真的多一句
        （那条测试只钉了 `Math.round(lv / 100 * 9)` 这个字符串在不在，没比同一个数）。
        新设置页不许照着抄，得跟 `proactive.daily_max` 一模一样。
        """
        from core import proactive as pa
        self.assertEqual(4, pa.daily_max(50), "后端在 50 这个点上是 4（取偶）")
        js = self._read("nest-setting.js")
        self.assertNotIn("Math.round(lv / 100 * 9)", js)
        self.assertIn("return (f%2===0)?f:f+1;", js, "补上「.5 取偶」，别用 Math.round")


class TestNestAssetsCannotGoStale(unittest.TestCase):
    """/nest 的脚本 URL 必须**跟着内容走**。

    ★ 真机上撞的：「开关还是两个窗口同步」—— 其实是手机跑的还是几小时前的
      `nest-window.js`。nest.html 里每一行都写死 `?v=1`，而 `/sw.js` 对静态资源是
      **缓存优先**，浏览器内存缓存也认这同一个 URL。URL 不带内容指纹，改了等于没改，
      跟后端一句关系都没有。`/` 早就在打指纹，`/nest` 当时漏了。
    """

    @classmethod
    def setUpClass(cls):
        import os
        import tempfile
        from starlette.testclient import TestClient
        cls.tmp = tempfile.TemporaryDirectory()
        cls.old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = os.path.join(cls.tmp.name, "lianhuan.db")
        import core.server as sv
        cls.c = TestClient(sv.app)

    @classmethod
    def tearDownClass(cls):
        import os
        if cls.old is None:
            os.environ.pop("LIANHUAN_DB", None)
        else:
            os.environ["LIANHUAN_DB"] = cls.old
        cls.tmp.cleanup()

    def test_nest_stamps_every_script(self):
        import re
        html = self.c.get("/nest").text
        for f in ("nest-window.js", "nest-setting.js", "nest-notes.js", "nest-tabs.js"):
            self.assertRegex(html, re.escape(f) + r"\?v=[0-9a-f]{8}",
                             f + " 没打上内容指纹")
        self.assertNotIn('.js?v=1"', html, "写死的 ?v=1 会一直被缓存挡住")

    def test_index_still_stamps_too(self):
        import re
        html = self.c.get("/").text
        self.assertRegex(html, r"/mini-player\.js\?v=[0-9a-f]{8}")

    def test_push_status_says_whether_ntfy_is_in_the_loop(self):
        """配了 ntfy 会同时发一份；不说清楚，「0 个端」配着「手机明明收到了」没人解释得清。"""
        j = self.c.get("/api/push/status").json()
        self.assertIn("ntfy", j)
        self.assertIn("subs", j)


if __name__ == "__main__":
    unittest.main()
