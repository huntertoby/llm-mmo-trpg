"""PB-1a：霧鎖真人的三個部位（正式內容；``docs/design/18-雲嶺內容.md`` 18.2.3「部位」表）。

拂塵（任何方向；破＝封住霧遁）、氣海（從背後；鎖霧、歸一才露出；破＝停掉歸一的回合開始回血）、
長劍（歸一才露出；破＝造成的傷害降成內容寫的倍率‰＋打斷蓄力）。實際跑引擎驗每一條。

部位血量（``hp_permille``）與長劍的降傷倍率是數值工坊開放的欄位，一律從 ``content/`` 的原始 YAML
讀現值（PB-1b2；使用者寫回後不必收編）；部位結構（ID、名稱、方向、露出階段、破壞效果種類）寫死。
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_setup, spawn, template
from trpg.content.battle import UnitTemplate
from trpg.content.loader import bundled_content_dir, parse_yaml
from trpg.content.parts import SealSkillBreak
from trpg.content.skills import CHARGING
from trpg.engine import BattleState, legal_actions, resolve
from trpg.engine.actions import Attack, EndTurn
from trpg.engine.battle import start_battle
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import (
    EventBase,
    FollowupCancelled,
    PartBroken,
    PartStatDown,
    SkillSealed,
    StatusApplied,
    StatusRemoved,
)
from trpg.engine.parts import part_targets
from trpg.engine.rules.statuses import damage_dealt_permille
from trpg.engine.setup import with_phase_assets
from trpg.engine.state import StatusInstance
from trpg.narrative.events import describe_event
from trpg.shared.types import Team, UnitId
from trpg.world.battle import grow_enemy

HERO = UnitId("unit_0001")
MASTER = UnitId("unit_0002")
MASTER_ID = "sect_mist_lock_master"
FLAT = "\n".join(["000000"] * 6)
PHASE = {"sword_array": 0, "mist_lock": 1, "return_to_one": 2}
MAX_HP = 120


def raw_parts() -> dict[str, dict[str, object]]:
    """霧鎖真人內容檔原始 YAML 的 ``parts``（部位 ID → 原始資料）。"""
    path = bundled_content_dir() / "units" / f"{MASTER_ID}.yaml"
    data = parse_yaml(path.read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["parts"]}


def raw_hp_permille(part: str) -> int:
    value = raw_parts()[part]["hp_permille"]
    assert isinstance(value, int)
    return value


def raw_sword_damage_permille() -> int:
    """長劍破掉後第 1 個效果（``stat_down damage_dealt``）的倍率‰。"""
    on_break = raw_parts()["sword"]["on_break"]
    assert isinstance(on_break, list)
    first = on_break[0]
    assert (first["type"], first["stat"]) == ("stat_down", "damage_dealt")
    amount = first["amount"]
    assert isinstance(amount, int) and 0 < amount < 1000  # 真的是降傷
    return int(amount)


def master(**overrides: object) -> UnitTemplate:
    return template(MASTER_ID, reactions=(), **overrides)


def arena(hero_at: tuple[int, int] = (2, 3), *, phase: str = "sword_array") -> BattleState:
    lib = library()
    setup = make_setup(
        make_map(FLAT, ally=[hero_at], enemy=[(3, 3)]),
        [
            spawn(Team.ALLY, hero_at, template("hero_fighter", reactions=())),
            spawn(Team.ENEMY, (3, 3), master(max_hp=MAX_HP)),
        ],
    )
    state = give_turn(start_battle(with_phase_assets(lib, setup), 0), HERO)
    state.units[MASTER].facing = "west"
    state.units[MASTER].phase_index = PHASE[phase]
    return state


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def reasons(state: BattleState) -> dict[str, str | None]:
    action = Attack(unit_id=HERO, target_id=MASTER)
    return {t.part_id: t.reason for t in part_targets(state, action)}


def break_part(state: BattleState, part: str) -> Ctx:
    s = state.clone()
    s.units[MASTER].part_hp[part] = 1
    ctx = Ctx(s)
    execute(
        ctx,
        [DamageEffect(target_id=MASTER, source_id=HERO, cause="attack", flat=5, part_id=part)],
    )
    return ctx


def test_the_three_parts_follow_the_design_table() -> None:
    parts = {p.id: p for p in library().unit(MASTER_ID).parts}
    assert [(p.id, p.name_zh, p.hp_permille, p.reach, p.exposed_in) for p in parts.values()] == [
        ("whisk", "拂塵", raw_hp_permille("whisk"), "any", ()),
        ("dantian", "氣海", raw_hp_permille("dantian"), "behind", ("mist_lock", "return_to_one")),
        ("sword", "長劍", raw_hp_permille("sword"), "any", ("return_to_one",)),
    ]
    assert [e.type for e in parts["whisk"].on_break] == ["seal_skill"]
    assert [e.type for e in parts["dantian"].on_break] == ["stop_mechanic"]
    assert [e.type for e in parts["sword"].on_break] == ["stat_down", "interrupt_charge"]


def test_each_part_hp_is_its_permille_of_120_hp() -> None:
    state = arena()
    assert state.units[MASTER].max_hp == MAX_HP
    assert state.units[MASTER].part_hp == {
        part: max(1, MAX_HP * raw_hp_permille(part) // 1000)
        for part in ("whisk", "dantian", "sword")
    }


def test_the_content_hp_gives_the_same_ratio() -> None:
    lib = library()
    hp = lib.ruleset.core.template_max_hp(lib.unit(MASTER_ID))
    setup = make_setup(
        make_map(FLAT, ally=[(2, 3)], enemy=[(3, 3)]),
        [spawn(Team.ALLY, (2, 3), "hero_fighter"), spawn(Team.ENEMY, (3, 3), MASTER_ID)],
    )
    state = start_battle(with_phase_assets(lib, setup), 0)
    assert state.units[MASTER].part_hp == {
        part: max(1, hp * raw_hp_permille(part) // 1000) for part in ("whisk", "dantian", "sword")
    }


@pytest.mark.parametrize(
    ("phase", "hero_at", "expected"),
    [
        ("sword_array", (2, 3), {"whisk": None, "dantian": "not_exposed", "sword": "not_exposed"}),
        ("sword_array", (4, 3), {"whisk": None, "dantian": "not_exposed", "sword": "not_exposed"}),
        ("mist_lock", (2, 3), {"whisk": None, "dantian": "need_behind", "sword": "not_exposed"}),
        ("mist_lock", (4, 3), {"whisk": None, "dantian": None, "sword": "not_exposed"}),
        ("return_to_one", (2, 3), {"whisk": None, "dantian": "need_behind", "sword": None}),
        ("return_to_one", (4, 3), {"whisk": None, "dantian": None, "sword": None}),
    ],
)
def test_what_can_be_picked_in_each_phase(
    phase: str, hero_at: tuple[int, int], expected: dict[str, str | None]
) -> None:
    assert reasons(arena(hero_at, phase=phase)) == expected


def test_breaking_the_whisk_seals_mist_shift() -> None:
    ctx = break_part(arena(phase="mist_lock"), "whisk")
    assert [e.skill_id for e in of(ctx.events, SkillSealed)] == ["skill_mist_shift"]
    turn = give_turn(ctx.state, MASTER)
    turn.units[MASTER].skills = ("skill_mist_shift", "skill_mist_lock_peaks", "skill_cluster_bolt")
    turn.units[MASTER].mana = 99
    assert all(getattr(a, "skill_id", None) != "skill_mist_shift" for a in legal_actions(turn))
    text = describe_event(of(ctx.events, PartBroken)[0], ctx.state) or ""
    assert "霧鎖真人的拂塵被打碎了" in text and "封住「霧遁」" in text


def test_breaking_the_dantian_in_return_to_one_stops_the_heal() -> None:
    state = arena((4, 3), phase="return_to_one")
    state.units[MASTER].statuses.append(StatusInstance(status_id="mist_return"))
    ctx = break_part(state, "dantian")
    assert [e.status_id for e in of(ctx.events, StatusRemoved)] == ["mist_return"]
    # 下一個回合開始不回血（對照組：沒破的照常回血）
    healed = []
    for s in (state, ctx.state):
        turn = give_turn(s, HERO)
        turn.units[MASTER].hp = 20
        after = resolve(turn, EndTurn(unit_id=HERO))
        assert after.state.active_unit == MASTER
        healed.append(after.state.units[MASTER].hp - 20)
    assert healed[0] > 0 and healed[1] == 0


def test_breaking_the_dantian_in_mist_lock_keeps_return_to_one_from_healing() -> None:
    ctx = break_part(arena((4, 3), phase="mist_lock"), "dantian")
    turn = give_turn(ctx.state, HERO)
    turn.units[MASTER].hp = 30  # ≤ 300‰ → 進入歸一
    result = resolve(turn, EndTurn(unit_id=HERO))
    assert result.state.units[MASTER].phase_index == PHASE["return_to_one"]
    assert not result.state.units[MASTER].has_status("mist_return")
    assert all(e.status_id != "mist_return" for e in of(result.events, StatusApplied))


def test_breaking_the_sword_lowers_damage_and_interrupts_the_cleave() -> None:
    state = arena(phase="return_to_one")
    state.units[MASTER].statuses.append(
        StatusInstance(status_id=CHARGING, skill_id="skill_charged_cleave")
    )
    ctx = break_part(state, "sword")
    damage = raw_sword_damage_permille()
    assert [(e.stat, e.total) for e in of(ctx.events, PartStatDown)] == [("damage_dealt", damage)]
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == ["part_broken"]
    unit = ctx.state.units[MASTER]
    assert damage_dealt_permille(ctx.state.ruleset, unit) == damage
    assert not unit.has_status(CHARGING)


def test_a_peaks_charge_carried_into_return_to_one_is_interrupted_too() -> None:
    state = arena(phase="return_to_one")
    state.units[MASTER].statuses.append(
        StatusInstance(status_id=CHARGING, skill_id="skill_mist_lock_peaks")
    )
    ctx = break_part(state, "sword")
    assert [e.reason for e in of(ctx.events, FollowupCancelled)] == ["part_broken"]


def test_growth_renames_the_sealed_skill_with_the_tier() -> None:
    lib = library()
    grown, extra = grow_enemy(lib, lib.unit(MASTER_ID), 6)
    whisk = next(p for p in grown.parts if p.id == "whisk")
    (seal,) = whisk.on_break
    assert isinstance(seal, SealSkillBreak)
    assert seal.skill in grown.skills and seal.skill in {s.id for s in extra}
