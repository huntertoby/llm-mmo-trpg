"""每日公告與首殺公告的排程（Phase 5E-3；計畫 31.6）。用假 Discord，不連網。"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest

from trpg.bot.announcer import Announcer, daily_due, read_state
from trpg.bot.config import AnnounceSettings, BotConfigError, load_announce_settings
from trpg.bot.fake import FakeDiscordGateway
from trpg.server.first_kills import FirstKill

TZ8 = dt.timezone(dt.timedelta(hours=8))
CHANNEL = "300"


def _at(day: int, hour: int, minute: int = 0) -> int:
    return int(dt.datetime(2026, 11, day, hour, minute, tzinfo=TZ8).timestamp())


def _kill(seq: int, target: str) -> FirstKill:
    return FirstKill(
        kind="elite",
        target=target,
        target_name_zh=target,
        character_id="c00000001",
        name="阿霧",
        region="cloud_ridge",
        location="x1",
        seq=seq,
        at=seq,
    )


@dataclass
class _Feed:
    kills: list[FirstKill] = field(default_factory=list)
    world: bool = True

    def daily_text(self, now: int) -> str | None:
        return f"daily {now}" if self.world else None

    def first_kills(self) -> Sequence[FirstKill]:
        return list(self.kills)

    def first_kill_text(self, kill: FirstKill) -> str:
        return f"kill {kill.target}"


def _announcer(tmp_path: Path, feed: _Feed) -> tuple[Announcer, FakeDiscordGateway]:
    gateway = FakeDiscordGateway()
    settings = AnnounceSettings(timezone="Etc/Nowhere", utc_offset_minutes=480, hour=6)
    return Announcer(gateway, CHANNEL, feed, tmp_path / "bot" / "state.json", settings=settings), (
        gateway
    )


def test_daily_posts_once_after_six_and_again_next_day(tmp_path: Path) -> None:
    announcer, gateway = _announcer(tmp_path, _Feed())
    assert announcer.tick(_at(3, 5, 59)) == []
    assert announcer.tick(_at(3, 6, 0)) == [f"daily {_at(3, 6, 0)}"]
    assert announcer.tick(_at(3, 6, 1)) == []
    assert announcer.tick(_at(3, 23, 59)) == []
    assert announcer.tick(_at(4, 5, 0)) == []
    assert len(announcer.tick(_at(4, 6, 0))) == 1
    assert len(gateway.posts_to(CHANNEL)) == 2
    state = read_state(announcer.state_path)
    assert state is not None and state.last_daily == "2026-11-04"


def test_late_start_posts_today_once(tmp_path: Path) -> None:
    announcer, gateway = _announcer(tmp_path, _Feed())
    assert len(announcer.tick(_at(5, 20, 0))) == 1  # 晚上才啟動：補貼當天
    assert announcer.tick(_at(5, 21, 0)) == []
    assert len(gateway.posts_to(CHANNEL)) == 1


def test_no_world_no_daily(tmp_path: Path) -> None:
    announcer, gateway = _announcer(tmp_path, _Feed(world=False))
    assert announcer.tick(_at(3, 7)) == []
    assert gateway.channel_posts == []


def test_first_kills_posted_once_and_not_flooded_on_first_start(tmp_path: Path) -> None:
    feed = _Feed(kills=[_kill(1, "old")])
    announcer, gateway = _announcer(tmp_path, feed)
    assert announcer.tick(_at(3, 5)) == []  # 第一次啟動：既有的首殺當作已貼
    feed.kills += [_kill(7, "wolf"), _kill(7, "hawk")]  # 同一個動作兩種精英
    assert announcer.tick(_at(3, 5, 1)) == ["kill wolf", "kill hawk"]
    assert announcer.tick(_at(3, 5, 2)) == []
    assert gateway.posts_to(CHANNEL) == ["kill wolf", "kill hawk"]


def test_same_elite_next_season_is_posted(tmp_path: Path) -> None:
    """季末重置（5F-5）後，新一季同一種精英的首殺照樣貼；第一季的舊鍵不變。"""
    feed = _Feed(kills=[_kill(1, "wolf")])
    announcer, _gateway = _announcer(tmp_path, feed)
    assert announcer.tick(_at(3, 5)) == []
    feed.kills.append(_kill(1, "wolf").model_copy(update={"season_id": "s2"}))
    assert announcer.tick(_at(3, 5, 1)) == ["kill wolf"]
    assert announcer.tick(_at(3, 5, 2)) == []
    state = read_state(tmp_path / "bot" / "state.json")
    assert state is not None and state.posted_kills == ("elite:wolf", "s2:elite:wolf")


def test_failed_post_is_retried(tmp_path: Path) -> None:
    feed = _Feed()
    announcer, gateway = _announcer(tmp_path, feed)
    announcer.tick(_at(3, 5))
    feed.kills.append(_kill(2, "wolf"))
    gateway.channel_down = True
    assert announcer.tick(_at(3, 6)) == []
    gateway.channel_down = False
    assert announcer.tick(_at(3, 6, 1)) == [f"daily {_at(3, 6, 1)}", "kill wolf"]


def test_broken_state_file(tmp_path: Path) -> None:
    announcer, _ = _announcer(tmp_path, _Feed())
    announcer.state_path.parent.mkdir(parents=True)
    announcer.state_path.write_text("{", encoding="utf-8")
    with pytest.raises(BotConfigError, match="壞了"):
        announcer.tick(_at(3, 7))


def test_timezone_fallback_and_settings(tmp_path: Path) -> None:
    fallback = AnnounceSettings(timezone="Etc/Nowhere", utc_offset_minutes=480)
    assert fallback.tzinfo().utcoffset(None) == dt.timedelta(hours=8)
    assert daily_due(_at(3, 6), fallback, None) == "2026-11-03"
    assert daily_due(_at(3, 5), fallback, None) is None
    assert load_announce_settings(env={"TRPG_BOT_CONFIG": ""}).hour == 6
    path = tmp_path / "bot.toml"
    path.write_text('[announce]\nhour = 7\ntimezone = "Asia/Taipei"\n', encoding="utf-8")
    assert load_announce_settings(path, env={}).hour == 7
    path.write_text("[announce]\nhour = 30\n", encoding="utf-8")
    with pytest.raises(BotConfigError, match="announce"):
        load_announce_settings(path, env={})


def test_example_config_has_announce_section() -> None:
    root = Path(__file__).resolve().parents[2]
    settings = load_announce_settings(root / "config" / "bot.example.toml", env={})
    assert settings == AnnounceSettings()


def _script() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "discord_bot.py"
    spec = importlib.util.spec_from_file_location("discord_bot_preview", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["discord_bot_preview"] = module
    spec.loader.exec_module(module)
    return module


def test_preview_prints_without_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRPG_SAVE_DIR", str(tmp_path))
    world = tmp_path / "world"
    world.mkdir()
    (world / "world.json").write_text(
        json.dumps(
            {"format": "trpg-world/1", "season_id": "s1", "season_seed": 1, "season_start": 0}
        ),
        encoding="utf-8",
    )
    out, err = io.StringIO(), io.StringIO()
    env = {"TRPG_BOT_CONFIG": ""}
    code = _script().main(
        ["preview", "--world-dir", str(world), "--now", str(_at(3, 6))], out, err, env
    )
    assert code == 0, err.getvalue()
    assert "今日公告" in out.getvalue() and "沒有還沒貼的首殺" in out.getvalue()
    assert not (tmp_path / "bot").exists()  # preview 不寫狀態檔
