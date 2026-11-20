"""SK-5：數值工坊新增兩種對象——被動觸發時機的預算係數（``skill_triggers.yaml``）與組合器的附帶
配方機率（``skill_composer.yaml``）。SK-3b 待決 4、WC-2 待決 11、SK-4 待決 4。

數值一律讀 ``content/`` 的現值（使用者寫回後不必收編）；只寫死欄位路徑與對象種類。
"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.objects import TABLE_NAMES_ZH, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup, patch_text
from trpg.content.loader import bundled_content_dir
from trpg.content.skill_triggers import EVERY_N_HITS
from trpg.content.tuning_fields import TABLE_KINDS, parse_path

CONTENT = bundled_content_dir()
TRIGGERS = "skill_triggers.yaml"
COMPOSER = "skill_composer.yaml"
COMPOSER_PATHS = (
    # SK-2b
    "structure.hook_core_permille",
    "structure.absorb_core_permille",
    "structure.absorb_secondary_permille",
    "structure.contagion_permille",
    # AP-2：白板主動技的預設 AP 與退回的 AP（整數，不是千分比）
    "whiteboard.ap_cost",
    "whiteboard.fallback_ap_cost",
    # AP-2
    "structure.borrow_core_permille",
    "structure.ap_spent_passive_permille",
    # SK-3b
    "structure.exploit_passive_permille",
    "structure.reroll_reaction_permille",
    # WC-2
    "passive.around_permille",
    "structure.stack_rider_permille",
    "structure.summon_rider_permille",
    # SK-4
    "structure.lifesteal_permille",
    "structure.lifesteal_amount_permille",
)
EXPLOITED = "on_keyword_exploited"


def _now(file: str, path: str) -> Any:
    found = lookup(read_data(CONTENT / file), parse_path(path))
    return None if found is MISSING else found


def _trigger_path(trigger_id: str) -> str:
    rows = read_data(CONTENT / TRIGGERS)["triggers"]
    index = next(i for i, row in enumerate(rows) if row["id"] == trigger_id)
    return f"triggers[{index}].budget_coefficient_permille"


def test_both_tables_are_listed(read_service: TuningService) -> None:
    assert {"skill_triggers", "skill_composer"} <= set(TABLE_KINDS)
    found = {o.kind: o for o in read_service.objects() if o.kind in TABLE_KINDS}
    assert (found["skill_triggers"].id, found["skill_triggers"].file) == (
        "skill_triggers",
        TRIGGERS,
    )
    assert (found["skill_composer"].id, found["skill_composer"].file) == (
        "skill_composer",
        COMPOSER,
    )
    for kind in ("skill_triggers", "skill_composer"):
        assert found[kind].category == "rules"
        assert found[kind].name_zh == TABLE_NAMES_ZH[kind]
    assert read_service.objects("skill_composer") == [found["skill_composer"]]


def test_trigger_coefficients_and_the_n_table_are_open(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "skill_triggers", "skill_triggers")
    rows = read_data(CONTENT / TRIGGERS)["triggers"]
    with_coef = [r["id"] for r in rows if "budget_coefficient_permille" in r]
    assert EVERY_N_HITS not in with_coef
    # HC-B：「每命中 n 次」依 n 查的係數也開（數字鍵），排在一般係數後面
    index = next(i for i, r in enumerate(rows) if r["id"] == EVERY_N_HITS)
    by_n = [f"triggers[{index}].budget_by_n_permille.{n}" for n in (2, 3)]
    assert [f.path for f in detail.fields] == [_trigger_path(i) for i in with_coef] + by_n
    assert [f.value for f in detail.fields[-2:]] == [_now(TRIGGERS, p) for p in by_n]
    exploited = next(f for f in detail.fields if f.path == _trigger_path(EXPLOITED))
    assert exploited.value == _now(TRIGGERS, exploited.path)
    assert "你造的關鍵字被利用時" in exploited.label_zh
    assert (exploited.limit_min, exploited.limit_max) == (1, None)
    assert any("全體共用" in n for n in detail.notes_zh)


def test_composer_opens_only_the_listed_values(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "skill_composer", "skill_composer")
    assert [f.path for f in detail.fields] == list(COMPOSER_PATHS)
    assert [f.value for f in detail.fields] == [_now(COMPOSER, p) for p in COMPOSER_PATHS]
    limits = {f.path: (f.limit_min, f.limit_max) for f in detail.fields}
    assert limits["structure.lifesteal_amount_permille"] == (1, 500)
    whiteboard = {"whiteboard.ap_cost", "whiteboard.fallback_ap_cost"}
    assert {limits[p] for p in COMPOSER_PATHS[:-1] if p not in whiteboard} == {(0, 1000)}
    # 結構性的清單不開（SK-5 規格「不開放結構性欄位」）
    assert read_service.table.target("skill_composer") is not None
    assert all("skeletons" not in f.path for f in detail.fields)


def test_changes_validate_and_bad_values_are_refused(read_service: TuningService) -> None:
    life = _now(COMPOSER, "structure.lifesteal_permille")
    amount = _now(COMPOSER, "structure.lifesteal_amount_permille")
    around = _now(COMPOSER, "passive.around_permille")
    coef_path = _trigger_path(EXPLOITED)
    coef = _now(TRIGGERS, coef_path)
    changes = (
        Change(file=COMPOSER, path="structure.lifesteal_permille", old=life, new=life + 50),
        Change(
            file=COMPOSER, path="structure.lifesteal_amount_permille", old=amount, new=amount + 50
        ),
        Change(file=COMPOSER, path="passive.around_permille", old=around, new=around + 50),
        Change(file=TRIGGERS, path=coef_path, old=coef, new=coef + 10),
    )
    read_service.drafts.put(Draft(name="sk5", changes=changes))
    result = read_service.check("sk5")
    assert result.ok, (result.field_errors, result.page_errors)
    bad = (
        TuningChangeIn(file=COMPOSER, path="structure.lifesteal_permille", old=life, new=1001),
        TuningChangeIn(
            file=COMPOSER, path="structure.lifesteal_amount_permille", old=amount, new=600
        ),
        TuningChangeIn(file=TRIGGERS, path=coef_path, old=coef, new=0),
    )
    for change in bad:
        refused = read_service.check("current", [change])
        assert not refused.ok
        assert [(e.file, e.path) for e in refused.field_errors] == [(change.file, change.path)]


def test_anchors_elsewhere_in_the_file_do_not_block_a_patch() -> None:
    """``skill_composer.yaml`` 的白板配方用了錨點：只擋路徑經過共用節點的改動。"""
    text = "s: {p: 1}  # 註解\nw: &x [1, 2]\nv: *x\nm: &y {q: 3}\n"
    assert patch_text(text, [(("s", "p"), 5)]) == text.replace("p: 1", "p: 5")
    assert patch_text(text, [(("m", "q"), 4)]) == text.replace("q: 3", "q: 4")  # 只有錨點沒別名
    with pytest.raises(PatchError, match="錨點"):
        patch_text(text, [(("w", 0), 9)])
    with pytest.raises(PatchError, match="錨點"):
        patch_text(text, [(("v", 1), 9)])


def test_structural_composer_fields_are_not_editable(read_service: TuningService) -> None:
    skeletons = list(_now(COMPOSER, "structure.lifesteal_skeletons"))
    change = TuningChangeIn(
        file=COMPOSER, path="structure.lifesteal_skeletons", old=skeletons, new=["strike"]
    )
    refused = read_service.check("current", [change])
    assert not refused.ok
