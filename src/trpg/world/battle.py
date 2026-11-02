"""遇敵展開戰鬥與勝負回寫（Phase 5A-4；``docs/phases/Phase5計畫.md`` 8.3～8.5）。

- :func:`prepare_battle`：由角色身上的遭遇（:class:`~trpg.world.state.EncounterResult`）組出原型戰鬥
  引擎的設定——地點的地圖（沒有時從區域地圖池抽）並換皮成遭遇的區域、遭遇的天氣、主角（目前 HP、
  法力、耐力；疲憊時開場 HP 打折）＋原型的標準隊友、依地點建議等級成長的敵方陣容。API 開戰與「看
  陣容」直接用它（5A-5）。
- :func:`fight`：``fight`` 動作——用同一份設定與 ``battle_seed`` 開戰、依序套用日誌裡的步驟，戰鬥
  結束後回寫角色與世界（經驗、耐力、已清空、全滅回小鎮＋疲憊）。重播照同樣的步驟重算，結果逐位元
  相同（第 2.4 節）。
- :func:`grow_enemy`：敵人依等級成長（追加 A：和主角同樣，每級屬性 +2、HP +5%，技能階級照 07 7.6；
  範本＝1 級基準）。

確定性：亂數只來自 ``battle_seed``（地圖 ``"{battle_seed}:map"``、陣容 ``"{battle_seed}:lineup"``、
戰鬥本身）；不讀時間、不呼叫 LLM。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.maps import MapDef
from trpg.content.regions import RegionDef
from trpg.content.skills import SkillDef
from trpg.engine.actions import Step
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.results import battle_result
from trpg.engine.runner import advance, apply_step
from trpg.engine.setup import BattleSetup, UnitSpawn, build_setup
from trpg.engine.state import BattleState
from trpg.roguelite.offers import at_run_tier
from trpg.roguelite.progress import hero_unit_id, level_for
from trpg.shared.errors import TrpgError
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Attribute, Team
from trpg.world.actions import (
    BattleEndedEvent,
    BattleStartedEvent,
    DefeatedEvent,
    FightAction,
    LeveledUpEvent,
    LocationClearedEvent,
    WorldEvent,
)
from trpg.world.common import max_hp, max_mana, rules_of, world_map_of
from trpg.world.encounters import EncounterLineup, lineup_templates, roll_lineup
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.state import CharacterState, ClearedLocation, EncounterResult, WorldState

__all__ = [
    "PreparedBattle",
    "auto_steps",
    "encounter_map",
    "enemy_level",
    "fight",
    "grow_enemy",
    "hero_start_hp",
    "prepare_battle",
    "reskin",
    "with_cleared",
]


@dataclass(frozen=True)
class PreparedBattle:
    """一場遭遇的戰鬥：引擎設定、種子、敵方陣容與等級、主角開場 HP。"""

    setup: BattleSetup
    seed: int
    lineup: EncounterLineup
    enemy_level: int
    hero_hp: int


# ---------------------------------------------------------------------------
# 地圖
# ---------------------------------------------------------------------------


def encounter_map(library: ContentLibrary, encounter: EncounterResult) -> MapDef:
    """遭遇的戰鬥地圖（已換皮成遭遇的區域）。``battle_map`` 為 ``None`` 時從該區 ``map_pool`` 的
    類型裡（不含 Boss）依地圖 ID 排序、以 ``"{battle_seed}:map"`` 均勻抽一張（代決 5A4-1）。"""
    if encounter.battle_map is not None:
        map_def = library.map(encounter.battle_map)
    else:
        pool = set(_region_def(library, encounter.region).map_pool) - {"boss"}
        options = sorted(m for m, d in library.maps.items() if d.archetype in pool)
        if not options:
            raise WorldError(f"區域 {encounter.region} 的地圖池沒有地圖")
        rng = Rng(fnv1a64(f"{encounter.battle_seed}:map".encode()))
        map_def = library.maps[options[rng.randint(0, len(options) - 1)]]
    return reskin(library, map_def, encounter.region)


def _region_def(library: ContentLibrary, region: str) -> RegionDef:
    if library.regions is None:
        raise WorldError("內容庫沒有 regions.yaml")
    found = library.regions.region_by_id().get(region)
    if found is None:
        raise WorldError(f"regions.yaml 沒有區域 {region}")
    return found


def reskin(library: ContentLibrary, map_def: MapDef, region: str) -> MapDef:
    """地圖換成 ``region`` 的外觀（05 5.1：機制不動，只換 ``region``）；``look`` 換成該區的預設外觀
    （原本的單張覆寫是給原區的，代決 5A4-2）。已經是該區時原樣回傳。"""
    if map_def.region == region:
        return map_def
    look = dict(_region_def(library, region).look)
    return map_def.model_copy(update={"region": region, "look": look})


# ---------------------------------------------------------------------------
# 敵人成長（追加 A）
# ---------------------------------------------------------------------------


def enemy_level(library: ContentLibrary, encounter: EncounterResult) -> int:
    """敵人的等級：遭遇地點建議等級的 ``level_min``（代決 5A4-5）。"""
    location = world_map_of(library, encounter.region).location_by_id().get(encounter.location)
    if location is None or location.level_min is None:
        return encounter.level
    return location.level_min


def grow_enemy(
    library: ContentLibrary, template: UnitTemplate, level: int
) -> tuple[UnitTemplate, tuple[SkillDef, ...]]:
    """``template``（1 級基準）成長到 ``level``；回傳成長後的範本與要加進規則包的重配技能。

    - 屬性：每級 ``attribute_points_per_level``，全部加在範本最高的屬性（同分取 str、dex、con、
      int、wis、wil 的第一個；代決 5A4-6）。
    - HP：基礎 HP ＋ ``level_hp_bonus``（同主角，每級 +5% 基礎 HP）。
    - 技能：階級低於 ``skill_tier_by_level[等級]`` 的照 roguelite ``at_run_tier`` 重配成
      ``<原 ID>_t<階級>``（只升不降），反應規則引用的 ID 一併改名。
    - ``level`` 欄位＝等級（召喚物依施放者等級成長）。
    """
    if level <= 1:
        return template, ()
    growth = rules_of(library).enemy_growth
    core = library.ruleset.core
    attributes = dict(template.attributes)
    best = max(attributes.get(a, 0) for a in Attribute)
    top = next(a for a in Attribute if attributes.get(a, 0) == best)
    attributes[top] = best + growth.attribute_points_per_level * (level - 1)
    tier = growth.tier_for(level)
    rename: dict[str, str] = {}
    extra: dict[str, SkillDef] = {}
    for skill_id in template.skills:
        skill = library.skills[skill_id]
        if skill.tier >= tier:
            continue
        done = at_run_tier(library, skill, tier)
        rename[skill_id] = done.id
        extra[done.id] = done
    update: dict[str, object] = {
        "attributes": attributes,
        "max_hp": template.max_hp + core.level_hp_bonus(template.max_hp, level),
        "skills": tuple(rename.get(s, s) for s in template.skills),
        "level": level,
    }
    if template.reactions is not None:
        update["reactions"] = tuple(
            r.model_copy(update={"reaction": rename[r.reaction]}) if r.reaction in rename else r
            for r in template.reactions
        )
    grown = template.model_copy(update=update)
    return grown, tuple(extra[k] for k in sorted(extra))


# ---------------------------------------------------------------------------
# 開戰設定
# ---------------------------------------------------------------------------


def hero_start_hp(library: ContentLibrary, char: CharacterState) -> int:
    """主角開場 HP：目前 HP（至少 1）；疲憊時不超過最大 HP × ``fatigue_hp_permille``‰（#98）。"""
    hp = max(1, char.hp)
    if char.fatigued:
        cap = max_hp(library, char) * rules_of(library).battle.fatigue_hp_permille // 1000
        hp = min(hp, max(1, cap))
    return hp


