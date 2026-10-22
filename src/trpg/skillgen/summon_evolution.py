"""召喚技能的三支分歧進化（Phase 3-33f2，``docs/design/06-技能.md`` 6.28、6.29.4；沒有 LLM）。

召喚技能（有 ``summon`` 效果）沒有骰子或倍率可調，一般的進化模板做不出來；這裡直接改它的
``summon`` 效果（參數在 ``content/skill_evolution.yaml`` 的 ``summon`` 區塊）：

- **加深**（``deepen``）：單隻更強——召喚物最大 HP 多 ``deepen_hp_permille``‰，並多一個小特性
  （``core.yaml`` 的 ``summon_traits``；依召喚物定位挑：不動或不攻擊的護甲、近戰移動、遠程
  暴擊範圍）。
- **橋接**（``bridge``）：召喚物多帶一個灌注關鍵字（第二個灌注）。關鍵字依「前後搭配的技能 →
  目標身上的次數 → 主角其他技能持有的招數」排序（同一般進化），都沒有統計時看召喚物定位偏好
  的灌注，再依推導表順序；進化後的技能（專屬規則）必須真的帶那個關鍵字。不會攻擊的召喚物
  （圖騰、土牆）沒有這一支。
- **數量型**（``count``）：一次召喚 2 隻，每隻只有 60% 的最大 HP 與傷害。圖騰（光環）沒有這一支。

**同階預算**：進化後的點數（:func:`trpg.skillgen.budget.skill_budget`）必須落在同階的區間內。
超出時依序試「縮短持續輪數」（最短 ``min_duration``）與「冷卻 +1、+2」（沿用一般進化的
:func:`cost_attempts`），第一個合格的就是結果；都不合格時這一支省略。稀有度不變（6.12 稀有度
不加強度）。

純函式、確定性（不使用亂數）。
"""

from __future__ import annotations

from typing import Any

from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skills import EffectSpec, SkillDef
from trpg.skillgen.evolution import Evolution, EvolutionRequest, cost_attempts, evolved_id
from trpg.skillgen.validate import validate_skill

__all__ = ["is_summon_skill", "summon_evolution_options"]

_SUMMON = "summon"
_DEEPEN = "summon_deepen"
_BRIDGE = "summon_bridge"
_COUNT = "summon_count"


def is_summon_skill(skill: SkillDef) -> bool:
    """技能召喚了召喚物（有 ``summon`` 效果）。"""
    return any(e.type == _SUMMON for e in skill.effects)


def _summon_index(skill: SkillDef) -> int:
    return next(i for i, e in enumerate(skill.effects) if e.type == _SUMMON)


def _role(library: ContentLibrary, unit: str) -> str:
    """召喚物定位：``static`` 不會動或不攻擊（圖騰、土牆、藤蔓）、``melee`` 近戰、``ranged``
    遠程。"""
    summon = library.ruleset.summon_def(unit)
    template = summon.template
    if template.inert or template.totem is not None or template.speed == 0:
        return "static"
    return "melee" if summon.weapon.range <= 1 else "ranged"


def _can_attack(library: ContentLibrary, unit: str) -> bool:
    template = library.ruleset.summon_def(unit).template
    return not template.inert and template.totem is None


