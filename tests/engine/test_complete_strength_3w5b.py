"""Phase 3W-5b：完整技能的召喚強度與姿態幅度在戰鬥中生效，卡片數字＝實戰。"""

from __future__ import annotations

from tests.engine.helpers import library
from tests.engine.skill_helpers import U1
from tests.engine.test_stance_upkeep_3w2b import _scene, _stance
from tests.engine.test_summon_growth import arena, cast_at
from trpg.api.hero_cards import unit_card_owner
from trpg.content.skills import SkillDef
from trpg.engine import UseSkill, resolve
from trpg.engine.rules.statuses import (
    damage_dealt_permille,
    damage_taken_permille,
    move_points_for_turn,
    scaled_permille,
)
from trpg.engine.state import StatusInstance
from trpg.narrative.skills import skill_card
from trpg.roguelite.offers import as_complete
from trpg.shared.types import Element


def _pct(permille: int) -> str:
    return f"×{permille / 10:g}%"


def test_scaled_permille_only_grows_the_good_side() -> None:
    assert scaled_permille(1150, 1200, "up") == 1180
    assert scaled_permille(700, 1200, "down") == 640
    assert scaled_permille(500, 1200, "up") == 500  # 移動減半是代價：不放大
    assert scaled_permille(1250, 1200, "down") == 1250
    assert scaled_permille(1150, 1000, "up") == 1150


def _with_magnitude(stance: SkillDef, magnitude: int) -> SkillDef:
    (effect,) = stance.effects
    return stance.model_copy(
        update={"effects": (effect.model_copy(update={"magnitude_permille": magnitude}),)}
    )


def test_stance_magnitude_is_applied_and_the_card_shows_the_real_number() -> None:
    stance = _with_magnitude(_stance("skill_t_stance_m", "stance_fire_2", 1), 1200)
    SkillDef.model_validate(stance.model_dump(mode="json"))  # 欄位合法
    state = resolve(_scene(stance), UseSkill(unit_id=U1, skill_id=stance.id)).state
    (status,) = [s for s in state.units[U1].statuses if s.status_id == "stance_fire_2"]
    assert status.magnitude_permille == 1200
    rules = state.ruleset
    actual = damage_dealt_permille(rules, state.units[U1], Element.FIRE)
    assert actual == 1180  # 1150 的 +150 × 1.2
    card = skill_card(library(), stance)
    assert any(_pct(actual) in line and "幅度強化 ×120%" in line for line in card.effects)


def test_defensive_stance_magnitude_keeps_its_drawback() -> None:
    lib = library()
    state = _scene(_stance("skill_t_stance_g", "stance_guard", 0))
    unit = state.units[U1]
    rules = state.ruleset
    unit.statuses = [StatusInstance("stance_guard", magnitude_permille=1200)]
    taken = damage_taken_permille(rules, unit, Element.FIRE)
    moves = move_points_for_turn(rules, unit)
    unit.statuses = [StatusInstance("stance_guard")]
    assert taken == 640 < damage_taken_permille(rules, unit, Element.FIRE) == 700
    assert moves == move_points_for_turn(rules, unit)  # 移動減少照原值
    stance = _with_magnitude(_stance("skill_t_stance_g", "stance_guard", 0), 1200)
    line = next(e for e in skill_card(lib, stance).effects if "幅度強化" in e)
    assert _pct(640) in line and _pct(500) in line


def test_complete_summon_hp_and_damage_match_the_card() -> None:
    lib = library()
    done = as_complete(lib, lib.skills["skill_summon_fire_spirit"])
    (spec,) = [e for e in done.effects if e.type == "summon"]
    assert spec.power_permille is not None and spec.power_permille > 1000
    plain_state, plain_id = cast_at(
        arena(["skill_summon_fire_spirit"]), "skill_summon_fire_spirit", 2, 3
    )
    before = arena([done])
    owner = unit_card_owner(before, before.units[U1], done)  # 網頁卡片用的持有者（實際值）
    state, sid = cast_at(before, done.id, 2, 3)
    summon = state.units[sid]
    assert summon.summon_power_permille == spec.power_permille
    assert summon.max_hp == plain_state.units[plain_id].max_hp * spec.power_permille // 1000
    (card,) = skill_card(lib, done, owner=owner).summons
    assert card.basis == "actual" and card.hp == summon.max_hp  # 卡片 HP ＝ 實際召喚出來的 HP
    assert _pct(spec.power_permille) in card.attack
    (base_card,) = skill_card(lib, done).summons  # 1 級基準值也乘上強度
    (plain_card,) = skill_card(lib, lib.skills["skill_summon_fire_spirit"]).summons
    assert base_card.hp == plain_card.hp * spec.power_permille // 1000
