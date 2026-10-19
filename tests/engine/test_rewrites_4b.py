"""改寫規則型原語（Phase 3C-4b）：``redirect_damage``、``copy_skill``、``extra_reaction``。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_skill,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, U3, U4, of
from tests.engine.test_intercept import scene as intercept_scene
from tests.engine.test_passive_triggers import always
from trpg.content.battle import UnitTemplate
from trpg.content.skills import SkillDef, skill_problems
from trpg.engine import (
    Attack,
    BattleState,
    Decision,
    EndTurn,
    UseSkill,
    legal_actions,
    preview,
    resolve,
    resume,
    state_from_json,
    state_to_json,
)
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import legal_actions_with_areas
from trpg.engine.context import Ctx
from trpg.engine.copying import copy_problem, copy_selections, copy_source, uncopyable_reason
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import (
    DamageDealt,
    DamageRedirected,
    EffectFizzled,
    ReactionsGranted,
    ReactionTriggered,
    SkillCopied,
    StatusApplied,
    StatusRemoved,
    UnitDowned,
)
from trpg.engine.runner import replay, run_battle
from trpg.engine.setup import build_setup
from trpg.engine.state import LastCast, StatusInstance, reaction_limit
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Team, UnitId
from trpg.sim.lineup import build_allies, default_lineup

LINK = "skill_t_link"
COPY = "skill_t_copy"
BOLT = "skill_t_bolt"
BELL = "skill_t_bell"


@pytest.fixture
def always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)


def _problems(skill: SkillDef) -> list[str]:
    rules = library().ruleset
    return skill_problems(
        skill,
        rules.shapes.by_id(),
        rules.primitives.by_id(),
        status_ids={s.id for s in rules.statuses.statuses},
        object_ids={o.id for o in rules.objects.objects},
        conditions=rules.conditions.by_id(),
    )


# ---------------------------------------------------------------------------
# redirect_damage
# ---------------------------------------------------------------------------

LINK_EFFECT = {"type": "redirect_damage", "permille": 400, "duration": 3, "affects": "allies"}


def link_scene() -> BattleState:
    """U1 施放者（我方）、U2 隊友、U3 敵人；輪到 U1。"""
    skill = make_skill(LINK, {"type": "single", "range": 4}, [LINK_EFFECT])
    m = make_map(FLAT7, ally=[(3, 3), (4, 4)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([skill])),
        spawn(Team.ALLY, (4, 4), no_reactions("hero_fighter"), skills=None),
        spawn(Team.ENEMY, (4, 3), no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[skill]), U1)


def linked(state: BattleState, *, permille: int = 500, source: UnitId = U1) -> BattleState:
    """U2 身上有以 ``source`` 為連結者的靈魂連結。"""
    state.units[U2].statuses.append(StatusInstance("soul_link", 3, source, permille))
    return state


def test_redirect_damage_links_an_ally_to_the_caster() -> None:
    result = resolve(link_scene(), UseSkill(unit_id=U1, skill_id=LINK, target_id=U2))
    (applied,) = of(result, StatusApplied)
    assert (applied.target_id, applied.status_id, applied.duration) == (U2, "soul_link", 3)
    link = result.state.units[U2].get_status("soul_link")
    assert link is not None and (link.source_id, link.amount) == (U1, 400)


def test_redirect_damage_on_the_caster_does_nothing() -> None:
    result = resolve(link_scene(), UseSkill(unit_id=U1, skill_id=LINK, target_id=U1))
    assert not result.state.units[U1].statuses
    assert [e.reason for e in of(result, EffectFizzled)] == ["self_link"]


def test_a_new_link_replaces_the_old_one() -> None:
    state = linked(link_scene(), permille=500, source=U3)
    result = resolve(state, UseSkill(unit_id=U1, skill_id=LINK, target_id=U2))
    link = result.state.units[U2].get_status("soul_link")
    assert link is not None and (link.source_id, link.amount) == (U1, 400)


def test_redirected_damage_goes_to_the_caster_and_not_the_ally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, die=6)
    state = linked(link_scene(), permille=500)
    result = resolve(give_turn(state, U3), Attack(unit_id=U3, target_id=U2))
    (hit,) = of(result, DamageDealt)
    (moved,) = of(result, DamageRedirected)
    assert hit.target_id == U2 and hit.redirected == moved.amount == (hit.amount * 500) // 1000
    assert hit.hp_before - hit.hp_after == hit.amount - hit.absorbed - hit.redirected
    assert (moved.from_id, moved.to_id, moved.status_id) == (U2, U1, "soul_link")
    assert result.state.units[U1].hp == state.units[U1].hp - moved.amount
    assert result.state.units[U2].hp == state.units[U2].hp - (hit.amount - hit.redirected)


def test_redirect_takes_the_part_that_got_past_the_shield() -> None:
    state = linked(link_scene(), permille=500)
    state.units[U2].statuses.append(StatusInstance("shielded", 2, U2, 3))
    ctx = Ctx(state)
    damage = DamageEffect.model_validate(
        {"target_id": U2, "cause": "effect", "flat": 10, "element": "fire"}
    )
    execute(ctx, [damage])
    (hit,) = [e for e in ctx.events if isinstance(e, DamageDealt)]
    assert hit.absorbed == 3 and hit.redirected == (hit.amount - 3) * 500 // 1000 > 0


def test_intercept_comes_first_and_the_link_follows_the_guardian(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """被攔下的攻擊落在守護者身上：原目標的連結不轉移；守護者自己有連結才轉移。"""
    always(monkeypatch)
    state = intercept_scene(guardians=((4, 4), (6, 6)))  # U3 相鄰守護者、U4 太遠
    state.units[U2].statuses.append(StatusInstance("soul_link", 3, U4, 500))
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not of(result, DamageRedirected)
    assert result.state.units[U4].hp == state.units[U4].hp
    state.units[U3].statuses.append(StatusInstance("soul_link", 3, U4, 500))
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    (hit,) = of(result, DamageDealt)
    (moved,) = of(result, DamageRedirected)
    assert hit.target_id == U3 and (moved.from_id, moved.to_id) == (U3, U4)
    assert result.state.units[U2].hp == state.units[U2].hp


def test_the_caster_going_down_from_the_transfer_ends_the_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, die=6)
    state = linked(link_scene(), permille=500)
    state.units[U1].hp = 1
    result = resolve(give_turn(state, U3), Attack(unit_id=U3, target_id=U2))
    (moved,) = of(result, DamageRedirected)
    assert (moved.hp_before, moved.hp_after) == (1, 0)
    assert result.state.units[U1].downed and any(isinstance(e, UnitDowned) for e in result.events)
    assert not result.state.units[U2].has_status("soul_link")
    assert [(e.target_id, e.reason) for e in of(result, StatusRemoved)] == [(U2, "source_lost")]


def test_undying_on_the_caster_survives_the_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch, die=6)
    state = linked(link_scene(), permille=500)
    state.units[U1].hp = 1
    state.units[U1].statuses.append(StatusInstance("undying", 2, U1))
    result = resolve(give_turn(state, U3), Attack(unit_id=U3, target_id=U2))
    assert result.state.units[U1].hp == 1 and not result.state.units[U1].downed
    assert result.state.units[U2].has_status("soul_link")


@pytest.mark.parametrize(
    ("cause", "mode"), [("fall", "percent_max_hp"), ("deadly_terrain", "lethal")]
)
def test_falls_and_deadly_terrain_are_not_redirected(cause: str, mode: str) -> None:
    state = linked(link_scene(), permille=500)
    ctx = Ctx(state)
    damage = DamageEffect.model_validate(
        {"target_id": U2, "cause": cause, "mode": mode, "permille": 500, "apply_element_mod": False}
    )
    execute(ctx, [damage])
    assert not [e for e in ctx.events if isinstance(e, DamageRedirected)]
    assert state.units[U1].hp == link_scene().units[U1].hp


def test_the_link_cannot_target_enemies_or_exceed_half() -> None:
    shape = {"type": "single", "range": 4}
    enemies = make_skill(LINK, shape, [{**LINK_EFFECT, "affects": "enemies"}])
    assert any("affects" in p or "enemies" in p for p in _problems(enemies))
    too_much = make_skill(LINK, shape, [{**LINK_EFFECT, "permille": 600}])
    assert any("permille" in p for p in _problems(too_much))


def _support_state(skill: SkillDef, ally: UnitTemplate) -> BattleState:
    m = make_map(FLAT7, ally=[(0, 0), (0, 1)], enemy=[(6, 6)])
    hero = caster_template([skill], base="hero_mage").model_copy(update={"ai_profile": "support"})
    spawns = [
        spawn(Team.ALLY, (0, 0), hero),
        spawn(Team.ALLY, (0, 1), ally),
        spawn(Team.ENEMY, (6, 6), no_reactions()),
    ]
    return give_turn(make_state(m, spawns), U1)


def test_the_ai_links_a_wounded_ally_only_when_the_caster_is_healthy() -> None:
    lib = library()
    policy = UtilityAI(lib.ai_profiles)
    skill = lib.skills["skill_soul_bond"]
    state = _support_state(skill, no_reactions("hero_fighter"))
    state.units[U2].hp = 5
    pick = policy(state)
    assert isinstance(pick, UseSkill) and pick.skill_id == "skill_soul_bond"
    state.units[U1].hp = 4  # 施放者自己快倒了：不連結
    pick = policy(state)
    assert not (isinstance(pick, UseSkill) and pick.skill_id == "skill_soul_bond")


# ---------------------------------------------------------------------------
# copy_skill
# ---------------------------------------------------------------------------

WALL_ROW3 = "\n".join(["0000000"] * 3 + ["0000300"] + ["0000000"] * 3)
BOLT_EFFECT = {"type": "damage", "dice": "1d6", "element": "fire", "affects": "enemies"}


def copy_scene(heights: str = FLAT7) -> BattleState:
    """U1（我方，有複製技能）(3,3)、U2（我方）(2,3)、U3（敵人，有 BOLT）(5,3)、U4（敵人）(5,5)；
    輪到 U1。"""
    copy = make_skill(COPY, {"type": "self"}, [{"type": "copy_skill"}])
    bolt = make_skill(
        BOLT, {"type": "single", "range": 5}, [BOLT_EFFECT], cost={"mana": 3, "cooldown": 2}
    )
    m = make_map(heights, ally=[(3, 3), (2, 3)], enemy=[(5, 3), (5, 5)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([copy])),
        spawn(Team.ALLY, (2, 3), no_reactions("hero_fighter")),
        spawn(Team.ENEMY, (5, 3), caster_template([bolt])),
        spawn(Team.ENEMY, (5, 5), no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[copy, bolt]), U1)


def enemy_casts_bolt(state: BattleState) -> BattleState:
    """U3 對 U2 施放 BOLT，然後回到 U1 的回合（同一輪）。"""
    result = resolve(give_turn(state, U3), UseSkill(unit_id=U3, skill_id=BOLT, target_id=U2))
    return give_turn(result.state, U1)


def pick_of(target: UnitId) -> UseSkill:
    return UseSkill(unit_id=U1, skill_id=BOLT, target_id=target)


def test_the_last_cast_is_recorded_and_survives_serialization() -> None:
    state = enemy_casts_bolt(copy_scene())
    assert state.casts == (LastCast(U3, BOLT, state.round),)
    assert state_from_json(state_to_json(state)).casts == state.casts


def test_copy_skill_casts_the_last_skill_for_free(always_hit: None) -> None:
    state = enemy_casts_bolt(copy_scene())
    mana = state.units[U1].mana
    result = resolve(state, UseSkill(unit_id=U1, skill_id=COPY, copy_cast=pick_of(U4)))
    (copied,) = of(result, SkillCopied)
    assert (copied.unit_id, copied.source_id, copied.skill_id) == (U1, U3, BOLT)
    (hit,) = of(result, DamageDealt)
    assert hit.target_id == U4 and hit.source_id == U1
    after = result.state.units[U1]
    assert after.mana == mana and BOLT not in after.cooldowns  # 不扣法力、不進冷卻
    assert after.ap == state.units[U1].ap - 1  # 只花複製技能自己的 AP
    assert result.state.casts[-1] == LastCast(U1, COPY, state.round)


def test_nothing_to_copy_means_the_skill_cannot_be_cast() -> None:
    state = copy_scene()
    assert copy_problem(state, state.units[U1]) == "本輪還沒有其他單位施放過技能，沒有技能可以複製"
    assert not [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == COPY]
    with pytest.raises(IllegalActionError, match="本輪還沒有其他單位施放過技能，沒有技能可以複製"):
        resolve(state, UseSkill(unit_id=U1, skill_id=COPY))
    again = enemy_casts_bolt(state)
    assert [a for a in legal_actions(again) if isinstance(a, UseSkill) and a.skill_id == COPY]


def test_only_the_skill_cast_this_round_can_be_copied() -> None:
    state = enemy_casts_bolt(copy_scene())
    state.round += 1
    assert copy_problem(state, state.units[U1]) == "本輪還沒有其他單位施放過技能，沒有技能可以複製"


def test_a_skill_cast_by_the_copier_itself_cannot_be_copied() -> None:
    state = copy_scene()
    state.casts = (LastCast(U1, BOLT, state.round),)
    assert "其他單位" in (copy_problem(state, state.units[U1]) or "")


def test_the_copier_own_casts_do_not_hide_the_last_cast_by_someone_else() -> None:
    state = enemy_casts_bolt(copy_scene())
    state.casts = (*state.casts, LastCast(U1, COPY, state.round))
    found = copy_source(state, state.units[U1])
    assert not isinstance(found, str) and found[0].id == BOLT


def test_the_original_caster_must_be_alive_and_visible() -> None:
    state = enemy_casts_bolt(copy_scene())
    state.units[U3].downed = True
    assert "不在場上" in (copy_problem(state, state.units[U1]) or "")
    walled = copy_scene(WALL_ROW3)
    walled.casts = (LastCast(U3, BOLT, walled.round),)  # 牆擋住了施放本身，所以直接記錄
    assert "看不到" in (copy_problem(walled, walled.units[U1]) or "")


@pytest.mark.parametrize(
    ("skill_id", "reason"),
    [
        ("skill_time_surge", "傳說"),
        ("skill_soul_bond", "改寫了規則"),
        ("skill_mirror_cast", "傳說"),
        ("skill_thunder_finisher", "層數"),
        ("skill_bear_trap", "不是一般的主動技能"),
        ("skill_riposte", "不是一般的主動技能"),
    ],
)
def test_some_skills_cannot_be_copied(skill_id: str, reason: str) -> None:
    state = copy_scene()
    skill = state.ruleset.skill_def(skill_id)
    assert reason in (uncopyable_reason(state, skill) or "")
    state.casts = (LastCast(U3, skill_id, state.round),)
    assert reason in (copy_problem(state, state.units[U1]) or "")


def test_a_plain_copy_skill_cannot_be_copied_either() -> None:
    state = copy_scene()
    assert "改寫了規則" in (uncopyable_reason(state, state.ruleset.skill_def(COPY)) or "")


def test_the_copy_needs_a_legal_target_and_the_right_skill(always_hit: None) -> None:
    state = enemy_casts_bolt(copy_scene())
    legal = {s.target_id for s, _ in copy_selections(state, state.units[U1])}
    assert legal == {U3, U4}  # 敵人（友方不能是目標）
    wrong = UseSkill(unit_id=U1, skill_id="skill_fire_bolt", target_id=U3)
    with pytest.raises(IllegalActionError, match="只能複製"):
        resolve(state, UseSkill(unit_id=U1, skill_id=COPY, copy_cast=wrong))
    ally = UseSkill(unit_id=U1, skill_id=BOLT, target_id=U2)
    with pytest.raises(IllegalActionError):
        resolve(state, UseSkill(unit_id=U1, skill_id=COPY, copy_cast=ally))
    far = state.clone()
    far.units[U4].pos = Pos(x=6, y=6)  # 射程 5：(3, 3) → (6, 6) 距離 6
    with pytest.raises(IllegalActionError, match="射程"):
        resolve(far, UseSkill(unit_id=U1, skill_id=COPY, copy_cast=pick_of(U4)))
    other = UseSkill(unit_id=U1, skill_id=BOLT, target_id=U3, copy_cast=pick_of(U4))
    state.units[U1].skills = (COPY, BOLT)
    with pytest.raises(IllegalActionError, match="copy_cast"):
        resolve(state, other)


def test_the_weapon_requirement_is_not_checked_when_copying() -> None:
    state = copy_scene()
    state.units[U3].pos = Pos(x=4, y=3)  # 緊鄰施放者
    state.casts = (LastCast(U3, "skill_shield_bash", state.round),)  # 需要近戰武器；U1 拿法器
    assert state.units[U1].weapon.weapon_class == "focus"
    assert state.ruleset.skill_def("skill_shield_bash").weapon_req == "melee"
    assert copy_problem(state, state.units[U1]) is None


def test_copying_still_needs_no_silence() -> None:
    state = enemy_casts_bolt(copy_scene())
    state.units[U1].statuses.append(StatusInstance("silenced", 2, U3))
    assert "沉默" in (copy_problem(state, state.units[U1]) or "")


def test_a_bare_copy_pauses_and_resumes_with_the_choice(always_hit: None) -> None:
    state = enemy_casts_bolt(copy_scene())
    paused = resolve(state, UseSkill(unit_id=U1, skill_id=COPY))
    assert paused.pending is not None
    assert (paused.pending.kind, paused.pending.unit_id) == ("copy_skill", U1)
    assert (paused.pending.skill_id, paused.pending.copy_skill_id) == (COPY, BOLT)
    assert not paused.events and paused.state.units[U1].ap == state.units[U1].ap  # 還沒付代價
    revived = state_from_json(state_to_json(paused.state))  # 暫停的狀態可以存讀
    assert revived.pending == paused.state.pending
    done = resume(revived, Decision(unit_id=U1, accept=True, copy_cast=pick_of(U4)))
    direct = resolve(state, UseSkill(unit_id=U1, skill_id=COPY, copy_cast=pick_of(U4)))
    assert done.pending is None and done.state.pending is None
    assert state_to_json(done.state) == state_to_json(direct.state)
    assert [e.model_dump() for e in done.events] == [e.model_dump() for e in direct.events]


def test_declining_the_copy_costs_nothing() -> None:
    state = enemy_casts_bolt(copy_scene())
    paused = resolve(state, UseSkill(unit_id=U1, skill_id=COPY))
    result = resume(paused.state, Decision(unit_id=U1, accept=False))
    assert result.pending is None and not result.events
    assert state_to_json(result.state) == state_to_json(state)


def test_a_bad_choice_keeps_the_pause() -> None:
    state = enemy_casts_bolt(copy_scene())
    paused = resolve(state, UseSkill(unit_id=U1, skill_id=COPY))
    with pytest.raises(IllegalActionError, match="必須指定"):
        resume(paused.state, Decision(unit_id=U1, accept=True))
    ally = UseSkill(unit_id=U1, skill_id=BOLT, target_id=U2)
    with pytest.raises(IllegalActionError):
        resume(paused.state, Decision(unit_id=U1, accept=True, copy_cast=ally))
    assert paused.state.pending is not None
    assert not legal_actions(paused.state)  # 暫停中沒有合法動作


def test_the_preview_of_a_bare_copy_does_not_pause() -> None:
    state = enemy_casts_bolt(copy_scene())
    shown = preview(state, UseSkill(unit_id=U1, skill_id=COPY))
    assert not [e for e in shown.min_events if isinstance(e, SkillCopied)]
    full = preview(state, UseSkill(unit_id=U1, skill_id=COPY, copy_cast=pick_of(U3)))
    assert any(isinstance(e, SkillCopied) for e in full.min_events)


def test_legal_actions_list_one_bare_copy_and_the_ai_gets_the_expanded_ones() -> None:
    state = enemy_casts_bolt(copy_scene())
    bare = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == COPY]
    assert len(bare) == 1 and bare[0].copy_cast is None
    actions, areas = legal_actions_with_areas(state, expand_copy=True)
    full = [a for a in actions if isinstance(a, UseSkill) and a.skill_id == COPY]
    assert sorted(a.copy_cast.target_id or "" for a in full if a.copy_cast) == [U3, U4]
    assert all(a.copy_cast is not None and id(a) in areas for a in full)


def test_the_ai_copies_a_skill_with_a_useful_target(always_hit: None) -> None:
    state = enemy_casts_bolt(copy_scene())
    pick = UtilityAI(library().ai_profiles)(state)
    assert isinstance(pick, UseSkill) and pick.skill_id == COPY
    assert pick.copy_cast is not None and pick.copy_cast.skill_id == BOLT
    assert resolve(state, pick).events  # 合法、可結算


def test_copy_skill_must_be_the_only_effect_and_self_shaped() -> None:
    with pytest.raises(ValidationError, match="形狀必須是 self"):
        make_skill(COPY, {"type": "single", "range": 3}, [{"type": "copy_skill"}])
    with pytest.raises(ValidationError, match="唯一的效果"):
        make_skill(
            COPY, {"type": "self"}, [{"type": "copy_skill"}, {"type": "heal", "dice": "1d4"}]
        )


def test_copy_source_names_the_skill_and_its_caster() -> None:
    state = enemy_casts_bolt(copy_scene())
    found = copy_source(state, state.units[U1])
    assert not isinstance(found, str) and found[0].id == BOLT and found[1].id == U3


# ---------------------------------------------------------------------------
# extra_reaction
# ---------------------------------------------------------------------------

BELL_EFFECT = {"type": "extra_reaction", "amount": 1, "affects": "allies"}


def bell_scene() -> BattleState:
    bell = make_skill(BELL, {"type": "single", "range": 4}, [BELL_EFFECT])
    m = make_map(FLAT7, ally=[(3, 3), (4, 4)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), caster_template([bell])),
        spawn(Team.ALLY, (4, 4), "hero_fighter", skills=None),
        spawn(Team.ENEMY, (4, 3), no_reactions()),
    ]
    return give_turn(make_state(m, spawns, skills=[bell]), U1)


def test_extra_reaction_raises_the_limit_until_the_next_round() -> None:
    state = bell_scene()
    core = state.ruleset.core
    assert reaction_limit(core, state.units[U2]) == core.reactions_per_round
    result = resolve(state, UseSkill(unit_id=U1, skill_id=BELL, target_id=U2))
    (granted,) = of(result, ReactionsGranted)
    assert (granted.unit_id, granted.source_id, granted.amount, granted.total) == (U2, U1, 1, 1)
    assert reaction_limit(core, result.state.units[U2]) == core.reactions_per_round + 1
    now = result.state
    while now.round == state.round:  # 把這一輪走完：額外次數到下一輪開始時歸零
        assert now.active_unit is not None
        now = resolve(now, EndTurn(unit_id=now.active_unit)).state
    assert now.units[U2].extra_reactions == 0
    assert reaction_limit(core, now.units[U2]) == core.reactions_per_round


def _reactions_in_two_attacks(state: BattleState) -> int:
    """敵人（U2）連續攻擊 U1 兩次，U1 觸發的反應次數。"""
    first = resolve(state, Attack(unit_id=U2, target_id=U1))
    second = resolve(first.state, Attack(unit_id=U2, target_id=U1))
    return sum(isinstance(e, ReactionTriggered) for e in [*first.events, *second.events])


def test_an_extra_reaction_allows_a_second_reaction_in_the_same_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch, d20=19)
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    spawns = [
        spawn(Team.ALLY, (3, 3), "hero_fighter", skills=None),
        spawn(Team.ENEMY, (4, 3), "bandit"),
    ]
    state = give_turn(make_state(m, spawns), U2)
    state.units[U2].ap = 4
    assert _reactions_in_two_attacks(state) == 1
    boosted = state.clone()
    boosted.units[U1].extra_reactions = 1
    assert _reactions_in_two_attacks(boosted) == 2


def test_extra_reaction_cannot_target_enemies() -> None:
    shape = {"type": "single", "range": 4}
    bad = make_skill(BELL, shape, [{**BELL_EFFECT, "affects": "enemies"}])
    assert any("affects" in p or "enemies" in p for p in _problems(bad))


def test_the_ai_gives_extra_reactions_only_to_units_that_react() -> None:
    lib = library()
    policy = UtilityAI(lib.ai_profiles)
    skill = lib.skills["skill_vigil_call"]
    reacting = policy(_support_state(skill, lib.unit("hero_fighter")))
    assert isinstance(reacting, UseSkill) and reacting.skill_id == "skill_vigil_call"
    assert reacting.target_id == U2
    quiet = policy(_support_state(skill, no_reactions("hero_fighter")))
    assert not (isinstance(quiet, UseSkill) and quiet.skill_id == "skill_vigil_call")


# ---------------------------------------------------------------------------
# 示範戰鬥：三個新技能都會被 AI 用到，而且紀錄可以重播
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("build", "map_id", "seed", "event"),
    [
        ("build_support", "oil_depot", 4, SkillCopied),
        ("build_guardian", "open_plain", 2, DamageRedirected),
        ("build_guardian", "open_plain", 2, ReactionsGranted),
    ],
)
def test_demo_battles_use_the_new_primitives_and_replay(
    build: str, map_id: str, seed: int, event: type
) -> None:
    lib, allies = build_allies(library(), [build])
    _, enemies = default_lineup(lib, map_id)
    setup = build_setup(lib, map_id, allies, enemies, max_rounds=30)
    run = run_battle(setup, seed, UtilityAI(lib.ai_profiles))
    assert any(isinstance(e, event) for e in run.events)
    again = replay(setup, seed, run.actions)
    assert state_to_json(again.state) == state_to_json(run.state)
    assert [e.model_dump() for e in again.events] == [e.model_dump() for e in run.events]


def test_all_six_rule_rewrite_primitives_have_equipped_hand_written_skills() -> None:
    lib = library()
    rewrites = {p.id for p in lib.ruleset.primitives.primitives if p.category == "rule_rewrite"}
    assert rewrites == {
        "grant_ap",
        "reset_cooldown",
        "cheat_death",
        "redirect_damage",
        "copy_skill",
        "extra_reaction",
    }
    equipped = {s for b in lib.builds.builds for s in b.hero.skills}
    for primitive in sorted(rewrites):
        skills = [s for s in lib.skills.values() if any(e.type == primitive for e in s.effects)]
        assert skills and all(s.id in equipped for s in skills), primitive