def _variant(skill: SkillDef, **changes: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """``summon`` 效果加上 ``changes`` 的草稿（技能欄位 dict、效果 dict 列表）。"""
    base = skill.model_dump(mode="json")
    effects = [e.model_dump(mode="json", exclude_none=True) for e in skill.effects]
    base.pop("effects")
    index = _summon_index(skill)
    effects[index] = {**effects[index], **changes}
    return base, effects


def _fit(
    skill: SkillDef,
    draft: tuple[dict[str, Any], list[dict[str, Any]]],
    library: ContentLibrary,
    accept: Any = None,
) -> SkillDef | None:
    """同階預算內的第一個合格版本：依序試「原持續輪數 → 縮短」×「原代價 → 冷卻 +1、+2」。"""
    base, effects = draft
    index = _summon_index(skill)
    original = effects[index]["duration"]
    floor = library.evolution.summon.min_duration
    for duration in range(original, floor - 1, -1):
        trial = [dict(e) for e in effects]
        trial[index]["duration"] = duration
        for cost in cost_attempts(skill):
            try:
                evolved = SkillDef.model_validate({**base, "cost": cost, "effects": trial})
            except ValueError:
                continue
            if validate_skill(evolved, library):
                continue
            if accept is None or accept(evolved):
                return evolved
    return None


def _named(
    skill: SkillDef, template: str, keyword: str | None, prefix: str, summary: str
) -> dict[str, Any]:
    concept = f"{skill.narrative.concept}（進化：{summary}）".lstrip("（")
    return {
        "id": evolved_id(skill.id, template, keyword),
        "name_zh": f"{prefix}・{skill.name_zh}",
        "narrative": {"concept": concept, "cast_flavor": skill.narrative.cast_flavor},
        "provenance": {"origin": "level_up", "parents": [skill.id]},
    }


def _finish(
    skill: SkillDef,
    changes: dict[str, Any],
    names: dict[str, Any],
    library: ContentLibrary,
    accept: Any = None,
) -> SkillDef | None:
    base, effects = _variant(skill, **changes)
    return _fit(skill, ({**base, **names}, effects), library, accept)


# ---------------------------------------------------------------------------
# 三支
# ---------------------------------------------------------------------------


def _deepen(skill: SkillDef, unit: str, library: ContentLibrary) -> Evolution | None:
    table = library.evolution.summon
    trait_id = table.traits.get(_role(library, unit))
    trait = library.ruleset.core.summon_traits.get(trait_id or "")
    if trait_id is None or trait is None:
        return None
    summary = table.deepen_summary_zh.format(hp=table.deepen_hp_permille // 10, trait=trait.name_zh)
    names = _named(skill, _DEEPEN, None, table.deepen_prefix_zh, summary)
    changes = {"max_hp_permille": table.deepen_hp_permille, "trait": trait_id}
    evolved = _finish(skill, changes, names, library)
    return None if evolved is None else Evolution("deepen", _DEEPEN, None, evolved, summary)


def _bridge_keywords(
    skill: SkillDef, unit: str, request: EvolutionRequest, library: ContentLibrary
) -> list[str]:
    """橋接可選的灌注關鍵字（已排序）：灌注對照表中、這招還沒有的（``summon`` 灌注除外）。"""
    own = set(derive_keywords(skill, library.keywords).all())
    usage = request.usage
    partners = usage.partners()
    order = library.keywords.ids()
    role = _role(library, unit)
    table = library.ruleset.core.summon_infusions
    found = [k for k in order if k in table and k != _SUMMON and k not in own]
    found.sort(
        key=lambda k: (
            -partners.get(k, 0),
            -usage.target_keywords.get(k, 0),
            -request.held_keywords.get(k, 0),
            role not in table[k].roles,
            order.index(k),
        )
    )
    return found[: library.evolution.bridge_keyword_tries]


def _bridge(
    skill: SkillDef, unit: str, request: EvolutionRequest, library: ContentLibrary
) -> Evolution | None:
    if not _can_attack(library, unit):
        return None
    table = library.evolution.summon
    for keyword in _bridge_keywords(skill, unit, request, library):
        graft = library.evolution.grafts.get(keyword)
        prefix = graft.prefix_zh if graft is not None else keyword
        name = next((k.name_zh for k in library.keywords.keywords if k.id == keyword), keyword)
        summary = table.bridge_summary_zh.replace("{keyword}", name)
        names = _named(skill, _BRIDGE, keyword, prefix, summary)

        def carries(evolved: SkillDef, k: str = keyword) -> bool:
            return k in derive_keywords(evolved, library.keywords, exclusive_only=True).all()

        evolved = _finish(skill, {"infusion": keyword}, names, library, carries)
        if evolved is not None:
            return Evolution("bridge", _BRIDGE, keyword, evolved, summary)
    return None


def _count(skill: SkillDef, unit: str, library: ContentLibrary) -> Evolution | None:
    if library.ruleset.summon_def(unit).template.totem is not None:
        return None
    table = library.evolution.summon
    summary = table.count_summary_zh.format(
        count=table.count_number, power=table.count_power_permille // 10
    )
    names = _named(skill, _COUNT, None, table.count_prefix_zh, summary)
    changes = {"count": table.count_number, "power_permille": table.count_power_permille}
    evolved = _finish(skill, changes, names, library)
    return None if evolved is None else Evolution("count", _COUNT, None, evolved, summary)


def summon_evolution_options(
    library: ContentLibrary, request: EvolutionRequest
) -> tuple[Evolution, ...]:
    """召喚技能的分歧進化：加深、橋接、數量型（依序；做不出來的省略，所以可能只有 0～3 支）。"""
    skill = request.skill
    unit = skill.effects[_summon_index(skill)].unit
    if unit is None or skill.effects[_summon_index(skill)].duration is None:
        return ()
    options = (
        _deepen(skill, unit, library),
        _bridge(skill, unit, request, library),
        _count(skill, unit, library),
    )
    return tuple(o for o in options if o is not None)


def summon_spec(skill: SkillDef) -> EffectSpec:
    """技能的 ``summon`` 效果（測試與顯示用）。"""
    return skill.effects[_summon_index(skill)]
