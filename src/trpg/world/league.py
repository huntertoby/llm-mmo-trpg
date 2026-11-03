"""影子循環賽（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36；09 9.7「季末保底」）。

- **報名**（:func:`enter_league`、:func:`withdraw_league`）：在城鎮把目前的 build 存成快照
  （:func:`~trpg.world.shadows.shadow_snapshot`）＋AI 打法；每個帳號 1 個角色（#100）；賽季第
  ``signup_close_day`` 天之後不能報名、更新、取消（#101）。
- **拉到等級上限**（:func:`leveled_snapshot`；9.7「全員拉到等級上限、屬性點重新分配；技能照常受
  預算上限約束」）：等級＝上限；新增的屬性點照開局自動配點補（已分配的不動，代決 5F4-2）；技能照
  上限的角色階級重配。
- **賽程**（:func:`league_schedule`）：每對組合 × 地圖 × 種子 × 交換先後手；種子由賽季種子衍生。
- **對戰**（:func:`match_setup`、:func:`play_match`）：1 對 1，雙方都由效用 AI 操作，
  ``max_rounds`` 保證結束（到上限＝和局）。

純函式：不讀時間、不呼叫 LLM；亂數只來自對戰的種子。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.world_season import LeagueRules
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.gear.core import build_gear, geared_template
from trpg.engine.runner import BattleRun, run_battle
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup, with_phase_assets
from trpg.engine.state import BattleState
from trpg.roguelite.offers import at_run_tier
from trpg.roguelite.start import allocation_problems, default_allocation, primary_attribute
from trpg.shared.rng import fnv1a64
from trpg.shared.types import Attribute, Team
from trpg.world.calendar import season_day
from trpg.world.common import here, rules_of
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.growth import hero_tier
from trpg.world.league_actions import (
    LeagueEnterAction,
    LeagueEnteredEvent,
    LeagueWithdrawAction,
    LeagueWithdrawnEvent,
)
from trpg.world.shadows import shadow_snapshot, shadow_spawn
from trpg.world.state import CharacterState, LeagueEntry, ShadowSnapshot, WorldState

__all__ = [
    "LeagueMatchSpec",
    "LeagueSpawn",
    "allocation_problem",
    "enter_league",
    "entry_spawn",
    "league_auto_allocation",
    "league_base_attributes",
    "league_point_pool",
    "league_rules",
    "league_schedule",
    "league_spawns",
    "league_step",
    "league_unit",
    "leveled_snapshot",
    "match_loser",
    "match_seed",
    "match_setup",
    "match_winner",
    "matches_per_pair",
    "play_match",
    "signup_problem",
    "withdraw_league",
]

PERMILLE = 1000

# ---------------------------------------------------------------------------
# 報名
# ---------------------------------------------------------------------------


def league_rules(library: ContentLibrary) -> LeagueRules | None:
    """這一季的循環賽規則（``season.yaml`` 的 ``league:``；沒有＝``None``）。"""
    season = library.world_season
    return None if season is None else season.league


def _require_rules(library: ContentLibrary) -> LeagueRules:
    rules = league_rules(library)
    if rules is None:
        raise WorldActionError("這一季沒有影子循環賽")
    return rules


def signup_problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> str | None:
    """現在不能報名、更新、取消的理由（中文）；可以時 ``None``。"""
    rules = league_rules(library)
    if rules is None:
        return "這一季沒有影子循環賽"
    if season_day(library, world, now) > rules.signup_close_day:
        return f"報名已截止（第 {rules.signup_close_day} 天截止）"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if char.pending_flash is not None or char.pending_offers:
        return "還有沒選的技能"
    if here(library, char).kind != "town":
        return "要在城鎮報名"
    return None


def _with_entries(world: WorldState, entries: Sequence[LeagueEntry]) -> WorldState:
    ordered = tuple(sorted(entries, key=lambda e: e.account))
    return world.model_copy(update={"league_entries": ordered})


def enter_league(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: LeagueEnterAction,
    now: int,
    *,
    actor: str,
) -> tuple[WorldState, LeagueEnteredEvent]:
    """``league_enter``：報名或更新（同一個角色）；同帳號已用別的角色報名 → 錯誤。"""
    problem = signup_problem(library, world, char, now)
    if problem is not None:
        raise WorldActionError(f"不能報名循環賽：{problem}")
    choices = () if library.world_mercenaries is None else library.world_mercenaries.ai_choices
    if action.ai is not None and action.ai not in choices:
        raise WorldActionError(f"沒有這種打法：{action.ai}")
    old = next((e for e in world.league_entries if e.account == actor), None)
    if old is not None and old.character_id != char.character_id:
        raise WorldActionError(f"這個帳號已經用「{old.name}」報名了，先取消報名")
    taken = next((e for e in world.league_entries if e.character_id == char.character_id), None)
    if taken is not None and taken.account != actor:
        raise WorldActionError("這個角色已經由別的帳號報名")
    snapshot = shadow_snapshot(char, now)
    allocation = None
    if action.allocation is not None:
        bad = allocation_problem(library, snapshot, action.allocation)
        if bad is not None:
            raise WorldActionError(f"循環賽的配點不合法：{bad}")
        allocation = {a: action.allocation[a] for a in Attribute if action.allocation.get(a)}
    entry = LeagueEntry(
        account=actor,
        character_id=char.character_id,
        name=char.hero.name_zh,
        snapshot=snapshot,
        ai=action.ai,
        allocation=allocation,
        entered_at=now if old is None else old.entered_at,
    )
    kept = [e for e in world.league_entries if e.account != actor]
    world = _with_entries(world, [*kept, entry])
    return world, LeagueEnteredEvent(ai=action.ai, updated=old is not None)


def withdraw_league(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    actor: str,
) -> tuple[WorldState, LeagueWithdrawnEvent]:
    """``league_withdraw``：取消這個角色的報名（截止前）。"""
    rules = _require_rules(library)
    if season_day(library, world, now) > rules.signup_close_day:
        raise WorldActionError(f"報名已截止（第 {rules.signup_close_day} 天截止），不能取消")
    kept = [
        e
        for e in world.league_entries
        if not (e.account == actor and e.character_id == char.character_id)
    ]
    if len(kept) == len(world.league_entries):
        raise WorldActionError("這個角色沒有報名循環賽")
    return _with_entries(world, kept), LeagueWithdrawnEvent()


def league_step(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: LeagueEnterAction | LeagueWithdrawAction,
    now: int,
    *,
    actor: str,
) -> tuple[WorldState, CharacterState, tuple[LeagueEnteredEvent | LeagueWithdrawnEvent, ...]]:
    """循環賽的世界動作（角色不變）。"""
    if isinstance(action, LeagueEnterAction):
        world, entered = enter_league(library, world, char, action, now, actor=actor)
        return world, char, (entered,)
    world, withdrawn = withdraw_league(library, world, char, now, actor=actor)
    return world, char, (withdrawn,)


# ---------------------------------------------------------------------------
# 拉到等級上限
# ---------------------------------------------------------------------------


def _skill_def(library: ContentLibrary, snapshot: ShadowSnapshot, skill_id: str) -> SkillDef:
    generated = {s.id: s for s in snapshot.skills}
    found = generated.get(skill_id) or library.skills.get(skill_id)
    if found is None:
        raise WorldError(f"參賽快照的技能 {skill_id} 不在內容庫也不在快照裡")
    return found


def _new_points(library: ContentLibrary, snapshot: ShadowSnapshot) -> int:
    """拉到上限時新增的屬性點（升到上限多出的＋快照未分配的）。"""
    level = max(rules_of(library).hero_growth.level_cap, snapshot.level)
    per_level = library.roguelite.attribute_points_per_level
    return snapshot.attribute_points + per_level * (level - snapshot.level)


def league_point_pool(library: ContentLibrary, snapshot: ShadowSnapshot) -> int:
    """（5F-4b，#32）報名時可以重新分配的屬性點：已分配的＋未分配的＋升到上限多出的。"""
    return sum(snapshot.attribute_spent.values()) + _new_points(library, snapshot)


