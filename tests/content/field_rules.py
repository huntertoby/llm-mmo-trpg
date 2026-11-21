"""實地地圖檢查要用的世界規則（HC-4d：大小建議與每區傳送石數在 ``world/rules.yaml`` 的
``field_maps``）。"""

from __future__ import annotations

from trpg.content.fields import FieldMapRules
from trpg.content.library import ContentLibrary


def field_map_rules(library: ContentLibrary) -> FieldMapRules:
    """內容庫的 ``world/rules.yaml`` ``field_maps``。"""
    assert library.world_rules is not None
    return library.world_rules.field_maps
