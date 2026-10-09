"""聊天与记忆的「视图」接口 —— 同一份数据的另外几种看法。

聊天记录按天翻、收藏、热力图月历、全局搜索、记忆总览/分层 ——
这些都不是新数据，是 `store` 里那两张表的聚合。所以放在一个独立模块里，
**字段名照原项目一个不改**：前端就是按那些字段写的。

★ 时间统一用本地时区的日期字符串（YYYY-MM-DD）。用 UTC 的话，
  晚上八点之后说的话会被归到「明天」，热力图看着永远差一天。
"""
from __future__ import annotations

import json
import time
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import windows as _winflags
from . import datadir as _datadir
from . import assistants as _asst

router = APIRouter()
_store = None          # server 启动时注入


def bind(store) -> None:
    global _store
    _store = store
    # 这几列是后加的：老库没有就补上（幂等）
    for ddl in ("ALTER TABLE turns ADD COLUMN starred INTEGER DEFAULT 0",
                "ALTER TABLE turns ADD COLUMN hidden INTEGER DEFAULT 0",
                "ALTER TABLE turns ADD COLUMN hidden_parts TEXT"):
        try:
            _store.db.execute(ddl)
            _store.db.commit()
        except Exception:
            pass


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts or 0).strftime("%Y-%m-%d")


def _hm(ts: float) -> str:
    return datetime.fromtimestamp(ts or 0).strftime("%H:%M")


LAYER_MAP = [
    ("L3", "核心", "关系基石"),
    ("L2", "长期", "重要的事"),
    ("L1", "短期", "最近的事"),
    ("manual", "校准", "你定的说话规矩 · 可改"),
]


# ── 聊天的三种看法 ────────────────────────────────────────
@router.get("/api/chat/heat")
def chat_heat(who: str = ""):
    """热力图：按天数对话条数。前端拿它画月历。"""
    heat: dict[str, int] = {}
    for r in _store.db.execute("SELECT ts FROM turns"):
        d = _day(r["ts"])
        heat[d] = heat.get(d, 0) + 1
    return JSONResponse({"heatmap": heat})


@router.get("/api/chat/day/{day}")
def chat_day(day: str, who: str = "", withhidden: int = 0):
    """某一天的完整记录。"""
    items = []
    for r in _store.db.execute("SELECT * FROM turns ORDER BY id"):
        if _day(r["ts"]) != day:
            continue
        try:
            files = json.loads(r["files"]) if r["files"] else []
        except Exception:
            files = []
        items.append({"id": r["id"], "role": r["role"], "content": r["content"],
                      "think": r["think"] or "", "starred": bool(r["starred"]),
                      "files": files,
                      "src": "web", "audio_url": None, "hidden": False,
                      "hidden_parts": None, "t": _hm(r["ts"])})
    return JSONResponse({"items": items, "hidden_count": 0})


@router.get("/api/chat/starred")
def chat_starred(who: str = ""):
    """收藏。★ 每条带 `ask`：收藏他那句话时，你说了什么他才这样说 ——
    没有上文的一句话，过几个月再看会不知道当时在聊什么。"""
    rows = list(_store.db.execute(
        "SELECT * FROM turns WHERE starred=1 ORDER BY id DESC LIMIT 200"))
    items = []
    for r in rows:
        ask = None
        if r["role"] != "user":
            u = _store.db.execute(
                "SELECT content FROM turns WHERE role='user' AND id<? ORDER BY id DESC LIMIT 1",
                (r["id"],)).fetchone()
            ask = u["content"] if u else None
        items.append({"id": r["id"], "role": r["role"], "content": r["content"],
                      "think": r["think"] or "", "starred": True, "src": "web",
                      "audio_url": None,
                      "t": datetime.fromtimestamp(r["ts"] or 0).strftime("%Y-%m-%d %H:%M"),
                      "ask": ask})
    return JSONResponse({"items": items})


def _split_say(t: str) -> list[str]:
    """跟前端 splitSay 一模一样 —— 撤第几句按这个下标记，两边不一致会撤错句子。"""
    t = "" if t is None else str(t)
    if "|||" in t:
        return [x.strip() for x in t.split("|||") if x.strip()]
    return [t]


