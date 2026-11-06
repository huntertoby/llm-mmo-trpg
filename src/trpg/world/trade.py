"""交易共同前置與郵寄（Phase 6T-1a；08 8.15、8.16、#136）。

**共同前置**

- **來歷與綁定**（:func:`stamp_gear`，每個世界動作之後）：新拿到的裝備記下「最初得自：〈原主〉
  （〈來源〉）」（:class:`~trpg.world.state.GearOrigin`）；穿上就綁定（``worn``）；獨特裝備（隱藏配方、
  獨特詞條）、首殺物品（這一場有精英首殺時掉的）取得就綁定；不在身上的紀錄刪掉。交易時紀錄原封不動
  跟著物品走（名稱、描述本來就存在物品上），不重新命名、不呼叫 LLM。
- **能交易**：背包裡的材料、消耗品（``trade.tradable_kinds``）、金幣、沒穿過也沒綁定的裝備。
  任務幣、靈感點、經驗、好感度、技能不在附件裡，本來就寄不了。
- **門檻**（:func:`send_quote`）：雙方都要 3 級起；收到的裝備物品等級不能高於收件人等級 ＋2；同一個
  帳號的角色之間不能互寄；收件人背包放得下、信箱沒滿。全部通過才寫，兩邊一起成功或一起不變
  （純函式：不合法拋 :class:`~trpg.world.errors.WorldActionError`，傳入的狀態不變）。
- **交易帳**（:attr:`~trpg.world.state.WorldState.trades`）：每封信一筆，記雙方帳號、物品 ID、估值
  （材料與消耗品照買價、裝備照回收價、金幣照面額）；稽核報表在 :mod:`trpg.world.trade_audit`。

**郵寄**（只在城鎮的郵差處；三區各一位，``world/trade.yaml``）

- **寄信**（``mail_send``，同時改寄件人與收件人）：附件從寄件人身上拿掉、信放進收件人的信箱；金幣收
  10% 稅（無條件進位），對方實收＝扣稅後。
- **領信**（``mail_claim``）：收件人進城在郵差處領，背包放不下就拒絕；被拒收、過期退回的信也這樣領。
- **拒收**（``mail_refuse``，同時改兩人）：信回到寄件人的信箱（``returned: refused``）。
- **過期**（6T-1b 改，玩法 PM 決定 6T-1a 第 6 項）：寄出 3 天（現實）沒領，**自動退回寄件人**——
  收件人看不到也領不了，寄件人的「退件・過期」分頁直接出現，和被拒收一樣用 ``mail_claim`` 領（不受
  信箱上限，沒有另外的取回動作）。那封信的資料還記在收件人的信箱，寄件人領的那一筆同時改兩人、從
  收件人身上拿掉。金幣的稅都不退。
- **季末**：角色整個清掉（季末重置政策表，數值類），沒領的信跟著清掉；季末前 3 天寄件時提示。
- 時間一律用日誌的 ``now``（守則 1），不讀系統時間。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary
from trpg.content.world_trade import MailLineKind, Postman, TradeRules
from trpg.world.actions import FightAction, InsightGainedEvent, WorldAction, WorldEvent
from trpg.world.calendar import day_of, day_start
from trpg.world.crafting_actions import CraftAction, GearCraftedEvent
from trpg.world.economy import gear_price
from trpg.world.economy_actions import LootChooseAction, LootGainedEvent
from trpg.world.errors import WorldActionError
from trpg.world.inventory import add_items, remove_gear, remove_items, slots_over
from trpg.world.state import (
    CharacterState,
    GearMod,
    GearOrigin,
    MailLetter,
    TradeRecord,
    WorldState,
)
from trpg.world.trade_actions import (
    MailClaimAction,
    MailClaimedEvent,
    MailRefuseAction,
    MailRefusedEvent,
    MailSendAction,
    MailSentEvent,
)

__all__ = [
    "PAIR_HANDLERS",
    "MailQuote",
    "PairResult",
    "TradeProblem",
    "bound_zh",
    "counterpart_of",
    "gear_lock_zh",
    "incoming_letters",
    "origin_zh",
    "place_name",
    "postman_here",
    "season_warning",
    "send_quote",
    "stamp_gear",
    "trade_rules",
    "trade_value",
]

_BOUND_ZH: Final[Mapping[str, str]] = {"unique": "獨特", "first_kill": "首殺", "legacy": "穿過"}


# ---------------------------------------------------------------------------
# 內容與查詢
# ---------------------------------------------------------------------------


def trade_rules(library: ContentLibrary) -> TradeRules | None:
    """交易規則；內容庫沒有 ``world/trade.yaml`` 時為 ``None``（交易關閉）。"""
    return library.world_trade


def _rules(library: ContentLibrary) -> TradeRules:
    rules = trade_rules(library)
    if rules is None:
        raise WorldActionError("這個世界還沒有開放交易（沒有 world/trade.yaml）")
    return rules


def postman_here(library: ContentLibrary, char: CharacterState) -> Postman | None:
    """角色所在地點的郵差（城鎮裡、站在郵差的地點）；沒有為 ``None``。"""
    rules = trade_rules(library)
    postman = None if rules is None else rules.mail.postman_of(char.region)
    if postman is None or postman.card.location != char.location:
        return None
    return postman


def _require_postman(library: ContentLibrary, char: CharacterState) -> Postman:
    if char.pending_encounter is not None:
        raise WorldActionError("還有沒處理的遭遇，不能寄信或領信")
    postman = postman_here(library, char)
    if postman is None:
        raise WorldActionError("信只能在城鎮的郵差這裡寄、這裡領")
    return postman


def _place_zh(library: ContentLibrary, region: str, location: str) -> str:
    world_map = library.location_map(region)
    found = None if world_map is None else world_map.location_by_id().get(location)
    return location if found is None else found.name_zh


def season_warning(library: ContentLibrary, world: WorldState, now: int) -> bool:
    """季末前 ``season_warning_days`` 天內（季末沒領的信會清掉）；沒有賽季資料時為假。"""
    rules = trade_rules(library)
    season = library.world_season
    if rules is None or season is None:
        return False
    end = day_start(library, day_of(library, world.season_start) + season.days)
    return end - rules.mail.season_warning_seconds <= now < end


# ---------------------------------------------------------------------------
# 來歷與綁定
# ---------------------------------------------------------------------------


def origin_zh(origin: GearOrigin) -> str:
    """卡片的「最初得自：〈原主〉（〈來源〉）」。"""
    return f"最初得自：{origin.owner_name}（{origin.source_zh}）"


def bound_zh(origin: GearOrigin | None) -> str | None:
    """綁定的標籤（「穿過」「獨特」「首殺」）；沒綁定為 ``None``。沒有紀錄的裝備當作綁定
    （穿過）。"""
    if origin is None:
        return "穿過"
    if origin.worn:
        return "穿過"
    return None if origin.bound is None else _BOUND_ZH[origin.bound]


def gear_lock_zh(char: CharacterState, item_id: str) -> str | None:
    """背包裡這件裝備不能寄的原因（綁定）；能寄為 ``None``。"""
    label = bound_zh(char.gear_origin.get(item_id))
    return None if label is None else f"{label}的裝備不能交易"


def _held_gear(char: CharacterState) -> list[ItemDef]:
    pending = () if char.pending_loot is None else char.pending_loot.gear
    return [*char.gear, *char.equipment.values(), *pending]


def _is_unique(library: ContentLibrary, item: ItemDef, events: Sequence[WorldEvent]) -> bool:
    gen = library.item_gen
    if gen is not None and any(r.affix in gen.unique_affixes for r in item.affixes):
        return True
    return any(
        isinstance(e, GearCraftedEvent) and e.item == item.id and e.hidden is not None
        for e in events
    )


def _first_kill_ids(events: Sequence[WorldEvent]) -> frozenset[str]:
    """這一步有精英首殺（靈感點 ``elite:``）時，掉落進背包的裝備 ID（首殺物品）。"""
    if not any(isinstance(e, InsightGainedEvent) and e.source.startswith("elite:") for e in events):
        return frozenset()
    return frozenset(g for e in events if isinstance(e, LootGainedEvent) for g in e.gear)


def _source(
    library: ContentLibrary, before: CharacterState, action: WorldAction
) -> tuple[str, str]:
    place = _place_zh(library, before.region, before.location)
    if isinstance(action, FightAction | LootChooseAction):
        return "drop", f"{place}的戰利品"
    if isinstance(action, CraftAction):
        return "craft", f"{place}打造"
    return "other", f"{place}取得"


def stamp_gear(
    library: ContentLibrary,
    before: CharacterState,
    char: CharacterState,
    action: WorldAction,
    *,
    events: Sequence[WorldEvent],
    now: int,
) -> CharacterState:
    """動作之後整理裝備的來歷（見模組說明）；沒有變化時回傳同一個物件。"""
    held = {g.id: g for g in _held_gear(char)}
    worn = {g.id for g in char.equipment.values()}
    rows = {k: v for k, v in char.gear_origin.items() if k in held}
    first_kill = _first_kill_ids(events)
    for item_id in sorted(held):
        origin = rows.get(item_id)
        if origin is None:
            kind, text = _source(library, before, action)
            bound = None
            if _is_unique(library, held[item_id], events):
                bound = "unique"
            elif item_id in first_kill:
                bound = "first_kill"
            origin = GearOrigin(
                owner=char.character_id,
                owner_name=char.hero.name_zh,
                source=kind,  # type: ignore[arg-type]
                source_zh=text,
                at=now,
                bound=bound,  # type: ignore[arg-type]
            )
        if item_id in worn and not origin.worn:
            origin = origin.model_copy(update={"worn": True})
        rows[item_id] = origin
    if rows == char.gear_origin:
        return char
    return char.model_copy(update={"gear_origin": rows})


# ---------------------------------------------------------------------------
# 寄信前的檢查與估價
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeProblem:
    """寄不出去的一個原因；``line`` 是郵差要說的那句（七種情境之一），沒有對應的為 ``None``。"""

    code: str
    text_zh: str
    line: MailLineKind | None = None


@dataclass(frozen=True)
class MailQuote:
    """寄件前的檢查結果（API 即時顯示：跑腿費、對方實收、估值與全部問題）。"""

    gold: int
    tax: int
    received: int
    value: int
    problems: tuple[TradeProblem, ...] = ()
    season_warning: bool = False
    gear: tuple[ItemDef, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.problems


def trade_value(
    library: ContentLibrary, items: Mapping[str, int], gear: Iterable[ItemDef], gold: int
) -> int:
    """估值（金幣）：材料與消耗品照買價、裝備照回收價（不收的算 0）、金幣照面額。"""
    total = gold
    for item, count in items.items():
        found = library.world_economy.items.get(item)
        total += 0 if found is None else found.price * count
    for piece in gear:
        total += gear_price(library, piece) or 0
    return total


def incoming_letters(char: CharacterState, now: int) -> tuple[MailLetter, ...]:
    """收件人看得到、能領的信（寄給自己、還沒過期的）。"""
    return tuple(m for m in char.mailbox if m.returned is None and not m.overdue(now))


def _same_account(actor: str | None, other_actor: str | None) -> bool:
    return actor is not None and other_actor is not None and actor == other_actor


def _party_problems(
    rules: TradeRules,
    sender: CharacterState,
    recipient: CharacterState | None,
    *,
    actor: str | None,
    other_actor: str | None,
) -> list[TradeProblem]:
    common = rules.trade
    problems: list[TradeProblem] = []
    if sender.level < common.min_level:
        text = f"角色 {common.min_level} 級起才能交易"
        problems.append(TradeProblem("low_level", text, "low_level"))
    if recipient is None:
        return [*problems, TradeProblem("no_recipient", "找不到收件的角色")]
    if recipient.character_id == sender.character_id:
        problems.append(TradeProblem("self", "不能寄給自己", "same_account"))
    elif _same_account(actor, other_actor):
        text = "同一個帳號的角色之間不能互寄"
        problems.append(TradeProblem("same_account", text, "same_account"))
    if recipient.level < common.min_level:
        text = f"對方還不到 {common.min_level} 級，不能收信"
        problems.append(TradeProblem("recipient_low_level", text, "too_strong"))
    return problems


def _attachment_problems(
    library: ContentLibrary,
    rules: TradeRules,
    sender: CharacterState,
    action: MailSendAction,
) -> tuple[list[TradeProblem], list[ItemDef]]:
    problems: list[TradeProblem] = []
    count = len(action.items) + len(action.gear)
    if count == 0 and action.gold == 0:
        problems.append(TradeProblem("empty", "要附上東西或金幣"))
    if count > rules.mail.max_attachments:
        text = f"附件最多 {rules.mail.max_attachments} 格（要寄 {count} 格）"
        problems.append(TradeProblem("too_many", text))
    if len(action.note) > rules.mail.note_max:
        problems.append(TradeProblem("note", f"留言最多 {rules.mail.note_max} 字"))
    for item, n in sorted(action.items.items()):
        found = library.world_economy.items.get(item)
        name = item if found is None else found.name_zh
        if n < 1:
            problems.append(TradeProblem("count", f"{name}的個數至少 1"))
        elif found is None or found.kind not in rules.trade.tradable_kinds:
            problems.append(TradeProblem("not_tradable", f"{name}不能交易"))
        elif sender.bag.get(item, 0) < n:
            have = sender.bag.get(item, 0)
            problems.append(TradeProblem("not_enough", f"背包裡的{name}只有 {have} 個"))
    gear: list[ItemDef] = []
    if len(set(action.gear)) != len(action.gear):
        problems.append(TradeProblem("duplicate", "同一件裝備只能寄一次"))
    for gear_id in dict.fromkeys(action.gear):
        piece = next((g for g in sender.gear if g.id == gear_id), None)
        if piece is None:
            problems.append(TradeProblem("no_gear", "背包裡沒有這件裝備（穿戴中的不能寄）"))
            continue
        lock = gear_lock_zh(sender, gear_id)
        if lock is not None:
            problems.append(TradeProblem("bound", f"{piece.name_zh}：{lock}"))
        gear.append(piece)
    if action.gold > sender.gold:
        problems.append(TradeProblem("gold", f"金幣不夠（有 {sender.gold}）"))
    return problems, gear


def _recipient_problems(
    library: ContentLibrary,
    rules: TradeRules,
    recipient: CharacterState,
    action: MailSendAction,
    *,
    gear: Sequence[ItemDef],
    now: int,
) -> list[TradeProblem]:
    problems: list[TradeProblem] = []
    cap = recipient.level + rules.trade.item_level_margin
    for piece in gear:
        if (piece.item_level or 1) > cap:
            text = f"{piece.name_zh}的物品等級高於對方等級 +{rules.trade.item_level_margin}"
            problems.append(TradeProblem("too_strong", text, "too_strong"))
    if len(incoming_letters(recipient, now)) >= rules.mail.mailbox_max:
        problems.append(TradeProblem("mailbox_full", "對方信箱滿了"))
    bag = add_items(recipient.bag, {k: v for k, v in action.items.items() if v > 0})
    short = slots_over(library, bag, len(recipient.gear) + len(gear))
    if short > 0:
        problems.append(TradeProblem("bag_full", f"對方背包放不下（還差 {short} 格）"))
    return problems


def send_quote(
    library: ContentLibrary,
    world: WorldState,
    sender: CharacterState,
    recipient: CharacterState | None,
    action: MailSendAction,
    *,
    now: int,
    actor: str | None,
    other_actor: str | None,
) -> MailQuote:
    """寄件前的全部檢查與估價（不改狀態；API 的預覽與 ``mail_send`` 共用）。"""
    rules = _rules(library)
    problems: list[TradeProblem] = []
    if sender.pending_encounter is not None or postman_here(library, sender) is None:
        problems.append(TradeProblem("not_here", "信只能在城鎮的郵差這裡寄"))
    problems += _party_problems(rules, sender, recipient, actor=actor, other_actor=other_actor)
    attach, gear = _attachment_problems(library, rules, sender, action)
    problems += attach
    if recipient is not None:
        problems += _recipient_problems(library, rules, recipient, action, gear=gear, now=now)
    tax = rules.trade.gold_tax(action.gold)
    if action.gold > 0 and action.gold - tax < 1:
        problems.append(TradeProblem("gold_small", "金幣太少，扣完跑腿費就沒了"))
    items = {k: v for k, v in action.items.items() if v > 0}
    value = trade_value(library, items, gear, action.gold)
    return MailQuote(
        gold=action.gold,
        tax=tax,
        received=max(0, action.gold - tax),
        value=value,
        problems=tuple(problems),
        season_warning=season_warning(library, world, now),
        gear=tuple(gear),
    )


# ---------------------------------------------------------------------------
# 寄信、領信、拒收、取回
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairResult:
    world: WorldState
    char: CharacterState
    other: CharacterState | None
    """改過的另一個角色；只改自己時為 ``None``。"""
    events: tuple[WorldEvent, ...]


def _with_letter(char: CharacterState, letter: MailLetter) -> CharacterState:
    box = sorted((*char.mailbox, letter), key=lambda m: m.id)
    return char.model_copy(update={"mailbox": tuple(box)})


def _without_letter(char: CharacterState, letter_id: str) -> CharacterState:
    box = tuple(m for m in char.mailbox if m.id != letter_id)
    return char.model_copy(update={"mailbox": box})


def _set_status(world: WorldState, letter_id: str, status: str, now: int) -> WorldState:
    rows = tuple(
        t.model_copy(update={"status": status, "closed_at": now}) if t.id == letter_id else t
        for t in world.trades
    )
    return world.model_copy(update={"trades": rows})


def _mail_send(  # noqa: PLR0917 - 和 PairHandler 同簽名（分派表的一格）
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    other: CharacterState | None,
    action: MailSendAction,
    now: int,
    *,
    actor: str,
    other_actor: str,
) -> PairResult:
    if other is None:
        raise WorldActionError("找不到收件的角色")
    quote = send_quote(
        library, world, char, other, action, now=now, actor=actor, other_actor=other_actor
    )
    if not quote.ok:
        raise WorldActionError("；".join(p.text_zh for p in quote.problems))
    rules = _rules(library)
    items = dict(sorted(action.items.items()))
    ids = [g.id for g in quote.gear]
    letter = MailLetter(
        id=f"mail_{len(world.trades) + 1:06d}",
        sender=char.character_id,
        sender_name=char.hero.name_zh,
        recipient=other.character_id,
        recipient_name=other.hero.name_zh,
        from_region=char.region,
        from_location=char.location,
        sent_at=now,
        expires_at=now + rules.mail.return_seconds,
        note=action.note,
        items=items,
        gear=quote.gear,
        gear_mods={k: v for k, v in char.gear_mods.items() if k in ids},
        gear_origin={k: v for k, v in char.gear_origin.items() if k in ids},
        gold=quote.received,
        tax=quote.tax,
    )
    sender = remove_gear(char, ids)
    sender = sender.model_copy(
        update={
            "bag": remove_items(char.bag, items),
            "gold": char.gold - action.gold,
            "gear_origin": {k: v for k, v in char.gear_origin.items() if k not in ids},
        }
    )
    record = TradeRecord(
        id=letter.id,
        at=now,
        sender=char.character_id,
        sender_account=actor,
        recipient=other.character_id,
        recipient_account=other_actor,
        items=items,
        gear=tuple(ids),
        gold=action.gold,
        tax=quote.tax,
        value=quote.value,
        expires_at=letter.expires_at,
    )
    world = world.model_copy(update={"trades": (*world.trades, record)})
    event = MailSentEvent(
        letter=letter.id,
        to=other.character_id,
        to_name=other.hero.name_zh,
        items=items,
        gear_names=tuple(g.name_zh for g in quote.gear),
        gold=action.gold,
        tax=quote.tax,
        received=quote.received,
        expires_at=letter.expires_at,
        season_warning=quote.season_warning,
    )
    return PairResult(world, sender, _with_letter(other, letter), (event,))


def _unique_id(item_id: str, taken: set[str]) -> str:
    if item_id not in taken:
        return item_id
    n = 2
    while f"{item_id}_{n}" in taken:
        n += 1
    return f"{item_id}_{n}"


def _receive(
    library: ContentLibrary, char: CharacterState, letter: MailLetter
) -> tuple[CharacterState, tuple[str, ...]]:
    """信的附件進背包（放不下就拒絕）；撞到身上已有的裝備 ID 時加序號（改動紀錄與來歷跟著改名）。"""
    bag = add_items(char.bag, letter.items)
    short = slots_over(library, bag, len(char.gear) + len(letter.gear))
    if short > 0:
        raise WorldActionError(f"背包放不下（還差 {short} 格），先整理背包再來領")
    taken = {g.id for g in _held_gear(char)}
    gear: list[ItemDef] = []
    mods: dict[str, GearMod] = dict(char.gear_mods)
    origins: dict[str, GearOrigin] = dict(char.gear_origin)
    for piece in letter.gear:
        new_id = _unique_id(piece.id, taken)
        taken.add(new_id)
        gear.append(piece if new_id == piece.id else piece.model_copy(update={"id": new_id}))
        if piece.id in letter.gear_mods:
            mods[new_id] = letter.gear_mods[piece.id]
        if piece.id in letter.gear_origin:
            origins[new_id] = letter.gear_origin[piece.id]
    char = char.model_copy(
        update={
            "bag": bag,
            "gear": (*char.gear, *gear),
            "gold": char.gold + letter.gold,
            "gear_mods": mods,
            "gear_origin": origins,
        }
    )
    return char, tuple(g.id for g in gear)


def _claim_own(
    library: ContentLibrary, world: WorldState, char: CharacterState, letter: MailLetter, now: int
) -> tuple[WorldState, CharacterState, MailClaimedEvent]:
    """領自己信箱裡的信：寄給自己還沒過期的、或被拒收退回來的。"""
    if letter.overdue(now):
        raise WorldActionError("這封信放太久，已經退回寄件人了")
    char, gear_ids = _receive(library, _without_letter(char, letter.id), letter)
    if letter.returned is None:
        world = _set_status(world, letter.id, "claimed", now)
    event = MailClaimedEvent(
        letter=letter.id,
        sender_name=letter.sender_name,
        items=dict(letter.items),
        gear=gear_ids,
        gear_names=tuple(g.name_zh for g in letter.gear),
        gold=letter.gold,
        returned=letter.returned,
    )
    return world, char, event


def _mail_claim(  # noqa: PLR0917 - 和 PairHandler 同簽名（分派表的一格）
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    other: CharacterState | None,
    action: MailClaimAction,
    now: int,
    *,
    actor: str,
    other_actor: str,
) -> PairResult:
    """``mail_claim``：領自己信箱裡的信（只改自己，``other`` 是 ``None``）；或領 **過期自動退回**
    的信（6T-1b，玩法 PM 決定 6T-1a 第 6 項：同拒收，退回寄件人、不受信箱上限、不用另外取回）——
    那封信還記在收件人的信箱（收件人看不到），領的時候同時從收件人身上拿掉（``other``＝收件人）。"""
    del actor, other_actor
    _require_postman(library, char)
    own = next((m for m in char.mailbox if m.id == action.letter), None)
    if own is not None:
        world, char, claimed = _claim_own(library, world, char, own, now)
        return PairResult(world, char, None, (claimed,))
    held = () if other is None else other.mailbox
    letter = next((m for m in held if m.id == action.letter), None)
    if other is None or letter is None or letter.sender != char.character_id:
        raise WorldActionError("信箱裡沒有這封信")
    if not letter.overdue(now):
        raise WorldActionError("對方還可以領，過期了才會退回來")
    char, gear_ids = _receive(library, char, letter)
    world = _set_status(world, letter.id, "reclaimed", now)
    event = MailClaimedEvent(
        letter=letter.id,
        sender_name=letter.sender_name,
        items=dict(letter.items),
        gear=gear_ids,
        gear_names=tuple(g.name_zh for g in letter.gear),
        gold=letter.gold,
        returned="expired",
    )
    return PairResult(world, char, _without_letter(other, letter.id), (event,))


def _mail_refuse(  # noqa: PLR0917 - 和 PairHandler 同簽名（分派表的一格）
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    other: CharacterState | None,
    action: MailRefuseAction,
    now: int,
    *,
    actor: str,
    other_actor: str,
) -> PairResult:
    del actor, other_actor
    _require_postman(library, char)
    letter = next((m for m in incoming_letters(char, now) if m.id == action.letter), None)
    if letter is None:
        raise WorldActionError("信箱裡沒有這封信（過期的已經退回寄件人）")
    if other is None or letter.sender != other.character_id:
        raise WorldActionError("寄件人不對")
    returned = letter.model_copy(update={"returned": "refused"})
    world = _set_status(world, letter.id, "refused", now)
    event = MailRefusedEvent(letter=letter.id, sender_name=letter.sender_name)
    return PairResult(
        world, _without_letter(char, letter.id), _with_letter(other, returned), (event,)
    )


type PairHandler = Callable[..., PairResult]
"""``(library, world, char, other, action, now, *, actor, other_actor) → PairResult``；``other``
可為 ``None``（領自己信箱裡的信只改自己，6T-1b），需要另一個角色的處理自己拒絕。"""

PAIR_HANDLERS: Final[dict[type, PairHandler]] = {
    MailSendAction: _mail_send,
    MailClaimAction: _mail_claim,
    MailRefuseAction: _mail_refuse,
}
"""可能同時改兩個角色的動作 → 處理（和 :data:`~trpg.world.trade_actions.PAIR_ACTIONS` 一致，
測試檢查）。"""


def counterpart_of(world: WorldState, char: CharacterState, action: WorldAction) -> str | None:
    """這個動作同時要改的另一個角色（寄信的收件人、拒收的寄件人、領過期退回的信時的收件人）；只改
    自己的動作為 ``None``。找不到那封信時也是 ``None``（動作本身會拒絕）。"""
    if isinstance(action, MailSendAction):
        return action.to
    if isinstance(action, MailRefuseAction):
        letter = next((m for m in char.mailbox if m.id == action.letter), None)
        return None if letter is None else letter.sender
    if isinstance(action, MailClaimAction):
        if any(m.id == action.letter for m in char.mailbox):
            return None  # 自己信箱裡的信：只改自己
        record = world.trade(action.letter)
        if record is None or record.sender != char.character_id or record.status != "sent":
            return None
        return record.recipient  # 過期自動退回的信還記在收件人身上（6T-1b）
    return None


def place_name(library: ContentLibrary, region: str, location: str) -> str:
    """地點的中文名（寄自哪裡）。"""
    return _place_zh(library, region, location)
