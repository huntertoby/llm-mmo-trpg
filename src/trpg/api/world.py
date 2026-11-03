"""大世界的工作階段與本機存檔（Phase 5A-5；``docs/phases/Phase5計畫.md`` 10.2）。

- 存檔：``<save_dir>/world/`` 底下 ``world.json``（``trpg-world/1``）、``chars/<id>.json``
  （``trpg-char/1``）、``log.jsonl``（``trpg-wlog/1``）；寫檔用
  :func:`trpg.world.save.write_atomic`。
- 世界第一次用到時建立（賽季 ``s1``、伺服器亂數種子、開始時間＝當下；代決 5A5-2）。5F-1：開賽日有
  設定時用它；每個世界動作的日誌帶做動作的帳號（``actor``，世界事件門檻的上線人數）。
- 讀取畫面用 :meth:`WorldStore.season_world`：換日後的世界（只算，不寫檔；5F-1 公告板）。
- 時間由這一層讀（:attr:`WorldStore.clock`，測試可注入），傳給純函式 ``world_step``（2.1）。
- **單一寫入佇列**（2.4）：一把鎖；每個成功的世界動作依序取 ``seq`` 寫進日誌，再寫角色與世界快照。
- 戰鬥：``prepare_battle`` 的設定在戰鬥工作階段表開一場（和一輪相同，用既有 ``/api/battles``
  端點操作）；結束後下一次讀取該角色時把步驟送 ``fight`` 回寫（:meth:`WorldStore.sync`）。
- 鎖的順序：世界的鎖 → 戰鬥的鎖。
- 帳號是 5E-1：角色以伺服器產生的 ID 存取，不登入（代決 5A5-1）。
- 全服首殺（5E-3，計畫 31.5）：每個成功的世界動作之後把新的精英首殺記到 ``first_kills.json``
  （:mod:`trpg.server.first_kills`；衍生資料，不影響重播）。
- 季末重置（5F-5）：:meth:`WorldStore.season_reset` 在世界的鎖內呼叫
  :func:`trpg.server.season_reset.season_reset`，真的執行後清掉記憶體快取（世界、角色、日誌、進行中
  的戰鬥、循環賽）。編年史的上季角色（:attr:`WorldStore.chronicle`）讓新角色沿用名字與外觀。
- 三選一背景預先計算（PERF-3）：每個世界動作之後、角色第一次讀進來時，把看得到的機遇與劇情步驟的
  三選一丟到背景先算（:mod:`trpg.api.offer_prefetch`）；``world_step`` 在
  :func:`~trpg.roguelite.offers.using_offer_cache` 裡執行，命中就直接拿（結果逐字相同）。
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from trpg.api.offer_prefetch import OfferPrefetcher
from trpg.api.sessions import BattleSession, SessionStore, StepRecord
from trpg.api.world_field_things import FieldSocial, Visitor
from trpg.content.library import ContentLibrary
from trpg.roguelite.offers import using_offer_cache
from trpg.roguelite.start import new_keyword_run, with_origin, with_race
from trpg.roguelite.state import RunState
from trpg.server.accounts import AccountStore, AccountTitle
from trpg.server.chronicle import (
    ChronicleHero,
    SeasonChronicleEntry,
    SeasonChronicleStore,
    legacy_doll,
)
from trpg.server.first_kills import FirstKill, FirstKillRegistry
from trpg.server.league import LeagueError, LeagueRunner, LeagueStore, start_problem
from trpg.server.notes import LocationNoteStore, NoteError
from trpg.server.season_archive import ReplayCheck, verify_first_kill, verify_league_match
from trpg.server.season_boss_board import SeasonBossBoard, first_kill_log_json
from trpg.server.season_reset import (
    ResetLine,
    SeasonResetError,
    SeasonResetReport,
    season_reset,
)
from trpg.shared.errors import TrpgError
from trpg.world.actions import FightAction, NarrateAction, WorldAction, WorldEvent
from trpg.world.battle import prepare_battle
from trpg.world.errors import WorldError
from trpg.world.growth import as_run, skill_seed, world_library
from trpg.world.layout import CHARS_DIR, LOG_FILE, WORLD_FILE, char_path
from trpg.world.replay import WorldLogEntry
from trpg.world.save import (
    dumps_char,
    dumps_log,
    dumps_world,
    loads_char,
    loads_world,
    read_log,
    write_atomic,
)
from trpg.world.season import FIRST_SEASON_ID
from trpg.world.season_board import roll_season
from trpg.world.season_events import SeasonBossClearedEvent
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import new_character, world_step

__all__ = [
    "SEASON_ID",
    "START_REGION",
    "WorldCharacterNotFoundError",
    "WorldConflictError",
    "WorldOutcome",
    "WorldStore",
]

SEASON_ID: Final = FIRST_SEASON_ID
START_REGION: Final = "cloud_ridge"
"""新角色的起始區域（第一季從雲嶺開始，09 9.6.5）。"""

CHAR_ID_PREFIX: Final = "c"

_LOG = logging.getLogger(__name__)


class WorldCharacterNotFoundError(TrpgError):
    """不存在的大世界角色（404）。"""


class WorldConflictError(TrpgError):
    """請求和角色目前的狀態不符：戰鬥中做其他世界動作、沒有遭遇卻開戰（409）。"""


@dataclass(frozen=True)
class WorldOutcome:
    """一次請求之後的角色、世界與這次產生的世界事件。"""

    world: WorldState
    char: CharacterState
    events: tuple[WorldEvent, ...]
    now: int
    battle: BattleSession | None


def _new_char_id() -> str:
    return CHAR_ID_PREFIX + secrets.token_hex(4)


def _now() -> int:
    return int(time.time())


class WorldStore:
    """大世界的角色與世界（記憶體快取＋本機 JSON 存檔）。"""

    def __init__(
        self,
        library: ContentLibrary,
        battles: SessionStore,
        root: Path,
        *,
        clock: Callable[[], int] = _now,
        new_id: Callable[[], str] = _new_char_id,
        prefetch: bool = True,
        season_start: int | None = None,
    ) -> None:
        self.season_start = season_start
        """建立世界時的開賽時間（UTC 秒；Phase 5F-1 的開賽日設定）；``None``＝建立當下。"""
        self.actor_of: Callable[[str], str | None] | None = None
        """角色 ID → 帳號 ID（世界事件門檻的上線人數，Q15）；``None`` 或回 ``None``＝用角色 ID。
        :func:`~trpg.api.app.create_app` 接上帳號的 ``owner_of``。"""
        self.grant_title: Callable[[str, AccountTitle], object] | None = None
        """帳號 ID ＋紀念稱號 → 記到帳號檔（5F-3b「碎晶的終結者」）；``None``＝不記。
        :func:`~trpg.api.app.create_app` 接上帳號的 ``grant_title``（帳號檔鎖，5D-R2）。"""
        self.account_titles: Callable[[str, str | None], tuple[str, ...]] | None = None
        """帳號 ID → 顯示用的紀念稱號（5F-3c：名片、評分榜、首殺、編年史）；``None``＝不顯示。
        :func:`~trpg.api.app.create_app` 接上帳號的 ``titles_of``。"""
        self._library = library
        self.offers = OfferPrefetcher(library, enabled=prefetch)
        """三選一的背景預先計算與快取（PERF-3）。"""
        self.battles = battles
        self.root = root
        self.clock = clock
        self._new_id = new_id
        self._lock = threading.RLock()
        self._world: WorldState | None = None
        self._chars: dict[str, CharacterState] = {}
        self._peeks: dict[str, tuple[int, CharacterState]] = {}
        """足跡用的別人存檔（不進 `_chars`、不預先計算；依修改時間重讀，6C-5）。"""
        self._entries: list[WorldLogEntry] | None = None
        self._stale_through: int | None = None
        """日誌裡舊規則的紀錄到哪一筆（6B-2：``trpg-wlog/1`` 的舊日誌規則已變、不能重播）。"""
        self._battles: dict[str, BattleSession] = {}
        self.first_kills = FirstKillRegistry(library, root)
        """全服首殺紀錄（5E-3）。"""
        self.boss_board = SeasonBossBoard(root)
        """賽季 Boss 的通關評分榜與首殺戰鬥紀錄（5F-3）。"""
        self.notes = LocationNoteStore(root)
        """地點留言（5E-3，#105；不進日誌）。"""
        self.league = LeagueStore(library, root, clock=self._now, library_of=lambda: self.library)
        """影子循環賽的賽果（5F-4；衍生資料，不進日誌）。"""
        self.league_runner = LeagueRunner(self.league)
        """循環賽的背景執行（5F-4；管理者開跑）。"""
        self.chronicle = SeasonChronicleStore(root)
        """編年史的季末紀錄（5F-5；上季角色的文字、名字與外觀）。"""

    # -- 路徑 -----------------------------------------------------------------

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def library(self) -> ContentLibrary:
        """這一季的內容庫（5F-R2）：照世界的季 ID 套上 ``season.yaml`` 的覆寫（沒有覆寫＝原本的內容
        庫）。還沒有世界存檔時用原本的（不為了這個建立世界）。"""
        with self._lock:
            if self._world is None and not self._world_path().is_file():
                return self._library
            return self._library.for_season(self.world().season_id)

    def _world_path(self) -> Path:
        return self.root / WORLD_FILE

    def _log_path(self) -> Path:
        return self.root / LOG_FILE

    def _char_path(self, character_id: str) -> Path:
        return char_path(self.root, character_id)

    # -- 讀取 -----------------------------------------------------------------

    def world(self) -> WorldState:
        """世界快照（第一次用到時讀檔或建立）。"""
        with self._lock:
            if self._world is None:
                path = self._world_path()
                if path.is_file():
                    self._world = loads_world(path.read_text(encoding="utf-8"))
                else:
                    start = self.clock() if self.season_start is None else self.season_start
                    self._world = WorldState(
                        season_id=SEASON_ID,
                        season_seed=secrets.randbits(64),
                        season_start=start,
                    )
                    write_atomic(path, dumps_world(self._world))
            return self._world

    def current_season(self) -> str:
        """目前的賽季 ID（帳號的角色上限用，5D-R2）。還沒有世界存檔時不建立，回第一季。"""
        with self._lock:
            if self._world is None and not self._world_path().is_file():
                return SEASON_ID
            return self.world().season_id

    def season_world(self, now: int) -> WorldState:
        """換日後的世界（公告板、公告用；只算，不寫檔，下一個世界動作才真的寫進去）。"""
        with self._lock:
            return roll_season(self.library, self.world(), now)[0]

    def entries(self) -> list[WorldLogEntry]:
        """世界動作日誌（第一次用到時讀檔）。"""
        with self._lock:
            if self._entries is None:
                path = self._log_path()
                text = path.read_text(encoding="utf-8") if path.is_file() else ""
                log = read_log(text) if text.strip() else None
                self._entries = [] if log is None else list(log.entries)
                self._stale_through = None if log is None else log.stale_through
            return self._entries

    def character_ids(self) -> list[str]:
        """存檔資料夾裡的角色 ID（依 ID 排序）。"""
        folder = self.root / CHARS_DIR
        with self._lock:
            found = set(self._chars)
            if folder.is_dir():
                found.update(p.stem for p in folder.glob("*.json"))
            return sorted(found)

    def character(self, character_id: str) -> CharacterState:
        with self._lock:
            char = self._chars.get(character_id)
            if char is not None:
                return char
            path = self._char_path(character_id)
            if not character_id.isalnum() or not path.is_file():
                raise WorldCharacterNotFoundError(f"找不到角色 {character_id}")
            char = loads_char(path.read_text(encoding="utf-8"))
            self._chars[character_id] = char
            self.offers.prefetch(self.world(), char)  # PERF-3：讀檔時已有的機遇、劇情步驟
            return char

    def _peek(self, character_id: str) -> CharacterState | None:
        """讀角色但不放進快取、不預先計算（足跡用；讀不了＝``None``）。"""
        char = self._chars.get(character_id)
        if char is not None:
            return char
        path = self._char_path(character_id)
        try:
            stamp = path.stat().st_mtime_ns
            cached = self._peeks.get(character_id)
            if cached is not None and cached[0] == stamp:
                return cached[1]
            char = loads_char(path.read_text(encoding="utf-8"))
        except (OSError, WorldError):
            return None
        self._peeks[character_id] = (stamp, char)
        return char

    def field_social(self, character_id: str) -> FieldSocial:
        """其他角色去過的地點（足跡）與每個地點的留言數（6C-5；畫面用，不進日誌）。

        來源是其他角色存檔的 ``visited_locations`` 加上目前位置（依角色 ID）；讀過的存檔依修改時間
        快取，不掃世界日誌。"""
        visitors: dict[tuple[str, str], list[Visitor]] = {}
        with self._lock:
            for cid in self.character_ids():
                other = None if cid == character_id else self._peek(cid)
                if other is None:
                    continue
                places = {r.key() for r in other.visited_locations}
                places.add((other.region, other.location))
                for place in sorted(places):
                    visitors.setdefault(place, []).append(Visitor(cid, other.hero.name_zh))
            try:
                notes = self.notes.all()
            except NoteError:
                notes = ()
        counts: dict[tuple[str, str], int] = {}
        for note in notes:
            place = (note.region, note.location)
            counts[place] = counts.get(place, 0) + 1
        return FieldSocial(visitors={k: tuple(v) for k, v in visitors.items()}, notes=counts)

    def growth_run(self, character_id: str) -> tuple[ContentLibrary, RunState]:
        """閃現與配點預覽用：大世界的內容庫視圖與角色轉成的 ``RunState``（帶角色技能種子）。"""
        with self._lock:
            char = self.character(character_id)
            run = as_run(char, seed=skill_seed(self.world(), char))
            return world_library(self.library), run

    def narrations(self, character_id: str, since: int) -> list[NarrateAction]:
        """這個角色在 ``since``（含）之後的說書人敘述（日誌順序；5B-5 事件卡從這裡讀旁白與情境敘述，
        代決 5B5-6）。從日誌尾端往回找，碰到更早的紀錄就停。"""
        with self._lock:
            found: list[NarrateAction] = []
            for entry in reversed(self.entries()):
                if entry.now < since:
                    break
                if entry.character_id == character_id and isinstance(entry.action, NarrateAction):
                    found.append(entry.action)
            found.reverse()
            return found

    def account_of(self, character_id: str) -> str:
        """角色的帳號（世界日誌的 ``actor``；沒有帳號時＝角色 ID，同 Q15）。"""
        found = None if self.actor_of is None else self.actor_of(character_id)
        return character_id if found is None else found

    def titles_of_account(
        self, account_id: str | None, season_id: str | None = None
    ) -> tuple[str, ...]:
        """帳號的紀念稱號（5F-3c；沒有帳號或沒接上帳號＝空）；``season_id`` 有值時只列那一季的。"""
        if account_id is None or self.account_titles is None:
            return ()
        return self.account_titles(account_id, season_id)

    def titles_of_character(
        self, character_id: str, season_id: str | None = None
    ) -> tuple[str, ...]:
        """角色所屬帳號的紀念稱號（稱號是帳號層級，5F-3b；5F-3c 顯示在名字旁）。"""
        if self.actor_of is None:
            return ()
        return self.titles_of_account(self.actor_of(character_id), season_id)

    def battle_of(self, character_id: str) -> BattleSession | None:
        with self._lock:
            return self._battles.get(character_id)

    # -- 建立 -----------------------------------------------------------------

    def create(
        self,
        name: str,
        weapon: str,
        keywords: Sequence[str],
        *,
        race: str | None = None,
        origin: str | None = None,
        seed: int | None = None,
        legacy: ChronicleHero | None = None,
    ) -> CharacterState:
        """建立角色（07 7.6 創角：起始武器＋2 個關鍵字，和一輪開局同一套函式；配點照預設，代決
        5A5-3）；站在起始區域的小鎮。不合法時拋 :class:`~trpg.roguelite.errors.ChoiceError`。

        ``legacy``（5F-5；5F-5c 玩法 PM 代決）：沿用上季角色的外觀＝名字與紙娃娃（取代 ``name``）。
        種族不算外觀：``race`` 省略＝帶上季的種族，給了就照新選（免費改）；紙娃娃裡跟著種族的部件
        （:data:`~trpg.server.chronicle.RACE_DOLL_FIELDS`）在種族改了時，目前的值新種族沒有才改回新角色範本的預設
        （5F-3c 代決，:func:`~trpg.server.chronicle.legacy_doll`）。"""
        if legacy is not None:
            name = legacy.name
            race = legacy.race if race is None else race
        start_seed = seed if seed is not None else secrets.randbelow(2**31)
        run = new_keyword_run(self.library, weapon, keywords, start_seed)
        run = with_origin(self.library, with_race(self.library, run, race), origin)
        update: dict[str, object] = {"name_zh": name}
        if legacy is not None and legacy.doll is not None:
            new_race = run.hero.race
            race_look = None if new_race is None else self.library.ruleset.race_def(new_race).look
            update["doll"] = legacy_doll(
                legacy.doll,
                legacy_race=legacy.race,
                race=new_race,
                base=run.hero.doll,
                race_look=race_look,
            )
        hero = run.hero.model_copy(update=update)
        with self._lock:
            self.world()
            taken = set(self.character_ids()) | {h.character_id for _, h in self.chronicle.heroes()}
            character_id = self._new_id()
            while character_id in taken:  # pragma: no cover - 機率極低
                character_id = self._new_id()
            char = new_character(
                self.library, character_id, hero, region=START_REGION, origin=run.origin
            )
            update = {"generated_skills": run.generated_skills, "news_seen_at": self.clock()}
            char = char.model_copy(update=update)  # 新角色：建立之前的消息不算「你不在的時候」
            self._save_char(char)
            return char

    # -- 動作 -----------------------------------------------------------------

    def sync(self, character_id: str) -> WorldOutcome:
        """讀取角色；進行中的戰鬥已結束時先把步驟送 ``fight`` 回寫（事件放在結果裡）。"""
        with self._lock:
            char = self.character(character_id)
            battle = self._battles.get(character_id)
            now = self.clock()
            if battle is None:
                return WorldOutcome(self.world(), char, (), now, None)
            with battle.lock:
                ended = battle.state.ended
                steps = tuple(battle.steps)
            if not ended:
                return WorldOutcome(self.world(), char, (), now, battle)
            del self._battles[character_id]
            return self._apply(char, FightAction(steps=steps), now)

    def act(self, character_id: str, action: WorldAction) -> WorldOutcome:
        """套用一個世界動作；不合法拋 :class:`~trpg.world.errors.WorldActionError`、什麼都不寫。"""
        if isinstance(action, FightAction):
            raise WorldConflictError("戰鬥請用開戰端點進行")
        with self._lock:
            synced = self.sync(character_id)
            if synced.battle is not None:
                raise WorldConflictError("戰鬥進行中，先打完這場")
            outcome = self._apply(synced.char, action, self.clock())
            return WorldOutcome(
                outcome.world,
                outcome.char,
                (*synced.events, *outcome.events),
                outcome.now,
                None,
            )

    def battle(self, character_id: str) -> tuple[WorldOutcome, BattleSession, list[StepRecord]]:
        """開戰或接續進行中的戰鬥（呼叫者之後用 ``/api/battles`` 操作）。"""
        with self._lock:
            synced = self.sync(character_id)
            if synced.battle is not None:
                return synced, synced.battle, []
            if synced.char.pending_encounter is None:
                raise WorldConflictError("目前沒有遭遇，不能開戰")
            prepared = prepare_battle(self.library, synced.char)
            battle, records = self.battles.open(prepared.setup, prepared.seed)
            battle.owner = None if self.actor_of is None else self.actor_of(character_id)  # 6S-1
            self._battles[character_id] = battle
            outcome = WorldOutcome(synced.world, synced.char, synced.events, synced.now, battle)
            return outcome, battle, records

    # -- 寫入 -----------------------------------------------------------------

    def _apply(self, char: CharacterState, action: WorldAction, now: int) -> WorldOutcome:
        world = self.world()
        actor = None if self.actor_of is None else self.actor_of(char.character_id)
        with using_offer_cache(self.offers.cache):  # PERF-3：背景算好的三選一
            result = world_step(self.library, world, char, action, now, actor=actor)
        entries = self.entries()
        seq = entries[-1].seq + 1 if entries else 1
        entry = WorldLogEntry(
            seq=seq, now=now, character_id=char.character_id, action=action, actor=actor
        )
        log_text = dumps_log([*entries, entry], stale_through=self._stale_through)
        write_atomic(self._log_path(), log_text)
        entries.append(entry)
        self._save_char(result.char)
        self._record_first_kills(result.char, result.events, seq, now, result.world.season_id)
        self._record_boss_clear(char, result.char, action, result.events, seq=seq, now=now)
        if result.world != world:
            write_atomic(self._world_path(), dumps_world(result.world))
        self._world = result.world
        self.offers.prefetch(result.world, result.char)  # PERF-3：新出現的機遇、劇情步驟
        self.auto_start_league(now)
        return WorldOutcome(result.world, result.char, result.events, now, None)

    # -- 影子循環賽（5F-4b） --------------------------------------------------

    def _now(self) -> int:
        """現在（``clock`` 可能在建立後被換掉，例如測試；循環賽的編年史時間用這個）。"""
        return self.clock()

    def season_boss_killed(self, season_id: str) -> bool:
        """這一季有沒有人首殺賽季 Boss（讀首殺紀錄；沒有資料或讀不了＝還沒首殺）。"""
        try:
            kills = self.first_kills.all()
        except Exception:
            _LOG.exception("首殺紀錄讀不了：當作還沒有人首殺賽季 Boss")
            return False
        return any(k.kind == "season_boss" and k.season_id == season_id for k in kills)

    def auto_start_league(self, now: int) -> bool:
        """第 ``signup_close_day + 1`` 天的刷新時間（第 14 天 6 點）之後、還沒有人首殺賽季 Boss 時
        自動開跑循環賽（玩法 PM 2026-11-03 代決；管理者手動開跑 ``POST /api/world/league/run``
        留著備用）。換日是被動的：在世界動作與看循環賽畫面時檢查。已經開跑、還有 ``pending`` 的
        賽程（伺服器重啟後）也在這裡接續。回傳這次有沒有開背景執行緒。出錯只記 log。"""
        try:
            with self._lock:
                world = self.season_world(now)
                record = self.league.record(world.season_id)
                if record is None:
                    if start_problem(self.library, world, now) is not None:
                        return False
                    if self.season_boss_killed(world.season_id):
                        return False  # 有人首殺：不自動開跑（娛樂賽與否是 5F-3／5F-5）
                    record = self.league.start(world, now)
                elif record.finished or self.league.stale(record):
                    return False  # 規則已變的賽程等管理者重新開跑（整個重跑）
            return self.league_runner.start()
        except LeagueError:
            return False
        except Exception:
            _LOG.exception("循環賽自動開跑失敗")
            return False

    def _record_first_kills(
        self,
        char: CharacterState,
        events: Sequence[WorldEvent],
        seq: int,
        now: int,
        season_id: str,
    ) -> None:
        """首殺紀錄是衍生資料：寫入失敗（檔壞了、磁碟）只記 log，不影響這次動作的回應（5D-R2）。
        日誌與角色已經寫好，之後可以從日誌補算。"""
        try:
            self.first_kills.record(char, events, seq=seq, now=now, season_id=season_id)
        except Exception:
            _LOG.exception("首殺紀錄寫入失敗（seq=%d，角色 %s）", seq, char.character_id)

    def _record_boss_clear(
        self,
        before: CharacterState,
        after: CharacterState,
        action: WorldAction,
        events: Sequence[WorldEvent],
        *,
        seq: int,
        now: int,
    ) -> None:
        """賽季 Boss 通關（5F-3）：評分榜記一筆；本季首殺另存那一場的戰鬥紀錄並記首殺。衍生資料：
        寫入失敗只記 log，不影響回應（同首殺）。"""
        cleared = next((e for e in events if isinstance(e, SeasonBossClearedEvent)), None)
        if cleared is None or not isinstance(action, FightAction):
            return
        season = self.world().season_id
        account = None if self.actor_of is None else self.actor_of(after.character_id)
        try:
            self.boss_board.record(
                before, after, cleared, season_id=season, account_id=account, seq=seq, now=now
            )
            if cleared.first:
                self._record_boss_first_kill(
                    before, after, action, cleared, account=account, seq=seq, now=now
                )
            if account is not None and self.grant_title is not None:
                title = AccountTitle(
                    id=f"season_boss:{cleared.boss}",
                    name_zh=cleared.title_zh,
                    season_id=season,
                    character_id=after.character_id,
                    at=now,
                )
                self.grant_title(account, title)
        except Exception:
            _LOG.exception("賽季 Boss 紀錄寫入失敗（seq=%d，角色 %s）", seq, after.character_id)

    def _record_boss_first_kill(
        self,
        before: CharacterState,
        after: CharacterState,
        action: FightAction,
        cleared: SeasonBossClearedEvent,
        *,
        account: str | None,
        seq: int,
        now: int,
    ) -> None:
        season = self.world().season_id
        log = self.boss_board.save_first_kill_log(
            season, first_kill_log_json(self.library, before, action)
        )
        encounter = before.pending_encounter
        self.first_kills.record_season_boss(
            FirstKill(
                kind="season_boss",
                target=cleared.boss,
                target_name_zh=cleared.name_zh,
                character_id=after.character_id,
                name=after.hero.name_zh,
                region=after.region if encounter is None else encounter.region,
                location=after.location if encounter is None else encounter.location,
                seq=seq,
                at=now,
                season_id=season,
                account_id=account,
                battle_log=log,
            )
        )

    # -- 季末重置（5F-5） ------------------------------------------------------

    def legacy_heroes(
        self, account_id: str | None
    ) -> tuple[tuple[SeasonChronicleEntry, ChronicleHero], ...]:
        """上季（含更早）的角色，新的季在前；``account_id`` 給了只列那個帳號的（開發模式沒登入
        ＝全部）。"""
        found = self.chronicle.heroes()
        if account_id is None:
            return found
        return tuple((s, h) for s, h in found if h.account_id == account_id)

    def legacy_hero(self, character_id: str, account_id: str | None) -> ChronicleHero:
        """沿用的上季角色；不存在或不是這個帳號的拋 :class:`WorldCharacterNotFoundError`。"""
        for _, hero in self.legacy_heroes(account_id):
            if hero.character_id == character_id:
                return hero
        raise WorldCharacterNotFoundError(f"找不到上季角色 {character_id}")

    def season_reset(
        self,
        *,
        accounts: AccountStore | None,
        start: int,
        season_id: str | None = None,
        seed: int | None = None,
        force: bool = False,
        dry_run: bool = True,
        confirm_season: str | None = None,
        backup_root: Path | None = None,
    ) -> SeasonResetReport:
        """季末重置（管理者）：存檔資料夾＝世界資料夾的上一層。真的執行時 ``confirm_season`` 要等於
        目前的季 ID；循環賽背景執行中一律拒絕。執行後清掉記憶體快取（進行中的戰鬥跟著角色清掉）。"""
        with self._lock:
            if self.league_runner.running:
                raise SeasonResetError("循環賽正在背景執行，等跑完再重置")
            current = self.current_season()
            if not dry_run and confirm_season != current:
                raise SeasonResetError(f"確認的季 ID 不符（目前是 {current}）")
            battles = len(self._battles)
            extra = (ResetLine(label_zh="進行中的大世界戰鬥", count=battles),) if battles else ()
            report = season_reset(
                self.library,
                self.root.parent,
                world_dir=self.root,
                start=start,
                now=self.clock(),
                accounts=accounts,
                season_id=season_id,
                seed=seed,
                force=force,
                dry_run=dry_run,
                backup_root=backup_root,
                extra_cleared=extra,
            )
            if not dry_run:
                self._forget()
            return report

    def verify_replay(self, kind: str, season_id: str, key: str) -> ReplayCheck:
        """從封存（目前這一季從世界資料夾）重播查證一筆首殺（``key``＝目標）或一場循環賽
        （``key``＝場次 ID）；只讀（5F-5c）。找不到拋 :class:`ArchiveRecordNotFoundError`。"""
        save_dir = self.root.parent
        if kind == "first_kill":
            return verify_first_kill(save_dir, self.root, season_id, key)
        return verify_league_match(save_dir, self.root, season_id, key)

    def _forget(self) -> None:
        """季末重置之後：記憶體裡的世界、角色、日誌、進行中的戰鬥與循環賽快取全部丟掉、重讀。"""
        self._world = None
        self._chars = {}
        self._entries = None
        self._stale_through = None
        self._battles = {}
        self.league.forget()

    def _save_char(self, char: CharacterState) -> None:
        write_atomic(self._char_path(char.character_id), dumps_char(char))
        self._chars[char.character_id] = char
