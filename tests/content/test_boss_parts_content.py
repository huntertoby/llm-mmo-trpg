"""PB-1a：``UnitTemplate.parts`` 的 schema 與內容檢查（05 5.12.2；``PhasePB-1計畫.md`` 4.1）。

HC-4a：部位數、血量加總、破壞效果數是規則（``core.yaml`` 的 ``boss_parts``），改在載入內容庫時檢查
（:func:`unit_phase_problems`），不在範本驗證。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.battle import UnitTemplate, template_part_problems
from trpg.content.library import unit_phase_problems
from trpg.content.parts import STAT_DOWN_STATS, BossPart

MIST = "sect_mist_lock_master"


def part(pid: str, **extra: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": pid,
        "name_zh": pid,
        "hp_permille": 200,
        "on_break": [{"type": "interrupt_charge"}],
    }
    data.update(extra)
    return data


def with_parts(parts: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    data = library().unit(MIST).model_dump()
    data["parts"] = parts
    data.update(overrides)
    return data


TWO = [part("a"), part("b")]
SEAL_UNKNOWN = {"type": "seal_skill", "skill": "skill_fireball"}


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (with_parts(TWO, tags=["humanoid"]), "boss"),
        (with_parts([part("a"), part("a")]), "重複"),
        (with_parts([part("a", on_break=[]), part("b")]), "on_break"),
        (
            with_parts(
                [
                    part("a", on_break=[{"type": "stat_down", "stat": "luck", "amount": 1}]),
                    part("b"),
                ]
            ),
            "stat",
        ),
        (with_parts([part("a", reach="sideways"), part("b")]), "reach"),
    ],
)
def test_bad_parts_fail_validation(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        UnitTemplate.model_validate(data)


@pytest.mark.parametrize(
    ("parts", "message"),
    [
        ([part("a")], "parts 要有 2～4 個部位（收到 1 個）"),
        ([part(c) for c in "abcde"], "parts 要有 2～4 個部位（收到 5 個）"),
        (
            [part("a", hp_permille=301), part("b", hp_permille=300)],
            "所有部位的血量加總不能超過 600‰（收到 601‰）",
        ),
        (
            [part("a", on_break=[{"type": "interrupt_charge"}] * 3), part("b")],
            "部位 a 的 on_break 最多 2 項（收到 3 項）",
        ),
    ],
)
def test_part_rules_are_checked_when_the_library_loads(
    parts: list[dict[str, Any]], message: str
) -> None:
    """HC-4a：範本本身組得起來；部位規則（core.yaml 的 boss_parts）在載入內容庫時擋。"""
    lib = library()
    template = UnitTemplate.model_validate(with_parts(parts))
    problems = unit_phase_problems(
        template,
        units=lib.units,
        weapons=lib.weapons,
        skills=lib.skills,
        ruleset=lib.ruleset,
        ai_profiles=lib.ai_profiles,
        weather=lib.weather,
    )
    assert message in problems


def test_summons_cannot_have_parts() -> None:
    template = UnitTemplate.model_validate(with_parts(TWO))
    assert template_part_problems(template) == []
    assert "召喚物不能有 parts" in template_part_problems(
        template.model_copy(update={"summon": True})
    )


def test_reference_checks_run_when_the_library_loads() -> None:
    lib = library()
    bad = [part("a", exposed_in=["nope"]), part("b", on_break=[SEAL_UNKNOWN])]
    template = UnitTemplate.model_validate(with_parts(bad))  # 範本本身照組得起來
    problems = "；".join(
        unit_phase_problems(
            template,
            units=lib.units,
            weapons=lib.weapons,
            skills=lib.skills,
            ruleset=lib.ruleset,
            ai_profiles=lib.ai_profiles,
            weather=lib.weather,
        )
    )
    assert "部位 a 的 exposed_in 不是這個單位的階段：nope" in problems
    assert "部位 b 封的招 skill_fireball 不在這個單位的技能組" in problems


def test_cross_file_checks_name_the_part() -> None:
    lib = library()
    bad = [
        part("a", on_break=[{"type": "control", "status": "nope_status"}]),
        part("b", on_break=[{"type": "control", "status": "weaken"}]),
        part("c", on_break=[{"type": "stop_mechanic", "status": "nope_status"}]),
    ]
    template = UnitTemplate.model_validate(with_parts(bad))
    problems = unit_phase_problems(
        template,
        units=lib.units,
        weapons=lib.weapons,
        skills=lib.skills,
        ruleset=lib.ruleset,
        ai_profiles=lib.ai_profiles,
        weather=lib.weather,
    )
    joined = "；".join(problems)
    assert "部位 a：未知的狀態 nope_status" in joined
    assert "部位 b：control 的狀態 weaken 不是控制狀態" in joined
    assert "部位 c：未知的狀態 nope_status" in joined


def test_good_parts_pass_the_cross_file_checks() -> None:
    lib = library()
    good = [
        part("a", on_break=[{"type": "control", "status": "stun", "duration": 1}]),
        part("b", on_break=[{"type": "stop_mechanic", "status": "mist_return"}]),
    ]
    template = UnitTemplate.model_validate(with_parts(good))
    assert (
        unit_phase_problems(
            template,
            units=lib.units,
            weapons=lib.weapons,
            skills=lib.skills,
            ruleset=lib.ruleset,
            ai_profiles=lib.ai_profiles,
            weather=lib.weather,
        )
        == []
    )


def test_defaults_and_optional_fields_are_not_serialized() -> None:
    data = BossPart.model_validate(part("a")).model_dump()
    assert data["hp_permille"] == 200 and data["reach"] == "any"
    for key in ("exposed_in", "armor_bonus", "resist", "element_mods", "break_text_zh"):
        assert key not in data


def test_units_without_parts_do_not_output_the_key() -> None:
    lib = library()
    with_parts_ids = sorted(t.id for t in lib.units.values() if t.parts)
    assert with_parts_ids == ["ashen_heart", MIST]  # GB-2：灰燼之心的部位綁格
    for template in lib.units.values():
        dumped = template.model_dump()
        assert ("parts" in dumped) == bool(template.parts), template.id


def test_stat_down_names() -> None:
    assert STAT_DOWN_STATS == (
        "move",
        "armor",
        "hit",
        "resist.physical",
        "resist.elemental",
        "resist.nature",
        "resist.spirit",
        "damage_dealt",
    )
