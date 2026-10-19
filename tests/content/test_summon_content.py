"""召喚的資料（Phase 3D-4a）：召喚物範本、``summon`` 原語的 schema 與跨檔案驗證、預算。"""

from __future__ import annotations

import shutil
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library, make_skill
from trpg.content.library import load_library
from trpg.content.skills import SkillDef, skill_problems
from trpg.content.summons import summon_dpr
from trpg.shared.errors import ContentError
from trpg.skillgen.budget import skill_budget

CONTENT = PROJECT_ROOT / "content"
SUMMON: dict[str, Any] = {"type": "summon", "unit": "summon_skeleton_warrior", "duration": 2}
TILE: dict[str, Any] = {"type": "ground_tile", "range": 3}


def _problems(skill: SkillDef, *, summon_ids: set[str] | None = None) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
        summon_ids=set(rules.summons.by_id()) if summon_ids is None else summon_ids,
    )


def test_the_two_summon_templates_are_loaded_into_the_ruleset() -> None:
    lib = library()
    summons = lib.ruleset.summons.by_id()
    assert set(summons) == {"summon_elemental_spirit", "summon_skeleton_warrior"}
    spirit, skeleton = summons["summon_elemental_spirit"], summons["summon_skeleton_warrior"]
    assert spirit.template.summon and skeleton.template.summon
    assert spirit.template.speed > 0 and not spirit.weapon.is_melee  # 可移動、會攻擊（遠程）
    assert skeleton.weapon.is_melee  # 近戰
    assert all(s not in lib.units for s in summons)  # 不是一般單位範本，不能直接參戰
    assert summon_dpr(skeleton) == Fraction(9, 2)  # 1d8 平均
    assert lib.ruleset.core.summon_limit_per_owner == 2
    assert lib.skeletons["summon"].enabled


def test_a_summon_template_outside_the_summons_folder_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    shutil.copy(
        root / "units" / "summons" / "summon_skeleton_warrior.yaml",
        root / "units" / "summon_skeleton_warrior.yaml",
    )
    with pytest.raises(ContentError, match="units/summons"):
        load_library(root)


def test_a_template_in_the_summons_folder_must_be_marked(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    path = root / "units" / "summons" / "summon_skeleton_warrior.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("summon: true", "summon: false"), encoding="utf-8"
    )
    with pytest.raises(ContentError, match="summon: true"):
        load_library(root)


def test_a_valid_summon_skill_has_no_problems() -> None:
    assert _problems(make_skill("skill_t_sum", TILE, [SUMMON])) == []


@pytest.mark.parametrize(
    ("effects", "shape", "message"),
    [
        ([{**SUMMON, "unit": "summon_dragon"}], TILE, "未知的召喚物範本"),
        ([{"type": "summon", "unit": "summon_skeleton_warrior"}], TILE, "缺少必要參數 duration"),
        ([{**SUMMON, "duration": 5}], TILE, "duration 必須在 1–4"),
        ([SUMMON], {"type": "single", "range": 3}, "只能搭配形狀 ground_tile"),
    ],
)
def test_invalid_summon_effects_are_reported(
    effects: list[dict[str, Any]], shape: dict[str, Any], message: str
) -> None:
    problems = _problems(make_skill("skill_t_sum", shape, effects))
    assert any(message in p for p in problems), problems


@pytest.mark.parametrize(
    ("effects", "kind", "message"),
    [
        ([{**SUMMON, "count": 2}], "active", "count 目前只能是 1"),
        ([SUMMON, SUMMON], "active", "最多一個 summon"),
        (
            [SUMMON, {"type": "apply_status", "status": "empowered", "duration": 2}],
            "active",
            "affects: self",
        ),
        ([SUMMON], "stance", "只能用在主動技能"),
    ],
)
def test_summon_skill_schema_rules(effects: list[dict[str, Any]], kind: str, message: str) -> None:
    data = make_skill("skill_t_sum", TILE, [SUMMON]).model_dump(mode="json")
    data.update(effects=effects, kind=kind)
    if kind == "stance":
        data["ap_cost"] = None
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(data)


def test_a_self_effect_next_to_the_summon_is_allowed() -> None:
    extra = {"type": "apply_status", "status": "empowered", "duration": 2, "affects": "self"}
    assert _problems(make_skill("skill_t_sum", TILE, [SUMMON, extra])) == []


def test_the_summon_budget_is_dpr_times_duration_times_the_round_value() -> None:
    lib = library()
    report = skill_budget(lib.skills["skill_raise_skeleton"], lib)
    permille = lib.budget.summon_round_value_permille
    assert report.raw == Fraction(9, 2) * 2 * Fraction(permille, 1000)
    assert report.ok
    spirit = make_skill(
        "skill_t_sum", TILE, [{**SUMMON, "unit": "summon_elemental_spirit", "duration": 3}]
    )
    assert skill_budget(spirit, lib).raw == Fraction(7, 2) * 3 * Fraction(permille, 1000)
