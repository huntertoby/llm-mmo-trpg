"""4-L10b：LLM 提議的引擎補值（4-L9 建議 B1～B3）。

B1：沒有旋鈕的結構（位移、地形、淨化等核心）過弱時，補值器把巢狀效果的數值也當旋鈕，仍不夠就依
``llm_cost.weak_steps`` 降 AP（必要時補冷卻／法力），直到預算下限；補完的技能卡片數字＝實戰。
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import (
    answered,
    caster_template,
    give_turn,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.skills.constants import SkillRarity
from trpg.engine import UseSkill, resolve
from trpg.engine.battle import legal_actions
from trpg.engine.state import StatusInstance
from trpg.narrative.skills import skill_card
from trpg.shared.types import Team, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.proposal import (
    ProposalContext,
    ProposalModels,
    build_proposal_models,
    evaluate_proposal,
)
from trpg.skillgen.proposal_budget import budget_filler, evaluate_with_repair, lift_weak
from trpg.skillgen.proposal_layouts import layout_of_effects
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.validate import validate_skill

SID = "skill_t_l10b"
CASTER = UnitId("unit_0001")
FOE = UnitId("unit_0003")


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


@pytest.fixture(scope="module")
def models(library: ContentLibrary) -> ProposalModels:
    return build_proposal_models(library)


def _proposal(
    library: ContentLibrary,
    skeleton: str,
    shape: dict[str, Any],
    effects: list[dict[str, Any]],
    **extra: Any,
) -> dict[str, Any]:
    return {
        "layout": layout_of_effects(library, [e["type"] for e in effects]),
        "kind": "active",
        "skeleton": skeleton,
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "shape": shape,
        "effects": effects,
        **extra,
    }


SINGLE = {"type": "single", "range": 4}
TILE = {"type": "ground_tile", "range": 4}

type Case = tuple[int, SkillRarity, str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]
B1_CASES: dict[str, Case] = {
    # 原語: (角色階級, 稀有度, 骨架, 形狀, 效果, 其他欄位)
    "teleport": (
        2,
        "rare",
        "displace",
        TILE,
        [{"type": "teleport"}, {"type": "apply_status", "affects": "self", "status": "concealed"}],
        {},
    ),
    "swap": (
        2,
        "rare",
        "displace",
        SINGLE,
        [
            {"type": "swap", "affects": "enemies"},
            {"type": "apply_status", "affects": "enemies", "status": "slow"},
        ],
        {},
    ),
    "swap_any": (
        3,
        "epic",
        "displace",
        {"type": "unit_pair", "range": 4},
        [{"type": "swap_any"}],
        {},
    ),
    "teleport_target": (
        3,
        "epic",
        "displace",
        {"type": "unit_then_tile", "range": 4},
        [{"type": "teleport_target"}],
        {},
    ),
    "leap": (
        2,
        "rare",
        "displace",
        {"type": "ground_tile", "range": 3},
        [{"type": "leap"}, {"type": "apply_status", "affects": "self", "status": "hasted"}],
        {},
    ),
    "raise_terrain": (
        1,
        "rare",
        "control",
        TILE,
        [{"type": "raise_terrain", "affects": "tiles"}],
        {"element": "earth"},
    ),
    "cleanse": (
        1,
        "rare",
        "aura",
        SINGLE,
        [
            {"type": "cleanse", "affects": "allies"},
            {"type": "apply_status", "affects": "allies", "status": "defending"},
        ],
        {},
    ),
    "apply_status": (
        1,
        "rare",
        "aura",
        SINGLE,
        [{"type": "apply_status", "affects": "allies", "status": "hasted"}],
        {},
    ),
    "consume_status": (
        1,
        "rare",
        "consume_status",
        SINGLE,
        [
            {
                "type": "consume_status",
                "status": "burning",
                "then": [{"type": "damage", "element": "fire"}],
            }
        ],
        {},
    ),
    "restore_resource": (
        1,
        "rare",
        "aura",
        {"type": "self"},
        [{"type": "restore_resource", "resource": "mana", "affects": "self"}],
        {},
    ),
    "topple": (1, "rare", "displace", {"type": "single", "range": 3}, [{"type": "topple"}], {}),
}


def _case(library: ContentLibrary, name: str) -> tuple[dict[str, Any], ProposalContext]:
    tier, rarity, skeleton, shape, effects, extra = B1_CASES[name]
    return _proposal(library, skeleton, shape, effects, **extra), ProposalContext(tier, rarity)


def _battle(skill: SkillDef) -> Any:
    """施放者 U1 在 (3,3)（法力 50）、友方在 (2,3)、敵方在 (4,3)（燃燒）與 (5,5)、石柱在 (3,5)。"""
    m = make_map(
        "\n".join(["0000000"] * 7),
        ally=[(3, 3), (2, 3)],
        enemy=[(4, 3), (5, 5)],
        objects=[(3, 5, "stone_pillar")],
    )
    spawns = [spawn(Team.ALLY, (3, 3), caster_template([skill]))]
    spawns.append(spawn(Team.ALLY, (2, 3), no_reactions("hero_archer")))
    spawns += [spawn(Team.ENEMY, xy, no_reactions()) for xy in [(4, 3), (5, 5)]]
    state = give_turn(make_state(m, spawns, skills=[skill]), CASTER)
    state.units[FOE].statuses.append(StatusInstance("burning", 2))
    state.units[CASTER].mana = 50  # 回復法力的技能看得出回了多少
    return state


@pytest.mark.parametrize("name", sorted(B1_CASES))
def test_knobless_core_is_lifted_to_the_budget_floor(
    library: ContentLibrary, models: ProposalModels, name: str
) -> None:
    proposal, ctx = _case(library, name)
    plain = evaluate_proposal(proposal, models, library, ctx, fill=budget_filler(library, seed=3))
    assert [e.code for e in plain.errors] == ["budget.weak"]
    evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=3)
    assert evaluation.ok, evaluation.result.errors
    assert evaluation.repaired == ("budget.weak",)
    skill = evaluation.result.skill
    assert skill is not None
    assert validate_skill(skill, library) == []
    report = skill_budget(skill, library)
    assert report.min_ratio <= report.ratio <= report.max_ratio
    # 確定性
    again = evaluate_with_repair(proposal, models, library, ctx, seed=3).result.skill
    assert again is not None and again.model_dump() == skill.model_dump()


@pytest.mark.parametrize("name", sorted(B1_CASES))
def test_lifted_skill_card_numbers_match_the_battle(
    library: ContentLibrary, models: ProposalModels, name: str
) -> None:
    proposal, ctx = _case(library, name)
    evaluation = evaluate_with_repair(proposal, models, library, ctx, seed=3)
    assert evaluation.result.skill is not None
    skill = evaluation.result.skill.model_copy(update={"id": SID})
    card = skill_card(library, skill)
    assert card.ap_cost == skill.ap_cost
    cost = skill.cost
    if cost.mana:
        assert f"法力 {cost.mana}" in card.cost
    if cost.cooldown:
        assert f"冷卻 {cost.cooldown} 回合" in card.cost
    for effect in skill.effects:  # 巢狀效果補上的骰子也寫在卡片上
        for sub in effect.then or ():
            if sub.dice is not None:
                assert any(str(sub.dice) in line for line in card.effects)
    state = _battle(skill)
    actions = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == SID]
    assert actions, f"{name}：找不到可施放的動作"
    before = state.units[CASTER]
    result = answered(resolve(state, actions[0]))
    after = result.state.units[CASTER]
    assert before.ap - after.ap == card.ap_cost
    restored = sum(
        e.amount or 0
        for e in skill.effects
        if e.type == "restore_resource" and e.resource == "mana"
    )
    assert before.mana - after.mana == (cost.mana or 0) - restored
    assert after.cooldowns.get(SID) == cost.cooldown


def test_lone_knobless_core_still_reports_weak(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """3 階的單獨傳送：降 AP 也補不到下限，照舊回報 ``budget.weak``（不降預算下限）。"""
    proposal = _proposal(library, "displace", TILE, [{"type": "teleport"}])
    evaluation = evaluate_with_repair(proposal, models, library, ProposalContext(3, "epic"), seed=3)
    assert [e.code for e in evaluation.result.errors] == ["budget.weak"]
    assert evaluation.repaired == ()


def test_proposal_that_passes_keeps_the_default_ap(
    library: ContentLibrary, models: ProposalModels
) -> None:
    """不過弱的提議不走補強：AP 維持 2。"""
    proposal = _proposal(
        library, "control", SINGLE, [{"type": "apply_status", "status": "blinded"}]
    )
    evaluation = evaluate_with_repair(proposal, models, library, ProposalContext(1, "rare"), seed=3)
    assert evaluation.ok and evaluation.repaired == ()
    assert evaluation.result.skill is not None and evaluation.result.skill.ap_cost == 2


def test_lift_weak_leaves_in_window_data_alone(library: ContentLibrary) -> None:
    skill = library.skills["skill_fire_arrow"]
    data = skill.model_dump(mode="json", exclude_none=True)
    assert lift_weak(library, data, 3) is data


def test_weak_steps_lower_ap_and_only_add_back_cooldown_or_mana(library: ContentLibrary) -> None:
    rules = library.composer.llm_cost
    assert rules.weak_steps
    for step in rules.weak_steps:
        assert step.ap == 1
        assert (step.cooldown or 0) <= rules.max_cooldown
    keys = [((s.cooldown or 0), (s.mana or 0)) for s in rules.weak_steps]
    assert keys == sorted(keys)  # 由輕到重
