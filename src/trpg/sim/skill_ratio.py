"""1 階武器技的「每 AP 傷害 ÷ 普攻每 AP」比值（BAL-21e 的量測核心；NW-2c 從
``scripts/t1_skill_ratio.py`` 搬來，腳本與數值工坊共用，``docs/phases/PhaseNW-2計畫.md`` 5.7）。

量法照開發 PM 的 #148 核對：主城靶場 ``training_range``、``range_trial`` 的推薦配點（開局自由點數
全照 ``recommended_allocation``）、打普通木樁 (6,4)；近戰站 (6,5)、遠程站 (6,7)；每把武器每個情境
跑 N 個種子取平均（含失手）。
比值＝（技能對木樁的傷害 ÷ 花掉的 AP）÷（普攻對木樁的傷害 ÷ 花掉的 AP）。

- 「直接」只算施放當下；「含持續」是施放後再過 :data:`DOT_ROUNDS` 輪（主角每輪直接結束回合）木樁的
  總損血（只在技能可能有後續傷害時另跑）。
- 條件類另跑「成立」：施放前直接把狀態改成條件成立；「不成立」是自然狀態（第 1 輪、背刺這兩種自然
  成立的，不成立另外做：等一輪、背後格放木樁擋住）。綁武器（``wielding_weapon``）不另跑，直接看那
  把武器的列。變奏（``variants``）每個另跑一次「成立」。

平行：:func:`ratio_task` 是頂層函式，內容庫用 :func:`trpg.sim.boss_probe.library_for` 依資料夾
快取；普攻的平均依（內容資料夾, 種子數, 武器, 配點）在每個行程內快取一次（確定性，只省時間）。

彙總（:func:`skill_summary`、:func:`odd_conditions`、:func:`low_tag`）與工坊的參考線
（:func:`reference_checks`，D4）也在這裡；腳本只留 CLI 與印表。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator, Sequence
from typing import Any, Final

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.engine.actions import Action, Attack, EndTurn, UseSkill
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle, legal_actions_with_areas
from trpg.engine.ids import CONCEALED
from trpg.engine.results import ResolveResult
from trpg.engine.rules.facing import back_xy
from trpg.engine.runner import advance, apply_step
from trpg.engine.setup import BattleSetup, UnitSpawn
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import BattleState, StatusInstance, UnitState
from trpg.engine.variants import variant_holds
from trpg.roguelite.start import apply_allocation, recommended_allocation, start_hero
from trpg.shared.types import Surface, Team
from trpg.sim.boss_probe import library_for
from trpg.world.opening import range_content

__all__ = [
    "CLASS_ORDER",
    "CLASS_ZH",
    "DOT_ROUNDS",
    "DUAL",
    "LOW_RATIO",
    "REFERENCE_LINES",
    "SINGLE_SHAPES",
    "RatioJob",
    "ReferenceLine",
    "bound_weapons",
    "class_rank",
    "conditions_of",
    "is_measurable",
    "lingers",
    "low_tag",
    "meta_of",
    "odd_conditions",
    "range_text",
    "ratio_jobs",
    "ratio_task",
    "reference_checks",
    "scenario_count",
    "scenarios_for",
    "skill_summary",
    "tier1_weapon_skills",
    "weapons_for",
]

DOT_ROUNDS: Final = 4
STAND: Final = {"melee": (6, 5), "ranged": (6, 7)}
"""主角站位（#148 核對的 ``measure.py``）。"""
ALLY_BESIDE_CASTER: Final = {"melee": (7, 5), "ranged": (7, 7)}
"""``adjacent_ally``：施放者旁邊放一個我方木樁。"""
ENEMY_BESIDE_TARGET: Final = (7, 4)
"""``target_isolated`` 不成立：目標旁邊放一個敵方木樁。"""
LOW_RATIO: Final = 0.9
SINGLE_SHAPES: Final = frozenset({"single", "unit_then_tile"})
CLASS_ORDER: Final = ("ranged", "melee", "focus")
CLASS_ZH: Final = {"ranged": "遠程", "melee": "近戰", "focus": "法器"}
DUAL: Final = "dual_dagger"
LINGERING: Final = frozenset({"apply_status", "create_surface", "summon", "delayed_damage"})
NATURAL_ON: Final = frozenset({"first_round", "target_isolated"})
"""在靶場自然成立的條件：「不成立」要另外做。"""

