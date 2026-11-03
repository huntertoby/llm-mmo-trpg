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

- 5E-3（``docs/phases/Phase5計畫.md`` 31.7）：``GET／POST …/notes``（角色所在地點的留言與足跡、
  留一則；#105）、``DELETE /api/world/notes/{note_id}``（管理者刪留言）。
- 5E-3b：``DELETE …/characters/{id}/notes/{note_id}``（作者刪自己的留言）；留言板回 ``admin``。

- 5F-1（``docs/phases/Phase5計畫.md`` 35.7）：``GET …/board``（城鎮公告板）。
- 5F-1b：``GET …/absence``（「你不在的時候」摘要；看過送 ``news_seen`` 動作）。
- 5F-4（``docs/phases/Phase5計畫.md`` 36.7）：``GET …/league``（影子循環賽：報名狀態、排行榜、
  場次）、``POST …/league/matches/{match_id}/replay``（某一場從開場播到結束＋重播驗證）、
  ``GET /api/world/league/matches/{match_id}/log``（原始戰鬥紀錄）、``POST /api/world/league/run``
  （管理者開跑；背景分批執行）。報名、取消走 ``…/actions``（``league_enter``、
  ``league_withdraw``）。

- 5E-1（``docs/phases/Phase5計畫.md`` 28.6）：全部端點經 :func:`~trpg.api.auth.require_world_access`
  依帳號存取（開發模式關時要登入；別人的角色 404）；角色列表只列自己的、建立角色先檢查上限再
  歸到帳號。

錯誤：沒有登入 401；角色不存在 404；角色已達上限 409；動作或內容不合法 422；戰鬥中做其他動作、
沒有遭遇卻開戰 409。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from trpg.api.absence_view import AbsenceView, absence_summary
from trpg.api.auth import (
    accounts_of,
    require_admin,
    require_league_admin,
    require_note_admin,
    require_world_access,
    viewer,
)
from trpg.api.league_schemas import LeagueReplayResponse, LeagueRunView, LeagueView
from trpg.api.league_view import PAGE_SIZE, league_view, match_title
from trpg.api.notes_schemas import LocationBoard, NoteRequest, location_board
from trpg.api.presenter import battle_response
from trpg.api.run_presenter import allocation_preview, flash_preview
from trpg.api.run_schemas import (
    AllocationPreviewOut,
    AllocationPreviewRequest,
    FlashPreviewOut,
    FlashPreviewRequest,
)
from trpg.api.season_schemas import SeasonBoardView
from trpg.api.season_view import season_board
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
from trpg.engine.runner import log_replay_problem
from trpg.server.league import STALE_ZH, LeagueError
from trpg.world.actions import SwearOathAction
from trpg.world.errors import WorldActionError

__all__ = ["router"]

router = APIRouter(
    prefix="/api/world", tags=["world"], dependencies=[Depends(require_world_access)]
)


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
    account = viewer(request)
    store = world_of(request)
    with store.lock:
        ids = store.character_ids()
        if account is not None:  # 只列自己的角色（建立順序）
            existing = set(ids)
            ids = [c for c in account.characters if c in existing]
        return [character_summary(store.library, store.character(c)) for c in ids]


@router.post("/characters", status_code=201)
def create_character(body: CreateWorldCharacterRequest, request: Request) -> WorldView:
    account = viewer(request)
    accounts = accounts_of(request)
    store = world_of(request)
    with store.lock:  # 建立角色經世界的鎖依序進行：檢查上限、建立、歸到帳號之間不會插隊
        if account is not None:
            accounts.check_character_room(account.account_id)  # 先檢查上限再建立（409）
        char = store.create(
            body.name,
            body.weapon,
            body.keywords,
            race=body.race,
            origin=body.origin,
            seed=body.seed,
        )
        if account is not None:
            accounts.attach_character(account.account_id, char.character_id)
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


@router.get("/characters/{character_id}/board")
def get_board(character_id: str, request: Request) -> SeasonBoardView:
    """城鎮公告板（5F-1）：賽季第幾天、今日目標、懸賞板、世界事件全服進度、已清空的地點。"""
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
        now = store.clock()
        return season_board(store.library, store.season_world(now), char, now)


@router.get("/characters/{character_id}/absence")
def get_absence(character_id: str, request: Request) -> AbsenceView:
    """「你不在的時候」摘要（5F-1b）：上次看過之後的世界事件成敗、懸賞歸屬、新開放的區域。看過時送
    ``news_seen`` 動作（``until``＝``as_of``）。只讀，用換日後的世界算。"""
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
        now = store.clock()
        return absence_summary(store.library, store.season_world(now), char, now)


