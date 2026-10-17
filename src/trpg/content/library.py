"""一次載入並交叉驗證全部戰鬥內容：:class:`Ruleset`（規則包）與 :class:`ContentLibrary`。

:class:`Ruleset` 是引擎結算需要的全部規則資料（核心數值、命中表、地形、狀態），會整份嵌入
戰鬥狀態，讓「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import PrivateAttr, model_validator

from trpg.content.battle import (
    StatusDef,
    StatusTable,
    TerrainDef,
    TerrainTable,
    UnitTemplate,
    WeaponDef,
    WeaponTable,
)
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.maps import MapDef, check_map
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.shared.errors import ContentError

__all__ = [
    "REQUIRED_STATUSES",
    "ContentLibrary",
    "Ruleset",
    "load_library",
]

REQUIRED_STATUSES = ("burning", "defending", "prone")
"""引擎規則直接引用的狀態 ID，必須存在於 ``statuses.yaml``。"""


class Ruleset(ContentModel):
    """引擎需要的規則資料。"""

    core: CoreRules
    hit_table: HitTable
    terrain: TerrainTable
    statuses: StatusTable

    _terrain_index: dict[str, TerrainDef] = PrivateAttr(default_factory=dict)
    _status_index: dict[str, StatusDef] = PrivateAttr(default_factory=dict)

    def model_post_init(self, context: object, /) -> None:
        # 查表索引（不屬於資料本身，不參與序列化與相等比較）
        self._terrain_index = self.terrain.by_id()
        self._status_index = self.statuses.by_id()

    @model_validator(mode="after")
    def _check(self) -> Ruleset:
        if (self.hit_table.slope, self.hit_table.cap) != (
            self.core.hit_slope,
            self.core.hit_mod_cap,
        ):
            raise ValueError(
                "hit_table.yaml 的 slope／cap 與 core.yaml 的 hit_slope／hit_mod_cap 不一致，"
                "請執行 `uv run python scripts/gen_hit_table.py` 重新產生"
            )
        ids = {s.id for s in self.statuses.statuses}
        missing = [s for s in REQUIRED_STATUSES if s not in ids]
        if missing:
            raise ValueError(f"statuses.yaml 缺少引擎需要的狀態：{', '.join(missing)}")
        return self

    def terrain_def(self, terrain_id: str) -> TerrainDef:
        return self._terrain_index[terrain_id]

    def status_def(self, status_id: str) -> StatusDef:
        return self._status_index[status_id]


@dataclass(frozen=True)
class ContentLibrary:
    """``content/`` 下全部已驗證的戰鬥內容。"""

    root: Path
    elements: ElementTable
    ruleset: Ruleset
    weapons: dict[str, WeaponDef]
    units: dict[str, UnitTemplate]
    maps: dict[str, MapDef]
    files: list[tuple[Path, ContentModel]] = field(default_factory=list)

    def unit(self, template_id: str) -> UnitTemplate:
        try:
            return self.units[template_id]
        except KeyError:
            known = ", ".join(sorted(self.units))
            raise KeyError(f"未知的單位範本：{template_id}（可用：{known}）") from None

    def map(self, map_id: str) -> MapDef:
        try:
            return self.maps[map_id]
        except KeyError:
            known = ", ".join(sorted(self.maps))
            raise KeyError(f"未知的地圖：{map_id}（可用：{known}）") from None

    def weapon_of(self, template: UnitTemplate) -> WeaponDef:
        return self.weapons[template.weapon]


def _load_dir[M: ContentModel](
    directory: Path, model: type[M], files: list[tuple[Path, ContentModel]]
) -> dict[str, M]:
    if not directory.is_dir():
        raise ContentError(directory, "找不到資料夾")
    result: dict[str, M] = {}
    for path in sorted(directory.glob("*.yaml")):
        item = load_content_file(path, model)
        item_id = getattr(item, "id", None)
        if item_id != path.stem:
            raise ContentError(path, f"檔名必須與 id 相同（id 為 {item_id!r}）")
        files.append((path, item))
        result[path.stem] = item
    return result


def load_library(content_dir: Path | None = None) -> ContentLibrary:
    """載入並交叉驗證 ``content/`` 下全部戰鬥內容；任何問題都拋出 :class:`ContentError`。"""
    root = default_content_dir() if content_dir is None else content_dir
    files: list[tuple[Path, ContentModel]] = []

    def load[M: ContentModel](rel: str, model: type[M]) -> M:
        path = root / rel
        item = load_content_file(path, model)
        files.append((path, item))
        return item

    elements = load("elements.yaml", ElementTable)
    core = load("rules/core.yaml", CoreRules)
    hit_table = load("rules/hit_table.yaml", HitTable)
    terrain = load("terrain.yaml", TerrainTable)
    weapons = load("weapons.yaml", WeaponTable)
    statuses = load("statuses.yaml", StatusTable)
    try:
        ruleset = Ruleset(core=core, hit_table=hit_table, terrain=terrain, statuses=statuses)
    except ValueError as exc:
        raise ContentError(root / "rules", str(exc)) from exc

    units = _load_dir(root / "units", UnitTemplate, files)
    weapon_map = weapons.by_id()
    for template_id, template in units.items():
        if template.weapon not in weapon_map:
            raise ContentError(
                root / "units" / f"{template_id}.yaml", f"未知的武器：{template.weapon}"
            )

    maps = _load_dir(root / "maps", MapDef, files)
    terrain_map = terrain.by_id()
    for map_id, map_def in maps.items():
        problems = check_map(map_def, terrain_map, core)
        if problems:
            raise ContentError(root / "maps" / f"{map_id}.yaml", "；".join(problems))

    return ContentLibrary(
        root=root,
        elements=elements,
        ruleset=ruleset,
        weapons=weapon_map,
        units=units,
        maps=maps,
        files=files,
    )
