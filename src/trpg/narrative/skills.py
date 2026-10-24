"""技能的繁體中文描述（原在 ``trpg.cli.skills``，Phase 3-1 搬出，讓 CLI 與網頁技能卡片共用）。

- 形狀、縮放、專精、代價、條件與每個效果的一句話描述。
- 修正規則（Phase 3C-2，``kind: modifier``）的一句話描述（:func:`modifier_summary`）。
- :func:`skill_card` 把一個技能整理成 :class:`SkillCard`（pydantic，可直接當 API 回應）。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.battle import Dice, WeaponDef
from trpg.content.keyword_derive import KeywordGrade, keyword_grades, skill_facts
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.rule_changes import RuleChangeDef, rule_change_sentence
from trpg.content.skills import (
    CHEAT_DEATH_STATUS,
    DAMAGE_MULTIPLIER,
    REDIRECT_STATUS,
    SELF_DAMAGE_OF_HIT,
    ConditionSpec,
    EffectSpec,
    ModifierSpec,
    ModifierTarget,
    ShapeSpec,
    SkillDef,
    TriggerSpec,
    VariantSpec,
    VariantWhen,
    condition_text,
    default_affects,
    on_hit_carrier,
)
from trpg.content.stacks import StackDef
from trpg.engine.ids import SHIELDED as SHIELD_STATUS
from trpg.engine.summons import SummonStats
from trpg.narrative.skill_icon import SkillIcon, skill_icon
from trpg.narrative.skill_levels import SkillLevelInfo
from trpg.narrative.summon_info import (
    SummonInfoCard,
    infusion_hint,
    summon_acts,
    summon_card_hp,
    summon_info,
    summon_innate_lines,
)
from trpg.shared.types import Attribute, Surface, rune_name
from trpg.skillgen.budget import self_status_allowance_permille
from trpg.skillgen.keywords import (
    SkillKeywords,
    derive_draft_keywords,
    derive_keywords,
    draft_facts,
)

__all__ = [
    "CATEGORY_TEXT",
    "DESCRIBED_PRIMITIVES",
    "KIND_TEXT",
    "RARITY_TEXT",
    "WEAPON_REQ_TEXT",
    "CardOwner",
    "KeywordRef",
    "SkillCard",
    "SkillCardKeywords",
    "SkillLevelInfo",
    "SkillStackRef",
    "SkillVariantCard",
    "activation_text",
    "branch_text",
    "condition_summary",
    "contest_label",
    "cost_parts",
    "cost_summary",
    "draft_card_keywords",
    "effect_summary",
    "followup_text",
    "keywords_card",
    "mastery_text",
    "miss_text",
    "modifier_summary",
    "rule_change_text",
    "scaling_detail",
    "scaling_label",
    "scaling_text",
    "shape_summary",
    "skill_ap",
    "skill_card",
    "skill_shape_text",
    "variant_change_text",
    "variant_condition_text",
]

_AFFECTS = {
    "enemies": "敵方",
    "allies": "友方",
    "all": "所有單位",
    "self": "自己",
    "tiles": "影響的格子",
}
RARITY_TEXT = {"common": "普通", "rare": "稀有", "epic": "史詩", "legendary": "傳說"}
CATEGORY_TEXT = {"weapon": "武器技", "spell": "法術技"}
WEAPON_REQ_TEXT = {"melee": "近戰武器", "ranged": "遠程武器", "focus": "法器", "any": "任何武器"}
KIND_TEXT = {
    "active": "主動",
    "reaction": "反應",
    "passive": "被動",
    "stance": "姿態",
    "modifier": "修正",
}
_ACTION_TEXT = {"attack": "普攻", "shove": "推擊", "trip": "絆倒", "interact": "互動"}


def _dice(dice: Dice) -> str:
    return f"{dice.count}d{dice.sides}"


def shape_summary(library: ContentLibrary, shape: ShapeSpec) -> str:
    """形狀與參數的一句話，例如「錐形 3」「單體 射程 6」。"""
    name = library.ruleset.shape_def(shape.type).name_zh
    labels = {
        "range": "射程",
        "size": "大小",
        "radius": "半徑",
        "jumps": "跳躍",
        "jump_range": "跳躍距離",
    }
    parts: list[str] = []
    for key, value in shape.param_values().items():
        text = "武器射程" if value == "weapon" else str(value)
        parts.append(f"{labels[key]} {text}")
    return f"{name}（{'，'.join(parts)}）" if parts else name


def skill_shape_text(library: ContentLibrary, skill: SkillDef) -> str:
    """技能的形狀一句話；穿透的技能（Phase 3C-5b）加上「穿透」。"""
    text = shape_summary(library, skill.shape)
    return f"{text}・穿透" if skill.pierce else text


def followup_text(library: ContentLibrary, skill: SkillDef) -> str | None:
    """複合技能（Phase 3F-3a）第二段的一句話，例如「到達落點後，以落點為原點：錐形（大小 2）：
    傷害…」；不是複合技能時為 ``None``。"""
    follow = skill.followup_skill()
    if follow is None or skill.followup is None:
        return None
    effects = "；".join(effect_summary(library, follow, e) for e in follow.effects)
    when = f"［條件：{condition_summary(library, follow.condition)}］" if follow.condition else ""
    if skill.followup.release is not None:  # 延遲段（Phase 3F-4b）
        lead = _DELAYED_LEADS[skill.followup.release]
    else:
        lead = _FOLLOWUP_LEADS[skill.followup.when]
    return f"{lead}：{shape_summary(library, follow.shape)}{when}：{effects}"


_FOLLOWUP_LEADS = {
    "after_move": "到達落點後，以落點為原點",
    "after_action": "結算後，從自己的位置（自選落點）",
    "after_gather": "聚集後，以聚集點為中心",
    "on_kill": "擊倒敵人的話，從自己的位置（自選目標）",
    "on_hit": "命中的話，對同一個目標",
}
_DELAYED_LEADS = {
    "next_turn": "蓄力，下回合開始時以自己為中心釋放",
    "attacked": "蓄力，下回合開始前被敵人攻擊時以自己為中心釋放（沒被攻擊就失效）",
}
"""延遲段（Phase 3F-4b）第二段一句話的開頭（依 ``followup.release``）。"""
"""複合技能第二段一句話的開頭（依 ``followup.when``；Phase 3F-4a）。"""


WEAPON_ATTR_LABEL = "武器屬性"
"""武器技（看手上武器的屬性，Phase 3H-6）在效果句裡的縮放屬性簡稱。"""


def scaling_label(skill: SkillDef, lib: ContentLibrary | None = None) -> str:
    """縮放屬性的簡稱：單屬性為「智力」，雙屬性為「力量／智力」（Phase 2H-2）。武器技看手上武器
    （3H-6）：給了 ``lib`` 時寫實際的屬性名——所需武器大類的主屬性（例「力量」），帶心智第二屬性
    時接在後面（「力量／智力」，3I-3；玩法 PM 2026-10-24：武器技所有數值都看手上武器，不加例外）；
    沒有 ``lib`` 時寫「武器屬性」。"""
    if skill.category == "weapon":
        if lib is None:
            return WEAPON_ATTR_LABEL
        names = [lib.skill_scaling.weapon_class_attr(skill.weapon_req).display_name]
        if skill.secondary_scaling_attr is not None:
            names.append(skill.secondary_scaling_attr.display_name)
        return "／".join(names)
    names = [skill.scaling_attr.display_name]
    if skill.secondary_scaling_attr is not None:
        names.append(skill.secondary_scaling_attr.display_name)
    return "／".join(names)


def contest_label(skill: SkillDef, lib: ContentLibrary | None = None) -> str:
    """對抗判定（擊倒、位移、狀態抵抗）的屬性簡稱：武器技只用武器的主屬性（第二屬性不參與對抗，
    :meth:`SkillDef.contest_attr`），其他同 :func:`scaling_label`。"""
    if skill.category == "weapon" and lib is not None:
        return lib.skill_scaling.weapon_class_attr(skill.weapon_req).display_name
    return scaling_label(skill, lib)


def scaling_detail(skill: SkillDef, weapon: WeaponDef | None = None) -> str:
    """縮放屬性的完整說明：雙屬性為「力量 50%＋智力 50%」。武器技（3H-6）看手上武器：有武器時寫
    武器的屬性（例「敏捷／力量（取較高）」），沒有時寫「武器的屬性」。"""
    if skill.category == "weapon":
        base = "武器的屬性" if weapon is None else weapon.scaling_names_zh()
        if skill.secondary_scaling_attr is None:
            return base
        return f"{base}＋{skill.secondary_scaling_attr.display_name}（取平均）"
    if skill.secondary_scaling_attr is None:
        return skill.scaling_attr.display_name
    return f"{skill.scaling_attr.display_name} 50%＋{skill.secondary_scaling_attr.display_name} 50%"


def mastery_text(
    skill: SkillDef, *, active: bool | None = None, weapon: WeaponDef | None = None
) -> str:
    """專精加成的說明；``active`` 為 ``None`` 表示不知道單位（只顯示加成內容）。武器技（3H-6）
    看手上武器的屬性。"""
    effect = "施放距離 +1" if skill.mastery == "range" else "施加的狀態持續 +1 回合"
    attr = (
        scaling_detail(skill, weapon)
        if skill.category == "weapon"
        else (skill.scaling_attr.display_name)
    )
    note = f"（{attr}為最高屬性時生效）"
    if active is not None:
        note = f"（{attr}為最高屬性，生效中）" if active else f"（{attr}不是最高屬性，未生效）"
    return effect + note


# ---------------------------------------------------------------------------
# 效果：依原語類型的描述器註冊表
# ---------------------------------------------------------------------------

type _EffectText = Callable[[ContentLibrary, SkillDef, EffectSpec], str]


_SCALE_TEXT = {
    "missing_hp_10pct": "你每少 10% 最大 HP",
    "distance": "與目標每距 1 格",
    "enemies_adjacent_target": "目標每有 1 名相鄰的敵人",
    "enemies_adjacent_self": "你每有 1 名相鄰的敵人",
}
"""依情況縮放的依據（Phase 3D-7b）。"""


def scaling_text(spec: EffectSpec) -> str | None:
    """傷害的縮放一句話（Phase 3D-7b），例如「你每少 10% 最大 HP，傷害 +8%（最多 +80%）」。"""
    scaling = spec.scaling
    if scaling is None:
        return None
    return (
        f"{_SCALE_TEXT[scaling.by]}，傷害 +{scaling.per_step_permille / 10:g}%"
        f"（最多 +{scaling.cap_permille / 10:g}%）"
    )


def _damage(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    head, extras = _damage_parts(lib, skill, spec)
    return head + "".join(f"，{e}" for e in extras)


def _damage_parts(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> tuple[str, list[str]]:
    """傷害句（骰值、元素）與附加句（吸血、爆骰、擊殺時……）分開，讓對象後綴接在傷害句後面。"""
    discount = skill.damage_permille or 1000
    if skill.category == "spell":
        assert spec.dice is not None and spec.element is not None
        attr, element = scaling_label(skill, lib), spec.element.display_name
        text = f"{_dice(spec.dice)}＋{attr}加成的{element}傷害"
        if skill.damage_permille is not None:
            text += f"（基礎傷害 ×{discount / 1000:g}）"
    else:
        permille = (spec.multiplier_permille or 1000) * discount // 1000
        element = f"（{spec.element.display_name}）" if spec.element is not None else ""
        text = f"武器傷害 ×{permille / 1000:g}{element}"
    extras: list[str] = []
    if spec.split_heal:
        extras.append("友方（含自己）改為治療同樣的骰值（不擲命中，只骰一次）")
    if spec.lifesteal_permille is not None:
        extras.append(f"吸血：你回復造成傷害的 {spec.lifesteal_permille / 10:g}%")
    if spec.explode:
        extras.append(f"爆骰（擲到最大值再擲一次，每顆最多再擲 {lib.ruleset.core.explode_max} 次）")
    if skill.crit_range is not None:
        extras.append(f"暴擊範圍 {skill.crit_range}–20")
    scale = scaling_text(spec)
    if scale is not None:
        extras.append(scale)
    if spec.on_kill:
        kill = "、".join(_on_kill_text(lib, skill, sub) for sub in spec.on_kill)
        extras.append(f"若這一招讓敵人倒下：{kill}")
    return text, extras


def _on_kill_text(lib: ContentLibrary, skill: SkillDef, sub: EffectSpec) -> str:
    """擊殺時效果（``on_kill``，Phase 3D-8b）的一句話（對象一律是施放者）。"""
    if sub.type == "refund_ap":
        return f"返還 {sub.amount or 1} AP"
    if sub.type == "refund_cooldown":
        return "本技能冷卻歸零"
    return f"你{_effect_core(lib, skill, sub)}"


def _heal(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None
    return f"治療 {_dice(spec.dice)}＋{scaling_label(skill, lib)}加成"


def _push_pull(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    text = f"{'推開' if spec.type == 'push' else '拉近'} {spec.distance} 格"
    if spec.collision_dice is not None:
        text += f"（撞擊傷害 {_dice(spec.collision_dice)}）"
    return text


def _knock_prone(lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    return f"擊倒（{contest_label(skill, lib)}對抗）"


def _teleport(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "傳送到目標格"


def _dash(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "衝鋒到目標身旁（先結算，不消耗移動點數；途中會被藉機攻擊與陷阱攔下）"


def _leap(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "跳到目標格（無視中間的單位與低矮地形；不觸發藉機攻擊）"


def _shadowstep(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    if spec.landing == "behind":
        where = "瞬間出現在目標背後（背後被占住時改到最近的側面；先結算）"
    else:
        where = "瞬間出現在目標身旁自選的一格（先結算）"
    return where + "，不觸發藉機攻擊，落地後面向目標"


def _summon(
    lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec, stats: SummonStats | None = None
) -> str:
    """召喚的一句話（清單 1.1～1.7）：HP 用和引擎同一個算法；自帶能力、圖騰類的「不移動、不攻擊」
    與灌注都由範本與 ``summon_infusions`` 產生。``stats`` 是戰鬥中施放者的實際值（3-41c），省略時
    為 1 級基準值。"""
    try:
        summon = lib.ruleset.summon_def(spec.unit or "")
    except KeyError:
        return f"在目標空格召喚召喚物，持續 {spec.duration} 輪"
    template = summon.template
    hp = summon_card_hp(lib, summon, spec) if stats is None else stats.max_hp
    if not summon_acts(summon.template):
        text = (
            f"在目標空格立起{template.name_zh}（HP {hp}），持續 {spec.duration} 輪"
            "（緊接在你之後行動；不移動、不攻擊）"
        )
    else:
        text = (
            f"在目標空格召喚{template.name_zh}（HP {hp}），持續 {spec.duration} 輪"
            "（緊接在你之後行動，由 AI 控制）"
        )
    innate = summon_innate_lines(lib, summon)
    if innate:
        text += f"；自帶：{'；'.join(innate)}"
    extra = _summon_variant_text(lib, spec)
    if extra:
        text += f"；{extra}"
    return f"{text}；{infusion_hint(lib, acts=summon_acts(template))}"


def _summon_variant_text(lib: ContentLibrary, spec: EffectSpec) -> str:
    """召喚技能分歧進化（Phase 3-33f2）多出的內容：數量型、加深（HP 與小特性）、橋接。"""
    parts: list[str] = []
    if isinstance(spec.count, int) and spec.count > 1 and spec.power_permille is not None:
        parts.append(
            f"一次召喚 {spec.count} 隻，每隻只有 {spec.power_permille / 10:g}% 的 HP 與傷害"
        )
    if spec.max_hp_permille:
        parts.append(f"最大 HP +{spec.max_hp_permille / 10:g}%")
    trait = lib.ruleset.core.summon_traits.get(spec.trait or "")
    if trait is not None:
        parts.append(f"小特性「{trait.name_zh}」（{trait.description_zh}）")
    if spec.infusion is not None:
        name = next(
            (k.name_zh for k in lib.keywords.keywords if k.id == spec.infusion), spec.infusion
        )
        parts.append(f"固有第二個灌注「{name}」")
    return "、".join(parts)


def rule_change_text(library: ContentLibrary, rule_id: str) -> str:
    """規則改變（Phase 3D-6）的一句話，例如「規則改變「移山」：你可以推動……」。"""
    rules = library.ruleset
    try:
        rule = rules.rule_change_def(rule_id)
    except KeyError:
        return "規則改變"
    return f"規則改變「{rule.name_zh}」：{rule_change_sentence_for(rules, rule)}"


def rule_change_sentence_for(rules: Ruleset, rule: RuleChangeDef) -> str:
    """規則改變的規則句，名稱從規則包查（:func:`trpg.content.rule_changes.rule_change_sentence`）。"""

    def summon_name(unit: str) -> str:
        try:
            return rules.summon_def(unit).template.name_zh
        except KeyError:
            return "召喚物"

    return rule_change_sentence(
        rule, status_name=lambda sid: rules.status_def(sid).name_zh, summon_name=summon_name
    )


def _rule_change(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return rule_change_text(lib, spec.rule or "")


def activation_text(library: ContentLibrary, skill: SkillDef) -> str | None:
    """常駐類傳說的啟動方式（Phase 3D-6）；其他技能為 ``None``。"""
    if skill.activation is None:
        return None
    core = library.ruleset.core
    head = f"花 AP {core.legendary_activation_ap} ＋ 源力 {skill.cost.source} 啟動"
    if skill.activation == "battle":
        return f"整場：{head}，本場剩餘時間有效"
    return f"限時：{head}，持續 {core.legendary_timed_rounds} 輪"


def _branch_effect_text(lib: ContentLibrary, skill: SkillDef, sub: EffectSpec) -> str:
    """賭注分支或失手反噬的一個效果（Phase 3D-7a）：倍率、自傷與一般效果（含對象）。"""
    if sub.type == DAMAGE_MULTIPLIER:
        assert sub.damage_multiplier_permille is not None
        return f"本次傷害 ×{sub.damage_multiplier_permille / 1000:g}"
    if sub.type == SELF_DAMAGE_OF_HIT:
        assert sub.self_damage_permille_of_hit is not None
        return f"你受到本次傷害的 {sub.self_damage_permille_of_hit / 10:g}%（不致命）"
    return effect_summary(lib, skill, sub)


def branch_text(
    lib: ContentLibrary, skill: SkillDef, effects: tuple[EffectSpec, ...] | None
) -> str:
    """賭注一個分支的一句話；沒有效果為「沒有額外效果」。"""
    if not effects:
        return "沒有額外效果"
    return "、".join(_branch_effect_text(lib, skill, sub) for sub in effects)


def _gamble(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.chance_permille is not None
    win = f"{spec.chance_permille / 10:g}%：{branch_text(lib, skill, spec.win)}"
    lose = f"{(1000 - spec.chance_permille) / 10:g}%：{branch_text(lib, skill, spec.lose)}"
    return f"賭注（命中後擲 d1000）——{win}｜{lose}"


def miss_text(lib: ContentLibrary, skill: SkillDef) -> str | None:
    """失手反噬（``cost.on_miss``，Phase 3D-7a）的一句話；沒有為 ``None``。"""
    if not skill.cost.on_miss:
        return None
    parts: list[str] = []
    for sub in skill.cost.on_miss:
        if sub.type == "apply_status" and sub.status is not None:
            name = lib.ruleset.status_def(sub.status).name_zh
            turns = f" {sub.duration} 回合" if sub.duration else ""
            parts.append(f"你獲得「{name}」{turns}")
        else:
            parts.append(f"{_damage(lib, skill, sub)}（對自己，不致命）")
    return "失手（含自然 1）時：" + "、".join(parts)


def _charge_through(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    after = (
        f"擊倒（{contest_label(skill, lib)}對抗）" if spec.on_hit == "knock_prone" else "推到路徑旁"
    )
    return (
        f"沿直線衝向目標格：沿途每個敵人各擲命中，命中受 {spec.dice} 物理傷害並{after}"
        "（隊友讓路；不觸發藉機攻擊；目標格的敵人背後被擋住時另受一次撞擊）"
    )


def _swap(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    check = f"（{contest_label(skill, lib)}對抗）" if spec.affects == "enemies" else ""
    return "與目標交換位置" + check


def _teleport_target(lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    core = lib.ruleset.core
    lethal = core.teleport_enemy_resist_bonus + core.teleport_lethal_resist_bonus
    return (
        f"把一個單位傳送到落點（友方必定成功；敵方{contest_label(skill, lib)}對抗，目標抵抗 "
        f"+{core.teleport_enemy_resist_bonus}；落點是致命地形時抵抗 +{lethal}，Boss 免疫）"
    )


def _swap_any(lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    return f"讓射程內的兩個單位互換位置（含敵人時每個敵人各過{contest_label(skill, lib)}對抗）"


def status_duration_text(lib: ContentLibrary, status_id: str, duration: int | None) -> str:
    """施加狀態的持續時間（Phase 3-41a 清單 3.7）：效果有寫回合數就用它，否則用狀態的預設
    （``statuses.yaml`` 的 ``duration``／``expires``）。"""
    if duration:
        return f" {duration} 回合"
    status = lib.ruleset.status_def(status_id)
    if status.expires == "own_turn_start":
        return "（到帶有者的下回合開始）"
    if status.duration is not None:
        return f" {status.duration} 回合"
    return "（持續到取消）" if status.stance else "（直到被移除）"


def _apply_status(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.status is not None
    name = lib.ruleset.status_def(spec.status).name_zh
    return f"狀態「{name}」{status_duration_text(lib, spec.status, spec.duration)}"


def _shield(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    """護盾（清單 3.6）：吸收量與持續時間（``shielded`` 狀態的預設回合）。"""
    status = lib.ruleset.status_def(SHIELD_STATUS)
    amount = "" if spec.dice is None else f"{_dice(spec.dice)}＋"
    rounds = spec.duration or status.duration
    return (
        f"護盾（吸收量 {amount}{scaling_label(skill, lib)}加成，持續 {rounds} 回合；"
        "已有護盾時取較大值）"
    )


def _cleanse(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    """淨化（玩法決定 #60）：只移除減益（``polarity: debuff``）；增益與中性狀態保留。"""
    return "淨化：移除身上所有負面狀態（增益、姿態與其他中性狀態不受影響）"


