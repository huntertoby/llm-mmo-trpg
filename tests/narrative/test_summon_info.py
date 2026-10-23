"""召喚物說明（Phase 3-41a，清單第 1 節）：HP 和引擎同一個算法、自帶能力、圖騰類行為、冰靈。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    spawn,
)
from trpg.content.skills import EffectSpec, SkillDef
from trpg.engine import UseSkill, resolve
from trpg.engine.events import UnitSummoned
from trpg.narrative.skills import skill_card
from trpg.narrative.summon_info import summon_card_hp
from trpg.shared.types import Pos, Team, UnitId

U1 = UnitId("unit_0001")
SID = "skill_t_card_summon"
FLAT = "\n".join(["0000000"] * 7)


def _summon_effects() -> list[tuple[str, int, EffectSpec]]:
    """內容裡所有技能的召喚效果：（技能 ID、效果序號、效果）。"""
    lib = library()
    return [
        (skill.id, i, e)
        for skill in sorted(lib.skills.values(), key=lambda s: s.id)
        for i, e in enumerate(skill.effects)
        if e.type == "summon"
    ]


def _engine_summons(skill: SkillDef, spec: EffectSpec) -> list[tuple[int, str | None]]:
    """1 級、縮放屬性修正 0 的施放者用 ``spec`` 召喚：每隻召喚物的（最大 HP、施放時選的灌注）。"""
    lib = library()
    effect = spec.model_dump(mode="json", exclude_none=True)
    test_skill = make_skill(
        SID, {"type": "ground_tile", "range": 4}, [effect], attr=skill.scaling_attr.value
    )
    base = lib.ruleset.core.ability_mod_base
    caster = caster_template([test_skill], attributes={skill.scaling_attr.value: base})
    m = make_map(FLAT, None, ally=[(0, 3)], enemy=[(6, 6)])
    spawns = [spawn(Team.ALLY, (0, 3), caster), spawn(Team.ENEMY, (6, 6), caster_template([]))]
    state = give_turn(make_state(m, spawns, skills=[test_skill]), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=SID, target_pos=Pos(x=2, y=3)))
    events = [e for e in result.events if isinstance(e, UnitSummoned)]
    assert events
    units = result.state.units
    return [(units[e.unit_id].max_hp, units[e.unit_id].infusion) for e in events]


@pytest.mark.parametrize(("skill_id", "index", "spec"), _summon_effects())
def test_card_hp_matches_the_engine(skill_id: str, index: int, spec: EffectSpec) -> None:
    """表格測試：每個召喚技能的卡片 HP 和引擎生成的召喚物最大 HP 相同（同一組輸入）。"""
    lib = library()
    skill = lib.skills[skill_id]
    summon = lib.ruleset.summon_def(spec.unit or "")
    for max_hp, chosen in _engine_summons(skill, spec):
        assert summon_card_hp(lib, summon, spec, chosen_infusion=chosen) == max_hp
    info = skill_card(lib, skill).summons[index if len(skill.effects) == 1 else 0]
    assert info.hp == summon_card_hp(lib, summon, spec)


def test_every_summon_skill_has_an_info_card_and_innate_text() -> None:
    lib = library()
    for skill_id, _, spec in _summon_effects():
        card = skill_card(lib, lib.skills[skill_id])
        [info] = [s for s in card.summons if s.id == spec.unit]
        summon = lib.ruleset.summon_def(info.id)
        effect = next(e for e in card.effects if summon.template.name_zh in e)
        assert f"HP {info.hp}" in effect and "灌注：" in effect
        if info.innate:
            assert "自帶：" in effect and all(line in effect for line in info.innate)


def test_skeleton_shows_its_shield_bash_and_role_scaled_hp() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_raise_skeleton"])
    [info] = card.summons
    template = lib.ruleset.summon_def("summon_skeleton_warrior").template
    role = lib.ruleset.core.summon_role_hp_permille["melee"]
    assert info.hp == lib.ruleset.core.template_max_hp(template) * role // 1000
    assert info.innate == ("普攻命中時絆倒目標使其「倒地」（敏捷對抗，每隻每輪 1 次）",)
    assert info.attack.startswith("單手劍：") and info.move == "4 格"


def test_ice_spirit_slows_and_freezes_targets_standing_in_water() -> None:
    """清單 1.3（A′）：規則不變，說明依 ``hit_rules`` 寫出緩速與水上冰凍。"""
    lib = library()
    [info] = skill_card(lib, lib.skills["skill_summon_ice_spirit"]).summons
    assert info.innate == (
        "普攻命中時施加「緩速」2 回合",
        "普攻命中站在水上的目標時施加「冰凍」1 回合",
    )


@pytest.mark.parametrize(
    "skill_id",
    ["skill_summon_plateau_totem", "skill_summon_pull_totem", "skill_summon_earth_wall"],
)
def test_totems_and_walls_do_not_move_or_attack(skill_id: str) -> None:
    """清單 1.5：高台圖騰、吸引圖騰、土牆寫「不移動、不攻擊」，不寫普攻相關的自帶能力。"""
    lib = library()
    card = skill_card(lib, lib.skills[skill_id])
    [info] = card.summons
    assert info.attack == "不攻擊" and info.move == "不移動"
    assert info.behavior[0].startswith("不移動、不攻擊")
    assert "不移動、不攻擊" in card.effects[0] and "由 AI 控制" not in card.effects[0]
    assert not any("普攻" in line for line in info.innate)


def test_support_summons_describe_their_pulse() -> None:
    """清單 1.6：守護靈給護盾、水精治療並造水。"""
    lib = library()
    [guardian] = skill_card(lib, lib.skills["skill_summon_guardian_spirit"]).summons
    assert any("HP 比例最低的友方" in line and "護盾" in line for line in guardian.innate)
    [sprite] = skill_card(lib, lib.skills["skill_summon_water_sprite"]).summons
    assert any("治療" in line and "「水」" in line for line in sprite.innate)
