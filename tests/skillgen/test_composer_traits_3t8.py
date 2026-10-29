"""骨架專屬的組合器設定來自 YAML（Phase 3T-8）。"""

from __future__ import annotations

import pytest

from tests.skillgen.helpers import lib
from trpg.content.skill_rules import ComposerTraits
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.composer_parts import Ctx, choose_core


def test_composer_traits_in_yaml() -> None:
    skeletons = lib().skeletons
    by_trait = {
        "legendary": {"aura", "modifier"},
        "explicit_only_active": {"builder_finisher", "trap", "rune", "sacrifice"},
        "hand_written_only": {"consume_status", "summon"},
    }
    for trait, expected in by_trait.items():
        assert {n for n, s in skeletons.items() if getattr(s.composer, trait)} == expected
    assert skeletons["control"].composer.core_count == "up_to_two"
    assert skeletons["displace"].composer.core_count == "second_by_chance"
    assert skeletons["trap"].composer.setup == "trap"
    assert skeletons["builder_finisher"].composer.setup == "stack"


@pytest.mark.parametrize("seed", range(20))
def test_core_count_follows_the_trait_not_the_id(seed: int) -> None:
    """控場骨架換成預設設定後，核心數量固定 1（不看骨架 ID）。"""
    library = lib()
    plain = library.skeletons["control"].model_copy(update={"composer": ComposerTraits()})
    ctx = Ctx(library, Rng(seed), plain, "legendary", 3, "spell", 1, Element.FIRE)
    assert len(choose_core(ctx)) == 1
