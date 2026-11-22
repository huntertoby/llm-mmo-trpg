"""技能、關鍵字、技能規則與裝備引用的跨檔案檢查。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from trpg.content.battle import OffhandDef, WeaponDef
from trpg.content.keyword_derive import skill_condition_specs
from trpg.content.library.ruleset import Ruleset, skill_reference_problems
from trpg.content.regions import RegionTable
from trpg.content.silent_strike import silent_strike_problems
from trpg.content.skill_icon_props import IconPropTable, icon_prop_problem
from trpg.content.skill_keywords import KeywordRule, KeywordTable
from trpg.content.skill_rules import BudgetRules, ExclusionTable, SkeletonDef, SkillMatch
from trpg.content.skills import MODIFIER_CHANGES, SkillDef
from trpg.content.skills.limits import skill_limit_problems
from trpg.shared.errors import ContentError

# WL-1 b（a 段裁定 4）：程式依骨架 id 寫死、骨架被刪時會出錯的地方。其他骨架只靠資料，不放這裡。
# 只列「找不到就丟例外」的用法；只做等值比較（找不到就走預設）、
# 或組出草稿再驗證（不合法就丟掉）的不列。
# 改到下面的程式時同步這份
# （``tests/content/test_code_required_skeletons.py`` 掃 ``library.skeletons["…"]``）。
CODE_REQUIRED_SKELETONS: Mapping[str, str] = {
    "area": "形態的吐息技（content/form_breath.py 直接建 SkillDef）",
    "passive": "組合器的被動技配方（skillgen/composer_recipes.py 的 library.skeletons[…]）",
    "reaction": "組合器的反應技與護主配方（skillgen/composer_recipes.py 的 library.skeletons[…]）",
    "stance": "隨機組合器的姿態技（skillgen/random_composer.py 的 library.skeletons[…]）",
    "summon": "組合器的整招召喚配方（skillgen/composer_recipes.py 的 library.skeletons[…]）",
}
"""程式需要的骨架：id → 用到它的地方（錯誤訊息用）。"""


def check_code_required_skeletons(root: Path) -> None:
    """程式需要的骨架（:data:`CODE_REQUIRED_SKELETONS`）都要有資料檔（WL-1 b）。

    讀任何表之前先看 ``skeletons/`` 的檔名：原語的 ``allowed_skeletons``、技能檔也會引用被刪的骨架，
    先報這一條（說明程式哪裡要它）。"""
    files = {p.stem for p in (root / "skeletons").glob("*.yaml")}
    needed = [
        f"{n}（{why}）" for n, why in sorted(CODE_REQUIRED_SKELETONS.items()) if n not in files
    ]
    if needed:
        raise ContentError(root / "skeletons", f"缺少程式需要的骨架：{'；'.join(needed)}")


def gear_reference_problems(
    skill: SkillDef, weapons: Mapping[str, WeaponDef], offhands: Mapping[str, OffhandDef]
) -> list[str]:
    """技能的限定武器（``weapon_only``）與「手持某種武器」條件引用的武器或副手存在，而且武器的
    大類符合技能的 ``weapon_req``（否則技能永遠不能裝，或加成永遠不會成立；Phase 3I-5）。"""
    refs = [("weapon_only", w) for w in skill.weapon_only]
    refs += [
        ("wielding_weapon", c.weapon)
        for c in skill_condition_specs(skill)
        if c.type == "wielding_weapon" and c.weapon is not None
    ]
    found = (
        (where, gear_class_problem(skill.weapon_req, g, weapons, offhands)) for where, g in refs
    )
    return [f"{where}：{p}" for where, p in found if p is not None]


_CLASS_ZH = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}


def gear_class_problem(
    weapon_req: str,
    gear_id: str,
    weapons: Mapping[str, WeaponDef],
    offhands: Mapping[str, OffhandDef],
) -> str | None:
    """``gear_id``（武器或副手）不存在、或武器大類與技能的 ``weapon_req`` 不符時的原因。驗證器與
    工坊的事前停用共用（Phase 3I-5）。副手不分大類，永遠相符。"""
    weapon = weapons.get(gear_id)
    if weapon is None:
        return None if gear_id in offhands else f"未知的武器或副手 {gear_id!r}"
    if weapon_req in ("any", weapon.weapon_class):
        return None
    return (
        f"{weapon.name_zh}是{_CLASS_ZH[weapon.weapon_class]}武器，"
        f"與技能的武器需求（{_CLASS_ZH.get(weapon_req, weapon_req)}）不符"
    )


def _check_skills(
    root: Path,
    skills: dict[str, SkillDef],
    ruleset: Ruleset,
    budget: BudgetRules,
    *,
    weapons: Mapping[str, WeaponDef] | None = None,
    offhands: Mapping[str, OffhandDef] | None = None,
) -> None:
    """技能引用的形狀、原語、狀態、物件都存在，參數在範圍內；費用花的資源與類別相符（3H-2）；
    限定武器與手持條件引用的裝備存在且大類相符（3I-5）。"""
    for skill_id, skill in skills.items():
        problems = skill_reference_problems(skill, ruleset, skills)
        # HC-4b：技能結構的規則型上限（core.yaml 的 skill_limits；原本在 SkillDef schema）
        problems += skill_limit_problems(skill, ruleset.core.skill_limits)
        if weapons is not None and offhands is not None:
            problems += gear_reference_problems(skill, weapons, offhands)
        cost = budget.cost_problem(skill.category, skill.cost)
        if cost is not None:
            problems.append(cost)
        if problems:
            raise ContentError(root / "skills" / f"{skill_id}.yaml", "；".join(problems))


def _story_skill_problems(
    skill: SkillDef, ruleset: Ruleset, skills: Mapping[str, SkillDef], budget: BudgetRules
) -> list[str]:
    """劇情技能（``world/quests/`` 的 ``story_skills``，Phase 5B-4）的引用與費用檢查（同
    ``content/skills/``；不進技能池）。劇情技能是給玩家的，不能標 ``enemy_only``（5F-R1）。"""
    problems = skill_reference_problems(skill, ruleset, skills)
    if skill.enemy_only:
        problems.append("劇情技能是給玩家的，不能標 enemy_only")
    if skill.icon_prop is not None:  # IP-1：只有 content/skills/ 的手寫技能可以填（06 6.36）
        problems.append("劇情技能不能填 icon_prop（只有 content/skills/ 的手寫技能可以填）")
    cost = budget.cost_problem(skill.category, skill.cost)
    return problems if cost is None else [*problems, cost]


def _keyword_rule_problems(
    rule: KeywordRule, ruleset: Ruleset, skills: Mapping[str, SkillDef]
) -> list[str]:
    """關鍵字推導規則引用的原語、條件、觸發、形狀、狀態、物件、層數、規則改變、技能都存在。"""
    known: dict[str, set[str]] = {
        "effect": set(ruleset.primitives.by_id()),
        "condition": set(ruleset.conditions.by_id()),
        "trigger": set(ruleset.skill_triggers.by_id()),
        "shape": set(ruleset.shapes.by_id()),
        "change": set(MODIFIER_CHANGES),
    }
    problems: list[str] = []
    if rule.source_id not in known[rule.source]:
        problems.append(f"未知的{rule.source} {rule.source_id!r}")
    params = rule.params()
    refs: dict[str, set[str]] = {
        "status": {s.id for s in ruleset.statuses.statuses},
        "object": {o.id for o in ruleset.objects.objects},
        "stack": set(ruleset.stacks.by_id()),
        "rule": set(ruleset.rule_changes.by_id()),
        "skill": set(skills),
        "infusion": set(ruleset.core.summon_infusions),
    }
    problems += [
        f"未知的 {name} {params[name]!r}"
        for name, ids in refs.items()
        if name in params and params[name] not in ids
    ]
    return problems


def _check_keywords(
    root: Path, keywords: KeywordTable, ruleset: Ruleset, skills: Mapping[str, SkillDef]
) -> None:
    """關鍵字推導表引用的內容都存在；帶無聲的技能是隱蔽關鍵字的技能（BS-1）。"""
    path = root / "skill_keywords.yaml"
    for keyword in keywords.keywords:
        for label, rules in (("makes", keyword.makes), ("uses", keyword.uses)):
            for index, rule in enumerate(rules):
                found = _keyword_rule_problems(rule, ruleset, skills)
                if found:
                    raise ContentError(path, f"{keyword.id}.{label}[{index}]：" + "；".join(found))
    for skill_id, skill in skills.items():  # BS-1（#157）：無聲只能來自隱蔽關鍵字的技能
        problems = silent_strike_problems(skill, skills, keywords)
        if problems:
            raise ContentError(root / "skills" / f"{skill_id}.yaml", "；".join(problems))


def _match_problems(match: SkillMatch | None, ruleset: Ruleset) -> list[str]:
    """互斥規則的比對引用的形狀、狀態、原語是否存在。"""
    if match is None:
        return []
    shape_ids, primitive_ids = set(ruleset.shapes.by_id()), set(ruleset.primitives.by_id())
    status_ids = {s.id for s in ruleset.statuses.statuses}
    problems = [f"未知的形狀 {p.type!r}" for p in match.shapes or () if p.type not in shape_ids]
    problems += [f"未知的狀態 {s!r}" for s in match.statuses or () if s not in status_ids]
    refs = [*(match.primitives_any or ()), *(match.primitives_all or ())]
    refs += [e.type for e in [*(match.effects_any or ()), *(match.effects_all or ())] if e.type]
    problems += [f"未知的原語 {r!r}" for r in refs if r not in primitive_ids]
    for sub in match.any_of or ():
        problems += _match_problems(sub, ruleset)
    return problems


def _check_skill_rules(
    root: Path,
    ruleset: Ruleset,
    exclusions: ExclusionTable,
    skeletons: dict[str, SkeletonDef],
    skills: Mapping[str, SkillDef],
) -> None:
    """互斥規則與骨架引用的形狀、狀態、原語都存在；骨架的 ``order`` 不重複；技能（含複合技能的
    第二段）用到的骨架都有資料檔。"""
    path = root / "skill_exclusions.yaml"
    for rule in exclusions.rules:
        found = [
            *_match_problems(rule.when, ruleset),
            *_match_problems(rule.forbid, ruleset),
            *_match_problems(rule.require, ruleset),
        ]
        if found:
            raise ContentError(path, f"互斥規則 {rule.id}：" + "；".join(found))
    _check_skeleton_index(root, skeletons, skills)
    shape_ids, primitive_ids = set(ruleset.shapes.by_id()), set(ruleset.primitives.by_id())
    for skeleton_id, skeleton in skeletons.items():
        where = root / "skeletons" / f"{skeleton_id}.yaml"
        unknown = [s for s in skeleton.shapes if s not in shape_ids]
        if unknown:
            raise ContentError(where, f"未知的形狀：{', '.join(unknown)}")
        if not skeleton.enabled:
            continue  # 停用的骨架可以引用尚未實作的原語
        used = [*skeleton.core.primitives, *(skeleton.secondary.primitives or ())]
        unknown = [p for p in used if p not in primitive_ids]
        if unknown:
            raise ContentError(where, f"未知的原語：{', '.join(unknown)}")


def _check_skeleton_index(
    root: Path, skeletons: Mapping[str, SkeletonDef], skills: Mapping[str, SkillDef]
) -> None:
    """骨架清單就是 ``skeletons/`` 的檔案（WL-1）：``order`` 不重複；技能（含複合技能的第二段）
    用到的骨架都有資料檔。"""
    orders: dict[int, list[str]] = {}
    for skeleton_id in sorted(skeletons):
        orders.setdefault(skeletons[skeleton_id].order, []).append(skeleton_id)
    clashes = ["、".join(ids) for _, ids in sorted(orders.items()) if len(ids) > 1]
    if clashes:
        raise ContentError(root / "skeletons", f"骨架的 order 重複：{'；'.join(clashes)}")
    users: dict[str, list[str]] = {}
    for skill_id in sorted(skills):
        skill = skills[skill_id]
        names = (skill.skeleton, *(() if skill.followup is None else (skill.followup.skeleton,)))
        for name in dict.fromkeys(names):
            if name not in skeletons:
                users.setdefault(name, []).append(skill_id)
    if users:
        missing = "；".join(f"{n}（{'、'.join(ids)} 用到）" for n, ids in sorted(users.items()))
        raise ContentError(root / "skeletons", f"缺少骨架資料檔：{missing}")


def pool_region_problems(skills: Mapping[str, SkillDef], regions: RegionTable | None) -> list[str]:
    """技能的 ``pool_regions``（6F-4c 區域技能池）只能填 ``regions.yaml`` 的區域 ID，
    且不可是空串列。"""
    known = set() if regions is None else set(regions.region_by_id())
    problems: list[str] = []
    for skill_id in sorted(skills):
        found = skills[skill_id].pool_regions
        if found is None:
            continue
        if not found:
            problems.append(f"技能 {skill_id} 的 pool_regions 不可是空串列（不限區域請省略）")
        unknown = sorted(r for r in found if r not in known)
        if unknown:
            problems.append(f"技能 {skill_id} 的 pool_regions 有未知的區域：{'、'.join(unknown)}")
    return problems


def icon_prop_fixed_problem(skill: SkillDef) -> str | None:
    """化身招與看手上武器的招不能填 ``icon_prop``（Phase QI-2a D4，06 6.36）：圖示固定畫化身／那把
    武器（推導表的道具第 1、2 列排在 ``icon_prop`` 前面），填了也不生效。看的是效果與複合第二段的
    效果（和圖示推導同一份效果清單）；可以填時 ``None``。"""
    effects = [*skill.effects, *(skill.followup.effects if skill.followup is not None else ())]
    if any(e.type == "enter_form" for e in effects):
        return "化身招（效果有 enter_form）的圖示固定畫化身，不能填 icon_prop（填了不生效）"
    if any(e.condition is not None and e.condition.type == "wielding_weapon" for e in effects):
        return (
            "效果帶「手持某種武器」條件（wielding_weapon）的招圖示固定畫那把武器，"
            "不能填 icon_prop（填了不生效）"
        )
    return None


def icon_prop_problems(skills: Mapping[str, SkillDef], table: IconPropTable) -> list[str]:
    """技能的 ``icon_prop``（Phase IP-1，06 6.36）只能是 ``skill_icon_props.yaml`` 的道具，而且要和
    技能的 ``weapon_req`` 對得上（:func:`~trpg.content.skill_icon_props.icon_prop_problem`）；
    化身招與 ``wielding_weapon`` 招不能填（QI-2a D4，:func:`icon_prop_fixed_problem`）。"""
    problems: list[str] = []
    for skill_id in sorted(skills):
        skill = skills[skill_id]
        if skill.icon_prop is None:
            continue
        found = icon_prop_problem(skill.icon_prop, skill.weapon_req, table)
        if found is not None:
            problems.append(f"技能 {skill_id} 的 {found}")
        fixed = icon_prop_fixed_problem(skill)
        if fixed is not None:
            problems.append(f"技能 {skill_id}：{fixed}")
    return problems