@router.post("/api/chat/{cid}/hide")
async def chat_hide(cid: int, req: Request):
    """藏一句 / 藏一轮 / 放回去。

    形状照原项目：{hidden:bool, part?:int, seg?:str}。
    · 带 part = 只撤那一个泡泡（seg 是那句正文，用来核对下标 —— 流式刚上屏的
      下标是前端自己数的，不核会撤错句子）
    · 不带 part 且 hidden=true = 整轮
    · hidden=false 不带 part = 放回去，两个标记一起清
    ★ 藏只管界面。记忆召回读同一张表，不看这两列。"""
    b = await req.json()
    r = _store.db.execute("SELECT content, hidden_parts FROM turns WHERE id=?", (cid,)).fetchone()
    if r is None:
        return JSONResponse({"ok": False, "error": "没有这条"}, status_code=404)
    hidden = bool(b.get("hidden", True))
    part = b.get("part")
    if not hidden and part is None:
        _store.db.execute("UPDATE turns SET hidden=0, hidden_parts=NULL WHERE id=?", (cid,))
    elif part is None:
        _store.db.execute("UPDATE turns SET hidden=1 WHERE id=?", (cid,))
    else:
        segs = _split_say(r["content"])
        part = int(part)
        seg = (b.get("seg") or "").strip()
        if seg and not (0 <= part < len(segs) and segs[part].strip() == seg):
            # 下标对不上就按正文找 —— 宁可多找一步，不撤错句子
            hits = [i for i, x in enumerate(segs) if x.strip() == seg]
            if not hits:
                return JSONResponse({"ok": False, "error": "对不上是哪一句"}, status_code=409)
            part = hits[0]
        parts = set(json.loads(r["hidden_parts"]) if r["hidden_parts"] else [])
        parts.add(part) if hidden else parts.discard(part)
        if len(parts) >= len(segs):
            _store.db.execute("UPDATE turns SET hidden=1, hidden_parts=NULL WHERE id=?", (cid,))
        else:
            _store.db.execute("UPDATE turns SET hidden_parts=? WHERE id=?",
                              (json.dumps(sorted(parts)), cid))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/chat/{cid}/del")
async def chat_del(cid: int):
    """真删。人说删就是删。"""
    _store.db.execute("DELETE FROM turns WHERE id=?", (cid,))
    _store.db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/chat/{cid}/star")
async def chat_star(cid: int):
    """按一下切换。返回按完的状态，前端要拿它把星点亮/熄灭。"""
    r = _store.db.execute("SELECT starred FROM turns WHERE id=?", (cid,)).fetchone()
    if r is None:
        return JSONResponse({"error": "没有这条"}, status_code=404)
    now = 0 if r["starred"] else 1
    _store.db.execute("UPDATE turns SET starred=? WHERE id=?", (now, cid))
    _store.db.commit()
    return JSONResponse({"ok": True, "starred": bool(now)})


# ── 搜索 ──────────────────────────────────────────────────
@router.get("/api/search")
def search(q: str = "", who: str = ""):
    """一个词翻遍聊天和记忆，结果带类型标签（前端按标签分组）。"""
    q = (q or "").strip()
    if not q:
        return JSONResponse({"items": []})
    out = []
    pat = f"%{q}%"
    for r in _store.db.execute(
            "SELECT * FROM turns WHERE content LIKE ? ORDER BY id DESC LIMIT 40", (pat,)):
        out.append({"id": r["id"], "kind": "聊天·" + ("你" if r["role"] == "user" else "他"),
                    "content": (r["content"] or "")[:200], "think": r["think"] or "",
                    "t": _day(r["ts"]), "starred": bool(r["starred"]), "src": "web"})
    labs = {k: lab for k, lab, _ in LAYER_MAP}
    for m in _store.search_memories(q, limit=40):
        out.append({"kind": labs.get(m.layer, m.layer),
                    "content": m.content[:200], "t": _day(m.ts)})
    return JSONResponse({"items": out})


