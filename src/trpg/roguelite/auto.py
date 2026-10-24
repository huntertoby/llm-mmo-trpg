"""AI 代打整輪（``trpg run auto``；測試與模擬用，Phase 3-5a）。

- 戰鬥：所有單位（含主角）由效用 AI 控制（:class:`~trpg.roguelite.battle.ActiveBattle`）。
- 配點：全部點在主角技能最常用的縮放屬性。
- 技能點：升級時全部花在主角裝備的第一個還沒滿級的主動技能（滿了換下一個）；分歧進化的門檻沒到的
  技能停在進化的前一級，經過進化時一律選第一支（加深，Phase 3-26b）。
- 戰後裝備三選一（Phase 3K-2）：挑預算分數比該部位目前裝備高最多的一件（空部位算 0 分），沒有比較
  高的就跳過（:func:`trpg.roguelite.gear.auto_gear_pick`）；營火不換裝。
- 升級與重骰：依序找第一個不用替換就裝得下的候選；都裝不下時，用第一個裝得下的候選換掉主角同一種
  欄位的最後一個技能；還是不行就跳過。營火一律重骰。

全部確定性：同一個 ``RunState`` 必得相同結果。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.battle import ActiveBattle
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.gear import auto_gear_pick
from trpg.roguelite.growth import crosses_evolution, evolution_choices, level_of, uses_of
from trpg.roguelite.offers import skill_defs, take_candidate
from trpg.roguelite.progress import apply_choice, finish_battle
from trpg.roguelite.start import primary_attribute
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    Choice,
    GearOfferNode,
    GearPickChoice,
    LeaveChoice,
    LevelUpChoice,
    LevelUpNode,
    PickChoice,
    RerollChoice,
    RunState,
    SkillOffer,
)

__all__ = ["AutoStop", "auto_choice", "auto_evolve", "auto_levels", "auto_play"]

type AutoStop = Callable[[RunState, ActiveBattle | None], bool]
"""停止條件：在每個節點與每個戰鬥步驟之前呼叫（``ActiveBattle`` 為進行中的戰鬥或 ``None``）。"""


def _slot(skill: SkillDef) -> str:
    return "passive" if skill.is_modifier else skill.kind


def _fits(
    library: ContentLibrary, run: RunState, offer: SkillOffer, pick: int, replace: str | None
) -> bool:
    try:
        take_candidate(library, run, offer, pick, replace)
    except ChoiceError:
        return False
    return True


def _auto_pick(
    library: ContentLibrary, run: RunState, offer: SkillOffer
) -> tuple[int | None, str | None]:
    picks = range(len(offer.candidates))
    for pick in picks:
        if _fits(library, run, offer, pick, None):
            return pick, None
    owned = skill_defs(library, run, run.hero.skills)
    for pick in picks:
        same = [s.id for s in owned if _slot(s) == _slot(offer.candidates[pick])]
        if same and _fits(library, run, offer, pick, same[-1]):
            return pick, same[-1]
    return None, None


def _reachable(library: ContentLibrary, run: RunState, skill_id: str, level: int) -> int:
    """``skill_id`` 最高能升到哪一級（不超過 ``level``）：分歧進化的門檻沒到時停在進化的前一級。"""
    growth = library.ruleset.skill_growth
    if crosses_evolution(library, run, skill_id, level) and uses_of(run, skill_id) < (
        growth.evolve_uses
    ):
        return min(level, growth.evolve_level - 1)
    return level


def auto_levels(library: ContentLibrary, run: RunState) -> dict[str, int]:
    """AI 代打花技能點（Phase 3-26a）：依裝備順序，把點數集中在第一個還沒滿級的主動技能；分歧進化的
    門檻（3-26b）沒到的技能停在進化的前一級，點數改給下一個。"""
    growth = library.ruleset.skill_growth
    points = run.skill_points
    levels: dict[str, int] = {}
    for skill in skill_defs(library, run, run.hero.skills):
        if skill.kind != "active":
            continue
        current = level_of(run, skill.id)
        affordable = min(growth.max_level - current, points // growth.upgrade_cost)
        target = _reachable(library, run, skill.id, current + affordable)
        if target > current:
            levels[skill.id] = target
            points -= (target - current) * growth.upgrade_cost
    return levels


def auto_evolve(library: ContentLibrary, run: RunState, levels: dict[str, int]) -> dict[str, int]:
    """AI 代打的分歧進化（Phase 3-26b）：經過進化而且有合格進化的技能一律選第一支（加深）。"""
    return {
        skill_id: 0
        for skill_id in sorted(levels)
        if crosses_evolution(library, run, skill_id, levels[skill_id])
        and evolution_choices(library, run, skill_id)
    }


def _battle_stop(stop: AutoStop, run: RunState) -> Callable[[ActiveBattle], bool]:
    return lambda battle: stop(run, battle)


def auto_choice(library: ContentLibrary, run: RunState) -> Choice:
    """升級或營火節點的自動選擇。"""
    node = run.node
    if isinstance(node, GearOfferNode):
        return GearPickChoice(pick=auto_gear_pick(library, run, node))
    if isinstance(node, LevelUpNode):
        weapon_attr = library.weapons[run.hero.weapon].scaling_attr
        attr = primary_attribute(skill_defs(library, run, run.hero.skills), weapon_attr)
        pick, replace = _auto_pick(library, run, node.offer)
        after = take_candidate(library, run, node.offer, pick, replace)
        levels = auto_levels(library, after)
        return LevelUpChoice(
            attributes={attr: node.points},
            pick=pick,
            replace=replace,
            levels=levels,
            evolve=auto_evolve(library, after, levels),
        )
    if isinstance(node, CampfireNode):
        if node.offer is not None:
            pick, replace = _auto_pick(library, run, node.offer)
            return PickChoice(pick=pick, replace=replace)
        return RerollChoice() if node.rerolls_left > 0 else LeaveChoice()
    raise ChoiceError(f"節點 {node.kind} 不需要選擇")


def auto_play(
    library: ContentLibrary,
    run: RunState,
    battle: ActiveBattle | None = None,
    *,
    stop: AutoStop | None = None,
    on_node: Callable[[RunState, RunState], None] | None = None,
) -> tuple[RunState, ActiveBattle | None]:
    """AI 代打到一輪結束或 ``stop`` 為真。``battle`` 是要接續的進行中戰鬥（讀檔）。回傳最後的
    ``RunState`` 與進行中的戰鬥（停在戰鬥中時；否則 ``None``）。``on_node(之前, 之後)`` 在每個
    節點完成後呼叫（CLI 印出進度）。"""
    while not run.ended:
        if stop is not None and stop(run, battle):
            return run, battle
        before = run
        if isinstance(run.node, BattleNode):
            if battle is None:
                battle = ActiveBattle(library, run)
            current = battle
            battle.auto(None if stop is None else _battle_stop(stop, run))
            if not current.state.ended:
                return run, current
            run = finish_battle(library, run, current.state, len(current.steps), current.steps)
            battle = None
        else:
            run = apply_choice(library, run, auto_choice(library, run))
        if on_node is not None:
            on_node(before, run)
    return run, None
