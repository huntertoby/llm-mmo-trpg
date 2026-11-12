"""新手引導的畫面資料（Phase 6F-2；09 9.6.9 #99、#125，玩法 PM 筆記 U1～U4）。

- :func:`guide_view`：任務追蹤器沒有任務時的指引。在主城、還沒到過新手區＝「到霧渡鎮找渡婆婆」
  ＋開場兩句（#125）；到了新手區、還沒接新手任務＝「找頭上有『！』的渡婆婆說話」。
- :func:`with_routes`：任務日誌每條進行中任務的目前這一步，往哪個出口走（方向＋下一個地點；U3）；
  新手任務鏈完成前，主線加「建議先完成霧渡新手路」（U4，:func:`with_advice` 給可以接的任務用）。
- :func:`battle_hints`：這場戰鬥可能出現的短提示（#99）：進行中任務的目前這一步在這裡打贏時的
  ``teach``，加上 ``newcomer.yaml`` 的通用提示。觸發由畫面判斷；只影響畫面。
- :func:`lesson_view`：教學。6F-4（#133）：升到 2 級、回到導師葛蘭所在的城鎮、還有沒分配的屬性點＝
  **先教配點**（``allocate``：葛蘭兩句、推薦配法、六個屬性的說明；看過或略過記成
  ``lesson:allocate``）；
  OB-3（#150）：走新開局流程的角色正式選定後才教（教重配再分），略過（``lesson:allocate_skip``）
  與上完分開記，略過後第一次進城鎮或營火再提示一次；
  之後才接 6F-2 的閃現教學（#132）：新手任務第 1 步完成、在城鎮、還沒閃現過、有靈感點、有戰鬥中
  用過的招＝第一次閃現的引導（說書人＋導師）；升到 ``reflash_level`` 級、閃現過＝改教重閃。閃現本身
  照 06 6.34.3 的規則由成長面板做（不另給點）；每種只跳一次（記在角色的 ``hints_seen``）、可以略過。
- :func:`level_up_view`：升級畫面（6F-4 C2）：等級比看過的高就出，文字照 ``newcomer.yaml``。
- :func:`hints_view`：出過的提示與「不再顯示」（6F-2b：記在角色身上）。

只讀內容與角色狀態，不改任何東西；清單依內容順序或 ID 排序（守則 2）。
"""

from __future__ import annotations

from collections.abc import Iterable

from trpg.api.world_growth_view import skill_names
from trpg.api.world_schemas import (
    AttributeNoteView,
    BattleHintView,
    GuideView,
    HintsStateView,
    LessonView,
    LevelUpView,
    OpeningLineView,
)
from trpg.api.world_story_schemas import QuestHereView, QuestLogView
from trpg.content.fields import FieldExit, FieldMapDef
from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.content.skills import SkillDef
from trpg.content.world_map import LocationMapDef
from trpg.content.world_newcomer import BattleHint, NewcomerContent, OpeningLine
from trpg.content.world_quests import AnyOf, AtLocation, QuestCondition, QuestDef, WinBattle
from trpg.roguelite.start import recommended_level_up
from trpg.shared.types import Attribute
from trpg.world.atlas import free_first_teleport
from trpg.world.common import here, in_capital, rules_of
from trpg.world.growth import at_service, flash_blocked_zh
from trpg.world.opening_choice import choice_problem, full_allocation, starter_steps_done
from trpg.world.opening_limits import in_starter_period
from trpg.world.opening_reselect import reselect_window_problem
from trpg.world.quests import has_flashed, quest_table
from trpg.world.state import CharacterState

__all__ = [
    "LESSON_SEEN_PREFIX",
    "OPENING_SEEN",
    "PRACTICE_SEEN",
    "battle_hints",
    "guide_view",
    "hints_view",
    "lesson_seen",
    "lesson_view",
    "level_up_view",
    "with_advice",
    "with_routes",
]

