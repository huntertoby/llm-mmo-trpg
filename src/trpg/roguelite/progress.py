"""一輪的推進：開戰設定、戰後結算、升級與營火的選擇、下一個節點（Phase 3-5a）。

全部是純函式（``RunState`` 進、``RunState`` 出）。節點順序：

1. 戰鬥（第 i 場）→ 打贏：寫回主角 HP、法力、源力（＋戰後獎勵），加經驗；沒打贏（含輪數上限）→
   一輪失敗。
2. 每升一級一個升級節點（＋屬性點、3 選 1 或跳過）。
3. 打完的場數在 ``campfire_after`` 內 → 營火（進入時 HP、法力回滿，源力 ＋N；可重骰一次）。
4. 下一場；下一場是 Boss 戰時源力至少 ``boss_floor``。Boss 戰打贏 → 一輪勝利。
"""

from __future__ import annotations

import hashlib

from trpg.content.library import ContentLibrary
from trpg.engine.results import battle_result
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup
from trpg.engine.state import BattleState, state_to_json
from trpg.roguelite.errors import ChoiceError, NodeConflictError
from trpg.roguelite.offers import make_offer, take_candidate
from trpg.roguelite.start import allocation_problems, apply_allocation
from trpg.roguelite.state import (
    BattleNode,
    BattleRecord,
    CampfireNode,
    Choice,
    EndedNode,
    LeaveChoice,
    LevelUpChoice,
    LevelUpNode,
    PickChoice,
    RerollChoice,
    RunState,
)
from trpg.shared.types import Team, UnitId

__all__ = [
    "apply_choice",
    "battle_setup",
    "finish_battle",
    "hero_unit_id",
    "level_for",
    "next_node",
]

_NODE_TEXT = {"battle": "戰鬥", "level_up": "升級", "campfire": "營火", "ended": "一輪已結束"}


def _battle_node(run: RunState) -> BattleNode:
    if not isinstance(run.node, BattleNode):
        raise NodeConflictError(f"目前不是戰鬥（{_NODE_TEXT[run.node.kind]}）")
    return run.node


def battle_setup(library: ContentLibrary, run: RunState) -> BattleSetup:
    """本場戰鬥的設定：主角（第一個我方單位，帶目前的 HP、法力、源力）＋ 標準隊友（滿狀態）＋
    本場的敵人；規則包加入主角的生成技能（``Ruleset.with_skills``）。"""
    plan = run.plan_of(_battle_node(run).index)
    rules = library.roguelite
    base = build_setup(
        library, plan.map_id, rules.companions, plan.enemies, max_rounds=rules.max_rounds
    )
    hero = UnitSpawn(
        template=run.hero,
        weapon=library.weapons[run.hero.weapon],
        team=Team.ALLY,
        source=run.source,
        hp=run.hp,
        mana=run.mana,
    )
    ruleset = library.ruleset.with_skills(run.generated_skills)
    return base.model_copy(update={"units": (hero, *base.units), "ruleset": ruleset})


def hero_unit_id(state: BattleState) -> UnitId:
    """主角的單位 ID：我方第一個單位（單位 ID 依設定順序分配，主角排在最前面）。"""
    return next(u.id for u in state.units_sorted() if u.team is Team.ALLY)


def level_for(library: ContentLibrary, xp: int) -> int:
    return 1 + sum(1 for t in library.roguelite.level_thresholds if xp >= t)


def finish_battle(
    library: ContentLibrary, run: RunState, state: BattleState, steps: int
) -> RunState:
    """戰鬥結束後結算（``state`` 必須已結束）。主角在戰鬥中倒下但我方勝利時以 1 HP 繼續。"""
    node = _battle_node(run)
    if not state.ended:
        raise NodeConflictError("戰鬥還沒結束")
    plan = run.plan_of(node.index)
    result = battle_result(state)
    hero = result.ally(hero_unit_id(state))
    assert hero is not None
    won = result.winner is Team.ALLY
    core = library.ruleset.core
    hp = max(hero.hp, 1) if won else hero.hp  # 倒下但我方勝利：以 1 HP 繼續（保守）
    source = min(core.source_max, hero.source + library.roguelite.source.after_battle)
    record = BattleRecord(
        index=node.index,
        map_id=plan.map_id,
        boss=plan.boss,
        won=won,
        end_reason=result.end_reason,
        rounds=result.round,
        steps=steps,
        hp=hp,
        mana=hero.mana,
        source=source if won else hero.source,
        hero_downed=hero.downed,
        state_digest=hashlib.sha256(state_to_json(state).encode("utf-8")).hexdigest(),
    )
    history = (*run.history, record)
    if not won:
        return run.model_copy(
            update={
                "hp": 0 if hero.downed else hero.hp,
                "mana": hero.mana,
                "source": hero.source,
                "history": history,
                "node": EndedNode(victory=False),
            }
        )
    xp = run.xp + library.roguelite.xp_per_battle
    gained = level_for(library, xp) - run.level
    finished = run.model_copy(
        update={
            "hp": hp,
            "mana": hero.mana,
            "source": source,
            "xp": xp,
            "levels_pending": run.levels_pending + gained,
            "battles_done": node.index,
            "history": history,
        }
    )
    return next_node(library, finished)


