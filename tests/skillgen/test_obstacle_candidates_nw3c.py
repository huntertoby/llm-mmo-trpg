"""NW-3c：組合器的造牆候選排除冷卻井（玩法 PM 交接 4.1.15 第 4 點）。

組合器 ``create_obstacle`` 的物件只從 :func:`~trpg.skillgen.composer_parts.obstacle_candidates`
抽：``blocks_move``、不是 ``explosive``、不在 ``skill_composer.yaml`` 的
``structure.obstacle_exclude``。冷卻井（打破造 3×3 水）在排除清單裡。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.skillgen.helpers import lib
from trpg.content.library import load_library
from trpg.content.loader import bundled_content_dir, parse_yaml
from trpg.shared.errors import ContentError
from trpg.skillgen.composer_parts import obstacle_candidates
from trpg.skillgen.random_composer import ComposeError, compose_random_skill


def test_candidates_follow_the_tag_filter_minus_the_exclusions() -> None:
    library = lib()
    excluded = set(library.composer.structure.obstacle_exclude)
    want = sorted(
        o.id
        for o in library.ruleset.objects.objects
        if "blocks_move" in o.tags and "explosive" not in o.tags and o.id not in excluded
    )
    assert list(obstacle_candidates(library)) == want


def test_cooling_well_is_never_a_candidate() -> None:
    library = lib()
    assert "cooling_well" in library.composer.structure.obstacle_exclude
    candidates = obstacle_candidates(library)
    assert "cooling_well" not in candidates
    # 其他可阻擋的牆照舊在（4.1.15 第 1 點：木箱、石柱這些也算）
    assert {"crate", "stone_pillar", "earth_wall", "ice_wall", "thorn_wall"} <= set(candidates)
    objects = library.ruleset.objects.by_id()
    assert all("explosive" not in objects[i].tags for i in candidates)


def _obstacle_objects(skill: Any) -> list[str]:
    return [
        spec.object
        for spec in skill.iter_effects(
            include_followup=True,
            include_variants=True,
            include_backlash=True,
            include_modifiers=True,
        )
        if spec.type == "create_obstacle" and spec.object is not None
    ]


def test_control_seeds_do_place_walls() -> None:
    """下面的性質測試不是空轉：控場骨架的前 60 個種子裡就有會造牆的（物件只看在不在候選內）。"""
    library = lib()
    allowed = set(obstacle_candidates(library))
    placed: list[str] = []
    for seed in range(60):
        try:
            skill = compose_random_skill(seed, skeleton="control", library=library)
        except ComposeError:
            continue
        placed += _obstacle_objects(skill)
    assert len(placed) >= 2
    assert set(placed) <= allowed


@settings(
    max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_composer_never_places_a_cooling_well(seed: int) -> None:
    """控場骨架是唯一會抽 ``create_obstacle`` 的骨架；任何種子都不會放出冷卻井。"""
    library = lib()
    allowed = set(obstacle_candidates(library))
    try:
        skill = compose_random_skill(seed, skeleton="control", library=library)
    except ComposeError:
        return
    placed = _obstacle_objects(skill)
    assert "cooling_well" not in placed
    assert set(placed) <= allowed


def test_unknown_excluded_object_fails_to_load(tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(bundled_content_dir(), content)
    path = content / "skill_composer.yaml"
    text = path.read_text(encoding="utf-8")
    assert "obstacle_exclude: [cooling_well]" in text
    path.write_text(
        text.replace("obstacle_exclude: [cooling_well]", "obstacle_exclude: [no_such_object]"),
        encoding="utf-8",
    )
    assert parse_yaml(path.read_text(encoding="utf-8")) is not None
    with pytest.raises(ContentError, match="no_such_object"):
        load_library(content)
