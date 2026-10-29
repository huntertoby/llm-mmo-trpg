"""AI 代打整輪（``trpg run auto``；測試與模擬用，Phase 3-5a）。

- 戰鬥：所有單位（含主角）由效用 AI 控制（:class:`~trpg.roguelite.battle.ActiveBattle`）。
- 配點：全部點在主角技能最常用的縮放屬性。
- 戰後裝備三選一（Phase 3K-2）：挑預算分數比該部位目前裝備高最多的一件（空部位算 0 分），沒有比較
  高的就跳過（:func:`trpg.roguelite.gear.auto_gear_pick`）；營火不換裝。
- 升級（白板）與完整技能三選一（Phase 3W-5）：依序找第一個不用替換就裝得下的候選；都裝不下時，用
  第一個裝得下的候選換掉主角同一種欄位的最後一個技能；還是不行就跳過。
- 靈感點（Phase 3W-5，:func:`auto_flash_choice`）：戰鬥之間每個節點先花點數，不指定類別、一律選
  第一個選項（轉型要卸下別招時卸下該欄最後一招）：

  1. 營火：有完整技能還沒重閃過調整欄時，先重閃它（1 點）。
  2. 閃現：裝備中可以閃的技能，挑閃過最多次的（同次數依技能列順序），所以會先把一招練到第 3 次
     大變化。
  3. 有完整技能還沒重閃過調整欄、而且還沒到營火時，保留 1 點給營火。

  出題失敗（這一次沒有合法變化）的技能在同一個節點跳過，不會卡住。

- 策略（Phase 3W-8，只影響模擬；預設 ``none`` ＝ 上面的行為）：``none`` 不指定類別；``all`` 每次閃現
  都指定類別（依用法排第一的類別，2 點；點數不夠就等到存夠；該招沒有可指定的類別才退回不指定）；
  ``mixed`` 在這一輪已經閃過的總次數為偶數時照 ``all`` 的做法，奇數時不指定。

全部確定性：同一個 ``RunState`` 必得相同結果。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.battle import ActiveBattle
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.flashes import focus_order, owned_skills, problem_of, state_of
from trpg.roguelite.gear import auto_gear_pick
from trpg.roguelite.offers import skill_defs, take_candidate
from trpg.roguelite.progress import apply_choice, finish_battle
from trpg.roguelite.start import primary_attribute
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    Choice,
    CompleteOfferNode,
    CompletePickChoice,
    FlashChoice,
    FlashPickChoice,
    GearOfferNode,
    GearPickChoice,
    LeaveChoice,
    LevelUpChoice,
    LevelUpNode,
    RunState,
    SkillOffer,
)
from trpg.skillgen.flash_major import transform_slot_plan
from trpg.skillgen.flash_state import COMPLETE_SLOT

__all__ = [
    "FLASH_POLICIES",
    "AutoStop",
    "FlashPolicy",
    "auto_choice",
    "auto_flash_choice",
    "auto_play",
]

type FlashPolicy = Literal["none", "all", "mixed"]
"""AI 花靈感點的策略（3W-8）：不指定類別、全指定類別、混合。"""
FLASH_POLICIES: tuple[FlashPolicy, ...] = ("none", "all", "mixed")

type AutoStop = Callable[[RunState, ActiveBattle | None], bool]
"""停止條件：在每個節點與每個戰鬥步驟之前呼叫（``ActiveBattle`` 為進行中的戰鬥或 ``None``）。"""


def _slot(skill: SkillDef) -> str:
    return skill.slot_kind


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


def _pending_pick(library: ContentLibrary, run: RunState) -> FlashPickChoice:
    """待選的閃現：選第一個選項；轉型要卸下別招時卸下該欄最後一招。"""
    pending = run.pending_flash
    assert pending is not None
    option = pending.offer.options[0]
    unequip = None
    if pending.skill in run.hero.skills:
        equipped = skill_defs(library, run, run.hero.skills)
        plan = transform_slot_plan(
            equipped, pending.skill, option.skill, library.ruleset.core.skill_slots
        )
        if plan.needs_unequip:
            unequip = plan.candidates[-1]
    return FlashPickChoice(pick=0, unequip=unequip)


def _unadjusted_complete(run: RunState) -> list[str]:
    """還沒重閃過調整欄的完整技能（學會的，依技能列順序）。"""
    return [
        s
        for s in owned_skills(run)
        if (state := state_of(run, s)).complete and state.adjustment is None
    ]


def _wants_focus(run: RunState, policy: FlashPolicy) -> bool:
    """這一次閃現想指定類別嗎（``mixed``：這一輪已經閃過的總次數為偶數時）。"""
    if policy == "mixed":
        return sum(len(s.records) for s in run.flash.values()) % 2 == 0
    return policy == "all"


def auto_flash_choice(
    library: ContentLibrary,
    run: RunState,
    skip: frozenset[str] = frozenset(),
    policy: FlashPolicy = "none",
) -> FlashChoice | None:
    """AI 這一個節點要花的靈感點（見模組說明）；不花時 ``None``。``skip`` 是這個節點出題失敗過的
    技能；``policy`` 是指定類別的策略。"""
    cost = library.flash.pricing.rule(False).cost
    if run.ended or run.insight < cost:
        return None
    complete = [s for s in _unadjusted_complete(run) if s not in skip]
    if isinstance(run.node, CampfireNode) and complete:
        return FlashChoice(skill=complete[0], slot=COMPLETE_SLOT)
    reserve = cost if complete and not isinstance(run.node, CampfireNode) else 0
    if run.insight - reserve < cost:
        return None
    ready = [s for s in run.hero.skills if s not in skip and problem_of(library, run, s) is None]
    if not ready:
        return None
    best = max(ready, key=lambda s: (len(state_of(run, s).records), -run.hero.skills.index(s)))
    category = None
    if _wants_focus(run, policy):
        if run.insight - reserve < library.flash.pricing.rule(True).cost:
            return None  # 想指定類別就等到存夠點數
        order = focus_order(library, run, best)
        category = order[0] if order else None
    return FlashChoice(skill=best, category=category)


def auto_choice(library: ContentLibrary, run: RunState) -> Choice:
    """節點的自動選擇（不含花靈感點，見 :func:`auto_flash_choice`）。"""
    if run.pending_flash is not None:
        return _pending_pick(library, run)
    node = run.node
    if isinstance(node, GearOfferNode):
        return GearPickChoice(pick=auto_gear_pick(library, run, node))
    if isinstance(node, LevelUpNode):
        weapon_attr = library.weapons[run.hero.weapon].scaling_attr
        attr = primary_attribute(skill_defs(library, run, run.hero.skills), weapon_attr)
        pick, replace = _auto_pick(library, run, node.offer)
        return LevelUpChoice(attributes={attr: node.points}, pick=pick, replace=replace)
    if isinstance(node, CompleteOfferNode):
        pick, replace = _auto_pick(library, run, node.offer)
        return CompletePickChoice(pick=pick, replace=replace)
    if isinstance(node, CampfireNode):
        return LeaveChoice()
    raise ChoiceError(f"節點 {node.kind} 不需要選擇")


def _battle_stop(stop: AutoStop, run: RunState) -> Callable[[ActiveBattle], bool]:
    return lambda battle: stop(run, battle)


def _spend(
    library: ContentLibrary,
    run: RunState,
    skip: set[str],
    on_node: Callable[[RunState, RunState], None] | None,
    policy: FlashPolicy,
) -> RunState:
    """這個節點能花的靈感點都花掉（閃現出題 → 選第一個選項）。"""
    while (flash := auto_flash_choice(library, run, frozenset(skip), policy)) is not None:
        before = run
        try:
            run = apply_choice(library, run, flash)
        except ChoiceError:
            skip.add(flash.skill)
            continue
        run = apply_choice(library, run, _pending_pick(library, run))
        if on_node is not None:
            on_node(before, run)
    return run


def auto_play(
    library: ContentLibrary,
    run: RunState,
    battle: ActiveBattle | None = None,
    *,
    stop: AutoStop | None = None,
    on_node: Callable[[RunState, RunState], None] | None = None,
    flash_policy: FlashPolicy = "none",
) -> tuple[RunState, ActiveBattle | None]:
    """AI 代打到一輪結束或 ``stop`` 為真。``battle`` 是要接續的進行中戰鬥（讀檔）。回傳最後的
    ``RunState`` 與進行中的戰鬥（停在戰鬥中時；否則 ``None``）。``on_node(之前, 之後)`` 在每個
    節點完成後（以及每次閃現後）呼叫（CLI 印出進度）。``flash_policy`` 見模組說明。"""
    while not run.ended:
        if stop is not None and stop(run, battle):
            return run, battle
        before = run
        if isinstance(run.node, BattleNode) and run.pending_flash is None:
            if battle is None:
                battle = ActiveBattle(library, run)
            current = battle
            battle.auto(None if stop is None else _battle_stop(stop, run))
            if not current.state.ended:
                return run, current
            run = finish_battle(library, run, current.state, len(current.steps), current.steps)
            battle = None
        else:
            if run.pending_flash is None:
                run = _spend(library, run, set(), on_node, flash_policy)
                before = run
            run = apply_choice(library, run, auto_choice(library, run))
        if on_node is not None:
            on_node(before, run)
    return run, None
