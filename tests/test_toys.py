"""玩具箱 —— 他写的小网页，在巢里点开就玩。

地基是原项目那套（`data/plays/*.html` ＋ `/api/plays` ＋ `/plays/<file>` ＋
`write_play` / `list_plays` 两只手）。这一版补的是**界面**，外加人能做的两件事：
  · 戳他现做一个（真用引擎写；写不出来老实说，不塞个空壳进玩具箱）
  · 不喜欢了划掉

★ 两条硬线：
  ① 文件名是外面传进来的 —— `../` 那种必须在落盘/删之前就断掉
  ② 玩的时候用 `sandbox="allow-scripts"`：小玩意是**同一个域名**下的网页，
     不隔开它就能摸到外层页面（也就摸得到会话）
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

TOY = ("<!DOCTYPE html><html><head><title>捏泡泡</title></head>"
       "<body><button onclick=\"this.textContent='啵'\">捏</button></body></html>")


class _Base(unittest.TestCase):
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
        self.old_db = __import__("os").environ.get("LIANHUAN_DB")
        __import__("os").environ["LIANHUAN_DB"] = str(Path(self.tmp.name) / "lh.db")
        self.addCleanup(self._restore_env)
        self.store = SqliteStore(Path(self.tmp.name) / "lh.db")
        self.said = []

        async def _say(p):
            self.said.append(p)
            return getattr(self, "reply", "")
        self.hl.bind(self.store, _say)
        self.plays = Path(self.tmp.name) / "plays"
        self.plays.mkdir(parents=True, exist_ok=True)

    def _restore_env(self):
        import os
        if self.old_db is None:
            os.environ.pop("LIANHUAN_DB", None)
        else:
            os.environ["LIANHUAN_DB"] = self.old_db


class TestTheShelfListsWhatIsReallyThere(_Base):
    def test_it_reads_the_title_out_of_the_file(self):
        (self.plays / "a.html").write_text(TOY, encoding="utf-8")
        items = self.c.get("/api/plays").json()["items"]
        self.assertEqual(1, len(items))
        self.assertEqual("捏泡泡", items[0]["title"], "名字取 <title>，不是文件名")
        self.assertEqual("a.html", items[0]["file"])
        self.assertEqual("/plays/a.html", items[0]["url"])

    def test_no_title_falls_back_to_the_filename(self):
        (self.plays / "b.html").write_text("<html><body>hi</body></html>", encoding="utf-8")
        self.assertEqual("b", self.c.get("/api/plays").json()["items"][0]["title"])

    def test_it_only_lists_html(self):
        (self.plays / "a.html").write_text(TOY, encoding="utf-8")
        (self.plays / "_offline.json").write_text("{}", encoding="utf-8")
        self.assertEqual(["a.html"],
                         [x["file"] for x in self.c.get("/api/plays").json()["items"]])

    def test_an_empty_shelf_is_honest(self):
        self.assertEqual([], self.c.get("/api/plays").json()["items"])


class TestDeleting(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        import os
        self.old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = str(Path(self.tmp.name) / "lh.db")
        self.addCleanup(lambda: (os.environ.pop("LIANHUAN_DB", None) if self.old is None
                                 else os.environ.__setitem__("LIANHUAN_DB", self.old)))
        from optional.homelife import routes as hl
        self.hl = hl
        app = FastAPI()
        app.include_router(hl.router)
        self.c = TestClient(app)
        self.store = SqliteStore(Path(self.tmp.name) / "lh.db")

        async def _say(p):
            return ""
        hl.bind(self.store, _say)
        self.plays = Path(self.tmp.name) / "plays"
        self.plays.mkdir(parents=True, exist_ok=True)
        (self.plays / "a.html").write_text(TOY, encoding="utf-8")
        # 玩具箱外面放一个「不该被碰到」的文件
        (Path(self.tmp.name) / "precious.txt").write_text("别删我", encoding="utf-8")

    def test_a_toy_can_be_cleared_away(self):
        self.assertTrue(self.c.post("/api/plays/a.html/del").json()["ok"])
        self.assertEqual([], self.c.get("/api/plays").json()["items"])
        self.assertFalse((self.plays / "a.html").exists())

    def test_a_path_that_climbs_out_is_refused(self):
        """★ 名字是外面传进来的 —— `../` 必须在落盘/删之前断掉。"""
        for bad in ("../precious.txt", "..%2Fprecious.txt", "a.txt", "....//x.html",
                    ".hidden.html", "sub/x.html"):
            r = self.c.post(f"/api/plays/{bad}/del")
            self.assertIn(r.status_code, (400, 404), bad)
        self.assertTrue((Path(self.tmp.name) / "precious.txt").exists(), "外面那个文件不许被碰")

    def test_deleting_something_that_is_not_there_says_so(self):
        self.assertEqual(404, self.c.post("/api/plays/nope.html/del").status_code)


class TestAskingForANewOne(_Base):
    def test_it_writes_a_real_toy_and_puts_it_on_the_shelf(self):
        self.reply = "这是给你的：\n```html\n" + TOY + "\n```\n玩得开心"
        r = self.c.post("/api/plays/new", json={"hint": "解压的"}).json()
        self.assertTrue(r["ok"], r)
        self.assertTrue((self.plays / r["file"]).exists(), "文件得真落盘")
        self.assertEqual("捏泡泡", r["title"])
        self.assertIn("解压的", self.said[0], "他说想要什么，得带进提示词")
        items = self.c.get("/api/plays").json()["items"]
        self.assertEqual([r["file"]], [x["file"] for x in items])

    def test_a_stub_engine_is_not_allowed_to_fake_one(self):
        """★ 引擎是桩（回声）时写不出玩具 —— 那就老实说，别塞个空壳上架。"""
        self.reply = ""
        r = self.c.post("/api/plays/new", json={})
        self.assertEqual(502, r.status_code)
        self.assertEqual([], self.c.get("/api/plays").json()["items"])

    def test_something_that_is_not_html_is_refused(self):
        self.reply = "好的，我这就写！（然后什么都没写）"
        self.assertEqual(502, self.c.post("/api/plays/new", json={}).status_code)
        self.assertEqual([], self.c.get("/api/plays").json()["items"])

    def test_a_too_big_toy_is_refused_by_the_hand(self):
        self.reply = "<!DOCTYPE html><html><body>" + ("x" * 500_000) + "</body></html>"
        r = self.c.post("/api/plays/new", json={})
        self.assertEqual(502, r.status_code, "那只手有 400KB 上限，超了不许上架")


class TestTheHandsActuallyWork(unittest.TestCase):
    """★ 这一条是被真事逼出来的：`write_play` / `list_plays` 两只手**一直是坏的**。

    `execute()` 里有一句 `from datetime import date as _dd` —— 于是 `_dd` 在整个函数里
    成了局部名，而上面那两处想用的是「数据目录」那个 `_dd` → UnboundLocalError。
    也就是说：他以前想写玩具，一调用就报错（界面上只会看到「他没做成」）。
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        import os
        self.old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = str(Path(self.tmp.name) / "lh.db")
        self.addCleanup(lambda: (os.environ.pop("LIANHUAN_DB", None) if self.old is None
                                 else os.environ.__setitem__("LIANHUAN_DB", self.old)))

    def test_list_and_write_do_not_blow_up(self):
        import asyncio
        from core import hands
        self.assertEqual([], asyncio.run(hands.execute("list_plays", {}))["items"])
        r = asyncio.run(hands.execute("write_play", {"filename": "t1", "html": TOY}))
        self.assertTrue(r["ok"], r)
        self.assertIn("t1.html", asyncio.run(hands.execute("list_plays", {}))["items"])

    def test_the_hand_still_says_no_to_junk(self):
        import asyncio
        from core import hands
        self.assertFalse(asyncio.run(hands.execute("write_play", {"filename": "x", "html": "短"}))["ok"])
        self.assertFalse(asyncio.run(
            hands.execute("write_play", {"filename": "x", "html": "x" * 500_000}))["ok"])


