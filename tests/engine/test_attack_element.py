"""Phase 3I-6：臨時附魔與攻擊元素的優先順序（玩法決定 #52，docs/design/06-技能.md 6.10）。"""

from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    make_state,
    no_reactions,
    spawn,
    template,
    with_rolls,
)
from trpg.cli.battle import cmd_replay
from trpg.engine import Action, Attack, BattleState, UseSkill, legal_actions, resolve
from trpg.engine.ai.simple import choose_action
from trpg.engine.attack_element import (
    AttackElementSources,
    attack_element_sources,
    effective_attack_element,
    resolve_attack_element,
)
from trpg.engine.events import DamageDealt, StatusApplied, StatusRemoved, SurfaceChanged
from trpg.engine.runner import run_battle
from trpg.engine.skills.targeting import damage_parameters
from trpg.engine.state import StatusInstance
from trpg.shared.types import Element, Team, UnitId

P, F, ICE, L, H = (
    Element.PHYSICAL,
    Element.FIRE,
    Element.ICE,
    Element.LIGHTNING,
    Element.HOLY,
)
U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
FLAT = "\n".join(["00000000"] * 5)


def src(
    enchant: Element | None = None,
    basic: Element | None = None,
    affix: Element | None = None,
    weapon: Element = P,
    mod: Element | None = None,
) -> AttackElementSources:
    return AttackElementSources(
        enchant=enchant, modifier=mod, basic_affix=basic, weapon_affix=affix, weapon=weapon
    )


# (來源, 是普攻, 武器技自己的元素, 期望) —— 全部規則的表格（詞條來源用測試資料模擬，3K-1 接上）
PRIORITY_TABLE: list[tuple[AttackElementSources, bool, Element | None, Element]] = [
    # 06 6.10（#52 補充二，使用者「是」）：武器本身的元素（法杖）只有附魔能覆寫；
    # 普攻：附魔 ＞ 武器本身元素 ＞ 修正技能 ＞ 普攻附加詞條 ＞ 武器元素詞條 ＞ 物理
    (src(), True, None, P),
    (src(weapon=ICE), True, None, ICE),
    (src(affix=L, weapon=ICE), True, None, ICE),  # 法杖元素不被詞條覆寫
    (src(basic=H, affix=L, weapon=ICE), True, None, ICE),
    (src(mod=L, weapon=F), True, None, F),  # 火焰法杖＋雷擊之手 → 仍是火
    (src(enchant=F, basic=H, affix=L, weapon=ICE, mod=L), True, None, F),
    (src(enchant=H, weapon=ICE), True, None, H),  # 附魔能覆寫法杖
    (src(enchant=F), True, None, F),
    (src(mod=L, basic=H, affix=ICE), True, None, L),  # 物理武器：修正 ＞ 普攻附加 ＞ 武器詞條
    (src(basic=H, affix=ICE), True, None, H),
    (src(affix=L), True, None, L),
    (src(basic=H), True, None, H),
    # 無元素武器技：附魔 ＞ 武器本身元素 ＞ 修正技能 ＞ 武器元素詞條 ＞ 物理（不看普攻附加）
    (src(), False, None, P),
    (src(weapon=ICE), False, None, ICE),
    (src(affix=L, weapon=ICE), False, None, ICE),
    (src(mod=L, weapon=F), False, None, F),
    (src(mod=L, affix=ICE), False, None, L),
    (src(affix=L), False, None, L),
    (src(basic=H), False, None, P),
    (src(basic=H, affix=L), False, None, L),
    (src(enchant=F, mod=L, affix=L, weapon=ICE), False, None, F),
    # 本身已有元素的武器技：不受任何來源影響
    (src(enchant=F, basic=H, affix=L, weapon=ICE, mod=L), False, Element.POISON, Element.POISON),
    (src(enchant=F), False, Element.EARTH, Element.EARTH),
    (src(), False, Element.EARTH, Element.EARTH),
    # 技能自己的元素寫成物理 ＝ 沒有元素
    (src(enchant=F), False, P, F),
]


@pytest.mark.parametrize(("sources", "is_basic", "own", "expected"), PRIORITY_TABLE)
def test_priority_table(
    sources: AttackElementSources, is_basic: bool, own: Element | None, expected: Element
) -> None:
    assert resolve_attack_element(sources, is_basic=is_basic, skill_element=own) is expected


