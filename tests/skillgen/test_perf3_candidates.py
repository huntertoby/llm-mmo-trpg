"""PERF-3：指定關鍵字的組合不抽傳說、橋接搜尋的變體數上限（玩法 PM 2026-11-03）。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute
from trpg.skillgen import candidates
from trpg.skillgen.candidates import (
    BRIDGE_VARIANT_CAP,
    CandidateRequest,
    CandidateRules,
    generate_candidates,
)
from trpg.skillgen.random_composer import (
    KEYWORD_TRIES,
    KeywordExhaustedError,
    compose_random_skill,
    compose_with_stats,
)

_HERO = {
    Attribute.STR: 8,
    Attribute.DEX: 14,
    Attribute.CON: 10,
    Attribute.INT: 12,
    Attribute.WIS: 10,
    Attribute.WIL: 8,
}


def _request(seed: int, counts: dict[str, int] | None = None) -> CandidateRequest:
    return CandidateRequest(
        keyword_counts=counts if counts is not None else {"ignite": 2, "charged": 1, "marked": 1},
        weapon_class="melee",
        seed=seed,
        tier=2,
        hero_attributes=_HERO,
        weapon_attrs=(Attribute.DEX,),
    )


def test_keyword_composition_never_legendary() -> None:
    """候選產生器的指定關鍵字組合（``skip_legendary``）不出傳說；其他呼叫（沒指定關鍵字、或沒要求
    跳過）照舊會出傳說。"""
    lib = library()
    for seed in range(60):
        found = compose_with_stats(seed, tier=2, library=lib, keyword="ignite", skip_legendary=True)
        assert found.skill.rarity != "legendary"
    plain = [compose_random_skill(seed, tier=2, library=lib).rarity for seed in range(200)]
    assert "legendary" in plain
    keyed = [
        compose_random_skill(seed, tier=2, library=lib, keyword="ignite").rarity
        for seed in range(200)
    ]
    assert "legendary" in keyed


def test_keyword_variants_reported_and_limited() -> None:
    lib = library()
    found = compose_with_stats(5, tier=2, library=lib, keyword="ignite")
    assert 1 <= found.variants <= KEYWORD_TRIES
    # 第一個變體沒有該關鍵字的種子：只准試 1 個變體時做不出來，例外帶著用掉的變體數
    seed = next(
        s
        for s in range(200)
        if compose_with_stats(s, tier=2, library=lib, keyword="ignite").variants > 1
    )
    with pytest.raises(KeywordExhaustedError) as caught:
        compose_with_stats(seed, tier=2, library=lib, keyword="ignite", keyword_tries=1)
    assert caught.value.variants == 1


def _spy_bridge(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    used: list[int] = []
    original = candidates._bridge

    def bridge(search: Any, *args: Any, **kwargs: Any) -> Any:
        out = original(search, *args, **kwargs)
        used.append(search.bridge_used)
        return out

    monkeypatch.setattr(candidates, "_bridge", bridge)
    return used


@pytest.mark.parametrize("cap", [1, 30])
def test_bridge_cap_bounds_variants_and_keeps_three(
    monkeypatch: pytest.MonkeyPatch, cap: int
) -> None:
    """上限用完就放寬關鍵字（單一關鍵字），三張不少；用掉的變體數不超過上限。"""
    lib = library()
    used = _spy_bridge(monkeypatch)
    rules = CandidateRules(composer_share_permille=1000, bridge_variant_cap=cap)
    for seed in range(4):
        found = generate_candidates(lib, _request(seed), rules)
        assert [c.kind for c in found] == ["deepen", "bridge", "new"]
        assert used[-1] <= cap
        bridge = found[1]
        if len(bridge.keywords) == 1:
            assert bridge.fallback


def test_bridge_cap_deterministic() -> None:
    lib = library()
    rules = CandidateRules(composer_share_permille=1000, bridge_variant_cap=20)

    def dump(found: tuple[candidates.Candidate, ...]) -> list[str]:
        return [c.skill.model_dump_json() for c in found]

    first = generate_candidates(lib, _request(7), rules)
    again = generate_candidates(lib, _request(7), rules)
    assert dump(first) == dump(again)


def test_default_cap() -> None:
    assert CandidateRules().bridge_variant_cap == BRIDGE_VARIANT_CAP > 0


def test_no_cap_means_unlimited(monkeypatch: pytest.MonkeyPatch) -> None:
    """``bridge_variant_cap=0``：不設上限（不計數）。"""
    lib = library()
    used = _spy_bridge(monkeypatch)
    rules = CandidateRules(composer_share_permille=1000, bridge_variant_cap=0)
    found = generate_candidates(lib, _request(2), rules)
    assert len(found) == 3
    assert used == [0]
    assert all(isinstance(c.skill, SkillDef) for c in found)
