"""數值工坊端點（NW-1a A8；前綴 ``/api/tuning``，``/api/workshop`` 已被技能工坊用）。

**三道門**（第 0 節第 2 點，缺一不可）：

1. ``dev_mode`` 為真才掛（:func:`trpg.api.app._include_routers`）；
2. 另要環境變數 ``TRPG_TUNING=1``（不沿用 ``TRPG_DEV_ROUTES``）——沒開時端點**不存在**（不掛
   路由，404）；
3. 每個請求帶 ``CF-Connecting-IP``、``X-Forwarded-For``、``Forwarded`` 任一標頭（＝經 Tunnel 或
   反向代理轉發）就 403「數值工坊只能在本機瀏覽器直接開」（:func:`local_only`）。

錯誤一律 ``{"detail": "<中文>"}``。
"""

from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request, Response
from pydantic import ValidationError

from trpg.api.tuning.drafts import DRAFT_NAME_PATTERN
from trpg.api.tuning.objects import ObjectNotFoundError
from trpg.api.tuning.schemas import (
    TuningApplyIn,
    TuningApplyResult,
    TuningBudgetIn,
    TuningBudgetResult,
    TuningCheckResult,
    TuningDiff,
    TuningDraftIn,
    TuningDraftView,
    TuningGroupIn,
    TuningGroupPreset,
    TuningGroupPreview,
    TuningHistoryEntry,
    TuningLadders,
    TuningObjectDetail,
    TuningObjectSummary,
    TuningSimJob,
    TuningSimOptions,
    TuningSimRequest,
    TuningStatus,
)
from trpg.api.tuning.service import DraftInputError, TuningService
from trpg.api.tuning.sim_jobs import SimBusyError, SimRequestError
from trpg.api.tuning.skills import GroupError
from trpg.api.tuning.writeback import WritebackError

__all__ = ["FORWARD_HEADERS", "TUNNEL_ZH", "local_only", "router"]

FORWARD_HEADERS: Final = ("cf-connecting-ip", "x-forwarded-for", "forwarded")
TUNNEL_ZH: Final = "數值工坊只能在本機瀏覽器直接開"


def local_only(request: Request) -> None:
    """第三道門：轉發標頭任一個在就 403。"""
    if any(name in request.headers for name in FORWARD_HEADERS):
        raise HTTPException(status_code=403, detail=TUNNEL_ZH)


router = APIRouter(prefix="/api/tuning", tags=["tuning"], dependencies=[Depends(local_only)])

DraftName = Annotated[str, Path(pattern=DRAFT_NAME_PATTERN)]


def _service(request: Request) -> TuningService:
    service = getattr(request.app.state, "tuning", None)
    if not isinstance(service, TuningService):
        raise HTTPException(status_code=404, detail="Not Found")
    return service


Service = Annotated[TuningService, Depends(_service)]


@router.get("/status")
def get_status(service: Service) -> TuningStatus:
    """能不能寫回與原因、是否要重開伺服器、草稿清單、跑中的模擬。"""
    return service.status()


@router.get("/objects")
def get_objects(service: Service, kind: str | None = None) -> list[TuningObjectSummary]:
    """可改的對象（``unit``：敵人與頭目；``skill``：技能，附篩選欄位與 1 階預算比例）。"""
    return service.objects(kind)


@router.post("/skills/group-preview")
def post_group_preview(body: TuningGroupIn, service: Service) -> TuningGroupPreview:
    """分組改的預覽（不寫檔）：逐招的改動、前後預算比例、跳過原因（一次最多 100 招）。"""
    try:
        return service.group_preview(body)
    except GroupError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ObjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/skills/presets")
def get_presets(service: Service) -> list[TuningGroupPreset]:
    """分組改的常用預設組。"""
    return service.presets()


@router.get("/skills/ladders")
def get_ladders(service: Service) -> TuningLadders:
    """骰子與武器倍率的階梯（由弱到強；骰子欄位「±1 級」用，和分組改同一份）。"""
    return service.ladders()


