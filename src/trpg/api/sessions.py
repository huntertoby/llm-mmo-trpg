"""戰鬥工作階段（Phase 3-2；``docs/phases/Phase3計畫.md`` 4.2、4.3）。

一場網頁戰鬥 ＝ 一個 :class:`BattleSession`：玩家操控 **主角**（我方第一個單位），其餘單位由
效用 AI（:class:`~trpg.engine.ai.commanded.CommandedAI`）控制。

- 工作階段只保存 ``setup ＋ seed ＋ 步驟列表``（與 ``BattleLog.actions`` 同格式）以及由它們推導出的
  目前狀態；目前狀態永遠可以用 :func:`trpg.engine.runner.replay` 重現（3-5 的存檔就存這些）。
- **自動推進** 用 :func:`trpg.engine.runner.advance`（``run_battle`` 的同一個迴圈），停止條件
  :meth:`BattleSession.awaits_player`：輪到主角且主角有 ``EndTurn`` 以外的合法動作、或出現
  主角的反應詢問。只剩 ``EndTurn`` 時自動結束回合、非主角的詢問一律接受，與 ``run_battle`` 相同。
- 戰術指令：我方不註冊指揮官，玩家的指令以 :meth:`CommandedAI.issue` 直接下達，下一次我方 AI
  決策即生效；紀錄（含下達時的輪數）就是 ``CommandedAI.order_log``，匯出時寫進
  ``BattleLog.orders``。重播只重播動作，所以指令不影響重播一致性。
- 每個工作階段一把 :class:`threading.Lock`；呼叫者（路由）持有鎖之後才呼叫會改變狀態的方法。
- 伺服器層可以用 :mod:`secrets` 產生 ID（引擎內仍禁止）。重啟伺服器後工作階段消失。
"""

from __future__ import annotations

import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass

from trpg.api.schemas import Awaiting, CreateBattleRequest
from trpg.api.workshop import custom_skill_defs, equip_custom_skills
from trpg.content.library import ContentLibrary
from trpg.content.maps import BOSS_ARCHETYPE, TRAINING_ARCHETYPE
from trpg.engine.actions import ACTION_ADAPTER, Action, Decision, FollowupTarget, Step, UseSkill
from trpg.engine.ai.orders import OrderRecord, OrderSet, validate_order
from trpg.engine.battle import begin_battle, has_only_end_turn, resolve, resume
from trpg.engine.events import EventBase
from trpg.engine.preview import Preview, preview
from trpg.engine.results import Pending, ResolveResult
from trpg.engine.runner import (
    DEFAULT_MAX_ACTIONS,
    BattleLog,
    BattleRun,
    StepLimitExceeded,
    advance,
    apply_step,
)
from trpg.engine.setup import BattleSetup, BattleSetupError, build_setup
from trpg.engine.state import BattleState, PendingResolution, state_from_json
from trpg.shared.errors import IllegalActionError, TrpgError
from trpg.shared.types import Team, UnitId
from trpg.sim.commanders import build_commanded_ai
from trpg.sim.lineup import UnknownBuildError, build_allies, default_lineup

__all__ = [
    "AutoAdvanceLimitError",
    "BattleNotFoundError",
    "BattleSession",
    "InvalidRequestError",
    "SessionConflictError",
    "SessionStore",
    "StepRecord",
    "order_problems",
    "playable_maps",
]


class BattleNotFoundError(TrpgError):
    """不存在的戰鬥（404）。"""


class SessionConflictError(TrpgError):
    """請求與工作階段目前在等的東西不符：不是主角的回合、不是在等決定、戰鬥已結束（409）。"""


class InvalidRequestError(TrpgError):
    """請求內容格式正確但引用了不存在的內容、或戰術指令無效（422）。"""


class AutoAdvanceLimitError(TrpgError):
    """自動推進超過步數上限（500）。工作階段保留，``battle_id`` 讓客戶端仍能讀取或匯出紀錄。"""

    def __init__(self, battle_id: str, message: str) -> None:
        self.battle_id = battle_id
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class StepRecord:
    """一次請求中結算的一步（開場時 ``step`` 為 ``None``）。"""

    step: Step | None
    result: ResolveResult


