"""測試用：開局的規則數字（HC-7 起在 ``content/world/newcomer.yaml``），照正式內容讀一次。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.world.opening_limits import opening_end_level, starter_steps

OPENING_END_LEVEL = opening_end_level(library())
"""開局結束的等級（``opening_end_level``）。"""
STARTER_STEPS = starter_steps(library())
"""入門期的新手任務步數（``starter_steps``）。"""
