"""BS-1：數值工坊開放背刺／潛行偷襲的加成（``rules/core.yaml``）與無聲的預算成本
（``skill_budget.yaml``），06 6.21.1「數值工坊開放的欄位」。

數值一律讀 ``content/`` 的現值（使用者寫回後不必收編）；只寫死欄位路徑與對象種類。
"""

from __future__ import annotations

from typing import Any

from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.objects import TABLE_NAMES_ZH, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, lookup
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TABLE_KINDS, parse_path

CONTENT = bundled_content_dir()
CORE = "rules/core.yaml"
BUDGET = "skill_budget.yaml"
CORE_PATHS = ("backstab_hit_bonus", "backstab_crit_range_bonus", "ambush_hit_bonus")
BUDGET_PATHS = ("modifier.points_milli.silent_strike", "silent_strike_round_milli")


def _now(file: str, path: str) -> Any:
    found = lookup(read_data(CONTENT / file), parse_path(path))
    return None if found is MISSING else found


def test_the_rules_and_budget_tables_are_listed(read_service: TuningService) -> None:
    assert TABLE_KINDS == ("ai", "rules", "budget")
    found = {o.kind: o for o in read_service.objects() if o.kind in ("rules", "budget")}
    assert (found["rules"].id, found["rules"].file, found["rules"].category) == (
        "core",
        CORE,
        "rules",
    )
    assert (found["budget"].id, found["budget"].file, found["budget"].category) == (
        "skill_budget",
        BUDGET,
        "rules",
    )
    assert found["rules"].name_zh == TABLE_NAMES_ZH["rules"]


def test_the_detail_shows_the_current_values(read_service: TuningService) -> None:
    core = object_detail(CONTENT, read_service.table, "rules", "core")
    assert [f.path for f in core.fields] == list(CORE_PATHS)
    assert [f.value for f in core.fields] == [_now(CORE, p) for p in CORE_PATHS]
    assert any("全體共用" in n for n in core.notes_zh)
    budget = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    assert [f.path for f in budget.fields] == list(BUDGET_PATHS)
    assert [f.value for f in budget.fields] == [_now(BUDGET, p) for p in BUDGET_PATHS]


def test_changes_validate_and_bad_values_are_refused(read_service: TuningService) -> None:
    hit, silent = _now(CORE, "backstab_hit_bonus"), _now(BUDGET, BUDGET_PATHS[0])
    changes = (
        Change(file=CORE, path="backstab_hit_bonus", old=hit, new=hit + 1),
        Change(file=BUDGET, path=BUDGET_PATHS[0], old=silent, new=silent + 40),
    )
    read_service.drafts.put(Draft(name="bs1", changes=changes))
    result = read_service.check("bs1")
    assert result.ok, (result.field_errors, result.page_errors)
    bad = TuningChangeIn(file=CORE, path="backstab_hit_bonus", old=hit, new=-1)
    refused = read_service.check("current", [bad])
    assert not refused.ok
    assert [(e.file, e.path) for e in refused.field_errors] == [(CORE, "backstab_hit_bonus")]