def league_base_attributes(snapshot: ShadowSnapshot) -> dict[Attribute, int]:
    """重新分配前的基礎屬性（快照的屬性扣掉已分配的點）。"""
    hero = snapshot.hero
    return {a: hero.attributes.get(a, 0) - snapshot.attribute_spent.get(a, 0) for a in Attribute}


def league_auto_allocation(
    library: ContentLibrary, snapshot: ShadowSnapshot
) -> dict[Attribute, int]:
    """不自己配時的配點（相對 :func:`league_base_attributes`）：已分配的不動＋新增的點照開局自動
    配點補到主屬性（代決 5F4-2）。"""
    points = _new_points(library, snapshot)
    hero = snapshot.hero
    weapon = library.weapons[hero.weapon]
    equipped = [_skill_def(library, snapshot, s) for s in hero.skills]
    main = primary_attribute(equipped, weapon.scaling_attr)
    added: Mapping[Attribute, int] = default_allocation(main, weapon, points) if points > 0 else {}
    total = {a: snapshot.attribute_spent.get(a, 0) + added.get(a, 0) for a in Attribute}
    return {a: v for a, v in total.items() if v}


def allocation_problem(
    library: ContentLibrary, snapshot: ShadowSnapshot, allocation: Mapping[Attribute, int]
) -> str | None:
    """報名的重新配點不合法的理由（中文）；合法時 ``None``。"""
    problems = allocation_problems(allocation, league_point_pool(library, snapshot))
    return "；".join(problems) if problems else None


