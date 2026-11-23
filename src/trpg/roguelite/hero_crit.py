"""一輪中主角面板的暴擊傷害（CR-1c，``docs/design/05-戰鬥.md`` 5.4.2 第 8 點）。

一輪中不在戰鬥裡，沒有戰鬥狀態。這裡照開戰的做法組一份只有主角一個單位的最小戰鬥狀態：

- 單位：:func:`~trpg.roguelite.progress.hero_spawn`（和開戰同一份範本、武器、裝備）交給
  :func:`~trpg.engine.lifecycle.make_unit`（和開戰同一個函式：裝備詞條、種族、裝備授予的技能都照算）；
- 規則包：內容庫的規則包加上主角的生成技能，和開戰同一個 ``gated_with_skills``（E5 預算閘門）；
- 地圖：1×1 的石地（高度 0、沒有表面），主角站在 (0, 0)；第 1 輪、沒有其他單位。

倍率與來源交給引擎的 :func:`~trpg.engine.crit_damage.crit_damage_breakdown`（和結算、戰鬥中的單位卡
同一個函式；主手武器普攻、沒有目標，修正技只算不看目標的條件）。不擲骰、不改任何狀態。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.engine import modifiers
from trpg.engine.crit_damage import CritDamageBreakdown, crit_damage_breakdown
from trpg.engine.lifecycle import make_unit
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import BattleState, Tile
from trpg.roguelite.progress import hero_spawn
from trpg.roguelite.state import RunState
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, UnitId
from trpg.skillgen.reshape_gate import gated_with_skills

__all__ = ["hero_crit_breakdown", "hero_panel_state"]

_HERO = UnitId("hero")


def hero_panel_state(library: ContentLibrary, run: RunState) -> BattleState:
    """只有主角一個單位的最小戰鬥狀態（面板用，不拿來打）。"""
    spawn = hero_spawn(library, run)
    ruleset = gated_with_skills(library, run.generated_skills)  # 和開戰同一個（E5 預算閘門）
    unit = make_unit(
        _HERO,
        template=spawn.template,
        weapon=spawn.weapon,
        team=spawn.team,
        pos=Pos(x=0, y=0),
        name=run.hero.name_zh,
        rules=ruleset,
        equipment=spawn.equipment,
    )
    return BattleState(
        map_id="",
        map_name_zh="",
        width=1,
        height=1,
        tiles=[Tile(height=0, terrain="stone")],
        ruleset=ruleset,
        units={_HERO: unit},
        turn_order=[_HERO],
        turn_pos=0,
        active_unit=None,
        round=1,
        max_rounds=None,
        seed=0,
        rng_state=Rng(0).get_state(),
    )


def hero_crit_breakdown(library: ContentLibrary, run: RunState) -> CritDamageBreakdown:
    """主角主手武器普攻的暴擊傷害倍率與來源（和戰鬥中單位卡的參數相同）。"""
    state = hero_panel_state(library, run)
    unit = state.units[_HERO]
    return crit_damage_breakdown(state, unit, use=modifiers.ATTACK, subject=Subject(None, unit.xy))
