"""BAL-10b：閃現小變化模板補充（第 1 段：複合技、修正型被動、姿態與變身；06 6.34.3、6.34.4）。

每個新模板／放寬都檢查：結果合法（含 6.6 硬上限）、預算比例在窗內、強度下限（6.34.3：不低於閃現前，
結構不變的強化嚴格變強）、只動該動的欄位、卡片的數字＝實戰。技能都由資料挑（不寫死在程式裡），
內容裡沒有的結構用測試夾具補。
"""

from __future__ import annotations

from functools import cache

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
from trpg.content.flash_templates import FlashRules
from trpg.content.skills import EffectSpec, ModifierSpec, SkillDef
from trpg.engine import modifiers as mods
from trpg.engine import resolve
from trpg.engine.actions import UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import DamageDealt
from trpg.engine.skills.conditions import Subject
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import apply_variation, at_role_tier, at_tier
from trpg.skillgen.flash_offer import FlashRequest, choose, make_offer
from trpg.skillgen.flash_ops import FLASH_OPS
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

BONUS = 40
SEED = 11
NEW_TEMPLATES = {
    "followup_potency": "combo",
    "followup_area": "area",
    "followup_range": "area",
    "followup_element": "element",
    "mod_duration": "modifier",
    "mod_stack": "modifier",
    "mod_cooldown": "modifier",
    "mod_cost": "modifier",
    "stance_enter_light": "cost",
}


def _var(template: str, element: str | None = None) -> Variation:
    category = NEW_TEMPLATES.get(template) or library().flash.minor_template(template).category  # type: ignore[union-attr]
    return Variation(source="minor", template=template, category=category, element=element)


def _apply(skill: SkillDef, template: str, element: str | None = None) -> SkillDef | None:
    return apply_variation(library(), skill, _var(template, element), bonus=BONUS, rng=Rng(SEED))


def _sound(before: SkillDef, got: SkillDef, *, strict: bool = False) -> None:
    """合法、比例在窗內、強度下限（結構不變的強化要嚴格變強）。"""
    lib = library()
    assert validate_skill(got, lib) == [], got.id
    report = skill_budget(got, lib)
    assert report.ok, (got.id, float(report.ratio))
    assert report.min_ratio <= report.ratio <= report.max_ratio
    assert report.bonus_permille == BONUS
    if strict:
        assert budget_power(got, lib) > budget_power(before, lib), got.id
    else:
        assert budget_power(got, lib) >= budget_power(before, lib), got.id
    assert (got.kind, got.tier) == (before.kind, before.tier)


def _renamed(skill: SkillDef) -> SkillDef:
    return skill.model_copy(update={"id": f"{skill.id}_fl_test"})


# ---------------------------------------------------------------------------
# 登錄
# ---------------------------------------------------------------------------


def test_new_templates_are_in_the_data_with_existing_categories() -> None:
    table = library().flash
    for template_id, category in NEW_TEMPLATES.items():
        template = table.minor_template(template_id)
        assert template is not None, template_id
        assert template.category == category  # 6.34.4 既有類別，不新增類別
        assert template.op in FLASH_OPS
    assert {c.id for c in table.categories} == {
        "area",
        "combo",
        "element",
        "cost",
        "extend",
        "support",
        "trigger",
        "modifier",
        "deepen",
        "bridge",
    }


def test_form_upkeep_can_never_be_a_flash_knob() -> None:
    """#67：形態維持費固定（化形專精減半），不能當修正模板的旋鈕。"""
    assert "form_upkeep_permille" not in library().flash.rules.modifier_knobs
    with pytest.raises(ValueError, match="form_upkeep_permille"):
        FlashRules.model_validate({"modifier_knobs": {"form_upkeep_permille": [-100, -200]}})


# ---------------------------------------------------------------------------
# 1 複合技：接續段強化
# ---------------------------------------------------------------------------


def _compounds() -> list[str]:
    """內建的複合技（有接續段、不是陷阱）。"""
    return sorted(
        s.id
        for s in library().skills.values()
        if s.kind == "active" and s.followup is not None and s.trap is None
    )


def _damaging_compounds() -> list[str]:
    lib = library()
    return [
        i
        for i in _compounds()
        if any(e.type == "damage" for e in lib.skills[i].followup.effects)  # type: ignore[union-attr]
    ]


