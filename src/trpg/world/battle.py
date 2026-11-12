"""遇敵展開戰鬥與勝負回寫（Phase 5A-4；``docs/phases/Phase5計畫.md`` 9.3～8.5）。

- :func:`prepare_battle`：由角色身上的遭遇（:class:`~trpg.world.state.EncounterResult`）組出原型戰鬥
  引擎的設定——地點的地圖（沒有時從區域地圖池抽）並換皮成遭遇的區域、遭遇的天氣、主角（目前 HP、
  法力、耐力；疲憊時開場 HP 打折）＋隊伍的傭兵（5C-1）與借來的影子（5C-2；沒有隊友＝獨行）、依地點
  建議等級成長的敵方陣容。API 開戰與「看陣容」直接用它（5A-5）。遭遇是賽季 Boss 時轉給
  :func:`prepare_season_boss_battle`（5F-R2：兩者只共用主角與傭兵的出場設定）。
- :func:`fight`：``fight`` 動作——用同一份設定與 ``battle_seed`` 開戰、依序套用日誌裡的步驟，戰鬥
  結束後回寫角色與世界（經驗、耐力、已清空、全滅回小鎮＋疲憊）。重播照同樣的步驟重算，結果逐位元
  相同（第 2.4 節）。
- :func:`grow_enemy`：敵人依等級成長（追加 A：和主角同樣，每級屬性 +2、HP +5%，技能階級照 07 7.6；
  範本＝1 級基準）。

5A-6 接上成長與下一場修正：

- 規則包加入主角的生成技能（閃現、升階重配後的技能）。
- ``next_battle``（5B-2 情境判定）：buff／debuff 開場掛在主角身上；增援（:func:`~trpg.world.
  encounters.reinforce_lineup`，玩法 PM 定）；打完一場（勝負都算）清空，撤退不消耗（代決 5A6-8）。
- 先手：遭遇地點的 ``ally_first_threads``（斷崖幫寨的暗門）→ 我方先手；增援時陣容已滿 → 敵人
  先手；兩者同時成立時抵銷（代決 5A6-4）。
- 戰後：主角裝備的技能記「先上場用過」與用法統計（一般戰鬥不給靈感，06 6.34.2）；打贏的經驗走
  :func:`~trpg.world.growth.gain_xp`（當下升級、升階重配），每種精英首殺給靈感。

確定性：亂數只來自 ``battle_seed``（地圖 ``"{battle_seed}:map"``、陣容 ``"{battle_seed}:lineup"``、
增援 ``"{battle_seed}:reinforce"``、戰鬥本身）；不讀時間、不呼叫 LLM。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.maps import MapDef, Objective
from trpg.content.regions import RegionDef
from trpg.content.skills import SkillDef
from trpg.engine.actions import Step
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.events import EventBase, UnitDowned
from trpg.engine.oaths import OathSetup
from trpg.engine.results import battle_result
from trpg.engine.runner import advance, apply_step
from trpg.engine.setup import (
    BattleSetup,
    UnitSpawn,
    build_setup,
    phase_spawn_ids,
    with_phase_assets,
)
from trpg.engine.state import BattleState, SpawnTemplate
from trpg.roguelite.flashes import after_battle_flash
from trpg.roguelite.offers import at_run_tier
from trpg.roguelite.progress import hero_unit_id
from trpg.shared.errors import TrpgError
from trpg.shared.rng import Rng, fnv1a64
from trpg.shared.types import Attribute, Team, UnitId
from trpg.skillgen.usage import collect_usage, merge_usage
from trpg.world.actions import (
    BattleEndedEvent,
    BattlefieldCut,
    BattleStartedEvent,
    CutFallback,
    DefeatedEvent,
    FightAction,
    InsightGainedEvent,
    LocationClearedEvent,
    StoryFlagClearedEvent,
    WorldEvent,
)
from trpg.world.battlefield import Battlefield, UnitCounts, contact_battlefield
from trpg.world.calendar import day_of
from trpg.world.common import max_hp, max_mana, rules_of, world_map_of
from trpg.world.companions import companion_spawns, companion_win_affinity
from trpg.world.economy import battle_gold, pouch_skills, spend_pouch
from trpg.world.encounters import (
    EncounterLineup,
    LineupMember,
    elite_kinds,
    lineup_templates,
    reinforce_lineup,
    roll_lineup,
)
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.gear import hero_loadout
from trpg.world.growth import as_run, gain_xp, world_library
from trpg.world.loot import add_loot, boss_bonus_units, roll_loot
from trpg.world.oaths import oath_carries, oath_events, oath_setup
from trpg.world.party import party_spawns, shadow_spawns
from trpg.world.season_boss import boss_def, boss_result
from trpg.world.shadows import record_lent
from trpg.world.state import (
    CharacterState,
    ClearedLocation,
    EncounterResult,
    LastBattle,
    LootSummary,
    WorldState,
)
from trpg.world.threads import active_threads
from trpg.world.weapon_mix import hero_skills

__all__ = [
    "PreparedBattle",
    "armored",
    "auto_steps",
    "battle_objective",
    "battle_xp",
    "encounter_map",
    "enemy_level",
    "fight",
    "first_team",
    "grow_allies",
    "grow_enemy",
    "hero_spawn",
    "hero_start_hp",
    "hero_statuses",
    "prepare_battle",
    "prepare_season_boss_battle",
    "reskin",
    "season_boss_lineup",
    "with_cleared",
]


@dataclass(frozen=True)
class PreparedBattle:
    """一場遭遇的戰鬥：引擎設定、種子、敵方陣容（含增援）與等級、主角開場 HP、增援人數、先手、
    主角開場狀態（5A-6）。"""

    setup: BattleSetup
    seed: int
    lineup: EncounterLineup
    enemy_level: int
    hero_hp: int
    reinforcements: int = 0
    first_team: Team | None = None
    hero_statuses: tuple[str, ...] = ()
    oath: OathSetup | None = None
    """這場帶的誓約（5C-3；``None``＝沒有誓約）。"""
    field_cut: BattlefieldCut | None = None
    """就地開打切出的戰場（6C-2，:mod:`trpg.world.battlefield`）；``None``＝用模板地圖。"""
    cut_fallback: CutFallback | None = None
    """碰到地圖上的敵人卻退回模板的原因（6C-2）。"""


# ---------------------------------------------------------------------------
# 地圖
# ---------------------------------------------------------------------------


def encounter_map(library: ContentLibrary, encounter: EncounterResult) -> MapDef:
    """遭遇的戰鬥地圖（已換皮成遭遇的區域）。``battle_map`` 為 ``None`` 時從該區 ``map_pool`` 的
    類型裡（不含 Boss）依地圖 ID 排序、以 ``"{battle_seed}:map"`` 均勻抽一張（代決 5A4-1）；遭遇指定
    勝利條件時（5B-4c）只從支援它的地圖抽（都不支援時照原樣）。賽季 Boss 的地圖不經過這裡
    （:func:`prepare_season_boss_battle`）。"""
    if encounter.battle_map is not None:
        map_def = library.map(encounter.battle_map)
    else:
        pool = set(_region_def(library, encounter.region).map_pool) - {"boss"}
        options = sorted(m for m, d in library.maps.items() if d.archetype in pool)
        if encounter.objective is not None:  # 戰鬥解法的勝利條件（5B-4c）：優先挑支援它的地圖
            kind = encounter.objective
            options = [m for m in options if library.maps[m].supports_objective(kind)] or options
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


def battle_xp(library: ContentLibrary, encounter: EncounterResult, lineup: EncounterLineup) -> int:
    """打贏一場給的經驗（5A-SIM2 方案 B）：1 份隨地點建議等級；陣容含精英給 ``elite`` 份，否則
    ``battle`` 份。"""
    source = "elite" if elite_kinds(library, lineup) else "battle"
    return rules_of(library).xp.xp_for(source, enemy_level(library, encounter))


def grow_allies(
    library: ContentLibrary, units: Sequence[UnitSpawn], level: int
) -> tuple[tuple[UnitSpawn, ...], tuple[SkillDef, ...]]:
    """標準隊友（之後的傭兵、影子同一條）照主角等級 ``level`` 成長（5A-SIM2：同 :func:`grow_enemy`
    的規則）；回傳成長後的單位與要加進規則包的重配技能。"""
    grown: list[UnitSpawn] = []
    extra: dict[str, SkillDef] = {}
    for unit in units:
        template, skills = grow_enemy(library, unit.template, level)
        extra.update((s.id, s) for s in skills)
        grown.append(unit.model_copy(update={"template": template}))
    return tuple(grown), tuple(extra[k] for k in sorted(extra))


def enemy_level(library: ContentLibrary, encounter: EncounterResult) -> int:
    """敵人的等級：遭遇地點建議等級的 ``level_min``（代決 5A4-5）＋遇敵當下該區的建議等級加成
    （Phase 5F-1，世界事件失敗 +1）。賽季 Boss 用遭遇的等級
    （:func:`prepare_season_boss_battle`）。"""
    location = world_map_of(library, encounter.region).location_by_id().get(encounter.location)
    if location is None or location.level_min is None:
        return encounter.level + encounter.level_bonus
    return location.level_min + encounter.level_bonus


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
    - Boss 階段（5F-2）換上的技能組一併升階改名。
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
    phase_skills = [s for phase in template.phases for s in phase.skills or ()]
    for skill_id in dict.fromkeys((*template.skills, *phase_skills)):
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
    if template.phases:
        update["phases"] = tuple(
            phase
            if phase.skills is None
            else phase.model_copy(update={"skills": tuple(rename.get(s, s) for s in phase.skills)})
            for phase in template.phases
        )
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


def hero_statuses(char: CharacterState) -> tuple[str, ...]:
    """``next_battle`` 的 buff／debuff 狀態（依產生順序、同一狀態只掛一次；代決 5A6-8）。"""
    seen: list[str] = []
    for mod in char.next_battle:
        if mod.status is not None and mod.status not in seen:
            seen.append(mod.status)
    return tuple(seen)


def first_team(
    library: ContentLibrary, char: CharacterState, encounter: EncounterResult, enemy_first: bool
) -> Team | None:
    """先手的陣營：遭遇地點列了 ``ally_first_threads`` 且角色持有其中一條有效個人線頭（以遭遇時間
    判定到期）→ 我方；增援時陣容已滿 → 敵方；兩者都成立時抵銷（``None``）。

    實地地圖上碰到敵人（Phase 6C-1，21.10 第 4 條）：從背後、在視野外接觸算我方一票，被看到算
    敵方一票，和上面兩條一起照「兩邊都有就抵銷」判定。"""
    table = library.world_encounters.get(encounter.region)
    entry = None if table is None else table.location_by_id().get(encounter.location)
    wanted = () if entry is None else entry.ally_first_threads
    ally_first = any(t.thread in wanted and t.expires_at > encounter.at for t in char.threads)
    contact = None if encounter.contact is None else encounter.contact.first
    ally_first = ally_first or contact == "ally"
    enemy_first = enemy_first or contact == "enemy"
    if ally_first == enemy_first:
        return None
    return Team.ALLY if ally_first else Team.ENEMY


def hero_spawn(
    library: ContentLibrary,
    char: CharacterState,
    hp: int,
    items: tuple[str, ...] = (),
    *,
    statuses: tuple[str, ...] | None = None,
) -> UnitSpawn:
    """主角的出場設定（同 roguelite ``hero_spawn``：等級加成併入基礎 HP，體質由引擎加）；
    ``items`` 是腰包的道具技能（5D-1，接在技能最後）。主手是別大類時，原大類的武器技不放進技能列
    （6T-1b，:func:`~trpg.world.weapon_mix.usable_skills`）。PR-2a 起公開：工坊靶場的「靶場試玩」
    （:func:`trpg.world.opening.own_practice`）用同一套技能列與裝備。"""
    core = library.ruleset.core
    hero = char.hero
    leveled = hero.model_copy(
        update={
            "max_hp": hero.max_hp + core.level_hp_bonus(hero.max_hp, char.level),
            "scaled_resources": True,
            "level": char.level,
            "skills": (*hero_skills(library, char), *items),
        }
    )
    return UnitSpawn(
        template=leveled,
        weapon=library.weapons[hero.weapon],
        equipment=hero_loadout(library, char),  # 穿戴的裝備（5D-2；空時照範本）
        team=Team.ALLY,
        hp=hp,
        mana=char.mana,
        stamina=char.stamina,
        opening_statuses=hero_statuses(char) if statuses is None else statuses,
    )


def armored(
    library: ContentLibrary,
    char: CharacterState,
    encounter: EncounterResult,
    templates: Sequence[UnitTemplate],
) -> tuple[UnitTemplate, ...]:
    """遭遇表地點的護甲調整（Phase 5F-5a，``armor_mods``；灰燼之心）：陣容中該單位的護甲加上符合的
    總和（世界旗標看遇敵當下、線頭看遇敵時刻 ``at`` 還有效的個人線頭、劇情旗標看角色），結果不低於
    0。沒有遭遇表或沒寫時原樣（賽季 Boss 不經過這裡）。不耗亂數。"""
    table = library.world_encounters.get(encounter.region)
    entry = None if table is None else table.location_by_id().get(encounter.location)
    mods = None if entry is None else entry.armor_mods
    if mods is None:
        return tuple(templates)
    delta = mods.total(
        world_flags=encounter.world_flags,
        story_flags=char.story_flags,
        threads={t.thread for t in active_threads(char.threads, encounter.at)},
    )
    if delta == 0:
        return tuple(templates)
    return tuple(
        t.model_copy(update={"armor_bonus": max(0, t.armor_bonus + delta)})
        if t.id == mods.unit
        else t
        for t in templates
    )


def season_boss_lineup(library: ContentLibrary, encounter: EncounterResult) -> EncounterLineup:
    """賽季 Boss 的陣容（Phase 5F-3）：``season_boss.units`` 依序（第一個是本體）。"""
    boss = boss_def(library)
    if boss is None or boss.id != encounter.season_boss:
        raise WorldError(f"內容庫沒有賽季頭目 {encounter.season_boss}")
    return EncounterLineup(
        region=encounter.region,
        location=encounter.location,
        group=boss.id,
        members=tuple(LineupMember(unit=u) for u in boss.units),
    )


def battle_objective(map_def: MapDef, encounter: EncounterResult) -> Objective | None:
    """遭遇的勝利條件（5B-4c 戰鬥解法）：指定了撤離或守點而且地圖有資料 → 該條件；地圖沒有資料
    → 一般勝利（全滅，代決 5B4c-8）；沒指定 → ``None``（地圖預設）。"""
    if encounter.objective is None:
        return None
    if map_def.supports_objective(encounter.objective):
        return map_def.objective_for(encounter.objective)
    return map_def.objective_for("eliminate")


def _pending(char: CharacterState) -> EncounterResult:
    encounter = char.pending_encounter
    if encounter is None:
        raise WorldActionError("目前沒有遭遇")
    return encounter


def prepare_battle(library: ContentLibrary, char: CharacterState) -> PreparedBattle:
    """角色身上遭遇的戰鬥設定（見模組說明）；沒有遭遇時拋 :class:`WorldActionError`。賽季 Boss
    的遭遇轉給 :func:`prepare_season_boss_battle`。"""
    encounter = _pending(char)
    if encounter.season_boss is not None:
        return prepare_season_boss_battle(library, char)
    reinforce = sum(1 for m in char.next_battle if m.kind == "reinforce")
    rolled = roll_lineup(library, encounter, char.story_flags)  # 線頭到期結局的變化（5B-4b）
    reinforced = reinforce_lineup(library, encounter, rolled, reinforce)
    lineup = reinforced.lineup
    level = enemy_level(library, encounter)
    extra: dict[str, SkillDef] = {}
    # 第三方（5B-M3 三方混戰）照同一等級成長，排在敵方之後
    enemies = _enemy_spawns(
        library,
        (
            (Team.ENEMY, armored(library, char, encounter, lineup_templates(library, lineup))),
            (Team.THIRD, lineup_templates(library, lineup, third=True)),
        ),
        level,
        extra,
    )
    phase_spawns = _phase_spawns(library, enemies, level, extra)  # Boss 階段的召喚（5F-2）
    # 我方＝主角＋傭兵（5C-1）＋影子（5C-2）；沒有隊友＝獨行（5C-2 玩法 PM 定 ③）
    mercenaries = _mercenary_spawns(library, char, extra)
    shadow_units, shadow_skills = shadow_spawns(library, char)
    extra.update((s.id, s) for s in shadow_skills)
    # 劇情夥伴（5C-3）：排在傭兵、影子之後，同樣照主角等級成長
    companions, companion_skills = grow_allies(library, companion_spawns(library, char), char.level)
    extra.update((s.id, s) for s in companion_skills)
    statuses = hero_statuses(char)
    hero, hp = _hero_with_items(library, char, extra, statuses)
    first = first_team(library, char, encounter, reinforced.enemy_first)
    oath = oath_setup(library, char)  # 誓約的加成與判定（5C-3；主角＝units[0]）
    allies = (hero, *mercenaries, *shadow_units, *companions)
    field = _battlefield(library, encounter, allies, enemies, first)  # 就地開打（6C-2）
    setup = _battle_setup(
        library,
        field.map,
        encounter,
        units=(*allies, *enemies),
        extra=extra,
        phase_spawns=phase_spawns,
        first=first,
        oath=oath,
    )
    return PreparedBattle(
        setup=setup,
        seed=encounter.battle_seed,
        lineup=lineup,
        enemy_level=level,
        hero_hp=hp,
        reinforcements=reinforced.added,
        first_team=first,
        hero_statuses=statuses,
        oath=oath,
        field_cut=field.cut,
        cut_fallback=field.fallback,
    )


def _battlefield(
    library: ContentLibrary,
    encounter: EncounterResult,
    allies: Sequence[UnitSpawn],
    enemies: Sequence[UnitSpawn],
    first: Team | None,
) -> Battlefield:
    """戰鬥地圖（已換皮成遭遇的區域）：地圖上碰到的敵人就地切 12×12，否則（或不合法時）用
    :func:`encounter_map` 的模板（6C-2）。模板照舊先選（亂數只看 ``battle_seed``，切不切都
    一樣）。"""
    template = encounter_map(library, encounter)
    counts = UnitCounts(
        allies=len(allies),
        enemies=sum(1 for u in enemies if u.team is Team.ENEMY),
        third=sum(1 for u in enemies if u.team is Team.THIRD),
    )
    found = contact_battlefield(library, encounter, template, counts, first)
    if found.cut is None:
        return found
    return Battlefield(map=reskin(library, found.map, encounter.region), cut=found.cut)


def prepare_season_boss_battle(library: ContentLibrary, char: CharacterState) -> PreparedBattle:
    """賽季 Boss 的戰鬥設定（Phase 5F-3；5F-R2 從 :func:`prepare_battle` 拆出）：

    - 地圖：遭遇指定的 Boss 地圖（在界域裡，不換皮）。
    - 陣容：``season_boss.units`` 固定陣容，沒有增援、沒有第三方、不套護甲調整。
    - 等級：遭遇的等級（依滿等設計，``season_boss.level``）。
    - 我方：主角＋傭兵（#87 只准傭兵：沒有影子、劇情夥伴）。
    - 不帶下一場修正（不套用、也不消耗，代決 5F3-4）、不看先手。誓約照帶。
    """
    encounter = _pending(char)
    if encounter.battle_map is None:  # 挑戰時一定帶 Boss 地圖；保險起見照一般遭遇的抽法
        map_def = encounter_map(library, encounter)
    else:
        map_def = library.map(encounter.battle_map)
    lineup = season_boss_lineup(library, encounter)
    level = encounter.level
    extra: dict[str, SkillDef] = {}
    enemies = _enemy_spawns(
        library, ((Team.ENEMY, lineup_templates(library, lineup)),), level, extra
    )
    phase_spawns = _phase_spawns(library, enemies, level, extra)
    mercenaries = _mercenary_spawns(library, char, extra)
    hero, hp = _hero_with_items(library, char, extra, ())
    oath = oath_setup(library, char)
    setup = _battle_setup(
        library,
        map_def,
        encounter,
        units=(hero, *mercenaries, *enemies),
        extra=extra,
        phase_spawns=phase_spawns,
        first=None,
        oath=oath,
    )
    return PreparedBattle(
        setup=setup,
        seed=encounter.battle_seed,
        lineup=lineup,
        enemy_level=level,
        hero_hp=hp,
        oath=oath,
    )


def _enemy_spawns(
    library: ContentLibrary,
    sides: Sequence[tuple[Team, Sequence[UnitTemplate]]],
    level: int,
    extra: dict[str, SkillDef],
) -> list[UnitSpawn]:
    """敵方（與第三方）依序照 ``level`` 成長成出場設定；重配的技能加進 ``extra``。"""
    enemies: list[UnitSpawn] = []
    for team, templates in sides:
        for template in templates:
            grown, skills = grow_enemy(library, template, level)
            extra.update((s.id, s) for s in skills)
            enemies.append(
                UnitSpawn(
                    template=grown,
                    weapon=library.weapon_of(grown),
                    equipment=library.loadout_of(grown),
                    team=team,
                )
            )
    return enemies


def _mercenary_spawns(
    library: ContentLibrary, char: CharacterState, extra: dict[str, SkillDef]
) -> tuple[UnitSpawn, ...]:
    """隊伍的傭兵（5C-1），照主角等級成長；重配的技能加進 ``extra``（一般遭遇與賽季 Boss 共用）。"""
    allies, skills = grow_allies(library, party_spawns(library, char), char.level)
    extra.update((s.id, s) for s in skills)
    return allies


def _hero_with_items(
    library: ContentLibrary,
    char: CharacterState,
    extra: dict[str, SkillDef],
    statuses: tuple[str, ...],
) -> tuple[UnitSpawn, int]:
    """主角的出場設定與開場 HP（一般遭遇與賽季 Boss 共用）：生成技能（5A-6）與腰包的道具（5D-1：
    1 AP、次數＝個數、不佔欄位）加進 ``extra``；``statuses`` 是開場狀態。"""
    extra.update((s.id, s) for s in char.generated_skills)
    items = pouch_skills(library, char)
    extra.update((s.id, s) for s in items)
    hp = hero_start_hp(library, char)
    hero = hero_spawn(library, char, hp, tuple(s.id for s in items), statuses=statuses)
    return hero, hp


def _battle_setup(
    library: ContentLibrary,
    map_def: MapDef,
    encounter: EncounterResult,
    *,
    units: tuple[UnitSpawn, ...],
    extra: dict[str, SkillDef],
    phase_spawns: dict[str, SpawnTemplate],
    first: Team | None,
    oath: OathSetup | None,
) -> BattleSetup:
    """組出引擎設定：借 roguelite 設定的骨架，換上地圖、規則包（加 ``extra`` 技能）、單位、先手、
    勝利條件、誓約與 Boss 階段的召喚和天氣（5F-2）。"""
    base = build_setup(
        library,
        map_def.id if map_def.id in library.maps else encounter_map(library, encounter).id,
        library.roguelite.companions,  # 只借用設定的骨架；我方在下面整組換掉
        (),
        max_rounds=rules_of(library).battle.max_rounds,
        weather=encounter.weather,
    )
    setup = base.model_copy(
        update={
            "map": map_def,
            "ruleset": library.ruleset.with_skills(extra[k] for k in sorted(extra)),
            "units": units,
            "first_team": first,
            "objective": battle_objective(map_def, encounter),
            "oath": oath,
            "spawn_templates": {**base.spawn_templates, **phase_spawns},
        }
    )
    return with_phase_assets(library, setup)  # 階段會換成的天氣（5F-2）


def _phase_spawns(
    library: ContentLibrary, enemies: Sequence[UnitSpawn], level: int, extra: dict[str, SkillDef]
) -> dict[str, SpawnTemplate]:
    """敵方 Boss 階段（5F-2）會召喚的範本，照敵人等級成長（代決 5F2-11）；重配的技能加進
    ``extra``。"""
    found: dict[str, SpawnTemplate] = {}
    for template_id in phase_spawn_ids(enemies):
        grown, skills = grow_enemy(library, library.unit(template_id), level)
        extra.update((s.id, s) for s in skills)
        found[template_id] = SpawnTemplate(
            template=grown,
            weapon=library.weapon_of(grown),
            equipment=library.loadout_of(grown),
        )
    return found


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


def _run(prepared: PreparedBattle, steps: Sequence[Step]) -> tuple[BattleState, list[EventBase]]:
    opening = begin_battle(prepared.setup, prepared.seed)
    state = opening.state
    events: list[EventBase] = list(opening.events)
    for number, step in enumerate(steps, start=1):
        try:
            result = apply_step(state, step)
        except TrpgError as exc:
            raise WorldActionError(f"戰鬥的第 {number} 步無法套用：{exc}") from exc
        state = result.state
        events.extend(result.events)
    if not state.ended:
        raise WorldActionError("戰鬥還沒結束")
    return state, events


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
    """``fight`` 動作（見模組說明）；賽季 Boss 的回寫轉給 :func:`_season_boss_fight`。"""
    prepared = prepare_battle(library, char)
    encounter = _pending(char)
    battle = _run(prepared, action.steps)
    started = _started_event(char, encounter, prepared)
    finish = _season_boss_fight if encounter.season_boss is not None else _encounter_fight
    return finish(
        library, world, char, prepared, action=action, battle=battle, started=started, now=now
    )


def _started_event(
    char: CharacterState, encounter: EncounterResult, prepared: PreparedBattle
) -> BattleStartedEvent:
    return BattleStartedEvent(
        location=encounter.location,
        battle_map=prepared.setup.map.id,
        region=encounter.region,
        lineup=prepared.lineup,
        enemy_level=prepared.enemy_level,
        weather=encounter.weather,
        hero_hp=prepared.hero_hp,
        fatigued=char.fatigued,
        reinforcements=prepared.reinforcements,
        first_team=prepared.first_team,
        hero_statuses=prepared.hero_statuses,
        mercenaries=char.mercenaries,
        shadows=tuple(s.owner for s in char.shadows),
        companions=char.companions,
        oath=None if prepared.oath is None else prepared.oath.template,
        field_cut=prepared.field_cut,
        cut_fallback=prepared.cut_fallback,
    )


def _encounter_fight(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    prepared: PreparedBattle,
    *,
    action: FightAction,
    battle: tuple[BattleState, list[EventBase]],
    started: WorldEvent,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """一般遭遇的回寫（見模組說明）。"""
    state, battle_events = battle
    encounter = _pending(char)
    result = battle_result(state)
    hero_id = hero_unit_id(state)
    hero = result.ally(hero_id)
    assert hero is not None
    won = result.winner is Team.ALLY
    level_before = char.level
    char, used = _after_battle_skills(library, char, prepared, action.steps, hero_id, won=won)
    char = char.model_copy(update={"next_battle": ()})  # 下一場修正打完一場就消耗（5A-6）
    char, pouch_used = spend_pouch(library, char, state, hero_id)  # 腰包用掉的道具（5D-1）
    loot: LootSummary | None = None
    if won:
        world, char, more, loot = _won_rewards(
            library, world, char, prepared, battle=battle, hp=hero.hp, mana=hero.mana, now=now
        )
    else:
        char, more = _lost(library, char, hero.mana)
    oath_more, oath_broken = oath_events(prepared.oath, battle_events)  # 誓約（5C-3）
    more += oath_more
    char = char.model_copy(update={"oath_broken_next": oath_carries(prepared.oath, battle_events)})
    world, lent = record_lent(  # 影子主人每天第一次被借用（5C-2，#102）
        library, world, char, encounter, prepared.lineup, won=won, now=now
    )
    more += lent
    xp_gained = battle_xp(library, encounter, prepared.lineup) if won else 0
    ended = BattleEndedEvent(
        won=won,
        end_reason=result.end_reason,
        rounds=result.round,
        hp=char.hp,
        mana=char.mana,
        xp_gained=xp_gained,
        level=char.level,
        skills_used=used,
    )
    if won and prepared.lineup.variant is not None:  # 線頭到期結局的變化打贏就結束（5B-4b）
        flag = prepared.lineup.variant
        flags = tuple(f for f in char.story_flags if f != flag)
        char = char.model_copy(update={"story_flags": flags})
        more.append(StoryFlagClearedEvent(flag=flag))
    last = LastBattle(
        region=encounter.region,
        location=encounter.location,
        won=won,
        end_reason=result.end_reason,
        rounds=result.round,
        xp_gained=xp_gained,
        level_before=level_before,
        level=char.level,
        at=now,
        oath=None if prepared.oath is None else prepared.oath.template,
        oath_broken=oath_broken,
        loot=loot,
    )
    char = char.model_copy(update={"last_battle": last})
    return world, char, (started, ended, *pouch_used, *more)


def _won_rewards(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    prepared: PreparedBattle,
    *,
    battle: tuple[BattleState, list[EventBase]],
    hp: int,
    mana: int,
    now: int,
) -> tuple[WorldState, CharacterState, list[WorldEvent], LootSummary | None]:
    """一般遭遇打贏的回寫：經驗與已清空（:func:`_won`）、夥伴好感（18.7.6）、金錢（5D-1）、
    區域 Boss 保底（5F-3）與掉落（5D-2）。"""
    state, battle_events = battle
    encounter = _pending(char)
    world, char, more = _won(
        library, world, char, encounter, prepared.lineup, hp=hp, mana=mana, now=now
    )
    char, liked = companion_win_affinity(library, char, now)  # 帶夥伴打贏（18.7.6）
    more += liked
    elite = bool(elite_kinds(library, prepared.lineup))
    char, gold = battle_gold(library, char, elite=elite, level=prepared.enemy_level)  # 5D-1
    more += gold
    today = day_of(library, now)
    bonus = boss_bonus_units(library, char, prepared.lineup, today)  # 區域 Boss 保底（5F-3）
    if bonus:
        days = {**char.boss_drop_days, **dict.fromkeys(bonus, today)}
        char = char.model_copy(update={"boss_drop_days": days})
    roll = roll_loot(  # 掉落（5D-2）：材料、裝備進背包
        library,
        char,
        setup=prepared.setup,
        lineup=prepared.lineup,
        state=state,
        events=battle_events,
        seed=prepared.seed,
        level=prepared.enemy_level,
        boss_bonus=bonus,
        fixed_class=_fixed_main_hand(library, encounter, prepared.lineup),  # 6T-1a（#135）
        mix=world.weapon_mix,
    )
    char, loot, loot_events = add_loot(library, char, roll)
    more += loot_events
    return world, char, more, loot


def _fixed_main_hand(
    library: ContentLibrary, encounter: EncounterResult, lineup: EncounterLineup
) -> bool:
    """這場的主手一律同大類（08 8.13 #135）：懸賞、區域 Boss（Boss 地點，或陣容有 ``loot.yaml`` 的
    ``bosses``）。"""
    if encounter.bounty is not None:
        return True
    kind = world_map_of(library, encounter.region).location_by_id()[encounter.location].kind
    bosses = {} if library.world_loot is None else library.world_loot.bosses
    return kind == "boss" or any(m.unit in bosses for m in lineup.members)


def _season_boss_fight(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    prepared: PreparedBattle,
    *,
    action: FightAction,
    battle: tuple[BattleState, list[EventBase]],
    started: WorldEvent,
    now: int,
) -> tuple[WorldState, CharacterState, tuple[WorldEvent, ...]]:
    """賽季 Boss 戰的回寫（Phase 5F-3，代決 5F3-4、5F3-5）：勝負都不給經驗、金錢、掉落；HP、法力、
    耐力照開戰前，不疲憊、不回小鎮（失敗只扣次數，#98）；下一場修正不消耗；腰包用掉的道具照扣、
    技能用法照記。打贏記通關與分數（:func:`~trpg.world.season_boss.boss_result`）。"""
    state, battle_events = battle
    encounter = _pending(char)
    result = battle_result(state)
    hero_id = hero_unit_id(state)
    won = result.winner is Team.ALLY
    char, used = _after_battle_skills(library, char, prepared, action.steps, hero_id, won=won)
    char, pouch_used = spend_pouch(library, char, state, hero_id)
    party = _party_ids(prepared.setup, len(party_spawns(library, char)))
    downed = {e.unit_id for e in battle_events if isinstance(e, UnitDowned)}
    survivors = sum(1 for uid in party if (u := state.units.get(uid)) is not None and u.alive)
    world, outcome = boss_result(
        library,
        world,
        char,
        won=won,
        rounds=result.round,
        survivors=survivors,
        allies=len(party),
        no_down=not downed & set(party),
        now=now,
    )
    ended = BattleEndedEvent(
        won=won,
        end_reason=result.end_reason,
        rounds=result.round,
        hp=char.hp,
        mana=char.mana,
        xp_gained=0,
        level=char.level,
        skills_used=used,
    )
    last = LastBattle(
        region=encounter.region,
        location=encounter.location,
        won=won,
        end_reason=result.end_reason,
        rounds=result.round,
        xp_gained=0,
        level_before=char.level,
        level=char.level,
        at=now,
    )
    char = char.model_copy(update={"pending_encounter": None, "last_battle": last})
    return world, char, (started, ended, *pouch_used, outcome)


def _party_ids(setup: BattleSetup, mercenaries: int) -> tuple[UnitId, ...]:
    """主角與傭兵的單位 ID（設定順序的前 ``1 + 傭兵數`` 名；引擎依序配發 ``unit_0001`` 起）。"""
    count = min(len(setup.units), 1 + mercenaries)
    return tuple(UnitId(f"unit_{i:04d}") for i in range(1, count + 1))


def _after_battle_skills(
    library: ContentLibrary,
    char: CharacterState,
    prepared: PreparedBattle,
    steps: Sequence[Step],
    hero_id: UnitId,
    *,
    won: bool,
) -> tuple[CharacterState, tuple[str, ...]]:
    """戰後：主角裝備的技能照這場的用法統計記「先上場用過」並累加用法統計（roguelite
    ``after_battle_flash``；06 6.34.2 大世界一般戰鬥 **不給** 靈感，所以丟掉它算的靈感點）。
    另外回傳這場用過的技能 ID（排序；5B-4b 導師任務鏈的條件）。"""
    usage = collect_usage(
        prepared.setup, prepared.seed, steps, hero_id, library.keywords, only=char.hero.skills
    )
    flashed: dict[str, Any] = after_battle_flash(
        world_library(library), as_run(char), usage, won=won
    )
    flashed.pop("insight", None)
    used = tuple(sorted(k for k, u in usage.items() if u.uses > 0))
    merged = merge_usage(char.skill_usage, usage)
    return char.model_copy(update={**flashed, "skill_usage": merged}), used


def _elite_first_kills(
    library: ContentLibrary, char: CharacterState, lineup: EncounterLineup
) -> tuple[CharacterState, list[WorldEvent]]:
    """每種精英的首殺各給 ``insight_per_elite_kind`` 點靈感（06 6.34.2；代決 5A6-7）。"""
    amount = rules_of(library).hero_growth.insight_per_elite_kind
    events: list[WorldEvent] = []
    kills = set(char.elite_kills)
    for kind in elite_kinds(library, lineup):
        if kind in kills:
            continue
        kills.add(kind)
        char = char.model_copy(update={"insight": char.insight + amount})
        events.append(
            InsightGainedEvent(source=f"elite:{kind}", amount=amount, insight=char.insight)
        )
    return char.model_copy(update={"elite_kills": tuple(sorted(kills))}), events


def _won(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    encounter: EncounterResult,
    lineup: EncounterLineup,
    *,
    hp: int,
    mana: int,
    now: int,
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    """打贏：HP 照戰後（倒下以 1 HP 繼續）、法力不回、耐力回滿（#113）；經驗與升級（共用的
    :func:`~trpg.world.growth.gain_xp`）；精英首殺靈感；已清空。"""
    rules = rules_of(library).battle
    char = char.model_copy(
        update={
            "hp": max(1, hp),
            "mana": mana,
            "stamina": None,
            "fatigued": False,
            "pending_encounter": None,
        }
    )
    char, events = gain_xp(library, world, char, battle_xp(library, encounter, lineup))
    char, insight = _elite_first_kills(library, char, lineup)
    events += insight
    kind = world_map_of(library, encounter.region).location_by_id()[encounter.location].kind
    if kind in rules.clear_kinds and encounter.contact is None:
        # 碰到地圖上的一隊（6C-1b）：每隊清空、全打完才寫已清空，由 field_enemies.after_fight 處理
        respawn_at = now + rules.respawn_seconds
        world = with_cleared(world, encounter.region, encounter.location, respawn_at)
        events.append(LocationClearedEvent(location=encounter.location, respawn_at=respawn_at))
    return world, char, events


def _lost(
    library: ContentLibrary, char: CharacterState, mana: int
) -> tuple[CharacterState, list[WorldEvent]]:
    """全滅（含輪數上限，代決 5A4-7）：回本區小鎮、HP 回滿、法力回滿、耐力回滿；不給也不扣經驗；
    下一場疲憊（9.6.9 #98；代決 5A4-8）。6F-1：法力原本照戰後（1/28 回鎮的實機問題），改成和 HP
    一樣回滿（9.6.7 第 2 條城鎮完全回復；待玩法 PM 確認），``mana`` 參數不再使用。"""
    del mana
    town = world_map_of(library, char.region).town
    char = char.model_copy(
        update={
            "location": town,
            "stamina": None,
            "fatigued": True,
            "pending_encounter": None,
            "camped_at": None,
        }
    )
    char = char.model_copy(update={"hp": max_hp(library, char), "mana": max_mana(library, char)})
    return char, [DefeatedEvent(location=town, hp=char.hp)]
