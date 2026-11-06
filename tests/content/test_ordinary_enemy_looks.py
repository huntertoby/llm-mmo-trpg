"""Phase QK-6a（#137 第 4 點）：一般敵人依單位 id 在 ``look_range`` 裡挑外觀。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.battle import CreatureLook, DollLook, LookRange, UnitTemplate
from trpg.content.enemy_looks import (
    is_ordinary_enemy,
    look_range_problems,
    ordinary_enemy_doll,
    pick_look,
)
from trpg.content.library import ContentLibrary
from trpg.content.library.tables import _check_unit_races
from trpg.engine.lifecycle import make_unit
from trpg.shared.errors import ContentError
from trpg.shared.types import Pos, Team, UnitId

RANGED = (
    "bandit",
    "bandit_archer",
    "bandit_shieldbearer",
    "bandit_rookie",
    "bandit_archer_rookie",
    "bandit_guard",
    "bandit_archer_guard",
    "bandit_shieldbearer_guard",
)
SEED = 7
IDS = tuple(f"unit_{i}" for i in range(1, 201))


def _with(template: UnitTemplate, **update: Any) -> UnitTemplate:
    return UnitTemplate.model_validate({**template.model_dump(), **update})


def test_demo_templates_have_ranges(library: ContentLibrary) -> None:
    for tid in RANGED:
        template = library.unit(tid)
        assert template.look_range is not None, tid
        assert is_ordinary_enemy(template, Team.ENEMY), tid
    for tid in ("bandit_boss", "bandit_warlord", "bandit_captain", "sect_swordsman"):
        assert library.unit(tid).look_range is None, tid


def test_same_id_same_look(library: ContentLibrary) -> None:
    bandit = library.unit("bandit")
    first = ordinary_enemy_doll(bandit, "unit_3", Team.ENEMY, SEED)
    second = ordinary_enemy_doll(bandit, "unit_3", Team.ENEMY, SEED)
    assert first is not None and first.custom is not None
    assert first == second
    assert first.model_copy(update={"custom": None}) == bandit.doll  # 其餘照範本


def test_same_seed_same_look_other_seed_differs(library: ContentLibrary) -> None:
    """同一種子、同一單位挑出相同外觀；換種子（換一場）就不同（單位 ID 每場從同一組編號開始）。"""
    bandit = library.unit("bandit")
    look_range = bandit.look_range
    assert look_range is not None
    for uid in IDS[:10]:
        assert pick_look(SEED, bandit.id, uid, look_range) == pick_look(
            SEED, bandit.id, uid, look_range
        )
    one = [pick_look(1, bandit.id, uid, look_range) for uid in IDS[:10]]
    two = [pick_look(2, bandit.id, uid, look_range) for uid in IDS[:10]]
    assert one != two
    same_uid = {repr(pick_look(seed, bandit.id, "unit_0004", look_range)) for seed in range(30)}
    assert len(same_uid) > 10  # 同一個編號在不同場長得不一樣


def test_ids_cover_the_range(library: ContentLibrary) -> None:
    bandit = library.unit("bandit")
    look_range = bandit.look_range
    assert look_range is not None
    picks = [pick_look(SEED, bandit.id, uid, look_range) for uid in IDS]
    for name in ("skin", "hair", "hair_color", "beard"):
        seen = {getattr(p, name) for p in picks}
        assert seen == set(getattr(look_range, name)), name
    for pick in picks:
        assert pick.face is None and pick.frame is None  # 範圍以外的欄位不挑


def test_make_unit_writes_custom(library: ContentLibrary) -> None:
    bandit = library.unit("bandit")
    looks = []
    for uid in ("unit_4", "unit_5", "unit_6"):
        unit = make_unit(
            UnitId(uid),
            template=bandit,
            weapon=library.weapons[bandit.weapon],
            team=Team.ENEMY,
            pos=Pos(x=0, y=0),
            name="x",
            rules=library.ruleset,
            seed=SEED,
        )
        assert unit.doll is not None and unit.doll.custom is not None
        assert unit.doll == ordinary_enemy_doll(bandit, uid, Team.ENEMY, SEED)
        looks.append(unit.doll.custom)
    assert len(set(map(repr, looks))) > 1


def test_ally_side_keeps_template(library: ContentLibrary) -> None:
    bandit = library.unit("bandit")
    assert ordinary_enemy_doll(bandit, "unit_3", Team.ALLY, SEED) == bandit.doll


def test_boss_creature_summon_untouched(library: ContentLibrary) -> None:
    for tid in sorted(library.units):
        template = library.unit(tid)
        if template.look_range is None:
            for uid in IDS[:5]:
                assert ordinary_enemy_doll(template, uid, Team.ENEMY, SEED) == template.doll, tid
    boss = library.unit("bandit_boss")
    assert not is_ordinary_enemy(boss, Team.ENEMY)
    lizard = library.unit("ember_lizard")
    assert not is_ordinary_enemy(lizard, Team.ENEMY)


def test_boss_creature_summon_cannot_have_range(library: ContentLibrary) -> None:
    look_range = {"hair": ["short", "long"]}
    # 頭目可以照寫（測試常把一般敵人加上 boss 標籤），但不挑：外觀固定
    boss = _with(library.unit("bandit"), tags=["boss", "humanoid"])
    assert boss.look_range is not None
    assert ordinary_enemy_doll(boss, "unit_2", Team.ENEMY, SEED) == boss.doll
    lizard = library.unit("ember_lizard")
    assert lizard.doll is not None and lizard.doll.creature is not None
    with pytest.raises(ValidationError, match="人形"):
        _with(lizard, look_range=look_range)
    summons = [t for t in library.units.values() if t.summon]
    if summons:
        with pytest.raises(ValidationError, match="召喚物"):
            _with(summons[0], look_range=look_range)


def test_identity_features_kept(library: ContentLibrary) -> None:
    bandit = library.unit("bandit")
    assert bandit.doll is not None
    look_range = LookRange(hair=("short", "long"), beard=("none", "stubble"), skin=("#7a4e32",))
    for hair in ("bun", "none"):
        doll = bandit.doll.model_copy(update={"hair": hair, "beard": True})
        template = bandit.model_copy(update={"doll": doll, "look_range": look_range})
        for uid in IDS[:20]:
            got = ordinary_enemy_doll(template, uid, Team.ENEMY, SEED)
            assert got is not None and got.custom is not None
            assert got.custom.hair is None and got.custom.beard is None
            assert got.custom.skin == "#7a4e32"
    skull = bandit.doll.model_copy(update={"skull": True})
    template = bandit.model_copy(update={"doll": skull, "look_range": look_range})
    assert ordinary_enemy_doll(template, "unit_1", Team.ENEMY, SEED) == skull
    creature = bandit.doll.model_copy(update={"creature": CreatureLook(body="lizard")})
    template = bandit.model_copy(update={"doll": creature, "look_range": look_range})
    assert ordinary_enemy_doll(template, "unit_1", Team.ENEMY, SEED) == creature


def test_out_of_range_fails_to_load(library: ContentLibrary) -> None:
    table = library.ruleset.races
    assert table is not None
    assert look_range_problems(table, LookRange(hair=("short",))) == []
    assert look_range_problems(table, LookRange(race="elf", beard=("full",)))
    assert look_range_problems(table, LookRange(skin=("#000000",)))
    assert look_range_problems(table, LookRange(race="nobody", hair=("short",)))
    bad = library.unit("bandit").model_copy(
        update={"look_range": LookRange(race="elf", hair=("short",), beard=("goatee",))}
    )
    with pytest.raises(ContentError, match="beard"):
        _check_unit_races(Path("content"), {"bandit": bad}, table)


def test_range_schema() -> None:
    with pytest.raises(ValidationError, match="至少"):
        LookRange()
    with pytest.raises(ValidationError, match="重複"):
        LookRange(hair=("short", "short"))
    with pytest.raises(ValidationError):
        LookRange.model_validate({"hair": ["mohawk"]})
    with pytest.raises(ValidationError):
        LookRange.model_validate({"skin": ["red"]})


def test_doll_without_custom_on_templates(library: ContentLibrary) -> None:
    for template in library.units.values():
        doll: DollLook | None = template.doll
        assert doll is None or doll.custom is None, template.id
