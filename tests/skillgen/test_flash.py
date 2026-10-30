"""Phase 3W-1：閃現的規則核心——資料、預算上限加成、套用變化、推出技能、出題（混合、指定類別、
轉型保底）、確定性與實戰一致。"""

from __future__ import annotations

import dataclasses
from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.flash_templates import FlashTable
from trpg.content.library import scale_mana_cost
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import DamageDealt
from trpg.engine.preview import preview
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash_category import allowed_categories, is_support_skill
from trpg.skillgen.flash_derive import (
    apply_variation,
    derive_skill,
    unimplemented_ops,
    with_budget_bonus,
)
from trpg.skillgen.flash_offer import FlashOffer, FlashRequest, choose, make_offer
from trpg.skillgen.flash_ops import FLASH_OPS
from trpg.skillgen.flash_state import COMPLETE_SLOT, SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

FIRE_BOLT = "skill_fire_bolt"
"""火焰箭：單體、射程 5、1d8 火焰 ＋ 燃燒。"""
SEED = 7
RANGE = Variation(source="minor", template="range_plus", category="area")
AREA = Variation(source="minor", template="area_plus", category="area")


def _used(state: SkillFlash) -> SkillFlash:
    return state.model_copy(update={"used": True})


def _offer(skill_id: str, state: SkillFlash | None = None, **fields: Any) -> FlashOffer:
    lib = library()
    state = state or _used(acquire(skill_id))
    return make_offer(lib, FlashRequest(lib.skills[skill_id], state, SkillUsage(), SEED, **fields))


PREFER = ("range_plus", "extend_duration", "cost_charge")
"""走 ``_walk`` 時優先選的小變化（結構單純，之後的大變化選項才穩定）。"""


def _walk(skill_id: str, picks: int) -> tuple[SkillFlash, SkillDef]:
    """閃 ``picks`` 次（有 ``PREFER`` 裡的模板就選它，否則選第一個）。"""
    lib = library()
    state = _used(acquire(skill_id))
    skill = lib.skills[skill_id]
    for _ in range(picks):
        offer = _offer(skill_id, state)
        assert offer.options, f"{skill_id} 第 {len(state.records) + 1} 次沒有選項"
        names = [o.variation.template for o in offer.options]
        index = next((names.index(p) for p in PREFER if p in names), 0)
        state, skill = choose(state, offer, index)
        state = _used(state)
    return state, skill


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_content_matches_decisions_69_and_70() -> None:
    table = library().flash
    rules = table.rules
    assert (rules.max_flashes, rules.major_flash, rules.budget_step_permille) == (5, 3, 40)
    assert (rules.complete.flashes, rules.complete.budget_permille) == (3, 120)
    assert rules.dissolve_refund_permille == 500
    assert (table.pricing.open.cost, table.pricing.open.options) == (1, 4)
    assert (table.pricing.focused.cost, table.pricing.focused.options) == (2, 3)
    minor = [c.id for c in table.stage_categories("minor")]
    assert minor == [
        "area",
        "combo",
        "element",
        "cost",
        "extend",
        "support",
        "trigger",
        "modifier",
    ]
    assert [c.id for c in table.stage_categories("major")] == ["deepen", "bridge"]
    assert table.category("cost").kinds == ("active", "stance")
    assert set(table.category("trigger").kinds) == {"passive", "reaction"}
    assert table.category("support").support_only


