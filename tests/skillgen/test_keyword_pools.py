"""主題合併（R2）。

原 ``test_pools_24c.py``：

關鍵字池的真實利用者與不限武器的 1 階技能（Phase 3-24c，``docs/design/06-技能.md`` 6.27.2）。

原 ``test_pools_27.py``：

關鍵字池補齊第二批與挑釁怒吼（Phase 3-27，``docs/phases/Phase3計畫.md`` 29 節）。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import give_turn, library, make_map, make_setup
from tests.engine.test_weapons_ranged import armed, dice, foe, kinds, weapon
from tests.skillgen.test_keywords import _skill
from trpg.engine import BattleState, UseSkill, resolve, start_battle
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.events import DamageDealt
from trpg.engine.state import StatusInstance
from trpg.shared.types import Team, UnitId
from trpg.skillgen.keywords import derive_keywords, is_starter_skill
from trpg.skillgen.validate import validate_skill

# --- 原 test_pools_24c.py ---

NEW_SKILLS = (
    "bone_pursuit",
    "shock_follow",
    "soul_burst",
    "spirit_offering",
    "scorching_slash",
    "flare_shot",
    "kindle_pop",
    "icebreaker",
    "frost_snap",
    "thaw_blast",
    "spark_chain",
    "thunder_clap",
    "splash_flask",
    "frost_touch",
    "mark_prey",
)


def _exclusive_users(keyword: str, *, starter: bool) -> list[str]:
    lib = library()
    return [
        sid
        for sid, skill in sorted(lib.skills.items())
        if skill.kind == "active"
        and (not starter or is_starter_skill(skill))
        and keyword in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    ]


@pytest.mark.parametrize(
    ("keyword", "minimum"),
    [("ignite", 3), ("frozen", 3), ("charged", 3), ("collision", 2), ("summon", 1)],
)
def test_pools_have_enough_active_exploiters_under_exclusive_rules(
    keyword: str, minimum: int
) -> None:
    """專屬規則下，起始等級（1 階普通或稀有）的主動利用者數量。"""
    assert len(_exclusive_users(keyword, starter=True)) >= minimum


@pytest.mark.parametrize("name", NEW_SKILLS)
def test_every_new_skill_passes_validation_and_budget(name: str) -> None:
    lib = library()
    skill = lib.skills[f"skill_{name}"]
    assert validate_skill(skill, lib) == []
    assert skill.tier == 1 and skill.kind == "active" and is_starter_skill(skill)
    assert derive_keywords(skill, lib.keywords, exclusive_only=True).all()  # 專屬規則就有關鍵字


def test_taunting_roar_applies_marked() -> None:
    lib = library()
    roar = lib.skills["skill_taunting_roar"]
    assert any(e.type == "apply_status" and e.status == "marked" for e in roar.effects)
    assert validate_skill(roar, lib) == []
    assert "marked" in derive_keywords(roar, lib.keywords, exclusive_only=True).makes


@pytest.mark.parametrize("keyword", ["wet", "frozen", "marked"])
def test_any_weapon_starter_makes_wet_frozen_and_marked(keyword: str) -> None:
    lib = library()
    found = [
        s.id
        for s in lib.skills.values()
        if is_starter_skill(s)
        and s.weapon_req == "any"
        and keyword in derive_keywords(s, lib.keywords, exclusive_only=True).makes
    ]
    assert found, keyword


def test_sacrifice_belongs_to_the_summon_pool_and_target_collided_to_collision() -> None:
    lib = library()
    kw = derive_keywords(lib.skills["skill_soul_burst"], lib.keywords, exclusive_only=True)
    assert kw.uses == ("summon",)
    kw2 = derive_keywords(lib.skills["skill_bone_pursuit"], lib.keywords, exclusive_only=True)
    assert kw2.uses == ("collision",)


def test_new_keyword_descriptions_follow_the_gameplay_wording() -> None:
    table = {k.id: k.description_zh for k in library().keywords.keywords}
    assert "連鎖" in table["charged"] and "靜電" in table["charged"]
    assert "獻祭" in table["summon"]
    assert "近戰" in table["prone"]


def test_a_keywordless_skill_is_a_basic_skill_with_no_validator_complaint() -> None:
    lib = library()
    plain = _skill(
        id="skill_t_plain",
        cost={"mana": 6},
        effects=[{"type": "damage", "dice": "2d6", "element": "physical"}],
    )
    assert not derive_keywords(plain, lib.keywords)
    assert [p for p in validate_skill(plain, lib) if p.rule == "keyword.required"] == []


def test_every_keyword_pool_has_at_least_three_active_exploiters() -> None:
    """06 6.27.2：每個池至少 3 招主動利用者（只算專屬規則；Phase 3-51 移除暫定規則後的檢查）。"""
    lib = library()
    short = {
        k: len(_exclusive_users(k, starter=False))
        for k in lib.keywords.start_ids()  # KW-1：start_hidden 的四個層數關鍵字在 KW-2 補齊
        if len(_exclusive_users(k, starter=False)) < 3
    }
    assert short == {}


# --- 原 test_pools_27.py ---

U1, U2 = UnitId("unit_0001"), UnitId("unit_0002")

KEYWORDS = (
    "ignite",
    "wet",
    "charged",
    "frozen",
    "prone",
    "collision",
    "marked",
    "high_ground",
    "concealed",
    "summon",
)

# 技能 -> (武器, 關鍵字池, 讓條件成立的布置)
NEW_SKILLS_27: dict[str, tuple[str, str, str]] = {
    "trample": ("one_handed_sword", "prone", "prone"),
    "ground_finish": ("one_handed_sword", "prone", "prone"),
    "gravity_crush": ("lightning_staff", "prone", "prone"),
    "tide_cleave": ("one_handed_sword", "wet", "water"),
    "ripple_shot": ("bow", "wet", "water"),
    "hunters_strike": ("one_handed_sword", "marked", "marked"),
    "pinpoint_shot": ("bow", "marked", "marked"),
    "plunging_strike": ("one_handed_sword", "high_ground", "high"),
    "downdraft": ("one_handed_sword", "high_ground", "high"),
    "pinning_shot": ("bow", "collision", "collided"),
    "veiled_shot": ("bow", "concealed", "self_concealed"),
    "glacier_offering": ("one_handed_sword", "summon", ""),
}


def _users(keyword: str, *, starter: bool) -> list[str]:
    lib = library()
    return [
        sid
        for sid, skill in sorted(lib.skills.items())
        if skill.kind == "active"
        and (not starter or is_starter_skill(skill))
        and keyword in derive_keywords(skill, lib.keywords, exclusive_only=True).uses
    ]


@pytest.mark.parametrize("keyword", KEYWORDS)
def test_every_pool_has_three_exclusive_active_exploiters(keyword: str) -> None:
    assert len(_users(keyword, starter=True)) >= 3
    assert len(_users(keyword, starter=False)) >= 3


@pytest.mark.parametrize("name", sorted(NEW_SKILLS_27))
def test_27_every_new_skill_passes_validation_and_budget(name: str) -> None:
    lib = library()
    skill = lib.skills[f"skill_{name}"]
    assert validate_skill(skill, lib) == []
    assert skill.tier == 1 and skill.kind == "active" and is_starter_skill(skill)
    _, pool, _ = NEW_SKILLS_27[name]
    assert pool in derive_keywords(skill, lib.keywords, exclusive_only=True).uses


def test_taunting_roar_is_ap_1_cooldown_2_and_still_marks() -> None:
    lib = library()
    roar = lib.skills["skill_taunting_roar"]
    assert roar.ap_cost == 1 and roar.cost.cooldown == 2
    marked = [e for e in roar.effects if e.type == "apply_status" and e.status == "marked"]
    assert len(marked) == 1 and marked[0].duration == 1
    assert validate_skill(roar, lib) == []
    assert "marked" in derive_keywords(roar, lib.keywords, exclusive_only=True).makes


_HEIGHTS = "\n".join(["000000000"] * 5)
_HIGH = "\n".join(["110000000"] * 5)


def _scene(name: str, setup: str, *, lit: bool) -> BattleState:
    weapon_id, _, _ = NEW_SKILLS_27[name]
    ranged = weapon_id == "bow"
    caster = weapon_id == "lightning_staff"
    skill = f"skill_{name}"
    attacker_at, foe_at = ((1, 2), (4, 2)) if ranged else ((1, 2), (2, 2))
    hero = "hero_archer" if ranged else ("hero_mage" if caster else "hero_fighter")
    surfaces = [(*foe_at, "water")] if lit and setup == "water" else []
    heights = _HIGH if lit and setup == "high" else _HEIGHTS
    m = make_map(heights, None, ally=[attacker_at], enemy=[foe_at], surfaces=surfaces)
    spawns = [
        armed(Team.ALLY, attacker_at, weapon(weapon_id), base=hero, skills=[skill]),
        foe(foe_at),
    ]
    state = give_turn(start_battle(make_setup(m, spawns), 0), U1)
    state.units[U1].mana = 99
    if lit and setup in ("prone", "marked"):
        state.units[U2].statuses = [StatusInstance(status_id=setup, remaining=3, source_id=None)]
    if lit and setup == "collided":
        state.units[U2].collided_round = state.round
    if lit and setup == "self_concealed":
        state.units[U1].statuses = [StatusInstance(status_id="concealed", remaining=3)]
    return state


def _damage(state: BattleState, name: str) -> int:
    res = resolve(state, UseSkill(unit_id=U1, skill_id=f"skill_{name}", target_id=U2))
    return sum(e.amount for e in kinds(res.events, DamageDealt))


@pytest.mark.parametrize("name", [n for n, v in sorted(NEW_SKILLS_27.items()) if v[2]])
def test_the_bonus_only_applies_when_the_condition_holds(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    dice(monkeypatch, d20=19, die=3)
    _, _, setup = NEW_SKILLS_27[name]
    plain = _damage(_scene(name, setup, lit=False), name)
    lit = _damage(_scene(name, setup, lit=True), name)
    assert plain > 0 and lit > plain


@pytest.mark.parametrize("name", [n for n, v in sorted(NEW_SKILLS_27.items()) if v[2]])
def test_the_ai_scores_the_new_skill_best_when_the_condition_holds(name: str) -> None:
    """條件成立時，技能是（不含瞄準這種準備動作的）最高分動作。"""
    state = _scene(name, NEW_SKILLS_27[name][2], lit=True)
    ranked = UtilityAI(library().ai_profiles).rank(state)
    best = max((s for s in ranked if s.action.type != "aim"), key=lambda s: s.score)
    assert isinstance(best.action, UseSkill) and best.action.skill_id == f"skill_{name}"
