"""隨機組合器的零件：脈絡、強度旋鈕、形狀、效果、條件與代價（``docs/phases/Phase2B計畫.md`` 5.1）。

組合器的流程是「骨架 → 核心原語 → 形狀 → 效果與參數 → 條件 → 代價 → 調整強度」，全部依資料表
（骨架、原語、形狀、狀態、表面、條件）生成，不寫死具體內容。這個模組負責前六步；最後一步（調整
強度）在 :mod:`trpg.skillgen.composer_tuning`。

做不出合格結構時拋出 :class:`Retry`，由 :mod:`trpg.skillgen.random_composer` 用同一個亂數串流重抽。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from typing import Any

from trpg.content.battle import StatusDef
from trpg.content.composer_rules import ComposerRules, DiceRules, DurationRules, LadderRange
from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import (
    LEGACY_REACTION_EVENTS,
    PrimitiveDef,
    SkillRarity,
    default_affects,
    rarity_rank,
)
from trpg.shared.rng import Rng
from trpg.shared.types import Element, Surface

__all__ = [
    "NON_INTERCEPT_EVENTS",
    "Ctx",
    "Knob",
    "Retry",
    "build_condition",
    "build_cost",
    "build_effects",
    "build_passive_cost",
    "build_passive_effects",
    "build_reaction_cost",
    "build_reaction_effects",
    "build_shape",
    "build_stance_effects",
    "choose_core",
    "dice_ladder",
]

# 抽選機率與範圍在 ``content/skill_composer.yaml``（``library.composer``）；這裡只留結構判斷。
_BIG_SHAPES = frozenset({"square3", "allies_in_radius"})
_ALLY_SHAPES = frozenset({"allies_in_radius", "square3"})


class Retry(Exception):
    """這次抽到的結構做不出合格的技能；重抽。"""


@dataclass
class Knob:
    """一個強度旋鈕：效果 ``index`` 的 ``field`` 依 ``values`` 由小到大調整。"""

    index: int
    field: str
    values: tuple[Any, ...]
    weight: int = 1
    pos: int = 0

    @property
    def value(self) -> Any:
        return self.values[self.pos]

    def can_up(self) -> bool:
        return self.pos < len(self.values) - 1


@dataclass
class Ctx:
    """一次嘗試的脈絡：已決定的參數與累積的狀態。"""

    library: ContentLibrary
    rng: Rng
    skeleton: SkeletonDef
    rarity: SkillRarity
    tier: int
    category: str
    ap_cost: int
    theme: Element
    shape: str = ""
    shape_params: dict[str, Any] = field(default_factory=dict)
    effects: list[dict[str, Any]] = field(default_factory=list)
    knobs: list[Knob] = field(default_factory=list)
    control_groups: list[str] = field(default_factory=list)
    min_cooldown: int = 0
    core_count: int = 0
    trap: dict[str, Any] | None = None
    """陷阱技能的 ``trap`` 欄位（Phase 2E-3；``build_effects`` 決定）。"""
    required_stacks: int = 0
    """消耗施放者層數的技能，``cost.stacks`` 要求的層數（0 ＝ 沒有需求）。"""

    @property
    def rules(self) -> ComposerRules:
        return self.library.composer

    @property
    def rank(self) -> int:
        return rarity_rank(self.rarity)

    def primitive(self, primitive_id: str) -> PrimitiveDef:
        return self.library.ruleset.primitives.by_id()[primitive_id]

    def chance(self, permille: int) -> bool:
        return self.rng.chance_permille(permille)

    def add(
        self, spec: dict[str, Any], knobs: tuple[tuple[str, tuple[Any, ...], int], ...]
    ) -> None:
        index = len(self.effects)
        self.effects.append(spec)
        for name, values, weight in knobs:
            self.knobs.append(Knob(index, name, values, weight))
            spec[name] = values[0]


# ---------------------------------------------------------------------------
# 旋鈕的階梯
# ---------------------------------------------------------------------------


@cache
def dice_ladder(rules: DiceRules) -> tuple[str, ...]:
    """骰子由弱到強：顆數 1–``max_count``、面數 ``sides``，依平均值排序。"""
    combos = sorted(
        (count * (sides + 1), sides, count)
        for count in range(1, rules.max_count + 1)
        for sides in rules.sides
    )
    return tuple(f"{count}d{sides}" for _, sides, count in combos)


@cache
def _multiplier_ladder(ranges: tuple[LadderRange, ...]) -> tuple[int, ...]:
    return tuple(v for r in ranges for v in range(r.start, r.stop, r.step))


# ---------------------------------------------------------------------------
# 核心原語與形狀
# ---------------------------------------------------------------------------


def _pick_distinct(rng: Rng, options: list[str], count: int) -> list[str]:
    return rng.shuffled(options)[:count]


def _core_count(ctx: Ctx, options: list[str]) -> int:
    limit = min(len(options), 2)
    if limit < 1:
        raise Retry
    if ctx.skeleton.id in ("control", "aura", "displace"):
        if ctx.skeleton.id == "displace":
            return 1 + ctx.chance(ctx.rules.structure.displace_second_core_permille)
        return ctx.rng.randint(1, limit)
    return 1


def choose_core(ctx: Ctx) -> list[str]:
    """核心原語（依 ``skeleton.core.primitives`` 與稀有度），含互斥（推與拉不並存）。"""
    options = [
        p
        for p in ctx.skeleton.core.primitives
        if rarity_rank(ctx.primitive(p).min_rarity) <= ctx.rank and _composable(ctx, p)
    ]
    beneficial = ctx.skeleton.core.beneficial_only
    options = [p for p in options if p != "apply_status" or _has_status(ctx, beneficial)]
    count = min(_core_count(ctx, options), len(options))
    picked = _pick_distinct(ctx.rng, sorted(options), count)
    if "push" in picked and "pull" in picked:
        picked.remove("pull")
    if "teleport" in picked:  # 傳送只能搭配 ground_tile，不與其他位移並存
        picked = ["teleport"]
    if ctx.skeleton.id == "combo":  # 連段：第二個核心是帶條件的追加傷害
        double = ctx.chance(ctx.rules.structure.combo_double_damage_permille)
        picked = ["damage", "damage"] if double else ["damage"]
    return picked


def _has_status(ctx: Ctx, beneficial: bool) -> bool:
    """這個稀有度有沒有可由技能施加的（有益或有害）狀態。"""
    return any(
        s.budget_points is not None
        and s.beneficial == beneficial
        and rarity_rank(s.min_rarity) <= ctx.rank
        and not s.stance
        for s in ctx.library.ruleset.statuses.statuses
    )


def build_shape(ctx: Ctx, core: list[str], only: tuple[str, ...] | None = None) -> None:
    """形狀（骨架允許、稀有度夠、核心原語接受；``only`` 再限縮），再依形狀的參數範圍隨機填值。"""
    shapes = ctx.library.ruleset.shapes.by_id()
    allowed = [
        s
        for s in ctx.skeleton.shapes
        if s not in _HAND_WRITTEN_SHAPES
        and (only is None or s in only)
        and rarity_rank(shapes[s].min_rarity) <= ctx.rank
        and all(_accepts(ctx.primitive(p), s) for p in core)
    ]
    if not allowed:
        raise Retry
    ctx.shape = ctx.rng.choice(sorted(allowed))
    ctx.shape_params = {}
    for name, spec in sorted(shapes[ctx.shape].params.items()):
        ctx.shape_params[name] = _shape_param(ctx, name, spec.min, spec.max, spec.allow_weapon)


def _accepts(primitive: PrimitiveDef, shape: str) -> bool:
    return primitive.allowed_shapes is None or shape in primitive.allowed_shapes


def _shape_param(ctx: Ctx, name: str, low: int, high: int, allow_weapon: bool) -> Any:
    rng = ctx.rng
    if allow_weapon and ctx.category == "weapon":
        return "weapon"
    if name == "range" and ctx.shape in ("cross", "square3"):
        zero = ctx.chance(ctx.rules.structure.cross_zero_range_permille)
        return 0 if zero else rng.randint(max(low, ctx.rules.structure.cross_min_range), high)
    if name == "range":
        return rng.randint(min(max(low, ctx.rules.structure.other_min_range), high), high)
    return rng.randint(low, high)


# ---------------------------------------------------------------------------
# 效果
# ---------------------------------------------------------------------------


def _beneficial_affects(ctx: Ctx) -> str:
    """有益效果的對象：範圍型光環是範圍內友方；光環骨架的 ``single`` 是被選中的友方（含自己，
    2D-1）；其他形狀（自身、控場的單體……）只作用在施放者身上。"""
    if ctx.shape in _ALLY_SHAPES or (ctx.shape == "single" and ctx.skeleton.id == "aura"):
        return "allies"
    return "self"


def _affects_enemies(ctx: Ctx, primitive_id: str, spec: dict[str, Any]) -> bool:
    primitive = ctx.primitive(primitive_id)
    affects = spec.get("affects") or default_affects(primitive)
    return affects in ("enemies", "all")


def _status_candidates(ctx: Ctx, beneficial: bool) -> list[StatusDef]:
    out: list[StatusDef] = []
    used = {e.get("status") for e in ctx.effects}
    for status in ctx.library.ruleset.statuses.statuses:
        if status.budget_points is None or status.beneficial != beneficial or status.id in used:
            continue
        if rarity_rank(status.min_rarity) > ctx.rank or status.stance:
            continue  # 姿態狀態只有姿態技能（build_stance_effects）會施加
        if status.control_group == "hard" and ctx.shape != "single":
            continue
        if status.control_group is not None and status.control_group in ctx.control_groups:
            continue
        out.append(status)
    return sorted(out, key=lambda s: s.id)


def _duration_values(
    default: int | None, group: str | None, rules: DurationRules
) -> tuple[int, ...]:
    if default is None:
        return ()
    if group == "hard":
        return (default,)
    extra = rules.movement_extra if group == "movement" else rules.other_extra
    return tuple(range(1, min(default + extra, rules.cap) + 1))


def _status_effect(ctx: Ctx, *, beneficial: bool) -> None:
    candidates = _status_candidates(ctx, beneficial)
    if not candidates:
        raise Retry
    if ctx.shape == "self" and not beneficial and ctx.skeleton.id != "passive":
        raise Retry  # 自身形狀不得有對敵方的效果（被動的 self 形狀是「作用在觸發對象」）
    status = ctx.rng.choice(candidates)
    spec: dict[str, Any] = {"type": "apply_status", "status": status.id}
    if beneficial:
        spec["affects"] = _beneficial_affects(ctx)
    if status.control_group is not None:
        ctx.control_groups.append(status.control_group)
    if status.control_group == "hard":
        ctx.min_cooldown = max(ctx.min_cooldown, ctx.rules.structure.stun_min_cooldown)
    values = _duration_values(status.duration, status.control_group, ctx.rules.duration)
    weight = ctx.rules.duration.status_weight
    ctx.add(spec, (("duration", values, weight),) if len(values) > 1 else ())
    if values:
        spec["duration"] = values[0]


def _surface_effect(ctx: Ctx, *, beneficial_only: bool) -> None:
    surfaces = [
        s
        for s in sorted(ctx.library.ruleset.surfaces.surfaces, key=lambda s: s.id.value)
        if s.budget_points is not None and (s.beneficial or not beneficial_only)
    ]
    if not surfaces:
        raise Retry
    surface = ctx.rng.choice(surfaces)
    spec: dict[str, Any] = {"type": "create_surface", "surface": surface.id.value}
    if beneficial_only:
        spec["affects"] = _beneficial_affects(ctx)
    if surface.duration is None:
        ctx.add(spec, ())
        return
    duration = ctx.rules.duration
    values = tuple(range(1, min(surface.duration + duration.surface_extra, duration.cap) + 1))
    ctx.add(spec, (("duration", values, duration.surface_weight),))


def _damage_effect(ctx: Ctx, weight: int) -> None:
    if ctx.category == "spell":
        spec: dict[str, Any] = {"type": "damage", "element": ctx.theme.value}
        ctx.add(spec, (("dice", dice_ladder(ctx.rules.dice), weight),))
        return
    spec = {"type": "damage"}
    if ctx.theme is not Element.PHYSICAL:
        spec["element"] = ctx.theme.value
    ctx.add(spec, (("multiplier_permille", _multiplier_ladder(ctx.rules.multipliers), weight),))


def _heal_effect(ctx: Ctx, weight: int, primitive_id: str = "heal") -> None:
    """治療與護盾（骰子強度旋鈕相同）。"""
    spec = {"type": primitive_id, "affects": "self" if ctx.shape == "self" else "allies"}
    ctx.add(spec, (("dice", dice_ladder(ctx.rules.dice), weight),))


def _cleanse_effect(ctx: Ctx) -> None:
    ctx.add({"type": "cleanse", "affects": "self" if ctx.shape == "self" else "allies"}, ())


def _fixed_effect(ctx: Ctx, primitive_id: str) -> None:
    spec: dict[str, Any] = {"type": primitive_id}
    if primitive_id == "create_obstacle":
        objects = sorted(
            o.id
            for o in ctx.library.ruleset.objects.objects
            if "blocks_move" in o.tags and "explosive" not in o.tags
        )
        if not objects:
            raise Retry
        spec["object"] = ctx.rng.choice(objects)
    elif primitive_id in ("raise_terrain", "lower_terrain"):
        spec["amount"] = 1
    ctx.add(spec, ())


def _make_effect(ctx: Ctx, primitive_id: str, *, core: bool, beneficial_only: bool) -> None:
    """加入一個效果（含旋鈕）；做不出來時拋出 :class:`Retry`。"""
    weight = ctx.rules.structure.knob_weight_core if core else ctx.rules.structure.knob_weight_other
    if primitive_id == "damage":
        _damage_effect(ctx, weight)
    elif primitive_id in ("heal", "shield"):
        _heal_effect(ctx, weight, primitive_id)
    elif primitive_id == "cleanse":
        _cleanse_effect(ctx)
    elif primitive_id in ("push", "pull"):
        distances = tuple(ctx.rules.structure.push_pull_distances)
        ctx.add({"type": primitive_id}, (("distance", distances, 1),))
    elif primitive_id == "apply_status":
        _status_effect(ctx, beneficial=beneficial_only or _wants_buff(ctx, core))
    elif primitive_id == "create_surface":
        _surface_effect(ctx, beneficial_only=beneficial_only)
    else:
        _fixed_effect(ctx, primitive_id)


def _wants_buff(ctx: Ctx, core: bool) -> bool:
    """控場骨架的核心狀態有四分之一是自我增益（自身形狀或敵方不在範圍內時一定是增益）。"""
    if not _has_status(ctx, True):
        return False
    if ctx.shape == "self" or "teleport" in [e["type"] for e in ctx.effects]:
        return True
    return (
        core
        and ctx.skeleton.id == "control"
        and ctx.chance(ctx.rules.structure.control_buff_permille)
    )


def _secondary_pool(ctx: Ctx) -> list[str]:
    rules = ctx.skeleton.secondary
    fallback = ctx.rules.structure.fallback_secondary
    pool = list(rules.primitives) if rules.primitives is not None else list(fallback)
    primitives = ctx.library.ruleset.primitives.by_id()
    kept: list[str] = []
    for name in sorted(pool):
        primitive = primitives[name]
        if rarity_rank(primitive.min_rarity) > ctx.rank or not _accepts(primitive, ctx.shape):
            continue
        if not _composable(ctx, name):
            continue
        if rules.harmful_only and not primitive.harmful:
            continue
        if name in ("add_stack", "consume_stack", "place_trap"):
            continue  # 層數與陷阱的結構效果由 _stack_effect、_trap_setup 加入
        if "enemies" in ctx.skeleton.forbid_affects and default_affects(primitive) == "enemies":
            continue
        if ctx.shape == "self" and default_affects(primitive) == "enemies":
            continue
        if _conflicts(ctx, name) or _share_capped_without_core_knob(ctx, name):
            continue
        kept.append(name)
    return kept


def _share_capped_without_core_knob(ctx: Ctx, name: str) -> bool:
    """附帶原語有占比上限（例如控場的傷害 ≤ 40%），但核心效果沒有任何旋鈕可以提高：
    強度只能靠這個附帶效果，必然超過上限。"""
    if name not in ctx.skeleton.secondary.max_share_permille:
        return False
    return not any(k.index < ctx.core_count for k in ctx.knobs)


def _conflicts(ctx: Ctx, name: str) -> bool:
    types = [e["type"] for e in ctx.effects]
    if name in types and name != "apply_status":  # 同一種效果不重複（兩個表面只有後者生效）
        return True
    if "teleport" in types and name in ("damage", "push", "pull", "knock_prone"):
        return True
    return (name == "pull" and "push" in types) or (name == "push" and "pull" in types)


def _secondary_count(ctx: Ctx) -> int:
    limit = ctx.library.budget.rarity[ctx.rarity].max_effects - len(ctx.effects)
    structural = 1 if ctx.skeleton.id in ("builder_finisher", "trap") else 0  # 層數／陷阱的結構效果
    most = min(ctx.skeleton.secondary.max_count - structural, limit)
    if most <= 0:
        return 0
    return ctx.rng.randint(1 if ctx.rank >= rarity_rank("epic") else 0, most)


def _trap_setup(ctx: Ctx) -> None:
    """陷阱技能：第一個效果是 ``place_trap``，並抽 ``trap`` 欄位（觸發方式、輪數、範圍）。"""
    rules = ctx.rules.trap
    delay = ctx.chance(rules.delay_permille)
    span = rules.delay_rounds if delay else rules.enter_rounds
    shapes = tuple(sorted(rules.shape_weights))
    roll = ctx.rng.randint(1, sum(rules.shape_weights.values()))
    shape = shapes[-1]
    for name in shapes:
        roll -= rules.shape_weights[name]
        if roll <= 0:
            shape = name
            break
    ctx.trap = {
        "trigger": "delay" if delay else "enter",
        "rounds": ctx.rng.randint(span.min, span.max),
        "shape": shape,
    }
    ctx.add({"type": "place_trap"}, ())


def _stack_effect(ctx: Ctx) -> None:
    """蓄力與終結：一個 ``add_stack``（累積）或 ``consume_stack``（消耗），層數 ID 依資料表抽。"""
    rules = ctx.rules.builder
    stacks = sorted(ctx.library.ruleset.stacks.stacks, key=lambda s: s.id)
    if not stacks:
        raise Retry
    stack = ctx.rng.choice(stacks)
    affects = "self" if stack.owner == "self" else "enemies"
    if ctx.chance(rules.builder_permille):
        amounts = tuple(range(1, min(stack.max, rules.max_amount) + 1))
        spec: dict[str, Any] = {"type": "add_stack", "stack": stack.id, "affects": affects}
        ctx.add(spec, (("amount", amounts, ctx.rules.structure.knob_weight_other),))
        return
    ladder = tuple(range(rules.per_stack.start, rules.per_stack.stop, rules.per_stack.step))
    spec = {"type": "consume_stack", "stack": stack.id, "affects": affects}
    ctx.add(spec, (("per_stack_permille", ladder, ctx.rules.structure.knob_weight_other),))
    if stack.owner == "self" and ctx.chance(rules.required_permille):
        ctx.required_stacks = ctx.rng.randint(1, min(stack.max, rules.max_required_stacks))


def build_effects(ctx: Ctx, core: list[str]) -> None:
    """核心效果，再加 0 到 ``max_count`` 個附帶效果。"""
    beneficial = ctx.skeleton.core.beneficial_only
    if ctx.skeleton.id == "trap":
        _trap_setup(ctx)
    ctx.core_count = len(ctx.effects) + len(core)
    for name in core:
        _make_effect(ctx, name, core=True, beneficial_only=beneficial)
    if ctx.skeleton.id == "builder_finisher":
        _stack_effect(ctx)
    if ctx.skeleton.id == "aura" or ctx.skeleton.core.beneficial_only:
        return
    for _ in range(_secondary_count(ctx)):
        pool = _secondary_pool(ctx)
        if not pool:
            break
        _make_effect(ctx, ctx.rng.choice(pool), core=False, beneficial_only=False)
    _dash_first(ctx)


def _dash_first(ctx: Ctx) -> None:
    """衝鋒（``dash``，Phase 3D-2）一律最先結算，必須是技能的第一個效果：把它移到最前面，旋鈕
    與核心數量的索引跟著位移。"""
    types = [e["type"] for e in ctx.effects]
    if "dash" not in types or types[0] == "dash":
        return
    at = types.index("dash")
    ctx.effects.insert(0, ctx.effects.pop(at))
    for knob in ctx.knobs:
        if knob.index < at:
            knob.index += 1
        elif knob.index == at:
            knob.index = 0


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


def _condition_spec(ctx: Ctx, kind: str) -> dict[str, Any]:
    rng = ctx.rng
    rules = ctx.rules.condition
    if kind == "target_hp_below":
        low, high = rules.target_hp_below.min, rules.target_hp_below.max
        return {"type": kind, "permille": rng.randint(low, high)}
    if kind == "self_hp_below":
        low, high = rules.self_hp_below.min, rules.self_hp_below.max
        return {"type": kind, "permille": rng.randint(low, high)}
    if kind == "target_on_surface":
        names = sorted(s.value for s in Surface if s is not Surface.NONE)
        return {"type": kind, "surface": rng.choice(names)}
    if kind == "target_has_status":
        names = sorted(s.id for s in ctx.library.ruleset.statuses.statuses if not s.beneficial)
        return {"type": kind, "status": rng.choice(names)}
    return {"type": kind}


def _enemy_effects(ctx: Ctx) -> list[int]:
    return [i for i, e in enumerate(ctx.effects) if _affects_enemies(ctx, str(e["type"]), e)]


def _condition_kinds(ctx: Ctx, enemy_effects: list[int]) -> list[str]:
    """這個技能能用的條件：目標型條件需要「影響範圍內有別的單位」。"""
    available = {
        c.id
        for c in ctx.library.ruleset.conditions.conditions
        if rarity_rank(c.min_rarity) <= ctx.rank
    }
    if ctx.skeleton.id == "aura":
        kinds = ["self_hp_below"] + (["target_hp_below"] if ctx.shape != "self" else [])
    elif ctx.shape == "self" or not enemy_effects:
        kinds = ["self_hp_below"]
    else:
        kinds = ["self_hp_below", *ctx.rules.condition.target_conditions]
    return [k for k in kinds if k in available]


def _rolls_condition(ctx: Ctx) -> bool:
    return ctx.rank >= rarity_rank("rare") and ctx.chance(ctx.rules.condition.skill_permille)


def build_condition(ctx: Ctx) -> dict[str, Any] | None:
    """技能層級的條件（``None`` 表示沒有）；效果層級的條件直接寫進對應的效果。

    稀有（含）以上 30% 機率有條件；骨架要求條件（連段）時一定有。
    """
    required = ctx.skeleton.requires_condition
    if ctx.skeleton.id in ("builder_finisher", "trap"):
        return None  # 蓄力／終結與陷阱不帶技能條件（陷阱觸發時沒有施放時的選取）
    if not required and not _rolls_condition(ctx):
        return None
    enemy = _enemy_effects(ctx)
    kinds = _condition_kinds(ctx, enemy)
    if not kinds:
        if required:
            raise Retry
        return None
    spec = _condition_spec(ctx, ctx.rng.choice(kinds))
    damages = [i for i, e in enumerate(ctx.effects) if e["type"] == "damage"]
    effect_level = ctx.skeleton.id == "combo" and len(damages) > 1
    if effect_level or (not required and ctx.chance(ctx.rules.condition.effect_level_permille)):
        index = damages[1] if effect_level else ctx.rng.choice(enemy or [0])
        ctx.effects[index]["condition"] = spec
        return None
    return spec


# ---------------------------------------------------------------------------
# 代價
# ---------------------------------------------------------------------------


def _needs_cooldown(ctx: Ctx) -> bool:
    params = ctx.shape_params
    return (
        ctx.shape in _BIG_SHAPES
        or (ctx.shape == "ring" and params.get("radius") == ctx.rules.structure.big_ring_radius)
        or (ctx.shape == "cone" and params.get("size") == ctx.rules.structure.big_cone_size)
    )


def build_cost(ctx: Ctx) -> dict[str, Any]:
    """AP 之外的代價：法力、冷卻、每場次數。"""
    rng = ctx.rng
    rules = ctx.rules.cost
    ap = ctx.ap_cost
    if ctx.category == "spell":
        mana_range = rules.spell_mana_per_ap
        mana = rng.randint(mana_range.min, mana_range.max) * ap + (ctx.tier - 1) * (
            rules.spell_mana_per_tier
        )
    else:
        mana_range = rules.weapon_mana_per_ap
        mana = (
            0
            if ctx.chance(rules.weapon_free_permille)
            else rng.randint(mana_range.min, mana_range.max) * ap
        )
    cost: dict[str, Any] = {"mana": mana}
    cooldown: int | None = None
    if not (ap <= rules.no_cooldown_max_ap and ctx.chance(rules.no_cooldown_permille)):
        cooldown = min(rng.randint(1, rules.cooldown_base_max + ap), rules.cooldown_cap)
    floor = max(ctx.min_cooldown, 1 if _needs_cooldown(ctx) else 0)
    if floor:
        cooldown = min(max(cooldown or 0, floor), rules.cooldown_cap)
    if cooldown is not None:
        cost["cooldown"] = cooldown
    if ctx.chance(rules.uses_per_battle_permille):
        cost["uses_per_battle"] = rng.randint(rules.uses_per_battle.min, rules.uses_per_battle.max)
    if ctx.required_stacks:
        cost["stacks"] = ctx.required_stacks
    self_status = _self_status_cost(ctx)
    if self_status is not None:
        cost["self_status"] = self_status
    return cost


def _self_status_cost(ctx: Ctx) -> dict[str, Any] | None:
    """自身狀態代價（Phase 2H-1）：小機率從允許清單抽一個稀有度夠的狀態。"""
    rules = ctx.rules.cost
    if not ctx.chance(rules.self_status_permille):
        return None
    statuses = ctx.library.ruleset.statuses.by_id()
    options = sorted(
        status_id
        for status_id in ctx.library.budget.allowance.self_status.allowed
        if (status := statuses.get(status_id)) is not None
        and status.budget_points is not None
        and rarity_rank(status.min_rarity) <= ctx.rank
    )
    if not options:
        return None
    span = rules.self_status_duration
    return {
        "status": ctx.rng.choice(options),
        "duration": ctx.rng.randint(span.min, span.max),
    }


# ---------------------------------------------------------------------------
# 被動（Phase 2E-1）
# ---------------------------------------------------------------------------


_HAND_WRITTEN_PRIMITIVES = frozenset(
    {
        "hurl_object",
        "topple",
        "restore_resource",
        "steal_buff",
        "leap",
        "swap",
        "teleport_target",
        "swap_any",
        "charge_through",
        "summon",
        "zone",
        "rule_change",
        "gamble",
        "revive",
        "delayed_damage",
    }
)
"""只給手寫技能的結構型原語（Phase 3C-5a 的場景物件原語：需要地圖上有對應的物件；3D-2 的
``leap`` 與 ``swap``：落點與交換對象的條件要另外設計，隨機組合器只使用 ``dash``）。"""
_HAND_WRITTEN_SHAPES = frozenset({"object_then_tile", "unit_then_tile", "unit_pair"})
"""只給手寫技能的形狀（Phase 3C-5a：投擲物件專用；3D-2b：位移他人專用）。"""


def _composable(ctx: Ctx, name: str) -> bool:
    """組合器可以使用的原語：改寫規則型（Phase 3C-4a 的 ``grant_ap`` 等）與場景物件原語
    （3C-5a）只給手寫技能。"""
    return ctx.primitive(name).category != "rule_rewrite" and name not in _HAND_WRITTEN_PRIMITIVES


def _skeleton_allows(ctx: Ctx, name: str, *, core: bool) -> bool:
    """原語 ``name`` 是否在骨架資料允許的範圍：核心看 ``core.primitives``，
    附帶看 ``secondary.primitives``（``None`` 表示不限）。"""
    if core:
        return name in ctx.skeleton.core.primitives
    allowed = ctx.skeleton.secondary.primitives
    return allowed is None or name in allowed


def _usable_primitives(
    ctx: Ctx, names: tuple[str, ...], *, core: bool, beneficial: bool
) -> list[str]:
    """``names`` 中骨架允許、稀有度夠、（``apply_status``）有可用狀態的原語（依原順序）。"""
    return [
        name
        for name in names
        if _skeleton_allows(ctx, name, core=core)
        and _composable(ctx, name)
        and rarity_rank(ctx.primitive(name).min_rarity) <= ctx.rank
        and (name != "apply_status" or _has_status(ctx, beneficial))
    ]


def _passive_candidates(target: str) -> tuple[str, ...]:
    """被動可考慮的原語：作用在另一方（敵人）是傷害或有害狀態，作用在持有者是治療、護盾或增益。"""
    return ("damage", "apply_status") if target == "other" else ("heal", "shield", "apply_status")


def _passive_effect(ctx: Ctx, name: str, target: str, *, core: bool) -> None:
    weight = ctx.rules.structure.knob_weight_core if core else ctx.rules.structure.knob_weight_other
    if name == "damage":
        _damage_effect(ctx, weight)
    elif name in ("heal", "shield"):
        _heal_effect(ctx, weight, name)
    else:
        _status_effect(ctx, beneficial=target == "self")


def build_passive_effects(ctx: Ctx, target: str) -> None:
    """被動的效果：一個核心效果，再依機率多一個不同原語的附帶效果（骨架 ``max_count: 1``）。

    ``target``：``trigger.target``（``other`` 或 ``self``）；形狀固定為 ``self``。
    """
    names = _passive_candidates(target)
    beneficial = target == "self"
    options = _usable_primitives(ctx, names, core=True, beneficial=beneficial)
    if not options:
        raise Retry
    first = ctx.rng.choice(options)
    ctx.core_count = 1
    _passive_effect(ctx, first, target, core=True)
    rest = [
        name
        for name in _usable_primitives(ctx, names, core=False, beneficial=beneficial)
        if name != first
    ]
    if rest and ctx.chance(ctx.rules.passive.second_effect_permille):
        _passive_effect(ctx, ctx.rng.choice(rest), target, core=False)


def build_passive_cost(ctx: Ctx) -> dict[str, Any]:
    """被動的代價：法力（隨階級增加）與偶爾的冷卻。"""
    rules = ctx.rules.passive
    mana = ctx.rng.randint(rules.mana.min, rules.mana.max) + (ctx.tier - 1) * rules.mana_per_tier
    cost: dict[str, Any] = {"mana": mana}
    if ctx.chance(rules.cooldown_permille):
        cost["cooldown"] = ctx.rng.randint(rules.cooldown.min, rules.cooldown.max)
    return cost


# ---------------------------------------------------------------------------
# 反應技與姿態（Phase 2E-2）
# ---------------------------------------------------------------------------

NON_INTERCEPT_EVENTS = tuple(e for e in LEGACY_REACTION_EVENTS if e != "ally_hit_adjacent")
"""非擋攻擊的反應事件（``ally_hit_adjacent`` 另外抽）；只從 2E-2 的四個事件抽（3D-3 的新事件只給
手寫技能，既有種子的組合結果不變）。"""


def _shield_if_allowed(ctx: Ctx, *, core: bool) -> None:
    if (
        _skeleton_allows(ctx, "shield", core=core)
        and rarity_rank(ctx.primitive("shield").min_rarity) <= ctx.rank
    ):
        weight = (
            ctx.rules.structure.knob_weight_core if core else ctx.rules.structure.knob_weight_other
        )
        _heal_effect(ctx, weight, "shield")


def _intercept_effects(ctx: Ctx) -> None:
    """擋攻擊：形狀 self，``intercept`` ＋ 自身護盾（讓高階也有強度旋鈕）。"""
    if not _skeleton_allows(ctx, "intercept", core=True):
        raise Retry
    ctx.shape, ctx.shape_params = "self", {}
    ctx.core_count = 1
    ctx.add({"type": "intercept"}, ())
    _shield_if_allowed(ctx, core=False)


def build_reaction_effects(ctx: Ctx, event: str) -> None:
    """反應技的形狀與效果。

    擋攻擊：見 :func:`_intercept_effects`；其他事件：自身增益（形狀 self，只用骨架核心允許的原語）
    或對觸發者的傷害、有害狀態、推拉（形狀 single）。候選原語都由骨架資料篩選。
    """
    rules = ctx.rules.reaction
    if event == "ally_hit_adjacent":
        _intercept_effects(ctx)
        return
    if ctx.chance(rules.self_permille):
        # 沒有骨架允許的自身增益原語時，改走對觸發者的分支。
        own = _usable_primitives(
            ctx, ("heal", "shield", "apply_status"), core=True, beneficial=True
        )
        if own:
            build_shape(ctx, [], only=("self",))
            ctx.core_count = 1
            name = ctx.rng.choice(own)
            if name == "apply_status":
                _status_effect(ctx, beneficial=True)
            else:
                _heal_effect(ctx, ctx.rules.structure.knob_weight_core, name)
            return
    options = _usable_primitives(
        ctx, ("damage", "apply_status", "push", "pull"), core=True, beneficial=False
    )
    if not options:
        raise Retry
    name = ctx.rng.choice(options)
    build_shape(ctx, [name], only=("single",))
    ctx.core_count = 1
    _make_effect(ctx, name, core=True, beneficial_only=False)
    if ctx.chance(rules.second_effect_permille):
        pool = _secondary_pool(ctx)
        if pool:
            _make_effect(ctx, ctx.rng.choice(pool), core=False, beneficial_only=False)


def build_reaction_cost(ctx: Ctx) -> dict[str, Any]:
    """反應技的代價：法力（隨階級增加）與偶爾的冷卻（不花 AP）。"""
    rules = ctx.rules.reaction
    mana = ctx.rng.randint(rules.mana.min, rules.mana.max) + (ctx.tier - 1) * rules.mana_per_tier
    cost: dict[str, Any] = {"mana": mana}
    cooldown = (
        ctx.rng.randint(rules.cooldown.min, rules.cooldown.max)
        if ctx.chance(rules.cooldown_permille)
        else 0
    )
    cooldown = max(cooldown, ctx.min_cooldown)
    if cooldown:
        cost["cooldown"] = cooldown
    return cost


def build_stance_effects(ctx: Ctx) -> None:
    """姿態的效果：一個姿態狀態（對自己，不帶持續），階級 2 以上（或抽中）再加一個自身護盾。"""
    stances = sorted(
        (
            s
            for s in ctx.library.ruleset.statuses.statuses
            if s.stance and s.budget_points is not None and rarity_rank(s.min_rarity) <= ctx.rank
        ),
        key=lambda s: s.id,
    )
    if not stances:
        raise Retry
    ctx.shape, ctx.shape_params = "self", {}
    ctx.core_count = 1
    ctx.add({"type": "apply_status", "status": ctx.rng.choice(stances).id, "affects": "self"}, ())
    if ctx.tier > 1 or ctx.chance(ctx.rules.stance.shield_permille):
        _shield_if_allowed(ctx, core=False)
