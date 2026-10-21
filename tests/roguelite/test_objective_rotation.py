"""勝利條件輪替（Phase 3-22）：一輪的 5 場一般戰鬥至少 1 場撤離、1 場守點，Boss 戰全滅。"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest
from pydantic import ValidationError

from tests.roguelite.helpers import library
from trpg.content.roguelite import RunRules, roguelite_problems
from trpg.roguelite import new_run
from trpg.roguelite.progress import battle_setup
from trpg.roguelite.start import make_plan
from trpg.roguelite.state import BattleNode


def test_every_run_has_at_least_one_escape_and_one_defend() -> None:
    lib = library()
    for seed in range(60):
        plan = make_plan(lib, seed)
        regular = [p for p in plan if not p.boss]
        counts = Counter(p.objective for p in regular)
        assert counts["escape"] >= 1 and counts["defend"] >= 1, seed
        assert len(regular) == lib.roguelite.battles
        for p in regular:  # 被選中的場次，地圖一定有那個條件的資料
            assert lib.map(p.map_id).supports_objective(p.objective), (seed, p)
        archetypes = [lib.map(p.map_id).archetype for p in regular]
        assert len(set(archetypes)) == len(archetypes)  # 同一輪地圖類型仍不重複


def test_boss_battle_stays_eliminate() -> None:
    lib = library()
    for seed in range(20):
        boss = make_plan(lib, seed)[-1]
        assert boss.boss and boss.objective == "eliminate"
        setup = battle_setup(
            lib,
            new_run(lib, "build_banisher", seed).model_copy(
                update={"node": BattleNode(index=boss.index)}
            ),
        )
        assert setup.effective_objective.kind == "eliminate"


def test_plan_is_deterministic_and_varies_with_the_seed() -> None:
    lib = library()
    assert make_plan(lib, 11) == make_plan(lib, 11)
    kinds = {tuple(p.objective for p in make_plan(lib, s)) for s in range(30)}
    assert len(kinds) > 3  # 不是每輪都排成同樣的順序


def test_battle_setup_uses_the_map_objective_data() -> None:
    lib = library()
    for seed in range(12):
        run = new_run(lib, "build_banisher", seed)
        for plan in run.plan[:-1]:
            at = run.model_copy(update={"node": BattleNode(index=plan.index)})
            objective = battle_setup(lib, at).effective_objective
            assert objective == lib.map(plan.map_id).objective_for(plan.objective)
            assert objective.kind == plan.objective


def test_rotation_rules_are_content_and_validated() -> None:
    lib = library()
    rotation = lib.roguelite.objective_rotation
    assert (rotation.min_escape, rotation.min_defend) == (1, 1)
    data: dict[str, Any] = lib.roguelite.model_dump(mode="json")
    with pytest.raises(ValidationError, match="最少場數總和"):
        RunRules.model_validate({**data, "objective_rotation": {"min_escape": 3, "min_defend": 3}})
    # 要求的場數多到地圖類型不夠保證時，跨檔案檢查會說明
    greedy = RunRules.model_validate(
        {**data, "objective_rotation": {"min_escape": 3, "min_defend": 2}}
    )
    problems = roguelite_problems(greedy, lib.maps, lib.units, lib.ruleset.core.tier_budget)
    assert any("支援" in p for p in problems)
