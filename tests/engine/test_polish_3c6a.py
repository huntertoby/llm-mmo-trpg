"""Phase 3C-6a：累積的小修正（``Phase3C計畫.md`` 8.2A）的引擎、紀錄文字、CLI 測試。

穿透失手的紀錄與穿透折扣的顯示、貼牆推擊的紀錄、奪取增益的順序、`legal_actions` 沒有未選取目標的
單體動作、AI 對會超載技能的低血量規則、`enemies_adjacent_target` 示範技能、技能卡片的時機一行、
`sim maps` 的召喚次數、被揭露的敵方陷阱標記、環境預告的炸彈不重複。
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.skill_helpers import U1, U2, cast, of
from tests.engine.test_combo_resources import _steal_state
from tests.engine.test_facing_backstab import duel
from tests.engine.test_pierce import always, arena, shoot
from trpg.cli.render import render_battle_grid, render_legend, render_telegraph
from trpg.content.library import load_library
from trpg.engine import BattleSetupError, Shove, UseSkill, legal_actions, resolve
from trpg.engine.ai.gamble import overloads
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.engine.environment import Telegraph, TelegraphBomb, TelegraphChange
from trpg.engine.events import (
    Collided,
    DamageDealt,
    MoveBlocked,
    ShotPierced,
    StatusApplied,
    StatusRemoved,
)
from trpg.engine.state import TrapState
from trpg.narrative.events import describe_event
from trpg.narrative.skills import skill_card
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute, Pos, Team

# ---------------------------------------------------------------------------
# 穿透：失手與折扣顯示
# ---------------------------------------------------------------------------


def test_a_missed_pierced_shot_does_not_claim_the_back_discount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 1 if sides == 20 else min(4, sides))
    state = arena(objects=[(2, 3, "crate")])
    result = resolve(state, shoot())
    (event,) = of(result, ShotPierced)
    assert event.behind == ()  # 失手：沒有人受傷，所以後方沒有人「只受 70%」
    text = describe_event(event, result.state)
    assert text is not None and "穿過了" in text and "只受" not in text


def test_a_hit_pierced_shot_still_reports_the_back_discount_separately_from_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(objects=[(2, 3, "crate")])
    result = resolve(state, shoot())
    (event,) = of(result, ShotPierced)
    assert event.behind == (U2,)
    assert "只受 70% 傷害" in (describe_event(event, result.state) or "")
    (dealt,) = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert dealt.pierce_permille == 700 and dealt.multiplier_permille == 980  # 穿透箭 ×1.4 再 ×0.7
    text = describe_event(dealt, result.state) or ""
    assert (
        "加成 ×1.4" in text
        and "格擋/加成" not in text
        and "穿透後方 ×0.7" in text
        and "×0.98" not in text
    )


def test_a_pierce_discount_alone_is_not_shown_as_a_block(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(arena(objects=[(2, 3, "crate")]), shoot())
    (dealt,) = [d for d in of(result, DamageDealt) if d.target_id == U2]
    only = dealt.model_copy(update={"multiplier_permille": 700})
    text = describe_event(only, result.state) or ""
    assert "穿透後方 ×0.7" in text and "格擋/加成" not in text


# ---------------------------------------------------------------------------
# 貼牆推擊：以「撞上牆壁」為主
# ---------------------------------------------------------------------------


def test_a_shove_into_a_pillar_logs_the_collision_not_a_blocked_move() -> None:
    m = make_map(
        "\n".join(["0000000"] * 7), ally=[(2, 3)], enemy=[(3, 3)], objects=[(4, 3, "crate")]
    )
    hero = caster_template([], base="hero_fighter", weapon="one_handed_sword")
    state = give_turn(
        make_state(m, [spawn(Team.ALLY, (2, 3), hero), spawn(Team.ENEMY, (3, 3), no_reactions())]),
        U1,
    )
    result = resolve(with_rolls(state, [(20, 20)]), Shove(unit_id=U1, target_id=U2))
    blocked = of(result, MoveBlocked)
    assert blocked and all(e.forced for e in blocked)
    assert all(describe_event(e, result.state) is None for e in blocked)
    (collided,) = of(result, Collided)
    assert "撞上了" in (describe_event(collided, result.state) or "")


# ---------------------------------------------------------------------------
# 奪取增益：先被奪走、再獲得
# ---------------------------------------------------------------------------


def test_steal_buff_logs_the_loss_before_the_gain() -> None:
    from trpg.engine.state import StatusInstance  # noqa: PLC0415

    result = cast(_steal_state([StatusInstance("guarded", 3)]), target_id=U2)
    kinds = [type(e) for e in result.events if isinstance(e, StatusRemoved | StatusApplied)]
    assert kinds == [StatusRemoved, StatusApplied]
    lines = [describe_event(e, result.state) for e in result.events]
    texts = [t for t in lines if t and ("被奪走" in t or "獲得狀態" in t)]
    assert "被奪走" in texts[0] and "獲得狀態" in texts[1]


# ---------------------------------------------------------------------------
# legal_actions：單體技一律帶目標
# ---------------------------------------------------------------------------


def test_unit_targeted_skills_never_list_a_selection_less_action() -> None:
    lib = load_library()
    checked = 0
    for sid, skill in sorted(lib.skills.items()):
        if skill.kind != "active" or lib.ruleset.shape_def(skill.shape.type).targeting != "unit":
            continue
        for xy, weapon, base in (
            ((2, 3), "one_handed_sword", "hero_fighter"),
            ((1, 3), "bow", "hero_archer"),
            ((1, 3), "staff", "hero_mage"),
        ):
            try:
                state = duel(xy, (3, 3), skills=(sid,), weapon=weapon, base=base)
            except (KeyError, BattleSetupError):
                continue
            bare = [
                a
                for a in legal_actions(state)
                if isinstance(a, UseSkill)
                and a.skill_id == sid
                and a.target_id is None
                and a.target_object_id is None
            ]
            assert bare == [], sid
            checked += 1
    assert checked > 30


def test_a_selection_less_cast_of_a_single_skill_is_rejected() -> None:
    state = duel((2, 3), (3, 3), skills=("skill_bone_crusher",), weapon="one_handed_sword")
    with pytest.raises(IllegalActionError):
        resolve(state, UseSkill(unit_id=U1, skill_id="skill_bone_crusher"))


# ---------------------------------------------------------------------------
# AI：會超載的技能在低血量時也被壓低
# ---------------------------------------------------------------------------

OVERCURRENT = "skill_overcurrent"


def _striker(stacks: int, hp_percent: int):  # type: ignore[no-untyped-def]
    state = duel((1, 3), (3, 3), skills=(OVERCURRENT,), weapon="lightning_staff", base="hero_mage")
    unit = state.units[U1]
    if stacks:
        unit.stacks["overload_surge"] = stacks
    unit.hp = unit.max_hp * hp_percent // 100
    return state


def test_overloads_is_true_only_when_the_cast_reaches_the_threshold() -> None:
    skill = library().skills[OVERCURRENT]
    assert not overloads(_striker(0, 100), _striker(0, 100).units[U1], skill)
    assert not overloads(_striker(3, 100), _striker(3, 100).units[U1], skill)
    full = _striker(4, 100)  # 再 +1 層就是第 5 層：反噬
    assert overloads(full, full.units[U1], skill)


def test_a_low_hp_caster_avoids_the_cast_that_would_overload_it() -> None:
    action = UseSkill(unit_id=U1, skill_id=OVERCURRENT, target_id=U2)
    ai = UtilityAI(library().ai_profiles)
    loaded = _striker(4, 100)
    profile = ai.profile_for(loaded.units[U1])
    healthy = score_action(loaded, action, profile).score
    assert healthy > 0
    hurt = score_action(_striker(4, 25), action, profile).score
    assert 0 < hurt < healthy * Fraction(1, 5)
    safe = score_action(_striker(0, 25), action, profile).score  # 沒有堆疊：不會超載，不受影響
    assert safe == score_action(_striker(0, 100), action, profile).score


# ---------------------------------------------------------------------------
# enemies_adjacent_target 示範技能
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_the_cluster_bolt_scales_with_the_enemies_around_the_target() -> None:
    lib = load_library()
    skill = lib.skills["skill_cluster_bolt"]
    assert skill.effects[0].scaling is not None
    assert skill.effects[0].scaling.by == "enemies_adjacent_target"
    assert "skill_cluster_bolt" in {s for b in lib.builds.builds for s in b.hero.skills}
    lone = duel(
        (1, 3), (3, 3), skills=("skill_cluster_bolt",), weapon="lightning_staff", base="hero_mage"
    )
    crowd = duel(
        (1, 3),
        (3, 3),
        skills=("skill_cluster_bolt",),
        weapon="lightning_staff",
        base="hero_mage",
        extra=((Team.ENEMY, (4, 3)), (Team.ENEMY, (3, 2))),
    )
    action = UseSkill(unit_id=U1, skill_id="skill_cluster_bolt", target_id=U2)
    rolls = [(20, 15)] + [(6, 3)] * 6
    one = [
        e for e in of(resolve(with_rolls(lone, rolls), action), DamageDealt) if e.target_id == U2
    ]
    many = [
        e for e in of(resolve(with_rolls(crowd, rolls), action), DamageDealt) if e.target_id == U2
    ]
    assert one and many and many[0].amount > one[0].amount
    assert many[0].multiplier_permille == 1300 and one[0].multiplier_permille == 1000


# ---------------------------------------------------------------------------
# 技能卡片：反應時機與觸發時機
# ---------------------------------------------------------------------------


def test_reaction_and_passive_cards_show_their_timing() -> None:
    lib = library()
    counter = skill_card(lib, lib.skills["skill_counterspell"])
    assert counter.timing == "反應時機：被法術命中時（傷害結算之前）"
    thorn = skill_card(lib, lib.skills["skill_thorn_skin"])
    assert thorn.timing is not None and thorn.timing.startswith("觸發時機：")
    plain = skill_card(lib, lib.skills["skill_pincer_strike"])
    assert plain.timing is None
    from trpg.content.skills import SKILL_REACTION_EVENTS  # noqa: PLC0415
    from trpg.narrative.skills import REACTION_TIMING_TEXT  # noqa: PLC0415

    assert set(REACTION_TIMING_TEXT) == set(SKILL_REACTION_EVENTS)


# ---------------------------------------------------------------------------
# sim maps：召喚物次數
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_sim_maps_reports_the_summon_count(capsys: pytest.CaptureFixture[str]) -> None:
    from trpg.cli.main import main  # noqa: PLC0415

    argv = ["sim", "maps", "--maps", "swamp", "--seeds", "3", "--jobs", "1"]
    assert main([*argv, "--ally-build", "build_summoner"]) == 0
    assert "召喚物（整批合計）：我方召喚" in capsys.readouterr().out
    assert main(argv) == 0
    assert "召喚物（整批合計）" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# CLI：被揭露的敵方陷阱、環境預告的炸彈
# ---------------------------------------------------------------------------


def _trap(owner: str, team: Team, x: int, revealed: tuple[Team, ...] = ()) -> TrapState:
    return TrapState(
        owner,  # type: ignore[arg-type]
        team,
        Pos(x=x, y=3),
        "skill_bear_trap",
        3,
        tuple((a, 10) for a in Attribute),
        revealed,
    )


def test_a_revealed_enemy_trap_uses_its_own_glyph_in_the_grid_and_legend() -> None:
    state = duel((1, 3), (5, 5))
    state.traps = [_trap(U1, Team.ALLY, 2), _trap(U2, Team.ENEMY, 4)]
    row = render_battle_grid(state).splitlines()[1 + 3]
    assert "^" in row and "x" not in row  # 敵方陷阱還沒被揭露：看不到
    state.traps = [_trap(U1, Team.ALLY, 2), _trap(U2, Team.ENEMY, 4, (Team.ALLY,))]
    row = render_battle_grid(state).splitlines()[1 + 3]
    assert "^" in row and "x" in row
    legend = render_legend(state)
    assert "^ 我方陷阱" in legend and "x 被揭露的敵方陷阱" in legend


def _bomb_forecast(*, explodes: bool) -> Telegraph:
    tiles = (Pos(x=3, y=3), Pos(x=4, y=3))
    changes = (
        (
            TelegraphChange(
                kind="bomb_exploded", pos=Pos(x=3, y=3), unit_id=U2, amount=1, tiles=tiles
            ),
        )
        if explodes
        else ()
    )
    bomb = TelegraphBomb(
        unit_id=U2,
        pos=Pos(x=3, y=3),
        remaining=1 if explodes else 2,
        radius=1,
        tiles=tiles,
        explodes=explodes,
    )
    return Telegraph(round=1, events=[], changes=changes, burning=(), upcoming=(), bombs=(bomb,))


def test_the_telegraph_lists_a_bomb_once() -> None:
    state = duel((1, 3), (3, 3))
    soon = render_telegraph(state, _bomb_forecast(explodes=True))
    assert soon.count("定時炸彈") == 1  # 下一次就爆炸：只列「將在…爆炸」那一行
    later = render_telegraph(state, _bomb_forecast(explodes=False))
    assert later.count("定時炸彈") == 1 and "還要 2 次環境回合爆炸" in later
