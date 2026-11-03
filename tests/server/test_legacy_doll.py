"""沿用上季角色的紙娃娃（Phase 5F-5c；玩法 PM 2026-11-03 代決：種族不算外觀）。"""

from __future__ import annotations

from trpg.content.battle import DollGear, DollLook
from trpg.server.chronicle import RACE_DOLL_FIELDS, legacy_doll

OLD = DollLook(
    skin="#111111",
    hair="long",
    hair_color="#222222",
    eyes="#333333",
    pants="#444444",
    gear={"cloak": DollGear(kind="cape", material="cloth", color="#555555")},
)
BASE = DollLook(skin="#f1c9a5", hair="short", hair_color="#6a3d1e")


def test_same_race_keeps_the_whole_doll() -> None:
    assert legacy_doll(OLD, legacy_race="fox", race="fox", base=BASE) == OLD


def test_a_new_race_resets_the_race_parts_only() -> None:
    doll = legacy_doll(OLD, legacy_race="fox", race="elf", base=BASE)
    assert doll is not None
    for name in RACE_DOLL_FIELDS:
        assert getattr(doll, name) == getattr(BASE, name)
    assert doll.pants == OLD.pants and doll.gear == OLD.gear  # 裝備、褲子不跟種族


def test_a_new_race_without_a_template_doll_falls_back_to_default() -> None:
    assert legacy_doll(OLD, legacy_race="fox", race=None, base=None) is None
