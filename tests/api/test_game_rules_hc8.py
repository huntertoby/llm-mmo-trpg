"""HC-8：``/api/glossary`` 的 ``rules`` 多四個屬性點說明組字用的欄位：伺服器一律由內容庫填，
欄位的預設值（規格要求有預設值）等於目前的內容。"""

from __future__ import annotations

from trpg.api.glossary import build_glossary
from trpg.api.schemas import GameRulesOut
from trpg.content.library import load_library

FIELDS = ("quantity_scale", "attribute_points_per_level", "base_attribute", "start_free_points")


def test_attribute_fields_follow_data() -> None:
    library = load_library()
    rules = build_glossary(library).rules
    run = library.roguelite
    assert rules.quantity_scale == library.ruleset.core.quantity_scale
    assert rules.attribute_points_per_level == run.attribute_points_per_level
    assert rules.base_attribute == run.base_attribute
    assert rules.start_free_points == run.start_free_points


def test_defaults_equal_current_content() -> None:
    rules = build_glossary(load_library()).rules
    for name in FIELDS:
        assert GameRulesOut.model_fields[name].default == getattr(rules, name), name
