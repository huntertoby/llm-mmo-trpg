"""說書人的外層組裝（Phase 5B-3；``docs/phases/Phase5計畫.md`` 15.1、15.2 第 7 點）。

``trpg.world`` 不匯入 narrative／llm、``trpg.narrative`` 不匯入 world（2.3），所以由這裡把兩邊
接起來：從世界狀態與內容庫組出說書人的請求（允許清單用
:func:`trpg.world.narration.story_choices`，和引擎核對同一個函式）→
:func:`trpg.narrative.storyteller.tell_story`（經 ``LLMClient``，不合法重試、連不上就降級）→
世界動作 :class:`~trpg.world.actions.NarrateAction`。組好的動作先用
:func:`~trpg.world.narration.narration_problems` 核對，不過就改用降級文字（一定通過），呼叫端再把它
交給世界的寫入佇列（``WorldStore.act``）寫進日誌。``client=None``＝模型關閉，直接降級。

路由與畫面在 5B-5；這裡只提供函式。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.world import WorldStyle
from trpg.content.world_events import EventSkeletonDef, NpcCardDef, ThreadDef
from trpg.content.world_narration import StoryAllowed, StoryScene
from trpg.content.world_situations import Outcome
from trpg.llm.client import LLMClient
from trpg.narrative.storyteller import StoryRequest, fallback_story, tell_story
from trpg.world.actions import (
    NarrateAction,
    SituationCheckEvent,
    SituationResultEvent,
    ThreadAddedEvent,
    WorldEvent,
)
from trpg.world.affinity import talk_entries
from trpg.world.clock import day_phase
from trpg.world.common import world_map_of
from trpg.world.narration import narration_problems, region_npcs, region_skeletons, story_choices
from trpg.world.situations import situation_template
from trpg.world.state import CharacterState, WorldState
from trpg.world.weather import weather_at

__all__ = ["chat_story", "event_story", "outcome_result_lines", "outcome_story", "situation_story"]

_OUTCOME_ZH: dict[Outcome, str] = {"success": "成功", "partial": "部分成功", "failure": "失敗"}


def _thread_defs(library: ContentLibrary) -> dict[str, ThreadDef]:
    out: dict[str, ThreadDef] = {}
    for table in library.world_event_content.events.values():
        out.update(table.thread_by_id())
    return out


def _request(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    allowed: StoryAllowed,
    *,
    scene: StoryScene,
    now: int,
    skeletons: tuple[EventSkeletonDef, ...] = (),
    first_npc: str | None = None,
    **extra: Any,
) -> StoryRequest:
    world_map = world_map_of(library, char.region)
    locations = world_map.location_by_id()
    templates = library.world_event_content.story
    cards = region_npcs(library, char.region)
    npc_ids = [n for n in allowed.all_npcs() if n in cards]
    if first_npc is not None:
        npc_ids = [first_npc, *(n for n in npc_ids if n != first_npc)]
    threads = _thread_defs(library)
    trigger = char.pending_event
    if scene == "event" and trigger is not None:
        weather, phase = trigger.weather, trigger.day_phase
    else:
        weather, phase = weather_at(library, world, char.region, now), day_phase(now)
    return StoryRequest(
        scene=scene,
        region_name=world_map.name_zh,
        tone="" if templates is None else templates.tones.get(char.region, ""),
        location_name=locations[char.location].name_zh,
        weather=weather,
        day_phase=phase,
        allowed=allowed,
        skeletons=skeletons,
        npcs=tuple(_card_for(library, char, cards[n]) for n in npc_ids),
        threads=tuple(threads[t] for t in allowed.threads if t in threads),
        location_names={loc: locations[loc].name_zh for loc in allowed.locations},
        **extra,
    )


def _card_for(library: ContentLibrary, char: CharacterState, card: NpcCardDef) -> NpcCardDef:
    """給說書人的人設卡：``hooks_zh`` 換成 NPC 依目前好感度能給的內容（5B-4，玩法 PM 定：中立給一般
    傳聞、友善給隱藏任務入口、信賴才說祕密；沒有＝空字串）。LLM 只能包裝這些。"""
    hooks = "；".join(e.text_zh for e in talk_entries(library, char, card.id))
    return card.model_copy(update={"hooks_zh": hooks})


def _finish(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    request: StoryRequest,
    *,
    client: LLMClient | None,
    now: int,
    style: WorldStyle | None,
    **fields: Any,
) -> NarrateAction:
    templates = library.world_event_content.story
    told = tell_story(client, request, templates=templates, world=style)
    action = NarrateAction(
        scene=request.scene,
        story=told.story,
        source=told.source,
        prompt_version=told.prompt_version,
        **fields,
    )
    if narration_problems(library, world, char, action, now):
        action = action.model_copy(
            update={"story": fallback_story(request, templates), "source": "fallback"}
        )
    return action


def event_story(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    client: LLMClient | None,
    now: int,
    *,
    style: WorldStyle | None = None,
) -> NarrateAction:
    """事件開場：從允許的候選挑骨架、填角色與動機、短旁白（09 9.6.7 #6、#7）。"""
    allowed = story_choices(library, world, char, "event", now=now)
    skeletons = region_skeletons(library, char.region)
    trigger = char.pending_event
    assert trigger is not None  # story_choices 已檢查
    request = _request(
        library,
        world,
        char,
        allowed,
        scene="event",
        now=now,
        skeletons=tuple(skeletons[s] for s in allowed.skeletons),
        default_skeleton=trigger.skeleton,
    )
    return _finish(library, world, char, request, client=client, now=now, style=style)


