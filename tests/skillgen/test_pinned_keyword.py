"""skillgen「指定關鍵字」模式（Phase 5B-4d；Phase5計畫 24.5；07 7.6「關鍵字由觸發情境決定」）。"""

from __future__ import annotations

import dataclasses

import pytest

from tests.engine.helpers import library
from trpg.shared.types import Attribute
from trpg.skillgen import candidates
from trpg.skillgen.candidates import (
    CandidateRequest,
    CandidateRules,
    generate_candidates,
    skill_has_keywords,
)

_HERO = {
    Attribute.STR: 8,
    Attribute.DEX: 14,
    Attribute.CON: 10,
    Attribute.INT: 12,
    Attribute.WIS: 10,
    Attribute.WIL: 8,
}

PIN = "charged"


def _request(
    seed: int, counts: dict[str, int] | None = None, pin: str | None = PIN
) -> CandidateRequest:
    return CandidateRequest(
        keyword_counts=counts if counts is not None else {"ignite": 2, "charged": 1, "marked": 1},
        weapon_class="melee",
        seed=seed,
        tier=2,
        hero_attributes=_HERO,
        weapon_attrs=(Attribute.DEX,),
        pinned_keyword=pin,
    )


@pytest.mark.parametrize("seed", [1, 7, 23])
def test_all_three_carry_the_pinned_keyword(seed: int) -> None:
    lib = library()
    found = generate_candidates(lib, _request(seed))
    assert [c.kind for c in found] == ["deepen", "bridge", "new"]
    for candidate in found:
        assert candidate.keywords[0] == PIN
        assert skill_has_keywords(candidate.skill, candidate.keywords, lib)
    assert len({c.skill.id for c in found}) == 3
    deepen, bridge, new = found
    assert deepen.keywords == (PIN,) and not deepen.fallback  # 已持有：加深
    held = {"ignite", "marked"}
    if not bridge.fallback:  # 橋接＝指定＋另一個持有的
        assert len(bridge.keywords) == 2 and bridge.keywords[1] in held
    else:
        assert bridge.keywords == (PIN,)
    if not new.fallback:  # 新方向＝指定＋還沒有的
        assert len(new.keywords) == 2 and new.keywords[1] not in {*held, PIN}
    else:
        assert new.keywords == (PIN,)


def test_unheld_pin_is_fallback_deepen() -> None:
    lib = library()
    found = generate_candidates(lib, _request(3, counts={"ignite": 2}))
    assert found and all(c.keywords[0] == PIN for c in found)
    assert found[0].fallback  # 角色沒有「帶電」：加深是退回


def test_deterministic_and_none_is_unchanged() -> None:
    lib = library()
    assert generate_candidates(lib, _request(11)) == generate_candidates(lib, _request(11))
    plain = _request(11, pin=None)
    assert plain == dataclasses.replace(_request(11), pinned_keyword=None)
    assert generate_candidates(lib, plain) != generate_candidates(lib, _request(11))
    # 沒指定時和 PERF-3 一樣：不帶 pinned_keyword 欄位的請求結果逐字相同
    legacy = CandidateRequest(
        keyword_counts={"ignite": 2, "charged": 1, "marked": 1},
        weapon_class="melee",
        seed=11,
        tier=2,
        hero_attributes=_HERO,
        weapon_attrs=(Attribute.DEX,),
    )
    assert generate_candidates(lib, legacy) == generate_candidates(lib, plain)


def test_unknown_pin_rejected() -> None:
    with pytest.raises(ValueError, match="指定關鍵字"):
        generate_candidates(library(), _request(1, pin="no_such_keyword"))


def test_caps_are_counted_per_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    """橋接與新方向的多關鍵字搜尋各自受 ``bridge_variant_cap`` 管（代決 5B4d-7）。"""
    seen: list[tuple[int, int]] = []
    original = candidates._pinned

    def spy(search: candidates._Search, *args: object) -> list[candidates.Candidate | None]:
        out = original(search, *args)  # type: ignore[arg-type]
        seen.append((search.bridge_used, search.pinned_new_used))
        return out

    monkeypatch.setattr(candidates, "_pinned", spy)
    cap = 20
    found = generate_candidates(library(), _request(5), CandidateRules(bridge_variant_cap=cap))
    assert len(found) == 3 and all(c.keywords[0] == PIN for c in found)
    bridge_used, new_used = seen[0]
    assert bridge_used <= cap and new_used <= cap