_BASIC: dict[tuple[str | None, int, str, tuple[tuple[str, int], ...]], tuple[float, int]] = {}
"""普攻的平均（每個工作行程內）：鍵＝(內容資料夾, 種子數, 武器, 配點)。"""


# ---------------------------------------------------------------------------
# 技能分類
# ---------------------------------------------------------------------------


def _walk(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def conditions_of(skill: SkillDef) -> list[str]:
    """技能與效果上的條件種類（不含 ``wielding_weapon``），另加疊層 ``stack:<id>``、引爆狀態
    （``consume_status`` 當成目標要有該狀態）；排序。"""
    data = skill.model_dump(mode="json", exclude_none=True)
    kinds: set[str] = set()
    for node in _walk({"condition": data.get("condition"), "e": data["effects"]}):
        cond = node.get("condition")
        if isinstance(cond, dict) and cond.get("type") not in (None, "wielding_weapon"):
            kinds.add(_cond_key(cond))
        if node.get("type") == "consume_stack" and node.get("stack"):
            kinds.add(f"stack:{node['stack']}")
        if node.get("type") == "consume_status" and node.get("status"):
            kinds.add(f"target_has_status:{node['status']}")
    return sorted(kinds)


def _cond_key(cond: dict[str, Any]) -> str:
    kind = str(cond["type"])
    for extra in ("status", "surface", "permille"):
        if cond.get(extra) is not None:
            return f"{kind}:{cond[extra]}"
    return kind


def bound_weapons(skill: SkillDef) -> list[str]:
    data = skill.model_dump(mode="json", exclude_none=True)
    found = {
        str(node["condition"]["weapon"])
        for node in _walk(data["effects"])
        if isinstance(node.get("condition"), dict)
        and node["condition"].get("type") == "wielding_weapon"
    }
    return sorted(found)


def lingers(skill: SkillDef) -> bool:
    data = skill.model_dump(mode="json", exclude_none=True)
    if data.get("followup") or any(v.get("element") for v in data.get("variants", [])):
        return True
    for node in _walk(data["effects"]):
        if node.get("type") in LINGERING and node.get("affects") not in ("self", "allies"):
            return True
    return False


def has_shadowstep_behind(skill: SkillDef) -> bool:
    data = skill.model_dump(mode="json", exclude_none=True)
    return any(n.get("type") == "shadowstep" and n.get("landing") == "behind" for n in _walk(data))


def is_measurable(skill: SkillDef) -> bool:
    """量得到比值的招：1 階、主動、武器技、非敵人專用（同 :func:`tier1_weapon_skills`）。"""
    return (
        skill.tier == 1
        and not skill.enemy_only
        and skill.kind == "active"
        and skill.category == "weapon"
    )


def tier1_weapon_skills(lib: ContentLibrary) -> list[SkillDef]:
    """1 階、主動、武器技、非敵人專用（依大類、ID 排序）。"""
    out = [s for s in lib.skills.values() if is_measurable(s)]
    return sorted(out, key=lambda s: (class_rank(str(s.weapon_req)), s.id))


def class_rank(weapon_class: str) -> int:
    return CLASS_ORDER.index(weapon_class) if weapon_class in CLASS_ORDER else len(CLASS_ORDER)


def weapons_for(lib: ContentLibrary, skill: SkillDef) -> list[str]:
    """可放這招的開局武器（大類相符、不是敵人專用、``weapon_only`` 相符）。"""
    out = []
    for wid in sorted(lib.weapons):
        wd = lib.weapons[wid]
        if wd.summon_only or wd.enemy_only or wd.weapon_class != skill.weapon_req:
            continue
        if skill.weapon_only and wid not in skill.weapon_only:
            continue
        out.append(wid)
    return out


# ---------------------------------------------------------------------------
# 一場
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Scenario:
    name: str
    """``base``（沒有條件）、``off``（條件不成立）、``on``（條件成立）、``var:<id>``（變奏）。"""
    wait_round: bool = False
    blocker: tuple[int, int] | None = None
    ally_at: tuple[int, int] | None = None
    tweaks: tuple[str, ...] = ()
    variant: str | None = None


def scenarios_for(lib: ContentLibrary, skill: SkillDef, weapon_class: str) -> list[Scenario]:
    conds = conditions_of(skill)
    out: list[Scenario] = []
    if conds:
        out.append(_off(lib, skill, conds, weapon_class))
        out.append(_on(skill, conds, weapon_class))
    else:
        out.append(Scenario("base"))
    out.extend(Scenario(f"var:{v.id}", variant=v.id) for v in skill.variants)
    return out


def scenario_count(skill: SkillDef) -> int:
    """一把武器要跑幾個情境（不必建場地；和 :func:`scenarios_for` 的長度相同）。"""
    return (2 if conditions_of(skill) else 1) + len(skill.variants)


def _off(lib: ContentLibrary, skill: SkillDef, conds: list[str], weapon_class: str) -> Scenario:
    wait = "first_round" in conds
    blocker = None
    tweaks: list[str] = []
    if "from_behind" in conds:
        if has_shadowstep_behind(skill):
            blocker = _target_back(lib)
        else:
            tweaks.append("face_caster")
    if "target_isolated" in conds:
        blocker = ENEMY_BESIDE_TARGET
    del weapon_class
    return Scenario("off", wait_round=wait, blocker=blocker, tweaks=tuple(tweaks))


def _on(skill: SkillDef, conds: list[str], weapon_class: str) -> Scenario:
    ally_at = None
    tweaks: list[str] = []
    for cond in conds:
        kind = cond.split(":", 1)[0]
        if kind in NATURAL_ON or (kind == "from_behind" and has_shadowstep_behind(skill)):
            continue
        if kind == "adjacent_ally":
            ally_at = ALLY_BESIDE_CASTER[weapon_class]
        elif kind == "flanked":
            ally_at = (6, 3)  # 主角在木樁南邊，對面格是北邊
        else:
            tweaks.append(cond)
    return Scenario("on", ally_at=ally_at, tweaks=tuple(tweaks))


def _target_back(lib: ContentLibrary) -> tuple[int, int]:
    """木樁開場朝向的背後格（瞬步背刺的落點；擋住它＝背刺不成立）。"""
    state = begin_battle(_setup(lib, "dagger", "skill_shadow_backstab", Scenario("off")), 1).state
    target = _target(lib, state)
    x, y = back_xy(target)
    return (x, y)


def _setup(lib: ContentLibrary, weapon: str, skill_id: str, sc: Scenario) -> BattleSetup:
    hero = _hero(lib, weapon, skill_id)
    wc = lib.weapons[weapon].weapon_class
    units = [
        UnitSpawn(template=hero, weapon=lib.weapon_of(hero), team=Team.ALLY, position=STAND[wc])
    ]
    if sc.ally_at is not None:
        t = lib.unit("training_dummy")
        units.append(
            UnitSpawn(template=t, weapon=lib.weapon_of(t), team=Team.ALLY, position=sc.ally_at)
        )
    arena = range_content(lib)
    spots: list[tuple[str, tuple[int, int]]] = [(d.unit, (d.at[0], d.at[1])) for d in arena.dummies]
    if sc.blocker is not None:
        spots.append(("training_dummy", sc.blocker))
    for unit, at in spots:
        t = lib.unit(unit)
        units.append(
            UnitSpawn(
                template=t,
                weapon=lib.weapon_of(t),
                equipment=lib.loadout_of(t),
                team=Team.ENEMY,
                position=at,
            )
        )
    return BattleSetup(
        map=lib.maps[arena.map],
        ruleset=lib.ruleset,
        units=tuple(units),
        max_rounds=30,
        first_team=Team.ALLY,
    )


def _hero(lib: ContentLibrary, weapon: str, skill_id: str) -> Any:
    skill = lib.skills[skill_id]
    alloc = recommended_allocation([skill], lib.weapons[weapon], lib.roguelite.start_free_points)
    return apply_allocation(start_hero(lib, weapon, [skill_id]), alloc)


def _alloc_key(lib: ContentLibrary, weapon: str, skill_id: str) -> tuple[tuple[str, int], ...]:
    skill = lib.skills[skill_id]
    alloc = recommended_allocation([skill], lib.weapons[weapon], lib.roguelite.start_free_points)
    return tuple(sorted((str(k), v) for k, v in alloc.items()))


def _target_pos(lib: ContentLibrary) -> tuple[int, int]:
    at = range_content(lib).dummies[2].at
    return (at[0], at[1])


def _target(lib: ContentLibrary, state: BattleState) -> UnitState:
    unit = state.unit_at(*_target_pos(lib))
    assert unit is not None
    return unit


def _hero_id(state: BattleState) -> Any:
    return next(
        u.id
        for u in sorted(state.units.values(), key=lambda u: str(u.id))
        if u.team is Team.ALLY and u.template_id != "training_dummy"
    )


def _settle(res: ResolveResult, policy: CommandedAI) -> BattleState:
    """結算暫停（例如主角的反應）一律交給 AI 決定，直到沒有暫停。"""
    if res.pending is None:
        return res.state
    state, _, _ = advance(res.state, res.pending, policy, stop=lambda st, p: p is None)
    return state


def _end_turn(state: BattleState, hid: Any, policy: CommandedAI) -> BattleState:
    return _to_hero(_settle(apply_step(state, EndTurn(unit_id=hid)), policy), hid, policy)


def _to_hero(state: BattleState, hid: Any, policy: CommandedAI) -> BattleState:
    if state.active_unit != hid and not state.ended:
        state, _, _ = advance(
            state, None, policy, stop=lambda st, p: p is None and st.active_unit == hid
        )
    return state


def _apply_tweaks(
    lib: ContentLibrary,
    state: BattleState,
    hero: UnitState,
    target: UnitState,
    tweaks: Sequence[str],
) -> None:
    for tweak in tweaks:
        kind, _, arg = tweak.partition(":")
        if kind == "target_has_status":
            target.statuses.append(StatusInstance(arg, remaining=2))
        elif kind == "target_on_surface":
            _surface(state, target.xy, arg)
        elif kind == "height_advantage":
            _raise(state, hero.xy, target.xy)
        elif kind == "self_concealed":
            hero.statuses.append(StatusInstance(CONCEALED, remaining=4))
        elif kind == "moved_this_turn":
            hero.moved_this_turn = True
        elif kind == "target_collided":
            target.collided_round = state.round
        elif kind == "target_hp_below":
            target.hp = target.max_hp * int(arg) // 1000 - 1
        elif kind == "stack":
            hero.stacks[arg] = lib.ruleset.stacks.by_id()[arg].max
        elif kind == "face_caster":
            target.facing = _facing_toward(target.xy, hero.xy)
        elif kind == "from_behind":
            target.facing = _facing_toward(hero.xy, target.xy)  # 背對主角
        else:
            raise ValueError(f"不會做的條件：{tweak}")


def _facing_toward(src: tuple[int, int], dst: tuple[int, int]) -> Any:
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    if abs(dx) >= abs(dy):
        return "east" if dx > 0 else "west"
    return "south" if dy > 0 else "north"


def _surface(state: BattleState, xy: tuple[int, int], surface: str) -> None:
    tile = state.tile(*xy)
    state.set_tile(xy[0], xy[1], dataclasses.replace(tile, surface=Surface(surface)))


def _raise(state: BattleState, caster: tuple[int, int], target: tuple[int, int]) -> None:
    tile = state.tile(*caster)
    height = state.tile(*target).height + 1
    state.set_tile(caster[0], caster[1], dataclasses.replace(tile, height=height))


def _variant_tweak(
    state: BattleState,
    hero: UnitState,
    target: UnitState,
    skill: SkillDef,
    variant: str,
) -> None:
    spec = next(v for v in skill.variants if v.id == variant)
    when = spec.when
    if when.caster_surface:
        _surface(state, hero.xy, str(when.caster_surface[0]))
    elif when.target_surface:
        _surface(state, target.xy, str(when.target_surface[0]))
    elif when.caster_high_ground is not None:
        _raise(state, hero.xy, target.xy)
    # caster_adjacent_blocker：近戰站位旁 (5,4) 是石柱，自然成立


def _pick(state: BattleState, skill_id: str, target: UnitState) -> Action | None:
    actions, areas = legal_actions_with_areas(state)
    best: tuple[tuple[int, int, int, int, int], Action] | None = None
    for i, act in enumerate(actions):
        if not isinstance(act, UseSkill) or act.skill_id != skill_id:
            continue
        area = areas.get(id(act))
        units = area.units if area is not None else ()
        tiles = area.tiles if area is not None else ()
        hit = act.target_id == target.id or target.id in units
        dist = min((abs(x - target.xy[0]) + abs(y - target.xy[1]) for x, y in tiles), default=99)
        others = sum(1 for u in units if u != target.id)
        key = (0 if hit else 1, 0 if act.target_id == target.id else 1, others, dist, i)
        if best is None or key < best[0]:
            best = (key, act)
    return None if best is None else best[1]


def one(
    lib: ContentLibrary,
    setup: BattleSetup,
    seed: int,
    skill_id: str | None,
    *,
    sc: Scenario,
    dot: bool,
) -> dict[str, Any] | None:
    """一個種子：``imm``、``tot``、``ap``、``met``（條件在施放前是否成立）；不能放時 ``None``。"""
    policy = CommandedAI(UtilityAI(lib.ai_profiles), {})
    state = begin_battle(setup, seed).state
    hid = _hero_id(state)
    state = _to_hero(state, hid, policy)
    if sc.wait_round:
        state = _end_turn(state, hid, policy)
    hero = state.units[hid]
    target = _target(lib, state)
    met: bool | None = None
    action: Action
    if skill_id is None:
        action = Attack(unit_id=hid, target_id=target.id)
    else:
        skill = lib.skills[skill_id]
        _apply_tweaks(lib, state, hero, target, sc.tweaks)
        if sc.variant is not None:
            _variant_tweak(state, hero, target, skill, sc.variant)
        picked = _pick(state, skill_id, target)
        if picked is None:
            return None
        action = picked
        met = _conditions_met(state, hero, target, skill, sc)
    hp0, ap0 = target.hp, hero.ap
    state = _settle(apply_step(state, action), policy)
    imm = hp0 - state.units[target.id].hp
    ap = ap0 - state.units[hid].ap
    if dot:
        for _ in range(DOT_ROUNDS):
            if state.ended:
                break
            state = _end_turn(state, hid, policy)
    return {"imm": imm, "tot": hp0 - state.units[target.id].hp, "ap": ap, "met": met}


def _conditions_met(
    state: BattleState, hero: UnitState, target: UnitState, skill: SkillDef, sc: Scenario
) -> bool | None:
    if sc.variant is not None:
        spec = next(v for v in skill.variants if v.id == sc.variant)
        return variant_holds(state, hero, spec.when, target.xy)
    if sc.name == "base":
        return None
    subject = Subject(target, target.xy)
    conds = [skill.condition] if skill.condition is not None else []
    skip = {"wielding_weapon"}
    if has_shadowstep_behind(skill):
        skip.add("from_behind")  # 施放後才繞到背後，施放前看不出來
    for effect in skill.effects:
        cond = getattr(effect, "condition", None)
        if cond is not None and cond.type not in skip:
            conds.append(cond)
    if not conds:
        return None  # 只有疊層
    return all(condition_met(state, hero, c, subject) for c in conds)


# ---------------------------------------------------------------------------
# 工作
# ---------------------------------------------------------------------------


def _mean(
    lib: ContentLibrary,
    setup: BattleSetup,
    seeds: int,
    skill_id: str | None,
    *,
    sc: Scenario,
    dot: bool,
) -> dict[str, Any]:
    imm = tot = 0
    ap = 0
    met: int | None = None
    n = 0
    for seed in range(1, seeds + 1):
        r = one(lib, setup, seed, skill_id, sc=sc, dot=dot)
        if r is None:
            return {"castable": False}
        imm += r["imm"]
        tot += r["tot"]
        ap = r["ap"]
        if r["met"] is not None:
            met = (met or 0) + (1 if r["met"] else 0)
        n += 1
    return {"castable": True, "imm": imm / n, "tot": tot / n, "ap": ap, "met": met}


@dataclasses.dataclass(frozen=True)
class RatioJob:
    """一組（武器 × 招）：這招的每個情境各跑 ``seeds`` 個種子（種子 1..seeds）。"""

    weapon: str
    skill: str
    seeds: int


def measure(lib: ContentLibrary, job: RatioJob, root: str | None = None) -> dict[str, Any]:
    """一組（武器 × 招）的結果（同 ``t1_skill_ratio.py run`` JSON 的 ``rows`` 一列）。``root`` 只
    當普攻快取的鍵（同一個行程跑不同內容資料夾時不混用）。"""
    weapon, skill_id, seeds = job.weapon, job.skill, job.seeds
    skill = lib.skills[skill_id]
    wc = lib.weapons[weapon].weapon_class
    alloc = _alloc_key(lib, weapon, skill_id)
    key = (root, seeds, weapon, alloc)
    if key not in _BASIC:
        base = _mean(
            lib,
            _setup(lib, weapon, skill_id, Scenario("base")),
            seeds,
            None,
            sc=Scenario("base"),
            dot=False,
        )
        _BASIC[key] = (base["imm"], base["ap"])
    b_imm, b_ap = _BASIC[key]
    per_ap = b_imm / b_ap
    dot = lingers(skill)
    out: dict[str, Any] = {}
    for sc in scenarios_for(lib, skill, wc):
        res = _mean(lib, _setup(lib, weapon, skill_id, sc), seeds, skill_id, sc=sc, dot=dot)
        if res["castable"] and res["ap"] > 0:
            res["ratio"] = round(res["imm"] / res["ap"] / per_ap, 3)
            res["ratio_tot"] = round(res["tot"] / res["ap"] / per_ap, 3)
        out[sc.name] = res
    return {
        "weapon": weapon,
        "class": wc,
        "skill": skill_id,
        "basic": {"imm": b_imm, "ap": b_ap},
        "alloc": dict(alloc),
        "scenarios": out,
    }


def ratio_task(root: str | None, job: RatioJob) -> dict[str, Any]:
    """平行用的頂層函式：``root`` 的內容庫（``None``＝專案內建）量一組。"""
    return measure(library_for(root), job, root)


def meta_of(lib: ContentLibrary, skill: SkillDef) -> dict[str, Any]:
    return {
        "name_zh": skill.name_zh,
        "class": str(skill.weapon_req),
        "ap": skill.ap_cost,
        "shape": str(skill.shape.type),
        "conds": conditions_of(skill),
        "bound": bound_weapons(skill),
        "variants": [v.id for v in skill.variants],
        "lingers": lingers(skill),
        "weapon_only": list(skill.weapon_only),
        "weapons": weapons_for(lib, skill),
        "damaging": any(
            n.get("type") in ("damage", "charge_through")
            for n in _walk(skill.model_dump(mode="json", exclude_none=True))
        ),
        "summon": any(
            n.get("type") == "summon"
            for n in _walk(skill.model_dump(mode="json", exclude_none=True))
        ),
    }


def ratio_jobs(
    lib: ContentLibrary,
    skills: Sequence[SkillDef],
    seeds: int,
    weapons: set[str] | None = None,
) -> list[RatioJob]:
    """每招 × 可用武器（招在外層、武器在內層；``weapons`` 有給時只留這些武器）。"""
    return [
        RatioJob(w, s.id, seeds)
        for s in skills
        for w in weapons_for(lib, s)
        if weapons is None or w in weapons
    ]


# ---------------------------------------------------------------------------
# 彙總
# ---------------------------------------------------------------------------


def range_text(values: Sequence[float]) -> str:
    """``0.74～0.78``（兩位小數相同時只寫一個；沒有值寫「—」）。"""
    if not values:
        return "—"
    lo, hi = min(values), max(values)
    return f"{lo:.2f}" if f"{lo:.2f}" == f"{hi:.2f}" else f"{lo:.2f}～{hi:.2f}"


def _ratios(rows: list[dict[str, Any]], scenario: str, field: str) -> list[float]:
    out = []
    for r in rows:
        res = r["scenarios"].get(scenario)
        if res and res.get("castable") and field in res:
            out.append(float(res[field]))
    return out


def skill_summary(meta: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """一招的摘要：一般武器（不含雙匕首、不含綁定武器）與綁定武器、雙匕首分開。"""
    bound = set(meta["bound"])
    normal = [r for r in rows if r["weapon"] != DUAL and r["weapon"] not in bound]
    if not normal:
        normal = [r for r in rows if r["weapon"] not in bound] or rows
    names = list(rows[0]["scenarios"]) if rows else []
    plain = "base" if "base" in names else "off"
    out: dict[str, Any] = {
        "plain": _ratios(normal, plain, "ratio"),
        "plain_tot": _ratios(normal, plain, "ratio_tot"),
        "on": _ratios(normal, "on", "ratio"),
        "on_tot": _ratios(normal, "on", "ratio_tot"),
        "vars": {n: _ratios(normal, n, "ratio") for n in names if n.startswith("var:")},
        "vars_tot": {n: _ratios(normal, n, "ratio_tot") for n in names if n.startswith("var:")},
        "dual": _ratios([r for r in rows if r["weapon"] == DUAL], plain, "ratio"),
        "bound": {r["weapon"]: _ratios([r], plain, "ratio") for r in rows if r["weapon"] in bound},
    }
    return out


def odd_conditions(data: dict[str, Any]) -> list[str]:
    """施放前檢查條件時和情境不符的組（「成立」沒成立、「不成立」卻成立）。"""
    out = []
    for r in data["rows"]:
        for name, res in r["scenarios"].items():
            met = res.get("met")
            if not res.get("castable") or met is None:
                continue
            want = 0 if name == "off" else data["seeds"]
            if met != want:
                out.append(f"{r['skill']} {r['weapon']} {name} 成立 {met}/{data['seeds']}")
    return out


def low_tag(m: dict[str, Any]) -> str:
    """BAL-21e 的類別：召喚／非傷害招／非單體／條件類／無條件。"""
    if m["summon"]:
        return "召喚"
    if not m["damaging"]:
        return "非傷害招"
    if m["shape"] not in SINGLE_SHAPES:
        return "非單體"
    return "條件類" if m["conds"] or m["variants"] else "無條件"


# ---------------------------------------------------------------------------
# 參考線（D4：只當參考，不擋寫回）
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ReferenceLine:
    key: str
    label_zh: str
    threshold: float
    tentative: bool
    """``True``＝「建議，未定案」（BAL-21e 第 6 節、專案 PM 交接）。"""


REFERENCE_LINES: Final = {
    "plain": ReferenceLine("plain", "無條件單體（直接）", 0.9, tentative=False),
    "on": ReferenceLine("on", "條件成立（直接）", 1.1, tentative=False),
    "off": ReferenceLine("off", "條件不成立（直接）", 0.6, tentative=True),
    "arrow": ReferenceLine("arrow", "1 AP 箭類（直接）", 0.6, tentative=True),
}
"""D4 的四條參考線（``docs/phases/PhaseNW-2計畫.md`` 0.0）。"""


def _is_arrow(meta: dict[str, Any]) -> bool:
    """1 AP 箭類：1 階、遠程、AP 1、單體傷害（同工坊常用預設組；``meta`` 只會是 1 階武器技）。"""
    return (
        meta["class"] == "ranged"
        and meta["ap"] == 1
        and meta["damaging"]
        and meta["shape"] in SINGLE_SHAPES
    )


def reference_checks(
    meta: dict[str, Any], summary: dict[str, Any]
) -> list[tuple[ReferenceLine, float | None]]:
    """這招適用的參考線與比較用的值（範圍的**最高值**，同 BAL-21e「低於 0.9」的判法；沒有值為
    ``None``）。召喚、非傷害招、非單體不套參考線（回空）。

    - 無條件：一般 → ``plain`` ≥ 0.9；1 AP 箭類 → ``arrow`` ≥ 0.6（建議）。
    - 條件類（含變奏）：成立（``on`` 與各變奏）→ ``on`` ≥ 1.1；不成立 → ``off`` ≥ 0.6（建議）。
    """
    tag = low_tag(meta)
    if tag not in ("無條件", "條件類"):
        return []
    plain = max(summary["plain"], default=None)
    if tag == "無條件":
        line = REFERENCE_LINES["arrow" if _is_arrow(meta) else "plain"]
        return [(line, plain)]
    on_values = [*summary["on"], *(x for v in summary["vars"].values() for x in v)]
    return [
        (REFERENCE_LINES["on"], max(on_values, default=None)),
        (REFERENCE_LINES["off"], plain),
    ]