class BattleSession:
    """一場網頁戰鬥。建立後呼叫 :meth:`begin`（推進到第一次輪到主角）。"""

    def __init__(
        self,
        battle_id: str,
        library: ContentLibrary,
        setup: BattleSetup,
        seed: int,
        *,
        max_auto_steps: int = DEFAULT_MAX_ACTIONS,
    ) -> None:
        self.battle_id = battle_id
        self.library = library
        self.setup = setup
        self.seed = seed
        self.max_auto_steps = max_auto_steps
        self.lock = threading.Lock()
        self.policy = build_commanded_ai(library.ai_profiles)
        """我方隊友與敵方共用的效用 AI（敵方沒有指揮官，與 CLI 預設相同）。"""
        self._opening = begin_battle(setup, seed)
        self.state: BattleState = self._opening.state
        self.pending: Pending | None = self._opening.pending
        self.steps: list[Step] = []
        self.events: list[EventBase] = list(self._opening.events)
        self.hero_id: UnitId = next(u.id for u in self.state.units_sorted() if u.team is Team.ALLY)
        """主角：我方第一個單位（``hero_build`` 的英雄；單位 ID 依設定順序分配）。"""

    # -- 狀態 ------------------------------------------------------------------

    def awaits_player(self, state: BattleState, pending: Pending | None) -> bool:
        """自動推進的停止條件：主角的反應詢問，或輪到主角且有 ``EndTurn`` 以外的合法動作。"""
        if pending is not None:
            return pending.unit_id == self.hero_id
        return state.active_unit == self.hero_id and not has_only_end_turn(state)

    @property
    def awaiting(self) -> Awaiting:
        if self.state.ended:
            return "ended"
        if self.pending is not None and self.pending.unit_id == self.hero_id:
            return "decision"
        if self.awaits_player(self.state, self.pending):
            return "action"
        return "stalled"

    @property
    def orders(self) -> OrderSet:
        return self.policy.current_orders(Team.ALLY)

    @property
    def order_log(self) -> list[OrderRecord]:
        return list(self.policy.order_log)

    # -- 推進 ------------------------------------------------------------------

    def begin(self) -> list[StepRecord]:
        """開場事件 ＋ 自動推進到第一次輪到主角（或戰鬥結束）。"""
        return [StepRecord(None, self._opening), *self._advance()]

    def _commit(self, step: Step, result: ResolveResult) -> StepRecord:
        self.state = result.state
        self.pending = result.pending
        self.steps.append(step)
        self.events.extend(result.events)
        return StepRecord(step, result)

    def _advance(self) -> list[StepRecord]:
        """自動推進。每一步結算後立刻寫回工作階段，所以超過上限（``StepLimitExceeded``）時
        已結算的部分仍然保留、仍可重播。"""
        records: list[StepRecord] = []

        def on_step(step: Step | None, result: ResolveResult) -> None:
            assert step is not None
            records.append(self._commit(step, result))

        try:
            advance(
                self.state,
                self.pending,
                self.policy,
                on_step=on_step,
                max_actions=self.max_auto_steps,
                stop=self.awaits_player,
            )
        except StepLimitExceeded as exc:
            raise AutoAdvanceLimitError(self.battle_id, str(exc)) from exc
        return records

    def _require(self, awaiting: Awaiting) -> None:
        current = self.awaiting
        if current == awaiting:
            return
        reasons = {
            "ended": "戰鬥已結束",
            "decision": "目前在等主角回答反應詢問",
            "action": "目前在等主角的動作",
            "stalled": "自動推進超過上限，戰鬥無法繼續",
        }
        raise SessionConflictError(reasons[current])

    def _require_hero(self, action: Action) -> None:
        if action.unit_id != self.hero_id:
            hero = self.state.units[self.hero_id].name_zh
            raise IllegalActionError(f"只能操控主角 {hero}（{self.hero_id}）")

    def act(self, action: Action) -> list[StepRecord]:
        """結算主角的動作，再自動推進。不合法時拋出 ``IllegalActionError``，狀態不變。"""
        self._require("action")
        self._require_hero(action)
        result = resolve(self.state, action)
        return [self._commit(action, result), *self._advance()]

    def decide(
        self,
        accept: bool,
        copy_cast: UseSkill | None = None,
        followup_target: FollowupTarget | None = None,
    ) -> list[StepRecord]:
        """回答主角的反應詢問（或 ``copy_skill`` 的選目標，``copy_cast`` 為複製技能的選取；或複合
        技能第二段的選目標，``followup_target`` 為第二段的選取，Phase 3F-4a），再自動推進。不合法
        時拋出 ``IllegalActionError``，狀態不變。"""
        self._require("decision")
        decision = Decision(
            unit_id=self.hero_id,
            accept=accept,
            copy_cast=copy_cast,
            followup_target=followup_target,
        )
        result = resume(self.state, decision)
        return [self._commit(decision, result), *self._advance()]

    def preview(self, action: Action) -> Preview:
        """預覽主角的動作（不改變工作階段；引擎的 ``preview`` 已濾掉對方的隱藏陷阱）。"""
        pending = self.state.pending
        if self.awaiting == "decision" and pending is not None and pending.kind == "copy_skill":
            return self._preview_copy(pending, action)
        if self.awaiting == "decision" and pending is not None and pending.kind == "followup":
            return self._preview_followup(pending, action)
        self._require("action")
        self._require_hero(action)
        return preview(self.state, action)

    def _preview_copy(self, pending: PendingResolution, pick: Action) -> Preview:
        """``copy_skill`` 暫停中（Phase 3C-6a）：``pick`` 是被複製技能的選取（``copy_options``
        之一）；預覽「暫停前的狀態帶著這個選取重新結算原本的施放」，與 ``decide`` 的結果一致。"""
        self._require_hero(pick)
        if not isinstance(pick, UseSkill):
            raise IllegalActionError("複製技能的預覽必須是被複製技能的選取（use_skill）")
        original = ACTION_ADAPTER.validate_json(pending.action_json)
        assert isinstance(original, UseSkill)
        base = state_from_json(pending.base_state_json)
        return preview(base, original.model_copy(update={"copy_cast": pick}))

    def _preview_followup(self, pending: PendingResolution, pick: Action) -> Preview:
        """複合技能第二段的暫停中（Phase 3F-4b）：``pick`` 是原本的施放帶上 ``followup_target``
        （``followup_options`` 之一）；預覽「暫停前的狀態帶著這個選取重新結算原本的施放」，與
        ``decide`` 的結果一致（第一段已結算的部分也在預覽裡）。"""
        self._require_hero(pick)
        original = ACTION_ADAPTER.validate_json(pending.action_json)
        assert isinstance(original, UseSkill)
        if (
            not isinstance(pick, UseSkill)
            or pick.skill_id != original.skill_id
            or pick.followup_target is None
        ):
            raise IllegalActionError(
                f"第二段的預覽必須是「{original.skill_id}」帶上 followup_target 的 use_skill"
            )
        base = state_from_json(pending.base_state_json)
        return preview(base, original.model_copy(update={"followup_target": pick.followup_target}))

    def restore(self, steps: list[Step], orders: list[OrderRecord]) -> None:
        """讀檔（Phase 3-5a）：依序重播存檔的步驟（不自動推進），再還原隊友指令紀錄。重播失敗時
        拋出引擎的錯誤（呼叫者轉成存檔錯誤）。"""
        for step in steps:
            self._commit(step, apply_step(self.state, step))
        self.policy.restore_orders(orders)

    def set_orders(self, orders: OrderSet) -> OrderRecord:
        """設定我方隊友的戰術指令（空集合 ＝ 取消）。無效時拋出 ``InvalidRequestError``。"""
        if self.state.ended:
            raise SessionConflictError("戰鬥已結束")
        problems = order_problems(self.state, orders, self.hero_id)
        if problems:
            raise InvalidRequestError("；".join(problems))
        return self.policy.issue(self.state, Team.ALLY, orders)

    def to_log(self) -> BattleLog:
        """與 ``trpg battle --log-json`` 同格式的紀錄（``final_state`` 為目前狀態）。"""
        run = BattleRun(
            self.setup,
            self.seed,
            self.state,
            list(self.steps),
            list(self.events),
            orders=self.order_log,
        )
        return run.to_log()