def test_every_minor_op_in_the_data_is_implemented() -> None:
    """3W-2 新增模板時，``op`` 要同時登錄到 ``FLASH_OPS``。"""
    assert unimplemented_ops(library().flash) == ()
    assert {"area", "range"} <= set(FLASH_OPS)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {"categories": [{"id": "a", "name_zh": "甲"}, {"id": "a", "name_zh": "乙"}]},
            "類別 ID 重複",
        ),
        (
            {
                "categories": [{"id": "a", "name_zh": "甲", "stage": "major"}],
                "minor": [
                    {
                        "id": "t",
                        "category": "a",
                        "op": "area",
                        "delta": 1,
                        "prefix_zh": "x",
                        "summary_zh": "y",
                    }
                ],
            },
            "不是小變化類別",
        ),
        (
            {
                "categories": [{"id": "a", "name_zh": "甲"}],
                "minor": [
                    {"id": "t", "category": "a", "op": "area", "prefix_zh": "x", "summary_zh": "y"}
                ],
            },
            "delta",
        ),
        ({"rules": {"max_flashes": 2, "major_flash": 3}}, "major_flash"),
        (
            {"transforms": [{"id": "t", "to": "passive", "prefix_zh": "x", "summary_zh": "y"}]},
            "trigger",
        ),
    ],
)
def test_schema_rejects_bad_tables(data: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        FlashTable.model_validate(data)


def test_library_checks_major_templates_against_the_evolution_table() -> None:
    from trpg.content.library import _load_flash  # noqa: PLC0415
    from trpg.shared.errors import ContentError  # noqa: PLC0415

    lib = library()
    good = lib.flash.model_dump(mode="json")
    bad = {**good, "major": [{"id": "m", "category": "bridge", "evolution": "intensify"}]}
    unknown = {**good, "major": [{"id": "m", "category": "deepen", "evolution": "nope"}]}
    for data, message in ((bad, "是 deepen"), (unknown, "未知的進化模板")):

        def load(_rel: str, model: type[Any], d: dict[str, Any] = data) -> Any:
            return model.model_validate(d)

        with pytest.raises(ContentError, match=message):
            _load_flash(lib.root, load, lib.evolution, lib.ruleset.skill_triggers)


# ---------------------------------------------------------------------------
# 預算上限加成
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bonus", [0, 40, 120, 200])
def test_budget_bonus_scales_the_usable_budget(bonus: int) -> None:
    lib = library()
    skill = lib.skills[FIRE_BOLT]
    plain = skill_budget(skill, lib)
    raised = skill_budget(with_budget_bonus(skill, bonus), lib)
    assert raised.bonus_permille == bonus
    assert raised.total == plain.total
    assert raised.usable == plain.usable * Fraction(1000 + bonus, 1000)


def test_handwritten_skills_have_no_bonus() -> None:
    lib = library()
    assert all(s.budget_bonus_permille is None for s in lib.skills.values())
    assert with_budget_bonus(lib.skills[FIRE_BOLT], 0) is lib.skills[FIRE_BOLT]
    with pytest.raises(ValueError, match="不可為負"):
        with_budget_bonus(lib.skills[FIRE_BOLT], -5)


# ---------------------------------------------------------------------------
# 套用變化
# ---------------------------------------------------------------------------


def _within_cap(skill: SkillDef, base: SkillDef, flashes: int) -> None:
    lib = library()
    report = skill_budget(skill, lib)
    assert report.bonus_permille == 40 * flashes
    assert report.min_ratio <= report.ratio <= report.max_ratio
    plain = skill_budget(with_budget_bonus(skill, 0), lib)
    assert report.total <= plain.usable * Fraction(1000 + 40 * flashes, 1000)
    assert validate_skill(skill, lib) == []
    assert (skill.tier, skill.kind, skill.ap_cost) == (base.tier, base.kind, base.ap_cost)


def test_range_plus_adds_one_range_and_retunes_within_the_raised_cap() -> None:
    lib = library()
    base = lib.skills[FIRE_BOLT]
    done = apply_variation(lib, base, RANGE, bonus=40, rng=Rng(1))
    assert done is not None
    assert done.shape.range == 6
    _within_cap(done, base, 1)


def test_area_plus_grows_size_or_radius() -> None:
    lib = library()
    grown = 0
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        if skill.kind != "active" or skill.tier != 1:
            continue
        done = apply_variation(lib, skill, AREA, bonus=40, rng=Rng(2))
        if done is None:
            continue
        grown += 1
        before, after = skill.shape, done.shape
        assert (after.size or 0) + (after.radius or 0) == (before.size or 0) + (
            before.radius or 0
        ) + 1
        _within_cap(done, skill, 1)
        if grown >= 5:
            break
    assert grown >= 3


def test_templates_that_do_not_fit_return_none() -> None:
    lib = library()
    single = lib.skills[FIRE_BOLT]  # 單體沒有 size／radius
    assert apply_variation(lib, single, AREA, bonus=40, rng=Rng(0)) is None
    unknown = Variation(source="minor", template="nope", category="area")
    assert apply_variation(lib, single, unknown, bonus=40, rng=Rng(0)) is None
    transform = Variation(source="transform", template="nope", category="transform")
    assert apply_variation(lib, single, transform, bonus=120, rng=Rng(0)) is None


# ---------------------------------------------------------------------------
# 推出技能、選擇、重閃
# ---------------------------------------------------------------------------


def test_five_flashes_raise_the_cap_step_by_step_and_derive_matches_the_pick() -> None:
    lib = library()
    base = lib.skills[FIRE_BOLT]
    state = _used(acquire(FIRE_BOLT))
    names = []
    for nth in range(1, 6):
        offer = _offer(FIRE_BOLT, state)
        assert offer.nth == nth and offer.major is (nth == 3) and offer.cost == 1
        state, skill = choose(state, offer, 0)
        assert derive_skill(lib, base, state, SEED) == skill  # 重算 ＝ 選到的結果
        _within_cap(skill, base, nth)
        assert skill.id.startswith(f"{FIRE_BOLT}_fl_") and skill.provenance.parents == (FIRE_BOLT,)
        names.append(skill.name_zh)
        state = _used(state)
    assert state.spent == 5
    assert names[:2] == ["火焰箭", "火焰箭"]  # 小變化不改名
    assert all(n.endswith("・火焰箭") for n in names[2:])  # 大變化：組合式名稱
    assert len({s for s in names[2:]}) == 1
    # 第 5 次之後不能再閃（由 flash_state 檢查）；已閃 5 次的技能 ID 都不同
    assert len(state.records) == 5


def test_choose_rejects_stale_or_foreign_offers() -> None:
    state = _used(acquire(FIRE_BOLT))
    offer = _offer(FIRE_BOLT, state)
    with pytest.raises(ValueError, match="不存在"):
        choose(state, offer, 9)
    with pytest.raises(ValueError, match="不是"):
        choose(_used(acquire("skill_other")), offer, 0)
    moved, _ = choose(state, offer, 0)
    with pytest.raises(ValueError, match="過期"):
        choose(moved, offer, 0)


def test_reflash_replaces_one_slot_and_reapplies_the_later_ones() -> None:
    lib = library()
    base = lib.skills[FIRE_BOLT]
    state, _skill = _walk(FIRE_BOLT, 4)
    offer = _offer(FIRE_BOLT, state, slot=1)
    assert offer.slot == 1 and offer.reflashes == 1 and not offer.major and offer.cost == 1
    assert offer.options
    after, again = choose(state.model_copy(update={"used": False}), offer, 0)  # 不需要先上場
    assert len(after.records) == 4 and after.record(1).reflashes == 1  # type: ignore[union-attr]
    assert not after.used
    assert after.spent == state.spent + 1
    assert derive_skill(lib, base, after, SEED) == again
    assert again.budget_bonus_permille == 160  # 次數沒變
    # 重閃第 3 次出大變化
    major = _offer(FIRE_BOLT, state, slot=3)
    assert major.major and all(o.variation.source != "minor" for o in major.options)
    # 同一欄再重閃：種子標籤的重閃次數遞增
    assert _offer(FIRE_BOLT, after, slot=1).reflashes == 2


def test_offers_are_deterministic_and_round_trip() -> None:
    state, _skill = _walk(FIRE_BOLT, 2)
    first = _offer(FIRE_BOLT, state)
    assert _offer(FIRE_BOLT, state) == first
    assert FlashOffer.model_validate_json(first.model_dump_json()) == first
    assert SkillFlash.model_validate_json(state.model_dump_json()) == state


# ---------------------------------------------------------------------------
# 出題：混合、指定類別、轉型保底
# ---------------------------------------------------------------------------


def test_open_major_offer_mixes_deepen_and_bridge() -> None:
    state, _ = _walk(FIRE_BOLT, 2)
    offer = _offer(FIRE_BOLT, state)
    assert offer.major and len(offer.options) == 4
    # 第 3 次：加深、橋接各至少 1，有合法轉型時另有轉型（3W-3）
    assert {o.variation.category for o in offer.options} == {"deepen", "bridge", "transform"}


def test_open_minor_offer_covers_two_categories_when_it_can() -> None:
    """用一個假的「連段」模板（實際上換成距離 +1 的改法），檢查混合出題至少涵蓋 2 類。"""
    lib = library()
    table = lib.flash
    fake = table.minor_template("range_plus").model_copy(  # type: ignore[union-attr]
        update={"id": "fake_combo", "category": "combo", "prefix_zh": "連", "summary_zh": "假"}
    )
    lib = dataclasses.replace(lib, flash=table.model_copy(update={"minor": (*table.minor, fake)}))
    square = next(
        s.id
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active"
        and s.shape.type == "square3"
        and isinstance(s.shape.range, int)
        and s.tier == 1
        and s.followup is None
        and s.trap is None
    )
    skill = lib.skills[square]
    request = FlashRequest(skill, _used(acquire(square)), SkillUsage(), SEED)
    offer = make_offer(lib, request)
    categories = [o.variation.category for o in offer.options]
    assert len(set(categories)) >= 2, categories


def test_focused_offer_costs_two_and_stays_in_its_category() -> None:
    state, _ = _walk(FIRE_BOLT, 2)
    offer = _offer(FIRE_BOLT, state, category="bridge")
    assert offer.cost == 2 and offer.category == "bridge"
    assert 1 <= len(offer.options) <= 4  # 指定類別 3 個 ＋ 轉型保底另列 1 個
    assert all(o.variation.category in ("bridge", "transform") for o in offer.options)
    moved, _skill = choose(state, offer, 0)
    assert moved.spent == state.spent + 2
    with pytest.raises(ValueError, match="不能指定類別"):
        _offer(FIRE_BOLT, state, category="area")  # 第 3 次只能指定加深或橋接
    with pytest.raises(ValueError, match="不能指定類別"):
        _offer(FIRE_BOLT, category="trigger")  # 主動技沒有觸發類


def test_categories_follow_skill_kind() -> None:
    lib = library()
    table = lib.flash
    fire = lib.skills[FIRE_BOLT]
    assert "cost" in allowed_categories(table, fire, major=False)
    assert "trigger" not in allowed_categories(table, fire, major=False)
    assert "support" not in allowed_categories(table, fire, major=False)  # 有傷害，不是輔助技
    passive = next(
        s for s in sorted(lib.skills.values(), key=lambda s: s.id) if s.kind == "passive"
    )
    kinds = allowed_categories(table, passive, major=False)
    assert "trigger" in kinds and "cost" not in kinds and "area" not in kinds
    heal = next(
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active" and is_support_skill(s, lib.flash)
    )
    assert "support" in allowed_categories(table, heal, major=False)


def test_transform_is_guaranteed_on_the_major_flash() -> None:
    state, _ = _walk(FIRE_BOLT, 2)
    open_offer = _offer(FIRE_BOLT, state)
    sources = [o.variation.source for o in open_offer.options]
    assert len(sources) == 4 and sources.count("transform") == 1  # 不指定：佔 4 個之一
    focused = _offer(FIRE_BOLT, state, category="deepen")
    assert [o.variation.source for o in focused.options][-1] == "transform"  # 指定：另列第 4 個
    assert sum(o.variation.source == "major" for o in focused.options) <= 3
    minor = _offer(FIRE_BOLT, _walk(FIRE_BOLT, 1)[0])
    assert all(o.variation.source != "transform" for o in minor.options)  # 小變化沒有轉型
    reflash = _offer(FIRE_BOLT, _walk(FIRE_BOLT, 3)[0], slot=3)
    assert any(o.variation.source == "transform" for o in reflash.options)  # 重閃第 3 次也保底
    transformed = next(o for o in open_offer.options if o.variation.source == "transform")
    assert transformed.skill.name_zh.split("・")[0] in ("餘波", "反擊")  # 1 階只開被動、反應
    assert transformed.skill.kind in ("passive", "reaction")


def test_complete_skill_reflashes_its_adjustment_slot_only() -> None:
    lib = library()
    base = with_budget_bonus(lib.skills[FIRE_BOLT], 120)
    state = acquire(FIRE_BOLT, complete=True)
    assert derive_skill(lib, base, state, SEED) == base
    offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), SEED, slot=COMPLETE_SLOT))
    assert not offer.major and offer.options and offer.reflashes == 0
    after, skill = choose(state, offer, 0)
    assert after.adjustment is not None and after.records == ()
    assert skill.budget_bonus_permille == 120 and after.spent == 1
    again = make_offer(lib, FlashRequest(base, after, SkillUsage(), SEED, slot=COMPLETE_SLOT))
    assert again.reflashes == 1