def _hero_spawn(library: ContentLibrary, char: CharacterState, hp: int) -> UnitSpawn:
    """主角的出場設定（同 roguelite ``hero_spawn``：等級加成併入基礎 HP，體質由引擎加）。"""
    core = library.ruleset.core
    hero = char.hero
    leveled = hero.model_copy(
        update={
            "max_hp": hero.max_hp + core.level_hp_bonus(hero.max_hp, char.level),
            "scaled_resources": True,
            "level": char.level,
        }
    )
    return UnitSpawn(
        template=leveled,
        weapon=library.weapons[hero.weapon],
        equipment=library.loadout_of(hero),
        team=Team.ALLY,
        hp=hp,
        mana=char.mana,
        stamina=char.stamina,
    )


def prepare_battle(library: ContentLibrary, char: CharacterState) -> PreparedBattle:
    """角色身上遭遇的戰鬥設定（見模組說明）；沒有遭遇時拋 :class:`WorldActionError`。"""
    encounter = char.pending_encounter
    if encounter is None:
        raise WorldActionError("目前沒有遭遇")
    map_def = encounter_map(library, encounter)
    lineup = roll_lineup(library, encounter)
    level = enemy_level(library, encounter)
    enemies: list[UnitSpawn] = []
    extra: dict[str, SkillDef] = {}
    for template in lineup_templates(library, lineup):
        grown, skills = grow_enemy(library, template, level)
        extra.update((s.id, s) for s in skills)
        enemies.append(
            UnitSpawn(
                template=grown,
                weapon=library.weapon_of(grown),
                equipment=library.loadout_of(grown),
                team=Team.ENEMY,
            )
        )
    base = build_setup(
        library,
        map_def.id,
        library.roguelite.companions,  # 5C-1 前用原型的標準隊友（代決 5A4-4）
        (),
        max_rounds=rules_of(library).battle.max_rounds,
        weather=encounter.weather,
    )
    hp = hero_start_hp(library, char)
    ruleset = library.ruleset.with_skills(extra[k] for k in sorted(extra))
    setup = base.model_copy(
        update={
            "map": map_def,
            "ruleset": ruleset,
            "units": (_hero_spawn(library, char, hp), *base.units, *enemies),
        }
    )
    return PreparedBattle(
        setup=setup, seed=encounter.battle_seed, lineup=lineup, enemy_level=level, hero_hp=hp
    )


