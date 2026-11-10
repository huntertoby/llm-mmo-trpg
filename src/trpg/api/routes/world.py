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

- 5F-5（``docs/phases/Phase5計畫.md`` 40.5）：``GET /api/world/chronicle``（編年史）、
  ``GET /api/world/legacy``（自己帳號上季的角色）、``POST /api/world/season/reset``（管理者的季末
  重置，預設 dry-run）；建立角色加 ``legacy_character``（沿用上季角色的名字與外觀）。

- QK-9b：``POST …/characters/{id}/dev-teleport?region=``（開發用：搬到某區的城鎮；同 ``dev-boss``
  只在開發模式掛、要 ``TRPG_DEV_ROUTES=1``）。
- 6F-3：``POST …/characters/{id}/dev-boss``（開發用：Boss 戰直接開打，不回寫世界；在
  :data:`dev_router`，只在開發模式掛，而且要 ``TRPG_DEV_ROUTES=1``，見 :mod:`trpg.api.world_dev`）。

- OB-1（#150）：建立角色時給 ``weapon``／``keywords``（舊流程）只留開發模式，正式模式 403
  （測試用環境變數 :data:`LEGACY_CREATE_ENV` 統一打開，``tests/conftest.py``）；``actions`` 加
  ``opening_class``（選大類）。

- TR-1（#134）：建立角色的 ``weapon``／``keywords`` 改成選填（正式流程都不給＝停在主城工坊靶場）；
  ``POST …/characters/{id}/range/trial``（靶場的沙盒試打，不寫日誌）；``actions`` 加
  ``opening_confirm``（確定出發）。

- 6D-R1：``GET …/characters/{id}/fields/{map_id}``（實地地圖的靜態地形；只給這個角色看得到的圖，
  其他一律 404）；``GET …/characters/{id}?with_tiles=1`` 讓 ``field.tiles`` 直接帶地形。

- 5F-5c：``POST /api/world/season/verify``（管理者；從舊季的唯讀封存重播查證首殺或循環賽場次）。

- 5E-1（``docs/phases/Phase5計畫.md`` 28.6）：全部端點經 :func:`~trpg.api.auth.require_world_access`
  依帳號存取（開發模式關時要登入；別人的角色 404）；角色列表只列自己的、建立角色先檢查上限再
  歸到帳號。

