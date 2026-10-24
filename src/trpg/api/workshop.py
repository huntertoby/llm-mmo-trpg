"""技能工坊的伺服器端邏輯（Phase 3F-1）：「裝上試玩」把自訂技能裝到主角身上。

規則全部沿用既有函式：技能以 :func:`trpg.skillgen.draft.build_skill`（schema）與
:func:`trpg.skillgen.validate.validate_skill`（骨架、互斥、稀有度、預算）檢查，以
:meth:`trpg.content.library.Ruleset.with_skills` 加入規則包（與內容庫載入同一份引用檢查），
裝備上限用 :func:`trpg.content.skills.skill_slot_problems`、武器相容用
:func:`~trpg.content.skills.weapon_problem`。
自訂技能的定義存在戰鬥設定的規則包裡，所以下載的戰鬥紀錄可以直接 ``trpg battle replay``。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trpg.content.equipment import loadout_held
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_slot_problems, weapon_problem
from trpg.engine.setup import BattleSetup
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.skillgen.draft import DraftError, build_skill
from trpg.skillgen.validate import validate_skill

__all__ = ["WorkshopRequestError", "custom_skill_defs", "equip_custom_skills"]


class WorkshopRequestError(TrpgError):
    """自訂技能不合法、裝不下或對手設定錯誤（422，中文原因）。"""


def custom_skill_defs(library: ContentLibrary, raw: Sequence[Mapping[str, Any]]) -> list[SkillDef]:
    """請求中的自訂技能定義 → :class:`SkillDef`；schema 或規則不合法時拋出
    :class:`WorkshopRequestError`（列出每個技能的原因）。"""
    skills: list[SkillDef] = []
    problems: list[str] = []
    for index, data in enumerate(raw):
        label = f"自訂技能 {index + 1}「{data.get('name_zh') or data.get('id') or '未命名'}」"
        try:
            skill = build_skill(data)
        except DraftError as exc:
            problems.append(f"{label}：{'；'.join(exc.messages)}")
            continue
        violations = validate_skill(skill, library)
        if violations:
            problems.append(f"{label}不合法：{'；'.join(v.message for v in violations)}")
            continue
        skills.append(skill)
    ids = [s.id for s in skills]
    if len(set(ids)) != len(ids):
        problems.append("自訂技能的 ID 不可重複")
    if problems:
        raise WorkshopRequestError("；".join(problems))
    return skills


def _hero_skills(
    template_skills: tuple[str, ...], custom: Sequence[SkillDef], replace: Sequence[str]
) -> tuple[str, ...]:
    """被替換的技能位置依序換成自訂技能，多出來的自訂技能接在最後。"""
    pending = [s.id for s in custom]
    out: list[str] = []
    for skill_id in template_skills:
        if skill_id in replace:
            if pending:
                out.append(pending.pop(0))
            continue
        out.append(skill_id)
    return (*out, *pending)


def equip_custom_skills(
    setup: BattleSetup, custom: Sequence[SkillDef], replace: Sequence[str]
) -> BattleSetup:
    """把自訂技能裝到主角（我方第一個單位）身上：先拿掉 ``replace`` 的技能，再檢查裝備上限與
    武器。"""
    hero_index = next(i for i, u in enumerate(setup.units) if u.team is Team.ALLY)
    hero = setup.units[hero_index]
    unknown = [s for s in replace if s not in hero.template.skills]
    if unknown:
        raise WorkshopRequestError(
            f"主角 {hero.template.name_zh} 沒有裝備要替換的技能：{'、'.join(unknown)}"
            f"（目前：{'、'.join(hero.template.skills) or '無'}）"
        )
    try:
        ruleset = setup.ruleset.with_skills(custom)
    except ValueError as exc:
        raise WorkshopRequestError(f"自訂技能無法加入規則包：{exc}") from exc
    skills = _hero_skills(hero.template.skills, custom, replace)
    defs = ruleset.skills.by_id()
    problems = skill_slot_problems((defs[s] for s in skills), ruleset.core.skill_slots)
    held = loadout_held(hero.weapon, hero.equipment)
    problems += [
        p for s in custom if (p := weapon_problem(s, hero.weapon.weapon_class, held)) is not None
    ]
    if problems:
        raise WorkshopRequestError("；".join(problems))
    template = hero.template.model_copy(update={"skills": skills})
    units = list(setup.units)
    units[hero_index] = hero.model_copy(update={"template": template})
    return setup.model_copy(update={"units": tuple(units), "ruleset": ruleset})
