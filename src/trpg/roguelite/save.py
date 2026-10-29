"""一輪的存檔（Phase 3-5a；``docs/phases/Phase3計畫.md`` 0.2 E）。

存檔是一個 JSON 物件：

- ``format``：:data:`SAVE_FORMAT`（``trpg-run/13``）。讀檔時必須是它或 :data:`COMPATIBLE_FORMATS`
  （``trpg-run/5``～``/12``），否則拒絕；舊格式讀入後寫出為 ``/13``。
  Phase 3W-5b 起引擎沒有技能等級：主角範本（``run.hero``）少了 ``skill_levels``（``/13``）；舊存檔
  由 :func:`convert_raw_hero` 拿掉這個欄位（3W-5 起一輪已不再帶入等級，值一定是空的或作廢）。
  Phase 3W-5 起技能點、技能等級與分歧進化取消，改成靈感點與閃現（``/12``：``run.insight``、
  ``run.flash``、``run.flash_bases``、``run.pending_flash``、``run.complete_offers_done``、
  ``run.flash_llm_log``、節點 ``complete_offer``；營火沒有重骰）。舊存檔由 :func:`convert_raw_run`
  轉換（玩法 PM 已確認，``1752ae6c``）：技能等級與未花的技能點作廢，靈感點 ＝ 已打贏的一般戰鬥場數
  （照新規則「每贏一場 1 點」重算，不把舊技能點換成靈感點）；分歧進化過的技能保留進化後的定義，
  視為剛取得的技能（閃現 0 次）；營火的重骰候選丟棄；升級候選照舊。
  Phase 3W-9 起技能的預算用角色階級：``run.skill_tier`` 記主角技能
  目前照哪一階配數值（``/11``；舊存檔沒有＝還沒照角色階級重配），:func:`upgrade_save` 在戰鬥之間
  把舊存檔的每招技能照角色階級重配一次（戰鬥中的存檔等那場打完，下一個節點再重配）。
  Phase 4-L8 起提議紀錄多了提議與命名 prompt 的版本號
  ``prompt_version``、``naming_prompt_version``（``/10``；舊紀錄沒有＝未記錄）。
  Phase 4-L7 起提議紀錄多了命名與敘事的來源 ``name_source``、
  ``name_attempts``、``name_codes``（``/9``；舊紀錄沒有＝沒有命名步驟）。
  Phase 4-L6 起多了 LLM 生成開關 ``run.llm``、run 內配額 ``run.llm_uses``、
  提議紀錄 ``run.llm_log`` 與候選標示的 ``offer.tags[].llm``（``/8``；舊存檔沒有＝
  關閉，候選來源 ``llm`` 只出現在 ``/8``）。
  Phase 3R-3a 起多了出身 ``run.origin``（``/7``；舊存檔沒有＝無出身，
  種族 ``run.hero.race`` 同理沒有＝無種族）。
  Phase 3-22 起每場戰鬥的安排多了勝利條件 ``objective``（``/2``）；Phase 3-24b2 起開局改成「武器 ＋
  關鍵字」（``run.start``，``build_id`` 可為空）、多了行為紀錄 ``run.behavior`` 與候選標示
  ``offer.tags``（``/3``）；Phase 3-26a 起多了技能成長 ``run.skill_points``、``run.skill_levels``、
  ``run.bench``（``/4``）；Phase 3-26b 起多了用法統計 ``run.skill_usage`` 與分歧進化
  ``run.evolutions``（``/5``）；Phase 3K-2 起多了戰後裝備 ``run.equipment``、``run.backpack`` 與節點
  ``gear_offer``（``/6``）。更舊的存檔明確拒絕並提示開新一輪。
- ``engine``：寫入時引擎的戰鬥紀錄格式（``LOG_FORMAT``）。只有 **戰鬥進行中** 的存檔需要重播；
  此時版本不同（舊版引擎的步驟不保證能在新版重播出同樣結果）就 **捨棄那場戰鬥、回到該戰鬥節點的
  開頭**（清掉 ``battle``、保留節點；開戰不改一輪的狀態，所以等於還沒開打），並回傳提示
  :data:`STALE_BATTLE_NOTICE`（3W-R1，開發 PM 決定；:func:`loads_save_noted`）。戰鬥之間的存檔
  不受影響。
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
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.content.library import ContentLibrary
from trpg.engine.runner import LOG_FORMAT
from trpg.roguelite.battle import ActiveBattle, SavedBattle
from trpg.roguelite.errors import SaveFormatError
from trpg.roguelite.retier import sync_skill_tier
from trpg.roguelite.state import BattleNode, RunState

__all__ = [
    "COMPATIBLE_FORMATS",
    "CONTENT_CHANGED_NOTICE",
    "OLD_FORMATS",
    "RUN_ID_PATTERN",
    "SAVE_DIR_ENV",
    "SAVE_FORMAT",
    "STALE_BATTLE_NOTICE",
    "RunSave",
    "convert_raw_hero",
    "convert_raw_run",
    "default_save_dir",
    "dumps_save",
    "load_save",
    "load_save_noted",
    "loads_save",
    "loads_save_noted",
    "restore_battle",
    "ruleset_hash",
    "save_path",
    "upgrade_save",
    "write_save",
]

SAVE_FORMAT = "trpg-run/13"
COMPATIBLE_FORMATS = (
    "trpg-run/5",
    "trpg-run/6",
    "trpg-run/7",
    "trpg-run/8",
    "trpg-run/9",
    "trpg-run/10",
    "trpg-run/11",
    "trpg-run/12",
)
"""仍可讀入的舊格式（讀入時由 :func:`convert_raw_run`、:func:`convert_raw_hero` 轉成目前的
格式）。"""
_GROWTH_FORMATS = frozenset(COMPATIBLE_FORMATS) - {"trpg-run/12"}
"""還有技能點、技能等級、分歧進化（Phase 3-26a／b）的格式：讀入時轉成靈感點（3W-5）。"""
OLD_FORMATS = ("trpg-run/1", "trpg-run/2", "trpg-run/3", "trpg-run/4")
"""已知的舊存檔格式（讀檔時提示開新一輪）。"""
RUN_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
SAVE_DIR_ENV = "TRPG_SAVE_DIR"
"""可覆寫存檔資料夾的環境變數。"""
STALE_BATTLE_NOTICE = "這場戰鬥的紀錄格式已更新，從這場的開頭重新開始。"
CONTENT_CHANGED_NOTICE = "內容檔已更新，這場戰鬥從開頭重新開始。"
"""戰鬥中的存檔引擎版本不符、捨棄那場戰鬥時給玩家的提示（3W-R1）。"""


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


def convert_raw_run(raw: dict[str, Any]) -> dict[str, Any]:
    """``/11`` 以前的一輪（JSON 物件）轉成 ``/12``（Phase 3W-5，見模組說明）：拿掉技能點、技能
    等級、分歧進化，靈感點 ＝ 已打贏的一般戰鬥場數；營火的重骰候選丟棄。不改原物件。"""
    run = dict(raw)
    run.pop("skill_points", None)
    run.pop("skill_levels", None)
    run.pop("evolutions", None)
    history = run.get("history") or []
    wins = sum(1 for r in history if isinstance(r, dict) and r.get("won") and not r.get("boss"))
    run.setdefault("insight", wins)
    node = run.get("node")
    if isinstance(node, dict) and node.get("kind") == "campfire":
        run["node"] = {k: v for k, v in node.items() if k not in ("rerolls_left", "offer")}
    return run


def convert_raw_hero(raw: dict[str, Any]) -> dict[str, Any]:
    """``/12`` 以前的一輪（JSON 物件）的主角範本拿掉引擎已移除的技能等級欄位（Phase 3W-5b）。
    不改原物件。"""
    hero = raw.get("hero")
    if not isinstance(hero, dict) or "skill_levels" not in hero:
        return raw
    return {**raw, "hero": {k: v for k, v in hero.items() if k != "skill_levels"}}


def loads_save(text: str) -> RunSave:
    """解析存檔；格式不對時拋出 :class:`SaveFormatError`（提示見 :func:`loads_save_noted`）。"""
    return loads_save_noted(text)[0]


def loads_save_noted(text: str) -> tuple[RunSave, str | None]:
    """解析存檔，連同讀檔時要給玩家的提示（沒有時 ``None``）；格式不對時拋出
    :class:`SaveFormatError`。戰鬥中的存檔引擎版本不符時捨棄那場戰鬥（見模組說明）。"""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SaveFormatError(f"存檔不是有效的 JSON：{exc}") from exc
    found = raw.get("format") if isinstance(raw, dict) else None
    if found != SAVE_FORMAT and found not in COMPATIBLE_FORMATS:
        hint = "（舊版存檔無法讀取，請開新一輪）" if found in OLD_FORMATS else ""
        raise SaveFormatError(f"存檔格式必須是 {SAVE_FORMAT}，收到 {found!r}{hint}")
    if found in _GROWTH_FORMATS and isinstance(raw.get("run"), dict):
        raw = {**raw, "run": convert_raw_run(raw["run"])}
    if found in COMPATIBLE_FORMATS and isinstance(raw.get("run"), dict):
        raw = {**raw, "run": convert_raw_hero(raw["run"])}
    try:
        save = RunSave.model_validate({**raw, "format": SAVE_FORMAT})
    except ValidationError as exc:
        raise SaveFormatError(f"存檔內容不合法：{exc.error_count()} 個錯誤：{exc}") from exc
    if re.match(RUN_ID_PATTERN, save.run_id) is None:
        raise SaveFormatError(f"不合法的 run_id：{save.run_id!r}")
    notice = None
    if save.battle is not None:
        if not isinstance(save.run.node, BattleNode):
            raise SaveFormatError("存檔有進行中的戰鬥，但一輪的節點不是戰鬥")
        if save.engine != LOG_FORMAT:
            save = save.model_copy(update={"battle": None, "engine": LOG_FORMAT})
            notice = STALE_BATTLE_NOTICE
    return save, notice


def upgrade_save(library: ContentLibrary, save: RunSave) -> RunSave:
    """舊存檔轉換（Phase 3W-9）：``run.skill_tier`` 為空（``/10`` 以前）而且不在戰鬥中時，主角的
    每招技能照角色目前的階級重配（:func:`trpg.roguelite.retier.sync_skill_tier`；手寫技能變成
    ``<原 ID>_t<階級>`` 的生成技能）。戰鬥中的存檔不動（重播要用存檔當時的技能），那場打完後的下一個
    節點再重配。已經是新格式時原樣回傳。"""
    if save.run.skill_tier is not None or save.battle is not None:
        return save
    return save.model_copy(update={"run": sync_skill_tier(library, save.run)})


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
    return load_save_noted(path)[0]


def load_save_noted(path: Path) -> tuple[RunSave, str | None]:
    """讀取存檔檔案，連同讀檔提示（:func:`loads_save_noted`）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SaveFormatError(f"無法讀取存檔 {path}：{exc}") from exc
    return loads_save_noted(text)


def restore_battle(library: ContentLibrary, save: RunSave) -> ActiveBattle | None:
    """重播存檔中進行中的戰鬥（沒有時 ``None``）。"""
    if save.battle is None:
        return None
    return ActiveBattle.restore(library, save.run, save.battle)
