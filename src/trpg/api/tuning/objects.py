"""數值工坊的對象與欄位（NW-1a；技能對象 NW-2a）：白名單 × 磁碟上的檔 → 畫面用的清單與表單資料。

值一律讀**磁碟上**的 ``content/``（寫回後不重開伺服器也看到新值）；唯讀提示（遭遇護甲調整、技能的
使用者與預算）讀伺服器啟動時載入的內容庫。"""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import Any, Final, Literal

from trpg.api.tuning.schemas import (
    TuningFieldView,
    TuningObjectDetail,
    TuningObjectSummary,
    TuningSkillFacets,
    TuningSkillUser,
    TuningUnitSkills,
)
from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup
from trpg.content.battle import UnitTemplate
from trpg.content.equipment import loadout_held
from trpg.content.library import ContentLibrary
from trpg.content.loader import load_content_file, parse_yaml
from trpg.content.skills import SkillDef, weapon_problem
from trpg.content.skills.primitives import PrimitiveTable
from trpg.content.skills.shapes import ShapeTable
from trpg.content.tuning_fields import (
    PathPart,
    TuningField,
    TuningFields,
    TuningTarget,
    format_path,
    parse_path,
    target_files,
)
from trpg.skillgen.budget import BudgetError, skill_budget

__all__ = [
    "AI_NAME_ZH",
    "AI_NOTES_ZH",
    "RETIER_NOTE_ZH",
    "ObjectNotFoundError",
    "concrete_fields",
    "field_limits",
    "field_value",
    "list_objects",
    "object_detail",
    "object_file",
    "primitive_names",
    "read_data",
    "retier_notes",
    "skill_facets",
    "skill_users",
    "unit_levels",
    "unit_skill_picker",
]

_DEFAULTS_ZH: Final = {
    "speed": "沒寫＝5",
    "armor_bonus": "沒寫＝0",
    "level": "沒寫＝1",
    "max_mana": "沒寫＝依武器大類",
    "stamina": "沒寫＝依武器大類",
    "cost.stamina": "沒寫＝0",
    "cost.mana": "沒寫＝0",
    "cost.cooldown": "沒寫＝沒有冷卻",
    "stance_upkeep": "沒寫＝0",
    "phases[*].skills": "沒寫＝沿用上一階段",
}

_PART_DEFAULT_ZH: Final = "沒寫＝和本體相同"
"""部位的護甲、抗性、元素修正沒寫時（PB-1n）。"""

_STAT_ZH: Final = {
    "move": "移動下降（格）",
    "armor": "護甲下降（點）",
    "hit": "命中下降（點）",
    "resist.physical": "物理抗性下降（‰）",
    "resist.elemental": "元素抗性下降（‰）",
    "resist.nature": "自然抗性下降（‰）",
    "resist.spirit": "靈性抗性下降（‰）",
    "damage_dealt": "之後造成傷害的倍率（‰；750＝−25%）",
}
"""``stat_down`` 的數量欄位標籤（依 ``stat``；PB-1n）。"""

_SITE_WORDS: Final = {
    "effects": "效果",
    "followup": "第二段",
    "variants": "變奏",
    "add_effect": "追加效果",
    "replace_effect": "替換效果",
    "then": "之後",
    "on_kill": "擊殺時",
    "win": "成功時",
    "lose": "失敗時",
}

type Value = int | str | list[str] | None


class ObjectNotFoundError(LookupError):
    """沒有這個對象（或不在白名單內）。"""


def read_data(path: Path) -> Any:
    return parse_yaml(path.read_bytes().decode("utf-8").removeprefix("﻿"))


def object_file(content_dir: Path, target: TuningTarget, object_id: str) -> Path:
    for path in target_files(content_dir, target):
        if path.stem == object_id:
            return path
    raise ObjectNotFoundError(f"數值工坊沒有這個對象：{target.kind}/{object_id}")


AI_NAME_ZH: Final = "AI 估值表（全體共用）"
"""``ai_profiles.yaml`` 在清單上的名字（PB-1n）。"""

AI_NOTES_ZH: Final = (
    "這份是敵我全體共用的 AI 估值表：改一個值會影響所有戰鬥裡的 AI，不只一隻頭目。",
    "目前只開放頭目部位（parts）的 8 個值，全部是占位；行為模式權重等其他欄位等 NW-3。",
    "「打部位」的值給玩家方隊友 AI 用（決定要不要瞄準部位）；護背扣分與快破門檻給頭目用。",
)
"""AI 估值表表單頂端的唯讀提示（PB-1n）。"""


