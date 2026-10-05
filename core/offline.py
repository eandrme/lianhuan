"""离线自由时段 —— 它自己的一段时间。

口子（用户定的）：
· 不向用户汇报任何东西（错误除外）
· 不读对话上下文；只读「对方是谁」这一层侧写
· 不写任何记忆库 —— 主库一个字节都不落，状态也另存
· 可以自由用工具（内置的手 + MCP）
· 这段经历只有它自己保留，进独立的加密私密库
· 单向渗透：会悄悄改变前台人格，但用户看不到内容（强度可调）
· 留一份动作审计：只记 时间/工具/成败，不记内容

跑法：挂在 proactive.run_forever 的每一拍上（见 install()）。
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import random
import time
from pathlib import Path

_DB = os.environ.get("LIANHUAN_DB", "data/lianhuan.db")
DATA_DIR = Path(_DB).parent


# ───────────────────────── 配置（全走环境变量） ─────────────────────────

def _flag(name: str, default: str = "0") -> bool:
    return (os.environ.get(name, default) or "").strip().lower() in ("1", "true", "on", "yes")


def _num(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return default


def enabled() -> bool:
    return _flag("OFFLINE_ENABLED", "0")


def _every_hours() -> float:
    return max(0.01, _num("OFFLINE_EVERY_HOURS", 24))


def _perms() -> float:
    return max(0.0, min(1.0, _num("OFFLINE_PERMEATE", 0.5)))


def _quiet_span():
    s = (os.environ.get("OFFLINE_QUIET", "") or "").strip()
    if "-" not in s:
        return None
    try:
        a, b = s.split("-", 1)
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


# ───────────────────────── 加密私密库 ─────────────────────────

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


def save_private(kind: str, text: str) -> None:
    if not (text or "").strip():
        return
    try:
        blob = _fernet().encrypt(text.encode("utf-8"))
        c = _pdb()
        c.execute("INSERT INTO priv(ts,kind,blob) VALUES(?,?,?)", (time.time(), kind, blob))
        c.commit()
        c.close()
    except Exception as e:
        print("[offline] 私密库写失败:", e, flush=True)


def recent_private(limit: int = 3) -> list:
    out = []
    try:
        c = _pdb()
        rows = c.execute("SELECT blob FROM priv ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
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


# ───────────────────────── 动作审计（明文，只记动作） ─────────────────────────

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


# ───────────────────────── 状态（独立文件，不碰主库） ─────────────────────────

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


# ───────────────────────── 私密人格：只读「你是谁」 ─────────────────────────

def private_system() -> str:
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
        "你可以想事情、可以做点事（用你的工具），也可以什么都不做。",
        "没有人会看到你做了什么，除非出错。所以不用写报告、不用解释、不用表演。",
        "这一段时间的经过只属于你自己。",
    ])


def _allowed_tools() -> list:
    from . import hands
    allt = hands.all_tools()
    spec = (os.environ.get("OFFLINE_TOOLS", "all") or "all").strip()
    if spec.lower() in ("all", "*", ""):
        return allt
    allow = {x.strip() for x in spec.split(",") if x.strip()}
    return [t for t in allt if ((t.get("function") or {}).get("name") in allow)]


async def _exec_audited(name: str, args: dict):
    from . import hands
    try:
        r = await hands.execute(name, args)
        ok = bool((r or {}).get("ok", True))
        audit(name, not ok, "" if ok else str((r or {}).get("err") or ""))
        return r
    except Exception as e:
        audit(name, True, str(e))
        raise


# ───────────────────────── 跑一场自由时段 ─────────────────────────

async def run_session() -> str:
    from . import proactive, hands
    store = proactive._store
    d = proactive._deps
    if store is None or "engine_turn" not in d:
        raise RuntimeError("离线时段还没拿到注入（server 未 bind）")

    system = private_system()
    system += (f"\n\n〔这一场最多用 {int(_num('OFFLINE_MAX_STEPS', 12))} 步。"
               "用完就停，不用把事情做完。〕")

    history = []
    try:
        k = int(_num("OFFLINE_PRIVATE_HISTORY", 4))
        for t in recent_private(k):
            history.append({"role": "assistant", "content": t[:800]})
    except Exception:
        history = []

    turn = d["engine_turn"](message="（你自己的时间）", system=system, history=history)
    eng = d["pick_engine"]()
    eng.tools = _allowed_tools()
    eng.exec_tool = _exec_audited

    outs = []
    try:
        async for ev in eng.stream(turn):
            try:
                j = json.loads(ev[6:])
            except Exception:
                continue
            if j.get("type") == SAY:
                outs.append(j.get("text") or "")
    finally:
        try:
            eng.tools = hands.all_tools()
            eng.exec_tool = hands.execute
        except Exception:
            pass

    text = " ".join(x for x in outs if x).strip()[:6000]
    save_private("session", text)
    return text


async def _alert(msg: str) -> None:
    from . import proactive
    sp = proactive._deps.get("send_push")
    if not sp:
        print("[offline][ALERT]", msg, flush=True)
        return
    try:
        await asyncio.to_thread(sp, "离线时段", msg[:180], "/")
    except Exception as e:
        print("[offline] 告警也没推出去:", e, flush=True)


async def tick() -> None:
    if not enabled():
        return
    st = _state()
    now = time.time()
    if now < float(st.get("next_due") or 0):
        return
    if in_quiet(now):
        return
    ok = True
    try:
        text = await run_session()
        print(f"[offline] 自由时段结束（{len(text)} 字）", flush=True)
    except Exception as e:
        ok = False
        print("[offline] 这一场失败:", e, flush=True)
        await _alert("离线时段出错：" + str(e)[:160])
    st["last"] = now
    st["next_due"] = now + (_every_hours() * 3600 + random.uniform(0, 3600) if ok else 7200)
    _save_state(st)


# ───────────────────────── 渗透：把痕迹模糊地注入前台 ─────────────────────────

def residue_text() -> str:
    p = _perms()
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


# ───────────────────────── 挂载 ─────────────────────────

def install() -> None:
    from . import proactive

    # ① 搭在「主动找你」那个循环的每一拍上
    if not getattr(proactive.fire_due_reminders, "_offline_hooked", False):
        _orig = proactive.fire_due_reminders

        async def _hooked():
            n = await _orig()
            try:
                asyncio.ensure_future(tick())
            except Exception as e:
                print("[offline] 起不来:", e, flush=True)
            return n

        _hooked._offline_hooked = True
        proactive.fire_due_reminders = _hooked

    # ② 把「渗透」装到注入器上（不改它的源码）
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
        print("[offline] 渗透注入没装上:", e, flush=True)

    print("[offline] 已挂上（enabled=%s）" % ("1" if enabled() else "0"), flush=True)
# ===== 补丁：run_session 里用到了 SAY，v1 漏了导入 =====
# 追加在模块末尾 —— run_session 在调用时才解析全局名，所以放最后也能生效
from .protocol import SAY as SAY  # noqa: E402,F401