# ── 记忆字云的数据 ────────────────────────────────────────
@router.get("/api/memories/cloud")
def memories_cloud(limit: int = 1600, cut: int = 100):
    """★ 口径跟 /api/memory/overview 完全一致 —— 字云就摆在总览四栏上头，
    两个数字必须对得上（原项目逮到过一次差 57 条的账）。"""
    cut = max(40, min(400, cut))
    mems = _store.all_memories()
    mems.sort(key=lambda m: (m.ts or 0))
    mem, by = [], {}
    for i, m in enumerate(mems[:limit]):
        by[m.layer] = by.get(m.layer, 0) + 1
        mem.append({"i": i, "id": m.id, "text": m.content[:cut], "len": len(m.content),
                    "layer": m.layer, "day": _day(m.ts), "ref": 0, "str": 1.0,
                    "tags": ",".join(m.tags or [])})
    return JSONResponse({"n": len(mem), "layers": by, "memories": mem})


@router.get("/api/memories/cloud/{mid}")
def memories_cloud_one(mid: int):
    m = next((x for x in _store.all_memories() if x.id == mid), None)
    if not m:
        return JSONResponse({"ok": False}, status_code=404)
    return JSONResponse({"ok": True, "id": m.id, "text": m.content, "layer": m.layer,
                         "day": _day(m.ts),
                         "t": datetime.fromtimestamp(m.ts or 0).strftime("%Y-%m-%d %H:%M"),
                         "ring": "", "tags": m.tags or []})


@router.get("/api/memories/cloud/{mid}/near")
def memories_cloud_near(mid: int, k: int = 6):
    """选中一条时找「跟它有关的」画连线。原项目用向量近邻；
    开源版没有向量，用同一套 2-gram 重合度顶上 —— 形状一致，规模小时效果够。"""
    mems = _store.all_memories()
    me = next((x for x in mems if x.id == mid), None)
    if not me:
        return JSONResponse({"items": []})
    terms = set(_store._terms(me.content))
    scored = []
    for m in mems:
        if m.id == mid or not m.content:
            continue
        n = sum(1 for t in _store._terms(m.content) if t in terms)
        if n:
            scored.append((n, m))
    scored.sort(key=lambda x: -x[0])
    return JSONResponse({"items": [{"id": m.id, "sim": round(min(0.99, n / 8), 3)}
                                   for n, m in scored[:max(1, min(int(k), 12))]]})


# ── 记忆的两种看法 ────────────────────────────────────────
@router.get("/api/memory/overview")
def memory_overview():
    mems = _store.all_memories()
    counts: dict[str, int] = {}
    for m in mems:
        counts[m.layer] = counts.get(m.layer, 0) + 1
    layers = [{"key": k, "label": lab, "sub": sub, "count": counts.get(k, 0)}
              for k, lab, sub in LAYER_MAP]
    heat: dict[str, int] = {}
    for m in mems:
        d = _day(m.ts)
        heat[d] = heat.get(d, 0) + 1
    for r in _store.db.execute("SELECT ts FROM turns"):
        d = _day(r["ts"])
        heat[d] = heat.get(d, 0) + 1
    return JSONResponse({"total": len(mems), "layers": layers, "heatmap": heat})


def _mem_row(m) -> dict:
    return {"id": m.id, "layer": m.layer, "tags": ",".join(m.tags or []),
            "content": m.content, "day": _day(m.ts), "my_note": None}


@router.get("/api/memory/all")
def memory_all(layer: str = "", limit: int = 300):
    mems = _store.all_memories()
    if layer:
        mems = [m for m in mems if m.layer == layer]
    mems.sort(key=lambda m: (-(m.ts or 0), -(m.id or 0)))
    return JSONResponse({"items": [_mem_row(m) for m in mems[:min(int(limit), 500)]]})


@router.get("/api/memory/layer/{layer}")
def memory_layer(layer: str):
    mems = [m for m in _store.all_memories() if m.layer == layer]
    mems.sort(key=lambda m: (-(m.ts or 0), -(m.id or 0)))
    return JSONResponse({"items": [_mem_row(m) for m in mems[:200]]})