@router.get("/characters/{character_id}/league")
def get_league(
    character_id: str,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = PAGE_SIZE,
) -> LeagueView:
    """影子循環賽（5F-4）：報名狀態、排行榜（隱藏地點用提示語）、場次（分頁，5F-4b）與進度。
    第 14 天換日後、還沒有人首殺賽季 Boss 時，第一次看到這裡就自動開跑（5F-4b）。"""
    store = world_of(request)
    with store.lock:
        store.character(character_id)
        store.auto_start_league(store.clock())
    with store.lock:
        char = store.character(character_id)
        now = store.clock()
        world = store.season_world(now)
        record = store.league.record(world.season_id)
        return league_view(
            store.library,
            world,
            char,
            record,
            now,
            account=store.account_of(character_id),
            running=store.league_runner.running,
            stale=record is not None and store.league.stale(record),
            page=page,
            page_size=page_size,
        )


@router.post("/characters/{character_id}/league/matches/{match_id}/replay")
def post_league_replay(character_id: str, match_id: str, request: Request) -> LeagueReplayResponse:
    """某一場循環賽的重播（5F-4）：依紀錄的步驟在戰鬥工作階段重播（不推進、不呼叫 AI），回傳從開場
    到結束的每一步（既有戰鬥畫面播放），並比對最終狀態。紀錄不能重播時 409。"""
    store = world_of(request)
    with store.lock:
        store.character(character_id)
        record = store.league.record(store.world().season_id)
        match = None if record is None else record.match(match_id)
        log = store.league.log(match_id)
    assert record is not None and match is not None  # log() 已檢查
    if store.league.stale(record):  # 5F-4b：不跨 ruleset 重播
        raise LeagueError(f"這一場不能重播：{STALE_ZH}（管理者重新開跑會整個重跑）")
    problem = log_replay_problem(log)
    if problem is not None:
        raise LeagueError(f"這一場不能重播：{problem}")
    battle, _ = store.battles.open(log.setup, log.seed, restore=(list(log.actions), []))
    with battle.lock:
        verified = battle.state == log.final_state
        out = battle_response(battle, battle.history())
    return LeagueReplayResponse(
        title_zh=match_title(store.library, record, match), battle=out, verified=verified
    )


@router.get("/league/matches/{match_id}/log")
def get_league_log(match_id: str, request: Request) -> Response:
    """某一場循環賽的原始戰鬥紀錄（``trpg battle replay`` 同格式，可以自己重播驗證）。"""
    store = world_of(request)
    return Response(content=store.league.log_text(match_id), media_type="application/json")


@router.post("/league/run", dependencies=[Depends(require_league_admin)])
def post_league_run(request: Request) -> LeagueRunView:
    """開始（或接續）影子循環賽（管理者，代決 5F4-1）：截止後凍結報名、排好賽程，背景分批跑。"""
    store = world_of(request)
    with store.lock:  # 只在凍結報名時拿世界的鎖
        record = store.league.start(store.world(), store.clock())
    started = store.league_runner.start()
    return LeagueRunView(started=started, done=record.done, total=len(record.matches))


@router.get("/llm")
def get_world_llm(request: Request) -> WorldLlmView:
    """大世界的 LLM 開關（預設跟著伺服器設定，玩法 PM 2026-11-03）。"""
    store = world_of(request)
    with store.lock:
        return world_llm_of(request).view()


# 伺服器全域開關：帶了 token 的非管理者 403（5E-2，計畫 29.8）。說明不放 docstring，OpenAPI 不變。
@router.post("/llm", dependencies=[Depends(require_admin)])
def post_world_llm(body: WorldLlmRequest, request: Request) -> WorldLlmView:
    """改大世界的 LLM 開關：打開時先探測，連不到維持關閉並回提示；``null`` 回到伺服器設定。"""
    store = world_of(request)
    with store.lock:
        return world_llm_of(request).set(body.enabled)


def _is_admin(request: Request) -> bool:
    """登入的是管理者（開發模式沒帶 token 不算：畫面只在管理者登入時給每則刪除鍵）。"""
    account = viewer(request)
    return account is not None and account.admin


@router.get("/characters/{character_id}/notes")
def get_notes(character_id: str, request: Request) -> LocationBoard:
    """角色現在所在地點的留言（最新 20 則）與其他角色的足跡（5E-3，#105）。"""
    store = world_of(request)
    with store.lock:
        return location_board(store, store.character(character_id), admin=_is_admin(request))


@router.post("/characters/{character_id}/notes")
def post_note(character_id: str, body: NoteRequest, request: Request) -> LocationBoard:
    """在角色現在所在的地點留一則（1～50 字、不能換行；不進世界日誌、不送進 LLM）。"""
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
        store.notes.add(char, body.text, store.clock())
        return location_board(store, char, admin=_is_admin(request))


@router.delete("/characters/{character_id}/notes/{note_id}")
def delete_own_note(character_id: str, note_id: str, request: Request) -> LocationBoard:
    """作者刪自己的留言（5E-3b）：只能刪這個角色留的；別人的或不存在都 404。"""
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
        store.notes.delete(note_id, author=character_id)
        return location_board(store, char, admin=_is_admin(request))


@router.delete("/notes/{note_id}", status_code=204, dependencies=[Depends(require_note_admin)])
def delete_note(note_id: str, request: Request) -> Response:
    """刪一則留言（管理者；#105「使用者手動刪」）。"""
    store = world_of(request)
    with store.lock:
        store.notes.delete(note_id)
    return Response(status_code=204)
