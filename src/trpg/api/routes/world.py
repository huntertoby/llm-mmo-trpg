"""大世界的端點（Phase 5A-5；``docs/phases/Phase5計畫.md`` 10.3）。

- ``GET /api/world/characters``：角色列表。
- ``POST /api/world/characters``：建立角色（07 7.6 創角；選項沿用 ``/api/runs/start-options``）。
- ``GET /api/world/characters/{id}``：地點圖畫面的整份資料（先同步已結束的戰鬥）。
- ``POST /api/world/characters/{id}/actions``：移動、紮營、撤退、休息、換技能、傳送；5A-7 加上配點、
  重配、閃現、選閃現、溶掉、傳承、立誓、解除誓約。
- ``POST /api/world/characters/{id}/battle``：開戰或接續進行中的戰鬥（之後用 ``/api/battles``）。
- ``POST /api/world/characters/{id}/flash-preview``、``…/allocation-preview``：閃現與配點的預覽
  （5A-7；同一輪的預覽，不扣點、不寫日誌）。
- 5B-5（``docs/phases/Phase5計畫.md`` 18.3）：``actions`` 加接任務、選三選一、說話、酒館，動作之後有
  沒敘述的事件就自動送說書人旁白；``…/situation``（打開情境判定）、``…/situation/answer``（送出回答，
  第一次送出即定案）、``…/chat``（和 NPC 自由聊天）；``GET／POST /api/world/llm``（大世界的
  LLM 開關）。

錯誤：角色不存在 404；動作或內容不合法 422；戰鬥中做其他動作、沒有遭遇卻開戰 409。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Request

from trpg.api.presenter import battle_response
from trpg.api.run_presenter import allocation_preview, flash_preview
from trpg.api.run_schemas import (
    AllocationPreviewOut,
    AllocationPreviewRequest,
    FlashPreviewOut,
    FlashPreviewRequest,
)
from trpg.api.state import world_llm_of, world_of
from trpg.api.world import WorldOutcome, WorldStore
from trpg.api.world_flow import act_with_story, answer_situation, chat, open_situation
from trpg.api.world_presenter import character_summary, event_lines, world_view
from trpg.api.world_schemas import (
    CreateWorldCharacterRequest,
    WorldActionRequest,
    WorldBattleResponse,
    WorldCharacterSummary,
    WorldView,
)
from trpg.api.world_story_schemas import (
    ChatRequest,
    SituationAnswerRequest,
    SituationOpenRequest,
    WorldLlmRequest,
    WorldLlmView,
)
from trpg.world.actions import SwearOathAction
from trpg.world.errors import WorldActionError

__all__ = ["router"]

router = APIRouter(prefix="/api/world", tags=["world"])


def _view(store: WorldStore, outcome: WorldOutcome, region: str) -> WorldView:
    battle = outcome.battle
    trigger = outcome.char.pending_event
    narrations = (
        store.narrations(outcome.char.character_id, trigger.at) if trigger is not None else []
    )
    return world_view(
        store.library,
        outcome.world,
        outcome.char,
        outcome.now,
        events=event_lines(store.library, region, outcome.events, outcome.char),
        battle_id=battle.battle_id if battle is not None else None,
        raw_events=outcome.events,
        narrations=narrations,
    )


@router.get("/characters")
def list_characters(request: Request) -> list[WorldCharacterSummary]:
    store = world_of(request)
    with store.lock:
        return [character_summary(store.library, store.character(c)) for c in store.character_ids()]


@router.post("/characters", status_code=201)
def create_character(body: CreateWorldCharacterRequest, request: Request) -> WorldView:
    store = world_of(request)
    with store.lock:
        char = store.create(
            body.name,
            body.weapon,
            body.keywords,
            race=body.race,
            origin=body.origin,
            seed=body.seed,
        )
        outcome = store.sync(char.character_id)
        return _view(store, outcome, char.region)


@router.get("/characters/{character_id}")
def get_character(character_id: str, request: Request) -> WorldView:
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        return _view(store, store.sync(character_id), region)


@router.post("/characters/{character_id}/actions")
def post_action(
    character_id: str, request: Request, action: Annotated[WorldActionRequest, Body()]
) -> WorldView:
    if isinstance(action, SwearOathAction) and (
        action.source != "menu" or action.prompt_version is not None
    ):
        raise WorldActionError("立誓目前只能從模板選單選（LLM 轉換之後再開放）")
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        client = world_llm_of(request).client()
        return _view(store, act_with_story(store, client, character_id, action), region)


@router.post("/characters/{character_id}/battle")
def post_battle(character_id: str, request: Request) -> WorldBattleResponse:
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        outcome, battle, records = store.battle(character_id)
        view = _view(store, outcome, region)
        with battle.lock:
            battle_out = battle_response(battle, records)
        return WorldBattleResponse(world=view, battle=battle_out)


@router.post("/characters/{character_id}/flash-preview")
def post_flash_preview(
    character_id: str, body: FlashPreviewRequest, request: Request
) -> FlashPreviewOut:
    """閃現（``slot`` 為空）或重閃第 ``slot`` 次之前的預覽（5A-7）：不扣點、不寫日誌。點數與地點
    另外看（``WorldView.growth``）。"""
    store = world_of(request)
    with store.lock:
        library, run = store.growth_run(character_id)
        return flash_preview(library, run, body.skill, body.slot)


@router.post("/characters/{character_id}/allocation-preview")
def post_allocation_preview(
    character_id: str, body: AllocationPreviewRequest, request: Request
) -> AllocationPreviewOut:
    """配點後的最大 HP、法力、耐力與變化文字（5A-7；同一輪的預覽）。"""
    store = world_of(request)
    with store.lock:
        library, run = store.growth_run(character_id)
        return allocation_preview(library, run, body.attributes)


@router.post("/characters/{character_id}/situation")
def post_situation(character_id: str, body: SituationOpenRequest, request: Request) -> WorldView:
    """打開目前事件的某個情境判定解法：說書人寫情境敘述（還沒送出前可以換別的解法）。"""
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        client = world_llm_of(request).client()
        return _view(store, open_situation(store, client, character_id, body.template), region)


@router.post("/characters/{character_id}/situation/answer")
def post_situation_answer(
    character_id: str, body: SituationAnswerRequest, request: Request
) -> WorldView:
    """送出情境判定的回答（**第一次送出即定案**，09 9.6.4）：玩家文字只放進 LLM 的
    ``<player_input>``；引用的事實由引擎核對。回應的 ``situation_result`` 是判定明細與結果敘述。"""
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        client = world_llm_of(request).client()
        outcome = answer_situation(
            store, client, character_id, template=body.template, text=body.text, cite=body.cite
        )
        return _view(store, outcome, region)


@router.post("/characters/{character_id}/chat")
def post_chat(character_id: str, body: ChatRequest, request: Request) -> WorldView:
    """和所在地點的 NPC 自由聊天（只換資訊，不改狀態）；回話在 ``dialog``。"""
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        client = world_llm_of(request).client()
        return _view(store, chat(store, client, character_id, npc=body.npc, text=body.text), region)


@router.get("/llm")
def get_world_llm(request: Request) -> WorldLlmView:
    """大世界的 LLM 開關（預設跟著伺服器設定，玩法 PM 2026-11-03）。"""
    store = world_of(request)
    with store.lock:
        return world_llm_of(request).view()


@router.post("/llm")
def post_world_llm(body: WorldLlmRequest, request: Request) -> WorldLlmView:
    """改大世界的 LLM 開關：打開時先探測，連不到維持關閉並回提示；``null`` 回到伺服器設定。"""
    store = world_of(request)
    with store.lock:
        return world_llm_of(request).set(body.enabled)
