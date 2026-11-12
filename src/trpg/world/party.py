"""隊伍、系統傭兵與借來的影子（Phase 5C-1、5C-2；``docs/phases/Phase5計畫.md`` 22、23）。

- **雇用**（09 9.6.9 #97）：一隊 3 人＝主角＋最多 ``max_hired`` 名隊友（傭兵與影子共用）；免費、只在
  城鎮且沒有遭遇時選（出城前選好、野外不能換）。``hire`` 整組換成新的清單；**0 名＝獨行**
  （5C-2 玩法 PM 定 ③）。影子存的是借用當下的複本（:mod:`trpg.world.shadows`）。
- **打法**（玩法 PM 定 ④）：``hire`` 帶每名成員的 AI 打法（``ai_choices``），存在
  ``CharacterState.party_ai``；沒選＝預設（傭兵：底稿；影子：主人設定的 ``shadow_ai``）。
- **出場**（:func:`party_spawns`）：傭兵的戰鬥單位＝底稿 build 的英雄範本，ID 與名字換成傭兵的
  （代決 5C1-6）；技能照欄位上限挑（玩法 PM 定 ②，:func:`slot_capped`）；照主角等級成長由
  :func:`trpg.world.battle.grow_allies` 做（5A-SIM2）。影子由 :func:`shadow_spawns` 壓到招募者的
  上限。
- **賽季 Boss**（#87、#100）：隊伍有影子時 :func:`season_boss_problem` 回理由（5F-3 檢查）。
- **開局的護衛**（OB-7，#154）：``hire`` 之後護衛（``escort.mercenary``，賽倫）不在隊上時記劇情旗標
  :data:`ESCORT_PARTED`；之後再雇用他就不是「開局帶來的那一位」，隊伍面板不顯示來歷
  （:func:`is_escort`）。

純函式：不讀時間、不擲骰。
"""

from __future__ import annotations

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef, skill_slot_problems
from trpg.content.world_mercenaries import MercenaryDef, MercenaryTable
from trpg.engine.setup import UnitSpawn
from trpg.shared.types import Team
from trpg.world.actions import (
    HireAction,
    PartyChangedEvent,
    ShadowAiAction,
    ShadowAiChangedEvent,
    WorldEvent,
)
from trpg.world.common import here
from trpg.world.errors import WorldActionError, WorldError
from trpg.world.gear import item_loadout, mercenary_equipment
from trpg.world.shadows import shadow_spawn
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "ESCORT_PARTED",
    "SEASON_BOSS_PROBLEM",
    "default_party",
    "hire",
    "hire_problem",
    "is_escort",
    "mercenary_table",
    "party_mercenaries",
    "party_spawns",
    "season_boss_problem",
    "set_shadow_ai",
    "shadow_spawns",
    "slot_capped",
]

SEASON_BOSS_PROBLEM = "賽季頭目只准系統傭兵，隊伍裡不能有影子"
ESCORT_PARTED = "escort_parted"
"""劇情旗標：開局帶的護衛已經在城鎮換下過（OB-7，#154）。"""


def mercenary_table(library: ContentLibrary) -> MercenaryTable:
    """傭兵名單；內容庫沒有 ``world/mercenaries.yaml`` 時拋 :class:`WorldActionError`。"""
    table = library.world_mercenaries
    if table is None:
        raise WorldActionError("內容庫沒有系統傭兵名單")
    return table


def hire_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """現在不能雇用（換隊友）的理由；可以時為 ``None``。"""
    if library.world_mercenaries is None:
        return "沒有系統傭兵名單"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇"
    if here(library, char).kind != "town":
        return "出城前在城鎮選好，野外不能換"
    return None


def _check_members(
    table: MercenaryTable, world: WorldState, char: CharacterState, action: HireAction
) -> None:
    chosen, shadows = action.mercenaries, action.shadows
    total = len(chosen) + len(shadows)
    limit = table.max_hired - len(char.companions)  # 劇情夥伴佔隊友位（5C-3，#97）
    if total > limit:
        extra = "（劇情夥伴佔了隊友位）" if char.companions else ""
        raise WorldActionError(f"最多帶 {limit} 名隊友{extra}（收到 {total} 名）")
    if len(set(chosen)) != len(chosen):
        raise WorldActionError("同一名傭兵不能雇兩次")
    if len(set(shadows)) != len(shadows):
        raise WorldActionError("同一個影子不能借兩次")
    known = table.by_id()
    unknown = [m for m in chosen if m not in known]
    if unknown:
        raise WorldActionError(f"沒有這名傭兵：{', '.join(unknown)}")
    if char.character_id in shadows:
        raise WorldActionError("不能借自己的影子")
    missing = [s for s in shadows if world.shadow_of(s) is None]
    if missing:
        raise WorldActionError(f"沒有這個影子：{', '.join(missing)}")
    members = {*chosen, *shadows}
    strangers = sorted(k for k in action.ai if k not in members)
    if strangers:
        raise WorldActionError(f"打法只能設定給隊伍成員：{', '.join(strangers)}")
    bad = sorted(v for v in action.ai.values() if v not in table.ai_choices)
    if bad:
        raise WorldActionError(f"沒有這種打法：{', '.join(bad)}")