# ===== 离线自由时段：状态接口 =====
@router.get("/api/offline")
async def _api_offline_state():
    try:
        from . import offline as _off
        st = _off._state()
        # ★ 每扇窗的「离线模式」开关：这几拍轮不到哪扇窗，状态就说哪扇。
        #   `enabled` 仍是服务端那把总闸（OFFLINE_ENABLED），window_ok 是这一扇的开关，
        #   两个都开才真的会有它自己的一段时间。前端别拿一个当另一个。
        try:
            act_sid = _winflags.active_sid(_store)
            win_ok = _winflags.allows(_store, act_sid, "offline")
        except Exception:
            act_sid, win_ok = "main", True
        try:
            eng_ok = _off.engine_ok()
        except Exception:
            eng_ok = True
        return {
            "enabled": _off.enabled(),
            "active": bool(st.get("active")),
            "started": float(st.get("started") or 0),
            "last": float(st.get("last") or 0),
            "idle_min": _off.idle_min(),
            "window": st.get("sid") or act_sid,      # 这一场是记在哪扇窗名下的
            "active_window": act_sid,                # 你最近待的那扇窗
            "window_ok": bool(win_ok),
            # ★ 引擎还是桩（回声）时它不会开跑 —— 前端别把「什么都没发生」当坏了
            "engine_ok": bool(eng_ok),
        }
    except Exception as e:
        return {"enabled": False, "active": False, "started": 0, "last": 0,
                "err": str(e)[:120]}
# ===== 记忆手工编辑：读 / 存 / 删 =====
def _mem_fix_fts() -> None:
    """全文索引兜底重建（正常由触发器维护）"""
    try:
        _store.db.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
    except Exception:
        pass


@router.get("/api/memory/items")
async def _api_memory_items(limit: int = 500):
    try:
        rows = _store.db.execute(
            "SELECT id, content, layer, tags, ts FROM memories ORDER BY ts DESC LIMIT ?",
            (int(limit),)).fetchall()
        return {"items": [{"id": r["id"], "content": r["content"], "layer": r["layer"],
                           "tags": r["tags"], "ts": r["ts"]} for r in rows]}
    except Exception as e:
        return {"items": [], "err": str(e)[:160]}


@router.post("/api/memory/save")
async def _api_memory_save(req: Request):
    try:
        b = await req.json()
    except Exception:
        return {"ok": False, "err": "bad json"}
    content = (b.get("content") or "").strip()
    layer = (b.get("layer") or "L1").strip() or "L1"
    tags = b.get("tags") or "[]"
    mid = int(b.get("id") or 0)
    if not content:
        return {"ok": False, "err": "内容不能为空"}
    try:
        if mid:
            _store.db.execute("UPDATE memories SET content=?, layer=?, tags=? WHERE id=?",
                              (content, layer, tags, mid))
        else:
            import time as _t
            _store.db.execute("INSERT INTO memories(content, layer, tags, ts) VALUES(?,?,?,?)",
                              (content, layer, tags, _t.time()))
        _mem_fix_fts()
        _store.db.commit()
        return {"ok": True, "id": mid}
    except Exception as e:
        return {"ok": False, "err": str(e)[:200]}


@router.post("/api/memory/del")
async def _api_memory_del(req: Request):
    try:
        b = await req.json()
        mid = int(b.get("id") or 0)
        if not mid:
            return {"ok": False, "err": "缺 id"}
        _store.db.execute("DELETE FROM memories WHERE id=?", (mid,))
        _mem_fix_fts()
        _store.db.commit()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "err": str(e)[:200]}
# ===== offline：手动跑一场（?dry=1 只试跑，不落库、不改状态）=====
from . import offline as _offline

@router.post("/api/offline/run")
async def api_offline_run(dry: int = 0):
    import asyncio
    try:
        asyncio.ensure_future(_offline.tick(force=True, dry=bool(dry)))
    except Exception as e:
        return {"ok": False, "err": str(e)}
    return {"ok": True, "dry": bool(dry), "note": "看 journalctl -u lianhuan -f | grep -i offline"}
# ===== MCP 总管理：列表 / 加改删 / 试连 / 拨动 =====
# ★ 这一节是 `/api/mcp` 的**唯一**注册处（server.py 里再写一份会被这儿挡住 ——
#   FastAPI 按注册顺序匹配，views 的 router 先挂上；真撞过一次，白写半天）。
from fastapi import Body
from . import mcp_client as _mcp
from . import gate as _gate


