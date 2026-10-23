"""roguelite 一輪的工作階段（Phase 3-5a；``/api/runs``）。

- 一個 :class:`RunSession` ＝ 一輪（``RunState``）＋ 目前的戰鬥（:class:`BattleSession`，登記在
  戰鬥工作階段表裡，用既有的 ``/api/battles/{id}`` 端點操作）。
- 戰鬥結束後，任何一輪的請求先 :meth:`RunSession.sync`：以 ``finish_battle`` 寫回主角並前進到下一個
  節點。
- 存檔：``RunSave``（``trpg-run/5``），戰鬥中存的是 ``setup`` 以外的一切（種子、步驟、指令）；讀檔時
  重建 ``setup``、重播步驟、還原指令（:meth:`SessionStore.open`）。
- 鎖的順序：一輪的鎖 → 戰鬥的鎖。
"""

from __future__ import annotations

import logging
import secrets
import threading
from collections.abc import Callable
from pathlib import Path

from trpg.api.sessions import BattleSession, SessionStore, StepRecord
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite import (
    RunSave,
    RunState,
    SavedBattle,
    SaveFormatError,
    apply_choice,
    battle_setup,
    finish_battle,
    load_save,
    new_dev_run,
    new_keyword_run,
    new_run,
    ruleset_hash,
    save_path,
    write_save,
)
from trpg.roguelite.errors import NodeConflictError
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    Choice,
    LevelUpNode,
    LoadoutChoice,
    RespecChoice,
    SpendChoice,
)
from trpg.shared.errors import TrpgError
from trpg.shared.types import Attribute

__all__ = ["RunNotFoundError", "RunSession", "RunStore"]

_LOG = logging.getLogger(__name__)


class RunNotFoundError(TrpgError):
    """不存在的一輪或存檔（404）。"""


class RunSession:
    def __init__(self, run_id: str, library: ContentLibrary, run: RunState) -> None:
        self.run_id = run_id
        self.library = library
        self.run = run
        self.battle: BattleSession | None = None
        self.lock = threading.Lock()

    def sync(self) -> bool:
        """目前的戰鬥結束了就結算（寫回主角、前進到下一個節點）；有結算時回傳 ``True``。"""
        battle = self.battle
        if battle is None:
            return False
        with battle.lock:
            if not battle.state.ended:
                return False
            self.run = finish_battle(
                self.library, self.run, battle.state, len(battle.steps), battle.steps
            )
        self.battle = None
        return True

    def to_save(self) -> RunSave:
        saved = None
        if self.battle is not None:
            with self.battle.lock:
                saved = SavedBattle(
                    index=self.battle_index(),
                    seed=self.battle.seed,
                    steps=list(self.battle.steps),
                    orders=self.battle.order_log,
                )
        return RunSave(run_id=self.run_id, run=self.run, battle=saved)

    def battle_index(self) -> int:
        node = self.run.node
        assert isinstance(node, BattleNode)
        return node.index

    def known_skills(self) -> list[SkillDef]:
        """這一輪的生成技能與目前的候選（``/api/skills/{id}`` 找不到內容庫的技能時查這裡）。"""
        skills = list(self.run.generated_skills)
        node = self.run.node
        offer = node.offer if isinstance(node, LevelUpNode | CampfireNode) else None
        if offer is not None:
            skills += offer.candidates
        return skills


def _new_run_id() -> str:
    return secrets.token_hex(6)


