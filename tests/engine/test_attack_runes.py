"""普攻與符文（Phase 3-31，06 6.25「普攻與符文」）：普攻讀取符文（加傷）、單格引爆、留下符文，
各有「裝備詞條」與「修正型被動」兩種形式；每回合最多 1 次、計入 +50% 上限、刻與引爆不能同件。"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    give_turn,
    library,
    make_map,
    make_setup,
    no_reactions,
    spawn,
    with_rolls,
)
from tests.engine.test_gear_g2 import Rolls, _spawn, _state
from trpg.content.equipment import ItemDef, item_problems, loadout_problems
from trpg.content.skills import ModifierSpec, SkillDef
from trpg.engine import Attack, BattleState, EndTurn, resolve, start_battle
from trpg.engine import modifiers as mods
from trpg.engine.effects import InscribeEffect, run_effects
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    GearTriggered,
    RuneInscribed,
    RuneRemoved,
    SkillTriggered,
)
from trpg.engine.runes import has_own_rune, own_runes
from trpg.engine.runner import replay, run_battle
from trpg.engine.skills.conditions import Subject
from trpg.engine.state import state_to_json
from trpg.narrative.skill_icon import icon_of
from trpg.shared.types import Element, Team, UnitId
from trpg.skillgen.validate import validate_skill

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")
FOE = (1, 0)
AFFIX_READ = "affix_attack_rune_read"
AFFIX_DETONATE = "affix_attack_rune_detonate"
AFFIX_INSCRIBE = "affix_attack_rune_inscribe"
SKILLS = ("skill_rune_sight", "skill_rune_breaker", "skill_rune_etcher")


def _arena(
    slots: dict[str, Rolls] | None = None,
    skills: Sequence[str] = (),
    runes: Sequence[tuple[int, int]] = (FOE,),
    row: str = "0000",
) -> BattleState:
    """U1（近戰英雄）在 (0,0)，敵人在最右端；``runes`` 是 U1 預先刻好的雷紋格。"""
    state = give_turn(_state(_spawn(slots or {}, skills=skills), row), U1)
    effects = [
        InscribeEffect(source_id=U1, team=Team.ALLY, pos=xy, element=Element.LIGHTNING)
        for xy in runes
    ]
    return run_effects(state, effects).state if effects else state


def _foe_xy(state: BattleState) -> tuple[int, int]:
    return state.units[U2].xy


def _arena_adjacent(
    slots: dict[str, Rolls] | None = None,
    skills: Sequence[str] = (),
    extra_runes: Sequence[tuple[int, int]] = (),
) -> BattleState:
    """敵人與英雄相鄰（地圖寬 2，敵人在 (1,0)）；``extra_runes`` 是目標格以外的符文格。"""
    state = _arena(slots, skills, runes=(), row="00")
    cells = [_foe_xy(state), *extra_runes]
    effects = [
        InscribeEffect(source_id=U1, team=Team.ALLY, pos=xy, element=Element.LIGHTNING)
        for xy in cells
    ]
    return run_effects(state, effects).state


def _attack(state: BattleState) -> tuple[BattleState, list[EventBase]]:
    result = resolve(with_rolls(state, [(20, 19)]), Attack(unit_id=U1, target_id=U2))
    return result.state, result.events


def _multiplier(state: BattleState) -> int:
    foe = state.units[U2]
    return mods.damage_permille(state, state.units[U1], mods.ATTACK, Subject(foe, foe.xy))


def _next_turn(state: BattleState) -> BattleState:
    """走完這個回合與敵人的回合，回到 U1 的下一個回合（新回合開始時清除每回合計數）。"""
    while True:
        assert state.active_unit is not None
        state = resolve(state, EndTurn(unit_id=state.active_unit)).state
        if state.active_unit == U1:
            return give_turn(state, U1)


def _fresh_foe(state: BattleState) -> BattleState:
    """敵人補滿 HP（避免連續攻擊把測試用的敵人打死）。"""
    s = state.clone()
    s.units[U2].hp = s.units[U2].max_hp
    return s


def _kinds[E: EventBase](events: list[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


# ---------------------------------------------------------------------------
# 1 讀取符文（加傷）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slots", "skills"),
    [
        ({"main_hand": [(AFFIX_READ, 150)]}, ()),
        ({}, ("skill_rune_sight",)),
    ],
    ids=["affix", "passive"],
)
def test_read_adds_damage_on_own_rune_once_per_turn_and_resets(
    slots: dict[str, Rolls], skills: Sequence[str]
) -> None:
    state = _arena_adjacent(slots, skills)
    assert _multiplier(state) == 1150  # 站在自己的符文上：+15%
    after, _ = _attack(state)
    assert _multiplier(_fresh_foe(after)) == 1000  # 同一回合第二次：不再加傷
    again, _ = _attack(_fresh_foe(after))
    assert _multiplier(_fresh_foe(again)) == 1000
    reset = _next_turn(_fresh_foe(again))
    reset = run_effects(
        reset,
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=_foe_xy(reset), element=Element.FIRE)],
    ).state
    assert _multiplier(reset) == 1150  # 下一個回合重置


def test_read_needs_the_casters_own_rune() -> None:
    state = _arena_adjacent({"main_hand": [(AFFIX_READ, 150)]})
    assert _multiplier(state) == 1150
    no_rune = _arena({"main_hand": [(AFFIX_READ, 150)]}, runes=(), row="00")
    assert _multiplier(no_rune) == 1000
    foes = run_effects(
        no_rune,
        [InscribeEffect(source_id=U2, team=Team.ENEMY, pos=_foe_xy(no_rune), element=Element.FIRE)],
    ).state
    assert _multiplier(foes) == 1000  # 別人的符文不算


def test_read_only_applies_to_basic_attacks_not_skills() -> None:
    state = _arena_adjacent({"main_hand": [(AFFIX_READ, 150)]})
    skill = library().skills["skill_cleave"]
    foe = state.units[U2]
    use = mods.skill_use(skill)
    assert mods.damage_permille(state, state.units[U1], use, Subject(foe, foe.xy)) == 1000


def test_read_counts_toward_the_damage_bonus_cap() -> None:
    """讀取 +15%（詞條）＋ 被動 +15% ＋ 代價型 +20%／+10% ＝ +60%，截斷在 +50%。"""
    slots: dict[str, Rolls] = {
        "main_hand": [(AFFIX_READ, 150), ("affix_cost_glass", None)],
        "neck": [("affix_cost_glass", None)],
    }
    state = _arena_adjacent(slots, ("skill_rune_sight",))
    cap = state.ruleset.equipment.caps.damage_bonus_permille
    assert cap == 500
    gear = state.units[U1].gear
    assert {a.affix.id for a in gear.active_affixes("attack")} == {AFFIX_READ}
    assert _multiplier(state) <= 1000 + cap + max(
        0, -sum(b.amount for b in gear.bonuses if b.stat == "damage_permille" and b.amount < 0)
    )
    uncapped = (
        150
        + 150
        + sum(b.amount for b in gear.bonuses if b.stat == "damage_permille" and b.amount > 0)
    )
    assert uncapped > cap
    assert _multiplier(state) == 1000 + cap


# ---------------------------------------------------------------------------
# 2 單格引爆
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slots", "skills"),
    [
        ({"main_hand": [(AFFIX_DETONATE, None)]}, ()),
        ({}, ("skill_rune_breaker",)),
    ],
    ids=["affix", "passive"],
)
def test_detonate_removes_only_the_target_cell_rune_once_per_turn(
    slots: dict[str, Rolls], skills: Sequence[str]
) -> None:
    state = _arena_adjacent(slots, skills, extra_runes=[(0, 0)])
    assert len(own_runes(state, U1)) == 2
    after, events = _attack(state)
    removed = _kinds(events, RuneRemoved)
    assert [(r.reason, (r.pos.x, r.pos.y)) for r in removed] == [("detonated", FOE)]
    assert [r.xy for r in own_runes(after, U1)] == [(0, 0)]  # 另一格的符文還在
    assert any(
        isinstance(e, DamageDealt) and e.target_id == U2 and e.cause == "effect" for e in events
    )
    triggered = _kinds(events, GearTriggered) + _kinds(events, SkillTriggered)
    assert len(triggered) == 1
    # 同一回合再有符文也不再引爆（每回合 1 次）
    refreshed = run_effects(
        _fresh_foe(after),
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=FOE, element=Element.LIGHTNING)],
    ).state
    second, events2 = _attack(refreshed)
    assert not _kinds(events2, RuneRemoved) and has_own_rune(second, U1, FOE)
    # 下一個回合重置
    nxt = run_effects(
        _next_turn(_fresh_foe(second)),
        [InscribeEffect(source_id=U1, team=Team.ALLY, pos=FOE, element=Element.LIGHTNING)],
    ).state
    _, events3 = _attack(nxt)
    assert [r.reason for r in _kinds(events3, RuneRemoved)] == ["detonated"]


def test_detonate_without_a_rune_on_the_target_does_nothing() -> None:
    state = _arena({"main_hand": [(AFFIX_DETONATE, None)]}, runes=((0, 0),), row="00")
    _, events = _attack(state)
    assert not _kinds(events, RuneRemoved)
    assert not any(isinstance(e, DamageDealt) and e.cause == "effect" for e in events)


# ---------------------------------------------------------------------------
# 3 留下符文
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slots", "skills"),
    [
        ({"main_hand": [(AFFIX_INSCRIBE, None)]}, ()),
        ({}, ("skill_rune_etcher",)),
    ],
    ids=["affix", "passive"],
)
def test_inscribe_leaves_a_two_round_rune_on_the_target_cell(
    slots: dict[str, Rolls], skills: Sequence[str]
) -> None:
    state = _arena(slots, skills, runes=(), row="00")
    after, events = _attack(state)
    (placed,) = _kinds(events, RuneInscribed)
    assert (placed.owner_id, (placed.pos.x, placed.pos.y)) == (U1, FOE)
    assert (placed.element, placed.remaining) == (Element.LIGHTNING, 2)
    # 每回合 1 次：換一格也不會再刻（同一回合第二次攻擊）
    _, again = _attack(_fresh_foe(after))
    assert not _kinds(again, RuneInscribed)
    # 2 輪後消失
    remaining = after
    gone: list[RuneRemoved] = []
    for _ in range(3):
        remaining = resolve(remaining, EndTurn(unit_id=remaining.active_unit or U1)).state
        while remaining.active_unit != U1 and not remaining.ended:
            result = resolve(remaining, EndTurn(unit_id=remaining.active_unit or U2))
            remaining = result.state
            gone += _kinds(result.events, RuneRemoved)
        if gone:
            break
    assert [g.reason for g in gone] == ["expired"] and not own_runes(remaining, U1)


def test_inscribe_respects_the_six_rune_limit_per_owner() -> None:
    far = [(2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1)]  # 目標格以外的 6 個格子
    hero = _spawn({"main_hand": [(AFFIX_INSCRIBE, None)]})
    foe_spawn = spawn(Team.ENEMY, (1, 0), no_reactions("bandit"))
    m = make_map("0000\n0000", ally=[(0, 0)], enemy=[(1, 0)])
    state = give_turn(start_battle(make_setup(m, [hero, foe_spawn]), 0), U1)
    effects = [
        InscribeEffect(source_id=U1, team=Team.ALLY, pos=xy, element=Element.FIRE) for xy in far
    ]
    state = run_effects(state, effects).state
    assert len(own_runes(state, U1)) == 6
    oldest = own_runes(state, U1)[0]
    foe = state.units[U2]
    assert foe.xy not in far
    after, events = _attack(state)
    assert len(own_runes(after, U1)) == 6
    limited = [r for r in _kinds(events, RuneRemoved) if r.reason == "limit"]
    assert [r.rune_id for r in limited] == [oldest.id]
    assert has_own_rune(after, U1, foe.xy)


# ---------------------------------------------------------------------------
# 驗證器
# ---------------------------------------------------------------------------


def _item(*affixes: str, slot_type: str = "weapon") -> ItemDef:
    weapon = "one_handed_sword" if slot_type == "weapon" else None
    return ItemDef.model_validate(
        {
            "id": "item_t_rune",
            "name_zh": "測試",
            "slot_type": slot_type,
            "weapon": weapon,
            "affixes": [{"affix": a, "value": 120 if a == AFFIX_READ else None} for a in affixes],
        }
    )


def test_one_item_cannot_inscribe_and_detonate() -> None:
    lib = library()
    both = _item(AFFIX_INSCRIBE, AFFIX_DETONATE)
    problems = item_problems(both, lib.affixes, lib.weapons, lib.ruleset.equipment)
    assert any("不能同時" in p for p in problems)
    ok = _item(AFFIX_INSCRIBE, AFFIX_READ)
    assert item_problems(ok, lib.affixes, lib.weapons, lib.ruleset.equipment) == []
    # 穿戴時也檢查（快照內的同一件）
    hero = _spawn({"main_hand": [(AFFIX_INSCRIBE, None), (AFFIX_DETONATE, None)]})
    found = loadout_problems(hero.equipment, hero.weapon, lib.ruleset.equipment)
    assert any("不能同時" in p for p in found)


def test_two_items_may_split_inscribe_and_detonate() -> None:
    lib = library()
    for slot, affix in (("weapon", AFFIX_INSCRIBE), ("hands", AFFIX_DETONATE)):
        item = _item(affix, slot_type=slot)
        assert item_problems(item, lib.affixes, lib.weapons, lib.ruleset.equipment) == []


@pytest.mark.parametrize(
    ("affix", "good", "bad"),
    [
        (AFFIX_READ, ("weapon", "hands", "ring"), ("offhand", "body", "neck", "feet", "head")),
        (AFFIX_DETONATE, ("weapon", "hands"), ("ring", "offhand", "body", "neck")),
        (AFFIX_INSCRIBE, ("weapon", "hands"), ("ring", "offhand", "body", "neck")),
    ],
)
def test_rune_affixes_only_appear_on_the_listed_slots(
    affix: str, good: tuple[str, ...], bad: tuple[str, ...]
) -> None:
    lib = library()
    assert set(lib.affixes[affix].slots) == set(good)
    for slot_type in bad:
        item = _item(affix, slot_type=slot_type)
        assert any(
            "不能出現在" in p
            for p in item_problems(item, lib.affixes, lib.weapons, lib.ruleset.equipment)
        )


def test_read_affix_rolls_ten_to_fifteen_percent() -> None:
    lib = library()
    read = lib.affixes[AFFIX_READ]
    assert read.value is not None and (read.value.min, read.value.max) == (100, 150)
    assert read.value_unit == "permille" and read.category == "attack"
    for value in (99, 151):
        item = ItemDef.model_validate(
            {
                "id": "item_t_x",
                "name_zh": "x",
                "slot_type": "ring",
                "affixes": [{"affix": AFFIX_READ, "value": value}],
            }
        )
        assert item_problems(item, lib.affixes, lib.weapons, lib.ruleset.equipment)


def _passive(**overrides: object) -> dict[str, object]:
    data = library().skills["skill_rune_breaker"].model_dump(mode="json")
    data.update(overrides)
    return data


def test_one_passive_cannot_inscribe_and_detonate() -> None:
    rules = [
        {
            "applies_to": {"actions": ["attack"]},
            "change": {
                "on_hit_effects": [
                    {"type": "detonate_runes", "dice": "1d6", "scope": "target_cell"}
                ]
            },
            "per_turn_limit": 1,
        },
        {
            "applies_to": {"actions": ["attack"]},
            "change": {"on_hit_effects": [{"type": "inscribe", "element": "lightning"}]},
        },
    ]
    with pytest.raises(ValidationError, match="不能同時"):
        SkillDef.model_validate(_passive(modifiers=rules))
    one_rule = {
        "applies_to": {"actions": ["attack"]},
        "change": {
            "on_hit_effects": [
                {"type": "detonate_runes", "dice": "1d6", "scope": "target_cell"},
                {"type": "inscribe", "element": "lightning"},
            ]
        },
    }
    with pytest.raises(ValidationError, match="不能同時"):
        SkillDef.model_validate(_passive(modifiers=[one_rule]))


def test_modifier_schema_for_the_new_fields() -> None:
    def rule(**data: object) -> dict[str, object]:
        return {"applies_to": {"actions": ["attack"]}, **data}

    with pytest.raises(ValueError, match="scope"):  # 命中後引爆必須指定只引爆目標那 1 格
        ModifierSpec.model_validate(
            rule(change={"on_hit_effects": [{"type": "detonate_runes", "dice": "1d6"}]})
        )
    with pytest.raises(ValueError, match="per_turn_limit"):
        ModifierSpec.model_validate(rule(change={"hit_bonus": 1}, per_turn_limit=1))
    with pytest.raises(ValueError, match="只能套用在普攻"):
        ModifierSpec.model_validate(
            {
                "applies_to": {"all_attacks": True},
                "change": {"damage_permille": 100},
                "per_turn_limit": 1,
            }
        )
    with pytest.raises(ValidationError):
        ModifierSpec.model_validate(rule(change={"damage_permille": 100}, per_turn_limit=2))
    with pytest.raises(ValueError, match="element 或 tag"):
        ModifierSpec.model_validate(rule(change={"on_hit_effects": [{"type": "inscribe"}]}))


# ---------------------------------------------------------------------------
# 被動技能：預算、關鍵字、圖示
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", SKILLS)
def test_rune_passives_pass_budget_have_keywords_and_icons(skill_id: str) -> None:
    lib = library()
    skill = lib.skills[skill_id]
    assert skill.kind == "modifier" and skill.rarity == "epic"
    assert validate_skill(skill, lib) == []
    keywords = lib.ruleset.skill_keywords(skill)
    assert keywords.makes or keywords.uses
    assert icon_of(skill.model_dump(mode="json", exclude_none=True))


def test_rune_passive_keywords_read_or_make_runes() -> None:
    lib = library()
    kw = {s: lib.ruleset.skill_keywords(lib.skills[s]) for s in SKILLS}
    assert "marked" in kw["skill_rune_sight"].uses  # 讀取／利用符文
    assert "marked" in kw["skill_rune_breaker"].uses
    assert {"marked", "charged"} <= set(kw["skill_rune_etcher"].makes)  # 製造符文


# ---------------------------------------------------------------------------
# 確定性與重播
# ---------------------------------------------------------------------------


def test_same_seed_gives_the_same_events() -> None:
    def run() -> list[dict[str, object]]:
        state = _arena_adjacent(
            {"main_hand": [(AFFIX_READ, 150)], "hands": [(AFFIX_DETONATE, None)]},
            ("skill_rune_etcher",),
        )
        after, events = _attack(state)
        _, more = _attack(_fresh_foe(after))
        return [e.model_dump(mode="json") for e in events + more]

    first = run()
    assert first == run()
    assert any(e["type"] == "gear_triggered" for e in first)


def test_full_battle_with_attack_runes_replays_identically() -> None:
    """帶普攻符文的整場自動戰鬥：初始狀態 ＋ 步驟列表重播得到同樣的事件與最終狀態。"""
    hero = _spawn(
        {"main_hand": [(AFFIX_INSCRIBE, None), (AFFIX_READ, 120)]},
        skills=("skill_rune_breaker",),
    )
    foe = spawn(Team.ENEMY, (3, 0), no_reactions("bandit"))
    setup = make_setup(make_map("0000", ally=[(0, 0)], enemy=[(3, 0)]), [hero, foe], max_rounds=6)
    run = run_battle(setup, 5)
    again = replay(setup, 5, run.actions)
    assert [e.model_dump(mode="json") for e in again.events] == [
        e.model_dump(mode="json") for e in run.events
    ]
    assert state_to_json(again.state) == state_to_json(run.state)
    kinds = {e.model_dump(mode="json")["type"] for e in run.events}
    assert {"gear_triggered", "rune_inscribed"} <= kinds
    assert [e.model_dump(mode="json") for e in run_battle(setup, 5).events] == [
        e.model_dump(mode="json") for e in run.events
    ]
