"""引擎測試用的小工具：自訂地圖與單位、控制骰子結果。"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from functools import cache
from pathlib import Path
from typing import Any

from trpg.content.battle import Dice, UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.maps import MapDef
from trpg.content.skills import SkillDef, SkillTable
from trpg.engine import BattleSetup, BattleState, ResolveResult, UnitSpawn, resume, start_battle
from trpg.engine.runner import accept_all
from trpg.engine.state import SpawnTemplate
from trpg.shared.range_text import range_text, span
from trpg.shared.rng import Rng, RngState
from trpg.shared.types import Attribute, Team, UnitId
from trpg.skillgen.random_composer import default_library

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEMO_ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
DEMO_ENEMIES = ("bandit", "bandit_archer", "bandit_boss")


def library() -> ContentLibrary:
    """正式內容（與根固件 ``content_library``、``default_library()`` 同一份；CODE-2）。"""
    return default_library()


def card_dice(dice: Dice | None, flat: int = 0, lib: ContentLibrary | None = None) -> str:
    """卡片上的骰子寫法（X10-3b）：骰面 × ``quantity_scale`` 再疊固定值（2d6 →「20–120」）。"""
    assert dice is not None
    scale = (lib or library()).ruleset.core.quantity_scale
    return range_text(*span(dice.count, dice.sides, scale, flat))


@cache
def lf2_library() -> ContentLibrary:
    """正式內容，但閃現挑選模式關掉（``skill_pick.yaml`` 的 ``flash_enabled: false``）：PK-3 前的
    LF-2 提議流程（LLM 從目錄提議變化）。測 LF-2 程式本身的測試用這份。"""
    lib = default_library()
    return dataclasses.replace(
        lib, skill_pick=lib.skill_pick.model_copy(update={"flash_enabled": False})
    )


SK1_FLASH_TEMPLATES = frozenset(
    {
        "reshape_skeleton",
        "push_pull_swap",
        "range_reclaim",
        "momentum_buff",
        "element_swap",
        "surface_exploit",
        "distance_bonus",
        "trigger_swap",
        "kill_reset",
        "cost_blood",
        "cost_once",
        "support_cleanse",
        "support_haste",
    }
)
"""SK-1（06 6.38 第 3 點）加的閃現小變化模板。"""


def without_sk1_flash(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但拿掉 SK-1 加的閃現模板：鎖住「某個重現案例在舊模板下才成立」的測試用
    （例：RR-2 的強度下限卡住的重閃格，SK-1 的「每場一次」讓它有了選項）。"""
    minor = tuple(t for t in library.flash.minor if t.id not in SK1_FLASH_TEMPLATES)
    return dataclasses.replace(library, flash=library.flash.model_copy(update={"minor": minor}))


PRE_AP1_CORE: dict[str, int] = {"party_ap_per_turn": 3, "elite_ap_per_turn": 3, "miss_refund_ap": 0}
"""AP-1（#168）之前的行動經濟：每個單位每回合 3 AP、沒有失手返還（工坊值，關回舊行為）。"""


