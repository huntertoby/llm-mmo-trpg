"""世界亂數衍生與天氣（Phase 5A-2；``docs/phases/Phase5計畫.md`` 2.4、6.5）。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from tests.world.helpers import NOON, make_world, with_rules
from trpg.content.library import ContentLibrary
from trpg.shared.rng import fnv1a64
from trpg.world.clock import WEATHER_PERIOD_SECONDS
from trpg.world.rng import derive_seed, draw, region_seed
from trpg.world.state import CharacterState
from trpg.world.weather import weather_at

MakeChar = Callable[..., CharacterState]


def test_derive_seed_vectors() -> None:
    # 格式「賽季種子:角色:串流:計數」固定；改了會讓舊日誌重播不出同樣結果。
    assert derive_seed(123, "alice", "travel", 0) == fnv1a64(b"123:alice:travel:0")
    assert derive_seed(123, "alice", "travel", 0) == 17398986282972614499
    assert region_seed(123, "cloud_ridge", "weather", 5) == 5157342548396831369
    assert region_seed(123, "cloud_ridge", "weather", 5) == derive_seed(
        123, "@cloud_ridge", "weather", 5
    )


def test_seeds_differ_by_each_part() -> None:
    base = derive_seed(1, "alice", "travel", 0)
    assert base != derive_seed(2, "alice", "travel", 0)
    assert base != derive_seed(1, "bob", "travel", 0)
    assert base != derive_seed(1, "alice", "reveal", 0)
    assert base != derive_seed(1, "alice", "travel", 1)


def test_draw_advances_only_its_stream(make_char: MakeChar) -> None:
    char = make_char(rng_counters={"reveal": 4})
    rng_a, after = draw(7, char, "travel")
    assert after.rng_counters == {"reveal": 4, "travel": 1}
    assert list(after.rng_counters) == ["reveal", "travel"]
    rng_b, _ = draw(7, char, "travel")
    assert rng_a.get_state() == rng_b.get_state()
    rng_c, _ = draw(7, after, "travel")
    assert rng_c.get_state() != rng_a.get_state()


def test_weather_shared_within_region_and_half_day(library: ContentLibrary) -> None:
    world = make_world()
    a = weather_at(library, world, "cloud_ridge", NOON)
    assert a == weather_at(library, world, "cloud_ridge", NOON + 1)
    assert a in library.weather


def test_weather_changes_over_half_days(library: ContentLibrary) -> None:
    world = make_world()
    seen = Counter(
        weather_at(library, world, "cloud_ridge", NOON + i * WEATHER_PERIOD_SECONDS)
        for i in range(200)
    )
    assert len(seen) >= 3
    # 雲嶺偏霧、雨（05 5.1）
    assert seen["fog"] + seen["rain"] > seen["clear"] + seen["night"]


def test_zero_weight_never_drawn(library: ContentLibrary) -> None:
    lib = with_rules(
        library,
        weather=[{"region": "cloud_ridge", "day": {"fog": 1, "clear": 0}, "night": {"rain": 1}}],
    )
    world = make_world()
    for i in range(60):
        now = NOON + i * WEATHER_PERIOD_SECONDS
        expected = "fog" if i % 2 == 0 else "rain"  # NOON 在白天
        assert weather_at(lib, world, "cloud_ridge", now) == expected


def test_default_weather_for_unlisted_region(library: ContentLibrary) -> None:
    lib = with_rules(library, weather=[])
    world = make_world()
    assert weather_at(lib, world, "cloud_ridge", NOON) == "clear"
    assert weather_at(lib, world, "cloud_ridge", NOON + WEATHER_PERIOD_SECONDS) == "night"


def test_weather_depends_on_season_seed(library: ContentLibrary) -> None:
    times = [NOON + i * WEATHER_PERIOD_SECONDS for i in range(40)]
    a = [weather_at(library, make_world(season_seed=1), "cloud_ridge", t) for t in times]
    b = [weather_at(library, make_world(season_seed=2), "cloud_ridge", t) for t in times]
    assert a != b
