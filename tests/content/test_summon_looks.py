"""召喚物外觀（Phase 3-33h1）：外觀表 schema、範本外觀由表查得、視圖帶出外觀欄位。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.battle import SummonLook, UnitTemplate
from trpg.content.summons import load_summon_looks

CONTENT = PROJECT_ROOT / "content"


def test_the_look_table_loads() -> None:
    table = load_summon_looks(CONTENT)
    assert len(table.looks) == 19  # 17 種特色召喚物＋通用的元素之靈＋狐火誘餌（3R-2）
    bodies = {e.body for e in table.looks.values()}
    assert bodies == {"humanoid", "spirit", "construct", "beast", "plant", "totem"}


def test_every_summon_template_resolves_its_look_from_the_table() -> None:
    table = load_summon_looks(CONTENT).looks
    summons = library().ruleset.summons.summons
    assert len(summons) == len(table)
    for summon in summons:
        entry = table[summon.id.removeprefix("summon_")]
        look = summon.template.look
        assert look is not None, summon.id
        assert look == SummonLook.model_validate(entry.model_dump(exclude={"zh"})), summon.id


def test_template_files_do_not_carry_their_own_look() -> None:
    for path in sorted((CONTENT / "units" / "summons").glob("*.yaml")):
        assert "\nlook:" not in "\n" + path.read_text(encoding="utf-8"), path.name


def test_unknown_trait_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SummonLook.model_validate({"body": "totem", "trait": "sparkle"})
    traits = (
        "shield",
        "translucent",
        "glow",
        "puddle",
        "fuse",
        "no_ring",
        "flying",
        "ground",
        "aura",
    )
    for trait in traits:
        assert SummonLook.model_validate({"body": "totem", "trait": trait}).trait == trait


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
