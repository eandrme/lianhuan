"""想多深 —— 聊天里那个「深度思考」档。

三档：`fast`（偏快）· `auto`（自动，默认）· `deep`（偏深）。

★ 为什么单开一个模块：开源版里 `/api/think` 原来**只往 settings 里写一个没人读的值** ——
  老界面上那个「想多深」弹层于是等于摆设（开关翻过去了，什么都不变）。
  这一份把它接到两处，两处都看得见效果：

  ① **档位交给引擎**：OpenAI 兼容那条会给模型带 `reasoning_effort`
     （fast → 低档、deep → 这家支持的最高一档）。认这个字段的家（DeepSeek V4、
     o 系那一类）是真会少想/多想的；不认的家会把可选值列在报错里，引擎那边
     去掉字段重来一次，并记住这一家认哪几档 —— 不硬塞、不假装。
  ② **一句话进 system**：不管哪家引擎（Claude、本机 CLI、不认那个字段的家）
     都按档位给一句「先说结论」或「多想一层再答」。所以它**永远不是空开关**。

★ 只作用于**聊天那条路**。主动消息 / 离线时段 / 哄睡那些不读这一档 ——
  用户拨的是「主聊天界面」上那枚，别的地方替他决定想多深是越权。
"""
from __future__ import annotations

import re

MODES = ("fast", "auto", "deep")
DEFAULT = "auto"

#: 界面上给人看的短名字。三档的名字跟老界面（index.html 的「想多深」）保持一致。
LABELS = {"fast": "偏快", "auto": "自动", "deep": "偏深"}

#: 菜单里那一行小字：这一档到底改了什么。照实写，不吹。
NOTES = {
    "fast": "少想一点，答得快些",
    "auto": "不动它，由这家自己定（默认）",
    "deep": "多想一层再答，慢一些",
}

#: 各引擎对「档位」能做到什么 —— 界面拿它说实话。
ENGINE_NOTE = {
    "api": "会把档位标给这家（它认这个参数的话，真会少想/多想）",
    "anthropic": "Claude 一直是自适应思考；这一档改的是让它先说结论还是多想一层",
    "cli": "本机 CLI 那条只改提示词",
    "echo": "回声引擎，没有真的模型 —— 这一档现在改不了什么",
}

#: reasoning_effort 的档，从低到高（OpenAI / DeepSeek 都用这一套名字，各家只开放一部分）。
LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh", "ultra", "max")


def mode(store) -> str:
    """现在这一档。认不出的值（老库里可能存着 "medium" 之类）一律退回 auto。"""
    try:
        v = store.get_setting("think", DEFAULT)
    except Exception:
        return DEFAULT
    return v if v in MODES else DEFAULT


def effort(mode_: str, allowed=None) -> str | None:
    """这一档要标成哪个 reasoning_effort。auto 返回 None（什么都不标）。

    `allowed` = 这一家自己报出来的可选值（从它的报错里抄的）。没给就按最宽的那套挑；
    给了就只从它认的那几个里挑 —— fast 挑最低的那个，deep 挑最高的那个。
    """
    if mode_ not in ("fast", "deep"):
        return None
    want = {"fast": "low", "deep": "max"}[mode_]
    # ★ `allowed=[]`（这家一个档都不认）和 `allowed=None`（还没问过）是两件事：
    #   空列表得老老实实翻成 None，别拿它当「没给」又退回最宽的那套 —— 那就是硬塞。
    src = LEVELS if allowed is None else allowed
    pool = [x for x in src if x in LEVELS]
    if not pool:
        return None
    if want in pool:
        return want
    pool.sort(key=LEVELS.index)
    return pool[0] if mode_ == "fast" else pool[-1]


def nudge(mode_: str) -> str:
    """拼进 system 的那一句。auto 返回空串 —— 什么都不加，跟以前一模一样。"""
    if mode_ == "fast":
        return ("〔这一轮对方要的是**快**：先给结论，别铺垫、别把推演过程倒出来。"
                "想清楚就直接说，要解释也只解释最关键的那一步。〕")
    if mode_ == "deep":
        return ("〔这一轮**多想一层**再答：先把可能的方向在心里过一遍，"
                "想想有没有反例、有没有更简单的解释、有没有你没想到的那种可能，"
                "再给结论。但**想的过程别倒给对方** —— 回答照样干净利落，"
                "只在结论确实取决于某一步推理时，把那一步点一句。〕")
    return ""


_WORDS = re.compile(r"expected one of ([^;.\n]*)")
_SEP = re.compile(r"[,，]")


def allowed_from_error(text: str) -> list[str]:
    """从上游的报错里抄出「它认哪几档」。

    例（DeepSeek 实测）：`unknown variant `banana`, expected one of `none`, `minimal`,
    `low`, `medium`, `high`, `xhigh`, `ultra`, `max` at line 1 column 128`。
    ★ 抄不到就回空列表，调用方按「这家不认这个字段」处理 —— 不猜。
    """
    m = _WORDS.search(text or "")
    if not m:
        return []
    out = []
    for raw in _SEP.split(m.group(1)):
        # ★ 最后那一个后面往往还拖着一截尾巴（`` `max` at line 1 column 128 ``）——
        #   取第一个词再剥引号，别把「max` at line 1 column 128」当成一个档位丢掉。
        w = raw.strip().strip("`\"'").split()[0].strip("`\"',") if raw.strip() else ""
        if w in LEVELS:
            out.append(w)
    return out
