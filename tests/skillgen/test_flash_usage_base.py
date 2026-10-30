"""BAL-2b：觸發、修正類的基本用法分（資料驅動），讓「全指定」策略不再永遠把這兩類排最後。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_offer import FlashRequest, _usage_score, category_ranking
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage

TRIGGER_OR_MODIFIER = ("trigger", "modifier")


def test_base_scores_live_in_the_data_for_trigger_and_modifier_templates_only() -> None:
    table = library().flash
    for template in table.minor:
        if template.category in TRIGGER_OR_MODIFIER:
            continue
        assert template.usage_base == 0, template.id
    by_id = {t.id: t.usage_base for t in table.minor}
    assert by_id["trigger_potency"] >= 1 and by_id["mod_potency"] >= 1
    assert by_id["stance_potency"] >= 1


def test_usage_score_is_no_longer_zero_for_trigger_and_modifier_templates() -> None:
    lib = library()
    for template in lib.flash.minor:
        if template.category not in TRIGGER_OR_MODIFIER or template.usage_base == 0:
            continue
        variation = Variation(source="minor", template=template.id, category=template.category)
        assert _usage_score(lib, SkillUsage(), template, variation) == template.usage_base


def _passives(kind: str) -> list[SkillDef]:
    lib = library()
    return [s for s in sorted(lib.skills.values(), key=lambda s: s.id) if s.kind == kind]


def test_trigger_is_not_always_ranked_last_for_passives_and_reactions() -> None:
    lib = library()
    usage = SkillUsage(uses=6, targets=6, distance=6)
    seen_trigger = 0
    not_last = 0
    for kind in ("passive", "reaction"):
        for skill in _passives(kind):
            request = FlashRequest(
                base=skill, state=acquire(skill.id), usage=usage, seed=1, tier=skill.tier
            )
            ranking = category_ranking(lib, request)
            if "trigger" in ranking and len(ranking) > 1:
                seen_trigger += 1
                not_last += ranking.index("trigger") < len(ranking) - 1
    assert seen_trigger > 0
    assert not_last > 0
