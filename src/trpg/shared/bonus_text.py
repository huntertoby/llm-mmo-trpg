"""「目前加成」的文字（Phase 3H-5，玩法 PM）。

卡片主文顯示捨去後的整數（「目前 +4」）；實際值帶小數時（屬性 14 × 0.3 ＝ 4.2），那一小段另外
包成可滑過的標記，說明卡寫「實際 4.2，和其他加成合計後才捨去」。標記只是文字的一部分
（``⟦顯示字｜說明⟧``），由程式產生；前端 ``RuleText`` 把它排成說明框，不支援標記的地方用
:func:`plain_text` 還原成純文字。實際值為整數時不加標記。

整數運算：實際值 ＝ 屬性值 × 倍率‰ ÷ 1000，顯示值 ＝ 向下捨去（屬性不為負）。
"""

from __future__ import annotations

import re

__all__ = ["BONUS_MARK", "bonus_text", "plain_text"]

BONUS_MARK = re.compile(r"⟦([^｜⟧]*)｜[^⟧]*⟧")
"""標記的樣式：第 1 組是顯示字。前端用同一個樣式（``client/src/ui/ruleText.ts``）。"""


def bonus_text(value: int, permille: int) -> str:
    """「目前 +N」：``value`` 是屬性值、``permille`` 是倍率（‰）。"""
    scaled = value * permille
    shown = f"目前 +{scaled // 1000}"
    if scaled % 1000 == 0:
        return shown
    return f"⟦{shown}｜實際 {scaled / 1000:g}，和其他加成合計後才捨去⟧"


def plain_text(text: str) -> str:
    """去掉標記，只留顯示字（純文字的呈現處，例如 CLI、原生提示）。"""
    return BONUS_MARK.sub(r"\1", text)
