"""召喚物外觀（Phase 3-33h1）：外觀表 schema、範本外觀與表一致、視圖帶出外觀欄位。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.battle import SummonLook, UnitTemplate
from trpg.content.summons import load_summon_looks

CONTENT = PROJECT_ROOT / "content"


def test_the_seventeen_looks_load() -> None:
    table = load_summon_looks(CONTENT)
    assert len(table.looks) == 17
    bodies = {e.body for e in table.looks.values()}
    assert bodies == {"humanoid", "spirit", "construct", "beast", "plant", "totem"}


def test_existing_summon_templates_match_the_table() -> None:
    by_name = {e.zh: e for e in load_summon_looks(CONTENT).looks.values()}
    for summon in library().ruleset.summons.summons:
        look = summon.template.look
        assert look is not None, summon.id
        entry = by_name.get(summon.template.name_zh)
        if entry is None:  # 元素之靈是通用的靈，沒有對應的單一列
            assert look.body == "spirit"
            continue
        got = (look.body, look.variant, look.element, look.size, look.trait)
        assert got == (entry.body, entry.variant, entry.element, entry.size, entry.trait)


def test_look_elements_are_known_keywords() -> None:
    keywords = {k.id for k in library().ruleset.keywords.keywords}
    for entry in load_summon_looks(CONTENT).looks.values():
        assert entry.element is None or entry.element in keywords, entry.zh


def test_unknown_body_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SummonLook.model_validate({"body": "dragon"})


def test_look_only_for_summons() -> None:
    base = library().ruleset.summons.summons[0].template.model_dump()
    base["summon"] = False
    base["role"] = None
    base["totem"] = None
    with pytest.raises(ValidationError, match="外觀欄位"):
        UnitTemplate.model_validate(base)
