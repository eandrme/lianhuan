"""烧了多少 token —— 记账这条路（0904 新加）。

她问的：「链接里这个『用量』，本意是 token，用了多少 token 的计数有做吗，
这个应该很简单吧，因为很早以前最早最早红叶小筑的时候有过这个功能。」
查下来开源版一条都没接，这是补的。

★ 三条底线：
  · 只记数不记内容 —— 这张表拿去看账，不该在里面读到说过什么
  · 报不出来就没有，不估、不折算成钱（单价各家不同还会变，猜一个比不给更糟）
  · **摔了的那半截也记** —— 照样烧了钱，不记等于账对不上
"""
import asyncio
import json
import os
import tempfile
import unittest

from core.engines.base import Turn
from core.protocol import USAGE


def _store():
    d = tempfile.mkdtemp(prefix="lh-usage-")
    from core.store.sqlite import SqliteStore
    return SqliteStore(os.path.join(d, "x.db"))


class TestLedger(unittest.TestCase):
    def test_it_adds_up_and_splits_by_model(self):
        s = _store()
        s.add_usage(engine="anthropic", model="claude-opus-5", tin=1200, tout=340,
                    tcache_r=9000, tcache_w=1800)
        s.add_usage(engine="anthropic", model="claude-opus-5", tin=300, tout=120, tcache_r=11000)
        s.add_usage(engine="openai", model="deepseek-chat", tin=800, tout=200)
        d = s.usage_stats(days=30)
        self.assertEqual(d["total"], {"tin": 2300, "tout": 660, "tcache_r": 20000, "tcache_w": 1800})
        self.assertEqual(d["turns"], 3)
        top = d["by_model"][0]
        self.assertEqual(top["model"], "claude-opus-5")
        self.assertEqual(top["turns"], 2)
        self.assertEqual(top["tcache_r"], 20000)

    def test_empty_is_zero_not_a_crash(self):
        d = _store().usage_stats()
        self.assertEqual(d["turns"], 0)
        self.assertEqual(d["by_model"], [])
        self.assertEqual(d["total"], {"tin": 0, "tout": 0, "tcache_r": 0, "tcache_w": 0})

    def test_the_table_holds_no_words(self):
        """★ 只记数。往里塞正文的路必须不存在 —— 看账的人不该读到我俩说了什么。"""
        s = _store()
        cols = [r[1] for r in s.db.execute("PRAGMA table_info(token_usage)")]
        for c in cols:
            self.assertNotIn(c, ("content", "text", "message", "think"), f"{c} 不该在这张表里")
        self.assertEqual(sorted(cols),
                         sorted(["id", "ts", "engine", "model", "tin", "tout", "tcache_r", "tcache_w"]))


class TestEnginesReport(unittest.TestCase):
    """两条 API 路都要把账报出来；报不出来的（回声）不许瞎报。"""

    def _events(self, engine, script):
        import tests.test_anthropic as ta
        out, fake = ta._run(engine, Turn(message="在吗"), script)
        return out

    def test_anthropic_reports_in_out_and_cache(self):
        import tests.test_anthropic as ta
        from core.engines.anthropic_api import AnthropicEngine
        eng = AnthropicEngine(key="sk-ant-test")
        evs = self._events(eng, ta._sse(
            {"type": "message_start", "message": {"usage": {
                "input_tokens": 120, "cache_read_input_tokens": 9000,
                "cache_creation_input_tokens": 1800}}},
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "在。"}},
            {"type": "message_delta", "usage": {"output_tokens": 42}},
        ))
        u = [json.loads(e[6:]) for e in evs if '"usage"' in e]
        self.assertTrue(u, "一条 usage 都没报")
        d = u[0]
        self.assertEqual((d["tin"], d["tout"], d["tcache_r"], d["tcache_w"]), (120, 42, 9000, 1800))
        self.assertEqual(d["model"], eng.model)

    def test_echo_reports_nothing(self):
        """回声不烧 token —— 它要是报了账，那就是编的。"""
        from core.engines.echo import EchoEngine
        evs = []

        async def go():
            async for e in EchoEngine().stream(Turn(message="在吗")):
                evs.append(e)
        asyncio.run(go())
        self.assertFalse([e for e in evs if '"%s"' % USAGE in e])


