"""BAL-21e：1 階武器技的「每 AP 傷害 ÷ 普攻每 AP」比值表（只讀量測，不改任何內容）。

量法照開發 PM 的 #148 核對（共用筆記「核對-148示範招B案」）：主城靶場 ``training_range``、
``range_trial`` 的推薦配點（開局自由點數全照 ``recommended_allocation``）、打普通木樁 (6,4)；
近戰站 (6,5)、遠程站 (6,7)；每把武器每個情境預設 250 個種子取平均（含失手）。
比值＝（技能對木樁的傷害 ÷ 花掉的 AP）÷（普攻對木樁的傷害 ÷ 花掉的 AP）。

- 「直接」只算施放當下；「含持續」是施放後再過 ``DOT_ROUNDS`` 輪（主角每輪直接結束回合）木樁的
  總損血，涵蓋中毒、燃燒、表面、延遲段與召喚物（只在技能可能有後續傷害時另跑）。
- 條件類另跑「成立」：在施放前直接把狀態改成條件成立（目標加狀態、表面、高低差、隱匿、疊滿層、
  旁邊放一個我方木樁…），「不成立」是自然狀態（第 1 輪、背刺這兩種自然成立的，不成立另外做：
  等一輪、背後格放木樁擋住）。綁武器（``wielding_weapon``）不另跑，直接看那把武器的列。
- 變奏（``variants``）每個另跑一次「成立」。

用法（Windows 一律 ``uv run python``）::

    uv run python scripts/t1_skill_ratio.py run [--seeds 250] [--jobs 6]
        [--skills a,b] [--weapons a,b] [--out 檔] [--detail]
    uv run python scripts/t1_skill_ratio.py report [檔] [--detail]

結果 JSON 預設寫到系統暫存區（``tempfile.gettempdir()``），不進 repo。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from typing import Any

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
from trpg.skillgen.random_composer import default_library
from trpg.world.opening import range_content

DEFAULT_SEEDS = 250
DEFAULT_JOBS = 6
DOT_ROUNDS = 4
STAND = {"melee": (6, 5), "ranged": (6, 7)}
"""主角站位（#148 核對的 ``measure.py``）。"""
ALLY_BESIDE_CASTER = {"melee": (7, 5), "ranged": (7, 7)}
"""``adjacent_ally``：施放者旁邊放一個我方木樁。"""
ENEMY_BESIDE_TARGET = (7, 4)
"""``target_isolated`` 不成立：目標旁邊放一個敵方木樁。"""
LOW_RATIO = 0.9
SINGLE_SHAPES = frozenset({"single", "unit_then_tile"})
CLASS_ORDER = ("ranged", "melee", "focus")
CLASS_ZH = {"ranged": "遠程", "melee": "近戰", "focus": "法器"}
DUAL = "dual_dagger"
LINGERING = frozenset({"apply_status", "create_surface", "summon", "delayed_damage"})
NATURAL_ON = frozenset({"first_round", "target_isolated"})
"""在靶場自然成立的條件：「不成立」要另外做。"""

_LIB: ContentLibrary | None = None
_BASIC: dict[tuple[str, tuple[tuple[str, int], ...]], tuple[float, int]] = {}


def default_out() -> Path:
    return Path(tempfile.gettempdir()) / "t1_skill_ratio.json"


def library() -> ContentLibrary:
    global _LIB  # noqa: PLW0603 - 每個工作行程載入一次
    if _LIB is None:
        _LIB = default_library()
    return _LIB


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


def tier1_weapon_skills(lib: ContentLibrary) -> list[SkillDef]:
    """1 階、主動、武器技、非敵人專用（依大類、ID 排序）。"""
    out = [
        s
        for s in lib.skills.values()
        if s.tier == 1 and not s.enemy_only and s.kind == "active" and s.category == "weapon"
    ]
    return sorted(out, key=lambda s: (_class_rank(str(s.weapon_req)), s.id))


def _class_rank(weapon_class: str) -> int:
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


def task(job: tuple[str, str, int]) -> dict[str, Any]:
    weapon, skill_id, seeds = job
    lib = library()
    skill = lib.skills[skill_id]
    wc = lib.weapons[weapon].weapon_class
    key = (weapon, _alloc_key(lib, weapon, skill_id))
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
        "alloc": dict(key[1]),
        "scenarios": out,
    }


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


