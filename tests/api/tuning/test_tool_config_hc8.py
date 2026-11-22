"""HC-8：數值工坊的 10 項工具設定搬到 ``config/tuning.toml``（值不變、local 覆寫、驗證）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from trpg.api.tuning import drafts, schemas, skills
from trpg.api.tuning.tool_config import (
    DEFAULT_CONFIG_PATH,
    TUNING_TOOL,
    TuningToolConfigError,
    TuningToolSettings,
    load_tuning_tool_settings,
)

BEFORE = {
    "small_sample": 30,
    "max_ratio_seeds": 250,
    "sim_default_seeds": 3,
    "map_default_seeds": 24,
    "max_sim_maps": 3,
    "max_sim_battles": 160,
    "ratio_default_seeds": 50,
    "ratio_max_work": 40_000,
    "draft_name_max": 40,
    "max_group": 100,
}
"""HC-8 搬家前程式裡的值。"""


def _no_local(tmp_path: Path) -> Path:
    return tmp_path / "missing.local.toml"


def test_repo_file_and_defaults_equal_old_values(tmp_path: Path) -> None:
    from_file = load_tuning_tool_settings(DEFAULT_CONFIG_PATH, _no_local(tmp_path), env={})
    assert from_file.model_dump() == BEFORE
    assert TuningToolSettings().model_dump() == BEFORE


def test_module_constants_read_the_settings() -> None:
    # 本機沒有 tuning.local.toml 時就是 BEFORE；有的話常數照設定（這裡只核對接線）。
    wired = {
        "small_sample": schemas.SMALL_SAMPLE,
        "max_ratio_seeds": schemas.MAX_RATIO_SEEDS,
        "sim_default_seeds": schemas.SIM_DEFAULT_SEEDS,
        "map_default_seeds": schemas.MAP_DEFAULT_SEEDS,
        "max_sim_maps": schemas.MAX_SIM_MAPS,
        "max_sim_battles": schemas.MAX_SIM_BATTLES,
        "ratio_default_seeds": schemas.RATIO_DEFAULT_SEEDS,
        "ratio_max_work": schemas.RATIO_MAX_WORK,
        "draft_name_max": drafts.DRAFT_NAME_MAX,
        "max_group": skills.MAX_GROUP,
    }
    assert wired == TUNING_TOOL.model_dump()


def test_local_file_overrides_only_its_keys(tmp_path: Path) -> None:
    local = tmp_path / "tuning.local.toml"
    local.write_text("[sim]\ndefault_seeds = 5\n[skills]\nmax_group = 20\n", encoding="utf-8")
    got = load_tuning_tool_settings(DEFAULT_CONFIG_PATH, local, env={})
    assert got.sim_default_seeds == 5
    assert got.max_group == 20
    assert got.max_ratio_seeds == BEFORE["max_ratio_seeds"]


def test_env_path_and_missing_file(tmp_path: Path) -> None:
    other = tmp_path / "other.toml"
    other.write_text("[ratio]\nmax_work = 100\n", encoding="utf-8")
    got = load_tuning_tool_settings(
        None, _no_local(tmp_path), env={"TRPG_TUNING_CONFIG": str(other)}
    )
    assert got.ratio_max_work == 100
    with pytest.raises(TuningToolConfigError, match="找不到"):
        load_tuning_tool_settings(tmp_path / "nope.toml", _no_local(tmp_path), env={})


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("[sim]\ndefault_seed = 3\n", "不認得"),
        ("[simm]\ndefault_seeds = 3\n", "不認得"),
        ("[sim]\nmax_maps = 0\n", "不合法"),
        ("[sim]\ndefault_seeds = 300\n", "不能大於"),
        ("[sim\n", "無法讀取"),
    ],
)
def test_bad_files_are_rejected(tmp_path: Path, text: str, match: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(TuningToolConfigError, match=match):
        load_tuning_tool_settings(path, _no_local(tmp_path), env={})
