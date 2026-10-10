"""一轮对话里能连着做几步 —— 工具循环的轮数上限，以及「做完必须说点什么」。

用户定的两件事，都在这里钉住：

  ① **一口气做完**：一件事要好几步（翻记忆 → 查东西 → 写下来 → 回报），
     就该在这一轮里连着做完，不要做一步停下来等人催。
     原来上限是写死在 `while rounds < 5` 里的**字面量 5** —— 五步够干什么，
     查一次记忆就没得剩了。现在是有名字的常量 `MAX_TOOL_ROUNDS`。
  ② **每次动作都必须输出一些东西**：原来模型光动手不说话时，屏幕上是
     一条 error（「它光动手没说话 —— 看顶上的 🧠 面板」）—— 等于事做完了却什么都没有。

上限别调太高：轮数越多这一轮越慢、越烧 token。
"""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from core.engines.base import Turn  # noqa: E402
from core.engines.openai_compat import MAX_TOOL_ROUNDS, OpenAICompatEngine  # noqa: E402


class _Resp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._p = payload

    def json(self):
        return self._p

    @property
    def text(self):
        return json.dumps(self._p)


class _FakeClient:
    """每次 POST 依次吐出脚本里的下一个回应。"""

    def __init__(self, script):
        self.script = list(script)
        self.seen = []

    async def post(self, url, headers=None, json=None):  # noqa: A002 —— 跟 httpx 同名
        self.seen.append(json)
        return _Resp(self.script.pop(0))

    async def aclose(self):
        pass


def _toolcall(name="search_memory"):
    return {"choices": [{"message": {"role": "assistant", "content": None,
                                     "tool_calls": [{"id": "c", "type": "function",
                                                     "function": {"name": name,
                                                                  "arguments": "{}"}}]}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def _speak(text):
    return {"choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def _drive(script):
    """跑一轮，返回 (事件列表, 真被调用的工具名)。"""
    eng = OpenAICompatEngine(key="sk-test", base="https://example.invalid", model="m")
    called = []

    async def ex(name, args):
        called.append(name)
        return {"ok": True}

    eng.tools = [{"type": "function", "function": {
        "name": "search_memory", "description": "d",
        "parameters": {"type": "object", "properties": {}}}}]
    eng.exec_tool = ex
    fake = _FakeClient(script)
    # ★ 引擎是在函数里 `import httpx as _hx` 的 —— 打到 sys.modules 里那个模块对象上才有效
    real = httpx.AsyncClient
    httpx.AsyncClient = lambda *a, **kw: fake
    evs = []
    try:
        async def run():
            async for e in eng.stream(Turn(message="帮我把这件事做完")):
                evs.append(e)
        asyncio.run(run())
    finally:
        httpx.AsyncClient = real
    out = []
    for e in evs:
        for line in str(e).split("\n"):
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out, called


class TestTheCap(unittest.TestCase):
    def test_the_cap_is_a_named_constant_and_is_big_enough(self):
        self.assertGreaterEqual(MAX_TOOL_ROUNDS, 10,
                                "用户要的是「一口气做完多步」，上限至少两位数")
        self.assertLessEqual(MAX_TOOL_ROUNDS, 30,
                             "别调太高 —— 一轮会又长又慢又烧 token")
        src = (ROOT / "core" / "engines" / "openai_compat.py").read_text(encoding="utf-8")
        self.assertIn("while rounds < MAX_TOOL_ROUNDS:", src)
        self.assertNotIn("while rounds < 5:", src, "不许再留一个写死的 5")

    def test_it_really_chains_past_the_old_limit(self):
        """连做 8 步再说话 —— 旧的 5 轮上限会在第 6 步把它掐掉。"""
        out, called = _drive([_toolcall()] * 8 + [_speak("查完了，都记下了。")])
        self.assertEqual(8, len(called), "八步应该都做完")
        self.assertNotIn("error", [k.get("type") for k in out])
        said = [k.get("text") for k in out if k.get("type") == "s"]
        self.assertIn("查完了，都记下了。", said, "做完了要落到那句话上")

    def test_it_stops_at_the_cap(self):
        """一直动手没完没了 —— 也得在上限那儿停下，不能无限转。"""
        out, called = _drive([_toolcall()] * (MAX_TOOL_ROUNDS + 5) + [_speak("")])
        self.assertEqual(MAX_TOOL_ROUNDS, len(called))


class TestItAlwaysSaysSomething(unittest.TestCase):
    def test_the_dead_end_error_is_gone(self):
        import re as _re
        src = (ROOT / "core" / "engines" / "openai_compat.py").read_text(encoding="utf-8")
        # ★ 注释里提到那句是可以的（那是在讲「原来为什么错」）—— 先把注释去掉再查，
        #   跟 test_phone_audit 里 emoji / 导航那两条同一个规矩。
        code = _re.sub(r"(?m)^\s*#.*$", "", src)
        code = _re.sub(r"#[^\n\"']*$", "", code, flags=_re.M)
        self.assertNotIn("它光动手没说话", code,
                         "那条 error 等于「事做完了屏幕上什么都没有」")

    def test_actions_without_words_still_produce_output(self):
        """它跑满上限也没说话 —— 屏幕上必须还有东西，而且不能是 error。"""
        out, called = _drive([_toolcall()] * (MAX_TOOL_ROUNDS + 3) + [_speak("")])
        self.assertTrue(called, "得真动过手")
        kinds = [k.get("type") for k in out]
        self.assertNotIn("error", kinds, "不该再报错")
        said = [k.get("text") for k in out if k.get("type") == "s"]
        self.assertTrue(said, "每次动作都必须输出一些东西")
        self.assertIn("search_memory", "".join(said), "如实报它做了什么")

    def test_a_reply_attached_to_a_tool_call_is_not_thrown_away(self):
        """模型可能一边说话一边动手 —— 同一句里的 content 不许丢。"""
        both = {"choices": [{"message": {
            "role": "assistant", "content": "我先去翻一下记忆。",
            "tool_calls": [{"id": "c", "type": "function",
                            "function": {"name": "search_memory", "arguments": "{}"}}]}}],
            "usage": {}}
        out, called = _drive([both, _speak("翻到了。")])
        self.assertEqual(1, len(called))
        said = [k.get("text") for k in out if k.get("type") == "s"]
        self.assertIn("我先去翻一下记忆。", said, "动手时说的那句也要留下来")


class TestThePromptPushesFollowThrough(unittest.TestCase):
    def test_the_system_prompt_tells_it_to_finish_in_one_go(self):
        src = (ROOT / "core" / "server.py").read_text(encoding="utf-8")
        self.assertIn("〔一口气做完〕", src)
        self.assertIn("不要做一步就停下来等对方催", src)
        self.assertIn("只有真的需要对方拿主意、或需要等外部条件时，才中途停", src)
        # 得挨着那条硬规矩（一个管「别谎报」，一个管「别做一半」）
        i_rule = src.index("〔手·硬规矩〕")
        i_next = src.index("〔一口气做完〕")
        self.assertLess(i_rule, i_next)
        self.assertLess(i_next - i_rule, 900, "两条该是挨着的")


if __name__ == "__main__":
    unittest.main()