def next_node(library: ContentLibrary, run: RunState) -> RunState:
    """目前節點完成後的下一個節點（見模組說明），並套用進入時的效果（升級候選、營火回滿、Boss 前
    源力保底）。"""
    rules = library.roguelite
    core = library.ruleset.core
    if run.levels_pending > 0:
        leveled = run.model_copy(
            update={"level": run.level + 1, "levels_pending": run.levels_pending - 1}
        )
        offer = make_offer(library, leveled, "level_up")
        node = LevelUpNode(
            level=leveled.level, points=rules.attribute_points_per_level, offer=offer
        )
        return leveled.model_copy(update={"offers_made": run.offers_made + 1, "node": node})
    done = run.battles_done
    if done >= len(run.plan):
        return run.model_copy(update={"node": EndedNode(victory=True)})
    if done in rules.campfire_after and done not in run.campfires_done:
        return run.model_copy(
            update={
                "hp": run.max_hp,
                "mana": run.max_mana,
                "source": min(core.source_max, run.source + rules.source.campfire),
                "campfires_done": (*run.campfires_done, done),
                "node": CampfireNode(after_battle=done, rerolls_left=rules.rerolls_per_campfire),
            }
        )
    source = run.source
    if run.plan_of(done + 1).boss:
        source = max(source, min(core.source_max, rules.source.boss_floor))
    return run.model_copy(update={"source": source, "node": BattleNode(index=done + 1)})


def apply_choice(library: ContentLibrary, run: RunState, choice: Choice) -> RunState:
    """套用升級或營火的選擇。節點不符時拋出 :class:`NodeConflictError`，內容不合法時拋出
    :class:`ChoiceError`（狀態不變）。"""
    node = run.node
    if isinstance(node, LevelUpNode):
        if not isinstance(choice, LevelUpChoice):
            raise NodeConflictError("目前在升級，請送出升級選擇（level_up）")
        problems = allocation_problems(choice.attributes, node.points)
        if problems:
            raise ChoiceError("；".join(problems))
        hero = apply_allocation(run.hero, choice.attributes)
        taken = take_candidate(
            library, run.model_copy(update={"hero": hero}), node.offer, choice.pick, choice.replace
        )
        return next_node(library, taken)
    if isinstance(node, CampfireNode):
        return _campfire(library, run, node, choice)
    raise NodeConflictError(f"目前是{_NODE_TEXT[node.kind]}，沒有可以選擇的東西")


def _campfire(
    library: ContentLibrary, run: RunState, node: CampfireNode, choice: Choice
) -> RunState:
    if isinstance(choice, LeaveChoice):
        return next_node(library, run)
    if isinstance(choice, RerollChoice):
        if node.offer is not None:
            raise NodeConflictError("已經重骰過，請先選擇或放棄候選")
        if node.rerolls_left <= 0:
            raise NodeConflictError("這個營火沒有重骰次數了")
        offer = make_offer(library, run, "reroll")
        rerolled = node.model_copy(update={"offer": offer, "rerolls_left": node.rerolls_left - 1})
        return run.model_copy(update={"offers_made": run.offers_made + 1, "node": rerolled})
    if isinstance(choice, PickChoice):
        if node.offer is None:
            raise NodeConflictError("還沒有重骰，沒有候選可以選")
        taken = take_candidate(library, run, node.offer, choice.pick, choice.replace)
        if node.rerolls_left > 0:
            return taken.model_copy(update={"node": node.model_copy(update={"offer": None})})
        return next_node(library, taken)
    raise NodeConflictError("目前在營火，請送出 reroll、pick 或 leave")
