"""HC-4d：大世界的預設值搬進 content 之後的規則對照（少寫一格就驗證失敗、值照內容檔、規則型上限在
載入層檢查）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.library import ContentLibrary
from trpg.content.races import RaceTable
from trpg.content.regions import RegionTable
from trpg.content.roguelite import RunRules
from trpg.content.world import StyleEvalRules, WorldStyle
from trpg.content.world_crafting import CraftingRules, ResonanceRules
from trpg.content.world_economy import EconomyRules
from trpg.content.world_mercenaries import MercenaryTable
from trpg.content.world_newcomer import NewcomerContent
from trpg.content.world_oaths import OathCheck
from trpg.content.world_quests import AffinityRules
from trpg.content.world_rules import WorldRules
from trpg.content.world_season import SeasonContent
from trpg.content.world_situations import SituationRules, situation_problems
from trpg.content.world_trade import TradeRules


def _read(name: str) -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content" / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _drop(data: dict[str, Any], path: tuple[str | int, ...]) -> None:
    node: Any = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]


_CASES: list[tuple[str, type[BaseModel], tuple[str | int, ...]]] = [
    ("world/rules.yaml", WorldRules, ("week_days",)),
    ("world/rules.yaml", WorldRules, ("calendar", "refresh_hour")),
    ("world/rules.yaml", WorldRules, ("battle", "max_rounds")),
    ("world/rules.yaml", WorldRules, ("battle", "respawn_seconds")),
    ("world/rules.yaml", WorldRules, ("enemy_growth", "skill_tier_by_level")),
    ("world/rules.yaml", WorldRules, ("hero_growth", "level_thresholds")),
    ("world/rules.yaml", WorldRules, ("hero_growth", "level_cap")),
    ("world/rules.yaml", WorldRules, ("xp", "shares_permille")),
    ("world/rules.yaml", WorldRules, ("opportunity", "tier_up_permille")),
    ("world/rules.yaml", WorldRules, ("wish", "max_keywords")),
    ("world/rules.yaml", WorldRules, ("field", "walk_max_steps")),
    ("world/rules.yaml", WorldRules, ("field", "gap_third")),
    ("world/rules.yaml", WorldRules, ("field_maps", "layout_sizes")),
    ("world/rules.yaml", WorldRules, ("field_maps", "stones_per_region")),
    ("world/rules.yaml", WorldRules, ("day_parts", "noon")),
    ("world/season.yaml", SeasonContent, ("daily_goals", "count")),
    ("world/season.yaml", SeasonContent, ("world_events", 0, "base_players")),
    ("world/season.yaml", SeasonContent, ("league", "batch_size")),
    ("world/season.yaml", SeasonContent, ("season_boss", "score", "per_round")),
    ("world/season.yaml", SeasonContent, ("season_boss", "daily_attempts")),
    ("world/trade.yaml", TradeRules, ("trade", "min_level")),
    ("world/trade.yaml", TradeRules, ("mail", "note_max")),
    ("world/trade.yaml", TradeRules, ("audit", "lopsided_permille")),
    ("world/economy.yaml", EconomyRules, ("stack_max",)),
    ("world/economy.yaml", EconomyRules, ("battle_gold", "elite")),
    ("world/crafting.yaml", CraftingRules, ("enhance", "gold_per_level")),
    ("world/crafting.yaml", CraftingRules, ("craft", "leaning_weight")),
    ("world/resonance.yaml", ResonanceRules, ("pieces",)),
    ("world/mercenaries.yaml", MercenaryTable, ("min_per_role",)),
    ("world/mercenaries.yaml", MercenaryTable, ("shadow_reports_kept",)),
    ("world/affinity.yaml", AffinityRules, ("rumors_per_week",)),
    ("world/situation_rules.yaml", SituationRules, ("template_limits", "attributes_max")),
    ("world/newcomer.yaml", NewcomerContent, ("reflash_level",)),
    ("world/newcomer.yaml", NewcomerContent, ("range", "demos_per_class")),
    ("roguelite.yaml", RunRules, ("start", "heroes", "melee", "speed")),
    ("roguelite.yaml", RunRules, ("candidates", "llm_share_permille")),
    ("races.yaml", RaceTable, ("limits", "max_uses")),
    ("regions.yaml", RegionTable, ("locations_per_region",)),
    ("llm/world_shattered.yaml", WorldStyle, ("naming", "name_max_chars")),
    ("llm/world_shattered.yaml", WorldStyle, ("naming", "world_terms", "name_prefix_len")),
    ("llm/style_eval.yaml", StyleEvalRules, ("dot_share_max_permille",)),
]


@pytest.mark.parametrize(("name", "model", "path"), _CASES)
def test_missing_value_fails(
    name: str, model: type[BaseModel], path: tuple[str | int, ...]
) -> None:
    data = _read(name)
    model.model_validate(data)
    _drop(data, path)
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_values_follow_content(library: ContentLibrary) -> None:
    """值照搬原本的程式預設（內容檔有寫的以內容檔為準）。"""
    rules = library.world_rules
    assert rules is not None
    assert rules.week_days == 7
    assert (rules.calendar.utc_offset_minutes, rules.calendar.refresh_hour) == (480, 6)
    assert rules.field.walk_max_steps == 30
    assert rules.xp.shares_permille["main_step"] == 5000
    assert rules.field_maps.stones_per_region == (2, 3)
    sizes = rules.field_maps.layout_sizes
    assert (sizes["capital"].long, sizes["capital"].short) == ((28, 36), (20, 28))
    economy = library.world_economy.rules
    assert economy is not None and economy.stack_max["material"] == 20
    assert library.races is not None
    limits = library.races.limits
    assert (limits.max_uses, limits.max_effects) == (2, 3)
    assert (limits.max_sight_reduction_permille, limits.max_resist_permille) == (500, 250)
    assert library.regions is not None
    assert library.regions.locations_per_region == (15, 25)


def test_oath_hp_permille_only_where_used() -> None:
    """``hp_permille`` 只有「HP 低於某值前不能用」用到：其他種類不填也不輸出，這個種類沒填是
    缺欄位。"""
    other = OathCheck(kind="attack_each_turn")
    assert "hp_permille" not in other.model_dump()
    assert other.missing() == []
    until = OathCheck(kind="forbid_skill_tag_until_hp", tags=("fire",))
    assert until.missing() == ["hp_permille"]


def _race_data(tmp: Path, change: dict[str, Any]) -> dict[str, Any]:
    data = _read("races.yaml")
    data["limits"].update(change)
    return data


def test_race_limits_are_read_from_content(tmp_path: Path) -> None:
    """種族技次數上限改小，內容裡每場 2 次的種族技就驗證失敗（上限讀 races.yaml，不是模組常數）。"""
    RaceTable.model_validate(_race_data(tmp_path, {}))
    with pytest.raises(ValidationError, match="每場限用 1～1 次"):
        RaceTable.model_validate(_race_data(tmp_path, {"max_uses": 1}))


def test_template_limits_are_read_from_content(library: ContentLibrary) -> None:
    """情境模板的屬性數上限改小，現有模板（3 種屬性）就在跨檔案檢查被擋。"""
    content = library.world_event_content.situations
    rules = content.rules
    assert rules is not None
    tight = rules.model_copy(
        update={"template_limits": rules.template_limits.model_copy(update={"attributes_max": 2})}
    )
    region, table = sorted(content.templates.items())[0]
    events = library.world_event_content.events.get(region)
    kwargs: dict[str, Any] = {
        "events": events,
        "world_map": library.world_maps.get(region),
        "status_ids": library.ruleset.statuses.by_id(),
        "thread_ids": set(),
    }
    loose = situation_problems(table, rules=rules, **kwargs)
    strict = situation_problems(table, rules=tight, **kwargs)
    assert any("attributes 必須有 2～2 種" in p for p in strict if p not in loose), strict
