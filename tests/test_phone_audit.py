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


class TestNoEmojiAndSelfDrawnIcons(unittest.TestCase):
    """★ 用户定的：**界面里一个 emoji 都不许有**，图标全是自绘细线。

    两条都查「会不会复发」而不是「现在长什么样」：
      · 代码（去掉注释之后）里不许出现 emoji 范围的字符
      · 每一处 nestIcon("名字") 的名字，图标模块里必须真有 —— 没有的话会**静默**
        退回一个小圆点（界面上看着像少了个图标，日志里什么都没有）
    """

    @staticmethod
    def _code_without_comments(text):
        t = re.sub(r"/\*[\s\S]*?\*/", "", text)
        t = re.sub(r"(?m)//.*$", "", t)
        t = re.sub(r"<!--[\s\S]*?-->", "", t)
        return t

    def test_no_emoji_anywhere_in_the_ui(self):
        bad = {}
        for f in NEST_FILES:
            code = self._code_without_comments((WEB / f).read_text(encoding="utf-8"))
            hits = re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]", code)
            if hits:
                bad[f] = "".join(sorted(set(hits)))
        self.assertEqual({}, bad, "这些文件里还有 emoji（换成 nestIcon）")

    def test_every_icon_name_used_really_exists(self):
        ic = (WEB / "nest-icon.js").read_text(encoding="utf-8")
        block = ic[ic.index("const P={"):ic.index("\n  };", ic.index("const P={"))]
        have = set(re.findall(r"^\s*([a-z][a-z0-9]*):\s*\"", block, re.M))
        self.assertGreater(len(have), 40, "图标集不该这么少")
        used = set()
        for f in NEST_FILES:
            code = self._code_without_comments((WEB / f).read_text(encoding="utf-8"))
            used |= set(re.findall(r'nestIcon(?:HTML)?\("([a-z0-9]+)"', code))
        self.assertTrue(used, "一个图标都没用上？")
        missing = used - have
        self.assertEqual(set(), missing, "用了图标集里没有的名字（会静默变成一个小圆点）")

    def test_icons_are_lines_not_emoji_or_blocks(self):
        ic = (WEB / "nest-icon.js").read_text(encoding="utf-8")
        self.assertIn('setAttribute("fill","none")', ic, "图标只许用线")
        self.assertIn('setAttribute("stroke","currentColor")', ic, "颜色跟着文字走")
        self.assertIn('"1.5"', ic, "线宽 1.5（这一套的统一手感）")


