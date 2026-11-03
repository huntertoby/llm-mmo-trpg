"""每日公告與首殺公告的排程（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.6）。

- :meth:`Announcer.tick` 由 Bot 的事件迴圈每分鐘左右呼叫一次，``now`` 是伺服器時鐘（UTC 秒），
  排程不進引擎（守則 1）。
- 今天（設定時區）已過 ``hour`` 點、且還沒貼過今天 → 貼今日公告。Bot 晚啟動也會補貼當天一次，不補
  前幾天（代決 5E3-7）。
- 首殺紀錄裡還沒貼過的（依日誌序號；以 ``<kind>:<target>`` 記貼過哪些，季末清掉世界後照樣能貼新的）
  → 每筆貼一則。
- 貼失敗（``send_channel`` 回 ``False``）就不記，下次 ``tick`` 重試。
- 狀態檔 ``<存檔資料夾>/bot/announce_state.json``（``trpg-announce/1``；只有 Bot 程序寫）。第一次
  建立時把現有首殺都當作已貼（不洗版）。
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.bot.config import AnnounceSettings, BotConfigError
from trpg.bot.gateway import DiscordGateway
from trpg.server.first_kills import FirstKill

__all__ = [
    "ANNOUNCE_FORMAT",
    "AnnounceState",
    "AnnouncementFeed",
    "Announcer",
    "daily_due",
    "kill_key",
    "read_state",
]

ANNOUNCE_FORMAT: Final = "trpg-announce/1"


class AnnouncementFeed(Protocol):
    """公告文字的來源（:class:`trpg.server.announce.AnnouncementSource`）。"""

    def daily_text(self, now: int) -> str | None: ...

    def first_kills(self) -> Sequence[FirstKill]: ...

    def first_kill_text(self, kill: FirstKill) -> str: ...


class AnnounceState(BaseModel):
    """Bot 貼過什麼。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["trpg-announce/1"] = ANNOUNCE_FORMAT
    last_daily: str | None = None
    """最後貼過今日公告的日期（設定時區，YYYY-MM-DD）。"""
    posted_kills: tuple[str, ...] = ()
    """貼過的首殺（``<kind>:<target>``，排序）。"""


def daily_due(now: int, settings: AnnounceSettings, last_daily: str | None) -> str | None:
    """``now`` 該貼的今日公告日期（已過 ``hour`` 點且還沒貼過）；不用貼＝``None``。"""
    local = dt.datetime.fromtimestamp(now, settings.tzinfo())
    if local.hour < settings.hour:
        return None
    today = local.date().isoformat()
    return None if today == last_daily else today


def kill_key(kill: FirstKill) -> str:
    return f"{kill.kind}:{kill.target}"


def _write(path: Path, state: AnnounceState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(state.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_state(path: Path) -> AnnounceState | None:
    """讀狀態檔（不存在＝``None``；不建立）。"""
    if not path.is_file():
        return None
    try:
        return AnnounceState.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise BotConfigError(f"公告狀態檔 {path} 壞了：{exc}") from exc


class Announcer:
    """把公告貼到頻道。"""

    def __init__(
        self,
        gateway: DiscordGateway,
        channel_id: str,
        feed: AnnouncementFeed,
        state_path: Path,
        *,
        settings: AnnounceSettings | None = None,
    ) -> None:
        self.gateway = gateway
        self.channel_id = channel_id
        self.feed = feed
        self.state_path = state_path
        self.settings = settings if settings is not None else AnnounceSettings()

    def state(self) -> AnnounceState:
        """目前的狀態；檔案不存在時建立（現有首殺當作已貼）。"""
        found = read_state(self.state_path)
        if found is not None:
            return found
        keys = sorted({kill_key(k) for k in self.feed.first_kills()})
        state = AnnounceState(posted_kills=tuple(keys))
        _write(self.state_path, state)
        return state

    def tick(self, now: int) -> list[str]:
        """貼該貼的公告；回傳這次貼出去的文字。"""
        state = self.state()
        posted: list[str] = []
        today = daily_due(now, self.settings, state.last_daily)
        if today is not None:
            text = self.feed.daily_text(now)
            if text is not None and self.gateway.send_channel(self.channel_id, text):
                posted.append(text)
                state = state.model_copy(update={"last_daily": today})
                _write(self.state_path, state)
        for kill in sorted(self.feed.first_kills(), key=lambda k: k.seq):
            if kill_key(kill) in state.posted_kills:
                continue
            text = self.feed.first_kill_text(kill)
            if not self.gateway.send_channel(self.channel_id, text):
                break  # 照順序：前一筆沒貼出去，後面的等下次
            posted.append(text)
            keys = tuple(sorted({*state.posted_kills, kill_key(kill)}))
            state = state.model_copy(update={"posted_kills": keys})
            _write(self.state_path, state)
        return posted
