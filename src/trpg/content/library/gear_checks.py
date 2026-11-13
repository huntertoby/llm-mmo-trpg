"""武器詞條、外觀與物品生成的跨檔案檢查。"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

from trpg.content.appearance import AppearanceTable, item_appearance_problems
from trpg.content.battle import OffhandDef, UnitTemplate, WeaponDef
from trpg.content.equipment import (
    ActionAffix,
    AffixDef,
    ChargeAffix,
    ConditionalAffix,
    EquipmentRules,
    ItemDef,
    ItemTable,
    KeywordAffix,
    ReactionAffix,
    RuleAffix,
    TriggerAffix,
    WeaponTraitAffix,
    loadout_problems,
    resolve_loadout,
)
from trpg.content.item_budget import ItemGenRules, item_gen_problems
from trpg.content.library.ruleset import Ruleset
from trpg.content.silent_strike import carries_silent
from trpg.content.skill_keywords import KeywordTable
from trpg.content.weapon_params import set_weapon_param
from trpg.shared.errors import ContentError


@dataclass(frozen=True)
class _GearCatalog:
    """載入時檢查單位裝備用的物品、詞條與裝備規則（Phase 3G-G1）。"""

    items: dict[str, ItemDef]
    affixes: dict[str, AffixDef]
    rules: EquipmentRules

    def offhand_of(self, template: UnitTemplate) -> OffhandDef | None:
        """範本裝備的副手定義（沒有或解析失敗為 ``None``；解析失敗由 :meth:`problems` 回報）。"""
        try:
            return resolve_loadout(template.equipment, self.items, self.affixes).offhand_def()
        except ValueError:
            return None

    def problems(self, template: UnitTemplate, weapon: WeaponDef) -> list[str]:
        try:
            loadout = resolve_loadout(template.equipment, self.items, self.affixes)
        except ValueError as exc:
            return [f"equipment：{exc}"]
        return [f"equipment：{p}" for p in loadout_problems(loadout, weapon, self.rules)]


def _trait_problems(affix: WeaponTraitAffix, weapons: Mapping[str, WeaponDef]) -> list[str]:
    """武器特性強化：限定的武器存在、參數路徑在這些武器上存在，而且套用一次之後武器資料仍然合法。"""
    problems: list[str] = []
    for weapon_id in affix.weapons:
        weapon = weapons.get(weapon_id)
        if weapon is None:
            problems.append(f"詞條 {affix.id} 引用了未知的武器：{weapon_id}")
            continue
        data = weapon.model_dump()
        factor = affix.scale_permille
        if not set_weapon_param(data, affix.param, affix.delta, factor):
            problems.append(f"詞條 {affix.id}：武器 {weapon_id} 沒有可改的參數 {affix.param}")
            continue
        try:
            WeaponDef.model_validate(data)
        except ValueError as exc:
            problems.append(f"詞條 {affix.id}：改 {weapon_id}.{affix.param} 後武器不合法：{exc}")
    return problems


def _affix_reference_problems(
    affix: AffixDef,
    ruleset: Ruleset,
    weapons: Mapping[str, WeaponDef],
    keyword_ids: frozenset[str],
) -> list[str]:
    """詞條引用的條件、狀態、觸發時機、反應與規則改變存在（Phase 3G-G1）。

    Phase 3G-G2 起也檢查：技能強化的關鍵字 id（對照推導表）、武器特性強化限定的武器與參數。
    Phase 3G-G3a 起也檢查：觸發與充能的時機（對象要有「另一方」）、效果原語、充能的層數。
    Phase 3G-G3b 起也檢查：授予動作的技能（存在、主動技）、授予反應的反應與事件。
    """
    statuses = {s.id for s in ruleset.statuses.statuses}
    refs: list[tuple[str, str, set[str]]] = []
    if isinstance(affix, ConditionalAffix):
        refs.append(("條件", affix.condition.type, {c.id for c in ruleset.conditions.conditions}))
    if isinstance(affix, TriggerAffix):
        refs.append(("觸發時機", affix.trigger, {t.id for t in ruleset.skill_triggers.triggers}))
    if isinstance(affix, ChargeAffix):
        refs.append(
            ("觸發時機", affix.gain_trigger, {t.id for t in ruleset.skill_triggers.triggers})
        )
    if isinstance(affix, RuleAffix):
        refs.append(("規則改變", affix.rule, {r.id for r in ruleset.rule_changes.rule_changes}))
    if isinstance(affix, ReactionAffix):
        refs.append(("反應", affix.reaction, {r.id for r in ruleset.reactions.reactions}))
    if isinstance(affix, ActionAffix):
        refs.append(("技能", affix.skill, set(ruleset.skills.by_id())))
    for status in _affix_statuses(affix):
        refs.append(("狀態", status, statuses))
    if isinstance(affix, KeywordAffix):
        refs.append(("關鍵字", affix.keyword, set(keyword_ids)))
    extra = _trait_problems(affix, weapons) if isinstance(affix, WeaponTraitAffix) else []
    if isinstance(affix, ActionAffix):
        extra += _action_problems(affix, ruleset)
    if isinstance(affix, ReactionAffix):
        extra += _reaction_affix_problems(affix, ruleset)
    if isinstance(affix, TriggerAffix | ChargeAffix):
        extra += _trigger_charge_problems(affix, ruleset)
    return extra + [
        f"詞條 {affix.id} 引用了未知的{what}：{ref}"
        for what, ref, known in refs
        if ref not in known
    ]


def _action_problems(affix: ActionAffix, ruleset: Ruleset) -> list[str]:
    """授予動作（G3b）：授予的必須是主動技（被動技與反應技不是「動作」）。"""
    skills = ruleset.skills.by_id()
    skill = skills.get(affix.skill)
    if skill is not None and skill.kind != "active":
        return [f"詞條 {affix.id} 授予的技能 {skill.id} 必須是主動技（目前 {skill.kind}）"]
    if skill is not None and carries_silent(skill, skills):  # BS-1（#157）：無聲不做成詞條
        return [f"詞條 {affix.id} 授予的技能 {skill.id} 會給「無聲」：無聲不能來自裝備詞條"]
    return []


def _reaction_affix_problems(affix: ReactionAffix, ruleset: Ruleset) -> list[str]:
    """授予反應（G3b）：``extend_trigger`` 的事件必須是該反應支援的事件；``grant`` 的反應必須有
    ``range``（目前只有 ``redirect_damage``），也不能需要狀態。"""
    definition = ruleset.reactions.by_id().get(affix.reaction)
    if definition is None:
        return []
    if affix.mode == "extend_trigger" and affix.event not in definition.events:
        return [f"詞條 {affix.id}：反應 {affix.reaction} 不支援事件 {affix.event}"]
    if affix.mode == "grant" and (definition.effect != "redirect_damage" or affix.range is None):
        return [f"詞條 {affix.id}：授予的反應必須是 redirect_damage 並填寫 range"]
    return []


def _trigger_charge_problems(affix: TriggerAffix | ChargeAffix, ruleset: Ruleset) -> list[str]:
    """觸發與充能詞條（G3a）：效果原語存在；觸發對象（目標、攻擊者）需要該時機有「另一方」；
    充能的層數存在、屬於持有者自己（``owner: self``）且裝備版上限不超過層數本身的上限。"""
    problems = [
        f"詞條 {affix.id} 引用了未知的效果原語：{e.type}"
        for e in affix.effects
        if e.type not in ruleset.primitives.by_id()
    ]
    if isinstance(affix, ChargeAffix):
        stacks = ruleset.stacks.by_id()
        stack = stacks.get(affix.stack)
        if stack is None:
            problems.append(f"詞條 {affix.id} 引用了未知的層數：{affix.stack}")
        elif stack.owner != "self" or affix.max_stacks > stack.max:
            problems.append(
                f"詞條 {affix.id} 的層數 {stack.id} 必須是 owner: self 且上限不小於 max_stacks"
            )
        return problems
    triggers = ruleset.skill_triggers.by_id()
    trigger = triggers.get(affix.trigger)
    if trigger is not None and affix.effect_target != "self" and not trigger.has_other:
        problems.append(
            f"詞條 {affix.id}：時機 {affix.trigger} 沒有另一方，effect_target 只能是 self"
        )
    if affix.effect_target == "attacker" and affix.trigger != "on_damaged":
        problems.append(f"詞條 {affix.id}：effect_target: attacker 只能搭配 on_damaged")
    return problems


def _affix_statuses(affix: AffixDef) -> list[str]:
    found: list[str] = []
    for name in ("status", "on_hit_status"):
        value = getattr(affix, name, None)
        if isinstance(value, str):
            found.append(value)
    for effect in getattr(affix, "effects", ()):
        if effect.status is not None:
            found.append(effect.status)
    return found


def _check_appearance(
    root: Path, appearance: AppearanceTable, items: ItemTable, keywords: KeywordTable
) -> None:
    """外觀清單的關鍵字都是 3-24b1 的關鍵字；items.yaml 寫了的外觀欄位都認得且相容。"""
    unknown = sorted(set(appearance.keywords) - set(keywords.ids()))
    if unknown:
        raise ContentError(
            root / "equipment" / "appearance.yaml", f"未知的關鍵字：{', '.join(unknown)}"
        )
    problems = [p for item in items.items for p in item_appearance_problems(item, appearance)]
    if problems:
        raise ContentError(root / "items.yaml", "；".join(problems))


def _check_item_gen(root: Path, rules: ItemGenRules, affixes: Mapping[str, AffixDef]) -> None:
    """物品產生器的係數和詞條白名單一致（Phase 3K-1）。"""
    problems = item_gen_problems(rules, affixes)
    if problems:
        raise ContentError(root / "item_gen.yaml", "；".join(problems))


def _check_affixes(
    root: Path,
    affixes: Mapping[str, AffixDef],
    ruleset: Ruleset,
    weapons: Mapping[str, WeaponDef],
    offhands: Collection[str] = (),
) -> None:
    keyword_ids = frozenset(ruleset.keywords.ids())
    problems = [
        p
        for affix in affixes.values()
        for p in _affix_reference_problems(affix, ruleset, weapons, keyword_ids)
    ]
    problems += [  # RG-4：限定副手的詞條引用的副手存在
        f"詞條 {affix.id} 引用了未知的副手：{o}"
        for affix in affixes.values()
        for o in affix.offhands
        if o not in offhands
    ]
    if problems:
        raise ContentError(root / "affixes.yaml", "；".join(problems))