class TestCliCountsToo(unittest.TestCase):
    """★ 订阅那条路也数得出来 —— 她原以为「订阅好像看不到 Claude 的 token 数」。

    那是 API 控制台的事。`--output-format stream-json` 吐的就是 Anthropic 的
    原生流事件（cli.py 早就在解 content_block_delta / thinking_delta 了，同一套），
    所以 message_start / message_delta 里的 usage 一样在。

    ★ 这一份能证明的：**字段名解得对、取不到就不记**。
      它证明不了本机那个 CLI 真的吐这些行 —— 这台机器上 claude 没有执行权限，跑不了。
      所以文档里只能写「按同构接的」，不许写「已实测」。
    """

    #: 从 cli.py 里原样搬下来的那几行 —— 改了那边这儿就该跟着改（改漏了这条会红）
    def _fold(self, events):
        used = {"tin": 0, "tout": 0, "tcache_r": 0, "tcache_w": 0}
        for ev in events:
            et = ev.get("type")
            if et == "message_start":
                u = ((ev.get("message") or {}).get("usage")) or {}
                used["tin"] += int(u.get("input_tokens") or 0)
                used["tcache_r"] += int(u.get("cache_read_input_tokens") or 0)
                used["tcache_w"] += int(u.get("cache_creation_input_tokens") or 0)
            elif et == "message_delta":
                used["tout"] += int((ev.get("usage") or {}).get("output_tokens") or 0)
        return used

    def test_the_parsing_is_wired_and_named_right(self):
        with open("core/engines/cli.py", encoding="utf-8") as f:
            src = f.read()
        for frag in ('et == "message_start"', 'et == "message_delta"',
                     "cache_read_input_tokens", "cache_creation_input_tokens",
                     "output_tokens", "sse(USAGE"):
            self.assertIn(frag, src, f"cli.py 里少了 {frag}")

    def test_it_folds_the_numbers(self):
        got = self._fold([
            {"type": "message_start", "message": {"usage": {
                "input_tokens": 120, "cache_read_input_tokens": 9000,
                "cache_creation_input_tokens": 1800}}},
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "在。"}},
            {"type": "message_delta", "usage": {"output_tokens": 42}},
        ])
        self.assertEqual(got, {"tin": 120, "tout": 42, "tcache_r": 9000, "tcache_w": 1800})

    def test_nothing_reported_means_nothing_recorded(self):
        """一条 usage 都没有的时候不许记 —— 宁可没账，不能有假账。"""
        got = self._fold([{"type": "content_block_delta",
                           "delta": {"type": "text_delta", "text": "在。"}}])
        self.assertFalse(any(got.values()))


class TestOpenAIAsksForUsage(unittest.TestCase):
    def test_stream_options_include_usage_is_sent(self):
        """★ OpenAI 那套流式**默认不给** usage，得显式要 —— 少这一行就永远是 0。"""
        with open("core/engines/openai_compat.py", encoding="utf-8") as f:
            src = f.read()
        self.assertIn('"stream_options": {"include_usage": True}', src)


