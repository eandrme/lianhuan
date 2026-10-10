"""删对话窗口那颗按钮。

用户要的：「加一个可以删除对话窗口的按钮」。

★ 查下来后端那道门**一直就有**（`POST /api/nest/thread/del`），
  前端也有一份带「删」的窗口列表 —— 可它的入口早就没了：
  `nest-threads.js` 那个列表靠拦 `#bar .ibtn`（title 是「新对话」）才打得开，
  而那颗按钮在底部导航条撤掉之后搬进了抽屉，拦截永远不触发。
  于是人看到的是 `nest-tabs.js` 那份**没有删按钮**的列表，找不到地方删。

  现在只有一份列表（`nest-tabs.js` 的 `threadsInto`），抽屉 / 主界面中间那颗 HOME /
  「巢」那一格走的都是它，删按钮就在每一行右边。
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WEB = ROOT / "core" / "web"


class TestTheButtonExists(unittest.TestCase):
    def setUp(self):
        self.tabs = (WEB / "nest-tabs.js").read_text(encoding="utf-8")

    def test_the_shared_window_list_has_a_delete_button(self):
        self.assertIn("thr-del", self.tabs, "窗口列表每一行右边要有颗删按钮")
        self.assertRegex(self.tabs, r'nestIcon\("trash"', "用画出来的线稿垃圾桶，不用字形")
        # 44×44：手机上按得着
        self.assertRegex(self.tabs, r"\.thr \.thr-del\{[^}]*width:44px;height:44px")

    def test_it_calls_the_endpoint_that_already_existed(self):
        self.assertIn('jpost("/api/nest/thread/del",{sid:it.sid})', self.tabs)
        # nest-tabs.js 原来没有 jpost —— 补的那个也得看状态码，不能只看 body
        self.assertIn("const jpost=", self.tabs)
        self.assertIn("!r.ok||!d||d.ok===false", self.tabs,
                      "老服务端回 404 的 {\"error\":…} 里没有 ok 字段，只看 body 会当成存上了")

    def test_it_does_not_switch_windows_when_you_only_wanted_to_delete(self):
        """点删不能顺手把窗口切过去 —— 行本身是「点一下切过去」的。"""
        seg = self.tabs[self.tabs.index("const dx=el(\"button\",\"thr-del\""):]
        seg = seg[:seg.index("r.append(dx)")]
        self.assertIn("e.stopPropagation()", seg)
        self.assertIn("e.preventDefault()", seg)


class TestItIsSafe(unittest.TestCase):
    def setUp(self):
        self.tabs = (WEB / "nest-tabs.js").read_text(encoding="utf-8")
        self.del_fn = self.tabs[self.tabs.index("async function delThread("):]
        self.del_fn = self.del_fn[:self.del_fn.index("async function threadsInto(")]

    def test_the_main_window_is_not_deletable(self):
        """主窗口是旧记录，后端也拦着 —— 前端别去换那句拒绝，一开始就拦下。"""
        self.assertIn('it.sid==="main"', self.del_fn)
        self.assertIn("主窗口是老记录", self.del_fn)
        # 而且那颗按钮要画成灰的，一眼看得出删不了
        self.assertIn('it.sid==="main"?" off":""', self.tabs)
        self.assertRegex(self.tabs, r"\.thr \.thr-del\.off\{[^}]*opacity")

    def test_it_asks_first(self):
        self.assertIn("confirm(", self.del_fn)

    def test_deleting_the_current_window_falls_back_to_main(self):
        """★ 不退回的话，会话 id 还指着一扇不存在的窗 ——
        下一条主动消息会拿这个 id 重新落库，那扇窗**又冒出来了**，人会以为没删掉。"""
        self.assertIn("if(it.sid===getSid())", self.del_fn)
        idx = self.del_fn.index("if(it.sid===getSid())")
        seg = self.del_fn[idx:idx + 700]
        self.assertIn('setSid("main")', seg, "本地会话 id 要退回主窗口")
        self.assertIn('"/api/nest/focus"', seg, "后端的 focus 也要拨回 main")
        self.assertIn("renderThread()", seg, "聊天气泡要重画成主窗口的")

    def test_the_list_refreshes_after_deleting(self):
        self.assertIn("await reload()", self.del_fn)
        self.assertIn("async function load()", self.tabs)


class TestThereIsOnlyOneWindowList(unittest.TestCase):
    """两份列表就是这次「按钮找不到」的根子 —— 别再长出第二份。"""

    def test_nest_threads_no_longer_has_its_own_list(self):
        th = (WEB / "nest-threads.js").read_text(encoding="utf-8")
        self.assertNotIn("async function openThreads", th, "那份列表已经删了")
        self.assertNotIn("thr2", th, "它专用的样式也一并清了")
        # 它真正管的那件事还在
        self.assertIn("async function regen(", th, "「重新生成」不许被误伤")
        self.assertIn("async function renderThread(", th)

    def test_every_entry_point_goes_through_the_shared_list(self):
        tabs = (WEB / "nest-tabs.js").read_text(encoding="utf-8")
        self.assertIn("window.nestOpenThreads=openThreads", tabs)
        self.assertIn('barBtn("window","对话窗口",openThreads', tabs)
        self.assertIn("await threadsInto(holder, null)", tabs, "「巢」那一格也用同一份")
        # 主界面中间那颗 HOME 就是开的这个
        home = (WEB / "nest-home.js").read_text(encoding="utf-8")
        self.assertIn("window.nestOpenThreads", home)

    def test_the_dead_interceptor_is_gone(self):
        """原来靠拦 `#bar .ibtn[title=新对话]` 打开自己那份列表 —— 那颗按钮早搬走了。"""
        th = (WEB / "nest-threads.js").read_text(encoding="utf-8")
        self.assertNotIn('#bar .ibtn', th)


class TestTheBackendDoor(unittest.TestCase):
    def test_the_endpoint_still_refuses_main(self):
        src = (ROOT / "core" / "views.py").read_text(encoding="utf-8")
        seg = src[src.index('@router.post("/api/nest/thread/del")'):]
        seg = seg[:seg.index("@router.get")]
        self.assertIn('if sid == "main"', seg)
        self.assertIn("DELETE FROM turns WHERE TRIM(session_id)=?", seg)
        self.assertIn("commit()", seg, "删完要落库")


if __name__ == "__main__":
    unittest.main()
