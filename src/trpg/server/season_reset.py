"""季末重置（Phase 5F-5；``docs/phases/Phase5計畫.md`` 第 40 節；09 9.7、#91）。

照 :mod:`trpg.server.season_policy` 把世界換到下一季：數值類全清、紀念類保留。

- **入口**：:func:`season_reset`（管理者的 API ``POST /api/world/season/reset`` 與
  ``scripts/season_reset.py`` 都呼叫它）。``dry_run=True``（預設）只算出會清什麼、留什麼，
  不寫任何檔。
- **順序**（帳號資料夾的鎖檔內）：檢查 → 備份整個存檔資料夾 → 寫編年史（:data:`CARRIED` 的內容；
  同一季已有就不覆寫，中斷後重跑不會用半套資料蓋掉）→ 循環賽報名快照清空 → 世界日誌、循環賽、
  賽季 Boss 首殺的戰鬥紀錄搬進存檔資料夾的唯讀封存 ``archive/<舊季>/``（5F-5c，
  :mod:`trpg.server.season_archive`）→ 刪角色、留言 → 最後寫新一季的 ``world.json``。
- **確定性**：同一份存檔＋同樣的參數（開賽時間、季 ID、種子、``now``）→ 一模一樣的結果。清單一律
  依 ID 排序；新一季的種子預設由舊種子＋新季 ID 雜湊（不用 ``random``、``secrets``）。時間由呼叫者
  傳入。
- 只做檔案操作；遊戲伺服器的記憶體快取由呼叫者（:class:`~trpg.api.world.WorldStore`）清掉。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import shutil
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.library import ContentLibrary
from trpg.content.world_season import ChronicleFact, ChronicleTemplates, SeasonNaming
from trpg.server.accounts import AccountRecord, AccountStore, AccountTitle
from trpg.server.chronicle import (
    ChronicleHero,
    LeagueChronicle,
    LeagueChronicleRank,
    LeagueChronicleSeason,
    LeagueChronicleStore,
    RecipeDiscovery,
    SeasonChronicle,
    SeasonChronicleEntry,
    SeasonChronicleStore,
)
from trpg.server.first_kills import FirstKill, elite_kind_name, load_first_kills
from trpg.server.league import LeagueMatch, LeagueRecord
from trpg.server.notes import LocationNote, LocationNoteStore
from trpg.server.season_archive import SeasonArchiveError, archive_season
from trpg.server.season_boss_board import (
    BossBoardEntry,
    load_boss_board,
)
from trpg.server.season_policy import (
    HERO_LEGACY_FIELDS,
    MEMORIAL,
    NUMERIC,
    fields_of_kind,
)
from trpg.shared.errors import TrpgError
from trpg.world.calendar import season_status
from trpg.world.layout import (
    ARCHIVE_DIR,
    BOSS_BOARD_FILE,
    CHARS_DIR,
    CHRONICLE_DIR,
    FIRST_KILL_DIR,
    FIRST_KILLS_FILE,
    LEAGUE_ARCHIVE_DIR,
    LEAGUE_DIR,
    LEAGUE_FILE,
    LEAGUE_HISTORY_DIR,
    LOG_FILE,
    NOTES_FILE,
    SERVER_LOCK_FILE,
    WORLD_FILE,
    world_dir_of,
)
from trpg.world.loot import loot_rules
from trpg.world.save import dumps_world, loads_char, loads_world, write_atomic
from trpg.world.season_boss import boss_def
from trpg.world.state import CharacterState, RecipeRecord, WorldState

__all__ = [
    "BACKUP_DIR_NAME",
    "CARRIED_HANDLERS",
    "HANDLERS",
    "LEAGUE_HISTORY_DIR",
    "SPLIT_CARRIERS",
    "WORLD_FILES",
    "HandlerKind",
    "ResetLine",
    "SeasonFacts",
    "SeasonResetError",
    "SeasonResetReport",
    "chronicle_hero",
    "clear_numeric",
    "default_backup_root",
    "next_season_id",
    "recipe_discovery",
    "season_facts",
    "season_name_zh",
    "season_reset",
]

BACKUP_DIR_NAME: Final = "saves-backups"
_SEASON_ID: Final = re.compile(r"^s([0-9]+)$")
_ID_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")
MASK64: Final = (1 << 64) - 1

HandlerKind = Literal["replace", "delete", "keep", "split"]
"""重置怎麼處理一個存檔模型：``replace`` 換成新一季的預設、``delete`` 刪掉（整個數值類）、``keep``
不動（整個紀念類）、``split`` 數值類欄位清掉、紀念類欄位留在 :data:`SPLIT_CARRIERS` 的模型裡。"""

HANDLERS: Final[Mapping[type[BaseModel], tuple[HandlerKind, str]]] = {
    CharacterState: ("delete", "world/chars/*.json：先把 CARRIED 寫進編年史再刪"),
    WorldState: ("replace", "world/world.json：換成新一季（新 season_id、種子、開賽時間）"),
    RecipeRecord: ("split", "配方表清空；首位發現者寫進編年史的 RecipeDiscovery"),
    FirstKill: ("keep", "world/first_kills.json 不動（戰鬥紀錄在封存 archive/<舊季>/ 的同一路徑）"),
    BossBoardEntry: ("keep", "world/season_boss_board.json 不動"),
    AccountRecord: ("keep", "帳號資料夾不動（重置期間持有鎖檔）"),
    AccountTitle: ("keep", "帳號檔的紀念稱號（5F-3b「碎晶的終結者」）跟著帳號不動"),
    LocationNote: ("delete", "world/notes.json 刪掉"),
    LeagueRecord: ("split", "world/league/ 報名快照清空，搬進唯讀封存 archive/<舊季>/league/"),
    LeagueMatch: ("keep", "跟著賽程搬進封存，場次與戰鬥紀錄檔內容不動（可重播查證）"),
    LeagueChronicle: ("keep", "world/chronicle/league.json 不動"),
    LeagueChronicleSeason: ("keep", "world/chronicle/league.json 不動"),
    LeagueChronicleRank: ("keep", "world/chronicle/league.json 不動"),
    SeasonChronicle: ("keep", "world/chronicle/seasons.json：只加新的一季"),
    SeasonChronicleEntry: ("keep", "world/chronicle/seasons.json 的舊季不動"),
    ChronicleHero: ("keep", "world/chronicle/seasons.json 的舊季不動"),
    RecipeDiscovery: ("keep", "world/chronicle/seasons.json 的舊季不動"),
}
"""政策表每個模型的重置處理（架構測試檢查和分類一致、表裡每個模型都有）。"""

SPLIT_CARRIERS: Final[Mapping[type[BaseModel], type[BaseModel]]] = {
    RecipeRecord: RecipeDiscovery,
    LeagueRecord: LeagueRecord,
}
"""``split`` 的模型 → 留下紀念類欄位的模型（紀念類欄位都要是它的欄位）。"""

WORLD_FILES: Final[Mapping[str, str]] = {
    WORLD_FILE: "replace",
    LOG_FILE: "archive",  # 5F-5c：搬進唯讀封存 archive/<舊季>/
    CHARS_DIR: "delete",
    NOTES_FILE: "delete",
    LEAGUE_DIR: "archive",
    FIRST_KILLS_FILE: "keep",
    BOSS_BOARD_FILE: "keep",
    FIRST_KILL_DIR: "archive",
    CHRONICLE_DIR: "keep",
    LEAGUE_HISTORY_DIR: "keep",  # 5F-5 的舊位置（5F-5c 起改搬進封存）
    SERVER_LOCK_FILE: "keep",  # 5F-R1：遊戲伺服器的心跳檔（伺服器開著時才有；重置不動）
}
"""世界資料夾裡認得的檔案與資料夾。不認得的照保守做法保留，列在報告裡。"""


class SeasonResetError(TrpgError):
    """現在不能季末重置（409）：賽季還沒結束（沒有 ``force``）、季 ID 不合法、確認不符等。"""


class ResetLine(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label_zh: str
    count: int
    detail_zh: str = ""


class SeasonResetReport(BaseModel):
    """季末重置（或 dry-run）的結果。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dry_run: bool
    old_season: str
    new_season: str
    new_season_name_zh: str
    season_start: int
    """新一季的開賽時間（UTC 秒）。"""
    cleared: tuple[ResetLine, ...]
    kept: tuple[ResetLine, ...]
    chronicle: tuple[str, ...]
    """要寫進（或已寫進）編年史的文字（每個角色一行：「名字：文字」）。"""
    warnings: tuple[str, ...] = ()
    """``force`` 略過的檢查。"""
    backup: str | None = None
    """備份資料夾（dry-run＝``None``）。"""
    archive: str | None = None
    """舊季的唯讀封存資料夾（5F-5c；dry-run＝``None``）。"""


