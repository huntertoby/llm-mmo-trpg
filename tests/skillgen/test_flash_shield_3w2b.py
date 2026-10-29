"""Phase 3W-2b 第 7 點：護盾類白板（例：護身）第 3 次大變化的加深與橋接模板。

加深：護盾量提高、護盾附反傷、護盾結束時回少量生命；橋接：護盾破掉時在自己格子造水（潮濕），或對攻擊者施加
標記。補完仍湊不到加深或橋接時，空出的選項用同一招的小變化補滿。行為一致：每個模板套用結果通過驗證器、預算
窗、強度下限，放進戰鬥真的照卡片結算。
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2, of
from tests.engine.test_passive_triggers import always
from trpg.content.skills import SkillDef
from trpg.engine import Attack, BattleState, EndTurn, UseSkill, resolve
from trpg.engine.events import DamageDealt, Healed, ShieldAbsorbed, ShieldEnded, StatusApplied
from trpg.shared.rng import Rng
from trpg.shared.types import Surface, Team
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash import (
    FlashRequest,
    UsageSource,
    apply_variation,
    make_offer,
    with_budget_bonus,
)
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation, acquire
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard

LIB = library()
BONUS = 120
TEMPLATES = {
    "shield_potency": "deepen",
    "shield_thorns": "deepen",
    "shield_mending": "deepen",
    "shield_wet": "bridge",
    "shield_marking": "bridge",
}


def _shield_board(tier: int, seed: int = 1) -> SkillDef:
    return compose_whiteboard(seed, kind="active", tier=tier, library=LIB, recipe_id="guard_up")


def _variation(template_id: str) -> Variation:
    template = LIB.flash.extra_template(template_id)
    assert template is not None
    return Variation(
        source="major", template=template_id, category=template.category, keyword=template.keyword
    )


def _apply(board: SkillDef, template_id: str, *, seed: int = 1) -> SkillDef | None:
    return apply_variation(LIB, board, _variation(template_id), bonus=BONUS, rng=Rng(seed))


def test_the_five_templates_are_in_the_data() -> None:
    for template_id, category in TEMPLATES.items():
        template = LIB.flash.extra_template(template_id)
        assert template is not None and template.only == "shield"
        assert template.category == category
    statuses = LIB.ruleset.statuses.by_id()
    for template_id in ("shield_thorns", "shield_mending", "shield_wet", "shield_marking"):
        template = LIB.flash.extra_template(template_id)
        assert template is not None and template.status is not None
        assert statuses[template.status].absorbs_damage
        assert statuses[template.status].has_shield_riders


@pytest.mark.parametrize("tier", [1, 2, 3])
@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
def test_every_template_makes_a_valid_stronger_or_equal_shield(template_id: str, tier: int) -> None:
    board = _shield_board(tier)
    before = with_budget_bonus(board, BONUS)
    got = _apply(board, template_id)
    assert got is not None, (template_id, tier)
    assert validate_skill(got, LIB) == []
    report = skill_budget(got, LIB)
    assert report.min_ratio <= report.ratio <= report.max_ratio  # 預算比例在窗內
    assert budget_power(got, LIB) >= budget_power(before, LIB)  # 強度下限
    if template_id == "shield_potency":
        assert budget_power(got, LIB) > budget_power(board, LIB)  # 護盾量真的提高
        assert got.effects[0].status is None
    else:
        template = LIB.flash.extra_template(template_id)
        assert template is not None and got.effects[0].status == template.status


def test_bridge_templates_carry_the_keyword_they_bridge_to() -> None:
    board = _shield_board(2)
    for template_id, keyword in (("shield_wet", "wet"), ("shield_marking", "marked")):
        got = _apply(board, template_id)
        assert got is not None
        assert keyword in derive_keywords(got, LIB.keywords).all()
    assert "wet" not in derive_keywords(board, LIB.keywords).all()


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_third_flash_of_a_shield_whiteboard_offers_deepen_and_bridge(tier: int) -> None:
    board = _shield_board(tier)
    records: list[FlashRecord] = []
    for nth in (1, 2):  # 前兩次閃現各取出題的第一個小變化
        state = SkillFlash(base_id=board.id, records=tuple(records), used=True)
        first = make_offer(LIB, FlashRequest(board, state, SkillUsage(), 7, tier=tier)).options[0]
        records.append(FlashRecord(nth=nth, variation=first.variation))
    state = SkillFlash(base_id=board.id, records=tuple(records), used=True)
    offer = make_offer(LIB, FlashRequest(board, state, SkillUsage(), 7, tier=tier))
    cats = {o.variation.category for o in offer.options}
    assert {"deepen", "bridge"} <= cats, cats  # 護盾類也有加深與橋接
    assert len(offer.options) == LIB.flash.pricing.open.options  # 不少出選項（含保底的轉型）


def test_held_keywords_order_the_bridge_options() -> None:
    board = _shield_board(2)
    source = UsageSource()
    base = FlashRequest(board, acquire(board.id), SkillUsage(), 7, tier=2)
    plain = [
        v.template
        for v in source.ranked(LIB, base, "bridge", board)
        if v.template.startswith("shield_")
    ]
    marked_first = FlashRequest(
        board, acquire(board.id), SkillUsage(), 7, held_keywords={"marked": 5}, tier=2
    )
    ranked = [
        v.template
        for v in source.ranked(LIB, marked_first, "bridge", board)
        if v.template.startswith("shield_")
    ]
    assert set(plain) == set(ranked) == {"shield_wet", "shield_marking"}
    assert ranked[0] == "shield_marking"


def test_non_shield_skills_do_not_get_shield_templates() -> None:
    bolt = next(
        s for s in sorted(LIB.skills.values(), key=lambda s: s.id) if s.id.endswith("fire_bolt")
    )
    request = FlashRequest(bolt, acquire(bolt.id), SkillUsage(), 7, tier=2)
    for category in ("deepen", "bridge"):
        names = {v.template for v in UsageSource().ranked(LIB, request, category, bolt)}
        assert not {n for n in names if n.startswith("shield_")}


# ---------------------------------------------------------------------------
# 行為一致：放進戰鬥
# ---------------------------------------------------------------------------


def _shielded_duel(
    skill: SkillDef, *, hp: int = 100, foe: str = "bandit", foe_xy: tuple[int, int] = (4, 3)
) -> BattleState:
    """U1（法師）剛為自己施放 ``skill``（護盾）；之後輪到敵人 U2（預設相鄰）。"""
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[foe_xy])
    owner = caster_template([skill], base="hero_mage", max_hp=200).model_copy(
        update={"max_hp": 200}
    )
    enemy = no_reactions(foe, max_hp=999)
    state = give_turn(
        make_state(
            m, [spawn(Team.ALLY, (3, 3), owner), spawn(Team.ENEMY, foe_xy, enemy)], skills=[skill]
        ),
        U1,
    )
    state.units[U1].hp = hp
    cast = resolve(state, UseSkill(unit_id=U1, skill_id=skill.id))
    ended = answered(resolve(cast.state, EndTurn(unit_id=U1)))
    return give_turn(ended.state, U2)


def _fragile(state: BattleState) -> BattleState:
    """護盾只剩 1 點吸收量：一次命中就打破（測試破盾的附帶效果）。"""
    weak = state.clone()
    weak.units[U1].statuses = [
        replace(s, amount=1) if LIB.ruleset.status_def(s.status_id).absorbs_damage else s
        for s in weak.units[U1].statuses
    ]
    return weak


def _playable(template_id: str, tier: int = 2) -> SkillDef:
    done = _apply(_shield_board(tier), template_id)
    assert done is not None
    # 放進規則包要換成新的技能 ID
    return done.model_copy(update={"id": f"skill_t_{template_id}"})


def test_thorns_shield_reflects_damage_only_on_adjacent_attacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _playable("shield_thorns")
    always(monkeypatch)
    state = _shielded_duel(skill)
    unit = state.units[U1]
    assert any(s.status_id == "shielded_thorns" for s in unit.statuses)
    reflect = LIB.ruleset.status_def("shielded_thorns").shield_reflect
    result = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    absorbed = of(result, ShieldAbsorbed)
    assert absorbed and absorbed[0].status_id == "shielded_thorns" and absorbed[0].melee
    back = [d for d in of(result, DamageDealt) if d.target_id == U2]
    assert back and back[0].amount == reflect  # 卡片寫的反傷點數＝實戰


def test_thorns_shield_does_not_reflect_ranged_attacks(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _playable("shield_thorns")
    always(monkeypatch)
    state = _shielded_duel(skill, foe="bandit_archer", foe_xy=(6, 3))  # 遠程攻擊者，不相鄰
    result = answered(resolve(state, Attack(unit_id=U2, target_id=U1)))
    assert not [d for d in of(result, DamageDealt) if d.target_id == U2]


def test_mending_shield_heals_when_broken(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _playable("shield_mending")
    always(monkeypatch, die=99)
    state = _shielded_duel(skill, hp=100)
    heal = LIB.ruleset.status_def("shielded_mending").shield_end_heal
    result = answered(resolve(_fragile(state), Attack(unit_id=U2, target_id=U1)))
    ended = of(result, ShieldEnded)
    assert ended and ended[0].broken and ended[0].status_id == "shielded_mending"
    healed = [h for h in of(result, Healed) if h.target_id == U1]
    assert healed and healed[0].amount == heal


def test_mending_shield_heals_when_it_expires() -> None:
    skill = _playable("shield_mending")
    state = _shielded_duel(skill, hp=100)
    hp = state.units[U1].hp
    remaining = next(
        s.remaining for s in state.units[U1].statuses if s.status_id == "shielded_mending"
    )
    assert remaining is not None
    cur = give_turn(state, U1)
    healed = []
    for _ in range(remaining + 1):
        ended = answered(resolve(cur, EndTurn(unit_id=U1)))
        healed += [h for h in of(ended, Healed) if h.target_id == U1]
        cur = give_turn(answered(resolve(ended.state, EndTurn(unit_id=U2))).state, U1)
        if not cur.units[U1].has_status("shielded_mending"):
            break
    assert healed and healed[0].amount == min(3, state.units[U1].max_hp - hp)


def test_wet_shield_leaves_water_under_the_owner_when_broken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _playable("shield_wet")
    always(monkeypatch, die=99)
    state = _shielded_duel(skill)
    result = answered(resolve(_fragile(state), Attack(unit_id=U2, target_id=U1)))
    assert of(result, ShieldEnded)
    assert result.state.tile(*result.state.units[U1].xy).surface is Surface.WATER


def test_marking_shield_marks_the_attacker_that_broke_it(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = _playable("shield_marking")
    always(monkeypatch, die=99)
    state = _shielded_duel(skill)
    result = answered(resolve(_fragile(state), Attack(unit_id=U2, target_id=U1)))
    assert of(result, ShieldEnded)
    marked = [e for e in of(result, StatusApplied) if e.status_id == "marked"]
    assert [e.target_id for e in marked] == [U2]
    assert result.state.units[U2].has_status("marked")
