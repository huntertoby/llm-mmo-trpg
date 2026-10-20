"""roguelite 一輪的工作階段（Phase 3-5a；``/api/runs``）。

- 一個 :class:`RunSession` ＝ 一輪（``RunState``）＋ 目前的戰鬥（:class:`BattleSession`，登記在
  戰鬥工作階段表裡，用既有的 ``/api/battles/{id}`` 端點操作）。
- 戰鬥結束後，任何一輪的請求先 :meth:`RunSession.sync`：以 ``finish_battle`` 寫回主角並前進到下一個
  節點。
- 存檔：``RunSave``（``trpg-run/1``），戰鬥中存的是 ``setup`` 以外的一切（種子、步驟、指令）；讀檔時
  重建 ``setup``、重播步驟、還原指令（:meth:`SessionStore.open`）。
- 鎖的順序：一輪的鎖 → 戰鬥的鎖。
"""

from __future__ import annotations

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
    new_run,
    ruleset_hash,
    save_path,
    write_save,
)
from trpg.roguelite.errors import NodeConflictError
from trpg.roguelite.state import BattleNode, CampfireNode, Choice, LevelUpNode
from trpg.shared.errors import TrpgError
from trpg.shared.types import Attribute

__all__ = ["RunNotFoundError", "RunSession", "RunStore"]


class RunNotFoundError(TrpgError):
    """不存在的一輪或存檔（404）。"""


class RunSession:
    def __init__(self, run_id: str, library: ContentLibrary, run: RunState) -> None:
        self.run_id = run_id
        self.library = library
        self.run = run
        self.battle: BattleSession | None = None
        self.lock = threading.Lock()

    def sync(self) -> None:
        """目前的戰鬥結束了就結算（寫回主角、前進到下一個節點）。"""
        battle = self.battle
        if battle is None:
            return
        with battle.lock:
            if not battle.state.ended:
                return
            self.run = finish_battle(self.library, self.run, battle.state, len(battle.steps))
        self.battle = None

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

    def create(self, build: str, seed: int, attributes: dict[Attribute, int] | None) -> RunSession:
        run = new_run(self.library, build, seed, attributes)
        with self._lock:
            run_id = self._new_id()
            while run_id in self._runs:  # pragma: no cover - 機率極低
                run_id = self._new_id()
        return self._register(RunSession(run_id, self.library, run))

    def get(self, run_id: str) -> RunSession:
        with self._lock:
            session = self._runs.get(run_id)
        if session is None:
            raise RunNotFoundError(f"找不到一輪 {run_id}")
        return session

    def battle(self, session: RunSession) -> tuple[BattleSession, list[StepRecord]]:
        """開始本場戰鬥，或接續進行中的戰鬥（呼叫者持有一輪的鎖）。"""
        session.sync()
        if session.battle is not None:
            return session.battle, []
        if not isinstance(session.run.node, BattleNode):
            raise NodeConflictError(f"目前不是戰鬥（{session.run.node.kind}）")
        setup = battle_setup(self.library, session.run)
        seed = session.run.plan_of(session.battle_index()).seed
        battle, records = self.battles.open(setup, seed)
        session.battle = battle
        return battle, records

    def choose(self, session: RunSession, choice: Choice) -> None:
        session.sync()
        session.run = apply_choice(self.library, session.run, choice)

    def ruleset_hash(self) -> str:
        """目前內容庫的雜湊（第一次用到時才算，之後快取）。"""
        if self._ruleset_hash is None:
            self._ruleset_hash = ruleset_hash(self.library)
        return self._ruleset_hash

    def save(self, session: RunSession) -> tuple[Path, RunSave]:
        session.sync()
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
