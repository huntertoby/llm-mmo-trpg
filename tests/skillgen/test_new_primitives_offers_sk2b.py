"""#166 新原語接進出題（SK-2b，玩法交接 4.1.28 第 5 點）：

- 鉤：位移骨架的核心（直線、1 階可出、冷卻照 ``hook_min_cooldown``）。
- 吸收表面：打擊、蓄力／終結骨架的附帶（換層數、元素，放第一個）；光環骨架的核心（換治療、護盾，
  只吸自己腳下）。
- 疾病擴散：打擊、範圍、控場、陷阱的附帶，只在技能已施加燃燒、流血、中毒時加。
- 組合器用獨立串流：機率 0 時一個新原語都不出（父串流不推進，沒抽中的種子照舊）。
- LLM 題目：骨架的核心／附帶選單帶到新原語；``llm_topic.core_exclude`` 不排除它們。
"""

from __future__ import annotations

import dataclasses
from functools import cache
from typing import Any

import pytest

from tests.engine.helpers import library, make_skill
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.composer_parts import _HAND_WRITTEN_PRIMITIVES
from trpg.skillgen.proposal_subset import ProposalRequest, legal_core_primitives, select_subset
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

NEW = ("hook", "absorb_surface", "contagion")
FIELDS = ("hook_core_permille", "absorb_core_permille", "absorb_secondary_permille")


@cache
def _forced(*fields: str) -> ContentLibrary:
    lib = library()
    update = {f: 1000 for f in fields}
    structure = lib.composer.structure.model_copy(update=update)
    return dataclasses.replace(
        lib, composer=lib.composer.model_copy(update={"structure": structure})
    )


@cache
def _off() -> ContentLibrary:
    lib = library()
    update = {f: 0 for f in (*FIELDS, "contagion_permille")}
    structure = lib.composer.structure.model_copy(update=update)
    return dataclasses.replace(
        lib, composer=lib.composer.model_copy(update={"structure": structure})
    )


def _types(skill: SkillDef) -> list[str]:
    return [e.type for e in skill.effects]


def test_new_primitives_stay_out_of_the_plain_draw() -> None:
    assert set(NEW) <= _HAND_WRITTEN_PRIMITIVES
    assert not set(NEW) & set(library().composer.llm_topic.core_exclude)


@pytest.mark.parametrize("seed", range(6))
def test_hook_is_a_displace_core_at_tier_one(seed: int) -> None:
    lib = _forced("hook_core_permille")
    skill = compose_random_skill(seed, tier=1, rarity="rare", skeleton="displace", library=lib)
    assert "hook" in _types(skill)
    assert skill.shape.type == "line"
    assert (skill.cost.cooldown or 0) >= lib.budget.hook_min_cooldown
    assert validate_skill(skill, lib) == []


@pytest.mark.parametrize("seed", range(6))
def test_absorb_is_an_aura_core_on_the_casters_tile(seed: int) -> None:
    lib = _forced("absorb_core_permille")
    skill = compose_random_skill(seed, tier=1, rarity="rare", skeleton="aura", library=lib)
    first = skill.effects[0]
    assert (first.type, first.affects) == ("absorb_surface", "self")
    assert first.gain in ("heal", "shield") and first.dice is not None
    assert validate_skill(skill, lib) == []


@pytest.mark.parametrize("seed", range(12))
def test_absorb_secondary_on_strike_goes_first(seed: int) -> None:
    lib = _forced("absorb_secondary_permille")
    skill = compose_random_skill(seed, tier=1, rarity="rare", skeleton="strike", library=lib)
    assert validate_skill(skill, lib) == []
    if "absorb_surface" not in _types(skill):
        return  # 附帶名額已被別的效果用掉，或形狀不是單體
    first = skill.effects[0]
    assert first.type == "absorb_surface" and first.gain in ("element", "stack")
    assert skill.shape.type == "single"
    if first.gain == "stack":
        assert first.stack is not None and first.amount is not None


def test_absorb_secondary_appears_in_a_sample() -> None:
    lib = _forced("absorb_secondary_permille")
    found = [
        compose_random_skill(seed, tier=1, rarity="rare", skeleton=skeleton, library=lib)
        for skeleton in ("strike", "builder_finisher")
        for seed in range(30)
    ]
    assert any(s.effects[0].type == "absorb_surface" for s in found)