def _create_surface(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.surface is not None
    turns = f" {spec.duration} 回合" if spec.duration else ""
    return f"生成「{lib.ruleset.surface_def(spec.surface).name_zh}」表面{turns}"


def _create_obstacle(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.object is not None
    turns = f"，{spec.duration} 回合後消失" if spec.duration else ""
    return f"生成「{lib.ruleset.object_def(spec.object).name_zh}」{turns}"


def _inscribe(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    rounds = spec.duration or lib.ruleset.core.rune_default_rounds
    rune = rune_name(spec.element, spec.tag, lib.ruleset.skill_tags.rune_names())
    return (
        f"在影響格刻下你專屬的「{rune}」，持續 {rounds} 輪"
        "（符文本身沒有效果，敵我都看得到；之後由你的技能讀取）"
    )


def _sacrifice_summon(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None and spec.radius is not None
    scope = "只有它所在的格子" if spec.radius == 0 else f"{spec.radius} 格內"
    if spec.element is not None:
        return (
            f"獻祭你的一個召喚物，在它的位置爆炸：{scope}的敵人自動命中，受到"
            f" {_dice(spec.dice)}＋{scaling_label(skill, lib)}加成的{spec.element.display_name}傷害"
        )
    return (
        f"獻祭你的一個召喚物，在它的位置化為治療：{scope}的友方回復"
        f" {_dice(spec.dice)}＋{scaling_label(skill, lib)}加成的 HP"
    )


def _detonate_runes(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None
    element = f"{spec.element.display_name}" if spec.element is not None else "符文元素的"
    if spec.scope == "target_cell":
        return (
            f"引爆被命中目標所在格上你自己的符文（只引爆那 1 格）：移除符文，並對站在上面的單位"
            f"自動命中，造成 {_dice(spec.dice)}＋{scaling_label(skill, lib)}加成的{element}傷害"
        )
    return (
        f"引爆影響範圍內你自己的符文：每格移除符文，並對站在上面的單位自動命中，造成"
        f" {_dice(spec.dice)}＋{scaling_label(skill, lib)}加成的{element}傷害"
    )


def _destroy_object(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "摧毀可破壞的物件"


def _overload_text(lib: ContentLibrary, stack: StackDef) -> str:
    """超載層數（Phase 3D-7b）的說明：每層加成與到門檻時的反噬。"""
    overload = stack.overload
    assert overload is not None
    backlash: list[str] = []
    for sub in overload.backlash:
        if sub.type == "damage":
            assert sub.dice is not None and sub.element is not None
            backlash.append(f"受到 {_dice(sub.dice)} {sub.element.display_name}傷害（不致命）")
        else:
            assert sub.status is not None
            backlash.append(f"獲得「{lib.ruleset.status_def(sub.status).name_zh}」")
    return (
        f"。超載：你帶{tag_text(lib, (overload.tag,))}標籤的技能每層傷害"
        f" +{overload.per_stack_damage_permille / 10:g}%；"
        f"累積到 {overload.threshold} 層時，你{'、'.join(backlash)}並清空層數"
    )


def _stack(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.stack is not None
    stack = lib.ruleset.stack_def(spec.stack)
    if spec.type == "add_stack":
        text = f"累積 {spec.amount or 1} 層「{stack.name_zh}」（上限 {stack.max}）"
        return text + (_overload_text(lib, stack) if stack.overload is not None else "")
    assert spec.per_stack_permille is not None
    need = f"（至少 {skill.cost.stacks} 層才能施放）" if skill.cost.stacks else ""
    return f"消耗全部「{stack.name_zh}」，每層使本技能傷害 +{spec.per_stack_permille / 10:g}%{need}"


def _consume_status(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.status is not None and spec.then
    name = lib.ruleset.status_def(spec.status).name_zh
    then = "、".join(_effect_core(lib, skill, sub) for sub in spec.then)
    text = f"消耗目標身上的「{name}」，然後{then}"
    if spec.scale == "remaining_rounds":
        text += "（骰數 × 剩餘回合）"
    elif spec.scale == "stacks":
        assert spec.stack is not None
        text += f"（骰數 × 同時消耗的「{lib.ruleset.stack_def(spec.stack).name_zh}」層數）"
    if spec.splash is not None:
        text += f"，並波及周圍 {spec.splash} 格內的敵人"
    return text + "；目標沒有該狀態則不生效"


_ZONE_WHEN = {
    "enter": "進入區域時",
    "turn_start": "在區域內開始回合時",
    "both": "進入區域或在區域內開始回合時",
}
_ZONE_WHO = {"enemies": "敵人", "allies": "友方", "all": "任何單位"}
_DIRECTION_WORD = "施放方向"


def _zone(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    """持續區域（Phase 3D-5）的一句話。"""
    assert spec.when is not None and spec.effects
    if spec.anchor == "caster":
        anchor = "跟著你移動"
    elif spec.anchor == "moving":
        anchor = f"每次環境回合向{_DIRECTION_WORD}前進 {spec.speed or 1} 格"
    else:
        anchor = "固定不動"
    who = _ZONE_WHO[spec.affects or "enemies"]
    then = "、".join(_effect_core(lib, skill, sub) for sub in spec.effects)
    text = f"建立持續 {spec.duration} 輪的區域（{anchor}）：{who}{_ZONE_WHEN[spec.when]}，{then}"
    if spec.surface is not None:
        text += f"；區域經過的格子留下「{lib.ruleset.surface_def(spec.surface).name_zh}」"
    return text


def _place_trap(lib: ContentLibrary, skill: SkillDef, _spec: EffectSpec) -> str:
    """放置陷阱（3-48h）：寫出「踩到時」實際會結算的效果，例如「放置陷阱：敵人踩到時，造成 …」。"""
    trap = skill.trap
    assert trap is not None
    shape = {"single": "該格", "cross": "十字範圍", "square3": "3×3 範圍"}[trap.shape]
    then = "、".join(effect_summary(lib, skill, e) for e in skill.effects if e.type != "place_trap")
    result = f"以{shape}為中心，{then}" if then else "（還沒有踩到後的效果）"
    if trap.trigger == "enter":
        return f"放置隱藏陷阱（{trap.rounds} 輪後消失）：敵人踩到時，{result}"
    return f"放置隱藏陷阱：{trap.rounds} 輪後引爆，{result}"


def _grant_ap(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return f"立刻獲得 {spec.amount or 1} AP（不超過本回合上限，每輪限一次）"


def _reset_cooldown(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    which = "全部技能" if spec.which == "all" else f"帶{tag_text(lib, (spec.tag or '',))}標籤的技能"
    return f"{which}的冷卻歸零（花源力的技能除外）"


def _cheat_death(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    status = lib.ruleset.status_def(CHEAT_DEATH_STATUS)
    turns = spec.duration or status.duration
    return f"狀態「{status.name_zh}」{turns} 回合：受到致命傷害時 HP 留在 1（墜落與致命地形除外）"


def _redirect_damage(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    status = lib.ruleset.status_def(REDIRECT_STATUS)
    turns = spec.duration or status.duration
    share = (spec.permille or 0) / 10
    return f"狀態「{status.name_zh}」{turns} 回合：目標受到的傷害有 {share:g}% 轉給施放者"


def _copy_skill(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return (
        "立即複製施放本輪最後施放的主動技能（自己選目標，不扣法力與 AP、不進冷卻；"
        "傳說與改寫規則型除外）"
    )


def _extra_reaction(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return f"本輪反應次數 +{spec.amount or 1}（到下一輪開始）"


def _restore_resource(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    amount = spec.amount or 1
    if spec.resource == "cooldown":
        return f"目標所有技能的冷卻 −{amount}（花源力的技能除外）"
    return f"回復 {amount} 點法力（不超過上限）"


def _steal_buff(_lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    return "奪取目標身上一個增益（剩餘回合最長者），以相同的剩餘回合施加到自己身上"


def _dispel(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    if spec.count == "all":
        return "驅散目標身上的全部增益"
    return "驅散目標身上一個增益（剩餘回合最長者）"


def _reveal(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return (
        f"揭露範圍內的敵人：移除隱蔽，{spec.duration} 回合內不能再隱蔽；範圍內的敵方陷阱對你的"
        "陣營顯示（不擲命中）"
    )


def _revive(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    return (
        f"讓射程內倒下的友方以 {(spec.hp_permille or 0) / 10:g}% 最大 HP 站起來"
        "（站回原位置，被占用時站到附近最近的空格；每個單位每場最多一次，召喚物不能被復活）"
    )


def _grant_skill(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.skill is not None
    granted = lib.ruleset.skill_def(spec.skill)
    return (
        f"讓目標暫時獲得技能「{granted.name_zh}」，持續 {spec.duration} 輪"
        "（在目標的回合結束時倒數；不佔技能欄位，重新施放只刷新輪數）"
    )


def _delayed_damage(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None and spec.element is not None
    where = "，只波及目標自己" if not spec.radius else f"，波及半徑 {spec.radius} 格內的所有單位"
    return (
        f"在目標身上綁定時炸彈（{lib.ruleset.status_def('time_bomb').name_zh}）：{spec.rounds} 次"
        f"環境回合後在目標當下的位置爆炸{where}（敵我不分），{_dice(spec.dice)}＋"
        f"{scaling_label(skill, lib)}加成的{spec.element.display_name}傷害；目標倒下時立即爆炸；"
        "可被淨化移除"
    )


def _hurl_object(lib: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    assert spec.dice is not None
    text = f"把 {spec.range} 格內的可推動物件丟到落點，落點單位受 {_dice(spec.dice)} 物理傷害"
    if spec.knock_prone:
        text += f"並擊倒（{contest_label(skill, lib)}對抗）"
    return text + "；油桶落地爆炸、可破壞的物件碎掉"


def _topple(lib: ContentLibrary, _skill: SkillDef, _spec: EffectSpec) -> str:
    core = lib.ruleset.core
    return (
        f"推倒石柱或枯樹，往遠離自己的方向壓住 {core.topple_length} 格"
        f"（{_dice(core.topple_damage_dice)} 物理傷害並倒地）"
    )


def _terrain(_lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    verb = "抬高" if spec.type == "raise_terrain" else "降低"
    return f"{verb}地形 {spec.amount or 1} 層"


def _name_only(lib: ContentLibrary, _skill: SkillDef, spec: EffectSpec) -> str:
    """只寫原語的中文名（``skill_primitives.yaml`` 的 ``name_zh``）。"""
    return lib.ruleset.primitive_def(spec.type).name_zh


_EFFECT_TEXT: dict[str, _EffectText] = {
    "damage": _damage,
    "heal": _heal,
    "shield": _shield,
    "cleanse": _cleanse,
    "intercept": _name_only,
    "push": _push_pull,
    "pull": _push_pull,
    "knock_prone": _knock_prone,
    "teleport": _teleport,
    "dash": _dash,
    "leap": _leap,
    "shadowstep": _shadowstep,
    "charge_through": _charge_through,
    "summon": _summon,
    "swap": _swap,
    "teleport_target": _teleport_target,
    "swap_any": _swap_any,
    "apply_status": _apply_status,
    "create_surface": _create_surface,
    "create_obstacle": _create_obstacle,
    "destroy_object": _destroy_object,
    "inscribe": _inscribe,
    "detonate_runes": _detonate_runes,
    "sacrifice_summon": _sacrifice_summon,
    "add_stack": _stack,
    "consume_stack": _stack,
    "consume_status": _consume_status,
    "place_trap": _place_trap,
    "raise_terrain": _terrain,
    "lower_terrain": _terrain,
    "grant_ap": _grant_ap,
    "reset_cooldown": _reset_cooldown,
    "cheat_death": _cheat_death,
    "redirect_damage": _redirect_damage,
    "copy_skill": _copy_skill,
    "extra_reaction": _extra_reaction,
    "restore_resource": _restore_resource,
    "steal_buff": _steal_buff,
    "dispel": _dispel,
    "reveal": _reveal,
    "revive": _revive,
    "delayed_damage": _delayed_damage,
    "grant_skill": _grant_skill,
    "hurl_object": _hurl_object,
    "topple": _topple,
    "zone": _zone,
    "rule_change": _rule_change,
    "gamble": _gamble,
}
"""原語 → 效果敘述（Phase 3E-2b：載入內容時檢查 ``skill_primitives.yaml`` 的每個原語都在這裡，
見 :mod:`trpg.primitive_coverage`）。"""

DESCRIBED_PRIMITIVES: frozenset[str] = frozenset(_EFFECT_TEXT)
"""有效果敘述的原語 ID。"""


def _effect_core(library: ContentLibrary, skill: SkillDef, spec: EffectSpec) -> str:
    describe = _EFFECT_TEXT.get(spec.type)
    if describe is None:
        return library.ruleset.primitive_def(spec.type).name_zh
    return describe(library, skill, spec)


def _surface_names(library: ContentLibrary, ids: tuple[str, ...]) -> str:
    return "／".join(f"「{library.ruleset.surface_def(Surface(i)).name_zh}」" for i in ids)


def variant_condition_text(library: ContentLibrary, when: VariantWhen) -> str:
    """戰場變奏（Phase 3-25a）的條件，例如「施放者站在「水」上」。"""
    if when.caster_surface is not None:
        return f"施放者站在{_surface_names(library, when.caster_surface)}上"
    if when.target_surface is not None:
        return f"目標點在{_surface_names(library, when.target_surface)}上"
    if when.caster_high_ground is not None:
        return "施放者比目標點高至少 1 層"
    return "施放者身旁（八方向）有牆壁或擋路物件"


def variant_change_text(library: ContentLibrary, skill: SkillDef, variant: VariantSpec) -> str:
    """戰場變奏（Phase 3-25a）的替換內容，例如「形狀改為直線（3 格）；傷害改為雷電」。"""
    form = skill.variant_form(variant.id)
    parts: list[str] = []
    if variant.shape is not None or variant.range_delta is not None:
        delta = "" if variant.range_delta is None else f"射程 {variant.range_delta:+d}，"
        parts.append(f"{delta}形狀為{skill_shape_text(library, form)}")
    if variant.replace_effect is not None:
        swap = variant.replace_effect
        text = effect_summary(library, form, form.effects[swap.index])
        parts.append(f"第 {swap.index + 1} 個效果改為{text}")
    if variant.add_effect is not None:
        parts.append(f"加上{effect_summary(library, form, form.effects[-1])}")
    if variant.element is not None:
        parts.append(f"傷害改為{variant.element.display_name}")
    return "；".join(parts)


_OWN_TARGET_TEXT: frozenset[str] = frozenset(
    {
        "summon",
        "zone",
        "rule_change",
        "gamble",
        "sacrifice_summon",
        "place_trap",
        "teleport_target",
        "swap_any",
        "revive",
        "topple",
        "teleport",
        "dash",
        "leap",
        "shadowstep",
        "charge_through",
        "copy_skill",
    }
)
"""句子本身已寫明對象（或對象就是施放者自己的位移）的原語：不再加「（敵方）」等後綴（清單 3.5）。"""


def effect_summary(
    library: ContentLibrary,
    skill: SkillDef,
    spec: EffectSpec,
    *,
    summon_stats: SummonStats | None = None,
) -> str:
    """一個效果的一句話，含對象，例如「2d6＋智力加成的火焰傷害（敵方）」。``summon_stats``：戰鬥中
    召喚效果用施放者的實際值（3-41c）。"""
    primitive = library.ruleset.primitive_def(spec.type)
    affects = spec.affects or default_affects(primitive)
    suffix = "" if spec.type in _OWN_TARGET_TEXT else f"（{_AFFECTS[affects]}）"
    if spec.type == "damage":  # 對象接在傷害句後面，擊殺時等附加句放在對象之後（清單 3.5）
        head, extras = _damage_parts(library, skill, spec)
        text = head + suffix + "".join(f"，{e}" for e in extras)
    elif spec.type == "summon" and summon_stats is not None:
        text = _summon(library, skill, spec, summon_stats) + suffix
    else:
        text = _effect_core(library, skill, spec) + suffix
    if spec.condition is not None:
        text += f"，若{condition_summary(library, spec.condition)}"
    return text


def condition_summary(library: ContentLibrary, condition: ConditionSpec) -> str:
    """條件的一句話（不含「若」或「使用條件」前綴）。"""
    rules = library.ruleset
    return condition_text(
        condition,
        status_name=lambda sid: rules.status_def(sid).name_zh,
        surface_name=lambda surface: rules.surface_def(surface).name_zh,
        tag_name=rules.skill_tags.name,
        tag_runes=rules.skill_tags.rune_names(),
    )


# ---------------------------------------------------------------------------
# 修正規則（Phase 3C-2）
# ---------------------------------------------------------------------------


def tag_text(library: ContentLibrary, tags: Iterable[str]) -> str:
    """技能標籤的中文名（``content/skill_tags.yaml``），例如「「推擊」／「控制」」；查不到的標籤
    顯示「特定」，不顯示英文代號（Phase 3-41a）。"""
    names = library.ruleset.skill_tags
    return "／".join(f"「{names.name(t)}」" for t in tags)


def _targets_text(library: ContentLibrary, target: ModifierTarget) -> str:
    """套用對象，例如「你的所有攻擊」「推擊、帶「推擊」標籤的技能」。"""
    parts: list[str] = []
    if target.all_attacks:
        parts.append("你的所有攻擊（普攻與攻擊技能）")
    if target.all_skills:
        parts.append("你施放的所有技能")
    parts += [_ACTION_TEXT[a] for a in target.actions if not (a == "attack" and target.all_attacks)]
    if target.skill_tags and not target.all_skills:
        parts.append(f"帶{tag_text(library, target.skill_tags)}標籤的技能")
    return "、".join(parts)


_SIMPLE_CHANGE_TEXT = {
    "hit_bonus": "命中 {value:+d}",
    "cooldown_delta": "命中後該技能的冷卻 {value:+d} 回合（最少 0）",
    "ap_delta": "AP {value:+d}（最少 1）",
    "range_delta": "射程 {value:+d}",
    "grant_pierce": "遠程單體與直線技能獲得穿透（無視半掩護，穿過木製物件）",
    "area_delta": "範圍型形狀的大小 +{value}（直線與錐形的長度、環形與光環的半徑，有上限）",
    "allow_self_target": "治療、護盾、增益類技能的影響範圍也包含自己",
    "summon_attack_dice": "召喚物的攻擊傷害骰 +{value} 顆",
    "summon_limit_delta": "你同時存在的召喚物上限 {value:+d} 隻（最少 1 隻、最多 3 隻）",
    "summon_duration_delta": "你召喚的召喚物持續 +{value} 輪",
}
"""只有一個整數的改變：格式字串（``value`` 為改變的數值）。"""


def _shape_to_text(library: ContentLibrary, target: str) -> str:
    """``shape_to`` 的說明：列出 ``skill_shapes.yaml`` 的轉換表中轉成 ``target`` 的原形狀。"""
    shapes = library.ruleset.shapes.by_id()
    sources = [c for c in library.ruleset.shapes.conversions if c.to == target]
    names = "、".join(shapes[c.from_shape].name_zh for c in sources)
    return f"{names}形狀的技能轉為{shapes[target].name_zh}（效果原語不支援新形狀的技能不轉）"


def _damage_text(rule: ModifierSpec) -> str:
    amount = rule.change.damage_permille
    assert amount is not None
    if rule.empty_slots_cap is None:
        return f"傷害 {amount / 10:+g}%"
    return f"主動技能欄每空 1 格，傷害 {amount / 10:+g}%（最多 {rule.empty_slots_cap} 格）"


def _change_text(library: ContentLibrary, skill: SkillDef, rule: ModifierSpec) -> str:
    change = rule.change
    kind = change.kind
    simple = _SIMPLE_CHANGE_TEXT.get(kind)
    if simple is not None:
        return simple.format(value=getattr(change, kind))
    if change.damage_permille is not None:
        return _damage_text(rule)
    if change.heal_permille is not None:
        return f"你的治療量 {change.heal_permille / 10:+g}%"
    if change.summon_hp_permille is not None or change.summon_damage_permille is not None:
        what, value = (
            ("最大 HP", change.summon_hp_permille)
            if change.summon_hp_permille is not None
            else ("傷害", change.summon_damage_permille)
        )
        return f"你召喚的召喚物{what} +{(value or 0) / 10:g}%"
    if change.push_distance_delta is not None:
        cap = library.ruleset.core.max_displace_distance
        return (
            f"推擊與拉扯距離 +{change.push_distance_delta} 格"
            f"（最多 {cap} 格，超過的每格改為一次撞擊傷害）"
        )
    return _other_change_text(library, skill, rule)


def _other_change_text(library: ContentLibrary, skill: SkillDef, rule: ModifierSpec) -> str:
    change = rule.change
    if change.add_element is not None:
        return f"物理傷害改為{change.add_element.display_name}（已有元素的不變）"
    if change.add_tags is not None:
        return f"獲得{tag_text(library, change.add_tags)}標籤"
    if change.shape_to is not None:
        return _shape_to_text(library, change.shape_to)
    assert change.on_hit_effects is not None
    carrier = on_hit_carrier(skill, change.on_hit_effects)
    effects = "；".join(effect_summary(library, carrier, e) for e in carrier.effects)
    return f"命中後：{effects}"


def modifier_summary(library: ContentLibrary, skill: SkillDef, rule: ModifierSpec) -> str:
    """一條修正規則的一句話，例如「你的所有攻擊（普攻與攻擊技能）：傷害 +10%，若目標帶有狀態
    「燃燒」」。"""
    text = f"{_targets_text(library, rule.applies_to)}：{_change_text(library, skill, rule)}"
    if rule.condition is not None:
        text += f"，若{condition_summary(library, rule.condition)}"
    if rule.per_turn_limit is not None:
        text += f"（每回合最多 {rule.per_turn_limit} 次）"
    return text


def self_status_until(duration: int) -> str:
    """自身狀態的持續說法（3-50b）：狀態在施放當回合結束就 −1，所以 ``duration`` 2 ＝「到你下個回合
    結束」、3 ＝「到你下 2 個回合結束」（從下個回合起算）。"""
    nth = duration - 1
    return "到你下個回合結束" if nth <= 1 else f"到你下 {nth} 個回合結束"


def cost_parts(library: ContentLibrary, skill: SkillDef, *, with_ap: bool = True) -> list[str]:
    """代價的各段文字（AP、法力、耐力、HP、施放後狀態、冷卻、每場次數）。"""
    cost = skill.cost
    ap = skill_ap(library, skill)
    parts = [f"AP {ap}"] if with_ap and ap is not None else []
    if cost.mana:
        parts.append(f"法力 {cost.mana}")
    if cost.stamina:
        parts.append(f"耐力 {cost.stamina}")
    if cost.hp_percent:
        parts.append(f"HP {cost.hp_percent / 10:g}%")
    if cost.self_status:
        name = library.ruleset.status_def(cost.self_status.status).name_zh
        percent = self_status_allowance_permille(cost.self_status, library) / 10
        # 3-50b：持續寫成「到你下個回合結束」（有效回合 ＝ duration − 1）
        parts.append(
            f"代價：施放後自己{name}，{self_status_until(cost.self_status.duration)}"
            f"（換 {percent:g}% 預算）"
        )
    if cost.overdraft:
        percent = library.budget.allowance.overdraft_permille / 10
        parts.append(f"代價：施放後自己下一個回合少 {cost.overdraft} AP（換 {percent:g}% 預算）")
    if cost.cooldown:
        parts.append(f"冷卻 {cost.cooldown} 回合")
    if cost.uses_per_battle:
        parts.append(f"每場 {cost.uses_per_battle} 次")
    if cost.source:
        parts.append(f"源力 {cost.source}")
    miss = miss_text(library, skill)
    if miss is not None:
        parts.append(miss)
    return parts


def skill_ap(library: ContentLibrary, skill: SkillDef) -> int | None:
    """技能列顯示的 AP：主動技能的 ``ap_cost``、修正型傳說的啟動 AP（Phase 3D-6）；被動等為
    ``None``。"""
    if skill.ap_cost is not None:
        return skill.ap_cost
    if skill.is_activatable:
        return library.ruleset.core.legendary_activation_ap
    return None


def cost_summary(library: ContentLibrary, skill: SkillDef, *, with_ap: bool = True) -> str:
    """代價的一句話，例如「AP 2，法力 3，冷卻 2 回合」。"""
    return "，".join(cost_parts(library, skill, with_ap=with_ap))


# ---------------------------------------------------------------------------
# 技能卡片
# ---------------------------------------------------------------------------


REACTION_TIMING_TEXT: dict[str, str] = {
    "hit_by_melee": "被近戰攻擊命中時",
    "hit_by_attack": "被攻擊命中時",
    "ally_hit_adjacent": "相鄰的友方被攻擊命中時",
    "enemy_leaves_adjacent": "相鄰的敵人離開時",
    "hit_by_spell": "被法術命中時（傷害結算之前）",
    "ally_downed": "友方倒下時",
    "enemy_enters_adjacent": "敵人走進相鄰格時",
    "ally_targeted": "相鄰的友方被敵人瞄準時（命中判定之前）",
}
"""反應技觸發事件的中文說明（Phase 3C-6a：技能卡片的「反應時機」一行）。"""


def timing_text(library: ContentLibrary, skill: SkillDef) -> str | None:
    """技能卡片的時機一行：反應技為「反應時機：…」、被動為「觸發時機：…」；其他技能為 ``None``。"""
    if skill.reaction is not None:
        event = skill.reaction.event
        return f"反應時機：{REACTION_TIMING_TEXT.get(event, event)}"
    if skill.trigger is not None:
        return f"觸發時機：{trigger_timing_text(library, skill.trigger)}"
    return None


def trigger_timing_text(library: ContentLibrary, trigger: TriggerSpec) -> str:
    """被動觸發時機的一句話，帶參數的時機寫出參數（Phase 3-41a），例如「每命中 2 次」
    「施放帶「火焰」標籤的技能後」「敵人進入你的「水」表面時」。"""
    rules = library.ruleset
    name = rules.trigger_def(trigger.event).name_zh
    if trigger.n is not None:
        return name.replace(" n ", f" {trigger.n} ")
    if trigger.tag is not None:
        return f"施放帶{tag_text(library, (trigger.tag,))}標籤的技能後"
    if trigger.surface is not None:
        return f"敵人進入你的「{rules.surface_def(trigger.surface).name_zh}」表面時"
    if trigger.status is not None:
        return f"施加「{rules.status_def(trigger.status).name_zh}」後"
    return name


class KeywordRef(BaseModel):
    """技能卡上的一個關鍵字（Phase 3-24b1）：代碼、顯示名稱與一句話說明（給部件說明框）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    description_zh: str
    variant: bool = False
    """只有特定地形的戰場變奏型態才有這個關鍵字（Phase 3-25b；技能卡標「（特定地形）」）。"""
    general: bool = False
    """只由通用規則推導（Phase 3-41a，清單 2.1）：技能卡標灰並附上 ``reason_zh``。"""
    reason_zh: str | None = None
    """通用歸類的一句理由（``skill_keywords.yaml`` 的 ``reason_zh``）；專屬的為 ``None``。"""


class SkillCardKeywords(BaseModel):
    """技能製造與利用的關鍵字（Phase 3-24b1，``docs/design/06-技能.md`` 6.27.1；由原語、條件、觸發
    自動推導）。技能卡顯示「製造：點燃｜利用：倒地」。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    makes: tuple[KeywordRef, ...] = ()
    uses: tuple[KeywordRef, ...] = ()
    basic: bool = False
    """沒有任何關鍵字（含通用歸類）＝基礎技能（Phase 3-51，玩法決定 #55）：技能卡標「基礎技能：不和
    其他技能協同」。工坊草稿還沒完成時也是 ``True``，由介面決定要不要顯示。"""


BASIC_SKILL_NOTE_ZH = "基礎技能：不和其他技能協同"
"""基礎技能的卡片標示（玩法決定 #55）。"""


def keywords_card(
    library: ContentLibrary,
    found: SkillKeywords,
    grades: Mapping[tuple[str, str], KeywordGrade] | None = None,
) -> SkillCardKeywords:
    """推導結果（關鍵字 ID）附上顯示名稱。``grades``（:func:`keyword_grades`）：技能有專屬關鍵字時
    不顯示通用歸類（玩法決定 #54）；只有通用規則時標 ``general`` 並附理由；省略時全部照專屬顯示。
    沒有任何關鍵字的技能 ``basic`` 為真（玩法決定 #55）。"""
    defs = library.keywords.by_id()
    grades = grades or {}
    has_exclusive = any(g.grade == "exclusive" for g in grades.values())

    def ref(side: str, keyword_id: str) -> KeywordRef | None:
        d = defs[keyword_id]
        grade = grades.get((side, keyword_id))
        general = grade is not None and grade.grade == "general"
        if general and has_exclusive:
            return None
        return KeywordRef(
            id=d.id,
            name_zh=d.name_zh,
            description_zh=d.description_zh,
            variant=keyword_id in found.variant,
            general=general,
            reason_zh=grade.reason_zh if general and grade is not None else None,
        )

    def side_refs(side: str, ids: tuple[str, ...]) -> tuple[KeywordRef, ...]:
        return tuple(r for k in ids if (r := ref(side, k)) is not None)

    return SkillCardKeywords(
        makes=side_refs("makes", found.makes),
        uses=side_refs("uses", found.uses),
        basic=not found,
    )


def skill_card_keywords(library: ContentLibrary, skill: SkillDef) -> SkillCardKeywords:
    """``skill`` 的製造與利用關鍵字（附顯示名稱與分級）。"""
    table = library.keywords
    grades = keyword_grades(skill_facts(skill), table)
    return keywords_card(library, derive_keywords(skill, table), grades)


def draft_card_keywords(library: ContentLibrary, draft: Mapping[str, Any]) -> SkillCardKeywords:
    """組到一半的技能草稿（技能工坊）目前製造與利用的關鍵字（附分級）。"""
    table = library.keywords
    grades = keyword_grades((draft_facts(draft),), table)
    return keywords_card(library, derive_draft_keywords(draft, table), grades)


class SkillVariantCard(BaseModel):
    """技能卡上的一個戰場變奏型態（Phase 3-25b，6.24）：型態名、條件與替換內容的中文說明、
    型態自己的圖示（技能列在這個型態生效時換成它）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    condition: str
    """條件的一句話，例如「施放者站在「水」上」。"""
    condition_kind: str
    """``caster_surface``、``caster_high_ground``、``caster_adjacent_blocker``、``target_surface``。"""
    target_dependent: bool
    """條件看目標點（居高、目標點表面）：施放前要看預覽才知道生效哪個型態。"""
    change: str
    """替換內容的一句話，例如「形狀為直線（大小 3）；傷害改為雷電」。"""
    icon: SkillIcon


class SkillStackRef(BaseModel):
    """技能卡上的一個層數（3-41c）：製造（``add_stack``）或消耗（``consume_stack``、``scale:
    stacks``）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    role: Literal["makes", "uses"]


def skill_stacks(library: ContentLibrary, skill: SkillDef) -> tuple[SkillStackRef, ...]:
    """``skill`` 製造與消耗的層數（依效果順序、同一層數同一種用途只列一次）。"""
    found: dict[tuple[str, str], SkillStackRef] = {}
    for spec in skill.effects:
        if spec.stack is None:
            continue
        role: Literal["makes", "uses"] = "makes" if spec.type == "add_stack" else "uses"
        try:
            name = library.ruleset.stack_def(spec.stack).name_zh
        except KeyError:
            continue
        found.setdefault((spec.stack, role), SkillStackRef(id=spec.stack, name_zh=name, role=role))
    return tuple(found.values())


class SkillCard(BaseModel):
    """一張技能卡片的顯示內容（繁體中文文字，給網頁技能卡片用）。

    ``*_id`` 與 ``scaling_attrs`` 是對應的英文代碼（Phase 3-2；給前端上色、排序與篩選用）。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name_zh: str
    skeleton: str
    tier: int
    rank: int
    rarity: str
    kind: str
    category: str
    weapon_req: str
    scaling: str
    ap_cost: int | None
    cost: tuple[str, ...]
    """代價各段文字（含 AP）。"""
    source_cost: int | None
    """花費的源力（``cost.source``，傳說技能，Phase 3C-4a）；沒有為 ``None``。"""
    shape: str
    condition: str | None
    effects: tuple[str, ...]
    modifiers: tuple[str, ...]
    """修正規則的中文描述（Phase 3C-2；只有修正技能有）。"""
    activation: str | None = None
    """常駐類傳說的啟動方式（Phase 3D-6），例如「限時：花 AP 1 ＋ 源力 1 啟動，持續 3 輪」。"""
    activation_id: str | None = None
    """``timed``／``battle``（Phase 3D-6）；其他技能為 ``None``。"""
    mastery: str | None
    tags: tuple[str, ...]
    concept: str
    cast_flavor: str
    rarity_id: str
    kind_id: str
    category_id: str
    weapon_req_id: str
    scaling_attrs: tuple[str, ...]
    """縮放屬性的代碼（主屬性在前；雙屬性縮放時兩個）。"""
    mastery_id: str | None
    timing: str | None = None
    """反應技的反應時機、被動的觸發時機一行（Phase 3C-6a）；其他技能為 ``None``。"""
    effect_ids: tuple[str, ...] = ()
    """效果原語的代碼，依技能內的順序（Phase 3D-8d：網頁用來分辨兩段選取的種類，例如一般瞬步
    ``shadowstep`` 與傳送他人 ``teleport_target`` 都是「單位 → 落點」）。"""
    followup: str | None = None
    """複合技能（Phase 3F-3a）第二段的一句話（:func:`followup_text`）；其他技能為 ``None``。"""
    followup_when: str | None = None
    """複合技能第二段的種類（``followup.when``，Phase 3F-4b；網頁只有「位移 → 動作」用兩段選取，
    其他種類照第一段選取）；其他技能為 ``None``。"""
    icon: SkillIcon
    """組裝式技能圖示的資料（Phase 3-17，:func:`trpg.narrative.skill_icon.skill_icon`）。"""
    keywords: SkillCardKeywords = SkillCardKeywords()
    """製造與利用的關鍵字（Phase 3-24b1，:func:`skill_card_keywords`）。"""
    variants: tuple[SkillVariantCard, ...] = ()
    """戰場變奏的所有型態（Phase 3-25b；資料順序，多個成立時取前面的）；沒有變奏為空。"""
    summons: tuple[SummonInfoCard, ...] = ()
    """召喚技能可展開的「召喚物資訊」（Phase 3-41a，清單 1.8；每個召喚效果一張）；其他技能為空。"""
    skeleton_zh: str = ""
    """骨架的中文名（Phase 3-41a：技能卡標題列不顯示骨架 ID）。"""
    formula_lines: tuple[str, ...] = ()
    """傷害、治療、護盾的算法（3-41c，:meth:`SkillDef.formula_lines_zh`）：「傷害算法：骰值＋智力 ×
    0.5（目前 +6.5）」。有持有者（一輪主角、戰鬥中）時附「目前」加成與武器骰；其他卡片只有算式。"""
    stacks: tuple[SkillStackRef, ...] = ()
    """這張卡製造或消耗的層數（3-41c）：前端用它在卡片上提供層數說明框。"""
    growth: SkillLevelInfo | None = None
    """技能等級的顯示資料（Phase 3-26a）：只有一輪中主角持有（裝備或備用）的主動技能卡片帶它，
    由 ``trpg.api.run_presenter`` 帶入實際等級；候選、技能庫與工坊的卡片為 ``None``。"""


def _variant_card(
    library: ContentLibrary, skill: SkillDef, variant: VariantSpec
) -> SkillVariantCard:
    return SkillVariantCard(
        id=variant.id,
        name_zh=variant.name_zh,
        condition=variant_condition_text(library, variant.when),
        condition_kind=variant.when.kind,
        target_dependent=variant.when.target_dependent,
        change=variant_change_text(library, skill, variant),
        icon=skill_icon(skill.variant_form(variant.id)),
    )


@dataclass(frozen=True)
class CardOwner:
    """技能卡的持有者（3-41c）：一輪主角或戰鬥中的單位。有它時卡片附「目前」加成與實際值。"""

    weapon: WeaponDef | None = None
    attr_get: Callable[[Attribute], int] | None = None
    """讀持有者目前的屬性值（一輪為基礎＋裝備，戰鬥中為有效屬性）。"""
    summon_stats: Callable[[EffectSpec], SummonStats | None] | None = None
    """召喚效果 → 施放者當下的召喚物實際值（:func:`trpg.engine.summons.summon_stats`）。"""


def _scaling_attr_ids(skill: SkillDef, weapon: WeaponDef | None) -> tuple[str, ...]:
    """卡片 ``scaling_attrs``（給前端上色與篩選）：武器技有持有者武器時是武器的屬性（3H-6），
    其他是技能自己的縮放屬性（武器技沒有武器時是顯示提示）。"""
    attrs: tuple[Attribute | None, ...]
    if skill.category == "weapon" and weapon is not None:
        attrs = (weapon.scaling_attr, weapon.secondary_scaling_attr, skill.secondary_scaling_attr)
    else:
        attrs = (skill.scaling_attr, skill.secondary_scaling_attr)
    return tuple(dict.fromkeys(a.value for a in attrs if a is not None))


def _summon_stats(owner: CardOwner | None, spec: EffectSpec) -> SummonStats | None:
    if owner is None or owner.summon_stats is None or spec.type != "summon":
        return None
    return owner.summon_stats(spec)


def _summon_cards(
    library: ContentLibrary, skill: SkillDef, owner: CardOwner | None
) -> tuple[SummonInfoCard, ...]:
    return tuple(
        info
        for e in skill.effects
        if e.type == "summon"
        and (info := summon_info(library, skill, e, stats=_summon_stats(owner, e))) is not None
    )


def skill_card(
    library: ContentLibrary,
    skill: SkillDef,
    *,
    mastery_active: bool | None = None,
    owner: CardOwner | None = None,
) -> SkillCard:
    """``skill`` 的卡片內容；``mastery_active`` 見 :func:`mastery_text`；``owner`` 見
    :class:`CardOwner`（召喚物資訊與傷害算法的「目前」值；省略時為 1 級基準值與純算式）。"""
    return SkillCard(
        id=skill.id,
        name_zh=skill.name_zh,
        skeleton=skill.skeleton,
        tier=skill.tier,
        rank=skill.rank,
        rarity=RARITY_TEXT[skill.rarity],
        kind=KIND_TEXT[skill.kind],
        category=CATEGORY_TEXT[skill.category],
        weapon_req=WEAPON_REQ_TEXT[skill.weapon_req],
        scaling=scaling_detail(skill, None if owner is None else owner.weapon),
        ap_cost=skill_ap(library, skill),
        cost=tuple(cost_parts(library, skill, with_ap=skill_ap(library, skill) is not None)),
        source_cost=skill.cost.source,
        shape=skill_shape_text(library, skill),
        condition=(
            None if skill.condition is None else condition_summary(library, skill.condition)
        ),
        effects=tuple(
            effect_summary(library, skill, e, summon_stats=_summon_stats(owner, e))
            for e in skill.effects
        ),
        modifiers=tuple(modifier_summary(library, skill, r) for r in skill.modifiers),
        activation=activation_text(library, skill),
        activation_id=skill.activation,
        mastery=(
            None
            if skill.mastery is None
            else mastery_text(
                skill, active=mastery_active, weapon=None if owner is None else owner.weapon
            )
        ),
        tags=tuple(skill.tags),
        concept=skill.narrative.concept,
        cast_flavor=skill.narrative.cast_flavor,
        rarity_id=skill.rarity,
        kind_id=skill.kind,
        category_id=skill.category,
        weapon_req_id=skill.weapon_req,
        scaling_attrs=_scaling_attr_ids(skill, None if owner is None else owner.weapon),
        mastery_id=skill.mastery,
        timing=timing_text(library, skill),
        effect_ids=tuple(e.type for e in skill.effects),
        followup=followup_text(library, skill),
        followup_when=None if skill.followup is None else skill.followup.when,
        icon=skill_icon(skill),
        keywords=skill_card_keywords(library, skill),
        variants=tuple(_variant_card(library, skill, v) for v in skill.variants),
        summons=_summon_cards(library, skill, owner),
        skeleton_zh=skeleton_name(library, skill.skeleton),
        formula_lines=skill.formula_lines_zh(
            library.ruleset.core,
            None if owner is None else owner.weapon,
            None if owner is None else owner.attr_get,
        ),
        stacks=skill_stacks(library, skill),
    )


def skeleton_name(library: ContentLibrary, skeleton_id: str) -> str:
    """骨架的中文名（``content/skeletons/`` 的 ``name_zh``）；查不到時為空字串。"""
    found = library.skeletons.get(skeleton_id)
    return "" if found is None else found.name_zh