def _category(data: Any, kind: str) -> Literal["boss", "enemy", "skill", "ai"]:
    if kind == "skill":
        return "skill"
    if kind == "ai":
        return "ai"
    tags = data.get("tags") or ()
    return "boss" if "boss" in tags else "enemy"


# ---------------------------------------------------------------------------
# 路徑展開
# ---------------------------------------------------------------------------


def _phase_label(data: Any, index: int) -> str:
    phase = (data.get("phases") or [])[index]
    return f"第 {index + 1} 階段「{phase.get('name_zh') or phase.get('id')}」"


def _part_group(data: Any, path: str) -> str | None:
    """部位欄位的分組標題（PB-1n 待決 2：表單按部位分組），例「部位 1「拂塵」」；
    其他欄位 ``None``。"""
    parts = parse_path(path)
    if parts[:1] != ("parts",) or len(parts) < 2 or not isinstance(parts[1], int):  # noqa: PLR2004
        return None
    part = (data.get("parts") or [])[parts[1]]
    return f"部位 {parts[1] + 1}「{part.get('name_zh') or part.get('id')}」"


def _part_label(data: Any, parts: Sequence[PathPart], field: TuningField) -> str:
    """部位欄位的標籤（PB-1n）：「部位「拂塵」血量（‰）」；破壞效果的數量依 ``stat`` 換成
    「部位「長劍」破掉後：之後造成傷害的倍率（‰；750＝−25%）」。"""
    index = parts[1]
    assert isinstance(index, int)
    part = (data.get("parts") or [])[index]
    label = f"部位「{part.get('name_zh') or part.get('id')}」"
    if len(parts) > 3 and parts[2] == "on_break" and isinstance(parts[3], int):  # noqa: PLR2004
        effects = part.get("on_break") or []
        stat = str(effects[parts[3]].get("stat") or "")
        which = f"第 {parts[3] + 1} 個效果" if len(effects) > 1 else ""
        return f"{label}破掉後{which}：{_STAT_ZH.get(stat, field.label_zh)}"
    return label + field.label_zh.removeprefix("部位")


def _part_skipped(field: TuningField, data: Any, parts: Sequence[PathPart]) -> bool:
    """``parts[*].on_break[*].*`` 只展開 ``stat_down``（其他破壞效果沒有數量；PB-1n）。"""
    if len(parts) < 4 or parts[0] != "parts" or parts[2] != "on_break":  # noqa: PLR2004
        return False
    try:
        effect = lookup(data, parts[:4])
    except PatchError:
        return True
    return not (isinstance(effect, dict) and effect.get("type") == "stat_down")


def _phase_skipped(field: TuningField, phase: Any) -> bool:
    """``phases[*]`` 的欄位不展開到這個階段：開場階段（沒有 ``trigger``；schema 規定開場階段不能有
    改動，NW-1b 起 ``mana_restore``、NW-2a 起 ``skills`` 也照這條）；``phases[*].trigger.*`` 另外
    只展開 ``hp_below``。"""
    trigger = (phase or {}).get("trigger") if isinstance(phase, dict) else None
    if not trigger:
        return True
    return field.path.startswith("phases[*].trigger.") and trigger.get("kind") != "hp_below"


def _expand(data: Any, parts: Sequence[PathPart]) -> list[tuple[PathPart, ...]]:
    """把每個 ``*`` 換成清單的每個索引（清單不存在就沒有）。"""
    if "*" not in parts:
        return [tuple(parts)]
    star = list(parts).index("*")
    try:
        items = lookup(data, parts[:star])
    except PatchError:
        return []
    out: list[tuple[PathPart, ...]] = []
    for i in range(len(items) if isinstance(items, list) else 0):
        out += _expand(data, (*parts[:star], i, *parts[star + 1 :]))
    return out


def _effect_type(data: Any, parts: Sequence[PathPart]) -> str | None:
    """路徑上最深、而且有 ``type`` 鍵的那一層的 ``type``（效果的原語）。"""
    for end in range(len(parts) - 1, 0, -1):
        try:
            node = lookup(data, parts[:end])
        except PatchError:
            return None
        if isinstance(node, dict) and "type" in node:
            return str(node["type"])
    return None