def _strength(effect: EffectSpec) -> float:
    if effect.dice is not None:
        return effect.dice.count * (effect.dice.sides + 1) / 2
    return float(effect.multiplier_permille or 0)


def test_there_are_compound_skills_to_test() -> None:
    assert len(_damaging_compounds()) >= 6


@pytest.mark.parametrize("skill_id", _damaging_compounds())
def test_followup_potency_only_raises_the_followup(skill_id: str) -> None:
    lib = library()
    base = lib.skills[skill_id]
    for tier in sorted({base.tier, 3}):
        before = at_role_tier(lib, base, tier)
        got = _apply(before, "followup_potency")
        assert got is not None, (skill_id, tier)
        _sound(before, got, strict=True)
        assert got.shape == before.shape  # 第一段形狀不動
        assert [e.type for e in got.effects] == [e.type for e in before.effects]
        assert got.followup is not None and before.followup is not None
        assert got.followup.shape == before.followup.shape
        old = [_strength(e) for e in before.followup.effects if e.type == "damage"]
        new = [_strength(e) for e in got.followup.effects if e.type == "damage"]
        assert all(n >= o for n, o in zip(new, old, strict=True))  # 接續段只往上調
        assert sum(new) > sum(old)


def test_followup_area_and_range_grow_only_the_followup_shape() -> None:
    lib = library()
    grown = {"followup_area": 0, "followup_range": 0}
    for skill_id in _compounds():
        base = lib.skills[skill_id]
        for template in grown:
            before = at_role_tier(lib, base, base.tier)
            got = _apply(before, template)
            if got is None:
                continue
            grown[template] += 1
            _sound(before, got)
            assert got.shape == before.shape
            assert got.followup is not None and before.followup is not None
            old, new = before.followup.shape, got.followup.shape
            if template == "followup_range":
                assert new.range == old.range + 1  # type: ignore[operator]
            else:
                assert (new.size or new.radius or 0) == (old.size or old.radius or 0) + 1
    assert grown["followup_area"] >= 2 and grown["followup_range"] >= 2, grown


def test_followup_element_adds_a_second_element_to_the_followup() -> None:
    lib = library()
    added = 0
    for skill_id in _damaging_compounds():
        before = at_role_tier(lib, lib.skills[skill_id], 3)
        assert before.followup is not None
        own = {e.element for e in (*before.effects, *before.followup.effects) if e.element}
        element = next(e for e in ("ice", "holy", "poison") if e not in {o.value for o in own})
        got = _apply(before, "followup_element", element)
        if got is None:
            continue
        added += 1
        _sound(before, got)
        assert got.followup is not None
        assert len(got.followup.effects) == len(before.followup.effects) + 1
        assert any(
            e.element is not None and e.element.value == element for e in got.followup.effects
        )
        assert [e.type for e in got.effects] == [e.type for e in before.effects]  # 第一段只重調數值
    assert added >= 2


def test_followup_element_needs_role_tier_two() -> None:
    lib = library()
    for skill_id in _damaging_compounds():
        skill = lib.skills[skill_id]
        if skill.tier == 1:
            assert _apply(at_role_tier(lib, skill, 1), "followup_element", "ice") is None


@pytest.mark.parametrize("skill_id", _compounds())
def test_compound_skills_have_two_options_at_their_lowest_tier(skill_id: str) -> None:
    """目標（BAL-10b）：複合技在最低階級第 1 次 ≥ 2 個選項；第 2 次每個分支至少還有選項。"""
    lib = library()
    base = lib.skills[skill_id]
    for seed in (1, 2):
        state = acquire(base.id)
        offer = make_offer(lib, FlashRequest(base, state, SkillUsage(), seed, tier=base.tier))
        assert len(offer.options) >= 2, (skill_id, seed)
        for index in range(len(offer.options)):
            picked, _ = choose(state, offer, index)
            second = make_offer(lib, FlashRequest(base, picked, SkillUsage(), seed, tier=base.tier))
            assert second.options, (skill_id, seed, index)


@cache
def _flashed_armor_break() -> SkillDef:
    lib = library()
    base = lib.skills["skill_armor_break_combo"]
    got = _apply(at_role_tier(lib, base, base.tier), "followup_potency")
    assert got is not None
    return _renamed(got)


