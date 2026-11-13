"""TXT-2：許願池兩個關鍵字（玩法 PM 確認 WP-1 第 4 條，補「組合器做得到時，讓其中一張卡同時帶兩個
關鍵字」）。

指定關鍵字模式下，``region_keywords`` 的第 2 個（許願的第 2 個關鍵字）已持有時，橋接先試
「第 1＋第 2」；還沒有時新方向先試（5B-4d 本來就區域偏向排前）。組合器做不到時照舊只帶第 1 個。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

import pytest

from tests.engine.helpers import library
from tests.skillgen.test_pinned_keyword import _request
from trpg.skillgen import candidates
from trpg.skillgen.candidates import CandidateRequest, generate_candidates, skill_has_keywords

COUNTS = {"ignite": 2, "charged": 1, "marked": 1}


def _wish(seed: int, first: str, second: str | None) -> CandidateRequest:
    keywords = (first,) if second is None else (first, second)
    return dataclasses.replace(_request(seed, counts=COUNTS, pin=first), region_keywords=keywords)


def _first_tries(
    monkeypatch: pytest.MonkeyPatch, request: CandidateRequest
) -> dict[str, tuple[str, ...]]:
    """每種候選第一次搜尋的關鍵字組。"""
    seen: dict[str, tuple[str, ...]] = {}
    real = candidates._Search.find

    def spy(self: candidates._Search, rng: object, keywords: Sequence[str], want: object = None):  # type: ignore[no-untyped-def]
        seen.setdefault(self.kind, tuple(keywords))
        return real(self, rng, keywords, want)  # type: ignore[arg-type]

    monkeypatch.setattr(candidates._Search, "find", spy)
    generate_candidates(library(), request)
    return seen


def test_held_second_keyword_is_tried_first_by_the_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 「標記」與「帶電」持有數相同，照推導表順序「帶電」在前；許願的第 2 個是「標記」時橋接先試它
    assert _first_tries(monkeypatch, _wish(7, "ignite", None))["bridge"] == ("ignite", "charged")
    assert _first_tries(monkeypatch, _wish(7, "ignite", "marked"))["bridge"] == ("ignite", "marked")


def test_unheld_second_keyword_is_tried_first_by_new(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _first_tries(monkeypatch, _wish(2, "charged", "wet"))["new"] == ("charged", "wet")


@pytest.mark.parametrize(
    ("seed", "first", "second", "kind"),
    [
        (7, "ignite", "marked", "bridge"),  # 已持有：橋接那張帶兩個
        (5, "ignite", "prone", "new"),  # 還沒有：新方向那張帶兩個
        (2, "charged", "wet", "new"),
    ],
)
def test_one_card_carries_both_when_the_composer_can(
    seed: int, first: str, second: str, kind: str
) -> None:
    lib = library()
    found = generate_candidates(lib, _wish(seed, first, second))
    both = [c for c in found if set(c.keywords) == {first, second}]
    assert [c.kind for c in both] == [kind]
    assert skill_has_keywords(both[0].skill, (first, second), lib)
    assert all(c.keywords[0] == first for c in found)  # 三張照舊都帶第 1 個


def test_composer_cannot_falls_back_to_the_first_keyword() -> None:
    """做不到時照舊：三張都只保證帶第 1 個（「帶電＋點燃」這個種子組不出來）。"""
    found = generate_candidates(library(), _wish(1, "charged", "ignite"))
    assert found and all(c.keywords[0] == "charged" for c in found)
    assert not any(set(c.keywords) == {"charged", "ignite"} for c in found)


def test_single_keyword_order_is_unchanged() -> None:
    """機遇、故事事件等其他指定關鍵字的呼叫端只傳指定關鍵字本身：結果和沒有區域偏向時相同。"""
    lib = library()
    for seed in (1, 7, 23):
        plain = _request(seed, counts=COUNTS, pin="ignite")
        pinned_only = dataclasses.replace(plain, region_keywords=("ignite",))
        assert generate_candidates(lib, plain) == generate_candidates(lib, pinned_only)