def order_problems(state: BattleState, orders: OrderSet, hero_id: UnitId) -> list[str]:
    """玩家下給我方隊友的指令的問題（中文；空串列 ＝ 有效）。"""
    problems = [
        reason
        for order in orders.team_orders
        if (reason := validate_order(state, Team.ALLY, order)) is not None
    ]
    for uid in sorted(orders.unit_orders):
        unit = state.units.get(uid)
        if unit is None:
            problems.append(f"單位 {uid} 不存在")
            continue
        if unit.team is not Team.ALLY:
            problems.append(f"{unit.name_zh}（{uid}）不是我方隊友")
            continue
        if uid == hero_id:
            problems.append(f"主角 {unit.name_zh} 由玩家操控，不能下戰術指令")
            continue
        if unit.is_summon:  # Phase 3D-4a：召喚物只聽全隊指令
            problems.append(f"召喚物 {unit.name_zh} 由 AI 控制，不能下個別戰術指令")
            continue
        problems.extend(
            reason
            for order in orders.unit_orders[uid]
            if (reason := validate_order(state, Team.ALLY, order)) is not None
        )
    return problems


def playable_maps(
    library: ContentLibrary, *, include_training: bool = False, include_boss: bool = False
) -> list[str]:
    """可以在網頁上開戰的地圖：有預設遭遇（``encounter``）的地圖，依 ID 排序。技能工坊的靶場（地圖
    類型 ``training``，Phase 3F-1）只有 ``include_training`` 時才列入、Boss 地圖（``boss``，
    Phase 3-5b）只有 ``include_boss`` 時才列入（一般地圖列表都不列）。"""
    return sorted(
        m
        for m, d in library.maps.items()
        if d.encounter is not None
        and (include_boss or d.archetype != BOSS_ARCHETYPE)
        and (include_training or d.archetype != TRAINING_ARCHETYPE)
    )


