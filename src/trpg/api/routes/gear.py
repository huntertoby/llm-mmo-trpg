"""裝備測試端點（Phase 3G-G4，開發工具）。

``GET /api/gear/catalog`` 是選單（欄位、測試物品、詞條白名單、武器）；
``POST /api/gear/check`` 檢查一組裝備並回傳穿上後的主角（含加成來源）。「進戰鬥」是
``POST /api/battles`` 的 ``equipment``。所有驗證都在 :mod:`trpg.api.gear`（沿用引擎的驗證函式）。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from trpg.api.gear import gear_catalog, gear_problems
from trpg.api.gear_schemas import GearCatalog, GearCheck, GearCheckRequest
from trpg.api.schemas import CreateBattleRequest
from trpg.api.state import store_of
from trpg.engine.battle import begin_battle
from trpg.engine.setup import BattleSetupError
from trpg.engine.view import UnitView, project_for
from trpg.shared.types import Team

__all__ = ["router"]

router = APIRouter(prefix="/api/gear", tags=["gear"])


@router.get("/catalog")
def get_catalog(request: Request) -> GearCatalog:
    """裝備測試的選單。"""
    return gear_catalog(store_of(request).library)


@router.post("/check")
def post_check(body: GearCheckRequest, request: Request) -> GearCheck:
    """靶場上的主角穿這組裝備是否合法；合法時附上開戰時的主角（含裝備、加成來源與實際數值）。"""
    store = store_of(request)
    library = store.library
    base = store.base_setup(
        CreateBattleRequest(
            map_id=library.workshop.map, seed=0, hero_build=body.hero_build, ally_builds=()
        )
    )
    setup, problems = gear_problems(base, library, body.equipment)
    if problems:
        return GearCheck(legal=False, problems=tuple(problems))
    try:
        state = begin_battle(setup, 0).state
    except BattleSetupError as exc:
        return GearCheck(legal=False, problems=(str(exc),))
    hero_id = next(u.id for u in state.units_sorted() if u.team is Team.ALLY)
    hero: UnitView = next(u for u in project_for(state, Team.ALLY).units if u.id == hero_id)
    return GearCheck(legal=True, hero=hero)
