"""穿透 ``pierce``（Phase 3C-5b，``docs/phases/Phase3C計畫.md`` 7A.4）。

穿透的遠程單體與直線技能：無視半掩護；射線穿過 ``penetrable`` 物件（木箱、倒木）時物件受全額傷害、
後方目標只受 ``pierce_behind_permille``（700‰）；石柱等非 ``penetrable`` 的物件照樣擋住。修正規則
``grant_pierce`` 讓帶標籤的技能獲得穿透；基本動作不能穿透。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    no_reactions,
    spawn,
    template,
)
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, UseSkill, legal_actions, resolve, start_battle
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    ObjectDamaged,
    ShotPierced,
)
from trpg.engine.preview import preview
from trpg.engine.skills.targeting import pierce_active
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget

U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
ROW = "0000000"
FLAT = "\n".join([ROW] * 7)
HERO = (0, 3)
ARROW = "skill_armor_piercing_arrow"
TIMBER = "skill_timber_piercer"
FIRE_ARROW = "skill_fire_arrow"


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def always(monkeypatch: pytest.MonkeyPatch, die: int = 4) -> None:
    """d20 一律 19（命中、不暴擊）、其他骰子一律 ``die``。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(die, sides))


def line_skill(**changes: Any) -> SkillDef:
    """測試專用：遠程直線、穿透的武器技（5 格）。"""
    data: dict[str, Any] = {
        "id": "skill_test_pierce_line",
        "name_zh": "測試穿透直線",
        "tier": 1,
        "rarity": "rare",
        "skeleton": "area",
        "category": "weapon",
        "weapon_req": "ranged",
        "ap_cost": 2,
        "scaling_attr": "dex",
        "shape": {"type": "line", "size": 5},
        "pierce": True,
        "effects": [{"type": "damage", "multiplier_permille": 1000}],
        "tags": ["ranged"],
    }
    data.update(changes)
    return SkillDef.model_validate(data)


def arena(
    skills: Sequence[str | SkillDef] = (ARROW,),
    *,
    objects: Sequence[tuple[int, int, str]] = (),
    foes: Sequence[tuple[int, int]] = ((4, 3),),
) -> BattleState:
    """U1 弓手（在 ``HERO``，裝備 ``skills``）；之後依序是 ``foes``（不反應、HP 200）。"""
    ids = [s if isinstance(s, str) else s.id for s in skills]
    given = [s for s in skills if isinstance(s, SkillDef)]
    m = make_map(FLAT, ally=[HERO], enemy=list(foes), objects=objects)
    hero = template("hero_archer", reactions=[], skills=ids, max_mana=99)
    spawns = [spawn(Team.ALLY, HERO, hero)]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    setup = make_setup(m, spawns, skills=given)
    return give_turn(start_battle(setup, 0), U1)


def shoot(target: UnitId = U2, skill: str = ARROW) -> UseSkill:
    return UseSkill(unit_id=U1, skill_id=skill, target_id=target)


def aim(direction: str, skill: str) -> UseSkill:
    return UseSkill(unit_id=U1, skill_id=skill, direction=direction)  # type: ignore[arg-type]


def rolled(events: Sequence[EventBase]) -> AttackRolled:
    return of(events, AttackRolled)[0]


def dealt(events: Sequence[EventBase], unit: UnitId) -> int:
    (hit,) = [d for d in of(events, DamageDealt) if d.target_id == unit and d.cause == "attack"]
    return hit.amount


# ---------------------------------------------------------------------------
# 無視半掩護
# ---------------------------------------------------------------------------


