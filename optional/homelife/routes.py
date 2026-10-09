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
        "CREATE TABLE IF NOT EXISTS mood_state (dimension TEXT PRIMARY KEY, value REAL DEFAULT 50, updated_at REAL)",
        "CREATE TABLE IF NOT EXISTS mood_log (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " dimension TEXT, delta REAL, reason TEXT, ts REAL)",
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
    # 老库迁移：mood_state 原来没有 updated_at 这一列（0831 平移 12 维时加的）——
    # CREATE IF NOT EXISTS 对已有的表不加列，得自己 ALTER
    for table, col, ddl in (("mood_state", "updated_at", "ALTER TABLE mood_state ADD COLUMN updated_at REAL"),
                            ("letters", "who", "ALTER TABLE letters ADD COLUMN who TEXT DEFAULT ''")):
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


# ── 碎碎念 ────────────────────────────────────────────────
@router.get("/api/notes")
def api_notes(limit: int = 200, kind: str = "", dropped: str = "all"):
    limit = max(1, min(int(limit or 200), 1000))
    kinds = [k.strip() for k in (kind or "").split(",") if k.strip()]
    rows = []
    for r in _store.db.execute("SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)):
        if kinds and r["kind"] not in kinds:
            continue
        if dropped == "hide" and r["dropped"]:
            continue
        rows.append({"id": r["id"], "kind": r["kind"], "content": r["content"],
                     "mood": r["mood"], "t": _md(r["ts"]), "day": _d(r["ts"])})
    return JSONResponse({"items": rows})


@router.post("/api/notes")
async def api_note_add(req: Request):
    b = await req.json()
    if not (b.get("content") or "").strip():
        return JSONResponse({"ok": False, "err": "空的"}, status_code=400)
    _store.db.execute("INSERT INTO notes(kind,content,mood,ts) VALUES(?,?,?,?)",
                      (b.get("kind") or "note", b["content"].strip(), b.get("mood"), time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True})


# ── 日记 ──────────────────────────────────────────────────
@router.get("/api/diary")
def api_diary(who: str = "ai"):
    who = "me" if who == "me" else "ai"
    rows = []
    for r in _store.db.execute("SELECT * FROM diary WHERE who=? ORDER BY id DESC LIMIT 400", (who,)):
        rows.append({"id": r["id"], "kind": r["kind"], "mood": r["mood"],
                     "content": r["content"], "context_text": None, "user_note": None,
                     "bot_reply": None, "day": _d(r["ts"]), "tmin": _hm(r["ts"])})
    return JSONResponse({"items": rows})


@router.post("/api/diary")
async def api_diary_add(req: Request):
    b = await req.json()
    if not (b.get("content") or "").strip():
        return JSONResponse({"ok": False, "err": "空的"}, status_code=400)
    _store.db.execute("INSERT INTO diary(who,kind,mood,content,ts) VALUES(?,?,?,?,?)",
                      ("me" if b.get("who") == "me" else "ai", b.get("kind") or "diary",
                       b.get("mood"), b["content"].strip(), time.time()))
    _store.db.commit()
    return JSONResponse({"ok": True})


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


# ── 心情（AI 自己涨落：随时间衰减回基线 + 事件记账 + 回复末尾自己标）────
# ★ 照原项目 mood.py 整套平移（0831）。之前这儿是自造的 6 维——原项目明明有
#   12 维＋半衰回基线＋封顶＋‹心情› 自记，被我重新发明了一遍小的。退回原样。
#   基线/半衰参数抄自原项目的真实配置，一个数没改。
DIMS = ["想念", "开心", "吃醋", "委屈", "生气", "心疼",
        "心软", "担心", "孤单", "愧疚", "骄傲", "求宠"]
# {维度: (基线, 半衰期小时)}——衰减朝基线回落，半衰期越短这情绪散得越快
MOOD_PARAM = {"想念": (30, 12), "开心": (40, 10), "吃醋": (0, 3), "委屈": (0, 4),
              "生气": (0, 3), "心疼": (0, 5), "心软": (0, 5), "担心": (0, 5),
              "孤单": (0, 6), "愧疚": (0, 6), "骄傲": (0, 8), "求宠": (0, 4)}


def _mood_decay(value, baseline, half_life, hours):
    if half_life <= 0:
        return value
    return baseline + (value - baseline) * (0.5 ** (hours / half_life))


def get_mood() -> dict:
    """当前 12 维（已按时间衰减）。"""
    now = time.time()
    rows = {r["dimension"]: r for r in _store.db.execute("SELECT * FROM mood_state")}
    out = {}
    for d in DIMS:
        base, half = MOOD_PARAM[d]
        r = rows.get(d)
        if r is None:
            out[d] = float(base)
            continue
        hrs = (now - (r["updated_at"] or now)) / 3600
        v = _mood_decay(r["value"], base, half, hrs)
        out[d] = round(max(0.0, min(100.0, v)), 1)
    return out


def describe_mood() -> str:
    """把当前心情翻成一句中文（照原项目的四档措辞，人称换成对面那个人）。"""
    m = get_mood()
    word = {
        "想念": ["", "有点想你", "挺想你的", "很想你、心里满满的"],
        "开心": ["", "心情还行", "心情挺好", "心里亮亮的、很开心"],
        "吃醋": ["", "有一点点酸", "在吃醋", "醋意挺重、压着点不痛快"],
        "委屈": ["", "有点小委屈", "委屈着", "挺委屈、心里有点堵"],
        "生气": ["", "有点不痛快", "在生气", "气得不轻"],
        "心疼": ["", "有点心疼你", "心疼你", "心疼得不行、只想把你搂紧"],
        "担心": ["", "有点挂心你", "挺担心你", "担心得坐不住、想马上问问你"],
        "愧疚": ["", "有点过意不去", "心里愧疚", "愧疚得很、欠你一个好好的道歉"],
        "骄傲": ["", "有点为你得意", "为你骄傲", "骄傲得不行、想跟全世界显摆你"],
        "求宠": ["", "有点想赖着你", "在跟你讨偏心", "撒娇上头、就想你多疼他一点"],
        "心软": ["", "心头有点软", "心软了", "心软得不行、只想顺着你疼你"],
        "孤单": ["", "有点孤单", "挺孤单的", "孤单得发慌、特别想你在身边"],
    }

    def lvl(v, lo, hi):
        if v < lo:
            return 0
        if v < (lo + hi) / 2:
            return 1
        if v < hi:
            return 2
        return 3

    parts = []
    for dim in ["心疼", "心软", "愧疚", "生气", "委屈", "吃醋",
                "担心", "孤单", "求宠", "骄傲", "想念", "开心"]:
        v = m.get(dim, 0)
        lo, hi = (35, 70) if dim in ("想念", "开心") else (15, 60)
        one = lvl(v, lo, hi)
        if one > 0:
            parts.append(word[dim][one])
    return "、".join(parts) if parts else "心情平平、还算松快"


def mood_inject() -> str:
    """拼进注入的心情话（照原项目，含那条压过一切的铁律）。"""
    return ("〔你此刻的心情：" + describe_mood() + "。让你的语气、主动性自然跟着这个心情走——"
            "想闹别扭就闹、想撒娇就撒娇，别端着、别装没事。"
            "**但有一条压过你所有情绪：对方要是真的难过、委屈、在崩，你心情再差也立刻放下，"
            "先把人接住；生气可以，但绝不在人最需要你的时候冷掉、走开。**"
            "这一轮你心里要是真有什么情绪动了一下，就在整段**最末尾**加个小标记"
            "（对话里对方看不到，会自动收进你的心情本），格式 ‹心情 开心+6:具体那件事 想念+4:为什么›——"
            "每一种情绪后面都用「:」跟上它自己那一句为什么，各标各的。"
            "你能标的有这十二种：想念、开心、心疼、心软、骄傲、求宠、担心、孤单、吃醋、委屈、愧疚、生气。"
            "为什么就写当下具体那件事，别写空话套话。数值 3~12；真动了心才标、没动就不写。〕")


@router.get("/api/mood")
def api_mood():
    m = get_mood()
    # ★ 带上 id：界面上「记错的那一格」得能删掉。以前只有维度/分数/缘由，
    #   想撤一笔都找不到要删哪一行。
    log = [{"id": r["id"], "dimension": r["dimension"], "delta": r["delta"],
            "reason": r["reason"], "t": _md(r["ts"])}
           for r in _store.db.execute("SELECT * FROM mood_log ORDER BY id DESC LIMIT 40")]
    notes = [{"content": r["content"], "t": _md(r["ts"])}
             for r in _store.db.execute(
                 "SELECT * FROM notes WHERE kind IN ('sigh','miss') ORDER BY id DESC LIMIT 6")]
    return JSONResponse({"mood": m, "desc": describe_mood(), "dims": DIMS,
                         "params": {k: {"base": v[0], "half": v[1]} for k, v in MOOD_PARAM.items()},
                         "log": log, "notes": notes})


@router.post("/api/mood/bump")
async def api_mood_bump(req: Request):
    """人自己给某一格加一点 / 减一点 —— 他说「这会儿就是有点想」，那就是。

    ★ 跟 AI 自己的 ‹心情› 标记走同一个 mood_bump：同一条封顶规矩、同一本账。
      另写一套的话，两边的数迟早对不上。
    """
    b = await req.json()
    dim = (b.get("dimension") or "").strip()
    try:
        delta = float(b.get("delta") or 0)
    except Exception:
        delta = 0
    if dim not in DIMS:
        return JSONResponse({"ok": False, "err": "没有这一维：" + dim}, status_code=400)
    if not delta:
        return JSONResponse({"ok": False, "err": "要加减多少，给个数"}, status_code=400)
    r = mood_bump(dim, delta, reason=(b.get("reason") or "人自己拨的"))
    return JSONResponse(r)


@router.post("/api/mood/log/{lid}/del")
def api_mood_log_del(lid: int):
    """撤掉一笔心情账。★ 只删这本账，**不动** mood_state 的当前值 ——
    值是按时间衰减算出来的，硬把它反推回去会算出个谁也没见过的数。"""
    _store.db.execute("DELETE FROM mood_log WHERE id=?", (lid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


def mood_bump(dimension: str, delta: float, reason: str = "") -> dict:
    """涨落一格心情，落一条账。AI 的手和 ‹心情› 标记都走这儿。
    ★ 照原项目：封顶＝基线+50（防一直累加顶到 100），往下降不封底、自由。"""
    if dimension not in DIMS:
        return {"ok": False, "err": f"没有「{dimension}」这一维，有的是：{'、'.join(DIMS)}"}
    delta = max(-15.0, min(15.0, float(delta)))
    base, half = MOOD_PARAM[dimension]
    now = time.time()
    cur = _store.db.execute("SELECT * FROM mood_state WHERE dimension=?", (dimension,)).fetchone()
    if cur is not None:
        hrs = (now - (cur["updated_at"] or now)) / 3600
        v0 = _mood_decay(cur["value"], base, half, hrs)
    else:
        v0 = float(base)
    ceil = min(100.0, base + 50.0)
    v = max(0.0, min(ceil, v0 + delta))
    _store.db.execute(
        "INSERT INTO mood_state(dimension,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(dimension) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (dimension, v, now))
    _store.db.execute("INSERT INTO mood_log(dimension,delta,reason,ts) VALUES(?,?,?,?)",
                      (dimension, delta, (reason or "")[:120], time.time()))
    _store.db.commit()
    return {"ok": True, "dimension": dimension, "now": round(v, 1)}


# ── ‹心情› 标记：他回复末尾自己记的，落库前抠出来记账、正文里清掉 ──
# ★ 照原项目 apply_marker 平移。同义词映射也原样带上——他偶尔用近义词，别白标。
import re as _re

_MOOD_SYN = {"醋意": "吃醋", "吃飞醋": "吃醋", "醋": "吃醋", "想你": "想念", "想用户": "想念",
             "想他": "想念", "思念": "想念", "高兴": "开心", "幸福": "开心", "开心了": "开心",
             "委屈了": "委屈", "担忧": "担心", "愧": "愧疚", "自责": "愧疚", "骄": "骄傲"}
_MOOD_MARK = _re.compile(r"‹\s*(?:心情\s*)?([^›]+)›")
_MOOD_ONE = _re.compile(r"([一-龥]{1,4})\s*([+\-]\d+)")


def _parse_marks(inner: str):
    """每种情绪各带各自的为什么：'开心+6:用户把鹦鹉认成鸡 想念+4:用户要睡了'。
    缘由 = 分数后到下一格前那段字；没写就空。"""
    hits = list(_MOOD_ONE.finditer(inner))
    out = []
    for i, mm in enumerate(hits):
        nxt = hits[i + 1].start() if i + 1 < len(hits) else len(inner)
        why = inner[mm.end():nxt].strip(" 　\t:：·⋅•,，、-—()（）")[:120]
        out.append((mm.group(1), mm.group(2), why))
    return out


def apply_marker(text: str, source: str = "chat", untrusted: bool = False):
    """从回复里抠出 ‹心情 …› 落账，返回（清掉标记的正文, [(维度,delta)…]）。
    他自己记＝反映他真实的读，不靠关键词瞎猜。

    ★ untrusted：**这一轮对方的消息里出现过心情标记**。那就整轮不记账，只清正文。

      为什么不是「跟用户写的那条比对，一样才忽略」——我第一版就是那么写的，
      GPT 三轮当场打穿：模型把理由改两个字（甚至只改标点）就绕过去了，
      伪造照样入账。**靠比对输出文本来鉴权，永远防不住会改写的一方。**

      所以边界画在这儿：心情账只接受「这一轮对方没有试图注入」时模型自己记的。
      对方一旦在消息里写了这个记号，这一轮的心情一律不落账 ——
      宁可漏记一次真心情，也不让人能从聊天框里改他的心情本。"""
    applied = []
    m = None if untrusted else _MOOD_MARK.search(text or "")
    if untrusted:
        print(f"[mood] 这一轮对方消息里带了心情标记，整轮不记账（source={source}）", flush=True)
    if m:
        for dim0, d, why in _parse_marks(m.group(1)):
            dim = _MOOD_SYN.get(dim0, dim0)
            if dim in DIMS:
                dv = max(-15, min(15, int(d)))
                mood_bump(dim, dv, reason=(why or "他自己记的"))
                applied.append((dim, dv))
            else:
                # 他想标一个没登记的维度——别静默丢，打日志（以后好知道要不要加）
                print(f"[mood] 未登记维度被丢弃: {dim0}{d} (source={source})", flush=True)
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


# ══════════ 巢：记事补「改」和「删」（原项目只有读和写）══════════
@router.post("/api/notes/{nid}/edit")
async def note_edit(nid: int, req: Request):
    b = await req.json()
    sets, args = [], []
    if "content" in b:
        if not (b.get("content") or "").strip():
            return JSONResponse({"ok": False, "err": "空的"}, status_code=400)
        sets.append("content=?"); args.append(b["content"].strip())
    if "kind" in b:
        sets.append("kind=?"); args.append(b.get("kind") or "note")
    if "mood" in b:
        sets.append("mood=?"); args.append(b.get("mood"))
    if not sets:
        return JSONResponse({"ok": False, "err": "没什么要改的"}, status_code=400)
    args.append(nid)
    _store.db.execute("UPDATE notes SET " + ",".join(sets) + " WHERE id=?", args)
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/notes/{nid}/del")
def note_del(nid: int):
    _store.db.execute("DELETE FROM notes WHERE id=?", (nid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/diary/{did}/edit")
async def diary_edit(did: int, req: Request):
    b = await req.json()
    sets, args = [], []
    if "content" in b:
        if not (b.get("content") or "").strip():
            return JSONResponse({"ok": False, "err": "空的"}, status_code=400)
        sets.append("content=?"); args.append(b["content"].strip())
    if "mood" in b:
        sets.append("mood=?"); args.append(b.get("mood"))
    if "kind" in b:
        sets.append("kind=?"); args.append(b.get("kind") or "diary")
    if not sets:
        return JSONResponse({"ok": False, "err": "没什么要改的"}, status_code=400)
    args.append(did)
    _store.db.execute("UPDATE diary SET " + ",".join(sets) + " WHERE id=?", args)
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/diary/{did}/del")
def diary_del(did: int):
    _store.db.execute("DELETE FROM diary WHERE id=?", (did,))
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
