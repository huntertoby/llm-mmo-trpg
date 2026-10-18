"""目前已知的內容資料檔清單，以及一次載入全部的工具（供 ``trpg content check`` 使用）。

新增單一資料檔時，在 :data:`KNOWN_CONTENT_FILES` 加一筆；``trpg content check`` 另以
:func:`trpg.content.library.load_library` 載入資料夾並做跨檔案檢查。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trpg.content.battle import StatusTable, TerrainTable, WeaponTable
from trpg.content.composer_rules import ComposerRules
from trpg.content.environment import (
    AiProfileTable,
    InteractionTable,
    ObjectTable,
    ReactionTable,
    SurfaceTable,
    WeatherTable,
)
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.rules import CoreRules, HitTable
from trpg.content.schemas import ContentModel, ElementTable
from trpg.content.sim_builds import BuildTable
from trpg.content.skill_rules import BudgetRules, ExclusionTable, SynergyTable
from trpg.content.skill_triggers import SkillTriggerTable
from trpg.content.skills import ConditionTable, PrimitiveTable, ShapeTable

__all__ = ["KNOWN_CONTENT_FILES", "ContentFile", "load_all_content"]


@dataclass(frozen=True)
class ContentFile:
    """一個已知的內容資料檔：相對於內容資料夾的路徑與對應的 model。"""

    relative_path: str
    model: type[ContentModel]


KNOWN_CONTENT_FILES: tuple[ContentFile, ...] = (
    ContentFile("elements.yaml", ElementTable),
    ContentFile("rules/core.yaml", CoreRules),
    ContentFile("rules/hit_table.yaml", HitTable),
    ContentFile("terrain.yaml", TerrainTable),
    ContentFile("weapons.yaml", WeaponTable),
    ContentFile("statuses.yaml", StatusTable),
    ContentFile("objects.yaml", ObjectTable),
    ContentFile("surfaces.yaml", SurfaceTable),
    ContentFile("interactions.yaml", InteractionTable),
    ContentFile("weather.yaml", WeatherTable),
    ContentFile("reactions.yaml", ReactionTable),
    ContentFile("ai_profiles.yaml", AiProfileTable),
    ContentFile("skill_shapes.yaml", ShapeTable),
    ContentFile("skill_primitives.yaml", PrimitiveTable),
    ContentFile("skill_conditions.yaml", ConditionTable),
    ContentFile("skill_triggers.yaml", SkillTriggerTable),
    ContentFile("skill_budget.yaml", BudgetRules),
    ContentFile("skill_composer.yaml", ComposerRules),
    ContentFile("sim/builds.yaml", BuildTable),
    ContentFile("skill_synergies.yaml", SynergyTable),
    ContentFile("skill_exclusions.yaml", ExclusionTable),
)
"""單一資料檔。資料夾（``units/``、``maps/``、``skills/``）與跨檔案檢查由
:func:`trpg.content.library.load_library` 負責。"""


def load_all_content(content_dir: Path | None = None) -> list[tuple[Path, ContentModel]]:
    """依 :data:`KNOWN_CONTENT_FILES` 的順序載入並驗證全部資料檔。

    任一檔案失敗即拋出 :class:`~trpg.shared.errors.ContentError`。
    """
    base = default_content_dir() if content_dir is None else content_dir
    loaded: list[tuple[Path, ContentModel]] = []
    for item in KNOWN_CONTENT_FILES:
        path = base / item.relative_path
        loaded.append((path, load_content_file(path, item.model)))
    return loaded
