"""朋友的影子（Phase 5C-2；``docs/phases/Phase5計畫.md`` 23）。

- **存影子**（09 9.6.10 #102）：角色在城鎮整備（:data:`PREP_ACTIONS`）之後，自動把目前的 build 存成
  影子（:attr:`WorldState.shadows`，每個角色一份；覆寫時保留任務幣與戰報）。
- **強度上限**（9.6.8 #87）：借來的影子在開戰時照招募者壓到上限（:func:`shadow_spawn`）——等級取
  兩者較低、多出的等級扣屬性點、技能階級高於上限的往下重配；物品等級在 5D。
- **被借用的獎勵**（#102）：帶著影子打完一場時，主人每天第一次給任務幣並加一則戰報
  （:func:`record_lent`；任務幣先記在世界的影子紀錄，5D 轉入角色）。

純函式：不讀時間、不擲骰。
"""

from __future__ import annotations

from typing import Final

from trpg.content.battle import UnitTemplate
from trpg.content.equipment import Loadout
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.engine.setup import UnitSpawn
from trpg.roguelite.offers import at_run_tier
from trpg.shared.types import Attribute, Team
from trpg.world.actions import (
    HireAction,
    LoadoutAction,
    RestAction,
    ShadowAiAction,
    ShadowLentEvent,
    ShadowSavedEvent,
    WorldAction,
    WorldEvent,
)
from trpg.world.calendar import day_of
from trpg.world.common import here
from trpg.world.economy_actions import EquipAction
from trpg.world.encounters import EncounterLineup
from trpg.world.gear import item_loadout, shadow_equipment
from trpg.world.growth import GROWTH_ACTIONS, hero_tier
from trpg.world.state import (
    CharacterState,
    EncounterResult,
    ShadowRecord,
    ShadowReport,
    ShadowSnapshot,
    WorldState,
)
from trpg.world.weapon_mix import usable_skills

__all__ = [
    "PREP_ACTIONS",
    "SHADOW_UNIT_PREFIX",
    "capped_attributes",
    "record_lent",
    "save_after_prep",
    "shadow_level",
    "shadow_role_zh",
    "shadow_snapshot",
    "shadow_spawn",
    "shadow_tier",
    "with_shadow",
]


def shadow_role_zh(library: ContentLibrary, snapshot: ShadowSnapshot) -> str:
    """影子的定位：武器・種族（代決 5C2-9；循環賽排行榜與編年史的 build 名也用，5F-4／5F-4b）。"""
    hero = snapshot.hero
    weapon = library.weapons[hero.weapon].name_zh if hero.weapon in library.weapons else hero.weapon
    table = library.ruleset.races
    race = (
        None
        if hero.race is None or table is None
        else next((r.name_zh for r in table.races if r.id == hero.race), hero.race)
    )
    return weapon if race is None else f"{weapon}・{race}"


PREP_ACTIONS: Final = (
    RestAction,
    LoadoutAction,
    HireAction,
    ShadowAiAction,
    EquipAction,  # 5D-2：換裝備也算整備（影子帶裝備，20.5）
    *GROWTH_ACTIONS,
)
"""算「城鎮整備」的動作（代決 5C2-2）。"""

SHADOW_UNIT_PREFIX: Final = "shadow_"
"""影子戰鬥單位 ID 的前綴（``shadow_<主人 ID>``）。"""


# ---------------------------------------------------------------------------
# 存影子
# ---------------------------------------------------------------------------


def shadow_snapshot(char: CharacterState, now: int) -> ShadowSnapshot:
    """角色目前的 build 存成影子（裝備中的技能；不在內容庫的技能帶定義）。"""
    generated = {s.id: s for s in char.generated_skills}
    skills = sorted({s for s in char.hero.skills if s in generated})
    return ShadowSnapshot(
        owner=char.character_id,
        hero=char.hero,
        level=char.level,
        skill_tier=char.skill_tier,
        attribute_points=char.attribute_points,
        attribute_spent=dict(char.attribute_spent),
        skills=tuple(generated[s] for s in skills),
        ai_profile=char.shadow_ai,
        equipment=dict(char.equipment),  # 5D-2：存影子時穿的裝備（20.5）
        region=char.region,
        location=char.location,
        saved_at=now,
    )


