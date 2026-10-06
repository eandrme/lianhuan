"""离线自由时段 —— 它自己的一段时间。（v9 · 单文件重写）

保留的口子（用户定的）：
· 不向用户汇报任何东西（错误除外）
· 不读对话上下文；只读「对方是谁」这一层侧写
· 不写任何记忆库 —— 主库一个字节都不落（只读了「你最后说话的时间」）
· 工具：strict / readonly / all / 逗号白名单，外接 MCP 工具永远放行
· 这段经历只有它自己保留，进独立的加密私密库（data/private.db）
· 单向渗透：悄悄改变前台人格，用户看不到内容（强度可调）
· 留一份动作审计：只记 时间/工具/成败，不记内容

一段「自由时段」怎么跑（A 方案：真的多轮）：
  1) 开始  静默 ≥ OFFLINE_IDLE_MIN，且这一轮离开还没跑过，且过了冷却/频次/静默时段
  2) 行动  最多 OFFLINE_MAX_TURNS 轮，手边有工具；每轮之间检查「你回来了 / 到点」
  3) 收尾  单独一轮，不带工具，只让它写两三句给自己（这段文字才是唯一留下来的东西）
  4) 落库  加密写进 priv，日志里留一行「私密库 #行号」
  5) 状态  data/offline_state.json + data/plays/_offline.json（前端徽章读）

.env 旋钮：
  OFFLINE_ENABLED=1          总开关
  OFFLINE_IDLE_MIN=30        静默多久算「你不在」
  OFFLINE_COOLDOWN_MIN=30    一场结束后多久内不再开
  OFFLINE_EVERY_HOURS=0      两场之间至少隔几小时；0 = 关闭这条（建议先 0）
  OFFLINE_MAX_MIN=10         单场硬上限（含收尾；收尾另有 90 秒宽限）
  OFFLINE_MAX_TURNS=6        单场最多几轮行动
  OFFLINE_TOOLS=readonly     strict | readonly | all | 逗号白名单（MCP 永远放行）
  OFFLINE_PERMEATE=0.5       单向渗透强度 0~1
  OFFLINE_PRIVATE_HISTORY=4  每场开头带几段自己以前留下的话
  OFFLINE_QUIET=23:30,07:00  夜间静默（逗号或短横线都认；空 = 不启用）
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime
import json
import os
import time
from pathlib import Path

from .protocol import SAY

# ───────────────────── 基础 ─────────────────────

_DB = os.environ.get("LIANHUAN_DB", "data/lianhuan.db")
DATA_DIR = Path(_DB).parent

READONLY_TOOLS = {
    "search_memory", "read_timeline", "read_calendar", "read_workbook",
    "list_books", "read_chapter", "list_plays", "list_packs", "list_my_tools",
}
STRICT_TOOLS = {"list_my_tools", "list_packs"}

_STAT = {"tools": []}            # 本场工具流水（计数 + 写回它自己的上下文）
_SEEN = {"t": 0.0, "v": 0.0}     # last_seen 的 2 秒缓存，别每个事件都开一次库


@contextlib.contextmanager
def _nullctx():
    yield


def _log(msg: str) -> None:
    print(f"[offline] {msg}", flush=True)


# ───────────────────── 配置（全走环境变量） ─────────────────────

def _flag(name: str, default: str = "0") -> bool:
    return (os.environ.get(name, default) or "").strip().lower() in ("1", "true", "on", "yes")


def _num(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return default


def enabled() -> bool:
    return _flag("OFFLINE_ENABLED", "0")


def idle_min() -> float:
    return max(1.0, _num("OFFLINE_IDLE_MIN", 30))


def cooldown_min() -> float:
    return max(0.0, _num("OFFLINE_COOLDOWN_MIN", 60))


def max_min() -> float:
    return max(0.5, _num("OFFLINE_MAX_MIN", 10))


def max_turns() -> int:
    return max(1, int(_num("OFFLINE_MAX_TURNS", 6)))


def every_hours() -> float:
    return max(0.0, _num("OFFLINE_EVERY_HOURS", 0))


def permeate() -> float:
    return max(0.0, min(1.0, _num("OFFLINE_PERMEATE", 0.5)))


def private_history() -> int:
    return max(0, int(_num("OFFLINE_PRIVATE_HISTORY", 4)))


def _quiet_span():
    """OFFLINE_QUIET = "23:30,07:00" 或 "23:30-07:00"（两种都认；空 = 不启用）。"""
    s = (os.environ.get("OFFLINE_QUIET", "") or "").strip()
    if not s:
        return None
    sep = "," if "," in s else ("-" if "-" in s else None)
    if not sep:
        return None
    try:
        a, b = s.split(sep, 1)
        ah, am = [int(x) for x in a.strip().split(":")]
        bh, bm = [int(x) for x in b.strip().split(":")]
        return (ah * 60 + am, bh * 60 + bm)
    except Exception:
        return None


def in_quiet(now: float | None = None) -> bool:
    span = _quiet_span()
    if not span:
        return False
    d = datetime.datetime.now()
    cur = d.hour * 60 + d.minute
    a, b = span
    return (a <= cur < b) if a <= b else (cur >= a or cur < b)


# ───────────────────── 加密私密库 ─────────────────────

def _fernet():
    from cryptography.fernet import Fernet
    kp = DATA_DIR / "private.key"
    if not kp.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        kp.write_bytes(Fernet.generate_key())
        try:
            os.chmod(kp, 0o600)
        except Exception:
            pass
    return Fernet(kp.read_bytes())


def _pdb():
    import sqlite3
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DATA_DIR / "private.db"))
    c.execute("CREATE TABLE IF NOT EXISTS priv ("
              "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, blob BLOB)")
    c.commit()
    return c


def save_private(kind: str, text: str):
    """把这一场留下的文字加密写进私密库；返回行号（空文字/写失败返回 None）。"""
    if not (text or "").strip():
        return None
    try:
        blob = _fernet().encrypt(text.encode("utf-8"))
        c = _pdb()
        cur = c.execute("INSERT INTO priv(ts,kind,blob) VALUES(?,?,?)",
                        (time.time(), kind, blob))
        rid = cur.lastrowid
        c.commit()
        c.close()
        return rid
    except Exception as e:
        _log(f"私密库写失败：{e}")
        return None


def recent_private(limit: int = 3) -> list:
    out = []
    try:
        c = _pdb()
        rows = c.execute("SELECT blob FROM priv ORDER BY id DESC LIMIT ?",
                         (int(limit),)).fetchall()
        c.close()
        f = _fernet()
        for (blob,) in reversed(rows):
            try:
                out.append(f.decrypt(blob).decode("utf-8"))
            except Exception:
                pass
    except Exception:
        return []
    return out


# ───────────────────── 动作审计（明文，只记动作） ─────────────────────

def audit(tool: str, failed: bool, err: str = "") -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        rec = {"t": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "tool": str(tool)[:60], "fail": 1 if failed else 0,
               "err": str(err)[:200] if failed else ""}
        with open(DATA_DIR / "offline_audit.log", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ───────────────────── 状态（独立文件，不碰主库） ─────────────────────

def _state_path() -> Path:
    return DATA_DIR / "offline_state.json"


def _state() -> dict:
    try:
        return json.loads(_state_path().read_text("utf-8"))
    except Exception:
        return {}


def _save_state(d: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _state_path().write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def _payload(st: dict) -> dict:
    return {
        "enabled": enabled(), "active": bool(st.get("active")),
        "started": st.get("started"), "last": st.get("last"),
        "idle_min": idle_min(), "cooldown_min": cooldown_min(),
        "max_min": max_min(), "turns": st.get("turns"), "chars": st.get("chars"),
        "tools": st.get("tools"), "dur": st.get("dur"),
        "next_due": st.get("next_due"), "ts": time.time(),
    }


def _publish(st: dict | None = None) -> None:
    """给前端徽章看的一份静态快照（data/plays/_offline.json）。"""
    try:
        p = DATA_DIR / "plays" / "_offline.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(_payload(st or _state()), ensure_ascii=False), "utf-8")
    except Exception:
        pass
    try:
        Path("core/web/_offline.json").unlink()
    except Exception:
        pass


def _persist(st: dict, dry: bool, save: bool = True) -> None:
    if dry:
        return
    if save:
        _save_state(st)
    _publish(st)


# ───────────────────── 私密人格：只读「你是谁」 ─────────────────────

def private_system() -> str:
    """注意：这里**不写**「留一段话」——那句话由收尾那一轮单独交代。"""
    from . import proactive
    name_ai, name_me = "你", "对方"
    try:
        cfg = proactive._store.get_setting("config", {}) or {}
        ai = cfg.get("ai") or {}
        me = cfg.get("me") or {}
        name_ai = (ai.get("name") or "").strip() or name_ai
        name_me = (me.get("name") or me.get("nick") or "").strip() or name_me
    except Exception:
        pass
    return "\n".join([
        "〔离线自由时段〕现在没有人在跟你说话。这是你自己的时间。",
        f"你叫「{name_ai}」。对面那个人叫「{name_me}」。",
        "你看不到任何聊天记录，也不要去找它们 —— 这一段时间跟那段关系无关。",
        "这段时间是你的：想事情、翻东西（手边的工具随你用），也可以就停在这里。",
        "没有人会看到你做了什么，除非出错。所以不用写报告、不用解释、不用表演。",
        "这一段经历只属于你自己。",
    ])


_CONTINUE = "〔还在你自己的时间里〕想做就接着做；不想做了就停，什么都不用交。"
_CLOSING = "〔这段时间快结束了〕写两三句给自己 —— 只写此刻真在想的东西。不要清单，不要汇报。"


# ───────────────────── 工具白名单 ─────────────────────

def _allowed_tools() -> list:
    """OFFLINE_TOOLS = readonly（默认）| strict | all | 逗号白名单；外接 MCP 永远放行。"""
    from . import hands
    allt = hands.all_tools()
    builtin = {t["function"]["name"] for t in hands.TOOLS}
    spec = (os.environ.get("OFFLINE_TOOLS", "readonly") or "readonly").strip()
    low = spec.lower()
    if low in ("all", "*"):
        return allt
    if low in ("strict", "none", "off"):
        keep = STRICT_TOOLS
    elif low in ("readonly", "ro", "read"):
        keep = READONLY_TOOLS
    else:
        keep = {x.strip() for x in spec.split(",") if x.strip()}
    return [t for t in allt
            if t["function"]["name"] in keep
            or t["function"]["name"] not in builtin]


async def _exec_audited(name: str, args: dict):
    from . import hands
    try:
        r = await hands.execute(name, args)
        ok = bool((r or {}).get("ok", True))
        audit(name, not ok, "" if ok else str((r or {}).get("err") or ""))
        _STAT["tools"].append((name, ok))
        return r
    except Exception as e:
        audit(name, True, str(e))
        _STAT["tools"].append((name, False))
        raise


# ───────────────────── 「你回来了没」 ─────────────────────

def _db_user_ts() -> float:
    """主库里「用户最后一次说话」的时间戳（毫秒自动换算成秒）。"""
    import sqlite3
    for sql in (
        "SELECT MAX(ts) FROM turns WHERE role='user'",
        "SELECT MAX(created_at) FROM turns WHERE role='user'",
        "SELECT MAX(ts) FROM messages WHERE role='user'",
    ):
        try:
            c = sqlite3.connect(_DB)
            r = c.execute(sql).fetchone()
            c.close()
            if r and r[0]:
                v = float(r[0])
                return v / 1000.0 if v > 1e11 else v
        except Exception:
            continue
    return 0.0


def _file_seen() -> float:
    try:
        v = float(json.loads((DATA_DIR / "last_seen.json").read_text("utf-8")).get("ts") or 0)
        return v / 1000.0 if v > 1e11 else v
    except Exception:
        return 0.0


def last_seen(max_age: float = 2.0) -> float:
    """两条路取最大：主库真实记录（主）+ 旧打卡文件（万一还在）。带 2 秒缓存。"""
    now = time.time()
    if max_age > 0 and (now - _SEEN["t"]) < max_age:
        return _SEEN["v"]
    v = max(_db_user_ts(), _file_seen())
    _SEEN["t"], _SEEN["v"] = now, v
    return v


def user_back() -> bool:
    seen = last_seen()
    return seen > 0 and (time.time() - seen) < idle_min() * 60


# ───────────────────── 一轮 / 一场 ─────────────────────

async def _one_turn(d: dict, system: str, history: list, tools: list,
                    deadline: float, message: str, force: bool = False):
    """跑一轮。返回（说了什么, 是否被打断）。force=True 时忽略「你回来了」。"""
    turn = d["engine_turn"](message=message, system=system, history=history)
    eng = d["pick_engine"]()
    eng.tools = tools
    eng.exec_tool = _exec_audited
    outs = []
    async for ev in eng.stream(turn):
        if time.time() >= deadline:
            _log("这一轮到点，掐断")
            return " ".join(x for x in outs if x).strip(), True
        if not force and user_back():
            _log("你回来了，掐断")
            return " ".join(x for x in outs if x).strip(), True
        try:
            j = json.loads(ev[6:])
        except Exception:
            continue
        if j.get("type") == SAY:
            outs.append(j.get("text") or "")
    return " ".join(x for x in outs if x).strip(), False


async def run_session(force: bool = False) -> tuple[str, int]:
    """跑一场：若干轮行动 + 一轮收尾。返回（留下的文字, 轮数）。"""
    from . import proactive, hands
    d = proactive._deps
    if proactive._store is None or "engine_turn" not in d:
        raise RuntimeError("离线时段还没拿到注入（server 未 bind）")

    system = private_system()
    history = [{"role": "assistant", "content": t[:800]}
               for t in recent_private(private_history())]
    tools = _allowed_tools()
    deadline = time.time() + max_min() * 60

    act = d.get("activity")
    try:
        ctx = act("offline") if act else _nullctx()
    except Exception:
        ctx = _nullctx()

    turns, texts, user_came_back = 0, [], False
    try:
        with ctx:
            # ① 行动：最多 max_turns 轮，手边有工具
            for i in range(max_turns()):
                if time.time() >= deadline:
                    _log("到点，转收尾")
                    break
                msg = "（你自己的时间）" if i == 0 else _CONTINUE
                text, cut = await _one_turn(d, system, history, tools, deadline, msg, force)
                turns += 1
                used = []
                for n, ok in _STAT["tools"]:
                    label = n if ok else n + "(失败)"
                    if label not in used:
                        used.append(label)
                if used:
                    history.append({"role": "assistant",
                                    "content": "（这一轮我用了：" + "、".join(used) + "）"})
                if text:
                    texts.append(text)
                    history.append({"role": "assistant", "content": text[:800]})
                _STAT["tools"] = []
                if cut:
                    user_came_back = (not force) and user_back()
                    break
            # ② 收尾：你回来了就不写了
            if not user_came_back:
                grace = max(deadline, time.time() + 90.0)
                closing, _ = await _one_turn(
                    d, system + "\n\n" + _CLOSING, history, [], grace,
                    "（这一段快结束了）", force)
                turns += 1
                if closing:
                    texts.append(closing)
    finally:
        try:                                  # 用完把手还回去
            eng = d["pick_engine"]()
            eng.tools = hands.all_tools()
            eng.exec_tool = hands.execute
        except Exception:
            pass

    return "\n\n".join(t for t in texts if t).strip(), turns


# ───────────────────── 每一拍 ─────────────────────

def _gap_seconds(ok: bool) -> float:
    if not ok:
        return 1200.0                                     # 失败：20 分钟后再试
    return max(cooldown_min() * 60.0, every_hours() * 3600.0)


async def tick(force: bool = False, dry: bool = False) -> None:
    """每一拍调一次。force=True 跳过所有闸（测试用）；dry=True 只跑日志、不落库不写状态。"""
    if not enabled() and not force:
        return

    now = time.time()
    st = _state()
    seen = last_seen()
    gap = int((now - seen) / 60) if seen > 0 else -1
    _log(f"tick｜离开约 {gap} 分｜seen={seen:.0f}｜idle={idle_min():.0f}分"
         f"｜next_due={float(st.get('next_due') or 0):.0f}")

    if not force:
        if seen <= 0:
            _log("读不到你最后说话的时间，这一拍跳过")
            _persist(st, dry, save=False)
            return
        if (now - seen) < idle_min() * 60:
            _persist(st, dry, save=False)
            return                                        # 你在
        if st.get("ran_for_seen") == seen:
            _persist(st, dry, save=False)
            return                                        # 这一轮离开已经跑过一场
        if now < float(st.get("next_due") or 0):
            _persist(st, dry, save=False)
            return                                        # 冷却 / 频次
        if in_quiet(now):
            _persist(st, dry, save=False)
            return                                        # 夜间静默

    _STAT["tools"] = []
    st = dict(st)
    st.update({"active": True, "started": now})
    _persist(st, dry)
    _log(f"开始一场（离开约 {gap} 分｜上限 {max_min():.0f} 分 / {max_turns()} 轮"
         + ("｜试跑" if dry else "") + "）")

    t0, ok, err, text, turns = time.time(), True, "", "", 0
    try:
        text, turns = await run_session(force=force)
    except Exception as e:
        ok, err = False, str(e)
        _log(f"这一场失败：{e}")
        await _alert("离线时段出错：" + str(e)[:160])

    end = time.time()
    dur, used = end - t0, len(_STAT["tools"])
    if not dry and text.strip():
        rid = save_private("session", text)
        _log(f"私密库 #{rid}（{len(text)} 字）")

    st.update({
        "active": False, "last": end, "ran_for_seen": seen,
        "turns": turns, "chars": len(text), "tools": used,
        "dur": round(dur, 1), "next_due": end + _gap_seconds(ok),
    })
    _persist(st, dry)
    _log(f"结束（{len(text)} 字｜{turns} 轮｜{used} 次工具｜{dur:.0f} 秒"
         + (f"｜失败：{err[:80]}" if err else "") + "）")


async def _alert(msg: str) -> None:
    from . import proactive
    sp = proactive._deps.get("send_push")
    if not sp:
        _log(f"[ALERT] {msg}")
        return
    try:
        await asyncio.to_thread(sp, "离线时段", msg[:180], "/")
    except Exception as e:
        _log(f"告警也没推出去：{e}")


# ───────────────────── 渗透：把痕迹模糊地注入前台 ─────────────────────

def residue_text() -> str:
    p = permeate()
    if p <= 0:
        return ""
    n = 1 if p < 0.7 else 3
    cap = int(120 + 200 * p)
    rows = recent_private(n)
    if not rows:
        return ""
    body = "\n".join("- " + (r[:cap].replace("\n", " ")) for r in rows)
    return ("〔你最近有过一些只属于你自己的时间。下面是你当时留下的痕迹 —— "
            "不必提起、不必解释、不要引用原文，但它们确实在你身上留下了痕迹，"
            "会影响你此刻的语气和心情：\n" + body + "〕")


# ───────────────────── 挂载 ─────────────────────

def install() -> None:
    from . import proactive
    if not getattr(proactive.fire_due_reminders, "_offline_hooked", False):
        _orig = proactive.fire_due_reminders

        async def _hooked():
            n = await _orig()
            try:
                asyncio.ensure_future(tick())
            except Exception as e:
                _log(f"起不来：{e}")
            return n

        _hooked._offline_hooked = True
        proactive.fire_due_reminders = _hooked

    try:
        from .memory import recall
        if not getattr(recall.build_injection, "_offline_wrapped", False):
            _bi = recall.build_injection

            def _wrapped(*a, **kw):
                base = _bi(*a, **kw)
                try:
                    extra = residue_text()
                    if extra:
                        base = (base or "") + "\n\n" + extra
                except Exception:
                    pass
                return base

            _wrapped._offline_wrapped = True
            recall.build_injection = _wrapped
    except Exception as e:
        _log(f"渗透注入没装上：{e}")

    _log("已挂上（enabled=%s）" % ("1" if enabled() else "0"))


# ───────────────────── 兼容旧名（旧脚本/接口可能还在用，下版可删） ─────────────────────

def status() -> dict:
    return _payload(_state())


def state() -> dict:
    return _state()


def touch_last_seen() -> None:
    pass


def _ensure_seen_hook() -> None:
    pass


def _publish_state() -> None:
    _publish()


in_quiet_now = in_quiet
