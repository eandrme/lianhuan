"""助手 —— 一位助手下面挂几扇窗。

★ 原来「人格」是全局一份（`settings.persona`）、MCP 也是全局一把，窗口只是
  `turns.session_id` 的切分 —— 想「这一位用这套口吻、只拿这几样工具」没有地方放。
  这一层就是那个地方。一位助手＝

    名字 · 名字下面那行小字 · 头像 · 自己那份系统提示词 · 允许它用的 MCP ·
    挂在他名下的窗口

★ 存法：settings 里一个 JSON（`assistants`），跟 persona / theme 一个规矩 ——
  搬家跟着走（在 `PORTABLE_SETTINGS` 里）。
★ 向后兼容：**没配过助手**（老库、刚装好）时这一层整个不生效 —— 聊天照样走全局人格、
  工具照旧全给。一旦建了/改了助手，就按助手这一层走。
  没挂到任何助手名下的窗口，算**第一位**助手名下的 —— 老窗口升级过来就有家，不用迁移。
★ MCP 的默认值有讲究（这是用户点名要的那条「不同步」）：
    · 第一位（默认那一位）没勾过 = **不限**（所有连上的 MCP 都给）—— 老行为一字不差；
    · 新建的助手 = **一个都不给**，要哪个在这个助手的设置里手动勾。
"""
from __future__ import annotations

import uuid
from typing import Any

KEY = "assistants"

#: 一位助手的字段。`mcp` 的 None 和 [] 是两件事：None＝不限，[]＝一个都不给。
FIELDS = ("name", "sign", "avatar", "prompt", "mcp", "windows")


def norm_sid(sid) -> str:
    return (str(sid) if sid is not None else "").strip() or "main"


def _new_id() -> str:
    """短、够唯一、人看着不累。

    ★ 原来用毫秒时间戳取模 —— **同一毫秒里建两位就撞 id**，而 `all_items` 按 id 去重，
      于是第二位当场消失（真机上撞的：建了「小满」，名单里只剩「阿澈」，窗口也挂错人）。
      uuid4 前 8 位够用，且不依赖时钟。"""
    return "a" + uuid.uuid4().hex[:8]


def _clean(a: dict) -> dict:
    """把一条助手洗成规规矩矩的样子 —— 手改过的 JSON 也不能把别处搞崩。"""
    a = a if isinstance(a, dict) else {}
    mcp = a.get("mcp", None)
    if mcp is not None and not isinstance(mcp, list):
        mcp = [] if mcp in ("", False) else None
    wins = a.get("windows")
    wins = [norm_sid(x) for x in wins] if isinstance(wins, list) else []
    out = {
        "id": str(a.get("id") or _new_id()),
        "name": str(a.get("name") or "").strip()[:40],
        "sign": str(a.get("sign") or "").strip()[:80],
        "avatar": str(a.get("avatar") or "").strip()[:300],
        "prompt": str(a.get("prompt") or "")[:8000],
        "mcp": None if mcp is None else [str(x) for x in mcp if str(x).strip()],
        "windows": wins,
    }
    return out


def _raw(store) -> dict:
    try:
        d = store.get_setting(KEY, {}) or {}
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def all_items(store) -> list[dict]:
    """所有助手（洗过的）。**空列表＝这一层没启用**，别处据此走老路。"""
    d = _raw(store)
    items = d.get("items")
    if not isinstance(items, list):
        return []
    seen, out = set(), []
    for a in items:
        if not isinstance(a, dict):          # 手改坏的那种整条跳过，别凭空造一位出来
            continue
        c = _clean(a)
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
    return out


def _write(store, items: list[dict]) -> None:
    store.set_setting(KEY, {"version": 1, "items": items})


def get(store, aid) -> dict | None:
    aid = str(aid or "")
    for a in all_items(store):
        if a["id"] == aid:
            return a
    return None


def default_id(store) -> str | None:
    items = all_items(store)
    return items[0]["id"] if items else None


