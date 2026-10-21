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
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.state import BattleNode, BattlePlan, RunState
from trpg.shared.rng import MASK64, Rng
from trpg.shared.types import Attribute

__all__ = [
    "allocation_problems",
    "apply_allocation",
    "default_build",
    "make_plan",
    "new_run",
    "primary_attribute",
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
