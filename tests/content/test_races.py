"""可玩種族與出身（Phase 3R-1）：資料、防最佳解驗證（故意寫壞的資料必須載入失敗並給中文原因）。"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from trpg.cli.main import main
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.races import (
    MAX_RACE_EFFECTS,
    PASSIVE_RULE_SPECS,
    RACE_EFFECT_SPECS,
    OriginTable,
    RaceTable,
    forbidden_key_problems,
)
from trpg.shared.errors import ContentError


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


_RACE_IDS = {
    "human",
    "elf",
    "fox",
    "dragonkin",
    "dwarf",
    "cyborg",
    "orc",
    "fiend",
    "scalefolk",
    "seafolk",
}
_REALMS = {"crystal_crown", "cloud_ridge", "arcane_hub", "ashen_waste", "frost_tide"}


def _raw_races() -> dict[str, Any]:
    text = (default_content_dir() / "races.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)  # type: ignore[no-any-return]


def _load_bad(tmp_path: Path, data: dict[str, Any], model: type[Any] = RaceTable) -> str:
    """寫成暫存檔載入，必須失敗；回傳錯誤訊息。"""
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError) as info:
        load_content_file(path, model)
    return str(info.value)


def _first(data: dict[str, Any]) -> dict[str, Any]:
    return data["races"][0]  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# 內建資料
# ---------------------------------------------------------------------------


def test_bundled_races_load(library: ContentLibrary) -> None:
    assert library.races is not None
    assert set(library.races.by_id()) == _RACE_IDS


def test_each_race_has_one_skill_and_one_passive_with_rules(library: ContentLibrary) -> None:
    assert library.races is not None
    for race in library.races.races:
        skill = race.skill
        assert skill.ap_cost == 1, race.id
        assert 1 <= skill.uses_per_battle <= 2, race.id
        assert skill.occupies_skill_slot is False, race.id
        assert 1 <= len(skill.effects) <= MAX_RACE_EFFECTS, race.id
        assert race.passive.rule in PASSIVE_RULE_SPECS, race.id
        assert all(e.type in RACE_EFFECT_SPECS for e in skill.effects), race.id


def test_two_races_per_realm(library: ContentLibrary) -> None:
    assert library.races is not None
    counts: dict[str, int] = {}
    for race in library.races.races:
        counts[race.home_realm] = counts.get(race.home_realm, 0) + 1
    assert counts == dict.fromkeys(_REALMS, 2)


def test_bundled_origins_cover_five_realms(library: ContentLibrary) -> None:
    assert library.origins is not None
    assert {o.realm for o in library.origins.origins} == _REALMS
    for origin in library.origins.origins:
        assert origin.npc_attitude[origin.realm] == "friendly"


def test_table_values_match_design_7_7(library: ContentLibrary) -> None:
    """抽查 7.7 表的數字：次數、距離、減免。"""
    assert library.races is not None
    races = library.races.by_id()
    uses = {r: races[r].skill.uses_per_battle for r in races}
    assert uses == {
        "human": 1,
        "elf": 2,
        "fox": 1,
        "dragonkin": 1,
        "dwarf": 1,
        "cyborg": 1,
        "orc": 2,
        "fiend": 2,
        "scalefolk": 1,
        "seafolk": 1,
    }
    assert races["dragonkin"].passive.permille == -200
    assert races["seafolk"].skill.effects[0].distance == 2
    assert races["seafolk"].skill.shape.range == 4
    assert races["cyborg"].skill.effects[0].amount == 10


def test_no_bundled_race_data_contains_forbidden_keys() -> None:
    assert forbidden_key_problems(_raw_races(), "races") == []


def test_content_check_cli_lists_races_and_origins(capsys: pytest.CaptureFixture[str]) -> None:

    assert main(["content", "check"]) == 0
    out = capsys.readouterr().out
    assert "races.yaml" in out
    assert "origins.yaml" in out


# ---------------------------------------------------------------------------
# 防最佳解：故意寫壞，必須載入失敗並給中文原因
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("where", "key", "value", "kind"),
    [
        ("skill", "damage", {"dice": "1d6"}, "傷害"),
        ("skill", "dice", "1d6", "傷害"),
        ("skill", "hit_bonus", 2, "命中"),
        ("skill", "crit_range", 1, "暴擊"),
        ("skill", "max_hp_permille", 100, "最大 HP"),
        ("skill", "grant_ap", 1, "AP"),
        ("skill", "attrs", {"str": 1}, "屬性"),
        ("passive", "damage_permille", 100, "傷害"),
        ("passive", "accuracy", 5, "命中"),
        ("passive", "crit", 5, "暴擊"),
        ("passive", "max_hp", 10, "最大 HP"),
        ("passive", "ap_bonus", 1, "AP"),
        ("passive", "dex", 1, "屬性"),
        ("race", "stats", {"con": 2}, "屬性"),
    ],
)
def test_pure_numbers_are_rejected(
    tmp_path: Path, where: str, key: str, value: object, kind: str
) -> None:
    data = _raw_races()
    target = _first(data) if where == "race" else _first(data)[where]
    target[key] = value
    message = _load_bad(tmp_path, data)
    assert "種族不得給" + kind in message
    assert "防最佳解原則 1" in message


def test_damage_in_effect_params_is_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    _first(data)["skill"]["effects"][0]["dice"] = "1d6"
    assert "種族不得給傷害" in _load_bad(tmp_path, data)


@pytest.mark.parametrize(
    ("effect_type", "kind"),
    [("damage", "傷害"), ("delayed_damage", "傷害"), ("grant_ap", "AP"), ("heal", "最大 HP")],
)
def test_damaging_effect_types_are_rejected(tmp_path: Path, effect_type: str, kind: str) -> None:
    data = _raw_races()
    _first(data)["skill"]["effects"] = [{"type": effect_type}]
    message = _load_bad(tmp_path, data)
    assert f"會給{kind}" in message


def test_unknown_effect_type_is_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    _first(data)["skill"]["effects"] = [{"type": "teleport"}]
    assert "effects.0.type" in _load_bad(tmp_path, data)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("ap_cost", 2, "必須固定花 1 AP"),
        ("ap_cost", 0, "必須固定花 1 AP"),
        ("uses_per_battle", 3, "每場限用 1～2 次"),
        ("uses_per_battle", 0, "每場限用 1～2 次"),
        ("occupies_skill_slot", True, "不佔技能欄"),
    ],
)
def test_skill_budget_rules(tmp_path: Path, field: str, value: object, reason: str) -> None:
    data = _raw_races()
    _first(data)["skill"][field] = value
    assert reason in _load_bad(tmp_path, data)


def test_too_many_effects_are_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    effect = {"type": "bonus_move", "amount": 1}
    _first(data)["skill"]["effects"] = [dict(effect) for _ in range(MAX_RACE_EFFECTS + 1)]
    assert "最多 3 個效果" in _load_bad(tmp_path, data)


def test_push_must_declare_no_collision_damage(tmp_path: Path) -> None:
    data = _raw_races()
    races = {r["id"]: r for r in data["races"]}
    del races["dragonkin"]["skill"]["effects"][0]["no_collision_damage"]
    assert "no_collision_damage 必須明寫為 true" in _load_bad(tmp_path, data)


def test_effect_with_foreign_parameter_is_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    _first(data)["skill"]["effects"][0]["surface"] = "fire"
    assert "不可使用參數 surface" in _load_bad(tmp_path, data)


def test_effect_missing_required_parameter_is_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    del _first(data)["skill"]["effects"][0]["amount"]
    assert "缺少必填參數 amount" in _load_bad(tmp_path, data)


def test_unknown_passive_rule_is_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    _first(data)["passive"]["rule"] = "extra_strength"
    message = _load_bad(tmp_path, data)
    assert "不在允許清單內" in message


def test_passive_resist_is_capped(tmp_path: Path) -> None:
    data = _raw_races()
    races = {r["id"]: r for r in data["races"]}
    races["dragonkin"]["passive"]["permille"] = -900
    assert "幅度有上限" in _load_bad(tmp_path, data)


def test_passive_cannot_boost_damage_taken_up(tmp_path: Path) -> None:
    data = _raw_races()
    races = {r["id"]: r for r in data["races"]}
    races["dragonkin"]["passive"]["permille"] = 200
    assert "只能減傷" in _load_bad(tmp_path, data)


def test_sight_reduction_capped_at_half(tmp_path: Path) -> None:
    data = _raw_races()
    _first(data)["passive"]["permille"] = 900
    assert "最多減半" in _load_bad(tmp_path, data)


def test_duplicate_race_ids_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    data["races"].append(copy.deepcopy(data["races"][0]))
    assert "ID 重複" in _load_bad(tmp_path, data)


def test_unknown_field_is_rejected(tmp_path: Path) -> None:
    data = _raw_races()
    _first(data)["bonus"] = 1
    assert _load_bad(tmp_path, data)


# ---------------------------------------------------------------------------
# 出身：不影響戰鬥
# ---------------------------------------------------------------------------


def _raw_origins() -> dict[str, Any]:
    text = (default_content_dir() / "origins.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)  # type: ignore[no-any-return]


@pytest.mark.parametrize("key", ["max_hp", "damage", "hit_bonus", "crit", "ap_bonus", "attrs"])
def test_origin_cannot_carry_combat_numbers(tmp_path: Path, key: str) -> None:
    data = _raw_origins()
    data["origins"][0][key] = 1
    assert "種族不得給" in _load_bad(tmp_path, data, OriginTable)


def test_origin_extra_unknown_field_rejected(tmp_path: Path) -> None:
    data = _raw_origins()
    data["origins"][0]["combat_bonus"] = 1
    assert _load_bad(tmp_path, data, OriginTable)


def test_duplicate_realm_origins_rejected(tmp_path: Path) -> None:
    data = _raw_origins()
    data["origins"][1]["realm"] = data["origins"][0]["realm"]
    assert "每個界域只能有一個出身" in _load_bad(tmp_path, data, OriginTable)


# ---------------------------------------------------------------------------
# 跨檔案檢查（library）
# ---------------------------------------------------------------------------


def _copy_content(tmp_path: Path) -> Path:

    dest = tmp_path / "content"
    shutil.copytree(default_content_dir(), dest)
    return dest


def test_library_rejects_unknown_realm(tmp_path: Path) -> None:

    root = _copy_content(tmp_path)
    path = root / "races.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("home_realm: cloud_ridge", "home_realm: nowhere", 1), "utf-8")
    with pytest.raises(ContentError) as info:
        load_library(root)
    assert "未知的界域 nowhere" in str(info.value)


def test_library_rejects_unknown_shape(tmp_path: Path) -> None:

    root = _copy_content(tmp_path)
    path = root / "races.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("shape: {type: self}", "shape: {type: nope}", 1),
        "utf-8",
    )
    with pytest.raises(ContentError) as info:
        load_library(root)
    assert "未知的形狀 nope" in str(info.value)


def test_library_requires_origin_for_every_realm(tmp_path: Path) -> None:

    root = _copy_content(tmp_path)
    data = _raw_origins()
    data["origins"] = data["origins"][:-1]
    (root / "origins.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError) as info:
        load_library(root)
    assert "沒有出身" in str(info.value)


def _fox_decoy(data: dict[str, Any]) -> dict[str, Any]:
    fox = next(r for r in data["races"] if r["id"] == "fox")
    return fox["skill"]["effects"][0]  # type: ignore[no-any-return]


def test_decoy_template_lifetime_and_ai_range_come_from_the_yaml() -> None:
    effect = _fox_decoy(_raw_races())
    assert effect["summon"] == "summon_foxfire_decoy"
    assert effect["lifetime"] == 3 and effect["ai_trigger_range"] == 7


@pytest.mark.parametrize("missing", ["summon", "lifetime", "ai_trigger_range"])
def test_decoy_requires_its_parameters(tmp_path: Path, missing: str) -> None:
    data = _raw_races()
    del _fox_decoy(data)[missing]
    assert f"缺少必填參數 {missing}" in _load_bad(tmp_path, data)


def test_decoy_with_unknown_summon_template_is_rejected(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    data = _raw_races()
    _fox_decoy(data)["summon"] = "summon_nowhere"
    (root / "races.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError) as info:
        load_library(root)
    assert "未知的召喚物範本 summon_nowhere" in str(info.value)