def run(args: argparse.Namespace) -> int:
    lib = library()
    skills = tier1_weapon_skills(lib)
    if args.skills:
        wanted = set(args.skills.split(","))
        skills = [s for s in skills if s.id in wanted]
    weapons_filter = set(args.weapons.split(",")) if args.weapons else None
    meta = {s.id: meta_of(lib, s) for s in skills}
    jobs = [
        (w, s.id, args.seeds)
        for s in skills
        for w in meta[s.id]["weapons"]
        if weapons_filter is None or w in weapons_filter
    ]
    print(
        f"{len(skills)} 招、{len(jobs)} 組（武器×招）、每組 {args.seeds} 種子、程序池 {args.jobs}",
        file=sys.stderr,
    )
    with ProcessPoolExecutor(max_workers=args.jobs, mp_context=get_context("spawn")) as pool:
        rows = list(pool.map(task, jobs, chunksize=1))
    rows.sort(key=lambda r: (_class_rank(r["class"]), r["skill"], r["weapon"]))
    data = {"seeds": args.seeds, "dot_rounds": DOT_ROUNDS, "skills": meta, "rows": rows}
    out = Path(args.out) if args.out else default_out()
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"寫入 {out}", file=sys.stderr)
    report_data(data, detail=args.detail)
    return 0


# ---------------------------------------------------------------------------
# 重印
# ---------------------------------------------------------------------------


def _rng(values: Sequence[float]) -> str:
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


def _cond_zh(meta: dict[str, Any]) -> str:
    parts = list(meta["conds"]) + [f"變奏 {v}" for v in meta["variants"]]
    if meta["bound"]:
        parts.append("綁 " + "/".join(meta["bound"]))
    return "、".join(parts) if parts else "無"


def _low_tag(m: dict[str, Any]) -> str:
    if m["summon"]:
        return "召喚"
    if not m["damaging"]:
        return "非傷害招"
    if m["shape"] not in SINGLE_SHAPES:
        return "非單體"
    return "條件類" if m["conds"] or m["variants"] else "無條件"


def _skill_line(
    m: dict[str, Any], sid: str, rows: list[dict[str, Any]]
) -> tuple[str, float | None]:
    """摘要表的一列，與這招所有武器、情境的直接比值最高值（沒有可用武器時 ``None``）。"""
    head = f"| {m['name_zh']} `{sid}` | {m['ap']} | {m['shape']} | {_cond_zh(m)} "
    if not rows:
        return head + "| 沒有可用武器 | | | | | |", None
    s = skill_summary(m, rows)
    ons = [_rng(s["on"])] if s["on"] else []
    on_tots = [_rng(s["on_tot"])] if s["on_tot"] else []
    for vname, vals in s["vars"].items():
        ons.append(f"{vname[4:]} {_rng(vals)}")
        on_tots.append(f"{vname[4:]} {_rng(s['vars_tot'][vname])}")
    on = "；".join(ons) or "—"
    on_tot = "；".join(on_tots) if m["lingers"] and on_tots else "—"
    bound = "；".join(f"{w} {_rng(v)}" for w, v in s["bound"].items()) or "—"
    plain_tot = _rng(s["plain_tot"]) if m["lingers"] else "—"
    plain = _rng(s["plain"]) if s["plain"] else "不可放"
    line = f"{head}| {plain} | {plain_tot} | {on} | {on_tot} | {_rng(s['dual'])} | {bound} |"
    every = s["plain"] + s["on"] + [x for v in s["vars"].values() for x in v]
    every += [x for v in s["bound"].values() for x in v]
    return line, max(every, default=0.0)