def test_flashed_followup_card_shows_the_engine_numbers() -> None:
    """卡片的接續段數字就是技能定義（引擎結算用的同一份）；結算時接續段真的打出傷害。"""
    lib = library()
    skill = _flashed_armor_break()
    assert skill.followup is not None
    damage = next(e for e in skill.followup.effects if e.type == "damage")
    assert damage.dice is not None
    card = skill_card(lib, skill)
    assert card.followup is not None and f"{damage.dice.count}d{damage.dice.sides}" in card.followup
    m = make_map("\n".join(["00000"] * 5), ally=[(0, 2)], enemy=[(1, 2)])
    spawns = [
        spawn(Team.ALLY, (0, 2), caster_template([skill])),
        spawn(Team.ENEMY, (1, 2), no_reactions()),
    ]
    hits = 0
    for seed in range(40):
        battle = give_turn(make_state(m, spawns, skills=[skill], seed=seed), "unit_0001")
        battle.units[UnitId("unit_0002")].max_hp = battle.units[UnitId("unit_0002")].hp = 999
        action = next(
            a
            for a in legal_actions(battle)
            if isinstance(a, UseSkill) and a.skill_id == skill.id and a.target_id == "unit_0002"
        )
        result = answered(resolve(battle, action))
        dealt = [
            e
            for e in result.events
            if isinstance(e, DamageDealt) and e.source_id == "unit_0001" and not e.crit
        ]
        if len(dealt) >= 2:  # 第一段命中 → 接續段（錐形，同一個目標）
            hits += 1
            follow = dealt[-1]
            assert len(follow.rolls) == damage.dice.count
            assert all(1 <= r <= damage.dice.sides for r in follow.rolls)
    assert hits > 0


# ---------------------------------------------------------------------------
# 2 修正型被動
# ---------------------------------------------------------------------------


def _modifiers() -> list[SkillDef]:
    return sorted(
        (s for s in library().skills.values() if s.kind == "modifier"), key=lambda s: s.id
    )


def _no_damage_heal(skill: SkillDef) -> bool:
    return not any(
        (getattr(m.change, n) or 0) > 0
        for m in skill.modifiers
        for n in ("damage_permille", "heal_permille")
    )


def test_mod_potency_now_works_without_damage_or_heal_magnitudes() -> None:
    """放寬：沒有傷害、治療幅度的修正（召喚物、形態進入獎勵、命中後骰子……）也能出強效，有條件、
    沒條件都可以；形態維持費（#67）不動。"""
    lib = library()
    done = 0
    for skill in _modifiers():
        if not _no_damage_heal(skill):
            continue
        before = at_role_tier(lib, skill, skill.tier)
        got = _apply(before, "mod_potency")
        if got is None:
            continue
        done += 1
        _sound(before, got, strict=True)
        old = {m.change.kind: m.change.form_upkeep_permille for m in before.modifiers}
        new = {m.change.kind: m.change.form_upkeep_permille for m in got.modifiers}
        assert new.get("form_upkeep_permille") == old.get("form_upkeep_permille")
    assert done >= 3


def test_unconditioned_modifiers_still_skip_relax_and_second_keyword() -> None:
    """玩法 PM（BAL-2）：沒有條件的修正型被動不出「條件放寬」「第二個關鍵字」。"""
    lib = library()
    for skill in _modifiers():
        if any(m.condition is not None for m in skill.modifiers):
            continue
        for template_id in ("mod_relax", "mod_keyword"):
            template = lib.flash.minor_template(template_id)
            assert template is not None
            variation = Variation(
                source="minor", template=template_id, category="modifier", keyword="wet"
            )
            assert FLASH_OPS[template.op](skill, template, variation, lib) == []


def test_mod_duration_adds_one_round() -> None:
    lib = library()
    done = 0
    for skill in _modifiers():
        for tier in range(skill.tier, 4):
            before = at_role_tier(lib, skill, tier)
            got = _apply(before, "mod_duration")
            if got is None:
                continue
            done += 1
            _sound(before, got)

            def rounds(s: SkillDef) -> int:
                total = 0
                for m in s.modifiers:
                    total += m.change.summon_duration_delta or 0
                    total += sum(e.duration or 0 for e in m.change.on_hit_effects or ())
                return total

            assert rounds(got) == rounds(before) + 1
    assert done >= 1