def _new_battle_id() -> str:
    return secrets.token_urlsafe(12)


class SessionStore:
    """記憶體內的工作階段表。"""

    def __init__(
        self,
        library: ContentLibrary,
        *,
        max_auto_steps: int = DEFAULT_MAX_ACTIONS,
        new_id: Callable[[], str] = _new_battle_id,
    ) -> None:
        self.library = library
        self.max_auto_steps = max_auto_steps
        self._new_id = new_id
        self._sessions: dict[str, BattleSession] = {}
        self._lock = threading.Lock()

    def _setup(self, request: CreateBattleRequest) -> BattleSetup:
        # 工坊試玩（帶自訂技能）可以選 Boss 地圖；一般開戰不行（Phase 3-5c-2）
        maps = playable_maps(
            self.library, include_training=True, include_boss=bool(request.custom_skills)
        )
        if request.map_id not in maps:
            raise InvalidRequestError(f"未知的地圖：{request.map_id}（可用：{', '.join(maps)}）")
        fill = request.ally_builds is None
        builds = (request.hero_build, *(request.ally_builds or ()))
        try:
            library, allies = build_allies(self.library, builds, fill=fill)
        except UnknownBuildError as exc:
            raise InvalidRequestError(str(exc)) from exc
        enemies = self._enemies(request)
        setup = build_setup(library, request.map_id, allies, enemies, max_rounds=request.max_rounds)
        if not request.custom_skills and not request.replace_skills:
            return setup
        custom = custom_skill_defs(self.library, request.custom_skills)
        return equip_custom_skills(setup, custom, request.replace_skills)

    def _enemies(self, request: CreateBattleRequest) -> list[str]:
        """地圖的預設敵人；靶場改用 ``workshop.yaml`` 的對手（Phase 3F-1）。"""
        _default_allies, enemies = default_lineup(self.library, request.map_id)
        if self.library.map(request.map_id).archetype != TRAINING_ARCHETYPE:
            if request.opponents is not None:
                raise InvalidRequestError("只有靶場可以選對手（opponents）")
            return enemies
        rules = self.library.workshop
        chosen = rules.opponent(request.opponents)
        if chosen is None:
            known = "、".join(o.id for o in rules.opponents)
            raise InvalidRequestError(f"未知的對手：{request.opponents}（可用：{known}）")
        return list(chosen.enemies)

    def create(self, request: CreateBattleRequest) -> tuple[BattleSession, list[StepRecord]]:
        """建立戰鬥並推進到第一次輪到主角。工作階段在推進前就登記（推進失敗時仍保留）。"""
        setup = self._setup(request)
        with self._lock:
            battle_id = self._new_id()
            while battle_id in self._sessions:  # pragma: no cover - 機率極低
                battle_id = self._new_id()
        try:
            session = BattleSession(
                battle_id,
                self.library,
                setup,
                request.seed,
                max_auto_steps=self.max_auto_steps,
            )
        except BattleSetupError as exc:
            raise InvalidRequestError(str(exc)) from exc
        with session.lock:
            with self._lock:
                self._sessions[battle_id] = session
            return session, session.begin()

    def open(
        self,
        setup: BattleSetup,
        seed: int,
        restore: tuple[list[Step], list[OrderRecord]] | None = None,
    ) -> tuple[BattleSession, list[StepRecord]]:
        """以現成的設定開一場戰鬥並登記（roguelite 一輪的戰鬥，Phase 3-5a）。``restore`` 為存檔
        的 ``(步驟, 指令)`` 時重播到存檔當下、不推進（回傳空的紀錄）；否則與 :meth:`create` 相同，
        推進到第一次輪到主角。"""
        with self._lock:
            battle_id = self._new_id()
            while battle_id in self._sessions:  # pragma: no cover - 機率極低
                battle_id = self._new_id()
        session = BattleSession(
            battle_id, self.library, setup, seed, max_auto_steps=self.max_auto_steps
        )
        if restore is not None:  # 重播成功才登記
            session.restore(*restore)
        with session.lock:
            with self._lock:
                self._sessions[battle_id] = session
            return session, ([] if restore is not None else session.begin())

    def get(self, battle_id: str) -> BattleSession:
        with self._lock:
            session = self._sessions.get(battle_id)
        if session is None:
            raise BattleNotFoundError(f"找不到戰鬥 {battle_id}")
        return session

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