OPENING_SEEN = "opening"
"""``hints_seen`` 裡「開場看過了」的 ID（6F-2b）。"""
LESSON_SEEN_PREFIX = "lesson:"
"""``hints_seen`` 裡教學看過了的 ID 前綴（``lesson:allocate``、``lesson:flash``、
``lesson:reflash``）。"""
PRACTICE_SEEN = "range:practice"
"""``hints_seen`` 裡「點開過工坊師傅的『靶場試玩』」的 ID（PR-2a：師傅選單第 1 列的「新」小牌；
前端點開時送既有的 ``hint_seen``，「重新顯示提示」會清掉）。"""


def lesson_seen(char: CharacterState, kind: str) -> bool:
    return f"{LESSON_SEEN_PREFIX}{kind}" in char.hints_seen


def hints_view(char: CharacterState) -> HintsStateView:
    """出過的提示與「不再顯示」（6F-2b：記在角色身上）。"""
    return HintsStateView(seen=char.hints_seen, off=char.hints_off)


# ---------------------------------------------------------------------------
# 指引（U2、#125）
# ---------------------------------------------------------------------------


def _starters(library: ContentLibrary, region: str) -> list[QuestDef]:
    table = quest_table(library, region)
    return [] if table is None else [q for q in table.quests if q.kind == "starter"]


def guide_view(library: ContentLibrary, char: CharacterState) -> GuideView | None:
    newcomer = library.world_newcomer
    if newcomer is None:
        return None
    if _should_choose(library, newcomer, char):
        # OB-5（#150 第 3 點）：入門期打完新手前兩步＝回導師那裡正式選定
        return GuideView(text_zh=newcomer.guide_choose_zh)
    if free_first_teleport(library, char, newcomer.start_region):
        opening = tuple(
            OpeningLineView(speaker_zh=line.speaker_zh, text_zh=line.text_zh)
            for line in newcomer.opening
        )
        return GuideView(
            text_zh=newcomer.guide_capital_zh,
            how_zh=newcomer.guide_capital_how_zh,
            opening=opening,
        )
    if char.region != newcomer.start_region:
        return None
    starters = _starters(library, char.region)
    if starters and all(char.quest_state(q.id) is None for q in starters):
        return GuideView(text_zh=newcomer.guide_town_zh)
    return None


def _should_choose(
    library: ContentLibrary, newcomer: NewcomerContent, char: CharacterState
) -> bool:
    """入門期、新手任務前兩步都打完了（接下來要做的是正式選定）。"""
    opening = char.opening
    if opening is None or opening.stage != "starter" or not newcomer.guide_choose_zh:
        return False
    return starter_steps_done(library, char)


# ---------------------------------------------------------------------------
# 主線的建議（U4）
# ---------------------------------------------------------------------------


def _advice(library: ContentLibrary, char: CharacterState, kind: str) -> str | None:
    newcomer = library.world_newcomer
    if newcomer is None or kind != "main":
        return None
    for starter in _starters(library, char.region):
        state = char.quest_state(starter.id)
        if state is None or not state.done:
            return newcomer.main_advice_zh.format(quest=starter.name_zh)
    return None


def _kind_of(library: ContentLibrary, region: str, quest_id: str) -> str | None:
    table = quest_table(library, region)
    defn = None if table is None else table.quest_by_id().get(quest_id)
    return None if defn is None else defn.kind


def with_advice(
    library: ContentLibrary, char: CharacterState, offers: Iterable[QuestHereView]
) -> tuple[QuestHereView, ...]:
    out: list[QuestHereView] = []
    for offer in offers:
        kind = _kind_of(library, char.region, offer.id)
        advice = None if kind is None else _advice(library, char, kind)
        out.append(offer if advice is None else offer.model_copy(update={"advice_zh": advice}))
    return tuple(out)


# ---------------------------------------------------------------------------
# 任務追蹤的方向（U3）
# ---------------------------------------------------------------------------


def _targets(conditions: Iterable[QuestCondition]) -> set[str]:
    out: set[str] = set()
    for condition in conditions:
        leaves = condition.conditions if isinstance(condition, AnyOf) else (condition,)
        for leaf in leaves:
            if isinstance(leaf, AtLocation | WinBattle) and leaf.location is not None:
                out.add(leaf.location)
    return out