class TestThePhoneShell(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "nest.html").read_text(encoding="utf-8")
        self.tabs = (WEB / "nest-tabs.js").read_text(encoding="utf-8")
        self.all_js = _nest_text()

    def test_every_script_tag_points_at_a_real_file(self):
        for m in re.finditer(r'<script src="/([^"?]+)', self.html):
            self.assertTrue((WEB / m.group(1)).exists(), "少了这个文件：" + m.group(1))

    def test_the_six_rooms_are_in_the_agreed_order(self):
        """房间顺序是定下的：聊天 · 记忆 · 巢 · 书房 · 一起 · 我的（书房第 4、一起在它后面）。"""
        ids = self._tab_ids()
        self.assertEqual(["chat", "memory", "rooms", "study", "notes", "setting"], ids)
        self.assertNotIn("toys", ids, "玩具箱并进「一起」了，不再单独占一格")

    def test_the_toy_box_lives_inside_together(self):
        notes = (WEB / "nest-notes.js").read_text(encoding="utf-8")
        self.assertRegex(notes, r'"玩具"', "「一起」里得有玩具那一档")
        self.assertIn("NEST_PANES.toys", notes, "那一档得真把玩具箱画出来")

    @staticmethod
    def _tab_ids():
        js = (WEB / "nest-tabs.js").read_text(encoding="utf-8")
        block = js[js.index("const TABS=["):js.index("];", js.index("const TABS=["))]
        return re.findall(r'\["(\w+)","', block)

    def test_every_tab_has_somebody_implementing_it(self):
        ids = self._tab_ids()
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

    def test_the_shell_is_washi_and_foam(self):
        """外壳得真是这一套：和纸底、墨晕背景、海沫玻璃、宋体、月光版。"""
        for bit in ("--paper:#F2EDE2", "--ink-1:#6E8296", "--accent:#6E93B3",
                    "feTurbulence", "drift1", 'data-moon="1"', "backdrop-filter:blur(18px)"):
            self.assertIn(bit, self.html, bit)
        self.assertIn("Noto Serif SC", self.html, "标题那套宋体")
        # ★ 不引外部字体：手机上连不上时 <link> 会**阻塞渲染**，整页白等它超时
        self.assertNotIn("fonts.googleapis.com", self.html)
        self.assertNotIn("cdn.tailwindcss.com", self.html)

    def test_both_avatars_can_be_uploaded(self):
        skin = (WEB / "nest-skin2.js").read_text(encoding="utf-8")
        self.assertIn("nestIdent.save", skin)
        for who in ('"ai"', '"me"'):
            self.assertIn(who, skin, "他和我的都要能传")
        self.assertIn("/api/upload", skin)
        self.assertIn("paintAva", self.html, "顶栏那两颗圆头像")

    def test_the_palette_has_exactly_one_accent(self):
        """★ 用户定的色板：唯一强调色 #6E93B3，正文 / 次要 / 元信息 / 墨色都是定值。

        暖土金那一族（上一版的主色）**一个字节都不许留** —— 它们最容易从
        某个模块的老样式里悄悄长回来，而光看代码看不出来（只有一处也是花的）。
        """
        for bit in ("--tx-1:#46505C", "--tx-2:#7C8794", "--tx-3:#A7B0BB",
                    "--ink-1:#6E8296", "--ink-2:#55677C", "--ink-3:#93A6B8",
                    "--latin-c:#8A95A2", "--accent:#6E93B3"):
            self.assertIn(bit, self.html, bit)
        warm = re.compile(r"#(?:[Bb]8860[Bb]|[Cc]9[Aa]24[Aa]|[Bb][Cc]9[Aa]62|[Bb]07[Dd]3[Aa]|"
                          r"[Ee]0915[Cc]|[Cc]9[Aa]62)", re.I)
        for f in NEST_FILES:
            txt = (WEB / f).read_text(encoding="utf-8")
            self.assertIsNone(warm.search(txt), f + " 里还有暖土金那一族的颜色")

    def test_shadows_are_only_the_one_cool_shadow(self):
        """阴影只有 rgba(70,100,130,.10)：纯黑阴影、暖色阴影一律不许有。"""
        bad = {}
        for f in NEST_FILES:
            for m in re.finditer(r"box-shadow:\s*([^;\n}]+)", (WEB / f).read_text(encoding="utf-8")):
                v = m.group(1)
                if re.search(r"#000|rgba\(\s*0\s*,\s*0\s*,\s*0", v):
                    bad.setdefault(f, []).append(v.strip())
        self.assertEqual({}, bad, "这几处还是纯黑阴影")

    def test_the_ink_washes_are_three_by_three(self):
        """背景：3 团墨晕，每团外缘**恰好 3 层**内缩 0.5px、12% 的等高线。"""
        blobs = re.findall(r'<g class="blob drift\d"[^>]*>(.*?)</g>', self.html, re.S)
        self.assertEqual(3, len(blobs), "墨晕该是 3 团")
        for i, b in enumerate(blobs, 1):
            rings = [e for e in re.findall(r"<ellipse[^>]*>", b) if 'fill="none"' in e]
            self.assertEqual(3, len(rings), f"第 {i} 团外缘该有 3 层等高线")
            for r in rings:
                self.assertIn('stroke-width="0.5"', r)
                self.assertIn('opacity="0.12"', r)
        # 墨点 / 星屑：6~10 个、1~2px、20%、不闪
        g = re.search(r'<g fill="#6E8296" opacity="0\.20">(.*?)</g>', self.html, re.S)
        self.assertIsNotNone(g, "墨点那一组没了")
        specks = re.findall(r"<circle[^>]*>|<path[^>]*>", g.group(1))
        self.assertTrue(6 <= len(specks) <= 10, f"墨点/星屑该是 6~10 个，现在 {len(specks)}")
        for c in re.findall(r'<circle[^>]*r="([\d.]+)"', g.group(1)):
            self.assertTrue(1 <= float(c) <= 2, f"墨点半径 {c} 不在 1~2px")
        self.assertNotIn("animation", g.group(0), "墨点不许闪")

    def test_the_heart_is_a_notch_in_the_bottom_nav(self):
        """★ 聊天页那枚心：底部导航**正中间向上凸起 26px**，不许再压在输入框上。

        以前它是 `position:fixed` 到屏幕上、离底 54px —— 正好骑在输入框那一行上。
        现在它住在导航条里（#tabs 是 relative），靠 bottom:calc(100% - 26px) 探出半个身子。
        """
        self.assertIn("bottom:calc(100% - 26px)", self.html)
        fab = self.html[self.html.index("#newChatFab"):]
        self.assertNotIn("position:fixed", fab[:fab.index("}")], "心不许再 fixed 到屏幕上")
        self.assertIn("nav.append(fab)", self.tabs, "心得挂进导航条里")
        self.assertIn(".fab-slot", self.tabs, "正中间得给它留一格缺口，不然压住两格的字")
        # 输入框底下要留出那 26px，否则「不压在输入框上」只是句空话
        self.assertIn("calc(34px + env(safe-area-inset-bottom))", self.html)

    def test_the_memory_screen_has_a_hanging_line_index(self):
        """记忆页追加的「垂线索引」：细线垂下 → 末端小圆圈 → 旁边竖排标题 + 竖排日期。"""
        skin = (WEB / "nest-skin2.js").read_text(encoding="utf-8")
        for bit in (".tvi-line", ".tvi-node", ".tvi-title", ".tvi-date", "tideIndex"):
            self.assertIn(bit, skin, bit)
        self.assertIn("writing-mode:vertical-rl", skin, "标题 / 日期都得是竖排")
        self.assertIn('head.append(idx)', skin, "索引得真插进记忆页里")
        # 多条线长短不一 = 横向错落
        m = re.search(r"LINE_LEN=\[([\d,]+)\]", skin)
        self.assertIsNotNone(m, "得有一组长短不同的线")
        self.assertGreater(len(set(m.group(1).split(","))), 1, "线一样长就不叫错落了")

    def test_the_study_cover_is_a_seal_not_a_color_block(self):
        """书房封面：去掉大色块，改成一枚印章式的细线方框。"""
        study = (WEB / "nest-study.js").read_text(encoding="utf-8")
        cover = study[study.index(".st-cover{"):study.index(".st-title{")]
        self.assertNotIn("linear-gradient", cover, "封面不许再是大色块")
        self.assertNotIn("var(--accent)", cover, "封面不许用强调色铺底")
        self.assertIn("border:1px solid var(--ink-1)", cover, "得是细线方框")
        self.assertIn(".st-cover::after", study, "印章那味儿靠里面再收一圈线")

    def test_every_progress_bar_is_a_hairline(self):
        """所有进度条都是 1px 细线填充 —— 不许有 5px / 7px 的粗色块。"""
        for f, sel in (("nest-study.js", ".st-bar .track"), ("nest-notes.js", ".mo-row .track")):
            txt = (WEB / f).read_text(encoding="utf-8")
            line = next(l for l in txt.splitlines() if l.startswith(sel + "{"))
            self.assertIn("height:1px", line, f + " 的进度条还是粗的")
        skin2 = (WEB / "nest-skin2.js").read_text(encoding="utf-8")
        self.assertNotIn("border-radius:999px!important", skin2, "别再有胶囊墙")

    def test_the_memory_screen_has_the_tide_card(self):
        skin = (WEB / "nest-skin2.js").read_text(encoding="utf-8")
        self.assertIn("OUR TIDE", skin)
        self.assertIn("DAYS TOGETHER", skin)
        self.assertIn("/api/chat/heat", skin, "天数从真聊天记录算，不编")

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
