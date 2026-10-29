"""技能查詢與欄位輔助：武器需求、元素、持有裝備、欄位數檢查。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from trpg.content.rules import SkillSlots
from trpg.content.skills.constants import _ELEMENT_VALUES, _GROUP_NAMES, _REQ_NAMES
from trpg.content.skills.effects import EffectSpec
from trpg.content.skills.skill import SkillDef
from trpg.shared.types import Element


def on_hit_carrier(skill: SkillDef, effects: tuple[EffectSpec, ...]) -> SkillDef:
    """把修正規則的命中後效果包成一個「技能」（同一個修正技能的複本，``effects`` 換成命中後
    效果），讓驗證、預算與引擎的自動命中施放沿用一般技能的程式。不經過 schema 驗證。"""
    return skill.model_copy(update={"effects": effects})


def skill_elements(skill: SkillDef) -> frozenset[Element]:
    """技能的元素（Phase 3-54d，06 6.33「大地元素的判定與限制」）：技能元素欄（``element``）有填就是
    它；
    沒填時沿用 ``tags`` 裡的元素名稱（組合器的主題元素、手寫技能的主題標籤），有多個元素標籤時取
    **第一個非物理的**（保守：只算一個元素）。物理不算（物理是沒有元素）。**效果自己寫的元素不算**：
    一段大地傷害不會讓技能變成大地技能。"""
    if skill.element is not None:
        found = {skill.element}
    else:
        tagged = (Element(t) for t in skill.tags if t in _ELEMENT_VALUES)
        found = {next((e for e in tagged if e is not Element.PHYSICAL), Element.PHYSICAL)}
    found.discard(Element.PHYSICAL)
    return frozenset(found)


def is_wind_skill(skill: SkillDef) -> bool:
    """風元素的技能（Phase 3-54a，06 6.33）：頂層有 ``element: wind`` 的傷害效果。

    風壓撞擊（推擊的撞擊傷害加成）用這個判斷；只看技能資料（卡片、預算與實戰同源），武器詞條或
    修正規則在戰鬥中加上的風元素不算。"""
    return any(e.type == "damage" and e.element is Element.WIND for e in skill.effects)


# ---------------------------------------------------------------------------
# 單位與技能
# ---------------------------------------------------------------------------


def weapon_problem(
    skill: SkillDef,
    weapon_class: str,
    held: Mapping[str, str] | None = None,
    *,
    names: Mapping[str, str] | None = None,
) -> str | None:
    """技能的 ``weapon_req`` 與武器分類不相容、或不是限定武器（``weapon_only``，3I-5）時的原因。

    ``held``：單位手上的主手武器與副手（ID → 中文名，見 :func:`held_gear`）；技能有 ``weapon_only``
    而沒給 ``held`` 一律視為不符。``names``：ID → 中文名，只用來把限定武器寫成中文。"""
    if skill.weapon_req not in ("any", weapon_class):
        need, have = _REQ_NAMES[skill.weapon_req], _REQ_NAMES[weapon_class]
        return f"技能「{skill.name_zh}」需要{need}，但單位的武器是{have}"
    if skill.weapon_only and not (held and set(skill.weapon_only) & set(held)):
        lookup = names or {}
        need_text = "、".join(lookup.get(w, w) for w in skill.weapon_only)
        have_text = "、".join(sorted(held.values())) if held else "空手"
        return f"技能「{skill.name_zh}」限定手持{need_text}，但單位手上是{have_text}"
    return None


def held_gear(weapon: Any, offhand: Any = None) -> dict[str, str]:
    """單位手上的主手武器與副手（ID → 中文名），給 :func:`weapon_problem` 與 ``wielding_weapon``
    條件用；``weapon``／``offhand`` 是有 ``id``、``name_zh`` 的定義（副手可為 ``None``）。"""
    held = {weapon.id: weapon.name_zh}
    if offhand is not None:
        held[offhand.id] = offhand.name_zh
    return held


def skill_slot_problems(skills: Iterable[SkillDef], slots: SkillSlots) -> list[str]:
    """裝備的技能數量超過 ``core.yaml`` 的欄位上限時的原因（依 ``kind``），以及規則改變型傳說
    超過 1 個（Phase 3D-6）。"""
    skills = tuple(skills)
    # 修正技能（kind: modifier，3C-2）裝在被動欄位，與觸發型被動共用上限
    counts: Counter[str] = Counter(s.slot_kind for s in skills)
    limits = {
        "active": slots.active,
        "passive": slots.passive,
        "reaction": slots.reaction,
        "stance": slots.stance,
    }
    names = {"active": "主動", "passive": "被動（含修正）", "reaction": "反應", "stance": "姿態"}
    problems = [
        f"{names[kind]}技能超過欄位上限：{counts[kind]} 個（上限 {limits[kind]}）"
        for kind in limits
        if counts[kind] > limits[kind]
    ]
    groups: dict[str, list[str]] = {}
    for s in skills:
        if s.exclusive_group is not None:
            groups.setdefault(s.exclusive_group, []).append(s.name_zh)
    for group in sorted(groups):  # 專精互斥（3-33f1）：同一群組最多裝 1 個
        if len(groups[group]) > 1:
            problems.append(
                f"{_GROUP_NAMES.get(group, group)}只能擇一裝備，收到 {len(groups[group])} 個："
                f"{'、'.join(sorted(groups[group]))}"
            )
    changes = sorted(s.name_zh for s in skills if s.rule_change_id is not None)
    if len(changes) > 1:  # 改變規則型傳說每人最多裝 1 個（Phase 3D-6，使用者決定）
        problems.append(
            f"規則改變型傳說每人最多裝 1 個，收到 {len(changes)} 個：{'、'.join(changes)}"
        )
    return problems
