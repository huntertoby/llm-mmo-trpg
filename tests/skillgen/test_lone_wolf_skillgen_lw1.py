"""LW-1：獨狼條件（#156）開放給 LLM 與技能工具；「施放者沒有某狀態」只給敵人專用招。"""

from __future__ import annotations

from functools import cache

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import ConditionSpec
from trpg.skillgen.option_params import ENEMY_ONLY_CONDITION, condition_choice
from trpg.skillgen.proposal import build_proposal_models
from trpg.skillgen.validate import validate_skill


@cache
def _lib() -> ContentLibrary:
    return library()


def test_llm_schema_offers_lone_wolf_but_not_self_lacks_status() -> None:
    defs = build_proposal_models(_lib()).json_schema()["$defs"]
    assert "Condition_lone_wolf" in defs
    assert set(defs["Condition_lone_wolf"]["properties"]) == {"type"}
    assert "Condition_self_lacks_status" not in defs


def test_options_mark_enemy_only_conditions_unavailable() -> None:
    by_id = _lib().ruleset.conditions.by_id()
    lone = condition_choice(by_id["lone_wolf"], _lib(), effect_level=True)
    lacks = condition_choice(by_id["self_lacks_status"], _lib(), effect_level=True)
    assert "unavailable_zh" not in lone.info
    assert lacks.info["unavailable_zh"] == ENEMY_ONLY_CONDITION


def _messages(skill_id: str, **update: object) -> list[str]:
    skill = _lib().skills[skill_id].model_copy(update=update)
    return [v.message for v in validate_skill(skill, _lib())]


def test_player_skills_cannot_use_self_lacks_status() -> None:
    lacks = ConditionSpec(type="self_lacks_status", status="root")
    messages = _messages("skill_lone_wolf_pounce", condition=lacks)
    assert any("self_lacks_status" in m and "敵人專用" in m for m in messages)
    # 敵人專用招可以（界隙閃擊本身通過驗證）
    assert validate_skill(_lib().skills["skill_rift_flicker"], _lib()) == []


def test_lone_wolf_is_a_valid_condition_on_actives_and_passives() -> None:
    for sid in ("skill_lone_wolf_pounce", "skill_unguarded_shot", "skill_lone_strider"):
        assert validate_skill(_lib().skills[sid], _lib()) == [], sid
