"""共读 v1 —— 传一本 txt，切好章，两个人就着书聊。

原项目的书房还有 epub、跨端进度、批注嵌回原文那些；这一版先把「能一起读」立住：
上传 txt → 自动切章 → 读 → 划一句批注 → 就这一章问它（带当前章上下文）。
"""
from __future__ import annotations

import base64
import re
import time
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()
_store = None
_say = None


def bind(store, say) -> None:
    global _store, _say
    _store, _say = store, say
    for ddl in (
        "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT NOT NULL, current INTEGER DEFAULT 0, my_idx INTEGER DEFAULT 0,"
        " ai_idx INTEGER DEFAULT 0, ts REAL)",
        "CREATE TABLE IF NOT EXISTS book_chapters (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " bid INTEGER NOT NULL, idx INTEGER NOT NULL, title TEXT, content TEXT)",
        "CREATE TABLE IF NOT EXISTS book_annotations (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " bid INTEGER NOT NULL, chapter_idx INTEGER, quote TEXT, note TEXT, author TEXT, ts REAL)",
        "CREATE TABLE IF NOT EXISTS book_chat (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " bid INTEGER NOT NULL, role TEXT, content TEXT, ts REAL)",
    ):
        store.db.execute(ddl)
    store.db.commit()


_CH = re.compile(r"^\s*(第\s*[0-9一二三四五六七八九十百千两〇零]+\s*[章回节卷幕]|Chapter\s+\d+|CHAPTER\s+\d+)[^\n]{0,40}$",
                 re.M)


def _split_chapters(text: str) -> list[tuple[str, str]]:
    """按章题切；一本没有章题的书就按 3000 字一刀（宁可粗，别不能读）。"""
    marks = list(_CH.finditer(text))
    if len(marks) >= 2:
        out = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.end():end].strip()
            if body:
                out.append((m.group(0).strip(), body))
        if out:
            return out
    chunks = [text[i:i + 3000] for i in range(0, len(text), 3000)]
    return [(f"第 {i + 1} 屏", c) for i, c in enumerate(chunks) if c.strip()]


