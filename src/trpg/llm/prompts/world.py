"""世界觀資料：模型與載入函式已移到 ``trpg.content.world``，這裡重新匯出（4-L4）。"""

from trpg.content.world import (
    DEFAULT_WORLD_FILE,
    GlossaryEntry,
    Realm,
    WorldStyle,
    load_world_style,
)

__all__ = ["DEFAULT_WORLD_FILE", "GlossaryEntry", "Realm", "WorldStyle", "load_world_style"]