錯誤：沒有登入 401；角色不存在 404；角色已達上限 409；動作或內容不合法 422；戰鬥中做其他動作、
沒有遭遇卻開戰 409。
"""

from __future__ import annotations

import os
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response

from trpg.api.absence_view import AbsenceView, absence_summary
from trpg.api.auth import (
    AdminRequiredError,
    accounts_of,
    owner_id,
    reject_dev_fields,
    require_admin,
    require_league_admin,
    require_note_admin,
    require_season_admin,
    require_world_access,
    viewer,
)
from trpg.api.chronicle_schemas import (
    ChronicleTitles,
    ChronicleView,
    LegacyHeroView,
    SeasonResetRequest,
    SeasonVerifyRequest,
    chronicle_view,
    legacy_view,
)
from trpg.api.league_schemas import LeagueReplayResponse, LeagueRunView, LeagueView
from trpg.api.league_view import PAGE_SIZE, league_view, match_outcome_zh, match_title
from trpg.api.notes_schemas import LocationBoard, NoteRequest, location_board
from trpg.api.presenter import battle_response
from trpg.api.routes.runs import DEV_ROUTES_ENV
from trpg.api.run_presenter import allocation_preview, flash_preview
from trpg.api.run_schemas import (
    AllocationPreviewOut,
    AllocationPreviewRequest,
    FlashPreviewOut,
    FlashPreviewRequest,
)
from trpg.api.season_schemas import SeasonBoardView
from trpg.api.season_view import season_board
from trpg.api.sessions import InvalidRequestError
from trpg.api.state import world_llm_of, world_of
from trpg.api.world import WorldCharacterNotFoundError, WorldOutcome, WorldStore
from trpg.api.world_dev import dev_boss_battle, dev_teleport
from trpg.api.world_field_schemas import FieldTilesView
from trpg.api.world_field_view import field_tiles, visible_field_map
from trpg.api.world_flow import act_with_story, answer_situation, chat, open_situation
from trpg.api.world_pregen import (
    PregenWaitOut,
    PregenWaitRequest,
    flash_wait_request,
    opportunity_wait_request,
)
from trpg.api.world_presenter import character_summary, event_lines, world_view
from trpg.api.world_range import open_range_trial
from trpg.api.world_range_schemas import RangeTrialRequest, RangeTrialResponse
from trpg.api.world_schemas import (
    CreateWorldCharacterRequest,
    WorldActionRequest,
    WorldBattleResponse,
    WorldCharacterSummary,
    WorldDevBattleResponse,
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
from trpg.roguelite.state import FlashChoice
from trpg.server.league import STALE_ZH, LeagueError
from trpg.server.season_archive import ReplayCheck
from trpg.server.season_reset import SeasonResetReport
from trpg.world.actions import SwearOathAction
from trpg.world.calendar import season_start_at
from trpg.world.errors import WorldActionError
from trpg.world.generated import GenRequest

__all__ = ["dev_router", "router"]

LEGACY_CREATE_ENV = "TRPG_LEGACY_CREATE"
"""``1``＝開發模式關時也接受舊流程建角（只給測試用，OB-1；正式伺服器不要設）。"""

router = APIRouter(
    prefix="/api/world", tags=["world"], dependencies=[Depends(require_world_access)]
)
dev_router = APIRouter(
    prefix="/api/world", tags=["world"], dependencies=[Depends(require_world_access)]
)
"""開發用端點（6F-3）：只在開發模式掛（:func:`trpg.api.app.create_app`）。"""


def _view(
    store: WorldStore, outcome: WorldOutcome, region: str, *, inline_tiles: bool = False
) -> WorldView:
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
        events=event_lines(store.library, region, outcome.events, outcome.char, outcome.now),
        battle_id=battle.battle_id if battle is not None else None,
        raw_events=outcome.events,
        narrations=narrations,
        titles=store.titles_of_character,
        social=store.field_social(outcome.char.character_id),  # 6C-5 足跡與留言石碑
        prepare=store.prepared_battle,  # 6C-R3：遭遇面板的 prepare_battle 快取
        # 6C-R3：靜態地形改由 GET …/characters/{id}/fields/{map_id} 取；前端取不到時用
        # ?with_tiles=1 請伺服器直接帶（6D-R1）
        inline_tiles=inline_tiles,
    )


@router.get("/characters/{character_id}/fields/{map_id}")
def get_field_tiles(
    character_id: str,
    map_id: str,
    request: Request,
    response: Response,
    h: Annotated[str | None, Query(max_length=64)] = None,
) -> FieldTilesView:
    """實地地圖的靜態地形（6C-R3）：只看內容。``h`` 等於目前的雜湊時允許瀏覽器快取（內容一樣
    就一樣）；不同或省略照樣回傳目前的地形（前端以回傳的 ``hash`` 為準）。

    6D-R1：經角色走（擁有者檢查同其他 ``/characters/{id}`` 路由），只給這個角色看得到的圖
    （:func:`~trpg.api.world_field_view.visible_field_map`）；看不到和不存在一樣 404、訊息相同。"""
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
    missing = WorldCharacterNotFoundError(f"找不到實地地圖 {map_id}")
    if visible_field_map(store.library, char, map_id) is None:
        raise missing
    found = field_tiles(store.library, map_id)
    if found is None:
        raise missing
    if h == found.hash:
        response.headers["Cache-Control"] = "private, max-age=86400, immutable"
    return found


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
    if os.environ.get(LEGACY_CREATE_ENV) != "1":  # OB-1（#150）：舊流程建角只留開發模式
        reject_dev_fields(request, body.dev_fields())
    account = viewer(request)
    accounts = accounts_of(request)
    store = world_of(request)
    with store.lock:  # 建立角色經世界的鎖依序進行：檢查上限、建立、歸到帳號之間不會插隊
        if account is not None:
            accounts.check_character_room(account.account_id)  # 先檢查上限再建立（409）
        legacy = (
            None
            if body.legacy_character is None
            else store.legacy_hero(
                body.legacy_character, None if account is None else account.account_id
            )
        )
        char = store.create(
            body.name,
            body.weapon,
            body.keywords,
            race=body.race,
            origin=body.origin,
            seed=body.seed,
            legacy=legacy,
            look=body.look,
        )
        if account is not None:
            accounts.attach_character(account.account_id, char.character_id)
        outcome = store.sync(char.character_id)
        return _view(store, outcome, char.region)


@router.get("/characters/{character_id}")
def get_character(
    character_id: str,
    request: Request,
    with_tiles: Annotated[bool, Query()] = False,
) -> WorldView:
    """``with_tiles`` 為真時 ``field.tiles`` 直接帶這個角色看到的地形（6D-R1：前端另外取靜態地形
    失敗時的退路）。"""
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        return _view(store, store.sync(character_id), region, inline_tiles=with_tiles)


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


@router.post("/characters/{character_id}/range/trial")
def post_range_trial(
    character_id: str, body: RangeTrialRequest, request: Request
) -> RangeTrialResponse:
    """TR-1（#134）：主城工坊靶場的沙盒試打——未完成開局的角色拿起一把武器打木樁（普攻＋該大類
    2 招示範招），或看關鍵字起始技能的示範。在戰鬥工作階段表開一場（之後用 ``/api/battles``），
    **不寫世界日誌、不改角色、不登記成角色的戰鬥**：不算勝負、不給經驗與掉落、不耗 HP 與法力。
    已完成開局的角色 422。"""
    return open_range_trial(world_of(request), character_id, body, owner_id(request))


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


@dev_router.post("/characters/{character_id}/dev-boss")
def post_dev_boss(
    character_id: str,
    request: Request,
    *,
    location: str = "cloud_summit",
    region: str | None = None,
    level: int | None = None,
    ai_until: Literal["charge", "last"] | None = None,
    facing: Literal["north", "east", "south", "west"] | None = None,
    opening: Literal["summon", "form"] | None = None,
) -> WorldDevBattleResponse:
    """開發用（6F-3）：``location`` 的 Boss 戰（或任何有戰鬥的地點）直接開打，給實戰截圖用；不寫
    日誌、不回寫世界，主線限制照舊。另外要 ``TRPG_DEV_ROUTES=1``（否則 404）。
    QK-9b：``facing``＝主角開場朝向（照它排起始位置）；``opening``＝開場就放出召喚物／變身。"""
    if os.environ.get(DEV_ROUTES_ENV) != "1":
        raise HTTPException(status_code=404, detail="Not Found")
    store = world_of(request)
    dev = dev_boss_battle(
        store,
        character_id,
        location=location,
        region=region,
        level=level,
        ai_until=ai_until,
        facing=facing,
        opening=opening,
    )
    dev.battle.owner = owner_id(request)  # 6S-1：只給開的人
    with dev.battle.lock:
        out = battle_response(dev.battle, dev.records)
    return WorldDevBattleResponse(title_zh=dev.title_zh, battle=out)


@dev_router.post("/characters/{character_id}/dev-teleport")
def post_dev_teleport(character_id: str, request: Request, *, region: str) -> WorldView:
    """開發用（QK-9b）：角色直接搬到 ``region`` 的城鎮（拍 NPC 用；主線限制不管）。會改角色存檔、
    不寫世界日誌。只在開發模式掛，另外要 ``TRPG_DEV_ROUTES=1``（否則 404）。"""
    if os.environ.get(DEV_ROUTES_ENV) != "1":
        raise HTTPException(status_code=404, detail="Not Found")
    store = world_of(request)
    with store.lock:
        moved = dev_teleport(store, character_id, region)
        return _view(store, store.sync(character_id), moved.region)


@router.post("/characters/{character_id}/pregen/wait")
def post_pregen_wait(character_id: str, body: PregenWaitRequest, request: Request) -> PregenWaitOut:
    """6L-2：按閃現（或重閃）、選機遇解法之前先問 LLM 的版本好了沒——會等到好了或 10 秒（期間前端
    顯示等待提示、可以取消）。不扣點、不寫日誌；等待時不佔世界的寫入鎖。"""
    store = world_of(request)
    pregen = store.pregen
    if pregen is None:
        return PregenWaitOut(status="off")
    gen: GenRequest | None = None
    with store.lock:
        char = store.character(character_id)
        library = store.library
        if body.kind == "flash":
            if body.skill is None:
                raise WorldActionError("閃現的等待要指定技能")
            choice = FlashChoice(skill=body.skill, slot=body.slot, category=body.category)
            gen = flash_wait_request(library, store.world(), char, choice)
        elif body.solution is not None:
            gen = opportunity_wait_request(library, store.world(), char, body.solution)
        if gen is None:
            return PregenWaitOut(status="none")
    kind: Literal["flash", "complete_offer"] = "flash" if body.kind == "flash" else "complete_offer"
    return pregen.wait(character_id, kind, gen, library=library)


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
    """城鎮公告板（5F-1）：賽季第幾天、今日目標、懸賞板、世界事件全服進度、已清空的地點；
    5F-3 加賽季 Boss（封印、鑰匙、帳號今天剩幾次、首殺、評分榜）。"""
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
        now = store.clock()
        world = store.season_world(now)
        actor = None if store.actor_of is None else store.actor_of(character_id)
        return season_board(
            store.library,
            world,
            char,
            now,
            actor=actor,
            boss_board=store.boss_board.top(world.season_id),
            titles=store.titles_of_character,
        )


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
    battle.owner = owner_id(request)  # 6S-1：重播的戰鬥工作階段只給看的人
    with battle.lock:
        verified = battle.state == log.final_state
        out = battle_response(battle, battle.history())
    return LeagueReplayResponse(
        title_zh=match_title(store.library, record, match),
        battle=out,
        verified=verified,
        outcome_zh=match_outcome_zh(record, match),
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


@router.get("/chronicle")
def get_chronicle(request: Request) -> ChronicleView:
    """編年史（5F-5）：每季的季末紀錄、首位發現的配方、循環賽最終排名、首殺與評分榜。所有人可看。"""
    store = world_of(request)
    with store.lock:
        return chronicle_view(
            store.current_season(),
            store.chronicle.load().seasons,
            store.league.chronicle.load().seasons,
            store.first_kills.all(),
            store.boss_board.all(),
            titles=ChronicleTitles(store.titles_of_character, store.titles_of_account),
            library=store.library,
        )


@router.get("/legacy")
def get_legacy(request: Request) -> list[LegacyHeroView]:
    """自己帳號上季（含更早）的角色，新的季在前（5F-5；開發模式沒登入＝全部）。"""
    account = viewer(request)
    store = world_of(request)
    with store.lock:
        found = store.legacy_heroes(None if account is None else account.account_id)
        return legacy_view(store.library, found)


@router.post("/season/verify", dependencies=[Depends(require_season_admin)])
def post_season_verify(body: SeasonVerifyRequest, request: Request) -> ReplayCheck:
    """重播查證（管理者，5F-5c）：給一筆首殺（``target``）或一場循環賽（``match_id``），從唯讀封存
    （目前這一季從世界資料夾）確定性重播，回報結果和保留下來的紀錄是否一致。只讀。找不到 404；
    沒給對應的 ``target``／``match_id`` 422。"""
    key = body.target if body.kind == "first_kill" else body.match_id
    if key is None:
        field = "target" if body.kind == "first_kill" else "match_id"
        raise InvalidRequestError(f"{body.kind} 要給 {field}")
    return world_of(request).verify_replay(body.kind, body.season_id, key)


@router.post("/season/reset", dependencies=[Depends(require_season_admin)])
def post_season_reset(body: SeasonResetRequest, request: Request) -> SeasonResetReport:
    """季末重置（管理者，5F-5）：預設 dry-run，只列出會清什麼、留什麼；``dry_run: false`` 時先備份
    整個存檔資料夾再清，``confirm_season`` 要等於目前的季 ID。不能重置時 409。
    真的執行一律要登入的管理者帳號，開發模式也一樣（開發 PM 代決：會清資料，不比照 LLM 開關
    放行）。"""
    if not body.dry_run:
        account = viewer(request)
        if account is None or not account.admin:
            raise AdminRequiredError("季末重置要用管理者帳號登入後執行（開發模式也一樣）")
    store = world_of(request)
    return store.season_reset(
        accounts=accounts_of(request),
        start=season_start_at(store.library, body.start_date),
        season_id=body.season_id,
        seed=body.seed,
        force=body.force,
        dry_run=body.dry_run,
        confirm_season=body.confirm_season,
    )


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
