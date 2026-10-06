"""工具调用留痕 —— 让你看得见它调了什么、成没成。

只记动作 + 截断过的入参/结果（各 160/240 字），方便你判断"它到底干了啥"。
写 data/tool_calls.jsonl，一行一条；`recent()` 给界面读。
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path

_DB = os.environ.get("LIANHUAN_DB", "data/lianhuan.db")
DATA_DIR = Path(_DB).parent
LOG = DATA_DIR / "tool_calls.jsonl"
MAX_BYTES = 2 * 1024 * 1024
KEEP_LINES = 2000


def _short(v, n: int) -> str:
    try:
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    except Exception:
        s = str(v)
    return " ".join(str(s).split())[:n]


def record(tool: str, ok: bool, err: str = "", args=None, result=None, ms: float = 0) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        rec = {
            "t": datetime.datetime.now().strftime("%m-%d %H:%M:%S"),
            "tool": str(tool)[:80],
            "ok": 1 if ok else 0,
            "ms": int(ms * 1000),
            "err": _short(err, 200),
            "args": _short(args, 160),
            "res": _short(result, 240),
        }
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if LOG.stat().st_size > MAX_BYTES:
            _trim()
    except Exception:
        pass


def _trim() -> None:
    try:
        lines = LOG.read_text(encoding="utf-8").splitlines()[-KEEP_LINES:]
        LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def recent(limit: int = 50) -> list:
    limit = max(1, min(int(limit or 50), 300))
    try:
        lines = LOG.read_text(encoding="utf-8").splitlines()[-limit:]
    except Exception:
        return []
    out = []
    for ln in reversed(lines):
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out
