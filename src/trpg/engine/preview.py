"""預覽（dry run，``docs/專案計畫.md`` 5.9）：``preview(state, action) -> Preview``。

做法：用 **同一套引擎** 在狀態複本上模擬兩次（:func:`trpg.engine.battle.resolve_with` 的預覽模式）：

- ``min``（最少後果）：動作本身的判定視為成功但不暴擊；所有傷害骰取最小值；次要判定（藉機攻擊、
  冰面滑倒）對守方有利；``prompt`` 反應不使用。→「若命中且傷害為最小值時 **確定** 會發生的連鎖」。
- ``max``（最多後果）：動作本身暴擊；傷害骰取最大值；次要判定對守方不利；``prompt`` 反應使用。
  → 與 ``min`` 的差集為「可能發生的連鎖」。

命中率、暴擊率以 :class:`fractions.Fraction` 窮舉 d20（優劣勢時窮舉 400 組）精確計算；
期望傷害窮舉傷害骰的分布，以與結算相同的整數公式計算。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from trpg.content.skills import SkillDef
from trpg.engine.actions import Action, Attack, Shove, Trip, UseSkill
from trpg.engine.battle import _actor, simulate_preview
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    Healed,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectExploded,
    ObjectIgnited,
    ObjectMoved,
    ReactionTriggered,
    StatusApplied,
    SurfaceChanged,
    TerrainChanged,
    UnitDowned,
    UnitEscaped,
    UnitFell,
    UnitMoved,
)
from trpg.engine.rules.combat import (
    PERMILLE,
    PPM,
    Cover,
    advantage_state,
    half_cover,
    hit_modifier,
    is_hit,
    situational_modifier,
)
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.skills.targeting import (
    compute_area,
    damage_parameters,
    resolve_effects,
    skill_profile,
)
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Attribute, ObjectId, UnitId

__all__ = [
    "DamageRange",
    "Outcome",
    "Preview",
    "TargetPreview",
    "dice_distribution",
    "preview",
]

type XY = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Outcome:
    """連鎖結果的摘要（用於比較「確定」與「可能」）。

    ``kind``：``damaged``、``downed``、``moved``、``fell``、``deadly_terrain``、``escaped``、
    ``status``、``surface``、``terrain``、``object_damaged``、``object_destroyed``、
    ``object_exploded``、``object_ignited``、``object_moved``、``reaction``。
    """

    kind: str
    unit_id: UnitId | None = None
    object_id: ObjectId | None = None
    pos: XY | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class DamageRange:
    """對主要目標的傷害（``minimum``／``maximum`` 為命中時的範圍；``expected`` 已乘上命中率）。"""

    minimum: int
    maximum: int
    expected: Fraction
    expected_if_hit: Fraction


@dataclass(frozen=True, slots=True)
class TargetPreview:
    """技能對一個需要命中判定的單位的預覽（沒有傷害效果時 ``damage`` 為 ``None``）。"""

    unit_id: UnitId
    hit_chance: Fraction
    crit_chance: Fraction
    damage: DamageRange | None
    ally: bool = False
    knock_chance: Fraction | None = None
    """技能含 ``knock_prone`` 且會對這個單位生效時，擊倒的對抗成功率（命中之後；比照推擊、絆倒的
    :func:`_maneuver_chance`）；沒有擊倒效果時為 ``None``。"""


@dataclass(frozen=True, slots=True)
class Preview:
    action: Action
    hit_chance: Fraction | None
    """命中率（攻擊）或成功率（推擊、絆倒）；攻擊物件為 1；其他動作為 ``None``。
    攻擊單位時已包含高度、半掩護與優劣勢（隱蔽、倒地、天氣）。"""
    crit_chance: Fraction | None
    damage: DamageRange | None
    affected_tiles: tuple[XY, ...]
    affected_units: tuple[UnitId, ...]
    certain: tuple[Outcome, ...]
    possible: tuple[Outcome, ...]
    min_events: tuple[EventBase, ...]
    max_events: tuple[EventBase, ...]
    min_state: BattleState
    max_state: BattleState
    cover: Cover | None = None
    """攻擊單位時目標受到的半掩護（來源物件與懲罰）；沒有時為 ``None``。"""
    notes: tuple[str, ...] = ()
    """命中修正的說明（繁體中文），例如 ``("半掩護 −2：木箱 (3, 4)",)``。"""
    targets: tuple[TargetPreview, ...] = ()
    """技能：每個需要命中判定的單位（依單位 ID）的命中率、暴擊率與傷害範圍。"""
    healed: tuple[tuple[UnitId, int, int], ...] = ()
    """技能：治療 ``(單位, 最少, 最多)``（含所有治療效果的總和）。"""


# ---------------------------------------------------------------------------
# 機率
# ---------------------------------------------------------------------------


def _naturals(advantage: str) -> Counter[int]:
    """自然骰的分布（次數，總和 20 或 400）。"""
    if advantage == "none":
        return Counter(range(1, 21))
    pick = max if advantage == "advantage" else min
    return Counter(pick(a, b) for a, b in product(range(1, 21), repeat=2))


def _chances(
    naturals: Counter[int], bonus: int, target: int, crit_range: int
) -> tuple[Fraction, Fraction]:
    total = sum(naturals.values())
    hit = sum(n for nat, n in naturals.items() if is_hit(nat, nat + bonus, target))
    crit = sum(
        n for nat, n in naturals.items() if is_hit(nat, nat + bonus, target) and nat >= crit_range
    )
    return Fraction(hit, total), Fraction(crit, total)


def dice_distribution(count: int, sides: int) -> Counter[int]:
    """``count`` 顆 ``sides`` 面骰總和的分布（次數）。``count == 0`` 時為 ``{0: 1}``。"""
    dist: Counter[int] = Counter({0: 1})
    for _ in range(count):
        nxt: Counter[int] = Counter()
        for value, n in dist.items():
            for face in range(1, sides + 1):
                nxt[value + face] += n
        dist = nxt
    return dist


def _expected(dist: Counter[int], amount: dict[int, int]) -> Fraction:
    total = sum(dist.values())
    return Fraction(sum(amount[s] * n for s, n in dist.items()), total)


# ---------------------------------------------------------------------------
# 連鎖摘要
# ---------------------------------------------------------------------------


def _xy(pos: object) -> XY | None:
    x, y = getattr(pos, "x", None), getattr(pos, "y", None)
    return None if x is None or y is None else (x, y)


def _outcome(e: EventBase) -> Outcome | None:  # noqa: PLR0911, PLR0912
    if isinstance(e, DamageDealt):
        return Outcome("damaged", unit_id=e.target_id, detail=e.cause)
    if isinstance(e, UnitDowned):
        return Outcome("downed", unit_id=e.unit_id)
    if isinstance(e, UnitMoved) and e.mode != "walk":
        return Outcome("moved", unit_id=e.unit_id, pos=_xy(e.to_pos), detail=e.mode)
    if isinstance(e, UnitFell):
        return Outcome("fell", unit_id=e.unit_id)
    if isinstance(e, EnteredDeadlyTerrain):
        return Outcome("deadly_terrain", unit_id=e.unit_id, pos=_xy(e.pos))
    if isinstance(e, UnitEscaped):
        return Outcome("escaped", unit_id=e.unit_id)
    if isinstance(e, StatusApplied):
        return Outcome("status", unit_id=e.target_id, detail=e.status_id)
    if isinstance(e, SurfaceChanged):
        return Outcome("surface", pos=_xy(e.pos), detail=e.after.value)
    if isinstance(e, TerrainChanged):
        return Outcome("terrain", pos=_xy(e.pos), detail=f"{e.terrain_after}:{e.height_after}")
    if isinstance(e, ObjectDamaged):
        return Outcome("object_damaged", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectDestroyed):
        return Outcome("object_destroyed", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectExploded):
        return Outcome("object_exploded", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectIgnited):
        return Outcome("object_ignited", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectMoved):
        return Outcome("object_moved", object_id=e.object_id, pos=_xy(e.to_pos))
    if isinstance(e, ReactionTriggered):
        return Outcome("reaction", unit_id=e.unit_id, detail=e.reaction)
    return None


def outcomes(events: list[EventBase]) -> list[Outcome]:
    """事件 → 連鎖結果（去除重複，保留第一次出現的順序）。"""
    seen: dict[Outcome, None] = {}
    for e in events:
        o = _outcome(e)
        if o is not None:
            seen.setdefault(o, None)
    return list(seen)


def _affected(
    state: BattleState, events: list[EventBase]
) -> tuple[tuple[XY, ...], tuple[UnitId, ...]]:
    tiles: set[XY] = set()
    units: set[UnitId] = set()
    for o in outcomes(events):
        if o.pos is not None:
            tiles.add(o.pos)
        if o.unit_id is not None:
            units.add(o.unit_id)
            unit = state.units.get(o.unit_id)
            if unit is not None:
                tiles.add(unit.xy)
        if o.object_id is not None and o.object_id in state.objects:
            tiles.add(state.objects[o.object_id].xy)
    return tuple(sorted(tiles, key=lambda p: (p[1], p[0]))), tuple(sorted(units))


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def _primary_damage(events: list[EventBase], actor: UnitId, target: str) -> EventBase | None:
    for e in events:
        if isinstance(e, DamageDealt | ObjectDamaged) and e.cause == "attack":
            key = e.target_id if isinstance(e, DamageDealt) else e.object_id
            if e.source_id == actor and key == target:
                return e
    return None


def _amount_table(
    state: BattleState, unit: UnitState, sums: list[int], *, mod_ppm: int, weather: int, mult: int
) -> dict[int, int]:
    weapon = unit.weapon
    core = state.ruleset.core
    scaled = unit.attributes[weapon.scaling_attr] * core.basic_attack_attr_multiplier_permille
    table: dict[int, int] = {}
    for s in sums:
        raw = (s + weapon.flat) * PERMILLE + scaled
        table[s] = max(
            raw * mod_ppm * weather * mult // (PERMILLE * PPM * PERMILLE * PERMILLE),
            core.min_damage_on_hit,
        )
    return table


def _cover_notes(cover: Cover | None) -> tuple[str, ...]:
    if cover is None:
        return ()
    x, y = cover.pos
    return (f"半掩護 −{cover.penalty}：{cover.name_zh} ({x}, {y})",)


def _attack_numbers(
    state: BattleState,
    action: Attack,
    actor: UnitState,
    min_events: list[EventBase],
    max_events: list[EventBase],
) -> tuple[Fraction, Fraction, DamageRange | None]:
    core = state.ruleset.core
    weapon = actor.weapon
    if action.target_object_id is not None:
        hit, crit = Fraction(1), Fraction(0)
        crit_dist: Counter[int] = Counter()
        target_key: str = action.target_object_id
    else:
        assert action.target_id is not None
        target = state.units[action.target_id]
        cover = half_cover(state, actor, target)
        bonus = (
            hit_modifier(actor, target, state.ruleset)
            + core.proficiency
            + situational_modifier(state, actor, target)
            - (0 if cover is None else cover.penalty)
        )
        naturals = _naturals(advantage_state(state, actor, target))
        hit, crit = _chances(naturals, bonus, core.hit_target, weapon.crit_range)
        crit_dist = dice_distribution(weapon.dice.count * 2, weapon.dice.sides)
        target_key = action.target_id
    low = _primary_damage(min_events, actor.id, target_key)
    high = _primary_damage(max_events, actor.id, target_key)
    if low is None or high is None:
        return hit, crit, None
    normal_dist = dice_distribution(weapon.dice.count, weapon.dice.sides)
    if isinstance(low, DamageDealt):
        mod, weather, mult = low.element_mod_ppm, low.weather_permille, low.multiplier_permille
    else:
        mod, weather, mult = PPM, _object_weather(state, actor), PERMILLE
    sums = sorted(set(normal_dist) | set(crit_dist))
    table = _amount_table(state, actor, sums, mod_ppm=mod, weather=weather, mult=mult)
    e_normal = _expected(normal_dist, table)
    e_crit = _expected(crit_dist, table) if crit_dist else Fraction(0)
    expected_if_hit = Fraction(0) if hit == 0 else ((hit - crit) * e_normal + crit * e_crit) / hit
    damage = DamageRange(
        minimum=getattr(low, "amount", 0),
        maximum=getattr(high, "amount", 0),
        expected=expected_if_hit * hit,
        expected_if_hit=expected_if_hit,
    )
    return hit, crit, damage


def _object_weather(state: BattleState, actor: UnitState) -> int:
    weather = state.weather
    if weather is None:
        return PERMILLE
    return PERMILLE + weather.element_damage_permille.get(actor.weapon.element, 0)


def _maneuver_chance(state: BattleState, actor: UnitState, action: Shove | Trip) -> Fraction:
    target = state.units[action.target_id]
    attr = Attribute.STR if isinstance(action, Shove) else Attribute.DEX
    rules = state.ruleset
    modifier = rules.hit_table.modifier(actor.attributes[attr], max(1, target.attributes[attr]))
    hit, _ = _chances(
        _naturals("none"), modifier + rules.core.proficiency, rules.core.hit_target, 21
    )
    return hit


def _damage_expectation(  # noqa: PLR0917
    state: BattleState,
    actor: UnitState,
    action: UseSkill,
    target_id: UnitId,
    hit: Fraction,
    crit: Fraction,
    min_events: list[EventBase],
    max_events: list[EventBase],
) -> DamageRange | None:
    """技能對 ``target_id`` 的傷害範圍：最少／最多取自模擬事件，期望值依效果的骰子分布精確計算
    （事件與效果數量對不上時退回最少與最多的平均）。"""
    skill = state.ruleset.skill_def(action.skill_id)

    def direct(events: list[EventBase]) -> list[DamageDealt]:
        return [
            e
            for e in events
            if isinstance(e, DamageDealt)
            and e.cause == "attack"
            and e.source_id == actor.id
            and e.target_id == target_id
        ]

    low, high = direct(min_events), direct(max_events)
    if not low or not high:
        return None
    minimum, maximum = sum(e.amount for e in low), sum(e.amount for e in high)
    target = state.units[target_id]
    specs = [
        skill.effects[r.spec_index]
        for r in resolve_effects(state, skill)
        if r.type == "damage"
        and condition_met(
            state, actor, skill.effects[r.spec_index].condition, Subject(target, target.xy)
        )
    ]
    if hit == 0:
        return DamageRange(minimum, maximum, Fraction(0), Fraction(0))
    if len(specs) != len(low):
        mid = Fraction(minimum + maximum, 2)
        return DamageRange(minimum, maximum, mid * hit, mid)
    core = state.ruleset.core
    total = Fraction(0)
    for spec, event in zip(specs, low, strict=True):
        params = damage_parameters(state, actor, skill, spec)
        dice = params.dice
        count, sides = (0, 1) if dice is None else (dice.count, dice.sides)
        normal, doubled = dice_distribution(count, sides), dice_distribution(count * 2, sides)
        table: dict[int, int] = {}
        for value in sorted(set(normal) | set(doubled)):
            raw = (value + params.flat) * PERMILLE + params.scaled_permille
            table[value] = max(
                raw
                * event.element_mod_ppm
                * event.weather_permille
                * event.multiplier_permille
                // (PERMILLE * PPM * PERMILLE * PERMILLE),
                core.min_damage_on_hit,
            )
        total += ((hit - crit) * _expected(normal, table) + crit * _expected(doubled, table)) / hit
    return DamageRange(minimum, maximum, total * hit, total)


def _knock_chance(
    state: BattleState, actor: UnitState, skill: SkillDef, target: UnitState
) -> Fraction | None:
    """技能對 ``target`` 的擊倒對抗成功率（技能屬性對相同屬性）；不會擊倒時為 ``None``。"""
    enemy = target.team is not actor.team
    if not any(
        r.type == "knock_prone" and (r.affects == "all" or (enemy and r.affects == "enemies"))
        for r in resolve_effects(state, skill)
    ):
        return None
    attr = skill.scaling_attr
    rules = state.ruleset
    modifier = rules.hit_table.modifier(actor.attributes[attr], max(1, target.attributes[attr]))
    hit, _ = _chances(
        _naturals("none"), modifier + rules.core.proficiency, rules.core.hit_target, 21
    )
    return hit


def _skill_targets(
    state: BattleState,
    actor: UnitState,
    action: UseSkill,
    min_events: list[EventBase],
    max_events: list[EventBase],
) -> tuple[TargetPreview, ...]:
    skill = state.ruleset.skill_def(action.skill_id)
    profile = skill_profile(state, actor, skill)
    core = state.ruleset.core
    rolled = sorted(
        {e.target_id for e in max_events if isinstance(e, AttackRolled) and e.skill_id == skill.id}
    )
    result: list[TargetPreview] = []
    for uid in rolled:
        target = state.units[uid]
        cover = half_cover(state, actor, target, profile)
        bonus = (
            hit_modifier(actor, target, state.ruleset, profile)
            + core.proficiency
            + situational_modifier(state, actor, target)
            - (0 if cover is None else cover.penalty)
        )
        naturals = _naturals(advantage_state(state, actor, target, profile))
        hit, crit = _chances(naturals, bonus, core.hit_target, profile.crit_range)
        damage = _damage_expectation(state, actor, action, uid, hit, crit, min_events, max_events)
        knock = _knock_chance(state, actor, skill, target)
        result.append(
            TargetPreview(
                uid, hit, crit, damage, ally=target.team is actor.team, knock_chance=knock
            )
        )
    return tuple(result)


def _skill_heals(
    actor: UnitState, min_events: list[EventBase], max_events: list[EventBase]
) -> tuple[tuple[UnitId, int, int], ...]:
    def totals(events: list[EventBase]) -> dict[UnitId, int]:
        out: dict[UnitId, int] = {}
        for e in events:
            if isinstance(e, Healed) and e.source_id == actor.id:
                out[e.target_id] = out.get(e.target_id, 0) + e.amount
        return out

    low, high = totals(min_events), totals(max_events)
    return tuple((uid, low.get(uid, 0), high[uid]) for uid in sorted(high))


def preview(state: BattleState, action: Action) -> Preview:
    """預覽 ``action`` 的結果（不修改 ``state``、不消耗亂數）。

    不合法時拋出 ``IllegalActionError``。
    """
    actor = _actor(state, action)
    low, high = simulate_preview(state, action)
    min_events, max_events = list(low.events), list(high.events)
    hit: Fraction | None = None
    crit: Fraction | None = None
    damage: DamageRange | None = None
    cover: Cover | None = None
    if isinstance(action, Attack):
        hit, crit, damage = _attack_numbers(state, action, actor, min_events, max_events)
        if action.target_id is not None:
            cover = half_cover(state, actor, state.units[action.target_id])
    elif isinstance(action, Shove | Trip):
        hit, crit = _maneuver_chance(state, actor, action), Fraction(0)
    targets: tuple[TargetPreview, ...] = ()
    healed: tuple[tuple[UnitId, int, int], ...] = ()
    if isinstance(action, UseSkill):
        targets = _skill_targets(state, actor, action, min_events, max_events)
        healed = _skill_heals(actor, min_events, max_events)
    certain = outcomes(min_events)
    certain_set = set(certain)
    possible = [o for o in outcomes(max_events) if o not in certain_set]
    tiles, units = _affected(high.state, max_events)
    if isinstance(action, UseSkill):
        area = compute_area(state, actor, state.ruleset.skill_def(action.skill_id), action)
        tiles = tuple(sorted({*tiles, *area.tiles}, key=lambda p: (p[1], p[0])))
        units = tuple(sorted({*units, *area.units}))
    return Preview(
        action=action,
        hit_chance=hit,
        crit_chance=crit,
        damage=damage,
        affected_tiles=tiles,
        affected_units=units,
        certain=tuple(certain),
        possible=tuple(possible),
        min_events=tuple(min_events),
        max_events=tuple(max_events),
        min_state=low.state,
        max_state=high.state,
        cover=cover,
        notes=_cover_notes(cover),
        targets=targets,
        healed=healed,
    )
