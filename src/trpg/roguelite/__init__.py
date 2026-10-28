"""單人 roguelite 原型循環（Phase 3-5a）：一輪流程、地圖與遭遇抽選、升級選技能、本機存檔。

- ``state``：``RunState``（可序列化的一輪進度）、節點與選擇。
- ``start``：開新一輪（起始武器 ＋ 關鍵字、開發者起始包、回歸範本；開局配點、每一場的安排）。
- ``offers``：升級與重骰的技能候選（隨機組合器）、裝備上限檢查。
- ``progress``：開戰設定、戰後結算、選擇、下一個節點（純函式）。
- ``battle``：進行中的戰鬥（``setup ＋ seed ＋ 步驟 ＋ 指令``，可重播）。
- ``save``：存檔格式 ``trpg-run/6``。
- ``auto``：AI 代打整輪。

參數在 ``content/roguelite.yaml``。依賴：可匯入 ``engine``、``content``、``skillgen``、``shared``；
不得匯入 ``api``、``cli``、``sim``、``llm``、``narrative``。
確定性：禁止使用 ``random`` 模組與讀取時間；所有亂數由一輪的種子以 ``trpg.shared.rng.Rng`` 衍生。
"""

from __future__ import annotations

from trpg.roguelite.auto import auto_choice, auto_play
from trpg.roguelite.battle import ActiveBattle, SavedBattle
from trpg.roguelite.errors import ChoiceError, NodeConflictError, RunError, SaveFormatError
from trpg.roguelite.progress import apply_choice, battle_setup, finish_battle, next_node
from trpg.roguelite.save import (
    SAVE_FORMAT,
    RunSave,
    dumps_save,
    load_save,
    loads_save,
    restore_battle,
    ruleset_hash,
    save_path,
    write_save,
)
from trpg.roguelite.start import new_dev_run, new_keyword_run, new_run
from trpg.roguelite.state import RunState

__all__ = [
    "SAVE_FORMAT",
    "ActiveBattle",
    "ChoiceError",
    "NodeConflictError",
    "RunError",
    "RunSave",
    "RunState",
    "SaveFormatError",
    "SavedBattle",
    "apply_choice",
    "auto_choice",
    "auto_play",
    "battle_setup",
    "dumps_save",
    "finish_battle",
    "load_save",
    "loads_save",
    "new_dev_run",
    "new_keyword_run",
    "new_run",
    "next_node",
    "restore_battle",
    "ruleset_hash",
    "save_path",
    "write_save",
]
