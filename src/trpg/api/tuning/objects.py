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
)
from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup
from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.loader import load_content_file, parse_yaml
from trpg.content.skills import SkillDef
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
    "ObjectNotFoundError",
    "concrete_fields",
    "field_limits",
    "field_value",
    "list_objects",
    "object_detail",
    "object_file",
    "primitive_names",
    "read_data",
    "skill_facets",
    "skill_users",
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


def _category(data: Any, kind: str) -> Literal["boss", "enemy", "skill"]:
    if kind == "skill":
        return "skill"
    tags = data.get("tags") or ()
    return "boss" if "boss" in tags else "enemy"


# ---------------------------------------------------------------------------
# 路徑展開
# ---------------------------------------------------------------------------


def _phase_label(data: Any, index: int) -> str:
    phase = (data.get("phases") or [])[index]
    return f"第 {index + 1} 階段「{phase.get('name_zh') or phase.get('id')}」"


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
        budget_ratio_permille=ratio,
    )


def _ratio_permille(skill: SkillDef, library: ContentLibrary) -> int | None:
    try:
        report = skill_budget(skill, library)
    except BudgetError:
        return None
    return int((report.ratio * 1000 * 2 + 1) // 2)


def skill_users(library: ContentLibrary | None, skill_id: str) -> list[TuningSkillUser]:
    """裝了這招的單位（開場或某個階段）與模擬用的 build（依 ID 排序）。"""
    if library is None:
        return []
    out: list[TuningSkillUser] = []
    for unit_id in sorted(library.units):
        unit = library.units[unit_id]
        where = ["開場"] if skill_id in unit.skills else []
        where += [
            f"第 {i + 1} 階段"
            for i, phase in enumerate(unit.phases)
            if phase.skills is not None and skill_id in phase.skills
        ]
        if where:
            out.append(
                TuningSkillUser(kind="unit", id=unit_id, name_zh=unit.name_zh, where_zh=where)
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
                    name_zh=str(data.get("name_zh") or path.stem),
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


def field_limits(
    content_dir: Path, data: Any, field: TuningField, path: str
) -> tuple[int | None, int | None]:
    """原語或形狀表上的範圍（擋的範圍；畫面只顯示）。"""
    prims, shapes = _tables(content_dir)
    parts = parse_path(path)
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


def _readonly(field: TuningField, value: Value) -> str | None:
    if field.kind == "range" and value == "weapon":
        return "武器射程：改成數字會改變技能和武器的綁定，屬結構，不在數值工坊改"
    return None


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
                default_zh=_DEFAULTS_ZH.get(field.path) if value is None else None,
                hint_min=field.hint_min,
                hint_max=field.hint_max,
                limit_min=low,
                limit_max=high,
                readonly_zh=_readonly(field, value),
                note_zh=field.note_zh,
            )
        )
    if kind == "skill":
        skill = SkillDef.model_validate(data)
        return TuningObjectDetail(
            kind=kind,
            id=object_id,
            name_zh=skill.name_zh,
            category="skill",
            file=path.relative_to(content_dir).as_posix(),
            fields=fields,
            notes_zh=[],
            skill=skill_facets(skill, library),
            used_by=skill_users(library, skill.id),
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
    )