def _engine_damage_permille(skill: SkillDef) -> int:
    """裝著這招（只有它，主動技能欄全空）的施放者普攻打敵人的傷害倍率（‰，引擎算的）。"""
    m = make_map("000\n000", ally=[(0, 0)], enemy=[(1, 0)])
    spawns = [spawn(Team.ALLY, (0, 0), caster_template([skill])), spawn(Team.ENEMY, (1, 0))]
    state = give_turn(make_state(m, spawns, skills=[skill]), "unit_0001")
    unit, foe = state.units[UnitId("unit_0001")], state.units[UnitId("unit_0002")]
    return mods.damage_permille(state, unit, mods.ATTACK, Subject(foe, foe.xy))


def test_mod_stack_counts_one_more_slot_and_the_engine_agrees() -> None:
    lib = library()
    done = 0
    for skill in _modifiers():
        if not any(m.empty_slots_cap for m in skill.modifiers):
            continue
        for tier in range(skill.tier, 4):
            before = at_role_tier(lib, skill, tier)
            got = _apply(before, "mod_stack")
            if got is None:
                continue
            done += 1
            _sound(before, got)
            rule = next(m for m in got.modifiers if m.empty_slots_cap)
            old = next(m for m in before.modifiers if m.empty_slots_cap)
            assert rule.empty_slots_cap == (old.empty_slots_cap or 0) + 1
            card = " ".join(skill_card(lib, got).modifiers)
            assert f"最多 {rule.empty_slots_cap} 格" in card
            empty = lib.ruleset.core.skill_slots.active
            per = rule.change.damage_permille or 0
            expected = 1000 + per * min(empty, rule.empty_slots_cap or 0)
            assert _engine_damage_permille(_renamed(got)) == expected  # 卡片＝實戰
    assert done >= 1


def _paired_ember() -> SkillDef:
    """夾具：命中後冷卻 −1（燃燒中）＋一條火焰技能的傷害加成。"""
    ember = library().skills["skill_ember_cycle"]
    condition = ember.modifiers[0].condition
    rules = (
        ModifierSpec.model_validate(
            {
                "applies_to": {"skill_tags": ["fire"]},
                "condition": None
                if condition is None
                else condition.model_dump(mode="json", exclude_none=True),
                "change": {"cooldown_delta": -1},
            }
        ),
        ModifierSpec.model_validate(
            {"applies_to": {"skill_tags": ["fire"]}, "change": {"damage_permille": 200}}
        ),
    )
    return ember.model_copy(update={"id": "skill_ember_cycle_paired_test", "modifiers": rules})


def test_mod_cooldown_deepens_the_cooldown_cut() -> None:
    lib = library()
    done = 0
    for tier in (1, 2, 3):
        before = at_tier(_paired_ember(), tier)
        got = _apply(before, "mod_cooldown")
        if got is None:
            continue
        done += 1
        _sound(before, got)
        assert got.modifiers[0].change.cooldown_delta == -2
        assert "冷卻 -2 回合" in " ".join(skill_card(lib, got).modifiers)
    assert done >= 2


def test_mod_cost_lightens_a_drawback_and_keeps_form_upkeep() -> None:
    lib = library()
    done = 0
    for skill in _modifiers():
        before = at_role_tier(lib, skill, 3)
        got = _apply(before, "mod_cost")
        if got is None:
            continue
        done += 1
        _sound(before, got)

        def drawback(s: SkillDef) -> int:
            total = 0
            for m in s.modifiers:
                c = m.change
                total += min(c.damage_permille or 0, 0) + min(c.heal_permille or 0, 0)
                total += min(c.hit_bonus or 0, 0) * 10
            return total

        assert drawback(got) > drawback(before)  # 代價變輕
        upkeep = [
            m.change.form_upkeep_permille for m in before.modifiers if m.change.form_upkeep_permille
        ]
        assert [
            m.change.form_upkeep_permille for m in got.modifiers if m.change.form_upkeep_permille
        ] == upkeep
    assert done >= 1


def _with_drawback(skill_id: str, drawback: dict[str, int]) -> SkillDef:
    """夾具：內建修正型被動加上一條代價規則，以及一條正向規則（讓其他幅度有地方調）。"""
    base = library().skills[skill_id]
    rule = ModifierSpec.model_validate(
        {
            "applies_to": {"skill_tags": ["push"]},
            "change": drawback,
        }
    )
    return base.model_copy(
        update={"id": f"{skill_id}_drawback_test", "modifiers": (*base.modifiers, rule)}
    )


