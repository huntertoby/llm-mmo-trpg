"""HC-3：工坊畫面的預設種子數與上限由 API 帶（對齊 ``api/tuning/schemas.py``），前端不寫死。"""

from __future__ import annotations

from trpg.api.tuning.ratios import DEFAULT_SEEDS
from trpg.api.tuning.schemas import MAX_RATIO_SEEDS, SMALL_SAMPLE
from trpg.api.tuning.service import (
    DEFAULT_MAP_SEEDS,
    DEFAULT_SIM_SEEDS,
    MAX_SIM_MAPS,
    TuningService,
)
from trpg.api.tuning.skills import MAX_GROUP


def test_sim_options_carry_defaults_and_limits(read_service: TuningService) -> None:
    options = read_service.sim_options()
    assert options.default_seeds == DEFAULT_SIM_SEEDS
    assert options.map_default_seeds == DEFAULT_MAP_SEEDS
    assert options.ratio_default_seeds == DEFAULT_SEEDS
    assert options.ratio_max_seeds == MAX_RATIO_SEEDS
    assert options.max_maps == MAX_SIM_MAPS
    assert options.small_sample == SMALL_SAMPLE


def test_status_carries_group_limit(read_service: TuningService) -> None:
    assert read_service.status().max_group == MAX_GROUP
