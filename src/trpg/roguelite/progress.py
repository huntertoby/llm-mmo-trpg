"""一輪的推進：開戰設定、戰後結算、升級與營火的選擇、下一個節點（Phase 3-5a）。

全部是純函式（``RunState`` 進、``RunState`` 出）。節點順序：

1. 戰鬥（第 i 場）→ 打贏：寫回主角 HP、法力、源力（＋戰後獎勵），加經驗與靈感點、記下「先上場
   用過」（3W-5）；沒打贏（含輪數上限）→ 一輪失敗。
2. 一般戰鬥打贏 → 裝備三選一（3K-2）。
3. 每升一級一個升級節點（＋屬性點、白板 3 選 1 或跳過）。角色升階時（3W-9，6.34.9）先把主角每招
   技能照新階級的預算重配（``trpg.roguelite.retier``），候選也用新階級。
4. 打完的場數在 ``complete_skill_after`` 內 → 完整技能三選一（3W-5，06 6.34.6）。
5. 打完的場數在 ``campfire_after`` 內 → 營火（進入時 HP、法力回滿，源力 ＋N）。
6. 下一場；下一場是 Boss 戰時源力至少 ``boss_floor``。Boss 戰打贏 → 一輪勝利。

閃現（3W-5，:mod:`trpg.roguelite.flashes`）不推進節點：戰鬥之間（一輪沒結束、不在戰鬥中）都可以
閃現；重閃、溶掉、傳承只在營火。付了點還沒選的閃現選項要先選完，才能做別的選擇。
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence

from trpg.content.library import ContentLibrary
from trpg.engine.actions import MANAGEMENT_ACTION_TYPES, Step
from trpg.engine.gear.core import build_gear, geared_template
from trpg.engine.results import battle_result
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup
from trpg.engine.state import BattleState, state_to_json
from trpg.roguelite.attributes import allocate_attributes, merge_spent, respec_attributes
from trpg.roguelite.errors import ChoiceError, NodeConflictError
from trpg.roguelite.flashes import (
    after_battle_flash,
    dissolve,
    inherit,
    open_flash,
    pick_flash,
    with_acquired,
)
from trpg.roguelite.gear import equip, gear_offer_node, run_loadout, take_gear
from trpg.roguelite.growth import set_loadout
from trpg.roguelite.offers import make_offer, offer_updates, take_candidate
from trpg.roguelite.retier import run_tier, sync_skill_tier
from trpg.roguelite.start import allocation_problems, apply_allocation
from trpg.roguelite.state import (
    AllocateChoice,
    BattleNode,
    BattleRecord,
    CampfireNode,
    Choice,
    CompleteOfferNode,
    CompletePickChoice,
    DissolveChoice,
    EndedNode,
    EquipChoice,
    FlashChoice,
    FlashPickChoice,
    GearOfferNode,
    GearPickChoice,
    InheritChoice,
    LeaveChoice,
    LevelUpChoice,
    LevelUpNode,
    LoadoutChoice,
    RespecAttributesChoice,
    RunState,
    SkillOffer,
)
from trpg.shared.types import Attribute, Team, UnitId
from trpg.skillgen.usage import SkillUsage, collect_usage, merge_usage

__all__ = [
    "add_behavior",
    "apply_choice",
    "battle_setup",
    "battle_usage",
    "finish_battle",
    "hero_effective_attributes",
    "hero_spawn",
    "hero_unit_id",
    "level_for",
    "next_node",
    "run_loadout",
]

_NODE_TEXT = {
    "battle": "戰鬥",
    "gear_offer": "裝備三選一",
    "level_up": "升級",
    "complete_offer": "完整技能三選一",
    "campfire": "營火",
    "ended": "一輪已結束",
}


def _battle_node(run: RunState) -> BattleNode:
    if not isinstance(run.node, BattleNode):
        raise NodeConflictError(f"目前不是戰鬥（{_NODE_TEXT[run.node.kind]}）")
    return run.node


def hero_effective_attributes(library: ContentLibrary, run: RunState) -> dict[Attribute, int]:
    """主角的有效屬性（戰鬥之間沒有狀態）：基礎屬性＋裝備的屬性詞條，和引擎開戰時的
    :func:`trpg.engine.gear.core.geared_template` 同一個算法（角色面板的常駐數值階數用）。"""
    ruleset = library.ruleset
    gear = build_gear(run_loadout(library, run), ruleset.equipment)
    return dict(geared_template(run.hero, gear, ruleset).attributes)


def hero_spawn(library: ContentLibrary, run: RunState) -> UnitSpawn:
    """主角的出場設定：帶目前的 HP、法力、耐力、源力與等級加成（一輪與單場戰鬥共用）。Phase 3W-5
    起沒有技能等級（閃現的變化已經套用在技能定義上）。"""
    core = library.ruleset.core
    # 等級加成併入範本的基礎 HP，體質的部分由引擎加（與 RunState.max_hp_in 同一個式子）
    leveled = run.hero.model_copy(
        update={
            "max_hp": run.hero.max_hp + core.level_hp_bonus(run.hero.max_hp, run.level),
            "scaled_resources": True,  # 法力與耐力上限依屬性（3H-2；舊存檔的主角範本沒有此旗標）
            "level": run.level,  # 角色等級（3-33b）：召喚物成長依施放者等級
        }
    )
    return UnitSpawn(
        template=leveled,
        weapon=library.weapons[run.hero.weapon],
        equipment=run_loadout(library, run),
        team=Team.ALLY,
        source=run.source,
        hp=run.hp,
        mana=run.mana,
        stamina=run.stamina,
    )


def battle_setup(library: ContentLibrary, run: RunState) -> BattleSetup:
    """本場戰鬥的設定：主角（第一個我方單位，帶目前的 HP、法力、源力）＋ 標準隊友（滿狀態）＋
    本場的敵人；規則包加入主角的生成技能（``Ruleset.with_skills``）。"""
    plan = run.plan_of(_battle_node(run).index)
    rules = library.roguelite
    base = build_setup(
        library,
        plan.map_id,
        rules.companions,
        plan.enemies,
        max_rounds=rules.max_rounds,
        objective=library.map(plan.map_id).objective_for(plan.objective),
    )
    hero = hero_spawn(library, run)
    ruleset = library.ruleset.with_skills(run.generated_skills)
    return base.model_copy(update={"units": (hero, *base.units), "ruleset": ruleset})


def with_hp_change(library: ContentLibrary, before: RunState, after: RunState) -> RunState:
    """``after`` 的最大 HP 與 ``before`` 不同時（升級、配點加體質），目前 HP 同步增加（或減少，
    不低於 1）相同的量；法力與耐力上限（3H-2，依屬性）也一樣（不低於 0；耐力為「滿」時維持滿）。"""
    core = library.ruleset.core
    update: dict[str, int] = {}
    delta = after.max_hp_in(core) - before.max_hp_in(core)
    if delta:
        update["hp"] = max(1, after.hp + delta)
    delta = after.max_mana_in(core) - before.max_mana_in(core)
    if delta:
        update["mana"] = max(0, after.mana + delta)
    delta = after.max_stamina_in(core) - before.max_stamina_in(core)
    if delta and after.stamina is not None:
        update["stamina"] = max(0, after.stamina + delta)
    return after.model_copy(update=update) if update else after


def hero_unit_id(state: BattleState) -> UnitId:
    """主角的單位 ID：我方第一個單位（單位 ID 依設定順序分配，主角排在最前面）。"""
    return next(u.id for u in state.units_sorted() if u.team is Team.ALLY)


def level_for(library: ContentLibrary, xp: int) -> int:
    return 1 + sum(1 for t in library.roguelite.level_thresholds if xp >= t)


def add_behavior(
    behavior: Mapping[str, int], actions: Sequence[Step], hero: UnitId
) -> dict[str, int]:
    """行為紀錄（候選產生器用，Phase 3-24b2）：把主角在 ``actions`` 裡做過的動作類型累加進
    ``behavior``（不含結束回合等管理操作與暫停中的決定；施放技能記為 ``use_skill``）。依類型
    排序。"""
    counts = Counter(behavior)
    counts.update(
        step.type
        for step in actions
        if step.unit_id == hero and step.type not in (*MANAGEMENT_ACTION_TYPES, "decision")
    )
    return {k: counts[k] for k in sorted(counts)}


def battle_usage(
    library: ContentLibrary, run: RunState, actions: Sequence[Step], hero: UnitId
) -> dict[str, SkillUsage]:
    """這一場（``run`` 仍在戰鬥節點）主角每招技能的用法統計（Phase 3-26b）：以開戰設定、種子與步驟
    重播出事件（確定性），只統計主角裝備中的技能。"""
    if not actions:
        return {}
    setup = battle_setup(library, run)
    plan = run.plan_of(_battle_node(run).index)
    return collect_usage(setup, plan.seed, actions, hero, library.keywords, only=run.hero.skills)


def finish_battle(
    library: ContentLibrary,
    run: RunState,
    state: BattleState,
    steps: int,
    actions: Sequence[Step] = (),
) -> RunState:
    """戰鬥結束後結算（``state`` 必須已結束）。主角在戰鬥中倒下但我方勝利時以 1 HP 繼續。
    ``actions`` 是這場的步驟（累加進行為紀錄 ``RunState.behavior`` 與用法統計
    ``RunState.skill_usage``）。"""
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
        stamina=hero.stamina,
        state_digest=hashlib.sha256(state_to_json(state).encode("utf-8")).hexdigest(),
    )
    history = (*run.history, record)
    behavior = add_behavior(run.behavior, actions, hero_unit_id(state))
    this_battle = battle_usage(library, run, actions, hero_unit_id(state))
    usage = merge_usage(run.skill_usage, this_battle)
    flashed = after_battle_flash(library, run, this_battle, won=won)  # 靈感點與先上場用過（3W-5）
    if won and not plan.boss and run.plan_of(node.index + 1).boss:  # Boss 前加給（BAL-1，預設 0）
        flashed["insight"] += library.flash.rules.insight_preboss
    if not won:
        return run.model_copy(
            update={
                **flashed,
                "behavior": behavior,
                "skill_usage": usage,
                "hp": 0 if hero.downed else hero.hp,
                "mana": hero.mana,
                "stamina": hero.stamina,
                "source": hero.source,
                "history": history,
                "node": EndedNode(victory=False),
            }
        )
    xp = run.xp + library.roguelite.xp_per_battle
    gained = level_for(library, xp) - run.level
    mana, stamina = hero.mana, hero.stamina
    refill = library.roguelite.refill_after_battle  # 每場回滿的資源（3H-2 設定點，預設不開）
    if run.test_mode or "mana" in refill:
        mana = max(run.max_mana_in(core), hero.max_mana)
    if run.test_mode or "stamina" in refill:
        stamina = max(run.max_stamina_in(core), hero.max_stamina)
    hp = _heal_after_battle(library, hp, hero.max_hp)  # BAL-4c 設定點，預設 0
    if run.test_mode:
        # 測試模式（Phase 3-39）：戰後回滿到戰鬥中的實際上限（含裝備加成；升級再依最大 HP 的差補上）
        hp = max(run.max_hp_in(core), hero.max_hp)
    finished = run.model_copy(
        update={
            **flashed,
            "hp": hp,
            "mana": mana,
            "stamina": stamina,
            "source": source,
            "xp": xp,
            "levels_pending": run.levels_pending + gained,
            "battles_done": node.index,
            "history": history,
            "behavior": behavior,
            "skill_usage": usage,
        }
    )
    if not plan.boss:  # 一般戰鬥打贏：先裝備三選一，再升級（07 7.1）；Boss 戰後一輪結束，不給
        gear = gear_offer_node(library, finished, node.index)
        if gear is not None:
            return finished.model_copy(update={"node": gear})
    return next_node(library, finished)


def _heal_after_battle(library: ContentLibrary, hp: int, max_hp: int) -> int:
    """打贏後回復 ``heal_after_battle_permille``‰ 最大生命（BAL-4c 設定點；預設 0 時原值）。"""
    permille = library.roguelite.heal_after_battle_permille
    if permille == 0:
        return hp
    return min(max_hp, hp + max_hp * permille // 1000)


def next_node(library: ContentLibrary, run: RunState) -> RunState:
    """目前節點完成後的下一個節點（見模組說明），並套用進入時的效果（升級候選、營火回滿、Boss 前
    源力保底）。"""
    rules = library.roguelite
    core = library.ruleset.core
    if run.levels_pending > 0:
        return _level_up(library, run)
    run = sync_skill_tier(library, run)  # 舊存檔（skill_tier 為空）在戰鬥之間照角色階級重配一次
    done = run.battles_done
    if done >= len(run.plan):
        return run.model_copy(update={"node": EndedNode(victory=True)})
    if done in rules.complete_skill_after and done not in run.complete_offers_done:
        return _complete_offer(library, run, done)
    if done in rules.campfire_after and done not in run.campfires_done:
        return run.model_copy(
            update={
                "hp": run.max_hp_in(core),
                "mana": run.max_mana_in(core),
                "stamina": run.max_stamina_in(core),
                "source": min(core.source_max, run.source + rules.source.campfire),
                "campfires_done": (*run.campfires_done, done),
                "node": CampfireNode(after_battle=done),
            }
        )
    source = run.source
    if run.plan_of(done + 1).boss:
        source = max(source, min(core.source_max, rules.source.boss_floor))
    return run.model_copy(update={"source": source, "node": BattleNode(index=done + 1)})


def _level_up(library: ContentLibrary, run: RunState) -> RunState:
    """處理一次升級：等級 +1、最大 HP 同步，角色升階時每招重配（3W-9），產生白板候選。"""
    before_tier = run_tier(library, run)
    leveled = with_hp_change(
        library,
        run,
        run.model_copy(update={"level": run.level + 1, "levels_pending": run.levels_pending - 1}),
    )
    # 升階重算（3W-9，6.34.9）：角色升階的當下（戰鬥之間）每招照新階級的預算重配
    leveled = sync_skill_tier(library, leveled)
    offer = make_offer(library, leveled, "level_up")
    node = LevelUpNode(
        level=leveled.level,
        points=library.roguelite.attribute_points_per_level,
        offer=offer,
        tier_up=run_tier(library, leveled) > before_tier,
    )
    return leveled.model_copy(
        update={"offers_made": run.offers_made + 1, "node": node, **offer_updates(leveled, offer)}
    )


def _complete_offer(library: ContentLibrary, run: RunState, after: int) -> RunState:
    """完整技能三選一（3W-5，06 6.34.6）：候選照完整技能的強度重調。"""
    offer = make_offer(library, run, "complete")
    return run.model_copy(
        update={
            "offers_made": run.offers_made + 1,
            "complete_offers_done": (*run.complete_offers_done, after),
            "node": CompleteOfferNode(after_battle=after, offer=offer),
            **offer_updates(run, offer),
        }
    )


def _take(
    library: ContentLibrary,
    run: RunState,
    offer: SkillOffer,
    pick: int | None,
    replace: str | None,
) -> RunState:
    """裝上候選（白板或完整技能），閃現狀態從頭算。"""
    taken = take_candidate(library, run, offer, pick, replace)
    if pick is None:
        return taken
    return with_acquired(taken, offer.candidates[pick].id, complete=offer.reason == "complete")


def apply_choice(library: ContentLibrary, run: RunState, choice: Choice) -> RunState:
    """套用升級或營火的選擇。節點不符時拋出 :class:`NodeConflictError`，內容不合法時拋出
    :class:`ChoiceError`（狀態不變）。"""
    if run.pending_flash is not None and not isinstance(choice, FlashPickChoice):
        raise NodeConflictError("還有閃現的選項沒有選，請先送出 flash_pick")
    if isinstance(
        choice, FlashChoice | FlashPickChoice | DissolveChoice | InheritChoice | LoadoutChoice
    ):
        return _manage_skills(library, run, choice)
    if isinstance(choice, RespecAttributesChoice | AllocateChoice):
        return _manage_attributes(library, run, choice)
    if isinstance(choice, EquipChoice):
        return _equip_from_backpack(library, run, choice)
    return _node_choice(library, run, choice)


def _node_choice(library: ContentLibrary, run: RunState, choice: Choice) -> RunState:
    """推進節點的選擇（裝備三選一、升級、完整技能三選一、營火離開）。"""
    node = run.node
    if isinstance(node, GearOfferNode):
        if not isinstance(choice, GearPickChoice):
            raise NodeConflictError("目前在裝備三選一，請送出 gear_pick（pick 為空 ＝ 跳過）")
        return next_node(library, take_gear(library, run, node, choice.pick))
    if isinstance(node, LevelUpNode):
        if not isinstance(choice, LevelUpChoice):
            raise NodeConflictError("目前在升級，請送出升級選擇（level_up）")
        problems = allocation_problems(choice.attributes, node.points)
        if problems:
            raise ChoiceError("；".join(problems))
        hero = apply_allocation(run.hero, choice.attributes)
        spent = merge_spent(run.attribute_spent, choice.attributes)
        allocated = with_hp_change(
            library, run, run.model_copy(update={"hero": hero, "attribute_spent": spent})
        )
        taken = _take(library, allocated, node.offer, choice.pick, choice.replace)
        return next_node(library, taken)
    if isinstance(node, CompleteOfferNode):
        if not isinstance(choice, CompletePickChoice):
            raise NodeConflictError(
                "目前在完整技能三選一，請送出 complete_pick（pick 為空 ＝ 跳過）"
            )
        return next_node(library, _take(library, run, node.offer, choice.pick, choice.replace))
    if isinstance(node, CampfireNode):
        return _campfire(library, run, node, choice)
    raise NodeConflictError(f"目前是{_NODE_TEXT[node.kind]}，沒有可以選擇的東西")


def _equip_from_backpack(library: ContentLibrary, run: RunState, choice: EquipChoice) -> RunState:
    """營火換裝（Phase 3K-2）：把背包裡的裝備換上，換下的進背包；不推進節點。"""
    if not isinstance(run.node, CampfireNode):
        raise NodeConflictError(f"換裝只能在營火（目前是{_NODE_TEXT[run.node.kind]}）")
    held = next((i for i in run.backpack if i.id == choice.item_id), None)
    if held is None:
        raise ChoiceError(f"背包裡沒有這件裝備：{choice.item_id}")
    return equip(library, run, held, choice.slot, from_backpack=True)


_CAMPFIRE_ONLY = {"inherit": "傳承", "dissolve": "溶掉技能", "loadout": "換技能"}


def _manage_skills(
    library: ContentLibrary,
    run: RunState,
    choice: FlashChoice | FlashPickChoice | DissolveChoice | InheritChoice | LoadoutChoice,
) -> RunState:
    """靈感點與技能庫（Phase 3W-5；不推進節點）：閃現在戰鬥之間都可以；重閃、溶掉、傳承與換技能只在
    營火（06 6.34.3、6.34.9）。戰鬥進行中由 API 擋下。"""
    if run.ended:
        raise NodeConflictError(f"目前是{_NODE_TEXT[run.node.kind]}，不能管理技能")
    if isinstance(choice, FlashPickChoice):
        return pick_flash(library, run, choice)
    camp = isinstance(run.node, CampfireNode)
    if isinstance(choice, FlashChoice):
        if choice.slot is not None and not camp:
            raise NodeConflictError(f"重閃只能在營火（目前是{_NODE_TEXT[run.node.kind]}）")
        return open_flash(library, run, choice)
    if not camp:
        what = _CAMPFIRE_ONLY[choice.kind]
        raise NodeConflictError(f"{what}只能在營火（目前是{_NODE_TEXT[run.node.kind]}）")
    if isinstance(choice, DissolveChoice):
        return dissolve(library, run, choice)
    if isinstance(choice, InheritChoice):
        return inherit(library, run, choice)
    return set_loadout(library, run, choice.skills)


def _manage_attributes(
    library: ContentLibrary, run: RunState, choice: RespecAttributesChoice | AllocateChoice
) -> RunState:
    """營火的免費屬性重配與重配後的分配（Phase 3H-3；不推進節點）：重配只在營火；分配在營火與
    戰前都可以（戰鬥中由 API 擋下）。體質改變時最大 HP 與目前 HP 同步增減（和升級配點一樣）。"""
    if isinstance(choice, RespecAttributesChoice):
        if not isinstance(run.node, CampfireNode):
            raise NodeConflictError(f"重配屬性點只能在營火（目前是{_NODE_TEXT[run.node.kind]}）")
        return with_hp_change(library, run, respec_attributes(run))
    if run.ended:
        raise NodeConflictError(f"目前是{_NODE_TEXT[run.node.kind]}，不能分配屬性點")
    return with_hp_change(library, run, allocate_attributes(run, choice.attributes))


def _campfire(
    library: ContentLibrary, run: RunState, node: CampfireNode, choice: Choice
) -> RunState:
    if isinstance(choice, LeaveChoice):
        return next_node(library, run)
    raise NodeConflictError(
        "目前在營火，請送出 flash、dissolve、inherit、loadout、equip、respec_attributes、"
        "allocate 或 leave"
    )
