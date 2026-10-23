"""開新一輪：主角（起始 build ＋ 開局配點）與每一場的安排（Phase 3-5a）。

亂數一律由「一輪的種子」``Rng(seed).fork(<標籤>)`` 衍生（``fork`` 不推進父串流，所以每個標籤的
子串流只取決於種子與標籤，彼此獨立）：

- ``plan/map_types``：洗牌地圖類型，取前 ``battles`` 種（同一輪不重複）。
- ``plan/map/<i>``：第 i 場在該類型的地圖中抽一張。
- ``plan/encounter/<i>``：第 i 場的敵人選項。
- ``plan/objective/<kind>/<n>``：勝利條件輪替（Phase 3-22）——挑出第 n 場撤離（``escape``）或守點
  （``defend``）的場次；該場的地圖若不支援，改在同類型中重抽（``plan/map/<i>``）。
- ``plan/battle/<i>``：第 i 場戰鬥的種子（含 Boss 戰）。
- 升級與重骰的候選見 :mod:`trpg.roguelite.offers`（``offer/<n>``）。

**新開局**（Phase 3-24b2，06 6.27.3）：自選起始武器 ＋ 選 2 個關鍵字，從每個關鍵字的技能池（只看專屬
規則）各給 1 招 1 階起始技能：

- ``start/skill/<關鍵字>``：在池裡與武器相容、還沒選到的起始技能中抽一招；池裡沒有時，以同一個串流
  取組合器種子（指定該關鍵字，最多 ``start.composer_tries`` 個）補一招生成技能。仍湊不到就拒絕
  （:class:`ChoiceError`），前端在開局預覽中把該關鍵字標成不可選。
- ``start/weapon``、``start/keywords``：``trpg run auto`` 沒有指定時以種子抽武器與關鍵字。

以 build（``content/sim/builds.yaml``）開局的 :func:`new_run` 保留給回歸測試與模擬（開發用）；
玩家介面不提供。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

from trpg.content.battle import UnitTemplate
from trpg.content.equipment import loadout_problems, resolve_loadout
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, weapon_problem
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.state import BattleNode, BattlePlan, RunStart, RunState
from trpg.shared.rng import MASK64, Rng
from trpg.shared.types import Attribute
from trpg.skillgen.keywords import derive_keywords, is_starter_skill, keyword_pools
from trpg.skillgen.random_composer import ComposeError, compose_random_skill

__all__ = [
    "allocation_problems",
    "apply_allocation",
    "check_test_equipment",
    "default_build",
    "default_start",
    "make_plan",
    "new_dev_run",
    "new_keyword_run",
    "new_run",
    "primary_attribute",
    "start_weapons",
    "starter_pools",
    "starting_skill",
    "top_attribute",
]


def top_attribute(attributes: Mapping[Attribute, int]) -> Attribute:
    """最高的屬性；並列時取六屬性順序（力量、敏捷、體質、智力、感知、意志）的第一個。"""
    best = max(attributes[a] for a in Attribute)
    return next(a for a in Attribute if attributes[a] == best)


def primary_attribute(skills: Iterable[SkillDef], fallback: Attribute = Attribute.STR) -> Attribute:
    """技能最常用的縮放屬性（自動配點用；並列時取六屬性順序的第一個）。沒有技能時（白板主角）用
    ``fallback``，呼叫端傳武器的縮放屬性（法杖 → 智力）。"""
    counts = Counter(s.scaling_attr for s in skills)
    if not counts:
        return fallback
    best = max(counts.values())
    return next(a for a in Attribute if counts[a] == best)


def allocation_problems(allocation: Mapping[Attribute, int], points: int) -> list[str]:
    """配點的問題（中文；空串列 ＝ 合法）：每項不可為負，總和必須等於 ``points``。"""
    problems = [f"{a.display_name} 的配點不可為負：{v}" for a, v in allocation.items() if v < 0]
    total = sum(allocation.values())
    if total != points:
        problems.append(f"必須分配 {points} 點屬性，收到 {total} 點")
    return problems


def apply_allocation(hero: UnitTemplate, allocation: Mapping[Attribute, int]) -> UnitTemplate:
    attributes = {a: hero.attributes[a] + allocation.get(a, 0) for a in Attribute}
    return hero.model_copy(update={"attributes": attributes})


def default_build(library: ContentLibrary, seed: int) -> str:
    """沒有指定 build 時（``trpg run auto``）：以 ``Rng(seed).fork("build")`` 從 build 中抽一個。"""
    return Rng(seed).fork("build").choice(sorted(b.id for b in library.builds.sim_builds()))


def make_plan(library: ContentLibrary, seed: int) -> tuple[BattlePlan, ...]:
    """每一場的地圖、敵人與戰鬥種子（見模組說明）。最後一場是 Boss 戰（固定地圖）。"""
    rules = library.roguelite
    root = Rng(seed)
    pool = sorted(rules.map_pool)
    archetypes = sorted({library.map(m).archetype for m in pool})
    picked = root.fork("plan/map_types").shuffled(archetypes)[: rules.battles]
    map_ids = [
        root.fork(f"plan/map/{i}").choice([m for m in pool if library.map(m).archetype == a])
        for i, a in enumerate(picked, start=1)
    ]
    objectives = _assign_objectives(library, root, pool, picked, map_ids)
    plans: list[BattlePlan] = []
    for index, map_id in enumerate(map_ids, start=1):
        plans.append(
            BattlePlan(
                index=index,
                map_id=map_id,
                enemies=root.fork(f"plan/encounter/{index}").choice(
                    rules.encounters[index - 1].options
                ),
                seed=_battle_seed(root, index),
                objective=objectives[index - 1],
            )
        )
    boss = rules.battles + 1
    plans.append(
        BattlePlan(
            index=boss,
            map_id=rules.boss.map,
            enemies=rules.boss.enemies,
            seed=_battle_seed(root, boss),
            boss=True,
        )
    )
    return tuple(plans)


def _assign_objectives(
    library: ContentLibrary,
    root: Rng,
    pool: list[str],
    archetypes: Sequence[str],
    map_ids: list[str],
) -> list[Literal["eliminate", "escape", "defend"]]:
    """一般戰鬥的勝利條件（Phase 3-22）：先排滿撤離、再排滿守點的最少場數，其餘全滅。被選中的場次若
    原本抽到的地圖不支援該條件，在同地圖類型中改抽支援的地圖（就地修改 ``map_ids``）。"""
    rotation = library.roguelite.objective_rotation
    result: list[Literal["eliminate", "escape", "defend"]] = ["eliminate"] * len(map_ids)
    for kind, count in (("escape", rotation.min_escape), ("defend", rotation.min_defend)):
        for n in range(1, count + 1):
            supporting = [
                [
                    m
                    for m in pool
                    if library.map(m).archetype == a and library.map(m).supports_objective(kind)
                ]
                for a in archetypes
            ]
            free = [i for i, r in enumerate(result) if r == "eliminate" and supporting[i]]
            if not free:
                raise ChoiceError(f"排不出第 {n} 場 {kind}：沒有支援它的地圖類型")
            i = root.fork(f"plan/objective/{kind}/{n}").choice(free)
            if map_ids[i] not in supporting[i]:
                map_ids[i] = root.fork(f"plan/map/{i + 1}").choice(supporting[i])
            result[i] = "escape" if kind == "escape" else "defend"
    return result


def _battle_seed(root: Rng, index: int) -> int:
    return root.fork(f"plan/battle/{index}").next_u32()


def new_run(
    library: ContentLibrary,
    build_id: str,
    seed: int,
    allocation: Mapping[Attribute, int] | None = None,
) -> RunState:
    """開新一輪：主角用 build 的英雄（武器、HP、法力、行為模式、起始技能組），六項屬性皆為
    ``base_attribute`` 再加開局配點。``allocation`` 省略時全部點在技能最常用的縮放屬性
    （:func:`primary_attribute`）。不合法時拋出 :class:`ChoiceError`。"""
    if not 0 <= seed <= MASK64:
        raise ChoiceError(f"種子必須在 0～2**64−1，收到 {seed}")
    builds = library.builds.by_id()
    build = builds.get(build_id)
    if build is None:
        raise ChoiceError(f"未知的 build：{build_id}（可用：{', '.join(sorted(builds))}）")
    rules = library.roguelite
    if allocation is None:
        skills = [library.skills[s] for s in build.hero.skills]
        weapon_attr = library.weapons[build.hero.weapon].scaling_attr
        allocation = {primary_attribute(skills, weapon_attr): rules.start_free_points}
    problems = allocation_problems(allocation, rules.start_free_points)
    if problems:
        raise ChoiceError("；".join(problems))
    base = {a: rules.base_attribute for a in Attribute}
    core = library.ruleset.core
    # 範本的基礎 HP ＝ build 英雄在「體質 10」時的 HP（亦即 build 英雄以自己的體質算出的最終 HP），
    # 開局配點加體質之後才額外增加（Phase 3-7）
    authored_hp = core.template_max_hp(build.hero)
    hero = apply_allocation(
        build.hero.model_copy(update={"attributes": base, "max_hp": authored_hp}), allocation
    )
    start_hp = core.run_max_hp(hero.max_hp, hero.attributes[Attribute.CON], 1)
    return RunState(
        seed=seed,
        build_id=build_id,
        hero=hero,
        level=1,
        xp=0,
        hp=start_hp,
        mana=hero.max_mana,
        source=core.source_min_at_start,
        plan=make_plan(library, seed),
        node=BattleNode(index=1),
    )


# ---------------------------------------------------------------------------
# 新開局：起始武器 ＋ 關鍵字（Phase 3-24b2）
# ---------------------------------------------------------------------------


def start_weapons(library: ContentLibrary) -> tuple[str, ...]:
    """開局可選的武器：``weapons.yaml`` 的全部武器，不含召喚物專用的（依 ID 排序）。"""
    return tuple(sorted(w for w, d in library.weapons.items() if not d.summon_only))


def _check_seed(seed: int) -> None:
    if not 0 <= seed <= MASK64:
        raise ChoiceError(f"種子必須在 0～2**64−1，收到 {seed}")


def _weapon_class(library: ContentLibrary, weapon: str) -> str:
    found = library.weapons.get(weapon)
    if found is None:
        raise ChoiceError(f"未知的武器：{weapon}（可用：{', '.join(start_weapons(library))}）")
    return found.weapon_class


def _composed_starter(
    library: ContentLibrary, rng: Rng, keyword: str, weapon_class: str, taken: set[str]
) -> SkillDef | None:
    hint = "spell" if weapon_class == "focus" else None
    for _ in range(library.roguelite.start.composer_tries):
        try:
            skill = compose_random_skill(
                rng.next_u32(), tier=1, category=hint, library=library, keyword=keyword
            )
        except ComposeError:
            continue
        keywords = derive_keywords(skill, library.keywords, exclusive_only=True).all()
        if (
            is_starter_skill(skill)
            and keyword in keywords
            and skill.id not in taken
            and weapon_problem(skill, weapon_class) is None
        ):
            return skill
    return None


def starter_pools(library: ContentLibrary) -> dict[str, tuple[str, ...]]:
    """開局用的技能池：只看專屬規則、只列可當起始技能的（1 階、普通或稀有、主動技）。"""
    return keyword_pools(library, starter_only=True, exclusive_only=True)


def starting_skill(
    library: ContentLibrary,
    weapon: str,
    keyword: str,
    seed: int,
    *,
    taken: Iterable[str] = (),
    pools: Mapping[str, tuple[str, ...]] | None = None,
) -> SkillDef | None:
    """``keyword`` 池給的起始技能（見模組說明；``None`` ＝ 這把武器湊不到）。``pools`` 可傳入
    預先算好的 :func:`starter_pools` 以免重算。"""
    if keyword not in library.keywords.ids():
        raise ChoiceError(f"未知的關鍵字：{keyword}（可用：{', '.join(library.keywords.ids())}）")
    weapon_class = _weapon_class(library, weapon)
    pools = pools if pools is not None else starter_pools(library)
    used = set(taken)
    rng = Rng(seed).fork(f"start/skill/{keyword}")
    options = [
        library.skills[s]
        for s in pools[keyword]
        if s not in used and weapon_problem(library.skills[s], weapon_class) is None
    ]
    if options:
        return rng.choice(options)
    return _composed_starter(library, rng, keyword, weapon_class, used)


def _start_hero(library: ContentLibrary, weapon: str, skills: Sequence[str]) -> UnitTemplate:
    rules = library.roguelite
    base = rules.start.heroes[_weapon_class(library, weapon)]
    return UnitTemplate(
        id="hero",
        name_zh=base.name_zh,
        attributes={a: rules.base_attribute for a in Attribute},
        max_hp=base.max_hp,
        speed=base.speed,
        armor_bonus=base.armor_bonus,
        weapon=weapon,
        resist=dict(base.resist),
        tags=("hero",),
        max_mana=base.max_mana,
        skills=tuple(skills),
    )


def _fixed_starter(
    library: ContentLibrary,
    pools: Mapping[str, tuple[str, ...]],
    skill_id: str,
    keyword: str,
    weapon_class: str,
) -> SkillDef:
    if skill_id not in pools[keyword]:
        raise ChoiceError(f"技能 {skill_id} 不在「{keyword}」的起始技能池裡")
    skill = library.skills[skill_id]
    problem = weapon_problem(skill, weapon_class)
    if problem is not None:
        raise ChoiceError(problem)
    return skill


def _pick_starters(
    library: ContentLibrary,
    weapon: str,
    keywords: Sequence[str],
    seed: int,
    skills: Sequence[str],
) -> list[SkillDef]:
    weapon_class = _weapon_class(library, weapon)
    pools = starter_pools(library)
    picked: list[SkillDef] = []
    for index, keyword in enumerate(keywords):
        skill: SkillDef | None
        if skills:
            skill = _fixed_starter(library, pools, skills[index], keyword, weapon_class)
        else:
            skill = starting_skill(
                library, weapon, keyword, seed, taken=[s.id for s in picked], pools=pools
            )
        if skill is None:
            name = library.keywords.by_id()[keyword].name_zh
            weapon_name = library.weapons[weapon].name_zh
            raise ChoiceError(f"「{name}」沒有{weapon_name}能用的起始技能，請換一個關鍵字或武器")
        picked.append(skill)
    return picked


def new_keyword_run(
    library: ContentLibrary,
    weapon: str,
    keywords: Sequence[str],
    seed: int,
    allocation: Mapping[Attribute, int] | None = None,
    *,
    dev_pack: str | None = None,
    skills: Sequence[str] = (),
    test_mode: bool = False,
    test_equipment: Mapping[str, str] | None = None,
) -> RunState:
    """新開局（06 6.27.3）：起始武器 ＋ ``start.keywords`` 個不重複的關鍵字，每個關鍵字的池各給
    1 招（:func:`starting_skill`；``skills`` 直接指定時改用它們，但仍必須在該關鍵字的專屬起始技能池
    裡、與武器相容）。``allocation`` 省略時全部點在武器的縮放屬性。不合法時拋出
    :class:`ChoiceError`。

    ``test_mode``（Phase 3-39）：測試模式的一輪（戰後回滿）；``test_equipment`` 為挑的裝備
    （欄位 → 物品 ID，取代範本的裝備）；兩者都不影響亂數與其他規則。"""
    _check_seed(seed)
    rules = library.roguelite
    _weapon_class(library, weapon)
    equipment = dict(test_equipment or {})
    if equipment and not test_mode:
        raise ChoiceError("挑選裝備只能在測試模式使用")
    keywords = tuple(keywords)
    unknown = sorted(set(keywords) - set(library.keywords.ids()))
    if unknown:
        raise ChoiceError(f"未知的關鍵字：{', '.join(unknown)}")
    if len(keywords) != rules.start.keywords or len(set(keywords)) != len(keywords):
        raise ChoiceError(f"必須選 {rules.start.keywords} 個不同的關鍵字，收到 {list(keywords)}")
    if allocation is None:
        allocation = {library.weapons[weapon].scaling_attr: rules.start_free_points}
    problems = allocation_problems(allocation, rules.start_free_points)
    if problems:
        raise ChoiceError("；".join(problems))
    check_test_equipment(library, weapon, equipment)
    picked = _pick_starters(library, weapon, keywords, seed, skills)
    hero = apply_allocation(_start_hero(library, weapon, [s.id for s in picked]), allocation)
    core = library.ruleset.core
    generated = sorted((s for s in picked if s.id not in library.skills), key=lambda s: s.id)
    return RunState(
        seed=seed,
        start=RunStart(weapon=weapon, keywords=keywords, dev_pack=dev_pack),
        hero=hero,
        level=1,
        xp=0,
        hp=core.run_max_hp(hero.max_hp, hero.attributes[Attribute.CON], 1),
        mana=hero.max_mana,
        source=core.source_min_at_start,
        generated_skills=tuple(generated),
        plan=make_plan(library, seed),
        node=BattleNode(index=1),
        test_mode=test_mode,
        test_equipment=equipment,
    )


def check_test_equipment(
    library: ContentLibrary, weapon: str, equipment: Mapping[str, str]
) -> None:
    """測試模式挑的裝備不合法時拋出 :class:`ChoiceError`（中文，多個原因以「；」連接）：未知的欄位
    或物品，以及穿戴規則（種類、占用、同一枚戒指、代價型條數、主手武器必須是起始武器）。"""
    if not equipment:
        return
    try:
        loadout = resolve_loadout(equipment, library.items, library.affixes)
    except ValueError as exc:
        raise ChoiceError(str(exc)) from exc
    problems = loadout_problems(loadout, library.weapons[weapon], library.ruleset.equipment)
    if problems:
        raise ChoiceError("；".join(problems))


def new_dev_run(
    library: ContentLibrary,
    pack_id: str,
    seed: int,
    allocation: Mapping[Attribute, int] | None = None,
) -> RunState:
    """以開發者起始包開局（06 6.27.6；開發用）：武器與關鍵字取自 ``dev_starters.yaml``。"""
    packs = library.dev_starters.by_id()
    pack = packs.get(pack_id)
    if pack is None:
        raise ChoiceError(f"未知的開發者起始包：{pack_id}（可用：{', '.join(sorted(packs))}）")
    return new_keyword_run(
        library,
        pack.weapon,
        pack.keywords,
        seed,
        allocation,
        dev_pack=pack.id,
        skills=pack.skills,
    )


def default_start(library: ContentLibrary, seed: int) -> tuple[str, tuple[str, ...]]:
    """沒有指定開局時（``trpg run auto``、模擬抽樣）：以種子抽武器（``start/weapon``），再從這把武器
    的池裡有相容起始技能的關鍵字中抽 ``start.keywords`` 個（``start/keywords``）。"""
    root = Rng(seed)
    weapon = root.fork("start/weapon").choice(start_weapons(library))
    weapon_class = library.weapons[weapon].weapon_class
    pools = starter_pools(library)
    usable = [
        k
        for k in library.keywords.ids()
        if any(weapon_problem(library.skills[s], weapon_class) is None for s in pools[k])
    ]
    count = library.roguelite.start.keywords
    return weapon, tuple(root.fork("start/keywords").shuffled(usable)[:count])
