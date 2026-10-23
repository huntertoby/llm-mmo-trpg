"""技能工坊的「戰場變奏」步驟（Phase 3-25b，``docs/design/06-技能.md`` 6.24）。

稀有以上的主動技能（不是複合、陷阱、被動）在稀有度之後多一步：加 1～2 個變奏（稀有 1 個、史詩以上
2 個，數量上限取自 ``core.yaml`` 的 ``variant_max_by_rarity``）。每個變奏 ＝ id、型態名、條件
（四種恰好一種）＋ 替換內容 1～2 項。欄位的選項沿用既有推導：形狀取自骨架的形狀步驟、附帶效果取自
效果步驟的原語（只列幾個不需要複雜參數的）；schema 與預算的檢查仍由
:class:`~trpg.content.skills.SkillDef` 與驗證器負責（錯誤顯示在即時檢查）。
替換既有附帶效果（``replace_effect``）工坊不提供，用進階 YAML 編輯。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.shared.types import Element, Surface
from trpg.skillgen.draft import Draft
from trpg.skillgen.option_models import Choice, FieldSpec

__all__ = ["variant_fields", "variant_notes", "variants_visible"]

type EffectChoices = Callable[[Draft, ContentLibrary, SkeletonDef], list[Choice]]
type ShapeChoices = Callable[[Draft, ContentLibrary, SkeletonDef], tuple[Choice, ...]]

_ADD_EFFECTS = ("knock_prone", "apply_status", "push", "pull", "create_surface")
"""變奏「加一個附帶效果」可選的原語（工坊只列這幾個，其他用進階 YAML）。"""


def variants_visible(draft: Draft, library: ContentLibrary) -> bool:
    """只有稀有以上、已選骨架的主動技能（不是複合、陷阱、被動、修正）顯示變奏步驟。"""
    rarity = draft.get("rarity")
    cap = library.ruleset.core.variant_max_by_rarity.get(str(rarity), 0)
    return (
        cap > 0
        and draft.get("kind", "active") == "active"
        and draft.get("followup") is None
        and draft.get("trap") is None
        and draft.get("activation") is None
    )


def variant_notes(draft: Draft, library: ContentLibrary) -> tuple[str, ...]:
    cap = library.ruleset.core.variant_max_by_rarity.get(str(draft.get("rarity")), 0)
    rate = library.budget.variant_surcharge_permille
    step = library.budget.variant_range_step_permille
    return (
        f"這個稀有度最多 {cap} 個變奏（稀有 1 個、史詩以上 2 個）",
        f"基礎型態每多一個變奏預算多算 {rate / 10:g}%；每個型態各自都要落在預算窗內",
        f"變奏的射程每 +1 格，該型態多算基礎點數的 {step / 10:g}%（−1 不折抵）",
        "替換內容填 1～2 項；不能改 AP、冷卻、代價；帶變奏的技能不能含區域、延遲傷害、複製技能",
        "替換既有附帶效果請用進階 YAML",
    )


def _surface_choices(library: ContentLibrary) -> tuple[Choice, ...]:
    return tuple(
        Choice(value=s.id.value, name_zh=s.name_zh)
        for s in library.ruleset.surfaces.surfaces
        if s.id is not Surface.NONE
    )


def _when_field(library: ContentLibrary) -> FieldSpec:
    surfaces = _surface_choices(library)
    return FieldSpec(
        field="when",
        name_zh="條件",
        description_zh="恰好填一種：站在某種表面、居高、身旁有牆、目標點在某種表面",
        type="object",
        required=True,
        fields=(
            FieldSpec(
                field="caster_surface",
                name_zh="施放者站在這些表面上",
                type="multi_choice",
                choices=surfaces,
            ),
            FieldSpec(
                field="caster_high_ground",
                name_zh="施放者比目標點高至少 1 層",
                type="bool",
            ),
            FieldSpec(
                field="caster_adjacent_blocker",
                name_zh="施放者身旁（八方向）有牆壁或擋路物件",
                type="bool",
            ),
            FieldSpec(
                field="target_surface",
                name_zh="目標點在這些表面上",
                type="multi_choice",
                choices=surfaces,
            ),
        ),
    )


def _element_field() -> FieldSpec:
    return FieldSpec(
        field="element",
        name_zh="換元素",
        description_zh="把所有傷害效果的元素換掉",
        type="choice",
        choices=tuple(Choice(value=e.value, name_zh=e.display_name) for e in Element),
    )


def variant_fields(
    draft: Draft,
    library: ContentLibrary,
    skeleton: SkeletonDef,
    effect_choices: EffectChoices,
    shape_choices: ShapeChoices,
) -> tuple[FieldSpec, ...]:
    """變奏步驟的欄位：一個 ``variants`` 列表，每項的子欄位見模組說明。"""
    cap = library.ruleset.core.variant_max_by_rarity.get(str(draft.get("rarity")), 0)
    adds = tuple(c for c in effect_choices(draft, library, skeleton) if c.value in _ADD_EFFECTS)
    items: list[FieldSpec] = [
        FieldSpec(
            field="id",
            name_zh="型態代碼",
            description_zh="小寫英文與底線，技能內不可重複（例：tide_pierce）",
            type="text",
            required=True,
            auto_generated=True,
        ),
        FieldSpec(
            field="name_zh",
            name_zh="型態名",
            description_zh="例：水中貫穿",
            type="text",
            required=True,
        ),
        _when_field(library),
        FieldSpec(
            field="shape",
            name_zh="換形狀",
            description_zh="整個換掉（替換內容 1～2 項擇一或兩項）",
            type="choice",
            choices=shape_choices(draft, library, skeleton),
        ),
        FieldSpec(
            field="range_delta",
            name_zh="射程 ±",
            description_zh="結果至少 1；+1 格約加基礎點數 5%",
            type="int",
            min=-3,
            max=3,
        ),
        _element_field(),
    ]
    if adds:
        items.append(
            FieldSpec(
                field="add_effect",
                name_zh="加一個附帶效果",
                type="choice",
                choices=adds,
            )
        )
    return (
        FieldSpec(
            field="variants",
            name_zh="戰場變奏",
            description_zh="條件成立時自動換成這個型態（可省略）",
            type="variants",
            min_count=0,
            max_count=cap,
            fields=tuple(items),
        ),
    )
