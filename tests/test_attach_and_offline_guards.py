"""附件旁白要说实话 ＋ 离线那道门要拦得住。

这一批全是**走查时真抓到的**「说了没做」型毛病，共同点是：
单看代码没问题、测试也全绿，跑起来却在教模型撒谎。

  ① `_attach_note` 对**所有**引擎都说「图片你直接能看见」——
     可靠 claude / 本机 CLI 那两条压根不把 `Turn.images` 发出去（见 engines/base.py
     的 `sees_images`）。模型于是被要求描述一张它没收到的图。
  ② 大小 / 预算挤掉的附件，被一把算成「PDF/Word/压缩包这类读不了」——
     模型会跟人解释错原因（「你的 PDF 我读不了」，其实那是张太大的图）。
  ③ 「一轮 400KB」的预算数的是**字符数**：一个 180KB 的中文文件只有 6 万字，
     三个就能塞进 540KB。
  ④ 离线那一场直接调 `hands.execute`，**绕过 exec_guard** ——
     `OFFLINE_TOOLS=all` 时 `send_sticker` 照发不误，回一个 ok:true 而屏幕上什么都没有。
  ⑤ 手动「真跑一场」走 `force=True`，连「引擎是不是桩」都跳过了：
     回声的诊断原文被写进私密库，接着 residue 又把它渗回正常聊天的提示词。
  ⑥ `last_seen()` 把机器拼的轮也算成「你回来了」（windows.active_sid 早就排除了）——
     切个空间、重新生成一次，就能让该开的离线时段不开、正跑的当场掐断。
  ⑦ 把 OFFLINE_ENABLED 关掉，残影照样往正常聊天的提示词里渗。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WEB = ROOT / "core" / "web"


def _meta(name: str, kind: str, size: int, path: str) -> dict:
    return {"name": name, "kind": kind, "size": size, "path": path, "url": "/x"}


class TestTheAttachNoteTellsTheTruth(unittest.TestCase):
    """旁白是**给模型看的**，说错一句它就照着编。"""

    @classmethod
    def setUpClass(cls):
        from core import server
        cls.sv = server

    def test_images_are_only_promised_to_engines_that_really_send_them(self):
        f = [_meta("a.png", "img", 1000, "/nope/a.png")]
        yes = self.sv._attach_note(f, 1, [], True, True)
        no = self.sv._attach_note(f, 1, [], True, False)
        self.assertIn("你直接能看见", yes)
        self.assertIn("看不见图片", no)
        self.assertIn("别猜", no, "得同时告诉它：看不见就老实说，别编")
        self.assertNotIn("你直接能看见", no)

    def test_the_capability_flag_matches_reality(self):
        """只有真把图拼进请求的那家才算「看得见」。"""
        from core.engines.openai_compat import OpenAICompatEngine
        from core.engines.anthropic_api import AnthropicEngine
        from core.engines.cli import CliEngine
        from core.engines.echo import EchoEngine
        self.assertTrue(OpenAICompatEngine.sees_images, "OpenAI 兼容那条真发图")
        for cls in (AnthropicEngine, CliEngine, EchoEngine):
            self.assertFalse(cls.sees_images, cls.__name__ + " 不把图送出去")

    def test_an_oversized_thing_is_not_blamed_on_pdf(self):
        """被预算挤掉的不许栽赃成「PDF 读不了」—— 那会让它跟人解释错原因。"""
        big = [_meta("big.png", "img", 9 * 1024 * 1024, "/nope/big.png")]
        note = self.sv._attach_note(big, 0, [], True, True)
        self.assertIn("太大", note)
        self.assertNotIn("PDF", note)
        txt = [_meta("big.txt", "file", 630 * 1024, "/nope/big.txt")]
        note2 = self.sv._attach_note(txt, 0, [], True, True)
        self.assertIn("太大", note2)
        self.assertNotIn("PDF", note2)

    def test_a_real_pdf_is_still_reported_as_unreadable(self):
        f = [_meta("a.pdf", "file", 1000, "/nope/a.pdf")]
        note = self.sv._attach_note(f, 0, [], True, True)
        self.assertIn("PDF", note)
        self.assertIn("别编", note)

    def test_a_normal_over_budget_file_is_counted_separately(self):
        f = [_meta("a.png", "img", 1000, "/nope/a.png"),
             _meta("a.pdf", "file", 1000, "/nope/a.pdf"),
             _meta("b.txt", "file", 100, "/nope/b.txt")]
        note = self.sv._attach_note(f, 1, [("b.txt", "内容")], True, True)
        self.assertIn("b.txt", note, "读到了的要说读到了")
        self.assertIn("PDF", note)
        self.assertNotIn("太大", note, "这一轮没有被挤掉的")


class TestTheTextBudgetIsCountedInBytes(unittest.TestCase):
    """「单文件 200KB / 一轮 400KB」—— 数的得是字节，不是字符。"""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def _write(self, name: str, text: str) -> dict:
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return _meta(name, "file", p.stat().st_size, str(p))

    def test_a_chinese_file_does_not_sneak_past_the_budget(self):
        from core import server
        # 每个约 180KB 字节（中文一个字 3 字节 → 6 万字）
        chunk = "雨" * 60000
        metas = [self._write(f"n{i}.txt", chunk) for i in range(3)]
        _, texts = server._attach_payload(metas)
        total = sum(len(t.encode("utf-8")) for _, t in texts)
        self.assertLessEqual(total, server.MAX_TXT_TOTAL,
                             f"一轮塞进模型的内容该 ≤{server.MAX_TXT_TOTAL} 字节，现在 {total}")
        self.assertLess(len(texts), 3, "三个 180KB 的中文文件不该全进去")

    def test_ascii_and_chinese_are_measured_the_same_way(self):
        from core import server
        # 400KB 的 ASCII 该正好卡在预算里（不超），中文那组已经被上一条拦住了
        metas = [self._write("a.txt", "x" * (server.MAX_TXT_BYTES - 10))]
        _, texts = server._attach_payload(metas)
        self.assertEqual(1, len(texts), "一个没超单文件上限的就该读到")


class TestOfflineDoesNotFakeSuccess(unittest.TestCase):
    """离线那一场没有「回复」可以挂图，也没有助手身份 —— 那两只手就该当场拒掉。"""

    def test_sticker_is_refused_offline(self):
        from core import offline
        r = asyncio.run(offline._exec_audited("send_sticker", {"name": "猫"}))
        self.assertFalse(r.get("ok"), "不许回 ok:true 却什么都没发生")
        self.assertIn("表情包", r.get("err", ""))

    def test_the_reason_is_written_into_the_audit_log(self):
        """拒了也要留痕：不然「它那时候到底动没动手」事后查不出来。"""
        from core import offline
        offline._STAT["tools"] = []
        asyncio.run(offline._exec_audited("send_sticker", {}))
        self.assertEqual([("send_sticker", False)], offline._STAT["tools"])

    def test_ordinary_hands_still_work_offline(self):
        """拒的只是那两只**没有地方放结果**的手，别的照跑（这一场本来就有手）。"""
        from core import offline
        r = asyncio.run(offline._exec_audited("list_my_tools", {}))
        self.assertIn("builtin", r, "该能用的还得能用")
        self.assertNotIn("err", r, "没被误伤")


class TestOfflineGatesHold(unittest.TestCase):
    """那道门是「别让桩把机器废话写进你自己的时间」，手动触发也不例外。"""

    def test_a_stub_engine_is_refused_even_when_forced(self):
        src = (ROOT / "core" / "offline.py").read_text(encoding="utf-8")
        tick = src[src.index("async def tick("):]
        tick = tick[:tick.index("\n    _STAT[\"tools\"] = []")]
        self.assertIn("engine_ok()", tick,
                      "engine_ok 得在 if not force 之外 —— 否则「真跑一场」会把回声诊断写进私密库")
        head = tick[:tick.index("if not force:")]
        self.assertIn("engine_ok()", head, "这一条要在 skip 之前判")

    def test_manual_run_endpoint_still_goes_through_tick(self):
        """`/api/offline/run` 不许自己另开一条绕过闸门的路。"""
        src = (ROOT / "core" / "views.py").read_text(encoding="utf-8")
        seg = src[src.index("/api/offline/run"):]
        seg = seg[:1200]
        self.assertIn("offline.tick(", seg)
        self.assertNotIn("run_session(", seg, "别绕过 tick 直接开会话")


class TestResidueRespectsTheMasterSwitch(unittest.TestCase):
    def test_turning_offline_off_stops_the_leak(self):
        src = (ROOT / "core" / "offline.py").read_text(encoding="utf-8")
        seg = src[src.index("def _wrapped(*a, **kw):"):]
        seg = seg[:seg.index("_wrapped._offline_wrapped")]
        self.assertIn("residue_text() if enabled()", seg,
                      "关掉之后残影不许再往正常聊天的提示词里渗")


class TestMachineTurnsAreNotYouComingBack(unittest.TestCase):
    """切空间 / 重新生成 / 接电话都会往 turns 里写 role='user' 的行 ——
    那不是「你回来了」。windows.active_sid 早就排除了，offline.last_seen 原来没有。"""

    def test_last_seen_ignores_spoken_zero_turns(self):
        from core import offline
        from core.store.sqlite import SqliteStore
        st = SqliteStore()
        st.db.execute("INSERT INTO turns(session_id,role,content,spoken,hidden,ts) "
                      "VALUES('main','user','机器拼的一句',0,1,?)", (9_999_999_999.0,))
        st.db.execute("INSERT INTO turns(session_id,role,content,spoken,hidden,ts) "
                      "VALUES('main','user','我真正说的',1,0,?)", (1_000_000_000.0,))
        st.db.commit()
        got = offline._db_user_ts()
        self.assertLess(got, 9e9, "机器那轮（spoken=0）不许顶掉「人最后说话的时间」")
        self.assertGreaterEqual(got, 1_000_000_000.0)

    def test_the_query_falls_back_for_old_databases(self):
        """老库万一没有 spoken 那一列，也得读得出来（宁可宽一点）。"""
        src = (ROOT / "core" / "offline.py").read_text(encoding="utf-8")
        seg = src[src.index("def _db_user_ts()"):]
        seg = seg[:seg.index("def _file_seen()")]
        self.assertIn("COALESCE(spoken,1)=1", seg)
        self.assertIn("WHERE role='user'\"", seg, "得留一句不带 spoken 的退路")


if __name__ == "__main__":
    unittest.main()
