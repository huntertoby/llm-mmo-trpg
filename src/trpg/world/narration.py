"""說書人敘述的引擎核對（Phase 5B-3；``docs/phases/Phase5計畫.md`` 14.3、14.5）。

說書人（``trpg.narrative.storyteller``，由外層呼叫）只提議文字與「從允許清單挑 ID」；本模組決定
允許清單（:func:`story_choices`，外層餵 LLM 與引擎核對用同一個函式），並在 :func:`apply_narration`
再核對一次（09 9.6.7 #6「引擎驗證合法性：角色存在、地點對」；9.5 canon 驗證的規則部分）：

- 引用的 NPC、地點、線頭必須存在且角色看得到（地點＝本區不是隱藏或已發現的；線頭＝持有的有效線頭）。
- 文字不可含本區未發現的隱藏地點名稱、NPC 的祕密原文（18.5：祕密只給說書人參考）。
- 事件敘述只能從 ``pending_event.candidates`` 挑骨架（5B1-3）；有接得上有效線頭的候選時只能挑那些
  （9.6.7 #6「優先接線頭」）；每個事件只敘述 1 次。

敘述不改任何數值、不產生物品、經驗、補給、線頭；唯一的狀態變化是事件敘述換骨架。純函式：不耗亂數、
不讀時間（``now`` 只用來判斷線頭有效）。
"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.content.library import ContentLibrary
from trpg.content.world_events import EventSkeletonDef, NpcCardDef
from trpg.content.world_narration import StoryAllowed, StoryScene, allowed_problems
from trpg.world.actions import NarrateAction, NarratedEvent, WorldEvent
from trpg.world.common import world_map_of
from trpg.world.errors import WorldActionError
from trpg.world.situations import held_threads, situation_template
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "apply_narration",
    "narration_problems",
    "region_npcs",
    "region_skeletons",
    "story_choices",
]


def region_skeletons(library: ContentLibrary, region: str) -> dict[str, EventSkeletonDef]:
    table = library.world_event_content.events.get(region)
    return {} if table is None else table.skeleton_by_id()


def region_npcs(library: ContentLibrary, region: str) -> dict[str, NpcCardDef]:
    table = library.world_event_content.npcs.get(region)
    return {} if table is None else table.npc_by_id()


def _skeleton(library: ContentLibrary, region: str, skeleton_id: str) -> EventSkeletonDef:
    skeleton = region_skeletons(library, region).get(skeleton_id)
    if skeleton is None:
        raise WorldActionError(f"{region} 沒有事件骨架 {skeleton_id}")
    return skeleton


def _here_npcs(cards: Mapping[str, NpcCardDef], location: str) -> set[str]:
    return {n.id for n in cards.values() if n.location == location}


def _common(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """（看得到的地點、持有的線頭、禁止文字）。"""
    world_map = world_map_of(library, char.region)
    visible: list[str] = []
    hidden_names: set[str] = set()
    for loc in world_map.locations:
        if loc.hidden and not char.has_revealed(char.region, loc.id):
            hidden_names.add(loc.name_zh)
        else:
            visible.append(loc.id)
    secrets = {n.secret_zh for n in region_npcs(library, char.region).values() if n.secret_zh}
    forbidden = tuple(sorted(s for s in hidden_names | secrets if s.strip()))
    return tuple(sorted(visible)), held_threads(world, char, now), forbidden


def _event_skeletons(
    library: ContentLibrary, char: CharacterState, held: tuple[str, ...]
) -> tuple[str, ...]:
    trigger = char.pending_event
    assert trigger is not None
    skeletons = region_skeletons(library, char.region)
    candidates = [s for s in trigger.candidates if s in skeletons]
    live = set(held)
    followed = [s for s in candidates if live.intersection(skeletons[s].follows)]
    return tuple(sorted(followed or candidates))


def _require_event(char: CharacterState) -> None:
    if char.pending_event is None:
        raise WorldActionError("目前沒有事件可以敘述")
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇")


def _check_fields(
    scene: StoryScene,
    *,
    template: str | None,
    outcome: str | None,
    npc: str | None,
    player_text: str,
) -> None:
    if (template is not None) != (scene in ("situation", "outcome")):
        raise WorldActionError("只有情境與結果敘述要指定情境模板")
    if (outcome is not None) != (scene == "outcome"):
        raise WorldActionError("只有結果敘述要指定判定結果")
    if (npc is not None) != (scene == "chat"):
        raise WorldActionError("只有聊天要指定 NPC")
    if player_text and scene != "chat":
        raise WorldActionError("只有聊天可以帶玩家的話")


def story_choices(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    scene: StoryScene,
    *,
    now: int,
    template: str | None = None,
    outcome: str | None = None,
    npc: str | None = None,
    player_text: str = "",
) -> StoryAllowed:
    """``scene`` 的允許清單；前提不成立拋 :class:`WorldActionError`（14.3）。"""
    _check_fields(scene, template=template, outcome=outcome, npc=npc, player_text=player_text)
    locations, held, forbidden = _common(library, world, char, now)
    cards = region_npcs(library, char.region)
    here = _here_npcs(cards, char.location)
    if scene == "event":
        _require_event(char)
        assert char.pending_event is not None
        if char.pending_event.narrated:
            raise WorldActionError("這個事件已經敘述過了")
        skeletons = _event_skeletons(library, char, held)
        if not skeletons:
            raise WorldActionError("這個事件沒有可以挑的骨架")
        per = {
            s: tuple(sorted(n for n in _skeleton(library, char.region, s).npcs if n in cards))
            for s in skeletons
        }
        return StoryAllowed(
            skeletons=skeletons,
            npcs=tuple(sorted(here)),
            skeleton_npcs=per,
            locations=locations,
            threads=held,
            forbidden=forbidden,
        )
    if scene == "chat":
        if char.pending_encounter is not None:
            raise WorldActionError("還有沒處理的遭遇")
        assert npc is not None
        card = cards.get(npc)
        if card is None:
            raise WorldActionError(f"{char.region} 沒有 NPC {npc}")
        if card.location != char.location:
            raise WorldActionError(f"{card.name_zh}不在這裡")
        return StoryAllowed(
            npcs=tuple(sorted(cards)),
            locations=locations,
            threads=held,
            forbidden=forbidden,
        )
    assert template is not None
    defn = situation_template(library, char.region, template)
    if scene == "situation":
        _require_event(char)
        assert char.pending_event is not None
        if defn.skeleton != char.pending_event.skeleton:
            raise WorldActionError(f"情境模板 {template} 不屬於目前的事件")
    skeleton = _skeleton(library, char.region, defn.skeleton)
    npcs = here | {n for n in skeleton.npcs if n in cards}
    return StoryAllowed(
        npcs=tuple(sorted(npcs)),
        locations=locations,
        threads=held,
        forbidden=forbidden,
    )


def narration_problems(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: NarrateAction,
    now: int,
) -> list[str]:
    """``action`` 的所有問題（空＝可以套用）。前提不成立時只回傳那一條。"""
    try:
        choices = story_choices(
            library,
            world,
            char,
            action.scene,
            now=now,
            template=action.template,
            outcome=action.outcome,
            npc=action.npc,
            player_text=action.player_text,
        )
    except WorldActionError as exc:
        return [str(exc)]
    return allowed_problems(action.scene, action.story, choices)


def apply_narration(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: NarrateAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """套用一段敘述；不合法拋 :class:`WorldActionError`（狀態不變）。"""
    problems = narration_problems(library, world, char, action, now)
    if problems:
        raise WorldActionError("；".join(problems))
    skeleton: str | None = None
    if action.scene == "event":
        trigger = char.pending_event
        assert trigger is not None and action.story.skeleton is not None
        skeleton = action.story.skeleton
        live = set(held_threads(world, char, now))
        hits = sorted(live.intersection(_skeleton(library, char.region, skeleton).follows))
        trigger = trigger.model_copy(
            update={
                "skeleton": skeleton,
                "follows_thread": hits[0] if hits else None,
                "narrated": True,
            }
        )
        char = char.model_copy(update={"pending_event": trigger})
    elif action.scene in ("situation", "outcome"):
        assert action.template is not None
        skeleton = situation_template(library, char.region, action.template).skeleton
    event = NarratedEvent(
        scene=action.scene,
        skeleton=skeleton,
        template=action.template,
        outcome=action.outcome,
        npc=action.npc,
        story=action.story,
        source=action.source,
    )
    return char, (event,)