def test_pierce_ignores_half_cover(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    covered = arena((ARROW, FIRE_ARROW), objects=[(3, 3, "crate")])
    plain = resolve(covered, shoot(skill=FIRE_ARROW))
    assert rolled(plain.events).cover == -covered.ruleset.core.half_cover_hit_penalty
    pierced = resolve(covered, shoot())
    assert rolled(pierced.events).cover == 0 and rolled(pierced.events).cover_object_id is None


def test_a_stone_pillar_still_blocks_the_shot() -> None:
    state = arena((ARROW,), objects=[(2, 3, "stone_pillar")])
    # 3-24a1：弓有拋射、能越過 1 格高的石柱；這裡驗證一般（無拋射）武器的視線，改用無拋射的弓
    state.units[U1].weapon = state.units[U1].weapon.model_copy(update={"lob": 0})
    with pytest.raises(IllegalActionError, match="視線"):
        resolve(state, shoot())
    assert not any(
        isinstance(a, UseSkill) and a.skill_id == ARROW and a.target_id == U2
        for a in legal_actions(state)
    )


# ---------------------------------------------------------------------------
# 穿過 penetrable 物件
# ---------------------------------------------------------------------------


def test_the_shot_passes_a_crate_which_takes_full_damage_while_the_target_takes_70_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    bare = resolve(arena(), shoot())
    full = dealt(bare.events, U2)
    blocked = arena(objects=[(2, 3, "crate")])
    result = resolve(blocked, shoot())
    behind = dealt(result.events, U2)
    assert abs(behind - full * 700 // 1000) <= 1 and behind < full
    (crate,) = of(result.events, ObjectDamaged)
    assert crate.source_id == U1
    assert abs(crate.amount - full) <= 1  # 物件受全額傷害（沒有後方折扣）
    (event,) = of(result.events, ShotPierced)
    assert (event.unit_id, event.skill_id, event.behind) == (U1, ARROW, (U2,))
    assert event.behind_permille == blocked.ruleset.core.pierce_behind_permille == 700
    assert [(p.x, p.y) for p in event.object_tiles] == [(2, 3)]
    assert [(p.x, p.y) for p in event.route] == [(1, 3), (2, 3), (3, 3)]


def test_a_fallen_log_is_pierced_too_and_a_shot_without_objects_emits_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    log = resolve(arena(objects=[(1, 3, "fallen_log")]), shoot())
    assert len(of(log.events, ShotPierced)) == 1
    assert not of(resolve(arena(), shoot()).events, ShotPierced)


def test_a_penetrable_object_beside_the_route_is_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(arena(objects=[(2, 2, "crate")]), shoot())
    assert not of(result.events, ShotPierced) and not of(result.events, ObjectDamaged)


def test_the_line_passes_a_crate_and_only_the_units_behind_it_are_discounted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    skill = line_skill()
    foes = [(1, 3), (3, 3), (5, 3)]
    base = resolve(arena([skill], foes=foes), aim("east", skill.id))
    assert not of(base.events, ShotPierced)
    result = resolve(arena([skill], objects=[(2, 3, "crate")], foes=foes), aim("east", skill.id))
    full = {u: dealt(base.events, u) for u in (U2, U3, U4)}
    after = {u: dealt(result.events, u) for u in full}
    assert after[U2] == full[U2]  # 木箱前面的目標不打折
    for unit in (U3, U4):  # 木箱後面的兩個目標都打折
        assert abs(after[unit] - full[unit] * 700 // 1000) <= 1 and after[unit] < full[unit]
    (event,) = of(result.events, ShotPierced)
    assert event.behind == (U3, U4)
    assert of(result.events, ObjectDamaged)  # 木箱同樣受傷


def test_a_pillar_stops_the_line(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    skill = line_skill()
    state = arena([skill], objects=[(2, 3, "stone_pillar")], foes=[(1, 3), (4, 3)])
    result = resolve(state, aim("east", skill.id))
    hit = {d.target_id for d in of(result.events, DamageDealt)}
    assert hit == {U2}  # 石柱（阻擋視線）擋住：後方的目標打不到
    assert not of(result.events, ShotPierced)


# ---------------------------------------------------------------------------
# grant_pierce 與基本動作
# ---------------------------------------------------------------------------


def test_grant_pierce_gives_a_tagged_skill_pierce(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    objects = [(3, 3, "crate")]
    without = resolve(arena((FIRE_ARROW,), objects=objects), shoot(skill=FIRE_ARROW))
    assert rolled(without.events).cover != 0 and not of(without.events, ShotPierced)
    granted = resolve(arena((FIRE_ARROW, TIMBER), objects=objects), shoot(skill=FIRE_ARROW))
    assert rolled(granted.events).cover == 0
    assert len(of(granted.events, ShotPierced)) == 1


def test_grant_pierce_needs_the_tag_the_shape_and_a_ranged_skill() -> None:
    rules = library().ruleset
    bare = arena((FIRE_ARROW,))
    assert pierce_active(bare, bare.units[U1], rules.skill_def(FIRE_ARROW)) is False
    granted = arena((FIRE_ARROW, TIMBER))
    hero = granted.units[U1]
    assert pierce_active(granted, hero, rules.skill_def(FIRE_ARROW)) is True
    untagged = line_skill(id="skill_test_no_tag", tags=["line"], pierce=False)
    assert pierce_active(granted, hero, untagged) is False  # 沒有 ranged 標籤
    cone = line_skill(pierce=False, shape={"type": "cone", "size": 3})
    assert pierce_active(granted, hero, cone) is False  # 形狀不對


def test_a_basic_attack_cannot_pierce(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena((ARROW, TIMBER), objects=[(3, 3, "crate")])
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert rolled(result.events).cover != 0  # 普攻：半掩護照常
    assert not of(result.events, ShotPierced)


# ---------------------------------------------------------------------------
# 資料：schema、預算、預覽
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"weapon_req": "melee"},  # 近戰武器技
        {"shape": {"type": "cone", "size": 3}},  # 錐形
        {"shape": {"type": "single", "range": 1}},  # 射程 1 的單體
        {"effects": [{"type": "knock_prone"}]},  # 沒有傷害效果
        {"kind": "passive", "ap_cost": None, "trigger": {"event": "on_hit"}},
    ],
)
def test_pierce_is_limited_to_ranged_single_and_line_skills(changes: Mapping[str, Any]) -> None:
    with pytest.raises(ValidationError):
        line_skill(**changes)


def test_grant_pierce_must_be_true_and_cannot_target_basic_actions() -> None:
    base = library().ruleset.skill_def(TIMBER).model_dump(mode="json")
    rule = base["modifiers"][0]
    with pytest.raises(ValidationError):
        SkillDef.model_validate(
            {**base, "modifiers": [{**rule, "change": {"grant_pierce": False}}]}
        )
    attack = {"applies_to": {"actions": ["attack"]}, "change": {"grant_pierce": True}}
    with pytest.raises(ValidationError, match="grant_pierce"):
        SkillDef.model_validate({**base, "modifiers": [attack]})


def test_pierce_adds_the_budget_bonus_from_the_content_file() -> None:
    lib = library()
    arrow = lib.ruleset.skill_def(ARROW)
    with_pierce = skill_budget(arrow, lib)
    without = skill_budget(arrow.model_copy(update={"pierce": False}), lib)
    bonus = lib.budget.pierce_bonus_permille
    assert bonus == 150
    assert with_pierce.total * 1000 == without.total * (1000 + bonus)
    assert with_pierce.ok and skill_budget(lib.ruleset.skill_def(TIMBER), lib).ok


def test_the_preview_hit_chance_ignores_cover_and_matches_the_roll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = arena((ARROW, FIRE_ARROW), objects=[(3, 3, "crate")])
    covered = preview(state, shoot(skill=FIRE_ARROW)).targets[0].hit_chance
    pierced = preview(state, shoot()).targets[0].hit_chance
    assert pierced > covered  # 半掩護的 −2 沒有了
    always(monkeypatch)
    assert rolled(resolve(state, shoot()).events).cover == 0
