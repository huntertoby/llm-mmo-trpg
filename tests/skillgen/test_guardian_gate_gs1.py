"""GS-1（#171）：護主不獨佔指定關鍵字的反應題。

題目指定的關鍵字不是召喚、而且是反應題時，每題只擲一次要不要用護主（獨立串流
``composer.guardian``，``recipes.reaction_permille``）；沒擲中，這題所有的種子變體都不用護主。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen import random_composer
from trpg.skillgen.random_composer import (
    ComposeError,
    compose_with_stats,
    default_library,
    guardian_gate,
)

SEEDS = range(40)
GUARDIAN_MAX_PERMILLE = 350
"""驗收：召喚以外的關鍵字格，護主占 35% 以下（#171）。"""


def _is_guardian(skill: SkillDef) -> bool:
    return skill.kind == "reaction" and any(e.type == "summon_beside" for e in skill.effects)


def _reaction(seed: int, keyword: str, tier: int, rarity: str) -> SkillDef | None:
    try:
        return compose_with_stats(
            seed,
            tier=tier,
            rarity=rarity,  # type: ignore[arg-type]
            keyword=keyword,
            library=default_library(),
            kinds=("reaction",),
        ).skill
    except ComposeError:
        return None


def test_gate_only_for_keyword_reaction_questions_other_than_summon() -> None:
    lib = default_library()
    assert guardian_gate(1, None, lib, "reaction") is None
    assert guardian_gate(1, "summon", lib, "reaction") is None
    assert guardian_gate(1, "ignite", lib, None) is None
    assert guardian_gate(1, "ignite", lib, "passive") is None
    permille = lib.composer.recipes.reaction_permille
    for seed in SEEDS:
        # 獨立串流：只由題目的種子決定，和主串流、變體種子無關
        expected = Rng(seed).fork("composer.guardian").chance_permille(permille)
        assert guardian_gate(seed, "ignite", lib, "reaction") is expected


def test_gate_is_rolled_once_per_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """一題不管試了幾個種子變體，都只擲一次（用題目的種子）。"""
    calls: list[tuple[Any, ...]] = []
    real: Callable[..., Any] = random_composer.guardian_gate

    def counting(*args: Any) -> Any:
        calls.append(args)
        return real(*args)

    monkeypatch.setattr(random_composer, "guardian_gate", counting)
    lib = default_library()
    many_variants = 0
    for seed in range(12):
        calls.clear()
        try:
            found = compose_with_stats(
                seed, tier=3, rarity="epic", keyword="charged", library=lib, kinds=("reaction",)
            )
        except ComposeError:
            assert len(calls) == 1
            continue
        assert len(calls) == 1
        assert calls[0][0] == seed
        many_variants += found.variants > 1
    assert many_variants > 0  # 有題目真的試了好幾個變體


@pytest.mark.parametrize(
    ("keyword", "tier", "rarity"),
    [("ignite", 2, "rare"), ("charged", 3, "epic"), ("prone", 4, "rare")],
)
def test_guardian_share_follows_the_single_roll(keyword: str, tier: int, rarity: str) -> None:
    """沒擲中的題不出護主；護主占合法結果 35% 以下。"""
    lib = default_library()
    delivered = guardian = 0
    for seed in SEEDS:
        skill = _reaction(seed, keyword, tier, rarity)
        if skill is None:
            continue
        delivered += 1
        if _is_guardian(skill):
            guardian += 1
            assert guardian_gate(seed, keyword, lib, "reaction"), seed
    assert delivered >= len(SEEDS) // 2
    assert guardian * 1000 <= GUARDIAN_MAX_PERMILLE * delivered, (guardian, delivered)


@pytest.mark.parametrize("tier", [1, 2, 3, 4])
def test_summon_reactions_still_made_every_tier(tier: int) -> None:
    """召喚關鍵字的反應題照舊：1～4 階都做得出來（護主）。"""
    made = [s for seed in range(6) if (s := _reaction(seed, "summon", tier, "rare")) is not None]
    assert made, tier
    assert any(_is_guardian(s) for s in made)
