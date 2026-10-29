"""召喚技能的 AI（Phase 3D-4a，最簡單的近似；係數在 ``content/ai_profiles.yaml`` 的 ``summon:``）。

- **選位置**（:func:`summon_estimate`，不跑引擎）：召喚位置越靠近最近的敵人越好；沒有敵人時不納入
  候選。圖騰（3D-4b）相反：看光環範圍內有幾個友方。只決定「哪幾個位置值得完整預覽」。
- **評分**（:func:`summon_gains`，預覽收益的一部分）：新召喚物的預估每輪傷害
  （:func:`~trpg.content.summons.summon_dpr`）× 持續輪數 × ``damage`` 權重 × 命中折合
  （``hit_permille``），再扣掉召喚位置與最近敵人的距離 × ``distance_cost_permille``（讓完整評分
  也偏好靠近敵人的格子）；因超過上限而消失的舊召喚物，扣掉它剩餘輪數的同樣價值。圖騰的價值是
  光環範圍內的友方數 × 狀態價值 × 持續輪數 × ``support`` 權重 × 折合。
"""

from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from trpg.content.battle import SummonMode
from trpg.content.environment import AiProfile, SummonAiRules
from trpg.content.skills import SACRIFICE_SUMMON, SUMMON, SkillDef
from trpg.content.summons import summon_dpr
from trpg.engine.actions import (
    Action,
    Attack,
    Move,
    Run,
    SetSummonMode,
    Swap,
    Vault,
)
from trpg.engine.ai.orders import FocusTarget, HoldPosition, Protect, TacticalOrder
from trpg.engine.events import DamageDealt, EventBase, SummonExpired, UnitSummoned
from trpg.engine.ids import BOSS_TAG
from trpg.engine.rules.geometry import XY, manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summons.control import mode_problem
from trpg.engine.summons.core import growth_of, totem_of
from trpg.shared.types import Team, UnitId

__all__ = [
    "auto_mode_action",
    "blocker_gains",
    "blocking_summons",
    "effective_mode",
    "filter_by_mode",
    "has_summon",
    "mode_orders",
    "sacrifice_estimate",
    "summon_estimate",
    "summon_gains",
    "summon_template",
]

_ESTIMATE_BASE = 20
_PERMILLE = 1000


def has_summon(skill: SkillDef) -> bool:
    return any(e.type == SUMMON for e in skill.effects)


def summon_template(skill: SkillDef) -> str | None:
    """技能召喚的範本 ID（沒有召喚效果時 ``None``）。"""
    return next((e.unit for e in skill.effects if e.type == SUMMON), None)


def blocking_summons(state: BattleState, boss: UnitState, slack: int) -> frozenset[str]:
    """``boss`` 的敵方召喚物中「擋路」的 ID（Phase 3-33b）：召喚物 ``s`` 與某個敵方非召喚物單位
    ``h`` 滿足 ``距離(boss, s) + 距離(s, h) ≤ 距離(boss, h) + slack``（在 Boss 走向 ``h`` 的
    最短路徑附近）。"""
    foes = [u for u in state.living_units() if u.team is not boss.team]
    heroes = [u for u in foes if not u.is_summon]
    found: set[str] = set()
    for s in foes:
        if not s.is_summon:
            continue
        reach = manhattan(boss.xy, s.xy)
        if any(reach + manhattan(s.xy, h.xy) <= manhattan(boss.xy, h.xy) + slack for h in heroes):
            found.add(s.id)
    return frozenset(found)


def blocker_gains(
    state: BattleState,
    actor: UnitState,
    events: Sequence[EventBase],
    profile: AiProfile,
    hit: Fraction,
) -> Fraction:
    """Boss 優先清擋路的召喚物（Phase 3-33b）：預覽事件中受到傷害的擋路召喚物，每隻加
    ``boss_blocker_points`` × 命中折合（範圍技能順帶打到也算）。不是 Boss 或設定為 0 時 0。"""
    points = profile.summon.boss_blocker_points
    if points == 0 or not actor.has_tag(BOSS_TAG):
        return Fraction(0)
    blockers = blocking_summons(state, actor, profile.summon.boss_blocker_slack)
    hurt = {e.target_id for e in events if isinstance(e, DamageDealt) and e.target_id in blockers}
    return Fraction(points) * hit * len(hurt)