def with_shadow(world: WorldState, record: ShadowRecord) -> WorldState:
    """寫入（或取代）一個主人的影子紀錄（依主人 ID 排序）。"""
    owner = record.snapshot.owner
    kept = [s for s in world.shadows if s.snapshot.owner != owner]
    kept.append(record)
    kept.sort(key=lambda s: s.snapshot.owner)
    return world.model_copy(update={"shadows": tuple(kept)})


def save_after_prep(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: WorldAction,
    now: int,
) -> tuple[WorldState, tuple[WorldEvent, ...]]:
    """整備動作之後，人在城鎮、沒有待處理的遭遇、閃現或三選一時存成影子（#102）；否則不變。
    開局還沒正式選定的角色（#150 第 9 點「入門期不存朋友可借的影子」，OB-2）不存：別人不會借到
    拿佔位或入門配備的影子。"""
    if not isinstance(action, PREP_ACTIONS):
        return world, ()
    if char.opening is not None and char.opening.stage != "chosen":
        return world, ()
    if char.pending_encounter is not None or char.pending_flash is not None or char.pending_offers:
        return world, ()
    if here(library, char).kind != "town":
        return world, ()
    snapshot = shadow_snapshot(char, now)
    old = world.shadow_of(char.character_id)
    record = (
        ShadowRecord(snapshot=snapshot)
        if old is None
        else old.model_copy(update={"snapshot": snapshot})
    )
    return with_shadow(world, record), (ShadowSavedEvent(level=char.level),)


# ---------------------------------------------------------------------------
# 強度上限（#87）
# ---------------------------------------------------------------------------


def shadow_level(snapshot: ShadowSnapshot, recruiter_level: int) -> int:
    """借用時的等級：影子與招募者較低的那個。"""
    return min(snapshot.level, recruiter_level)


def shadow_tier(library: ContentLibrary, snapshot: ShadowSnapshot, recruiter_level: int) -> int:
    """借用時的技能階級上限：照借用等級的角色階級（影子本身較低時照影子的）。"""
    cap = hero_tier(library, shadow_level(snapshot, recruiter_level))
    own = snapshot.skill_tier if snapshot.skill_tier is not None else cap
    return min(own, cap)


def capped_attributes(
    library: ContentLibrary, snapshot: ShadowSnapshot, level: int
) -> dict[Attribute, int]:
    """壓到 ``level`` 的屬性：多出的等級 × 每級點數，先扣未分配點，再從分配最多的屬性逐點扣
    （同分照 str、dex、con、int、wis、wil；代決 5C2-8）。"""
    attributes = dict(snapshot.hero.attributes)
    excess = library.roguelite.attribute_points_per_level * max(0, snapshot.level - level)
    excess -= min(excess, snapshot.attribute_points)
    spent = {a: snapshot.attribute_spent.get(a, 0) for a in Attribute}
    order = list(Attribute)
    while excess > 0:
        best = max(spent.values())
        if best <= 0:
            break
        top = next(a for a in order if spent[a] == best)
        spent[top] -= 1
        attributes[top] = attributes.get(top, 0) - 1
        excess -= 1
    return attributes


def _capped_skills(
    library: ContentLibrary, snapshot: ShadowSnapshot, tier: int
) -> tuple[dict[str, str], dict[str, SkillDef]]:
    """技能照階級上限往下重配；不在內容庫的一律改名 ``<原 ID>_<主人 ID>``。回傳改名對照與要加進
    規則包的定義。"""
    generated = {s.id: s for s in snapshot.skills}
    rename: dict[str, str] = {}
    extra: dict[str, SkillDef] = {}
    for skill_id in snapshot.hero.skills:
        skill = generated.get(skill_id) or library.skills[skill_id]
        if skill.tier > tier:
            skill = at_run_tier(library, skill, tier)
        if library.skills.get(skill.id) == skill:
            rename[skill_id] = skill.id
            continue
        new_id = f"{skill.id}_{snapshot.owner}"
        rename[skill_id] = new_id
        extra[new_id] = skill.model_copy(update={"id": new_id})
    return rename, extra


