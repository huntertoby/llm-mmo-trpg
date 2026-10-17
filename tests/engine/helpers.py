"""引擎測試用的小工具：自訂地圖與單位、控制骰子結果。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import cache
from pathlib import Path
from typing import Any

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary, load_library
from trpg.content.maps import MapDef
from trpg.content.skills import SkillDef, SkillTable
from trpg.engine import BattleSetup, BattleState, UnitSpawn, start_battle
from trpg.engine.state import SpawnTemplate
from trpg.shared.rng import Rng, RngState
from trpg.shared.types import Attribute, Team, UnitId

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEMO_ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
DEMO_ENEMIES = ("bandit", "bandit_archer", "bandit_boss")


@cache
def library() -> ContentLibrary:
    return load_library(PROJECT_ROOT / "content")


def make_map(
    heights: str,
    terrain: str | None = None,
    *,
    ally: Sequence[tuple[int, int]] = ((0, 0),),
    enemy: Sequence[tuple[int, int]] | None = None,
    objects: Sequence[tuple[int, int, str]] = (),
    surfaces: Sequence[tuple[int, int, str]] = (),
    objective: dict[str, object] | None = None,
    events: Sequence[dict[str, object]] = (),
) -> MapDef:
    """以字串建立地圖。

    ``terrain`` 圖例：``.`` 石地、``x`` 深淵、``~`` 岩漿、``g`` 草地、``d`` 泥土、``#`` 牆壁。

    ``objects``／``surfaces``：``(x, y, 種類)``。``objective``、``events`` 直接以地圖檔格式給定。
    """
    rows = heights.strip().split("\n")
    w, h = len(rows[0]), len(rows)
    if terrain is None:
        terrain = "\n".join("." * w for _ in range(h))
    data: dict[str, object] = {
        "id": "test_map",
        "name_zh": "測試",
        "size": [w, h],
        "heights": heights.strip(),
        "terrain": terrain.strip(),
        "legend": {
            ".": "stone",
            "x": "chasm",
            "~": "lava",
            "g": "grass",
            "d": "dirt",
            "#": "wall",
        },
        "objects": [{"at": [x, y], "kind": k} for x, y, k in objects],
        "surfaces": [{"at": [x, y], "surface": k} for x, y, k in surfaces],
        "events": list(events),
        "start_zones": {
            "ally": [list(c) for c in ally],
            "enemy": [list(c) for c in (enemy or [(w - 1, h - 1)])],
        },
    }
    if objective is not None:
        data["objective"] = objective
    return MapDef.model_validate(data)


def template(base: str = "bandit", **overrides: object) -> UnitTemplate:
    """以既有範本為基礎修改欄位（例如 ``max_hp``、``tags``、``attributes``）。"""
    t = library().unit(base)
    if "attributes" in overrides and isinstance(overrides["attributes"], dict):
        attrs = dict(t.attributes)
        attrs.update({Attribute(k): v for k, v in overrides["attributes"].items()})
        overrides["attributes"] = attrs
    return UnitTemplate.model_validate({**t.model_dump(), **overrides})


def spawn(
    team: Team,
    pos: tuple[int, int],
    tmpl: UnitTemplate | str = "bandit",
    weapon: str | None = None,
    *,
    skills: Sequence[str] | None = (),
) -> UnitSpawn:
    """以範本 ID 指定時，``skills`` 預設為空（Phase 1 的測試不帶技能）；``None`` 表示沿用範本
    的技能。直接給範本物件時一律沿用它的技能。"""
    lib = library()
    t = lib.unit(tmpl) if isinstance(tmpl, str) else tmpl
    w = lib.weapons[weapon or t.weapon]
    if (isinstance(tmpl, str) and skills is not None) or (
        weapon is not None and weapon != t.weapon and skills is not None
    ):
        t = t.model_copy(update={"skills": tuple(skills)})
    return UnitSpawn(template=t, weapon=w, team=team, position=pos)


def make_setup(
    map_def: MapDef,
    spawns: Sequence[UnitSpawn],
    *,
    max_rounds: int | None = None,
    weather: str | None = None,
    spawn_templates: Sequence[str] = (),
    skills: Sequence[SkillDef] = (),
    **core: int,
) -> BattleSetup:
    """``core`` 可覆寫 ``rules/core.yaml`` 的數值。

    例如 ``fall_damage_permille_per_level=200``。``spawn_templates`` 為地圖事件會產生的單位範本。
    """
    lib = library()
    rs = lib.ruleset
    if core:
        rs = rs.model_copy(update={"core": rs.core.model_copy(update=core)})
    if skills:  # 測試專用技能：加進規則集（重建查表索引）
        rs = rs.model_copy(update={"skills": SkillTable(skills=(*rs.skills.skills, *skills))})
        rs.model_post_init(None)
    templates = {
        t: SpawnTemplate(template=lib.unit(t), weapon=lib.weapon_of(lib.unit(t)))
        for t in spawn_templates
    }
    return BattleSetup(
        map=map_def,
        ruleset=rs,
        units=tuple(spawns),
        max_rounds=max_rounds,
        weather=None if weather is None else lib.weather_def(weather),
        spawn_templates=templates,
    )


def make_state(
    map_def: MapDef,
    spawns: Sequence[UnitSpawn],
    *,
    seed: int = 0,
    weather: str | None = None,
    spawn_templates: Sequence[str] = (),
    skills: Sequence[SkillDef] = (),
    **core: int,
) -> BattleState:
    return start_battle(
        make_setup(
            map_def, spawns, weather=weather, spawn_templates=spawn_templates, skills=skills, **core
        ),
        seed,
    )


def give_turn(state: BattleState, unit_id: str) -> BattleState:
    """回傳複本：把行動者換成 ``unit_id``，並給滿 AP 與移動點數（測試用）。"""
    s = state.clone()
    uid = UnitId(unit_id)
    s.active_unit = uid
    s.turn_pos = s.turn_order.index(uid)
    unit = s.units[uid]
    unit.ap = s.ruleset.core.ap_per_turn
    unit.move_points = unit.speed
    return s


def rng_state_for(rolls: Sequence[tuple[int, int]], limit: int = 2_000_000) -> RngState:
    """找一個亂數狀態，使接下來依序 ``roll(sides)`` 得到指定值：``[(20, 20), (8, 3)]``。"""
    for seed in range(limit):
        rng = Rng(seed)
        start = rng.get_state()
        if all(rng.roll(sides) == value for sides, value in rolls):
            return start
    raise AssertionError(f"找不到符合 {rolls} 的種子")


def with_rolls(state: BattleState, rolls: Sequence[tuple[int, int]]) -> BattleState:
    s = state.clone()
    s.rng_state = rng_state_for(rolls)
    return s


def no_reactions(base: str = "bandit", **overrides: object) -> UnitTemplate:
    """沒有反應規則的範本（不格擋、不藉機攻擊），方便驗證其他規則。"""
    return template(base, reactions=[], **overrides)


def unit_at(state: BattleState, x: int, y: int) -> str | None:
    u = state.unit_at(x, y)
    return None if u is None else u.id


def make_skill(
    skill_id: str,
    shape: Mapping[str, Any],
    effects: Sequence[Mapping[str, Any]],
    *,
    category: str = "spell",
    weapon_req: str | None = None,
    ap_cost: int = 1,
    attr: str | None = None,
    cost: Mapping[str, Any] | None = None,
) -> SkillDef:
    """測試專用技能（不放在 ``content/``）。法術技預設需要法器、縮放智力；武器技預設近戰、力量。"""
    spell = category == "spell"
    return SkillDef.model_validate(
        {
            "id": skill_id,
            "name_zh": f"測試技 {skill_id[-6:]}",
            "tier": 1,
            "rarity": "common",
            "skeleton": "area",
            "category": category,
            "weapon_req": weapon_req or ("focus" if spell else "melee"),
            "ap_cost": ap_cost,
            "scaling_attr": attr or ("int" if spell else "str"),
            "shape": shape,
            "effects": list(effects),
            "cost": cost or {"mana": 0},
        }
    )


def caster_template(
    skills: Sequence[SkillDef | str], *, base: str = "hero_mage", **overrides: object
) -> UnitTemplate:
    """施放者範本：沒有反應規則、法力 99、裝備 ``skills``。"""
    ids = [s if isinstance(s, str) else s.id for s in skills]
    return template(base, reactions=[], max_mana=99, skills=ids, **overrides)
