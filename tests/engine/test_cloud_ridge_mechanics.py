"""主題合併（R2）。

原 ``test_mechanics_5am1.py``：

Phase 5A-M1：引擎機制①（``docs/phases/Phase5計畫.md`` 第 14 節）。

開場隱蔽（範本 ``opening_statuses``、詞綴 ``add_opening_statuses``）、死亡時留下表面（狀態
``on_death_surface``）、同門相護（內建反應 ``kin_ward``）、蓄力強招「九轉回天」與 AI 的估值。

原 ``test_mechanics_5am2.py``：

Phase 5A-M2：引擎機制②（``docs/phases/Phase5計畫.md`` 第 16 節）。

陣法範圍加成（狀態 ``formation``，劍陣弟子「劍陣」）、把傷害分給同門（狀態 ``share_damage``，詞綴
「連心的」）、戰鬥紀錄與單位卡特性欄的中文、AI 的估值。

原 ``test_mechanics_5am2b.py``：

Phase 5A-M2b：陣眼石靈「護陣」（狀態 ``ward``，``docs/design/18-雲嶺內容.md`` 18.2）。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn, template
from trpg.content.battle import OpeningStatus, StatusDef, UnitTemplate
from trpg.content.skills import CHARGING
from trpg.content.world_enemies import apply_affix
from trpg.engine import BattleState, UseSkill, preview, resolve
from trpg.engine.actions import Attack, EndTurn
from trpg.engine.ai.priority import formation_break, is_kin_warden, priority_points, share_discount
from trpg.engine.ai.utility import UtilityAI, position_value
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, DamageEffect
from trpg.engine.events import (
    DamageDealt,
    DamageRedirected,
    EventBase,
    FollowupCancelled,
    FollowupCharged,
    Healed,
    ReactionTriggered,
    ShieldGained,
    SurfaceChanged,
    UnitDowned,
)
from trpg.engine.formation import formation_permille, ward_permille
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.narrative.unit_traits import unit_trait_lines
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Surface, Team, UnitId

# --- 原 test_mechanics_5am1.py ---

FLAT = "\n".join(["0000000"] * 7)
U1, U2, U3, U4 = (UnitId(f"unit_000{i}") for i in range(1, 5))
REVIVAL = "skill_nine_turns_revival"


def _state(
    allies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    enemies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    seed: int = 0,
) -> BattleState:
    m = make_map(FLAT, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    spawns = [spawn(Team.ALLY, p, t) for p, t in allies]
    spawns += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    return make_state(m, spawns, seed=seed)


def _hero() -> UnitTemplate:
    return template("hero_fighter", reactions=[], skills=[])


def _always_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 18 if sides == 20 else min(2, sides))


# ---------------------------------------------------------------------------
# 開場隱蔽
# ---------------------------------------------------------------------------


def test_template_opening_concealment_lasts_one_turn() -> None:
    veiled = template("bandit", opening_statuses=[{"status": "concealed", "duration": 1}])
    state = _state([((0, 0), _hero())], [((6, 6), veiled)])
    status = state.units[U2].get_status("concealed")
    assert status is not None and status.remaining == 1
    assert not state.units[U1].has_status("concealed")
    for _ in range(20):  # 敵人自己的第 1 回合結束後就沒有了
        if state.round > 1:
            break
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
    assert not state.units[U2].has_status("concealed")


def test_mist_veiled_affix_adds_opening_concealment() -> None:
    lib = library()
    affix = lib.world_enemies.affix_by_id()["mist_veiled"]  # type: ignore[union-attr]
    veiled = apply_affix(lib.unit("mist_wolf"), affix, lib.ruleset.reactions.default_rules)
    assert veiled.opening_statuses == (OpeningStatus(status="concealed", duration=1),)
    assert veiled.skills == (*lib.unit("mist_wolf").skills, "skill_mist_shift")  # #149 詞綴帶招
    state = _state([((0, 0), _hero())], [((6, 6), veiled)])
    assert state.units[U2].has_status("concealed")


def test_opening_status_schema_limits() -> None:
    with pytest.raises(ValidationError):
        OpeningStatus(status="concealed", duration=3)


# ---------------------------------------------------------------------------
# 死亡時留下表面
# ---------------------------------------------------------------------------


def _down(state: BattleState, uid: UnitId) -> tuple[BattleState, list[str]]:
    """把 ``uid`` 打倒，回傳狀態與事件文字。"""
    s = state.clone()
    ctx = Ctx(s)
    execute(ctx, [DamageEffect(target_id=uid, source_id=U1, flat=999)])
    texts = [
        text
        for e in ctx.events
        if isinstance(e, SurfaceChanged) and (text := describe_event(e, s)) is not None
    ]
    return s, texts


def test_shard_golem_leaves_water_when_downed() -> None:
    golem = library().unit("shard_golem")
    state = _state([((0, 0), _hero())], [((3, 3), golem)])
    assert state.units[U2].has_status("shard_burst")
    after, texts = _down(state, U2)
    assert not after.units[U2].alive
    wet = {(x, y) for x in range(7) for y in range(7) if after.tile(x, y).surface is Surface.WATER}
    assert wet == {(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)}  # 半徑 1（曼哈頓）
    assert len(texts) == 5 and all("倒下時留下的" in text for text in texts)


def test_no_death_surface_without_status() -> None:
    state = _state([((0, 0), _hero())], [((3, 3), template("bandit"))])
    after, texts = _down(state, U2)
    assert not texts
    assert after.tile(3, 3).surface is Surface.NONE


def test_death_surface_status_rules() -> None:
    lib = library()
    burst = lib.ruleset.status_def("shard_burst")
    assert burst.polarity == "neutral" and burst.expires == "never"
    with pytest.raises(ValidationError):
        StatusDef.model_validate(
            {
                "id": "bad",
                "name_zh": "壞",
                "description_zh": "壞",
                "polarity": "buff",
                "beneficial": True,
                "expires": "never",
                "on_death_surface": {"surface": "fire"},
            }
        )


# ---------------------------------------------------------------------------
# 同門相護
# ---------------------------------------------------------------------------


def _sect(base: str = "sect_swordsman", **kw: object) -> UnitTemplate:
    return template(base, **kw)


def _kin_state(
    healer_at: tuple[int, int] = (3, 1), *, healer_tags: Sequence[str] = ("humanoid", "sect")
) -> BattleState:
    swordsman = _sect(reactions=[], max_hp=60)
    healer = template("sect_acolyte", tags=list(healer_tags))
    state = _state([((3, 4), _hero())], [((3, 3), swordsman), (healer_at, healer)])
    return give_turn(state, U1)


def test_kin_ward_shields_kin_within_two_tiles(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    state = _kin_state()
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    reacted = [e for e in result.events if isinstance(e, ReactionTriggered)]
    assert [(e.unit_id, e.reaction) for e in reacted] == [(U3, "kin_ward")]
    shields = [e for e in result.events if isinstance(e, ShieldGained)]
    assert shields and shields[0].unit_id == U2
    assert result.state.units[U3].reactions_used == 1
    texts = [describe_event(e, result.state) for e in reacted]
    assert "同門相護" in (texts[0] or "")


def test_kin_ward_once_per_round(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    state = _kin_state()
    first = resolve(state, Attack(unit_id=U1, target_id=U2)).state
    second = resolve(give_turn(first, U1), Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in second.events)


def test_kin_ward_out_of_range_or_not_kin(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    far = _kin_state(healer_at=(3, 0))  # 距離 3
    result = resolve(far, Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in result.events)
    stranger = _kin_state(healer_tags=("humanoid",))
    result = resolve(stranger, Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in result.events)


def test_kin_ward_blocked_by_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    state = _kin_state()
    state.units[U3].statuses.append(StatusInstance("silenced", remaining=1, source_id=U1))
    result = resolve(state, Attack(unit_id=U1, target_id=U2))
    assert not any(isinstance(e, ReactionTriggered) for e in result.events)


def test_kin_ward_triggers_on_skill_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    _always_hit(monkeypatch)
    hero = template("hero_fighter", reactions=[], skills=["skill_first_strike"], max_mana=99)
    swordsman = _sect(reactions=[], max_hp=60)
    healer = library().unit("sect_acolyte")
    state = give_turn(_state([((3, 4), hero)], [((3, 3), swordsman), ((3, 1), healer)]), U1)
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_first_strike", target_id=U2))
    assert any(isinstance(e, ReactionTriggered) and e.unit_id == U3 for e in result.events)


def test_cloud_ridge_kin_wardens() -> None:
    lib = library()
    state = _state(
        [((0, 0), _hero())],
        [
            ((6, 6), lib.unit("sect_acolyte")),
            ((5, 6), lib.unit("sect_alchemist")),
            ((4, 6), lib.unit("sect_steward")),
            ((3, 6), lib.unit("sect_swordsman")),
        ],
    )
    wardens = [is_kin_warden(state, state.units[u]) for u in (U2, U3, U4)]
    assert wardens == [True, True, True]
    assert not is_kin_warden(state, state.units[UnitId("unit_0005")])
    assert "skill_stand_firm" not in lib.unit("sect_swordsman").skills


# ---------------------------------------------------------------------------
# 蓄力強招「九轉回天」
# ---------------------------------------------------------------------------


def _revival_state() -> BattleState:
    steward = library().unit("sect_steward")
    swordsman = _sect(reactions=[], max_hp=60)
    state = _state([((0, 6), _hero())], [((3, 3), steward), ((3, 2), swordsman)])
    state = give_turn(state, U2)
    state.units[U2].hp = state.units[U2].max_hp - 20
    state.units[U3].hp = 10
    return state


def test_revival_charges_then_heals_next_turn() -> None:
    state = _revival_state()
    result = resolve(state, UseSkill(unit_id=U2, skill_id=REVIVAL))
    charged = [e for e in result.events if isinstance(e, FollowupCharged)]
    assert charged and charged[0].name_zh == "九轉回天"
    assert result.state.units[U2].has_status(CHARGING)
    assert result.state.units[U2].ap == 0  # 整回合（3 AP）
    s = result.state
    healed: list[Healed] = []
    for _ in range(30):
        assert s.active_unit is not None
        step = resolve(s, EndTurn(unit_id=s.active_unit))
        healed += [e for e in step.events if isinstance(e, Healed) and e.source_id == U2]
        s = step.state
        if not s.units[U2].has_status(CHARGING):
            break
    assert {e.target_id for e in healed} == {U2, U3}  # 3×3 內的友方；主角（敵方）不受治療


def test_revival_cancelled_by_stun() -> None:
    state = resolve(_revival_state(), UseSkill(unit_id=U2, skill_id=REVIVAL)).state
    s = state.clone()
    ctx = Ctx(s)
    execute(ctx, [ApplyStatusEffect(target_id=U2, status_id="stun", source_id=U1, duration=1)])
    assert any(isinstance(e, FollowupCancelled) for e in ctx.events)
    assert not s.units[U2].has_status(CHARGING)


def test_ai_casts_revival_when_kin_hurt() -> None:
    state = _revival_state()
    state.units[U2].cooldowns = {}
    action = UtilityAI(library().ai_profiles)(state)
    assert isinstance(action, UseSkill)
    assert action.skill_id in {REVIVAL, "skill_sanctuary"}


def test_ai_values_interrupting_charge_and_kin_wardens() -> None:
    lib = library()
    state = resolve(_revival_state(), UseSkill(unit_id=U2, skill_id=REVIVAL)).state
    state = give_turn(state, U1)
    hero = state.units[U1]
    hero.pos = hero.pos.model_copy(update={"x": 3, "y": 4})
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    if not any(isinstance(e, UnitDowned) for e in p.max_events):  # 打不倒：不加分
        assert priority_points(state, hero, p.min_events, p.max_events, Fraction(1), rules) == 0
    state.units[U2].hp = 1
    state.units[U2].statuses = [s for s in state.units[U2].statuses if s.status_id != "shielded"]
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    points = priority_points(state, hero, p.min_events, p.max_events, Fraction(1), rules)
    assert points == rules.priority_kill_points + rules.interrupt_points
    # 暈眩正在蓄力的敵人也算打斷
    stun = ApplyStatusEffect(target_id=U2, status_id="stun", source_id=U1, duration=1)
    s = state.clone()
    ctx = Ctx(s)
    execute(ctx, [stun])
    controlled = priority_points(state, hero, tuple(ctx.events), (), Fraction(1), rules)
    assert controlled == rules.interrupt_points


# --- 原 test_mechanics_5am2.py ---

FLAT_5AM2 = "\n".join(["0000000"] * 7)
U1_5AM2, U2_5AM2, U3_5AM2, U4_5AM2, U5 = (UnitId(f"unit_000{i}") for i in range(1, 6))


def _5am2_state(
    allies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    enemies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    seed: int = 0,
) -> BattleState:
    m = make_map(FLAT_5AM2, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    spawns = [spawn(Team.ALLY, p, t) for p, t in allies]
    spawns += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    return make_state(m, spawns, seed=seed)


def _5am2_hero(**overrides: object) -> UnitTemplate:
    return template("hero_fighter", reactions=[], skills=[], **overrides)


def _hit(state: BattleState, target: UnitId, source: UnitId, flat: int = 10) -> list[EventBase]:
    """``source`` 對 ``target`` 造成 ``flat`` 點攻擊傷害（就地修改 ``state``），回傳事件。"""
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=target, source_id=source, flat=flat, cause="attack")])
    return list(ctx.events)


def _dealt(events: Sequence[EventBase], target: UnitId) -> DamageDealt:
    return next(e for e in events if isinstance(e, DamageDealt) and e.target_id == target)


# ---------------------------------------------------------------------------
# 陣法範圍加成
# ---------------------------------------------------------------------------


def _disciple() -> UnitTemplate:
    return library().unit("sect_array_disciple")


@pytest.mark.parametrize(
    ("others", "expected"),
    [
        ([], 800),  # 落單
        ([(3, 3)], 1200),
        ([(3, 3), (2, 4)], 1400),
        ([(3, 3), (2, 4), (4, 4)], 1400),  # 最多算 2 名
    ],
)
def test_formation_permille_by_kin_count(others: list[tuple[int, int]], expected: int) -> None:
    enemies = [((3, 5), _disciple())] + [(p, _disciple()) for p in others]
    state = _5am2_state([((0, 0), _5am2_hero())], enemies)
    holder = state.units[U2_5AM2]
    assert holder.has_status("sword_formation")
    assert formation_permille(state, holder) == expected


def test_formation_ignores_far_foreign_and_downed_units() -> None:
    plain = template("bandit")  # 沒有 sword_array 標籤
    state = _5am2_state(
        [((3, 4), _5am2_hero(tags=["hero", "sword_array"]))],  # 敵方帶標籤也不算
        [((3, 6), _disciple()), ((3, 2), _disciple()), ((4, 6), plain)],  # 第二名相隔 4 格
    )
    assert formation_permille(state, state.units[U2_5AM2]) == 800
    state.units[U3_5AM2].pos = Pos(x=3, y=3)  # 3 格
    assert formation_permille(state, state.units[U2_5AM2]) == 1200
    state.units[U3_5AM2].downed = True
    assert formation_permille(state, state.units[U2_5AM2]) == 800


def test_formation_scales_attack_damage_and_log() -> None:
    state = _5am2_state(
        [((3, 0), _5am2_hero(max_hp=200))], [((3, 5), _disciple()), ((3, 3), _disciple())]
    )
    events = _hit(state, U1_5AM2, U2_5AM2, flat=10)
    hit = _dealt(events, U1_5AM2)
    assert hit.formation_permille == 1200 and hit.amount == 12
    assert "陣法 ×1.2" in (describe_event(hit, state) or "")
    # 不是攻擊（例如狀態傷害）不加
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=U1_5AM2, source_id=U2_5AM2, flat=10, cause="effect")])
    assert _dealt(ctx.events, U1_5AM2).amount == 10


def test_formation_alone_is_weaker() -> None:
    state = _5am2_state([((3, 0), _5am2_hero(max_hp=200))], [((3, 5), _disciple())])
    hit = _dealt(_hit(state, U1_5AM2, U2_5AM2, flat=10), U1_5AM2)
    assert hit.formation_permille == 800 and hit.amount == 8


def test_formation_schema_limits() -> None:
    base = {
        "id": "x_formation",
        "name_zh": "測",
        "description_zh": "測",
        "polarity": "neutral",
        "expires": "never",
    }
    spec = {"kin_tag": "sect", "per_ally_permille": 100, "max_allies": 2}
    StatusDef.model_validate({**base, "formation": spec})
    with pytest.raises(ValidationError):
        StatusDef.model_validate({**base, "formation": {**spec, "range": 6}})
    with pytest.raises(ValidationError):  # 只能用在中性、不倒數的狀態
        StatusDef.model_validate(
            {**base, "polarity": "buff", "beneficial": True, "formation": spec}
        )
    with pytest.raises(ValidationError):
        StatusDef.model_validate({**base, "share_damage": {"permille": 950}})


# ---------------------------------------------------------------------------
# 把傷害分給同門
# ---------------------------------------------------------------------------


def _linked(**overrides: object) -> UnitTemplate:
    return template(
        "bandit", opening_statuses=[OpeningStatus(status="heart_link")], max_hp=60, **overrides
    )


def test_share_damage_splits_to_adjacent_kin() -> None:
    state = _5am2_state(
        [((0, 0), _5am2_hero())],
        [((3, 3), _linked()), ((3, 2), template("bandit")), ((2, 3), template("bandit"))],
    )
    before = {u: state.units[u].hp for u in (U2_5AM2, U3_5AM2, U4_5AM2)}
    events = _hit(state, U2_5AM2, U1_5AM2, flat=21)  # 21 × 30% ＝ 6（捨去），平分 3＋3
    hit = _dealt(events, U2_5AM2)
    assert hit.shared == 6 and before[U2_5AM2] - state.units[U2_5AM2].hp == 15
    moved = [(e.to_id, e.amount) for e in events if isinstance(e, DamageRedirected)]
    assert moved == [(U3_5AM2, 3), (U4_5AM2, 3)]
    assert before[U3_5AM2] - state.units[U3_5AM2].hp == 3
    texts = [describe_event(e, state) or "" for e in events]
    assert any("6 點分給同門" in t for t in texts)
    assert any("分擔了" in t and "連心" in t for t in texts)


def test_share_damage_remainder_goes_to_lower_id() -> None:
    state = _5am2_state(
        [((0, 0), _5am2_hero())],
        [((3, 3), _linked()), ((3, 2), template("bandit")), ((2, 3), template("bandit"))],
    )
    events = _hit(state, U2_5AM2, U1_5AM2, flat=17)  # 17 × 30% ＝ 5 → 3＋2
    assert [(e.to_id, e.amount) for e in events if isinstance(e, DamageRedirected)] == [
        (U3_5AM2, 3),
        (U4_5AM2, 2),
    ]


def test_share_damage_needs_adjacent_ally() -> None:
    state = _5am2_state(
        [((3, 4), _5am2_hero())], [((3, 3), _linked()), ((3, 1), template("bandit"))]
    )
    hp = state.units[U2_5AM2].hp
    events = _hit(state, U2_5AM2, U1_5AM2, flat=10)
    assert _dealt(events, U2_5AM2).shared == 0 and hp - state.units[U2_5AM2].hp == 10
    assert not any(isinstance(e, DamageRedirected) for e in events)


def test_share_damage_after_shield_and_can_down_kin() -> None:
    state = _5am2_state(
        [((0, 0), _5am2_hero())], [((3, 3), _linked()), ((3, 2), template("bandit"))]
    )
    state.units[U2_5AM2].statuses.append(StatusInstance("shielded", remaining=2, amount=5))
    state.units[U3_5AM2].hp = 2
    events = _hit(state, U2_5AM2, U1_5AM2, flat=25)  # 護盾吸收 5，剩 20 × 30% ＝ 6
    hit = _dealt(events, U2_5AM2)
    assert hit.absorbed == 5 and hit.shared == 6
    assert any(isinstance(e, UnitDowned) and e.unit_id == U3_5AM2 for e in events)


def test_share_damage_skips_falls() -> None:
    state = _5am2_state(
        [((0, 0), _5am2_hero())], [((3, 3), _linked()), ((3, 2), template("bandit"))]
    )
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=U2_5AM2, source_id=None, flat=10, cause="fall")])
    assert _dealt(ctx.events, U2_5AM2).shared == 0


def test_heart_linked_affix_uses_share_status() -> None:
    lib = library()
    affix = lib.world_enemies.affix_by_id()["heart_linked"]  # type: ignore[union-attr]
    wolf = apply_affix(lib.unit("mist_wolf"), affix, lib.ruleset.reactions.default_rules)
    assert wolf.opening_statuses == (OpeningStatus(status="heart_link"),)
    assert "skill_soul_bond" not in wolf.skills
    lines = unit_trait_lines(lib, "mist_wolf_heart_linked")
    assert any(line.startswith("分傷「連心」") for line in lines)


def test_sword_array_disciple_traits_and_no_stopgap() -> None:
    lib = library()
    disciple = lib.unit("sect_array_disciple")
    assert "skill_shoulder_strike" not in disciple.skills
    assert "sword_array" in disciple.tags
    lines = unit_trait_lines(lib, "sect_array_disciple")
    assert any(
        line.startswith("陣法「劍陣」") and "+20%" in line and "×80%" in line for line in lines
    )


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------


def test_ai_position_prefers_staying_in_formation() -> None:
    lib = library()
    state = _5am2_state([((0, 0), _5am2_hero())], [((6, 6), _disciple()), ((6, 3), _disciple())])
    weights = lib.ai_profiles.by_id()["flanker"].weights
    assert weights.formation > 0
    near = state.clone()
    near.units[U2_5AM2].pos = Pos(x=6, y=5)  # 與同門相隔 2 格
    far = state.clone()
    far.units[U2_5AM2].pos = Pos(x=5, y=0)  # 與同門相隔 4 格（同樣離主角較近，接近分數更高）
    no_formation = lib.ai_profiles.by_id()["flanker"].weights.model_copy(update={"formation": 0})
    gap_with = position_value(near, U2_5AM2, weights) - position_value(far, U2_5AM2, weights)
    gap_without = position_value(near, U2_5AM2, no_formation) - position_value(
        far, U2_5AM2, no_formation
    )
    assert gap_with - gap_without == weights.formation * 4  # (1200 − 800) ÷ 100 × 權重


def test_ai_values_breaking_formation() -> None:
    lib = library()
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    state = _5am2_state(
        [((3, 0), _5am2_hero())],
        [((3, 5), _disciple()), ((3, 3), _disciple()), ((0, 6), _disciple())],
    )
    hero = state.units[U1_5AM2]
    after = state.clone()
    after.units[U3_5AM2].downed = True  # 打倒中間那名：U2 落單（1200 → 800）
    assert formation_break(state, after, hero, rules) == Fraction(
        400 * rules.formation_break_points, 1000
    )
    # 自己方的陣法不算；沒變化不加分
    assert formation_break(state, state.clone(), hero, rules) == 0


def test_ai_discounts_focusing_heart_linked() -> None:
    lib = library()
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    state = _5am2_state(
        [((3, 4), _5am2_hero())], [((3, 3), _linked()), ((2, 3), template("bandit"))]
    )
    state = give_turn(state, U1_5AM2)
    p = preview(state, Attack(unit_id=U1_5AM2, target_id=U2_5AM2))
    shared = [e for e in p.max_events if isinstance(e, DamageRedirected)]
    assert shared and all(e.to_id == U3_5AM2 for e in shared)
    discount = share_discount(
        state, state.units[U1_5AM2], p.min_events, p.max_events, Fraction(1), rules
    )
    assert discount > 0
    # 沒有相鄰同伴：不分、不扣
    state.units[U3_5AM2].pos = Pos(x=0, y=6)
    p = preview(state, Attack(unit_id=U1_5AM2, target_id=U2_5AM2))
    assert (
        share_discount(state, state.units[U1_5AM2], p.min_events, p.max_events, Fraction(1), rules)
        == 0
    )


def test_formation_battle_is_deterministic() -> None:
    def run() -> list[str]:
        state = _5am2_state(
            [((3, 4), _5am2_hero())],
            [((3, 5), _disciple()), ((3, 6), _disciple()), ((2, 5), _linked())],
            seed=11,
        )
        state = give_turn(state, U2_5AM2)
        out = resolve(state, Attack(unit_id=U2_5AM2, target_id=U1_5AM2))
        return [e.model_dump_json() for e in out.events]

    assert run() == run()


# --- 原 test_mechanics_5am2b.py ---

FLAT_5AM2B = "\n".join(["0000000"] * 7)
U1_5AM2B, U2_5AM2B, U3_5AM2B, U4_5AM2B = (UnitId(f"unit_000{i}") for i in range(1, 5))


def _5am2b_state(
    allies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    enemies: Sequence[tuple[tuple[int, int], UnitTemplate]],
) -> BattleState:
    m = make_map(FLAT_5AM2B, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    spawns = [spawn(Team.ALLY, p, t) for p, t in allies]
    spawns += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    return make_state(m, spawns)


def _stone() -> UnitTemplate:
    return library().unit("sect_array_stone")


def _monk() -> UnitTemplate:
    return template("bandit", tags=("humanoid", "sect"), max_hp=100)


def _5am2b_hit(state: BattleState, target: UnitId, flat: int = 10) -> list[EventBase]:
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=target, source_id=U1_5AM2B, flat=flat, cause="attack")])
    return list(ctx.events)


def _5am2b_dealt(events: Sequence[EventBase], target: UnitId) -> DamageDealt:
    return next(e for e in events if isinstance(e, DamageDealt) and e.target_id == target)


def _scene() -> BattleState:
    # U1 玩家；U2 陣眼石靈 (3,3)；U3 同門 (3,5)；U4 同門 (0,6)（超出 3 格）
    return _5am2b_state(
        [((3, 0), template("hero_fighter", reactions=[], skills=[], max_hp=200))],
        [((3, 3), _stone()), ((3, 5), _monk()), ((0, 6), _monk())],
    )


def test_ward_reduces_kin_damage_in_range_only() -> None:
    state = _scene()
    assert state.units[U2_5AM2B].has_status("array_ward")
    assert ward_permille(state, state.units[U3_5AM2B]) == 800
    assert ward_permille(state, state.units[U4_5AM2B]) == 1000  # 距離 6 格
    assert ward_permille(state, state.units[U2_5AM2B]) == 1000  # 石靈自己不算
    near = _5am2b_dealt(_5am2b_hit(state, U3_5AM2B, 10), U3_5AM2B)
    far = _5am2b_dealt(_5am2b_hit(state, U4_5AM2B, 10), U4_5AM2B)
    assert near.ward_permille == 800 and near.amount == 8
    assert far.ward_permille == 1000 and far.amount == 10
    assert "護陣 ×0.8" in (describe_event(near, state) or "")


def test_ward_ends_when_stone_is_broken() -> None:
    state = _scene()
    events = _5am2b_hit(state, U2_5AM2B, 500)  # 打碎石靈
    assert any(isinstance(e, UnitDowned) and e.unit_id == U2_5AM2B for e in events)
    assert ward_permille(state, state.units[U3_5AM2B]) == 1000
    assert _5am2b_dealt(_5am2b_hit(state, U3_5AM2B, 10), U3_5AM2B).amount == 10


def test_ward_ignores_other_team_and_non_kin() -> None:
    state = _scene()
    state.units[U3_5AM2B].team = Team.ALLY  # 不同陣營
    assert ward_permille(state, state.units[U3_5AM2B]) == 1000
    state = _scene()
    state.units[U3_5AM2B].pos = Pos(x=3, y=4)
    state.units[U3_5AM2B].tags = ("humanoid",)  # 沒有 sect 標籤
    assert ward_permille(state, state.units[U3_5AM2B]) == 1000


def test_ward_schema_and_traits() -> None:
    base = {
        "id": "x_ward",
        "name_zh": "測",
        "description_zh": "測",
        "polarity": "neutral",
        "expires": "never",
        "ward": {"range": 3, "taken_permille": 800},
    }
    assert StatusDef.model_validate(base).ward is not None
    with pytest.raises(ValidationError):
        StatusDef.model_validate({**base, "polarity": "buff", "beneficial": True})
    with pytest.raises(ValidationError):
        StatusDef.model_validate({**base, "ward": {"range": 3, "taken_permille": 1000}})
    lines = unit_trait_lines(library(), "sect_array_stone")
    assert any(line.startswith("護陣「護陣」") and "×80%" in line for line in lines)


def test_ai_values_breaking_the_ward_stone() -> None:
    lib = library()
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    state = _scene()
    down = UnitDowned(unit_id=U2_5AM2B, seq=0, round=1)
    plain = UnitDowned(unit_id=U3_5AM2B, seq=0, round=1)
    hero = state.units[U1_5AM2B]
    ev_stone = priority_points(state, hero, (down,), (down,), Fraction(1), rules)
    ev_plain = priority_points(state, hero, (plain,), (plain,), Fraction(1), rules)
    assert ev_stone - ev_plain == rules.ward_kill_points