def shadow_spawn(
    library: ContentLibrary,
    snapshot: ShadowSnapshot,
    recruiter_level: int,
    ai_profile: str | None = None,
) -> tuple[UnitSpawn, tuple[SkillDef, ...]]:
    """借來的影子的出場設定（壓到招募者的上限；每場滿狀態）與要加進規則包的技能。"""
    level = shadow_level(snapshot, recruiter_level)
    tier = shadow_tier(library, snapshot, recruiter_level)
    rename, extra = _capped_skills(library, snapshot, tier)
    hero = snapshot.hero
    core = library.ruleset.core
    renamed = tuple(rename.get(s, s) for s in hero.skills)
    defs = {**library.skills, **extra}
    weapon_class = library.weapons[hero.weapon].weapon_class
    update: dict[str, object] = {
        "id": f"{SHADOW_UNIT_PREFIX}{snapshot.owner}",
        "attributes": capped_attributes(library, snapshot, level),
        "max_hp": hero.max_hp + core.level_hp_bonus(hero.max_hp, level),
        "scaled_resources": True,
        "level": level,
        "skills": usable_skills(renamed, defs, weapon_class),  # 別大類主手（6T-1b）
        "ai_profile": ai_profile or snapshot.ai_profile or hero.ai_profile,
    }
    if hero.reactions is not None:
        update["reactions"] = tuple(
            r.model_copy(update={"reaction": rename.get(r.reaction, r.reaction)})
            for r in hero.reactions
        )
    template: UnitTemplate = hero.model_copy(update=update)
    spawn = UnitSpawn(
        template=template,
        weapon=library.weapons[hero.weapon],
        equipment=_shadow_loadout(library, snapshot, recruiter_level),
        team=Team.ALLY,
    )
    return spawn, tuple(extra[k] for k in sorted(extra))


def _shadow_loadout(
    library: ContentLibrary, snapshot: ShadowSnapshot, recruiter_level: int
) -> Loadout:
    """影子的裝備（5D-2，20.5）：存影子時穿的，物品等級壓到招募者等級（5D-2b）；沒存裝備時照範本。"""
    if not snapshot.equipment:
        return library.loadout_of(snapshot.hero)
    return item_loadout(library, shadow_equipment(library, snapshot.equipment, recruiter_level))


# ---------------------------------------------------------------------------
# 被借用的獎勵（#102）
# ---------------------------------------------------------------------------


def record_lent(
    library: ContentLibrary,
    world: WorldState,
    borrower: CharacterState,
    encounter: EncounterResult,
    lineup: EncounterLineup,
    *,
    won: bool,
    now: int,
) -> tuple[WorldState, list[WorldEvent]]:
    """帶著影子打完一場：每個影子的主人這一天第一次被借用時給任務幣、加一則戰報（代決 5C2-6）。"""
    table = library.world_mercenaries
    coins = 0 if table is None else table.shadow_daily_coins
    kept = 20 if table is None else table.shadow_reports_kept
    day = day_of(library, now)
    events: list[WorldEvent] = []
    for snapshot in borrower.shadows:
        record = world.shadow_of(snapshot.owner)
        if record is None or record.reward_day == day:
            continue
        report = ShadowReport(
            day=day,
            at=now,
            borrower=borrower.character_id,
            borrower_name=borrower.hero.name_zh,
            region=encounter.region,
            location=encounter.location,
            won=won,
            foes=tuple(m.unit for m in lineup.members),
            coins=coins,
        )
        record = record.model_copy(
            update={
                "coins": record.coins + coins,
                "reward_day": day,
                "reports": (*record.reports, report)[-kept:],
            }
        )
        world = with_shadow(world, record)
        events.append(ShadowLentEvent(owner=snapshot.owner, coins=coins))
    return world, events
