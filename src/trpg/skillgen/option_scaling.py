"""工坊的第二縮放屬性與專精選單（Phase 3H-8；放在「稀有度」步驟，因為縮放範圍與專精能不能用都要看
已填好的效果與形狀）。

- 第二屬性（``secondary_scaling_attr``）：法術技、史詩以上（``dual_scaling_min_rarity``）才列出，
  選項限 :meth:`~trpg.content.skill_scaling.SkillScalingRules.allowed_attrs` 的範圍、不含主屬性。
  **武器技不列**（武器技看手上武器的屬性；魔劍士方案 A 未定，3I-3 才可能開放）。
- 專精（``mastery``）：沒有第二屬性時列出；選項用 schema 試組決定（``range`` 要有施放距離、
  ``duration`` 要有 ``apply_status`` 效果），不另寫規則。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import RARITY_ORDER, SkillDef, rarity_rank
from trpg.shared.types import Attribute
from trpg.skillgen.draft import Draft, DraftError, build_skill
from trpg.skillgen.option_models import Choice, FieldSpec

__all__ = ["scaling_extra_fields"]

_MASTERY_TEXT: dict[str, tuple[str, str]] = {
    "range": ("射程專精", "施放距離 +1"),
    "duration": ("持續專精", "此技能施加的狀態持續 +1 回合"),
}


def _try(draft: Draft, overrides: Mapping[str, Any]) -> SkillDef | None:
    try:
        return build_skill(draft, overrides)
    except DraftError:
        return None


def _probe_rarity(draft: Draft, library: ContentLibrary) -> str:
    chosen = draft.get("rarity")
    if isinstance(chosen, str) and chosen in RARITY_ORDER:
        return chosen
    if isinstance(draft.get("cost"), Mapping) and draft["cost"].get("source") is not None:
        return "legendary"
    return library.ruleset.core.dual_scaling_min_rarity


def _secondary_field(draft: Draft, library: ContentLibrary, probe: SkillDef) -> FieldSpec | None:
    """法術技的第二屬性選單；稀有度不夠且還沒填時不列（已填的仍列出，才能取消）。"""
    dual = library.ruleset.core.dual_scaling_min_rarity
    rarity = draft.get("rarity")
    enough = isinstance(rarity, str) and rarity_rank(rarity) >= rarity_rank(dual)
    if not enough and draft.get("secondary_scaling_attr") is None:
        return None
    allowed = library.skill_scaling.allowed_attrs(probe, library.weapons)
    choices = tuple(
        Choice(value=a.value, name_zh=a.display_name)
        for a in Attribute
        if a in allowed and a != probe.scaling_attr
    )
    return FieldSpec(
        field="secondary_scaling_attr",
        name_zh="第二縮放屬性",
        description_zh=(
            f"雙屬性縮放：命中與傷害取「{probe.scaling_attr.display_name}」與第二屬性的平均；"
            "只列這招技能的縮放範圍內的屬性。選了第二屬性就不能再選專精"
        ),
        type="choice",
        choices=choices,
    )


def _mastery_field(draft: Draft, probe: SkillDef) -> FieldSpec | None:
    base = {"rarity": probe.rarity, "secondary_scaling_attr": None}
    options = [m for m in _MASTERY_TEXT if _try(draft, {**base, "mastery": m}) is not None]
    if not options:
        return None
    top = (
        "手上武器的屬性" if probe.category == "weapon" else f"「{probe.scaling_attr.display_name}」"
    )
    return FieldSpec(
        field="mastery",
        name_zh="專精",
        description_zh=f"{top}是自己所有屬性中最高（含並列）時，額外獲得一項加成",
        type="choice",
        choices=tuple(
            Choice(value=m, name_zh=_MASTERY_TEXT[m][0], description_zh=_MASTERY_TEXT[m][1])
            for m in options
        ),
    )


def scaling_extra_fields(draft: Draft, library: ContentLibrary) -> tuple[FieldSpec, ...]:
    """稀有度步驟的第二屬性與專精欄位（修正技能沒有；試組不成立時也沒有）。"""
    if draft.get("kind") == "modifier":
        return ()
    base = {
        "rarity": _probe_rarity(draft, library),
        "secondary_scaling_attr": None,
        "mastery": None,
    }
    probe = _try(draft, base)
    if probe is None:
        return ()
    out: list[FieldSpec] = []
    secondary = _secondary_field(draft, library, probe) if probe.category == "spell" else None
    if secondary is not None:
        out.append(secondary)
    if draft.get("secondary_scaling_attr") is None:
        mastery = _mastery_field(draft, probe)
        if mastery is not None:
            out.append(mastery)
    return tuple(out)
