"""NW-1a T-A2：YAML 字面替換 :mod:`trpg.api.tuning.yaml_patch`（只改那一個值、其他位元組不動）。"""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup, patch_text
from trpg.content.loader import bundled_content_dir, parse_yaml
from trpg.content.tuning_fields import (
    PathPart,
    load_tuning_fields,
    parse_path,
    target_files,
)

CONTENT = bundled_content_dir()


def _concrete_cases() -> list[tuple[str, tuple[PathPart, ...]]]:
    """每個單位檔 × 每個白名單欄位（``phases[*]`` 展開成有 HP 門檻的階段）。"""
    table = load_tuning_fields(CONTENT)
    unit = table.target("unit")
    assert unit is not None
    cases: list[tuple[str, tuple[PathPart, ...]]] = []
    for path in target_files(CONTENT, unit):
        data = parse_yaml(path.read_text(encoding="utf-8"))
        rel = path.relative_to(CONTENT).as_posix()
        for field in unit.fields:
            parts = parse_path(field.path)
            if "*" not in parts:
                cases.append((rel, parts))
                continue
            for i, phase in enumerate(data.get("phases") or ()):
                if (phase.get("trigger") or {}).get("kind") == "hp_below":
                    cases.append((rel, tuple(i if p == "*" else p for p in parts)))
    return cases


CASES = _concrete_cases()
TEXTS = {rel: (CONTENT / rel).read_bytes().decode("utf-8") for rel, _ in CASES}


def _set(data: dict[str, object], parts: tuple[PathPart, ...], value: int) -> None:
    node: object = data
    for part in parts[:-1]:
        if isinstance(part, int):
            assert isinstance(node, list)
            node = node[part]
        else:
            assert isinstance(node, dict)
            node = node.setdefault(part, {})
    assert isinstance(node, dict)
    node[parts[-1]] = value


def test_cases_cover_every_unit_and_the_phase_thresholds() -> None:
    assert len({rel for rel, _ in CASES}) > 50
    assert ("units/ashen_heart.yaml", ("phases", 1, "trigger", "permille")) in CASES
    assert ("units/ashen_heart.yaml", ("max_hp",)) in CASES


@settings(max_examples=300, deadline=None)
@given(case=st.sampled_from(CASES), value=st.integers(min_value=-5000, max_value=5000))
def test_patch_changes_only_that_value(case: tuple[str, tuple[PathPart, ...]], value: int) -> None:
    rel, parts = case
    text = TEXTS[rel]
    before = parse_yaml(text)
    existed = lookup(before, parts) is not MISSING
    new = patch_text(text, [(parts, value)])
    expected = parse_yaml(text)
    _set(expected, parts, value)
    assert parse_yaml(new) == expected
    if lookup(before, parts) == value:  # 本來就是這個值：一個位元組都不動
        assert new == text
        return
    old_lines, new_lines = text.splitlines(keepends=True), new.splitlines(keepends=True)
    removed = [x for x in difflib.ndiff(old_lines, new_lines) if x.startswith("- ")]
    added = [x for x in difflib.ndiff(old_lines, new_lines) if x.startswith("+ ")]
    assert len(added) == 1  # 只動到一行（改值或流式插入是改那一行；區塊式插入是多一行）
    assert len(removed) == (1 if existed or len(new_lines) == len(old_lines) else 0)
    for line in old_lines:  # 註解一行都沒少
        if line.lstrip().startswith("#"):
            assert line in new_lines


def test_replace_keeps_comments_and_other_bytes() -> None:
    text = "# 頭\nmax_hp: 160   # 初值\nspeed: 0\n"
    assert patch_text(text, [(("max_hp",), 150)]) == "# 頭\nmax_hp: 150   # 初值\nspeed: 0\n"


