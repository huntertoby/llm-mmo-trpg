"""HC-4d：搬進 content 的大世界數值開進工坊（新開四張全體共用的表，分組顯示）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

import pytest

from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TABLE_KINDS, parse_path

CONTENT = bundled_content_dir()
OPENED: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "world_rules": (
        "world/rules.yaml",
        "rules",
        (
            "battle.fatigue_hp_permille",
            "battle.respawn_seconds",
            "xp.base",
            "hero_growth.insight_per_level",
            "wish.cost_quest_coins",
            "wish.refund_permille",
            "field.sight_range",
            "field.perceive_range",
        ),
    ),
    "world_economy": (
        "world/economy.yaml",
        "economy",
        ("battle_gold.battle", "battle_gold.elite", "sell_permille", "bag_slots"),
    ),
    "world_trade": (
        "world/trade.yaml",
        "trade",
        ("trade.min_level", "mail.mailbox_max", "mail.return_days", "audit.big_value"),
    ),
    "world_season": (
        "world/season.yaml",
        "season",
        (
            "daily_goals.newbie_days",
            "daily_goals.coins",
            "season_boss.daily_attempts",
            "season_boss.score.per_round",
            "league.seeds",
        ),
    ),
}
"""這段新開的表與欄位（表 → 檔、對象 ID、欄位）。"""


def _now(file: str, path: str) -> object:
    return lookup(read_data(CONTENT / file), parse_path(path))


@pytest.mark.parametrize("kind", sorted(OPENED))
def test_world_numbers_are_open_with_groups_and_notes(
    read_service: TuningService, kind: str
) -> None:
    file, object_id, paths = OPENED[kind]
    assert kind in TABLE_KINDS
    detail = object_detail(CONTENT, read_service.table, kind, object_id)
    fields = {f.path: f for f in detail.fields}
    assert sorted(fields) == sorted(paths)
    for path in paths:
        field = fields[path]
        assert field.value == _now(file, path), path
        assert field.group_zh, path
        assert field.label_zh and not field.label_zh.isascii(), path
        assert "調高" in field.note_zh and "調低" in field.note_zh, path
        assert field.hint_min is not None and field.hint_max is not None, path
        assert field.hint_min <= field.value <= field.hint_max, path  # type: ignore[operator]
    assert any("HC-4d" in n for n in detail.notes_zh)


def test_a_world_draft_validates(read_service: TuningService) -> None:
    file, path = "world/economy.yaml", "battle_gold.battle"
    now = _now(file, path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=file, path=path, old=now, new=now + 1)
    result = read_service.check("hc4d-gold", [item])
    assert result.ok, (result.field_errors, result.page_errors)


def test_a_world_permille_over_the_schema_cap_is_refused(read_service: TuningService) -> None:
    file, path = "world/rules.yaml", "wish.refund_permille"
    now = _now(file, path)
    assert isinstance(now, int)
    item = TuningChangeIn(file=file, path=path, old=now, new=1001)
    result = read_service.check("hc4d-refund", [item])
    assert not result.ok
