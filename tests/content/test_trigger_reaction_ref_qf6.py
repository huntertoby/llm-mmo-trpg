"""QF-6（佇列 (u)，E4 報告第 8 點）：被動技 ``trigger.reaction`` 篩選的 ID 載入時要存在。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef

_ID = "skill_test_reaction_ref_qf6"


def _passive(reaction: str) -> SkillDef:
    return SkillDef.model_validate(
        {
            "id": _ID,
            "name_zh": "測試反應篩選",
            "tier": 1,
            "rarity": "epic",
            "kind": "passive",
            "skeleton": "passive",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "wis",
            "shape": {"type": "self"},
            "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
            "trigger": {"event": "on_hit", "source": "reaction", "reaction": reaction},
            "cost": {"mana": 0},
        }
    )


def test_unknown_reaction_id_is_rejected_with_skill_and_reaction_id() -> None:
    ruleset = library().ruleset
    with pytest.raises(ValueError, match=_ID) as info:
        ruleset.with_skills([_passive("no_such_reaction")])
    assert "no_such_reaction" in str(info.value)
    assert "trigger.reaction" in str(info.value)


@pytest.mark.parametrize("reaction", ["opportunity_attack", "skill_riposte"])
def test_builtin_reaction_and_reaction_skill_ids_are_accepted(reaction: str) -> None:
    added = library().ruleset.with_skills([_passive(reaction)])
    trigger = added.skill_def(_ID).trigger
    assert trigger is not None
    assert trigger.reaction == reaction


def test_non_reaction_skill_id_is_rejected() -> None:
    other = next(s.id for s in library().skills.values() if s.kind == "active")
    with pytest.raises(ValueError, match="找不到反應") as info:
        library().ruleset.with_skills([_passive(other)])
    assert other in str(info.value)
