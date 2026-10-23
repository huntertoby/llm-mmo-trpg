"""新技能跟主屬性（Phase 3H-3，``docs/design/07-角色成長.md`` 7.2、``06-技能.md`` 6.10）。

隨機組合器、候選產生器與 LLM 提議產生技能之後，把 **縮放屬性改成主角目前最高的屬性**，但限在
``content/skill_scaling.yaml`` 的允許範圍內（武器技看武器、法術技依主題；內建技能池不改）：

- 允許範圍內有主角最高的屬性就用它；否則取允許範圍內主角數值最高的。
- 同分一律依六屬性順序（力量、敏捷、體質、智力、感知、意志）取第一個——確定性，不看 ``set`` 的
  迭代順序。
- ``avoid``：候選產生器的「新方向」要和主角最高屬性不同的屬性；允許範圍只剩 ``avoid`` 時不改，
  由呼叫者決定要不要換技能。
- **武器技**（3H-6）：引擎看手上武器，技能的 ``scaling_attr`` 只是顯示提示；一律設為所需武器大類
  的主屬性（``skill_scaling.yaml`` 的 ``weapon_class_attrs``），不帶第二屬性，不看主角屬性。
- 雙屬性技能（``secondary_scaling_attr``，3H-7）：第二屬性也限在允許範圍內——和新的主屬性相同
  或超出範圍時，改取範圍內（主屬性以外）主角最高的；範圍裡沒有別的屬性就拿掉（技能退回單屬性）。
  專精加成跟著主屬性走，不受影響。

:func:`fit_scaling`（3H-7）：沒有主角屬性時（工坊「隨機」、組合器的草稿、進化、LLM 提議）把縮放
屬性收進允許範圍——在範圍內就不動，否則取範圍裡第一個（玩法 PM 2026-10-24 第 5 題）；第二屬性
同理（範圍裡主屬性以外的第一個，沒有就拿掉）。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skill_scaling import ScalingFacts
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute, Element

__all__ = [
    "attr_names_zh",
    "fit_draft_scaling",
    "fit_scaling",
    "fix_weapon_scaling",
    "pick_scaling_attr",
    "retarget_scaling",
    "scaling_basis_zh",
]


def pick_scaling_attr(
    allowed: Collection[Attribute],
    attributes: Mapping[Attribute, int],
    avoid: Attribute | None = None,
) -> Attribute | None:
    """``allowed`` 中主角數值最高的屬性（並列依六屬性順序）；排除 ``avoid`` 後沒有時為 ``None``。"""
    pool = [a for a in Attribute if a in allowed and a != avoid]
    if not pool:
        return None
    best = max(attributes[a] for a in pool)
    return next(a for a in pool if attributes[a] == best)


def fix_weapon_scaling(skill: SkillDef, library: ContentLibrary) -> SkillDef:
    """武器技的 ``scaling_attr`` 設為所需武器大類的主屬性、拿掉第二屬性（3H-6）。"""
    attr = library.skill_scaling.weapon_class_attr(skill.weapon_req)
    if skill.scaling_attr == attr and skill.secondary_scaling_attr is None:
        return skill
    return skill.model_copy(update={"scaling_attr": attr, "secondary_scaling_attr": None})


def _with_attrs(skill: SkillDef, primary: Attribute, secondary: Attribute | None) -> SkillDef:
    if skill.scaling_attr == primary and skill.secondary_scaling_attr == secondary:
        return skill
    return skill.model_copy(update={"scaling_attr": primary, "secondary_scaling_attr": secondary})


def fit_scaling(skill: SkillDef, library: ContentLibrary) -> SkillDef:
    """把縮放屬性（含第二屬性）收進允許範圍，不看主角屬性（見模組說明）。武器技照
    :func:`fix_weapon_scaling`（進化而來的只拿掉第二屬性）；內建技能與沒有範圍可查時回傳原技能。"""
    if skill.provenance.origin == "builtin":
        return skill
    if skill.category == "weapon":
        if skill.provenance.parents:  # 進化的武器技保留提示屬性（只當顯示），只拿掉第二屬性
            return _with_attrs(skill, skill.scaling_attr, None)
        return fix_weapon_scaling(skill, library)
    allowed = library.scaling_range(skill)
    if not allowed:
        return skill
    primary = skill.scaling_attr if skill.scaling_attr in allowed else allowed[0]
    secondary = skill.secondary_scaling_attr
    if secondary is not None and (secondary == primary or secondary not in allowed):
        secondary = next((a for a in allowed if a != primary), None)
    return _with_attrs(skill, primary, secondary)


def fit_draft_scaling(draft: Mapping[str, Any], library: ContentLibrary) -> dict[str, Any]:
    """:func:`fit_scaling` 的草稿版（法術技；dict 進 dict 出，ID 由呼叫者之後再算）。"""
    out = dict(draft)
    if out.get("category") != "spell":
        return out
    allowed = [a.value for a in library.scaling_range(ScalingFacts.of_draft(out))]
    if allowed and out.get("scaling_attr") not in allowed:
        out["scaling_attr"] = allowed[0]
    second = out.get("secondary_scaling_attr")
    if second is not None and (second == out.get("scaling_attr") or second not in allowed):
        out.pop("secondary_scaling_attr")
        others = [a for a in allowed if a != out.get("scaling_attr")]
        if others:
            out["secondary_scaling_attr"] = others[0]
    return out


def retarget_scaling(
    skill: SkillDef,
    attributes: Mapping[Attribute, int],
    library: ContentLibrary,
    *,
    avoid: Attribute | None = None,
) -> SkillDef:
    """把 ``skill`` 的縮放屬性改成 ``attributes`` 中最高、且在允許範圍內的屬性（見模組說明）。
    不需要改（或沒有可用的屬性）時回傳原技能。內容庫的技能（手寫技能池）不會經過這裡。"""
    if skill.category == "weapon":
        return fix_weapon_scaling(skill, library)
    allowed = library.scaling_range(skill)
    attr = pick_scaling_attr(allowed, attributes, avoid) or skill.scaling_attr
    secondary = skill.secondary_scaling_attr
    if secondary is not None and (secondary == attr or secondary not in allowed):
        secondary = pick_scaling_attr([a for a in allowed if a != attr], attributes)
    return _with_attrs(skill, attr, secondary)


def attr_names_zh(attrs: Collection[Attribute]) -> str:
    return "、".join(a.display_name for a in attrs)


def _field(effect: Any, name: str) -> Any:
    return effect.get(name) if isinstance(effect, Mapping) else getattr(effect, name, None)


def _effect_name_zh(effect: Any, library: ContentLibrary) -> str:
    """主要效果的中文：原語名稱（元素或狀態）。"""
    kind = str(_field(effect, "type"))
    primitive = library.ruleset.find_primitive(kind)
    name = primitive.name_zh if primitive is not None else kind
    element = _field(effect, "element")
    status = _field(effect, "status")
    if element is not None and str(element) in {e.value for e in Element}:
        return f"{name}（{Element(str(element)).display_name}）"
    statuses = {s.id: s for s in library.ruleset.statuses.statuses}
    if status is not None and str(status) in statuses:
        return f"{name}（{statuses[str(status)].name_zh}）"
    return name


def scaling_basis_zh(skill: SkillDef | ScalingFacts, library: ContentLibrary) -> str:
    """縮放允許範圍的由來（中文；驗證器 ``scaling.range`` 與工坊縮放選單共用，Phase 3H-7）。"""
    facts = skill if isinstance(skill, ScalingFacts) else ScalingFacts.of_skill(skill)
    basis = library.scaling_basis(facts)
    if basis.source == "override":
        return f"這招是例外（{basis.reason_zh}）"
    if basis.source == "weapon":
        return "武器技看手上武器的屬性"
    if basis.source == "body":
        return "效果與標籤都沒有法術主題，屬於身體類（物理、裝備動作等）"
    label = library.skill_scaling.theme(basis.themes[0]).label_zh
    if basis.source == "tags":
        return f"效果沒有主題訊號，依標籤屬於「{label}」"
    assert basis.effect_index is not None
    main = _effect_name_zh(facts.effects[basis.effect_index], library)
    return f"主要效果「{main}」屬於「{label}」"