def _next_hop(
    world_map: LocationMapDef, char: CharacterState, targets: set[str]
) -> tuple[str, str] | None:
    """從目前地點走向最近的目標：（下一個地點, 目標）。只走看得到的地點（隱藏地點發現後才算）；
    鄰居依 ID 排序、同距離取 ID 小的目標（確定性）。"""
    visible = {
        loc.id
        for loc in world_map.locations
        if not loc.hidden or char.has_revealed(world_map.region, loc.id)
    }
    start = char.location
    if start not in visible:
        visible.add(start)
    prev: dict[str, str | None] = {start: None}
    frontier = [start]
    while frontier:
        reached = sorted(t for t in frontier if t in targets)
        if reached:
            goal = reached[0]
            hop = goal
            while prev[hop] != start and prev[hop] is not None:
                hop = prev[hop]  # type: ignore[assignment]
            return hop, goal
        nxt: list[str] = []
        for cur in frontier:
            for near in sorted(world_map.neighbors(cur)):
                if near in prev or near not in visible:
                    continue
                prev[near] = cur
                nxt.append(near)
        frontier = nxt
    return None


def _direction(found: FieldMapDef, exit_: FieldExit) -> str:
    """出口在地圖的哪一邊（x 越大越東、y 越小越北）。"""
    width, height = found.size
    mx = sum(x for x, _ in exit_.at) / len(exit_.at)
    my = sum(y for _, y in exit_.at) / len(exit_.at)
    dx = mx - (width - 1) / 2
    dy = my - (height - 1) / 2
    if abs(dx) * height >= abs(dy) * width:
        return "東" if dx > 0 else "西"
    return "南" if dy > 0 else "北"


def _route(library: ContentLibrary, char: CharacterState, targets: set[str]) -> str | None:
    world_map = library.location_map(char.region)
    if world_map is None or not targets or char.location in targets:
        return None
    if char.location not in world_map.location_by_id():
        return None
    found = _next_hop(world_map, char, targets)
    if found is None:
        return None
    hop, goal = found
    names = world_map.location_by_id()
    hop_name, goal_name = names[hop].name_zh, names[goal].name_zh
    where = hop_name if hop == goal else f"{hop_name}（再往{goal_name}）"
    outdoor = library.outdoor_map(char.region, char.location)
    exit_ = None
    if outdoor is not None:
        exit_ = next(
            (e for e in outdoor.exits if e.to == hop and e.region in (None, char.region)), None
        )
    if outdoor is None or exit_ is None:
        return f"往{where}"
    return f"往{_direction(outdoor, exit_)}邊的出口 → {where}"


def with_routes(
    library: ContentLibrary, char: CharacterState, quests: Iterable[QuestLogView]
) -> tuple[QuestLogView, ...]:
    table = quest_table(library, char.region)
    defs = {} if table is None else table.quest_by_id()
    out: list[QuestLogView] = []
    for view in quests:
        defn = defs.get(view.id)
        state = char.quest_state(view.id)
        if defn is None or state is None or state.done or state.steps_done >= len(defn.steps):
            out.append(view)
            continue
        step = defn.steps[state.steps_done]
        update = {
            "route_zh": _route(library, char, _targets(step.when)),
            "advice_zh": _advice(library, char, defn.kind),
        }
        out.append(view.model_copy(update=update))
    return tuple(out)


# ---------------------------------------------------------------------------
# 戰鬥短提示（U1、#99）
# ---------------------------------------------------------------------------


def _fights_here(condition: QuestCondition, location: str) -> bool:
    leaves = condition.conditions if isinstance(condition, AnyOf) else (condition,)
    return any(isinstance(leaf, WinBattle) and leaf.location in (None, location) for leaf in leaves)


def _hint_view(library: ContentLibrary, hint: BattleHint) -> BattleHintView:
    terrains: tuple[str, ...] = ()
    if hint.trigger == "lethal_terrain":
        terrains = tuple(sorted(t.id for t in library.ruleset.terrain.terrain if t.deadly))
    return BattleHintView(id=hint.id, trigger=hint.trigger, text_zh=hint.text_zh, terrains=terrains)


