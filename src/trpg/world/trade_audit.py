"""交易稽核報表（Phase 6T-1a；08 8.16「可疑的列進稽核報表，由使用者手動裁定」、#101）。

只讀世界的交易帳（:attr:`~trpg.world.state.WorldState.trades`），**只出報表，不擋交易、不自動
處理**。三種可疑：

- ``burst``（短時間大量）：同一個寄件帳號在 ``burst_seconds`` 內寄出 ``burst_count`` 封以上。
- ``big_value``（大額）：一封信的估值 ``big_value`` 以上。
- ``lopsided``（估值懸殊）：同一對帳號單向累計估值 ``pair_value`` 以上，而反方向不到它的
  ``lopsided_permille``。

門檻在 ``world/trade.yaml`` 的 ``audit``。純函式、確定性（依帳號、時間、信件 ID 排序）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from trpg.content.world_trade import TradeAudit
from trpg.world.state import TradeRecord

__all__ = ["AuditFlag", "audit_trades"]


class AuditFlag(BaseModel):
    """報表的一列。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["burst", "big_value", "lopsided"]
    accounts: tuple[str, ...]
    """相關的帳號（寄件方在前）。"""
    letters: tuple[str, ...]
    """相關的信件 ID（依 ID 排序）。"""
    value: int
    """相關信件的估值合計。"""
    text_zh: str


def _bursts(rules: TradeAudit, trades: Sequence[TradeRecord]) -> list[AuditFlag]:
    by_sender: dict[str, list[TradeRecord]] = {}
    for trade in trades:
        by_sender.setdefault(trade.sender_account, []).append(trade)
    flags: list[AuditFlag] = []
    for account in sorted(by_sender):
        rows = sorted(by_sender[account], key=lambda t: (t.at, t.id))
        for i, first in enumerate(rows):
            window = [t for t in rows[i:] if t.at < first.at + rules.burst_seconds]
            if len(window) >= rules.burst_count:
                minutes = rules.burst_seconds // 60
                flags.append(
                    AuditFlag(
                        kind="burst",
                        accounts=(account,),
                        letters=tuple(sorted(t.id for t in window)),
                        value=sum(t.value for t in window),
                        text_zh=f"帳號 {account} 在 {minutes} 分鐘內寄了 {len(window)} 封信",
                    )
                )
                break  # 每個帳號列第一段就好
    return flags


def _big(rules: TradeAudit, trades: Sequence[TradeRecord]) -> list[AuditFlag]:
    return [
        AuditFlag(
            kind="big_value",
            accounts=(t.sender_account, t.recipient_account),
            letters=(t.id,),
            value=t.value,
            text_zh=f"{t.sender_account} → {t.recipient_account}：一封估值 {t.value} 金幣",
        )
        for t in sorted(trades, key=lambda t: t.id)
        if t.value >= rules.big_value
    ]


def _lopsided(rules: TradeAudit, trades: Sequence[TradeRecord]) -> list[AuditFlag]:
    flows: dict[tuple[str, str], list[TradeRecord]] = {}
    for trade in trades:
        flows.setdefault((trade.sender_account, trade.recipient_account), []).append(trade)
    flags: list[AuditFlag] = []
    for (giver, taker), rows in sorted(flows.items()):
        given = sum(t.value for t in rows)
        back = sum(t.value for t in flows.get((taker, giver), []))
        if given >= rules.pair_value and back * 1000 < given * rules.lopsided_permille:
            flags.append(
                AuditFlag(
                    kind="lopsided",
                    accounts=(giver, taker),
                    letters=tuple(sorted(t.id for t in rows)),
                    value=given,
                    text_zh=f"{giver} → {taker} 累計估值 {given} 金幣，反方向只有 {back}",
                )
            )
    return flags


def audit_trades(rules: TradeAudit, trades: Sequence[TradeRecord]) -> tuple[AuditFlag, ...]:
    """交易帳的可疑項目（短時間大量、大額、估值懸殊，依序）。"""
    return (*_bursts(rules, trades), *_big(rules, trades), *_lopsided(rules, trades))
