"""效用評分 AI（``docs/專案計畫.md`` 5.9）：對每個合法動作跑 ``preview`` 評分，取最高分。

分數 ＝ 預覽收益 ＋ 命中率 × Σ 權重 × (動作後的位置價值 − 動作前的位置價值)，權重來自
``content/ai_profiles.yaml`` 的行為模式（莽夫、弓手、狡猾、守衛）。分數為正的動作中取最高者，
平手依 ``legal_actions`` 的順序；沒有正分的動作時結束回合。全部以 :class:`~fractions.Fraction`
計算，完全確定。

收益的估計：攻擊主要目標的傷害用預覽的精確期望值；其他傷害（爆炸、擴散……）取最少與最多後果
的平均再乘上命中率；「確定」的連鎖乘上命中率，「只是可能」的擊倒再除以 4。這些是啟發式，
供 Phase 2 以模擬調整。

掩護（Phase 1C）：位置價值的 ``cover`` 為「看得到、且從其位置看過來我受到半掩護」的敵人數；
收益的 ``expose`` 為動作讓幾名敵人離開掩護（被推離或掩護物被摧毀），``cover_damage`` 為對
「緊鄰敵人的掩護物」造成的每點傷害。

效能（Phase 1C 決定 #1）：每次決策只算一次「動作前」的位置價值；``Move`` 先以「直接把行動者放到
目的地」的位置價值（不跑引擎）排序，只保留前 ``move_candidates`` 個（``ai_profiles.yaml``）；
其中有風險的移動（可能被藉機攻擊、踩上有進入效果的表面、墜落、撤離、倒地站起）才跑完整
``preview``。沒有風險的移動結果是確定的（只有位置改變），其分數與完整預覽算出的分數相同。
``preview`` 本身在最少後果的模擬沒有經過分歧點時也只模擬一次。
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from trpg.content.environment import AiProfile, AiProfileTable, AiWeights
from trpg.engine.actions import Action, Attack, Defend, EndTurn, Move, UseSkill
from trpg.engine.battle import legal_actions
from trpg.engine.events import (
    DamageDealt,
    EventBase,
    ObjectDamaged,
    StatusApplied,
    UnitDowned,
    UnitMoved,
)
from trpg.engine.preview import Preview, preview
from trpg.engine.rules.combat import HALF_COVER, attack_problem, cover_object_between
from trpg.engine.rules.geometry import XY, chebyshev, has_line_of_sight, manhattan, neighbors4
from trpg.engine.skills.targeting import compute_area
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import ObjectId, Surface, Team, UnitId

__all__ = [
    "ActionScore",
    "UtilityAI",
    "defend_score",
    "is_risky_move",
    "position_value",
    "reactive_enemies",
    "score_action",
    "virtual_move_score",
    "worth_previewing",
]

_DEFEND_RADIUS = 6
_POSSIBLE_KILL_DIVISOR = 4
_DOWNED_PENALTY = 1000
_ESCAPED_BONUS = 1000
_ATTACK_CAUSES = ("attack",)
_PRONE = "prone"


@dataclass(frozen=True, slots=True)
class ActionScore:
    action: Action
    score: Fraction
    preview: Preview | None


def _enemies(state: BattleState, unit: UnitState) -> list[UnitState]:
    return [u for u in state.living_units() if u.team is not unit.team]


def _harmful(state: BattleState, xy: tuple[int, int]) -> bool:
    surface = state.tile(*xy).surface
    if surface is Surface.NONE:
        return False
    definition = state.ruleset.surface_def(surface)
    start = definition.on_turn_start
    enter = definition.on_enter
    if start is not None:
        if start.damage is not None and start.damage.only_tag is None:
            return True
        if start.apply_status is not None:
            return True
    return enter is not None and enter.apply_status is not None


def _objective_distance(state: BattleState, unit: UnitState) -> int:
    objective = state.objective
    if objective.kind == "eliminate" or not objective.tiles:
        return 0
    if objective.kind == "escape" and unit.team is not Team.ALLY:
        return 0
    return min(manhattan(unit.xy, t) for t in objective.tiles)


def _ward(state: BattleState, unit: UnitState) -> XY | None:
    """最需要保護的友方（HP 比例最低，同比例依 ID）的位置；沒有其他友方時為 ``None``。"""
    allies = [u for u in state.living_units() if u.team is unit.team and u.id != unit.id]
    if not allies:
        return None
    return min(allies, key=lambda u: (Fraction(u.hp, u.max_hp), u.id)).xy


def _protect_distance(state: BattleState, unit: UnitState) -> int:
    ward = _ward(state, unit)
    return 0 if ward is None else manhattan(unit.xy, ward)


def position_value(state: BattleState, unit_id: UnitId, w: AiWeights) -> Fraction:
    """行動者在 ``state`` 中所在位置的價值。"""
    return _unit_position_value(state, state.units[unit_id], w)


@dataclass(frozen=True, slots=True)
class _Scene:
    """同一次決策中不隨行動者位置改變的資料（虛擬移動評分時共用）。"""

    enemies: list[UnitState]
    ward: XY | None


def _scene(state: BattleState, unit: UnitState) -> _Scene:
    return _Scene(_enemies(state, unit), _ward(state, unit))


def _unit_position_value(
    state: BattleState, unit: UnitState, w: AiWeights, scene: _Scene | None = None
) -> Fraction:
    """``unit`` 的位置價值；``unit`` 可以是「放到別的格子」的虛擬複本（位置以 ``unit.xy`` 為準，
    其他單位以 ``state`` 為準）。``scene`` 為同一決策中共用的敵人清單與保護對象。"""
    if unit.escaped:
        return Fraction(_ESCAPED_BONUS * max(w.objective, 1))
    if unit.downed:
        return Fraction(-_DOWNED_PENALTY)
    if scene is None:
        scene = _scene(state, unit)
    xy = unit.xy
    enemies = scene.enemies
    value = 0
    if enemies:
        value -= w.approach * min(manhattan(xy, e.xy) for e in enemies)
        if w.threat:
            value += w.threat * sum(1 for e in enemies if attack_problem(state, unit, e) is None)
        value -= w.keep_distance * sum(1 for e in enemies if manhattan(xy, e.xy) <= 2)  # noqa: PLR2004
        if w.cover:
            value += w.cover * _covered_from(state, xy, enemies)
    value += w.height * state.tile(*xy).height
    if w.protect and scene.ward is not None:
        value -= w.protect * manhattan(xy, scene.ward)
    if w.objective:
        value -= w.objective * _objective_distance(state, unit)
    if _harmful(state, xy):
        value -= w.hazard
    return Fraction(value)


def _covered_from(state: BattleState, xy: XY, enemies: list[UnitState]) -> int:
    """看得到 ``xy``、且從其位置看過來 ``xy`` 受到半掩護的敵人數。"""
    return sum(
        1
        for e in enemies
        if cover_object_between(state, e.xy, xy) is not None and has_line_of_sight(state, e.xy, xy)
    )


def _in_cover(state: BattleState, unit: UnitState) -> bool:
    """``unit`` 四方向相鄰處有未摧毀的半掩護物件（「躲在掩護後」）。"""
    for nxt in neighbors4(state, unit.xy):
        oid = state.tile(*nxt).object_id
        if oid is not None and HALF_COVER in state.ruleset.object_def(state.objects[oid].kind).tags:
            return True
    return False


def _cover_objects_near_enemies(state: BattleState, actor: UnitState) -> set[ObjectId]:
    """緊鄰（四方向）敵人的半掩護物件。"""
    result: set[ObjectId] = set()
    for e in _enemies(state, actor):
        for nxt in neighbors4(state, e.xy):
            oid = state.tile(*nxt).object_id
            if (
                oid is not None
                and HALF_COVER in state.ruleset.object_def(state.objects[oid].kind).tags
            ):
                result.add(oid)
    return result


def _last_cause(events: tuple[EventBase, ...]) -> dict[UnitId, str]:
    cause: dict[UnitId, str] = {}
    for e in events:
        if isinstance(e, DamageDealt):
            cause[e.target_id] = e.cause
    return cause


def _gains(state: BattleState, actor: UnitState, p: Preview, w: AiWeights) -> Fraction:  # noqa: PLR0912, PLR0915
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    team = actor.team
    skill_primary: dict[UnitId, bool] = {}
    if isinstance(p.action, UseSkill):
        foes = [t for t in p.targets if not t.ally]
        if foes:
            hit = sum((t.hit_chance for t in foes), Fraction(0)) / len(foes)
        skill_primary = {t.unit_id: True for t in foes if t.damage is not None}

    def is_enemy(uid: UnitId) -> bool:
        return state.units[uid].team is not team if uid in state.units else False

    primary = None
    if isinstance(p.action, Attack) and p.action.target_id is not None and p.damage is not None:
        primary = p.action.target_id
    gains = Fraction(0)
    # 傷害：主要傷害用精確期望；其他取 min/max 平均 × 命中率
    other_enemy = Fraction(0)
    env_enemy = Fraction(0)
    friendly = Fraction(0)
    for events in (p.min_events, p.max_events):
        seen: set[UnitId] = set()
        for e in events:
            if not isinstance(e, DamageDealt) or e.cause == "deadly_terrain":
                continue  # 致命地形的「傷害」是擊倒本身，由 kill／env_kill 計分
            first = e.target_id not in seen
            if e.cause == "attack" and (
                (e.target_id == primary and first) or e.target_id in skill_primary
            ):
                seen.add(e.target_id)
                continue
            if is_enemy(e.target_id):
                other_enemy += e.amount
                if e.cause not in _ATTACK_CAUSES:
                    env_enemy += e.amount
            elif e.target_id in state.units:
                friendly += e.amount
    if p.damage is not None and primary is not None:
        gains += w.damage * p.damage.expected
    for t in p.targets:  # 技能：每個目標各自的命中率與期望傷害
        if t.damage is not None and not t.ally:
            gains += w.damage * t.damage.expected
    healed = sum(Fraction(lo + hi, 2) for uid, lo, hi in p.healed if uid in state.units)
    gains += w.heal * healed
    gains += w.damage * hit * other_enemy / 2
    gains += w.env_damage * hit * env_enemy / 2
    gains -= w.friendly_fire * friendly / 2
    # 擊倒
    certain_down = {e.unit_id for e in p.min_events if isinstance(e, UnitDowned)}
    possible_down = {e.unit_id for e in p.max_events if isinstance(e, UnitDowned)} - certain_down
    causes = _last_cause(p.max_events) | _last_cause(p.min_events)
    for uid, factor in [(u, hit) for u in sorted(certain_down)] + [
        (u, hit / _POSSIBLE_KILL_DIVISOR) for u in sorted(possible_down)
    ]:
        if is_enemy(uid):
            gains += w.kill * factor
            if causes.get(uid, "attack") not in _ATTACK_CAUSES:
                gains += w.env_kill * factor
        elif uid in state.units:
            gains -= w.kill * factor
    # 推擊、狀態、表面
    pushed = {
        e.unit_id
        for e in p.min_events
        if isinstance(e, UnitMoved) and e.mode == "forced" and is_enemy(e.unit_id)
    }
    gains += w.push * hit * len(pushed)
    statuses = {
        (e.target_id, e.status_id)
        for e in p.min_events
        if isinstance(e, StatusApplied) and is_enemy(e.target_id)
    }
    gains += w.status * hit * len(statuses)
    after = p.min_state
    before_harm = sum(1 for u in _enemies(state, actor) if _harmful(state, u.xy))
    after_harm = sum(
        1 for u in after.living_units() if u.team is not team and _harmful(after, u.xy)
    )
    gains += w.surface * hit * (after_harm - before_harm)
    if w.expose or w.cover_damage:
        gains += _cover_gains(state, actor, p, w, hit)
    if isinstance(p.action, Defend):
        near = sum(1 for e in _enemies(state, actor) if manhattan(actor.xy, e.xy) <= _DEFEND_RADIUS)
        gains += w.defend * near
    return gains


def _cover_gains(
    state: BattleState, actor: UnitState, p: Preview, w: AiWeights, hit: Fraction
) -> Fraction:
    """推離掩護（``expose``）與破壞敵人的掩護物（``cover_damage``）的收益。"""
    team = actor.team
    before = sum(1 for e in _enemies(state, actor) if _in_cover(state, e))
    exposed = Fraction(0)
    for after in (p.min_state, p.max_state):
        now = sum(1 for e in after.living_units() if e.team is not team and _in_cover(after, e))
        exposed += before - now
    gains = w.expose * hit * exposed / 2
    if w.cover_damage:
        shields = _cover_objects_near_enemies(state, actor)
        if shields:
            dealt = sum(
                e.amount
                for events in (p.min_events, p.max_events)
                for e in events
                if isinstance(e, ObjectDamaged) and e.object_id in shields
            )
            gains += w.cover_damage * hit * Fraction(dealt, 2)
    return gains


def score_action(
    state: BattleState,
    action: Action,
    profile: AiProfile,
    *,
    before: Fraction | None = None,
) -> ActionScore:
    """單一動作的分數（``EndTurn`` 固定為 0），以完整 ``preview`` 計算。

    ``before`` 為行動者在 ``state`` 的位置價值（省略時重新計算）。
    """
    if isinstance(action, EndTurn):
        return ActionScore(action, Fraction(0), None)
    w = profile.weights
    actor = state.units[action.unit_id]
    p = preview(state, action)
    if before is None:
        before = position_value(state, actor.id, w)
    after = position_value(p.min_state, actor.id, w)
    # 位置變化只在動作成功時發生（攻擊、技巧動作乘上命中率／成功率）
    hit = p.hit_chance if p.hit_chance is not None else Fraction(1)
    return ActionScore(action, _gains(state, actor, p, w) + hit * (after - before), p)


def defend_score(state: BattleState, unit: UnitState, w: AiWeights) -> Fraction:
    """防禦的分數：``defend`` × 6 格內的敵人數（防禦只替自己加上狀態，位置不變；與完整
    ``preview`` 的分數相同）。"""
    near = sum(1 for e in _enemies(state, unit) if manhattan(unit.xy, e.xy) <= _DEFEND_RADIUS)
    return Fraction(w.defend * near)


_ALWAYS_PREVIEW_TAGS = ("explosive", "conductive", "blocks_sight")
_OBJECT_NEAR_ENEMY = 2


def worth_previewing(state: BattleState, scene: _Scene, action: Attack) -> bool:
    """攻擊物件的便宜篩選：只有可能帶來收益的物件才跑完整 ``preview``。

    - 易爆（連鎖爆炸）、導電（雷電擴散）、阻擋視線（打掉後視線改變）的物件一律評估；
    - 其他物件只在 2 格（切比雪夫距離）內有敵人時評估（橋上的敵人、掩護後的敵人、點燃後
      波及的範圍）。

    被略過的物件攻擊不會傷到敵人、不會改變行動者的位置價值，分數不會是正的，因此不影響選擇。
    攻擊單位一律評估。
    """
    if action.target_object_id is None:
        return True
    obj = state.objects[action.target_object_id]
    tags = state.ruleset.object_def(obj.kind).tags
    if any(tag in tags for tag in _ALWAYS_PREVIEW_TAGS):
        return True
    return any(chebyshev(obj.xy, e.xy) <= _OBJECT_NEAR_ENEMY for e in scene.enemies)


SKILL_CANDIDATES = 3
"""每個技能最多評分（完整 ``preview``）的選取數。"""


def skill_estimate(  # noqa: PLR0917
    state: BattleState,
    unit: UnitState,
    action: UseSkill,
    scene: _Scene,
    w: AiWeights,
    before: Fraction,
) -> Fraction:
    """技能選取的便宜估計（不跑引擎），只用來篩出每個技能最值得完整評分的幾個選取。

    - 含 ``teleport``：把行動者放到目標格後的位置價值變化（同 :func:`virtual_move_score`）；
    - 其餘：影響範圍內的敵人數 × 3 − 友方數 × 3，有治療效果的再加上受傷友方每人 2；
      最後以與施放者的距離為平手判定（近者優先，保持確定）。
    """
    skill = state.ruleset.skill_def(action.skill_id)
    if any(e.type == "teleport" for e in skill.effects) and action.target_pos is not None:
        moved = unit.clone()
        moved.pos = action.target_pos
        return _unit_position_value(state, moved, w, scene) - before
    area = compute_area(state, unit, skill, action)
    score = Fraction(0)
    heals = any(e.type == "heal" for e in skill.effects)
    for uid in area.units:
        other = state.units[uid]
        if other.team is not unit.team:
            score += 3
        elif heals and other.hp < other.max_hp:
            score += 2
        else:
            score -= 3
    return score - Fraction(manhattan(unit.xy, area.origin), 1000)


def virtual_move_score(
    state: BattleState,
    unit: UnitState,
    move: Move,
    w: AiWeights,
    before: Fraction,
    *,
    scene: _Scene | None = None,
) -> Fraction:
    """不跑引擎的移動分數：把行動者直接放到目的地後的位置價值 − 動作前的位置價值。

    對沒有風險的移動（:func:`is_risky_move` 為假）而言，這就是完整 ``preview`` 的分數。
    """
    moved = unit.clone()
    moved.pos = move.path[-1]
    return _unit_position_value(state, moved, w, scene) - before


def reactive_enemies(state: BattleState, unit: UnitState) -> list[XY]:
    """可能對 ``unit`` 藉機攻擊的敵人位置：存活、本輪反應次數未用完、有「敵人離開相鄰格」的
    反應規則（不檢查耐力與武器，寧可多算）。"""
    limit = state.ruleset.core.reactions_per_round
    return [
        e.xy
        for e in _enemies(state, unit)
        if e.reactions_used < limit
        and any(rule.when.event == "enemy_leaves_adjacent" for rule in e.reactions)
    ]


def is_risky_move(
    state: BattleState, unit: UnitState, move: Move, enemies: list[XY] | None = None
) -> bool:
    """移動是否可能有「位置改變」以外的後果（需要完整 ``preview`` 才能評分）。

    - 倒地（先站起來）；
    - 路徑上離開某個「本輪還能反應、且有藉機攻擊規則」的敵人的相鄰格（可能被藉機攻擊）；
    - 走上有進入效果的表面（燃燒、冰面滑倒檢定）；
    - 往下的落差達到墜落門檻；
    - 撤離勝利條件下，我方走上出口格。
    """
    if unit.has_status(_PRONE):
        return True
    if enemies is None:
        enemies = reactive_enemies(state, unit)
    rules = state.ruleset
    min_drop = rules.core.fall_damage_min_drop
    objective = state.objective
    exits = objective.tiles if objective.kind == "escape" and unit.team is Team.ALLY else ()
    path = move.path
    last = len(path) - 1
    prev_height = state.tile(path[0].x, path[0].y).height
    for i, pos in enumerate(path):
        xy = (pos.x, pos.y)
        if i < last:
            nxt = (path[i + 1].x, path[i + 1].y)
            if any(manhattan(xy, e) == 1 and manhattan(nxt, e) != 1 for e in enemies):
                return True
        if i == 0:
            continue
        tile = state.tile(*xy)
        if tile.surface is not Surface.NONE and rules.surface_def(tile.surface).on_enter:
            return True
        if prev_height - tile.height >= min_drop:
            return True
        if xy in exits:
            return True
        prev_height = tile.height
    return False


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
    ) -> None:
        self._profiles = profiles.by_id()
        self._override = override
        self._move_candidates = (
            profiles.move_candidates if move_candidates is None else move_candidates
        )

    def profile_for(self, unit: UnitState) -> AiProfile:
        key = self._override or unit.ai_profile or "brute"
        return self._profiles.get(key, self._profiles["brute"])

    @property
    def move_candidates(self) -> int:
        return self._move_candidates

    def rank_all(self, state: BattleState) -> list[ActionScore]:
        """所有合法動作以完整 ``preview`` 計算的分數（依 ``legal_actions`` 的順序；不篩選，
        較慢，供測試與分析使用）。"""
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        profile = self.profile_for(unit)
        before = position_value(state, unit.id, profile.weights)
        return [score_action(state, a, profile, before=before) for a in legal_actions(state)]

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
        w = profile.weights
        actions = legal_actions(state)
        before = position_value(state, unit.id, w)
        scored: dict[int, ActionScore] = {}
        estimates: list[tuple[Fraction, int]] = []
        scene = _scene(state, unit)
        for index, action in enumerate(actions):
            if isinstance(action, Move):
                estimates.append(
                    (virtual_move_score(state, unit, action, w, before, scene=scene), index)
                )
            elif isinstance(action, Defend):
                scored[index] = ActionScore(action, defend_score(state, unit, w), None)
            elif isinstance(action, Attack) and not worth_previewing(state, scene, action):
                continue
            elif isinstance(action, UseSkill):
                continue  # 技能在下面依估計篩選後才評分
            else:
                scored[index] = score_action(state, action, profile, before=before)
        for index in self._skill_candidates(state, unit, actions, scene, w, before):
            scored[index] = score_action(state, actions[index], profile, before=before)
        estimates.sort(key=lambda item: (-item[0], item[1]))
        enemies = reactive_enemies(state, unit)
        for estimate, index in estimates[: self._move_candidates]:
            move = actions[index]
            assert isinstance(move, Move)
            if is_risky_move(state, unit, move, enemies):
                scored[index] = score_action(state, move, profile, before=before)
            else:
                scored[index] = ActionScore(move, estimate, None)
        return [scored[i] for i in sorted(scored)]

    def _skill_candidates(  # noqa: PLR0917
        self,
        state: BattleState,
        unit: UnitState,
        actions: list[Action],
        scene: _Scene,
        w: AiWeights,
        before: Fraction,
    ) -> list[int]:
        """每個技能依便宜的估計（:func:`skill_estimate`）只保留前 ``skill_candidates`` 個選取，
        回傳它們在 ``actions`` 的索引（遞增）。"""
        by_skill: dict[str, list[tuple[Fraction, int]]] = {}
        for index, action in enumerate(actions):
            if isinstance(action, UseSkill):
                est = skill_estimate(state, unit, action, scene, w, before)
                by_skill.setdefault(action.skill_id, []).append((est, index))
        chosen: list[int] = []
        for options in by_skill.values():
            options.sort(key=lambda item: (-item[0], item[1]))
            chosen.extend(index for _, index in options[:SKILL_CANDIDATES])
        return sorted(chosen)

    def __call__(self, state: BattleState) -> Action:
        unit = state.active
        if unit is None:
            raise ValueError("目前沒有行動中的單位")
        best: ActionScore | None = None
        for scored in self.rank(state):
            if scored.score > 0 and (best is None or scored.score > best.score):
                best = scored
        return best.action if best is not None else EndTurn(unit_id=unit.id)
