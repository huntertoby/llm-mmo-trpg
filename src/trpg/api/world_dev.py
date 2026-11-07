"""大世界的開發用戰鬥入口（Phase 6F-3）：Boss 戰直接開打，給實戰截圖與驗收用。

- 只在開發模式（``config/server.toml`` 的 ``dev_mode``，``dev_router`` 才掛）**而且**環境變數
  ``TRPG_DEV_ROUTES=1`` 時可用，否則 404（同 roguelite 的 ``dev-advance``）。前端只在 ``?dev=1``
  顯示按鈕。
- **不碰世界**：用角色存檔的複本（換到 Boss 地點、可選等級）照正式的
  :func:`~trpg.world.battle.prepare_battle` 組出戰鬥設定，在戰鬥工作階段表開一場；不寫世界
  日誌、角色存檔，打完也不回寫（同循環賽重播，不登記成角色進行中的戰鬥）。所以正式遊戲的主線
  限制（霧牆、世界事件）照舊，一般玩家碰不到。
- 戰鬥本身就是正式的大世界 Boss 戰（同一個陣容、Boss 地圖、階段與蓄力招），播放走既有戰鬥畫面。
- ``ai_until``（截圖用）：先讓效用 AI 連主角一起代打，停在指定的那一刻、輪到主角時，再交給畫面
  （``charge``＝Boss 蓄力中，主角結束回合就看得到 Boss 放大招；``last``＝敵人只剩一名而且 HP 不到
  一成半，下一擊多半就是最後一擊）。代打的步驟用存檔重播的方式還原（同 roguelite 讀檔），
  結果和照順序打
  完全一樣。
- QK-9b（截圖用，同樣不碰世界）：``facing``＝開場朝向——用既有的「指定起始位置」把主角放在地圖
  中間、第一個敵人放在那個方向（近戰相鄰、遠程隔一格），其他敵人在更遠的同一側、隊友在主角背後，
  開場朝向照正式規則（面向敵方重心）就是指定的方向（另用既有的 ``first_team`` 讓我方先動，
  免得敵人先走過來把主角打得轉身）；``opening``＝開場就讓主角放出召喚物
  （``summon``）或變身成形態（``form``）——輪到主角時照合法動作的順序找第一個做得到的技能放出（落點離主角近的先試），
  再讓 AI 代打到又輪到主角。兩者都只是「初始設定＋動作列表」，重播結果一樣，不改任何規則與數值。
- :func:`dev_teleport`（QK-9b）：把角色存檔直接搬到某區的城鎮（拍 NPC 用；主線限制不管）。這個
  **會改角色存檔、不寫世界日誌**（開發用角色之後的世界日誌重播會對不上），只在開發入口用。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from trpg.api.sessions import BattleSession, StepRecord
from trpg.api.world import WorldStore
from trpg.engine.actions import Step, UseSkill
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle, legal_actions
from trpg.engine.results import Pending
from trpg.engine.rules.facing import FACING_VECTORS
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.runner import accept_all, advance, apply_step
from trpg.engine.setup import BattleSetup, BattleSetupError
from trpg.engine.state import BattleState, Facing
from trpg.shared.types import Team
from trpg.world.battle import PreparedBattle, prepare_battle
from trpg.world.common import max_hp, max_mana, world_map_of
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.solutions import make_encounter
from trpg.world.state import CharacterState
from trpg.world.town import with_visited_town

__all__ = ["DevBattle", "dev_boss_battle", "dev_teleport"]

MAX_DEV_LEVEL = 20
"""開發入口可指定的最高等級（只改複本）。"""

type AiUntil = Literal["charge", "last"]
_LOW_PERMILLE = 150


def _hero_turn(state: BattleState) -> bool:
    active = state.active_unit
    return (
        active is not None
        and state.units[active].team is Team.ALLY
        and active == min(u.id for u in state.units.values() if u.team is Team.ALLY)
    )


def _boss_charging(state: BattleState) -> bool:
    return any(
        u.alive and "boss" in u.tags and u.get_status("charging") is not None
        for u in state.units.values()
        if u.team is Team.ENEMY
    )


def _last_foe_low(state: BattleState) -> bool:
    foes = [u for u in state.living_units() if u.team is Team.ENEMY and not u.is_summon]
    return len(foes) == 1 and foes[0].hp * 1000 <= _LOW_PERMILLE * foes[0].max_hp


_STOPS: dict[str, Callable[[BattleState], bool]] = {"charge": _boss_charging, "last": _last_foe_low}


@dataclass(frozen=True)
class DevBattle:
    title_zh: str
    battle: BattleSession
    records: list[StepRecord]


type Opening = Literal["summon", "form"]
_OPENING_ZH: dict[str, str] = {"summon": "放出召喚物", "form": "變身成形態"}
_SPREAD = (0, -1, 1, -2, 2, -3, 3)
"""排開時沿垂直方向的位移順序（確定性）。"""
_BESIDE = (2, -2, 3, -3)
"""隊友站在主角兩側隔一格（往前走時不擋主角的射線）。"""


def _has_summon(state: BattleState, hero: str) -> bool:
    return any(u.alive and u.owner_id == hero for u in state.units.values())


def _in_form(state: BattleState, hero: str) -> bool:
    return state.units[hero].form is not None  # type: ignore[index]


_OPENED: dict[str, Callable[[BattleState, str], bool]] = {"summon": _has_summon, "form": _in_form}


def _offsets(facing: Facing, foes: int, friends: int, gap: int) -> list[tuple[int, int]]:
    """主角在 (0, 0)：隊友在主角兩側隔一格排開，第一個敵人在 ``facing`` 方向 ``gap`` 格，
    其他敵人在更遠
    的同一側排開。回傳的順序：主角、其他隊友、敵人。"""
    dx, dy = FACING_VECTORS[facing]
    px, py = -dy, dx
    out = [(0, 0)]
    for j in range(friends - 1):
        o, r = _BESIDE[j % len(_BESIDE)], j // len(_BESIDE)
        out.append((-dx * r + px * o, -dy * r + py * o))
    out.append((dx * gap, dy * gap))
    for k in range(foes - 1):
        o, r = _SPREAD[k % len(_SPREAD)], gap + 2 + k // len(_SPREAD)
        out.append((dx * r + px * o, dy * r + py * o))
    return out


def _face_setup(setup: BattleSetup, seed: int, facing: Facing) -> BattleSetup:
    """開場朝向 ``facing`` 的起始位置（只用既有的 ``UnitSpawn.position``；朝向照正式規則算）。
    錨點從地圖中間往外找，第一個全部站得住、開場主角朝向正確的就用。"""
    allies = [i for i, u in enumerate(setup.units) if u.team is Team.ALLY]
    foes = [i for i, u in enumerate(setup.units) if u.team is Team.ENEMY]
    reach = setup.units[allies[0]].weapon.range
    offsets = _offsets(facing, len(foes), len(allies), 1 if reach <= 1 else min(reach, 2))
    probe = begin_battle(setup, seed).state
    w, h = probe.width, probe.height
    anchors = sorted(
        ((x, y) for y in range(h) for x in range(w)),
        key=lambda c: (abs(2 * c[0] - w) + abs(2 * c[1] - h), c[1], c[0]),
    )
    for ax, ay in anchors:
        cells = [(ax + ox, ay + oy) for ox, oy in offsets]
        if not all(
            probe.in_bounds(*c) and is_standable(probe, c) and not is_deadly(probe, c)
            for c in cells
        ):
            continue
        units = list(setup.units)
        for i, cell in zip((*allies, *foes), cells, strict=True):
            units[i] = units[i].model_copy(update={"position": cell})
        # 我方先動（既有的 ``first_team``）：敵人還沒走過來、主角還沒被打得轉身就輪到主角
        candidate = setup.model_copy(update={"units": tuple(units), "first_team": Team.ALLY})
        try:
            state = begin_battle(candidate, seed).state
        except BattleSetupError:
            continue
        hero = min(u.id for u in state.units.values() if u.team is Team.ALLY)
        if state.units[hero].facing == facing:
            return candidate
    raise WorldActionError(f"這張地圖排不出開場朝{facing}的位置（換地點再試）")


def _through(state: BattleState, step: Step) -> tuple[BattleState, list[Step]]:
    """結算一步，暫停時照預設（:func:`accept_all`）回答到沒有暫停。"""
    result = apply_step(state, step)
    steps: list[Step] = [step]
    while result.pending is not None and not result.state.ended:
        decision = accept_all(result.state, result.pending)
        result = apply_step(result.state, decision)
        steps.append(decision)
    return result.state, steps


def _opening_steps(
    library_ai: UtilityAI, setup: BattleSetup, seed: int, opening: Opening
) -> list[Step]:
    """AI 代打到輪到主角 → 照合法動作的順序，第一個能放出召喚物／變成形態的技能 → 再代打到
    輪到主角。"""
    opened = begin_battle(setup, seed)
    policy = CommandedAI(library_ai, {})
    turn = _hero_stop
    state, _, steps = advance(opened.state, opened.pending, policy, stop=turn)
    if state.ended or state.active_unit is None:
        raise WorldActionError("還沒輪到主角戰鬥就結束了（換等級再試）")
    hero = state.active_unit
    hx, hy = state.units[hero].xy
    casts = [a for a in legal_actions(state) if isinstance(a, UseSkill)]
    # 落點離主角近的先試（召喚物放在主角旁邊，截圖看得到）；一樣近照合法動作的順序（sorted 穩定）
    casts.sort(
        key=lambda a: (
            0 if a.target_pos is None else abs(a.target_pos.x - hx) + abs(a.target_pos.y - hy)
        )
    )
    for action in casts:
        after, cast = _through(state, action)
        if _OPENED[opening](after, hero):
            steps += cast
            if not after.ended and not turn(after, None):
                after, _, more = advance(after, None, policy, stop=turn)
                steps += more
            return steps
    raise WorldActionError(f"主角沒有能{_OPENING_ZH[opening]}的技能（換角色或技能）")


def _hero_stop(state: BattleState, pending: Pending | None) -> bool:
    return pending is None and _hero_turn(state)


def dev_boss_battle(
    store: WorldStore,
    character_id: str,
    *,
    location: str,
    region: str | None = None,
    level: int | None = None,
    ai_until: AiUntil | None = None,
    facing: Facing | None = None,
    opening: Opening | None = None,
) -> DevBattle:
    """``location``（``region`` 省略＝角色所在區）的遭遇直接開打；``level``＝複本的等級（省略＝照
    角色）；``facing``／``opening`` 見模組說明（QK-9b）。地點不存在、沒有遭遇（城鎮）或角色正在
    戰鬥時拋 :class:`WorldActionError`。"""
    if ai_until is not None and opening is not None:
        raise WorldActionError("ai_until 與 opening 只能選一個")
    with store.lock:
        prepared, title = _prepare(store, character_id, location, region, level)
        setup = prepared.setup
        if facing is not None:
            setup = _face_setup(setup, prepared.seed, facing)
        if ai_until is None and opening is None:
            battle, records = store.battles.open(setup, prepared.seed)
            return DevBattle(title_zh=title, battle=battle, records=records)
        ai = UtilityAI(store.library.ai_profiles)
        if opening is not None:
            steps = _opening_steps(ai, setup, prepared.seed, opening)
        else:
            assert ai_until is not None
            steps = _rehearse(ai, setup, prepared.seed, ai_until)
        battle, records = store.battles.open(setup, prepared.seed, restore=(steps, []))
        return DevBattle(title_zh=title, battle=battle, records=records)


def _rehearse(ai: UtilityAI, setup: BattleSetup, seed: int, ai_until: AiUntil) -> list[Step]:
    want = _STOPS[ai_until]
    opening = begin_battle(setup, seed)
    state, _, steps = advance(
        opening.state,
        opening.pending,
        CommandedAI(ai, {}),
        stop=lambda st, pending: pending is None and _hero_turn(st) and want(st),
    )
    if state.ended:
        raise WorldActionError(f"AI 代打到結束都沒有出現「{ai_until}」的時刻（換等級再試）")
    return steps


def _prepare(
    store: WorldStore, character_id: str, location: str, region: str | None, level: int | None
) -> tuple[PreparedBattle, str]:
    synced = store.sync(character_id)
    if synced.battle is not None:
        raise WorldActionError("戰鬥進行中，先打完這場")
    char = synced.char
    where = char.region if region is None else region
    library = store.library
    target = world_map_of(library, where).location_by_id().get(location)
    if target is None:
        raise WorldActionError(f"{where} 沒有地點 {location}")
    if not target.battle_maps:
        raise WorldActionError(f"{target.name_zh}沒有戰鬥（城鎮或傳送點）")
    copy = char.model_copy(
        update={"region": where, "location": location, "field": None, "field_visit": None}
    )
    if level is not None:
        copy = copy.model_copy(update={"level": max(1, min(MAX_DEV_LEVEL, level))})
    copy = copy.model_copy(
        update={"hp": max_hp(library, copy), "mana": max_mana(library, copy), "fatigued": False}
    )
    encounter, copy = make_encounter(library, synced.world, copy, target, synced.now)
    copy = copy.model_copy(update={"pending_encounter": encounter})
    return prepare_battle(library, copy), f"開發：{target.name_zh}"


def dev_teleport(store: WorldStore, character_id: str, region: str) -> CharacterState:
    """開發用（QK-9b）：角色直接搬到 ``region`` 的城鎮（同正式傳送的結果：城鎮、去過的小鎮），
    不管主線限制與「去過沒有」。**直接改角色存檔、不寫世界日誌**；戰鬥或遭遇中不行。"""
    with store.lock:
        synced = store.sync(character_id)
        char = synced.char
        if synced.battle is not None or char.pending_encounter is not None:
            raise WorldActionError("戰鬥或遭遇中不能傳送")
        try:
            town = world_map_of(store.library, region).town
        except WorldError as exc:
            raise WorldActionError(str(exc)) from exc
        moved = char.model_copy(update={"region": region, "location": town, "camped_at": None})
        moved = with_visited_town(moved, region)
        store._save_char(moved)  # 開發入口：刻意不寫世界日誌
        return moved
