"""正式選定（Phase OB-2，#150 第 3 點；21 21.5、06 6.27.3、07 7.2）。

世界動作 ``opening_confirm`` 依開局階段分流（:func:`apply_opening_confirm`）：

- ``pick_class``：舊的一次選定（:func:`trpg.world.opening.apply_opening_confirm`；OB-5 前端換掉之前
  照收）。
- ``starter``：**正式選定**（:func:`apply_formal_choice`）。條件（:func:`choice_problem`）：新手任務
  打完前 :data:`STARTER_STEPS` 步、人在葛蘭所在的城鎮或主城、沒有待處理的遭遇。
- ``chosen``：開局閘門擋掉（4 級前的免費重選是 OB-3 的另一個動作）。

正式選定的順序（每一步的理由見 ``docs/phases/PhaseOB-2報告.md``）：

1. 檢查全部做完才動狀態（不合法拋 :class:`WorldActionError`，狀態不變）。
2. 依開局種子取起始 2 招（:func:`~trpg.roguelite.start.new_keyword_run`，和靶場預覽同一套）。
3. 收回入門招：裝備中與備用的入門招，連同它們的 ``flash``、``flash_bases``、``skill_usage``、
   ``skill_regions``、``generated_skills``（入門招一律從 ``range.demos`` 讀）。
4. 換武器、依新武器的大類重建基礎值（名字、種族、外觀照舊）；雙手或成對武器把副手收進背包。
5. 全部屬性點（開局點＋升級得到的）照推薦配法重配，全數寫進 ``attribute_spent``。
6. 最大 HP、法力、耐力的變化走 ``with_hp_change``，再把 HP、法力回滿。
7. 起始技能照角色目前的階級重配（一般是 1 階，不變）。
8. ``opening`` 轉 ``chosen``：記下武器、關鍵字、起始 2 招（``granted_skills``）。
9. 出入門期保留的三選一的第 1 組；玩家選完一組才出下一組（OB-3，
   :func:`trpg.world.quests.issue_deferred_offers`、``take_offer``），兩組不會拿到同一招。

純函式、確定性：不讀時間、不用全域亂數；起始技能用開局種子，三選一用角色技能種子。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Final

from trpg.content.battle import UnitTemplate, WeaponDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.attributes import merge_spent
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.progress import with_hp_change
from trpg.roguelite.start import (
    apply_allocation,
    new_keyword_run,
    recommended_allocation,
    recommended_level_up,
    start_hero,
    start_weapons,
)
from trpg.roguelite.state import RunState
from trpg.shared.types import Attribute
from trpg.world.actions import OpeningConfirmAction, OpeningConfirmedEvent, WorldEvent
from trpg.world.common import here, in_capital, max_hp, max_mana
from trpg.world.errors import WorldActionError
from trpg.world.growth import as_run, from_run, sync_tier
from trpg.world.inventory import room_problem
from trpg.world.opening import apply_opening_confirm as _apply_first_choice
from trpg.world.opening import mentor_town, starter_skill_ids
from trpg.world.opening_limits import STARTER_STEPS
from trpg.world.quests import issue_deferred_offers, quest_table
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "STARTER_STEPS",
    "apply_formal_choice",
    "apply_opening_confirm",
    "choice_problem",
    "chosen_hero",
    "full_allocation",
    "place_ok",
    "starter_steps_done",
    "stow_off_hand",
    "with_starting_skills",
    "without_skills",
]

_NOT_YET_ZH: Final = "還不能正式選定：打完新手第 2 步，回霧渡鎮找葛蘭"
_PLACE_ZH: Final = "正式選定要回霧渡鎮找葛蘭，或到主城的工坊靶場"
_OFF_HAND: Final = "off_hand"


def _steps_left(library: ContentLibrary, char: CharacterState) -> bool:
    """新手區的新手任務（``kind: starter``）還沒打完前 :data:`STARTER_STEPS` 步（沒接也算沒打完）。
    內容沒有新手任務時不擋。"""
    newcomer = library.world_newcomer
    table = None if newcomer is None else quest_table(library, newcomer.start_region)
    if table is None:
        return False
    for quest in table.quests:
        if quest.kind != "starter":
            continue
        state = char.quest_state(quest.id)
        done = 0 if state is None else state.steps_done
        if done < min(STARTER_STEPS, len(quest.steps)):
            return True
    return False


def starter_steps_done(library: ContentLibrary, char: CharacterState) -> bool:
    """新手任務前 :data:`STARTER_STEPS` 步都打完了（畫面的指引用）。"""
    return not _steps_left(library, char)


def place_ok(library: ContentLibrary, char: CharacterState) -> bool:
    """葛蘭所在的城鎮或主城（21.5 第 3 點）；沒有設定導師時任何城鎮都可以（同配點教學）。"""
    if in_capital(char):
        return True
    town = mentor_town(library)
    if town is None:
        return here(library, char).kind == "town"
    return (char.region, char.location) == town


def choice_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """入門期的角色現在不能正式選定的原因（中文）；可以時 ``None``。不在入門期也回原因。"""
    if char.opening is None or char.opening.stage != "starter":
        return "不在入門期"
    if _steps_left(library, char):
        return _NOT_YET_ZH
    if not place_ok(library, char):
        return _PLACE_ZH
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能正式選定"
    return None


def full_allocation(
    library: ContentLibrary, skills: Sequence[SkillDef], weapon: WeaponDef, total: int
) -> dict[Attribute, int]:
    """``total`` 點全部照推薦配法（07 7.2，#133）：開局的點數照 :func:`recommended_allocation`，其餘
    每級一份照 :func:`recommended_level_up`（兩招屬性不同時給目前比較低的）——等於用這把武器與這兩招
    從 1 級一路照推薦升上來的結果。"""
    rules = library.roguelite
    start = min(total, rules.start_free_points)
    allocation = dict(recommended_allocation(skills, weapon, start)) if start > 0 else {}
    left = total - start
    per_level = max(1, rules.attribute_points_per_level)
    while left > 0:
        points = min(per_level, left)
        current = {a: rules.base_attribute + allocation.get(a, 0) for a in Attribute}
        for attr, n in recommended_level_up(skills, weapon, current, points).items():
            allocation[attr] = allocation.get(attr, 0) + n
        left -= points
    return merge_spent({}, allocation)


def without_skills(char: CharacterState, skills: Iterable[str]) -> CharacterState:
    """收回 ``skills``（裝備中與備用）與它們的紀錄（閃現、用法、取得地點、生成技能）；其他的招
    留著。正式選定收回入門招、重選（OB-3）收回起始 2 招與新手三選一拿到的招共用。"""
    gone = set(skills)
    return char.model_copy(
        update={
            "hero": char.hero.model_copy(
                update={"skills": tuple(s for s in char.hero.skills if s not in gone)}
            ),
            "bench": tuple(s for s in char.bench if s not in gone),
            "flash": {k: v for k, v in char.flash.items() if k not in gone},
            "flash_bases": tuple(s for s in char.flash_bases if s.id not in gone),
            "skill_usage": {k: v for k, v in char.skill_usage.items() if k not in gone},
            "skill_regions": {k: v for k, v in char.skill_regions.items() if k not in gone},
            "generated_skills": tuple(s for s in char.generated_skills if s.id not in gone),
        }
    )


def stow_off_hand(
    library: ContentLibrary, char: CharacterState, weapon: WeaponDef
) -> CharacterState:
    """雙手或成對武器占用副手：穿著的副手收進背包（同換主手的規則）；背包放不下就不能選，訊息
    寫明是哪把武器、為什麼、差幾格（21.5「OB-2 補充」：提示原因）。"""
    if not (weapon.two_handed or weapon.paired) or _OFF_HAND not in char.equipment:
        return char
    equipment = dict(char.equipment)
    gear = (*char.gear, equipment.pop(_OFF_HAND))
    room = room_problem(library, char.bag, len(gear))
    if room is not None:
        raise WorldActionError(f"不能選{weapon.name_zh}：它占用副手，副手要收進背包，但{room}")
    return char.model_copy(update={"equipment": equipment, "gear": gear})


def chosen_hero(
    library: ContentLibrary,
    char: CharacterState,
    weapon: str,
    skills: Sequence[SkillDef],
    total: int,
) -> tuple[UnitTemplate, dict[Attribute, int]]:
    """正式的主角範本與配點：新武器大類的基礎值＋``skills``，``total`` 點照推薦重配；名字、種族、
    外觀照舊。"""
    allocation = full_allocation(library, skills, library.weapons[weapon], total)
    hero = apply_allocation(start_hero(library, weapon, [s.id for s in skills]), allocation)
    base = char.hero
    hero = hero.model_copy(update={"name_zh": base.name_zh, "race": base.race, "doll": base.doll})
    return hero, allocation


def with_starting_skills(
    library: ContentLibrary, world: WorldState, char: CharacterState, run: RunState
) -> tuple[CharacterState, tuple[str, ...]]:
    """把 ``run`` 的起始 2 招（1 階）照角色目前的階級重配後併進角色：排在裝備的最前面，其他來源的招
    照原順序排在後面。回傳角色與起始 2 招（重配後）的 ID。"""
    others = char.hero.skills
    alone = char.model_copy(
        update={
            "hero": char.hero.model_copy(update={"skills": run.hero.skills}),
            "bench": (),
            "generated_skills": run.generated_skills,
            "flash": {},
            "skill_usage": {},
            "skill_tier": run.skill_tier,
        }
    )
    alone, _events = sync_tier(library, world, alone)
    given = alone.hero.skills
    generated = {s.id: s for s in (*char.generated_skills, *alone.generated_skills)}
    merged = char.model_copy(
        update={
            "hero": char.hero.model_copy(update={"skills": (*given, *others)}),
            "generated_skills": tuple(generated[k] for k in sorted(generated)),
            "skill_tier": alone.skill_tier if char.skill_tier is None else char.skill_tier,
        }
    )
    return merged, given


def apply_formal_choice(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: OpeningConfirmAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """入門期的正式選定（順序見模組說明）；不合法拋 :class:`WorldActionError`，狀態不變。"""
    problem = choice_problem(library, char)
    if problem is not None:
        raise WorldActionError(problem)
    opening = char.opening
    assert opening is not None
    if action.weapon not in start_weapons(library):
        raise WorldActionError(f"靶場沒有這把武器：{action.weapon}")
    try:
        run = new_keyword_run(library, action.weapon, action.keywords, opening.seed, "recommended")
    except ChoiceError as exc:
        raise WorldActionError(str(exc)) from exc
    generated = {s.id: s for s in run.generated_skills}
    picked = [generated.get(s) or library.skills[s] for s in run.hero.skills]
    weapon = library.weapons[action.weapon]
    before = as_run(char)
    done = stow_off_hand(library, without_skills(char, starter_skill_ids(library, char)), weapon)
    # 入門期：開局的點數直接配在主角身上、不在 attribute_spent 裡（正式選定後才全數記進去）
    total = (
        library.roguelite.start_free_points
        + done.attribute_points
        + sum(done.attribute_spent.values())
    )
    hero, allocation = chosen_hero(library, done, action.weapon, picked, total)
    hero = hero.model_copy(update={"skills": done.hero.skills})  # 起始 2 招在下一步併進來
    done = done.model_copy(
        update={"hero": hero, "attribute_points": 0, "attribute_spent": allocation}
    )
    done, given = with_starting_skills(library, world, done, run)
    done = from_run(done, with_hp_change(library, before, as_run(done)))
    done = done.model_copy(update={"hp": max_hp(library, done), "mana": max_mana(library, done)})
    chosen = opening.model_copy(
        update={
            "stage": "chosen",
            "weapon_class": weapon.weapon_class,
            "weapon": action.weapon,
            "keywords": tuple(action.keywords),
            "granted_skills": given,
        }
    )
    done = done.model_copy(update={"opening": chosen})
    names = {s.id: s.name_zh for s in (*done.generated_skills, *picked)}
    confirmed = OpeningConfirmedEvent(
        weapon=action.weapon,
        keywords=tuple(action.keywords),
        skills=given,
        skill_names=tuple(names.get(s) or library.skills[s].name_zh for s in given),
    )
    done, offered = issue_deferred_offers(library, world, done)
    return done, (confirmed, *offered)


def apply_opening_confirm(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: OpeningConfirmAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """世界動作 ``opening_confirm``：入門期＝正式選定；選大類之前＝舊的一次選定。"""
    if char.opening is not None and char.opening.stage == "starter":
        return apply_formal_choice(library, world, char, action)
    return _apply_first_choice(library, world, char, action, now)
