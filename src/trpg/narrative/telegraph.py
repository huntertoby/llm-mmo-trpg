"""環境預告的繁體中文描述（Phase 3-4b）：把 :class:`~trpg.engine.environment.TelegraphChange`
與預告中的地圖事件轉成一行文字，給網頁側欄與格子上的說明用。"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.maps import MapEvent, SpawnUnitsEvent
from trpg.engine.environment import TelegraphChange
from trpg.engine.state import BattleState
from trpg.narrative.events import xy_text
from trpg.shared.types import Pos, Surface

__all__ = ["change_text", "upcoming_text"]


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


_CHANGE_TEXT: dict[str, Callable[[BattleState, TelegraphChange, Callable[[str], str]], str]] = {
    "surface": _surface,
    "terrain": _terrain,
    "object_destroyed": _destroyed,
    "object_ignited": _ignited,
    "object_exploded": _exploded,
    "unit_spawned": _spawned,
    "unit_damaged": _damaged,
    "unit_downed": _downed,
}


def change_text(
    state: BattleState, change: TelegraphChange, template_name: Callable[[str], str] = str
) -> str:
    """一項預告變化的一行文字。``template_name`` 把單位範本 ID 轉成中文名（援軍用）。"""
    return _CHANGE_TEXT[change.kind](state, change, template_name)


def upcoming_text(event: MapEvent, template_name: Callable[[str], str] = str) -> str:
    """再下一輪結束時的地圖事件（提前一輪預告）的一行文字。"""
    if isinstance(event, SpawnUnitsEvent):
        names = "、".join(template_name(u.template) for u in event.units)
        return f"第 {event.round} 輪結束時援軍出現：{names}"
    where = "、".join(xy_text(Pos(x=x, y=y)) for x, y in event.positions())
    return f"第 {event.round} 輪結束時地形改變：{where}"
