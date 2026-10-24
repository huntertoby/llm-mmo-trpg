"""裝備外觀清單的 schema 與推導（Phase 3G-G5a；資料檔 ``content/equipment/appearance.yaml``）。

外觀只由資料欄位決定、不影響任何規則（美術 PM 的 ``docs/art/裝備外觀移植需求.md``）：

- 物品（:class:`~trpg.content.equipment.ItemDef`）選填 ``kind``（造型）、``form``（形制）、
  ``material``（材質）、``dye``（染色，只對布、皮有效）、``style``（風格，目前只有 ``common``）、
  ``rarity``。
- ``keywords`` **不是人填的**：由物品的詞條推導（:func:`derive_keywords`，取前 2 個），關鍵字 id 與
  ``skill_keywords.yaml``（Phase 3-24b1）一致。
- 不認得的值一律退回預設（前端 ``render/gearIcon.ts`` 的 ``resolveGear``）；本檔的
  :func:`item_appearance_problems` 只用來檢查 **本專案寫在 items.yaml 裡的物品** 有沒有寫錯。

前端用的清單由 ``scripts/export_appearance.py`` 匯出成 ``client/src/render/gearAppearance.json``。
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.equipment import AffixDef, AttackAffix, ItemDef, KeywordAffix
from trpg.content.schemas import ContentModel
from trpg.content.slots import SlotType
from trpg.shared.types import Element

__all__ = [
    "AppearanceTable",
    "FormDef",
    "KindDef",
    "appearance_export",
    "appearance_json",
    "derive_keywords",
    "item_appearance_problems",
]

ELEMENT_KEYWORD: dict[Element, str] = {
    Element.FIRE: "ignite",
    Element.LIGHTNING: "charged",
    Element.ICE: "frozen",
}
"""普攻附加元素 → 關鍵字（水不是元素，潮濕沒有對應的普攻附加）。"""

STATUS_KEYWORD: dict[str, str] = {"marked": "marked"}
"""普攻命中時施加的狀態 → 關鍵字。"""

KEYWORD_ALIASES: dict[str, str] = {"shock": "charged"}
"""詞條裡暫定的關鍵字寫法（``affixes.yaml``）→ 3-24b1 的關鍵字 id。"""


class FormDef(ContentModel):
    """一個形制；可以限定自己的材質與預設材質（例如頭冠預設金、頭巾預設布）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    materials: tuple[str, ...] | None = None
    default_material: str | None = Field(default=None, pattern=ID_PATTERN)


class KindDef(ContentModel):
    """一個造型：欄位種類、形制、可用材質與預設材質。"""

    id: str = Field(pattern=ID_PATTERN)
    slot_type: SlotType
    name_zh: str = Field(min_length=1)
    paired: bool = False
    forms: tuple[FormDef, ...] = Field(min_length=1)
    materials: tuple[str, ...] = Field(min_length=1)
    default_material: str = Field(pattern=ID_PATTERN)

    def form_materials(self, form: FormDef) -> tuple[str, ...]:
        return form.materials if form.materials is not None else self.materials

    def form_default(self, form: FormDef) -> str:
        return form.default_material if form.default_material is not None else self.default_material


