"""一輪的存檔（Phase 3-5a；``docs/phases/Phase3計畫.md`` 0.2 E）。

存檔是一個 JSON 物件：

- ``format``：:data:`SAVE_FORMAT`（``trpg-run/1``）。讀檔時必須相同，否則拒絕。
- ``engine``：寫入時引擎的戰鬥紀錄格式（``LOG_FORMAT``）。只有 **戰鬥進行中** 的存檔需要重播；
  此時版本不同就拒絕（舊版引擎的步驟不保證能在新版重播出同樣結果）。戰鬥之間的存檔不受影響。
- ``run_id``：一輪的 ID（檔名 ``run-<run_id>.json``）。
- ``run``：:class:`~trpg.roguelite.state.RunState`（主角、進度、生成技能定義、每一場的安排、歷程、
  目前節點與候選）。
- ``ruleset_hash``：寫入時內容庫的穩定雜湊（:func:`ruleset_hash`，Phase 3-5c-1）。可省略（舊存檔）；
  戰鬥中的存檔讀檔時要與目前的內容庫相同（沒有此欄位視為不符），戰鬥之間的存檔不檢查。
- ``battle``：進行中的戰鬥（:class:`~trpg.roguelite.battle.SavedBattle`：種子、步驟、指令），
  沒有時為 ``null``。

存檔不含亂數狀態：一輪的所有亂數都由 ``run.seed`` 以標籤衍生（計數器 ``offers_made`` 在 ``run``
裡），戰鬥的亂數狀態由「種子 ＋ 步驟」重播得到。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.library import ContentLibrary
from trpg.engine.runner import LOG_FORMAT
from trpg.roguelite.battle import ActiveBattle, SavedBattle
from trpg.roguelite.errors import SaveFormatError
from trpg.roguelite.state import BattleNode, RunState

__all__ = [
    "RUN_ID_PATTERN",
    "SAVE_DIR_ENV",
    "SAVE_FORMAT",
    "RunSave",
    "default_save_dir",
    "dumps_save",
    "load_save",
    "loads_save",
    "restore_battle",
    "ruleset_hash",
    "save_path",
    "write_save",
]

SAVE_FORMAT = "trpg-run/1"
RUN_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SAVE_DIR_ENV = "TRPG_SAVE_DIR"
"""可覆寫存檔資料夾的環境變數。"""


def default_save_dir() -> Path:
    """存檔資料夾：環境變數 ``TRPG_SAVE_DIR``，否則專案根目錄的 ``saves/``（在 .gitignore 內）。"""
    override = os.environ.get(SAVE_DIR_ENV)
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "saves"


class RunSave(BaseModel):
    """存檔的內容（見模組說明）。"""

    model_config = ConfigDict(extra="forbid")

    format: str = SAVE_FORMAT
    engine: str = LOG_FORMAT
    run_id: str
    run: RunState
    battle: SavedBattle | None = None
    ruleset_hash: str | None = None


def ruleset_hash(library: ContentLibrary) -> str:
    """內容庫的穩定 SHA-256（全部內容檔的相對路徑與排序鍵 JSON；不用內建 ``hash()``）。"""
    items = [
        [path.relative_to(library.root).as_posix(), model.model_dump(mode="json")]
        for path, model in sorted(
            library.files, key=lambda f: f[0].relative_to(library.root).as_posix()
        )
    ]
    text = json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dumps_save(save: RunSave) -> str:
    return save.model_dump_json(indent=1)


def loads_save(text: str) -> RunSave:
    """解析存檔；格式不對、版本不符時拋出 :class:`SaveFormatError`。"""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SaveFormatError(f"存檔不是有效的 JSON：{exc}") from exc
    found = raw.get("format") if isinstance(raw, dict) else None
    if found != SAVE_FORMAT:
        raise SaveFormatError(f"存檔格式必須是 {SAVE_FORMAT}，收到 {found!r}")
    try:
        save = RunSave.model_validate(raw)
    except ValidationError as exc:
        raise SaveFormatError(f"存檔內容不合法：{exc.error_count()} 個錯誤：{exc}") from exc
    if save.battle is not None:
        if save.engine != LOG_FORMAT:
            raise SaveFormatError(
                f"這是戰鬥中的存檔，寫入時的引擎版本 {save.engine} 與目前的 {LOG_FORMAT} 不同，"
                "無法重播"
            )
        if not isinstance(save.run.node, BattleNode):
            raise SaveFormatError("存檔有進行中的戰鬥，但一輪的節點不是戰鬥")
    if re.match(RUN_ID_PATTERN, save.run_id) is None:
        raise SaveFormatError(f"不合法的 run_id：{save.run_id!r}")
    return save


def save_path(save_dir: Path, run_id: str) -> Path:
    if re.match(RUN_ID_PATTERN, run_id) is None:
        raise SaveFormatError(f"不合法的 run_id：{run_id!r}")
    return save_dir / f"run-{run_id}.json"


def write_save(save_dir: Path, save: RunSave) -> Path:
    """寫入 ``save_dir/run-<run_id>.json``（資料夾不存在時建立），回傳路徑。"""
    path = save_path(save_dir, save.run_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_save(save), encoding="utf-8", newline="\n")
    return path


def load_save(path: Path) -> RunSave:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SaveFormatError(f"無法讀取存檔 {path}：{exc}") from exc
    return loads_save(text)


def restore_battle(library: ContentLibrary, save: RunSave) -> ActiveBattle | None:
    """重播存檔中進行中的戰鬥（沒有時 ``None``）。"""
    if save.battle is None:
        return None
    return ActiveBattle.restore(library, save.run, save.battle)