@pytest.mark.parametrize("skill_id", ["skill_heavy_stomp", "skill_summon_elite"])
def test_mod_cost_never_removes_a_one_step_drawback(skill_id: str) -> None:
    """BAL-10c：AP +1、召喚上限 −1、射程 −1 這類只有 1 格的代價，減了就消失，所以不出。"""
    lib = library()
    base = lib.skills[skill_id]
    template = lib.flash.minor_template("mod_cost")
    assert template is not None
    for tier in (1, 2, 3):
        before = at_role_tier(lib, base, tier)
        drafts = FLASH_OPS[template.op](before, template, _var("mod_cost"), lib)
        assert drafts == [], (skill_id, tier)
        assert _apply(before, "mod_cost") is None


def test_mod_cost_keeps_at_least_one_step_of_a_multi_step_drawback() -> None:
    """有 2 格以上的代價照出，而且最少留 1 格（不歸 0、不拿掉那條規則）。"""
    lib = library()
    template = lib.flash.minor_template("mod_cost")
    assert template is not None
    step = lib.flash.rules.modifier_drawback_step
    skill = _with_drawback("skill_heavy_stomp", {"damage_permille": -2 * step})
    drafts = FLASH_OPS[template.op](skill, template, _var("mod_cost"), lib)
    assert len(drafts) == 1
    base, _ = drafts[0]
    assert len(base["modifiers"]) == len(skill.modifiers)
    assert base["modifiers"][-1]["change"]["damage_permille"] == -step
    one_step = _with_drawback("skill_heavy_stomp", {"damage_permille": -step})
    assert FLASH_OPS[template.op](one_step, template, _var("mod_cost"), lib) == []
    two_hits = _with_drawback("skill_heavy_stomp", {"hit_bonus": -2})
    drafts = FLASH_OPS[template.op](two_hits, template, _var("mod_cost"), lib)
    assert [d[0]["modifiers"][-1]["change"]["hit_bonus"] for d in drafts] == [-1]
    one_hit = _with_drawback("skill_heavy_stomp", {"hit_bonus": -1})
    assert FLASH_OPS[template.op](one_hit, template, _var("mod_cost"), lib) == []


# ---------------------------------------------------------------------------
# 3 姿態與變身
# ---------------------------------------------------------------------------


def _forms() -> list[str]:
    return sorted(s.id for s in library().skills.values() if s.form_id is not None)


@pytest.mark.parametrize("skill_id", _forms())
def test_forms_offer_only_the_modifier_category(skill_id: str) -> None:
    """變身姿態不出費用類（BAL-10c，回到 BAL-2c）：輕巧、蓄力都不出，修正類照出。"""
    lib = library()
    base = lib.skills[skill_id]
    for tier in sorted({base.tier, 3}):
        before = at_role_tier(lib, base, tier)
        assert _apply(before, "stance_cost_heavy") is None, (skill_id, tier)
        assert _apply(before, "stance_cost_light") is None, (skill_id, tier)
        got = _apply(before, "stance_potency")
        assert got is not None, (skill_id, tier)
        assert got.stance_upkeep == before.stance_upkeep == 0
        assert got.cost == before.cost
        assert got.form_magnitude > before.form_magnitude


def _cooled_bear() -> SkillDef:
    bear = library().skills["skill_form_bear"]
    form = bear.effects[0].model_copy(update={"magnitude_permille": 1400})
    return bear.model_copy(
        update={
            "id": "skill_form_bear_cooled_test",
            "cost": bear.cost.model_copy(update={"cooldown": 2}),
            "effects": (form,),
        }
    )


def test_enter_light_only_cuts_the_casting_cost() -> None:
    """進入代價 −1：只減施放費用（冷卻），姿態本體與維持費都不動。"""
    for tier in (2, 3):
        before = at_tier(_cooled_bear(), tier)
        got = _apply(before, "stance_enter_light")
        assert got is not None, tier
        _sound(before, got)
        assert got.cost.cooldown == 1
        assert got.effects == before.effects
        assert got.stance_upkeep == before.stance_upkeep