def _caller_is_local(request: Request) -> bool:
    """这次请求是不是「明确允许的本机」。跟中间件里那道判断同一个口径 ——
    千万别在别处另写一套（两套口径迟早会对不上）。"""
    peer = request.client.host if request.client else ""
    addr = _gate.client_addr(peer, request.headers.get("x-forwarded-for", ""))
    here = _gate.local_addr(addr)
    return bool(here and (not _gate.on() or _gate.allow_local_commands()))


MCP_KINDS = {"http", "sse", "stdio"}


def _mcp_spec_from(b: dict) -> tuple:
    """把界面填的那份变成一条装配单。返回 (spec, 错误)。"""
    kind = (b.get("kind") or "http").strip().lower()
    if kind not in MCP_KINDS:
        return {}, "连接方式只有 Streamable HTTP / SSE / 本机命令三种"
    if kind == "stdio":
        cmdline = (b.get("command") or "").strip()
        if not cmdline:
            return {}, "本机命令要填（比如 npx -y 某个包）"
        parts = cmdline.split()
        return {"command": parts[0], "args": parts[1:], "env": b.get("env") or {}}, ""
    url = (b.get("url") or "").strip()
    if not url:
        return {}, "地址要填（那一串 https://…/mcp 或 …/sse）"
    if not url.lower().startswith(("http://", "https://")):
        return {}, "地址要以 http:// 或 https:// 开头"
    headers = {}
    for pair in (b.get("headers") or []):
        if isinstance(pair, dict):                       # [{"name":…, "value":…}]
            headers[str(pair.get("name") or "")] = pair.get("value") or ""
        elif isinstance(pair, (list, tuple)) and len(pair) == 2:   # 也认 {名字: 值}
            headers[str(pair[0] or "")] = pair[1] or ""
    return {"url": url, "headers": headers}, ""


@router.get("/api/mcp")
async def api_mcp_list(request: Request):
    """列 MCP server。★ 请求头只回**名字和末四位** —— 里面往往就是 Bearer token。

    `local` 是「这次请求是不是本机」，界面拿它决定「本机命令」那一档能不能选
    （起进程只在本机开放，见 gate.LOCAL_ONLY 那条注释）。"""
    return {"ok": True, "servers": _mcp.status(), "local": _caller_is_local(request)}


@router.post("/api/mcp/save")
async def api_mcp_save(request: Request):
    """加一条 / 改一条 / 删一条。

    ★ 本机命令（stdio）只能在本机操作 —— 那是**起进程**，跟 /api/mcp/add 同一条线
      （手机上点「保存」要的是一句能照着做的话，不是一条规矩）。
      Streamable HTTP / SSE 不在这条线里：它不发命令，只是这台机器往外连一个你
      自己填的地址、带你自己填的头 —— 所以手机上也能加。"""
    import re as _re
    b = await request.json()
    name = _re.sub(r"[^\w-]", "", (b.get("name") or ""))[:24]
    if not name:
        return JSONResponse({"ok": False, "error": "给它起个名字（字母数字和 _-）"},
                            status_code=400)
    old = _mcp.spec_of(name)
    old_kind = (old.get("type") or ("http" if old.get("url") else "stdio")).strip().lower()
    local = _caller_is_local(request)

    if b.get("remove"):
        # 已存着的那条是不是「本机命令」由**服务端**说了算，不听调用方报的 kind
        if old_kind == "stdio" and not local:
            return JSONResponse({"ok": False, "error": "「本机命令」那条只能在这台机器上删 —— "
                                                       "它会把这台机器上的那个进程停掉。"},
                                status_code=403)
        _mcp.drop_server(name)
        return {"ok": True, "removed": name}

    spec, err = _mcp_spec_from(b)
    if err:
        return JSONResponse({"ok": False, "error": err}, status_code=400)
    kind = (b.get("kind") or "http").strip().lower()
    if kind == "stdio" and not local:
        return JSONResponse({"ok": False, "error": "「本机命令」只能在这台机器上（127.0.0.1）"
                                                   "用本机页面加 —— 它会在这台机器上起一个进程。"
                                                   "手机上想加 MCP，用 Streamable HTTP 或 SSE 那种地址。"},
                            status_code=403)
    old_name = _re.sub(r"[^\w-]", "", (b.get("old_name") or ""))[:24]
    if old_name and old_name != name:
        _mcp.drop_server(old_name)          # 改了名字＝把旧那条摘掉，别留僵尸
    if kind == "stdio":
        _mcp.save_server(name, spec["command"], spec["args"], spec.get("env") or {})
    else:
        _mcp.save_http(name, spec["url"], kind, spec["headers"])
    await _mcp.start_all()                  # 立刻连一次（连不上也照样存下，错误照实回）
    st = next((x for x in _mcp.status() if x["name"] == name), None)
    return {"ok": bool(st and st["ok"]), "server": st}