def report_data(data: dict[str, Any], *, detail: bool = False) -> None:
    meta: dict[str, dict[str, Any]] = data["skills"]
    by_skill: dict[str, list[dict[str, Any]]] = {}
    for r in data["rows"]:
        by_skill.setdefault(r["skill"], []).append(r)
    print(f"種子 {data['seeds']}／組；含持續＝施放後 {data['dot_rounds']} 輪；")
    print("比值＝技能每 AP ÷ 普攻每 AP；範圍是一般武器（不含雙匕首與綁定武器）")
    print("直接／含持續＝無條件或條件不成立；成立＝條件或變奏成立；綁定武器＝不成立情境下那把武器")
    low: list[tuple[str, str, float, str]] = []
    for wc in CLASS_ORDER:
        ids = [s for s in meta if meta[s]["class"] == wc]
        print(f"\n## {CLASS_ZH[wc]}（{len(ids)} 招）\n")
        print("| 招 | AP | 形狀 | 條件 | 直接 | 含持續 | 成立 直接 | 成立 含持續 ", end="")
        print("| 雙匕首 | 綁定武器 |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for sid in ids:
            line, best = _skill_line(meta[sid], sid, by_skill.get(sid, []))
            print(line)
            if best is not None and best < LOW_RATIO:
                low.append((wc, sid, best, _low_tag(meta[sid])))
        by_weapon(data, wc)
    print(f"\n## 低於 {LOW_RATIO} 的招（直接傷害，取所有武器與情境的最高值仍 < {LOW_RATIO}）\n")
    print("| 大類 | 招 | 最高比值 | 類別 | 含持續最高 |")
    print("|---|---|---|---|---|")
    tags = ("無條件", "條件類", "非單體", "召喚", "非傷害招")
    low.sort(key=lambda t: (_class_rank(t[0]), tags.index(t[3]), t[2], t[1]))
    for wc, sid, best, tag in low:
        tots = [
            float(res["ratio_tot"])
            for r in by_skill[sid]
            for res in r["scenarios"].values()
            if res.get("castable") and "ratio_tot" in res
        ]
        tot = f"{max(tots):.2f}" if meta[sid]["lingers"] and tots else "—"
        print(f"| {CLASS_ZH[wc]} | {meta[sid]['name_zh']} `{sid}` | {best:.2f} | {tag} | {tot} |")
    counts = "；".join(
        f"{CLASS_ZH[wc]}{tag} {sum(1 for t in low if t[0] == wc and t[3] == tag)}"
        for wc in CLASS_ORDER
        for tag in tags
        if any(t[0] == wc and t[3] == tag for t in low)
    )
    print(f"\n共 {len(low)} 招（{counts}）")
    odd = odd_conditions(data)
    print(f"\n條件檢查：施放前條件和情境不符 {len(odd)} 組")
    for line in odd:
        print(f"- {line}")
    if detail:
        print_detail(data)


def by_weapon(data: dict[str, Any], wc: str) -> None:
    """大類 × 武器：單體傷害招（形狀單體、有傷害效果）的直接比值（條件類取不成立）分布。"""
    meta = data["skills"]
    rows = [
        r
        for r in data["rows"]
        if r["class"] == wc
        and meta[r["skill"]]["damaging"]
        and meta[r["skill"]]["shape"] in SINGLE_SHAPES
    ]
    weapons = sorted({r["weapon"] for r in rows})
    if not weapons:
        return
    print(f"\n{CLASS_ZH[wc]} × 武器（單體傷害招的直接比值；條件類取不成立）\n")
    print("| 武器 | 普攻每 AP | 單體傷害招 | ≥ 0.9 | 中位數 | 最高 |")
    print("|---|---|---|---|---|---|")
    for w in weapons:
        vals = []
        basic = 0.0
        for r in rows:
            if r["weapon"] != w:
                continue
            basic = r["basic"]["imm"] / r["basic"]["ap"]
            name = "base" if "base" in r["scenarios"] else "off"
            res = r["scenarios"][name]
            if res.get("castable") and "ratio" in res:
                vals.append(float(res["ratio"]))
        vals.sort()
        med = vals[len(vals) // 2] if vals else 0.0
        hi = vals[-1] if vals else 0.0
        good = sum(1 for v in vals if v >= LOW_RATIO)
        print(f"| {w} | {basic:.2f} | {len(vals)} | {good} | {med:.2f} | {hi:.2f} |")


def print_detail(data: dict[str, Any]) -> None:
    print("\n## 逐武器明細\n")
    for r in data["rows"]:
        parts = []
        for name, res in r["scenarios"].items():
            if not res.get("castable"):
                parts.append(f"{name}=不可放")
                continue
            met = "" if res.get("met") is None else f" 成立{res['met']}"
            parts.append(f"{name}={res.get('ratio', 0):.2f}/{res.get('ratio_tot', 0):.2f}{met}")
        basic = r["basic"]["imm"] / r["basic"]["ap"]
        print(f"{r['skill']:28s} {r['weapon']:16s} 普攻 {basic:.2f}/AP  " + "  ".join(parts))


def report(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else default_out()
    data = json.loads(path.read_text(encoding="utf-8"))
    report_data(data, detail=args.detail)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="跑量測並寫 JSON")
    p_run.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    p_run.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    p_run.add_argument("--skills", default="", help="只跑這些招（逗號分隔）")
    p_run.add_argument("--weapons", default="", help="只跑這些武器（逗號分隔）")
    p_run.add_argument("--out", default="", help=f"JSON 路徑（預設 {default_out()}）")
    p_run.add_argument("--detail", action="store_true", help="另印逐武器明細")
    p_rep = sub.add_parser("report", help="從 JSON 重印摘要表")
    p_rep.add_argument("path", nargs="?", default="")
    p_rep.add_argument("--detail", action="store_true")
    args = parser.parse_args(argv)
    return run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    raise SystemExit(main())