def hire(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: HireAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """``hire`` 動作：在城鎮把隊友（傭兵＋影子）整組換掉（免費）；空＝獨行。"""
    table = mercenary_table(library)
    problem = hire_problem(library, char)
    if problem is not None:
        raise WorldActionError(f"不能換隊友：{problem}")
    _check_members(table, world, char, action)
    snapshots = []
    for owner in action.shadows:
        record = world.shadow_of(owner)
        assert record is not None
        snapshots.append(record.snapshot)
    ai = dict(sorted(action.ai.items()))
    flags = char.story_flags
    escort = table.escort
    if escort is not None and escort.mercenary not in action.mercenaries:
        flags = tuple(sorted({*flags, ESCORT_PARTED}))  # OB-7（#154）：護衛換下過
    char = char.model_copy(
        update={
            "mercenaries": action.mercenaries,
            "shadows": tuple(snapshots),
            "party_ai": ai,
            "companion_bench": (),  # 自己換過隊伍：夥伴離隊時不再還原（5C-3）
            "story_flags": flags,
        }
    )
    event = PartyChangedEvent(
        mercenaries=action.mercenaries,
        shadows=action.shadows,
        shadow_names=tuple(s.hero.name_zh for s in snapshots),
        ai=ai,
    )
    return char, (event,)


def set_shadow_ai(
    library: ContentLibrary, char: CharacterState, action: ShadowAiAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """``shadow_ai`` 動作：在城鎮設定自己影子的預設打法（#102）。"""
    table = mercenary_table(library)
    problem = hire_problem(library, char)
    if problem is not None:
        raise WorldActionError(f"不能改影子的打法：{problem}")
    if action.profile is not None and action.profile not in table.ai_choices:
        raise WorldActionError(f"沒有這種打法：{action.profile}")
    char = char.model_copy(update={"shadow_ai": action.profile})
    return char, (ShadowAiChangedEvent(profile=action.profile),)


def party_mercenaries(library: ContentLibrary, char: CharacterState) -> tuple[MercenaryDef, ...]:
    """隊伍裡的傭兵定義（依出場順序）。名單不見了或傭兵被移除時拋 :class:`WorldError`
    （內容錯誤，不是玩家的動作錯）。"""
    if not char.mercenaries:
        return ()
    table = library.world_mercenaries
    if table is None:
        raise WorldError("內容庫沒有系統傭兵名單，但角色帶著傭兵")
    known = table.by_id()
    missing = [m for m in char.mercenaries if m not in known]
    if missing:
        raise WorldError(f"傭兵名單沒有：{', '.join(missing)}")
    return tuple(known[m] for m in char.mercenaries)


def slot_capped(library: ContentLibrary, template: UnitTemplate) -> UnitTemplate:
    """技能照欄位上限挑（玩法 PM 定 ②）：依原本順序，加進去會違反欄位上限（主動 6、被動 3、反應
    1、姿態 1）、專精互斥或傳說上限的就跳過；被跳過的反應技能，``reactions`` 規則一併拿掉。"""
    slots = library.ruleset.core.skill_slots
    chosen: list[str] = []
    defs: list[SkillDef] = []
    for skill_id in template.skills:
        skill = library.skills[skill_id]
        if not skill_slot_problems([*defs, skill], slots):
            chosen.append(skill_id)
            defs.append(skill)
    if len(chosen) == len(template.skills):
        return template
    update: dict[str, object] = {"skills": tuple(chosen)}
    if template.reactions is not None:
        update["reactions"] = tuple(r for r in template.reactions if r.reaction in chosen)
    return template.model_copy(update=update)


def is_escort(library: ContentLibrary, char: CharacterState, mercenary: str) -> bool:
    """``mercenary`` 是不是開局帶來、一直沒換下過的護衛（OB-7，#154：隊伍面板的來歷只給這一位）。"""
    table = library.world_mercenaries
    escort = None if table is None else table.escort
    return (
        escort is not None
        and escort.mercenary == mercenary
        and ESCORT_PARTED not in char.story_flags
    )


def default_party(library: ContentLibrary) -> tuple[str, ...]:
    """新角色一開始帶的傭兵（``default_party``；沒有名單＝獨行）。"""
    table = library.world_mercenaries
    return () if table is None else table.default_party


def party_spawns(library: ContentLibrary, char: CharacterState) -> tuple[UnitSpawn, ...]:
    """隊伍傭兵的出場設定（1 級基準，還沒照主角等級成長；依出場順序）。"""
    builds = library.builds.by_id()
    spawns: list[UnitSpawn] = []
    for merc in party_mercenaries(library, char):
        base = builds[merc.build].hero
        update: dict[str, object] = {"id": merc.id, "name_zh": merc.name_zh}
        profile = char.party_ai.get(merc.id)
        if profile is not None:
            update["ai_profile"] = profile
        template = slot_capped(library, base).model_copy(update=update)
        worn = mercenary_equipment(library, merc.id, base, char.level)  # 系統裝備（5D-2，20.5）
        spawns.append(
            UnitSpawn(
                template=template,
                weapon=library.weapon_of(template),
                equipment=item_loadout(library, worn),
                team=Team.ALLY,
            )
        )
    return tuple(spawns)


def shadow_spawns(
    library: ContentLibrary, char: CharacterState
) -> tuple[tuple[UnitSpawn, ...], tuple[SkillDef, ...]]:
    """借來的影子的出場設定（壓到招募者的上限，#87）與要加進規則包的技能。"""
    spawns: list[UnitSpawn] = []
    extra: dict[str, SkillDef] = {}
    for snapshot in char.shadows:
        profile = char.party_ai.get(snapshot.owner)
        spawn, skills = shadow_spawn(library, snapshot, char.level, profile)
        spawns.append(spawn)
        extra.update((s.id, s) for s in skills)
    return tuple(spawns), tuple(extra[k] for k in sorted(extra))


def season_boss_problem(char: CharacterState) -> str | None:
    """隊伍能不能打賽季 Boss（#87、#100：只准系統傭兵）；5F-3 開 Boss 戰時檢查。"""
    return SEASON_BOSS_PROBLEM if char.shadows else None
