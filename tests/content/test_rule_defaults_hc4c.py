"""HC-4c：閃現模板收尾、AI 與環境的預設值搬進 content 之後的規則對照。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library, make_map, make_state, spawn, template
from trpg.content.environment import AiProfileTable
from trpg.content.flash_templates import FlashTable, TransformTemplate
from trpg.content.library import Ruleset
from trpg.engine.ai.displace import exposure, is_hurt
from trpg.shared.types import Team, UnitId


def _read(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _drop(data: dict[str, Any], path: tuple[str | int, ...]) -> None:
    node: Any = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]


@pytest.mark.parametrize(
    "path",
    [
        ("rules", "insight_per_win"),
        ("rules", "form_magnitudes"),
        ("rules", "tighten_permille"),
        ("rules", "complete", "cost_cuts"),
        ("rules", "complete", "cost_cuts", 0, "step"),
        ("pricing", "open", "min_categories"),
        ("pricing", "focused", "min_categories"),
    ],
    ids=lambda p: "/".join(map(str, p)),
)
def test_flash_numbers_have_no_program_default(path: tuple[str | int, ...]) -> None:
    """HC-4b3 裁定 4：閃現表剩下的幾格也必填，內容檔少寫一格就驗證失敗。"""
    data = _read("flash_templates.yaml")
    _drop(data, path)
    field = next(p for p in reversed(path) if isinstance(p, str))
    with pytest.raises(ValidationError, match=field):
        FlashTable.model_validate(data)


def test_flash_values_follow_the_content_file() -> None:
    """值以內容檔為準：``insight_per_win`` 是 2（原本程式寫 1）、法力與耐力的步距 10。"""
    table = FlashTable.model_validate(_read("flash_templates.yaml"))
    assert table.rules.insight_per_win == 2
    assert [(c.field, c.step) for c in table.rules.complete.cost_cuts] == [
        ("stance_upkeep", 1),
        ("cooldown", 1),
        ("mana", 10),
        ("stamina", 10),
        ("ap_cost", 1),
    ]
    assert table.pricing.focused.min_categories == 1


def test_transform_scale_permille_is_gone() -> None:
    """HC-4b3 裁定 3：沒有程式讀的 ``scale_permille`` 刪掉，寫了就驗證失敗。"""
    assert "scale_permille" not in TransformTemplate.model_fields
    transforms = _read("flash_templates.yaml")["transforms"]
    found = [t for t in transforms if t["id"] == "to_passive_on_hit"]
    data = {**found[0], "scale_permille": 500}
    with pytest.raises(ValidationError, match="scale_permille"):
        TransformTemplate.model_validate(data)


# ---------------------------------------------------------------------------
# AI 與環境（HC-4c 第 2 項）
# ---------------------------------------------------------------------------

AI_FILE = "ai_profiles.yaml"


@pytest.mark.parametrize(
    "path",
    [
        ("move_candidates",),
        ("skill_candidates",),
        ("trap_likelihood_permille",),
        ("trap",),
        ("trap", "max_active"),
        ("trap", "shape_factor_permille"),
        ("rewrite", "ap_points"),
        ("rewrite", "share_discount_permille"),
        ("rewrite", "redirect_min_hp_permille"),
        ("gamble", "hp_floor_permille"),
        ("self_cost", "stun_enemy_radius"),
        ("stance", "cancel_hp_below_permille"),
        ("form", "rotate_value"),
        ("summon", "infuse_threat_damage"),
        ("zone", "path_permille"),
        ("rune", "near_permille"),
        ("terrain", "pit_points"),
        ("orders", "environment_permille"),
        ("run", "retreat_enemy_radius"),
        ("basic", "ice_slip_points"),
        ("objective_ai", "hold_radius"),
        ("skill_ai", "charge_per_enemy"),
        ("skill_ai", "shadowstep"),
        ("skill_ai", "shadowstep_behind"),
        ("heuristics",),
        ("heuristics", "race", "min_ap_after"),
        ("heuristics", "estimate", "rune_cell_points"),
        ("heuristics", "scoring", "possible_kill_divisor"),
    ],
    ids=lambda p: "/".join(map(str, p)),
)
def test_ai_numbers_have_no_program_default(path: tuple[str, ...]) -> None:
    """程式不再有預設值：``ai_profiles.yaml`` 少寫一格就驗證失敗。"""
    data = _read(AI_FILE)
    _drop(data, path)
    with pytest.raises(ValidationError, match=path[-1]):
        AiProfileTable.model_validate(data)


def test_written_values_follow_the_content_file() -> None:
    """以前程式和內容檔不同的幾格，生效的一直是內容檔（結果不變）；沒寫的照程式原本的值寫進去。"""
    table = AiProfileTable.model_validate(_read(AI_FILE))
    assert table.move_candidates == 6  # 程式原本 8
    assert table.basic.aim_hit_permille == 700  # 程式原本 500
    assert table.summon.infuse_threat_damage == 2  # 程式原本 4
    assert table.skill_candidates == 3
    assert table.rewrite.redirect_min_hp_permille == 500
    assert table.heuristics.estimate.rune_cell_points == (3, 2, 1)


def test_the_heuristics_ride_in_the_ruleset() -> None:
    """不分行為模式的 AI 數值嵌入規則包（引擎從 ``state.ruleset.ai`` 讀，重播不依賴資料檔）。"""
    lib = library()
    assert lib.ruleset.ai == lib.ai_profiles.heuristics
    assert "ai" in Ruleset.model_fields


def test_the_engine_reads_the_heuristics_from_the_ruleset() -> None:
    """改規則包的值，引擎的 AI 估計跟著變（不是模組常數）。"""
    m = make_map("\n".join(["00000"] * 5), None, ally=[(0, 0)], enemy=[(3, 0)])
    spawns = [spawn(Team.ALLY, (0, 0), template()), spawn(Team.ENEMY, (3, 0), template())]
    state = make_state(m, spawns)
    unit = state.units[UnitId("unit_0001")]
    assert exposure(state, unit, (0, 0)) == 0
    unit.hp = unit.max_hp // 2
    assert not is_hurt(state, unit)
    scoring = state.ruleset.ai.scoring.model_copy(
        update={"exposure_radius": 3, "hurt_hp_permille": 500}
    )
    ai = state.ruleset.ai.model_copy(update={"scoring": scoring})
    state.ruleset = state.ruleset.model_copy(update={"ai": ai})
    assert exposure(state, unit, (0, 0)) == 1
    assert is_hurt(state, unit)
