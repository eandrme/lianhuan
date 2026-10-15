"""过日子那一套 —— 记事四件套 · 心情 · 梗库 · 玩具厅（真实现，不是契约）。

字段名照原项目一个不改，前端零改动。存 SQLite（跟聊天记忆同一个库）。
这些不是「用户自己动手」的部分 —— **我们的实现就是默认可装的**；
不喜欢魔改的人再去 UPSTREAM.md 找原文献，那是第二选项。

AI 的楼中接话 / 替用户发一条动态，用当前引擎生成（bind 时注入）。
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()
_store = None
_say = None            # async (prompt) -> str，bind 注入：用当前引擎说一句


def bind(store, say) -> None:
    global _store, _say
    _store, _say = store, say
    for ddl in (
        "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " kind TEXT DEFAULT 'note', content TEXT NOT NULL, mood TEXT, dropped INTEGER DEFAULT 0, ts REAL)",
        "CREATE TABLE IF NOT EXISTS diary (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " who TEXT DEFAULT 'ai', kind TEXT DEFAULT 'diary', mood TEXT, content TEXT NOT NULL, ts REAL)",
        "CREATE TABLE IF NOT EXISTS letters (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " tags TEXT DEFAULT '', content TEXT NOT NULL, day TEXT, ts REAL,"
        # ★ who：这封信是哪位助手写的（空＝通用／主助手）。一个助手一沓信，
        #   助手管理里就看他这一沓。老库这一列靠下面的 ALTER 补。
        " who TEXT DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS moments (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " author TEXT DEFAULT 'me', content TEXT NOT NULL, image TEXT, ts REAL)",
        "CREATE TABLE IF NOT EXISTS moment_comments (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " mid INTEGER NOT NULL, author TEXT, content TEXT NOT NULL, ts REAL)",
        "CREATE TABLE IF NOT EXISTS timeline_events (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " kind TEXT DEFAULT '', content TEXT NOT NULL, meta TEXT, ts REAL)",
        "CREATE TABLE IF NOT EXISTS memes (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " word TEXT NOT NULL, aliases TEXT DEFAULT '', meaning TEXT DEFAULT '',"
        " origin TEXT DEFAULT '', ref_count INTEGER DEFAULT 0, ts REAL)",
        # ★ 表情包：用户自己攒的图（一张一行，指向 data/uploads 里的文件）。
        #   图本身不上数据库，只存它在服务器哪儿 —— 跟聊天气泡里的附件同一个规矩。
        "CREATE TABLE IF NOT EXISTS stickers (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT DEFAULT '', tags TEXT DEFAULT '', url TEXT NOT NULL, ts REAL)",
        # ★ 健康账：一天一条。字段照原项目那套（steps / resting_hr / hrv_ms /
        #   menstrual），原项目由手表推进来，开源版没有手表这条路 —— 就自己记。
        "CREATE TABLE IF NOT EXISTS health_log (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " day TEXT NOT NULL UNIQUE, steps INTEGER, resting_hr REAL, hrv_ms REAL,"
        " menstrual TEXT DEFAULT '', note TEXT DEFAULT '', ts REAL)",
    ):
        store.db.execute(ddl)
    store.db.commit()
    for table, col, ddl in (("letters", "who", "ALTER TABLE letters ADD COLUMN who TEXT DEFAULT ''"),):
        try:
            cols = [r[1] for r in store.db.execute(f"PRAGMA table_info({table})")]
            if col not in cols:
                store.db.execute(ddl)
                store.db.commit()
        except Exception as e:
            print(f"[homelife] {table}.{col} 迁移失败:", e, flush=True)


def _d(ts):  return datetime.fromtimestamp(ts or 0).strftime("%Y-%m-%d")
def _hm(ts): return datetime.fromtimestamp(ts or 0).strftime("%H:%M")
def _md(ts): return datetime.fromtimestamp(ts or 0).strftime("%m-%d %H:%M")


# ── 信 ────────────────────────────────────────────────────
@router.get("/api/letters")
def api_letters(who: str = ""):
    """信箱。`?who=<助手 id>` 只看那位写的那一沓；不带＝全部。

    ★ 一带 who 就**只回那一沓**（不把 who 为空的那堆也倒进来）—— 助手管理里要的是
      「他写的信」，混进别人写的就不叫分类了。"""
    sql, args = "SELECT * FROM letters", ()
    if who.strip():
        sql += " WHERE COALESCE(who,'')=?"
        args = (who.strip(),)
    rows = [{"id": r["id"], "tags": r["tags"] or "", "content": r["content"],
             "day": r["day"] or _d(r["ts"]), "who": r["who"] or "", "src": "local"}
            for r in _store.db.execute(sql + " ORDER BY id DESC LIMIT 200", args)]
    return JSONResponse({"items": rows, "letters": rows})


@router.post("/api/letters")
async def api_letter_add(req: Request):
    """自己写一封（不经过模型）。助手管理里「替他写一封」和「我写一封」都走这儿。"""
    b = await req.json()
    content = (b.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "err": "空的信寄不出去"}, status_code=400)
    cur = _store.db.execute(
        "INSERT INTO letters(tags,content,day,ts,who) VALUES(?,?,?,?,?)",
        (str(b.get("tags") or "")[:200], content[:8000],
         str(b.get("day") or "") or _d(time.time()), time.time(),
         str(b.get("who") or "")[:40]))
    _store.db.commit()
    return JSONResponse({"ok": True, "id": cur.lastrowid})


@router.post("/api/letters/{lid}/del")
def api_letter_del(lid: int):
    _store.db.execute("DELETE FROM letters WHERE id=?", (lid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


# ── 空间（动态 ＋ 楼中回复，AI 会接话）──────────────────────
def _moments_out():
    out = []
    for r in _store.db.execute("SELECT * FROM moments ORDER BY id DESC LIMIT 100"):
        cs = [{"id": c["id"], "author": c["author"], "content": c["content"], "t": _md(c["ts"])}
              for c in _store.db.execute(
                  "SELECT * FROM moment_comments WHERE mid=? ORDER BY id", (r["id"],))]
        out.append({"id": r["id"], "author": r["author"], "content": r["content"],
                    "image": r["image"], "t": _md(r["ts"]), "day": _d(r["ts"]), "comments": cs})
    return out


@router.get("/api/moments")
def api_moments():
    return JSONResponse({"items": _moments_out()})


async def _ai_reply_to(mid: int, context: str) -> None:
    """AI 在楼里接一句。失败就不接 —— 帖子本身已经落库，不能因为嘴笨丢帖子。"""
    try:
        text = await _say("对方刚在你们共享的空间里贴了一条动态：「" + context[:300]
                          + "」\n用一两句话在楼里自然地接话（不要引号，不要解释）。")
        if text.strip():
            _store.db.execute("INSERT INTO moment_comments(mid,author,content,ts) VALUES(?,?,?,?)",
                              (mid, "ai", text.strip()[:500], time.time()))
            _store.db.commit()
    except Exception:
        pass


@router.post("/api/moments/mine")
async def api_moment_mine(req: Request):
    b = await req.json()
    content = (b.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "err": "空的"}, status_code=400)
    cur = _store.db.execute("INSERT INTO moments(author,content,image,ts) VALUES(?,?,?,?)",
                            ("me", content, b.get("image"), time.time()))
    _store.db.commit()
    asyncio.get_running_loop().create_task(_ai_reply_to(cur.lastrowid, content))
    return JSONResponse({"ok": True, "id": cur.lastrowid})


@router.post("/api/moments/new")
async def api_moment_new(req: Request):
    """戳 AI 发一条。真用引擎写，写不出来老实说。"""
    try:
        text = await _say("在你们共享的空间里发一条你自己的动态：此刻想说的一两句话"
                          "（不要引号，不要解释，就是那条动态本身）。")
    except Exception:
        text = ""
    if not text.strip():
        return JSONResponse({"ok": False, "err": "这回没写出来"}, status_code=502)
    cur = _store.db.execute("INSERT INTO moments(author,content,ts) VALUES(?,?,?)",
                            ("ai", text.strip()[:500], time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True, "id": cur.lastrowid})


@router.post("/api/moments/{mid}/comment")
async def api_moment_comment(mid: int, req: Request):
    b = await req.json()
    content = (b.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "err": "空的"}, status_code=400)
    _store.db.execute("INSERT INTO moment_comments(mid,author,content,ts) VALUES(?,?,?,?)",
                      (mid, "me", content, time.time()))
    _store.db.commit()
    asyncio.get_running_loop().create_task(_ai_reply_to(mid, content))
    return JSONResponse({"ok": True})


@router.post("/api/moments/{mid}/edit")
async def api_moment_edit(mid: int, req: Request):
    """改一条动态的正文（配图不动 —— 换图走「重贴一条」）。"""
    b = await req.json()
    content = (b.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "err": "正文不能空"}, status_code=400)
    cur = _store.db.execute("UPDATE moments SET content=? WHERE id=?",
                            (content[:2000], mid))
    _store.db.commit()
    return JSONResponse({"ok": True, "gone": cur.rowcount})


@router.post("/api/moments/{mid}/del")
def api_moment_del(mid: int):
    """删一条动态（连同它楼里的评论）。自己的空间，删就是删。"""
    _store.db.execute("DELETE FROM moment_comments WHERE mid=?", (mid,))
    cur = _store.db.execute("DELETE FROM moments WHERE id=?", (mid,))
    _store.db.commit()
    return JSONResponse({"ok": True, "gone": cur.rowcount})


@router.post("/api/moments/comment/{cid}/del")
def api_moment_comment_del(cid: int):
    cur = _store.db.execute("DELETE FROM moment_comments WHERE id=?", (cid,))
    _store.db.commit()
    return JSONResponse({"ok": True, "gone": cur.rowcount})


# ── 时间线 ────────────────────────────────────────────────
@router.get("/api/timeline")
def api_timeline(limit: int = 80):
    limit = max(1, min(int(limit or 80), 200))
    today = datetime.now().date()
    out = []
    for r in _store.db.execute("SELECT * FROM timeline_events ORDER BY ts DESC LIMIT ?", (limit,)):
        d = datetime.fromtimestamp(r["ts"] or 0).date()
        md = json.loads(r["meta"]) if r["meta"] else {}
        out.append({"id": r["id"], "kind": r["kind"] or "", "content": r["content"],
                    "date": d.isoformat(), "time": _hm(r["ts"]),
                    "days": (d - today).days, "src": md.get("src") or "", "meta": md})
    return JSONResponse({"items": out})


@router.post("/api/timeline")
async def api_timeline_add(req: Request):
    b = await req.json()
    if not (b.get("content") or "").strip():
        return JSONResponse({"ok": False}, status_code=400)
    _store.db.execute("INSERT INTO timeline_events(kind,content,meta,ts) VALUES(?,?,?,?)",
                      (b.get("kind") or "", b["content"].strip(),
                       json.dumps(b.get("meta") or {}, ensure_ascii=False), time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/timeline/{tid}/edit")
async def api_timeline_edit(tid: int, req: Request):
    """改时间线里那一条（写错了、或想换条道）。"""
    b = await req.json()
    content = (b.get("content") or "").strip()
    if not content:
        return JSONResponse({"ok": False, "err": "不能空着"}, status_code=400)
    if b.get("kind"):
        _store.db.execute("UPDATE timeline_events SET content=?, kind=? WHERE id=?",
                          (content[:500], str(b["kind"])[:20], tid))
    else:
        _store.db.execute("UPDATE timeline_events SET content=? WHERE id=?",
                          (content[:500], tid))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/timeline/{tid}/del")
def api_timeline_del(tid: int):
    """删一条。★ 这是一份「这个家怎么起来的」的流水，记错了得能划掉 ——
    不然错的那条会一直躺在时间线上，越攒越像真的。"""
    cur = _store.db.execute("DELETE FROM timeline_events WHERE id=?", (tid,))
    _store.db.commit()
    return JSONResponse({"ok": True, "gone": cur.rowcount})


import re as _re

_MOOD_MARK = _re.compile(r"‹\s*(?:心情\s*)?([^›]+)›")


def apply_marker(text: str, source: str = "chat", untrusted: bool = False):
    """把回复里的 ‹…› 带内标记剥掉（只清洗，不落账）。返回（清洗后的正文, [])。"""
    applied = []
    cleaned = _MOOD_MARK.sub("", text or "").strip()
    return cleaned, applied


# ── 梗库 ──────────────────────────────────────────────────
@router.get("/api/memes")
def api_memes():
    rows = [{"id": r["id"], "word": r["word"], "aliases": r["aliases"], "meaning": r["meaning"],
             "origin": r["origin"], "tags": "", "source": "", "author": "",
             "ref_count": r["ref_count"], "weight": 1.0, "day": _d(r["ts"])}
            for r in _store.db.execute("SELECT * FROM memes ORDER BY id DESC LIMIT 300")]
    return JSONResponse({"items": rows})


@router.post("/api/memes")
async def api_meme_add(req: Request):
    b = await req.json()
    word, meaning = (b.get("word") or "").strip(), (b.get("meaning") or "").strip()
    if not word or not meaning:
        return JSONResponse({"ok": False, "err": "梗和它是什么意思，两样都得写"}, status_code=400)
    _store.db.execute("INSERT INTO memes(word,aliases,meaning,origin,ts) VALUES(?,?,?,?,?)",
                      (word, b.get("aliases") or "", meaning, b.get("origin") or "", time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/memes/edit")
async def api_meme_edit(req: Request):
    b = await req.json()
    word = (b.get("word") or "").strip()
    r = _store.db.execute("SELECT id FROM memes WHERE word=?", (word,)).fetchone()
    if not r:
        return JSONResponse({"ok": False, "err": "没有这条"}, status_code=404)
    for k in ("meaning", "aliases", "origin"):
        if b.get(k) is not None:
            _store.db.execute(f"UPDATE memes SET {k}=? WHERE id=?", (str(b[k]), r["id"]))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/memes/{mid}/edit")
async def api_meme_edit_by_id(mid: int, req: Request):
    """按 id 改。★ 原来只有「按 word 找」那一条 —— 梗本身写错了字就改不动
    （一改 word，那条就找不到了）。界面上点的是哪张卡，就该改哪一行。"""
    b = await req.json()
    if not _store.db.execute("SELECT id FROM memes WHERE id=?", (mid,)).fetchone():
        return JSONResponse({"ok": False, "err": "没有这条"}, status_code=404)
    sets, args = [], []
    for k in ("word", "meaning", "aliases", "origin"):
        if b.get(k) is not None:
            v = str(b[k]).strip()
            if k == "word":
                if not v:
                    return JSONResponse({"ok": False, "err": "梗本身不能是空的"}, status_code=400)
                dup = _store.db.execute("SELECT id FROM memes WHERE word=? AND id<>?",
                                        (v, mid)).fetchone()
                if dup:
                    return JSONResponse({"ok": False, "err": "已经有一条同名的梗了"},
                                        status_code=409)
            sets.append(f"{k}=?")
            args.append(v)
    if not sets:
        return JSONResponse({"ok": False, "err": "没什么要改的"}, status_code=400)
    args.append(mid)
    _store.db.execute("UPDATE memes SET " + ",".join(sets) + " WHERE id=?", args)
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/memes/{mid}/del")
def api_meme_del(mid: int):
    """删一条梗。★ 原项目只有「录」和「改」，攒了几百条之后没法收拾。"""
    _store.db.execute("DELETE FROM memes WHERE id=?", (mid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


# ── 玩具厅（data/plays/*.html，AI 写的小玩意放这儿）──────────
@router.get("/api/plays")
def api_plays():
    import os
    import re
    from pathlib import Path
    from core import datadir as _dd
    d = _dd.home_dir() / "plays"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for f in sorted(d.glob("*.html")):
        title = f.stem
        try:
            head = f.read_text(encoding="utf-8", errors="replace")[:2000]
            mt = re.search(r"<title>(.*?)</title>", head, re.S | re.I)
            if mt and mt.group(1).strip():
                title = mt.group(1).strip()
        except Exception:
            pass
        out.append({"file": f.name, "title": title, "url": "/plays/" + f.name})
    return JSONResponse({"items": out})

def _plays_dir():
    from core import datadir as _dd
    d = _dd.home_dir() / "plays"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _play_path(name: str):
    """把前端给的文件名落到 plays 目录里的**一个文件**上。

    ★ 名字是外面传进来的：`../` 那种必须在这一步就断掉，不能拿它去 open/删。
      规矩照原项目那条来：只收 `xxx.html`，字母数字点划，别的都不认。"""
    import re as _re
    from pathlib import Path as _P
    n = _P(str(name or "")).name                     # 先把路径成分剥掉
    if not _re.fullmatch(r"[A-Za-z0-9._-]+\.html", n) or n.startswith("."):
        return None
    p = (_plays_dir() / n).resolve()
    if p.parent != _plays_dir().resolve():
        return None
    return p


@router.post("/api/plays/{name}/del")
def api_play_del(name: str):
    """删掉一个小玩意。**人自己也能收拾** —— 他写坏了、或者不喜欢了，得有地方划掉。"""
    p = _play_path(name)
    if p is None:
        return JSONResponse({"ok": False, "err": "这个名字不认（只收 xxx.html）"}, status_code=400)
    if not p.exists():
        return JSONResponse({"ok": False, "err": "没有这个小玩意"}, status_code=404)
    p.unlink()
    return JSONResponse({"ok": True, "gone": p.name})


@router.post("/api/plays/new")
async def api_play_new(req: Request):
    """戳他现做一个小玩意。真用引擎写；写不出来老实说，不塞个空壳进玩具箱。"""
    try:
        b = await req.json()
    except Exception:
        b = {}
    hint = str((b or {}).get("hint") or "").strip()[:200]
    ask = ("给{对方}写一个小网页玩意，会上架到玩具厅。"
           "要求：**一个自包含的 .html**（内联 CSS 和 JS，不引任何外链、不用外部图片），"
           "手机上点开就能玩，画面好看、手感要对（点一下有反馈），"
           "不要跟已有的重复，别写说明文字。"
           + ((" 这一回想要的是：" + hint) if hint else "")
           + " 只回 HTML 本身，不要解释、不要 markdown 代码块。")
    try:
        text = await _say(ask)
    except Exception as e:                                     # noqa: BLE001
        return JSONResponse({"ok": False, "err": f"引擎那边出事了：{type(e).__name__}"},
                            status_code=502)
    html = str(text or "").strip()
    if not html:
        return JSONResponse({"ok": False, "err": "这回没写出来（引擎是桩的时候就会这样）"},
                            status_code=502)
    # 模型常见的两种包装：```html 围栏、或者前后带一句解释
    if "```" in html:
        seg = html.split("```")
        html = max(seg, key=len)
        if html.lstrip().lower().startswith("html"):
            html = html.lstrip()[4:]
    i = html.lower().find("<!doctype")
    if i < 0:
        i = html.lower().find("<html")
    if i > 0:
        html = html[i:]
    if len(html) < 40 or ("<" not in html) or ("</" not in html):
        return JSONResponse({"ok": False, "err": "它回的东西不像 HTML，这次不上架"},
                            status_code=502)
    import re as _re
    import time as _tm
    mt = _re.search(r"<title[^>]*>(.*?)</title>", html, _re.S | _re.I)
    title = (mt.group(1).strip() if mt else "")[:40] or "小玩意"
    slug = _re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:24]
    fn = (slug or "toy") + "-" + format(int(_tm.time()) % 100000, "x")
    from core import hands as _hands
    r = await _hands.execute("write_play", {"filename": fn, "html": html})
    if not (isinstance(r, dict) and r.get("ok")):
        return JSONResponse({"ok": False, "err": str((r or {}).get("err") or "没上架成")},
                            status_code=502)
    return JSONResponse({"ok": True, "file": fn + ".html", "title": title,
                         "url": r.get("url") or ("/plays/" + fn + ".html")})


# ══════════ 巢：表情包（用户自己攒的图）══════════
# 图本身走 /api/upload 落进 data/uploads（跟聊天里发图同一条路），这儿只记账：
# 名字、标签、在服务器哪儿。点一张＝把它放进输入框上头，配句话一起发出去。
def _sticker_row(r) -> dict:
    return {"id": r["id"], "name": r["name"] or "", "tags": r["tags"] or "",
            "url": r["url"], "t": _md(r["ts"]), "day": _d(r["ts"])}


@router.get("/api/stickers")
def api_stickers(limit: int = 400):
    lim = max(1, min(int(limit or 400), 1000))
    rows = [_sticker_row(r) for r in _store.db.execute(
        "SELECT * FROM stickers ORDER BY id DESC LIMIT ?", (lim,))]
    return JSONResponse({"items": rows})


@router.post("/api/stickers")
async def api_sticker_add(req: Request):
    b = await req.json()
    url = str(b.get("url") or "").strip()
    # ★ 只收本站上传目录里的图：不收外链（哪天链接烂了，卡上就是个破图标），
    #   更不信前端报上来的路径 —— 拿它直接开文件就是任意文件读取。
    if not _re.fullmatch(r"/uploads/[^/\\]+", url):
        return JSONResponse({"ok": False, "err": "先把图传上来（/api/upload），再存这张"},
                            status_code=400)
    # ★ 还得真在盘上 —— 存一条指向不存在文件的记录，卡上就是个破图标，
    #   以后聊天里带上它也会被附件那一关悄悄丢掉。不如当场说实话。
    import os as _os
    from pathlib import Path as _P
    from core import datadir as _dd2
    up = (_dd2.home_dir()
          / "uploads" / url.split("/", 2)[-1])
    if not (up.is_file() and up.name == url.split("/", 2)[-1]):
        return JSONResponse({"ok": False, "err": "服务器上没有这张图 —— 先传一次再存"},
                            status_code=400)
    cur = _store.db.execute(
        "INSERT INTO stickers(name,tags,url,ts) VALUES(?,?,?,?)",
        ((b.get("name") or "").strip()[:60], (b.get("tags") or "").strip()[:120],
         url, time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True, "id": cur.lastrowid})


@router.post("/api/stickers/{sid}/edit")
async def api_sticker_edit(sid: int, req: Request):
    b = await req.json()
    if not _store.db.execute("SELECT id FROM stickers WHERE id=?", (sid,)).fetchone():
        return JSONResponse({"ok": False, "err": "没有这张"}, status_code=404)
    sets, args = [], []
    if "name" in b:
        sets.append("name=?")
        args.append(str(b.get("name") or "").strip()[:60])
    if "tags" in b:
        sets.append("tags=?")
        args.append(str(b.get("tags") or "").strip()[:120])
    if not sets:
        return JSONResponse({"ok": False, "err": "没什么要改的"}, status_code=400)
    args.append(sid)
    _store.db.execute("UPDATE stickers SET " + ",".join(sets) + " WHERE id=?", args)
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/stickers/{sid}/del")
def api_sticker_del(sid: int):
    """删掉这张。★ 只从表情包里摘掉，**不删 data/uploads 里那个文件** ——
    同一张图可能还挂在某条聊天记录的气泡上，删文件会把那条记录弄破。"""
    _store.db.execute("DELETE FROM stickers WHERE id=?", (sid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


# ══════════ 巢：健康账（一天一条）══════════
# ⚠ 形状照原项目 /api/health_recent：items 里每条是 {t, payload}，payload 里有
#   steps / resting_hr / hrv_ms / menstrual —— **没有睡眠时长**（原项目也没有）。
#   原项目这份数据是手表推进来的，开源版没有那条路：自己记，空着就是空着。
def _int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def _float_or_none(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def _health_row(r) -> dict:
    return {"id": r["id"], "t": r["day"],
            "payload": {"steps": (None if r["steps"] is None else int(r["steps"])),
                        "resting_hr": r["resting_hr"], "hrv_ms": r["hrv_ms"],
                        "menstrual": r["menstrual"] or "", "note": r["note"] or ""},
            "captured_at": r["ts"]}


@router.get("/api/health_recent")
def api_health_recent(days: int = 30):
    lim = max(1, min(int(days or 30), 400))
    rows = list(_store.db.execute(
        "SELECT * FROM health_log ORDER BY day DESC LIMIT ?", (lim,)))
    rows.reverse()                     # 老 → 新：界面上「最新的那条」在最后
    return JSONResponse({"items": [_health_row(r) for r in rows]})


@router.post("/api/health")
async def api_health_save(req: Request):
    """记一天。同一天再记＝改那一天（一天一条，不会攒出两条打架的账）。

    ★ 只覆盖**这次真带来的那几样**：白天先记步数、晚上回来补心率，
      不该把上午那 9000 步抹掉。要清空某一格就显式送空值。
    """
    b = await req.json()
    day = (b.get("day") or "").strip() or datetime.now().strftime("%Y-%m-%d")
    if not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        return JSONResponse({"ok": False, "err": "日期要写成 2025-01-31 这种"}, status_code=400)
    steps = _int_or_none(b.get("steps"))
    if steps is not None:
        steps = max(0, min(steps, 200000))          # 手滑多打几个 0 也存得下
    got = {"steps": steps, "resting_hr": _float_or_none(b.get("resting_hr")),
           "hrv_ms": _float_or_none(b.get("hrv_ms")),
           "menstrual": (b.get("menstrual") or "").strip()[:40],
           "note": (b.get("note") or "").strip()[:400]}
    cur = _store.db.execute("SELECT * FROM health_log WHERE day=?", (day,)).fetchone()
    vals = dict(got)
    if cur is not None:                             # 老库里那几样：这次没带的原样留着
        for k in got:
            if k not in b:
                vals[k] = cur[k]
    if all(vals[k] in (None, "") for k in vals):
        return JSONResponse({"ok": False, "err": "一天至少记一样"}, status_code=400)
    if cur is not None:
        _store.db.execute(
            "UPDATE health_log SET steps=?,resting_hr=?,hrv_ms=?,menstrual=?,note=?,ts=? "
            "WHERE id=?",
            (vals["steps"], vals["resting_hr"], vals["hrv_ms"], vals["menstrual"],
             vals["note"], time.time(), cur["id"]))
        hid = cur["id"]
    else:
        c = _store.db.execute(
            "INSERT INTO health_log(day,steps,resting_hr,hrv_ms,menstrual,note,ts) "
            "VALUES(?,?,?,?,?,?,?)",
            (day, vals["steps"], vals["resting_hr"], vals["hrv_ms"], vals["menstrual"],
             vals["note"], time.time()))
        hid = c.lastrowid
    _store.db.commit()
    return JSONResponse({"ok": True, "id": hid, "day": day})


@router.post("/api/health/{hid}/del")
def api_health_del(hid: int):
    _store.db.execute("DELETE FROM health_log WHERE id=?", (hid,))
    _store.db.commit()
    return JSONResponse({"ok": True})
