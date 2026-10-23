"""召喚物小卡的灌注 HP 句（Phase 3H-5）：由灌注資料產生，之後有別的灌注動 HP 時自動多列。"""

from __future__ import annotations

from dataclasses import replace

from tests.engine.helpers import library
from trpg.content.rules import SummonInfusion
from trpg.narrative.summon_info import hp_infusion_text, summon_info


def test_summon_card_lists_hp_infusions_from_the_data() -> None:
    lib = library()
    assert hp_infusion_text(lib) == "選「召喚物」灌注時 HP +20%"
    skill = next(s for s in lib.skills.values() if any(e.type == "summon" for e in s.effects))
    spec = next(e for e in skill.effects if e.type == "summon")
    card = summon_info(lib, skill, spec)
    assert card is not None and card.hp_infusion_zh == "選「召喚物」灌注時 HP +20%"
    more = dict(lib.ruleset.core.summon_infusions)
    more["wet"] = SummonInfusion(hp_permille=100)  # 之後有別的灌注動 HP：自動多列
    core = lib.ruleset.core.model_copy(update={"summon_infusions": more})
    lib2 = replace(lib, ruleset=lib.ruleset.model_copy(update={"core": core}))
    assert hp_infusion_text(lib2).count("HP +") == 2
