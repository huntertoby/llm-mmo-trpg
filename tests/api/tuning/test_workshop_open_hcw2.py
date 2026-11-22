"""HC-W2：工坊開放 2（形狀查表倍率搬進 ``skill_budget.yaml``；形態、裝備規則、物品生成開進工坊）。

數值一律讀 ``content/`` 的現值；只寫死欄位路徑。
"""

from __future__ import annotations

from typing import Any

import pytest

from trpg.api.tuning.check import prepare
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.objects import object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import lookup
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TABLE_KINDS, parse_path
from trpg.skillgen.budget import skill_budget

CONTENT = bundled_content_dir()
BUDGET = "skill_budget.yaml"
NEW_TABLES = {
    "forms": "forms.yaml",
    "equipment": "rules/equipment.yaml",
    "item_gen": "item_gen.yaml",
}
"""HC-W2 新開的三張表：對象種類 → 檔（對象 ID＝檔名）。"""


def _cone_skills(library: ContentLibrary) -> dict[str, int]:
    """內建技能裡用錐形的招 → 錐形長度（size）。"""
    out: dict[str, int] = {}
    for sid, skill in sorted(library.skills.items()):
        if skill.shape.type == "cone":
            size = skill.shape.param_values().get("size")
            if isinstance(size, int):
                out[sid] = size
    return out


def test_shape_lookup_tables_are_open_in_the_shape_group(read_service: TuningService) -> None:
    detail = object_detail(CONTENT, read_service.table, "budget", "skill_budget")
    by_path = {f.path: f for f in detail.fields}
    prices = read_data(CONTENT / BUDGET)["shape_budget"]
    params = {"cone": "錐形長度", "cross": "十字臂長", "ring": "環形半徑", "chain": "連鎖跳"}
    for sid, word in params.items():
        assert by_path[f"shape_budget.{sid}.base_permille"].group_zh == "形狀"
        for key in ("by_value", "non_power_by_value"):
            for value, permille in (prices[sid].get(key) or {}).items():
                field = by_path[f"shape_budget.{sid}.{key}.{value}"]
                assert field.value == permille
                assert field.group_zh == "形狀"
                assert f"{word} {value}" in field.label_zh
                assert "越大" in field.note_zh


def test_a_cone_table_draft_moves_only_the_cones_of_that_size(
    read_service: TuningService, content_library: ContentLibrary
) -> None:
    cones = _cone_skills(content_library)
    size = max(set(cones.values()), key=list(cones.values()).count)  # 用最多招的長度
    path = f"shape_budget.cone.by_value.{size}"
    now = content_library.budget.shape_budget["cone"].by_value
    assert now is not None
    change = Change(file=BUDGET, path=path, old=now[size], new=now[size] * 2)
    prepared = prepare(CONTENT, read_service.table, [change])
    assert not prepared.errors
    draft = load_library(read_service.workspace.draft(prepared.texts))
    assert (draft.budget.shape_budget["cone"].by_value or {})[size] == now[size] * 2
    moved = 0
    for sid, skill_size in cones.items():
        before = skill_budget(content_library.skills[sid], content_library)
        after = skill_budget(draft.skills[sid], draft)
        assert after.usable == before.usable
        if skill_size != size:
            assert after.ratio == before.ratio, sid
        elif after.ratio != before.ratio:
            assert after.ratio > before.ratio, sid
            moved += 1
    assert moved, "至少要有一招這個長度的錐形預算比例變高"
    other = next(s for s in sorted(content_library.skills) if s not in cones)
    assert (
        skill_budget(draft.skills[other], draft).ratio
        == skill_budget(content_library.skills[other], content_library).ratio
    )


# ---------------------------------------------------------------------------
# 第 2 項：形態、裝備規則、物品生成
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(NEW_TABLES))
def test_the_new_tables_are_open_with_names_notes_and_groups(
    read_service: TuningService, kind: str
) -> None:
    assert kind in TABLE_KINDS
    file = NEW_TABLES[kind]
    object_id = file.rsplit("/", 1)[-1].removesuffix(".yaml")
    summaries = read_service.objects(kind)
    assert [s.id for s in summaries] == [object_id]
    detail = object_detail(CONTENT, read_service.table, kind, object_id)
    assert detail.file == file
    assert detail.notes_zh
    data = read_data(CONTENT / file)
    assert detail.fields
    for field in detail.fields:
        assert field.value == lookup(data, parse_path(field.path)), field.path
        assert field.label_zh and "{" not in field.label_zh, field.path
        assert "越" in field.note_zh, field.path  # 調高、調低會怎樣
        assert field.group_zh, field.path