def battle_hints(library: ContentLibrary, char: CharacterState) -> tuple[BattleHintView, ...]:
    hints: list[BattleHint] = []
    table = quest_table(library, char.region)
    for defn in () if table is None else table.quests:
        state = char.quest_state(defn.id)
        if state is None or state.done or state.steps_done >= len(defn.steps):
            continue
        step = defn.steps[state.steps_done]
        if any(_fights_here(c, char.location) for c in step.when):
            hints.extend(step.teach)
    newcomer = library.world_newcomer
    if newcomer is not None:
        hints.extend(newcomer.battle_hints)
    views = tuple(_hint_view(library, h) for h in hints)
    if newcomer is None or not newcomer.starter_teach_note_zh or not in_starter_period(char):
        return views
    # OB-5（玩法 PM 定稿）：入門期放不出這幾則提示講的招，句尾加一句
    noted = set(newcomer.starter_teach_hints)
    return tuple(
        v.model_copy(update={"text_zh": v.text_zh + newcomer.starter_teach_note_zh})
        if v.id in noted
        else v
        for v in views
    )


# ---------------------------------------------------------------------------
# 閃現教學（#132）
# ---------------------------------------------------------------------------


def _lines(lines: Iterable[OpeningLine]) -> tuple[OpeningLineView, ...]:
    return tuple(
        OpeningLineView(speaker_zh=line.speaker_zh, text_zh=line.text_zh) for line in lines
    )


def _starter_step_done(library: ContentLibrary, char: CharacterState, region: str) -> bool:
    return any(
        (state := char.quest_state(q.id)) is not None and (state.done or state.steps_done >= 1)
        for q in _starters(library, region)
    )


def _reflash_lesson(
    newcomer: NewcomerContent, char: CharacterState, names: dict[str, str]
) -> LessonView | None:
    if char.level < newcomer.reflash_level or not newcomer.reflash_lesson:
        return None
    flashed = sorted(names.get(k, k) for k, s in char.flash.items() if s.records)
    return LessonView(
        kind="reflash", lines=_lines(newcomer.reflash_lesson), skills_zh=tuple(flashed)
    )


def _flash_lesson(
    library: ContentLibrary, newcomer: NewcomerContent, char: CharacterState, names: dict[str, str]
) -> LessonView | None:
    ready = newcomer.flash_lesson and char.insight >= 1
    if not ready or not _starter_step_done(library, char, newcomer.start_region):
        return None
    if flash_blocked_zh(char) is not None:
        # OB-3（#150 第 6 點）：開局還沒結束的角色 4 級前不能閃現——第 3 步打完（升到 4 級）回
        # 霧渡鎮才引導；已完成開局的舊角色照舊在第 1 步之後
        return None
    used = sorted(
        names.get(k, k)
        for k, s in char.flash.items()
        if s.used and not s.records and not s.complete
    )
    if not used:
        return None
    return LessonView(kind="flash", lines=_lines(newcomer.flash_lesson), skills_zh=tuple(used))


def _skill_defs(library: ContentLibrary, char: CharacterState) -> dict[str, SkillDef]:
    found = dict(player_skills(library))
    for skill in (*char.flash_bases, *char.generated_skills):
        found[skill.id] = skill
    return found


def _mentor_town(library: ContentLibrary, newcomer: NewcomerContent) -> tuple[str, str] | None:
    """駐堂導師所在的（區域, 地點）；沒有設定＝``None``（任何城鎮都教）。"""
    if newcomer.mentor_npc is None:
        return None
    table = library.world_event_content.npcs.get(newcomer.start_region)
    card = None if table is None else table.npc_by_id().get(newcomer.mentor_npc)
    return None if card is None else (newcomer.start_region, card.location)