def test_contagion_only_after_a_spreading_status() -> None:
    """附帶名額常被用滿、會擴散的狀態也不常抽到，所以三個骨架合起來看至少出現一次。"""
    lib = _forced()
    structure = lib.composer.structure.model_copy(update={"contagion_permille": 1000})
    lib = dataclasses.replace(
        lib, composer=lib.composer.model_copy(update={"structure": structure})
    )
    kinds = set(lib.ruleset.core.contagion_statuses)
    seen = 0
    for skeleton in ("area", "control", "trap"):
        for seed in range(40):
            skill = compose_random_skill(
                seed, tier=2, rarity="epic", skeleton=skeleton, library=lib
            )
            types = _types(skill)
            if "contagion" not in types:
                continue
            seen += 1
            at = types.index("contagion")
            assert any(
                e.type == "apply_status" and e.status in kinds for e in skill.effects[:at]
            ), skill.id
            assert validate_skill(skill, lib) == []
    assert seen > 0


@pytest.mark.parametrize("skeleton", ["displace", "aura", "strike", "area", "control"])
def test_zero_chance_never_adds_them(skeleton: str) -> None:
    lib = _off()
    for seed in range(15):
        skill = compose_random_skill(seed, tier=1, rarity="rare", skeleton=skeleton, library=lib)
        assert not set(NEW) & set(_types(skill))


# -- 驗證器 ---------------------------------------------------------------------

STRIKE_BASE: dict[str, Any] = {"type": "damage", "dice": "2d6", "element": "fire"}


def _rules(skill: SkillDef) -> set[str]:
    return {v.rule for v in validate_skill(skill, library())}


def _strike(*effects: dict[str, Any]) -> SkillDef:
    data = make_skill("skill_t", {"type": "single", "range": 3}, list(effects)).model_dump(
        mode="json", exclude_none=True
    )
    return SkillDef.model_validate({**data, "skeleton": "strike", "rarity": "rare"})


def test_strike_takes_absorb_although_harmful_only() -> None:
    absorb = {"type": "absorb_surface", "affects": "self", "gain": "element"}
    rules = library().skeletons["strike"].secondary
    assert rules.admits("absorb_surface", harmful=False)
    assert not rules.admits("heal", harmful=False)
    assert "skeleton.secondary" not in _rules(_strike(absorb, STRIKE_BASE))
    heal = {"type": "heal", "dice": "1d4", "affects": "self"}
    assert "skeleton.secondary" in _rules(_strike(STRIKE_BASE, heal))


def test_contagion_needs_a_spreading_status_before_it() -> None:
    contagion: dict[str, Any] = {"type": "contagion"}
    burn = {"type": "apply_status", "status": "burning"}
    slow = {"type": "apply_status", "status": "slow"}
    rule = "cap.contagion_source"
    assert rule in _rules(_strike(STRIKE_BASE, contagion))
    assert rule in _rules(_strike(STRIKE_BASE, slow, contagion))
    assert rule in _rules(_strike(STRIKE_BASE, contagion, burn))  # 要在施加之後
    assert rule not in _rules(_strike(STRIKE_BASE, burn, contagion))


# -- LLM 題目 -------------------------------------------------------------------


def test_llm_topics_can_offer_them() -> None:
    lib = library()
    assert "hook" in legal_core_primitives(lib, ProposalRequest(1, "rare", skeleton="displace"))
    assert "absorb_surface" in legal_core_primitives(
        lib, ProposalRequest(1, "rare", skeleton="aura")
    )
    strike = select_subset(lib, ProposalRequest(1, "rare", skeleton="strike"))
    assert {"absorb_surface", "contagion"} <= set(strike.primitives)


@pytest.mark.parametrize("skeleton", ["combo", "aura"])
def test_unlisted_secondary_skeletons_never_get_them(skeleton: str) -> None:
    """附帶「不限」的骨架（連段、光環）不由獨立串流加吸收表面、疾病擴散（只加在明列的骨架）。"""
    lib = _forced("absorb_secondary_permille")
    update = {"contagion_permille": 1000, "absorb_core_permille": 0}  # 光環的核心另有串流
    structure = lib.composer.structure.model_copy(update=update)
    lib = dataclasses.replace(
        lib, composer=lib.composer.model_copy(update={"structure": structure})
    )
    for seed in range(20):
        skill = compose_random_skill(seed, tier=2, rarity="epic", skeleton=skeleton, library=lib)
        assert "contagion" not in _types(skill)
        assert "absorb_surface" not in _types(skill)
