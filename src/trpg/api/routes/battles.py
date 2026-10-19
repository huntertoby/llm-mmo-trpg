"""戰鬥端點（``docs/phases/Phase3計畫.md`` 4.4）。

會改變狀態的請求一律先取得該場戰鬥的鎖（同一場戰鬥依序處理）。錯誤碼由 ``trpg.api.app`` 的
例外處理器對應：不存在 404、不合法的動作 400、狀態不符 409、內容錯誤 422、推進超過上限 500。
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from trpg.api.presenter import battle_response
from trpg.api.schemas import (
    BattleResponse,
    CreateBattleRequest,
    DecisionRequest,
    PreviewOut,
    preview_out,
)
from trpg.api.state import store_of
from trpg.engine.actions import Action
from trpg.engine.ai.orders import OrderSet

__all__ = ["router"]

router = APIRouter(prefix="/api/battles", tags=["battles"])


@router.post("", status_code=201)
def create_battle(body: CreateBattleRequest, request: Request) -> BattleResponse:
    """建立戰鬥並推進到第一次輪到主角；``steps`` 含開場事件。"""
    session, records = store_of(request).create(body)
    with session.lock:
        return battle_response(session, records)


@router.get("/{battle_id}")
def get_battle(battle_id: str, request: Request) -> BattleResponse:
    session = store_of(request).get(battle_id)
    with session.lock:
        return battle_response(session, [])


@router.post("/{battle_id}/actions")
def post_action(battle_id: str, action: Action, request: Request) -> BattleResponse:
    session = store_of(request).get(battle_id)
    with session.lock:
        before = session.state
        records = session.act(action)
        return battle_response(session, records, before)


@router.post("/{battle_id}/decision")
def post_decision(battle_id: str, body: DecisionRequest, request: Request) -> BattleResponse:
    session = store_of(request).get(battle_id)
    with session.lock:
        before = session.state
        records = session.decide(body.accept)
        return battle_response(session, records, before)


@router.post("/{battle_id}/preview")
def post_preview(battle_id: str, action: Action, request: Request) -> PreviewOut:
    session = store_of(request).get(battle_id)
    with session.lock:
        return preview_out(session.preview(action))


@router.put("/{battle_id}/orders")
def put_orders(battle_id: str, orders: OrderSet, request: Request) -> BattleResponse:
    """設定我方隊友的戰術指令（取代目前的指令；空集合 ＝ 取消）。不推進戰鬥。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        session.set_orders(orders)
        return battle_response(session, [])


@router.get("/{battle_id}/log")
def get_log(battle_id: str, request: Request) -> Response:
    """與 ``trpg battle --log-json`` 同格式的完整紀錄（可用 ``trpg battle replay`` 重播）。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        text = session.to_log().model_dump_json(indent=1)
    return Response(content=text, media_type="application/json")
