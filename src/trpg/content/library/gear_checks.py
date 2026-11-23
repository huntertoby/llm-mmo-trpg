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
    TerrainAffix,
    TriggerAffix,
    WeaponTraitAffix,
    loadout_problems,
    resolve_loadout,
)
from trpg.content.item_budget import ItemGenRules, item_gen_problems
from trpg.content.library.ruleset import Ruleset
from trpg.content.silent_strike import carries_silent
from trpg.content.skill_keywords import KeywordTable
from trpg.content.unit_rules import unit_rule_permille_problems
from trpg.content.weapon_params import set_weapon_param
from trpg.shared.errors import ContentError


@dataclass(frozen=True)
class _GearCatalog:
    """載入時檢查單位裝備用的物品、詞條與裝備規則（Phase 3G-G1）。"""

    items: dict[str, ItemDef]
    affixes: dict[str, AffixDef]
    rules: EquipmentRules
    offhand_names: dict[str, str]
    """副手 ID → 中文名（QF-6：詞條限定副手的訊息讀資料）。"""

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
        return [
            f"equipment：{p}"
            for p in loadout_problems(loadout, weapon, self.rules, self.offhand_names)
        ]


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
        if affix.reaction is not None:  # E4：反應篩選的 ID
            refs.append(("反應", affix.reaction, {r.id for r in ruleset.reactions.reactions}))
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


GEAR_GRANTABLE_KINDS: tuple[str, ...] = ("active", "reaction", "modifier", "passive")
"""裝備可以授予的技能種類（E1，08 8.28：主動、反應、修正、被動）；姿態不在其中。"""
GEAR_GRANTABLE_ZH: tuple[str, ...] = ("主動", "反應", "修正", "被動")
SIGNATURE_SKILL_KINDS: dict[str, str] = {
    "action": "active",
    "reaction": "reaction",
    "behavior": "modifier",
}
"""授予技能（第 9 類）當招牌時，招牌種類 → 技能種類（E6-a1，08 8.27：新動作＝主動、新反應＝反應、
行為改寫＝修正）。"""


def _action_problems(affix: ActionAffix, ruleset: Ruleset) -> list[str]:
    """授予技能（G3b；E1 起四類）：授予的必須是主動、反應、修正或被動技（姿態不行）。"""
    skills = ruleset.skills.by_id()
    skill = skills.get(affix.skill)
    if skill is not None and skill.kind not in GEAR_GRANTABLE_KINDS:
        kinds = "、".join(GEAR_GRANTABLE_ZH)
        return [f"詞條 {affix.id} 授予的技能 {skill.id} 必須是{kinds}技（目前 {skill.kind}）"]
    if skill is not None and carries_silent(skill, skills):  # BS-1（#157）：無聲不做成詞條
        return [f"詞條 {affix.id} 授予的技能 {skill.id} 會給「無聲」：無聲不能來自裝備詞條"]
    wanted = SIGNATURE_SKILL_KINDS.get(affix.signature or "")
    if skill is not None and wanted is not None and skill.kind != wanted:
        return [
            f"詞條 {affix.id}：招牌 {affix.signature} 授予的技能 {skill.id} 必須是 {wanted} 技"
            f"（目前 {skill.kind}）"
        ]
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
    root: Path,
    appearance: AppearanceTable,
    items: ItemTable,
    keywords: KeywordTable,
    offhands: Collection[str] | None = None,
) -> None:
    """外觀清單的關鍵字都是 3-24b1 的關鍵字；items.yaml 寫了的外觀欄位都認得且相容；形制限定的
    副手（``FormDef.offhands``，RG-5）都在 ``offhands.yaml``（``offhands`` 為 ``None`` 時不查）。"""
    path = root / "equipment" / "appearance.yaml"
    unknown = sorted(set(appearance.keywords) - set(keywords.ids()))
    if unknown:
        raise ContentError(path, f"未知的關鍵字：{', '.join(unknown)}")
    if offhands is not None:
        bad = sorted(
            f"{kind.id}.{form.id}：{o}"
            for kind in appearance.kinds
            for form in kind.forms
            for o in form.offhands or ()
            if o not in offhands
        )
        if bad:
            raise ContentError(path, f"形制限定了未知的副手：{'；'.join(bad)}")
    problems = [p for item in items.items for p in item_appearance_problems(item, appearance)]
    if problems:
        raise ContentError(root / "items.yaml", "；".join(problems))


def _terrain_affix_problems(
    affix: TerrainAffix, ruleset: Ruleset, weather_ids: Collection[str]
) -> list[str]:
    """地形規則（E2）：引用的天氣、地形存在；``permille`` 的上限同種族被動（``races.yaml`` 的
    ``limits``；沒有種族表時不檢查上限）。"""
    problems: list[str] = []
    bad_weather = sorted(set(affix.weathers or ()) - set(weather_ids))
    if bad_weather:
        problems.append(f"詞條 {affix.id}：未知的天氣 {'、'.join(bad_weather)}")
    terrain_ids = {t.id for t in ruleset.terrain.terrain}
    bad_terrain = sorted(set(affix.terrain or ()) - terrain_ids)
    if bad_terrain:
        problems.append(f"詞條 {affix.id}：未知的地形 {'、'.join(bad_terrain)}")
    if ruleset.races is not None:
        limits = ruleset.races.limits
        problems += [
            f"詞條 {affix.id}：{p}"
            for p in unit_rule_permille_problems(
                affix,
                max_sight_reduction=limits.max_sight_reduction_permille,
                max_resist=limits.max_resist_permille,
            )
        ]
    return problems


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
    *,
    weather_ids: Collection[str] = (),
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
    problems += [  # E2：地形規則引用的天氣、地形與 permille 上限
        p
        for affix in affixes.values()
        if isinstance(affix, TerrainAffix)
        for p in _terrain_affix_problems(affix, ruleset, weather_ids)
    ]
    if problems:
        raise ContentError(root / "affixes.yaml", "；".join(problems))
