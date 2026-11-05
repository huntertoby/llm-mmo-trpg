"""郵寄的端點（Phase 6T-1a；08 8.16、#136）。畫面在 6T-1b。

- ``GET /api/world/characters/{id}/mail``：郵寄面板（郵差與他的話、收件匣、退件・過期、寄出中、
  能寄的背包物品、上限與稅率、季末提示）。
- ``GET …/mail/recipients``：寄給誰（別的帳號的角色；自己帳號的不列）。
- ``POST …/mail/quote``：寄件前的檢查（跑腿費、對方實收、估值、全部問題；不寫日誌）。
- ``POST …/mail/send``：寄信（同時改寄件人與收件人，日誌一筆）。
- ``POST …/mail/{letter}/claim``、``…/refuse``、``…/reclaim``：領信、退回寄件人、取回過期的信。
- ``GET /api/world/trades/audit``：交易稽核報表（管理者；只出報表，#101）。

錯誤：同 :mod:`trpg.api.routes.world`（動作不合法 422、角色不存在 404、戰鬥中 409）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Request

from trpg.api.auth import require_trade_admin, require_world_access
from trpg.api.state import world_of
from trpg.api.world import WorldCharacterNotFoundError, WorldStore
from trpg.api.world_mail_schemas import (
    MailActionResponse,
    MailQuoteView,
    MailRecipientView,
    MailView,
    TradeAuditView,
)
from trpg.api.world_mail_view import (
    mail_event_lines,
    mail_line,
    mail_view,
    quote_view,
    recipient_view,
)
from trpg.content.world_trade import MailLineKind
from trpg.world.errors import WorldActionError
from trpg.world.state import MailLetter
from trpg.world.trade import send_quote
from trpg.world.trade_actions import (
    MailClaimAction,
    MailClaimedEvent,
    MailReclaimAction,
    MailRefuseAction,
    MailSendAction,
)
from trpg.world.trade_audit import audit_trades

__all__ = ["router"]

router = APIRouter(prefix="/api/world", tags=["mail"], dependencies=[Depends(require_world_access)])


type _Letter = Annotated[str, Path(pattern=r"^mail_[0-9]{6,}$")]


def _lookup(store: WorldStore) -> Callable[[str], MailLetter | None]:
    """信件 ID → 收件人信箱裡的那封信（照交易帳找收件人；讀不到為 ``None``）。"""
    world = store.world()

    def find(letter_id: str) -> MailLetter | None:
        record = world.trade(letter_id)
        if record is None:
            return None
        try:
            other = store.character(record.recipient)
        except WorldCharacterNotFoundError:
            return None
        return next((m for m in other.mailbox if m.id == letter_id), None)

    return find


def _mail(store: WorldStore, character_id: str, line: MailLineKind | None = None) -> MailView:
    char = store.character(character_id)
    now = store.clock()
    view = mail_view(store.library, store.world(), char, now, lookup=_lookup(store), line=line)
    if view is None:
        raise WorldActionError("這個世界還沒有開放交易")
    return view


@router.get("/characters/{character_id}/mail")
def get_mail(character_id: str, request: Request) -> MailView:
    store = world_of(request)
    with store.lock:
        store.sync(character_id)
        return _mail(store, character_id)


@router.get("/characters/{character_id}/mail/recipients")
def get_recipients(character_id: str, request: Request) -> list[MailRecipientView]:
    """別的帳號的角色（依名字、ID 排序）。"""
    store = world_of(request)
    with store.lock:
        mine = store.account_of(character_id)
        now = store.clock()
        rows = []
        for cid in store.character_ids():
            if cid == character_id or store.account_of(cid) == mine:
                continue
            try:
                other = store.character(cid)
            except WorldCharacterNotFoundError:
                continue
            rows.append(recipient_view(store.library, other, now))
        return sorted(rows, key=lambda r: (r.name_zh, r.character_id))


@router.post("/characters/{character_id}/mail/quote")
def post_quote(
    character_id: str, request: Request, action: Annotated[MailSendAction, Body()]
) -> MailQuoteView:
    store = world_of(request)
    with store.lock:
        char = store.character(character_id)
        try:
            other = store.character(action.to)
        except WorldCharacterNotFoundError:
            other = None
        quote = send_quote(
            store.library,
            store.world(),
            char,
            other,
            action,
            now=store.clock(),
            actor=store.account_of(character_id),
            other_actor=None if other is None else store.account_of(action.to),
        )
        return quote_view(store.library, char.region, quote)


def _act(
    store: WorldStore,
    character_id: str,
    action: MailSendAction | MailClaimAction | MailRefuseAction | MailReclaimAction,
) -> MailActionResponse:
    outcome = store.act(character_id, action)
    line: MailLineKind | None = None
    if isinstance(action, MailSendAction):
        line = "sent"
    elif isinstance(action, MailReclaimAction) or any(
        isinstance(e, MailClaimedEvent) and e.returned is not None for e in outcome.events
    ):
        line = "returned"
    view = _mail(store, character_id, line)
    return MailActionResponse(
        mail=view,
        events=mail_event_lines(store.library, outcome.events),
        line_zh=None if line is None else mail_line(store.library, outcome.char.region, line),
    )


@router.post("/characters/{character_id}/mail/send")
def post_send(
    character_id: str, request: Request, action: Annotated[MailSendAction, Body()]
) -> MailActionResponse:
    store = world_of(request)
    with store.lock:
        return _act(store, character_id, action)


@router.post("/characters/{character_id}/mail/{letter}/claim")
def post_claim(character_id: str, letter: _Letter, request: Request) -> MailActionResponse:
    store = world_of(request)
    with store.lock:
        return _act(store, character_id, MailClaimAction(letter=letter))


@router.post("/characters/{character_id}/mail/{letter}/refuse")
def post_refuse(character_id: str, letter: _Letter, request: Request) -> MailActionResponse:
    store = world_of(request)
    with store.lock:
        return _act(store, character_id, MailRefuseAction(letter=letter))


@router.post("/characters/{character_id}/mail/{letter}/reclaim")
def post_reclaim(character_id: str, letter: _Letter, request: Request) -> MailActionResponse:
    store = world_of(request)
    with store.lock:
        return _act(store, character_id, MailReclaimAction(letter=letter))


@router.get("/trades/audit", dependencies=[Depends(require_trade_admin)])
def get_trade_audit(request: Request) -> TradeAuditView:
    """這一季交易帳的可疑項目（短時間大量、大額、估值懸殊）；只出報表，不自動處理。"""
    store = world_of(request)
    with store.lock:
        world = store.world()
        rules = store.library.world_trade
        flags = () if rules is None else audit_trades(rules.audit, world.trades)
        return TradeAuditView(season_id=world.season_id, trades=len(world.trades), flags=flags)