STRUCTURE: dict[str, tuple[str, ...]] = {
    "forms": (),
    "equipment": (),
    "item_gen": ("total_budget[", "max_attempts", "offer_attempts"),
}
"""三個檔裡不開的整數（HC-W2 報告的欄位表）：全身預算的等級是表的鍵；重試次數是程式的參數。
總減傷上限 HC-4b 起和核心規則的元素修正下限一起開。"""


@pytest.mark.parametrize("kind", sorted(NEW_TABLES))
def test_every_number_is_open_or_listed_as_structure(
    read_service: TuningService, kind: str
) -> None:
    file = NEW_TABLES[kind]
    object_id = file.rsplit("/", 1)[-1].removesuffix(".yaml")
    detail = object_detail(CONTENT, read_service.table, kind, object_id)
    opened = {f.path for f in detail.fields}
    closed: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")
        elif (
            isinstance(node, int)
            and not isinstance(node, bool)
            and path not in opened
            and (not path.startswith(STRUCTURE[kind]) or path.endswith(".total"))
        ):
            closed.append(path)

    walk(read_data(CONTENT / file), "")
    assert closed == []


def test_labels_name_the_form_the_element_and_the_level(read_service: TuningService) -> None:
    forms = object_detail(CONTENT, read_service.table, "forms", "forms")
    data = read_data(CONTENT / "forms.yaml")
    by_path = {f.path: f for f in forms.fields}
    for i, form in enumerate(data["forms"]):
        field = by_path[f"forms[{i}].natural_weapon.dice"]
        assert field.label_zh.startswith(f"形態「{form['name_zh']}」：")
        assert field.group_zh == f"形態「{form['name_zh']}」"
        for j, taken in enumerate((form.get("effects") or {}).get("damage_taken") or ()):
            label = by_path[f"forms[{i}].effects.damage_taken[{j}].permille"].label_zh
            assert "{element}" not in label
            if taken["element"] == "physical":
                assert "受到物理傷害" in label
    item_gen = object_detail(CONTENT, read_service.table, "item_gen", "item_gen")
    rows = read_data(CONTENT / "item_gen.yaml")["total_budget"]
    labels = {f.path: f.label_zh for f in item_gen.fields}
    for i, row in enumerate(rows):
        assert f"等級 {row['level']}" in labels[f"total_budget[{i}].total"]


_DRAFTS = {
    "forms": ("upkeep_mana", 5),
    "equipment": ("caps.move_bonus", 1),
    "item_gen": ("rarity_weights.common", 10),
}
"""每張新表各改一格（現值加這麼多）。"""


@pytest.mark.parametrize("kind", sorted(_DRAFTS))
def test_a_draft_of_each_new_table_saves_and_validates(
    read_service: TuningService, kind: str
) -> None:
    file = NEW_TABLES[kind]
    path, delta = _DRAFTS[kind]
    now = lookup(read_data(CONTENT / file), parse_path(path))
    assert isinstance(now, int)
    item = TuningChangeIn(file=file, path=path, old=now, new=now + delta)
    view = read_service.put_draft(f"hcw2-{kind}", [item])
    assert [(c.file, c.path, c.new) for c in view.changes] == [(file, path, now + delta)]
    result = read_service.check(f"hcw2-{kind}")
    assert result.ok, (result.field_errors, result.page_errors)
    change = Change(file=file, path=path, old=now, new=now + delta)
    prepared = prepare(CONTENT, read_service.table, [change])
    draft = load_library(read_service.workspace.draft(prepared.texts))
    loaded: dict[str, Any] = {
        "forms": draft.ruleset.forms,
        "equipment": draft.ruleset.equipment,
        "item_gen": draft.item_gen,
    }
    assert lookup(loaded[kind].model_dump(), parse_path(path)) == now + delta


def test_a_bad_draft_of_a_new_table_is_refused(read_service: TuningService) -> None:
    """schema 照擋：遞減權重第 1 條必須是 1000。"""
    file = NEW_TABLES["equipment"]
    now = read_data(CONTENT / file)["diminishing_permille"][0]
    item = TuningChangeIn(file=file, path="diminishing_permille[0]", old=now, new=now - 1)
    result = read_service.check("hcw2-bad", [item])
    assert not result.ok