def test_the_resolver_is_pure() -> None:
    sources = src(enchant=F, basic=H, affix=L, weapon=ICE)
    first = resolve_attack_element(sources, is_basic=True)
    assert first is resolve_attack_element(sources, is_basic=True)
    assert isinstance(first, Element)


# ---------------------------------------------------------------------------
# 狀態資料與單位身上的來源
# ---------------------------------------------------------------------------


def arena(
    skills: Sequence[str] = (),
    *,
    hero: str = "hero_fighter",
    weapon: str | None = None,
    surfaces: Sequence[tuple[int, int, str]] = (),
    ally: bool = False,
) -> BattleState:
    """主角 U1（法力 99）、敵人 U2（HP 200，緊鄰），``ally`` 時再加一個友方 U3。"""
    hero_t = template(hero, reactions=[], max_mana=99, skills=list(skills))
    spawns = [
        spawn(Team.ALLY, (1, 2), hero_t, weapon),
        spawn(Team.ENEMY, (2, 2), no_reactions(max_hp=200)),
    ]
    allies = [(1, 2)]
    if ally:
        spawns.append(spawn(Team.ALLY, (1, 3), template("hero_fighter", reactions=[])))
        allies.append((1, 3))
    m = make_map(FLAT, ally=allies, enemy=[(2, 2)], surfaces=surfaces)
    return give_turn(make_state(m, spawns), U1)


def enchant(state: BattleState, unit_id: UnitId, status: str) -> BattleState:
    state.units[unit_id].statuses.append(StatusInstance(status, 3))
    return state


def test_statuses_declare_the_element_in_data() -> None:
    rules = library().ruleset
    assert rules.status_def("infused_fire").attack_element is F
    assert rules.status_def("infused_holy").attack_element is H
    assert rules.status_def("burning").attack_element is None


def test_sources_are_collected_from_the_unit() -> None:
    state = enchant(arena(hero="hero_mage", weapon="fire_staff"), U1, "infused_holy")
    sources = attack_element_sources(state.ruleset, state.units[U1])
    assert sources == AttackElementSources(enchant=H, basic_affix=None, weapon_affix=None, weapon=F)
    assert effective_attack_element(state.ruleset, state.units[U1], is_basic=True) is H
    plain = arena(hero="hero_mage", weapon="fire_staff")
    assert effective_attack_element(plain.ruleset, plain.units[U1], is_basic=True) is F


# ---------------------------------------------------------------------------
# 實戰：附魔期間普攻與武器技真的造成該元素傷害，並觸發元素互動
# ---------------------------------------------------------------------------


def attack_events(state: BattleState) -> list[object]:
    return list(
        resolve(with_rolls(state, [(20, 15), (8, 4)]), Attack(unit_id=U1, target_id=U2)).events
    )


def attack_damage(state: BattleState) -> DamageDealt:
    events = attack_events(state)
    return next(e for e in events if isinstance(e, DamageDealt) and e.cause == "attack")


def test_enchanted_basic_attack_deals_the_enchant_element() -> None:
    assert attack_damage(arena()).element is P
    assert attack_damage(enchant(arena(), U1, "infused_fire")).element is F
    assert attack_damage(enchant(arena(), U1, "infused_holy")).element is H


def test_fire_enchant_ignites_oil_with_a_basic_attack() -> None:
    oil = [(2, 2, "oil")]

    def fire_surfaces(state: BattleState) -> list[SurfaceChanged]:
        return [
            e
            for e in attack_events(state)
            if isinstance(e, SurfaceChanged) and e.cause == "interaction:fire_ignites_oil"
        ]

    assert not fire_surfaces(arena(surfaces=oil))
    assert fire_surfaces(enchant(arena(surfaces=oil), U1, "infused_fire"))


def test_enchant_changes_a_weapon_skill_without_its_own_element() -> None:
    state = enchant(arena(["skill_cleave"]), U1, "infused_fire")
    cleave = library().skills["skill_cleave"]
    params = damage_parameters(state, state.units[U1], cleave, cleave.effects[0])
    assert params.element is F
    cast = resolve(
        with_rolls(state, [(20, 15), (8, 4), (8, 4)]),
        UseSkill(unit_id=U1, skill_id="skill_cleave", direction="east"),
    )
    dealt = [e for e in cast.events if isinstance(e, DamageDealt)]
    assert dealt
    assert all(e.element is params.element for e in dealt)  # 卡片（傷害參數）與實戰一致


