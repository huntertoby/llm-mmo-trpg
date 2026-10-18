"""隨機組合器的零件：脈絡、強度旋鈕、形狀、效果、條件與代價（``docs/phases/Phase2B計畫.md`` 5.1）。

組合器的流程是「骨架 → 核心原語 → 形狀 → 效果與參數 → 條件 → 代價 → 調整強度」，全部依資料表
（骨架、原語、形狀、狀態、表面、條件）生成，不寫死具體內容。這個模組負責前六步；最後一步（調整
強度）在 :mod:`trpg.skillgen.composer_tuning`。

做不出合格結構時拋出 :class:`Retry`，由 :mod:`trpg.skillgen.random_composer` 用同一個亂數串流重抽。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trpg.content.battle import StatusDef
from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import PrimitiveDef, SkillRarity, default_affects, rarity_rank
from trpg.shared.rng import Rng
from trpg.shared.types import Element, Surface

__all__ = [
    "Ctx",
    "Knob",
    "Retry",
    "build_condition",
    "build_cost",
    "build_effects",
    "build_shape",
    "choose_core",
    "dice_ladder",
]

_BIG_SHAPES = frozenset({"square3", "allies_in_radius"})
_ALLY_SHAPES = frozenset({"allies_in_radius", "square3"})
_BIG_RING_RADIUS = 2
_BIG_CONE_SIZE = 4
_NO_COOLDOWN_MAX_AP = 2
_DICE_SIDES = (4, 6, 8, 10, 12)
_DICE_MAX_COUNT = 8
_DURATION_CAP = 6
_FALLBACK_SECONDARY = ("apply_status", "push", "pull", "knock_prone")
_TARGET_CONDITIONS = (
    "target_hp_below",
    "height_advantage",
    "target_on_surface",
    "target_has_status",
)


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


def dice_ladder() -> tuple[str, ...]:
    """骰子由弱到強：顆數 1–8、面數 {4, 6, 8, 10, 12}，依平均值排序。"""
    combos = sorted(
        (count * (sides + 1), sides, count)
        for count in range(1, _DICE_MAX_COUNT + 1)
        for sides in _DICE_SIDES
    )
    return tuple(f"{count}d{sides}" for _, sides, count in combos)


_DICE = dice_ladder()
_MULTIPLIERS = (*range(500, 3000, 100), *range(3000, 6000, 250), *range(6000, 10001, 500))


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
        return ctx.rng.randint(1, limit) if ctx.skeleton.id != "displace" else 1 + ctx.chance(250)
    return 1


def choose_core(ctx: Ctx) -> list[str]:
    """核心原語（依 ``skeleton.core.primitives`` 與稀有度），含互斥（推與拉不並存）。"""
    options = [
        p
        for p in ctx.skeleton.core.primitives
        if rarity_rank(ctx.primitive(p).min_rarity) <= ctx.rank
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
        picked = ["damage", "damage"] if ctx.chance(500) else ["damage"]
    return picked


def _has_status(ctx: Ctx, beneficial: bool) -> bool:
    """這個稀有度有沒有可由技能施加的（有益或有害）狀態。"""
    return any(
        s.budget_points is not None
        and s.beneficial == beneficial
        and rarity_rank(s.min_rarity) <= ctx.rank
        for s in ctx.library.ruleset.statuses.statuses
    )


def build_shape(ctx: Ctx, core: list[str]) -> None:
    """形狀（骨架允許、稀有度夠、核心原語接受），再依形狀的參數範圍隨機填值。"""
    shapes = ctx.library.ruleset.shapes.by_id()
    allowed = [
        s
        for s in ctx.skeleton.shapes
        if rarity_rank(shapes[s].min_rarity) <= ctx.rank
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
        return 0 if ctx.chance(150) else rng.randint(max(low, 2), high)
    if name == "range":
        return rng.randint(min(max(low, 3), high), high)
    return rng.randint(low, high)


# ---------------------------------------------------------------------------
# 效果
# ---------------------------------------------------------------------------


def _beneficial_affects(ctx: Ctx) -> str:
    return "allies" if ctx.shape in _ALLY_SHAPES else "self"


def _affects_enemies(ctx: Ctx, primitive_id: str, spec: dict[str, Any]) -> bool:
    primitive = ctx.primitive(primitive_id)
    affects = spec.get("affects") or default_affects(primitive)
    return affects in ("enemies", "all")


def _status_candidates(ctx: Ctx, beneficial: bool) -> list[StatusDef]:
    out: list[StatusDef] = []
    for status in ctx.library.ruleset.statuses.statuses:
        if status.budget_points is None or status.beneficial != beneficial:
            continue
        if rarity_rank(status.min_rarity) > ctx.rank:
            continue
        if status.id == "stun" and ctx.shape != "single":
            continue
        if status.control_group is not None and status.control_group in ctx.control_groups:
            continue
        out.append(status)
    return sorted(out, key=lambda s: s.id)


def _duration_values(default: int | None, group: str | None) -> tuple[int, ...]:
    if default is None:
        return ()
    if group == "hard":
        return (default,)
    extra = 1 if group == "movement" else 3
    return tuple(range(1, min(default + extra, _DURATION_CAP) + 1))


def _status_effect(ctx: Ctx, *, beneficial: bool) -> None:
    candidates = _status_candidates(ctx, beneficial)
    if not candidates:
        raise Retry
    if ctx.shape == "self" and not beneficial:
        raise Retry  # 自身形狀不得有對敵方的效果
    status = ctx.rng.choice(candidates)
    spec: dict[str, Any] = {"type": "apply_status", "status": status.id}
    if beneficial:
        spec["affects"] = _beneficial_affects(ctx)
    if status.control_group is not None:
        ctx.control_groups.append(status.control_group)
    if status.id == "stun":
        ctx.min_cooldown = max(ctx.min_cooldown, 4)
    values = _duration_values(status.duration, status.control_group)
    ctx.add(spec, (("duration", values, 2),) if len(values) > 1 else ())
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
    values = tuple(range(1, min(surface.duration + 3, _DURATION_CAP) + 1))
    ctx.add(spec, (("duration", values, 1),))


def _damage_effect(ctx: Ctx, weight: int) -> None:
    if ctx.category == "spell":
        spec: dict[str, Any] = {"type": "damage", "element": ctx.theme.value}
        ctx.add(spec, (("dice", _DICE, weight),))
        return
    spec = {"type": "damage"}
    if ctx.theme is not Element.PHYSICAL:
        spec["element"] = ctx.theme.value
    ctx.add(spec, (("multiplier_permille", _MULTIPLIERS, weight),))


def _heal_effect(ctx: Ctx, weight: int) -> None:
    spec = {"type": "heal", "affects": "self" if ctx.shape == "self" else "allies"}
    ctx.add(spec, (("dice", _DICE, weight),))


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
    weight = 6 if core else 1
    if primitive_id == "damage":
        _damage_effect(ctx, weight)
    elif primitive_id == "heal":
        _heal_effect(ctx, weight)
    elif primitive_id in ("push", "pull"):
        ctx.add({"type": primitive_id}, (("distance", (1, 2), 1),))
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
    return core and ctx.skeleton.id == "control" and ctx.chance(250)


def _secondary_pool(ctx: Ctx) -> list[str]:
    rules = ctx.skeleton.secondary
    pool = list(rules.primitives) if rules.primitives is not None else list(_FALLBACK_SECONDARY)
    primitives = ctx.library.ruleset.primitives.by_id()
    kept: list[str] = []
    for name in sorted(pool):
        primitive = primitives[name]
        if rarity_rank(primitive.min_rarity) > ctx.rank or not _accepts(primitive, ctx.shape):
            continue
        if rules.harmful_only and not primitive.harmful:
            continue
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
    if "teleport" in types and name in ("damage", "push", "pull", "knock_prone"):
        return True
    return (name == "pull" and "push" in types) or (name == "push" and "pull" in types)


def _secondary_count(ctx: Ctx) -> int:
    limit = ctx.library.budget.rarity[ctx.rarity].max_effects - len(ctx.effects)
    most = min(ctx.skeleton.secondary.max_count, limit)
    if most <= 0:
        return 0
    return ctx.rng.randint(1 if ctx.rank >= rarity_rank("epic") else 0, most)


def build_effects(ctx: Ctx, core: list[str]) -> None:
    """核心效果，再加 0 到 ``max_count`` 個附帶效果。"""
    beneficial = ctx.skeleton.core.beneficial_only
    ctx.core_count = len(core)
    for name in core:
        _make_effect(ctx, name, core=True, beneficial_only=beneficial)
    if ctx.skeleton.id == "aura" or ctx.skeleton.core.beneficial_only:
        return
    for _ in range(_secondary_count(ctx)):
        pool = _secondary_pool(ctx)
        if not pool:
            return
        _make_effect(ctx, ctx.rng.choice(pool), core=False, beneficial_only=False)


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


def _condition_spec(ctx: Ctx, kind: str) -> dict[str, Any]:
    rng = ctx.rng
    if kind == "target_hp_below":
        return {"type": kind, "permille": rng.randint(200, 600)}
    if kind == "self_hp_below":
        return {"type": kind, "permille": rng.randint(300, 700)}
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
        kinds = ["self_hp_below", *_TARGET_CONDITIONS]
    return [k for k in kinds if k in available]


def build_condition(ctx: Ctx) -> dict[str, Any] | None:
    """技能層級的條件（``None`` 表示沒有）；效果層級的條件直接寫進對應的效果。

    稀有（含）以上 30% 機率有條件；骨架要求條件（連段）時一定有。
    """
    required = ctx.skeleton.requires_condition
    if not required and not (ctx.rank >= rarity_rank("rare") and ctx.chance(300)):
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
    if effect_level or (not required and ctx.chance(500)):
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
        or (ctx.shape == "ring" and params.get("radius") == _BIG_RING_RADIUS)
        or (ctx.shape == "cone" and params.get("size") == _BIG_CONE_SIZE)
    )


def build_cost(ctx: Ctx) -> dict[str, Any]:
    """AP 之外的代價：法力、冷卻、每場次數。"""
    rng = ctx.rng
    ap = ctx.ap_cost
    if ctx.category == "spell":
        mana = rng.randint(2, 4) * ap + (ctx.tier - 1) * 2
    else:
        mana = 0 if ctx.chance(350) else rng.randint(1, 3) * ap
    cost: dict[str, Any] = {"mana": mana}
    cooldown: int | None = None
    if not (ap <= _NO_COOLDOWN_MAX_AP and ctx.chance(300)):
        cooldown = min(rng.randint(1, 2 + ap), 6)
    floor = max(ctx.min_cooldown, 1 if _needs_cooldown(ctx) else 0)
    if floor:
        cooldown = min(max(cooldown or 0, floor), 6)
    if cooldown is not None:
        cost["cooldown"] = cooldown
    if ctx.chance(120):
        cost["uses_per_battle"] = rng.randint(1, 2)
    return cost
