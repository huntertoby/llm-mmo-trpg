"""HC-5b（QF-4b 裁定 2）：伴生配方照護主快取預算比例；快取不改亂數與結果。"""

from __future__ import annotations

from dataclasses import replace

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.skillgen.composer_recipes import is_companion, passive_recipes
from trpg.skillgen.memo import library_memo
from trpg.skillgen.random_composer import compose_random_skill


def _fresh() -> ContentLibrary:
    """換一個內容庫物件：快取表掛在內容庫上，``replace`` 後是新的空表。"""
    return replace(library())


def test_the_companion_recipe_is_recognised() -> None:
    found = [r for r in passive_recipes(library(), 2) if is_companion(r)]
    assert found


def test_cached_and_uncached_companion_skills_are_the_same() -> None:
    """同一批種子：第一次（空快取）與第二次（快取命中）做出的技能逐位元組相同。"""
    lib = _fresh()
    seeds = range(40)

    def run() -> list[str]:
        out: list[str] = []
        for seed in seeds:
            skill = compose_random_skill(
                seed, tier=2, rarity="epic", skeleton="passive", library=lib, keyword="summon"
            )
            out.append(skill.model_dump_json())
        return out

    first = run()
    assert library_memo(lib, "composer.companion.ratio")  # 有伴生被抽到、快取有東西
    assert run() == first
    assert first == [s for s in _run_on(_fresh(), seeds)]


def _run_on(lib: ContentLibrary, seeds: range) -> list[str]:
    return [
        compose_random_skill(
            seed, tier=2, rarity="epic", skeleton="passive", library=lib, keyword="summon"
        ).model_dump_json()
        for seed in seeds
    ]
