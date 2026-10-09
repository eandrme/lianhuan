"""想多深（深度思考）—— 这一档必须**真的有用**。

★ 加它之前，开源版的 `/api/think` 只往 settings 里写一个**没人读**的值：
  老界面那个「想多深」弹层等于摆设（拨了什么都不变）。这个文件钉住它落地在三处：

  ① 一句话进 system —— 哪家引擎都吃得到（Claude / 本机 CLI / 不认参数的家）
  ② OpenAI 兼容那条把它翻成 `reasoning_effort` —— 认这个字段的家真会少想/多想
  ③ 这家不认那个字段时，退一档重来一次，**绝不让整轮说话失败**
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import think                                            # noqa: E402


class TestThinkMapping(unittest.TestCase):
    def test_only_three_modes_and_unknown_falls_back_to_auto(self):
        self.assertEqual(("fast", "auto", "deep"), think.MODES)
        self.assertEqual("auto", think.DEFAULT)

        class S:
            def __init__(self, v): self.v = v
            def get_setting(self, k, d=None): return self.v

        self.assertEqual("deep", think.mode(S("deep")))
        self.assertEqual("auto", think.mode(S("medium")), "老库里存过 medium，退回自动")
        self.assertEqual("auto", think.mode(S(None)))

    def test_effort_mapping(self):
        self.assertIsNone(think.effort("auto"), "自动＝什么都不标，行为跟从前一模一样")
        self.assertEqual("low", think.effort("fast"))
        self.assertEqual("max", think.effort("deep"))

    def test_effort_respects_what_the_provider_allows(self):
        """这家只认到 medium，那「偏深」就按它认的最高那档走 —— 不是不发。"""
        self.assertEqual("medium", think.effort("deep", ["none", "minimal", "low", "medium"]))
        self.assertEqual("low", think.effort("fast", ["low", "medium"]))
        self.assertEqual("medium", think.effort("fast", ["medium", "high"]),
                         "连 low 都不认就从它认的里面挑最低的")
        self.assertIsNone(think.effort("deep", []), "一个都不认就别发")

    def test_the_nudge_says_something_different_per_mode(self):
        self.assertEqual("", think.nudge("auto"), "自动那一档不加任何话")
        f, d = think.nudge("fast"), think.nudge("deep")
        self.assertTrue(f and d and f != d)
        self.assertIn("快", f)
        self.assertIn("多想一层", d)

    def test_it_can_read_the_allowed_values_out_of_a_real_error(self):
        """DeepSeek 实测的原话（探针真发的，不是编的）。"""
        msg = ("Failed to deserialize the JSON body into the target type: reasoning_effort: "
               "unknown variant `banana`, expected one of `none`, `minimal`, `low`, `medium`, "
               "`high`, `xhigh`, `ultra`, `max` at line 1 column 128 (request_id: 8fd33a46)")
        got = think.allowed_from_error(msg)
        self.assertIn("max", got)
        self.assertIn("low", got)
        self.assertNotIn("at", got, "后面那截尾巴不能被当成档位")
        self.assertEqual([], think.allowed_from_error("完全是别的错"))


class _FakeProvider(BaseHTTPRequestHandler):
    """一个**真的**监听端口的 OpenAI 兼容上游：把请求体记下来，回最小的流式响应。

    还能扮演「不认 reasoning_effort 的家」：第一次 422 ＋ DeepSeek 那种报错，第二次收。
    """
    seen: list = []
    reject_effort = False
    rejected_once = False

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        type(self).seen.append(body)
        if type(self).reject_effort and not type(self).rejected_once and "reasoning_effort" in body:
            type(self).rejected_once = True
            err = {"error": {"message": "reasoning_effort: unknown variant `max`, expected one of "
                                        "`none`, `minimal`, `low`, `medium` at line 1 column 9"}}
            raw = json.dumps(err).encode()
            self.send_response(422)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for chunk in ('data: {"choices":[{"delta":{"content":"好"}}]}\n\n',
                      'data: [DONE]\n\n'):
            self.wfile.write(chunk.encode())
            self.wfile.flush()


class TestTheEngineReallyGetsIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _FakeProvider)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _run(self, mode, reject=False, clear_memo=True):
        from core.engines.openai_compat import OpenAICompatEngine, _EFFORT_MEMO
        from core.engines.base import Turn
        _FakeProvider.seen = []
        _FakeProvider.reject_effort = reject
        _FakeProvider.rejected_once = False
        if clear_memo:
            _EFFORT_MEMO.clear()
        eng = OpenAICompatEngine(base=f"http://127.0.0.1:{self.port}", model="m1", key="k")
        out = []

        async def go():
            async for ev in eng.stream(Turn(message="在吗", think=mode)):
                if ev.startswith("data: "):
                    try:
                        out.append(json.loads(ev[6:]))
                    except Exception:
                        pass
        asyncio.run(go())
        return _FakeProvider.seen, out

    def test_auto_sends_nothing_extra(self):
        seen, out = self._run("auto")
        self.assertNotIn("reasoning_effort", seen[0], "默认这一档跟以前一字不差")
        self.assertIn("好", "".join(d.get("text", "") for d in out if d.get("type") == "s"))

    def test_fast_and_deep_are_translated(self):
        self.assertEqual("low", self._run("fast")[0][0].get("reasoning_effort"))
        self.assertEqual("max", self._run("deep")[0][0].get("reasoning_effort"))

    def test_a_provider_that_rejects_it_gets_a_second_chance(self):
        """★ 不认「偏深」这档的家不能让整轮说话失败 ——
        从它的报错里抄出它认哪几档，**按它认的最高那档**重来一次。"""
        seen, out = self._run("deep", reject=True)
        self.assertEqual(2, len(seen), "该重来一次")
        self.assertEqual("max", seen[0].get("reasoning_effort"), "第一次照用户说的试")
        self.assertEqual("medium", seen[1].get("reasoning_effort"),
                         "第二次按这家认的最高那档走（不是干脆不发）")
        self.assertFalse(any(d.get("type") == "error" for d in out), "用户不该看到这轮失败")
        self.assertIn("好", "".join(d.get("text", "") for d in out if d.get("type") == "s"))

    def test_it_remembers_and_uses_what_that_provider_allows(self):
        from core.engines.openai_compat import _EFFORT_MEMO
        self._run("deep", reject=True)                     # 先撞出来，记下可选值
        key = (f"http://127.0.0.1:{self.port}", "m1")
        self.assertEqual(["none", "minimal", "low", "medium"], _EFFORT_MEMO.get(key))
        seen2, _ = self._run("deep", clear_memo=False)      # 下一轮直接用它认的最高档
        self.assertEqual(1, len(seen2), "记住之后不该再撞一次")
        self.assertEqual("medium", seen2[0].get("reasoning_effort"))


class TestThinkApiAndWiring(unittest.TestCase):
    """/api/think 三档读写 ＋ 它真的进了这一轮的 system / turn。"""

    def setUp(self):
        from fastapi.testclient import TestClient
        from core.store.sqlite import SqliteStore
        import core.server as sv
        self.sv = sv
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_store = sv.store
        sv.store = SqliteStore(Path(self.tmp.name) / "t.db")

        def restore():
            sv.store = self.old_store
        self.addCleanup(restore)
        self.c = TestClient(sv.app)

    def test_get_shape(self):
        j = self.c.get("/api/think").json()
        self.assertEqual("auto", j["mode"], "出厂是自动")
        self.assertEqual(["fast", "auto", "deep"], j["modes"])
        self.assertIn("engine_note", j, "界面要能说清「你现在这家能照办到什么程度」")

    def test_post_only_accepts_the_three(self):
        self.assertEqual(200, self.c.post("/api/think", json={"mode": "deep"}).status_code)
        self.assertEqual("deep", self.c.get("/api/think").json()["mode"])
        self.assertEqual(400, self.c.post("/api/think", json={"mode": "medium"}).status_code,
                         "老接口谁传都收，于是界面上「拨了没用」也没人发现")
        self.assertEqual(400, self.c.post("/api/think", json={}).status_code)

    def _ask(self, mode):
        from core.engines.base import Engine
        from core.protocol import DONE, SAY, sse
        cap = {}

        class Cap(Engine):
            name, label, ready, stub = "cap", "捕获", True, False

            async def stream(self, turn):
                cap["t"] = turn
                yield sse(SAY, text="好")
                yield sse(DONE, session_id=turn.session_id)

        old = self.sv.pick_engine
        self.sv.pick_engine = lambda: Cap()
        self.addCleanup(lambda: setattr(self.sv, "pick_engine", old))
        self.c.post("/api/think", json={"mode": mode})
        r = self.c.post("/chat", json={"message": "在吗"})
        list(r.iter_lines())            # 走完流，落库/收尾才会跑
        return cap["t"]

    def test_deep_reaches_both_halves(self):
        t = self._ask("deep")
        self.assertEqual("deep", t.think, "档位得随这一轮交给引擎")
        self.assertIn("多想一层", t.system, "提示词那一半也得在")

    def test_fast_reaches_both_halves(self):
        t = self._ask("fast")
        self.assertEqual("fast", t.think)
        self.assertIn("快", t.system)

    def test_auto_changes_nothing(self):
        t = self._ask("auto")
        self.assertEqual("auto", t.think)
        for word in ("多想一层", "对方要的是"):
            self.assertNotIn(word, t.system, "自动这一档不许往 system 里加东西")


class TestTheSwitchIsInTheChatUi(unittest.TestCase):
    def test_the_page_loads_the_switch(self):
        html = (ROOT / "core" / "web" / "nest.html").read_text(encoding="utf-8")
        self.assertIn('src="/nest-think.js', html)

    def test_it_sits_next_to_the_composer_and_reads_the_three_modes(self):
        js = (ROOT / "core" / "web" / "nest-think.js").read_text(encoding="utf-8")
        self.assertIn('$("#composer .row")', js, "要装在主聊天界面的输入框那一行")
        self.assertIn("/api/think", js)
        for m in ("fast", "auto", "deep"):
            self.assertIn(m, js)
        # 三档的名字跟老界面一致，别自己另起一套
        self.assertIn("偏快", js)
        self.assertIn("偏深", js)

    def test_it_is_a_plain_on_off_switch(self):
        """★ 用户要的是「打开和关闭」：点一下＝开/关。

        开＝偏深、关＝自动（自动那一档什么都不发、什么都不加）。
        偏快是第三种状态，别把它装成「关」—— 长按/右键出三档菜单，设置页里也有一份。"""
        js = (ROOT / "core" / "web" / "nest-think.js").read_text(encoding="utf-8")
        self.assertIn('const ON_MODE="deep", OFF_MODE="auto"', js)
        self.assertIn("cur===ON_MODE ? OFF_MODE : ON_MODE", js, "点一下就是开/关")
        self.assertIn("openMenu", js, "偏快那一档还在（长按/右键）")

    def test_it_does_not_pretend_when_it_cannot_read_the_server(self):
        js = (ROOT / "core" / "web" / "nest-think.js").read_text(encoding="utf-8")
        self.assertIn("loaded=false", js, "读不到就不画一个假的档位")
        self.assertIn('"unknown"', js)


class TestASavedConfigNeverNeedsRetyping(unittest.TestCase):
    """★ 真机上撞的：「每次关掉页面重新打开都要再配置一遍模型」。

    配置其实一直存着（key/base/model 都在 secrets.json 里），只是引擎那个设置
    停在回声 —— 界面一句「现在接的：回声」就让人以为得从头再填一遍。
    两条防线：① 设置页给一颗「接上存着的那份配置」；② 每次换引擎都留一行日志，
    以后再出现「它自己变回去了」，一眼看得出是谁干的。
    """

    def setUp(self):
        from fastapi.testclient import TestClient
        from core.store.sqlite import SqliteStore
        import core.server as sv
        self.sv = sv
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_store, self.old_secrets = sv.store, sv.SECRETS
        sv.store = SqliteStore(Path(self.tmp.name) / "t.db")
        sv.SECRETS = Path(self.tmp.name) / "secrets.json"
        self.addCleanup(self._restore)
        self.c = TestClient(sv.app)

    def _restore(self):
        self.sv.store, self.sv.SECRETS = self.old_store, self.old_secrets

    def test_one_tap_reconnects_the_stored_config_without_a_key(self):
        # 装作「上次存过一份」：key 在盘上、引擎却停在回声
        self.sv.SECRETS.write_text(json.dumps(
            {"api_key": "sk-test-abcdefghijklmn", "api_base": "https://api.deepseek.com",
             "api_model": "deepseek-flash"}), encoding="utf-8")
        self.sv.store.set_setting("engine", "echo")
        r = self.c.post("/api/engine/config",
                        json={"engine": "api", "base": "https://api.deepseek.com",
                              "model": "deepseek-flash"})
        self.assertTrue(r.json()["ok"])
        cfg = self.c.get("/api/engine/config").json()
        self.assertEqual("api", cfg["engine"])
        self.assertTrue(cfg["key_set"], "不重贴 key 也得能接上 —— 它本来就在盘上")
        self.assertEqual("deepseek-flash", cfg["model"])

    def test_every_engine_write_goes_through_the_logging_helper(self):
        """三个写引擎的地方（引擎配置 / 换模型 / 老设置接口）都必须留痕。

        ★ 原来一处都不留 —— 引擎「自己变回回声」时查不出是谁干的。"""
        src = (ROOT / "core" / "server.py").read_text(encoding="utf-8")
        self.assertEqual(1, src.count('store.set_setting("engine"'),
                         "只该剩 _set_engine 里那一次直写，别的都走它")
        self.assertIn("def _set_engine(", src)
        for why in ("engine/config", "ai_model", "/api/settings"):
            self.assertIn(why, src, why + " 那一处没走 _set_engine")

    def test_the_settings_page_offers_the_one_tap(self):
        js = (ROOT / "core" / "web" / "nest-setting.js").read_text(encoding="utf-8")
        self.assertIn("接上存着的那份配置", js)
        self.assertIn("stranded", js, "只在「存着配置 + 引擎停在回声」时露出来")
        self.assertIn("secThink", js, "设置页里也有想多深（偏快那一档住这儿）")


if __name__ == "__main__":
    unittest.main()