def test_a_weapon_skill_with_its_own_element_ignores_the_enchant() -> None:
    skills = library().skills.values()
    own = next(
        s
        for s in skills
        if s.category != "spell"
        and any(e.type == "damage" and e.element is not None for e in s.effects)
    )
    spec = next(e for e in own.effects if e.type == "damage" and e.element is not None)
    state = enchant(arena(), U1, "infused_holy")
    assert damage_parameters(state, state.units[U1], own, spec).element is spec.element


def test_the_staff_element_returns_after_the_enchant_ends() -> None:
    state = arena(hero="hero_mage", weapon="fire_staff")
    ruleset, unit = state.ruleset, state.units[U1]
    assert effective_attack_element(ruleset, unit, is_basic=True) is F
    unit.statuses.append(StatusInstance("infused_holy", 1))
    assert effective_attack_element(ruleset, unit, is_basic=True) is H
    unit.statuses.clear()
    assert effective_attack_element(ruleset, unit, is_basic=True) is F


# ---------------------------------------------------------------------------
# 附魔技能：自己、友方、後施放的覆蓋先施放的
# ---------------------------------------------------------------------------


def test_fire_enchant_targets_self_and_holy_weapon_targets_an_ally() -> None:
    state = arena(["skill_fire_enchant", "skill_holy_weapon"], ally=True)
    after = resolve(state, UseSkill(unit_id=U1, skill_id="skill_fire_enchant")).state
    assert [s.status_id for s in after.units[U1].statuses] == ["infused_fire"]
    result = resolve(after, UseSkill(unit_id=U1, skill_id="skill_holy_weapon", target_id=U3))
    applied = [e for e in result.events if isinstance(e, StatusApplied)]
    assert [(e.target_id, e.status_id) for e in applied] == [(U3, "infused_holy")]
    ally = result.state.units[U3]
    assert [s.status_id for s in ally.statuses] == ["infused_holy"]
    assert effective_attack_element(result.state.ruleset, ally, is_basic=True) is H


def test_the_later_enchant_replaces_the_earlier_one() -> None:
    state = enchant(arena(["skill_fire_enchant", "skill_holy_weapon"]), U1, "infused_holy")
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_fire_enchant"))
    removed = [e for e in result.events if isinstance(e, StatusRemoved)]
    assert [(e.status_id, e.reason) for e in removed] == [("infused_holy", "replaced")]
    unit = result.state.units[U1]
    assert [s.status_id for s in unit.statuses] == ["infused_fire"]
    assert effective_attack_element(result.state.ruleset, unit, is_basic=True) is F


def test_recasting_the_same_enchant_refreshes_without_replacing() -> None:
    state = enchant(arena(["skill_fire_enchant"]), U1, "infused_fire")
    result = resolve(state, UseSkill(unit_id=U1, skill_id="skill_fire_enchant"))
    assert not [e for e in result.events if isinstance(e, StatusRemoved)]
    assert [s.status_id for s in result.state.units[U1].statuses] == ["infused_fire"]


def test_a_battle_with_enchant_skills_is_deterministic_and_replays(tmp_path: Path) -> None:
    hero_t = template("hero_fighter", max_mana=99, skills=["skill_fire_enchant", "skill_cleave"])
    setup = make_setup(
        make_map(FLAT, ally=[(1, 2)], enemy=[(5, 2)]),
        [spawn(Team.ALLY, (1, 2), hero_t), spawn(Team.ENEMY, (5, 2))],
        max_rounds=6,
    )

    def chooser(state: BattleState) -> Action:
        unit = state.active
        if unit is not None and unit.id == U1 and not unit.statuses and unit.ap >= 1:
            cast = UseSkill(unit_id=U1, skill_id="skill_fire_enchant")
            if cast in legal_actions(state):
                return cast
        return choose_action(state)

    first = run_battle(setup, 11, chooser)
    again = run_battle(setup, 11, chooser)
    assert [e.model_dump() for e in first.events] == [e.model_dump() for e in again.events]
    assert any(isinstance(e, StatusApplied) and e.status_id == "infused_fire" for e in first.events)
    path = tmp_path / "log.json"
    path.write_text(first.to_log().model_dump_json(), encoding="utf-8")
    out = io.StringIO()
    assert cmd_replay(path, out) == 0
    assert "重播驗證通過" in out.getvalue()
