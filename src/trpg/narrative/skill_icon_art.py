"""Q 版技能主圖的推導（Phase QI-2a，需求 ``docs/art/Q版小圖示-技能圖示移植需求.md`` 3.3）。

技能定義（可以缺欄位的 JSON）→ :class:`IconArt`：主圖畫哪個道具 ``prop``、怎麼出手 ``motion``、效果
記號 ``act`` 與染色 ``tint``、閃光染色 ``spark``。規則照美術的參考實作
``docs/art/sample/tools/qskills_derive.py``；規則查的表在 ``content/skill_icon_art.yaml``
（:class:`~trpg.content.skill_icon_art.IconArtTable`）。

和參考實作不同的地方（都是為了「永遠不丟例外、結果和輸入的鍵順序無關」）：

- 輸入一律容錯取值，型別不對當作沒有；**值是 ``None`` 的鍵當作沒有**（``SkillDef.model_dump`` 會帶出
  沒填的欄位）；
- 修正技的染色照**表的列順序**找第一個有填的改動鍵（參考實作照輸入的鍵順序；目前資料兩者相同）；
- ``icon_prop`` 插在道具第 2、3 列之間，而且值要在允許清單內才用（D3：清單外退回推導，不報錯）。

只影響圖示：不進引擎、規則包、存檔與 LLM prompt。確定性：表一律依序比對，不依賴 ``set`` 順序。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.skill_icon_art import IconArtTable
from trpg.content.skill_icon_props import IconPropTable

if TYPE_CHECKING:
    from trpg.content.library import ContentLibrary

__all__ = [
    "IconArt",
    "IconArtRules",
    "default_icon_art_rules",
    "derive_art",
    "icon_art_rules",
]

_ELEMENT_IDS: tuple[str, ...] = (
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


class IconArt(BaseModel):
    """Q 版主圖的代碼（前端只畫，不推導）。代碼表見 ``content/skill_icon_art.yaml`` 檔頭。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prop: str
    """道具：``w:<種類>[/<形制>]``、``el:<元素>``、``summon:<組>``、``form:<化身>`` 或 ``none``。"""
    motion: str
    """出手（9 種）。"""
    act: str
    """效果記號（23 種）。"""
    tint: str | None
    """記號的染色；沒有為 ``None``。"""
    spark: str | None
    """閃光的染色：``variants`` 裡第一個帶元素的變奏的元素；沒有為 ``None``。"""


