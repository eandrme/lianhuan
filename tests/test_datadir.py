"""默认数据目录那道闸 —— **测试绝不许写进用户真正的家**。

★ 真机上撞的（0925）：一条测试用「删 sys.modules 再 import」来换库，可那换不动 ——
  `del sys.modules["core.server"]` 不会删掉父包 `core` 上的属性，`from core import server`
  拿回的还是**绑着真库**的旧模块，于是 `set_setting("engine", "echo")` 写进了用户真正的家：
  他接好的模型每跑一次测试就被打回回声，表现出来是「每次关掉页面重新打开都要再配一遍」。
  （同一时期还漏过：工具流水写进真家的 data/tool_calls.jsonl、VAPID 私钥、
   私密库、上传目录 —— 都从「谁先 import 谁说了算」那条路上漏的。）
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import datadir                                          # noqa: E402


class TestTheDefaultHomeIsGuarded(unittest.TestCase):
    def test_under_unittest_the_default_is_not_the_real_home(self):
        p = datadir.home_db()
        self.assertNotEqual(datadir.DEFAULT, str(p),
                            "跑测试时默认路径绝不许是用户真正的那个库")
        self.assertTrue(str(p).startswith(tempfile.gettempdir()), str(p))

    def test_a_store_built_without_a_path_does_not_land_in_the_real_home(self):
        from core.store.sqlite import SqliteStore
        s = SqliteStore()
        self.assertNotEqual(Path(datadir.DEFAULT).resolve(), s.path.resolve())
        s2 = SqliteStore("data/lianhuan.db")          # 显式写成默认串也一样拦
        self.assertNotEqual(Path(datadir.DEFAULT).resolve(), s2.path.resolve())

    def test_an_explicit_path_is_left_alone(self):
        """测试自己的临时库、android-full 的库、真服务的库 —— 一律不许被改道。"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mine.db"
            from core.store.sqlite import SqliteStore
            self.assertEqual(p, SqliteStore(p).path)
            self.assertEqual(p, datadir.guard_default(p))

    def test_an_explicit_env_var_wins(self):
        old = os.environ.get("LIANHUAN_DB")
        os.environ["LIANHUAN_DB"] = "/tmp/somewhere-else.db"
        try:
            self.assertEqual(Path("/tmp/somewhere-else.db"), datadir.home_db(),
                             "显式指过就听它的（这时出事是调用方自己负责）")
        finally:
            if old is None:
                os.environ.pop("LIANHUAN_DB", None)
            else:
                os.environ["LIANHUAN_DB"] = old

    def test_outside_tests_the_default_is_untouched(self):
        """真服务那条路一个字不改：不是测试进程时，默认还是 data/lianhuan.db。"""
        old = datadir.under_test
        datadir.under_test = lambda: False
        try:
            self.assertEqual(datadir.DEFAULT, str(datadir.guard_default(Path(datadir.DEFAULT))))
        finally:
            datadir.under_test = old


class TestTheHomeWritersGoThroughTheGuard(unittest.TestCase):
    """会往家里写东西的那几处，路径都得从 datadir 来（现算），不许自己拼。"""

    CASES = [
        ("core/store/sqlite.py", "datadir.guard_default", "那个库"),
        ("core/server.py", "_datadir.home_dir()", "secrets / uploads / files"),
        ("core/hands.py", "datadir", "工具流水"),
    ]

    def test_writers_use_the_guard(self):
        for rel, needle, what in self.CASES:
            src = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(needle, src, f"{rel} 里的{what}没走 datadir")

    def test_nobody_re_derives_the_default_path_by_hand(self):
        """谁都不许再自己写一遍 `os.environ.get("LIANHUAN_DB", "data/lianhuan.db")`。

        ★ 那条路绕开闸门 —— 真机上就是这么把东西写进用户家里的。"""
        bad = []
        for p in list((ROOT / "core").rglob("*.py")) + list((ROOT / "optional").rglob("*.py")):
            # ★ 只认真文件：这个仓库里 core/toollog.py 是个**目录**（历史遗留），
            #   rglob 会把它也捞出来，读它当场 IsADirectoryError。
            if not p.is_file() or "__pycache__" in str(p) or "/vendor/" in str(p):
                continue
            if p.name == "datadir.py":
                continue
            if 'os.environ.get("LIANHUAN_DB", "data/lianhuan.db")' in p.read_text(encoding="utf-8"):
                bad.append(str(p.relative_to(ROOT)))
        self.assertEqual([], bad, "这些地方还在自己拼默认路径：" + "、".join(bad))


if __name__ == "__main__":
    unittest.main()
