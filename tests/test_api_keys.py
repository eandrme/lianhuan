"""设置里的「API key 管理」—— 模型那两把钥匙要看得见、改得了、删得掉。

模型这一侧其实有**两把**钥匙（`core/server.py` 的 `ENGINE_SLOTS` 一处定义）：
  · OpenAI 兼容那一大票（DeepSeek / Kimi / 智谱 / 硅基流动 / Ollama…）→ api_key
  · Claude（不是 OpenAI 兼容的形状）→ anthropic_key

原来的两个缺口，正是用户要这个功能的原因：
  ① `/api/engine/config` 只报**当前选中那个引擎**的 key_set/key_tail ——
     所以另一把填没填，界面上永远看不到（「我要看到我之前添加的那两个 key」）；
  ② 那个 POST 每个字段都是 `if v: sec[dst] = v`，**空值直接跳过** ——
     填过的 key 没有任何办法拿掉，只能上服务器手改 secrets.json。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WEB = ROOT / "core" / "web"


def _client():
    from fastapi.testclient import TestClient
    import core.server as sv
    return TestClient(sv.app), sv


class _KeysCase(unittest.TestCase):
    """★ 别去动 LIANHUAN_DB。

    第一版在这里 set/pop 那个环境变量，结果把 `core.offline._DB` 这种
    **import 期算死的常量**冻在了本用例的临时目录上 —— 后面的用例
    （test_attach_and_offline_guards 那条「机器轮不算你回来了」）读到 0.0，
    单独跑却好好的。测试之间不该靠环境变量串味。
    走 datadir 自带的那套隔离（不设 LIANHUAN_DB，它就换到 /tmp 的测试库）就够，
    要收拾的只有 secrets.json 这个**共享文件**：进来先存一份，出去原样还回去。
    """

    def setUp(self):
        self.c, self.sv = _client()
        self.sec_path = Path(self.sv.SECRETS)
        self._bak = self.sec_path.read_text(encoding="utf-8") if self.sec_path.exists() else None
        self._env = {k: os.environ.pop(k, None)
                     for k in ("LIANHUAN_API_KEY", "LIANHUAN_ANTHROPIC_KEY")}

    def tearDown(self):
        # ① secrets.json 原样还回去（里面有别的用例可能要用的东西）
        if self._bak is None:
            try:
                self.sec_path.unlink()
            except FileNotFoundError:
                pass
        else:
            self.sec_path.write_text(self._bak, encoding="utf-8")
        # ② 环境变量也还回去
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestBothSlotsAreVisible(_KeysCase):

    def test_the_response_lists_two_slots(self):
        j = self.c.get("/api/engine/config").json()
        self.assertIn("slots", j, "得有两个槽位，不然界面上只看得见当前那一个")
        engines = [s["engine"] for s in j["slots"]]
        self.assertEqual(["api", "anthropic"], engines)
        for s in j["slots"]:
            for f in ("label", "key_set", "key_tail", "from", "base", "model"):
                self.assertIn(f, s, f)

    def test_a_key_put_into_either_slot_shows_up(self):
        c = self.c
        c.post("/api/engine/config", json={"engine": "api", "base": "https://api.deepseek.com",
                                           "model": "deepseek-chat", "key": "sk-aaaabbbbcccc1234"})
        c.post("/api/engine/config", json={"engine": "anthropic", "base": "https://api.anthropic.com",
                                           "model": "claude-sonnet-5", "key": "sk-ant-zzzzyyyy5678"})
        slots = {s["engine"]: s for s in c.get("/api/engine/config").json()["slots"]}
        self.assertTrue(slots["api"]["key_set"])
        self.assertTrue(slots["anthropic"]["key_set"], "另一把也要看得见，哪怕当前引擎不是它")
        self.assertEqual("1234", slots["api"]["key_tail"])
        self.assertEqual("5678", slots["anthropic"]["key_tail"])
        self.assertEqual("local", slots["api"]["from"])

    def test_the_plaintext_key_never_goes_out(self):
        c = self.c
        c.post("/api/engine/config", json={"engine": "api", "key": "sk-SECRETSECRET9999"})
        raw = json.dumps(c.get("/api/engine/config").json(), ensure_ascii=False)
        self.assertNotIn("SECRETSECRET", raw, "只回末四位，明文一个字都不许出去")
        self.assertIn("9999", raw)


class TestKeysCanBeDeleted(_KeysCase):

    def test_clear_key_removes_exactly_that_slot(self):
        c = self.c
        c.post("/api/engine/config", json={"engine": "api", "base": "https://a.example",
                                           "model": "m1", "key": "sk-first-key-1111"})
        c.post("/api/engine/config", json={"engine": "anthropic", "base": "https://b.example",
                                           "model": "m2", "key": "sk-second-key-2222"})
        r = c.post("/api/engine/config", json={"engine": "anthropic", "clear_key": True})
        self.assertTrue(r.json().get("ok"))
        slots = {s["engine"]: s for s in c.get("/api/engine/config").json()["slots"]}
        self.assertFalse(slots["anthropic"]["key_set"], "清掉的那把该是空的")
        self.assertFalse(slots["anthropic"]["base"], "base/model 也一起清")
        self.assertTrue(slots["api"]["key_set"], "★ 另一把不许被误伤")
        self.assertEqual("1111", slots["api"]["key_tail"])

    def test_the_file_on_disk_really_loses_the_key(self):
        c, sv = self.c, self.sv
        c.post("/api/engine/config", json={"engine": "api", "key": "sk-todelete-3333"})
        c.post("/api/engine/config", json={"engine": "api", "clear_key": True})
        sec = json.loads(Path(sv.SECRETS).read_text(encoding="utf-8"))
        self.assertNotIn("api_key", sec, "secrets.json 里也要真没了，不能只在接口层装样子")

    def test_an_empty_key_alone_still_does_not_wipe_anything(self):
        """老语义要保住：**不带 clear_key 时，空 key 只是「不改」。**"""
        c = self.c
        c.post("/api/engine/config", json={"engine": "api", "key": "sk-keepme-4444"})
        c.post("/api/engine/config", json={"engine": "api", "key": ""})
        slots = {s["engine"]: s for s in c.get("/api/engine/config").json()["slots"]}
        self.assertTrue(slots["api"]["key_set"], "空 key 不该把已经存着的那把清掉")


class TestTheSettingsSection(unittest.TestCase):
    def setUp(self):
        self.js = (WEB / "nest-setting.js").read_text(encoding="utf-8")

    def test_there_is_a_section_and_it_is_registered(self):
        self.assertIn("secApiKeys", self.js)
        self.assertIn("secApiKeys(box)", self.js, "得真挂进「我的」那一页")
        self.assertIn('id="keys-sec"', self.js)

    def test_it_reads_the_two_slots_and_offers_edit_and_delete(self):
        seg = self.js[self.js.index("async function secApiKeys("):]
        seg = seg[:seg.index("async function secEngine(")]
        self.assertIn("/api/engine/config", seg)
        self.assertIn("j.slots", seg, "得用新加的 slots，不能只看当前引擎那一把")
        self.assertIn("clear_key", seg, "「删掉」要发 clear_key")
        self.assertIn("confirm(", seg, "删之前要问一句")
        self.assertIn('type="password"', seg, "新 key 用密码框输入")

    def test_it_does_not_offer_to_delete_an_env_key(self):
        """环境变量那份 app 删不掉 —— 那就别给一个按了没用的「删」。"""
        seg = self.js[self.js.index("async function secApiKeys("):]
        seg = seg[:seg.index("async function secEngine(")]
        self.assertIn('sl.from!=="env"', seg)
        self.assertIn("环境变量", seg)


if __name__ == "__main__":
    unittest.main()