def with_pre_ap1_turns(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但用 AP-1 之前的行動經濟（:data:`PRE_AP1_CORE`）：鎖住「某個重現案例在舊 AP
    下才成立」的測試用（例：開發一輪種子 2 打到營火的閃現歷程，玩家方 4 AP 後戰鬥變短、歷程
    換了）。"""
    rs = library.ruleset
    core = rs.core.model_copy(update=PRE_AP1_CORE)
    return dataclasses.replace(library, ruleset=rs.model_copy(update={"core": core}))


SK2B_PRIMITIVES = frozenset({"hook", "absorb_surface", "contagion"})
"""SK-2b 接進骨架（出題）的新原語。"""


def without_sk2b_offers(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但骨架拿掉 SK-2b 接進出題的新原語（鉤、吸收表面、疾病擴散）：鎖住「LLM 題目樣本」
    固定的測試用（例：補強順序的分布表，題目多了新核心後樣本會換一批）。"""

    def strip(skeleton: Any) -> Any:
        core = skeleton.core.model_copy(
            update={
                "primitives": tuple(p for p in skeleton.core.primitives if p not in SK2B_PRIMITIVES)
            }
        )
        secondary = skeleton.secondary
        if secondary.primitives is not None:
            kept = tuple(p for p in secondary.primitives if p not in SK2B_PRIMITIVES)
            secondary = secondary.model_copy(update={"primitives": kept, "harmless_ok": ()})
        return skeleton.model_copy(update={"core": core, "secondary": secondary})

    return dataclasses.replace(
        library, skeletons={k: strip(v) for k, v in library.skeletons.items()}
    )


SK2B_STREAMS = (
    "hook_core_permille",
    "absorb_core_permille",
    "absorb_secondary_permille",
    "contagion_permille",
)
"""SK-2b 組合器獨立串流的機率欄位（``skill_composer.yaml`` 的 ``structure``）。"""


def sk2b_streams_off(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但 SK-2b 的組合器串流機率都是 0：組合器的種子結果和 SK-2b 之前逐字相同（鎖住
    「某些種子做出某種招」的既有測試用）。"""
    structure = library.composer.structure.model_copy(update=dict.fromkeys(SK2B_STREAMS, 0))
    composer = library.composer.model_copy(update={"structure": structure})
    return dataclasses.replace(library, composer=composer)


def without_sk3b_offers(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但反應骨架拿掉 SK-3b 接進出題的重擲：鎖住「LLM 題目樣本」固定的測試用（同
    :func:`without_sk2b_offers`）。"""

    def strip(skeleton: Any) -> Any:
        kept = tuple(p for p in skeleton.core.primitives if p != "reroll")
        return skeleton.model_copy(
            update={"core": skeleton.core.model_copy(update={"primitives": kept})}
        )

    return dataclasses.replace(
        library, skeletons={k: strip(v) for k, v in library.skeletons.items()}
    )


def without_ap2_offers(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但光環骨架拿掉 AP-2 接進出題的預支（``borrow_ap``）：鎖住「LLM 題目樣本」固定的
    測試用（同 :func:`without_sk3b_offers`）。"""

    def strip(skeleton: Any) -> Any:
        kept = tuple(p for p in skeleton.core.primitives if p != "borrow_ap")
        return skeleton.model_copy(
            update={"core": skeleton.core.model_copy(update={"primitives": kept})}
        )

    return dataclasses.replace(
        library, skeletons={k: strip(v) for k, v in library.skeletons.items()}
    )


def with_whiteboard_ap(library: ContentLibrary, ap: int) -> ContentLibrary:
    """``library`` 但白板主動技的預設 AP 是 ``ap``（AP-2 起 1）：鎖住「某個種子的白板剛好是某個
    樣子」的測試用（例：點燃斬種子 75 在 AP-2 之前是 2 AP、燃燒 5 回合）。"""
    whiteboard = library.composer.whiteboard.model_copy(update={"ap_cost": ap})
    composer = library.composer.model_copy(update={"whiteboard": whiteboard})
    return dataclasses.replace(library, composer=composer)


SK3B_STREAMS = ("exploit_passive_permille", "reroll_reaction_permille")
"""SK-3b 接進出題的組合器串流（「你造的關鍵字被利用時」被動、重擲反應技）。"""


def sk3b_streams(library: ContentLibrary, permille: int) -> ContentLibrary:
    """``library`` 但 SK-3b 的兩個組合器串流機率都設成 ``permille``（0＝和 SK-3b 之前逐字相同；
    1000＝能做就做）。"""
    structure = library.composer.structure.model_copy(update=dict.fromkeys(SK3B_STREAMS, permille))
    composer = library.composer.model_copy(update={"structure": structure})
    return dataclasses.replace(library, composer=composer)


def wish_off(library: ContentLibrary) -> ContentLibrary:
    """``library`` 但許願池願望驅動關掉（``skill_pick.yaml`` 的 ``wish_enabled: false``）：PK-4 前的
    許願流程（對關鍵字＋自由設計）。測 WP-1～3 程式本身的測試用這份。"""
    return dataclasses.replace(
        library, skill_pick=library.skill_pick.model_copy(update={"wish_enabled": False})
    )


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
        "archetype": "test",
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
    if base == "bandit":  # #149 起盜賊有招；測試裡的「盜賊」是沒有技能的通用替身
        overrides.setdefault("skills", ())
    if "attributes" in overrides and isinstance(overrides["attributes"], dict):
        attrs = dict(t.attributes)
        attrs.update({Attribute(k): v for k, v in overrides["attributes"].items()})
        overrides["attributes"] = attrs
    merged = {**t.model_dump(), **overrides}
    if "max_hp" in overrides:  # 測試寫的 max_hp 是「最終 HP」：扣掉體質加成（Phase 3-7）
        core = library().ruleset.core
        wanted = int(overrides["max_hp"])  # type: ignore[call-overload]
        bonus = (merged["attributes"][Attribute.CON] - core.hp_con_base) * core.hp_per_con_point
        if wanted - bonus < 1:  # 基礎 HP 至少 1：體質加成扣不掉時，改用中性體質
            merged["attributes"] = {**merged["attributes"], Attribute.CON: core.hp_con_base}
            bonus = 0
        merged["max_hp"] = wanted - bonus
    return UnitTemplate.model_validate(merged)


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


def giant_template(base: str = "bandit", **overrides: object) -> UnitTemplate:
    """合成的不動巨型頭目（GB-1a，05 5.12.4）：佔 3×3、帶 ``boss`` 標籤、速度 0、預設 2000 HP
    （X10-2b ×10）。
    只放在測試裡，不進 ``content/``；**不帶** ``immovable`` 標籤（證明免疫來自佔格，不是標籤）。"""
    overrides.setdefault("tags", ("boss",))
    overrides.setdefault("speed", 0)
    overrides.setdefault("max_hp", 2000)
    return template(base, footprint=3, **overrides)


def spawn_giant(
    team: Team, pos: tuple[int, int] | None, tmpl: UnitTemplate | None = None
) -> UnitSpawn:
    """巨型單位的 ``UnitSpawn``（``pos`` 是中心格；``None``＝照起始區放）。"""
    t = giant_template() if tmpl is None else tmpl
    return UnitSpawn(template=t, weapon=library().weapons[t.weapon], team=team, position=pos)


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


def ally_mana(raw: int) -> int:
    """我方施放者實際付的法力（BAL-4c：``mana_cost_permille`` 依施放者陣營打折）。"""
    return library().ruleset.core.mana_cost(raw)


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
    """施放者範本：沒有反應規則、法力 990（X10-2b ×10）、裝備 ``skills``。"""
    ids = [s if isinstance(s, str) else s.id for s in skills]
    return template(base, reactions=[], max_mana=990, skills=ids, **overrides)


def answered(result: ResolveResult) -> ResolveResult:
    """結算暫停時（反應詢問、``copy_skill``／複合技能第二段的選目標）以預設決策（:func:`accept_all`）
    回答到不再暫停；回傳最後一次的結果。亂數走訪 ``legal_actions`` 的測試用（Phase 3F-4a：「動作 →
    位移」「擊殺 → 接下一段」的技能列出的動作沒有帶第二段，結算到第二段會暫停）。"""
    while result.pending is not None:
        result = resume(result.state, accept_all(result.state, result.pending))
    return result


def with_conduct_permille(state: BattleState, permille: int = 1000) -> BattleState:
    """回傳複本：規則包的雷電擴散（``op: conduct``）倍率改成 ``permille``‰。

    BAL-13c 起內容的擴散倍率是 500‰；測擴散「基準怎麼算」的測試用 1000‰ 的副本，讓擴散傷害
    ＝基準傷害，斷言的意義不變。"""
    rs = state.ruleset
    rules = tuple(
        rule.model_copy(
            update={
                "then": tuple(
                    o.model_copy(update={"damage_permille": permille}) if o.op == "conduct" else o
                    for o in rule.then
                )
            }
        )
        for rule in rs.interactions.rules
    )
    s = state.clone()
    s.ruleset = rs.model_copy(
        update={"interactions": rs.interactions.model_copy(update={"rules": rules})}
    )
    return s