def sacrifice_estimate(
    state: BattleState, unit: UnitState, skill: SkillDef, target_xy: XY
) -> Fraction | None:
    """獻祭召喚物（Phase 3-24c）的便宜估計：被獻祭的召喚物所在位置、半徑內的敵人數 × 3（爆炸）或
    受傷的友方數 × 2（治療）；範圍內沒有值得的對象時 ``None``（不納入候選）。"""
    spec = next(e for e in skill.effects if e.type == SACRIFICE_SUMMON)
    radius = spec.radius or 0
    near = [u for u in state.living_units() if manhattan(u.xy, target_xy) <= radius]
    if spec.element is not None:
        score = 3 * sum(1 for u in near if u.team is not unit.team)
    else:
        score = 2 * sum(1 for u in near if u.team is unit.team and u.hp < u.max_hp)
    if score == 0:
        return None
    return Fraction(score) - Fraction(manhattan(unit.xy, target_xy), _PERMILLE)


def _nearest_enemy(state: BattleState, team: object, xy: XY) -> int | None:
    distances = [manhattan(xy, u.xy) for u in state.living_units() if u.team is not team]
    return min(distances) if distances else None


def _totem_allies(state: BattleState, team: object, template_id: str, xy: XY) -> int:
    """圖騰放在 ``xy`` 時，光環範圍內的友方數（不含圖騰；不計其他圖騰）。"""
    try:
        spec = state.ruleset.summon_def(template_id).template.totem
    except KeyError:
        return 0
    if spec is None:
        return 0
    return sum(
        1
        for u in state.living_units()
        if u.team is team and totem_of(state, u) is None and manhattan(u.xy, xy) <= spec.radius
    )


def summon_estimate(
    state: BattleState, unit: UnitState, xy: XY, template_id: str | None = None
) -> Fraction | None:
    """召喚位置 ``xy`` 的便宜估計：越靠近最近的敵人越高（同距離時離施放者近者優先）；沒有敵人時
    ``None``。圖騰（``template_id``）看光環範圍內的友方數，沒有友方時 ``None``。"""
    tie = Fraction(manhattan(unit.xy, xy), _PERMILLE)
    if template_id is not None and _is_totem(state, template_id):
        allies = _totem_allies(state, unit.team, template_id, xy)
        return Fraction(allies) - tie if allies else None
    nearest = _nearest_enemy(state, unit.team, xy)
    if nearest is None:
        return None
    return Fraction(_ESTIMATE_BASE - nearest) - tie


def _is_totem(state: BattleState, template_id: str) -> bool:
    try:
        return state.ruleset.summon_def(template_id).template.totem is not None
    except KeyError:
        return False


def _value(
    state: BattleState,
    template_id: str,
    rounds: int,
    *,
    xy: XY,
    team: object,
    profile: AiProfile,
    flat: int = 0,
    bonus_permille: int = 0,
    infused: bool = False,
) -> Fraction:
    """召喚物在 ``rounds`` 輪內的預估價值（等值傷害點數）。``flat``／``bonus_permille`` 是施放者
    成長（Phase 3-33c：普攻固定傷害、傷害加成）；``infused`` 為真時每輪另加 ``infusion_points``。"""
    try:
        summon = state.ruleset.summon_def(template_id)
    except KeyError:
        return Fraction(0)
    rules = profile.summon
    hit = Fraction(rules.hit_permille, _PERMILLE)
    rounds = max(rounds, 0)
    spec = summon.template.totem
    if spec is None:
        template = summon.template
        dpr = summon_dpr(summon, flat=flat, bonus_permille=bonus_permille)
        if infused:
            dpr += rules.infusion_points
        extra = Fraction(0)
        if template.inert:  # 不行動的召喚物（土牆）：擋路的價值
            extra += Fraction(rules.inert_round_points) * rounds
        if (
            template.detonate is not None
        ):  # 自爆（爆裂傀儡，3-33e2a）：爆炸算一次，一般攻擊只算 1 輪
            blast = template.detonate
            average = Fraction(blast.dice.count * (blast.dice.sides + 1), 2) + blast.flat
            extra += average * Fraction(rules.detonate_targets_permille, _PERMILLE)
            rounds = min(rounds, 1)
        return profile.weights.damage * (dpr * rounds + extra) * hit
    points = profile.ally_status_values.get(spec.status, rules.totem_ally_points)
    allies = _totem_allies(state, team, template_id, xy)
    return profile.weights.support * points * allies * min(rounds, 99) * hit


