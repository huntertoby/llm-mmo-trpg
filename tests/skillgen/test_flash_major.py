"""Phase 3W-3：大變化與轉型——依角色階級的轉型、保底與種子挑種類、轉型後的小變化、欄位卸下、
輔助類與召喚類的加深／橋接、強度下限、行為一致（卡片數字＝實戰）。"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

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
from trpg.content.skills import SkillDef
from trpg.engine import resolve
from trpg.engine.actions import Attack, Move, UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import (
    DamageDealt,
    ReactionTriggered,
    SkillTriggered,
    SkillUsed,
    StatusApplied,
    TrapPlaced,
    TrapTriggered,
    UnitSummoned,
)
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.shared.types import Pos, Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.flash import (
    DataOrderSource,
    FlashError,
    FlashOffer,
    FlashRequest,
    UsageSource,
    _Builder,
    _replaced_floor,
    apply_variation,
    choose,
    derive_skill,
    is_support_skill,
    make_offer,
    skill_before,
    with_budget_bonus,
)
from trpg.skillgen.flash_major import (
    meets_floor,
    transform_slot_plan,
    transform_variations,
)
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation, acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard

FIRE_BOLT = "skill_fire_bolt"
SEED = 11
RANGE = Variation(source="minor", template="range_plus", category="area")
AREA = Variation(source="minor", template="area_plus", category="area")
PASSIVE = "to_passive_on_hit"
REACTION = "to_reaction_melee"
SUMMON = "to_summon"
TRAP = "to_trap"
STANCE = "to_stance"
MODIFIER = "to_modifier"
ALL_TRANSFORMS = (PASSIVE, REACTION, SUMMON, TRAP, STANCE, MODIFIER)


def _transform(template: str) -> Variation:
    return Variation(source="transform", template=template, category="transform")


def _state(base_id: str, *minors: Variation, transform: str | None = None) -> SkillFlash:
    """第 1、2 次是 ``minors``（最多 2 個），第 3 次是 ``transform``（沒給就不閃第 3 次）。"""
    records = [FlashRecord(nth=i + 1, variation=v) for i, v in enumerate(minors)]
    if transform is not None:
        records.append(FlashRecord(nth=3, variation=_transform(transform)))
    return SkillFlash(base_id=base_id, records=tuple(records), used=True)


def _derived(template: str, *minors: Variation, base_id: str = FIRE_BOLT) -> SkillDef:
    lib = library()
    state = _state(base_id, *minors, transform=template)
    return derive_skill(lib, lib.skills[base_id], state, SEED)


def _board(seed: int, kind: str = "active") -> SkillDef:
    return compose_whiteboard(seed, kind=kind, tier=1, library=library())


# ---------------------------------------------------------------------------
# 資料與階級
# ---------------------------------------------------------------------------


def test_transform_data_matches_decision_73() -> None:
    lib = library()
    table = lib.flash
    tiers = {t.id: (t.to, t.min_tier) for t in table.transforms}
    assert tiers == {
        PASSIVE: ("passive", 1),
        REACTION: ("reaction", 1),
        SUMMON: ("summon", 2),
        TRAP: ("trap", 2),
        STANCE: ("stance", 2),
        MODIFIER: ("modifier", 3),
    }
    units = {u for t in table.transforms for us in t.units.values() for u in us}
    for unit in units:
        assert lib.ruleset.summon_def(unit) is not None
    statuses = lib.ruleset.statuses.by_id()
    for t in table.transforms:
        for status in (s for ids in t.stances.values() for s in ids):
            assert statuses[status].stance
    extra = {t.id: (t.category, t.only) for t in table.extra_major}
    assert extra["support_wide"] == ("deepen", "support")
    assert extra["support_imbue"] == ("bridge", "support")
    assert extra["summon_bridge"] == ("bridge", "summon")


@pytest.mark.parametrize(
    ("tier", "kinds"),
    [
        (1, {"passive", "reaction"}),
        (2, {"passive", "reaction", "summon", "trap", "stance"}),
        (3, {"passive", "reaction", "summon", "trap", "stance", "modifier"}),
    ],
)
def test_transform_kinds_open_by_hero_tier(tier: int, kinds: set[str]) -> None:
    lib = library()
    fire = lib.skills[FIRE_BOLT]
    found = transform_variations(lib, fire, tier=tier, rng=Rng(1))
    opened = {lib.flash.transform_template(v.template).to for v in found}  # type: ignore[union-attr]
    assert opened == kinds
    passive = next(s for s in lib.skills.values() if s.kind == "passive")
    assert transform_variations(lib, passive, tier=3, rng=Rng(1)) == []  # 只有主動技轉型


def test_kind_order_is_seeded_and_covers_every_kind() -> None:
    lib = library()
    fire = lib.skills[FIRE_BOLT]
    first = Counter(
        lib.flash.transform_template(
            transform_variations(lib, fire, tier=3, rng=Rng(s))[0].template
        ).to  # type: ignore[union-attr]
        for s in range(60)
    )
    assert len(first) >= 4  # 種子隨機挑一種：不同種子會挑到不同種類
    again = transform_variations(lib, fire, tier=3, rng=Rng(5))
    assert again == transform_variations(lib, fire, tier=3, rng=Rng(5))
    assert {v.template for v in again} == set(ALL_TRANSFORMS)


# ---------------------------------------------------------------------------
# 每種轉型：預算、驗證、卡片、實戰
# ---------------------------------------------------------------------------


_KIND_OF = {
    PASSIVE: "passive",
    REACTION: "reaction",
    SUMMON: "active",
    TRAP: "active",
    STANCE: "stance",
    MODIFIER: "modifier",
}


@pytest.mark.parametrize("template", ALL_TRANSFORMS)
def test_every_transform_is_valid_and_within_the_budget_window(template: str) -> None:
    lib = library()
    skill = _derived(template)
    assert skill.kind == _KIND_OF[template]
    assert validate_skill(skill, lib) == []
    report = skill_budget(skill, lib)
    assert report.min_ratio <= report.ratio <= report.max_ratio
    assert skill.budget_bonus_permille == 120  # 第 3 次：+120‰
    prefix = lib.flash.transform_template(template).prefix_zh  # type: ignore[union-attr]
    assert skill.name_zh == f"{prefix}・火焰箭"
    assert skill.provenance.parents == (FIRE_BOLT,)
    card = skill_card(lib, skill)
    assert card.id == skill.id and card.name_zh == skill.name_zh
    assert lib.ruleset.with_skills([skill]).skills.by_id()[skill.id] == skill
    for effect in skill.effects:  # 卡片上的骰子＝技能資料的骰子
        if effect.dice is not None:
            assert str(effect.dice) in " ".join(card.effects)


def _dice_count(skill: SkillDef) -> int:
    effect = next(e for e in skill.effects if e.type == "damage")
    assert effect.dice is not None
    match = re.match(r"(\d+)d\d+", str(effect.dice))
    assert match is not None
    return int(match.group(1))


_FLAT = "0000000\n0000000\n0000000\n0000000\n0000000\n0000000\n0000000"


def _battle(skill: SkillDef | None, *, seed: int = 0, enemy_x: int = 1) -> Any:
    """施放者（unit_0001，帶 skill 與火焰箭）在 (0, 0)，敵人（unit_0002）在 (enemy_x, 0)。"""
    lib = library()
    m = make_map(_FLAT, ally=[(0, 0)], enemy=[(enemy_x, 0)])
    carried = [lib.skills[FIRE_BOLT], *([] if skill is None else [skill])]
    spawns = [
        spawn(Team.ALLY, (0, 0), caster_template(carried, max_hp=200)),
        spawn(Team.ENEMY, (enemy_x, 0), no_reactions(max_hp=200)),
    ]
    extra = [] if skill is None else [skill]
    return give_turn(make_state(m, spawns, seed=seed, skills=extra), "unit_0001")


def test_passive_transform_triggers_on_a_hit_with_the_card_dice() -> None:
    skill = _derived(PASSIVE)
    state = _battle(skill)
    result = answered(
        resolve(state, Attack(unit_id=UnitId("unit_0001"), target_id=UnitId("unit_0002")))
    )
    triggered = next(e for e in result.events if isinstance(e, SkillTriggered))
    assert triggered.skill_id == skill.id and triggered.trigger == "on_hit"
    after = result.events[result.events.index(triggered) + 1 :]
    damage = next(e for e in after if isinstance(e, DamageDealt))
    assert len(damage.rolls) == _dice_count(skill)  # 卡片的骰數＝實際擲出的骰數
    assert damage.target_id == UnitId("unit_0002")


def test_reaction_transform_answers_a_melee_hit() -> None:
    skill = _derived(REACTION)
    for seed in range(40):  # 反擊要擲命中：找一個命中的種子
        state = give_turn(_battle(skill, seed=seed), "unit_0002")
        result = answered(
            resolve(state, Attack(unit_id=UnitId("unit_0002"), target_id=UnitId("unit_0001")))
        )
        dealt = [
            e for e in result.events if isinstance(e, DamageDealt) and e.target_id == "unit_0002"
        ]
        if dealt:
            break
    assert any(isinstance(e, ReactionTriggered) for e in result.events)
    assert next(e for e in result.events if isinstance(e, SkillUsed)).skill_id == skill.id
    assert dealt and len(dealt[0].rolls) == _dice_count(skill)


def test_summon_transform_summons_the_unit_of_its_element() -> None:
    skill = _derived(SUMMON)
    state = _battle(skill)
    casts = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == skill.id]
    assert casts
    result = answered(resolve(state, casts[0]))
    summoned = next(e for e in result.events if isinstance(e, UnitSummoned))
    assert summoned.unit_id in result.state.units
    assert skill.effects[0].unit == "summon_fire_spirit"  # 火焰箭是火元素


def test_trap_transform_places_a_trap_that_hits_with_the_card_dice() -> None:
    skill = _derived(TRAP)
    state = _battle(skill, enemy_x=1)
    casts = [
        a
        for a in legal_actions(state)
        if isinstance(a, UseSkill) and a.skill_id == skill.id and a.target_pos == Pos(x=2, y=0)
    ]
    placed = answered(resolve(state, casts[0]))
    assert any(isinstance(e, TrapPlaced) for e in placed.events)
    walk = give_turn(placed.state, "unit_0002")
    path = (Pos(x=1, y=0), Pos(x=2, y=0))
    stepped = answered(resolve(walk, Move(unit_id=UnitId("unit_0002"), path=path)))
    assert any(isinstance(e, TrapTriggered) for e in stepped.events)
    damage = next(e for e in stepped.events if isinstance(e, DamageDealt))
    assert len(damage.rolls) == _dice_count(skill)


def test_stance_transform_enters_its_stance() -> None:
    skill = _derived(STANCE)
    state = _battle(skill)
    casts = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == skill.id]
    result = resolve(state, casts[0])
    applied = [e for e in result.events if isinstance(e, StatusApplied)]
    # 原招是火焰箭：轉成同元素的元素姿態（3W-2b；沒有元素才是狂怒）
    assert [e.status_id for e in applied] == [skill.effects[0].status]
    assert skill.effects[0].status in library().flash.stance_ladders["fire"]
    assert applied[0].target_id == UnitId("unit_0001")


def test_modifier_transform_changes_the_casters_fire_skill() -> None:
    skill = _derived(MODIFIER)
    target = UnitId("unit_0002")

    def cast(state: Any) -> Any:
        acts = [
            a
            for a in legal_actions(state)
            if isinstance(a, UseSkill) and a.skill_id == FIRE_BOLT and a.target_id == target
        ]
        return answered(resolve(state, acts[0]))

    base = cast(_battle(None))
    plus = cast(_battle(skill))
    assert [e.model_dump() for e in base.events] != [e.model_dump() for e in plus.events]


# ---------------------------------------------------------------------------
# 出題：保底、種子、階級
# ---------------------------------------------------------------------------


def _offer(
    base_id: str,
    state: SkillFlash,
    tier: int,
    *,
    category: str | None = None,
    slot: int | None = None,
) -> FlashOffer:
    lib = library()
    request = FlashRequest(
        lib.skills[base_id], state, SkillUsage(), SEED, slot=slot, category=category, tier=tier
    )
    return make_offer(lib, request)


def test_major_offer_always_has_a_legal_transform_and_respects_tier() -> None:
    lib = library()
    state = _state(FIRE_BOLT, RANGE, RANGE)
    allowed = {1: {"passive", "reaction"}, 2: {"passive", "reaction", "summon", "trap", "stance"}}
    allowed[3] = allowed[2] | {"modifier"}
    for tier in (1, 2, 3):
        for category in (None, "deepen", "bridge"):
            offer = _offer(FIRE_BOLT, state, tier, category=category)
            transforms = [o for o in offer.options if o.variation.source == "transform"]
            assert len(transforms) == 1, (tier, category)
            kind = lib.flash.transform_template(transforms[0].variation.template).to  # type: ignore[union-attr]
            assert kind in allowed[tier]
            # 大變化不受階級限制：1 階也有加深與橋接
            cats = {o.variation.category for o in offer.options}
            assert {"deepen", "bridge"} <= cats if category is None else category in cats
    # 重閃第 3 次也保底
    full = _state(FIRE_BOLT, RANGE, RANGE, transform=PASSIVE)
    reflash = _offer(FIRE_BOLT, full, 3, slot=3)
    assert reflash.major and any(o.variation.source == "transform" for o in reflash.options)


def test_open_major_offer_has_at_least_one_deepen_and_one_bridge() -> None:
    lib = library()
    checked = 0
    for seed in range(14):
        board = _board(seed)
        # 白板種類多（3W-4b），不是每張都能 +距離：改用小變化的出題結果走完前 2 次閃現
        state = acquire(board.id)
        minors: list[Variation] = []
        for _ in range(2):
            first = make_offer(lib, FlashRequest(board, state, SkillUsage(), seed)).options[0]
            minors.append(first.variation)
            state = _state(board.id, *minors)
        try:
            derive_skill(lib, board, state, seed, 2)
        except FlashError:
            continue
        request = FlashRequest(board, state, SkillUsage(), seed, tier=2)
        offer = make_offer(lib, request)
        cats = Counter(o.variation.category for o in offer.options)
        # 有些白板（例：純護盾）沒有任何合法的加深或橋接：能做到的類別才要求各出現
        before = skill_before(lib, request)
        builder = _Builder(lib, request, _replaced_floor(lib, request))
        feasible = {
            c
            for c in ("deepen", "bridge")
            if any(builder.option(v) for v in UsageSource().ranked(lib, request, c, before))
        }
        assert cats["transform"] == 1 and len(offer.options) >= 3, cats
        assert all(cats[c] >= 1 for c in feasible), (feasible, cats)
        if len(feasible) == 2:
            assert len(offer.options) == 4
            checked += 1
    assert checked >= 4


def test_transform_choice_is_deterministic_and_round_trips() -> None:
    state = _state(FIRE_BOLT, RANGE, RANGE)
    first = _offer(FIRE_BOLT, state, 3)
    assert _offer(FIRE_BOLT, state, 3) == first
    assert FlashOffer.model_validate_json(first.model_dump_json()) == first
    index = next(i for i, o in enumerate(first.options) if o.variation.source == "transform")
    moved, skill = choose(state, first, index)
    lib = library()
    assert derive_skill(lib, lib.skills[FIRE_BOLT], moved, SEED, 3) == skill
    picks: Counter[str] = Counter()
    for seed in range(30):
        request = FlashRequest(lib.skills[FIRE_BOLT], state, SkillUsage(), seed, tier=3)
        offer = make_offer(lib, request)
        picks[
            next(o for o in offer.options if o.variation.source == "transform").variation.template
        ] += 1
    assert len(picks) >= 3  # 可轉的種類多時，由種子挑不同種類


# ---------------------------------------------------------------------------
# 轉型後的小變化：合法的保留、不合法的換同類別、預算重算
# ---------------------------------------------------------------------------


def _cone_skill() -> str:
    lib = library()
    return next(
        s.id
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active"
        and s.tier == 1
        and s.shape.type in ("cone", "line")
        and s.followup is None
        and s.trap is None
        and any(e.type == "damage" and e.affects in (None, "enemies") for e in s.effects)
        and apply_variation(lib, s, _transform(SUMMON), bonus=120, rng=Rng(1)) is not None
        and apply_variation(lib, s, _transform(PASSIVE), bonus=120, rng=Rng(1)) is not None
        and apply_variation(lib, s, AREA, bonus=40, rng=Rng(1)) is not None
    )


def test_legal_minors_are_kept_and_illegal_ones_swap_to_the_same_category() -> None:
    lib = library()
    plain = _derived(SUMMON)
    assert plain.shape.range == 4
    kept = _derived(SUMMON, RANGE)  # 距離 +1 對召喚（地面格）照用
    assert kept.shape.range == 5
    cone = _cone_skill()
    swapped = _derived(SUMMON, AREA, base_id=cone)  # 範圍 +1 對召喚不合法 → 換同類別的距離 +1
    assert swapped.shape.range == 5
    passive = _derived(PASSIVE, AREA, base_id=cone)  # 被動沒有形狀：兩種範圍變化都不合法 → 省略
    assert passive.kind == "passive" and passive.shape.type == "self"
    for done in (kept, swapped, passive):
        assert validate_skill(done, lib) == []
        assert done.budget_bonus_permille == 120  # 預算照新種類重算，加成與轉型同次


def test_later_minors_apply_on_the_new_kind() -> None:
    lib = library()
    base = lib.skills[FIRE_BOLT]
    records = [
        FlashRecord(nth=1, variation=RANGE),
        FlashRecord(nth=2, variation=RANGE),
        FlashRecord(nth=3, variation=_transform(SUMMON)),
    ]
    skill = derive_skill(lib, base, SkillFlash(base_id=FIRE_BOLT, records=tuple(records)), SEED)
    assert skill.kind == "active" and skill.shape.range == 6  # 4 ＋ 兩次距離（地面格上限 6）
    # 第 4 次再加距離：新種類已經到上限 → 這個變化套不上（出題時不會出現）
    full = SkillFlash(
        base_id=FIRE_BOLT,
        records=(*records, FlashRecord(nth=4, variation=RANGE)),
    )
    with pytest.raises(FlashError):
        derive_skill(lib, base, full, SEED)
    assert validate_skill(skill, lib) == []


def test_reflashing_a_minor_slot_keeps_the_transform() -> None:
    lib = library()
    state = _state(FIRE_BOLT, RANGE, RANGE, transform=SUMMON)
    offer = _offer(FIRE_BOLT, state, 3, slot=1)
    assert offer.options
    after, skill = choose(state, offer, 0)
    assert skill.name_zh.startswith("靈召・") and skill.kind == "active"
    assert derive_skill(lib, lib.skills[FIRE_BOLT], after, SEED, 3) == skill


# ---------------------------------------------------------------------------
# 欄位
# ---------------------------------------------------------------------------


def test_slot_plan_reports_which_skills_must_be_unequipped() -> None:
    lib = library()
    slots = lib.ruleset.core.skill_slots
    fire = lib.skills[FIRE_BOLT]
    actives = [s for s in sorted(lib.skills.values(), key=lambda s: s.id) if s.kind == "active"]
    others = [s for s in actives if s.id != FIRE_BOLT][:5]
    passives = [
        s for s in sorted(lib.skills.values(), key=lambda s: s.id) if s.slot_kind == "passive"
    ]
    stances = [s for s in lib.skills.values() if s.kind == "stance" and s.form_id is None]

    summon = _derived(SUMMON)  # 主動欄 → 主動欄：原地換，不用卸下
    plan = transform_slot_plan([fire, *others], FIRE_BOLT, summon, slots)
    assert not plan.changes_slot and not plan.needs_unequip

    passive = _derived(PASSIVE)  # 主動欄 → 被動欄
    free = transform_slot_plan([fire, *passives[: slots.passive - 1]], FIRE_BOLT, passive, slots)
    assert free.changes_slot and not free.needs_unequip and free.occupied == slots.passive - 1
    full = transform_slot_plan([fire, *passives[: slots.passive]], FIRE_BOLT, passive, slots)
    assert full.needs_unequip and full.must_unequip == 1
    assert set(full.candidates) == {s.id for s in passives[: slots.passive]}

    modifier = _derived(MODIFIER)  # 修正型被動佔被動欄
    assert modifier.slot_kind == "passive"
    assert transform_slot_plan(
        [fire, *passives[: slots.passive]], FIRE_BOLT, modifier, slots
    ).needs_unequip

    stance = _derived(STANCE)
    crowded = transform_slot_plan([fire, stances[0]], FIRE_BOLT, stance, slots)
    assert crowded.new_slot == "stance" and crowded.must_unequip == 1
    assert crowded.candidates == (stances[0].id,)

    reaction = _derived(REACTION)
    held = [s for s in lib.skills.values() if s.kind == "reaction"][:1]
    assert transform_slot_plan([fire, *held], FIRE_BOLT, reaction, slots).must_unequip == 1


# ---------------------------------------------------------------------------
# 輔助類與召喚類的大變化、強度下限
# ---------------------------------------------------------------------------


def _supports() -> list[SkillDef]:
    lib = library()
    return [
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active" and is_support_skill(s)
    ]


def test_support_skills_get_deepen_and_bridge_templates() -> None:
    lib = library()
    source = DataOrderSource()
    both = 0
    per_side: Counter[str] = Counter()
    seen: set[str] = set()
    supports = _supports()
    assert len(supports) >= 10
    for skill in supports:
        request = FlashRequest(skill, acquire(skill.id), SkillUsage(), SEED)
        found = {}
        for category in ("deepen", "bridge"):
            for variation in source.ranked(lib, request, category, skill):
                done = apply_variation(lib, skill, variation, bonus=120, rng=Rng(1))
                if done is not None:
                    assert validate_skill(done, lib) == []
                    assert meets_floor(skill, done, lib)  # 強度下限
                    assert done.budget_bonus_permille == 120
                    found[category] = variation
                    per_side[category] += 1
                    seen.add(variation.template)
                    break
        both += len(found) == 2
    assert per_side["deepen"] >= len(supports) - 4 and per_side["bridge"] >= len(supports) - 4
    assert both >= len(supports) - 6  # 多數輔助技兩邊都有（原本約 3 成沒有任何進化）
    assert "support_imbue" in seen
    wide = Variation(source="major", template="support_wide", category="deepen")
    assert (
        apply_variation(lib, lib.skills["skill_sanctuary"], wide, bonus=120, rng=Rng(1)) is not None
    )


def test_summon_skills_use_the_summon_evolutions() -> None:
    lib = library()
    spirit = lib.skills["skill_summon_fire_spirit"]
    source = DataOrderSource()
    request = FlashRequest(spirit, acquire(spirit.id), SkillUsage(), SEED)
    templates: set[str] = set()
    for category in ("deepen", "bridge"):
        for variation in source.ranked(lib, request, category, spirit):
            done = apply_variation(lib, spirit, variation, bonus=120, rng=Rng(1))
            if done is not None:
                assert validate_skill(done, lib) == []
                templates.add(variation.template)
    assert templates & {"summon_deepen", "summon_count"}
    assert "summon_bridge" in templates


def test_major_results_never_fall_below_the_budget_score_before() -> None:
    lib = library()
    source = DataOrderSource()
    checked = 0
    for seed in range(15):
        board = _board(seed)
        request = FlashRequest(board, acquire(board.id), SkillUsage(), seed)
        before = skill_budget(board, lib).total
        for category in ("deepen", "bridge"):
            for variation in source.ranked(lib, request, category, board):
                done = apply_variation(lib, board, variation, bonus=120, rng=Rng(seed))
                if done is not None:
                    assert skill_budget(done, lib).total >= before
                    # 召喚類模板會自己加前綴（強化・、雙生・…）；其餘沿用原名
                    assert done.name_zh == board.name_zh or done.name_zh.endswith(
                        f"・{board.name_zh}"
                    )
                    checked += 1
    assert checked >= 20


def test_major_names_use_prefix_and_original_name() -> None:
    state = _state(FIRE_BOLT, RANGE, RANGE)
    offer = _offer(FIRE_BOLT, state, 3)
    for option in offer.options:
        assert option.skill.name_zh.endswith("・火焰箭")
        assert option.summary_zh


# ---------------------------------------------------------------------------
# 白板（1 階）的轉型覆蓋
# ---------------------------------------------------------------------------


def test_whiteboards_can_transform_into_every_kind() -> None:
    lib = library()
    ok: Counter[str] = Counter()
    total = 0
    for seed in range(20):
        board = _board(seed)
        total += 1
        for template in ALL_TRANSFORMS:
            if apply_variation(lib, board, _transform(template), bonus=120, rng=Rng(seed)):
                ok[template] += 1
    # 3W-4b 後白板種類多（治療、輔助等不適合每種轉型）：每種轉型都要有白板可達，
    # 且每張白板至少有一種合法轉型（出題保底靠這點）。
    assert all(ok[t] >= total * 0.2 for t in ALL_TRANSFORMS), ok
    for seed in range(20):
        board = _board(seed)
        assert any(
            apply_variation(lib, board, _transform(t), bonus=120, rng=Rng(seed))
            for t in ALL_TRANSFORMS
        ), seed


def test_support_skill_transforms_to_a_defensive_stance_only() -> None:
    lib = library()
    heal = next(
        s for s in _supports() if apply_variation(lib, s, _transform(STANCE), bonus=120, rng=Rng(1))
    )
    stance = apply_variation(
        lib, with_budget_bonus(heal, 120), _transform(STANCE), bonus=120, rng=Rng(1)
    )
    assert stance is not None
    assert stance.effects[0].status in {
        "stance_bulwark",
        "stance_guard",
        "stance_ironwall",
        "stance_bastion",
    }
    assert apply_variation(lib, heal, _transform(PASSIVE), bonus=120, rng=Rng(1)) is None
