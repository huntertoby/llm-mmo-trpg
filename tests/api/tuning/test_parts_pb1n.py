"""PB-1n：數值工坊開放頭目部位（``parts[*]``）與 AI 部位評分（``ai_profiles.yaml`` 的 ``parts:``）。

- T-A1：每個新路徑對得到 schema、展開規則（只展開有部位的頭目、``on_break`` 只展開 ``stat_down``）。
- T-A2：YAML 字面替換（流式、沒寫的 ``armor_bonus`` 插入、註解保留）。
- 驗證：加總 601‰ 擋下、長劍降傷 1000 擋下、中文原因；改後能載入並跑一場小模擬（霧鎖真人）。
- 寫回（暫存 repo）：拂塵血量、AI ``parts.seal_skill`` 只差那一個值。

數值一律從 ``content/`` 讀現值（使用者在工坊寫回後這些測試不必收編）；只有「部位結構」
（三個部位、長劍第 1 個效果是 ``stat_down damage_dealt``）是寫死的。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.api.tuning.conftest import git
from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.objects import AI_NAME_ZH, concrete_fields, object_detail, read_data
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, lookup, patch_text
from trpg.content.loader import bundled_content_dir, parse_yaml
from trpg.content.tuning_fields import (
    TARGET_MODELS,
    load_tuning_fields,
    parse_path,
    path_matches,
    target_files,
)
from trpg.sim.boss_probe import boss_jobs, library_for, probe_battle

CONTENT = bundled_content_dir()
MIST = "units/sect_mist_lock_master.yaml"
AI = "ai_profiles.yaml"
WHISK_HP = "parts[0].hp_permille"
SWORD_AMOUNT = "parts[2].on_break[0].amount"
SEAL = "parts.seal_skill"

PART_PATTERNS = (
    "parts[*].hp_permille",
    "parts[*].armor_bonus",
    *(f"parts[*].resist.{g}" for g in ("physical", "elemental", "nature", "spirit")),
    *(
        f"parts[*].element_mods.{e}"
        for e in (
            "physical",
            "fire",
            "ice",
            "lightning",
            "poison",
            "wind",
            "earth",
            "holy",
            "shadow",
        )
    ),
    "parts[*].on_break[*].amount",
)
AI_PATHS = (
    "parts.seal_skill",
    "parts.interrupt_charge",
    "parts.stat_down",
    "parts.control",
    "parts.stop_mechanic",
    "parts.priority_bonus",
    "parts.guard_back_bonus",
    "parts.near_break_permille",
)


def _now(file: str, path: str) -> Any:
    """``content/`` 上的現值（沒寫＝``None``）。"""
    found = lookup(read_data(CONTENT / file), parse_path(path))
    return None if found is MISSING else found


def _in(path: str, old: Any, new: int | None, file: str = MIST) -> TuningChangeIn:
    return TuningChangeIn(file=file, path=path, old=old, new=new)


def _lower(value: int) -> int:
    """比現值小的另一個合法值（部位血量變小不會超過加總上限）。"""
    return value - 1 if value > 1 else value + 1


# ---------------------------------------------------------------------------
# T-A1：白名單
# ---------------------------------------------------------------------------


def test_part_and_ai_fields_are_whitelisted_with_hints_and_notes() -> None:
    table = load_tuning_fields(CONTENT)  # 載入檢查：每個路徑都對得到 schema 的整數欄位
    unit, ai = table.target("unit"), table.target("ai")
    assert unit is not None and ai is not None
    for pattern in PART_PATTERNS:
        field = unit.field_for(pattern.replace("*", "0"))
        assert field is not None and field.path == pattern, pattern
        assert field.note_zh and field.hint_min is not None and field.hint_max is not None
    hp = unit.field_for(WHISK_HP)
    assert hp is not None and (hp.kind, hp.hint_min, hp.hint_max) == ("permille", 50, 400)
    assert "600‰" in hp.note_zh
    amount = unit.field_for(SWORD_AMOUNT)
    assert amount is not None and "750" in amount.note_zh and amount.existing_only
    assert [f.path for f in ai.fields] == list(AI_PATHS)
    assert all(f.note_zh and f.hint_max is not None for f in ai.fields)
    assert TARGET_MODELS["ai"].__name__ == "AiProfileTable"
    assert [p.name for p in target_files(CONTENT, ai)] == [AI]


def test_mist_lock_expands_three_parts_and_only_the_stat_down_amount() -> None:
    table = load_tuning_fields(CONTENT)
    unit = table.target("unit")
    assert unit is not None
    data = read_data(CONTENT / MIST)
    got = {path: label for _f, path, label in concrete_fields(data, unit)}
    for i, name in enumerate(("拂塵", "氣海", "長劍")):
        assert got[f"parts[{i}].hp_permille"] == f"部位「{name}」血量（‰）"
        assert got[f"parts[{i}].armor_bonus"] == f"部位「{name}」護甲加值"
        assert f"parts[{i}].resist.physical" in got
        assert f"parts[{i}].element_mods.shadow" in got
    amounts = sorted(p for p in got if p.endswith(".amount"))
    assert amounts == [SWORD_AMOUNT]  # 封招、停機制、打斷蓄力沒有數量
    assert got[SWORD_AMOUNT] == "部位「長劍」破掉後第 1 個效果：之後造成傷害的倍率（‰；750＝−25%）"
    for _f, path, _l in concrete_fields(data, unit):  # 每個具體路徑都對得到白名單
        assert unit.field_for(path) is not None and parse_path(path)


def test_units_without_parts_get_no_part_fields() -> None:
    table = load_tuning_fields(CONTENT)
    unit = table.target("unit")
    assert unit is not None
    data = read_data(CONTENT / "units/ashen_heart.yaml")
    assert "parts" not in data
    assert not [p for _f, p, _l in concrete_fields(data, unit) if p.startswith("parts")]


def test_detail_shows_defaults_limits_and_ai_object(read_service: TuningService) -> None:
    detail = read_service.object("unit", "sect_mist_lock_master")
    rows = {f.path: f for f in detail.fields}
    whisk = rows[WHISK_HP]
    assert (whisk.value, whisk.limit_min, whisk.limit_max) == (_now(MIST, WHISK_HP), 1, 1000)
    armor = rows["parts[0].armor_bonus"]
    if armor.value is None:
        assert armor.default_zh == "沒寫＝和本體相同"
    sword = rows[SWORD_AMOUNT]
    assert (sword.value, sword.limit_min, sword.limit_max) == (_now(MIST, SWORD_AMOUNT), 1, 999)
    objects = [o for o in read_service.objects() if o.kind == "ai"]
    assert [(o.id, o.category, o.name_zh, o.file) for o in objects] == [
        ("ai_profiles", "ai", AI_NAME_ZH, AI)
    ]
    ai = object_detail(CONTENT, read_service.table, "ai", "ai_profiles")
    assert [f.path for f in ai.fields] == list(AI_PATHS)
    assert [f.value for f in ai.fields] == [_now(AI, p) for p in AI_PATHS]
    near = ai.fields[-1]
    assert (near.kind, near.limit_min, near.limit_max) == ("permille", 0, 1000)
    assert ai.category == "ai" and any("全體共用" in n for n in ai.notes_zh)


# ---------------------------------------------------------------------------
# T-A2：YAML 字面替換
# ---------------------------------------------------------------------------


def _changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    old, new = before.splitlines(), after.splitlines()
    assert len(old) == len(new)
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


def test_patch_flow_part_value_changes_only_that_number() -> None:
    text = (CONTENT / MIST).read_bytes().decode("utf-8")
    old = _now(MIST, WHISK_HP)
    new = patch_text(text, [(parse_path(WHISK_HP), _lower(old))])
    [(was, now)] = _changed_lines(text, new)
    assert was.startswith("  - {id: whisk, name_zh: 拂塵,")  # 流式部位
    assert now == was.replace(f"hp_permille: {old}", f"hp_permille: {_lower(old)}")


def test_patch_flow_effect_amount_inside_block_part() -> None:
    text = (CONTENT / MIST).read_bytes().decode("utf-8")
    old = _now(MIST, SWORD_AMOUNT)
    new = patch_text(text, [(parse_path(SWORD_AMOUNT), _lower(old))])
    [(was, now)] = _changed_lines(text, new)
    assert was.startswith("    on_break: [{type: stat_down, stat: damage_dealt, amount:")
    assert now == was.replace(f"amount: {old}", f"amount: {_lower(old)}")


SAMPLE = """\
# 部位（測試用；同霧鎖真人的寫法：流式一項＋區塊式兩項）
parts:
  - {id: whisk, name_zh: 拂塵, hp_permille: 200, reach: any, on_break: [{type: seal_skill, skill: skill_mist_shift}]}
  - id: dantian
    name_zh: 氣海
    hp_permille: 200
    reach: behind   # 背後近戰
    on_break: [{type: stop_mechanic, status: mist_return}]
  - id: sword
    name_zh: 長劍
    hp_permille: 200
    on_break: [{type: stat_down, stat: damage_dealt, amount: 750}, {type: interrupt_charge}]
