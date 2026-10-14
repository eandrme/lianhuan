import os


def _on(name: str) -> bool:
    """环境变量开关：1/true/yes/on 为开，其余（含未设置）为关。"""
    return (os.environ.get(name, '') or '').strip().lower() in ('1', 'true', 'yes', 'on')


def mood_enabled() -> bool:
    """心情注入总开关，默认关。"""
    return _on('MOOD_INJECT')
