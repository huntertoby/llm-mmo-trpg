"""大世界說書人與情境判定的流程（Phase 5B-5；``docs/phases/Phase5計畫.md`` 18.2、18.3）。

- :class:`WorldLlm`：大世界自己的 LLM 開關（玩法 PM 2026-11-03：預設跟著伺服器設定）。伺服器層級、
  只存記憶體；打開時先探測，連不到維持關閉並回提示（代決 5B5-1）。
- :func:`act_with_story`：世界動作之後，角色有沒敘述過的事件就自動送一次 ``event_story``（5B-3 待決
  建議；代決 5B5-3）。
- :func:`open_situation`／:func:`answer_situation`：情境判定（09 9.6.4）。玩家文字只放進 LLM 的
  ``<player_input>``（``trpg.llm.situation`` 用 ``wrap_player_input``；代決 5B5-5）；點選引用的事實
  併進提議的用心清單，引擎照常逐筆核對（代決 5B5-4）；**第一次送出即定案**（引擎結算後清掉事件）。
- :func:`chat`：和所在地點的 NPC 自由聊天（只換資訊，不改狀態）。

全部在世界的寫入鎖裡依序做（代決 5B5-2）；LLM 只提議，敘述先經 ``narration_problems``、情境提議經
引擎合法性檢查，不過就降級（``docs/專案計畫.md`` 3.1：模型不可用時遊戲照常）。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final, Literal

from trpg.api.llm_health import UNAVAILABLE_NOTICE, LlmHealth
from trpg.api.llm_source import LLM_OFF_NOTICE, LlmProvider
from trpg.api.world import WorldOutcome, WorldStore
from trpg.api.world_story import chat_story, event_story, outcome_story, situation_story
from trpg.api.world_story_schemas import CARE_CITE_MAX, WorldLlmView
from trpg.content.world_situations import (
    CareClaim,
    SituationFact,
    SituationProposal,
    default_proposal,
)
from trpg.llm.client import LLMClient
from trpg.llm.situation import SituationRequest, propose_situation
from trpg.world.actions import NarrateAction, SituationAction, WorldAction
from trpg.world.errors import WorldActionError
from trpg.world.narration import region_skeletons
from trpg.world.situations import situation_facts, situation_rules, situation_template
from trpg.world.state import CharacterState, WorldState

__all__ = [
    "CITABLE_ITEMS",
    "WorldLlm",
    "act_with_story",
    "answer_situation",
    "chat",
    "narrate_event",
    "open_situation",
]

CITABLE_ITEMS: Final = frozenset({"clue", "npc_bond", "exchange"})
"""玩家可以點選引用的用心清單項目（9.6.4 ①②③；④弱點要方法相符，由 LLM 判斷）。"""


class WorldLlm:
    """大世界的 LLM 開關（18.2）。``enabled``＝改過就照改的，否則照伺服器設定（``generate``）。"""

    def __init__(self, provider: LlmProvider | None, health: LlmHealth | None = None) -> None:
        self._provider = provider
        self._override: bool | None = None
        self._client: LLMClient | None = None
        self.notice: str | None = None
        self.health = health
        """本機模型的健康檢查（5E-3）：不可用時 :meth:`client` 回 ``None``（全部走模板）。"""

    @property
    def default(self) -> bool:
        return self._provider is not None and self._provider.generate_default()

    @property
    def enabled(self) -> bool:
        return self._override if self._override is not None else self.default

    def view(self) -> WorldLlmView:
        available = self.health.available if self.health is not None else None
        notice = self.notice
        if notice is None and self.enabled and available is False:
            notice = UNAVAILABLE_NOTICE
        return WorldLlmView(
            enabled=self.enabled,
            default=self.default,
            overridden=self._override is not None,
            notice_zh=notice,
            model_available=available,
        )

    def set(self, enabled: bool | None) -> WorldLlmView:
        """``True`` 打開（先探測，連不到維持關閉並留提示）、``False`` 關閉、``None`` 回到
        伺服器設定。"""
        self.notice = None
        if enabled is True:
            notice = self._probe()
            if notice is not None:
                self._override = False
                self.notice = notice
                return self.view()
        self._override = enabled
        return self.view()

    def _probe(self) -> str | None:
        if self._provider is None:
            return LLM_OFF_NOTICE
        if self.health is not None:  # 打開時的探測也更新健康狀態（5E-3）
            return None if self.health.check() else LLM_OFF_NOTICE
        return self._provider.probe()

    def client(self) -> LLMClient | None:
        """開著時的 client（建一次重用）；關閉、或健康檢查說模型不可用時 ``None``（說書人與情境
        提議直接降級，5E-3）。"""
        if not self.enabled or self._provider is None:
            return None
        if self.health is not None and not self.health.usable:
            return None
        if self._client is None:
            self._client = self._provider.story_client()
        return self._client


def _merge(first: WorldOutcome, second: WorldOutcome | None) -> WorldOutcome:
    if second is None:
        return first
    return WorldOutcome(
        second.world, second.char, (*first.events, *second.events), second.now, second.battle
    )


type _Builder = Callable[[WorldState, CharacterState, int], NarrateAction]


def _narrate(store: WorldStore, character_id: str, build: _Builder) -> WorldOutcome | None:
    """組一段敘述並寫進日誌；前提不成立或被引擎拒絕（不該發生）時略過，不擋住動作（18.3）。"""
    world, char = store.world(), store.character(character_id)
    try:
        action = build(world, char, store.clock())
        return store.act(character_id, action)
    except WorldActionError:
        return None


def narrate_event(
    store: WorldStore, client: LLMClient | None, character_id: str
) -> WorldOutcome | None:
    """角色有沒敘述過的事件（且沒有遭遇）時送一次 ``event_story``；沒有就 ``None``。"""
    char = store.character(character_id)
    trigger = char.pending_event
    if trigger is None or trigger.narrated or char.pending_encounter is not None:
        return None
    return _narrate(
        store,
        character_id,
        lambda world, now_char, now: event_story(store.library, world, now_char, client, now),
    )


def act_with_story(
    store: WorldStore, client: LLMClient | None, character_id: str, action: WorldAction
) -> WorldOutcome:
    """世界動作＋自動事件旁白（代決 5B5-3）。"""
    outcome = store.act(character_id, action)
    return _merge(outcome, narrate_event(store, client, character_id))


def open_situation(
    store: WorldStore, client: LLMClient | None, character_id: str, template: str
) -> WorldOutcome:
    """打開某個情境判定解法：情境敘述（scene ``situation``）寫進日誌。前提不成立 422。"""
    world, char, now = store.world(), store.character(character_id), store.clock()
    action = situation_story(store.library, world, char, client, now, template=template)
    return store.act(character_id, action)


def _with_cites(
    proposal: SituationProposal, cite: Sequence[str], facts: dict[str, SituationFact]
) -> SituationProposal:
    """引用的事實排在前面併進用心清單（同一事實不重複、共 ≤ 4 筆）；引擎照常逐筆核對。"""
    claims = [CareClaim(item=facts[c].item, fact=c) for c in dict.fromkeys(cite)]
    cited = {c.fact for c in claims}
    claims += [c for c in proposal.care if c.fact not in cited]
    return proposal.model_copy(update={"care": tuple(claims[:CARE_CITE_MAX])})


def answer_situation(
    store: WorldStore,
    client: LLMClient | None,
    character_id: str,
    *,
    template: str,
    text: str,
    cite: Sequence[str],
) -> WorldOutcome:
    """送出情境判定的回答（第一次送出即定案）→ 判定 → 結果敘述。"""
    library = store.library
    world, char, now = store.world(), store.character(character_id), store.clock()
    if char.pending_event is None:
        raise WorldActionError("目前沒有事件可以判定（同一件事只能判定一次）")
    defn = situation_template(library, char.region, template)
    if defn.skeleton != char.pending_event.skeleton:
        raise WorldActionError(f"情境模板 {template} 不屬於目前的事件")
    facts = {f.fact: f for f in situation_facts(library, world, char, defn, now)}
    for fact in cite:
        if fact not in facts or facts[fact].item not in CITABLE_ITEMS:
            raise WorldActionError(f"不能引用 {fact}：不是你持有的線索、往來或交換條件")
    rules = situation_rules(library)
    source: Literal["llm", "fallback"] = "fallback"
    version: str | None = None
    proposal = default_proposal(defn, rules)
    if client is not None:
        skeleton = region_skeletons(library, char.region)[defn.skeleton]
        request = SituationRequest(
            template=defn,
            skeleton=skeleton,
            rules=rules,
            facts=tuple(facts.values()),
            player_text=text,
        )
        proposed = propose_situation(client, request)
        proposal, source, version = proposed.proposal, proposed.source, proposed.prompt_version

    def submit(prop: SituationProposal, src: Literal["llm", "fallback"]) -> WorldOutcome:
        action = SituationAction(
            template=template,
            player_text=text,
            proposal=_with_cites(prop, cite, facts),
            source=src,
            prompt_version=version,
        )
        return store.act(character_id, action)

    try:
        result = submit(proposal, source)
    except WorldActionError:
        if source != "llm":
            raise
        result = submit(default_proposal(defn, rules), "fallback")  # LLM 提議被引擎拒絕 → 降級
    story = _narrate(
        store,
        character_id,
        lambda w, c, n: outcome_story(library, w, c, client, n, events=result.events),
    )
    return _merge(result, story)


def chat(
    store: WorldStore, client: LLMClient | None, character_id: str, *, npc: str, text: str
) -> WorldOutcome:
    """和所在地點的 NPC 自由聊天（只換資訊，不改狀態）；NPC 不在這裡 422。"""
    world, char, now = store.world(), store.character(character_id), store.clock()
    action = chat_story(store.library, world, char, client, now, npc=npc, player_text=text)
    return store.act(character_id, action)
