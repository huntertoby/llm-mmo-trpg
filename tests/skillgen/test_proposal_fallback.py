"""4-L5：退回（組合器 → 技能池 → 工坊推導）。"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.content.library import ContentLibrary
from trpg.skillgen import proposal_fallback
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import FallbackError, fallback_skill, wanted_kind
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.random_composer import ComposeError, default_library
from trpg.skillgen.validate import validate_skill


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


def _ctx(request: ProposalRequest) -> ProposalContext:
    return ProposalContext(request.tier, request.rarity)


def _no_composer(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: Any, **__: Any) -> Any:
        raise ComposeError("測試：組合器失敗")

    monkeypatch.setattr(proposal_fallback, "compose_random_skill", fail)


def test_composer_first_with_keywords(library: ContentLibrary) -> None:
    request = ProposalRequest(1, "rare", keywords=("ignite",))
    skill, source = fallback_skill(library, request, _ctx(request), seed=4)
    assert source == "composer"
    assert skill.tier == 1 and skill.rarity == "rare" and skill.kind == "active"
    assert skill_has_keywords(skill, ("ignite",), library)
    assert validate_skill(skill, library) == []
    again, _ = fallback_skill(library, request, _ctx(request), seed=4)
    assert again == skill


@pytest.mark.parametrize(
    ("request_", "kind"),
    [
        (ProposalRequest(1, "epic", kind="passive"), "passive"),
        (ProposalRequest(2, "rare", kind="stance"), "stance"),  # 姿態要角色 2 階（3W-9）
        (ProposalRequest(1, "common", skeleton="strike"), "active"),
    ],
)
def test_composer_respects_kind_and_skeleton(
    library: ContentLibrary, request_: ProposalRequest, kind: str
) -> None:
    skill, source = fallback_skill(library, request_, _ctx(request_), seed=2)
    assert source == "composer" and skill.kind == kind == wanted_kind(library, request_)
    if request_.skeleton is not None:
        assert skill.skeleton == request_.skeleton


def test_pool_when_composer_fails(library: ContentLibrary, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_composer(monkeypatch)
    request = ProposalRequest(1, "rare", keywords=("ignite",))
    skill, source = fallback_skill(library, request, _ctx(request), seed=4)
    assert source == "pool"
    assert skill.id in library.skills and skill.tier == 1 and skill.rarity == "rare"
    assert skill_has_keywords(skill, ("ignite",), library)


def test_workshop_when_composer_and_pool_fail(
    library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_composer(monkeypatch)
    monkeypatch.setattr(proposal_fallback, "_from_pool", lambda *_: None)
    for request in (
        ProposalRequest(1, "common", skeleton="strike"),
        ProposalRequest(1, "rare"),
        ProposalRequest(1, "epic", kind="passive"),
    ):
        skill, source = fallback_skill(library, request, _ctx(request), seed=4)
        assert source == "workshop"
        assert skill.id.startswith("skill_ws_") and validate_skill(skill, library) == []
        assert skill.kind == wanted_kind(library, request)
        assert skill.provenance.created_by == "workshop"
        again, _ = fallback_skill(library, request, _ctx(request), seed=4)
        assert again == skill


def test_all_sources_fail(library: ContentLibrary, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_composer(monkeypatch)
    monkeypatch.setattr(proposal_fallback, "_from_pool", lambda *_: None)
    monkeypatch.setattr(proposal_fallback, "_from_workshop", lambda *_: None)
    request = ProposalRequest(1, "rare")
    with pytest.raises(FallbackError, match="退回失敗"):
        fallback_skill(library, request, _ctx(request), seed=4)
