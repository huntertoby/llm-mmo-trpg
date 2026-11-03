"""沿用上季角色的紙娃娃（Phase 5F-5c；玩法 PM 2026-11-03 代決：種族不算外觀）。"""

from __future__ import annotations

from trpg.content.battle import DollGear, DollLook
from trpg.content.races import RaceLook
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


def test_a_new_race_keeps_values_the_new_race_also_has() -> None:
    """5F-3c 代決：目前的值新種族也有（等於範本預設或新種族外觀的同名欄位）就保留。"""
    elf = RaceLook(skin="#f6e0cc", hair="long", hair_color="#e8e0c8")
    old = OLD.model_copy(update={"skin": "#f6e0cc", "hair_color": "#6a3d1e"})
    doll = legacy_doll(old, legacy_race="fox", race="elf", base=BASE, race_look=elf)
    assert doll is not None
    assert doll.skin == "#f6e0cc"  # 新種族外觀的膚色
    assert doll.hair == "long"  # 新種族外觀的髮型
    assert doll.hair_color == "#6a3d1e"  # 範本預設也算新種族有
    assert doll.eyes == BASE.eyes  # 新種族沒有的值改回預設
    assert doll.pants == OLD.pants and doll.gear == OLD.gear


def test_skull_is_kept_only_when_the_new_template_has_it() -> None:
    skull = OLD.model_copy(update={"skull": True})
    elf = RaceLook(skin="#f6e0cc")
    doll = legacy_doll(skull, legacy_race="fox", race="elf", base=BASE, race_look=elf)
    assert doll is not None and doll.skull is False
    base = BASE.model_copy(update={"skull": True})
    doll = legacy_doll(skull, legacy_race="fox", race="elf", base=base, race_look=elf)
    assert doll is not None and doll.skull is True