def _allocate_view(
    library: ContentLibrary,
    newcomer: NewcomerContent,
    char: CharacterState,
    *,
    respec: bool = False,
    reminder: bool = False,
) -> LessonView:
    """配點教學的畫面資料。``respec``（OB-3）：點數已經全部照推薦配好，教的是重配再自己分——
    能分的是全部點數，推薦＝用起始兩招從頭照推薦配的結果（07 7.2）。"""
    defs = _skill_defs(library, char)
    starters = [defs[s] for s in char.hero.skills[:2] if s in defs]  # 起始兩招（07 7.2）
    weapon = library.weapons.get(char.hero.weapon)
    points = char.attribute_points
    if respec:
        points += sum(char.attribute_spent.values())
    if respec and weapon is not None:
        recommended = full_allocation(library, starters, weapon, points)
    else:
        recommended = recommended_level_up(starters, weapon, char.hero.attributes, points)
    lines = newcomer.allocate_lesson
    done = newcomer.allocate_done_zh
    if respec:  # OB-5：走新開局流程的角色用定稿的那一組字（空＝沿用舊的）
        lines = newcomer.allocate_respec_lesson or lines
        done = newcomer.allocate_respec_done_zh or done
    if reminder and newcomer.allocate_again_lesson:
        lines = newcomer.allocate_again_lesson
    return LessonView(
        kind="allocate",
        lines=_lines(lines),
        points=points,
        start_points=0 if respec else library.roguelite.start_free_points,
        recommended=recommended,
        recommended_zh="、".join(f"{a.display_name} +{n}" for a, n in recommended.items()),
        done_zh=done or None,
        skip_zh=newcomer.allocate_skip_zh or None,
        notes=tuple(
            AttributeNoteView(attr=a, text_zh=newcomer.attribute_notes[a])
            for a in Attribute
            if a in newcomer.attribute_notes
        ),
        respec=respec,
        reminder=reminder,
        reselect_reminder=_reselect_reminder(newcomer, char) if respec else (),
    )


def _reselect_reminder(
    newcomer: NewcomerContent, char: CharacterState
) -> tuple[OpeningLineView, ...]:
    """OB-6 Q2：正式選定後配點教學收尾彈窗的第二段（葛蘭提醒 4 級前可重選）；沒有資格時空。"""
    if newcomer.range is None or reselect_window_problem(char) is not None:
        return ()
    return _lines(newcomer.range.reselect_reminder)


def _allocate_reminder(
    library: ContentLibrary, newcomer: NewcomerContent, char: CharacterState
) -> LessonView | None:
    """略過配點教學之後的再提示（OB-3，09 9.6.9）：略過後離開過（換過地點）、第一次進城鎮或營火
    時出一次。"""
    if not newcomer.allocate_lesson or lesson_seen(char, "allocate"):
        return None
    waiting = (
        lesson_seen(char, "allocate_skip")
        and lesson_seen(char, "allocate_left")
        and not lesson_seen(char, "allocate_again")
    )
    busy = bool(char.pending_offers) or char.pending_encounter is not None
    if not waiting or busy or not at_service(library, char):
        return None
    if char.attribute_points + sum(char.attribute_spent.values()) <= 0:
        return None
    return _allocate_view(library, newcomer, char, respec=True, reminder=True)


def _allocate_lesson(
    library: ContentLibrary, newcomer: NewcomerContent, char: CharacterState
) -> LessonView | None:
    """配點教學（#133；人在城鎮）。已完成開局的舊角色：升到 2 級、在導師所在的城鎮、還有沒分配的
    屬性點、還沒上過。走新開局流程的角色（OB-3，#150）：入門期不出，正式選定、三選一選完之後在導師
    所在的城鎮出（點數都已照推薦配好，教重配再分）；略過之後改由 :func:`_allocate_reminder` 再提示
    一次。"""
    if not newcomer.allocate_lesson or lesson_seen(char, "allocate"):
        return None
    if lesson_seen(char, "allocate_skip"):
        return _allocate_reminder(library, newcomer, char)
    town = _mentor_town(library, newcomer)
    if town is not None and (char.region, char.location) != town:
        return None
    if char.opening is not None:
        ready = char.opening.stage == "chosen" and not char.pending_offers
        return _allocate_view(library, newcomer, char, respec=True) if ready else None
    ready = char.level >= 2 and char.attribute_points > 0  # noqa: PLR2004 - 2 級＝第一次升級
    return _allocate_view(library, newcomer, char) if ready else None