# ---------------------------------------------------------------------------
# 實戰一致：閃現後的技能進規則包、合法動作、預覽 ＝ 結算
# ---------------------------------------------------------------------------


def test_a_flashed_skill_plays_in_the_engine_as_its_card_says() -> None:
    lib = library()
    _state, skill = _walk(FIRE_BOLT, 1)  # 距離 +1：射程 6
    played = scale_mana_cost(
        skill, lib.ruleset.core.ally_mana_cost_permille
    )  # 規則包內的版本（BAL-4b）
    assert lib.ruleset.with_skills([skill]).skills.by_id()[skill.id] == played
    card = skill_card(lib, skill)
    assert card.id == skill.id
    m = make_map("\n".join(["0000000"] * 7), ally=[(0, 0)], enemy=[(6, 0)])
    spawns = [
        spawn(Team.ALLY, (0, 0), caster_template([skill, lib.skills[FIRE_BOLT]])),
        spawn(Team.ENEMY, (6, 0), no_reactions()),
    ]
    battle = give_turn(make_state(m, spawns, skills=[skill]), "unit_0001")
    casts = [a for a in legal_actions(battle) if isinstance(a, UseSkill)]
    target = UnitId("unit_0002")
    assert any(a.skill_id == skill.id and a.target_id == target for a in casts)
    assert not any(a.skill_id == FIRE_BOLT and a.target_id == target for a in casts)  # 原本射程 5
    action = next(a for a in casts if a.skill_id == skill.id and a.target_id == target)
    seen = preview(battle, action)
    result = resolve(battle, action)
    dealt = [e for e in result.events if isinstance(e, DamageDealt) and e.target_id == target]
    if dealt and seen.damage is not None and not dealt[0].crit:
        assert seen.damage.minimum <= dealt[0].amount <= seen.damage.maximum
