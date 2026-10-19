"""環境預告的繁體中文描述（Phase 3-4b）：把 :class:`~trpg.engine.environment.TelegraphChange`
與預告中的地圖事件轉成一行文字，給網頁側欄與格子上的說明用。"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.maps import MapEvent, SpawnUnitsEvent
from trpg.engine.environment import TelegraphBomb, TelegraphChange
from trpg.engine.state import BattleState
from trpg.narrative.events import DIRECTION_TEXT, cells_text, xy_text
from trpg.shared.types import Pos, Surface

__all__ = ["bomb_text", "change_text", "upcoming_text"]


def _surface_name(value: str | None) -> str:
    return "無" if value is None or value == Surface.NONE.value else Surface(value).display_name


def _terrain_name(state: BattleState, value: str | None) -> str:
    terrain_id, _, height = (value or "").partition(":")
    return f"{state.ruleset.terrain_def(terrain_id).name_zh}（高度 {height}）"


def _object_name(state: BattleState, change: TelegraphChange) -> str:
    obj = None if change.object_id is None else state.objects.get(change.object_id)
    return "物件" if obj is None else state.ruleset.object_def(obj.kind).name_zh


def _unit_name(state: BattleState, change: TelegraphChange) -> str:
    unit = None if change.unit_id is None else state.units.get(change.unit_id)
    return "單位" if unit is None else unit.name_zh


def _where(change: TelegraphChange) -> str:
    return "" if change.pos is None else f" {xy_text(change.pos)}"


def _surface(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return f"表面變化{_where(c)}：{_surface_name(c.before)} → {_surface_name(c.after)}"


def _terrain(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return (
        f"地形變化{_where(c)}：{_terrain_name(state, c.before)} → {_terrain_name(state, c.after)}"
    )


def _destroyed(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return f"{_object_name(state, c)}{_where(c)} 將被摧毀"


def _ignited(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return f"{_object_name(state, c)}{_where(c)} 將被點燃"


def _exploded(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return f"{_object_name(state, c)}{_where(c)} 將爆炸"


def _spawned(state: BattleState, c: TelegraphChange, template_name: Callable[[str], str]) -> str:
    return f"援軍 {template_name(c.after or '')}{_where(c)} 將出現"


def _damaged(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return f"{_unit_name(state, c)}{_where(c)} 將受到 {c.amount or 0} 點傷害"


def _downed(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return f"{_unit_name(state, c)} 將倒下"


def _zone_name(state: BattleState, c: TelegraphChange) -> str:
    try:
        return state.ruleset.skill_def(c.after or "").name_zh
    except KeyError:
        return "區域"


_ZONE_EXPIRY = {
    "timeout": "時間到了",
    "owner_gone": "施放者離場",
    "limit": "超過上限",
    "blocked": "前方都是牆壁或地圖邊緣",
}


def _zone_moved(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    direction = DIRECTION_TEXT.get(c.before or "", c.before or "")
    return f"「{_zone_name(state, c)}」區域將向{direction}前進到 {cells_text(c.tiles)}"


def _zone_expired(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    why = _ZONE_EXPIRY.get(c.before or "", c.before or "")
    return f"「{_zone_name(state, c)}」區域將消失（{why}）"


def _bomb_exploded(state: BattleState, c: TelegraphChange, _t: Callable[[str], str]) -> str:
    return (
        f"{_unit_name(state, c)} 身上的定時炸彈將在{_where(c)} 爆炸"
        f"（半徑 {c.amount or 0} 格，{cells_text(c.tiles)}）"
    )


_CHANGE_TEXT: dict[str, Callable[[BattleState, TelegraphChange, Callable[[str], str]], str]] = {
    "surface": _surface,
    "terrain": _terrain,
    "object_destroyed": _destroyed,
    "object_ignited": _ignited,
    "object_exploded": _exploded,
    "unit_spawned": _spawned,
    "unit_damaged": _damaged,
    "unit_downed": _downed,
    "zone_moved": _zone_moved,
    "zone_expired": _zone_expired,
    "bomb_exploded": _bomb_exploded,
}


def change_text(
    state: BattleState, change: TelegraphChange, template_name: Callable[[str], str] = str
) -> str:
    """一項預告變化的一行文字。``template_name`` 把單位範本 ID 轉成中文名（援軍用）。"""
    return _CHANGE_TEXT[change.kind](state, change, template_name)


def bomb_text(state: BattleState, bomb: TelegraphBomb) -> str:
    """帶著定時炸彈的單位的一行文字（倒數與爆炸範圍；Phase 3D-8b）。"""
    unit = state.units.get(bomb.unit_id)
    name = bomb.unit_id if unit is None else unit.name_zh
    when = "下一次環境回合就會爆炸" if bomb.explodes else f"還要 {bomb.remaining} 次環境回合爆炸"
    return f"{name} 身上的定時炸彈{when}（半徑 {bomb.radius} 格）"


def upcoming_text(event: MapEvent, template_name: Callable[[str], str] = str) -> str:
    """再下一輪結束時的地圖事件（提前一輪預告）的一行文字。"""
    if isinstance(event, SpawnUnitsEvent):
        names = "、".join(template_name(u.template) for u in event.units)
        return f"第 {event.round} 輪結束時援軍出現：{names}"
    where = "、".join(xy_text(Pos(x=x, y=y)) for x, y in event.positions())
    return f"第 {event.round} 輪結束時地形改變：{where}"