def test_insert_into_flow_mappings() -> None:
    assert patch_text("resist: {}\n", [(("resist", "physical"), 100)]) == (
        "resist: {physical: 100}\n"
    )
    text = "element_mods: {fire: -750, ice: 500}  # 弱冰\n"
    assert patch_text(text, [(("element_mods", "wind"), 250)]) == (
        "element_mods: {fire: -750, ice: 500, wind: 250}  # 弱冰\n"
    )
    phase = "phases:\n  - {id: a}\n  - id: b\n    trigger: {kind: hp_below, permille: 600}\n"
    assert patch_text(phase, [(("phases", 1, "trigger", "permille"), 550)]) == phase.replace(
        "600", "550"
    )


def test_insert_into_block_mapping_after_the_last_key() -> None:
    text = "id: x\nmax_hp: 10\nphases:\n  - {id: a}\n# 外觀\ndoll: {rarity: common}\n"
    assert patch_text(text, [(("speed",), 3)]) == text + "speed: 3\n"
    nested = "id: x\nattributes:\n  str: 10\n  dex: 8\nmax_hp: 5\n"
    assert patch_text(nested, [(("attributes", "con"), 12)]) == (
        "id: x\nattributes:\n  str: 10\n  dex: 8\n  con: 12\nmax_hp: 5\n"
    )


def test_insert_missing_parent_mapping() -> None:
    text = "id: x\nmax_hp: 10\n"
    assert patch_text(text, [(("resist", "spirit"), -200)]) == text + "resist: {spirit: -200}\n"


def test_crlf_and_bom_are_kept() -> None:
    text = "﻿id: x\r\nmax_hp: 10\r\n"
    assert patch_text(text, [(("max_hp",), 12)]) == "﻿id: x\r\nmax_hp: 12\r\n"
    assert patch_text(text, [(("speed",), 4)]) == "﻿id: x\r\nmax_hp: 10\r\nspeed: 4\r\n"


def test_delete_reverses_an_insert_byte_for_byte() -> None:
    for text, parts in (
        ("id: x\nmax_hp: 10\n", ("speed",)),
        ("resist: {}\n", ("resist", "physical")),
        ("element_mods: {fire: -750, ice: 500}\n", ("element_mods", "wind")),
        ("element_mods: {fire: -750, ice: 500}\n", ("element_mods", "fire")),
    ):
        if lookup(parse_yaml(text), parts) is MISSING:
            inserted = patch_text(text, [(parts, 7)])
            assert patch_text(inserted, [(parts, None)]) == text
        else:
            deleted = patch_text(text, [(parts, None)])
            assert lookup(parse_yaml(deleted), parts) is MISSING
    assert patch_text("a: {b: 1, c: 2}\n", [(("a", "b"), None)]) == "a: {c: 2}\n"
    assert patch_text("id: x\n", [(("speed",), None)]) == "id: x\n"  # 本來就沒寫


@pytest.mark.parametrize(
    ("text", "parts", "value", "why"),
    [
        ('max_hp: "10"\n', ("max_hp",), 5, "整數"),
        ("max_hp: 10\n", ("max_hp",), None, "唯一"),
        ("id: x\nspeed: 3  # 慢\n", ("speed",), None, "註解"),
        ("phases:\n  - {id: a}\n", ("phases", 3, "trigger", "permille"), 5, "第 3 項"),
        ("a: &x {b: 1}\nc: *x\n", ("a", "b"), 5, "錨點"),
        ("attributes: [1, 2]\n", ("attributes", "str"), 5, "對照表"),
    ],
)
def test_unsafe_patches_are_refused(
    text: str, parts: tuple[PathPart, ...], value: int | None, why: str
) -> None:
    with pytest.raises(PatchError, match=why):
        patch_text(text, [(parts, value)])


def test_real_boss_file_round_trip(tmp_path: Path) -> None:
    text = TEXTS["units/ashen_heart.yaml"]
    forward = patch_text(text, [(("max_hp",), 150), (("phases", 2, "trigger", "permille"), 250)])
    back = patch_text(forward, [(("max_hp",), 160), (("phases", 2, "trigger", "permille"), 300)])
    assert back == text
