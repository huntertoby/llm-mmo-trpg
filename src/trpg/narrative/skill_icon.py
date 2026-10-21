"""組裝式技能圖示的資料（Phase 3-17，``docs/art/移植需求.md`` 5.3）：技能定義 → :class:`SkillIcon`。

圖示本身（Canvas）在前端；這裡只做「資料 → 部件清單」的純函式推導：

- :func:`icon_of` 吃技能定義的 JSON（``content/skills/*.yaml`` 的同一份欄位，**可以缺欄位**，所以
  技能工坊組到一半的草稿也能用），永遠不丟例外：欄位缺漏、型別不對或不認得的值都退回預設；
- :func:`skill_icon` 是 :class:`~trpg.content.skills.SkillDef` 的便利包裝。

只新增顯示用資料，不影響引擎。確定性：只看輸入，不依賴 ``set`` 順序。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from trpg.content.skills import SkillDef

__all__ = [
    "ELEMENT_IDS",
    "IconCondition",
    "IconCost",
    "IconEffect",
    "IconModifier",
    "IconModifierChange",
    "IconSegment",
    "SkillIcon",
    "icon_of",
    "skill_icon",
]

ELEMENT_IDS: tuple[str, ...] = (
    "physical",
    "fire",
    "ice",
    "lightning",
    "poison",
    "wind",
    "earth",
    "holy",
    "shadow",
)
"""元素代碼（``trpg.shared.types.Element``）；``tags`` 裡出現這些字就當成技能的元素。"""

type IconCost = Literal["source", "gamble", "self", "stacks", "once", "delay"]
"""特殊代價（法力與冷卻每招都有，不列）：源力、賭注、自傷、消耗層數、每場一次、延遲。"""

_KINDS = ("active", "reaction", "passive", "stance", "modifier")
_RARITIES = ("common", "rare", "epic", "legendary")
_WEAPON_REQS = ("melee", "ranged", "focus", "any")
_MAX_EFFECTS_PER_SEGMENT = 12


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class IconEffect(_Model):
    """一個效果：原語代碼，附加狀態／表面／條件時帶上對應代碼。"""

    type: str
    status: str | None = None
    surface: str | None = None
    condition: str | None = None


class IconSegment(_Model):
    """技能的一段（複合技能有兩段）。"""

    skeleton: str | None
    shape_id: str | None
    """``skill_shapes.yaml`` 的形狀 id；草稿還沒選形狀時 ``None``。"""
    range: int | None
    """形狀射程；武器射程（``weapon``）或沒有射程為 ``None``。"""
    elements: tuple[str, ...] = ()
    """這一段自己效果上的元素（第二段與第一段不同時前端換底色）；沒有為空。"""
    effects: tuple[IconEffect, ...]


class IconCondition(_Model):
    id: str
    status: str | None = None
    """``target_has_status`` 的狀態代碼。"""


class IconModifierChange(_Model):
    key: str
    value: JsonValue = None


class IconModifier(_Model):
    applies_to: dict[str, JsonValue]
    """被改造的對象（``actions``／``skill_tags``／``all_attacks``／``all_skills``，只列有填的）。"""
    changes: tuple[IconModifierChange, ...]


class SkillIcon(_Model):
    """組裝式圖示需要的全部欄位（由 :func:`icon_of` 推導）。

    ``kind``、``rarity``、``weapon_req`` 為技能定義的代碼；草稿缺漏時退回
    ``active``／``common``／``any``。``partial`` 為真表示這是組到一半的草稿（沒有形狀或沒有效果），
    前端據此把還沒決定的部件畫成「（未選）」。
    """

    kind: str
    rarity: str
    elements: tuple[str, ...]
    """依序：效果（含複合第二段）上的 ``element`` → 沒有時取 ``tags`` 裡的第一個元素；可為空。"""
    weapon_req: str
    segments: tuple[IconSegment, ...]
    """1 段；有 ``followup`` 時 2 段。"""
    link: str | None
    """複合技能的接續種類（``followup.when``）。"""
    condition: IconCondition | None
    costs: tuple[IconCost, ...]
    trigger: str | None
    """被動的 ``trigger.event`` 或反應的 ``reaction.event``。"""
    modifier: IconModifier | None
    partial: bool = False


# ---- 容錯的取值 ----------------------------------------------------------------------------


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _seq(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value != "" else None


def _choice(value: Any, allowed: tuple[str, ...], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _enum_text(value: Any) -> str | None:
    """字串，或 ``StrEnum`` 之類帶 ``value`` 的東西（``Surface``）。"""
    if isinstance(value, str):
        return value or None
    inner = getattr(value, "value", None)
    return inner if isinstance(inner, str) and inner else None


def _effect(raw: Any) -> IconEffect | None:
    e = _map(raw)
    kind = _text(e.get("type"))
    if kind is None:
        return None
    cond = _text(_map(e.get("condition")).get("type"))
    return IconEffect(
        type=kind,
        status=_text(e.get("status")),
        surface=_enum_text(e.get("surface")),
        condition=cond,
    )


def _effects(raw: Any) -> tuple[IconEffect, ...]:
    out = (_effect(e) for e in _seq(raw)[:_MAX_EFFECTS_PER_SEGMENT])
    return tuple(e for e in out if e is not None)


def _elements_of(raw_effects: Any) -> list[str]:
    found: list[str] = []
    for raw in _seq(raw_effects):
        el = _enum_text(_map(raw).get("element"))
        if el is not None and el not in found:
            found.append(el)
    return found


def _segment(raw: Any, *, with_elements: bool) -> IconSegment:
    d = _map(raw)
    shape = _map(d.get("shape"))
    rng = shape.get("range")
    return IconSegment(
        skeleton=_text(d.get("skeleton")),
        shape_id=_text(shape.get("type")),
        range=rng if isinstance(rng, int) and not isinstance(rng, bool) else None,
        elements=tuple(_elements_of(d.get("effects"))) if with_elements else (),
        effects=_effects(d.get("effects")),
    )


def _condition(skill: Mapping[str, Any], followup: Mapping[str, Any]) -> IconCondition | None:
    """技能本身的條件；沒有時取第一個效果（含複合第二段）上的條件。"""
    cond = _map(skill.get("condition"))
    if _text(cond.get("type")) is None:
        cond = next(
            (
                c
                for raw in [*_seq(skill.get("effects")), *_seq(followup.get("effects"))]
                if _text((c := _map(_map(raw).get("condition"))).get("type")) is not None
            ),
            {},
        )
    cid = _text(cond.get("type"))
    if cid is None:
        return None
    return IconCondition(id=cid, status=_text(cond.get("status")))


def _costs(skill: Mapping[str, Any], all_effects: list[Any]) -> tuple[IconCost, ...]:
    cost = _map(skill.get("cost"))
    followup = _map(skill.get("followup"))
    out: list[IconCost] = []
    if cost.get("source"):
        out.append("source")
    if any(_map(e).get("type") == "gamble" for e in all_effects):
        out.append("gamble")
    if cost.get("on_miss") or cost.get("self_status"):
        out.append("self")
    if cost.get("stacks"):
        out.append("stacks")
    if cost.get("uses_per_battle") or skill.get("activation") == "battle":
        out.append("once")
    if skill.get("activation") == "timed" or followup.get("when") == "delayed":
        out.append("delay")
    return tuple(out)


def _changes(modifiers: list[Any]) -> tuple[IconModifierChange, ...]:
    out: list[IconModifierChange] = []
    for m in modifiers:
        for key, value in _map(_map(m).get("change")).items():
            if value is None or value is False or value in ([], ()):
                continue
            out.append(IconModifierChange(key=str(key), value=_json(value)))
    return tuple(out)


def _json(value: Any) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    return _enum_text(value) or str(value)


def _modifier(modifiers: list[Any]) -> IconModifier | None:
    if not modifiers:
        return None
    applies = {str(k): _json(v) for k, v in _map(_map(modifiers[0]).get("applies_to")).items() if v}
    return IconModifier(applies_to=applies, changes=_changes(modifiers))


def _trigger(skill: Mapping[str, Any], kind: str) -> str | None:
    if kind == "reaction":
        return _text(_map(skill.get("reaction")).get("event"))
    if kind == "passive":
        return _text(_map(skill.get("trigger")).get("event"))
    return None


def icon_of(skill: Mapping[str, Any]) -> SkillIcon:
    """技能定義 JSON（可以缺欄位）→ 圖示資料；永遠回傳，不認得的欄位退回預設。"""
    kind = _choice(skill.get("kind"), _KINDS, "active")
    followup_raw = skill.get("followup")
    followup = _map(followup_raw)
    has_followup = isinstance(followup_raw, Mapping) and bool(followup)
    segments = [_segment(skill, with_elements=True)]
    if has_followup:
        segments.append(_segment(followup, with_elements=True))
    all_effects = [*_seq(skill.get("effects")), *_seq(followup.get("effects"))]
    elements = _elements_of(all_effects)
    if not elements:
        tags = _seq(skill.get("tags"))
        elements = [t for t in tags if isinstance(t, str) and t in ELEMENT_IDS][:1]
    modifiers = _seq(skill.get("modifiers"))
    partial = segments[0].shape_id is None or not segments[0].effects
    return SkillIcon(
        kind=kind,
        rarity=_choice(skill.get("rarity"), _RARITIES, "common"),
        elements=tuple(elements),
        weapon_req=_choice(skill.get("weapon_req"), _WEAPON_REQS, "any"),
        segments=tuple(segments),
        link=(_text(followup.get("when")) or "after_move") if has_followup else None,
        condition=_condition(skill, followup),
        costs=_costs(skill, all_effects),
        trigger=_trigger(skill, kind),
        modifier=_modifier(modifiers),
        partial=partial and kind != "modifier" and not modifiers,
    )


def skill_icon(skill: SkillDef) -> SkillIcon:
    """:class:`SkillDef` 的圖示資料。"""
    return icon_of(skill.model_dump(mode="json"))