def leveled_snapshot(
    library: ContentLibrary,
    snapshot: ShadowSnapshot,
    allocation: Mapping[Attribute, int] | None = None,
) -> ShadowSnapshot:
    """拉到等級上限的快照（見模組說明；代決 5F4-2、5F4-3）。已在上限時只重配技能（相同時原樣）。
    ``allocation``（5F-4b，#32）：報名時的重新配點（全部可配的點）；``None``＝自動配點。"""
    cap = rules_of(library).hero_growth.level_cap
    level = max(cap, snapshot.level)
    tier = hero_tier(library, level)
    hero = snapshot.hero
    # 技能照上限的角色階級重配（往上或往下）
    rename: dict[str, str] = {}
    defs: dict[str, SkillDef] = {}
    for skill_id in hero.skills:
        skill = at_run_tier(library, _skill_def(library, snapshot, skill_id), tier)
        rename[skill_id] = skill.id
        if library.skills.get(skill.id) != skill:
            defs[skill.id] = skill
    spent = league_auto_allocation(library, snapshot) if allocation is None else dict(allocation)
    base = league_base_attributes(snapshot)
    attributes = {a: base[a] + spent.get(a, 0) for a in Attribute}
    update: dict[str, object] = {
        "attributes": attributes,
        "skills": tuple(rename[s] for s in hero.skills),
    }
    if hero.reactions is not None:
        update["reactions"] = tuple(
            r.model_copy(update={"reaction": rename.get(r.reaction, r.reaction)})
            for r in hero.reactions
        )
    return snapshot.model_copy(
        update={
            "hero": hero.model_copy(update=update),
            "level": level,
            "skill_tier": tier,
            "attribute_points": 0,
            "attribute_spent": {a: spent[a] for a in Attribute if spent.get(a)},
            "skills": tuple(defs[k] for k in sorted(defs)),
        }
    )


# ---------------------------------------------------------------------------
# 賽程
# ---------------------------------------------------------------------------


