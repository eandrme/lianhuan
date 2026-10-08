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
            name, label, ready, stub = "cap", "捕获", True, True

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
        self.assertIn("nestWinFlags.row", self._read("nest-threads.js"))

    def test_the_bar_switches_are_not_plain_buttons(self):
        """顶栏那两枚不能带 .ibtn：nest-threads 用 `#bar .ibtn` 认「＋」，
        混进去会让点开关变成开新对话。"""
        js = self._read("nest-window.js")
        self.assertIn('el("button","wf")', js)
        self.assertNotIn('"wf ibtn"', js)
        self.assertNotIn("'wf ibtn'", js)


if __name__ == "__main__":
    unittest.main()