class AppearanceTable(ContentModel):
    """``content/equipment/appearance.yaml``。"""

    styles: tuple[str, ...] = Field(min_length=1)
    materials: tuple[str, ...] = Field(min_length=1)
    dyes: tuple[str, ...]
    dye_materials: tuple[str, ...]
    rarities: tuple[str, ...] = Field(min_length=1)
    max_keywords: int = Field(ge=1)
    keywords: tuple[str, ...]
    element_keywords: tuple[str, ...]
    kinds: tuple[KindDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> AppearanceTable:
        for label, values in (
            ("風格", self.styles),
            ("材質", self.materials),
            ("染色", self.dyes),
            ("稀有度", self.rarities),
            ("關鍵字", self.keywords),
            ("造型", [k.id for k in self.kinds]),
        ):
            dup = sorted(v for v, n in Counter(values).items() if n > 1)
            if dup:
                raise ValueError(f"外觀清單的{label}重複：{', '.join(dup)}")
        if "common" not in self.styles or "common" not in self.rarities:
            raise ValueError("外觀清單必須有 common 風格與 common 稀有度（預設值）")
        if not set(self.dye_materials) <= set(self.materials):
            raise ValueError("dye_materials 必須是材質清單的子集")
        if not set(self.element_keywords) <= set(self.keywords):
            raise ValueError("element_keywords 必須是 keywords 的子集")
        for kind in self.kinds:
            self._check_kind(kind)
        return self

    def _check_kind(self, kind: KindDef) -> None:
        known = set(self.materials)
        forms = [f.id for f in kind.forms]
        if len(set(forms)) != len(forms):
            raise ValueError(f"造型 {kind.id}：形制重複")
        if not set(kind.materials) <= known or kind.default_material not in kind.materials:
            raise ValueError(f"造型 {kind.id}：材質必須在材質清單內，且預設材質在可用材質內")
        for form in kind.forms:
            allowed = kind.form_materials(form)
            if not set(allowed) <= known or kind.form_default(form) not in allowed:
                raise ValueError(f"造型 {kind.id} 的形制 {form.id}：材質或預設材質不合法")

    def kind_by_id(self) -> dict[str, KindDef]:
        return {k.id: k for k in self.kinds}

    def summary(self) -> str:
        forms = sum(len(k.forms) for k in self.kinds)
        return f"{len(self.kinds)} 個造型、{forms} 個形制、{len(self.materials)} 種材質"


def derive_keywords(affixes: Iterable[AffixDef], limit: int = 2) -> tuple[str, ...]:
    """由詞條推導外觀關鍵字（依詞條順序、去重、取前 ``limit`` 個）。

    - 第 3 類（技能強化）：詞條的 ``keyword``（暫定寫法先對照 :data:`KEYWORD_ALIASES`）；
    - 第 4 類（普攻附加）：``add_element``／``weapon_element``（3K-1）對照 :data:`ELEMENT_KEYWORD`、
      ``on_hit_status`` 對照 :data:`STATUS_KEYWORD`。
    其他類別不產生關鍵字。結果可能含前端不認得的 id（前端會跳過）。
    """
    found: list[str] = []
    for affix in affixes:
        keyword: str | None = None
        if isinstance(affix, KeywordAffix):
            keyword = KEYWORD_ALIASES.get(affix.keyword, affix.keyword)
        elif isinstance(affix, AttackAffix):
            element = affix.add_element or affix.weapon_element
            if element is not None:
                keyword = ELEMENT_KEYWORD.get(element)
            elif affix.on_hit_status is not None:
                keyword = STATUS_KEYWORD.get(affix.on_hit_status)
        if keyword is not None and keyword not in found:
            found.append(keyword)
    return tuple(found[:limit])


def item_appearance_problems(item: ItemDef, table: AppearanceTable) -> list[str]:
    """``items.yaml`` 裡的物品寫了外觀欄位時，檢查值都認得且彼此相容（沒寫的欄位不檢查）。"""
    kinds = table.kind_by_id()
    problems: list[str] = []
    if item.kind is not None:
        kind = kinds.get(item.kind)
        if kind is None:
            return [f"物品 {item.id}：未知的造型 {item.kind!r}"]
        if kind.slot_type != item.slot_type:
            problems.append(
                f"物品 {item.id}：造型 {kind.id} 屬於 {kind.slot_type}，不是 {item.slot_type}"
            )
        if kind.paired != item.paired:
            problems.append(f"物品 {item.id}：造型 {kind.id} 的 paired 必須是 {kind.paired}")
        problems += _form_material_problems(item, kind)
    elif item.form is not None or item.material is not None:
        problems.append(f"物品 {item.id}：填了 form／material 就要填 kind")
    if item.dye is not None:
        if item.dye not in table.dyes:
            problems.append(f"物品 {item.id}：未知的染色 {item.dye!r}")
        elif item.material is not None and item.material not in table.dye_materials:
            problems.append(f"物品 {item.id}：染色只對 {', '.join(table.dye_materials)} 有效")
    if item.style is not None and item.style not in table.styles:
        problems.append(f"物品 {item.id}：未知的風格 {item.style!r}")
    if item.rarity is not None and item.rarity not in table.rarities:
        problems.append(f"物品 {item.id}：未知的稀有度 {item.rarity!r}")
    return problems


def _form_material_problems(item: ItemDef, kind: KindDef) -> list[str]:
    form = next((f for f in kind.forms if f.id == item.form), None)
    if item.form is not None and form is None:
        return [f"物品 {item.id}：造型 {kind.id} 沒有形制 {item.form!r}"]
    allowed = kind.form_materials(form) if form is not None else kind.materials
    if item.material is not None and item.material not in allowed:
        return [f"物品 {item.id}：材質 {item.material!r} 不在允許內（{', '.join(allowed)}）"]
    return []


def appearance_export(table: AppearanceTable) -> dict[str, object]:
    """前端用的清單（``client/src/render/gearAppearance.json``；鍵為 camelCase，順序固定）。"""
    return {
        "styles": list(table.styles),
        "materials": list(table.materials),
        "dyes": list(table.dyes),
        "dyeMaterials": list(table.dye_materials),
        "rarities": list(table.rarities),
        "maxKeywords": table.max_keywords,
        "keywords": list(table.keywords),
        "elementKeywords": list(table.element_keywords),
        "kinds": [
            {
                "id": k.id,
                "slotType": k.slot_type,
                "zh": k.name_zh,
                "paired": k.paired,
                "materials": list(k.materials),
                "defaultMaterial": k.default_material,
                "forms": [
                    {
                        "id": f.id,
                        "zh": f.name_zh,
                        "materials": list(k.form_materials(f)),
                        "defaultMaterial": k.form_default(f),
                    }
                    for f in k.forms
                ],
            }
            for k in table.kinds
        ],
    }


def appearance_json(table: AppearanceTable) -> str:
    """:func:`appearance_export` 的固定格式文字（縮排 2、保留中文、結尾換行）。"""
    return json.dumps(appearance_export(table), ensure_ascii=False, indent=2) + "\n"
