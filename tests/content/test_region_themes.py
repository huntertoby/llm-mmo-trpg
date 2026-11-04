"""區域主題點綴（Phase RT-1）：`content/ui/region_themes.yaml` 的 schema、挑選與錯誤範例。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.loader import load_content_file
from trpg.content.regions import RegionTable
from trpg.content.registry import KNOWN_CONTENT_FILES
from trpg.content.ui_themes import CORNER_KINDS, FALLBACK_THEME, RegionThemeTable

THEME_FILE = PROJECT_ROOT / "content" / "ui" / "region_themes.yaml"
REGION_FILE = PROJECT_ROOT / "content" / "regions.yaml"

_OK_THEME: dict[str, Any] = {
    "accent": "#a898ff",
    "corner": "filigree",
    "plaque": "crystal",
    "portrait_ring": "#a898ff",
    "ink": "#22305a",
    "seal": "#7a5ad0",
}


def _table(**theme: Any) -> dict[str, Any]:
    return {
        "plaques": {"crystal": {"top": "#2a2a5a", "bottom": "#1a1a3a"}},
        "themes": {"hub": {**_OK_THEME, **theme}},
    }


def test_the_table_loads() -> None:
    table = load_content_file(THEME_FILE, RegionThemeTable)
    assert FALLBACK_THEME in table.themes
    assert "7 個區域主題" in table.summary()


def test_registered_for_content_check() -> None:
    assert any(
        f.relative_path == "ui/region_themes.yaml" and f.model is RegionThemeTable
        for f in KNOWN_CONTENT_FILES
    )


def test_every_region_and_the_capital_have_a_theme() -> None:
    table = load_content_file(THEME_FILE, RegionThemeTable)
    regions = load_content_file(REGION_FILE, RegionTable)
    for region in [r.id for r in regions.regions] + ["capital", "hub"]:
        assert region in table.themes, region


def test_all_corner_kinds_are_used() -> None:
    table = load_content_file(THEME_FILE, RegionThemeTable)
    assert {t.corner for t in table.themes.values()} == set(CORNER_KINDS)


@pytest.mark.parametrize(
    ("region", "corner", "plaque", "accent"),
    [
        ("cloud_ridge", "cloud", "jade", "#6aa84a"),
        ("ashen_waste", "rivet", "iron", "#ff6a1a"),
        ("capital", "filigree", "crystal", "#a898ff"),
        ("crystal_crown", "shard", "marble", "#8ab0ff"),
        ("arcane_hub", "gear", "brass", "#4ad0c8"),
        ("frost_tide", "shell", "sea", "#6ac0e8"),
    ],
)
def test_each_region_picks_its_own_theme(
    region: str, corner: str, plaque: str, accent: str
) -> None:
    theme = load_content_file(THEME_FILE, RegionThemeTable).theme_for(region)
    assert (theme.corner, theme.plaque, theme.accent, theme.portrait_ring) == (
        corner,
        plaque,
        accent,
        accent,
    )


@pytest.mark.parametrize("region", [None, "", "nowhere"])
def test_unknown_region_falls_back_to_hub(region: str | None) -> None:
    table = load_content_file(THEME_FILE, RegionThemeTable)
    assert table.theme_for(region) == table.themes["hub"]


def test_wait_fields_for_rt3() -> None:
    table = load_content_file(THEME_FILE, RegionThemeTable).themes
    assert table["ashen_waste"].wait_fx == "ember"
    assert table["capital"].wait_fx == "crystal"
    assert table["cloud_ridge"].wait_fx == "none"
    inks = {table[r].ink for r in ("cloud_ridge", "ashen_waste", "capital")}
    seals = {table[r].seal for r in ("cloud_ridge", "ashen_waste", "capital")}
    assert len(inks) == 3
    assert len(seals) == 3


@pytest.mark.parametrize(
    "bad",
    [
        {"corner": "dragon"},  # 未知的飾件
        {"accent": "purple"},  # 不是 #rrggbb
        {"portrait_ring": "#abc"},  # 太短
        {"plaque": "gold"},  # 未知的標題牌
        {"wait_fx": "fireworks"},  # 未知的等待點綴
        {"glow": "#ffffff"},  # 拼錯欄位
    ],
)
def test_bad_themes_are_rejected(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RegionThemeTable.model_validate(_table(**bad))


def test_missing_fields_are_rejected() -> None:
    raw = _table()
    del raw["themes"]["hub"]["seal"]
    with pytest.raises(ValidationError):
        RegionThemeTable.model_validate(raw)


def test_hub_is_required() -> None:
    raw = _table()
    raw["themes"] = {"capital": raw["themes"]["hub"]}
    with pytest.raises(ValidationError, match="hub"):
        RegionThemeTable.model_validate(raw)


def test_bad_plaque_colors_are_rejected() -> None:
    raw = _table()
    raw["plaques"]["crystal"] = {"top": "#2a2a5a"}
    with pytest.raises(ValidationError):
        RegionThemeTable.model_validate(raw)
