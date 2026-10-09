"""小手机排查 —— 把「手机上整台机器」当一件事来查，而不是一次看一眼某个页面。

这里查的都是**会自动复发、而且光看代码看不出来**的那几类：
  ① 前端引用了服务端**根本没有**的接口（点了才知道坏，而且只在某个分档里）
  ② 某个 <script src> 指向一个不存在的文件（那个模块整个不生效，页面照常打开）
  ③ 某个标签页没人实现（点进去看见「下一批接上」那种占位）
  ④ 「加到主屏」那一套缺件（iOS 只认 apple-*；图标不带 cookie 抓不到就变网页截图）
  ⑤ 底部标签栏被整屏面板盖住 / 压在手势条底下；输入框小于 16px 让 iOS 把整页放大
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
NEST_FILES = ("nest.html",) + tuple(sorted(p.name for p in WEB.glob("nest-*.js")))


def _nest_text() -> str:
    return "\n".join((WEB / f).read_text(encoding="utf-8") for f in NEST_FILES)


class TestEveryCallHasADoor(unittest.TestCase):
    """前端喊的每一条 /api，服务端都得真有那道门。"""

    @classmethod
    def setUpClass(cls):
        import core.server as sv
        cls.paths = sorted(sv.app.openapi().get("paths", {}))

    @staticmethod
    def _norm(p: str):
        """把前端那种拼出来的路径切成前缀。返回 (前缀, 是不是拼的)。"""
        # 结尾是 "/" 的，一定是拼出来的（这个应用的完整路由不会以 / 收尾）
        cut = p.rstrip("?").split("?")[0].endswith("/") or bool(
            re.search(r'\$\{', p))
        head = re.split(r'\$\{', p.split("?")[0])[0]
        head = re.split(r'["\'`+]', head)[0].rstrip("/")
        return head, cut

    def _exists(self, raw: str) -> bool:
        head, cut = self._norm(raw)
        if not head or head == "/api":
            return True
        for r in self.paths:
            rx = "^" + re.sub(r"\{[^}]+\}", "[^/]+", r).replace(":path", ".*") + "$"
            if re.match(rx, head):                      # 直接命中（含 /api/moments/{id}/del 这种）
                return True
            if cut and r.startswith(head + "/"):         # 拼出来的：是某条真路由的前缀
                return True
        return False

    def test_no_dead_endpoint_in_the_nest_ui(self):
        pat = re.compile(r'["\'`](/api/[A-Za-z0-9_\-/{}$.:]*)')
        missing = {}
        for f in NEST_FILES:
            for i, line in enumerate((WEB / f).read_text(encoding="utf-8").splitlines(), 1):
                for m in pat.finditer(line):
                    if not self._exists(m.group(1)):
                        missing.setdefault(m.group(1), []).append(f"{f}:{i}")
        self.assertEqual({}, missing, "这些接口前端在喊，服务端没有")


class TestThePhoneShell(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "nest.html").read_text(encoding="utf-8")
        self.tabs = (WEB / "nest-tabs.js").read_text(encoding="utf-8")
        self.all_js = _nest_text()

    def test_every_script_tag_points_at_a_real_file(self):
        for m in re.finditer(r'<script src="/([^"?]+)', self.html):
            self.assertTrue((WEB / m.group(1)).exists(), "少了这个文件：" + m.group(1))

    def test_every_tab_has_somebody_implementing_it(self):
        ids = re.findall(r'\["(\w+)","[^"]*","[^"]*"\]', self.tabs)
        self.assertIn("notes", ids)
        for k in ids:
            if k == "chat":
                # 聊天那一格不用面板：`go("chat")` 就是把面板收起来
                self.assertIn('k==="chat"', self.tabs)
                continue
            self.assertRegex(self.all_js, r'NEST_PANES\.' + k + r'\s*=',
                             f"「{k}」这一格没人实现，点进去只会看见占位")

    def test_the_home_screen_block_is_complete(self):
        """★ iOS 加到主屏时只认 apple-*，而且**抓图标那一下不一定带 cookie**。"""
        for bit in ('rel="apple-touch-icon"', 'rel="manifest"', "apple-mobile-web-app-capable",
                    "apple-mobile-web-app-title", "icon-180.png"):
            self.assertIn(bit, self.html, bit)
        import core.gate as gate
        for p in ("/icons/", "/manifest.json", "/favicon.ico", "/sw.js"):
            self.assertTrue(gate.public_asset(p), p + " 得能不带 cookie 拿到")
        self.assertFalse(gate.public_asset("/api/memories"), "别把 API 也放出去了")

    def test_the_bottom_bar_stays_reachable_and_above_the_gesture_bar(self):
        # ① 面板不许盖住标签栏（盖住了就只能先按 ✕ 回聊天才能换格子）
        self.assertRegex(self.tabs, r"#pane\{position:fixed;inset:0 0 var\(--nest-tabs-h")
        self.assertIn("--nest-tabs-h", self.tabs, "得有人把标签栏的高度量出来")
        self.assertIn("measure()", self.tabs)
        # ★ 开局 #app 是 hidden（口令那关），那会儿量出来是 0 —— 必须进站后再量一次。
        #   jsdom 不做排版，所以这条只能盯那个「再量一次」的钩子在不在。
        self.assertIn('attributeFilter:["hidden"]', self.tabs,
                      "得在 #app 显示出来之后再量一次，不然 --nest-tabs-h 永远是 0")
        # ② 手势条让位
        self.assertIn("env(safe-area-inset-bottom)", self.html)
        self.assertIn("env(safe-area-inset-bottom)", self.html.split("#composer")[1][:400],
                      "输入框那一条也要让")

    def test_form_controls_are_sixteen_pixels(self):
        """小于 16px 的输入框会让 iOS 把整页放大，而且不缩回去。"""
        self.assertRegex(self.html, r"input,textarea,select\{font-size:16px")

    def test_the_viewport_handles_the_keyboard_and_the_notch(self):
        self.assertIn("viewport-fit=cover", self.html)
        self.assertIn("interactive-widget=resizes-content", self.html,
                      "安卓键盘弹出时要缩小可视区，而不是盖住输入框")

    def test_the_three_new_sections_are_reachable(self):
        notes = (WEB / "nest-notes.js").read_text(encoding="utf-8")
        for k in ("空间", "时间线", "收藏"):
            self.assertIn(f'"{k}"', notes)
        for api in ("/api/moments", "/api/timeline", "/api/chat/starred"):
            self.assertIn(api, notes)
        # 记事里每一样都要能收拾（用户定的那条），空间 / 时间线也不例外
        for api in ("/api/moments/", "/api/timeline/"):
            self.assertIn(api + '"+x.id+"/edit', notes)
            self.assertIn(api + '"+x.id+"/del', notes)

    def test_messages_can_actually_be_starred(self):
        """收藏得有入口，而且收藏完要真写进库（不是只在界面上点个亮）。"""
        self.assertIn("doStar", self.html)
        self.assertIn("/star", self.html)
        self.assertIn("markStar", self.html)
        self.assertIn("it.starred", self.html, "翻历史时收藏过的那句也得亮着星")


if __name__ == "__main__":
    unittest.main()