def _present(data: Any, parts: Sequence[PathPart]) -> bool:
    try:
        found = lookup(data, parts)
    except PatchError:
        return False
    return found is not MISSING and found is not None


def _keep(data: Any, field: TuningField, parts: Sequence[PathPart]) -> bool:
    phase = parts[1] if parts[:1] == ("phases",) and len(parts) > 1 else None
    if isinstance(phase, int) and _phase_skipped(field, (data.get("phases") or [])[phase]):
        return False
    if _part_skipped(field, data, parts):
        return False
    if field.kinds and str(data.get("kind") or "active") not in field.kinds:
        return False
    if field.existing_only and not _present(data, parts):
        return False
    return not field.effect_types or _effect_type(data, parts) in field.effect_types


@cache
def _primitive_names_of(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    table = load_content_file(path, PrimitiveTable)
    names = {p.id: p.name_zh for p in table.primitives}
    names |= {p.id: p.name_zh for p in table.nested_only_effects}
    return names


def primitive_names(content_dir: Path) -> dict[str, str]:
    """原語 ID → 中文名（效果欄位的標籤用）。"""
    return _primitive_names_of(content_dir / "skill_primitives.yaml")


def _site_label(data: Any, parts: Sequence[PathPart], primitives: dict[str, str]) -> str:
    """效果欄位的前綴（例「效果 2（傷害）：」「第二段效果 1（推擊）：」）。"""
    words: list[str] = []
    for part in parts:
        if isinstance(part, int):
            if words:
                words[-1] += f" {part + 1}"
        elif part in _SITE_WORDS:
            words.append(_SITE_WORDS[part])
    kind = _effect_type(data, parts)
    name = primitives.get(kind or "", kind or "")
    return "".join(words) + (f"（{name}）" if name else "") + "："


def concrete_fields(
    data: Any, target: TuningTarget, primitives: dict[str, str] | None = None
) -> list[tuple[TuningField, str, str]]:
    """這個對象實際可改的欄位：``(白名單欄位, 具體路徑, 中文標籤)``。

    ``*`` 展開成每個索引；``phases[*]`` 不展開開場階段、``phases[*].trigger.*`` 只展開
    ``hp_below``（:func:`_phase_skipped`）；``kinds``、``existing_only``、``effect_types`` 照白名單
    篩（NW-2a）。效果層級的欄位標籤前面加效果位置與原語中文名。"""
    names = primitives if primitives is not None else {}
    effect_paths = {f"{s}.{f.path}" for s in target.effect_sites for f in target.effect_fields}
    out: list[tuple[TuningField, str, str]] = []
    for field in target.all_fields():
        for parts in _expand(data, parse_path(field.path)):
            if not _keep(data, field, parts):
                continue
            label = field.label_zh
            if parts[:1] == ("phases",) and len(parts) > 1 and isinstance(parts[1], int):
                label = f"{_phase_label(data, parts[1])}{field.label_zh}"
            elif parts[:1] == ("parts",) and len(parts) > 1 and isinstance(parts[1], int):
                label = _part_label(data, parts, field)
            elif field.path in effect_paths:
                label = f"{_site_label(data, parts, names)}{field.label_zh}"
            out.append((field, format_path(parts), label))
    return out


def field_value(data: Any, path: str) -> Value:
    """磁碟上的現值（整數、骰子字串、ID 清單；沒寫＝``None``）。"""
    try:
        found = lookup(data, parse_path(path))
    except PatchError:
        return None
    if found is MISSING or found is None or isinstance(found, bool):
        return None
    if isinstance(found, int | str):
        return found
    if isinstance(found, list) and all(isinstance(x, str) for x in found):
        return list(found)
    return None


# ---------------------------------------------------------------------------
# 技能的分類與使用者
# ---------------------------------------------------------------------------


def _has_condition(skill: SkillDef) -> bool:
    return skill.condition is not None or any(e.condition is not None for e in skill.effects)


def _single_damage(skill: SkillDef) -> bool:
    return skill.shape.type == "single" and any(e.type == "damage" for e in skill.effects)


def skill_facets(skill: SkillDef, library: ContentLibrary | None) -> TuningSkillFacets:
    """清單篩選用的分類；``library`` 有時另算 1 階預算比例。"""
    shape_range = skill.shape.range
    ratio: int | None = None
    if library is not None:
        ratio = _ratio_permille(skill, library)
    return TuningSkillFacets(
        tier=skill.tier,
        category=skill.category,
        weapon_req=skill.weapon_req,
        ap_cost=skill.ap_cost,
        kind=skill.kind,
        enemy_only=skill.enemy_only,
        has_condition=_has_condition(skill),
        shape=skill.shape.type,
        ranged=skill.weapon_req == "ranged" or (isinstance(shape_range, int) and shape_range >= 2),  # noqa: PLR2004
        tags=list(skill.tags),
        single_damage=skill.shape.type == "single"
        and any(e.type == "damage" for e in skill.effects),
        budget_ratio_permille=ratio,
    )


def _ratio_permille(skill: SkillDef, library: ContentLibrary) -> int | None:
    try:
        report = skill_budget(skill, library)
    except BudgetError:
        return None
    return int((report.ratio * 1000 * 2 + 1) // 2)


def unit_levels(library: ContentLibrary) -> dict[str, set[int]]:
    """大世界裡單位（範本或變體 ID）會出現的等級（R2 提示用）：遭遇表各地點的 ``level_min``
    （陣容、固定精英、加人）、懸賞的等級、賽季頭目的等級。等級另有區域加成（世界事件 +1），
    這裡不算。"""
    levels: dict[str, set[int]] = {}

    def add(name: str, level: int | None) -> None:
        if level is not None:
            levels.setdefault(name, set()).add(level)

    for region in sorted(library.world_encounters):
        table = library.world_encounters[region]
        lmap = library.location_map(region)
        places = lmap.location_by_id() if lmap is not None else {}
        groups = {g.id: g for g in table.groups}
        for loc in table.locations:
            place = places.get(loc.location)
            level = None if place is None else place.level_min
            for weight in loc.groups:
                for name in groups[weight.group].all_units if weight.group in groups else ():
                    add(name, level)
            if loc.elite is not None:
                add(loc.elite.unit, level)
    season = library.world_season
    if season is not None:
        for bounty in season.bounties:
            add(bounty.elite.unit, bounty.level)
        if season.season_boss is not None:
            for name in season.season_boss.units:
                add(name, season.season_boss.level)
    return levels


def _equips(template: UnitTemplate, skill_id: str) -> list[str]:
    where = ["開場"] if skill_id in template.skills else []
    where += [
        f"第 {i + 1} 階段"
        for i, phase in enumerate(template.phases)
        if phase.skills is not None and skill_id in phase.skills
    ]
    return where


def _battle_tier(library: ContentLibrary, levels: dict[str, set[int]], unit_id: str) -> int | None:
    rules = library.world_rules
    found = levels.get(unit_id)
    if rules is None or not found:
        return None
    return max(rules.enemy_growth.tier_for(level) for level in found)


def skill_users(library: ContentLibrary | None, skill_id: str) -> list[TuningSkillUser]:
    """裝了這招的單位（開場或某個階段；``tier`` 是大世界實戰會用的最高階級）與模擬用的 build
    （依 ID 排序）。"""
    if library is None:
        return []
    levels = unit_levels(library)
    out: list[TuningSkillUser] = []
    for unit_id in sorted(library.units):
        unit = library.units[unit_id]
        where = _equips(unit, skill_id)
        if where:
            out.append(
                TuningSkillUser(
                    kind="unit",
                    id=unit_id,
                    name_zh=unit.name_zh,
                    where_zh=where,
                    tier=_battle_tier(library, levels, unit_id),
                )
            )
    catalog = library.enemy_catalog()
    for name in sorted(set(levels) - set(library.units)):  # 變體（world/enemies.yaml）
        try:
            template = catalog.template(name)
        except (KeyError, ValueError):
            continue
        where = _equips(template, skill_id)
        if where:
            out.append(
                TuningSkillUser(
                    kind="unit",
                    id=name,
                    name_zh=template.name_zh,
                    where_zh=where,
                    tier=_battle_tier(library, levels, name),
                )
            )
    for build in sorted(library.builds.builds, key=lambda b: b.id):
        if skill_id in build.hero.skills:
            out.append(
                TuningSkillUser(kind="build", id=build.id, name_zh=build.name_zh, where_zh=[])
            )
    return out


# ---------------------------------------------------------------------------
# 清單與表單
# ---------------------------------------------------------------------------


def list_objects(
    content_dir: Path, table: TuningFields, library: ContentLibrary | None = None
) -> list[TuningObjectSummary]:
    out: list[TuningObjectSummary] = []
    for target in table.targets:
        for path in target_files(content_dir, target):
            data = read_data(path)
            facets = None
            if target.kind == "skill":
                facets = skill_facets(SkillDef.model_validate(data), library)
            out.append(
                TuningObjectSummary(
                    kind=target.kind,
                    id=path.stem,
                    name_zh=AI_NAME_ZH
                    if target.kind == "ai"
                    else str(data.get("name_zh") or path.stem),
                    category=_category(data, target.kind),
                    file=path.relative_to(content_dir).as_posix(),
                    skill=facets,
                )
            )
    return out


def _armor_notes(library: ContentLibrary | None, unit_id: str) -> list[str]:
    if library is None:
        return []
    notes: list[str] = []
    for region in sorted(library.world_encounters):
        for loc in library.world_encounters[region].locations:
            mods = loc.armor_mods
            if mods is not None and mods.unit == unit_id:
                notes.append(
                    f"實戰時另有遭遇護甲調整（{region}／{loc.location}，"
                    f"{mods.min_total:+d}～{mods.max_total:+d}，依劇情旗標；數值工坊 NW-3 才開）"
                )
    return notes


@cache
def _tables(content_dir: Path) -> tuple[PrimitiveTable | None, ShapeTable | None]:
    prim = content_dir / "skill_primitives.yaml"
    shapes = content_dir / "skill_shapes.yaml"
    return (
        load_content_file(prim, PrimitiveTable) if prim.is_file() else None,
        load_content_file(shapes, ShapeTable) if shapes.is_file() else None,
    )


def _default_zh(field: TuningField) -> str | None:
    if field.path.startswith("parts[*].") and field.path != "parts[*].hp_permille":
        return _PART_DEFAULT_ZH
    return _DEFAULTS_ZH.get(field.path)


def _part_limits(data: Any, parts: Sequence[PathPart]) -> tuple[int | None, int | None]:
    """部位欄位擋的範圍（schema：``content/parts.py``）。"""
    leaf = parts[-1]
    if leaf == "hp_permille":
        return 1, 1000
    if parts[2:3] == ("resist",):
        return -1000, 1000
    if leaf == "amount":
        effect = lookup(data, parts[:4])
        return (1, 999) if effect.get("stat") == "damage_dealt" else (1, None)
    return None, None


def field_limits(
    content_dir: Path, data: Any, field: TuningField, path: str
) -> tuple[int | None, int | None]:
    """原語或形狀表上的範圍（擋的範圍；畫面只顯示）。"""
    parts = parse_path(path)
    if parts[:1] == ("parts",) and len(parts) > 1:
        if isinstance(parts[1], int):
            return _part_limits(data, parts)
        return (0, 1000) if parts[-1] == "near_break_permille" else (0, None)  # AI 估值表
    prims, shapes = _tables(content_dir)
    leaf = parts[-1]
    if field.effect_types and prims is not None:
        kind = _effect_type(data, parts)
        defs = {p.id: p.params for p in prims.primitives}
        defs |= {p.id: p.params for p in prims.nested_only_effects}
        spec = defs.get(kind or "", {}).get(str(leaf))
        return (spec.min, spec.max) if spec is not None else (None, None)
    if len(parts) >= 2 and parts[-2] == "shape" and shapes is not None:  # noqa: PLR2004
        shape = lookup(data, parts[:-1])
        found = next((s for s in shapes.shapes if s.id == shape.get("type")), None)
        if found is not None:
            spec2 = {**found.params, **found.content_params}.get(str(leaf))
            if spec2 is not None:
                return spec2.min, spec2.max
    return None, None


RETIER_NOTE_ZH: Final = "這招在 2 階以上會依預算比例重算（夾在 70～100%），超出的部分只在 1 階有效"
"""R2（使用者 2026-11-12「照建議」）：維持現行升階規則（``retier``），只在表單頂端提示。"""


def retier_notes(skill: SkillDef, users: Sequence[TuningSkillUser]) -> list[str]:
    """技能表單頂端的唯讀提示：升階重算（R2）＋實戰會用升階版的單位（等級→階級）。"""
    notes = [RETIER_NOTE_ZH]
    upgraded = [u for u in users if u.kind == "unit" and u.tier is not None and u.tier > skill.tier]
    if upgraded:
        names = "、".join(f"{u.name_zh}（{u.id}，{u.tier} 階）" for u in upgraded)
        notes.append(f"實戰會用升階版（_t<階>）的單位：{names}；改 1 階的數字對它們可能沒有影響")
    else:
        notes.append("目前沒有單位在大世界實戰用這招的升階版（玩家角色升階時另依比例重算）")
    return notes


def _readonly(field: TuningField, value: Value) -> str | None:
    if field.kind == "range" and value == "weapon":
        return "武器射程：改成數字會改變技能和武器的綁定，屬結構，不在數值工坊改"
    return None


_CLASS_ZH: Final = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}


def unit_skill_picker(
    content_dir: Path, table: TuningFields, template: UnitTemplate, library: ContentLibrary | None
) -> TuningUnitSkills | None:
    """招式組編輯器用（NW-2b B5）：單位的武器、欄位上限，以及數值工坊開放的技能裡哪些和這個單位
    的武器不相容（同載入檢查的 ``weapon_problem``；欄位上限、敵人專用招由整包驗證擋）。"""
    skills_target = table.target("skill")
    if library is None or skills_target is None:
        return None
    weapon = library.weapons.get(template.weapon)
    if weapon is None:
        return None
    try:
        held = loadout_held(weapon, library.loadout_of(template))
    except ValueError:
        held = loadout_held(weapon, None)
    problems: dict[str, str] = {}
    for path in target_files(content_dir, skills_target):
        skill = library.skills.get(path.stem)
        if skill is None:
            continue
        problem = weapon_problem(skill, weapon.weapon_class, held)
        if problem is not None:
            problems[path.stem] = problem
    slots = library.ruleset.core.skill_slots
    return TuningUnitSkills(
        weapon_zh=f"{weapon.name_zh}（{_CLASS_ZH.get(weapon.weapon_class, weapon.weapon_class)}）",
        slots_zh=(
            f"主動 {slots.active}、被動 {slots.passive}、反應 {slots.reaction}、姿態 {slots.stance}"
        ),
        problems=problems,
    )


def object_detail(
    content_dir: Path,
    table: TuningFields,
    kind: str,
    object_id: str,
    library: ContentLibrary | None = None,
) -> TuningObjectDetail:
    target = table.target(kind)
    if target is None:
        raise ObjectNotFoundError(f"數值工坊沒有這類對象：{kind}")
    path = object_file(content_dir, target, object_id)
    data = read_data(path)
    primitives = primitive_names(content_dir)
    fields: list[TuningFieldView] = []
    for field, concrete, label in concrete_fields(data, target, primitives):
        value = field_value(data, concrete)
        low, high = field_limits(content_dir, data, field, concrete)
        fields.append(
            TuningFieldView(
                path=concrete,
                pattern=field.path,
                label_zh=label,
                kind=field.kind,
                value=value,
                default_zh=_default_zh(field) if value is None else None,
                hint_min=field.hint_min,
                hint_max=field.hint_max,
                limit_min=low,
                limit_max=high,
                readonly_zh=_readonly(field, value),
                note_zh=field.note_zh,
                group_zh=_part_group(data, concrete),
            )
        )
    if kind == "skill":
        skill = SkillDef.model_validate(data)
        users = skill_users(library, skill.id)
        return TuningObjectDetail(
            kind=kind,
            id=object_id,
            name_zh=skill.name_zh,
            category="skill",
            file=path.relative_to(content_dir).as_posix(),
            fields=fields,
            notes_zh=retier_notes(skill, users),
            skill=skill_facets(skill, library),
            used_by=users,
        )
    if kind == "ai":
        return TuningObjectDetail(
            kind=kind,
            id=object_id,
            name_zh=AI_NAME_ZH,
            category="ai",
            file=path.relative_to(content_dir).as_posix(),
            fields=fields,
            notes_zh=list(AI_NOTES_ZH),
        )
    template = UnitTemplate.model_validate(data)
    notes = ["大世界的敵人另依遭遇等級成長（grow_enemy），這裡改的是單位檔的基礎值。"]
    notes += _armor_notes(library, template.id)
    return TuningObjectDetail(
        kind=kind,
        id=object_id,
        name_zh=template.name_zh,
        category=_category(data, kind),
        file=path.relative_to(content_dir).as_posix(),
        fields=fields,
        notes_zh=notes,
        unit_skills=unit_skill_picker(content_dir, table, template, library),
    )