def situation_story(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    client: LLMClient | None,
    now: int,
    *,
    template: str,
    style: WorldStyle | None = None,
) -> NarrateAction:
    """情境判定前的情境敘述（9.6.4 第 1 點）。"""
    allowed = story_choices(library, world, char, "situation", now=now, template=template)
    defn = situation_template(library, char.region, template)
    request = _request(
        library,
        world,
        char,
        allowed,
        scene="situation",
        now=now,
        skeletons=(region_skeletons(library, char.region)[defn.skeleton],),
        template=defn,
    )
    return _finish(
        library, world, char, request, client=client, now=now, style=style, template=template
    )


def outcome_result_lines(library: ContentLibrary, events: Sequence[WorldEvent]) -> tuple[str, ...]:
    """判定事件的摘要（給說書人敘述結果；LLM 不能改）。"""
    threads = _thread_defs(library)
    lines: list[str] = []
    for event in events:
        if isinstance(event, SituationCheckEvent):
            lines.append(f"結果：{_OUTCOME_ZH[event.outcome]}")
        elif isinstance(event, SituationResultEvent):
            if event.hp_lost:
                lines.append("受了傷")
            if event.supplies_delta < 0:
                lines.append("失去了一些補給")
            elif event.supplies_delta > 0:
                lines.append("得到了一些補給")
            if event.next_battle:
                lines.append("下一場戰鬥會受到影響")
        elif isinstance(event, ThreadAddedEvent):
            defn = threads.get(event.thread)
            lines.append(f"留下線頭：{defn.text_zh if defn is not None else event.thread}")
    return tuple(lines)


def outcome_story(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    client: LLMClient | None,
    now: int,
    *,
    events: Sequence[WorldEvent],
    style: WorldStyle | None = None,
) -> NarrateAction:
    """情境判定的結果敘述（9.6.4 第 6 點）；``events`` 是那次判定的世界事件
    （含 ``situation_check``）。"""
    check = next(e for e in events if isinstance(e, SituationCheckEvent))
    allowed = story_choices(
        library, world, char, "outcome", now=now, template=check.template, outcome=check.outcome
    )
    defn = situation_template(library, char.region, check.template)
    request = _request(
        library,
        world,
        char,
        allowed,
        scene="outcome",
        now=now,
        skeletons=(region_skeletons(library, char.region)[defn.skeleton],),
        template=defn,
        outcome=check.outcome,
        result_zh=outcome_result_lines(library, events),
    )
    return _finish(
        library,
        world,
        char,
        request,
        client=client,
        now=now,
        style=style,
        template=check.template,
        outcome=check.outcome,
    )


def chat_story(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    client: LLMClient | None,
    now: int,
    *,
    npc: str,
    player_text: str,
    style: WorldStyle | None = None,
) -> NarrateAction:
    """和所在地點的 NPC 自由聊天：只換資訊（09 9.6.7 #3），不改任何狀態。"""
    allowed = story_choices(library, world, char, "chat", now=now, npc=npc, player_text=player_text)
    request = _request(
        library,
        world,
        char,
        allowed,
        scene="chat",
        now=now,
        first_npc=npc,
        player_text=player_text,
    )
    return _finish(
        library,
        world,
        char,
        request,
        client=client,
        now=now,
        style=style,
        npc=npc,
        player_text=player_text,
    )
