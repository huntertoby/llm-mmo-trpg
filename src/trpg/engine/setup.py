"""戰鬥設定：地圖、規則包、參戰單位（``start_battle`` 的輸入）。

``BattleSetup`` 內嵌完整的內容資料（地圖、規則、單位範本、武器），可序列化寫入戰鬥紀錄，
讓重播不依賴當下的資料檔。
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import UnitTemplate, WeaponDef
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.maps import MapDef
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team

__all__ = ["BattleSetup", "BattleSetupError", "UnitSpawn", "build_setup"]


class BattleSetupError(TrpgError):
    """戰鬥設定不合法（例如起始位置衝突、某一方沒有單位）。"""


class UnitSpawn(BaseModel):
    """一個參戰單位。``position`` 為 ``None`` 時依起始區順序自動排列。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    template: UnitTemplate
    weapon: WeaponDef
    team: Team
    position: tuple[int, int] | None = None


class BattleSetup(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    map: MapDef
    ruleset: Ruleset
    units: tuple[UnitSpawn, ...] = Field(min_length=2)
    max_rounds: int | None = Field(default=None, ge=1)


def build_setup(
    library: ContentLibrary,
    map_id: str,
    allies: Sequence[str],
    enemies: Sequence[str],
    *,
    max_rounds: int | None = None,
) -> BattleSetup:
    """以內容庫中的地圖與單位範本 ID 建立設定（位置一律自動排列）。"""
    spawns: list[UnitSpawn] = []
    for team, template_ids in ((Team.ALLY, allies), (Team.ENEMY, enemies)):
        for template_id in template_ids:
            template = library.unit(template_id)
            spawns.append(
                UnitSpawn(template=template, weapon=library.weapon_of(template), team=team)
            )
    return BattleSetup(
        map=library.map(map_id),
        ruleset=library.ruleset,
        units=tuple(spawns),
        max_rounds=max_rounds,
    )
