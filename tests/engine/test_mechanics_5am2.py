"""Phase 5A-M2：引擎機制②（``docs/phases/Phase5計畫.md`` 第 16 節）。

陣法範圍加成（狀態 ``formation``，劍陣弟子「劍陣」）、把傷害分給同門（狀態 ``share_damage``，詞綴
「連心的」）、戰鬥紀錄與單位卡特性欄的中文、AI 的估值。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import give_turn, library, make_map, make_state, spawn, template
from trpg.content.battle import OpeningStatus, StatusDef, UnitTemplate
from trpg.content.world_enemies import apply_affix
from trpg.engine import BattleState, preview, resolve
from trpg.engine.actions import Attack
from trpg.engine.ai.priority import formation_break, share_discount
from trpg.engine.ai.utility import position_value
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import DamageDealt, DamageRedirected, EventBase, UnitDowned
from trpg.engine.formation import formation_permille
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.narrative.unit_traits import unit_trait_lines
from trpg.shared.types import Pos, Team, UnitId

FLAT = "\n".join(["0000000"] * 7)
U1, U2, U3, U4, U5 = (UnitId(f"unit_000{i}") for i in range(1, 6))


def _state(
    allies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    enemies: Sequence[tuple[tuple[int, int], UnitTemplate]],
    seed: int = 0,
) -> BattleState:
    m = make_map(FLAT, None, ally=[p for p, _ in allies], enemy=[p for p, _ in enemies])
    spawns = [spawn(Team.ALLY, p, t) for p, t in allies]
    spawns += [spawn(Team.ENEMY, p, t) for p, t in enemies]
    return make_state(m, spawns, seed=seed)


def _hero(**overrides: object) -> UnitTemplate:
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
    state = _state([((0, 0), _hero())], enemies)
    holder = state.units[U2]
    assert holder.has_status("sword_formation")
    assert formation_permille(state, holder) == expected


def test_formation_ignores_far_foreign_and_downed_units() -> None:
    plain = template("bandit")  # 沒有 sword_array 標籤
    state = _state(
        [((3, 4), _hero(tags=["hero", "sword_array"]))],  # 敵方帶標籤也不算
        [((3, 6), _disciple()), ((3, 2), _disciple()), ((4, 6), plain)],  # 第二名相隔 4 格
    )
    assert formation_permille(state, state.units[U2]) == 800
    state.units[U3].pos = Pos(x=3, y=3)  # 3 格
    assert formation_permille(state, state.units[U2]) == 1200
    state.units[U3].downed = True
    assert formation_permille(state, state.units[U2]) == 800


def test_formation_scales_attack_damage_and_log() -> None:
    state = _state([((3, 0), _hero(max_hp=200))], [((3, 5), _disciple()), ((3, 3), _disciple())])
    events = _hit(state, U1, U2, flat=10)
    hit = _dealt(events, U1)
    assert hit.formation_permille == 1200 and hit.amount == 12
    assert "陣法 ×1.2" in (describe_event(hit, state) or "")
    # 不是攻擊（例如狀態傷害）不加
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=U1, source_id=U2, flat=10, cause="effect")])
    assert _dealt(ctx.events, U1).amount == 10


def test_formation_alone_is_weaker() -> None:
    state = _state([((3, 0), _hero(max_hp=200))], [((3, 5), _disciple())])
    hit = _dealt(_hit(state, U1, U2, flat=10), U1)
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
    state = _state(
        [((0, 0), _hero())],
        [((3, 3), _linked()), ((3, 2), template("bandit")), ((2, 3), template("bandit"))],
    )
    before = {u: state.units[u].hp for u in (U2, U3, U4)}
    events = _hit(state, U2, U1, flat=21)  # 21 × 30% ＝ 6（捨去），平分 3＋3
    hit = _dealt(events, U2)
    assert hit.shared == 6 and before[U2] - state.units[U2].hp == 15
    moved = [(e.to_id, e.amount) for e in events if isinstance(e, DamageRedirected)]
    assert moved == [(U3, 3), (U4, 3)]
    assert before[U3] - state.units[U3].hp == 3
    texts = [describe_event(e, state) or "" for e in events]
    assert any("6 點分給同門" in t for t in texts)
    assert any("分擔了" in t and "連心" in t for t in texts)


def test_share_damage_remainder_goes_to_lower_id() -> None:
    state = _state(
        [((0, 0), _hero())],
        [((3, 3), _linked()), ((3, 2), template("bandit")), ((2, 3), template("bandit"))],
    )
    events = _hit(state, U2, U1, flat=17)  # 17 × 30% ＝ 5 → 3＋2
    assert [(e.to_id, e.amount) for e in events if isinstance(e, DamageRedirected)] == [
        (U3, 3),
        (U4, 2),
    ]


def test_share_damage_needs_adjacent_ally() -> None:
    state = _state([((3, 4), _hero())], [((3, 3), _linked()), ((3, 1), template("bandit"))])
    hp = state.units[U2].hp
    events = _hit(state, U2, U1, flat=10)
    assert _dealt(events, U2).shared == 0 and hp - state.units[U2].hp == 10
    assert not any(isinstance(e, DamageRedirected) for e in events)


def test_share_damage_after_shield_and_can_down_kin() -> None:
    state = _state([((0, 0), _hero())], [((3, 3), _linked()), ((3, 2), template("bandit"))])
    state.units[U2].statuses.append(StatusInstance("shielded", remaining=2, amount=5))
    state.units[U3].hp = 2
    events = _hit(state, U2, U1, flat=25)  # 護盾吸收 5，剩 20 × 30% ＝ 6
    hit = _dealt(events, U2)
    assert hit.absorbed == 5 and hit.shared == 6
    assert any(isinstance(e, UnitDowned) and e.unit_id == U3 for e in events)


def test_share_damage_skips_falls() -> None:
    state = _state([((0, 0), _hero())], [((3, 3), _linked()), ((3, 2), template("bandit"))])
    ctx = Ctx(state)
    execute(ctx, [DamageEffect(target_id=U2, source_id=None, flat=10, cause="fall")])
    assert _dealt(ctx.events, U2).shared == 0


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
    state = _state([((0, 0), _hero())], [((6, 6), _disciple()), ((6, 3), _disciple())])
    weights = lib.ai_profiles.by_id()["flanker"].weights
    assert weights.formation > 0
    near = state.clone()
    near.units[U2].pos = Pos(x=6, y=5)  # 與同門相隔 2 格
    far = state.clone()
    far.units[U2].pos = Pos(x=5, y=0)  # 與同門相隔 4 格（同樣離主角較近，接近分數更高）
    no_formation = lib.ai_profiles.by_id()["flanker"].weights.model_copy(update={"formation": 0})
    gap_with = position_value(near, U2, weights) - position_value(far, U2, weights)
    gap_without = position_value(near, U2, no_formation) - position_value(far, U2, no_formation)
    assert gap_with - gap_without == weights.formation * 4  # (1200 − 800) ÷ 100 × 權重


def test_ai_values_breaking_formation() -> None:
    lib = library()
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    state = _state(
        [((3, 0), _hero())], [((3, 5), _disciple()), ((3, 3), _disciple()), ((0, 6), _disciple())]
    )
    hero = state.units[U1]
    after = state.clone()
    after.units[U3].downed = True  # 打倒中間那名：U2 落單（1200 → 800）
    assert formation_break(state, after, hero, rules) == Fraction(
        400 * rules.formation_break_points, 1000
    )
    # 自己方的陣法不算；沒變化不加分
    assert formation_break(state, state.clone(), hero, rules) == 0


def test_ai_discounts_focusing_heart_linked() -> None:
    lib = library()
    rules = lib.ai_profiles.by_id()["brute"].rewrite
    state = _state([((3, 4), _hero())], [((3, 3), _linked()), ((2, 3), template("bandit"))])
    state = give_turn(state, U1)
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    shared = [e for e in p.max_events if isinstance(e, DamageRedirected)]
    assert shared and all(e.to_id == U3 for e in shared)
    discount = share_discount(
        state, state.units[U1], p.min_events, p.max_events, Fraction(1), rules
    )
    assert discount > 0
    # 沒有相鄰同伴：不分、不扣
    state.units[U3].pos = Pos(x=0, y=6)
    p = preview(state, Attack(unit_id=U1, target_id=U2))
    assert (
        share_discount(state, state.units[U1], p.min_events, p.max_events, Fraction(1), rules) == 0
    )


def test_formation_battle_is_deterministic() -> None:
    def run() -> list[str]:
        state = _state(
            [((3, 4), _hero())],
            [((3, 5), _disciple()), ((3, 6), _disciple()), ((2, 5), _linked())],
            seed=11,
        )
        state = give_turn(state, U2)
        out = resolve(state, Attack(unit_id=U2, target_id=U1))
        return [e.model_dump_json() for e in out.events]

    assert run() == run()
