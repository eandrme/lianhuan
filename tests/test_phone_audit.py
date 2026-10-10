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

    def test_there_is_no_bottom_bar_and_the_gesture_bar_is_still_cleared(self):
        """★ 用户定的：**底部导航条整条撤掉**，入口全部平铺到主界面上。

        撤掉之后有三件事必须仍然成立，不然手机上会变成一座迷宫：
          · 面板铺满整屏（原来底下要给标签栏让一格 --nest-tabs-h）
          · 手势条还得让位，不然输入框压在那条小白条底下
          · 从聊天回得去主界面（底栏没了，原来那条路也断了）
        """
        # ① 不许再建那排六格，也不许再有那颗凸起的心
        for bad in ("nav.id=\"tabs\"", "id=\"tabs\"", "newChatFab", "fab-slot"):
            self.assertNotIn(bad, self.tabs, "底部导航条该撤干净了：" + bad)
        self.assertNotIn("#tabs", self.html)
        # ② 面板铺满整屏
        self.assertRegex(self.tabs, r"#pane\{position:fixed;inset:0;")
        # ③ 手势条让位
        self.assertIn("env(safe-area-inset-bottom)", self.html)
        self.assertIn("env(safe-area-inset-bottom)", self.html.split("#composer")[1][:400],
                      "输入框那一条也要让")
        # ④ 回主界面的路：聊天顶栏那颗 house + 抽屉第一条
        self.assertIn("btnHome", self.tabs)
        self.assertIn('go("home")', self.tabs)
        self.assertIn('["home","home","主界面","HOME"]', self.tabs, "抽屉第一条得是主界面")

    def test_every_view_is_reachable_through_the_router(self):
        """底栏撤了之后，跳转只有一条路：window.nestGo。谁都不许再去找那排按钮。"""
        self.assertIn("window.nestGo=go", self.tabs)
        self.assertIn("window.nestView=", self.tabs)
        # ★ 注释里提到那个老写法是可以的（那是在讲「别再这么干」），
        #   所以先把注释去掉再查 —— 跟 emoji 那两条同一个规矩。
        strip = TestNoEmojiAndSelfDrawnIcons._code_without_comments
        for dead in ('#tabs button[data-tab=', "querySelector('#tabs"):
            for f in NEST_FILES:
                self.assertNotIn(dead, strip((WEB / f).read_text(encoding="utf-8")),
                                 f + " 还在按已经不存在的那排按钮导航")
        # 五个可切换视图（主界面 + 记忆详情 + 一起 + 书房 + 时间线）都得有人实现
        alljs = _nest_text()
        for k in ("home", "memory-detail", "together", "study", "timeline"):
            self.assertIn('NEST_PANES["%s"]' % k if k == "memory-detail" else "NEST_PANES.%s" % k,
                          alljs, "「%s」这一页没人画" % k)

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

    def test_the_home_page_is_the_front_door(self):
        """★ 主界面：顶部身份栏 + 天数区 + 一路铺下来的卡片，卡片之间用细线串着。

        ☰ 拉抽屉 · 中间那颗 HOME（点了去挑对话窗口）· ⚙ 进设置。
        """
        home = (WEB / "nest-home.js").read_text(encoding="utf-8")
        for bit in ('el("div","hm-top")', "nestIcon(\"menu\"", "nestIcon(\"setting\"",
                    "nestOpenThreads", "hm-days", "hm-thread", "hm-wrap"):
            self.assertIn(bit, home, bit)
        # ① 天数区：SINCE · yy/mm/dd、大数字、一行说明
        self.assertIn('"SINCE · "', home)
        self.assertIn("sinceShort", home)
        self.assertIn("我们一起走过的日子", home)
        # 大数字 88px / 字重 500（定稿的尺寸）
        self.assertRegex(home, r"\.hm-days \.num\{[^}]*font-size:88px")
        self.assertRegex(home, r"\.hm-days \.num\{[^}]*font-weight:500")
        # 数字右上角那枚 12px 的淡墨点必须是**画出来的**（界面里不许有 ✦ 字形）
        self.assertIn("sparkle(12", home)
        self.assertIn('p.setAttribute("d","M12 2.6', home)
        # ② 卡片之间的细线：0.5px、rgba(110,130,150,.25)
        self.assertRegex(home, r"\.hm-thread \.ln\{width:\.5px")
        self.assertIn("rgba(110,130,150,.25)", home)
        # ③ 一段一段铺下来：记忆 / 一起 / 日历·书房 / 时间线 / 空间
        for bit in ("memBlock", "togetherBlock", "twoCol", "timelineBlock", "spaceBlock"):
            self.assertIn(bit, home, "主界面上少了这一块：" + bit)

    def test_the_memory_index_is_a_horizontal_snap_strip(self):
        """主界面上的 MEMORY INDEX：横向 scroll-snap，每张卡里一条垂线 + 节点 +
        竖排标题 + 竖排元信息；线长各不相同，所以一排看过去是错落的。"""
        home = (WEB / "nest-home.js").read_text(encoding="utf-8")
        for bit in (".hm-mcard", ".hm-mline", ".hm-mnode", ".hm-mtitle", ".hm-mmeta",
                    "scroll-snap-type:x mandatory", "/api/memory/all"):
            self.assertIn(bit, home, bit)
        # 卡宽 150 / 高 210 / 间距 14，滑到边缘露出下一张的一半
        self.assertRegex(home, r"\.hm-mcard\{flex:0 0 150px;width:150px;height:210px")
        self.assertRegex(home, r"\.hm-scroll\{display:flex;gap:14px")
        # 竖排（标题 + 元信息都竖着写）
        self.assertRegex(home, r"\.hm-mtitle\{writing-mode:vertical-rl")
        self.assertRegex(home, r"\.hm-mmeta\{writing-mode:vertical-rl")
        # 线长循环 60/100/140/80 —— 多条线长短不一才叫错落
        m = re.search(r"LINE_LEN=\[([\d,]+)\]", home)
        self.assertIsNotNone(m, "得有一组长短不同的线")
        self.assertEqual(["60", "100", "140", "80"], m.group(1).split(","))
        # 点一张卡 → 记忆详情
        self.assertIn('go("memory-detail",it.id)', home)
        # 节点：7px 圆 + 1px 描边 + 中心 0.8px 实心点
        self.assertRegex(home, r"\.hm-mnode\{[^}]*width:7px;height:7px")
        self.assertRegex(home, r"\.hm-mnode::after\{[^}]*width:\.8px;height:\.8px")

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

    def test_the_tide_card_lives_on_the_home_page(self):
        """OUR TIDE 现在是主界面上那张卡：两个头像交叠、陪伴天数、名字、一句诗、since。"""
        home = (WEB / "nest-home.js").read_text(encoding="utf-8")
        self.assertIn("OUR TIDE", home)
        self.assertIn("days of tides together", home)
        self.assertIn("/api/chat/heat", home, "天数从真聊天记录算，不编")
        self.assertIn("Love Like Foam Upon the Sea", home)
        # 两个 64px 圆头像，左白玻璃描边、右冰蓝底，交叠一点点
        self.assertRegex(home, r"\.hm-ava\{[^}]*width:64px;height:64px")
        self.assertRegex(home, r"\.hm-ava\.me\{[^}]*margin-left:-16px")
        self.assertIn("var(--foam-2", home)
        # 中间那条 56px 细横线
        self.assertRegex(home, r"\.hm-tide \.rule\{width:56px;height:1px")

    def test_the_together_page_is_a_three_column_feed(self):
        """一起页：引用块 + 下拉 + 标签行 + 日报 + 日期/总数 + 三列信息流。

        ★「不改功能」：原来那十一档的完整界面一个都没删，顶栏「分区」按一下就进去。
        """
        tg = (WEB / "nest-together.js").read_text(encoding="utf-8")
        # ① 引用块：左侧一条 2px accent 竖线 + 斜体正文
        self.assertRegex(tg, r"\.tg-quote::before\{[^}]*width:2px")
        self.assertRegex(tg, r"\.tg-quote\{[^}]*font-style:italic")
        self.assertIn("var(--accent)", tg)
        # ③ 一个下拉 + ④ 标签行（横向可滑，选中态才 accent）
        self.assertIn("el(\"select\")", tg)
        for c in ("全部", "梗库", "表情包", "健康", "收藏", "玩具", "日记", "碎碎念"):
            self.assertIn('"%s"' % c, tg, c)
        self.assertRegex(tg, r"\.tg-chips\{[^}]*overflow-x:auto")
        self.assertRegex(tg, r"\.tg-chips button\.on\{[^}]*color:var\(--accent\)")
        # ⑤ 居中一枚日报
        self.assertIn("日报", tg)
        self.assertRegex(tg, r"\.tg-daily\{[^}]*justify-content:center")
        # ⑥ 一行：左中文日期 · 右 No. n
        self.assertIn("zhDay", tg)
        self.assertIn('"NO. "+rows.length', tg)
        # ⑦ 三列：品类 68px / 内容 / 时间右对齐
        self.assertRegex(tg, r"\.tg-row \.cat\{[^}]*flex:0 0 68px")
        self.assertRegex(tg, r"\.tg-row \.tx\{[^}]*font-size:15px")
        self.assertRegex(tg, r"\.tg-row \.tm\{[^}]*text-align:right")
        self.assertRegex(tg, r"\.tg-row\{[^}]*border-bottom:1px solid rgba\(110,130,150,\.22\)")
        # 十一档一个都没少
        self.assertIn("nestNotesOpen", tg)
        self.assertIn("十一档", tg)

    def test_the_study_page_is_a_shelf_of_book_spines(self):
        """书房页：一排竖立的书脊（高低不一、底纹各异）+ 底下一条隔板。"""
        st = (WEB / "nest-study.js").read_text(encoding="utf-8")
        # ① 页头
        for bit in ("THE STUDY", '"书房"', "一起做事的房间。"):
            self.assertIn(bit, st, bit)
        self.assertRegex(st, r"\.st-h1\{[^}]*font-size:32px")
        # ② 右上角那枚手绘感空心星星：1px 描边、12px、转 15°
        self.assertIn("nestIcon(\"star\",12)", st)
        self.assertRegex(st, r"\.st-star\{[^}]*transform:rotate\(15deg\)")
        self.assertRegex(st, r"\.st-star svg\{stroke-width:1\}")
        # ③ 书脊：56 宽、圆角 4、1px 描边、四种高度、顶部 8px 书头
        self.assertRegex(st, r"\.st-spine\{[^}]*width:56px;flex:0 0 56px;border-radius:4px")
        self.assertIn("rgba(110,130,150,.18)", st)
        self.assertRegex(st, r"\.st-spine::before\{[^}]*height:8px")
        for h in ("200", "150", "120", "180"):
            self.assertIn("h:" + h, st, "少了 " + h + "px 那本书")
        for name in ("在读", "共读小窗", "创造", "创作的小窗"):
            self.assertIn('label:"%s"' % name, st, name)
        # 三根丝带 / 三种底纹都要有
        self.assertRegex(st, r"\.st-ribbon\{[^}]*width:3px;height:24px[^}]*var\(--accent\)")
        self.assertIn("#DCEAF3", st)
        for p in ("p-lines", "p-dots", "p-diag"):
            self.assertIn(p, st, p)
        # ④ 隔板：通宽 10px、浅灰 60%、两端圆角
        self.assertRegex(st, r"\.st-plank\{[^}]*height:10px[^}]*rgba\(201,207,214,\.6\)")
        # 四条书脊各自去得了地方（功能一个没丢）
        for fn in ("openCurrent", "openBookchat", "openCreation"):
            self.assertIn(fn, st, fn)
        self.assertIn("/api/books", st, "真正的书还在这一页上")
        self.assertIn("pickFile", st, "放书也还在")

    def test_the_timeline_page_has_alternating_odd_shaped_cards(self):
        """时间线页：编号 + 竖线 + 标题，卡片形状四种轮着来。"""
        tl = (WEB / "nest-timeline.js").read_text(encoding="utf-8")
        # ① 顶栏：‹ 返回 · 时间线 TIMELINE · 搜索
        self.assertIn("nestPageHead", tl)
        self.assertIn('title:"时间线"', tl)
        self.assertIn('en:"TIMELINE"', tl)
        self.assertIn('icon:"search"', tl)
        # 编号：Jost 26px / #A7B0BB
        self.assertRegex(tl, r"\.tl-c \.no\{[^}]*font-size:26px")
        # 编号与正文之间那条 1px 竖线，高 40px
        self.assertRegex(tl, r"\.tl-c \.vr\{width:1px;height:40px")
        # 主标题 15px
        self.assertRegex(tl, r"\.tl-c \.tt\{[^}]*font-size:15px")
        # 卡片：76~100 高、1px 描边、浅底、卡间 12px
        self.assertRegex(tl, r"\.tl-c\{[^}]*min-height:84px")
        self.assertIn("rgba(110,130,150,.30)", tl)
        self.assertIn("rgba(255,255,255,.35)", tl)
        self.assertRegex(tl, r"\.tl-list\{display:flex;flex-direction:column;gap:12px\}")
        # 四种形状轮着来
        self.assertIn('SHAPES=["s-a","s-b","s-c","s-d"]', tl)
        for shape in (".tl-c.s-a", ".tl-c.s-b", ".tl-c.s-c", ".tl-c.s-d"):
            self.assertIn(shape, tl, shape)
        self.assertIn("rotate(45deg)", tl, "书签那个 45° 尖角")
        # 那个弧口是**真的挖掉**一块（mask），不是拿个纸色圆盖上去 ——
        # 盖上去的话那一小块墨晕就透不过来了。
        self.assertIn("-webkit-mask:radial-gradient(circle 7px at 0 50%", tl)
        self.assertIn("mask:radial-gradient(circle 7px at 0 50%", tl)
        # 邮票齿是探出边缘的一小块卡片（转 45° 的方块），填色跟卡片一致
        self.assertNotIn("border-bottom:8px solid", tl, "不该是一块实心深色三角")
        self.assertRegex(tl, r"\.tl-c\.s-d::before,\.tl-c\.s-d::after\{[^}]*background:rgba\(255,255,255,\.35\)")

    def test_bubble_colours_and_names_are_editable(self):
        """★ 用户定的：助手气泡和用户气泡的**底色和字色**都能改，名字也都能改。"""
        skin = (WEB / "nest-skin.js").read_text(encoding="utf-8")
        # 主题里两边的字色都有
        for key in ("aiBubbleFg", "meBubbleFg"):
            self.assertIn(key, skin, key)
        self.assertIn('set("--nest-ai-fg"', skin)
        self.assertIn('set("--nest-me-fg"', skin)
        # 外壳真的读它们
        self.assertIn("var(--nest-ai-fg,var(--tx-1))", self.html)
        self.assertIn("var(--nest-me-fg,var(--tx-1))", self.html)
        # 「我的 › 外观」那一节：4 个颜色控件（两边各底色 + 字色）
        setting = (WEB / "nest-setting.js").read_text(encoding="utf-8")
        self.assertIn("secAppearance", setting)
        self.assertIn("window.nestTheme", setting)
        for key in ('"aiBubble"', '"aiBubbleFg"', '"meBubble"', '"meBubbleFg"'):
            self.assertIn(key, setting, key)
        self.assertIn('i.type="color"', setting)
        # 名字：他和我的都能改
        self.assertIn('["ai","他叫什么"', (WEB / "nest-skin2.js").read_text(encoding="utf-8"))
        self.assertIn('["me","我叫什么"', (WEB / "nest-skin2.js").read_text(encoding="utf-8"))

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
