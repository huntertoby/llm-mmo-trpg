"""NW-3：數值工坊白名單加 GB-3 的三個 AI 權重與格子物件的 ``max_hp``。

- AI 估值表（``ai_profiles.yaml``）：``parts.guard_face_bonus``、``parts.giant_spot_bonus``
  （表格層級，填入每個行為模式）；``profiles[*].weights.prefer_far_from_leader``（``existing_only``：只展開已寫的
  模式，目前只有 ``ember_brood``）。GB-3 報告待決 3。
- 格子物件（``objects.yaml``，新的表格對象 ``object``）：``objects[*].max_hp``（``existing_only``；
  沒寫的物件打不破，不展開）。CW-1 報告待決 5。
- 改後的內容：戰鬥吃到新值（AI 權重進每個模式；熔心坑開場的冷卻井 HP）；寫回只動那一個數字。

數值一律讀 ``content/`` 的現值（使用者寫回後不必收編）；只寫死欄位路徑、物件與模式 ID。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.api.tuning.conftest import git
from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.objects import TABLE_NAMES_ZH, concrete_fields, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, lookup, patch_text
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import TARGET_MODELS, load_tuning_fields, parse_path, target_files
from trpg.engine.battle import begin_battle
from trpg.engine.setup import build_setup
from trpg.sim.boss_probe import library_for
from trpg.sim.lineup import default_lineup

CONTENT = bundled_content_dir()
AI = "ai_profiles.yaml"
OBJECTS = "objects.yaml"
FACE = "parts.guard_face_bonus"
SPOT = "parts.giant_spot_bonus"
FAR = "profiles[*].weights.prefer_far_from_leader"
MAX_HP = "objects[*].max_hp"
PIT = "molten_heart_pit"


def _index(file: str, key: str, item_id: str) -> int:
    items = read_data(CONTENT / file)[key]
    return next(i for i, item in enumerate(items) if item["id"] == item_id)


BROOD_FAR = f"profiles[{_index(AI, 'profiles', 'ember_brood')}].weights.prefer_far_from_leader"
WELL_HP = f"objects[{_index(OBJECTS, 'objects', 'cooling_well')}].max_hp"


def _now(file: str, path: str) -> Any:
    found = lookup(read_data(CONTENT / file), parse_path(path))
    return None if found is MISSING else found


@pytest.fixture
def read_service(tmp_path: Path, content_library: ContentLibrary) -> TuningService:
    """讀專案內建 ``content/`` 的服務（**不寫回**；寫回測試用 ``repo_service``）。"""
    service = TuningService(bundled_content_dir(), tmp_path / "saves", content_library)
    service.git = None
    return service


# ---------------------------------------------------------------------------
# 白名單與展開
# ---------------------------------------------------------------------------


def test_the_new_fields_are_whitelisted() -> None:
    table = load_tuning_fields(CONTENT)  # 載入檢查：每個路徑都對得到 schema 的整數欄位
    ai, obj = table.target("ai"), table.target("object")
    assert ai is not None and obj is not None
    for pattern in (FACE, SPOT, FAR):
        field = ai.field_for(pattern.replace("*", "0"))
        assert field is not None and field.path == pattern, pattern
        assert field.kind == "int" and field.note_zh
        assert field.hint_min is not None and field.hint_max is not None
    far = ai.field_for(BROOD_FAR)
    assert far is not None and far.existing_only
    assert [f.path for f in obj.fields] == [MAX_HP]
    assert obj.fields[0].existing_only and obj.fields[0].hint_min == 1
    assert TARGET_MODELS["object"].__name__ == "ObjectTable"
    assert [p.name for p in target_files(CONTENT, obj)] == [OBJECTS]


def test_only_profiles_that_write_the_weight_expand_it() -> None:
    ai = load_tuning_fields(CONTENT).target("ai")
    assert ai is not None
    data = read_data(CONTENT / AI)
    got = {path: label for _f, path, label in concrete_fields(data, ai)}
    far = sorted(p for p in got if p.endswith("prefer_far_from_leader"))
    written = sorted(
        f"profiles[{i}].weights.prefer_far_from_leader"
        for i, p in enumerate(data["profiles"])
        if "prefer_far_from_leader" in p["weights"]
    )
    assert far == written and BROOD_FAR in far
    assert got[BROOD_FAR] == "行為模式「殼縫蟲群」：追離頭目遠的人"
    assert got[FACE] == "巨型頭目護面的加分"


def test_only_objects_with_max_hp_expand_and_are_labelled_by_name() -> None:
    obj = load_tuning_fields(CONTENT).target("object")
    assert obj is not None
    data = read_data(CONTENT / OBJECTS)
    got = {path: label for _f, path, label in concrete_fields(data, obj)}
    want = {
        f"objects[{i}].max_hp": f"物件「{o['name_zh']}」最大 HP"
        for i, o in enumerate(data["objects"])
        if o.get("max_hp") is not None
    }
    assert got == want
    assert got[WELL_HP] == "物件「冷卻井」最大 HP"
    grass = _index(OBJECTS, "objects", "grass")  # 沒寫 max_hp（打不破）：不展開
    assert f"objects[{grass}].max_hp" not in got


def test_list_and_detail_show_the_object_table(read_service: TuningService) -> None:
    found = [o for o in read_service.objects() if o.kind == "object"]
    assert [(o.id, o.category, o.name_zh, o.file) for o in found] == [
        ("objects", "object", TABLE_NAMES_ZH["object"], OBJECTS)
    ]
    detail = object_detail(CONTENT, read_service.table, "object", "objects")
    assert detail.category == "object" and any("全體共用" in n for n in detail.notes_zh)
    rows = {f.path: f for f in detail.fields}
    well = rows[WELL_HP]
    assert (well.value, well.limit_min, well.limit_max) == (_now(OBJECTS, WELL_HP), 1, None)
    ai = object_detail(CONTENT, read_service.table, "ai", "ai_profiles")
    values = {f.path: (f.value, f.limit_min) for f in ai.fields}
    assert values[FACE] == (_now(AI, FACE), 0)
    assert values[SPOT] == (_now(AI, SPOT), 0)
    assert values[BROOD_FAR] == (_now(AI, BROOD_FAR), None)
    assert any("殼縫蟲群" in n for n in ai.notes_zh)


# ---------------------------------------------------------------------------
# YAML 字面替換
# ---------------------------------------------------------------------------


def _changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    old, new = before.splitlines(), after.splitlines()
    assert len(old) == len(new)
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


@pytest.mark.parametrize(
    ("file", "path"),
    [(AI, FACE), (AI, SPOT), (AI, BROOD_FAR), (OBJECTS, WELL_HP)],
    ids=["face", "spot", "far", "well"],
)
def test_patch_changes_only_that_number(file: str, path: str) -> None:
    text = (CONTENT / file).read_bytes().decode("utf-8")
    old = _now(file, path)
    new = patch_text(text, [(parse_path(path), old + 2)])
    [(was, changed)] = _changed_lines(text, new)
    leaf = path.rsplit(".", 1)[-1]
    assert changed == was.replace(f"{leaf}: {old}", f"{leaf}: {old + 2}", 1)


# ---------------------------------------------------------------------------
# 驗證、戰鬥吃到新值
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            TuningChangeIn(file=OBJECTS, path=WELL_HP, old=_now(OBJECTS, WELL_HP), new=0),
            "不能小於 1",
        ),
        (
            TuningChangeIn(
                file=OBJECTS,
                path=f"objects[{_index(OBJECTS, 'objects', 'grass')}].max_hp",
                old=None,
                new=5,
            ),
            "不開放",
        ),
        (TuningChangeIn(file=AI, path=FACE, old=_now(AI, FACE), new=-1), "不能小於 0"),
        (
            TuningChangeIn(
                file=AI,
                path=f"profiles[{_index(AI, 'profiles', 'brute')}].weights.prefer_far_from_leader",
                old=None,
                new=3,
            ),
            "不開放",
        ),
    ],
    ids=["well-0", "grass", "face-negative", "brute-far"],
)
def test_illegal_values_are_refused(
    read_service: TuningService, change: TuningChangeIn, message: str
) -> None:
    result = read_service.check("current", [change])
    assert not result.ok
    assert [(e.file, e.path) for e in result.field_errors] == [(change.file, change.path)]
    assert message in result.field_errors[0].message_zh


def _well_hps(library: ContentLibrary) -> list[tuple[int | None, int | None]]:
    allies, enemies = default_lineup(library, PIT)
    state = begin_battle(build_setup(library, PIT, allies, enemies, max_rounds=30), 0).state
    return [(o.hp, o.max_hp) for o in state.objects.values() if o.kind == "cooling_well"]


def test_changed_values_reach_the_battle(
    read_service: TuningService, content_library: ContentLibrary
) -> None:
    face, spot, far, well = (
        _now(AI, FACE),
        _now(AI, SPOT),
        _now(AI, BROOD_FAR),
        _now(OBJECTS, WELL_HP),
    )
    changes = (
        Change(file=AI, path=FACE, old=face, new=face + 1),
        Change(file=AI, path=SPOT, old=spot, new=spot + 1),
        Change(file=AI, path=BROOD_FAR, old=far, new=far + 1),
        Change(file=OBJECTS, path=WELL_HP, old=well, new=well + 5),
    )
    read_service.drafts.put(Draft(name="nw3", changes=changes))
    result = read_service.check("nw3")
    assert result.ok, (result.field_errors, result.page_errors)
    _prepared, _digest, _before, after_root = read_service._sim_roots("nw3")
    library = library_for(str(after_root))
    profiles = library.ai_profiles.by_id()
    pairs = {(p.weights.guard_face_bonus, p.weights.giant_spot_bonus) for p in profiles.values()}
    assert pairs == {(face + 1, spot + 1)}  # 表格層級的 parts: 填入每個行為模式
    assert profiles["ember_brood"].weights.prefer_far_from_leader == far + 1
    assert profiles["brute"].weights.prefer_far_from_leader == 0
    assert library.ruleset.object_def("cooling_well").max_hp == well + 5
    before = _well_hps(content_library)
    after = _well_hps(library)
    assert len(after) == len(before) == 4
    assert set(before) == {(well, well)} and set(after) == {(well + 5, well + 5)}


# ---------------------------------------------------------------------------
# 寫回（暫存 repo；絕不碰真的 content/）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("file", "path"), [(AI, BROOD_FAR), (OBJECTS, WELL_HP)], ids=["far", "well"]
)
def test_writeback_changes_only_that_literal(
    repo: Path, repo_service: TuningService, file: str, path: str
) -> None:
    target = repo_service.content_dir / file
    before = target.read_bytes().decode("utf-8")
    old = _now(file, path)
    new = old + 1
    repo_service.drafts.put(
        Draft(name="current", changes=(Change(file=file, path=path, old=old, new=new),))
    )
    done = repo_service.apply("current")
    assert done.files == [file]
    shown = git(repo, "show", "--name-only", "--format=%B", "HEAD")
    assert shown.splitlines()[0] == f"tune({Path(file).stem}): {path} {old}→{new}"
    after = target.read_bytes().decode("utf-8")
    [(was, now)] = _changed_lines(before, after)
    leaf = path.rsplit(".", 1)[-1]
    assert now == was.replace(f"{leaf}: {old}", f"{leaf}: {new}", 1)
    assert b"\r\n" not in target.read_bytes()
    assert git(repo, "diff", "--name-only", "HEAD~1", "HEAD").split() == [f"content/{file}"]
