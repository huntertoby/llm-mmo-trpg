"""戰場變奏的產生（Phase 3-25b，``docs/design/06-技能.md`` 6.24）：隨機組合器與進化模板共用。

候選來自 ``content/skill_composer.yaml`` 的 ``variant``（條件 × 替換內容的所有組合）。
:func:`add_variant` 依亂數順序逐一試，第一個通過驗證（schema、稀有度數量上限、每個型態的預算窗）
的採用；都不合格回傳 ``None``（呼叫端維持原技能）。純函式、確定性（只用傳入的
:class:`~trpg.shared.rng.Rng`）。
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError
from trpg.skillgen.validate import validate_skill

__all__ = ["add_variant", "variant_candidates", "variant_eligible", "variant_specs", "with_variant"]


def variant_eligible(skill: SkillDef, library: ContentLibrary) -> bool:
    """技能能不能再加一個變奏：主動技能（不是複合、陷阱、傳說常駐、修正），而且稀有度上限還沒滿。"""
    cap = library.ruleset.core.variant_max_by_rarity.get(skill.rarity, 0)
    return (
        skill.kind == "active"
        and skill.trap is None
        and skill.followup is None
        and not skill.is_activatable
        and len(skill.variants) < cap
    )


def variant_specs(library: ContentLibrary, taken: Collection[str] = ()) -> list[dict[str, Any]]:
    """候選變奏（JSON；資料順序，條件在外圈、替換內容在內圈），已排除 id 在 ``taken`` 的。"""
    rules = library.composer.variant
    out: list[dict[str, Any]] = []
    for condition in rules.conditions:
        for change in rules.changes:
            variant_id = f"{condition.id}_{change.id}"
            if variant_id in taken:
                continue
            spec: dict[str, Any] = {
                "id": variant_id,
                "name_zh": f"{condition.name_zh}・{change.name_zh}",
                "when": condition.when.model_dump(mode="json", exclude_none=True),
            }
            spec.update(
                change.model_dump(mode="json", exclude_none=True, exclude={"id", "name_zh"})
            )
            out.append(spec)
    return out


def variant_candidates(skill: SkillDef, library: ContentLibrary) -> list[dict[str, Any]]:
    """``skill`` 還能加的候選變奏。"""
    return variant_specs(library, {v.id for v in skill.variants})


def with_variant(skill: SkillDef, spec: dict[str, Any]) -> SkillDef | None:
    """``skill`` 加上 ``spec`` 的結果；schema 不合法時 ``None``。"""
    data = skill.model_dump(mode="json", exclude_none=True)
    data["variants"] = [*data.get("variants", []), spec]
    try:
        return SkillDef.model_validate(data)
    except ValidationError:
        return None


def add_variant(skill: SkillDef, library: ContentLibrary, rng: Rng) -> SkillDef | None:
    """加一個通過驗證的變奏；沒有可用的候選時 ``None``。"""
    if not variant_eligible(skill, library):
        return None
    for spec in rng.shuffled(variant_candidates(skill, library)):
        found = with_variant(skill, spec)
        if found is None:
            continue
        try:
            if not validate_skill(found, library):
                return found
        except BudgetError:
            continue
    return None
