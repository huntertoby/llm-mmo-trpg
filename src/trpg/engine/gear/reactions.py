"""裝備的授予反應（第 10 類）詞條（Phase 3G-G3b，``docs/design/08-裝備.md`` 8.21.2.10、8.24）。

三種模式（:class:`~trpg.content.equipment.ReactionAffix`），只作用在持有者自己的反應：

- ``extend_trigger``：既有反應多一個觸發事件。開戰時（:func:`gear_reaction_rules`）替持有者加一條
  反應規則（例如 ``block`` 在 ``targeted_by_attack`` 時也觸發＝遠程攻擊也能格擋）；模式與「耐力
  太低不觸發」沿用持有者原本同一個反應的規則（沒有時為 ``auto``）。
- ``grant``：授予一個反應（``redirect_damage``：``range`` 格內的隊友被單體攻擊命中時，改由持有者
  承受）。規則同樣在開戰時加入；結算在 :func:`trpg.engine.reactions.try_intercept`。每輪次數用
  ``UnitState.gear_round_counts``（詞條 ID 為鍵，每輪開始清除）。
- ``extra_uses``：這個反應（限詞條指定的那一個，例如 ``overwatch_shot``）每輪可以多觸發 ``uses``
  次，不佔 ``reactions_per_round``（:func:`reaction_available`、:func:`spend_reaction`）。

反應規則仍然經過一般的反應暫停點（``auto``／``prompt``／``off``）；玩家用 ``set_reaction_mode``
切換。
"""

from __future__ import annotations

from trpg.content.battle import ReactionRule, ReactionWhen
from trpg.content.equipment import ReactionAffix
from trpg.content.library import Ruleset
from trpg.content.rules import CoreRules
from trpg.engine.gear.state import GearAffix, GearState
from trpg.engine.state import UnitState, reaction_limit

__all__ = [
    "REDIRECT",
    "extra_uses_left",
    "extra_uses_total",
    "gear_reaction_rules",
    "reaction_affixes",
    "reaction_available",
    "redirect_affix",
    "spend_reaction",
]

REDIRECT = "redirect_damage"
_EXTRA_PREFIX = "extra:"


def reaction_affixes(gear: GearState) -> tuple[tuple[GearAffix, ReactionAffix], ...]:
    """生效中的授予反應詞條（詞條 ID 排序）。"""
    return tuple(
        (g, g.affix) for g in gear.active_affixes("reaction") if isinstance(g.affix, ReactionAffix)
    )


def gear_reaction_rules(
    gear: GearState, rules: Ruleset, existing: tuple[ReactionRule, ...]
) -> tuple[ReactionRule, ...]:
    """裝備的 ``extend_trigger``／``grant`` 詞條要加進持有者的反應規則（已有同反應同事件的規則就
    不重複）；``existing`` 是持有者原本的規則。"""
    added: list[ReactionRule] = []
    for _, affix in reaction_affixes(gear):
        if affix.mode == "extra_uses":
            continue
        event = (
            affix.event if affix.event is not None else rules.reaction_def(affix.reaction).events[0]
        )
        pool = (*existing, *added)
        if any(r.reaction == affix.reaction and r.when.event == event for r in pool):
            continue
        base = next((r for r in pool if r.reaction == affix.reaction), None)
        added.append(
            ReactionRule(
                reaction=affix.reaction,
                when=ReactionWhen.model_validate({"event": event}),
                unless=None if base is None else base.unless,
                mode="auto" if base is None else base.mode,
            )
        )
    return tuple(added)


def redirect_affix(unit: UnitState) -> ReactionAffix | None:
    """持有者身上生效中的 ``redirect_damage`` 授予詞條；沒有時為 ``None``。"""
    return next(
        (a for _, a in reaction_affixes(unit.gear) if a.reaction == REDIRECT and a.mode == "grant"),
        None,
    )


def extra_uses_total(unit: UnitState, reaction: str) -> int:
    """裝備給 ``reaction`` 的額外觸發次數（每輪）。"""
    return sum(
        a.uses or 0
        for _, a in reaction_affixes(unit.gear)
        if a.mode == "extra_uses" and a.reaction == reaction
    )


def extra_uses_left(unit: UnitState, reaction: str) -> int:
    """本輪 ``reaction`` 還剩幾次裝備給的額外觸發。"""
    total = extra_uses_total(unit, reaction)
    if total == 0:
        return 0
    return max(total - unit.gear_round_counts.get(_EXTRA_PREFIX + reaction, 0), 0)


def reaction_available(core: CoreRules, unit: UnitState, reaction: str) -> bool:
    """本輪還能不能用 ``reaction``：一般反應次數沒用完，或裝備給了這個反應額外次數。"""
    return unit.reactions_used < reaction_limit(core, unit) or extra_uses_left(unit, reaction) > 0


def spend_reaction(core: CoreRules, unit: UnitState, reaction: str) -> None:
    """用掉一次 ``reaction``：先用一般反應次數，用完才用裝備給的額外次數。"""
    if unit.reactions_used < reaction_limit(core, unit):
        unit.reactions_used += 1
    else:
        key = _EXTRA_PREFIX + reaction
        unit.gear_round_counts[key] = unit.gear_round_counts.get(key, 0) + 1
