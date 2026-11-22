"""GS-1（#172）：「形態」關鍵字只出在主動題（含姿態），被動、反應題抽關鍵字時不抽它。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from trpg.content.skills.constants import SkillRarity
from trpg.skillgen.candidates import composer_kinds, topic_kinds
from trpg.skillgen.proposal_subset import ProposalRequest, SubsetError, select_subset
from trpg.skillgen.random_composer import default_library
from trpg.skillgen.whiteboard_candidates import _ensure_passive

FORM = "form"
NON_ACTIVE = ("passive", "reaction")
RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic")


def test_only_form_is_active_only() -> None:
    lib = default_library()
    assert [k.id for k in lib.keywords.keywords if k.active_only] == [FORM]
    for kind in NON_ACTIVE:
        assert not lib.keywords.topic_allows(FORM, kind)
        assert lib.keywords.topic_allows("ignite", kind)
    for other in ("active", "stance", None):
        assert lib.keywords.topic_allows(FORM, other)
    assert lib.keywords.topic_allows("no_such_keyword", "passive")  # 未知 ID 交給原本的檢查


@pytest.mark.parametrize("kind", NON_ACTIVE)
def test_passive_and_reaction_topics_never_take_form(kind: str) -> None:
    """出題檢查（``select_subset``，LLM 出題與盤點的「會出題」都用它）：被動、反應題指定形態
    一律不出；其他關鍵字不受影響。"""
    lib = default_library()
    for tier in (1, 2, 3, 4):
        for rarity in RARITIES:
            with pytest.raises(SubsetError, match="只出在主動題"):
                select_subset(lib, ProposalRequest(tier, rarity, kind=kind, keywords=(FORM,)))
    select_subset(lib, ProposalRequest(2, "epic", kind=kind, keywords=("ignite",)))


def test_active_topics_still_take_form() -> None:
    lib = default_library()
    try:
        select_subset(lib, ProposalRequest(2, "rare", kind="active", keywords=(FORM,)))
    except SubsetError as exc:
        assert "只出在主動題" not in str(exc)


def test_rolled_kinds_turn_active_for_form() -> None:
    """三選一、許願擲到的種類（主動 70／被動 20／反應 10）：關鍵字是形態時，0 次是被動或反應。"""
    lib = default_library()
    rolled: set[str] = set()
    for seed in range(200):
        kinds = composer_kinds(lib, seed, "new")
        rolled.update(kinds)
        assert not set(topic_kinds(lib, kinds, (FORM,))) & set(NON_ACTIVE), seed
        assert topic_kinds(lib, kinds, ("ignite",)) == kinds
    assert set(NON_ACTIVE) <= rolled  # 樣本裡真的擲到過被動與反應


def test_passive_floor_skips_form() -> None:
    """白板三選一的被動保底：試的關鍵字裡沒有形態（持有、沒持有、原本的都一樣）。"""
    lib = default_library()
    tried: list[str] = []

    def make_kind(_rng: Any, keyword: str, _want: Any, board_kind: str) -> None:
        assert board_kind == "passive"
        tried.append(keyword)

    maker = SimpleNamespace(
        library=lib,
        request=SimpleNamespace(seed=3, min_passive=1),
        make_kind=make_kind,
        taken=set(),
    )
    found = [
        SimpleNamespace(kind="new", keywords=(FORM,), skill=SimpleNamespace(kind="active")),
        SimpleNamespace(kind="deepen", keywords=("ignite",), skill=SimpleNamespace(kind="active")),
    ]
    _ensure_passive(maker, found, held=(FORM, "ignite"), unheld=("wet", FORM))  # type: ignore[arg-type]
    assert tried
    assert FORM not in tried
