"""主手掉落的武器大類（Phase 6T-1a；08 8.13 #135）與交易稽核報表（8.16、#101）。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_loot import MainHandMix
from trpg.content.world_trade import TradeAudit
from trpg.shared.rng import Rng
from trpg.world.actions import RestAction
from trpg.world.calendar import day_of
from trpg.world.season_board import record_activity, roll_season
from trpg.world.state import CharacterState, TradeRecord, WeaponMix
from trpg.world.step import world_step
from trpg.world.trade_audit import audit_trades
from trpg.world.weapon_mix import main_hand_class, other_class_odds, with_weapon_mix

MakeChar = Callable[..., CharacterState]
DAY = 86_400
RULES = MainHandMix()


def _share(kind: str, mix: WeaponMix | None, n: int = 4000) -> Counter[str]:
    return Counter(
        main_hand_class(RULES, mix, "melee", kind=kind, rng=Rng(seed))  # type: ignore[arg-type]
        for seed in range(n)
    )


def test_field_drop_is_half_same_class() -> None:
    counts = _share("field", WeaponMix(day=1, counts={"ranged": 30, "focus": 10, "melee": 99}))
    assert 1900 <= counts["melee"] <= 2100
    assert 1350 <= counts["ranged"] <= 1650 and 350 <= counts["focus"] <= 650  # 3：1


def test_elite_is_three_quarters_and_fixed_is_same() -> None:
    assert 2850 <= _share("elite", None)["melee"] <= 3150
    assert _share("fixed", None, 200) == Counter({"melee": 200})
    assert main_hand_class(None, None, "focus", kind="field", rng=Rng(1)) == "focus"


def test_thin_data_splits_evenly() -> None:
    thin = WeaponMix(day=1, counts={"ranged": 2})
    assert other_class_odds(RULES, thin, "melee") == {"focus": 1, "ranged": 1}
    assert other_class_odds(RULES, None, "focus") == {"melee": 1, "ranged": 1}
    counts = _share("field", thin)
    assert abs(counts["ranged"] - counts["focus"]) < 200


def test_mix_is_rolled_from_yesterday(library: ContentLibrary, make_char: MakeChar) -> None:
    today = day_of(library, NOON)
    world = make_world()
    world = record_activity(world, "acct_a", today, ("alice", "melee"))
    world = record_activity(world, "acct_a", today, ("alice2", "focus"))
    world = record_activity(world, "acct_b", today, ("bob", "melee"))
    assert world.activity[-1].characters == {"alice": "melee", "alice2": "focus", "bob": "melee"}
    assert world.activity[-1].actors == ("acct_a", "acct_b")
    rolled = with_weapon_mix(world, today + 1)
    assert rolled.weapon_mix == WeaponMix(day=today + 1, counts={"focus": 1, "melee": 2})
    assert with_weapon_mix(rolled, today + 1) is rolled
    # 換日時算一次（world_step 的 roll_season），同樣的日誌重播得到同樣的比例
    char = make_char(location="mist_ferry")
    first = world_step(library, make_world(), char, RestAction(), NOON).world
    assert first.activity[-1].characters == {"alice": "focus"}  # 測試主角拿法器
    second = world_step(library, first, char, RestAction(), NOON + DAY).world
    assert second.weapon_mix == WeaponMix(day=today + 1, counts={"focus": 1})
    assert roll_season(library, first, NOON + DAY)[0].weapon_mix == second.weapon_mix


def _trade(n: int, at: int, sender: str, recipient: str, value: int) -> TradeRecord:
    return TradeRecord(
        id=f"mail_{n:06d}",
        at=at,
        sender="c1",
        sender_account=sender,
        recipient="c2",
        recipient_account=recipient,
        gold=value,
        value=value,
        expires_at=at + 3 * DAY,
    )


def test_audit_report() -> None:
    rules = TradeAudit(burst_count=3, burst_seconds=600, big_value=500, pair_value=400)
    trades = [
        _trade(1, NOON, "a", "b", 100),
        _trade(2, NOON + 60, "a", "b", 150),
        _trade(3, NOON + 120, "a", "b", 600),
        _trade(4, NOON + 9000, "b", "a", 10),
        _trade(5, NOON + 9000, "c", "d", 50),
    ]
    flags = audit_trades(rules, trades)
    assert [(f.kind, f.accounts) for f in flags] == [
        ("burst", ("a",)),
        ("big_value", ("a", "b")),
        ("lopsided", ("a", "b")),
    ]
    assert flags[0].letters == ("mail_000001", "mail_000002", "mail_000003")
    assert flags[2].value == 850
    assert audit_trades(rules, trades[3:]) == ()


def _dropped_classes(
    library: ContentLibrary, char: CharacterState, *, fixed: bool, n: int = 300
) -> Counter[str]:
    from trpg.world.loot import _roll_gear  # noqa: PLC0415 - 只測主手大類這一段

    rules = library.world_loot
    assert rules is not None
    found: Counter[str] = Counter()
    for seed in range(n):
        for item in _roll_gear(
            library, rules, char, Rng(seed), region="cloud_ridge", level=3, elite=True, fixed=fixed
        ):
            if item.weapon is not None:
                found[library.weapons[item.weapon].weapon_class] += 1
    return found


def test_loot_uses_the_mix(library: ContentLibrary, make_char: MakeChar) -> None:
    """精英掉的主手約 1／4 是別大類；區域 Boss、懸賞（``fixed``）一律同大類。"""
    char = make_char()
    mine = library.weapons[char.hero.weapon].weapon_class
    mixed = _dropped_classes(library, char, fixed=False)
    assert mixed[mine] > 0 and sum(mixed.values()) > mixed[mine]
    fixed = _dropped_classes(library, char, fixed=True)
    assert set(fixed) == {mine}
