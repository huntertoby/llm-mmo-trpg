"""詞條文字的欄位代入（Phase 3-41a，說明整修清單 5.1～5.3）。

``affixes.yaml`` 的 ``name_zh`` 是模板：數字與名稱不寫死，用 ``{欄位}`` 從詞條自己的資料（與它引用的
狀態、層數、技能、規則改變）代入；載入內容庫時（:func:`trpg.content.library.load_library`）一次換好，
之後所有地方（裝備介面、戰鬥中的單位資訊、事件）看到的都是代入後的文字。``{n}`` 是擲出的數值，
留到顯示時才換（:func:`trpg.content.equipment.affix_text`）。

可用的欄位：

- 詞條自己的欄位：``{max_stacks}``、``{cost_stacks}``、``{cost_ap}``、``{amount}``、``{delta}``、
  ``{range}``、``{status_duration}``、``{rune_rounds}`` 等整數；名稱以 ``_permille`` 結尾的顯示成
  百分比（``{strike_permille}`` → ``30%``）。
- ``{every}``：觸發的「每第 N 次」（``n``）；``{stack}``：層數名稱；``{status}``：詞條的狀態名稱；
  ``{gain}``：充能累積的時機（觸發時機的中文名）；``{rune}``：刻下的符文名稱。
- ``{effect.<欄位>}``：第一個效果的欄位（``dice``、``element``、``status``、``duration``、
  ``amount``、``radius``）。
- ``{up.<數值>}``／``{down.<數值>}``：代價型詞條好處／壞處的數值（絕對值，``_permille`` 的顯示成
  百分比）。
- ``{skill}``、``{skill_ap}``、``{skill_cooldown}``、``{skill_range}``、``{skill_effect.<欄位>}``：
  動作類詞條解鎖的技能。
- ``{rule}``：改變規則類詞條的規則（「規則改變「血痕」：你步行經過……」，和傳說技能卡同一句）。

模板裡有不認得的欄位時載入失敗（:class:`ValueError`）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING

from trpg.content.battle import Dice
from trpg.content.equipment import (
    ActionAffix,
    AffixDef,
    AttackAffix,
    ChargeAffix,
    CostAffix,
    RuleAffix,
    TriggerAffix,
)
from trpg.content.rule_changes import rule_change_sentence
from trpg.content.skills import EffectSpec
from trpg.shared.types import Element, rune_name

if TYPE_CHECKING:
    from trpg.content.library import Ruleset

__all__ = ["resolve_affix_name", "resolve_affix_names"]

_FIELD = re.compile(r"\{([a-z_]+)(?:\.([a-z_]+))?\}")


def _format(name: str, value: object, ruleset: Ruleset) -> str | None:
    text: str | None = None
    if isinstance(value, Dice):
        text = f"{value.count}d{value.sides}"
    elif isinstance(value, Element):
        text = value.display_name
    elif isinstance(value, int) and not isinstance(value, bool):
        text = f"{abs(value) / 10:g}%" if name.endswith("_permille") else str(abs(value))
    elif isinstance(value, str) and name.endswith("status"):
        text = ruleset.status_def(value).name_zh
    return text


def _effect_field(effect: EffectSpec | None, field: str, ruleset: Ruleset) -> str | None:
    if effect is None:
        return None
    return _format(field, getattr(effect, field, None), ruleset)


def _cost_field(affix: AffixDef, side: str, stat: str) -> str | None:
    if not isinstance(affix, CostAffix):
        return None
    parts = affix.upside if side == "up" else affix.downside
    part = next((p for p in parts if p.stat == stat), None)
    if part is None:
        return None
    if stat.endswith("_permille"):
        return f"{abs(part.amount) / 10:g}%"
    return str(abs(part.amount))


def _skill_field(affix: AffixDef, name: str, sub: str | None, ruleset: Ruleset) -> str | None:
    if not isinstance(affix, ActionAffix):
        return None
    skill = ruleset.skill_def(affix.skill)
    if name == "skill_effect":
        return None if sub is None else _effect_field(skill.effects[0], sub, ruleset)
    values: dict[str, object] = {
        "skill": skill.name_zh,
        "skill_ap": skill.ap_cost,
        "skill_cooldown": skill.cost.cooldown,
        "skill_range": skill.shape.param_values().get("range"),
    }
    value = values.get(name)
    return None if value is None or sub is not None else str(value)


def _named_field(affix: AffixDef, name: str, ruleset: Ruleset) -> str | None:
    """名稱類欄位：層數、觸發時機、符文、規則改變、每第 N 次。"""
    if name == "stack" and isinstance(affix, ChargeAffix):
        return ruleset.stack_def(affix.stack).name_zh
    if name == "gain" and isinstance(affix, ChargeAffix):
        return ruleset.trigger_def(affix.gain_trigger).name_zh
    if name == "every" and isinstance(affix, TriggerAffix) and affix.n is not None:
        return str(affix.n)
    if name == "rune" and isinstance(affix, AttackAffix):
        return rune_name(affix.rune_element, None)
    if name == "rule" and isinstance(affix, RuleAffix):
        rule = ruleset.rule_change_def(affix.rule)
        sentence = rule_change_sentence(
            rule,
            status_name=lambda sid: ruleset.status_def(sid).name_zh,
            summon_name=lambda uid: ruleset.summon_def(uid).template.name_zh,
        )
        return f"規則改變「{rule.name_zh}」：{sentence}"
    return None


def _field_text(affix: AffixDef, name: str, sub: str | None, ruleset: Ruleset) -> str | None:
    if name == "effect":
        effects = getattr(affix, "effects", ())
        return None if sub is None else _effect_field(effects[0] if effects else None, sub, ruleset)
    if name in ("up", "down"):
        return None if sub is None else _cost_field(affix, name, sub)
    if name.startswith("skill"):
        return _skill_field(affix, name, sub, ruleset)
    named = _named_field(affix, name, ruleset)
    if named is not None or sub is not None:
        return named
    return _format(name, getattr(affix, name, None), ruleset)


def resolve_affix_name(affix: AffixDef, ruleset: Ruleset) -> AffixDef:
    """``affix`` 的 ``name_zh`` 代入欄位後的新詞條（``{n}`` 保留）；有不認得的欄位時拋出
    :class:`ValueError`。"""

    def replace(match: re.Match[str]) -> str:
        name, sub = match.group(1), match.group(2)
        if name == "n" and sub is None:
            return match.group(0)
        text = _field_text(affix, name, sub, ruleset)
        if text is None:
            raise ValueError(f"詞條 {affix.id} 的 name_zh 有不認得的欄位：{match.group(0)}")
        return text

    name = _FIELD.sub(replace, affix.name_zh)
    return affix if name == affix.name_zh else affix.model_copy(update={"name_zh": name})


def resolve_affix_names(affixes: Mapping[str, AffixDef], ruleset: Ruleset) -> dict[str, AffixDef]:
    """全部詞條的 ``name_zh`` 代入欄位（:func:`resolve_affix_name`）。"""
    return {key: resolve_affix_name(affix, ruleset) for key, affix in affixes.items()}
