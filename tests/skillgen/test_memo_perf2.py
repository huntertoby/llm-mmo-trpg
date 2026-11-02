"""組合器快取（PERF-2，:mod:`trpg.skillgen.memo`）：只影響速度，不影響結果。"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.skillgen.helpers import lib
from trpg.content.keyword_derive import derive_keywords
from trpg.skillgen import memo
from trpg.skillgen.composer_special import compose_legendary
from trpg.skillgen.keywords import has_keyword
from trpg.skillgen.random_composer import ComposeError, compose_random_skill


def test_has_keyword_matches_derive_keywords() -> None:
    library = lib()
    ids = [k.id for k in library.keywords.keywords]
    for skill in library.skills.values():
        found = set(derive_keywords(skill, library.keywords).all())
        for keyword in ids:
            assert has_keyword(skill, keyword, library.keywords) == (keyword in found), (
                skill.id,
                keyword,
            )
        assert not has_keyword(skill, "no_such_keyword", library.keywords)


def test_by_id_is_shared_and_equal() -> None:
    statuses = lib().ruleset.statuses
    first = memo.by_id(statuses)
    assert first == statuses.by_id()
    assert memo.by_id(statuses) is first


def test_draft_key_ignores_seed_fields_only() -> None:
    base = {"id": "skill_rand_1", "narrative": {"concept": "種子 1"}, "tier": 2}
    base["cost"] = {"mana": 4}
    same = {**base, "id": "skill_rand_99", "narrative": {"concept": "種子 99"}}
    assert memo.draft_key(base) == memo.draft_key(same)
    assert memo.draft_key(base) != memo.draft_key({**base, "cost": {"mana": 8}})
    assert memo.draft_key(base) != memo.draft_key({**base, "tier": 3})
    assert memo.draft_key({**base, "odd": object()}) is None


def test_library_memo_is_per_library() -> None:
    library = lib()
    other = replace(library)
    table = memo.library_memo(library, "t")
    table["k"] = 1
    assert memo.library_memo(library, "t") is table
    assert memo.library_memo(other, "t") == {}


@pytest.mark.parametrize("seed", [3, 17, 2024, 90001])
def test_legendary_same_cold_and_warm(seed: int) -> None:
    library = lib()
    memo.clear_memos()
    cold = compose_legendary(seed, library, tier=2)
    warm = compose_legendary(seed, library, tier=2)
    assert (cold is None) == (warm is None)
    if cold is not None and warm is not None:
        assert cold.model_dump_json() == warm.model_dump_json()


@pytest.mark.parametrize(("seed", "keyword"), [(5, "ignite"), (77, "charged"), (123, "frozen")])
def test_keyword_compose_same_cold_and_warm(seed: int, keyword: str) -> None:
    library = lib()

    def compose() -> str | None:
        try:
            skill = compose_random_skill(seed, tier=2, library=library, keyword=keyword)
        except ComposeError:
            return None
        return skill.model_dump_json()

    memo.clear_memos()
    cold = compose()
    assert compose() == cold