class TestTheUi(unittest.TestCase):
    def setUp(self):
        web = ROOT / "core" / "web"
        self.html = (web / "nest.html").read_text(encoding="utf-8")
        self.js = (web / "nest-toys.js").read_text(encoding="utf-8")
        self.tabs = (web / "nest-tabs.js").read_text(encoding="utf-8")

    def test_it_is_a_tab_and_the_module_is_loaded(self):
        self.assertIn('["toys","🧸","玩具箱"]', self.tabs)
        self.assertIn('src="/nest-toys.js', self.html)

    def test_it_walks_the_real_api(self):
        self.assertIn("/api/plays", self.js)
        self.assertIn("/api/plays/new", self.js)
        self.assertIn("/del", self.js)

    def test_playing_it_happens_in_a_sandbox(self):
        import re as _re
        code = _re.sub(r"/\*[\s\S]*?\*/", "", self.js)      # 注释里提过那一句，不算
        self.assertIn('setAttribute("sandbox","allow-scripts")', code,
                      "小玩意是同域名网页 —— 不隔开它就能摸到外层页面")
        self.assertNotIn("allow-same-origin", code, "给了它沙箱就白设了")
        self.assertIn("iframe", code)

    def test_there_is_a_way_out_for_toys_that_need_to_store_things(self):
        self.assertIn("新窗口", self.js, "沙箱里不让存东西，得有条别的路")

    def test_the_url_is_encoded(self):
        self.assertIn("encodeURIComponent(x.file", self.js,
                      "文件名里带引号/空格会顶穿 URL")


if __name__ == "__main__":
    unittest.main()
