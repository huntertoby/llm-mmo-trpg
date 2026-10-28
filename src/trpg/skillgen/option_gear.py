"""工坊的武器親和與限定武器選單（Phase 3I-5，06 6.10 #50）。

- **限定武器**（``weapon_only``，基本設定步驟，多選）：只有手持清單裡的武器（或副手）才能裝備、
  施放；專屬招牌技用。
- **武器親和**（效果的 ``condition: wielding_weapon``）：效果只在手持指定武器時生效，沒拿時技能
  照常可用、只是少那個效果。每個效果的選單多一個「武器親和」欄位。

選項與驗證器 **同源**：武器大類與技能 ``weapon_req`` 不符的選項，用
:func:`trpg.content.library.gear_class_problem`（驗證器 ``gear_reference_problems`` 用的同一個函式）
事前停用（``info.unavailable_zh``，3-48h 的機制）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary, gear_class_problem
from trpg.skillgen.draft import Draft
from trpg.skillgen.option_models import Choice, FieldSpec

__all__ = [
    "AFFINITY_PRIMITIVES",
    "gear_choices",
    "gear_pool",
    "weapon_only_field",
]

AFFINITY_PRIMITIVES: frozenset[str] = frozenset(
    {"damage", "apply_status", "heal", "shield", "push", "pull", "knock_prone", "create_surface"}
)
"""工坊的效果選單會多出「武器親和」欄位的原語（帶一個有武器加成的效果最常見的幾種）。"""

_CLASS_NAME = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器"}


def gear_pool(library: ContentLibrary) -> tuple[tuple[str, str, str], ...]:
    """玩家手上會出現的武器與副手：（ID、中文名、說明）。武器不含召喚物專用的，副手只列有物品的
    （``items.yaml`` 引用的），依資料檔順序。"""
    out = [
        (w.id, w.name_zh, _CLASS_NAME[w.weapon_class])
        for w in library.weapons.values()
        if not w.summon_only
    ]
    used = {i.offhand for i in library.items.values() if i.offhand is not None}
    out += [(o.id, o.name_zh, "副手") for o in library.offhands.values() if o.id in used]
    return tuple(out)


def gear_choices(library: ContentLibrary, weapon_req: object) -> tuple[Choice, ...]:
    """武器與副手的選項；大類與 ``weapon_req`` 不符的武器標上 ``unavailable_zh``。"""
    choices: list[Choice] = []
    for gear_id, name, desc in gear_pool(library):
        info: dict[str, object] = {}
        if isinstance(weapon_req, str):
            problem = gear_class_problem(weapon_req, gear_id, library.weapons, library.offhands)
            if problem is not None:
                info["unavailable_zh"] = problem
        choices.append(Choice(value=gear_id, name_zh=name, description_zh=desc, info=info))
    return tuple(choices)


def weapon_only_field(draft: Draft, library: ContentLibrary) -> FieldSpec:
    """限定武器（多選）；不選 ＝ 不限（照武器需求）。"""
    return FieldSpec(
        field="weapon_only",
        name_zh="限定武器",
        description_zh=(
            "專屬招牌技：只有手持勾選的武器（或副手）才能裝備、施放；不勾就是同大類武器都能用"
        ),
        type="multi_choice",
        choices=gear_choices(library, draft.get("weapon_req")),
    )
