"""第二段（followup）規格與各 ``when`` 的檢查函式。"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.skills.constants import (
    COMPOSITE_KIND_ZH,
    COMPOSITE_MOVES,
    DELAYED_RELEASE_VALUES,
    DELAYED_SHAPES,
    FOLLOWUP_CENTERED,
    FOLLOWUP_FORBIDDEN,
    FOLLOWUP_SHAPES,
    GATHER_SHAPES,
    ON_KILL_SECOND_SHAPES,
)
from trpg.content.skills.effects import EffectSpec, ShapeSpec
from trpg.content.skills.specs import FollowupSpec


def _types(effects: tuple[EffectSpec, ...]) -> str:
    return "、".join(e.type for e in effects)


def _lone_move(effects: tuple[EffectSpec, ...], where: str) -> None:
    """``where`` 只能是一個施放者自身位移原語（:data:`COMPOSITE_MOVES`）。"""
    if len(effects) != 1 or effects[0].type not in COMPOSITE_MOVES:
        raise ValueError(
            f"複合技能的{where}只能有一個施放者自身位移原語（{'、'.join(COMPOSITE_MOVES)}），"
            f"收到 {_types(effects)}"
        )


def _no_forbidden(
    effects: tuple[EffectSpec, ...], where: str, allowed: tuple[str, ...] = ()
) -> None:
    bad = [e.type for e in effects if e.type in FOLLOWUP_FORBIDDEN and e.type not in allowed]
    if bad:
        raise ValueError(
            f"複合技能的{where}不能有位移、召喚、區域、陷阱等原語（不能套娃），"
            f"收到 {'、'.join(bad)}"
        )


def _second_shape(follow: FollowupSpec, shapes: tuple[str, ...]) -> None:
    """第二段的形狀在 ``shapes`` 內；以原點為中心的 ``cross``、``square3`` 必須 ``range: 0``。"""
    if follow.shape.type not in shapes:
        raise ValueError(f"followup 的形狀只能是 {'、'.join(shapes)}，收到 {follow.shape.type}")
    if follow.shape.type in FOLLOWUP_CENTERED and follow.shape.range != 0:
        raise ValueError(
            f"followup 的形狀 {follow.shape.type} 以第二段的原點為中心，range 必須是 0，"
            f"收到 {follow.shape.range}"
        )


def _needs_damage(effects: tuple[EffectSpec, ...], what: str) -> None:
    if not any(e.type == "damage" for e in effects):
        raise ValueError(f"「{what}」的第一段必須有傷害效果（damage），收到 {_types(effects)}")


def _check_after_move(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """位移 → 動作（3F-3a）：第一段是一個自身位移；第二段是以落點為原點的動作。"""
    _lone_move(effects, "位移段")
    _second_shape(f, FOLLOWUP_SHAPES)
    _no_forbidden(f.effects, "動作段")


def _check_after_action(
    effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec
) -> None:
    """動作 → 位移（打帶跑，3F-4a）：第一段是動作；第二段是一個自身位移（形狀照該原語）。"""
    _no_forbidden(effects, "第一段")
    _lone_move(f.effects, "第二段（位移）")


def _check_after_gather(effects: tuple[EffectSpec, ...], shape: ShapeSpec, f: FollowupSpec) -> None:
    """聚集 → 範圍打擊（3F-4a）：第一段只有一個 ``pull``（朝聚集點拉），形狀在
    :data:`GATHER_SHAPES`；第二段以聚集點為中心（``cross``／``square3``，射程與第一段相同，環形為
    0）。"""
    if len(effects) != 1 or effects[0].type != "pull":
        raise ValueError(f"聚集段只能有一個拉扯原語（pull），收到 {_types(effects)}")
    if shape.type not in GATHER_SHAPES:
        raise ValueError(f"聚集段的形狀只能是 {'、'.join(GATHER_SHAPES)}，收到 {shape.type}")
    if f.shape.type not in FOLLOWUP_CENTERED:
        raise ValueError(
            f"聚集後的打擊以聚集點為中心，形狀只能是 {'、'.join(FOLLOWUP_CENTERED)}，"
            f"收到 {f.shape.type}"
        )
    reach = shape.range if shape.type in FOLLOWUP_CENTERED else 0
    if f.shape.range != reach:
        raise ValueError(
            f"聚集後的打擊以聚集點為中心，range 必須與聚集段相同（{reach}），收到 {f.shape.range}"
        )
    _no_forbidden(f.effects, "第二段")


def _check_on_kill(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """擊殺 → 接下一段（3F-4a）：第一段是有傷害的動作；第二段是動作或位移（可以先位移再動作，
    例如衝鋒接傷害），從施放者的位置選目標。"""
    _no_forbidden(effects, "第一段")
    _needs_damage(effects, COMPOSITE_KIND_ZH["on_kill"])
    _second_shape(f, ON_KILL_SECOND_SHAPES)
    _no_forbidden(f.effects, "第二段", allowed=COMPOSITE_MOVES)


def _check_on_hit(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """命中 → 加碼段（3F-4a）：第一段是有傷害的動作；第二段是動作，自動對命中的同一個目標。"""
    _no_forbidden(effects, "第一段")
    _needs_damage(effects, COMPOSITE_KIND_ZH["on_hit"])
    _second_shape(f, FOLLOWUP_SHAPES)
    _no_forbidden(f.effects, "第二段")


def _check_delayed(effects: tuple[EffectSpec, ...], _shape: ShapeSpec, f: FollowupSpec) -> None:
    """延遲段（3F-4b）：第一段任何動作（可以有一個自身位移）；第二段是以施放者為中心的動作
    （:data:`DELAYED_SHAPES`），必須指定 ``release``。"""
    if f.release is None:
        raise ValueError(
            f"延遲段必須指定 release（{'、'.join(DELAYED_RELEASE_VALUES)}）：何時釋放第二段"
        )
    _no_forbidden(effects, "第一段", allowed=COMPOSITE_MOVES)
    _second_shape(f, DELAYED_SHAPES)
    _no_forbidden(f.effects, "延遲段")


_FOLLOWUP_CHECKS: dict[str, Callable[[tuple[EffectSpec, ...], ShapeSpec, FollowupSpec], None]] = {
    "after_move": _check_after_move,
    "after_action": _check_after_action,
    "after_gather": _check_after_gather,
    "on_kill": _check_on_kill,
    "on_hit": _check_on_hit,
    "delayed": _check_delayed,
}
"""``followup.when`` → 兩段的結構檢查（schema 層級；骨架規則由驗證器檢查）。"""