# ---- 容錯的取值（skill_icon.py 共用） ---------------------------------------------------------


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _seq(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value != "" else None


def _enum_text(value: Any) -> str | None:
    """字串，或 ``StrEnum`` 之類帶 ``value`` 的東西（``Surface``）。"""
    if isinstance(value, str):
        return value or None
    inner = getattr(value, "value", None)
    return inner if isinstance(inner, str) and inner else None


def _texts(value: Any) -> list[str]:
    return [t for t in _seq(value) if isinstance(t, str) and t]


def _filled(value: Any) -> bool:
    """修正改動的值算不算「有填」：``None``、``False``、空字串與空集合都算沒有。"""
    return value is not None and value is not False and value not in ("", [], (), {})


# ---- 表 ----------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IconArtRules:
    """推導用的表（:class:`IconArtTable` 整理成查表用的形式）＋ ``icon_prop`` 的允許清單。

    用 :meth:`build` 或 :func:`icon_art_rules` 建；正式呼叫處一律用內容庫上的表。"""

    weapon_look: Mapping[str, str]
    melee_words: tuple[tuple[tuple[str, ...], str], ...]
    ranged_words: tuple[tuple[tuple[str, ...], str], ...]
    thrust_props: tuple[str, ...]
    ranged_kinds: tuple[str, ...]
    summon_group: Mapping[str, str]
    summon_tint: Mapping[str, str]
    mod_tag_prop: Mapping[str, str]
    mod_tint: tuple[tuple[str, str], ...]
    dot: Mapping[str, str]
    bind: Mapping[str, str]
    curse: Mapping[str, str]
    status_tint: Mapping[str, str]
    cond_tint: Mapping[str, str]
    surface_tint: Mapping[str, str]
    effect_action: tuple[tuple[tuple[str, ...], str, str | None], ...]
    late_action: tuple[tuple[tuple[str, ...], str, str | None], ...]
    shape_motion: Mapping[str | None, str]
    needs_prop: tuple[str, ...]
    allowed_props: frozenset[str]
    """``icon_prop`` 的允許清單（只做成員查詢，不迭代）。"""

    @classmethod
    def build(cls, table: IconArtTable, props: IconPropTable) -> IconArtRules:
        def tints(rows: Sequence[Any]) -> dict[str, str]:
            return {r.key: r.tint for r in rows}

        return cls(
            weapon_look={r.weapon: r.look for r in table.weapon_look},
            melee_words=tuple((r.words, r.kind) for r in table.melee_words),
            ranged_words=tuple((r.words, r.kind) for r in table.ranged_words),
            thrust_props=table.thrust_props,
            ranged_kinds=table.ranged_kinds,
            summon_group={r.unit: r.group for r in table.summon_group},
            summon_tint=tints(table.summon_tint),
            mod_tag_prop={r.tag: r.prop for r in table.mod_tag_prop},
            mod_tint=tuple((r.key, r.tint) for r in table.mod_tint),
            dot=tints(table.dot),
            bind=tints(table.bind),
            curse=tints(table.curse),
            status_tint=tints(table.status_tint),
            cond_tint=tints(table.cond_tint),
            surface_tint=tints(table.surface_tint),
            effect_action=tuple((r.effects, r.act, r.tint) for r in table.effect_action),
            late_action=tuple((r.effects, r.act, r.tint) for r in table.late_action),
            shape_motion={r.shape: r.motion for r in table.shape_motion},
            needs_prop=tuple(table.needs_prop),
            allowed_props=frozenset(p.id for p in props.props),
        )


@cache
def default_icon_art_rules() -> IconArtRules:
    """預設內容資料夾的推導表與允許清單（只給沒有內容庫的呼叫：測試、快照腳本、``icon_of(…)`` 不給
    ``art`` 時）。讀一次後快取。"""
    root = default_content_dir()
    table = load_content_file(root / "skill_icon_art.yaml", IconArtTable)
    props = load_content_file(root / "skill_icon_props.yaml", IconPropTable)
    return IconArtRules.build(table, props)


def icon_art_rules(library: ContentLibrary) -> IconArtRules:
    """內容庫上的推導表與允許清單。內容庫沒有推導表（不是 ``load_library`` 建的）時用預設的。"""
    if library.icon_art is None:
        return default_icon_art_rules()
    return IconArtRules.build(library.icon_art, library.icon_props)


# ---- 推導 --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Skill:
    """推導要看的欄位（已容錯取值）。"""

    effects: tuple[Mapping[str, Any], ...]
    """效果接複合第二段的效果（只留 dict）。"""
    main_effects: tuple[Mapping[str, Any], ...]
    followup: Mapping[str, Any]
    modifiers: tuple[Any, ...]
    kind: str | None
    weapon_req: str | None
    name: str
    tags: tuple[str, ...]
    shape: Mapping[str, Any]
    elements: tuple[str, ...]


def _read(skill: Mapping[str, Any], elements: Sequence[str]) -> _Skill:
    main = tuple(_map(e) for e in _seq(skill.get("effects")) if isinstance(e, Mapping))
    followup = _map(skill.get("followup"))
    follow = tuple(_map(e) for e in _seq(followup.get("effects")) if isinstance(e, Mapping))
    return _Skill(
        effects=main + follow,
        main_effects=main,
        followup=followup,
        modifiers=tuple(_seq(skill.get("modifiers"))),
        kind=_text(skill.get("kind")),
        weapon_req=_text(skill.get("weapon_req")),
        name=_text(skill.get("name_zh")) or "",
        tags=tuple(_texts(skill.get("tags"))),
        shape=_map(skill.get("shape")),
        elements=tuple(elements),
    )


def _is_modifier(s: _Skill) -> bool:
    return s.kind == "modifier" or (not s.effects and bool(s.modifiers))


def _first_word(name: str, table: tuple[tuple[tuple[str, ...], str], ...]) -> str | None:
    for words, kind in table:
        if any(w in name for w in words):
            return kind
    return None


def _prop_special(s: _Skill, rules: IconArtRules) -> str | None:
    """道具第 1 列（化身）、第 2 列（``wielding_weapon`` 的武器）。"""
    for e in s.effects:
        form = _text(e.get("form"))
        if e.get("type") == "enter_form" and form is not None:
            return f"form:{form}"
    for e in s.effects:
        cond = _map(e.get("condition"))
        weapon = _text(cond.get("weapon"))
        if cond.get("type") == "wielding_weapon" and weapon is not None:
            return "w:" + rules.weapon_look.get(weapon, weapon)
    return None


def _prop_modifier(s: _Skill, rules: IconArtRules) -> str | None:
    """道具第 3 列：修正技畫它改造的對象。"""
    if not _is_modifier(s):
        return None
    applies = _map(_map(s.modifiers[0] if s.modifiers else None).get("applies_to"))
    for tag in _texts(applies.get("skill_tags")):
        if tag in rules.mod_tag_prop:
            return rules.mod_tag_prop[tag]
    actions = _texts(applies.get("actions"))
    if applies.get("all_attacks") or "attack" in actions:
        return "w:bow" if s.weapon_req == "ranged" else "w:sword"
    if (actions or _texts(applies.get("skill_tags"))) and s.weapon_req == "melee":
        return "w:fist"
    return "w:tome/book"


def _prop_weapon_class(s: _Skill, rules: IconArtRules) -> str | None:
    """道具第 4 列：近戰／遠程技能看標籤、名稱關鍵字、形狀，再退回預設。"""
    if s.weapon_req == "ranged":
        return "w:" + (_first_word(s.name, rules.ranged_words) or "bow")
    if s.weapon_req != "melee":
        return None
    if "stealth" in s.tags:
        return "w:dagger"
    if "martial" in s.tags:
        return "w:fist"
    hit = _first_word(s.name, rules.melee_words)
    if hit is not None:
        return "w:" + hit
    return "w:greatsword" if _text(s.shape.get("type")) in ("cone", "ring") else "w:sword"


def _prop_spell(s: _Skill, rules: IconArtRules) -> str:
    """道具第 5～9 列：召喚物、元素、水、奧術、沒有。"""
    for e in s.effects:
        if e.get("type") == "summon":
            unit = (_text(e.get("unit")) or "").removeprefix("summon_")
            return "summon:" + rules.summon_group.get(unit, "spirit")
    el = s.elements[0] if s.elements else None
    if el not in (None, "physical"):
        return f"el:{el}"
    if "water" in s.tags or any(_enum_text(e.get("surface")) == "water" for e in s.effects):
        return "el:water"
    return "el:arcane" if "arcane" in s.tags else "none"


def _icon_prop(skill: Mapping[str, Any], rules: IconArtRules) -> str | None:
    """道具第 2b 列：``icon_prop`` 在允許清單內才用（D3：清單外的值執行期退回推導）。"""
    value = _text(skill.get("icon_prop"))
    return value if value is not None and value in rules.allowed_props else None


def _derive_prop(s: _Skill, skill: Mapping[str, Any], rules: IconArtRules) -> str:
    return (
        _prop_special(s, rules)
        or _icon_prop(skill, rules)
        or _prop_modifier(s, rules)
        or _prop_weapon_class(s, rules)
        or _prop_spell(s, rules)
    )


def _derive_motion(s: _Skill, prop: str, rules: IconArtRules) -> str:
    """出手：形狀 → 近戰武器（突刺／揮砍）→ 單體近距離揮砍 → 射出。吃最後決定的道具。

    延遲段的錨點不是自身（``followup.anchor``：``cast_tile``、``farthest_enemy``）時，招式實際砸在
    別處，改用延遲段落下的形狀推導（GB-4b，美術 PM 11-14 移植需求 6.1：熔岩濺落 ``square3`` →
    ``area``，不讀成自身增益）。"""
    shape = s.shape
    anchor = _text(s.followup.get("anchor"))
    if s.followup.get("when") == "delayed" and anchor not in (None, "self", "caster"):
        landed = _map(s.followup.get("shape"))
        if landed:
            shape = landed
    raw = shape.get("type")
    kind = raw if isinstance(raw, str) else None
    if raw is None or kind is not None:
        found = rules.shape_motion.get(kind)
        if found is not None:
            return found
    weapon = prop.startswith("w:")
    if weapon and s.weapon_req == "melee":
        thrust = kind == "single" and prop.partition("/")[0] in rules.thrust_props
        return "thrust" if thrust else "swing"
    ranged_weapon = weapon and prop[2:].partition("/")[0] in rules.ranged_kinds
    rng = shape.get("range")
    near = rng is None or (isinstance(rng, int) and not isinstance(rng, bool) and rng == 1)
    if kind == "single" and near and not ranged_weapon:
        return "swing"
    return "shot"


type _Action = tuple[str, str | None]


def _status_action(status: str, rules: IconArtRules) -> _Action:
    if status in rules.dot:
        return "dot", rules.dot[status]
    if status in rules.bind:
        return "bind", rules.bind[status]
    if status == "slow":
        return "slow", None
    if status == "marked":
        return "mark", None
    if status in rules.curse:
        return "curse", rules.curse[status]
    return "buff", rules.status_tint.get(status)


def _modifier_action(s: _Skill, rules: IconArtRules) -> _Action:
    """記號第 1 列：修正技。染色＝``add_element`` 的元素；否則照表的列順序找第一個有填的改動鍵。"""
    change = _map(_map(s.modifiers[0] if s.modifiers else None).get("change"))
    el = _enum_text(change.get("add_element"))
    if el is not None:
        return "modify", el
    tint = next((t for key, t in rules.mod_tint if _filled(change.get(key))), None)
    return "modify", tint


def _action_setup(s: _Skill, rules: IconArtRules) -> _Action | None:
    """記號第 1 列（修正技）、第 2 列（延遲段蓄力：第一段只有護盾）。"""
    if _is_modifier(s):
        return _modifier_action(s, rules)
    if _text(s.followup.get("when")) != "delayed":
        return None
    if any(e.get("type") != "shield" for e in s.main_effects):
        return None
    follow = [_map(e) for e in _seq(s.followup.get("effects"))]
    els = [el for e in follow if (el := _enum_text(e.get("element"))) is not None]
    first = els[0] if els else None
    return "builder", first if first != "physical" else None


def _action_effect(
    s: _Skill, table: tuple[tuple[tuple[str, ...], str, str | None], ...], rules: IconArtRules
) -> _Action | None:
    """表裡第一組在技能效果中出現的（表的順序＝優先順序）。"""
    for group, act, fixed in table:
        for e in s.effects:
            if e.get("type") not in group:
                continue
            if fixed is not None:
                return act, fixed
            return act, _effect_tint(act, e, rules)
    return None


def _effect_tint(act: str, e: Mapping[str, Any], rules: IconArtRules) -> str | None:
    if act == "summon":
        unit = (_text(e.get("unit")) or "").removeprefix("summon_")
        return rules.summon_tint.get(unit)
    if act == "detonate":
        status = _text(e.get("status")) or ""
        return rules.dot.get(status) or rules.bind.get(status)
    if act == "surface":
        return rules.surface_tint.get(_enum_text(e.get("surface")) or "")
    return None


def _action_status(s: _Skill, rules: IconArtRules) -> _Action | None:
    """記號第 14 列：第一個施加狀態的效果。"""
    for e in s.effects:
        status = _text(e.get("status"))
        if e.get("type") == "apply_status" and status is not None:
            return _status_action(status, rules)
    return None


def _action_damage(s: _Skill, rules: IconArtRules) -> _Action:
    """記號第 21～24 列：終結、追擊／連擊、傷害、其餘。"""
    if "finisher" in s.tags:
        return "finisher", None
    damages = [e for e in s.effects if e.get("type") == "damage"]
    conds = [c for e in damages if (c := _map(e.get("condition")))]
    if len(damages) > 1 or conds:
        keys = [_text(c.get("status")) or str(c.get("type")) for c in conds]
        tint = next((rules.cond_tint[k] for k in keys if k in rules.cond_tint), None)
        return "combo", tint or (s.elements[1] if len(s.elements) > 1 else None)
    return ("hit", None) if damages else ("buff", None)


def _derive_action(s: _Skill, rules: IconArtRules) -> _Action:
    return (
        _action_setup(s, rules)
        or _action_effect(s, rules.effect_action, rules)
        or _action_status(s, rules)
        or _action_effect(s, rules.late_action, rules)
        or _action_damage(s, rules)
    )


def _spark(skill: Mapping[str, Any]) -> str | None:
    for v in _seq(skill.get("variants")):
        el = _enum_text(_map(v).get("element"))
        if el is not None:
            return el
    return None


def element_tags(skill: Mapping[str, Any]) -> list[str]:
    """效果（含複合第二段）的元素；沒有時取 ``tags`` 裡第一個元素（同 ``SkillIcon.elements``）。"""
    found: list[str] = []
    followup = _map(skill.get("followup"))
    for raw in [*_seq(skill.get("effects")), *_seq(followup.get("effects"))]:
        el = _enum_text(_map(raw).get("element"))
        if el is not None and el not in found:
            found.append(el)
    if not found:
        found = [t for t in _texts(skill.get("tags")) if t in _ELEMENT_IDS][:1]
    return found


def derive_art(
    skill: Mapping[str, Any],
    rules: IconArtRules | None = None,
    *,
    elements: Sequence[str] | None = None,
) -> IconArt:
    """技能定義 JSON（可以缺欄位、型別可以不對）→ Q 版主圖代碼；永遠回傳。

    ``elements`` 是 ``SkillIcon.elements``（給了就不重算）；``rules`` 為 ``None`` 時用預設內容資料夾
    的表。"""
    rules = default_icon_art_rules() if rules is None else rules
    s = _read(skill, element_tags(skill) if elements is None else elements)
    prop = _derive_prop(s, skill, rules)
    act, tint = _derive_action(s, rules)
    if prop == "none" and act in rules.needs_prop:
        prop = "el:arcane"
    return IconArt(
        prop=prop, motion=_derive_motion(s, prop, rules), act=act, tint=tint, spark=_spark(skill)
    )
