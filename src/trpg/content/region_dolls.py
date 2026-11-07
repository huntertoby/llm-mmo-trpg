"""盜賊三套的區域外觀（``content/ui/region_dolls.yaml``，Phase QK-8）。

設計見 ``docs/design/18-雲嶺內容.md`` 18.5.1 第 1 條與 ``docs/art/QK移植需求.md`` 8.5。純前端資料：
前端 ``client/src/render/qNpcRegion.ts`` 在 build 時匯入同一份檔，戰場在表上的區域時，把表上範本的
紙娃娃外觀換成這裡的（武器、詞綴、特徵照範本）；Python 端只驗證 schema（``trpg content check``），
不進引擎結算。範本 ID 是否存在由 ``tests/content/test_region_dolls.py`` 對照
``content/units/`` 檢查。
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN, DollLook
from trpg.content.schemas import ContentModel

__all__ = ["RegionDollTable"]

Id = Annotated[str, Field(pattern=ID_PATTERN)]


class RegionDollTable(ContentModel):
    """``content/ui/region_dolls.yaml``：區域 ID → 範本 ID → 紙娃娃外觀。"""

    regions: dict[Id, dict[Id, DollLook]] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> RegionDollTable:
        for region in sorted(self.regions):
            table = self.regions[region]
            if not table:
                raise ValueError(f"{region}：至少要有一個範本")
            for template in sorted(table):
                doll = table[template]
                if doll.creature is not None:
                    raise ValueError(f"{region}／{template}：區域外觀只換紙娃娃，不能寫 creature")
                if doll.main_kind is not None:
                    raise ValueError(f"{region}／{template}：武器照範本，不能寫 main_kind")
        return self

    def doll_for(self, region: str | None, template: str) -> DollLook | None:
        """該區該範本的外觀；不在表上為 ``None``（照範本）。"""
        if region is None:
            return None
        return self.regions.get(region, {}).get(template)

    def summary(self) -> str:
        n = sum(len(t) for t in self.regions.values())
        return f"{len(self.regions)} 區、{n} 筆範本區域外觀"
