"""戰鬥設定：地圖、規則包、參戰單位、天氣、勝利條件（``start_battle`` 的輸入）。

``BattleSetup`` 內嵌完整的內容資料（地圖、規則、單位範本、武器、天氣），可序列化寫入戰鬥紀錄，
讓重播不依賴當下的資料檔。

部署階段（``docs/專案計畫.md`` 5.0）：:func:`deploy_allies` 讓玩家在我方起始區指定站位；
未指定的單位依起始區順序自動排列（確定性）。
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.battle import UnitTemplate, WeaponDef
from trpg.content.environment import WeatherDef
from trpg.content.library import ContentLibrary, Ruleset
from trpg.content.maps import MapDef, Objective, SpawnUnitsEvent
from trpg.content.rules import CoreRules
from trpg.engine.state import SpawnTemplate
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team

__all__ = [
    "BattleSetup",
    "BattleSetupError",
    "UnitSpawn",
    "build_setup",
    "deploy_allies",
    "deployment_tiles",
    "starting_source",
]


class BattleSetupError(TrpgError):
    """戰鬥設定不合法（例如起始位置衝突、某一方沒有單位）。"""


class UnitSpawn(BaseModel):
    """一個參戰單位。``position`` 為 ``None`` 時依起始區順序自動排列。

    ``source``：開場源力（Phase 3C-4a；Phase 3-5 由一輪存檔帶入）。我方單位的實際開場值 ＝
    clamp(max(值, ``source_min_at_start``), 0, ``source_max``)，``None`` 等同 0（即保底值）；
    敵方一律 0。見 :func:`starting_source`。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    template: UnitTemplate
    weapon: WeaponDef
    team: Team
    position: tuple[int, int] | None = None
    source: int | None = None


def starting_source(spawn: UnitSpawn, core: CoreRules) -> int:
    """單位的開場源力：敵人 0；我方 clamp(max(``spawn.source``, 保底), 0, 上限)。"""
    if spawn.team is not Team.ALLY:
        return 0
    wanted = spawn.source if spawn.source is not None else core.source_min_at_start
    return max(0, min(core.source_max, max(wanted, core.source_min_at_start)))


class BattleSetup(BaseModel):
    """戰鬥設定。

    - ``weather``：``None`` 等同晴朗（沒有天氣效果）。
    - ``objective``：``None`` 時使用地圖的 ``objective``。
    - ``spawn_templates``：地圖事件（援軍）會用到的單位範本，以範本 ID 為鍵。
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    map: MapDef
    ruleset: Ruleset
    units: tuple[UnitSpawn, ...] = Field(min_length=2)
    max_rounds: int | None = Field(default=None, ge=1)
    weather: WeatherDef | None = None
    objective: Objective | None = None
    spawn_templates: dict[str, SpawnTemplate] = Field(default_factory=dict)

    @property
    def effective_objective(self) -> Objective:
        return self.objective if self.objective is not None else self.map.objective


def build_setup(
    library: ContentLibrary,
    map_id: str,
    allies: Sequence[str],
    enemies: Sequence[str],
    *,
    max_rounds: int | None = None,
    weather: str | None = None,
    objective: Objective | None = None,
) -> BattleSetup:
    """以內容庫中的地圖與單位範本 ID 建立設定（位置一律自動排列）。

    ``weather`` 省略時使用地圖的預設天氣；地圖事件引用的單位範本會一併放入
    ``spawn_templates``。
    """
    map_def = library.map(map_id)
    spawns: list[UnitSpawn] = []
    for team, template_ids in ((Team.ALLY, allies), (Team.ENEMY, enemies)):
        for template_id in template_ids:
            template = library.unit(template_id)
            spawns.append(
                UnitSpawn(template=template, weapon=library.weapon_of(template), team=team)
            )
    templates: dict[str, SpawnTemplate] = {}
    for event in map_def.events:
        if isinstance(event, SpawnUnitsEvent):
            for placement in event.units:
                template = library.unit(placement.template)
                templates[template.id] = SpawnTemplate(
                    template=template, weapon=library.weapon_of(template)
                )
    return BattleSetup(
        map=map_def,
        ruleset=library.ruleset,
        units=tuple(spawns),
        max_rounds=max_rounds,
        weather=library.weather_def(weather or map_def.weather),
        objective=objective,
        spawn_templates=dict(sorted(templates.items())),
    )


def deployment_tiles(setup: BattleSetup) -> list[tuple[int, int]]:
    """部署階段我方可以選擇的格子（我方起始區，依地圖檔順序）。"""
    return list(setup.map.start_zones[Team.ALLY])


def deploy_allies(setup: BattleSetup, positions: Sequence[tuple[int, int]]) -> BattleSetup:
    """部署階段：依序為我方單位指定起始位置（必須在我方起始區內、不可重複）。

    ``positions`` 可以少於我方單位數，其餘單位照常自動排列。不合法時拋出
    :class:`BattleSetupError`。
    """
    allies = [i for i, spawn in enumerate(setup.units) if spawn.team is Team.ALLY]
    if len(positions) > len(allies):
        raise BattleSetupError(f"部署位置過多：我方只有 {len(allies)} 個單位")
    zone = set(deployment_tiles(setup))
    seen: set[tuple[int, int]] = set()
    for pos in positions:
        if pos not in zone:
            raise BattleSetupError(f"部署位置不在我方起始區：{pos}")
        if pos in seen:
            raise BattleSetupError(f"部署位置重複：{pos}")
        seen.add(pos)
    units = list(setup.units)
    for index, pos in zip(allies, positions, strict=False):
        units[index] = units[index].model_copy(update={"position": tuple(pos)})
    return setup.model_copy(update={"units": tuple(units)})