@pytest.mark.parametrize("field", ["mana", "stamina"])
def test_enter_light_cuts_mana_or_stamina_but_keeps_one(field: str) -> None:
    """BAL-10c：進入代價 −1 也能減進入時的法力、耐力；最少留 1，維持費不動。"""
    lib = library()
    fury = lib.skills["skill_fury_stance"]
    template = lib.flash.minor_template("stance_enter_light")
    assert template is not None and field in template.cost_fields
    paid = fury.model_copy(
        update={"id": f"fury_{field}_test", "cost": fury.cost.model_copy(update={field: 3})}
    )
    drafts = FLASH_OPS[template.op](paid, template, _var("stance_enter_light"), lib)
    assert [d[0]["cost"][field] for d in drafts] == [2]
    assert all(d[0]["stance_upkeep"] == paid.stance_upkeep for d in drafts)
    one = fury.model_copy(
        update={"id": f"fury_{field}_one_test", "cost": fury.cost.model_copy(update={field: 1})}
    )
    assert FLASH_OPS[template.op](one, template, _var("stance_enter_light"), lib) == []
    for tier in (1, 2, 3):
        before = at_tier(paid, tier)
        got = _apply(before, "stance_enter_light")
        if got is None:
            continue
        _sound(before, got)
        assert getattr(got.cost, field) == 2
        assert got.stance_upkeep == before.stance_upkeep and got.effects == before.effects
        skill = _renamed(got)
        assert str(getattr(skill.cost, field)) in " ".join(skill_card(lib, skill).cost)


def test_enter_light_is_not_offered_without_an_entry_cost() -> None:
    lib = library()
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        if skill.kind == "stance" and skill.cost.cooldown is None:
            assert _apply(skill, "stance_enter_light") is None, skill.id


def test_enter_light_never_touches_a_stance_upkeep() -> None:
    lib = library()
    fury = lib.skills["skill_fury_stance"]
    paid = fury.model_copy(
        update={
            "id": "skill_fury_paid_test",
            "stance_upkeep": 1,
            "cost": fury.cost.model_copy(update={"cooldown": 1}),
        }
    )
    template = lib.flash.minor_template("stance_enter_light")
    assert template is not None
    drafts = FLASH_OPS[template.op](paid, template, _var("stance_enter_light"), lib)
    assert drafts
    for base, effects in drafts:
        assert base["stance_upkeep"] == 1
        assert base["cost"]["cooldown"] is None
        assert effects == [e.model_dump(mode="json", exclude_none=True) for e in paid.effects]


def test_multi_effect_stance_only_changes_its_stance_effect() -> None:
    """多效果姿態（姿態本體 ＋ 其他效果）：姿態類模板只動姿態本體那個效果。"""
    lib = library()
    fury = lib.skills["skill_fury_stance"]
    extra = EffectSpec.model_validate(
        {"type": "apply_status", "affects": "self", "status": "regenerating", "duration": 2}
    )
    multi = fury.model_copy(
        update={"id": "skill_fury_multi_test", "effects": (*fury.effects, extra)}
    )
    multi = SkillDef.model_validate(multi.model_dump(mode="json"))
    changed = 0
    for template_id in ("stance_cost_heavy", "stance_potency"):
        template = lib.flash.minor_template(template_id)
        assert template is not None
        drafts = FLASH_OPS[template.op](multi, template, _var(template_id), lib)
        assert drafts, template_id
        for _, effects in drafts:
            assert effects[1] == extra.model_dump(mode="json", exclude_none=True)
            assert effects[0]["magnitude_permille"] > 1000
            changed += 1
    assert changed


def test_flashed_form_entry_cooldown_is_the_engine_cooldown() -> None:
    """卡片的進入冷卻＝引擎：進入形態後這招的冷卻就是卡片上的回合數；維持費照形態種類（#67）。"""
    lib = library()
    got = _apply(at_tier(_cooled_bear(), 2), "stance_potency")
    assert got is not None and got.cost.cooldown == 2
    skill = _renamed(got)
    card = skill_card(lib, skill)
    assert f"冷卻 {skill.cost.cooldown} 回合" in card.cost
    assert "−8 耐力" in " ".join(card.effects)  # 物理形態維持費 8（#67）不變
    m = make_map("000\n000", ally=[(0, 0)], enemy=[(2, 1)])
    spawns = [spawn(Team.ALLY, (0, 0), caster_template([skill])), spawn(Team.ENEMY, (2, 1))]
    battle = give_turn(make_state(m, spawns, skills=[skill]), "unit_0001")
    action = next(
        a for a in legal_actions(battle) if isinstance(a, UseSkill) and a.skill_id == skill.id
    )
    after = answered(resolve(battle, action)).state
    assert after.units[UnitId("unit_0001")].cooldowns.get(skill.id) == skill.cost.cooldown
