"""空间 · 时间线 · 收藏 —— 原项目本来就有的三样，这一轮接进巢。

★ 三样都有一条共同的硬线：**界面上看得见的东西，必须是库里真有的**。
  空间贴了要落库、评论要进楼、删要真删；时间线的「几天前」由后端算；
  收藏按一下要真写进 turns.starred（只是把星星点亮＝过几天回来就没了）。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI                                            # noqa: E402
from starlette.testclient import TestClient                            # noqa: E402
from core.store.sqlite import SqliteStore                              # noqa: E402


class _HomeCase(unittest.TestCase):
    """空间 / 时间线都住在 homelife 那个包里。"""

    @classmethod
    def setUpClass(cls):
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


class TestSpace(_HomeCase):
    def test_post_a_moment_and_see_it(self):
        r = self.c.post("/api/moments/mine", json={"content": "今天把阳台的灯换了"})
        self.assertTrue(r.json()["ok"])
        items = self.c.get("/api/moments").json()["items"]
        self.assertEqual(["今天把阳台的灯换了"], [x["content"] for x in items])
        self.assertEqual("me", items[0]["author"][:2] or "me")

    def test_an_empty_post_is_refused(self):
        self.assertEqual(400, self.c.post("/api/moments/mine", json={"content": "   "}).status_code)

    def test_comment_lands_in_the_thread(self):
        mid = self.c.post("/api/moments/mine", json={"content": "贴一条"}).json()["id"]
        self.assertTrue(self.c.post(f"/api/moments/{mid}/comment",
                                    json={"content": "回一句"}).json()["ok"])
        one = self.c.get("/api/moments").json()["items"][0]
        self.assertEqual("回一句", one["comments"][0]["content"])
        self.assertEqual("me", one["comments"][0]["author"])

    def test_edit_a_moment(self):
        mid = self.c.post("/api/moments/mine", json={"content": "写错了"}).json()["id"]
        self.assertTrue(self.c.post(f"/api/moments/{mid}/edit",
                                    json={"content": "写对了"}).json()["ok"])
        self.assertEqual("写对了", self.c.get("/api/moments").json()["items"][0]["content"])
        self.assertEqual(400, self.c.post(f"/api/moments/{mid}/edit",
                                          json={"content": ""}).status_code)

    def test_delete_takes_the_comments_with_it(self):
        mid = self.c.post("/api/moments/mine", json={"content": "要删的"}).json()["id"]
        self.c.post(f"/api/moments/{mid}/comment", json={"content": "楼里的"})
        self.assertTrue(self.c.post(f"/api/moments/{mid}/del").json()["ok"])
        self.assertEqual([], self.c.get("/api/moments").json()["items"])
        self.assertEqual([], list(self.store.db.execute("SELECT * FROM moment_comments")),
                         "帖子删了，楼里的评论不能留成孤儿")

    def test_delete_one_comment_only(self):
        mid = self.c.post("/api/moments/mine", json={"content": "贴"}).json()["id"]
        self.c.post(f"/api/moments/{mid}/comment", json={"content": "第一条"})
        self.c.post(f"/api/moments/{mid}/comment", json={"content": "第二条"})
        cid = self.c.get("/api/moments").json()["items"][0]["comments"][0]["id"]
        self.assertTrue(self.c.post(f"/api/moments/comment/{cid}/del").json()["ok"])
        left = [c["content"] for c in self.c.get("/api/moments").json()["items"][0]["comments"]]
        self.assertEqual(["第二条"], left)


class TestTimeline(_HomeCase):
    def test_edit_and_delete_a_note(self):
        """★ 时间线是这个家怎么起来的流水，记错了得能划掉。"""
        self.c.post("/api/timeline", json={"kind": "装修", "content": "写错了"})
        tid = self.c.get("/api/timeline").json()["items"][0]["id"]
        self.assertTrue(self.c.post(f"/api/timeline/{tid}/edit",
                                    json={"content": "写对了", "kind": "note"}).json()["ok"])
        it = self.c.get("/api/timeline").json()["items"][0]
        self.assertEqual("写对了", it["content"])
        self.assertEqual("note", it["kind"], "换道也要能换")
        self.assertTrue(self.c.post(f"/api/timeline/{tid}/del").json()["ok"])
        self.assertEqual([], self.c.get("/api/timeline").json()["items"])

    def test_edit_needs_something_to_say(self):
        self.c.post("/api/timeline", json={"kind": "note", "content": "有内容"})
        tid = self.c.get("/api/timeline").json()["items"][0]["id"]
        self.assertEqual(400, self.c.post(f"/api/timeline/{tid}/edit",
                                         json={"content": "  "}).status_code)

    def test_write_a_note_and_read_it_back(self):
        self.assertTrue(self.c.post("/api/timeline",
                                    json={"kind": "装修", "content": "换了阳台的灯"}).json()["ok"])
        it = self.c.get("/api/timeline").json()["items"][0]
        self.assertEqual("装修", it["kind"])
        self.assertEqual("换了阳台的灯", it["content"])
        self.assertRegex(it["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(it["time"], r"^\d{2}:\d{2}$")
        self.assertEqual(0, it["days"], "今天写的，距今 0 天")

    def test_the_meta_rides_along(self):
        """出门走走那条会带天气 / 在哪 —— 原项目就靠这个把上下文带回来。"""
        self.c.post("/api/timeline", json={"kind": "travel", "content": "出门走走",
                                           "meta": {"weather": "晴", "where": "河边"}})
        it = self.c.get("/api/timeline").json()["items"][0]
        self.assertEqual("晴", it["meta"]["weather"])
        self.assertEqual("河边", it["meta"]["where"])

    def test_an_empty_note_is_refused(self):
        self.assertEqual(400, self.c.post("/api/timeline", json={"content": ""}).status_code)


class TestStarred(unittest.TestCase):
    """收藏走的是真库（turns.starred）—— 用真 app 测。"""

    @classmethod
    def setUpClass(cls):
        import core.server as sv
        cls.sv = sv
        cls.c = TestClient(sv.app, client=("127.0.0.1", 45000))

    def setUp(self):
        from core import views as V
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_store, self.old_views = self.sv.store, V._store
        self.sv.store = SqliteStore(Path(self.tmp.name) / "lh.db")
        V.bind(self.sv.store)
        self.addCleanup(self._restore)
        self.store.add_turn(self._turn("user", "今晚吃什么"))
        self.store.add_turn(self._turn("assistant", "吃面吧，别点外卖了"))

    def _restore(self):
        from core import views as V
        self.sv.store, V._store = self.old_store, self.old_views

    @property
    def store(self):
        return self.sv.store

    def _turn(self, role, content):
        from core.store.base import Turn as T
        import time
        return T(role=role, content=content, think="", tools="", channel="text",
                 call_id="", session_id="main", ts=time.time())

    def _ids(self):
        return [r["id"] for r in self.store.db.execute(
            "SELECT id FROM turns ORDER BY id")]

    def test_star_a_reply_and_find_it_with_the_question_that_caused_it(self):
        uid, aid = self._ids()
        r = self.c.post(f"/api/chat/{aid}/star").json()
        self.assertTrue(r["starred"])
        items = self.c.get("/api/chat/starred").json()["items"]
        self.assertEqual(1, len(items))
        self.assertEqual("吃面吧，别点外卖了", items[0]["content"])
        self.assertEqual("今晚吃什么", items[0]["ask"],
                         "★ 带上文：没有上文，几个月后翻出来不知道当时在聊什么")
        self.assertTrue(items[0]["starred"])

    def test_it_is_a_toggle(self):
        _, aid = self._ids()
        self.c.post(f"/api/chat/{aid}/star")
        self.assertFalse(self.c.post(f"/api/chat/{aid}/star").json()["starred"])
        self.assertEqual([], self.c.get("/api/chat/starred").json()["items"])

    def test_a_missing_turn_says_so(self):
        self.assertEqual(404, self.c.post("/api/chat/999999/star").status_code)

    def test_history_carries_the_star_so_it_still_shows_next_time(self):
        _, aid = self._ids()
        self.c.post(f"/api/chat/{aid}/star")
        items = self.c.get("/api/nest/thread?sid=main").json()["items"]
        self.assertTrue(any(x.get("starred") for x in items),
                        "翻历史时那颗星得还在 —— 用户按过的收藏不能下次进来就没了")


class TestRerenderingKeepsWhatWasThere(unittest.TestCase):
    """切窗口 / 换分档时会**重画**历史 —— 重画的那两处也得把「有什么」带上。

    ★ 真发现：两个重画的地方（nest-tabs / nest-threads）都漏了 `starred`，
      于是切一次窗口，收藏过的星全没了 —— 后端一直在回，是前端没接着。
    """

    def test_both_renderers_pass_starred_and_files(self):
        for f in ("nest-tabs.js", "nest-threads.js"):
            js = (ROOT / "core" / "web" / f).read_text(encoding="utf-8")
            self.assertIn("starred:it.starred", js, f + " 重画时丢了收藏")
            self.assertIn("files:it.files", js, f + " 重画时丢了附件（表情包）")


if __name__ == "__main__":
    unittest.main()
