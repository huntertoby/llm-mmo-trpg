"""效用 AI 本體 :class:`UtilityAI`：產生候選、評分、取最高分的動作。

自 :mod:`trpg.engine.ai.utility` 拆出（Phase R1c），內容未改。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.environment import (
    AiProfile,
    AiProfileTable,
    AiWeights,
    TrapAiRules,
)
from trpg.engine.actions import (
    Action,
    ActivateCharge,
    Aim,
    Attack,
    Defend,
    EndStance,
    EndTurn,
    InfuseSkill,
    Move,
    Reload,
    Run,
    Shove,
    Swap,
    Trip,
    UseSkill,
    Vault,
)
from trpg.engine.ai.basics import aim_bonus, guard_bonus, swap_score
from trpg.engine.ai.charge import charge_score
from trpg.engine.ai.infuse import ap_ratio, infuse_setups, infuse_value, survival
from trpg.engine.ai.objective import hold_guard_bonus
from trpg.engine.ai.parts import part_score, part_variants, picks_parts
from trpg.engine.ai.race import race_ai_action
from trpg.engine.ai.stance import stance_cancel, stance_entry_blocked
from trpg.engine.ai.summon import (
    auto_mode_action,
    filter_by_mode,
    mode_orders,
    summon_template,
)
from trpg.engine.ai.utility.moves import (
    ice_slip_cost,
    is_risky_move,
    reactive_enemies,
    virtual_move_score,
    worth_previewing,
)
from trpg.engine.ai.utility.position import (
    ActionScore,
    OrderContext,
    OrdersSource,
    _order_weights,
    _Scene,
    _scene,
    _taunter,
    _Walk,
    position_value,
    resolve_orders,
)
from trpg.engine.ai.utility.scoring import defend_score, run_score, score_action, vault_score
from trpg.engine.ai.utility.skill_estimate import skill_estimate
from trpg.engine.ai.variant import cast_form, variant_move_bonus
from trpg.engine.battle import legal_actions, legal_actions_with_areas
from trpg.engine.events import (
    DamageDealt,
)
from trpg.engine.infusion import preferred_infusion
from trpg.engine.skills.targeting import (
    SkillArea,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import UnitId


def _hits_unit(scored: ActionScore, uid: UnitId) -> bool:
    """動作的有害效果是否影響到單位 ``uid``（攻擊、推擊、絆倒的目標；技能的敵方命中目標，或
    預覽中受到傷害者）。"""
    action = scored.action
    if isinstance(action, Attack | Shove | Trip):
        return action.target_id == uid
    p = scored.preview
    if p is None or not isinstance(action, UseSkill):
        return False
    if any(t.unit_id == uid and not t.ally for t in p.targets):
        return True
    return any(
        isinstance(e, DamageDealt) and e.target_id == uid for e in (*p.min_events, *p.max_events)
    )


def _with_infusion(state: BattleState, unit: UnitState, action: Action) -> Action:
    """召喚技能補上 AI 挑的灌注關鍵字（Phase 3-33b）：依召喚物定位（近戰／遠程）取對照表偏好的；
    沒有可選的關鍵字時不變。"""
    if not isinstance(action, UseSkill) or action.infusion is not None:
        return action
    template = summon_template(cast_form(state, action))
    if template is None:
        return action
    picked = preferred_infusion(state, unit, template)
    return action if picked is None else action.model_copy(update={"infusion": picked})


class UtilityAI:
    """效用評分 AI（可當作 ``Policy`` 使用：``UtilityAI(profiles)(state) -> Action``）。

    行動者的行為模式取 ``UnitState.ai_profile``；``override`` 可強制所有單位使用同一模式
    （測試用）；``move_candidates`` 可覆寫 ``ai_profiles.yaml`` 的候選移動數。
    """

    def __init__(
        self,
        profiles: AiProfileTable,
        *,
        override: str | None = None,
        move_candidates: int | None = None,
        skill_candidates: int | None = None,
        orders: OrdersSource | None = None,
    ) -> None:
        self._profiles = profiles.by_id()
        self._bonuses = profiles.orders
        self._run = profiles.run
        self._basic = profiles.basic
        self._parts = profiles.parts
        self.orders: OrdersSource | None = orders
        """戰術指令的來源（Phase 2C-2）；``None`` 時完全不受指令影響。"""
        self._override = override
        self._move_candidates = (
            profiles.move_candidates if move_candidates is None else move_candidates
        )
        self._skill_limit = (
            profiles.skill_candidates if skill_candidates is None else skill_candidates
        )

    def profile_for(self, unit: UnitState) -> AiProfile:
        key = self._override or unit.ai_profile or "brute"
        return self._profiles.get(key, self._profiles["brute"])

    @property
    def move_candidates(self) -> int:
        return self._move_candidates

    @property
    def skill_candidates(self) -> int:
        """每種技能最多跑完整 ``preview`` 的選取數。"""
        return self._skill_limit

    def order_context(self, state: BattleState, unit: UnitState) -> OrderContext | None:
        """``unit`` 此刻適用的有效戰術指令；沒有指令來源或沒有有效指令時為 ``None``。"""
        if unit.is_summon:  # 召喚物只依自己的模式行動（Phase 3-33c），不受陣營指令影響
            modes = mode_orders(state, unit, self.profile_for(unit).summon)
            return resolve_orders(state, unit, modes, self._bonuses)
        if self.orders is None:
            return None
        return resolve_orders(state, unit, self.orders(state, unit.id), self._bonuses)

    def rank_all(self, state: BattleState) -> list[ActionScore]:
        """所有合法動作以完整 ``preview`` 計算的分數（依 ``legal_actions`` 的順序；不篩選，
        較慢，供測試與分析使用）。"""
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        profile = self.profile_for(unit)
        ctx = self.order_context(state, unit)
        walk = _scene(state, unit, ctx).walk
        before = position_value(state, unit.id, profile.weights, ctx, walk=walk)
        return [
            self._score_other(state, a, profile, before, ctx, walk) for a in legal_actions(state)
        ]

    def rank(self, state: BattleState) -> list[ActionScore]:
        """候選動作的分數（依 ``legal_actions`` 的順序）。

        攻擊單位、推擊、絆倒、互動以完整 ``preview`` 評分；攻擊物件先經
        :func:`worth_previewing` 篩選；防禦直接計算（:func:`defend_score`）；``Move`` 先以
        :func:`virtual_move_score` 排序，只保留前 ``move_candidates`` 個，其中有風險者
        （:func:`is_risky_move`）才跑完整 ``preview``，其餘直接使用虛擬分數（``preview`` 欄位為
        ``None``）。
        """
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        profile = self.profile_for(unit)
        ctx = self.order_context(state, unit)
        w = _order_weights(profile.weights, ctx)
        actions, areas = legal_actions_with_areas(state, expand_copy=True)
        # 召喚物模式的硬性限制（待命不移動、守護我不離開太遠、集火只打目標；其他單位不變）
        actions = filter_by_mode(state, unit, actions, profile.summon)
        if all(isinstance(a, EndStance | EndTurn) for a in actions):
            return []  # 只剩結束回合與取消姿態（AI 不取消姿態）：不需要評分
        scene = _scene(state, unit, ctx)
        walk = scene.walk
        before = position_value(state, unit.id, w, ctx, walk=walk)
        scored: dict[int, ActionScore] = {}
        estimates: list[tuple[Fraction, int]] = []
        bonus = self._basic.variant_position_bonus
        slip = self._basic.ice_slip_points
        for index, action in enumerate(actions):
            if isinstance(action, Move):
                dest = (action.path[-1].x, action.path[-1].y)
                virtual = virtual_move_score(state, unit, action, w, before, scene=scene)
                virtual -= ice_slip_cost(state, unit, action, w, slip, scene=scene)  # 6E-2
                estimates.append((virtual + variant_move_bonus(state, unit, dest, bonus), index))
            elif isinstance(action, Defend | Run | Swap | Vault | Reload):  # 不跑 preview：直接計算
                scored[index] = ActionScore(
                    action, self._cheap_score(state, unit, w, action, scene=scene), None
                )
            elif isinstance(action, Attack) and not worth_previewing(state, scene, action):
                continue
            elif isinstance(action, UseSkill | EndStance | Aim):
                continue  # 技能在下面依估計篩選後才評分；AI 不主動取消姿態；瞄準看其他攻擊的預覽
            else:
                scored[index] = self._score_other(state, action, profile, before, ctx, walk)
        for index in self._skill_candidates(
            state, unit, actions, areas, scene, w, before, profile.trap
        ):
            scored[index] = score_action(
                state, actions[index], profile, before=before, orders=ctx, walk=walk
            )
        self._score_aim(state, unit, actions, scored)
        estimates.sort(key=lambda item: (-item[0], item[1]))
        enemies = reactive_enemies(state, unit)
        for estimate, index in estimates[: self._move_candidates]:
            move = actions[index]
            assert isinstance(move, Move)
            if is_risky_move(state, unit, move, enemies):
                full = score_action(state, move, profile, before=before, orders=ctx, walk=walk)
                dest = (move.path[-1].x, move.path[-1].y)
                extra = Fraction(variant_move_bonus(state, unit, dest, bonus))  # 戰場變奏（3-25a）
                extra -= ice_slip_cost(state, unit, move, w, slip, scene=scene)  # 冰面（6E-2）
                scored[index] = ActionScore(move, full.score + extra, full.preview)
            else:
                scored[index] = ActionScore(move, estimate, None)
        ranked = [scored[i] for i in sorted(scored)]
        return self._with_parts(state, ranked, profile, before, ctx, walk)

    def _with_parts(  # noqa: PLR0917
        self,
        state: BattleState,
        ranked: list[ActionScore],
        profile: AiProfile,
        before: Fraction,
        orders: OrderContext | None,
        walk: _Walk | None,
    ) -> list[ActionScore]:
        """打部位的變體（PB-1b，R8）：已評分的普攻與單體技能候選之後，緊接著放每個能選的部位
        （依部位 ID）；分數 ＝ 變體自己的預覽分數 ＋ :func:`part_score`。變體在技能的
        ``skill_candidates`` 截斷之後才展開，不擠掉本體候選；排在本體後面，同分時本體優先。"""
        unit = state.active
        if unit is None or not picks_parts(state, unit):
            return ranked  # 沒有部位的戰鬥、敵方與召喚物：候選清單原樣不動
        out: list[ActionScore] = []
        for scored in ranked:
            out.append(scored)
            for variant in part_variants(state, scored.action):
                full = score_action(
                    state, variant, profile, before=before, orders=orders, walk=walk
                )
                p = full.preview
                assert p is not None
                bonus = part_score(state, variant, p.min_events, p.max_events, self._parts)
                out.append(ActionScore(variant, full.score + bonus, p))
        return out

    def _score_other(  # noqa: PLR0917
        self,
        state: BattleState,
        action: Action,
        profile: AiProfile,
        before: Fraction,
        orders: OrderContext | None,
        walk: _Walk | None,
    ) -> ActionScore:
        """其餘動作的完整預覽分數；裝備充能的啟動（3G-G3a）另乘低權重、加自我增益的估值。"""
        scored = score_action(state, action, profile, before=before, orders=orders, walk=walk)
        if not isinstance(action, ActivateCharge):
            return scored
        score = charge_score(state, action, scored.score, profile, self._basic)
        return ActionScore(action, score, scored.preview)

    def _score_aim(
        self,
        state: BattleState,
        unit: UnitState,
        actions: list[Action],
        scored: dict[int, ActionScore],
    ) -> None:
        """瞄準（Phase 3-21a）：依已評分的攻擊與技能的預覽計分（技能評分之後才算）。"""
        index = next((i for i, a in enumerate(actions) if isinstance(a, Aim)), None)
        if index is None:
            return
        attacks = [
            (s.score, s.preview)
            for s in scored.values()
            if isinstance(s.action, Attack | UseSkill) and s.preview is not None
        ]
        scored[index] = ActionScore(
            actions[index], aim_bonus(state, unit, attacks, self._basic), None
        )

    def _cheap_score(
        self,
        state: BattleState,
        unit: UnitState,
        w: AiWeights,
        action: Defend | Run | Swap | Vault | Reload,
        *,
        scene: _Scene,
    ) -> Fraction:
        """守護／跑步／換位／攀跳／裝填的分數（不跑 preview）；守護隊友 ＝ 守護自己 ＋ 加分。"""
        if isinstance(action, Reload):
            return Fraction(self._basic.reload_points)
        if isinstance(action, Vault):
            return vault_score(unit, (action.dest.x, action.dest.y), scene, self._basic)
        if isinstance(action, Run):
            return run_score(state, unit, self._run)
        if isinstance(action, Swap):
            return swap_score(state, unit, state.units[action.target_id], self._basic)
        points = defend_score(state, unit, w) + hold_guard_bonus(state, unit, w)
        if action.target_id is not None:
            points += guard_bonus(state, unit, state.units[action.target_id], self._basic)
        return points

    def _skill_candidates(  # noqa: PLR0917
        self,
        state: BattleState,
        unit: UnitState,
        actions: list[Action],
        areas: dict[int, SkillArea],
        scene: _Scene,
        w: AiWeights,
        before: Fraction,
        trap: TrapAiRules,
    ) -> list[int]:
        """每個技能依便宜的估計（:func:`skill_estimate`）只保留前 ``skill_candidates`` 個選取，
        回傳它們在 ``actions`` 的索引（遞增）。"""
        by_skill: dict[str, list[tuple[Fraction, int]]] = {}
        stance = self.profile_for(unit).stance
        for index, action in enumerate(actions):
            if not isinstance(action, UseSkill):
                continue
            if stance_entry_blocked(state, unit, state.ruleset.skill_def(action.skill_id), stance):
                continue  # 有代價的姿態：敵人還不在可達範圍內、或血量已低（BAL-13d）
            est = skill_estimate(
                state, unit, action, areas[id(action)], scene, w, before, trap=trap
            )
            if est is not None:
                by_skill.setdefault(action.skill_id, []).append((est, index))
        chosen: list[int] = []
        for options in by_skill.values():
            options.sort(key=lambda item: (-item[0], item[1]))
            chosen.extend(index for _, index in options[: self._skill_limit])
        return sorted(chosen)

    def __call__(self, state: BattleState) -> Action:
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        switch = auto_mode_action(state, unit, self.profile_for(unit).summon)
        if switch is not None:  # 我方施放者切換召喚物的模式（0 AP；Phase 3-33c）
            return switch
        racial = race_ai_action(state, unit)  # 種族技的使用條件（Phase 3R-2）
        if racial is not None:
            return racial
        cancel = stance_cancel(state, unit, self.profile_for(unit).stance)
        if cancel is not None and cancel in legal_actions(state):  # 有代價的姿態（BAL-13d）
            return cancel
        ranked = self.rank(state)
        taunter = _taunter(state, unit)
        if taunter is not None:
            # 被嘲諷：只要有分數 > 0、且有害效果影響到嘲諷者的動作，就只在這些動作與移動之間選
            # （移動的 approach 已改以嘲諷者計算）；否則照一般規則行動
            hostile = [s for s in ranked if s.score > 0 and _hits_unit(s, taunter.id)]
            if hostile:
                ranked = [s for s in ranked if isinstance(s.action, Move) or s in hostile]
        best: ActionScore | None = None
        for scored in ranked:
            if scored.score > 0 and (best is None or scored.score > best.score):
                best = scored
        if taunter is None:  # 灌注技能給召喚物（Phase 3-33d）：比其他動作都好時才灌注
            infuse = self._best_infusion(state, unit)
            if infuse is not None and infuse[0] > (Fraction(0) if best is None else best.score):
                return infuse[1]
        if best is None:
            return EndTurn(unit_id=unit.id)
        return _with_infusion(state, unit, best.action)

    def _best_infusion(
        self, state: BattleState, unit: UnitState
    ) -> tuple[Fraction, InfuseSkill] | None:
        """分數最高的灌注候選（:mod:`trpg.engine.ai.infuse`；同分取列舉順序在前的）。"""
        if not any(s.owner_id == unit.id and s.alive for s in state.units.values()):
            return None
        profile = self.profile_for(unit)
        rules = profile.summon
        best: tuple[Fraction, InfuseSkill] | None = None
        for setup in infuse_setups(state, unit, rules):
            try:
                scored = score_action(setup.sim, setup.pick, profile)
            except IllegalActionError:
                continue
            if scored.score <= 0:
                continue
            summon = state.units[setup.action.summon_id]
            ratio = ap_ratio(state, setup.action.skill_id)
            value = infuse_value(scored.score, survival(state, summon, rules), rules, ratio)
            if best is None or value > best[0]:
                best = (value, setup.action)
        return best
