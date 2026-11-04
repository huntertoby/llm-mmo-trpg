"""6F-1：前 10 分鐘的文字修正（靈感點提示不露出原始 ID、提到閃現）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.world_growth_view import growth_event_line
from trpg.world.actions import InsightGainedEvent


def _line(source: str) -> str:
    line = growth_event_line(library(), InsightGainedEvent(source=source, amount=1, insight=1), {})
    assert line is not None
    return line


def test_quest_insight_uses_the_quest_name_and_mentions_flash() -> None:
    line = _line("quest:starter_ferry")
    assert line.startswith("任務「霧渡新手路」：靈感 ＋1（共 1 點）")
    assert "閃現" in line and "（G）" in line
    assert "starter_ferry" not in line and "quest:" not in line


def test_unknown_insight_sources_do_not_leak_ids() -> None:
    assert "nowhere" not in _line("quest:nowhere")
    assert "mystery" not in _line("mystery:thing")


def test_elite_insight_keeps_the_elite_name() -> None:
    assert _line("elite:mist_wolf").startswith("首次擊敗精英「")
