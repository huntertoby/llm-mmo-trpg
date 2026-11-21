"""召喚到身邊（``summon_beside``，TF-1）縮小版的強度與代價嘗試順序（HC-5b）。

閃現轉型（:mod:`trpg.skillgen.flash_major` 的伴生、護主）與組合器配方
（:mod:`trpg.skillgen.composer_recipes` 的伴生、護主）共用：代價與射程讀
``flash_templates.yaml`` 的轉型模板（``to_passive_companion``、``to_reaction_guardian``），
強度的間距與下限讀 ``flash_templates.yaml`` 的 ``rules.beside_power_step_permille`` 與
``core.yaml`` 的 ``skill_limits.min_beside_power_permille``——兩邊只留一份（HC-5a 裁定 2）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from trpg.content.flash_templates import TransformTemplate
from trpg.content.library import ContentLibrary

__all__ = [
    "COMPANION_TEMPLATE",
    "GUARDIAN_TEMPLATE",
    "NORMAL_POWER",
    "beside_power_tries",
    "beside_template",
]

NORMAL_POWER = 1000
"""原尺寸召喚物的強度（‰）；``power_permille`` 省略＝這個值。"""
COMPANION_TEMPLATE = "to_passive_companion"
GUARDIAN_TEMPLATE = "to_reaction_guardian"


def beside_template(library: ContentLibrary, template_id: str) -> TransformTemplate:
    """伴生或護主的轉型模板（``flash_templates.yaml`` 的 ``transforms``）；沒有時丟
    ``ValueError``（組合器配方的代價、射程照它，不能少）。"""
    found = library.flash.transform_template(template_id)
    if found is None:
        raise ValueError(f"flash_templates.yaml 缺少轉型模板 {template_id}（組合器配方照它的代價）")
    return found


def beside_power_tries(
    start: int, costs: Sequence[dict[str, Any]], library: ContentLibrary
) -> list[tuple[int, dict[str, Any]]]:
    """縮小版召喚物依序試的（強度‰, 代價）：先試數值工坊的設定值（每種代價），不在預算窗內時再
    依離設定值的遠近、每 ``rules.beside_power_step_permille`` 一格往上下試（最低
    ``skill_limits.min_beside_power_permille``，最高 :data:`NORMAL_POWER`，同距離先往上）。召喚到
    身邊沒有可調的骰子，強度由這裡找進預算窗。"""
    low = library.ruleset.core.skill_limits.min_beside_power_permille
    step = library.flash.rules.beside_power_step_permille
    powers = {start, *range(low, NORMAL_POWER + 1, step)}
    ordered = sorted(powers, key=lambda p: (abs(p - start), -p))
    return [(p, dict(c)) for p in ordered for c in costs]