def summon_gains(
    state: BattleState, actor: UnitState, events: Sequence[EventBase], profile: AiProfile
) -> Fraction:
    """預覽事件中召喚與因上限消失的收益（``state`` 為動作前的狀態）。"""
    gains = Fraction(0)
    cost = Fraction(profile.summon.distance_cost_permille, _PERMILLE)
    for e in events:
        if isinstance(e, UnitSummoned) and e.team is actor.team:
            xy = (e.pos.x, e.pos.y)
            rounds = e.expires_round - state.round
            grown = growth_of(state, actor, e.skill_id)  # 成長與灌注（3-33c）
            gains += _value(
                state,
                e.template_id,
                rounds,
                xy=xy,
                team=actor.team,
                profile=profile,
                flat=grown.flat,
                bonus_permille=grown.bonus_permille,
                infused=e.infusion is not None,
            )
            nearest = _nearest_enemy(state, actor.team, xy)
            if nearest is not None and not _is_totem(state, e.template_id):
                gains -= cost * nearest
        elif isinstance(e, SummonExpired) and e.reason in ("limit", "sacrificed"):
            old = state.units.get(e.unit_id)
            if old is not None and old.team is actor.team and old.summon_expires_round is not None:
                rounds = old.summon_expires_round - state.round
                gains -= _value(
                    state,
                    old.template_id,
                    rounds,
                    xy=old.xy,
                    team=actor.team,
                    profile=profile,
                    bonus_permille=old.summon_bonus_permille,
                    infused=old.infusion is not None,
                )
    return gains


# ---------------------------------------------------------------------------
# 模式（Phase 3-33c，6.29.2）
# ---------------------------------------------------------------------------


def effective_mode(state: BattleState, unit: UnitState) -> SummonMode:
    """召喚物實際依循的模式：集火的目標已不在場上或不是敵人時當作跟隨（引擎也會在目標離場時
    把模式改回跟隨，這裡是保險）。"""
    if unit.summon_mode != "focus":
        return unit.summon_mode
    target = None if unit.summon_target_id is None else state.units.get(unit.summon_target_id)
    if target is None or not target.alive or target.team is unit.team:
        return "follow"
    return "focus"


def mode_orders(
    state: BattleState, unit: UnitState, rules: SummonAiRules
) -> tuple[TacticalOrder, ...]:
    """召喚物的模式轉成戰術指令（評分加成，沿用效用 AI 的指令機制）：集火＝集火目標；守護我＝保護
    召喚者＋待在 ``guard_radius`` 內；跟隨＝待在召喚者 ``follow_radius`` 內（軟性）；待命＝守在
    原地。召喚者不在場上（殘影分身）時沒有指令。"""
    mode = effective_mode(state, unit)
    owner = None if unit.owner_id is None else state.units.get(unit.owner_id)
    if mode == "hold":
        return (HoldPosition(at=unit.xy, radius=0),)
    if owner is None or not owner.alive:
        return ()
    if mode == "focus":
        assert unit.summon_target_id is not None
        return (FocusTarget(target=unit.summon_target_id),)
    if mode == "guard":
        return (Protect(ward=owner.id), HoldPosition(at=owner.xy, radius=rules.guard_radius))
    return (HoldPosition(at=owner.xy, radius=rules.follow_radius),)


def _dest(action: Move | Vault) -> XY:
    if isinstance(action, Move):
        return (action.path[-1].x, action.path[-1].y)
    return (action.dest.x, action.dest.y)


def filter_by_mode(
    state: BattleState, unit: UnitState, actions: list[Action], rules: SummonAiRules
) -> list[Action]:
    """依模式濾掉不符的合法動作（硬性規則；軟性的偏好見 :func:`mode_orders`）：

    - 待命：不移動（走路、跑步、攀跳、換位），只打相鄰的敵人；
    - 守護我：只走到召喚者 ``guard_radius`` 內（現在已在外面時只走更靠近的）；有威脅召喚者的敵人
      可打時，只打他們；
    - 集火：集火目標打得到時只打牠；打不到但有路可以靠近時也不打別人；
    - 跟隨：不限制。
    """
    if not unit.is_summon:
        return actions
    mode = effective_mode(state, unit)
    if mode == "hold":
        return _hold(state, unit, actions)
    if mode == "guard":
        return _guard(state, unit, actions, rules)
    if mode == "focus":
        return _focus(state, unit, actions)
    return actions