# -- 小工具 -------------------------------------------------------------------


def season_name_zh(season_id: str, library: ContentLibrary | None = None) -> str:
    """季名（5F-R2：模板在 ``world/season.yaml`` 的 ``naming``，某一季可在 ``seasons.<季 ID>`` 寫
    ``name_zh``）：``s1`` → 「第一季」；不是 ``s<N>`` 的 ID 照 ``fallback``（「賽季 xxx」）。
    沒有內容庫或沒有賽季資料時用 :class:`~trpg.content.world_season.SeasonNaming` 的預設模板。"""
    base = None if library is None else (library.season_base or library).world_season
    return SeasonNaming().name_of(season_id) if base is None else base.name_of(season_id)


def next_season_id(season_id: str) -> str:
    """``s<N>`` → ``s<N+1>``；其他格式不能自動推（要明給季 ID）。"""
    found = _SEASON_ID.match(season_id)
    if found is None:
        raise SeasonResetError(f"目前的賽季 {season_id!r} 不是 s<N>，請指定新的季 ID")
    return f"s{int(found.group(1)) + 1}"


def _derived_seed(world: WorldState, new_id: str) -> int:
    digest = hashlib.sha256(f"{world.season_seed}:{new_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & MASK64


def default_backup_root(save_dir: Path) -> Path:
    """預設的備份根：存檔資料夾旁邊的 ``saves-backups/``（不在存檔資料夾裡，避免備份到自己）。"""
    return save_dir.resolve().parent / BACKUP_DIR_NAME


def clear_numeric[M: BaseModel](model: M) -> M:
    """把一筆紀錄的數值類欄位換成預設值（必填欄位＝空 tuple）；紀念類欄位不動。"""
    cls = type(model)
    update: dict[str, object] = {}
    for name in fields_of_kind(cls, NUMERIC):
        info = cls.model_fields[name]
        update[name] = () if info.is_required() else info.get_default(call_default_factory=True)
    return cls.model_validate({**model.model_dump(), **update})


def recipe_discovery(record: RecipeRecord) -> RecipeDiscovery:
    """配方的紀念類欄位（政策表決定哪些）→ 編年史的首位發現。"""
    kept = {name: getattr(record, name) for name in fields_of_kind(RecipeRecord, MEMORIAL)}
    return RecipeDiscovery.model_validate(kept)


def _skeleton_text(library: ContentLibrary) -> dict[str, str]:
    found: dict[str, str] = {}
    for region in sorted(library.world_event_content.events):
        table = library.world_event_content.events[region]
        for skeleton in table.skeletons:
            found[skeleton.id] = f"{skeleton.who_zh}：{skeleton.want_zh}"
    return found


@dataclass(frozen=True)
class SeasonFacts:
    """季末寫編年史用的全季事實（Phase 5F-5c；都來自世界狀態與伺服器的紀念檔，不推測）。"""

    season_id: str
    skeletons: Mapping[str, str]
    """事件骨架 ID → 「誰：想要什麼」。"""
    main_quests: Mapping[str, str]
    """主線任務 ID → 章節名。"""
    region_bosses: frozenset[str]
    """區域 Boss 的單位 ID（``world/loot.yaml`` 的 ``bosses``）。"""
    season_boss: str | None
    """賽季 Boss 的中文名（沒有賽季 Boss＝``None``）。"""
    boss_clears: frozenset[str]
    """這一季打倒過賽季 Boss 的角色 ID。"""
    first_kills: Mapping[str, tuple[str, ...]]
    """角色 ID → 這一季的全服首殺（目標中文名，依日誌序號）。"""
    recipes: Mapping[str, tuple[str, ...]]
    """角色 ID → 首位發現的配方名（依配方碼）。"""
    league_ranks: Mapping[str, int]
    """角色 ID → 循環賽最終名次（編年史 ``chronicle/league.json`` 的這一季）。"""


def season_facts(
    library: ContentLibrary,
    world: WorldState,
    *,
    first_kills: Sequence[FirstKill] = (),
    league: LeagueChronicleSeason | None = None,
) -> SeasonFacts:
    """從世界狀態、首殺紀錄與循環賽編年史整理這一季的事實（:class:`SeasonFacts`）。"""
    season = world.season_id
    mains = {
        q.id: q.name_zh
        for region in sorted(library.world_quests.quests)
        for q in library.world_quests.quests[region].quests
        if q.kind == "main"
    }
    loot = loot_rules(library)
    boss = boss_def(library)
    kills: dict[str, list[str]] = {}
    for kill in sorted(first_kills, key=lambda k: k.seq):
        if kill.season_id == season:
            kills.setdefault(kill.character_id, []).append(kill.target_name_zh)
    recipes: dict[str, list[str]] = {}
    for record in sorted(world.recipes, key=lambda r: r.code):
        if record.season_id == season:
            recipes.setdefault(record.discoverer, []).append(record.name_zh)
    accounts = {e.account: e.character_id for e in world.league_entries}
    ranks: dict[str, int] = {}
    if league is not None and league.season_id == season:
        ranks = {accounts[r.account]: r.rank for r in league.ranks if r.account in accounts}
    return SeasonFacts(
        season_id=season,
        skeletons=_skeleton_text(library),
        main_quests=mains,
        region_bosses=frozenset(() if loot is None else loot.bosses),
        season_boss=None if boss is None else boss.name_zh,
        boss_clears=frozenset(c.character_id for c in world.boss_clears),
        first_kills={k: tuple(v) for k, v in kills.items()},
        recipes={k: tuple(v) for k, v in recipes.items()},
        league_ranks=ranks,
    )


def _fact(rule: ChronicleFact, names: Sequence[str], joiner: str) -> str | None:
    if not names:
        return None
    return rule.text.format(items=joiner.join(rule.item.format(name=n) for n in names))


def _chronicle_text(templates: ChronicleTemplates | None, season: str, hero: ChronicleHero) -> str:
    """編年史的一行（模板在 ``world/season.yaml`` 的 ``chronicle``；沒有模板＝只寫季名
    ``season``）。"""
    if templates is None:
        return season
    t = templates
    facts = [
        None if hero.level is None else t.level.format(level=hero.level),
        _fact(t.elites, hero.elites, t.joiner),
        _fact(t.bosses, hero.bosses, t.joiner),
        _fact(t.first_kills, hero.first_kills, t.joiner),
        _fact(t.chapters, hero.chapters, t.joiner),
        _fact(t.events, hero.events, t.joiner),
        _fact(t.recipes, hero.recipes, t.joiner),
        None if hero.league_rank is None else t.league.format(rank=hero.league_rank),
    ]
    body = t.separator.join(f for f in facts if f is not None) or t.empty
    return t.line.format(season=season, facts=body)


def chronicle_hero(
    library: ContentLibrary,
    char: CharacterState,
    season_id: str,
    account_id: str | None,
    facts: SeasonFacts | None = None,
) -> ChronicleHero:
    """一個角色的編年史（5F-5c 列事實細節）：等級、打過的精英與 Boss、全服首殺、完成的主線章節與
    事件、首位發現的配方、循環賽名次＋名字、紙娃娃與種族（:data:`HERO_LEGACY_FIELDS`）。``facts``
    省略＝只用角色自己的狀態（沒有首殺、配方、循環賽、賽季 Boss）。"""
    if facts is None:
        empty = WorldState(season_id=season_id, season_seed=0, season_start=0)
        facts = season_facts(library, empty)
    cid = char.character_id
    elites: list[str] = []
    bosses: list[str] = []
    for kind in char.elite_kills:
        found = bosses if kind.partition("+")[0] in facts.region_bosses else elites
        found.append(elite_kind_name(library, kind))
    if facts.season_boss is not None and cid in facts.boss_clears:
        bosses.append(facts.season_boss)
    chapters = tuple(
        facts.main_quests[q.quest] for q in char.quests if q.done and q.quest in facts.main_quests
    )
    legacy = {name: getattr(char.hero, name) for name in HERO_LEGACY_FIELDS}
    hero = ChronicleHero(
        character_id=cid,
        account_id=account_id,
        name=legacy["name_zh"],
        race=legacy["race"],
        doll=legacy["doll"],
        level=char.level,
        elites=tuple(elites),
        bosses=tuple(bosses),
        first_kills=facts.first_kills.get(cid, ()),
        chapters=chapters,
        events=tuple(facts.skeletons.get(s, s) for s in char.finished_skeletons),
        recipes=facts.recipes.get(cid, ()),
        league_rank=facts.league_ranks.get(cid),
        text_zh="",
    )
    season = library.for_season(season_id).world_season  # 這一季的覆寫（5F-R2）
    templates = None if season is None else season.chronicle
    text = _chronicle_text(templates, season_name_zh(season_id, library), hero)
    return hero.model_copy(update={"text_zh": text})


CARRIED_HANDLERS: Final[Mapping[tuple[str, str], Callable[..., object]]] = {
    ("CharacterState", "hero"): chronicle_hero,
    ("CharacterState", "elite_kills"): chronicle_hero,
    ("CharacterState", "finished_skeletons"): chronicle_hero,
    ("CharacterState", "level"): chronicle_hero,  # 5F-5c 編年史列事實細節
    ("CharacterState", "quests"): chronicle_hero,
    ("WorldState", "recipes"): recipe_discovery,
    ("WorldState", "boss_clears"): season_facts,
    ("WorldState", "league_entries"): season_facts,
}
""":data:`~trpg.server.season_policy.CARRIED` 的每一項由哪個函式寫進紀念紀錄（架構測試檢查）。"""


# -- 讀現況 -------------------------------------------------------------------


@dataclass(frozen=True)
class _Current:
    world: WorldState
    chars: tuple[CharacterState, ...]
    log_entries: int
    notes: tuple[LocationNote, ...]
    league: LeagueRecord | None
    league_archived: int
    first_kills: tuple[FirstKill, ...]
    boss_board: tuple[BossBoardEntry, ...]
    boss_logs: int
    league_chronicle: LeagueChronicle
    season_chronicle: SeasonChronicle
    unknown: tuple[str, ...]


def _read_current(world_dir: Path) -> _Current:
    path = world_dir / WORLD_FILE
    if not path.is_file():
        raise SeasonResetError("還沒有世界存檔，不用重置")
    world = loads_world(path.read_text(encoding="utf-8"))
    chars_dir = world_dir / CHARS_DIR
    chars = tuple(
        loads_char(p.read_text(encoding="utf-8")) for p in sorted(chars_dir.glob("*.json"))
    )
    log = world_dir / LOG_FILE
    lines = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    league_path = world_dir / LEAGUE_DIR / LEAGUE_FILE
    league = (
        LeagueRecord.model_validate_json(league_path.read_text(encoding="utf-8"))
        if league_path.is_file()
        else None
    )
    archive = world_dir / LEAGUE_DIR / LEAGUE_ARCHIVE_DIR
    boss_dir = world_dir / FIRST_KILL_DIR
    unknown = tuple(sorted(p.name for p in world_dir.iterdir() if p.name not in WORLD_FILES))
    return _Current(
        world=world,
        chars=tuple(sorted(chars, key=lambda c: c.character_id)),
        log_entries=sum(1 for line in lines if line.strip()),
        notes=LocationNoteStore(world_dir).all(),
        league=league,
        league_archived=len(list(archive.glob("league-*.json"))) if archive.is_dir() else 0,
        first_kills=load_first_kills(world_dir / FIRST_KILLS_FILE),
        boss_board=load_boss_board(world_dir / BOSS_BOARD_FILE),
        boss_logs=len(list(boss_dir.glob("*.json"))) if boss_dir.is_dir() else 0,
        league_chronicle=LeagueChronicleStore(world_dir).load(),
        season_chronicle=SeasonChronicleStore(world_dir).load(),
        unknown=unknown,
    )


def _owners(accounts: Iterable[AccountRecord]) -> dict[str, str]:
    found: dict[str, str] = {}
    for record in sorted(accounts, key=lambda a: a.account_id):
        for character_id in record.characters:
            found.setdefault(character_id, record.account_id)
    return found


def _world_line(world: WorldState) -> ResetLine:
    parts = [
        f"旗標 {len(world.flags)}",
        f"已清空地點 {len(world.cleared)}",
        f"線頭 {len(world.threads)}",
        f"世界事件 {len(world.world_events)}",
        f"懸賞 {len(world.bounty_claims)}",
        f"封印鑰匙 {world.seal_keys}",
        f"Boss 挑戰 {len(world.boss_attempts)}",
        f"影子 {len(world.shadows)}",
    ]
    return ResetLine(label_zh="世界狀態", count=1, detail_zh="、".join(parts))


def _lines(
    current: _Current, accounts: Sequence[AccountRecord], extra_cleared: Sequence[ResetLine]
) -> tuple[tuple[ResetLine, ...], tuple[ResetLine, ...]]:
    league = current.league
    entries = 0 if league is None else len(league.entries)
    matches = 0 if league is None else len(league.matches)
    cleared = [
        ResetLine(
            label_zh="角色",
            count=len(current.chars),
            detail_zh="等級、技能、裝備、材料、任務幣、精英擊殺與完成的事件（先寫進編年史）",
        ),
        _world_line(current.world),
        ResetLine(
            label_zh="世界日誌",
            count=current.log_entries,
            detail_zh=f"搬進唯讀封存 {ARCHIVE_DIR}/{current.world.season_id}/",
        ),
        ResetLine(
            label_zh="配方表",
            count=len(current.world.recipes),
            detail_zh="首位發現者寫進編年史",
        ),
        ResetLine(label_zh="地點留言", count=len(current.notes)),
        ResetLine(
            label_zh="循環賽報名快照",
            count=entries,
            detail_zh="名次、名字、build 名已在編年史",
        ),
        *extra_cleared,
    ]
    kept = [
        ResetLine(label_zh="帳號", count=len(accounts), detail_zh="含角色歸屬紀錄"),
        ResetLine(label_zh="首殺紀錄", count=len(current.first_kills)),
        ResetLine(label_zh="賽季 Boss 評分榜", count=len(current.boss_board)),
        ResetLine(
            label_zh="賽季 Boss 首殺戰鬥紀錄",
            count=current.boss_logs,
            detail_zh=f"搬進唯讀封存 {ARCHIVE_DIR}/{current.world.season_id}/",
        ),
        ResetLine(
            label_zh="循環賽場次",
            count=matches,
            detail_zh=f"搬進唯讀封存 {ARCHIVE_DIR}/{current.world.season_id}/（舊賽程 "
            f"{current.league_archived} 份一起搬）",
        ),
        ResetLine(label_zh="循環賽最終排名（編年史）", count=len(current.league_chronicle.seasons)),
        ResetLine(
            label_zh="編年史季末紀錄",
            count=len(current.season_chronicle.seasons) + 1,
            detail_zh="含這一季",
        ),
        ResetLine(
            label_zh="上季角色的名字與外觀",
            count=len(current.chars),
            detail_zh="下季建角色可以沿用",
        ),
    ]
    if current.unknown:
        kept.append(
            ResetLine(
                label_zh="不認得的檔案（保留）",
                count=len(current.unknown),
                detail_zh="、".join(current.unknown),
            )
        )
    return tuple(cleared), tuple(kept)


# -- 檢查 ---------------------------------------------------------------------


def _new_season_id(current: _Current, season_id: str | None) -> str:
    old = current.world.season_id
    new = next_season_id(old) if season_id is None else season_id
    if not _ID_PATTERN.match(new):
        raise SeasonResetError(f"季 ID {new!r} 不合法（小寫英文開頭、只用小寫英數與底線）")
    if new == old:
        raise SeasonResetError(f"新的季 ID 不能和目前的一樣（{old}）")
    used = {s.season_id for s in current.season_chronicle.seasons}
    used |= {s.next_season_id for s in current.season_chronicle.seasons if s.season_id != old}
    if new in used:
        raise SeasonResetError(f"季 ID {new} 已經用過")
    return new


def _soft_problems(library: ContentLibrary, current: _Current, now: int) -> list[str]:
    """``force`` 可以略過的問題。"""
    problems: list[str] = []
    if season_status(library, current.world, now) != "ended":
        problems.append("這一季還沒結束")
    league = current.league
    if league is not None and league.season_id == current.world.season_id and not league.finished:
        problems.append(f"循環賽還有 {len(league.matches) - league.done} 場沒跑完")
    return problems


# -- 執行 ---------------------------------------------------------------------


def _backup(save_dir: Path, accounts_dir: Path | None, root: Path, now: int, old: str) -> Path:
    save = save_dir.resolve()
    target_root = root.resolve()
    if target_root == save or save in target_root.parents:
        raise SeasonResetError("備份資料夾不能放在存檔資料夾裡")
    stamp = dt.datetime.fromtimestamp(now, dt.UTC).strftime("%Y%m%d-%H%M%S")
    base = f"saves-{stamp}-{old}"
    target = target_root / base
    n = 2
    while target.exists():
        target = target_root / f"{base}-{n}"
        n += 1
    ignore = shutil.ignore_patterns("*.lock")  # 鎖檔被持有時 Windows 讀不了；鎖檔本身沒有資料

    def ignore_save(directory: str, names: list[str]) -> set[str]:
        skipped = set(ignore(directory, names))
        if Path(directory) == save and ARCHIVE_DIR in names:
            skipped.add(ARCHIVE_DIR)  # 5F-R1：存檔資料夾的 archive/ 本身就是唯讀封存，不再備份
        return skipped

    shutil.copytree(save, target, ignore=ignore_save)
    if accounts_dir is not None and accounts_dir.is_dir():
        accounts = accounts_dir.resolve()
        if save not in accounts.parents:
            shutil.copytree(accounts, target / "accounts", ignore=ignore)
    return target


def _clear_league_entries(world_dir: Path) -> None:
    """賽程檔（現在的與 ``league/archive/`` 的）報名快照清空（數值類）；搬進封存之前先改內容，
    中斷後重跑照樣接得上。"""
    league = world_dir / LEAGUE_DIR
    if not league.is_dir():
        return
    records = [league / LEAGUE_FILE]
    archive = league / LEAGUE_ARCHIVE_DIR
    if archive.is_dir():
        records += sorted(archive.glob("league-*.json"))
    for path in records:
        if path.is_file():
            record = LeagueRecord.model_validate_json(path.read_text(encoding="utf-8"))
            write_atomic(path, clear_numeric(record).model_dump_json(indent=1))


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


@dataclass(frozen=True)
class _Plan:
    new_id: str
    seed: int
    entry: SeasonChronicleEntry
    warnings: tuple[str, ...]


def _plan(
    library: ContentLibrary,
    current: _Current,
    accounts: Sequence[AccountRecord],
    *,
    now: int,
    season_id: str | None,
    seed: int | None,
    force: bool,
) -> _Plan:
    new_id = _new_season_id(current, season_id)
    problems = _soft_problems(library, current, now)
    if problems and not force:
        raise SeasonResetError(
            "不能重置：" + "；".join(problems) + "（確定要重置請加 force；腳本是 --force-season）"
        )
    if seed is not None and not 0 <= seed <= MASK64:
        raise SeasonResetError("種子要在 0～2^64-1")
    old = current.world.season_id
    owners = _owners(accounts)
    league = next((s for s in current.league_chronicle.seasons if s.season_id == old), None)
    facts = season_facts(library, current.world, first_kills=current.first_kills, league=league)
    heroes = tuple(
        chronicle_hero(library, c, old, owners.get(c.character_id), facts) for c in current.chars
    )
    recipes = tuple(
        recipe_discovery(r) for r in sorted(current.world.recipes, key=lambda r: r.code)
    )
    entry = SeasonChronicleEntry(
        season_id=old,
        name_zh=season_name_zh(old, library),
        started_at=current.world.season_start,
        reset_at=now,
        next_season_id=new_id,
        heroes=heroes,
        recipes=recipes,
    )
    new_seed = _derived_seed(current.world, new_id) if seed is None else seed
    return _Plan(new_id=new_id, seed=new_seed, entry=entry, warnings=tuple(problems))


@dataclass(frozen=True)
class _Options:
    start: int
    now: int
    season_id: str | None
    seed: int | None
    force: bool
    dry_run: bool
    backup_root: Path | None
    extra: Sequence[ResetLine]


def season_reset(
    library: ContentLibrary,
    save_dir: Path,
    *,
    start: int,
    now: int,
    accounts: AccountStore | None = None,
    world_dir: Path | None = None,
    season_id: str | None = None,
    seed: int | None = None,
    force: bool = False,
    dry_run: bool = True,
    backup_root: Path | None = None,
    extra_cleared: Sequence[ResetLine] = (),
) -> SeasonResetReport:
    """季末重置（``dry_run`` 只算不寫）。``start``＝新一季的開賽時間（UTC 秒），``now``＝現在。
    ``accounts`` 給了就整段持有帳號資料夾的鎖檔、用帳號查角色的主人；``world_dir`` 省略＝
    ``<save_dir>/world``；``backup_root`` 省略＝:func:`default_backup_root`。``extra_cleared`` 是
    呼叫者另外清掉的東西（例如伺服器記憶體裡進行中的戰鬥），只放進報告。不能重置時拋
    :class:`SeasonResetError`。"""
    if start < 0:
        raise SeasonResetError("開賽時間不合法")
    world = world_dir if world_dir is not None else world_dir_of(save_dir)
    options = _Options(start, now, season_id, seed, force, dry_run, backup_root, extra_cleared)
    if accounts is None:
        return _reset(library, save_dir, world, None, [], options=options)
    with accounts.locked():
        return _reset(library, save_dir, world, accounts, accounts.all(), options=options)


def _reset(
    library: ContentLibrary,
    save_dir: Path,
    world_dir: Path,
    accounts: AccountStore | None,
    records: Sequence[AccountRecord],
    *,
    options: _Options,
) -> SeasonResetReport:
    current = _read_current(world_dir)
    library = library.for_season(current.world.season_id)  # 舊季的 season.yaml 覆寫（5F-R2）
    plan = _plan(
        library,
        current,
        records,
        now=options.now,
        season_id=options.season_id,
        seed=options.seed,
        force=options.force,
    )
    cleared, kept = _lines(current, records, options.extra)
    old = current.world.season_id
    backup: Path | None = None
    archived: Path | None = None
    if not options.dry_run:
        root = options.backup_root or default_backup_root(save_dir)
        accounts_dir = None if accounts is None else accounts.root
        backup = _backup(save_dir, accounts_dir, root, options.now, old)
        SeasonChronicleStore(world_dir).add(plan.entry)
        _clear_league_entries(world_dir)
        try:
            archived = archive_season(save_dir, world_dir, old, options.now)
        except SeasonArchiveError as exc:
            raise SeasonResetError(str(exc)) from exc
        for name in (CHARS_DIR, NOTES_FILE):
            _remove(world_dir / name)
        fresh = WorldState(season_id=plan.new_id, season_seed=plan.seed, season_start=options.start)
        write_atomic(world_dir / WORLD_FILE, dumps_world(fresh))
    return SeasonResetReport(
        dry_run=options.dry_run,
        old_season=old,
        new_season=plan.new_id,
        new_season_name_zh=season_name_zh(plan.new_id, library),
        season_start=options.start,
        cleared=cleared,
        kept=kept,
        chronicle=tuple(f"{h.name}：{h.text_zh}" for h in plan.entry.heroes),
        warnings=plan.warnings,
        backup=None if backup is None else str(backup),
        archive=None if archived is None else str(archived),
    )
