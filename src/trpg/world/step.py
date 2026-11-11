"""套用世界動作（Phase 5A-2；``docs/phases/Phase5計畫.md`` 6.5）。

``world_step(library, world, char, action, now) → StepResult(world, char, events)`` 是純函式：
不讀時間、不呼叫 LLM、亂數只由 :mod:`trpg.world.rng` 依賽季種子衍生。不合法的動作拋
:class:`~trpg.world.errors.WorldActionError`，傳入的狀態不變（模型是不可變的）。

- **移動**（09 9.6.2、9.6.7 #9、#10）：走到相鄰地點；每一步擲遇敵（目的地建議等級越高越容易），
  可花補給趕路降低機率；遇敵只產生 :class:`EncounterResult`（開戰在 5A-4）。抵達後對目的地旁的
  隱藏地點自動感知判定（#112）。
- **紮營**（#114）：非戰鬥狀態的地點花補給，HP、法力、耐力回滿＝營火。
- **5A-4**：撤退、戰鬥（:mod:`trpg.world.battle`）、城鎮休息、換技能、傳送
  （:mod:`trpg.world.town`）；移動到「已清空」的地點不遇敵（擲骰照擲）。
- **5A-6**：成長的動作（配點、重配、閃現、溶掉、傳承、立誓；:mod:`trpg.world.growth`）。有已付點、
  還沒選的閃現選項時，只能送 ``flash_pick``。
- **5B-4**：接任務、選任務給的技能、和 NPC 說話、酒館（:mod:`trpg.world.quests`、
  :mod:`trpg.world.social`）；**每個動作之後** 依事件結果調好感度、推進進行中的任務
  （:func:`~trpg.world.quests.advance_quests`）。有任務給的三選一還沒選時，只能送 ``offer_pick``。
- **6T-1a**：交易與郵寄（:mod:`trpg.world.trade`）：寄信、拒收、領過期退回的信同時改兩個角色
  （``other``；:data:`PAIR_HANDLERS`）；領自己信箱裡的信只改自己（``other`` 是 ``None``，6T-1b）。
  **每個動作之後** 整理裝備的來歷與綁定（:func:`~trpg.world.trade.stamp_gear`）。
- **5B-4b**：放棄、交涉、戰鬥解法（``event_solve``，:mod:`trpg.world.solutions`；戰鬥解法的遭遇
  結束時在動作後段結算事件）；**每個動作之前** 結算到期、有結局的線頭（:mod:`trpg.world.endings`）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.world_map import LocationDef, LocationMapDef
from trpg.world.actions import (
    UI_NOTE_ACTIONS,
    AcceptQuestAction,
    CampAction,
    CampedEvent,
    ChangeLookAction,
    ChangeRaceAction,
    EncounterCheckEvent,
    EncounterEvent,
    EventSolveAction,
    FightAction,
    FlashPickAction,
    HintSeenAction,
    HintsOffAction,
    HintsResetAction,
    HireAction,
    LoadoutAction,
    NarrateAction,
    NewsSeenAction,
    OfferPickAction,
    OpeningClassAction,
    OpeningConfirmAction,
    RestAction,
    RetreatAction,
    ShadowAiAction,
    SituationAction,
    TalkAction,
    TavernAction,
    TeleportAction,
    TravelAction,
    TraveledEvent,
    WorldAction,
    WorldEvent,
)
from trpg.world.battle import fight
from trpg.world.calendar import day_of
from trpg.world.common import max_hp, max_mana
from trpg.world.common import rules_of as _rules
from trpg.world.common import world_map_of as _world_map
from trpg.world.companions import sync_companions
from trpg.world.crafting import CRAFTING_HANDLERS
from trpg.world.economy import ECONOMY_HANDLERS, after_step
from trpg.world.economy_actions import EquipAction, LootChooseAction
from trpg.world.endings import expire_threads
from trpg.world.errors import WorldActionError
from trpg.world.events import mark_finished, mark_met_opportunities, roll_event
from trpg.world.field import (
    FieldCtx,
    FieldHooks,
    outdoor_map,
    placed,
    stale_field,
    teleport_origin,
    use_teleport_stone,
    walk,
)
from trpg.world.field_actions import (
    SneakAction,
    UseFieldObjectAction,
    UseTeleportStoneAction,
    WalkAction,
)
from trpg.world.field_enemies import after_fight, arrive_watch, walk_watch, with_visit
from trpg.world.field_things import (
    arrive_sense,
    drop_stale_marks,
    on_campfire,
    place_event,
    sense_walk,
    sneak,
    use_field_object,
)
from trpg.world.gear import apply_equip
from trpg.world.growth import GROWTH_ACTIONS, apply_growth, hero_tier
from trpg.world.league import league_step
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.looks import apply_look_change
from trpg.world.loot import choose_loot
from trpg.world.narration import apply_narration
from trpg.world.opening import apply_opening_class, opening_gate
from trpg.world.opening_choice import apply_opening_confirm
from trpg.world.opening_limits import in_starter_period
from trpg.world.party import default_party, hire, set_shadow_ai
from trpg.world.perception import can_perceive, perceive, perception_modifier, reveal_location
from trpg.world.quests import accept_quest, advance_quests, take_offer
from trpg.world.race_change import apply_race_change
from trpg.world.rng import STREAM_TRAVEL, draw
from trpg.world.season_board import after_season_step, roll_season
from trpg.world.season_boss import challenge
from trpg.world.season_events import SeasonBossAction
from trpg.world.shadows import save_after_prep
from trpg.world.situations import resolve_situation
from trpg.world.social import hear_opportunity_hint, talk, tavern
from trpg.world.solutions import make_encounter, settle_event_combat, solve_event
from trpg.world.state import (
    CharacterState,
    LocationRef,
    WorldState,
)
from trpg.world.town import (
    loadout,
    rest,
    retreat,
    teleport,
    with_visited_location,
    with_visited_town,
)
from trpg.world.trade import PAIR_HANDLERS, stamp_gear

__all__ = [
    "HANDLERS",
    "NO_CAMP_KINDS",
    "PAIR_HANDLERS",
    "StepResult",
    "camp_problem",
    "max_hp",
    "max_mana",
    "new_character",
    "perception_modifier",
    "reveal_location",
    "world_step",
]

NO_CAMP_KINDS = frozenset({"town", "elite_lair", "boss"})
"""不能紮營的地點種類（#114：Boss 地點、精英巢穴不行；城鎮直接休息，5A-4）。精英巢穴、Boss 站在
營火點上、地點已清空時例外（:data:`CLEAR_FIRST_KINDS`，6C-5b）。"""
CLEAR_FIRST_KINDS = frozenset({"camp", "elite_lair", "boss"})
"""要等地點「已清空」才能紮營的種類（含營火點上；21.10 第 13 條，6C-5b）。其他種類有巡邏也能
紮營。"""


@dataclass(frozen=True)
class StepResult:
    world: WorldState
    char: CharacterState
    events: tuple[WorldEvent, ...]
    other: CharacterState | None = None
    """同時改的另一個角色（6T-1a 交易；只改自己的動作為 ``None``）。"""


# ---------------------------------------------------------------------------
# 內容與角色數值
# ---------------------------------------------------------------------------


def new_character(
    library: ContentLibrary,
    character_id: str,
    hero: UnitTemplate,
    *,
    region: str,
    origin: str | None = None,
) -> CharacterState:
    """新角色：等級 1、HP 與法力滿、補給 ``supplies.start``、站在 ``region`` 的小鎮。"""
    world_map = _world_map(library, region)
    char = CharacterState.model_validate(
        {
            "character_id": character_id,
            "hero": hero,
            "origin": origin,
            "level": 1,
            "xp": 0,
            "hp": 0,
            "mana": 0,
            "region": region,
            "location": world_map.town,
            "supplies": _rules(library).supplies.start,
            "visited_towns": (region,),
            "visited_locations": ({"region": region, "location": world_map.town},),  # 6C-6
            "skill_tier": hero_tier(library, 1),  # 開局不重配（6.34.9），第一次升階才重配
            "mercenaries": default_party(library),  # 預設賽倫＋回春（9.6.11，5C-3）
            "gold": 0 if (economy := library.world_economy.rules) is None else economy.start_gold,
        }
    )
    return char.model_copy(update={"hp": max_hp(library, char), "mana": max_mana(library, char)})


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def world_step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WorldAction,
    now: int,
    *,
    actor: str | None = None,
    other: CharacterState | None = None,
    other_actor: str | None = None,
) -> StepResult:
    """套用一個世界動作；不合法拋 :class:`WorldActionError`。動作之後推進任務（5B-4）。

    ``actor`` 是做這個動作的帳號 ID（世界事件門檻的上線人數，Q15；5F-1）；``None``＝用角色 ID。
    ``other``、``other_actor``（6T-1a）：同時改兩個角色的動作（:data:`PAIR_HANDLERS`）的另一個角色與
    他的帳號（``None``＝用角色 ID）；結果的 ``other`` 是改過的他。
    賽季的內容照世界的季 ID 套上 ``season.yaml`` 的覆寫（:meth:`ContentLibrary.for_season`，
    5F-R2）。"""
    library = library.for_season(world.season_id)  # 這一季的 season.yaml 覆寫（5F-R2）
    opening_gate(library, world, char, action)  # TR-1、OB-1：開局各階段能做的動作
    note = isinstance(action, UI_NOTE_ACTIONS)  # 6F-4：只記畫面紀錄的動作，隨時都能做
    if char.pending_flash is not None and not isinstance(action, FlashPickAction) and not note:
        raise WorldActionError("還有閃現的選項沒有選：先選一個")
    if (
        char.pending_flash is None
        and char.pending_offers
        and not isinstance(action, OfferPickAction | NarrateAction)
        and not note
    ):  # 敘述不改數值（只有事件敘述換骨架），三選一待選時也能寫進日誌（5B-5）
        raise WorldActionError("還有任務給的技能三選一沒有選：先選一招或跳過")
    # 換日（5F-1）：世界事件的開始、門檻調整、失敗只寫進世界狀態（調整紀錄可查），不算這個角色的事件
    world, _rolled = roll_season(library, world, now)
    world, char, ended = expire_threads(library, world, char, now)  # 線頭到期結局（5B-4b）
    before = char
    actor_id = char.character_id if actor is None else actor
    account = ACCOUNT_HANDLERS.get(type(action))
    pair = PAIR_HANDLERS.get(type(action))
    if account is not None:  # 算帳號的動作（5F-4 循環賽報名、5F-3 賽季 Boss 挑戰，#100）
        result = account(library, world, char, action, now, actor_id)
    elif pair is not None:  # 6T-1a：同時改兩個角色（交易）
        result = _pair(library, world, char, action, now, actor_id, other, other_actor)
    else:
        result = _dispatch(library, world, char, action, now)
    moved = result.char
    if not isinstance(action, _FIELD_MOVES):  # 6B-2：別的動作換了地點，舊位置作廢
        moved = stale_field(before, moved)
    moved = drop_stale_marks(before, moved)  # 6C-5：換了地點，潛行結束、舊的「！」消失
    moved = with_visit(library, result.world, moved)  # 6C-1：換了地點就開始新的一趟
    if (moved.region, moved.location) != (before.region, before.location):
        # 6C-6：區域圖的戰爭迷霧（換了地點才記；出發的地點也記，舊存檔才不會漏掉建角的小鎮）
        moved = with_visited_location(with_visited_location(moved), before.region, before.location)
    cleared_world, moved, cleared = after_fight(  # 6C-1、6C-1b：打贏的那一隊消失（每隊清空）
        library, result.world, before, moved, action=action, events=result.events, now=now
    )
    if moved is not result.char or cleared_world is not result.world:
        result = StepResult(world=cleared_world, char=moved, events=(*result.events, *cleared))
    world, char, settled = settle_event_combat(
        library, result.world, before, result.char, result.events, now=now
    )
    events = (*ended, *result.events, *settled)
    char = mark_finished(library, char, events, now=now)  # 只出一次的骨架（5B-4c、5B-4d）
    char = mark_met_opportunities(library, char, events)  # 機遇保底（5B-4d）
    char, extra = advance_quests(library, world, char, events, now)
    char, joined = sync_companions(library, char)  # 劇情夥伴加入／離隊（5C-3）
    extra = [*extra, *joined]
    world, saved = save_after_prep(library, world, char, action, now)  # 城鎮整備存影子（5C-2）
    world, char, paid = after_step(library, world, char, (*events, *extra))  # 任務幣（5D-1）
    world, char, season = after_season_step(  # 懸賞、世界事件、今日目標、上線紀錄（5F-1）
        library,
        world,
        char,
        (*events, *extra),
        now=now,
        actor=actor_id,
    )
    paid = [*paid, *season]
    char = stamp_gear(library, before, char, action, events=(*events, *extra), now=now)  # 6T-1a
    if (
        not ended
        and not settled
        and not extra
        and not saved
        and not paid
        and char is result.char
        and world is result.world
    ):
        return result
    events_all = (*events, *extra, *saved, *paid)
    return StepResult(world=world, char=char, events=events_all, other=result.other)


def _pair(  # noqa: PLR0917 - 兩個角色與兩個帳號
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WorldAction,
    now: int,
    actor: str,
    other: CharacterState | None,
    other_actor: str | None,
) -> StepResult:
    """同時改兩個角色的動作（6T-1a）：另一個角色從 API 或重播時日誌的 ``counterpart`` 拿；
    ``None`` 時由處理自己決定（領自己信箱裡的信只改自己，6T-1b；寄信、拒收拒絕）。"""
    handler = PAIR_HANDLERS[type(action)]
    done = handler(
        library,
        world,
        char,
        other,
        action,
        now,
        actor=actor,
        other_actor=(other.character_id if other is not None else actor)
        if other_actor is None
        else other_actor,
    )
    return StepResult(world=done.world, char=done.char, events=done.events, other=done.other)


type _Handler = Callable[[ContentLibrary, WorldState, CharacterState, Any, int], StepResult]
"""一類世界動作的處理：``(library, world, char, action, now) → StepResult``。"""
type _CharFn = Callable[
    [ContentLibrary, WorldState, CharacterState, Any, int],
    tuple[CharacterState, tuple[WorldEvent, ...]],
]
type _WorldFn = Callable[
    [ContentLibrary, WorldState, CharacterState, Any, int],
    tuple[WorldState, CharacterState, tuple[WorldEvent, ...]],
]


def _keeps_world(fn: _CharFn) -> _Handler:
    """只改角色的動作（世界快照不變）。"""

    def run(
        library: ContentLibrary, world: WorldState, char: CharacterState, action: Any, now: int
    ) -> StepResult:
        char, events = fn(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)

    return run


def _changes_world(fn: _WorldFn) -> _Handler:
    """可能改世界快照的動作。"""

    def run(
        library: ContentLibrary, world: WorldState, char: CharacterState, action: Any, now: int
    ) -> StepResult:
        world, char, events = fn(library, world, char, action, now)
        return StepResult(world=world, char=char, events=events)

    return run


def _news_seen(
    char: CharacterState, action: NewsSeenAction, now: int
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """看過「你不在的時候」摘要（5F-1b）：只往後、不超過現在。"""
    until = max(min(action.until, now), char.news_seen_at or 0)
    if until == char.news_seen_at:
        return char, ()
    return char.model_copy(update={"news_seen_at": until}), ()


def _hint_seen(
    char: CharacterState, action: HintSeenAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """出過的提示與看過的升級畫面（6F-4）：ID 併進 ``hints_seen``（排序、不重複）；``level`` 只
    往上、不超過目前等級。沒有變化就原樣回傳。"""
    seen = tuple(sorted({*char.hints_seen, *action.ids}))
    level = char.level_seen
    if action.level is not None:
        level = max(level, min(action.level, char.level))
    if seen == char.hints_seen and level == char.level_seen:
        return char, ()
    return char.model_copy(update={"hints_seen": seen, "level_seen": level}), ()


def _hints_off(
    char: CharacterState, action: HintsOffAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    if action.off == char.hints_off:
        return char, ()
    return char.model_copy(update={"hints_off": action.off}), ()


def _hints_reset(char: CharacterState) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """「重新顯示提示」（6F-4）：清掉出過的提示、教學紀錄與「不再顯示」（升級畫面的紀錄不清）。"""
    if not char.hints_seen and not char.hints_off:
        return char, ()
    return char.model_copy(update={"hints_seen": (), "hints_off": False}), ()


def _fight(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: FightAction, now: int
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    if char.pending_encounter is None:
        raise WorldActionError("目前沒有遭遇")
    return fight(library, world, char, action, now)


def _teleport(
    library: ContentLibrary,
    _world: WorldState,
    char: CharacterState,
    action: TeleportAction,
    _now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """傳到另一區的城鎮；站在傳送石上也可以（21.1「從圖上傳送」：大世界圖點城鎮；6D-5）。"""
    on_stone = teleport_origin(library, placed(library, char)) is not None
    return teleport(library, char, action, on_stone=on_stone)


def _handlers() -> dict[type, _Handler]:
    table: dict[type, _Handler] = dict.fromkeys(GROWTH_ACTIONS, _keeps_world(apply_growth))
    table |= {
        TravelAction: _travel_node,
        # 6B-2 實地地圖（:mod:`trpg.world.field`）
        WalkAction: _changes_world(
            lambda lib, world, char, action, now: walk(lib, world, char, action, now, hooks=_HOOKS)
        ),
        UseTeleportStoneAction: _keeps_world(
            lambda lib, _w, char, action, _n: use_teleport_stone(lib, char, action)
        ),
        # 6C-5 地圖上的東西（:mod:`trpg.world.field_things`）
        SneakAction: _keeps_world(sneak),
        UseFieldObjectAction: _keeps_world(use_field_object),
        CampAction: lambda lib, world, char, _action, now: _camp(lib, world, char, now),
        FightAction: _changes_world(_fight),
        # 事件的情境判定（5B-2）與說書人敘述（5B-3，:mod:`trpg.world.narration`）
        SituationAction: _changes_world(resolve_situation),
        NarrateAction: _keeps_world(apply_narration),
        # 任務與聊天（5B-4，:mod:`trpg.world.quests`、:mod:`trpg.world.social`）
        AcceptQuestAction: _keeps_world(accept_quest),
        OfferPickAction: _keeps_world(
            lambda lib, _w, char, action, _n: take_offer(lib, char, action)
        ),
        TalkAction: _keeps_world(talk),
        TavernAction: _keeps_world(lambda lib, world, char, _a, now: tavern(lib, world, char, now)),
        EventSolveAction: _changes_world(solve_event),
        # 5D-2 換裝備；5D-2b 背包滿了：戰後結算選要丟哪件
        EquipAction: _keeps_world(lambda lib, _w, char, action, _n: apply_equip(lib, char, action)),
        LootChooseAction: _keeps_world(
            lambda lib, _w, char, action, _n: choose_loot(lib, char, action)
        ),
        # 撤退與城鎮服務（5A-4，:mod:`trpg.world.town`）；雇用與影子 AI（5C-1、5C-2）
        RetreatAction: _keeps_world(lambda lib, _w, char, _a, _n: retreat(lib, char)),
        RestAction: _keeps_world(lambda lib, _w, char, _a, _n: rest(lib, char)),
        LoadoutAction: _keeps_world(lambda lib, _w, char, action, _n: loadout(lib, char, action)),
        TeleportAction: _keeps_world(_teleport),
        HireAction: _keeps_world(
            lambda lib, world, char, action, _n: hire(lib, world, char, action)
        ),
        ShadowAiAction: _keeps_world(
            lambda lib, _w, char, action, _n: set_shadow_ai(lib, char, action)
        ),
        NewsSeenAction: _keeps_world(
            lambda _l, _w, char, action, now: _news_seen(char, action, now)
        ),
        # 6F-4（6F-2b）：提示與教學的紀錄記在角色身上
        HintSeenAction: _keeps_world(lambda _l, _w, char, action, _n: _hint_seen(char, action)),
        HintsOffAction: _keeps_world(lambda _l, _w, char, action, _n: _hints_off(char, action)),
        HintsResetAction: _keeps_world(lambda _l, _w, char, _a, _n: _hints_reset(char)),
        # 6R-1（#138）：這一季的免費換種族（:mod:`trpg.world.race_change`）
        ChangeRaceAction: _keeps_world(apply_race_change),
        # 6R-2（#137）：主城隨時免費改外觀（:mod:`trpg.world.looks`）
        ChangeLookAction: _keeps_world(apply_look_change),
        # TR-1（#134）：主城工坊靶場的「確定出發」（:mod:`trpg.world.opening`）
        OpeningConfirmAction: _keeps_world(apply_opening_confirm),
        # OB-1（#150）：靶場選大類，進入入門期
        OpeningClassAction: _keeps_world(apply_opening_class),
    }
    table |= {kind: _keeps_world(fn) for kind, fn in ECONOMY_HANDLERS.items()}  # 5D-1
    table |= {kind: _changes_world(fn) for kind, fn in CRAFTING_HANDLERS.items()}  # 5D-3
    return table


def _dispatch(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WorldAction,
    now: int,
) -> StepResult:
    handler = HANDLERS.get(type(action))
    if handler is None:
        raise WorldActionError(f"未知的世界動作：{action!r}")  # pragma: no cover
    return handler(library, world, char, action, now)


# ---------------------------------------------------------------------------
# 移動
# ---------------------------------------------------------------------------


def _check_travel(
    world: WorldState, char: CharacterState, world_map: LocationMapDef, action: TravelAction
) -> LocationDef:
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能移動")
    locations = world_map.location_by_id()
    target = locations.get(action.to)
    if target is None:
        raise WorldActionError(f"{world_map.name_zh}沒有地點 {action.to}")
    if action.to not in world_map.neighbors(char.location):
        raise WorldActionError(f"{action.to} 不和目前所在的 {char.location} 相鄰")
    if target.hidden and not char.has_revealed(world_map.region, target.id):
        raise WorldActionError(f"還沒發現 {action.to}")
    if target.unlock_flag is not None and not world.has_flag(target.unlock_flag):
        raise WorldActionError(f"{target.name_zh}還沒開放")
    return target


_FIELD_MOVES = (WalkAction, UseTeleportStoneAction)
"""自己會設定實地地圖位置的動作（其他動作換了地點就讓舊位置作廢）。"""


def _travel_node(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: TravelAction,
    now: int,
) -> StepResult:
    """``travel`` 動作：目前地點有實地地圖時拒絕（6B-2：走到出口才換圖）。"""
    if outdoor_map(library, char.region, char.location) is not None:
        raise WorldActionError("這裡有實地地圖，請走到出口")
    result = _travel(library, world, char, action, now)
    return _sense_arrival(library, result, now)


def _sense_arrival(library: ContentLibrary, result: StepResult, now: int) -> StepResult:
    """走路（``travel``）抵達有實地地圖的地點：抵達格也做隱藏入口的感知（21.10 第 17 條：走路抵達的
    那一格照判，6C-5b）。傳送、撤退、全滅回城抵達時不判。"""
    char = result.char
    if outdoor_map(library, char.region, char.location) is None:
        return result
    sensed, events = arrive_sense(library, result.world, placed(library, char), now)
    if not events:
        return result
    return StepResult(world=result.world, char=sensed, events=(*result.events, *events))


def _travel_fn(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: TravelAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """踩上出口＝一次 ``travel``（:func:`trpg.world.field.walk` 用）。"""
    result = _travel(library, world, char, action, now)
    return result.world, result.char, result.events


def _arrive(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """走出口或門抵達另一張圖：開始這一趟（6C-1）、抵達格的隱藏入口感知（6C-5）。"""
    char, watched = arrive_watch(library, world, char, now)
    char, sensed = arrive_sense(library, world, char, now)
    return char, (*watched, *sensed)


def _cross_fn(
    ctx: FieldCtx, char: CharacterState, where: tuple[LocationMapDef, LocationDef]
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """跨區出口＝對面那一區的一次 ``travel``（21.10 第 20 條，6C-R2）：照常擲遇敵、擲事件；不趕路、
    過渡口本身不另外花東西。地點與開放條件只在 :func:`trpg.world.field._cross_region` 查一次
    （6D-R1 合一）。"""
    moved = char.model_copy(update={"region": where[0].region})
    result = _travel_to(ctx.library, ctx.world, moved, where, now=ctx.now, hasten=False)
    return result.world, result.char, result.events


_HOOKS: Final = FieldHooks(
    travel=_travel_fn, watch=walk_watch, arrive=_arrive, sense=sense_walk, cross=_cross_fn
)
"""``walk`` 的鉤子：踩出口＝``travel``、看得見的敵人（6C-1）、隱藏入口與「！」（6C-5）、跨區出口
（21.10 第 20 條）。"""


def _travel(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: TravelAction,
    now: int,
) -> StepResult:
    world_map = _world_map(library, char.region)
    target = _check_travel(world, char, world_map, action)
    return _travel_to(library, world, char, (world_map, target), now=now, hasten=action.hasten)


def _travel_to(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    where: tuple[LocationMapDef, LocationDef],
    *,
    now: int,
    hasten: bool,
) -> StepResult:
    """抵達 ``where`` 的地點（已檢查過能去）：擲遇敵、事件、提示與感知（``travel``、跨區出口
    共用）。"""
    world_map, target = where
    rules = _rules(library)
    spent = 0
    if hasten:
        spent = rules.hasten.cost
        if char.supplies < spent:
            raise WorldActionError(f"補給不足，趕路要 {spent} 補給")
    chance = rules.encounter.permille_for(target.level_max)
    if world.is_cleared(char.region, target.id, now):
        chance = 0  # 已清空：沒有敵人（代決 5A4-9）；擲骰照擲，亂數消耗不變
    if outdoor_map(library, char.region, target.id) is not None:
        chance = 0  # 6C-1：有實地地圖的地點改由看得見的敵人取代（21.9 第 7 條）；擲骰照擲
    if in_starter_period(char):
        chance = 0  # OB-4（#150）：入門期節點移動不遇敵（21.5 第 9 點）；擲骰照擲
    if hasten:
        chance = chance * rules.hasten.encounter_permille // 1000

    events: list[WorldEvent] = [
        TraveledEvent(
            from_location=char.location, to=target.id, hasten=hasten, supplies_spent=spent
        )
    ]
    from_location = char.location
    char = char.model_copy(
        update={
            "location": target.id,
            "supplies": char.supplies - spent,
            "camped_at": None,
            "field_event": None,  # 6C-5：進入下一張地圖，舊的「！」消失、潛行結束
            "sneaking": False,
        }
    )
    if target.kind == "town":
        char = with_visited_town(char, char.region)
    rng, char = draw(world.season_seed, char, STREAM_TRAVEL)
    roll = rng.randint(0, 999)
    encountered = roll < chance
    events.append(
        EncounterCheckEvent(
            location=target.id, chance_permille=chance, roll=roll, encountered=encountered
        )
    )
    if encountered and target.level_max is not None:
        result, char = make_encounter(library, world, char, target, now)
        result = result.model_copy(update={"from_location": from_location})
        char = char.model_copy(update={"pending_encounter": result})
        events.append(EncounterEvent(result=result))
    rolled = roll_event(library, world, char, encountered=encountered, now=now)
    char, placed_events = place_event(library, world, rolled.char, rolled.events)  # 6C-5「！」
    events += placed_events
    if not encountered:  # 5B-4e：還沒遇過機遇的角色抵達提示地點（說書人順口提；5B-4f 一天一次）
        char, hint = hear_opportunity_hint(library, world, char, now)
        events += hint
    char, found = _perceive(library, world, char, world_map, now)
    events += found
    return StepResult(world=world, char=char, events=tuple(events))


def _perceive(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    world_map: LocationMapDef,
    now: int,
) -> tuple[CharacterState, list[WorldEvent]]:
    """抵達後對相鄰的隱藏地點自動感知判定（#112；鄰居依 ID 排序）。

    抵達的地點有實地地圖時不在這裡判定：改成走到隱藏入口 3 格內才判定（21.9 第 10 條，6C-5，
    :func:`trpg.world.field_things.sense_doors`）。"""
    if outdoor_map(library, char.region, char.location) is not None:
        return char, []
    locations = world_map.location_by_id()
    today = day_of(library, now)
    region = world_map.region
    events: list[WorldEvent] = []
    for neighbor_id in world_map.neighbors(char.location):
        hidden = locations[neighbor_id]
        if not can_perceive(char, region, hidden, today):
            continue
        char, found = perceive(library, world, char, hidden, region=region, today=today)
        events += found
    return char, events


# ---------------------------------------------------------------------------
# 紮營
# ---------------------------------------------------------------------------


def camp_problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> str | None:
    """不能在目前地點紮營的原因；可以時回傳 ``None``。"""
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能紮營"
    world_map = _world_map(library, char.region)
    here = world_map.location_by_id()[char.location]
    if here.kind == "town":
        return "城鎮裡直接休息，不用紮營"
    on_fire = on_campfire(library, char)  # 6C-5：固定營火點（#120、#114）
    if here.kind in NO_CAMP_KINDS and not on_fire:
        return f"{here.name_zh}不能紮營"
    if here.kind in CLEAR_FIRST_KINDS and not world.is_cleared(char.region, here.id, now):
        return f"{here.name_zh}的敵人還在，要先清空才能紮營"  # 6C-5b：營火點上也一樣
    cost = _rules(library).camp_cost
    if char.supplies < cost:
        return f"補給不足，紮營要 {cost} 補給"
    return None


def _camp(library: ContentLibrary, world: WorldState, char: CharacterState, now: int) -> StepResult:
    problem = camp_problem(library, world, char, now)
    if problem is not None:
        raise WorldActionError(problem)
    char = char.model_copy(
        update={
            "supplies": char.supplies - _rules(library).camp_cost,
            "hp": max_hp(library, char),
            "mana": max_mana(library, char),
            "stamina": None,
            "camped_at": LocationRef(region=char.region, location=char.location),
        }
    )
    event = CampedEvent(
        location=char.location, supplies_left=char.supplies, hp=char.hp, mana=char.mana
    )
    return StepResult(world=world, char=char, events=(event,))


type _AccountHandler = Callable[
    [ContentLibrary, WorldState, CharacterState, Any, int, str], StepResult
]
"""算帳號的世界動作：多一個 ``actor``（帳號 ID；沒有帳號＝角色 ID）。"""


def _league(  # noqa: PLR0917 - 和 _AccountHandler 同簽名（分派表的一格）
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: LeagueEnterAction | LeagueWithdrawAction,
    now: int,
    actor: str,
) -> StepResult:
    world, char, events = league_step(library, world, char, action, now, actor=actor)
    return StepResult(world=world, char=char, events=events)


def _season_boss(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    _action: SeasonBossAction,
    now: int,
    actor: str,
) -> StepResult:
    world, char, events = challenge(library, world, char, now, actor=actor)
    return StepResult(world=world, char=char, events=events)


ACCOUNT_HANDLERS: Final[dict[type, _AccountHandler]] = {
    LeagueEnterAction: _league,
    LeagueWithdrawAction: _league,
    SeasonBossAction: _season_boss,  # 5F-3：每帳號每天 3 次
}
"""算帳號的世界動作 → 處理（5F-4 循環賽報名、5F-3 賽季 Boss 挑戰）；和 :data:`HANDLERS` 不重疊
（測試檢查）。"""

HANDLERS: Final = _handlers()
"""世界動作種類 → 處理（5D-R1 取代 ``isinstance`` 串）；每種世界動作恰好一個（測試檢查）。
放在模組最後，處理函式都定義好了才建表。"""
