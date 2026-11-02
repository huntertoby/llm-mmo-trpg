"""大世界的端點（Phase 5A-5；``docs/phases/Phase5計畫.md`` 10.3）。

- ``GET /api/world/characters``：角色列表。
- ``POST /api/world/characters``：建立角色（07 7.6 創角；選項沿用 ``/api/runs/start-options``）。
- ``GET /api/world/characters/{id}``：地點圖畫面的整份資料（先同步已結束的戰鬥）。
- ``POST /api/world/characters/{id}/actions``：移動、紮營、撤退、休息、換技能、傳送。
- ``POST /api/world/characters/{id}/battle``：開戰或接續進行中的戰鬥（之後用 ``/api/battles``）。

錯誤：角色不存在 404；動作或內容不合法 422；戰鬥中做其他動作、沒有遭遇卻開戰 409。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Request

from trpg.api.presenter import battle_response
from trpg.api.state import world_of
from trpg.api.world import WorldOutcome, WorldStore
from trpg.api.world_presenter import character_summary, event_lines, world_view
from trpg.api.world_schemas import (
    CreateWorldCharacterRequest,
    WorldActionRequest,
    WorldBattleResponse,
    WorldCharacterSummary,
    WorldView,
)

__all__ = ["router"]

router = APIRouter(prefix="/api/world", tags=["world"])


def _view(store: WorldStore, outcome: WorldOutcome, region: str) -> WorldView:
    battle = outcome.battle
    return world_view(
        store.library,
        outcome.world,
        outcome.char,
        outcome.now,
        events=event_lines(store.library, region, outcome.events),
        battle_id=battle.battle_id if battle is not None else None,
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
    store = world_of(request)
    with store.lock:
        region = store.character(character_id).region
        return _view(store, store.act(character_id, action), region)


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
