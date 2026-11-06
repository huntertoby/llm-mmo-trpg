"""實地地圖 ``spawns`` 的 ``personal``、``day_phase``（Phase 6C-1b；21.10 第 9、11 條）。

新手任務的 3 場固定戰與荒原三村落的守點戰標 ``personal``；渡口石階的石階巡邏（草稿：夜晚）標
``day_phase: night``；其他隊伍都不標（全天、共享）。
"""

from __future__ import annotations

import pytest

from trpg.content.library import ContentLibrary

MARKED: dict[tuple[str, str], tuple[bool, str | None]] = {
    ("ferry_steps", "bandit_raiders"): (True, None),  # 新手任務 1
    ("ferry_steps", "bandit_shield_line"): (False, "night"),  # 石階巡邏（夜晚）
    ("bamboo_path", "mist_wolf_pack"): (True, None),  # 新手任務 2
    ("rain_terraces", "terrace_clash"): (True, None),  # 新手任務 3
    ("ash_well_village", "village_raid_mid"): (True, None),  # 守點戰
    ("iron_forge_village", "village_raid_heavy"): (True, None),
    ("red_sand_village", "village_raid_light"): (True, None),
}


@pytest.mark.parametrize(("key", "expected"), sorted(MARKED.items()))
def test_marked_spawns(
    library: ContentLibrary, key: tuple[str, str], expected: tuple[bool, str | None]
) -> None:
    found = library.field_maps[key[0]]
    (spawn,) = [s for s in found.spawns if s.group == key[1]]
    assert (spawn.personal, spawn.day_phase) == expected


def test_other_spawns_are_shared_and_all_day(library: ContentLibrary) -> None:
    others = [
        (m.id, s.group, s.personal, s.day_phase)
        for m in sorted(library.field_maps.values(), key=lambda m: m.id)
        for s in m.spawns
        if (m.id, s.group) not in MARKED
    ]
    assert others
    assert [o for o in others if o[2] or o[3] is not None] == []
