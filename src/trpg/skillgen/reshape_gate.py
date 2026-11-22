"""裝備授予的行為改寫的預算閘門（E5，玩法交接 4.1.36 待決答覆 2；開發 PM 裁定 A）。

裝備授予的修正技（第 9 類詞條）若會讓技能變形（``shape_to``、``area_delta``、``allow_self_target``）
或讓普攻變形（``attack_shape``），變形後要用 **同一個技能預算檢查器**（:func:`skill_budget`）算
總點數，不能超過原技能的總點數：

- 沒超過：照常生效，傷害不降（1000‰）。
- 超過：照形狀係數自動降傷害——總點數裡傷害效果那部分乘上 ``p``‰，取剛好不超過原總點數的最大整數
  ``p``（無條件捨去）。
- 降到 ``modifier.reshape_gate_min_permille``（``skill_budget.yaml``，工坊可調）還超過，或變形後沒有
  傷害可降：那一招不能套用（0‰；畫面標灰寫「這招不能套用」）。
- 普攻用普攻的換算基準：單體普攻 → 普攻直線的形狀倍率（:func:`attack_line_shape_permille`）。

引擎不能匯入 skillgen，所以結果算成一張表放進規則包（:attr:`Ruleset.reshape_gates`，鍵
``<修正技 ID>|<技能 ID 或 attack>``，值為傷害‰，0＝不能套用），引擎只查表
（:mod:`trpg.engine.reshape_gate`）；表裡查不到的組合一律當「不能套用」。沒有裝備授予的變形修正技時
表是空的、不輸出，規則包與雜湊都不變。

**進戰鬥的規則包一律經過這裡**：內容庫載入（:func:`gate_library`，``load_checked_library``、網頁伺服器）
與加入 LLM／組合器技能（:func:`gated_with_skills`，取代直接呼叫 ``Ruleset.with_skills``）。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from fractions import Fraction

from trpg.content.equipment import ActionAffix
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.skills import SHAPE_CHANGES, SkillDef
from trpg.engine.modifiers import ActiveRule, reshaped_skill
from trpg.engine.reshape_gate import ATTACK_TARGET, BLOCKED, FULL, gate_key
from trpg.skillgen.budget import BudgetError, BudgetReport, attack_line_shape_permille, skill_budget

__all__ = [
    "attack_gate_permille",
    "gate_library",
    "gate_ruleset",
    "gated_with_skills",
    "gear_reshape_skills",
    "reshape_gates",
    "skill_gate_permille",
]

_DAMAGE = "damage"


def gear_reshape_skills(library: ContentLibrary, ruleset: Ruleset | None = None) -> list[SkillDef]:
    """會由裝備授予（第 9 類詞條引用）、而且有變形規則的修正技（依技能 ID）。"""
    rules = library.ruleset if ruleset is None else ruleset
    known = rules.skills.by_id()
    ids = sorted({a.skill for a in library.affixes.values() if isinstance(a, ActionAffix)})
    found: list[SkillDef] = []
    for skill_id in ids:
        skill = known.get(skill_id)
        if skill is not None and skill.is_modifier and _reshape_rules(skill):
            found.append(skill)
    return found


def _reshape_rules(skill: SkillDef) -> list[ActiveRule]:
    return [
        ActiveRule(skill, i, rule)
        for i, rule in enumerate(skill.modifiers)
        if rule.change.kind in SHAPE_CHANGES
    ]


def _min_permille(library: ContentLibrary) -> int:
    return library.budget.modifier.reshape_gate_min_permille


def _gate(over: Fraction, damage: Fraction, minimum: int) -> int:
    """總點數超出 ``over``、其中傷害占 ``damage`` 時，傷害要降到的倍率（‰；0＝不能套用）。"""
    if over <= 0:
        return FULL
    if damage <= 0:
        return BLOCKED
    permille = int((damage - over) * FULL / damage)  # 無條件捨去：降完不超過
    return permille if permille >= minimum else BLOCKED


def _damage_points(report: BudgetReport) -> Fraction:
    """總點數裡傷害效果的部分：``total`` × 傷害效果點數 ÷ ``raw``（條件、協同等倍率乘在 ``raw``
    上，所以按比例分）。"""
    if report.raw <= 0:
        return Fraction(0)
    share = sum((e.points for e in report.effects if e.type == _DAMAGE), Fraction(0))
    return report.total * share / report.raw


def skill_gate_permille(skill: SkillDef, shaped: SkillDef, library: ContentLibrary) -> int:
    """``skill`` 變形成 ``shaped`` 後的傷害倍率（‰；0＝不能套用）。算不出預算的一律不能套用。"""
    try:
        before = skill_budget(skill, library)
        after = skill_budget(shaped, library)
    except BudgetError:
        return BLOCKED
    return _gate(after.total - before.total, _damage_points(after), _min_permille(library))


def attack_gate_permille(library: ContentLibrary) -> int:
    """普攻變 2 格直線的傷害倍率（‰；0＝不能套用）：普攻的換算基準是基準武器傷害 × 形狀倍率，
    全部都是傷害，所以 ``p ＝ 單體倍率 ÷ 直線倍率``（無條件捨去）。"""
    before, after = attack_line_shape_permille(library)
    damage = Fraction(library.ruleset.core.budget_reference_weapon_damage * after, FULL)
    over = Fraction(library.ruleset.core.budget_reference_weapon_damage * (after - before), FULL)
    return _gate(over, damage, _min_permille(library))


def reshape_gates(ruleset: Ruleset, library: ContentLibrary) -> dict[str, int]:
    """``ruleset`` 裡每個（裝備授予的變形修正技, 會被它變形的主動技能或普攻）的傷害倍率。

    主動技能逐招套用那個修正技的變形規則（不看 ``applies_to``：引擎實際套用時才看對象；形狀沒變的
    不列）；射程寫「武器射程」的照 ``range_baseline`` 算（射程係數 1）。"""
    mods = gear_reshape_skills(library, ruleset)
    if not mods:
        return {}
    weapon_range = library.budget.range_baseline
    actives = [s for s in sorted(ruleset.skills.skills, key=lambda s: s.id) if s.kind == "active"]
    table: dict[str, int] = {}
    for mod in mods:
        rules = _reshape_rules(mod)
        if any(r.rule.change.attack_shape is not None for r in rules):
            table[gate_key(mod.id, ATTACK_TARGET)] = attack_gate_permille(library)
        skill_rules = [r for r in rules if r.rule.change.attack_shape is None]
        if not skill_rules:
            continue
        for skill in actives:
            shaped = reshaped_skill(ruleset, skill, skill_rules, weapon_range)
            if shaped is not skill:
                table[gate_key(mod.id, skill.id)] = skill_gate_permille(skill, shaped, library)
    return table


def gate_ruleset(ruleset: Ruleset, library: ContentLibrary) -> Ruleset:
    """填好閘門表的規則包（表沒變時回傳原物件；沒有裝備授予的變形修正技時表是空的）。"""
    table = reshape_gates(ruleset, library)
    if table == ruleset.reshape_gates:
        return ruleset
    return ruleset.model_copy(update={"reshape_gates": table})


def gate_library(library: ContentLibrary) -> ContentLibrary:
    """規則包填好閘門表的內容庫（:func:`gate_ruleset`；沒變時回傳原物件）。"""
    gated = gate_ruleset(library.ruleset, library)
    return library if gated is library.ruleset else dataclasses.replace(library, ruleset=gated)


def gated_with_skills(
    library: ContentLibrary, skills: Iterable[SkillDef], ruleset: Ruleset | None = None
) -> Ruleset:
    """``(ruleset or library.ruleset).with_skills(skills)`` 再重算閘門表（新加的 LLM、組合器技能也要
    查得到）。進戰鬥的規則包加技能一律用這個，不直接呼叫 ``with_skills``。"""
    base = library.ruleset if ruleset is None else ruleset
    return gate_ruleset(base.with_skills(skills), library)
