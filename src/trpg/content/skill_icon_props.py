"""技能圖示道具的允許清單（Phase IP-1，06 6.36，#151；資料檔 ``content/skill_icon_props.yaml``）。

技能的選填欄位 ``icon_prop``（:attr:`trpg.content.skills.SkillDef.icon_prop`）只能填這張清單裡的值，
而且要和技能的武器大類（``weapon_req``）對得上：

- 道具有 ``weapon_class``（近戰、遠程、法器）時，技能的 ``weapon_req`` 必須相同，或是 ``any``；
- 道具沒有 ``weapon_class``（拳腳、投擲這類中性道具，元素、召喚、化身類道具，``none``）時不限大類。

只影響圖示：不進引擎結算、預算、重播與出題。清單由美術 PM 維護（``docs/art/技能圖示道具清單.md``
第 1 節），這裡是它的資料版。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from trpg.content.schemas import ContentModel, duplicates

__all__ = [
    "ICON_PROP_PATTERN",
    "IconPropDef",
    "IconPropGroup",
    "IconPropTable",
    "icon_prop_problem",
]

ICON_PROP_PATTERN = r"^(?:none|(?:w|el|summon|form):[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_]*)?)$"
"""道具值的格式：``none``，或 ``前綴:名稱``（``w:sword/arcane`` 這種帶形制的也可以）。"""

type IconPropGroup = Literal["weapon", "offhand", "neutral", "element", "summon", "form", "special"]
"""美術清單第 1 節的分類：武器、副手、中性、元素、召喚物、化身、特殊值。"""

_CLASS_ZH = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}


class IconPropDef(ContentModel):
    """一個道具值。"""

    id: str = Field(pattern=ICON_PROP_PATTERN)
    name_zh: str = Field(min_length=1)
    group: IconPropGroup
    weapon_class: Literal["melee", "ranged", "focus"] | None = None
    """適用的武器大類；``None`` ＝ 不限（任何技能都能填）。"""


class IconPropTable(ContentModel):
    """``content/skill_icon_props.yaml``。"""

    props: tuple[IconPropDef, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> IconPropTable:
        dup = duplicates(p.id for p in self.props)
        if dup:
            raise ValueError(f"圖示道具 ID 重複：{', '.join(dup)}")
        return self

    def by_id(self) -> dict[str, IconPropDef]:
        return {p.id: p for p in self.props}

    def summary(self) -> str:
        return f"{len(self.props)} 個圖示道具"


def icon_prop_problem(icon_prop: str, weapon_req: str, table: IconPropTable) -> str | None:
    """``icon_prop`` 不在允許清單、或和技能的 ``weapon_req`` 對不上時的原因；合格時 ``None``。"""
    prop = table.by_id().get(icon_prop)
    if prop is None:
        return f"icon_prop {icon_prop!r} 不在圖示道具清單（skill_icon_props.yaml）裡"
    if prop.weapon_class is None or weapon_req in ("any", prop.weapon_class):
        return None
    need = _CLASS_ZH[prop.weapon_class]
    have = _CLASS_ZH.get(weapon_req, weapon_req)
    return f"icon_prop {icon_prop!r}（{prop.name_zh}）是{need}道具，與技能的武器需求（{have}）不符"
