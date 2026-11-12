"""Phase BAL-21a：延遲段落點 ``followup.anchor`` 與頭目階段 ``mana_restore`` 的內容檢查。

- ``anchor`` 只有 ``when: delayed`` 可以填，第一段的形狀要選一個格子
  （:data:`ANCHOR_FIRST_SHAPES`）；
- 兩個欄位沒填時都不輸出：現有內容的序列化（規則包雜湊）不變；
- 現有內容都沒有填（本段不改 ``content/``）；BAL-21b 起只有 :data:`ANCHORED_BUILTINS` 有填。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.battle import BossPhase, check_phases
from trpg.content.skills import ANCHOR_FIRST_SHAPES, SkillDef

#: 內建技能裡填了 ``anchor`` 的（BAL-21b 灰燼之心的熔岩濺落）；其他都不輸出 ``anchor``。
ANCHORED_BUILTINS = frozenset({"skill_lava_splash"})


def skill_data(*, shape: dict[str, Any] | None = None, **follow: Any) -> dict[str, Any]:
    second: dict[str, Any] = {
        "when": "delayed",
        "release": "next_turn",
        "anchor": "cast_tile",
        "skeleton": "area",
        "shape": {"type": "square3", "range": 0},
        "effects": [{"type": "damage", "dice": "1d6", "element": "fire"}],
    }
    second.update(follow)
    return {
        "id": "skill_t_anchor",
        "name_zh": "測試落點",
        "tier": 1,
        "rarity": "rare",
        "skeleton": "aura",
        "category": "spell",
        "weapon_req": "any",
        "ap_cost": 2,
        "scaling_attr": "int",
        "shape": shape or {"type": "ground_tile", "range": 4},
        "effects": [{"type": "shield", "dice": "1d4", "affects": "self"}],
        "followup": {k: v for k, v in second.items() if v is not None},
        "cost": {"mana": 6, "cooldown": 2},
    }


@pytest.mark.parametrize(
    "shape",
    [
        {"type": "ground_tile", "range": 4},
        {"type": "square3", "range": 4},
        {"type": "cross", "range": 3},
    ],
)
def test_tile_picking_first_stages_can_anchor(shape: dict[str, Any]) -> None:
    skill = SkillDef.model_validate(skill_data(shape=shape))
    assert skill.followup is not None and skill.followup.anchor == "cast_tile"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (skill_data(shape={"type": "self"}), "第一段的形狀要選一個格子"),
        (skill_data(shape={"type": "ring", "radius": 1}), "第一段的形狀要選一個格子"),
        (skill_data(anchor="caster"), "anchor"),
    ],
)
def test_bad_anchors_fail_to_load(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        SkillDef.model_validate(data)


def _on_hit(anchor: str | None) -> dict[str, Any]:
    data = skill_data(when="on_hit", release=None, anchor=anchor, shape={"type": "single"})
    data["skeleton"] = "strike"
    data["followup"]["skeleton"] = "strike"
    data["followup"]["shape"] = {"type": "single"}
    data["followup"]["effects"] = [{"type": "damage", "multiplier_permille": 500}]
    data["effects"] = [{"type": "damage", "multiplier_permille": 1000}]
    data["category"] = "weapon"
    data["weapon_req"] = "melee"
    data["scaling_attr"] = "str"
    data["cost"] = {"stamina": 1, "cooldown": 2}
    return data


def test_only_delayed_segments_can_anchor() -> None:
    SkillDef.model_validate(_on_hit(None))  # 對照：拿掉 anchor 就能載入
    with pytest.raises(ValidationError, match="只有延遲段（when: delayed）可以指定 anchor"):
        SkillDef.model_validate(_on_hit("cast_tile"))


def test_anchor_first_shapes_are_exactly_the_tile_picking_shapes() -> None:
    shapes = library().ruleset.shapes
    tile = sorted(s.id for s in shapes.shapes if s.targeting == "tile")
    assert sorted(ANCHOR_FIRST_SHAPES) == tile


def test_unset_fields_are_not_serialized() -> None:
    lib = library()
    for skill in lib.skills.values():
        if skill.followup is not None and skill.id not in ANCHORED_BUILTINS:
            assert "anchor" not in skill.followup.model_dump(), skill.id
            assert skill.followup.anchor is None, skill.id
    for unit in lib.units.values():
        for phase in unit.phases:
            assert "mana_restore" not in phase.model_dump(), unit.id
    for skill_id in sorted(ANCHORED_BUILTINS):
        followup = lib.skills[skill_id].followup
        assert followup is not None and followup.model_dump()["anchor"] == "cast_tile"
    anchored = SkillDef.model_validate(skill_data())
    assert anchored.model_dump()["followup"]["anchor"] == "cast_tile"


def test_mana_restore_is_optional_positive_and_not_for_the_opening_phase() -> None:
    later = BossPhase.model_validate(
        {
            "id": "two",
            "name_zh": "二",
            "trigger": {"kind": "hp_below", "permille": 500},
            "mana_restore": 30,
        }
    )
    assert later.mana_restore == 30 and later.model_dump()["mana_restore"] == 30
    assert later.changes_anything()
    with pytest.raises(ValidationError):
        BossPhase.model_validate({"id": "two", "name_zh": "二", "mana_restore": 0})
    opening = BossPhase.model_validate({"id": "one", "name_zh": "一", "mana_restore": 10})
    assert any("開場階段" in p for p in check_phases((opening, later)))
