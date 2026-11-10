"""PERF-4 R3：``build_subset_models`` 的記憶化不改變結果，範圍正確，而且有上限。"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import replace

import pytest

from trpg.content.library import ContentLibrary
from trpg.skillgen import proposal_subset
from trpg.skillgen.proposal_subset import (
    ProposalRequest,
    ProposalSubset,
    _build_subset_models,
    build_subset_models,
    select_subset,
)

REQUESTS = (
    ProposalRequest(tier=1, rarity="common"),
    ProposalRequest(tier=1, rarity="rare", skeleton="strike"),
    ProposalRequest(tier=1, rarity="legendary", skeleton="control", keywords=("wet",)),
    ProposalRequest(tier=3, rarity="epic", skeleton="control", keywords=("wet", "ignite")),
    ProposalRequest(tier=2, rarity="legendary", skeleton="control"),
    ProposalRequest(tier=2, rarity="rare", menu_seed=7),
    ProposalRequest(tier=1, rarity="legendary", kind="reaction"),
)


@pytest.fixture(autouse=True)
def _empty_cache() -> Iterator[None]:
    """快取是行程內共用的：測試前後都清掉，不影響同 worker 的其他測試。"""
    proposal_subset._models_cache.clear()
    yield
    proposal_subset._models_cache.clear()


def _subset(library: ContentLibrary, request: ProposalRequest) -> ProposalSubset:
    return select_subset(library, request)


@pytest.mark.parametrize("request_", REQUESTS, ids=repr)
def test_memoized_models_match_a_fresh_build(
    content_library: ContentLibrary, request_: ProposalRequest
) -> None:
    subset = _subset(content_library, request_)
    fresh = _build_subset_models(content_library, subset)
    first = build_subset_models(content_library, subset)
    again = build_subset_models(content_library, subset)
    assert again is first
    assert first.json_schema() == fresh.json_schema()
    assert again.json_schema() == fresh.json_schema()
    assert first.primitive_ids == fresh.primitive_ids
    assert first.variant_primitive_ids == fresh.variant_primitive_ids
    assert first.excluded_primitives == fresh.excluded_primitives
    assert first.layouts == fresh.layouts
    assert first.kinds == fresh.kinds


def test_presentation_only_fields_share_one_entry(content_library: ContentLibrary) -> None:
    subset = _subset(content_library, REQUESTS[0])
    first = build_subset_models(content_library, subset)
    assert build_subset_models(content_library, replace(subset, menu_seed=99, tokens=1)) is first


_OTHER = "__other__"
KEY_CHANGES: dict[str, Callable[[ProposalSubset], ProposalSubset]] = {
    "primitives": lambda s: replace(s, primitives=(*s.primitives, _OTHER)),
    "shapes": lambda s: replace(s, shapes=(*s.shapes, _OTHER)),
    "conditions": lambda s: replace(s, conditions=(*s.conditions, _OTHER)),
    "triggers": lambda s: replace(s, triggers=(*s.triggers, _OTHER)),
    "skeletons": lambda s: replace(s, skeletons=(*s.skeletons, _OTHER)),
    "rarity": lambda s: replace(s, rarity=None),
    "followup_skeletons": lambda s: replace(s, followup_skeletons=(_OTHER,)),
    "followup_shapes": lambda s: replace(s, followup_shapes=(_OTHER,)),
    "followup_moves": lambda s: replace(s, followup_moves=(_OTHER,)),
}


@pytest.mark.parametrize("field", sorted(KEY_CHANGES))
def test_every_model_input_is_part_of_the_key(content_library: ContentLibrary, field: str) -> None:
    subset = _subset(content_library, REQUESTS[4])
    changed = KEY_CHANGES[field](subset)
    assert proposal_subset._models_key(changed) != proposal_subset._models_key(subset)


def test_another_library_object_is_not_shared(content_library: ContentLibrary) -> None:
    subset = _subset(content_library, REQUESTS[0])
    first = build_subset_models(content_library, subset)
    other = replace(content_library)
    assert build_subset_models(other, subset) is not first


def test_cache_is_bounded_and_drops_the_oldest(
    content_library: ContentLibrary, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(proposal_subset, "_MODELS_CACHE_SIZE", 2)
    subset = _subset(content_library, REQUESTS[0])
    copies = [replace(content_library) for _ in range(3)]
    oldest = build_subset_models(copies[0], subset)
    build_subset_models(copies[1], subset)
    build_subset_models(copies[2], subset)
    assert len(proposal_subset._models_cache) == 2
    assert all(entry[0] is not copies[0] for entry in proposal_subset._models_cache.values())
    assert build_subset_models(copies[0], subset) is not oldest