@router.post("/api/mcp/probe")
async def api_mcp_probe(request: Request):
    """拿**还没保存**的这份配置试连一次 —— 不落盘、不留连接。

    连上了就报它认到几个工具；连不上就把真实原因（HTTP 401 / 地址不对 / 超时）说出来。"""
    b = await request.json()
    spec, err = _mcp_spec_from(b)
    if err:
        return JSONResponse({"ok": False, "error": err}, status_code=400)
    kind = (b.get("kind") or "http").strip().lower()
    if kind == "stdio" and not _caller_is_local(request):
        return JSONResponse({"ok": False, "error": "「本机命令」只能在这台机器上试 —— 它会起进程"},
                            status_code=403)
    if kind == "stdio":
        mcp_spec = {"command": spec["command"], "args": spec["args"], "env": spec.get("env") or {}}
    else:
        mcp_spec = {"url": spec["url"], "type": "sse" if kind == "sse" else "http"}
        if spec["headers"]:
            mcp_spec["headers"] = spec["headers"]
    out = await _mcp.probe(mcp_spec)
    return {"ok": bool(out.get("ok")), "error": out.get("err") or "",
            "tools": out.get("tools") or []}


@router.post("/api/mcp/toggle")
async def api_mcp_toggle(payload: dict = Body(...)):
    name = str(payload.get("name") or "")
    on = bool(payload.get("enabled"))
    if not name or not _mcp.set_enabled(name, on):
        return {"ok": False, "err": "没有这个 MCP"}
    await _mcp.start_all()              # 立刻连上 / 断开
    return {"ok": True, "servers": _mcp.status()}
# ===== 工具调用记录（自己读文件，不依赖新模块）=====
@router.get("/api/tools/log")
async def api_tools_log(limit: int = 50):
    import json as _j
    import os as _os
    from pathlib import Path as _P
    p = _datadir.home_dir() / "tool_calls.jsonl"
    try:
        lines = p.read_text(encoding="utf-8").splitlines()[-max(1, min(int(limit or 50), 300)):]
    except Exception:
        lines = []
    out = []
    for ln in reversed(lines):
        try:
            out.append(_j.loads(ln))
        except Exception:
            continue
    return {"ok": True, "calls": out}

# ══════════ 巢（Nest）前端专用：多窗口会话 ══════════
def _nest_sid(r) -> str:
    return (r["session_id"] or "").strip() or "main"


@router.get("/api/nest/threads")
def nest_threads(limit: int = 80, with_assistant: int = 0):
    """所有对话窗口（按 session_id 分组）。空 session_id = 老数据 = 主窗口。

    `with_assistant=1` 时每个窗口多带一个 `assistant`（挂在哪位助手下面）——
    助手管理那一页要按助手给窗口分组，别让前端再猜一遍。"""
    lim = max(1, min(int(limit or 80), 300))
    rows = list(_store.db.execute("SELECT * FROM turns ORDER BY id DESC LIMIT 4000"))
    seen, out = {}, []
    for r in reversed(rows):
        s = _nest_sid(r)
        it = seen.get(s)
        if it is None:
            seen[s] = it = {"sid": s, "n": 0, "t0": r["ts"], "t1": r["ts"], "title": ""}
            out.append(it)
        it["n"] += 1
        it["t1"] = r["ts"]
        if not it["title"] and r["role"] == "user" and (r["content"] or "").strip():
            it["title"] = (r["content"] or "").replace("|||", " ").strip()[:26]
    out.sort(key=lambda x: -(x["t1"] or 0))
    for it in out:
        it["title"] = it["title"] or "（空窗口）"
        if with_assistant:
            a = _asst.assistant_of(_store, it["sid"])
            it["assistant"] = a["id"] if a else ""
    return JSONResponse({"items": out[:lim]})