def _choose_lesson_ready(
    library: ContentLibrary, newcomer: NewcomerContent, char: CharacterState
) -> bool:
    """可以正式選定了（OB-5，#150 第 3 點）：入門期、新手前兩步打完、人在導師的城鎮或主城、沒有
    遭遇、沒有待選的三選一。條件就是 :func:`trpg.world.opening_choice.choice_problem`。"""
    if newcomer.range is None or char.opening is None or char.pending_offers:
        return False
    return choice_problem(library, char) is None


def lesson_view(library: ContentLibrary, char: CharacterState) -> LessonView | None:
    """配點教學優先（#133，6F-4）；之後閃現過＝重閃教學（到 ``reflash_level`` 級才有）；沒閃過＝
    第一次閃現的引導（等級不限：3 級還沒閃過的人照樣先教閃現）。看過的種類（``hints_seen`` 的
    ``lesson:<種類>``）不再出。"""
    newcomer = library.world_newcomer
    if newcomer is None or char.pending_flash is not None:
        return None
    if _choose_lesson_ready(library, newcomer, char):
        arena = newcomer.range
        said = () if arena is None else (arena.choose_capital if in_capital(char) else arena.choose)
        return LessonView(kind="choose", lines=_lines(said))
    if here(library, char).kind != "town":  # 營火：只有略過配點教學後的再提示（OB-3）
        return _allocate_reminder(library, newcomer, char)
    allocate = _allocate_lesson(library, newcomer, char)
    if allocate is not None:
        return allocate
    names = skill_names(library, char)
    lesson = (
        _reflash_lesson(newcomer, char, names)
        if has_flashed(char)
        else _flash_lesson(library, newcomer, char, names)
    )
    if lesson is None or lesson_seen(char, lesson.kind):
        return None
    return lesson


# ---------------------------------------------------------------------------
# 升級畫面（6F-4 C2）
# ---------------------------------------------------------------------------


def _starter_level_up(
    library: ContentLibrary, newcomer: NewcomerContent, char: CharacterState
) -> str | None:
    """入門期的升級畫面（OB-5，玩法 PM 定稿）：屬性點已自動配好；新手前兩步打完時改成指示回導師
    那裡正式選定。不在入門期、或內容沒寫這兩句＝``None``（照舊）。"""
    opening = char.opening
    if opening is None or opening.stage != "starter":
        return None
    text = newcomer.level_up_starter_zh
    if newcomer.level_up_choose_zh and starter_steps_done(library, char):
        text = newcomer.level_up_choose_zh
    if not text:
        return None
    return text.format(
        level=char.level,
        points=library.roguelite.attribute_points_per_level,
        insight=rules_of(library).hero_growth.insight_per_level,
    )


def level_up_view(library: ContentLibrary, char: CharacterState) -> LevelUpView | None:
    """等級比看過的（``level_seen``）高就出：「升到 N 級：屬性點 +2、靈感 +2。」還沒上過配點教學時
    接「回霧渡鎮找導師堂的葛蘭，學怎麼配點。」"""
    newcomer = library.world_newcomer
    if newcomer is None or not newcomer.level_up_zh or char.level <= char.level_seen:
        return None
    starter = _starter_level_up(library, newcomer, char)
    if starter is not None:
        return LevelUpView(level=char.level, text_zh=starter)
    text = newcomer.level_up_zh.format(
        level=char.level,
        points=library.roguelite.attribute_points_per_level,
        insight=rules_of(library).hero_growth.insight_per_level,
    )
    if newcomer.allocate_lesson and not lesson_seen(char, "allocate"):
        text += newcomer.level_up_mentor_zh
    return LevelUpView(level=char.level, text_zh=text)