def _attack_xy(state: BattleState, action: Attack) -> XY | None:
    if action.target_id is not None:
        target = state.units.get(action.target_id)
        return None if target is None else target.xy
    obj = None if action.target_object_id is None else state.objects.get(action.target_object_id)
    return None if obj is None else obj.xy


def _hold(state: BattleState, unit: UnitState, actions: list[Action]) -> list[Action]:
    kept: list[Action] = []
    for action in actions:
        if isinstance(action, Move | Run | Vault | Swap):
            continue
        if isinstance(action, Attack):
            at = _attack_xy(state, action)
            if at is None or manhattan(unit.xy, at) != 1:
                continue
        kept.append(action)
    return kept


def _guard(
    state: BattleState, unit: UnitState, actions: list[Action], rules: SummonAiRules
) -> list[Action]:
    owner = None if unit.owner_id is None else state.units.get(unit.owner_id)
    if owner is None or not owner.alive:
        return actions
    radius = rules.guard_radius
    here = manhattan(unit.xy, owner.xy)
    kept: list[Action] = []
    for action in actions:
        if isinstance(action, Swap):
            continue
        if isinstance(action, Move | Vault):
            there = manhattan(_dest(action), owner.xy)
            if there > radius and there >= here:
                continue
        kept.append(action)
    return _threats_first(state, owner, kept, rules)


def _threats_first(
    state: BattleState, owner: UnitState, actions: list[Action], rules: SummonAiRules
) -> list[Action]:
    """可打到威脅召喚者的敵人時，只留下對他們的普攻（其他普攻刪掉）。"""

    def threatens(target_id: UnitId | None) -> bool:
        enemy = None if target_id is None else state.units.get(target_id)
        if enemy is None:
            return False
        reach = enemy.weapon.range + enemy.speed + rules.guard_threat_range
        return manhattan(enemy.xy, owner.xy) <= reach

    if not any(isinstance(a, Attack) and threatens(a.target_id) for a in actions):
        return actions
    return [a for a in actions if not isinstance(a, Attack) or threatens(a.target_id)]


def _focus(state: BattleState, unit: UnitState, actions: list[Action]) -> list[Action]:
    target_id = unit.summon_target_id
    target = None if target_id is None else state.units.get(target_id)
    if target is None:
        return actions
    if any(isinstance(a, Attack) and a.target_id == target.id for a in actions):
        return [a for a in actions if not isinstance(a, Attack) or a.target_id == target.id]
    here = manhattan(unit.xy, target.xy)
    closing = any(isinstance(a, Move) and manhattan(_dest(a), target.xy) < here for a in actions)
    if not closing:
        return actions
    return [a for a in actions if not isinstance(a, Attack) or a.target_id == target.id]


def auto_mode_action(
    state: BattleState, unit: UnitState, rules: SummonAiRules
) -> SetSummonMode | None:
    """我方 AI 的施放者切換召喚物模式（規則保守，權重在 ``ai_profiles.yaml`` 的 ``summon:``）：

    施放者 HP 低於 ``auto_guard_hp_permille`` ‰ 時全部改守護我；否則場上有 Boss 且
    ``auto_focus_boss`` 時全部改集火 Boss（最小單位 ID）；都不是時不動。一次只回傳一個動作
    （0 AP，結算後下一次再回傳下一個，全部符合後回傳 ``None``）。只對我方（``Team.ALLY``）的
    非召喚物單位。"""
    if unit.is_summon or unit.team is not Team.ALLY:
        return None
    summons = [
        s
        for s in state.units_sorted()
        if s.owner_id == unit.id and s.alive and totem_of(state, s) is None
    ]
    if not summons:
        return None
    low = rules.auto_guard_hp_permille > 0 and (
        unit.hp * 1000 < rules.auto_guard_hp_permille * unit.max_hp
    )
    boss = next(
        (
            e
            for e in state.units_sorted()
            if e.alive and e.team is not unit.team and e.has_tag(BOSS_TAG)
        ),
        None,
    )
    if low:
        want: tuple[SummonMode, UnitId | None] = ("guard", None)
    elif boss is not None and rules.auto_focus_boss:
        want = ("focus", boss.id)
    else:
        return None
    for s in summons:
        if (s.summon_mode, s.summon_target_id) == want:
            continue
        action = SetSummonMode(unit_id=unit.id, summon_id=s.id, mode=want[0], target_id=want[1])
        if mode_problem(state, unit, action) is None:
            return action
    return None