class RunStore:
    """記憶體內的一輪工作階段表；存檔寫在 ``save_dir``。"""

    def __init__(
        self,
        library: ContentLibrary,
        battles: SessionStore,
        save_dir: Path,
        *,
        new_id: Callable[[], str] = _new_run_id,
    ) -> None:
        self.library = library
        self.battles = battles
        self.save_dir = save_dir
        self._new_id = new_id
        self._runs: dict[str, RunSession] = {}
        self._ruleset_hash: str | None = None
        self._lock = threading.Lock()

    def _register(self, session: RunSession) -> RunSession:
        with self._lock:
            self._runs[session.run_id] = session
        return session

    def create(
        self,
        seed: int,
        attributes: dict[Attribute, int] | None,
        *,
        weapon: str | None = None,
        keywords: tuple[str, ...] | None = None,
        dev_pack: str | None = None,
        build: str | None = None,
        test_mode: bool = False,
        test_equipment: dict[str, str] | None = None,
    ) -> RunSession:
        """開新一輪（Phase 3-24b2）：``weapon`` ＋ ``keywords``、``dev_pack`` 或 ``build`` 擇一。"""
        if build is not None:
            run = new_run(self.library, build, seed, attributes)
        elif dev_pack is not None:
            run = new_dev_run(self.library, dev_pack, seed, attributes)
        else:
            assert weapon is not None and keywords is not None
            run = new_keyword_run(
                self.library,
                weapon,
                keywords,
                seed,
                attributes,
                test_mode=test_mode,
                test_equipment=test_equipment,
            )
        with self._lock:
            run_id = self._new_id()
            while run_id in self._runs:  # pragma: no cover - 機率極低
                run_id = self._new_id()
        session = self._register(RunSession(run_id, self.library, run))
        self.autosave(session)
        return session

    def get(self, run_id: str) -> RunSession:
        with self._lock:
            session = self._runs.get(run_id)
        if session is None:
            raise RunNotFoundError(f"找不到一輪 {run_id}")
        return session

    def battle(self, session: RunSession) -> tuple[BattleSession, list[StepRecord]]:
        """開始本場戰鬥，或接續進行中的戰鬥（呼叫者持有一輪的鎖）。"""
        self.sync(session)
        if session.battle is not None:
            return session.battle, []
        if not isinstance(session.run.node, BattleNode):
            raise NodeConflictError(f"目前不是戰鬥（{session.run.node.kind}）")
        setup = battle_setup(self.library, session.run)
        seed = session.run.plan_of(session.battle_index()).seed
        battle, records = self.battles.open(setup, seed)
        session.battle = battle
        self.autosave(session)
        return battle, records

    def choose(self, session: RunSession, choice: Choice) -> None:
        self.sync(session)
        if session.battle is not None and isinstance(
            choice, SpendChoice | RespecChoice | LoadoutChoice
        ):
            # 戰鬥進行中改主角的技能會讓存檔重播不一致：戰鬥結束後才能花點數
            raise NodeConflictError("戰鬥進行中不能分配技能點或換裝")
        session.run = apply_choice(self.library, session.run, choice)
        self.autosave(session)

    def sync(self, session: RunSession) -> None:
        """結算已結束的戰鬥；有結算（節點改變）就自動存檔（呼叫者持有一輪的鎖）。"""
        if session.sync():
            self.autosave(session)

    def autosave(self, session: RunSession) -> None:
        """自動存檔（Phase 3-6）：覆寫同一個檔案。寫不進去時只記錄警告，不讓遊戲動作失敗。"""
        try:
            self.save(session)
        except OSError as exc:
            _LOG.warning("自動存檔失敗（%s）：%s", session.run_id, exc)

    def autosave_battle(self, battle_id: str) -> None:
        """戰鬥端點處理完一個動作或決定後呼叫：找出擁有這場戰鬥的一輪並自動存檔（沒有就略過，
        例如單獨開的戰鬥）。必須在釋放戰鬥的鎖之後呼叫（鎖的順序：一輪 → 戰鬥）。"""
        with self._lock:
            sessions = list(self._runs.values())
        for session in sessions:
            battle = session.battle
            if battle is not None and battle.battle_id == battle_id:
                with session.lock:
                    if session.battle is battle:
                        self.autosave(session)  # 戰鬥結束時 save 會先結算
                return

    def ruleset_hash(self) -> str:
        """目前內容庫的雜湊（第一次用到時才算，之後快取）。"""
        if self._ruleset_hash is None:
            self._ruleset_hash = ruleset_hash(self.library)
        return self._ruleset_hash

    def save(self, session: RunSession) -> tuple[Path, RunSave]:
        session.sync()  # 呼叫者持有一輪的鎖；結算後直接寫入最新狀態
        save = session.to_save().model_copy(update={"ruleset_hash": self.ruleset_hash()})
        return write_save(self.save_dir, save), save

    def load(self, run_id: str) -> RunSession:
        """讀檔（取代記憶體內同一個 run id 的一輪）；戰鬥中的存檔重播到存檔當下。"""
        path = save_path(self.save_dir, run_id)
        if not path.is_file():
            raise RunNotFoundError(f"找不到存檔 {path.name}")
        save = load_save(path)
        session = RunSession(save.run_id, self.library, save.run)
        if save.battle is not None:
            if save.ruleset_hash != self.ruleset_hash():
                raise SaveFormatError("內容檔已變更，無法重播戰鬥中的存檔；可讀取戰鬥之間的存檔")
            node = save.run.node
            assert isinstance(node, BattleNode)
            if save.battle.seed != save.run.plan_of(node.index).seed:
                raise SaveFormatError("存檔的戰鬥種子與一輪的安排不符")
            setup = battle_setup(self.library, save.run)
            try:
                session.battle, _ = self.battles.open(
                    setup, save.battle.seed, (save.battle.steps, save.battle.orders)
                )
            except TrpgError as exc:
                raise SaveFormatError(f"存檔的戰鬥無法重播：{exc}") from exc
        return self._register(session)

    def saves(self) -> list[RunSave]:
        """存檔資料夾裡的存檔（依檔名排序；讀不了的略過）。"""
        if not self.save_dir.is_dir():
            return []
        found: list[RunSave] = []
        for path in sorted(self.save_dir.glob("run-*.json")):
            try:
                found.append(load_save(path))
            except SaveFormatError:
                continue
        return found

    def find_skill(self, skill_id: str) -> SkillDef | None:
        with self._lock:
            sessions = list(self._runs.values())
        for session in sessions:
            for skill in session.known_skills():
                if skill.id == skill_id:
                    return skill
        return None
