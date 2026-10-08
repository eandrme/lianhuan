"""每个对话窗口的两枚开关 —— 主动消息 · 离线自由时段。

巢里的「窗口」就是会话（`turns.session_id`）。每一扇窗各带两枚开关，**默认都开**：

  · 主动消息：它掷骰子掷中了，才会往这个窗口凑过来说一句。关掉＝这个窗口里
    **别主动找我**。它只会往「你最近待的那扇窗」说，所以你最近这扇窗关掉，
    它就是安静下来 —— 不会绕到你别的窗口里去打扰你。
  · 离线自由时段：你最近待的那扇窗关掉，这一拍就不给它自己那段时间。

★ 书房小窗不在其列：它走 `/api/books/{id}/chat`，落的是 `book_chat` 表，
  跟 `turns` 无关，也就永远进不了这套开关 —— 那是纯粹的读书助手。

★ 读不出来就**当成开着**（fail open）：开关是后加的东西，一个坏掉的设置
  不该把原来的行为一刀切掉。默认值本来就是「开」，两条路是一致的。
"""
from __future__ import annotations

#: 存在 settings 表里的键（搬家时跟着走，见 store/sqlite.py 的 PORTABLE_SETTINGS）
KEY = "nest_window_flags"

#: 界面现在停在哪扇窗。★ **不**进搬家白名单：那是「这台设备上你最后开着的
#: 那扇窗」，换台机器本来就不该照搬过来（照搬反而会说话说到别的窗口去）。
FOCUS_KEY = "nest_window_focus"

#: 两枚开关。顺序就是界面上从左到右的顺序。
FLAG_KEYS = ("push", "offline")

#: 给人看的名字（前端也按这份翻译，两边别各写一套）
LABELS = {"push": "主动消息", "offline": "离线模式"}

#: 说明：关掉之后到底发生什么。界面上的小字用它。
HINTS = {
    "push": "开着：它想你了会在这个窗口里凑过来说一句（还要总闸 /api/whisper_freq 不为 0）",
    "offline": "开着：你久不在的时候，它可以在这个窗口名下有自己的一段时间",
}


def norm_sid(sid) -> str:
    """空 / 全是空格 = 老数据 = 主窗口。跟 views.nest_thread 的口径一致。"""
    return (str(sid) if sid is not None else "").strip() or "main"


def _raw(store) -> dict:
    try:
        d = store.get_setting(KEY, {}) or {}
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def flags(store, sid) -> dict:
    """某个窗口的两枚开关（缺的就用默认「开」）。"""
    sid = norm_sid(sid)
    f = _raw(store).get(sid) if store is not None else None
    f = f if isinstance(f, dict) else {}
    out = {"sid": sid}
    for k in FLAG_KEYS:
        out[k] = bool(f.get(k, True))
    return out


def set_flags(store, sid, **kw) -> dict:
    """只改传进来的那几枚，别的原样留着。返回改完的样子。"""
    sid = norm_sid(sid)
    cur = dict(_raw(store))
    f = cur.get(sid)
    f = dict(f) if isinstance(f, dict) else {}
    for k in FLAG_KEYS:
        if k in kw and kw[k] is not None:
            f[k] = bool(kw[k])
    cur[sid] = f
    store.set_setting(KEY, cur)
    return flags(store, sid)


def all_flags(store) -> dict:
    """所有被拨过的窗口 → {sid: {sid,push,offline}}。没拨过的不出现（默认开）。"""
    return {s: flags(store, s) for s in _raw(store)}


def focus_sid(store) -> str:
    """界面刚刚停在那一扇窗（前端切窗口时报上来的）。

    ★ 为什么要单独记一个：人切到某扇窗、**还没开口**就走了，这时候「最后一句话
      落在哪」还停在上上扇窗上 —— 拿它当「你现在在哪」，你在别处关了开关，
      这扇窗的开关就跟着失灵（反过来也一样）。人报一声自己现在在哪，最准。
    """
    try:
        v = store.get_setting(FOCUS_KEY, "") or ""
    except Exception:
        return ""
    return norm_sid(v) if str(v).strip() else ""


def set_focus(store, sid) -> str:
    """记下界面现在停在哪扇窗。空字符串 = 清掉，退回「按最后说话的地方猜」。"""
    v = (str(sid) if sid is not None else "").strip()
    store.set_setting(FOCUS_KEY, norm_sid(v) if v else "")
    return norm_sid(v) if v else ""


def active_sid(store) -> str:
    """你现在在哪扇窗 —— 主动消息/离线时段都按这一扇的开关走。

    优先信界面报上来的那扇（`focus_sid`）；没有（老前端、还没报过）就退回猜：
    最后一句**你自己真说的话**（role='user' 且 spoken=1）落在哪个会话。
    机器拼的指令（翻空间 / 重新生成那类 spoken=0）不算 —— 那些是后台自己
    在动，不代表人待在那扇窗前。再没有就退回最后一条记录所在的窗口，最后是主窗口。
    """
    if store is None:
        return "main"
    f = focus_sid(store)
    if f:
        return f
    for sql in (
        "SELECT COALESCE(NULLIF(TRIM(session_id),''),'main') s FROM turns "
        "WHERE role='user' AND COALESCE(spoken,1)=1 ORDER BY id DESC LIMIT 1",
        "SELECT COALESCE(NULLIF(TRIM(session_id),''),'main') s FROM turns "
        "ORDER BY id DESC LIMIT 1",
    ):
        try:
            r = store.db.execute(sql).fetchone()
        except Exception:
            r = None
        if r is not None:
            return norm_sid(r["s"])
    return "main"


def allows(store, sid, key: str) -> bool:
    """这扇窗的某一枚开关开着吗。认不出的键一律放行（不是我们的开关）。"""
    if key not in FLAG_KEYS:
        return True
    return bool(flags(store, sid)[key])


def allows_active(store, key: str) -> bool:
    """你最近那扇窗的某一枚开关开着吗 —— 主动消息 / 离线时段问的就是这个。"""
    return allows(store, active_sid(store), key)
