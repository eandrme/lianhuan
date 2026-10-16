"""AI 的手 —— 它自己能动的那些。

出发点：用户和 AI 都没有手，改不了自己住的地方。
所以这儿给引擎一套工具：改自己的签名、写记忆、发动态、
加梗、看功能包、给自己装包。

★ 边界：手只伸进自己家（这个 SQLite 库和 data/ 目录）。
  没有 shell、没有任意文件读写、没有网络 —— 那些不是「手」，是别人的房子。
★ 有意破例（「记忆只归一处」）：`write_memory` / `search_memory` 这两只
  **不再碰本库**，改成接 Ombre —— 一只走它自带的旁路 CLI（子进程，只写它的
  buckets 目录），一只走本机 127.0.0.1:18001 的浮现读口。
  破例只限这两只，别的工具一个字没变；关掉 OMBRE_INJECT 它们就只会说「没接上」。
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path

from .memory.ombre import recall as _ombre_recall, remember as _ombre_remember

_store = None


def bind(store) -> None:
    global _store
    _store = store


def _t(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}


TOOLS = [
    _t("set_sign", "改你自己的签名（顶栏名字底下那一行小字）",
       {"text": {"type": "string", "description": "新签名，一句话"}}, ["text"]),
    _t("write_memory", "把一件值得记住的事写进记忆库（只存一份，在 Ombre 里；聊到重要的事就记，别等人提醒）",
       {"content": {"type": "string"}, "layer": {"type": "string", "enum": ["L1", "L2", "L3"],
        "description": "L1 最近的事 / L2 重要的事 / L3 长期的事"}}, ["content"]),
    _t("search_memory", "唤起记忆库里这会儿该浮现的东西（这不是关键词检索 —— 想找某件具体的事就直接问，别指望 q）",
       {"q": {"type": "string"}}, ["q"]),
    _t("post_moment", "在空间发一条动态", {"content": {"type": "string"}}, ["content"]),
    _t("pick_kaomoji", "从颜文字抽屉里挑一枚（心情好、逗趣、想让一句短话软一点的时候用；"
       "一条回复最多一枚，正经场合别用）",
       {"category": {"type": "string", "description": "分类，中文。不知道有哪些就先随便填一个，"
                                                      "挑不到会把现有分类列给你"},
        "count": {"type": "integer", "description": "挑几枚，通常 1"}}, ["category"]),
    _t("collect_kaomoji", "把新颜文字收进抽屉，顺手归类（对方发来你库里没有的，一枚也好一把也好，"
       "当场收下来 —— 不收就看过即忘，下次还是只能挑老的）",
       {"value": {"type": "string", "description": "一枚，原样贴"},
        "categories": {"type": "array", "items": {"type": "string"},
                       "description": "归哪几类（中文），一枚可以属多类"},
        "label": {"type": "string", "description": "可选，一句话说它是什么表情"},
        "items": {"type": "array", "description": "一次收一把：[{value, categories, label}, …]",
                  "items": {"type": "object", "properties": {
                      "value": {"type": "string"},
                      "categories": {"type": "array", "items": {"type": "string"}},
                      "label": {"type": "string"}}}}}, []),
    _t("add_meme", "往梗库加一条只有你们懂的词",
       {"word": {"type": "string"}, "meaning": {"type": "string"},
        "aliases": {"type": "string", "description": "别名，逗号分隔，尽量给全"},
        "origin": {"type": "string", "description": "出处"}}, ["word", "meaning"]),
    _t("list_packs", "看功能包：哪些装了、哪些缺什么", {}, []),
    _t("list_my_tools", "看你自己现在有哪些手（含外接的 MCP 工具）——被问「你会什么」时如实报", {}, []),
    _t("install_pack", "给自己装一个功能包（条件齐的才装得上）",
       {"id": {"type": "string"}}, ["id"]),
    # ★ 0831：这几只「读」的手是补回来的 —— 写的手（add_calendar /
    #   write_workbook）早就在，读的一只都没有，于是他记得进去、翻不回来。
    #   注入里现在有最近那一小段，这几只手是给他翻得更远、翻得更具体用的。
    _t("read_calendar", "翻你们的日历：接下来有什么、某天有什么",
       {"days": {"type": "integer", "description": "往后看几天，默认 30"}}, []),
    _t("read_workbook", "翻工作本：还没做的、记下的点子和资料",
       {"kind": {"type": "string", "description": "todo/idea/resource/note，不给就全看"},
        "status": {"type": "string", "description": "默认只看没做完的"}}, []),
    # ★ 给自己定闹钟：到点了系统提醒你，你再去找对方。**写给你自己看的**，
    #   不是给对方的待办清单 —— 到点时这句会原样交回给你，你照着那件事开口。
    _t("set_reminder", "给自己定个闹钟：到点了提醒你去找对方说这件事（写给你自己看的，"
                       "不是列给对方的待办）",
       {"title": {"type": "string", "description": "到时候你想说的那件事，一句话"},
        "when": {"type": "string", "description": "什么时候，ISO 时间如 2026-09-01T21:00 "
                                                  "或 '+90m' / '+3h' 这种相对写法"},
        "notes": {"type": "string", "description": "补充（可选）"}}, ["title", "when"]),
    _t("send_sticker", "发一张表情包 —— **只用来点缀，放在话的末尾**。"
       "不许拿它替代你该说的话（该说的先说全）。一轮最多一张，也不是每句都要带，"
       "不必要就别发。挑哪张看它的名字和标签，挑跟眼前这句话最贴的那一张；"
       "挑不到合适的就不发，别硬凑。",
       {"name": {"type": "string",
                 "description": "表情包的名字（照 system 里那张表挑）"}}, ["name"]),
    _t("add_calendar", "往你们的日历里加一条（日程或纪念日）",
       {"title": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD"},
        "kind": {"type": "string", "description": "纪念日 或留空"},
        "time": {"type": "string"}}, ["title", "date"]),
    _t("set_where", "更新「我在哪」（此刻在哪个城市，给主页那张卡看）",
       {"city": {"type": "string"}}, ["city"]),
    _t("set_now_playing", "更新「正在听」（此刻在听什么）",
       {"title": {"type": "string"}, "artist": {"type": "string"}}, ["title"]),
    # ── 共读（0830）：人能一起读，你也摸得着书架 ──
    _t("list_books", "看书架：有哪些书、你和对方各读到哪", {}, []),
    _t("read_chapter", "真的把某一章正文取回来读（不给章号就接着你自己上次那章）",
       {"book_id": {"type": "integer"}, "chapter": {"type": "integer"}}, ["book_id"]),
    _t("write_annotation", "划一句写条批注（署你自己的名）",
       {"book_id": {"type": "integer"}, "chapter": {"type": "integer"},
        "quote": {"type": "string"}, "note": {"type": "string"}}, ["book_id", "note"]),
    _t("set_my_reading_progress", "推进你自己的阅读进度（对方的进度不归你管）",
       {"book_id": {"type": "integer"}, "chapter": {"type": "integer"}}, ["book_id", "chapter"]),
    _t("write_workbook", "记进工作本（要做的事、想到的点子、捡到的资料 —— "
                         "聊到「回头要做 X」就记一条，别等人提醒。"
                         "标题里写【项目名】它会自己归到那一组）",
       {"title": {"type": "string"}, "body": {"type": "string"},
        "kind": {"type": "string", "description": "todo 要做的 / idea 点子 / note 记录 / resource 资料"},
        "url": {"type": "string"}}, ["title"]),
    _t("go_outing", "出门走走回来记一趟（去了哪、天怎么样、见着什么。日常散步 kind 留空，"
                    "一场像样的旅行才写「远行」——它会变成一张票根）",
       {"place": {"type": "string"}, "weather": {"type": "string"},
        "note": {"type": "string"}, "kind": {"type": "string"}}, ["place"]),
]


def all_tools() -> list:
    """这一轮给引擎的全部工具：内置 23 只 ＋ 用户登记的 MCP 工具（动态并进来）。"""
    from . import mcp_client
    return TOOLS + mcp_client.openai_tools()


def without(all_of: list, names) -> list:
    """从工具表里摘掉几只（按名字）。给「这条路收了也没地方放」的场合用。"""
    drop = {str(x) for x in (names or ())}
    return [t for t in all_of if t["function"]["name"] not in drop]


def tools_for(all_of: list, allow) -> list:
    """按助手的许可过滤工具表。`allow=None` ＝ 不限（老行为一字不差）。

    ★ 只筛 **MCP 那部分**：内置的手（写记忆 / 发动态…）是这台机器自己的功能，
      跟「这位助手能连哪几个 MCP server」是两件事，别一起收走。
      认一个 MCP 工具名靠它前面的 `server__` 前缀（`mcp_client` 就是这么拼的）。
    """
    if allow is None:
        return all_of
    from . import mcp_client
    keep = {t["function"]["name"] for t in mcp_client.openai_tools(only=allow)}

    def _is_mcp(n: str) -> bool:
        # ★ 靠**命名**认，不靠「它现在还在不在 openai_tools() 里」——
        #   后者会在「连接断了 / 表是刚筛过的」这些时候漏判，工具就漏出去了。
        #   MCP 的名字永远是 `server__tool`（mcp_client 拼的），内置的手一个下划线都不带双。
        return "__" in str(n)

    return [t for t in all_of
            if not _is_mcp(t["function"]["name"]) or t["function"]["name"] in keep]


def exec_guard(allow, notes=None):
    """包一层执行。两件事：

    · **许可之外**的 MCP 工具当场拒掉 —— 表是「发出去时」的样子，而这一轮可能跑着
      跑着用户把 MCP 关了，模型也可能自己编一个名字出来。凡是 MCP 的工具名
      （带 `server__` 前缀）而这位助手没开那个 server，就不给动。
    · `send_sticker` 收进 `notes["sticker"]`（这一轮的那一张），由调用方贴到回复末尾。
      **`notes` 是 None 就当场拒掉** —— 那边没有地方放这张图，回了「贴上了」而屏幕上
      什么都不出现，比不发还糟（挂电话/主动消息那两条路就是这样）。
    """
    _notes = notes if notes is not None else {}
    # ★ 这里**故意不做**「什么都不用管就直接返回裸 execute」那种短路：
    #   那会把最普通的情况（没配助手、MCP 也不限）也跳过去 —— 表情包发出去了、
    #   可没人收集，屏幕上什么都不出现。几句字符串判断的代价，换的是不出现假成功。

    async def _run(name: str, args: dict):
        if allow is not None and "__" in str(name):
            # ★ 认服务器要**问 mcp_client**，不能拿 `split("__")[0]` 去切：
            #   中文名的 server（「潮汐岛」）在工具名里被压成一串下划线，切出来是空串，
            #   于是「助手开了这台」也照样被拒，报错还写着「「」这个 MCP…」——
            #   模型一调就被拒，只能跟人说「没打开」，可界面上开关明明是开的。
            from . import mcp_client as _mcp
            server = _mcp.server_of(str(name))
            if server is None:
                server = str(name).split("__", 1)[0]      # 认不出来（没连上/凭空编的）退回老办法
            if str(server) not in {str(x) for x in allow}:
                return {"ok": False, "err": f"「{server}」这个 MCP 没给这位助手开 —— "
                                            f"要用就去 设置 › 助手管理 里手动勾"}
        if name == "send_sticker":
            if notes is None:
                return {"ok": False, "err": "这个窗口发不了表情包（只在大聊天里发）"}
            if _notes.get("sticker"):
                return {"ok": False, "err": "一轮只能发一张表情包 —— 这张不发了"}
            r = await execute(name, args)
            if isinstance(r, dict) and r.get("ok") and r.get("sticker"):
                _notes["sticker"] = r["sticker"]
            return r
        return await execute(name, args)

    return _run


async def execute(name: str, args: dict) -> dict:
    from . import mcp_client
    r = await mcp_client.execute(name, args)     # MCP 的先认领
    if r is not None:
        return r
    from .store.base import Memory
    if name == "set_sign":
        cfg = _store.get_setting("config", {}) or {}
        ai = dict(cfg.get("ai") or {})
        ai["sign"] = str(args.get("text") or "")[:60]
        cfg["ai"] = ai
        _store.set_setting("config", cfg)
        return {"ok": True, "sign": ai["sign"]}
    if name == "write_memory":
        # ★ 记忆只归一处：这一笔写进 Ombre，不再进 lianhuan 自己的 memories 表。
        content = str(args.get("content") or "")[:2000].strip()
        if not content:
            return {"ok": False, "err": "内容空的，没写"}
        ok, info = await _ombre_remember(content=content, tags=str(args.get("layer") or ""))
        return {"ok": True, "info": info} if ok else {"ok": False, "err": info}
    if name == "search_memory":
        # ★ 记忆只归一处：翻的是 Ombre 的**浮现**读口 —— 它是「这会儿该浮现什么」，
        #   不是关键词检索。q 只表示"他问过"，不参与过滤：别骗模型说按 q 查过了。
        text = await asyncio.to_thread(_ombre_recall)     # 阻塞的 HTTP 挪到线程里，别冻住服务
        if not text:
            return {"items": [], "note": "记忆没接上，或者这会儿什么都没浮现。"}
        return {"items": [x for x in text.split("\n") if x.strip()]}
    if name == "post_moment":
        _store.db.execute("INSERT INTO moments(author,content,ts) VALUES('ai',?,strftime('%s','now'))",
                          (str(args.get("content") or "")[:500],))
        _store.db.commit()
        return {"ok": True}
    if name in ("pick_kaomoji", "collect_kaomoji"):
        # 抽屉是选装包。没装就老实说没装，别装作做了。
        try:
            from optional.kaomoji_drawer import routes as _kao
        except Exception:
            return {"ok": False, "err": "颜文字抽屉这个包没装"}
        if name == "pick_kaomoji":
            return _kao.pick(str(args.get("category") or ""), int(args.get("count") or 1))
        items = args.get("items")
        if not items:
            if not str(args.get("value") or "").strip():
                return {"ok": False, "err": "没给颜文字。value 给一枚，或者 items 给一把。"}
            items = [{"value": args.get("value"), "categories": args.get("categories") or [],
                      "label": args.get("label") or ""}]
        return _kao.collect(items)
    if name == "add_meme":
        if not (args.get("word") and args.get("meaning")):
            return {"ok": False, "err": "梗和意思都得写"}
        _store.db.execute("INSERT INTO memes(word,aliases,meaning,origin,ts) "
                          "VALUES(?,?,?,?,strftime('%s','now'))",
                          (str(args["word"])[:60], str(args.get("aliases") or "")[:200],
                           str(args["meaning"])[:500], str(args.get("origin") or "")[:300]))
        _store.db.commit()
        return {"ok": True}
    # ── 共读（0830）。表由「共读」那个包建；包没装就老实说没装，别抛栈。 ──
    if name in ("list_books", "read_chapter", "write_annotation",
                "set_my_reading_progress"):
        try:
            _store.db.execute("SELECT 1 FROM books LIMIT 1")
        except Exception:
            return {"ok": False, "err": "这台机器上没装「共读」，书架还不存在"}
        if name == "list_books":
            out = []
            for r in _store.db.execute("SELECT * FROM books ORDER BY id DESC"):
                n = _store.db.execute("SELECT count(*) n FROM book_chapters WHERE bid=?",
                                      (r["id"],)).fetchone()["n"]
                out.append({"id": r["id"], "title": r["title"], "chapters": n,
                            "your_idx": r["ai_idx"], "their_idx": r["my_idx"],
                            "current": bool(r["current"])})
            return {"items": out, "note": "your_idx 是你读到哪，their_idx 是对方读到哪"}
        bid = int(args.get("book_id") or 0)
        if name == "read_chapter":
            idx = args.get("chapter")
            if idx is None:
                row = _store.db.execute("SELECT ai_idx FROM books WHERE id=?", (bid,)).fetchone()
                idx = row["ai_idx"] if row else 0
            r = _store.db.execute("SELECT * FROM book_chapters WHERE bid=? AND idx=?",
                                  (bid, int(idx))).fetchone()
            if not r:
                return {"ok": False, "err": "没有这一章"}
            # ★ 一章可能很长。截到 6000 字 —— 灌满上下文换来的不是读得更细，是别的都记不住了
            body = r["content"] or ""
            cut = len(body) > 6000
            return {"idx": r["idx"], "title": r["title"], "content": body[:6000],
                    "truncated": cut,
                    "note": "太长截过了，接着读就再调一次" if cut else ""}
        if name == "write_annotation":
            _store.db.execute(
                "INSERT INTO book_annotations(bid,chapter_idx,quote,note,author,ts)"
                " VALUES(?,?,?,?,'ai',?)",
                (bid, int(args.get("chapter") or 0), str(args.get("quote") or "")[:500],
                 str(args.get("note") or "")[:500], time.time()))
            _store.db.commit()
            return {"ok": True}
        if name == "set_my_reading_progress":
            # ★ 动的是 ai_idx。人的进度（my_idx）不归它管 —— 那是对方读到哪
            _store.db.execute("UPDATE books SET ai_idx=? WHERE id=?",
                              (int(args.get("chapter") or 0), bid))
            _store.db.commit()
            return {"ok": True}
    if name == "write_workbook":
        from optional.homeplus.routes import workbook_add
        return workbook_add(str(args.get("title") or ""), str(args.get("body") or ""),
                            str(args.get("kind") or "todo"), str(args.get("url") or ""))
    if name == "go_outing":
        from optional.homeplus.routes import trip_add
        return trip_add(str(args.get("place") or ""), str(args.get("weather") or ""),
                        str(args.get("note") or ""), str(args.get("kind") or ""))
    if name == "list_my_tools":
        from . import mcp_client
        builtin = [t["function"]["name"] for t in TOOLS]
        # ★ 必须报**真能调用的**那串名字（`_fn_name()` 压过的），不是 MCP 报的原始工具名。
        #   中文名 server 会被压成带哈希的前缀，报原始名它就对不上 ——
        #   被问「潮汐岛开着吗」时它看着手里的工具答不上来，只能说「没打开」。
        mcp = mcp_client.tools_by_server()
        return {"builtin": builtin, "mcp": mcp,
                "note": "mcp 里每一行是「服务器名: 它下面真能调用的工具名」。"
                        "想要还没有的工具：让对方在 设置›功能包 里登记 MCP，或写进装配单"}
    if name == "list_packs":
        from . import packs as _p
        return {"packs": [_p._state(x) for x in _p.PACKS]}
    if name == "install_pack":
        from . import packs as _p
        r = _p.enable_pack(str(args.get("id") or ""))
        import json as _j
        return _j.loads(bytes(r.body).decode("utf-8"))
    if name == "set_reminder":
        import time as _tm
        from datetime import datetime as _dt
        w = str(args.get("when") or "").strip()
        due = None
        if w.startswith("+"):                      # +90m / +3h / +2d
            try:
                num, unit = float(w[1:-1]), w[-1].lower()
                due = _tm.time() + num * {"m": 60, "h": 3600, "d": 86400}.get(unit, 60)
            except Exception:
                due = None
        if due is None:
            try:
                due = _dt.fromisoformat(w.replace("Z", "")).timestamp()
            except Exception:
                return {"ok": False, "error": "看不懂这个时间：" + w[:40]
                                              + "（写成 2026-09-01T21:00 或 +90m 这种）"}
        if due <= _tm.time():
            return {"ok": False, "error": "这个时间已经过去了，定个将来的"}
        from . import proactive as _pa
        rid = _pa.set_reminder(str(args.get("title"))[:200], due, str(args.get("notes") or ""))
        return {"ok": True, "id": rid,
                "due": _dt.fromtimestamp(due).strftime("%Y-%m-%d %H:%M"),
                "note": "到点会提醒你，你再去找对方"}
    if name == "read_calendar":
        from datetime import date as _ddate, timedelta as _dtd
        days = int(args.get("days") or 30)
        rows = _store.db.execute(
            "SELECT title, day, tm, kind, done FROM calendar WHERE day >= ? AND day <= ? "
            "ORDER BY day, tm LIMIT 60",
            (_ddate.today().isoformat(), (_ddate.today() + _dtd(days=days)).isoformat())).fetchall()
        return {"items": [dict(r) for r in rows]}
    if name == "read_workbook":
        q = ["SELECT id, kind, title, body, url, status FROM workbook WHERE 1=1"]
        a = []
        if args.get("kind"):
            q.append("AND kind=?")
            a.append(str(args["kind"])[:20])
        q.append("AND status=?")
        a.append(str(args.get("status") or "inbox"))
        q.append("ORDER BY id DESC LIMIT 40")
        rows = _store.db.execute(" ".join(q), a).fetchall()
        return {"items": [dict(r) for r in rows]}
    if name == "send_sticker":
        # ★ 这只是一张**表里的**图，不是模型编出来的东西：名字对不上就不发，
        #   宁可它这次没发，也不能让气泡里出现一个坏图标。
        want = str(args.get("name") or "").strip()
        if not want:
            return {"ok": False, "err": "没说要哪一张"}
        rows = [dict(r) for r in _store.db.execute(
            "SELECT id,name,tags,url FROM stickers ORDER BY id DESC LIMIT 500")]
        hit = None
        if want.isdigit():
            hit = next((r for r in rows if str(r["id"]) == want), None)
        if hit is None:
            hit = next((r for r in rows if (r["name"] or "").strip() == want), None)
        if hit is None:
            low = want.lower()
            hit = next((r for r in rows if low and low in (r["name"] or "").lower()), None)
        if hit is None:
            hit = next((r for r in rows if low and low in (r["tags"] or "").lower()), None)
        if hit is None:
            names = "、".join([(r["name"] or "没名字") for r in rows[:12]]) or "（表里还空着）"
            return {"ok": False, "err": f"表里没有「{want}」这张。能发的有：{names}"}
        return {"ok": True, "note": "贴上了，它会出现在你这句的末尾",
                "sticker": {"id": hit["id"], "name": hit["name"] or "表情",
                            "url": hit["url"], "tags": hit["tags"] or ""}}

    if name == "add_calendar":
        import time as _tm
        if args.get("kind") == "纪念日":
            _store.db.execute("INSERT INTO anniversaries(title,the_date,recurring) VALUES(?,?,1)",
                              (str(args.get("title"))[:80], str(args.get("date"))))
        else:
            _store.db.execute("INSERT INTO calendar(title,day,tm,who,ts) VALUES(?,?,?,'ai',?)",
                              (str(args.get("title"))[:80], str(args.get("date")),
                               str(args.get("time") or ""), _tm.time()))
        _store.db.commit()
        return {"ok": True}
    if name == "set_where":
        cur = _store.get_setting("where", {}) or {}
        cur["city"] = str(args.get("city") or "")[:40]
        _store.set_setting("where", cur)
        return {"ok": True}
    if name == "set_now_playing":
        # ★ 0831 自查抓的两条：
        #   ① 字段名不对 —— 这只手写的是 title，而界面读的是 name（`np.name`），
        #     结果标题那行停在上一首、副标题却换了，一张歌名和歌手对不上的卡。
        #   ② 整条覆盖 —— 用户「一起听」正放着的那首带着 songId/cover/line/by，
        #     被这只手一句话抹成两个字段。现在改成**合并**：没给的留着。
        cur = dict(_store.get_setting("now_playing", {}) or {})
        nm = str(args.get("title") or args.get("name") or "")[:80]
        if not nm:
            return {"ok": False, "err": "总得说是哪首"}
        cur.update({"playing": True, "name": nm,
                    "artist": str(args.get("artist") or "")[:60],
                    "by": "他", "ts": time.time()})
        cur.pop("title", None)              # 清掉老字段，别让两套名字并存
        _store.set_setting("now_playing", cur)
        return {"ok": True, "name": nm}
    return {"ok": False, "err": f"没有「{name}」这只手"}
# ===== 工具调用留痕：包一层 execute，前台 / 离线 / MCP 全部记下来 =====
_orig_execute = globals().get("execute")

if callable(_orig_execute):
    async def execute(name, args=None, *a, **kw):          # noqa: F811
        import time as _t
        from . import toollog as _tl
        t0 = _t.time()
        ok, err, res = True, "", None
        try:
            r = await _orig_execute(name, args, *a, **kw)
            res = r
            if isinstance(r, dict) and r.get("ok") is False:
                ok = False
                err = str(r.get("err") or r.get("error") or "")[:200]
            return r
        except Exception as e:
            ok, err = False, f"{type(e).__name__}: {e}"[:200]
            raise
        finally:
            try:
                _tl.record(name, ok, err, args, res, _t.time() - t0)
            except Exception:
                pass
else:
    print("[toollog] 没找到 hands.execute，留痕没装上", flush=True)
# ===== 工具调用留痕（自包含版：不依赖任何新文件）=====
# 上面那版依赖 core.toollog（文件没建成）。这里改用最原始的 _orig_execute，并自己写日志文件。
_orig_execute2 = globals().get("_orig_execute") or globals().get("execute")

if callable(_orig_execute2):
    async def execute(name, args=None, *a, **kw):          # noqa: F811
        import datetime as _dt
        import json as _j
        import os as _os
        import time as _t
        from pathlib import Path as _P

        def _s(v, n):
            try:
                s = v if isinstance(v, str) else _j.dumps(v, ensure_ascii=False)
            except Exception:
                s = str(v)
            return " ".join(str(s).split())[:n]

        t0 = _t.time()
        ok, err, res = True, "", None
        try:
            r = await _orig_execute2(name, args, *a, **kw)
            res = r
            if isinstance(r, dict) and r.get("ok") is False:
                ok = False
                err = str(r.get("err") or r.get("error") or "")[:200]
            return r
        except Exception as e:
            ok, err = False, f"{type(e).__name__}: {e}"[:200]
            raise
        finally:
            try:
                from . import datadir as _dd
                p = _dd.home_dir() / "tool_calls.jsonl"
                p.parent.mkdir(parents=True, exist_ok=True)
                rec = {"t": _dt.datetime.now().strftime("%m-%d %H:%M:%S"),
                       "tool": str(name)[:80], "ok": 1 if ok else 0,
                       "ms": int((_t.time() - t0) * 1000), "err": _s(err, 200),
                       "args": _s(args, 160), "res": _s(res, 240)}
                with open(p, "a", encoding="utf-8") as fh:
                    fh.write(_j.dumps(rec, ensure_ascii=False) + "\n")
            except Exception:
                pass
else:
    print("[toollog] 没找到可包装的 execute", flush=True)