@router.post("/skills/{skill_id}/budget")
def post_budget(
    skill_id: Annotated[str, Path(pattern=r"^skill_[a-z0-9_]+$")],
    service: Service,
    body: Annotated[TuningBudgetIn | None, Body()] = None,
) -> TuningBudgetResult:
    """一招套上改動後的預算比例、判定、變奏、違規（數字同 ``trpg skills budget``）。"""
    try:
        return service.budget(skill_id, [] if body is None else body.changes)
    except ObjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/objects/{kind}/{object_id}")
def get_object(kind: str, object_id: str, service: Service) -> TuningObjectDetail:
    """一個對象的欄位（中文標籤、現值、建議範圍）。"""
    try:
        return service.object(kind, object_id)
    except ObjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/drafts/{name}")
def get_draft(name: DraftName, service: Service) -> TuningDraftView:
    """草稿（沒有時是空的）。"""
    return service.draft(name)


@router.put("/drafts/{name}")
def put_draft(name: DraftName, body: TuningDraftIn, service: Service) -> TuningDraftView:
    """整張改動單覆寫草稿（同一欄位只留一筆、改回原值的去掉）。"""
    try:
        return service.put_draft(name, body.changes)
    except (DraftInputError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/drafts/{name}", status_code=204)
def delete_draft(name: DraftName, service: Service) -> Response:
    """丟掉草稿（沒有也 204）。"""
    service.delete_draft(name)
    return Response(status_code=204)


@router.post("/drafts/{name}/check")
def post_check(
    name: DraftName,
    service: Service,
    body: Annotated[TuningDraftIn | None, Body()] = None,
) -> TuningCheckResult:
    """驗證（＝``trpg content check`` 同一套）。給了 body 就驗它（不必先存）。"""
    return service.check(name, None if body is None else body.changes)


@router.get("/drafts/{name}/diff")
def get_diff(name: DraftName, service: Service) -> TuningDiff:
    """差異表與 ``git diff`` 風格的文字。"""
    return service.diff(name)


@router.post("/drafts/{name}/revert/{commit}")
def post_revert(
    name: DraftName,
    service: Service,
    commit: Annotated[str, Path(pattern=r"^[0-9a-f]{7,40}$")],
) -> TuningDraftView:
    """把一筆 ``tune:`` commit 的反向改動單併進草稿（之後照樣驗證、寫回）。"""
    try:
        return service.revert(name, commit)
    except WritebackError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/drafts/{name}/apply")
def post_apply(
    name: DraftName,
    service: Service,
    body: Annotated[TuningApplyIn | None, Body()] = None,
) -> TuningApplyResult:
    """寫回 ``content/`` 並自動 commit 一筆 ``tune:``（前置檢查不過時 409，檔案不變）。

    草稿裡有招超出預算合格區間時，``confirm_budget`` 要恰好是那幾招（勾「我確定」），否則 409；
    確認後一起登記進 ``skill_budget.yaml`` 的例外清單。"""
    confirm = [] if body is None else body.confirm_budget
    moves = [] if body is None else body.confirm_min_moves
    try:
        return service.apply(name, confirm, moves)
    except WritebackError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/history")
def get_history(service: Service, limit: int = 20) -> list[TuningHistoryEntry]:
    """最近的 ``tune:`` commit（``git log --grep '^tune'``）。"""
    return service.history(max(1, min(limit, 50)))


@router.get("/sims/options")
def get_sim_options(service: Service) -> TuningSimOptions:
    """模擬情境的選項（頭目、build）與估時參數。"""
    try:
        return service.sim_options()
    except SimRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/sims")
def post_sim(body: TuningSimRequest, service: Service) -> TuningSimJob:
    """開一個模擬工作（背景；一次一個，再開回 409）。"""
    try:
        return service.start_sim(body)
    except SimBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SimRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sims/{job_id}")
def get_sim(job_id: str, service: Service) -> TuningSimJob:
    """工作進度與結果（前端每秒問一次）。"""
    job = service.sims.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="沒有這個模擬工作")
    return job


@router.delete("/sims/{job_id}")
def delete_sim(job_id: str, service: Service) -> TuningSimJob:
    """取消模擬（還沒開始的場次不跑；已在跑的跑完丟掉）。"""
    job = service.sims.cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="沒有這個模擬工作")
    return job