# ══════════ 助手管理：一位助手下面挂几扇窗 ══════════
# ★ 语义和数据都在 core/assistants.py 一处定义（含「没配过助手＝老行为」那条兼容线），
#   这里只管读和写。
@router.get("/api/assistants")
def assistants_list():
    items = _asst.all_items(_store)
    return JSONResponse({"ok": True, "items": items, "enabled": bool(items),
                         "default_id": _asst.default_id(_store)})


@router.post("/api/assistants/save")
async def assistants_save(req: Request):
    try:
        b = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "err": "读不懂这段 JSON"}, status_code=400)
    aid = str(b.get("id") or "").strip()
    fields = {}
    for k in ("name", "sign", "avatar", "prompt"):
        if k in b:
            fields[k] = b[k]
    if "mcp" in b:
        # null / "all" ＝ 不限（所有连上的 MCP 都给）；数组 ＝ 只给这几个
        v = b.get("mcp")
        fields["mcp"] = None if v in (None, "all", "全部") else [str(x) for x in (v or [])]
    if aid:
        out = _asst.save(_store, aid, **fields)
        if out is None:
            return JSONResponse({"ok": False, "err": "没有这位助手"}, status_code=404)
        return JSONResponse({"ok": True, "item": out})
    item = _asst.create(_store, **fields)
    return JSONResponse({"ok": True, "item": item})


@router.post("/api/assistants/del")
async def assistants_del(req: Request):
    b = await req.json()
    ok = _asst.remove(_store, str(b.get("id") or ""))
    return JSONResponse({"ok": ok, "items": _asst.all_items(_store)},
                        status_code=(200 if ok else 404))


@router.post("/api/assistants/window")
async def assistants_window(req: Request):
    """把一个窗口挂到某位助手名下；`id` 空＝摘下来（回到第一位助手名下）。"""
    b = await req.json()
    sid = _asst.norm_sid(b.get("sid"))
    aid = str(b.get("id") or "").strip()
    if not aid:
        _asst.detach_window(_store, sid)
    elif not _asst.attach_window(_store, sid, aid):
        return JSONResponse({"ok": False, "err": "没有这位助手"}, status_code=404)
    return JSONResponse({"ok": True, "items": _asst.all_items(_store)})


@router.get("/api/assistants/who")
def assistants_who(sid: str = "main"):
    """这个窗口现在挂在哪位助手下面（聊天顶栏那颗身份牌要用）。"""
    a = _asst.assistant_of(_store, sid)
    if a is None:
        return JSONResponse({"ok": True, "enabled": False, "assistant": None})
    return JSONResponse({"ok": True, "enabled": True, "assistant": a})


@router.get("/api/nest/thread")
def nest_thread(sid: str = "main", limit: int = 80, before: int = 0):
    """某个窗口的历史（带 think / tools / ts / 隐藏标记）。"""
    lim = max(1, min(int(limit or 80), 400))
    key = (sid or "main").strip() or "main"
    sql = ("SELECT * FROM turns WHERE COALESCE(NULLIF(TRIM(session_id),''),'main')=? "
           + ("AND id<? " if before else "") + "ORDER BY id DESC LIMIT ?")
    args = (key, int(before), lim) if before else (key, lim)
    rows = list(_store.db.execute(sql, args))
    rows.reverse()
    items = []
    for r in rows:
        try:
            tools = json.loads(r["tools"]) if r["tools"] else []
        except Exception:
            tools = []
        try:
            parts = json.loads(r["hidden_parts"]) if r["hidden_parts"] else None
        except Exception:
            parts = None
        try:
            files = json.loads(r["files"]) if r["files"] else []
        except Exception:
            files = []
        items.append({"id": r["id"], "role": r["role"], "content": r["content"],
                      "think": r["think"] or "", "tools": tools, "files": files,
                      "starred": bool(r["starred"]), "ts": r["ts"],
                      "hidden": bool(r["hidden"]), "parts": parts,
                      # ★ 「重新生成」把它换掉之后，那条旧回复被标成 spoken=0：
                      #   界面上还看得见，但它自己不再记得说过（前端拿这个画个小标）。
                      #   只可能是 assistant —— spoken=0 的 user 行是机器拼的指令，
                      #   那种行 hidden=1，前端根本不画。
                      "superseded": bool(r["role"] == "assistant"
                                         and not (r["spoken"] if r["spoken"] is not None else 1))})
    return JSONResponse({"items": items, "sid": key})

