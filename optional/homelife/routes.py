"""过日子那一套 —— 记事 · 梗库 · 表情包 · 健康（真实现，不是契约）。

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
    """AI 回一句。失败就不接 —— 帖子本身已经落库，不能因为嘴笨丢帖子。"""
    try:
        text = await _say("对方刚发了一条动态：「" + context[:300]
                          + "」\n用一两句话自然回一句（不要引号，不要解释）。")
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
        text = await _say("写一条动态：此刻想说的一两句话"
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
    """删一条动态（连同它的回复）。删就是删。"""
    _store.db.execute("DELETE FROM moment_comments WHERE mid=?", (mid,))
    cur = _store.db.execute("DELETE FROM moments WHERE id=?", (mid,))
    _store.db.commit()
    return JSONResponse({"ok": True, "gone": cur.rowcount})


@router.post("/api/moments/comment/{cid}/del")
def api_moment_comment_del(cid: int):
    cur = _store.db.execute("DELETE FROM moment_comments WHERE id=?", (cid,))
    _store.db.commit()
    return JSONResponse({"ok": True, "gone": cur.rowcount})


import re as _re

_MOOD_MARK = _re.compile(r"‹\s*(?:心情\s*)?([^›]+)›")


def apply_marker(text: str):
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
