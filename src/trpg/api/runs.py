"""roguelite 一輪的工作階段（Phase 3-5a；``/api/runs``）。

- 一個 :class:`RunSession` ＝ 一輪（``RunState``）＋ 目前的戰鬥（:class:`BattleSession`，登記在
  戰鬥工作階段表裡，用既有的 ``/api/battles/{id}`` 端點操作）。
- 戰鬥結束後，任何一輪的請求先 :meth:`RunSession.sync`：以 ``finish_battle`` 寫回主角並前進到下一個
  節點。
- 存檔：``RunSave``（``trpg-run/13``），戰鬥中存的是 ``setup`` 以外的一切（種子、步驟、指令）；
  讀檔時重建 ``setup``、重播步驟、還原指令（:meth:`SessionStore.open`）。
- 鎖的順序：一輪的鎖 → 戰鬥的鎖。
"""

from __future__ import annotations

import logging
import secrets
import threading
from collections.abc import Callable
from pathlib import Path

from trpg.api.llm_source import DEFAULT_ALERT_PERMILLE, LLM_OFF_NOTICE, LlmProvider
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
    load_save_noted,
    new_dev_run,
    new_keyword_run,
    new_run,
    ruleset_hash,
    save_path,
    upgrade_save,
    write_save,
)
from trpg.roguelite.errors import NodeConflictError
from trpg.roguelite.llm_hook import FlashSourceFactory, use_flash_source, use_proposer
from trpg.roguelite.start import with_origin, with_race
from trpg.roguelite.state import (
    AllocateChoice,
    BattleNode,
    Choice,
    CompleteOfferNode,
    DissolveChoice,
    FlashChoice,
    FlashPickChoice,
    InheritChoice,
    LevelUpNode,
    LoadoutChoice,
    RespecAttributesChoice,
)
from trpg.shared.errors import TrpgError
from trpg.shared.types import Attribute
from trpg.skillgen.proposal_topic import LlmProposer

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
        self.proposer: LlmProposer | None = None
        """這一輪的 LLM 提議器（4-L6b；``run.llm`` 為真且有模型來源時才有）。"""
        self.flash_source: FlashSourceFactory | None = None
        """這一輪的閃現變化提議來源（3W-5；``run.llm`` 為真且有模型來源時才有）。"""
        self.llm_notice: str | None = None
        """開局時要提示一次的訊息（例如本機模型未啟動）；只在建立的回應帶出。"""
        self.load_notice: str | None = None
        """讀檔時要提示一次的訊息（例如捨棄了格式過舊的戰鬥，3W-R1）；只在讀檔的回應帶出。"""
        self.alert_permille = DEFAULT_ALERT_PERMILLE

    def sync(self) -> bool:
        """目前的戰鬥結束了就結算（寫回主角、前進到下一個節點）；有結算時回傳 ``True``。"""
        battle = self.battle
        if battle is None:
            return False
        with battle.lock:
            if not battle.state.ended:
                return False
            with use_proposer(self.proposer):
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
        """這一輪的生成技能、目前的候選與待選的閃現選項（``/api/skills/{id}`` 找不到內容庫的技能時
        查這裡）。"""
        skills = list(self.run.generated_skills)
        node = self.run.node
        if isinstance(node, LevelUpNode | CompleteOfferNode):
            skills += node.offer.candidates
        if self.run.pending_flash is not None:
            skills += [o.skill for o in self.run.pending_flash.offer.options]
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
        llm: LlmProvider | None = None,
    ) -> None:
        self.library = library
        self.battles = battles
        self.save_dir = save_dir
        self._new_id = new_id
        self.llm = llm
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
        race: str | None = None,
        origin: str | None = None,
        llm: bool = False,
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
        run = with_race(self.library, run, race)  # 種族（Phase 3R-2）
        run = with_origin(self.library, run, origin)  # 出身（Phase 3R-3a）
        notice = None
        if llm:  # LLM 生成開關（Phase 4-L6b）：連不到本機模型時這一輪當作關閉並提示一次
            notice = self.llm.probe() if self.llm is not None else LLM_OFF_NOTICE
            if notice is None:
                run = run.model_copy(update={"llm": True})
        with self._lock:
            run_id = self._new_id()
            while run_id in self._runs:  # pragma: no cover - 機率極低
                run_id = self._new_id()
        session = RunSession(run_id, self.library, run)
        session.llm_notice = notice
        self._attach_llm(session)
        self._register(session)
        self.autosave(session)
        return session

    def _attach_llm(self, session: RunSession) -> None:
        """``run.llm`` 的一輪裝上提議器（開局與讀檔共用；讀檔不探測連線，失敗走原本的退回）。"""
        if self.llm is None:
            return
        session.alert_permille = self.llm.alert_permille()
        if session.run.llm:
            session.proposer = self.llm.proposer(self.library)
            session.flash_source = self.llm.flash_source(self.library)

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
        if session.run.pending_flash is not None:
            raise NodeConflictError("還有閃現的選項沒有選，請先送出 flash_pick")
        setup = battle_setup(self.library, session.run)
        seed = session.run.plan_of(session.battle_index()).seed
        battle, records = self.battles.open(setup, seed)
        session.battle = battle
        self.autosave(session)
        return battle, records

    def choose(self, session: RunSession, choice: Choice) -> None:
        self.sync(session)
        if session.battle is not None and isinstance(
            choice,
            FlashChoice
            | FlashPickChoice
            | DissolveChoice
            | InheritChoice
            | LoadoutChoice
            | RespecAttributesChoice
            | AllocateChoice,
        ):
            # 戰鬥進行中改主角的技能會讓存檔重播不一致：戰鬥結束後才能閃現、配點或換裝
            raise NodeConflictError("戰鬥進行中不能閃現、分配屬性點或換裝")
        with use_proposer(session.proposer), use_flash_source(session.flash_source):
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
        loaded, notice = load_save_noted(path)  # 引擎版本不符的戰鬥中存檔捨棄那場戰鬥（3W-R1）
        save = upgrade_save(self.library, loaded)  # 舊存檔照角色階級重配技能（3W-9）
        session = RunSession(save.run_id, self.library, save.run)
        session.load_notice = notice
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
        self._attach_llm(session)
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
