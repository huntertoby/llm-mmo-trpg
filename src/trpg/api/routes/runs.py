"""roguelite 一輪的端點（Phase 3-5a；``docs/phases/Phase3計畫.md`` 7.1）。

- ``POST /api/runs``：開新一輪（build、種子、開局配點）。
- ``GET /api/runs/saves``：存檔列表。
- ``POST /api/runs/load``：讀檔（``run_id``）；戰鬥中的存檔重播到存檔當下。
- ``GET /api/runs/{run_id}``：一輪的狀態（戰鬥已結束時先結算）。
- ``POST /api/runs/{run_id}/battle``：開始或接續本場戰鬥（回傳一輪與戰鬥；之後用
  ``/api/battles/{battle_id}/…`` 操作）。
- ``POST /api/runs/{run_id}/choice``：升級選擇、營火重骰／選擇／離開。
- ``POST /api/runs/{run_id}/save``：存檔（戰鬥中也可以）。

錯誤：不存在 404、節點不符 409、內容不合法或存檔壞掉 422。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from trpg.api.presenter import battle_response
from trpg.api.run_presenter import run_response, save_summary
from trpg.api.run_schemas import (
    CreateRunRequest,
    LoadRunRequest,
    RunBattleResponse,
    RunResponse,
    SaveOut,
    SaveSummary,
)
from trpg.api.runs import RunSession
from trpg.api.state import runs_of
from trpg.roguelite.state import Choice

__all__ = ["router"]

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _respond(session: RunSession) -> RunResponse:
    session.sync()
    return run_response(session)


@router.post("", status_code=201)
def create_run(body: CreateRunRequest, request: Request) -> RunResponse:
    session = runs_of(request).create(body.build, body.seed, body.attributes)
    with session.lock:
        return _respond(session)


@router.get("/saves")
def list_saves(request: Request) -> list[SaveSummary]:
    return [save_summary(s) for s in runs_of(request).saves()]


@router.post("/load")
def load_run(body: LoadRunRequest, request: Request) -> RunResponse:
    session = runs_of(request).load(body.run_id)
    with session.lock:
        return _respond(session)


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> RunResponse:
    session = runs_of(request).get(run_id)
    with session.lock:
        return _respond(session)


@router.post("/{run_id}/battle")
def run_battle(run_id: str, request: Request) -> RunBattleResponse:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        battle, records = store.battle(session)
        with battle.lock:
            battle_out = battle_response(battle, records)
        return RunBattleResponse(run=run_response(session), battle=battle_out)


@router.post("/{run_id}/choice")
def post_choice(run_id: str, choice: Choice, request: Request) -> RunResponse:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        store.choose(session, choice)
        return _respond(session)


@router.post("/{run_id}/save")
def save_run(run_id: str, request: Request) -> SaveOut:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        path, save = store.save(session)
        return SaveOut(
            run_id=save.run_id,
            file=path.name,
            format=save.format,
            in_battle=save.battle is not None,
        )