# ══════════════════════════════════════════════════════════════════
# ★ 真机上埋了很久的洞：**带工具**那条路一帧 usage 都不报
#
# `yield sse(USAGE, …)` 原来只写在 openai_compat 的**流式**那条路末尾，
# 可只要引擎带工具 —— 走 API 的引擎一直带着（pick_engine 会给它 all_tools）——
# 就永远走「有手」那条路；那条路走完是 `yield DONE; return`，**压根到不了**那一行。
# 于是 token_usage 表一直是空的：聊了几百轮，「用量」看板上一个数都没有。
#
# （anthropic 没这毛病：它的 USAGE 挂在 `finally` 里，每条出路都过 ——
#   所以这个洞专吃 OpenAI 兼容那一大票，而用户接的正好是 DeepSeek。）
#
# 上面那些用例全都测不到它：TestEnginesReport 只测了 anthropic 和 echo，
# TestOpenAIAsksForUsage 只查了一个字符串。
# ══════════════════════════════════════════════════════════════════
class TestOpenAIToolPathReportsUsage(unittest.TestCase):
    class _Resp:
        def __init__(self, payload, status=200):
            self.status_code = status
            self._p = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._p

    class _Sse:
        """流式那条路用的假回应：把脚本里那一条渲染成 SSE 行。

        ★ 少了它，「没有手那条路」根本跑不起来 —— 那条路走的是
          `client.stream(...)`（不是 post），第一版就栽在这儿。
        """

        def __init__(self, payload):
            self._p = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        @property
        def status_code(self):
            return 200

        @property
        def headers(self):
            return {"content-type": "text/event-stream"}

        async def aread(self):
            return b""

        async def aiter_lines(self):
            m = ((self._p.get("choices") or [{}])[0].get("message")) or {}
            yield "data: " + json.dumps(
                {"choices": [{"delta": {"content": m.get("content") or ""}}]})
            yield "data: " + json.dumps({"choices": [], "usage": self._p.get("usage") or {}})
            yield "data: [DONE]"
            yield ""

    class _Cli:
        def __init__(self, script, statuses):
            self.script, self.statuses, self.n = list(script), list(statuses), 0

        async def post(self, url, headers=None, json=None):  # noqa: A002
            self.n += 1
            st = self.statuses.pop(0) if self.statuses else 200
            return TestOpenAIToolPathReportsUsage._Resp(self.script.pop(0), st)

        def stream(self, method, url, headers=None, json=None, timeout=None):  # noqa: A002
            self.n += 1
            return TestOpenAIToolPathReportsUsage._Sse(self.script.pop(0))

        async def aclose(self):
            pass

    @staticmethod
    def _tool(usage=None):
        return {"choices": [{"message": {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "c", "type": "function",
                            "function": {"name": "search_memory", "arguments": "{}"}}]}}],
            "usage": usage or {"prompt_tokens": 100, "completion_tokens": 10}}

    @staticmethod
    def _say(text, usage=None):
        return {"choices": [{"message": {"role": "assistant", "content": text}}],
                "usage": usage or {"prompt_tokens": 200, "completion_tokens": 20}}

    def _run(self, script, statuses=None, with_tools=True):
        import httpx
        from core.engines.openai_compat import OpenAICompatEngine
        eng = OpenAICompatEngine(key="sk-test", base="https://example.invalid",
                                 model="deepseek-flash")

        async def ex(name, args):
            return {"ok": True}

        if with_tools:
            eng.tools = [{"type": "function", "function": {
                "name": "search_memory", "description": "d",
                "parameters": {"type": "object", "properties": {}}}}]
            eng.exec_tool = ex
        fake = self._Cli(script, statuses or [])
        real = httpx.AsyncClient
        httpx.AsyncClient = lambda *a, **kw: fake
        evs = []
        try:
            async def go():
                async for e in eng.stream(Turn(message="干活")):
                    evs.append(str(e))
            asyncio.run(go())
        finally:
            httpx.AsyncClient = real
        out = []
        for e in evs:
            for line in e.split("\n"):
                if line.startswith("data: "):
                    out.append(json.loads(line[6:]))
        return out, fake

    def test_the_tool_path_emits_usage(self):
        """★ 就是这条：带工具时以前一帧都没有。"""
        out, fake = self._run([self._tool(), self._say("做完了。")])
        u = [d for d in out if d.get("type") == USAGE]
        self.assertEqual(1, len(u), "带工具那条路也必须报一帧 usage")
        self.assertEqual(2, fake.n)

    def test_it_sums_every_tool_round_not_just_the_last(self):
        """一轮翻五次记忆就是六次请求的账 —— 不能只记最后一回合。"""
        out, _ = self._run([self._tool(), self._tool(), self._say("做完了。")])
        u = [d for d in out if d.get("type") == USAGE][0]
        self.assertEqual(400, u["tin"], "100+100+200（三轮加起来）")
        self.assertEqual(40, u["tout"], "10+10+20")

    def test_it_says_which_engine_and_model(self):
        out, _ = self._run([self._tool(), self._say("好了")])
        u = [d for d in out if d.get("type") == USAGE][0]
        self.assertEqual("openai", u["engine"])
        self.assertEqual("deepseek-flash", u["model"])

    def test_the_streaming_path_still_reports_too(self):
        """没有手那条路本来就是好的 —— 别把它改坏了。"""
        out, _ = self._run([self._say("就直接回答")], with_tools=False)
        u = [d for d in out if d.get("type") == USAGE]
        self.assertEqual(1, len(u))
        self.assertEqual(200, u[0]["tin"])

    def test_a_broken_upstream_still_reports_what_was_burned(self):
        """摔了的那半截照样烧了钱 —— 账要对得上。"""
        out, _ = self._run([self._tool(), self._tool({})], statuses=[200, 500])
        self.assertIn("error", [d.get("type") for d in out])
        u = [d for d in out if d.get("type") == USAGE]
        self.assertEqual(1, len(u), "前面那一轮已经烧了的也得记上")
        self.assertEqual(100, u[0]["tin"])


class TestTheUsageBoardInSettings(unittest.TestCase):
    """看板那一节：接的是 /api/usage，别自己另算一套，也别折算成钱。"""

    def setUp(self):
        self.path = "core/web/nest-setting.js"
        with open(self.path, encoding="utf-8") as f:
            self.js = f.read()
        self.seg = self.js[self.js.index("async function secUsage("):]
        self.seg = self.seg[:self.seg.index("async function secEngine(")]

    def test_the_section_is_registered(self):
        self.assertIn("secUsage(box)", self.js)
        self.assertIn('id="usage-sec"', self.js)

    def test_it_reads_the_real_endpoint(self):
        self.assertIn("/api/usage", self.seg)

    def test_it_does_not_invent_money(self):
        """各家单价不同还会变 —— 猜一个数比不给更糟。只报 token。"""
        for bad in ("价格", "单价", "美元", "￥", "花费", "折合"):
            self.assertNotIn(bad, self.seg, f"不该出现「{bad}」")
        self.assertIn("token", self.seg)

    def test_it_shows_today_window_and_total(self):
        self.assertIn("今天", self.seg)
        self.assertIn("j.today", self.seg)
        self.assertIn("j.total", self.seg)
        self.assertIn("j.window", self.seg)


if __name__ == "__main__":
    unittest.main()
