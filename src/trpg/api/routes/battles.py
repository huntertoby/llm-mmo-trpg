"""戰鬥端點（``docs/phases/Phase3計畫.md`` 4.4）。

會改變狀態的請求一律先取得該場戰鬥的鎖（同一場戰鬥依序處理）。錯誤碼由 ``trpg.api.app`` 的
例外處理器對應：不存在 404、不合法的動作 400、狀態不符 409、內容錯誤 422、推進超過上限 500。
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from trpg.api.hero_cards import hero_cards
from trpg.api.presenter import battle_response, history_response, preview_response
from trpg.api.schemas import (
    BattleHistory,
    BattleResponse,
    CommandOptionOut,
    CommandOptionsOut,
    CreateBattleRequest,
    DecisionRequest,
    HeroCards,
    InfuseOptionsOut,
    InfuseSkillOptionOut,
    PreviewOut,
    SkillReasons,
)
from trpg.api.skill_reasons import skill_reasons
from trpg.api.state import runs_of, store_of
from trpg.engine.actions import Action
from trpg.engine.ai.orders import OrderSet
from trpg.shared.types import UnitId

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


@router.get("/{battle_id}/history")
def get_history(battle_id: str, request: Request) -> BattleHistory:
    """到目前為止發生過的事件（還原戰鬥紀錄用：重新整理或讀檔回到戰鬥時）。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        return history_response(session)


@router.post("/{battle_id}/actions")
def post_action(battle_id: str, action: Action, request: Request) -> BattleResponse:
    session = store_of(request).get(battle_id)
    with session.lock:
        before = session.state
        records = session.act(action)
        out = battle_response(session, records, before)
    runs_of(request).autosave_battle(battle_id)  # 一輪的戰鬥：自動存檔（Phase 3-6）
    return out


@router.post("/{battle_id}/decision")
def post_decision(battle_id: str, body: DecisionRequest, request: Request) -> BattleResponse:
    session = store_of(request).get(battle_id)
    with session.lock:
        before = session.state
        records = session.decide(body.accept, body.copy_cast, body.followup_target)
        out = battle_response(session, records, before)
    runs_of(request).autosave_battle(battle_id)
    return out


@router.post("/{battle_id}/preview")
def post_preview(battle_id: str, action: Action, request: Request) -> PreviewOut:
    session = store_of(request).get(battle_id)
    with session.lock:
        return preview_response(session.preview(action), session.state)


@router.get("/{battle_id}/summons/{summon_id}/command-options")
def get_command_options(battle_id: str, summon_id: str, request: Request) -> CommandOptionsOut:
    """指揮主角的一隻召喚物（Phase 3-33c）時可選的終點與各終點打得到的敵人。不改變狀態。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        options = session.command_options(UnitId(summon_id))
        cost = session.state.ruleset.core.summon_command_ap_cost
    return CommandOptionsOut(
        summon_id=UnitId(summon_id),
        ap_cost=cost,
        options=tuple(
            CommandOptionOut(dest=o.dest, path=o.path, targets=o.targets) for o in options
        ),
    )


@router.get("/{battle_id}/summons/{summon_id}/infuse-options")
def get_infuse_options(battle_id: str, summon_id: str, request: Request) -> InfuseOptionsOut:
    """灌注技能給主角的一隻召喚物（Phase 3-33d）時的技能選單：不能灌注的附中文原因。不改變狀態。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        problem, choices = session.infuse_options(UnitId(summon_id))
        cost = session.state.ruleset.core.summon_infuse_ap_cost
    return InfuseOptionsOut(
        summon_id=UnitId(summon_id),
        ap_cost=cost,
        problem=problem,
        skills=tuple(
            InfuseSkillOptionOut(skill_id=c.skill_id, name_zh=c.name_zh, problem=c.problem)
            for c in choices
        ),
    )


@router.get("/{battle_id}/skill-reasons")
def get_skill_reasons(battle_id: str, request: Request) -> SkillReasons:
    """主角灰掉的技能的原因（引擎的拒絕理由）。不改變狀態、不推進戰鬥。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        return skill_reasons(session.state, session.hero_id)


@router.get("/{battle_id}/hero-cards")
def get_hero_cards(battle_id: str, request: Request) -> HeroCards:
    """主角的技能卡（附施放者當下的實際值：傷害算法的目前加成、召喚物資訊；3-41c）。不改變狀態、
    不推進戰鬥。"""
    store = store_of(request)
    session = store.get(battle_id)
    with session.lock:
        return hero_cards(session.state, store.library, session.hero_id)


@router.put("/{battle_id}/orders")
def put_orders(battle_id: str, orders: OrderSet, request: Request) -> BattleResponse:
    """設定我方隊友的戰術指令（取代目前的指令；空集合 ＝ 取消）。不推進戰鬥。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        session.set_orders(orders)
        out = battle_response(session, [])
    runs_of(request).autosave_battle(battle_id)
    return out


@router.get("/{battle_id}/log")
def get_log(battle_id: str, request: Request) -> Response:
    """與 ``trpg battle --log-json`` 同格式的完整紀錄（可用 ``trpg battle replay`` 重播）。"""
    session = store_of(request).get(battle_id)
    with session.lock:
        text = session.to_log().model_dump_json(indent=1)
    return Response(content=text, media_type="application/json")