def create(store, **fields) -> dict:
    """新建一位。`fields` 就是 `save` 那几样（name 可以不给）。

    ★ mcp 的默认值：第一位＝None（不限，老行为）；后面新建的＝[]（一个都不给）。
      这就是用户要的那条「不同步」—— 新助手默认手上什么都没有，要哪个手动勾。"""
    items = all_items(store)
    first = not items
    fields = dict(fields)
    name = str(fields.pop("name", "") or "").strip() or ("他" if first else "新的助手")
    a = _clean({"name": name, **fields})
    while any(x["id"] == a["id"] for x in items):     # 撞了就换一个（uuid 基本不会撞）
        a["id"] = _new_id()
    if "mcp" not in fields:
        a["mcp"] = None if first else []
    items.append(a)
    _write(store, items)
    return a


def save(store, aid, **fields) -> dict | None:
    items = all_items(store)
    for i, a in enumerate(items):
        if a["id"] != str(aid):
            continue
        for k in FIELDS:
            if k in fields and fields[k] is not None:
                a[k] = fields[k]
        items[i] = _clean(a)
        _write(store, items)
        return items[i]
    return None


def remove(store, aid) -> bool:
    """删一位助手。他名下的窗口**退回第一位**（窗口和聊天记录一条都不删）。"""
    items = all_items(store)
    gone = next((a for a in items if a["id"] == str(aid)), None)
    if gone is None:
        return False
    keep = [a for a in items if a["id"] != str(aid)]
    if keep:
        keep[0]["windows"] = list(dict.fromkeys(list(keep[0]["windows"]) + list(gone["windows"])))
    _write(store, keep)
    return True


def assistant_of(store, sid) -> dict | None:
    """这个窗口挂在哪位助手下面。

    ★ 一个助手都没有 → **None**（这一层没启用，别处走老路，一个字都不改）。
      有助手、但这个窗口没挂过 → 第一位（老窗口升级过来就有家）。
    """
    items = all_items(store)
    if not items:
        return None
    sid = norm_sid(sid)
    for a in items:
        if sid in a["windows"]:
            return a
    return items[0]


def attach_window(store, sid, aid) -> bool:
    """把一个窗口挂到某位助手名下（从原来那位那儿摘掉）。"""
    sid = norm_sid(sid)
    items = all_items(store)
    hit = False
    for a in items:
        a["windows"] = [w for w in a["windows"] if w != sid]
        if a["id"] == str(aid):
            a["windows"].append(sid)
            hit = True
    if hit:
        _write(store, items)
    return hit


def detach_window(store, sid) -> None:
    """从助手名册里摘掉一个窗口 —— 它自动回到第一位助手名下。"""
    sid = norm_sid(sid)
    items = all_items(store)
    for a in items:
        a["windows"] = [w for w in a["windows"] if w != sid]
    _write(store, items)


def mcp_allow(store, sid) -> list[str] | None:
    """这位助手能用哪些 MCP server。**None ＝ 不限**（所有连上的都给）。"""
    a = assistant_of(store, sid)
    if a is None:
        return None
    return a.get("mcp")


def persona_for(store, asst: dict | None) -> dict | None:
    """按助手覆盖人设（喂给 `recall.build_injection` 的 persona 参数）。

    ★ 只动 **ai 那半边**：`human` 是「你在跟谁说话」，那是用户自己的事，跟换助手无关。
      返回 None ＝ 不覆盖，别处照旧读全局那份。
    """
    if not asst:
        return None
    base = store.get_setting("persona", {}) or {}
    p: dict[str, Any] = {"ai": dict(base.get("ai") or {}),
                         "human": dict(base.get("human") or {})}
    for k in ("me", "user"):                      # 老库里那半边可能叫别的名字，原样带着
        if isinstance(base.get(k), dict) and k not in p:
            p[k] = dict(base[k])
    ai = p["ai"]
    if asst.get("name"):
        ai["name"] = asst["name"]
    if asst.get("prompt"):
        ai["text"] = asst["prompt"]
    return p


def sign_line(asst: dict | None) -> str:
    """名字下面那行小字 —— 它不是摆设：也进注入，写什么它就是什么。"""
    if not asst or not (asst.get("sign") or "").strip():
        return ""
    return ("〔你给自己写的一行小字（会显示在你名字下面，对方看得见）〕\n"
            + asst["sign"].strip()[:80])
