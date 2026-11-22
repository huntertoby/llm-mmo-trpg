"""同一個技能的第二份以上（E1，08 8.28 第 4 點，#174）。

裝備授予的技能和自己學的、或兩件裝備給同一招時不合併：第二份起在單位的技能清單裡用 **複本鍵**
``<技能 ID>~<n>``（n 從 2 起）。技能 ID 的格式（``skill_[a-z0-9_]+``）沒有 ``~``，所以不會撞到
真的技能。冷卻、使用次數、反應規則、事件都用這個鍵，所以兩份各自計算；規則包查定義時
（:meth:`trpg.content.library.Ruleset.skill_def`）把鍵還原成原技能，回傳的定義 ``id`` 是複本鍵。
"""

from __future__ import annotations

from typing import Final

__all__ = ["COPY_SEP", "base_skill_id", "copy_key", "copy_rank", "is_copy_key"]

COPY_SEP: Final = "~"


def copy_key(skill_id: str, n: int) -> str:
    """第 ``n`` 份（``n ≥ 2``）的鍵；``n == 1`` 就是技能 ID 本身。"""
    return skill_id if n <= 1 else f"{skill_id}{COPY_SEP}{n}"


def is_copy_key(key: str) -> bool:
    return COPY_SEP in key


def base_skill_id(key: str) -> str:
    """複本鍵的原技能 ID（不是複本鍵時原樣回傳）。"""
    return key.partition(COPY_SEP)[0]


def copy_rank(key: str) -> int:
    """這是第幾份（原技能 1、``~2`` 是 2）。"""
    _, sep, n = key.partition(COPY_SEP)
    return int(n) if sep and n.isdigit() else 1