def auto_steps(library: ContentLibrary, char: CharacterState) -> tuple[Step, ...]:
    """效用 AI 代打整場（主角也由 AI 操作），回傳步驟（測試、smoke 與模擬用）。"""
    prepared = prepare_battle(library, char)
    opening = begin_battle(prepared.setup, prepared.seed)
    policy = CommandedAI(UtilityAI(library.ai_profiles), {})
    steps: list[Step] = []

    def on_step(step: Step | None, _result: object) -> None:
        assert step is not None
        steps.append(step)

    advance(opening.state, opening.pending, policy, on_step=on_step)
    return tuple(steps)


# ---------------------------------------------------------------------------
# 戰鬥與回寫
# ---------------------------------------------------------------------------


def _run(prepared: PreparedBattle, steps: Sequence[Step]) -> BattleState:
    state = begin_battle(prepared.setup, prepared.seed).state
    for number, step in enumerate(steps, start=1):
        try:
            state = apply_step(state, step).state
        except TrpgError as exc:
            raise WorldActionError(f"戰鬥的第 {number} 步無法套用：{exc}") from exc
    if not state.ended:
        raise WorldActionError("戰鬥還沒結束")
    return state


def with_cleared(world: WorldState, region: str, location: str, respawn_at: int) -> WorldState:
    """把地點寫成「已清空」到 ``respawn_at``（已有就更新；依區域、地點排序）。"""
    kept = [c for c in world.cleared if (c.region, c.location) != (region, location)]
    kept.append(ClearedLocation(region=region, location=location, respawn_at=respawn_at))
    kept.sort(key=lambda c: (c.region, c.location))
    return world.model_copy(update={"cleared": tuple(kept)})


