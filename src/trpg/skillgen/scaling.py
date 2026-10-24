"""新技能跟主屬性（Phase 3H-3，``docs/design/07-角色成長.md`` 7.2、``06-技能.md`` 6.10）。

隨機組合器、候選產生器與 LLM 提議產生技能之後，把 **縮放屬性改成主角目前最高的屬性**，但限在
``content/skill_scaling.yaml`` 的允許範圍內（武器技看武器、法術技依主題；內建技能池不改）：

- 允許範圍內有主角最高的屬性就用它；否則取允許範圍內主角數值最高的。
- 同分一律依六屬性順序（力量、敏捷、體質、智力、感知、意志）取第一個——確定性，不看 ``set`` 的
  迭代順序。
- ``avoid``：候選產生器的「新方向」要和主角最高屬性不同的屬性；允許範圍只剩 ``avoid`` 時不改，
  由呼叫者決定要不要換技能。
- **武器技**（3H-6）：引擎看手上武器，技能的 ``scaling_attr`` 只是顯示提示；一律設為所需武器大類
  的主屬性（``skill_scaling.yaml`` 的 ``weapon_class_attrs``），不看主角屬性；可帶一個心智第二屬性
  （3I-3）。
- 雙屬性技能（``secondary_scaling_attr``，3H-7、3I-3）：只在主角第二高與最高屬性差 ≤ 4 時才有（否則
  拿掉）；第二屬性也限在允許範圍內（武器技為心智屬性，身體類法術沒有）——和新的主屬性相同
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
from trpg.content.skills import SkillDef, rarity_rank
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Attribute, Element

__all__ = [
    "attr_names_zh",
    "dual_eligible",
    "fit_draft_scaling",
    "fit_scaling",
    "fix_weapon_scaling",
    "grant_dual",
    "hero_dual_ok",
    "hero_secondary",
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


def hero_dual_ok(attributes: Mapping[Attribute, int], library: ContentLibrary) -> bool:
    """主角的第二高屬性與最高屬性的差不超過 ``dual_max_gap``（初值 4；3I-3，06 6.10 #46）才給
    雙屬性技能。"""
    ranked = sorted((attributes[a] for a in Attribute), reverse=True)
    return ranked[0] - ranked[1] <= library.skill_scaling.dual_max_gap


def dual_eligible(skill: SkillDef, library: ContentLibrary) -> bool:
    """技能種類上能帶第二屬性：稀有度夠（``dual_scaling_min_rarity``）的主動武器技或法術技，
    沒有專精，且第二屬性的允許集合（:meth:`ContentLibrary.secondary_range`，身體類法術為空）
    裡有主屬性以外的屬性。"""
    return (
        skill.kind == "active"
        and skill.mastery is None
        and rarity_rank(skill.rarity) >= rarity_rank(library.ruleset.core.dual_scaling_min_rarity)
        and any(a != skill.scaling_attr for a in library.secondary_range(skill))
    )


def hero_secondary(
    skill: SkillDef, attributes: Mapping[Attribute, int], library: ContentLibrary
) -> Attribute | None:
    """主角的第二屬性（3I-3）：主角第二高與最高屬性差 ≤ ``dual_max_gap`` 時，取第二屬性允許集合
    （武器技為心智屬性）裡主角最高的、不同於主屬性的屬性；否則 ``None``。"""
    if not hero_dual_ok(attributes, library):
        return None
    allowed = [a for a in library.secondary_range(skill) if a != skill.scaling_attr]
    return pick_scaling_attr(allowed, attributes)


def grant_dual(
    skill: SkillDef, attributes: Mapping[Attribute, int], library: ContentLibrary
) -> SkillDef:
    """LLM 提議與其他沒有抽籤的來源：以 ``dual_permille`` 的機率（用技能 ID 決定的確定性抽籤）
    加上主角的第二屬性（3I-3，#46：稀有以上、主角第二高與最高差 ≤ 4）。已有第二屬性、種類不合、
    條件不符或沒抽中時回傳原技能。"""
    if skill.secondary_scaling_attr is not None or not dual_eligible(skill, library):
        return skill
    roll = Rng(fnv1a64(skill.id.encode())).fork("scaling.dual")
    if not roll.chance_permille(library.composer.scaling.dual_permille):
        return skill
    second = hero_secondary(skill, attributes, library)
    return skill if second is None else _with_attrs(skill, skill.scaling_attr, second)


def fix_weapon_scaling(skill: SkillDef, library: ContentLibrary) -> SkillDef:
    """武器技的 ``scaling_attr`` 設為所需武器大類的主屬性（3H-6）；第二屬性只留心智屬性（3I-3），
    其他拿掉。"""
    attr = library.skill_scaling.weapon_class_attr(skill.weapon_req)
    second = skill.secondary_scaling_attr
    if second is not None and second not in library.skill_scaling.weapon_second_attrs:
        second = None
    return _with_attrs(skill, attr, second)


def _with_attrs(skill: SkillDef, primary: Attribute, secondary: Attribute | None) -> SkillDef:
    if skill.scaling_attr == primary and skill.secondary_scaling_attr == secondary:
        return skill
    return skill.model_copy(update={"scaling_attr": primary, "secondary_scaling_attr": secondary})


def fit_scaling(skill: SkillDef, library: ContentLibrary) -> SkillDef:
    """把縮放屬性（含第二屬性）收進允許範圍，不看主角屬性（見模組說明）。武器技照
    :func:`fix_weapon_scaling`（進化而來的保留提示屬性，只收第二屬性）；內建技能與沒有範圍可查時
    回傳原技能。身體類法術沒有第二屬性（3I-3）。"""
    if skill.provenance.origin == "builtin":
        return skill
    if skill.category == "weapon":
        if skill.provenance.parents:  # 進化的武器技保留提示屬性（只當顯示），第二屬性照規則收
            fixed = fix_weapon_scaling(skill, library)
            return _with_attrs(skill, skill.scaling_attr, fixed.secondary_scaling_attr)
        return fix_weapon_scaling(skill, library)
    allowed = library.scaling_range(skill)
    if not allowed:
        return skill
    primary = skill.scaling_attr if skill.scaling_attr in allowed else allowed[0]
    secondary = skill.secondary_scaling_attr
    if secondary is not None:
        pool = library.secondary_range(skill)
        if secondary == primary or secondary not in pool:
            secondary = next((a for a in pool if a != primary), None)
    return _with_attrs(skill, primary, secondary)


def fit_draft_scaling(draft: Mapping[str, Any], library: ContentLibrary) -> dict[str, Any]:
    """:func:`fit_scaling` 的草稿版（法術技；dict 進 dict 出，ID 由呼叫者之後再算）。"""
    out = dict(draft)
    if out.get("category") != "spell":
        return out
    facts = ScalingFacts.of_draft(out)
    allowed = [a.value for a in library.scaling_range(facts)]
    if allowed and out.get("scaling_attr") not in allowed:
        out["scaling_attr"] = allowed[0]
    second = out.get("secondary_scaling_attr")
    if second is not None:
        pool = [a.value for a in library.secondary_range(facts)]
        if second == out.get("scaling_attr") or second not in pool:
            out.pop("secondary_scaling_attr")
            others = [a for a in pool if a != out.get("scaling_attr")]
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
    武器技的主屬性是武器大類的主屬性。有第二屬性的技能（抽籤已經中了）：主角第二高與最高屬性差
    ≤ ``dual_max_gap`` 時第二屬性改取主角最高的允許屬性，否則拿掉（3I-3）。不需要改時回傳原技能。
    內容庫的技能（手寫技能池）不會經過這裡。"""
    if skill.category == "weapon":
        skill = fix_weapon_scaling(skill, library)
        if skill.secondary_scaling_attr is None:
            return skill
        return _with_attrs(skill, skill.scaling_attr, hero_secondary(skill, attributes, library))
    allowed = library.scaling_range(skill)
    attr = pick_scaling_attr(allowed, attributes, avoid) or skill.scaling_attr
    fitted = _with_attrs(skill, attr, skill.secondary_scaling_attr)
    if skill.secondary_scaling_attr is None:
        return fitted
    return _with_attrs(fitted, attr, hero_secondary(fitted, attributes, library))


def attr_names_zh(attrs: Collection[Attribute]) -> str:
    return "、".join(a.display_name for a in attrs)


def _field(effect: Any, name: str) -> Any:
    return effect.get(name) if isinstance(effect, Mapping) else getattr(effect, name, None)


def _effect_name_zh(effect: Any, library: ContentLibrary) -> str:
    """主要效果的中文：原語名稱（元素或狀態）。"""
    kind = str(_field(effect, "type"))
    if _field(effect, "type") is None:  # 修正規則賦予的元素（3I-3）
        element = _field(effect, "element")
        return f"賦予元素（{Element(str(element)).display_name}）" if element else "修正規則"
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
