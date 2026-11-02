"""單位卡的「特性」欄（Phase 5A-M1b，玩法決定 #82）：由單位範本產生中文句子。"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary, load_library
from trpg.narrative.unit_traits import unit_trait_lines


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_kin_ward_reaction_is_listed_for_the_sect_family(library: ContentLibrary) -> None:
    lines = unit_trait_lines(library, "sect_acolyte")
    assert any(line.startswith("反應「同門相護」：") for line in lines)


def test_opening_statuses_are_listed(library: ContentLibrary) -> None:
    lines = unit_trait_lines(library, "shard_golem")
    assert any(line.startswith("開場狀態「碎晶」") for line in lines)


def test_elite_affix_template_lists_the_affix_and_its_opening_status(
    library: ContentLibrary,
) -> None:
    lines = unit_trait_lines(library, "sect_acolyte_mist_veiled")
    assert lines[0].startswith("精英詞綴「霧隱」：")
    assert any(line.startswith("開場狀態「隱蔽」，開場 1 回合：") for line in lines)
    assert any(line.startswith("反應「同門相護」：") for line in lines)


def test_unknown_or_plain_templates_have_no_traits(library: ContentLibrary) -> None:
    assert unit_trait_lines(library, "no_such_template") == ()
    plain = [t for t in sorted(library.units) if not unit_trait_lines(library, t)]
    assert plain  # 沒有招牌的單位不會多出空列