@router.post("/api/books/upload")
async def book_upload(req: Request):
    b = await req.json()
    data = b.get("dataURL") or ""
    m = data.split(",", 1)
    try:
        raw = base64.b64decode(m[1]) if len(m) == 2 else (b.get("text") or "").encode()
    except Exception:
        return JSONResponse({"ok": False, "err": "读不出来"}, status_code=400)
    for enc in ("utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            text = ""
    if len(text) < 200:
        return JSONResponse({"ok": False, "err": "太短了，不像一本书（也可能是编码没认出来）"},
                            status_code=400)
    title = (b.get("title") or "").strip() or "没起名的书"
    chs = _split_chapters(text)
    cur = _store.db.execute("INSERT INTO books(title,ts) VALUES(?,?)", (title, time.time()))
    bid = cur.lastrowid
    for i, (t, c) in enumerate(chs):
        _store.db.execute("INSERT INTO book_chapters(bid,idx,title,content) VALUES(?,?,?,?)",
                          (bid, i, t, c))
    _store.db.commit()
    return JSONResponse({"ok": True, "id": bid, "chapters": len(chs)})


@router.get("/api/books")
def books():
    out = []
    for r in _store.db.execute("SELECT * FROM books ORDER BY id DESC"):
        n = _store.db.execute("SELECT count(*) n FROM book_chapters WHERE bid=?",
                              (r["id"],)).fetchone()["n"]
        out.append({"id": r["id"], "title": r["title"], "chapters": n,
                    "my_idx": r["my_idx"], "ai_idx": r["ai_idx"],
                    "current": bool(r["current"]),
                    "pct": round(100 * (r["my_idx"] + 1) / n) if n else 0})
    return JSONResponse({"items": out})


@router.get("/api/books/{bid}/chapters")
def book_chapters(bid: int):
    rows = [{"idx": r["idx"], "title": r["title"]}
            for r in _store.db.execute(
                "SELECT idx,title FROM book_chapters WHERE bid=? ORDER BY idx", (bid,))]
    return JSONResponse({"items": rows})


@router.get("/api/books/{bid}/chapter/{idx}")
def book_chapter(bid: int, idx: int):
    r = _store.db.execute("SELECT * FROM book_chapters WHERE bid=? AND idx=?",
                          (bid, idx)).fetchone()
    if not r:
        return JSONResponse({"err": "没有这一章"}, status_code=404)
    return JSONResponse({"idx": r["idx"], "title": r["title"], "content": r["content"]})


@router.post("/api/books/{bid}/progress")
async def book_progress(bid: int, req: Request):
    b = await req.json()
    _store.db.execute("UPDATE books SET my_idx=? WHERE id=?", (int(b.get("idx") or 0), bid))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/books/{bid}/current")
async def book_current(bid: int):
    _store.db.execute("UPDATE books SET current=0")
    _store.db.execute("UPDATE books SET current=1 WHERE id=?", (bid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.get("/api/books/{bid}/annotations")
def book_annos(bid: int):
    rows = [{"id": r["id"], "chapter_idx": r["chapter_idx"], "quote": r["quote"],
             "note": r["note"], "author": r["author"],
             "t": datetime.fromtimestamp(r["ts"] or 0).strftime("%m-%d %H:%M")}
            for r in _store.db.execute(
                "SELECT * FROM book_annotations WHERE bid=? ORDER BY id DESC", (bid,))]
    return JSONResponse({"items": rows})


@router.post("/api/books/{bid}/annotations")
async def book_anno_add(bid: int, req: Request):
    b = await req.json()
    _store.db.execute(
        "INSERT INTO book_annotations(bid,chapter_idx,quote,note,author,ts) VALUES(?,?,?,?,?,?)",
        (bid, int(b.get("chapter_idx") or 0), (b.get("quote") or "")[:500],
         (b.get("note") or "")[:500], b.get("author") or "me", time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.get("/api/books/{bid}/chat")
def book_chat_get(bid: int):
    rows = [{"role": r["role"], "content": r["content"],
             "t": datetime.fromtimestamp(r["ts"] or 0).strftime("%m-%d %H:%M")}
            for r in _store.db.execute(
                "SELECT * FROM book_chat WHERE bid=? ORDER BY id", (bid,))]
    return JSONResponse({"items": rows})


@router.post("/api/books/{bid}/chat")
async def book_chat_post(bid: int, req: Request):
    b = await req.json()
    q = (b.get("message") or b.get("content") or "").strip()
    if not q:
        return JSONResponse({"ok": False}, status_code=400)
    bk = _store.db.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
    ch = _store.db.execute("SELECT * FROM book_chapters WHERE bid=? AND idx=?",
                           (bid, bk["my_idx"] if bk else 0)).fetchone()
    _store.db.execute("INSERT INTO book_chat(bid,role,content,ts) VALUES(?,?,?,?)",
                      (bid, "user", q, time.time()))
    _store.db.commit()
    ctx = (ch["content"][:2400] if ch else "")
    try:
        a = await _say(f"你们在共读《{bk['title'] if bk else '书'}》，正读到「{ch['title'] if ch else ''}」。"
                       f"这一章的原文节选：\n{ctx}\n\n对方就这一章说：「{q}」\n"
                       f"就着书自然地聊回去（一两段，别写成书评）。")
    except Exception:
        a = ""
    if not a.strip():
        return JSONResponse({"ok": False, "err": "这回没接上话"}, status_code=502)
    _store.db.execute("INSERT INTO book_chat(bid,role,content,ts) VALUES(?,?,?,?)",
                      (bid, "assistant", a.strip(), time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True, "reply": a.strip()})


@router.get("/api/books/{bid}/notes")
def book_notes(bid: int):
    bk = _store.db.execute("SELECT title FROM books WHERE id=?", (bid,)).fetchone()
    annos = book_annos(bid)
    chat = book_chat_get(bid)
    import json as _j
    return JSONResponse({"title": bk["title"] if bk else "",
                         "annotations": _j.loads(bytes(annos.body))["items"],
                         "chat": _j.loads(bytes(chat.body))["items"]})

@router.post("/api/books/{bid}/rename")
async def book_rename(bid: int, req: Request):
    b = await req.json()
    t = (b.get("title") or "").strip()[:60]
    if not t:
        return JSONResponse({"ok": False, "err": "名字不能空"}, status_code=400)
    _store.db.execute("UPDATE books SET title=? WHERE id=?", (t, bid))
    _store.db.commit()
    return JSONResponse({"ok": True, "title": t})


@router.post("/api/books/{bid}/del")
async def book_del(bid: int):
    """删一本书，连它的章节 / 批注 / 小窗记录一起删。"""
    for sql in ("DELETE FROM book_chapters WHERE bid=?",
                "DELETE FROM book_annotations WHERE bid=?",
                "DELETE FROM book_chat WHERE bid=?"):
        _store.db.execute(sql, (bid,))
    _store.db.execute("DELETE FROM books WHERE id=?", (bid,))
    _store.db.commit()
    return JSONResponse({"ok": True})

# ══════════════════ 创造：世界观 / 角色 / 故事 ══════════════════
_CREATED = {"ok": False}


def _ct() -> None:
    """第一次用到时建表（幂等）。"""
    if _CREATED["ok"]:
        return
    for ddl in (
        "CREATE TABLE IF NOT EXISTS worlds (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT NOT NULL, note TEXT DEFAULT '', ts REAL)",
        "CREATE TABLE IF NOT EXISTS casts (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " wid INTEGER DEFAULT 0, name TEXT NOT NULL, note TEXT DEFAULT '', ts REAL)",
        "CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " wid INTEGER DEFAULT 0, title TEXT DEFAULT '', body TEXT DEFAULT '', ts REAL)",
        "CREATE TABLE IF NOT EXISTS story_notes (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " sid INTEGER NOT NULL, quote TEXT DEFAULT '', note TEXT DEFAULT '',"
        " author TEXT DEFAULT 'me', ts REAL)",
        "CREATE TABLE IF NOT EXISTS story_chat (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " sid INTEGER NOT NULL, role TEXT, content TEXT, ts REAL)",
    ):
        _store.db.execute(ddl)
    _store.db.commit()
    _CREATED["ok"] = True


def _t(ts) -> str:
    return datetime.fromtimestamp(ts or 0).strftime("%m-%d %H:%M")


@router.get("/api/worlds")
def worlds():
    """世界观列表 + 每个下面挂了多少角色/故事。"""
    _ct()
    out = []
    for r in _store.db.execute("SELECT * FROM worlds ORDER BY id DESC"):
        nc = _store.db.execute("SELECT count(*) n FROM casts WHERE wid=?", (r["id"],)).fetchone()["n"]
        ns = _store.db.execute("SELECT count(*) n FROM stories WHERE wid=?", (r["id"],)).fetchone()["n"]
        out.append({"id": r["id"], "name": r["name"], "note": r["note"] or "",
                    "casts": nc, "stories": ns, "t": _t(r["ts"])})
    orphan = _store.db.execute(
        "SELECT count(*) n FROM stories WHERE COALESCE(wid,0)=0").fetchone()["n"]
    return JSONResponse({"items": out, "orphan": orphan})


@router.post("/api/worlds/save")
async def world_save(req: Request):
    _ct()
    b = await req.json()
    name = (b.get("name") or "").strip()[:40]
    if not name:
        return JSONResponse({"ok": False, "err": "得有个名字"}, status_code=400)
    note = (b.get("note") or "")[:3000]
    wid = int(b.get("id") or 0)
    if wid:
        _store.db.execute("UPDATE worlds SET name=?, note=? WHERE id=?", (name, note, wid))
    else:
        wid = _store.db.execute("INSERT INTO worlds(name,note,ts) VALUES(?,?,?)",
                                (name, note, time.time())).lastrowid
    _store.db.commit()
    return JSONResponse({"ok": True, "id": wid})


@router.post("/api/worlds/{wid}/del")
def world_del(wid: int):
    """删世界观 —— 里面的角色和故事**不会**跟着删，变成「未归类」。"""
    _ct()
    _store.db.execute("UPDATE stories SET wid=0 WHERE wid=?", (wid,))
    _store.db.execute("UPDATE casts SET wid=0 WHERE wid=?", (wid,))
    _store.db.execute("DELETE FROM worlds WHERE id=?", (wid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.get("/api/worlds/{wid}")
def world_one(wid: int):
    _ct()
    w = _store.db.execute("SELECT * FROM worlds WHERE id=?", (wid,)).fetchone()
    casts = [{"id": r["id"], "name": r["name"], "note": r["note"] or "", "wid": r["wid"] or 0}
             for r in _store.db.execute("SELECT * FROM casts WHERE wid=? ORDER BY id", (wid,))]
    sts = [{"id": r["id"], "wid": r["wid"] or 0, "title": r["title"] or "",
            "excerpt": (r["body"] or "").replace("\n", " ")[:70], "t": _t(r["ts"])}
           for r in _store.db.execute("SELECT * FROM stories WHERE wid=? ORDER BY id DESC", (wid,))]
    return JSONResponse({"world": {"id": wid, "name": (w["name"] if w else ""),
                                   "note": (w["note"] if w else "")},
                         "casts": casts, "stories": sts})


@router.post("/api/casts/save")
async def cast_save(req: Request):
    _ct()
    b = await req.json()
    name = (b.get("name") or "").strip()[:40]
    if not name:
        return JSONResponse({"ok": False, "err": "角色得有个名字"}, status_code=400)
    cid, wid = int(b.get("id") or 0), int(b.get("wid") or 0)
    note = (b.get("note") or "")[:6000]
    if cid:
        _store.db.execute("UPDATE casts SET name=?, note=?, wid=? WHERE id=?", (name, note, wid, cid))
    else:
        cid = _store.db.execute("INSERT INTO casts(wid,name,note,ts) VALUES(?,?,?,?)",
                                (wid, name, note, time.time())).lastrowid
    _store.db.commit()
    return JSONResponse({"ok": True, "id": cid})


@router.post("/api/casts/{cid}/del")
def cast_del(cid: int):
    _ct()
    _store.db.execute("DELETE FROM casts WHERE id=?", (cid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.get("/api/stories")
def stories(wid: int = -1, q: str = ""):
    """wid >= 0 只看某个世界观下面的；不传 = 全部。"""
    _ct()
    sql = "SELECT * FROM stories"
    args = []
    if wid >= 0:
        sql += " WHERE COALESCE(wid,0)=?"
        args.append(wid)
    sql += " ORDER BY id DESC LIMIT 200"
    out = []
    for r in _store.db.execute(sql, args):
        if q and q not in (r["title"] or "") and q not in (r["body"] or ""):
            continue
        out.append({"id": r["id"], "wid": r["wid"] or 0, "title": r["title"] or "",
                    "excerpt": (r["body"] or "").replace("\n", " ")[:70],
                    "n": len(r["body"] or ""), "t": _t(r["ts"])})
    return JSONResponse({"items": out})


@router.get("/api/stories/{sid}")
def story_one(sid: int):
    _ct()
    r = _store.db.execute("SELECT * FROM stories WHERE id=?", (sid,)).fetchone()
    if not r:
        return JSONResponse({"ok": False, "err": "没有这篇"}, status_code=404)
    return JSONResponse({"ok": True, "id": r["id"], "wid": r["wid"] or 0,
                         "title": r["title"] or "", "body": r["body"] or ""})


@router.post("/api/stories/save")
async def story_save(req: Request):
    """id 为空 = 新写一篇；带 id = 改。wid=0 表示先不归类。"""
    _ct()
    b = await req.json()
    sid, wid = int(b.get("id") or 0), int(b.get("wid") or 0)
    title = (b.get("title") or "").strip()[:60] or "没起名"
    body = (b.get("body") or "")[:200000]
    if sid:
        _store.db.execute("UPDATE stories SET wid=?, title=?, body=? WHERE id=?",
                          (wid, title, body, sid))
    else:
        sid = _store.db.execute("INSERT INTO stories(wid,title,body,ts) VALUES(?,?,?,?)",
                                (wid, title, body, time.time())).lastrowid
    _store.db.commit()
    return JSONResponse({"ok": True, "id": sid})


@router.post("/api/stories/{sid}/del")
def story_del(sid: int):
    _ct()
    for sql in ("DELETE FROM story_notes WHERE sid=?", "DELETE FROM story_chat WHERE sid=?"):
        _store.db.execute(sql, (sid,))
    _store.db.execute("DELETE FROM stories WHERE id=?", (sid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.get("/api/stories/{sid}/notes")
def story_notes(sid: int):
    _ct()
    rows = [{"id": r["id"], "quote": r["quote"] or "", "note": r["note"] or "",
             "author": r["author"] or "me", "t": _t(r["ts"])}
            for r in _store.db.execute("SELECT * FROM story_notes WHERE sid=? ORDER BY id", (sid,))]
    return JSONResponse({"items": rows})


@router.post("/api/stories/{sid}/notes")
async def story_note_add(sid: int, req: Request):
    _ct()
    b = await req.json()
    _store.db.execute("INSERT INTO story_notes(sid,quote,note,author,ts) VALUES(?,?,?,?,?)",
                      (sid, (b.get("quote") or "")[:500], (b.get("note") or "")[:500],
                       b.get("author") or "me", time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.get("/api/stories/{sid}/chat")
def story_chat_get(sid: int):
    _ct()
    rows = [{"role": r["role"], "content": r["content"], "t": _t(r["ts"])}
            for r in _store.db.execute("SELECT * FROM story_chat WHERE sid=? ORDER BY id", (sid,))]
    return JSONResponse({"items": rows})


@router.post("/api/stories/{sid}/chat")
async def story_chat_post(sid: int, req: Request):
    """创作小窗：不带工具、和主聊天无关，只认这个故事。"""
    _ct()
    b = await req.json()
    q = (b.get("message") or "").strip()
    if not q:
        return JSONResponse({"ok": False}, status_code=400)
    st = _store.db.execute("SELECT * FROM stories WHERE id=?", (sid,)).fetchone()
    _store.db.execute("INSERT INTO story_chat(sid,role,content,ts) VALUES(?,?,?,?)",
                      (sid, "user", q, time.time()))
    _store.db.commit()
    body = (st["body"] if st else "") or ""
    title = (st["title"] if st else "") or "没起名"
    try:
        a = await _say("你们在一起写一个故事，题目叫《" + title + "》。"
                       "目前写到的内容：\n" + body[:2400] + "\n\n"
                       "对方说：「" + q + "」\n"
                       "就着这个故事接着聊 —— 像一起写东西的搭档，"
                       "一两段，可以提建议、接一句、或者顺着往下想，别写成文学评论。")
    except Exception:
        a = ""
    if not (a or "").strip():
        return JSONResponse({"ok": False, "err": "这回没接上话"}, status_code=502)
    _store.db.execute("INSERT INTO story_chat(sid,role,content,ts) VALUES(?,?,?,?)",
                      (sid, "assistant", a.strip(), time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True, "reply": a.strip()})
