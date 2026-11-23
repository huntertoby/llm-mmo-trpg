"""預支與「這回合用完所有 AP 時」接進出題（AP-2 第 4 項）：組合器的獨立串流做得出來、LLM 題目
出得到、提議補值把預支補成 0 AP、冷卻下限。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.llm.prompts.builder import PROMPT_VERSION
from trpg.skillgen.proposal_numbers import minimal_filler
from trpg.skillgen.proposal_subset import ProposalRequest, legal_core_primitives
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill


def _lib() -> ContentLibrary:
    return library()


def test_the_composer_no_longer_makes_the_zero_budget_borrow_aura() -> None:
    """QF-6（佇列 (r)）：只有預支一個效果的基本款預算 0，組合器改成重抽，不再組出來（原本的
    「做得出基本款」改成這一題；種子 238 等 6 個種子的結果因此改變）。"""
    lib = _lib()
    for seed in range(400):
        try:
            skill = compose_random_skill(seed, rarity="rare", skeleton="aura", library=lib)
        except ComposeError:
            continue
        assert [e.type for e in skill.effects] != ["borrow_ap"], seed
        assert validate_skill(skill, lib) == []


def test_the_composer_does_not_make_borrow_below_rare() -> None:
    lib = _lib()
    for seed in range(200):
        try:
            skill = compose_random_skill(seed, rarity="common", skeleton="aura", library=lib)
        except ComposeError:
            continue
        assert not skill.borrows_ap


def test_the_composer_makes_an_ap_spent_passive() -> None:
    lib = _lib()
    found = []
    for seed in range(400):
        try:
            skill = compose_random_skill(seed, rarity="epic", kinds=("passive",), library=lib)
        except ComposeError:
            continue
        if skill.trigger is not None and skill.trigger.event == "on_ap_spent_all":
            found.append(skill)
            assert skill.trigger.max_per_round == 1
            assert validate_skill(skill, lib) == []
    assert found


def test_the_prompt_version_moved() -> None:
    assert PROMPT_VERSION == "skill-proposal/24"


def test_llm_topics_can_take_borrow_as_the_core() -> None:
    lib = _lib()
    request = ProposalRequest(tier=1, rarity="rare", kind="active", skeleton="aura")
    assert "borrow_ap" in legal_core_primitives(lib, request)
    common = ProposalRequest(tier=1, rarity="common", kind="active", skeleton="aura")
    assert "borrow_ap" not in legal_core_primitives(lib, common)
    keyword = ProposalRequest(
        tier=1, rarity="rare", kind="active", skeleton="aura", keywords=("ignite",)
    )
    assert "borrow_ap" not in legal_core_primitives(lib, keyword)  # 預支不屬於任何關鍵字


def test_the_filler_makes_a_borrow_proposal_zero_ap_with_a_cooldown() -> None:
    lib = _lib()
    data = {
        "kind": "active",
        "category": "spell",
        "rarity": "rare",
        "effects": [{"type": "borrow_ap", "amount": 1}],
        "cost": {},
    }
    out = minimal_filler(lib)(data)
    assert out["ap_cost"] == 0
    assert out["cost"]["cooldown"] == lib.budget.borrow_min_cooldown
    once = minimal_filler(lib)({**data, "cost": {"uses_per_battle": 1}})
    assert once["ap_cost"] == 0 and "cooldown" not in once["cost"]
