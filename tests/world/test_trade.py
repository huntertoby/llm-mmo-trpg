"""交易共同前置與郵寄（Phase 6T-1a；08 8.15、8.16、#136）：來歷與綁定、門檻、寄信、領信、拒收、
過期自動退回（6T-1b）、交易帳與重播。"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.equipment import ItemDef
from trpg.content.item_gen import generate_item
from trpg.content.library import ContentLibrary
from trpg.shared.rng import Rng
from trpg.world.economy_actions import EquipAction
from trpg.world.errors import WorldActionError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, dumps_log_entry, loads_char, read_log
from trpg.world.state import CharacterState, GearOrigin, WorldState
from trpg.world.step import StepResult, world_step
from trpg.world.trade import (
    bound_zh,
    counterpart_of,
    gear_lock_zh,
    incoming_letters,
    origin_zh,
    send_quote,
    stamp_gear,
)
from trpg.world.trade_actions import (
    MailClaimAction,
    MailClaimedEvent,
    MailRefuseAction,
    MailSendAction,
    MailSentEvent,
)

MakeChar = Callable[..., CharacterState]
DAY = 86_400
ORE = "item_coarse_material"
PILL = "item_hp_potion_small"
DYE = "item_dye_indigo"


def _item(library: ContentLibrary, level: int = 3, seed: int = 7) -> ItemDef:
    return generate_item(library, Rng(seed), "body", "rare", level)


def _origin(owner: str = "alice", **updates: object) -> GearOrigin:
    data: dict[str, object] = {
        "owner": owner,
        "owner_name": "艾莉絲",
        "source": "drop",
        "source_zh": "竹林的戰利品",
        "at": NOON,
    }
    data.update(updates)
    return GearOrigin.model_validate(data)


@pytest.fixture
def pair(library: ContentLibrary, make_char: MakeChar) -> tuple[CharacterState, CharacterState]:
    """alice（3 級、霧渡鎮、有材料、藥水、一件沒穿過的身體裝備與金幣）與 bob（3 級、在野外）。"""
    body = _item(library)
    alice = make_char(
        "alice",
        level=3,
        gold=100,
        bag={ORE: 5, PILL: 2, DYE: 1},
        gear=(body,),
        gear_origin={body.id: _origin()},
    )
    bob = make_char("bob", level=3, location="bamboo_grove")
    return alice, bob


def _send(
    library: ContentLibrary,
    alice: CharacterState,
    bob: CharacterState,
    action: MailSendAction,
    *,
    world: WorldState | None = None,
    now: int = NOON,
    actor: str = "acct_a",
    other_actor: str = "acct_b",
) -> StepResult:
    return world_step(
        library,
        world or make_world(),
        alice,
        action,
        now,
        actor=actor,
        other=bob,
        other_actor=other_actor,
    )


# ---------------------------------------------------------------------------
# 來歷與綁定
# ---------------------------------------------------------------------------


def test_new_gear_gets_origin_and_wearing_binds(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    body = _item(library)
    char = make_char(gear=(body,))
    stamped = stamp_gear(library, char, char, EquipAction(item=body.id), events=(), now=NOON)
    origin = stamped.gear_origin[body.id]
    assert origin.owner == "alice" and origin.source == "other" and origin.tradable
    assert origin_zh(origin) == f"最初得自：{char.hero.name_zh}（霧渡鎮取得）"
    worn = world_step(library, make_world(), stamped, EquipAction(item=body.id), NOON).char
    assert worn.gear_origin[body.id].worn and bound_zh(worn.gear_origin[body.id]) == "穿過"
    # 換下來回到背包也還是綁定
    other = _item(library, seed=8)
    again = world_step(
        library,
        make_world(),
        worn.model_copy(update={"gear": (other,)}),
        EquipAction(item=other.id),
        NOON,
    ).char
    assert body in again.gear and gear_lock_zh(again, body.id) == "穿過的裝備不能交易"


def test_stamp_keeps_identity_and_prunes(library: ContentLibrary, make_char: MakeChar) -> None:
    body = _item(library)
    char = make_char(gear=(body,), gear_origin={body.id: _origin(), "item_gone": _origin()})
    pruned = stamp_gear(library, char, char, EquipAction(item=body.id), events=(), now=NOON)
    assert set(pruned.gear_origin) == {body.id}
    assert stamp_gear(library, pruned, pruned, EquipAction(item="x"), events=(), now=NOON) is pruned


def test_old_save_marks_gear_bound(library: ContentLibrary, make_char: MakeChar) -> None:
    """``trpg-char/8`` 照讀；舊存檔身上的裝備不知道穿過沒有，一律綁定。"""
    body = _item(library)
    data = json.loads(dumps_char(make_char(gear=(body,))))
    data["format"] = "trpg-char/8"
    del data["gear_origin"], data["mailbox"]
    old = loads_char(json.dumps(data, ensure_ascii=False))
    assert old.format == "trpg-char/15" and old.mailbox == ()
    assert old.gear_origin[body.id].bound == "legacy"
    assert gear_lock_zh(old, body.id) is not None


# ---------------------------------------------------------------------------
# 寄信
# ---------------------------------------------------------------------------


def test_send_moves_items_and_taxes_gold(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    alice, bob = pair
    body = alice.gear[0]
    action = MailSendAction(to="bob", items={ORE: 3}, gear=(body.id,), gold=55, note="給你")
    result = _send(library, alice, bob, action)
    sender, receiver = result.char, result.other
    assert receiver is not None
    assert sender.bag == {DYE: 1, ORE: 2, PILL: 2} and sender.gear == () and sender.gold == 45
    assert body.id not in sender.gear_origin
    (letter,) = receiver.mailbox
    assert letter.id == "mail_000001" and letter.items == {ORE: 3} and letter.gear == (body,)
    assert letter.gold == 49 and letter.tax == 6  # 10% 無條件進位
    assert letter.expires_at == NOON + 3 * DAY and letter.gear_origin[body.id].owner == "alice"
    assert receiver.bag == {} and receiver.gold == bob.gold  # 進城領了才進背包
    (record,) = result.world.trades
    assert (record.sender_account, record.recipient_account) == ("acct_a", "acct_b")
    assert record.gear == (body.id,) and record.items == {ORE: 3} and record.gold == 55
    assert record.value > 55 and record.status == "sent"
    sent = next(e for e in result.events if isinstance(e, MailSentEvent))
    assert (sent.tax, sent.received, sent.to_name) == (6, 49, bob.hero.name_zh)


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"alice": {"level": 2}}, "low_level"),
        ({"bob": {"level": 2}}, "recipient_low_level"),
        ({"alice": {"location": "bamboo_grove"}}, "not_here"),
        ({"bob": {"bag": {ORE: 20 * 30}}}, "bag_full"),
    ],
)
def test_send_thresholds(
    library: ContentLibrary,
    pair: tuple[CharacterState, CharacterState],
    change: dict[str, dict[str, object]],
    code: str,
) -> None:
    alice, bob = pair
    alice = alice.model_copy(update=change.get("alice", {}))
    bob = bob.model_copy(update=change.get("bob", {}))
    action = MailSendAction(to="bob", items={ORE: 1}, gold=10)
    quote = send_quote(
        library, make_world(), alice, bob, action, now=NOON, actor="a", other_actor="b"
    )
    assert code in {p.code for p in quote.problems}
    with pytest.raises(WorldActionError):
        _send(library, alice, bob, action)


def test_send_rules_on_attachments(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    alice, bob = pair
    world = make_world()

    def codes(action: MailSendAction, **kw: object) -> set[str]:
        quote = send_quote(
            library,
            world,
            kw.get("sender", alice),  # type: ignore[arg-type]
            kw.get("recipient", bob),  # type: ignore[arg-type]
            action,
            now=NOON,
            actor="a",
            other_actor=str(kw.get("other_actor", "b")),
        )
        return {p.code for p in quote.problems}

    assert codes(MailSendAction(to="bob")) == {"empty"}
    assert codes(MailSendAction(to="bob", items={DYE: 1})) == {"not_tradable"}  # 染料不能寄
    assert codes(MailSendAction(to="bob", items={ORE: 9})) == {"not_enough"}
    assert codes(MailSendAction(to="bob", gold=101)) == {"gold"}
    assert codes(MailSendAction(to="bob", gold=1)) == {"gold_small"}
    assert codes(MailSendAction(to="bob", gold=5), other_actor="a") == {"same_account"}
    assert codes(MailSendAction(to="alice", gold=5), recipient=alice) == {"self"}
    many = MailSendAction(to="bob", items={ORE: 1, PILL: 1}, gear=(alice.gear[0].id, "item_x"))
    assert "too_many" in codes(many) and "no_gear" in codes(many)
    worn = alice.model_copy(update={"gear_origin": {alice.gear[0].id: _origin(worn=True)}})
    assert codes(MailSendAction(to="bob", gear=(alice.gear[0].id,)), sender=worn) == {"bound"}
    unique = alice.model_copy(
        update={"gear_origin": {alice.gear[0].id: _origin(bound="first_kill")}}
    )
    assert codes(MailSendAction(to="bob", gear=(alice.gear[0].id,)), sender=unique) == {"bound"}
    strong = alice.model_copy(update={"gear": (_item(library, level=6),)})
    strong = strong.model_copy(update={"gear_origin": {strong.gear[0].id: _origin()}})
    quote = send_quote(
        library,
        world,
        strong,
        bob,
        MailSendAction(to="bob", gear=(strong.gear[0].id,)),
        now=NOON,
        actor="a",
        other_actor="b",
    )
    assert [p.line for p in quote.problems] == ["too_strong"]  # 6 級 > 3 + 2


def test_mailbox_limit(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    alice, bob = pair
    world = make_world()
    alice = alice.model_copy(update={"gold": 10_000})
    for n in range(20):
        result = _send(
            library, alice, bob, MailSendAction(to="bob", gold=10), world=world, now=NOON + n
        )
        assert result.other is not None
        world, alice, bob = result.world, result.char, result.other
    assert len(bob.mailbox) == 20
    with pytest.raises(WorldActionError, match="對方信箱滿了"):
        _send(library, alice, bob, MailSendAction(to="bob", gold=10), world=world, now=NOON + 30)
    # 過期的信不算在上限裡
    later = NOON + 3 * DAY + 30
    again = _send(library, alice, bob, MailSendAction(to="bob", gold=10), world=world, now=later)
    assert again.other is not None and len(again.other.mailbox) == 21


# ---------------------------------------------------------------------------
# 領信、拒收、過期取回
# ---------------------------------------------------------------------------


def _sent(library: ContentLibrary, pair: tuple[CharacterState, CharacterState]) -> StepResult:
    alice, bob = pair
    action = MailSendAction(to="bob", items={ORE: 2}, gear=(alice.gear[0].id,), gold=20)
    return _send(library, alice, bob, action)


def test_claim_in_town(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    sent = _sent(library, pair)
    bob = sent.other
    assert bob is not None
    with pytest.raises(WorldActionError, match="郵差"):
        world_step(library, sent.world, bob, MailClaimAction(letter="mail_000001"), NOON + 10)
    bob = bob.model_copy(update={"location": "mist_ferry"})
    full = bob.model_copy(update={"bag": {PILL: 300}})
    with pytest.raises(WorldActionError, match="背包放不下"):
        world_step(library, sent.world, full, MailClaimAction(letter="mail_000001"), NOON + 10)
    done = world_step(library, sent.world, bob, MailClaimAction(letter="mail_000001"), NOON + 10)
    got = done.char
    body = pair[0].gear[0]
    assert got.mailbox == () and got.bag == {ORE: 2} and got.gear == (body,) and got.gold == 18
    assert got.gear_origin[body.id].owner == "alice"  # 來歷跟著物品走，不重新命名
    assert got.gear[0].name_zh == body.name_zh
    assert done.world.trades[0].status == "claimed"
    event = next(e for e in done.events if isinstance(e, MailClaimedEvent))
    assert event.gold == 18 and event.returned is None


def test_claim_renames_clashing_gear(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    sent = _sent(library, pair)
    body = pair[0].gear[0]
    assert sent.other is not None
    bob = sent.other.model_copy(
        update={"location": "mist_ferry", "gear": (body,), "gear_origin": {body.id: _origin("bob")}}
    )
    got = world_step(library, sent.world, bob, MailClaimAction(letter="mail_000001"), NOON).char
    assert [g.id for g in got.gear] == [body.id, f"{body.id}_2"]
    assert got.gear_origin[f"{body.id}_2"].owner == "alice"


def test_refuse_returns_to_sender(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    sent = _sent(library, pair)
    assert sent.other is not None
    bob = sent.other.model_copy(update={"location": "mist_ferry"})
    refused = world_step(
        library, sent.world, bob, MailRefuseAction(letter="mail_000001"), NOON + 5, other=sent.char
    )
    assert refused.char.mailbox == ()
    alice = refused.other
    assert alice is not None
    (letter,) = alice.mailbox
    assert letter.returned == "refused" and letter.gold == 18  # 稅不退
    assert refused.world.trades[0].status == "refused"
    back = world_step(library, refused.world, alice, MailClaimAction(letter=letter.id), NOON + 9)
    assert back.char.gold == 80 + 18 and back.char.bag[ORE] == 5


def test_overdue_letter_returns_to_sender(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    sent = _sent(library, pair)
    alice, bob = sent.char, sent.other
    assert bob is not None
    late = NOON + 3 * DAY
    town_bob = bob.model_copy(update={"location": "mist_ferry"})
    with pytest.raises(WorldActionError, match="退回寄件人"):
        world_step(library, sent.world, town_bob, MailClaimAction(letter="mail_000001"), late)
    # 6T-1b（玩法 PM 決定 6T-1a 第 6 項）：過期的信自動退回寄件人，照退件用 mail_claim 領，
    # 同時從收件人身上拿掉；沒有另外的取回動作。
    claim = MailClaimAction(letter="mail_000001")
    assert counterpart_of(sent.world, alice, claim) == "bob"  # 資料還在收件人身上：同時改兩人
    assert counterpart_of(sent.world, town_bob, claim) is None  # 收件人領自己的：只改自己
    with pytest.raises(WorldActionError, match="過期了才會退回來"):
        world_step(library, sent.world, alice, claim, late - 1, other=bob)
    back = world_step(library, sent.world, alice, claim, late, other=bob)
    assert back.other is not None and back.other.mailbox == ()
    assert back.char.gold == 80 + 18 and back.char.gear == pair[0].gear  # 稅不退
    assert back.world.trades[0].status == "reclaimed"
    event = next(e for e in back.events if isinstance(e, MailClaimedEvent))
    assert event.returned == "expired"
    # 退回的信不算收件匣（不受 20 封上限）：收件人那邊看不到
    assert incoming_letters(bob, late) == ()


def test_pair_action_needs_other(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    with pytest.raises(WorldActionError, match="找不到收件的角色"):
        world_step(library, make_world(), pair[0], MailSendAction(to="bob", gold=10), NOON)


def test_season_warning(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    season = library.world_season
    assert season is not None
    world = make_world()
    end = NOON - NOON % DAY + season.days * DAY  # 約略：最後 3 天內
    late = _send(library, *pair, MailSendAction(to="bob", gold=10), world=world, now=end - DAY)
    early = _send(library, *pair, MailSendAction(to="bob", gold=10), world=world, now=NOON)
    late_event = next(e for e in late.events if isinstance(e, MailSentEvent))
    early_event = next(e for e in early.events if isinstance(e, MailSentEvent))
    assert late_event.season_warning and not early_event.season_warning


# ---------------------------------------------------------------------------
# 日誌與重播
# ---------------------------------------------------------------------------


def test_pair_entries_replay(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    alice, bob = pair
    world = make_world()
    send = MailSendAction(to="bob", items={ORE: 2}, gold=20)
    entries = (
        WorldLogEntry(
            seq=1,
            now=NOON,
            character_id="alice",
            action=send,
            actor="acct_a",
            counterpart="bob",
            counterpart_actor="acct_b",
        ),
        WorldLogEntry(
            seq=2,
            now=NOON + 5,
            character_id="bob",
            action=MailRefuseAction(letter="mail_000001"),
            actor="acct_b",
            counterpart="alice",
            counterpart_actor="acct_a",
        ),
    )
    town_bob = bob.model_copy(update={"location": "mist_ferry"})
    done = replay(library, world, {"alice": alice, "bob": town_bob}, entries)
    assert done.characters["alice"].mailbox[0].returned == "refused"
    assert done.characters["bob"].mailbox == ()
    assert done.world.trades[0].sender_account == "acct_a"
    text = dumps_log(entries)
    assert '"counterpart":"bob"' in text.splitlines()[1]
    assert read_log(text).entries == entries
    plain = WorldLogEntry(seq=3, now=NOON, character_id="alice", action=send)
    assert "counterpart" not in dumps_log_entry(plain)
    again = replay(library, world, {"alice": alice, "bob": town_bob}, entries)
    assert again == done


def test_expired_return_replays(
    library: ContentLibrary, pair: tuple[CharacterState, CharacterState]
) -> None:
    """6T-1b：寄件人領過期退回的信是一筆同時改兩人的日誌（``counterpart``＝收件人），重播一致。"""
    alice, bob = pair
    world = make_world()
    late = NOON + 3 * DAY
    entries = (
        WorldLogEntry(
            seq=1,
            now=NOON,
            character_id="alice",
            action=MailSendAction(to="bob", items={ORE: 2}, gold=20),
            actor="acct_a",
            counterpart="bob",
            counterpart_actor="acct_b",
        ),
        WorldLogEntry(
            seq=2,
            now=late,
            character_id="alice",
            action=MailClaimAction(letter="mail_000001"),
            actor="acct_a",
            counterpart="bob",
            counterpart_actor="acct_b",
        ),
    )
    done = replay(library, world, {"alice": alice, "bob": bob}, entries)
    assert done.characters["bob"].mailbox == ()
    assert done.characters["alice"].bag[ORE] == 5
    assert done.characters["alice"].gold == 100 - 20 + 18
    assert done.world.trades[0].status == "reclaimed"
    assert replay(library, world, {"alice": alice, "bob": bob}, entries) == done