class LeagueMatchSpec(BaseModel):
    """賽程裡的一場（:func:`league_schedule`）。``a``、``b`` 是帳號（``a < b``）；``ally`` 是站
    我方、先手的那位。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^m[0-9]{4,}$")
    a: str
    b: str
    map: str
    seed_index: int = Field(ge=0)
    seed: int = Field(ge=0)
    ally: str

    @property
    def enemy(self) -> str:
        return self.b if self.ally == self.a else self.a


def matches_per_pair(rules: LeagueRules) -> int:
    """每對組合打幾場（地圖 × 種子 × 交換先後手）。"""
    return len(rules.maps) * rules.seeds * 2


def match_seed(season_seed: int, a: str, b: str, map_id: str, index: int) -> int:
    """一對組合在一張地圖的第 ``index`` 個種子（交換先後手的兩場共用）。"""
    return fnv1a64(f"{season_seed}:league:{a}:{b}:{map_id}:{index}".encode())


def league_schedule(
    rules: LeagueRules, season_seed: int, entries: Sequence[LeagueEntry]
) -> tuple[LeagueMatchSpec, ...]:
    """全部場次（依帳號排序的 ``i < j`` 組合 × 地圖 × 種子 × 先後手；編號 ``m0001`` 起）。"""
    accounts = sorted(e.account for e in entries)
    specs: list[LeagueMatchSpec] = []
    for i, a in enumerate(accounts):
        for b in accounts[i + 1 :]:
            for map_id in rules.maps:
                for index in range(rules.seeds):
                    seed = match_seed(season_seed, a, b, map_id, index)
                    for ally in (a, b):
                        specs.append(
                            LeagueMatchSpec(
                                id=f"m{len(specs) + 1:04d}",
                                a=a,
                                b=b,
                                map=map_id,
                                seed_index=index,
                                seed=seed,
                                ally=ally,
                            )
                        )
    return tuple(specs)


# ---------------------------------------------------------------------------
# 對戰
# ---------------------------------------------------------------------------


type LeagueSpawn = tuple[UnitSpawn, tuple[SkillDef, ...]]
"""一位參賽者拉到上限後的出場設定（我方）與要加進規則包的技能。"""


def entry_spawn(library: ContentLibrary, entry: LeagueEntry) -> LeagueSpawn:
    """參賽者拉到等級上限後的出場設定（:func:`leveled_snapshot` ＋ 影子的 :func:`shadow_spawn`；
    AI 打法＝報名的打法，沒有＝快照的預設）。"""
    leveled = leveled_snapshot(library, entry.snapshot, entry.allocation)
    return shadow_spawn(library, leveled, leveled.level, entry.ai)


def league_spawns(
    library: ContentLibrary, entries: Sequence[LeagueEntry]
) -> dict[str, LeagueSpawn]:
    """每位參賽者（帳號 → 出場設定）；整個賽程共用，技能重配只算一次。"""
    return {e.account: entry_spawn(library, e) for e in entries}


def match_setup(
    library: ContentLibrary,
    rules: LeagueRules,
    spawns: Mapping[str, LeagueSpawn],
    spec: LeagueMatchSpec,
) -> BattleSetup:
    """一場的戰鬥設定：地圖（照地圖天氣）、``max_rounds``、我方＝``spec.ally``（先手）、敵方＝另一位。"""
    ally, ally_skills = spawns[spec.ally]
    enemy, enemy_skills = spawns[spec.enemy]
    extra = {s.id: s for s in (*ally_skills, *enemy_skills)}
    base = build_setup(
        library,
        spec.map,
        library.roguelite.companions,  # 只借用設定的骨架；單位在下面整組換掉
        (),
        max_rounds=rules.max_rounds,
    )
    setup = base.model_copy(
        update={
            "ruleset": library.ruleset.with_skills(extra[k] for k in sorted(extra)),
            "units": (
                league_unit(library, rules, ally, Team.ALLY, first=True),
                league_unit(library, rules, enemy, Team.ENEMY, first=False),
            ),
            "first_team": Team.ALLY,
        }
    )
    return with_phase_assets(library, setup)


def league_unit(
    library: ContentLibrary, rules: LeagueRules, spawn: UnitSpawn, team: Team, *, first: bool
) -> UnitSpawn:
    """循環賽的出場單位（5F-4b，只套在循環賽）：陣營、開場最大 HP 倍率（``hp_permille``；裝備與
    體質算完之後的最大 HP 乘倍率，無條件捨去）、開場狀態（雙方的 ``opening_statuses``＋先手的
    ``first_opening_statuses``，接在單位原有的開場狀態後面）。"""
    update: dict[str, object] = {"team": team}
    if rules.hp_permille != PERMILLE:
        ruleset = library.ruleset
        gear = build_gear(spawn.equipment, ruleset.equipment)
        full = ruleset.core.template_max_hp(geared_template(spawn.template, gear, ruleset))
        bonus = full * (rules.hp_permille - PERMILLE) // PERMILLE
        template = spawn.template
        update["template"] = template.model_copy(update={"max_hp": template.max_hp + bonus})
    statuses = (*rules.opening_statuses, *(rules.first_opening_statuses if first else ()))
    if statuses:
        update["opening_statuses"] = (*spawn.opening_statuses, *statuses)
    return spawn.model_copy(update=update)


def play_match(library: ContentLibrary, setup: BattleSetup, seed: int) -> BattleRun:
    """雙方都由效用 AI 操作，跑到結束（同 :func:`~trpg.world.battle.auto_steps` 的 AI）。"""
    policy = CommandedAI(UtilityAI(library.ai_profiles), {})
    return run_battle(setup, seed, policy)


def match_winner(state: BattleState, spec: LeagueMatchSpec) -> str | None:
    """贏的帳號；和局（到輪數上限、同時倒下）＝``None``。"""
    if state.winner is Team.ALLY:
        return spec.ally
    if state.winner is Team.ENEMY:
        return spec.enemy
    return None


def match_loser(spec: LeagueMatchSpec, winner: str | None) -> str | None:
    if winner is None:
        return None
    return spec.b if winner == spec.a else spec.a
