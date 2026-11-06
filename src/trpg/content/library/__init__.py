"""一次載入並交叉驗證全部戰鬥內容：:class:`Ruleset`（規則包）與 :class:`ContentLibrary`。

:class:`Ruleset` 是引擎結算需要的全部規則資料（核心數值、命中表、地形、狀態），會整份嵌入
戰鬥狀態，讓「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔。

依職責拆成子模組（R1b）：``ruleset``（規則包與技能引用檢查）、``container``
（:class:`ContentLibrary`）、``load``（入口 :func:`load_library`）、``base``（共用載入工具）、
``world``（大世界內容）、``tables``（種族、演化、閃現、召喚物等其他表）、``skill_checks``、
``unit_checks``、``gear_checks``（跨檔案檢查）。呼叫端一律從 ``trpg.content.library`` 匯入。
"""

from trpg.content.library.container import ContentLibrary, skill_name_problems
from trpg.content.library.gear_checks import _affix_reference_problems as _affix_reference_problems
from trpg.content.library.gear_checks import _trait_problems as _trait_problems
from trpg.content.library.load import load_library
from trpg.content.library.ruleset import (
    REQUIRED_STATUSES,
    Ruleset,
    enemy_template_ids,
    skill_reference_problems,
)
from trpg.content.library.skill_checks import _check_skills as _check_skills
from trpg.content.library.skill_checks import _story_skill_problems as _story_skill_problems
from trpg.content.library.skill_checks import (
    gear_class_problem,
    gear_reference_problems,
)
from trpg.content.library.skill_checks import pool_region_problems as pool_region_problems
from trpg.content.library.tables import _load_flash as _load_flash
from trpg.content.library.unit_checks import (
    player_template_enemy_only_problems,
    unit_skill_problems,
)
from trpg.content.library.unit_checks import unit_phase_problems as unit_phase_problems
from trpg.content.library.world import WORLD_ENCOUNTERS_DIR as WORLD_ENCOUNTERS_DIR
from trpg.content.library.world import WORLD_ENEMIES_FILE as WORLD_ENEMIES_FILE
from trpg.content.library.world import WORLD_FIELDS_DIR as WORLD_FIELDS_DIR
from trpg.content.library.world import WORLD_MAPS_DIR as WORLD_MAPS_DIR
from trpg.content.library.world import WORLD_MERCENARIES_FILE as WORLD_MERCENARIES_FILE
from trpg.content.library.world import WORLD_OATHS_FILE as WORLD_OATHS_FILE
from trpg.content.library.world import WORLD_RULES_FILE as WORLD_RULES_FILE
from trpg.content.library.world import _check_stele_regions as _check_stele_regions
from trpg.content.library.world import _load_world_maps as _load_world_maps

__all__ = [
    "REQUIRED_STATUSES",
    "ContentLibrary",
    "Ruleset",
    "enemy_template_ids",
    "gear_class_problem",
    "gear_reference_problems",
    "load_library",
    "player_template_enemy_only_problems",
    "skill_name_problems",
    "skill_reference_problems",
    "unit_skill_problems",
]