def fight(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: FightAction,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """``fight`` 動作（見模組說明）。"""
    prepared = prepare_battle(library, char)
    encounter = char.pending_encounter
    assert encounter is not None
    state = _run(prepared, action.steps)
    events: list[WorldEvent] = [
        BattleStartedEvent(
            location=encounter.location,
            battle_map=prepared.setup.map.id,
            region=encounter.region,
            lineup=prepared.lineup,
            enemy_level=prepared.enemy_level,
            weather=encounter.weather,
            hero_hp=prepared.hero_hp,
            fatigued=char.fatigued,
        )
    ]
    result = battle_result(state)
    hero = result.ally(hero_unit_id(state))
    assert hero is not None
    if result.winner is Team.ALLY:
        world, char, more = _won(
            library, world, char, encounter, hp=hero.hp, mana=hero.mana, now=now
        )
    else:
        char, more = _lost(library, char, hero.mana)
    ended = BattleEndedEvent(
        won=result.winner is Team.ALLY,
        end_reason=result.end_reason,
        rounds=result.round,
        hp=char.hp,
        mana=char.mana,
        xp_gained=rules_of(library).battle.xp_per_battle if result.winner is Team.ALLY else 0,
        level=char.level,
    )
    return world, char, (*events, ended, *more)


def _won(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    encounter: EncounterResult,
    *,
    hp: int,
    mana: int,
    now: int,
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    """打贏：HP 照戰後（倒下以 1 HP 繼續）、法力不回、耐力回滿（#113）；經驗與升級；已清空。"""
    rules = rules_of(library).battle
    events: list[WorldEvent] = []
    xp = char.xp + rules.xp_per_battle
    char = char.model_copy(
        update={
            "hp": max(1, hp),
            "mana": mana,
            "stamina": None,
            "xp": xp,
            "fatigued": False,
            "pending_encounter": None,
        }
    )
    target = level_for(library, xp)
    while char.level < target:
        before_hp, before_mana = max_hp(library, char), max_mana(library, char)
        leveled = char.model_copy(
            update={
                "level": char.level + 1,
                "attribute_points": char.attribute_points
                + library.roguelite.attribute_points_per_level,
            }
        )
        char = leveled.model_copy(
            update={
                "hp": max(1, leveled.hp + max_hp(library, leveled) - before_hp),
                "mana": max(0, leveled.mana + max_mana(library, leveled) - before_mana),
            }
        )
        events.append(LeveledUpEvent(level=char.level, attribute_points=char.attribute_points))
    kind = world_map_of(library, encounter.region).location_by_id()[encounter.location].kind
    if kind in rules.clear_kinds:
        respawn_at = now + rules.respawn_seconds
        world = with_cleared(world, encounter.region, encounter.location, respawn_at)
        events.append(LocationClearedEvent(location=encounter.location, respawn_at=respawn_at))
    return world, char, events


def _lost(
    library: ContentLibrary, char: CharacterState, mana: int
) -> tuple[CharacterState, list[WorldEvent]]:
    """全滅（含輪數上限，代決 5A4-7）：回本區小鎮、HP 回滿、耐力回滿、法力照戰後；不給也不扣經驗；
    下一場疲憊（9.6.9 #98；代決 5A4-8）。"""
    town = world_map_of(library, char.region).town
    char = char.model_copy(
        update={
            "location": town,
            "mana": mana,
            "stamina": None,
            "fatigued": True,
            "pending_encounter": None,
            "camped_at": None,
        }
    )
    char = char.model_copy(update={"hp": max_hp(library, char)})
    return char, [DefeatedEvent(location=town, hp=char.hp)]
