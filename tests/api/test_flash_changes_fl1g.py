"""FL-1g：選變體畫面「前 → 後」的美術驗收修正（``docs/art/FL-1b驗收.md`` 第 2、3 節）。

- 必修 1：代價變少照 ``better``，只有變多才是 ``cost``；
- 必修 2：倍率型（武器傷害）的新傷害寫出元素；
- 可修 2：條件字的技能標籤查 ``skill_tags``（不再退回「特定」）；
- 可修 3：同一張卡兩段同名時加段名；
- 可修 4：同一個狀態挪位置又改回合時併成一列。
"""

from __future__ import annotations

from tests.engine.helpers import library as _load_library
from trpg.api.flash_changes import flash_changes
from trpg.content.skills import ConditionSpec, EffectSpec, SkillDef
from trpg.shared.types import Element

LIB = _load_library()


def _skill(skill_id: str) -> SkillDef:
    return LIB.skills[skill_id]


def _with_cost(skill: SkillDef, **cost: int) -> SkillDef:
    return skill.model_copy(update={"cost": skill.cost.model_copy(update=cost)})


def test_cheaper_cost_is_better_and_pricier_is_cost() -> None:
    base = _skill("skill_akimbo_burst")
    cheaper = _with_cost(base, cooldown=1)
    rows = {c.field: c.direction for c in flash_changes(LIB, base, cheaper)}
    assert rows == {"cost.cooldown": "better"}
    rows = {c.field: c.direction for c in flash_changes(LIB, cheaper, base)}
    assert rows == {"cost.cooldown": "cost"}


def test_added_weapon_damage_names_its_element() -> None:
    base = _skill("skill_akimbo_burst")
    hit = EffectSpec(type="damage", element=Element.LIGHTNING, multiplier_permille=300)
    after = base.model_copy(update={"effects": (*base.effects, hit)})
    (row,) = [c for c in flash_changes(LIB, base, after) if c.before is None]
    assert row.after_zh == "3 成[[weapon_damage:300|雷電武器傷害]]"
    physical = hit.model_copy(update={"element": Element.PHYSICAL})
    after = base.model_copy(update={"effects": (*base.effects, physical)})
    (row,) = [c for c in flash_changes(LIB, base, after) if c.before is None]
    assert row.after_zh == "3 成[[weapon_damage:300|武器傷害]]"


def test_cast_tag_condition_uses_the_tag_name() -> None:
    base = _skill("skill_akimbo_burst")
    hit = EffectSpec(
        type="damage",
        multiplier_permille=300,
        condition=ConditionSpec(type="cast_tag_this_turn", tag="lightning"),
    )
    after = base.model_copy(update={"effects": (*base.effects, hit)})
    (row,) = [c for c in flash_changes(LIB, base, after) if c.before is None]
    assert row.after_zh is not None
    assert "「雷電」" in row.after_zh
    assert "特定" not in row.after_zh


def test_two_segments_with_the_same_name_get_segment_names() -> None:
    base = _skill("skill_akimbo_burst")
    first, second = base.effects
    weaker = (
        first.model_copy(update={"multiplier_permille": 700}),
        second.model_copy(update={"multiplier_permille": 400}),
    )
    after = base.model_copy(update={"effects": weaker})
    names = [c.name_zh for c in flash_changes(LIB, base, after)]
    assert names == ["傷害（第 1 段）", "傷害（第 2 段）"]
    only_one = base.model_copy(update={"effects": (weaker[0], second)})
    assert [c.name_zh for c in flash_changes(LIB, base, only_one)] == ["傷害"]


def test_moved_status_with_new_rounds_is_one_row() -> None:
    base = _skill("skill_cinder_dive")
    hit, burn = base.effects
    extra = EffectSpec(type="damage", element=Element.LIGHTNING, dice=hit.dice)
    longer = burn.model_copy(update={"duration": (burn.duration or 2) + 1})
    after = base.model_copy(update={"effects": (hit, extra, longer)})
    rows = flash_changes(LIB, base, after)
    burning = [c for c in rows if c.icon is not None and c.icon.id == "burning"]
    assert len(burning) == 1
    (row,) = burning
    assert (row.field, row.before_zh, row.after_zh, row.direction) == (
        "effects[2].amount",
        f"{burn.duration} 回合",
        f"{longer.duration} 回合",
        "better",
    )
    assert any(c.field == "effects[1]" and c.direction == "new" for c in rows)
