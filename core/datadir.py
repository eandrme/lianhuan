"""数据目录 —— 默认落点的**唯一**出处，而且**测试里绝不许落在真的家**。

★ 真机上撞的（0925）：一条测试用 `from core import server` 重新导入服务端，
  可 Python 给回的是**还绑着真库**的那个旧模块（`del sys.modules[...]` 不会把
  父包 `core` 上的那个属性删掉），于是 `set_setting("engine", "echo")` 写进了
  用户真正的家 —— 他接好的模型每跑一次测试就被打回回声，表现出来是
  「每次关掉页面重新打开都要再配一遍模型」，查了半天以为是前端没存住。

★ 所以：默认路径只在**这里**算，而且跑在 unittest 里时换成临时目录。
  显式给过 `LIANHUAN_DB` 的（真服务、android-full、各条测试自己的临时库）
  一律不动 —— 那是调用方明确指的，出了事它自己负责。

★ 不要用「文件在不在」当判据，也不要用 mtime：这里只认「是不是那个默认字符串」。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

#: 默认的家。跟历史上每一处写的都是同一个字符串。
DEFAULT = "data/lianhuan.db"

_test_home: Path | None = None


def under_test() -> bool:
    return "unittest" in sys.modules


def guard_default(p: Path) -> Path:
    """只拦一种：**默认路径 ＋ 跑在测试里 ＋ 没人显式指过**。

    ★ 拦下来之后顺手把 `LIANHUAN_DB` **钉成那个临时库** —— 这一跑里的其它模块
      （工具流水、私密库、上传目录…）也都跟着走到临时目录去，不会再有人
      悄悄写到真的家里。
    """
    global _test_home
    if not under_test():
        return p
    if str(p) not in (DEFAULT, "./" + DEFAULT):
        return p                       # 不是默认那个串 → 谁指的就听谁的
    env = (os.environ.get("LIANHUAN_DB") or "").strip()
    # ★ 只有「别人显式指过」才放行。**我们自己钉的那个临时库不算** ——
    #   不然闸门一开，后面某个调用方再写一遍 SqliteStore("data/lianhuan.db")
    #   就会大摇大摆落到真的家里去（这条差点又漏过去，是测试逼出来的）。
    if env and (not _test_home or env != str(_test_home)):
        return p
    if _test_home is None:
        _test_home = Path(tempfile.mkdtemp()) / "lianhuan.test.db"
        os.environ["LIANHUAN_DB"] = str(_test_home)
        print(f"[data] 测试里没指 LIANHUAN_DB —— 不碰真的家，改用 {_test_home}", flush=True)
    return _test_home


def home_db() -> Path:
    """那个库文件该落在哪儿。**默认值在测试里会被改到临时目录。**"""
    return guard_default(Path(os.environ.get("LIANHUAN_DB") or DEFAULT))


def home_dir() -> Path:
    """家的目录（secrets / uploads / files / 私密库 / 工具流水都住这儿）。"""
    return home_db().parent