# ══════════ 巢：删掉一个对话窗口 ══════════
@router.post("/api/nest/thread/del")
async def nest_thread_del(req: Request):
    """删掉某个窗口的全部聊天记录。主窗口（老记录）不给整个删。"""
    b = await req.json()
    sid = (b.get("sid") or "main").strip() or "main"
    if sid == "main":
        return JSONResponse({"ok": False, "err": "主窗口是老记录，不能整个删（可以逐条删）"},
                            status_code=400)
    n = _store.db.execute("DELETE FROM turns WHERE TRIM(session_id)=?", (sid,)).rowcount
    _store.db.commit()
    return JSONResponse({"ok": True, "n": n})


# ══════════ 巢：每个对话窗口的两枚开关（主动消息 · 离线自由时段）══════════
# ★ 语义、默认值和「哪扇窗算你现在这扇」都在 core/windows.py 里，一个地方定义；
#   这里只负责读和写。书房小窗走 book_chat，不进这套开关。
@router.get("/api/nest/window")
def nest_window_get(sid: str = "main"):
    try:
        f = _winflags.flags(_store, sid)
        act = _winflags.active_sid(_store)
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:160],
                             "sid": _winflags.norm_sid(sid)}, status_code=500)
    return JSONResponse({"ok": True, "active": act, "active_sid": act,
                         "focus": _winflags.focus_sid(_store),
                         "labels": _winflags.LABELS, "hints": _winflags.HINTS, **f})


@router.post("/api/nest/focus")
async def nest_focus_set(req: Request):
    """界面切窗口时报一声「我现在在哪扇窗」。

    ★ 有了它，那两枚开关才真的是「这一扇窗的」：人切过去还没开口就走了，
      也按他现在开着的那扇算。报不上来（老前端 / 网络抖）就退回按最后说话的
      地方猜 —— 是个增强，不是必需。
    """
    try:
        b = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "err": "读不懂这段 JSON"}, status_code=400)
    sid = b.get("sid")
    if sid is None:
        return JSONResponse({"ok": False, "err": "缺 sid"}, status_code=400)
    try:
        _winflags.set_focus(_store, sid)
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:160]}, status_code=500)
    return JSONResponse({"ok": True, "active": _winflags.active_sid(_store)})


@router.post("/api/nest/window")
async def nest_window_set(req: Request):
    try:
        b = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "err": "读不懂这段 JSON"}, status_code=400)
    sid = _winflags.norm_sid(b.get("sid"))
    kw = {k: b[k] for k in _winflags.FLAG_KEYS if k in b}
    if not kw:
        return JSONResponse({"ok": False, "err": "没有要拨的开关"}, status_code=400)
    try:
        f = _winflags.set_flags(_store, sid, **kw)
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:160]}, status_code=500)
    return JSONResponse({"ok": True, **f})


@router.get("/api/nest/windows")
def nest_windows_all():
    """所有被拨过的窗口。界面上给窗口列表画小标用 —— 没拨过的就是默认「开」。"""
    try:
        return JSONResponse({"ok": True, "items": _winflags.all_flags(_store),
                             "active": _winflags.active_sid(_store)})
    except Exception as e:
        return JSONResponse({"ok": False, "err": str(e)[:160], "items": {}},
                            status_code=500)
