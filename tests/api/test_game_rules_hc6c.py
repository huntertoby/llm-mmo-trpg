"""HC-6c：``/api/glossary`` 的 ``rules`` 多五個說明文字組字用的欄位，值都來自內容庫
（或程式常數）。"""

from __future__ import annotations

from trpg.api.glossary import build_glossary
from trpg.content.library import load_library
from trpg.sim.lineup import TEAM_SIZE


def test_new_rule_fields_follow_data() -> None:
    library = load_library()
    rules = build_glossary(library).rules
    assert rules.source_min_at_start == library.ruleset.core.source_min_at_start
    assert rules.summon_guard_radius == library.ai_profiles.summon.guard_radius
    assert rules.battle_team_size == TEAM_SIZE
    assert rules.item_skill_ap_cost == library.world_economy.item_skill_ap_cost
    situations = library.world_event_content.situations.rules
    assert situations is not None
    assert rules.situation_care_max == situations.check.care_max
