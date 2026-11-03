"""霧中劍客的霧影分身（Phase 5F-1b；18.7.4「會分身」，玩法 PM 2026-11-03 代決）。

不改引擎：本體 ``sect_mist_swordsman`` 帶召喚技能「霧影分身」（技能層級條件第一輪），開場用現有的
召喚原語召出 1 名低血量、同招式的霧影 ``summon_mist_shade``。
"""

from __future__ import annotations

from collections.abc import Callable

from tests.world.helpers import make_encounter
from trpg.content.library import ContentLibrary
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import UnitSummoned
from trpg.engine.runner import run_battle
from trpg.world.battle import prepare_battle
from trpg.world.state import CharacterState

MakeChar = Callable[..., CharacterState]
SWORDSMAN = "sect_mist_swordsman"
SHADE = "summon_mist_shade"


def test_shade_template_is_low_hp_with_same_moves(library: ContentLibrary) -> None:
    body = library.unit(SWORDSMAN)
    shade = library.ruleset.summon_def(SHADE)
    core = library.ruleset.core
    assert core.template_max_hp(shade.template) * 4 < core.template_max_hp(body)
    assert shade.template.weapon == body.weapon
    assert set(shade.template.skills) == set(body.skills) - {"skill_summon_mist_shade"}
    skill = library.skills["skill_summon_mist_shade"]
    assert skill.condition is not None and skill.condition.type == "first_round"


def test_bounty_battle_opens_with_one_shade(library: ContentLibrary, make_char: MakeChar) -> None:
    summoned = 0
    for seed in range(3):
        encounter = make_encounter("sword_tomb", seed=seed, level=5)
        encounter = encounter.model_copy(update={"bounty": "mist_swordsman"})
        char = make_char(location="sword_tomb", pending_encounter=encounter, level=5)
        prepared = prepare_battle(library, char)
        body = next(u for u in prepared.setup.units if u.template.id.startswith(SWORDSMAN))
        assert "elite" in body.template.tags  # 霧隱的
        run = run_battle(prepared.setup, prepared.seed, UtilityAI(library.ai_profiles))
        shades = [e for e in run.events if isinstance(e, UnitSummoned) and e.template_id == SHADE]
        assert len(shades) <= 1  # 只有第一輪能用＝每場最多一次
        if shades:
            assert shades[0].round == 1
            summoned += 1
    assert summoned >= 2  # 開場通常就召出（效用 AI 決定；還打不到敵人時召喚的分數最高）