# 檔尾註解
"""  # noqa: E501


def test_patch_inserts_missing_part_armor_and_resist_keeping_comments() -> None:
    edits = [
        (("parts", 0, "armor_bonus"), 5),  # 流式：插 , armor_bonus: 5
        (("parts", 2, "armor_bonus"), 1),  # 區塊式：插一行
        (("parts", 2, "resist", "physical"), 250),  # 整個 resist 沒寫：插 resist: {physical: 250}
    ]
    new = patch_text(SAMPLE, edits)
    expected = parse_yaml(SAMPLE)
    expected["parts"][0]["armor_bonus"] = 5
    expected["parts"][2]["armor_bonus"] = 1
    expected["parts"][2]["resist"] = {"physical": 250}
    assert parse_yaml(new) == expected
    lines = new.splitlines()
    assert lines[2].endswith("skill: skill_mist_shift}], armor_bonus: 5}")
    assert "    armor_bonus: 1" in lines and "    resist: {physical: 250}" in lines
    for line in SAMPLE.splitlines():
        if "#" in line:
            assert line in lines  # 註解一行都沒少
    assert len(lines) == len(SAMPLE.splitlines()) + 2  # 區塊式兩行（armor、resist）
    armor = edits[:2]
    assert patch_text(patch_text(SAMPLE, armor), [(p, None) for p, _v in armor]) == SAMPLE


def test_patch_ai_parts_value_keeps_the_rest_of_the_file() -> None:
    text = (CONTENT / AI).read_bytes().decode("utf-8")
    old = _now(AI, SEAL)
    new = patch_text(text, [(parse_path(SEAL), old + 4)])
    [(was, changed)] = _changed_lines(text, new)
    assert was.startswith(f"parts: {{seal_skill: {old},")
    assert changed == was.replace(f"seal_skill: {old},", f"seal_skill: {old + 4},")


# ---------------------------------------------------------------------------
# 驗證與小模擬
# ---------------------------------------------------------------------------


def test_part_hp_total_over_600_is_refused_in_chinese(read_service: TuningService) -> None:
    paths = [f"parts[{i}].hp_permille" for i in range(3)]
    result = read_service.check(
        "current", [_in(p, _now(MIST, p), v) for p, v in zip(paths, (250, 250, 101), strict=True)]
    )
    assert not result.ok
    messages = {e.path: e.message_zh for e in result.field_errors}
    assert set(messages) == set(paths)
    assert all("加總不能超過 600‰（收到 601‰）" in m for m in messages.values())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (_in(SWORD_AMOUNT, _now(MIST, SWORD_AMOUNT), 1000), "要小於 1000"),
        (_in(SWORD_AMOUNT, _now(MIST, SWORD_AMOUNT), 0), "不能小於 1"),
        (_in(WHISK_HP, _now(MIST, WHISK_HP), 0), "不能小於 1"),
        (
            _in("parts[0].resist.physical", _now(MIST, "parts[0].resist.physical"), 1200),
            "-1000–1000",
        ),
        (_in("parts[0].on_break[0].amount", None, 5), "不開放"),  # 封招沒有數量
        (
            _in("parts.near_break_permille", _now(AI, "parts.near_break_permille"), 1001, AI),
            "不能大於 1000",
        ),
        (_in(SEAL, _now(AI, SEAL), -1, file=AI), "不能小於 0"),
        (_in(SEAL, _now(AI, SEAL) + 1, 10, file=AI), f"已經被改過（現在是 {_now(AI, SEAL)}）"),
    ],
)
def test_illegal_part_values_are_refused(
    read_service: TuningService, change: TuningChangeIn, message: str
) -> None:
    result = read_service.check("current", [change])
    assert not result.ok
    assert [(e.file, e.path) for e in result.field_errors] == [(change.file, change.path)]
    assert message in result.field_errors[0].message_zh


def test_part_and_ai_changes_validate_and_run_a_smoke_battle(
    read_service: TuningService,
) -> None:
    sword, whisk, seal = _now(MIST, SWORD_AMOUNT), _now(MIST, WHISK_HP), _now(AI, SEAL)
    armor = _now(MIST, "parts[1].armor_bonus")
    new_sword = 500 if sword != 500 else 600
    changes = (
        Change(file=MIST, path=SWORD_AMOUNT, old=sword, new=new_sword),
        Change(file=MIST, path=WHISK_HP, old=whisk, new=_lower(whisk)),
        Change(file=MIST, path="parts[1].armor_bonus", old=armor, new=(armor or 0) + 2),
        Change(file=AI, path=SEAL, old=seal, new=seal + 4),
    )
    read_service.drafts.put(Draft(name="pb1n", changes=changes))
    result = read_service.check("pb1n")
    assert result.ok, (result.field_errors, result.page_errors)
    _prepared, _digest, _before, after_root = read_service._sim_roots("pb1n")
    library = library_for(str(after_root))
    mist = library.unit("sect_mist_lock_master")
    assert mist.parts[0].hp_permille == _lower(whisk)
    assert mist.parts[1].armor_bonus == (armor or 0) + 2
    assert library.ai_profiles.parts.seal_skill == seal + 4
    job = boss_jobs(library, "mist", seeds=1)[0]
    battle = probe_battle(library, job)  # 冒煙：改後的內容打得完一場
    assert battle.boss == "mist" and battle.rounds > 0


# ---------------------------------------------------------------------------
# 寫回（暫存 repo；絕不碰真的 content/）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("file", "path", "new"),
    [
        (MIST, WHISK_HP, _lower(_now(MIST, WHISK_HP))),
        (AI, SEAL, _now(AI, SEAL) + 4),
    ],
    ids=["whisk", "ai"],
)
def test_writeback_changes_only_that_literal(
    repo: Path, repo_service: TuningService, file: str, path: str, new: int
) -> None:
    target = repo_service.content_dir / file
    before = target.read_bytes().decode("utf-8")
    old = _now(file, path)
    repo_service.drafts.put(
        Draft(name="current", changes=(Change(file=file, path=path, old=old, new=new),))
    )
    done = repo_service.apply("current")
    assert done.files == [file]
    shown = git(repo, "show", "--name-only", "--format=%B", "HEAD")
    assert shown.splitlines()[0] == f"tune({Path(file).stem}): {path} {old}→{new}"
    assert shown.rstrip().splitlines()[-1] == f"content/{file}"
    after = target.read_bytes().decode("utf-8")
    [(was, now)] = _changed_lines(before, after)
    leaf = path.rsplit(".", 1)[-1]
    assert now == was.replace(f"{leaf}: {old}", f"{leaf}: {new}")
    assert b"\r\n" not in target.read_bytes()
    names = git(repo, "diff", "--name-only", "HEAD~1", "HEAD").split()
    assert names == [f"content/{file}"]


def test_patterns_match_concrete_paths() -> None:
    assert path_matches("parts[*].on_break[*].amount", "parts[2].on_break[0].amount")
    assert not path_matches("parts[*].on_break[*].amount", "parts[2].on_break.amount")
