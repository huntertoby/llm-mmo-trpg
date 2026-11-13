"""郵寄面板的畫面資料（Phase 6T-1a；格式在 :mod:`trpg.api.world_mail_schemas`）。

規則在 :mod:`trpg.world.trade`（純函式）；這裡只把角色、世界與交易規則轉成畫面要的句子與旗標。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from trpg.api.run_presenter import origin_realm
from trpg.api.world_economy_schemas import BagItemView
from trpg.api.world_economy_view import inventory_view, item_rare
from trpg.api.world_field_people import look_of
from trpg.api.world_mail_schemas import (
    LetterItemView,
    LetterView,
    MailBadgeView,
    MailProblemView,
    MailQuoteView,
    MailRecipientView,
    MailTabLinesView,
    MailView,
    PostmanView,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_trade import DAY_SECONDS, MailLineKind, Postman, TradeRules
from trpg.world.actions import WorldEvent
from trpg.world.gear import hero_loadout
from trpg.world.inventory import add_items, slots_over
from trpg.world.state import CharacterState, MailLetter, WorldState
from trpg.world.trade import (
    MailQuote,
    incoming_letters,
    place_name,
    postman_here,
    season_warning,
)
from trpg.world.trade_actions import (
    MailClaimedEvent,
    MailRefusedEvent,
    MailSentEvent,
)

__all__ = [
    "mail_badge",
    "mail_event_line",
    "mail_event_lines",
    "mail_line",
    "mail_view",
    "quote_view",
    "recipient_view",
]

type LetterLookup = Callable[[str], MailLetter | None]
"""信件 ID → 收件人信箱裡的那封信（寄出中、過期的信在對方身上；找不到為 ``None``）。"""


def _postman(library: ContentLibrary, postman: Postman) -> PostmanView:
    card = postman.card
    return PostmanView(
        id=card.id,
        name_zh=card.name_zh,
        race_zh=postman.race_zh,
        role_zh=card.role_zh,
        region=postman.region,
        location=card.location,
        place_zh=place_name(library, postman.region, card.location),
        portrait=card.portrait,
    )


def _returned_out(
    world: WorldState, char: CharacterState, now: int, lookup: LetterLookup
) -> list[MailLetter]:
    """寄出去、已經過期的信（自動退回寄件人，6T-1b；資料還在對方的信箱裡，寄件人照退件領）。"""
    found: list[MailLetter] = []
    for record in world.trades:
        if record.sender != char.character_id or record.status != "sent" or now < record.expires_at:
            continue
        letter = lookup(record.id)
        if letter is not None and letter.overdue(now):
            found.append(letter)
    return found


def _outgoing(
    world: WorldState, char: CharacterState, now: int, lookup: LetterLookup
) -> list[MailLetter]:
    found: list[MailLetter] = []
    for record in world.trades:
        if (
            record.sender == char.character_id
            and record.status == "sent"
            and now < record.expires_at
        ):
            letter = lookup(record.id)
            if letter is not None:
                found.append(letter)
    return found


def mail_line(library: ContentLibrary, region: str, kind: MailLineKind) -> str | None:
    """``region`` 的郵差在這個情境說的話；沒有郵差為 ``None``。"""
    rules = library.world_trade
    postman = None if rules is None else rules.mail.postman_of(region)
    return None if postman is None else postman.lines.line(kind)


def mail_badge(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> MailBadgeView | None:
    """郵差頭上的「✉」（角色所在區域有郵差時）：收件匣能領的、被拒收退回的、過期自動退回的（照
    交易帳算，不用讀對方的存檔）。"""
    rules = library.world_trade
    postman = None if rules is None else rules.mail.postman_of(char.region)
    if postman is None:
        return None
    unread = len(incoming_letters(char, now))
    returned = sum(1 for m in char.mailbox if m.returned is not None)
    returned += sum(
        1
        for t in world.trades
        if t.sender == char.character_id and t.status == "sent" and now >= t.expires_at
    )
    return MailBadgeView(
        postman=postman.card.id,
        region=postman.region,
        location=postman.card.location,
        here=postman_here(library, char) is not None,
        unread=unread,
        returned=returned,
        bubble="✉" if unread or returned else None,
    )


def _items(library: ContentLibrary, counts: dict[str, int]) -> tuple[LetterItemView, ...]:
    rows = []
    for item, count in sorted(counts.items()):
        found = library.world_economy.items.get(item)
        rows.append(
            LetterItemView(
                item=item,
                name_zh=item if found is None else found.name_zh,
                count=count,
                color=None if found is None else found.color,  # QI-7
                rare=None if found is None else item_rare(found),
            )
        )
    return tuple(rows)


def _gear_cards(library: ContentLibrary, letter: MailLetter) -> tuple[BagItemView, ...]:
    """附件裝備的卡片（照收件人的背包格式；來歷照信上記的）。"""
    views = []
    for piece in letter.gear:
        origin = letter.gear_origin.get(piece.id)
        views.append(
            BagItemView(
                item=piece.id,
                name_zh=piece.name_zh
                if piece.item_level is None
                else f"{piece.name_zh}（{piece.item_level} 級）",
                kind_zh="裝備",
                count=1,
                description_zh="",
                sell_price=0,
                field_usable=False,
                gear=True,
                tradable=origin is not None and origin.tradable,
                origin_zh=None
                if origin is None
                else f"最初得自：{origin.owner_name}（{origin.source_zh}）",
            )
        )
    return tuple(views)


def _fits(library: ContentLibrary, char: CharacterState, letter: MailLetter) -> bool:
    bag = add_items(char.bag, letter.items)
    return slots_over(library, bag, len(char.gear) + len(letter.gear)) == 0


def _letter(
    library: ContentLibrary,
    char: CharacterState,
    letter: MailLetter,
    now: int,
    *,
    action: str | None,
    status_zh: str,
    here: bool,
    can_refuse: bool = False,
) -> LetterView:
    problem: str | None = None
    if action is not None and not here:
        problem = "要在城鎮的郵差這裡"
    elif action is not None and not _fits(library, char, letter):
        problem = "背包放不下，先整理背包"
    left = max(0, -(-(letter.expires_at - now) // DAY_SECONDS))
    return LetterView(
        id=letter.id,
        sender=letter.sender,
        sender_name=letter.sender_name,
        recipient=letter.recipient,
        recipient_name=letter.recipient_name,
        from_zh=place_name(library, letter.from_region, letter.from_location),
        sent_at=letter.sent_at,
        expires_at=letter.expires_at,
        days_left=0 if letter.returned is not None else left,
        note=letter.note,
        items=_items(library, letter.items),
        gear=_gear_cards(library, letter),
        gold=letter.gold,
        tax=letter.tax,
        status_zh=status_zh,
        action=action,
        can_act=action is not None and problem is None,
        problem_zh=problem,
        can_refuse=can_refuse and here,
    )


_RETURNED_ZH = {"refused": "被拒收退回", "expired": "過期退回"}
_CLAIMED_ZH = {"refused": "被拒收退回來的信", "expired": "過期退回來的信"}


def _sendable(library: ContentLibrary, char: CharacterState) -> tuple[BagItemView, ...]:
    inventory = inventory_view(library, char, in_battle=False)
    return () if inventory is None else inventory.bag


def mail_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    lookup: LetterLookup,
    line: MailLineKind | None = None,
) -> MailView | None:
    """郵寄面板；沒有交易規則時為 ``None``。``line`` 指定郵差這次要說的情境（省略＝照有沒有信）。"""
    rules: TradeRules | None = library.world_trade
    if rules is None:
        return None
    postman = rules.mail.postman_of(char.region)
    here = postman_here(library, char) is not None and char.pending_encounter is None
    inbox = [
        _letter(
            library, char, m, now, action="claim", status_zh="可以領", here=here, can_refuse=True
        )
        for m in incoming_letters(char, now)
    ]
    returned = [
        _letter(
            library, char, m, now, action="claim", status_zh=_RETURNED_ZH[m.returned], here=here
        )
        for m in char.mailbox
        if m.returned is not None
    ]
    returned += [
        _letter(library, char, m, now, action="claim", status_zh="過期退回", here=here)
        for m in _returned_out(world, char, now, lookup)
    ]
    outgoing = [
        _letter(library, char, m, now, action=None, status_zh="寄出中", here=here)
        for m in _outgoing(world, char, now, lookup)
    ]
    level_ok = char.level >= rules.trade.min_level
    opening: MailLineKind = (
        "has_mail" if inbox or returned else ("open" if level_ok else "low_level")
    )
    if line is None:
        line = opening
    warning = season_warning(library, world, now)
    texts = rules.mail.texts
    return MailView(
        postman=None if postman is None else _postman(library, postman),
        here=here,
        here_problem_zh=None if here else "信只能在城鎮的郵差這裡寄、這裡領",
        line_zh=None if postman is None else postman.lines.line(line),
        inbox=tuple(inbox),
        returned=tuple(returned),
        outgoing=tuple(outgoing),
        sendable=_sendable(library, char),
        gold=char.gold,
        mailbox_count=len(inbox),
        mailbox_max=rules.mail.mailbox_max,
        max_attachments=rules.mail.max_attachments,
        note_max=rules.mail.note_max,
        tax_permille=rules.trade.gold_tax_permille,
        min_level=rules.trade.min_level,
        level_ok=level_ok,
        return_days=rules.mail.return_days,
        season_warning_zh=texts.season_warning_zh if warning else None,
        footer_zh=texts.format(texts.footer_zh, rules.mail.return_days),
        send_note_zh=texts.format(texts.send_note_zh, rules.mail.return_days),
        tab_lines=None
        if postman is None
        else MailTabLinesView(**postman.lines.tab_lines(postman.lines.line(opening))),
    )


def quote_view(library: ContentLibrary, region: str, quote: MailQuote) -> MailQuoteView:
    """寄件前的檢查結果。"""
    rules = library.world_trade
    permille = 0 if rules is None else rules.trade.gold_tax_permille
    tax_zh = ""
    if quote.gold > 0:
        percent = f"{permille // 10}%" if permille % 10 == 0 else f"{permille / 10:g}%"
        tax_zh = f"跑腿費 {percent}：−{quote.tax}　對方實收 {quote.received}"
    first = next((p for p in quote.problems if p.line is not None), None)
    return MailQuoteView(
        ok=quote.ok,
        gold=quote.gold,
        tax=quote.tax,
        received=quote.received,
        value=quote.value,
        tax_zh=tax_zh,
        problems=tuple(MailProblemView(code=p.code, text_zh=p.text_zh) for p in quote.problems),
        line_zh=None
        if first is None or first.line is None
        else mail_line(library, region, first.line),
        season_warning_zh=None
        if rules is None or not quote.season_warning
        else rules.mail.texts.season_warning_zh,
    )


def recipient_view(library: ContentLibrary, char: CharacterState, now: int) -> MailRecipientView:
    """寄給誰的一列（收件的那個角色）。"""
    rules = library.world_trade
    problem: str | None = None
    if rules is not None and char.level < rules.trade.min_level:
        problem = f"還不到 {rules.trade.min_level} 級"
    elif rules is not None and len(incoming_letters(char, now)) >= rules.mail.mailbox_max:
        problem = "信箱滿了"
    return MailRecipientView(
        character_id=char.character_id,
        name_zh=char.hero.name_zh,
        level=char.level,
        region=char.region,
        place_zh=place_name(library, char.region, char.location),
        can_receive=problem is None,
        problem_zh=problem,
        hero_look=look_of(library, char.hero, hero_loadout(library, char)),
        origin_realm=origin_realm(library, char.origin),
    )


def _counts_zh(library: ContentLibrary, counts: dict[str, int], gear: Sequence[str]) -> str:
    parts = [f"{row.name_zh} ×{row.count}" for row in _items(library, counts)]
    parts += list(gear)
    return "、".join(parts)


def mail_event_line(library: ContentLibrary, event: WorldEvent) -> str | None:
    """郵寄事件 → 中文句子。"""
    if isinstance(event, MailSentEvent):
        what = _counts_zh(library, event.items, event.gear_names)
        gold = (
            f"金幣 {event.gold}（跑腿費 {event.tax}，對方實收 {event.received}）"
            if event.gold
            else ""
        )
        body = "、".join(p for p in (what, gold) if p)
        return f"寄給{event.to_name}：{body}。"
    if isinstance(event, MailClaimedEvent):
        what = _counts_zh(library, event.items, event.gear_names)
        gold = f"金幣 {event.gold}" if event.gold else ""
        body = "、".join(p for p in (what, gold) if p) or "一封信"
        where = _CLAIMED_ZH.get(event.returned or "", f"{event.sender_name}的信")
        return f"領了{where}：{body}。"
    if isinstance(event, MailRefusedEvent):
        return f"把{event.sender_name}的信退回去了。"
    return None


def mail_event_lines(library: ContentLibrary, events: Iterable[WorldEvent]) -> tuple[str, ...]:
    return tuple(line for e in events if (line := mail_event_line(library, e)) is not None)
