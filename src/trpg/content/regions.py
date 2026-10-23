"""區域主題表（``content/regions.yaml``，Phase 3-37a）與地圖 ``region``／``look`` 的清理。

純顯示資料：不進引擎結算。未知的 ``region``、``look`` 鍵或值不會讓地圖載入失敗，而是被丟棄
（退回預設畫法）並回傳警告文字。
"""

from __future__ import annotations

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.maps import MapDef
from trpg.content.schemas import ContentModel

__all__ = ["LookKeyDef", "RegionDef", "RegionTable", "sanitize_map_theme"]


class RegionDef(ContentModel):
    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    look: dict[str, str] = Field(default_factory=dict)
    """該區的預設覆寫（地圖檔的 ``look`` 會蓋過它）。"""


class LookKeyDef(ContentModel):
    key: str = Field(pattern=ID_PATTERN)
    values: tuple[str, ...] = ()


class RegionTable(ContentModel):
    default_region: str = Field(pattern=ID_PATTERN)
    regions: tuple[RegionDef, ...] = Field(min_length=1)
    look_keys: tuple[LookKeyDef, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> RegionTable:
        ids = [r.id for r in self.regions]
        if len(set(ids)) != len(ids):
            raise ValueError("區域 ID 重複")
        if self.default_region not in ids:
            raise ValueError(f"default_region {self.default_region} 不在 regions 內")
        keys = [k.key for k in self.look_keys]
        if len(set(keys)) != len(keys):
            raise ValueError("look 鍵重複")
        for region in self.regions:
            problems = self.look_problems(region.look)
            if problems:
                raise ValueError(f"區域 {region.id} 的 look：{'；'.join(problems)}")
        return self

    def region_by_id(self) -> dict[str, RegionDef]:
        return {r.id: r for r in self.regions}

    def look_problems(self, look: dict[str, str]) -> list[str]:
        allowed = {k.key: k.values for k in self.look_keys}
        out: list[str] = []
        for key in sorted(look):
            if key not in allowed:
                out.append(f"未知的 look 鍵 {key!r}")
            elif look[key] not in allowed[key]:
                out.append(f"look.{key} 的值 {look[key]!r} 未知")
        return out

    def summary(self) -> str:
        return f"{len(self.regions)} 區、{len(self.look_keys)} 種 look 覆寫"


def sanitize_map_theme(map_def: MapDef, table: RegionTable) -> tuple[MapDef, list[str]]:
    """丟掉未知的 ``region``／``look``，並把區域的預設 ``look`` 併入（地圖檔的蓋過區域的）。

    回傳（新的地圖定義，警告列表）；不拋出例外。
    """
    warnings: list[str] = []
    region = map_def.region
    base: dict[str, str] = {}
    if region is not None:
        found = table.region_by_id().get(region)
        if found is None:
            warnings.append(f"地圖 {map_def.id}：未知的 region {region!r}，改用預設畫法")
            region = None
        else:
            base = dict(found.look)
    allowed = {k.key: k.values for k in table.look_keys}
    look = dict(base)
    for key in sorted(map_def.look):
        value = map_def.look[key]
        if key not in allowed:
            warnings.append(f"地圖 {map_def.id}：未知的 look 鍵 {key!r}，已忽略")
        elif value not in allowed[key]:
            warnings.append(f"地圖 {map_def.id}：look.{key} 的值 {value!r} 未知，已忽略")
        else:
            look[key] = value
    if region == map_def.region and look == map_def.look:
        return map_def, warnings
    return map_def.model_copy(update={"region": region, "look": look}), warnings
