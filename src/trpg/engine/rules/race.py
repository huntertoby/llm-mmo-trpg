"""種族的環境被動查詢（Phase 3R-2，``docs/design/07-角色成長.md`` 7.7；資料 ``races.yaml``）。

每一項被動由引擎的一個結算點讀取下面的查詢函式（規則的種類是封閉清單
:data:`trpg.content.races.PASSIVE_RULE_SPECS`），沒有種族的單位恆為「沒有被動」：

- ``sight_penalty_reduction``（人類）：:func:`sight_range_for`、:func:`concealed_limit_for`；
- ``sight_bonus_on_map_tag``（精靈）：:func:`sight_range_for`；
- ``detect_hidden_nearby``（狐族）：:func:`reveal_radius`（``combat.concealment_problem``、
  ``combat.advantage_sources``、``traps.detect_traps``、``traps.visible_traps``）；
- ``damage_taken_permille``（龍裔）：:func:`race_element_mods`（開戰時併進元素修正）；
- ``slip_immunity``／``free_move_on``（矮人、鱗族）：:func:`slip_immune`（``enter_surface``）；
- ``conduction_immunity``（晶能義體人）：:func:`conduction_immune`（``interactions`` 的導電）；
- ``knockback_reduction_at_hazard``（獸人）：:func:`hazard_push_reduction`（``push_distance``）；
- ``burn_immunity_on``（角魔）：:func:`burn_immune`（``interactions``／``turns`` 的表面燃燒）；
- ``weather_move_bonus``（海民）：:func:`weather_move_bonus`（``statuses.move_points_for_turn``）。

查詢只讀 ``Ruleset.races`` 與單位／戰鬥狀態，是確定性的純函式。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.content.library import Ruleset
from trpg.content.races import RacePassive
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Element, Surface

if TYPE_CHECKING:
    from trpg.content.battle import UnitTemplate

__all__ = [
    "burn_immune",
    "concealed_limit_for",
    "conduction_immune",
    "hazard_push_reduction",
    "passive_active",
    "passive_of",
    "race_element_mods",
    "reveal_radius",
    "sight_range_for",
    "slip_immune",
    "weather_move_bonus",
]

PERMILLE = 1000


def passive_of(rules: Ruleset, unit: UnitState, rule: str) -> RacePassive | None:
    """``unit`` 的環境被動，且規則為 ``rule``；沒有種族、種族不存在或規則不同時為 ``None``。"""
    if unit.race is None:
        return None
    try:
        passive = rules.race_def(unit.race).passive
    except KeyError:
        return None
    return passive if passive.rule == rule else None


def _ceil_share(amount: int, permille: int) -> int:
    """``amount`` 的 ``permille``‰，無條件進位（減免懲罰時對玩家有利）。"""
    return (amount * permille + PERMILLE - 1) // PERMILLE


def sight_range_for(state: BattleState, viewer: UnitState | None = None) -> int:
    """``viewer`` 的視線距離（曼哈頓）：``base_sight_range`` × 天氣倍率；人類的「明視」把天氣造成的
    縮減回復 ``permille``‰（進位），精靈的「林間視野」在 ``forest`` 地圖上 +1。``viewer`` 為
    ``None`` 時是不分單位的基準值。"""
    base = state.ruleset.core.base_sight_range
    weather = state.weather
    permille = PERMILLE if weather is None else weather.sight_range_permille
    result = base * permille // PERMILLE
    if viewer is None:
        return result
    clear = passive_of(state.ruleset, viewer, "sight_penalty_reduction")
    if (
        clear is not None
        and weather is not None
        and weather.id in (clear.weathers or ())
        and clear.permille
    ):
        result += _ceil_share(base - result, clear.permille)
    bonus = passive_of(state.ruleset, viewer, "sight_bonus_on_map_tag")
    if bonus is not None and set(bonus.map_tags or ()) & set(state.map_tags):
        result += bonus.amount or 0
    return result


def concealed_limit_for(state: BattleState, viewer: UnitState | None, default: int) -> int:
    """隱蔽目標可被選取的最遠距離。``default`` 是天氣覆寫後的值（夜晚較短）；人類的「明視」在夜晚
    把縮短的部分回復 ``permille``‰（進位）。"""
    weather = state.weather
    if viewer is None or weather is None:
        return default
    clear = passive_of(state.ruleset, viewer, "sight_penalty_reduction")
    if clear is None or not clear.permille or weather.id not in (clear.weathers or ()):
        return default
    normal = state.ruleset.core.concealed_ranged_max_distance
    return default + _ceil_share(max(0, normal - default), clear.permille)


def passive_active(state: BattleState, unit: UnitState) -> bool:
    """環境被動此刻有沒有作用（HUD 顯示用）：天氣型看目前天氣、地圖型看地圖標籤，其餘（地形、
    表面、位移類）是隨時待命，恆為真。"""
    if unit.race is None:
        return False
    passive = state.ruleset.race_def(unit.race).passive
    weather = None if state.weather is None else state.weather.id
    if passive.weathers is not None:
        return weather in passive.weathers
    if passive.map_tags is not None:
        return bool(set(passive.map_tags) & set(state.map_tags))
    return True


def reveal_radius(rules: Ruleset, unit: UnitState) -> int:
    """狐族「靈覺」：看得見這個距離內的敵方陷阱與隱蔽單位（沒有時 0）。"""
    passive = passive_of(rules, unit, "detect_hidden_nearby")
    return 0 if passive is None else passive.radius or 0


def race_element_mods(rules: Ruleset, template: UnitTemplate) -> dict[Element, int]:
    """單位的元素修正：範本的 ``element_mods`` 加上種族被動的元素減傷（龍裔火焰 −200‰ ＝ 抗性
    20%；開戰時併入，之後同一般元素抗性結算）。"""
    mods = dict(template.element_mods)
    if template.race is None:
        return mods
    try:
        passive = rules.race_def(template.race).passive
    except KeyError:
        return mods
    if passive.rule == "damage_taken_permille" and passive.element is not None:
        mods[passive.element] = mods.get(passive.element, 0) + (passive.permille or 0)
    return mods


def slip_immune(rules: Ruleset, unit: UnitState, surface: Surface) -> bool:
    """在 ``surface`` 上不會滑倒：矮人（冰）；鱗族在水與冰面上移動不花額外點數、不滑倒。"""
    for rule in ("slip_immunity", "free_move_on"):
        passive = passive_of(rules, unit, rule)
        if passive is not None and surface in (passive.surfaces or ()):
            return True
    return False


def conduction_immune(state: BattleState, unit: UnitState) -> bool:
    """站在水上時不會被雷電導電（晶能義體人「絕緣」；只看腳下的表面）。"""
    passive = passive_of(state.ruleset, unit, "conduction_immunity")
    return passive is not None and state.tile(*unit.xy).surface in (passive.surfaces or ())


def burn_immune(rules: Ruleset, unit: UnitState, surface: Surface) -> bool:
    """走在 ``surface`` 上不會因此燃燒（角魔「炎膚」；只擋表面造成的燃燒）。"""
    passive = passive_of(rules, unit, "burn_immunity_on")
    return passive is not None and surface in (passive.surfaces or ())


def weather_move_bonus(rules: Ruleset, unit: UnitState, weather_id: str | None) -> int:
    """指定天氣下回合開始的移動點數加值（海民「雨中海步」：下雨 +1）。"""
    passive = passive_of(rules, unit, "weather_move_bonus")
    if passive is None or weather_id is None or weather_id not in (passive.weathers or ()):
        return 0
    return passive.amount or 0


def hazard_push_reduction(
    state: BattleState, unit: UnitState, direction: tuple[int, int], distance: int
) -> int:
    """獸人「沉穩重心」：被 **推** 時，若推的路徑上（含落點，最多 ``distance`` 格）有岩漿或深淵，
    推的距離少 ``amount`` 格（回傳實際的減少量，不會讓距離低於 0；拉與傳送不呼叫這個函式）。"""
    passive = passive_of(state.ruleset, unit, "knockback_reduction_at_hazard")
    if passive is None or distance <= 0:
        return 0
    hazards = set(passive.terrain or ())
    x, y = unit.xy
    dx, dy = direction
    for step in range(1, distance + 1):
        nx, ny = x + dx * step, y + dy * step
        if not state.in_bounds(nx, ny):
            break
        if state.tile(nx, ny).terrain in hazards:
            return min(distance, passive.amount or 0)
    return 0
