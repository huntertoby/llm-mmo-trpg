"""NW-2a T-A2：技能檔的字面替換（整數、骰子）、招式組清單、預算例外清單。"""

from __future__ import annotations

import difflib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from trpg.api.tuning.objects import concrete_fields
from trpg.api.tuning.yaml_patch import (
    MISSING,
    PatchError,
    exception_comment,
    lookup,
    patch_exception_list,
    patch_text,
)
from trpg.content.loader import bundled_content_dir, parse_yaml
from trpg.content.tuning_fields import PathPart, load_tuning_fields, parse_path, target_files

CONTENT = bundled_content_dir()


def _skill_cases() -> list[tuple[str, tuple[PathPart, ...], str]]:
    """全部技能檔 × 每個展開的欄位（整數與骰子）：(檔, 路徑, kind)。"""
    table = load_tuning_fields(CONTENT)
    skill = table.target("skill")
    assert skill is not None
    cases: list[tuple[str, tuple[PathPart, ...], str]] = []
    for path in target_files(CONTENT, skill):
        data = parse_yaml(path.read_text(encoding="utf-8"))
        rel = path.relative_to(CONTENT).as_posix()
        for field, concrete, _label in concrete_fields(data, skill):
            value = lookup(data, parse_path(concrete))
            if field.kind == "range" and value == "weapon":
                continue
            cases.append((rel, parse_path(concrete), field.kind))
    return cases


CASES = _skill_cases()
TEXTS = {rel: (CONTENT / rel).read_bytes().decode("utf-8") for rel, _p, _k in CASES}
DICE = st.builds(lambda c, s: f"{c}d{s}", st.integers(1, 12), st.sampled_from([4, 6, 8, 10, 12]))


def _set(data: dict[str, object], parts: tuple[PathPart, ...], value: object) -> None:
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


def test_cases_cover_every_skill_file_and_dice() -> None:
    # LW-1 加 3 招；BS-1 加 2 招；RG-1 加 3 招；RG-2 加 1 招
    assert len({rel for rel, _p, _k in CASES}) == 426  # KW-2 加 16 招
    kinds = {k for _r, _p, k in CASES}
    assert {"int", "permille", "dice", "range"} <= kinds
    assert (
        "skills/skill_pinpoint_shot.yaml",
        ("effects", 1, "multiplier_permille"),
        "permille",
    ) in CASES


@settings(max_examples=400, deadline=None)
@given(case=st.sampled_from(CASES), number=st.integers(1, 9999), dice=DICE)
def test_patch_changes_only_that_value(
    case: tuple[str, tuple[PathPart, ...], str], number: int, dice: str
) -> None:
    rel, parts, kind = case
    value: object = dice if kind == "dice" else number
    text = TEXTS[rel]
    before = parse_yaml(text)
    existed = lookup(before, parts) is not MISSING
    new = patch_text(text, [(parts, value)])  # type: ignore[list-item]
    expected = parse_yaml(text)
    _set(expected, parts, value)
    assert parse_yaml(new) == expected
    if lookup(before, parts) == value:
        assert new == text
        return
    old_lines, new_lines = text.splitlines(keepends=True), new.splitlines(keepends=True)
    diff = list(difflib.ndiff(old_lines, new_lines))
    assert len([x for x in diff if x.startswith("+ ")]) == 1
    assert len([x for x in diff if x.startswith("- ")]) == (
        1 if existed or len(new_lines) == len(old_lines) else 0
    )
    for line in old_lines:  # 註解一行都沒少
        if line.lstrip().startswith("#"):
            assert line in new_lines


def test_flow_and_block_effects_and_cost_insert_and_cooldown_delete() -> None:
    text = TEXTS["skills/skill_pinpoint_shot.yaml"]
    flow = patch_text(text, [(("effects", 0, "multiplier_permille"), 1100)])
    assert "  - {type: damage, multiplier_permille: 1100}\n" in flow
    block = patch_text(text, [(("effects", 1, "multiplier_permille"), 1200)])
    assert "    multiplier_permille: 1200\n" in block and "  # 標記就是靶心" in block
    fire = TEXTS["skills/skill_fire_arrow.yaml"]
    inserted = patch_text(fire, [(("cost", "cooldown"), 2)])
    assert "cost: {stamina: 6, cooldown: 2}\n" in inserted
    assert patch_text(inserted, [(("cost", "cooldown"), None)]) == fire  # 清空冷卻＝刪鍵


def test_dice_replace_and_refusals() -> None:
    assert patch_text("dice: 2d6\n", [(("dice",), "3d8")]) == "dice: 3d8\n"
    with pytest.raises(PatchError, match="NdM"):
        patch_text("dice: 2d6\n", [(("dice",), "2x6")])
    with pytest.raises(PatchError, match="骰子"):
        patch_text('dice: "2d6"\n', [(("dice",), "3d8")])  # 加引號的照舊擋


def test_unit_skill_lists_flow_with_comment_and_block() -> None:
    text = TEXTS_UNIT = (CONTENT / "units" / "ashen_heart.yaml").read_text(encoding="utf-8")
    new = patch_text(text, [(("skills",), ("skill_fire_bolt", "skill_lava_splash"))])
    old_lines, new_lines = TEXTS_UNIT.splitlines(), new.splitlines()
    changed = [(a, b) for a, b in zip(old_lines, new_lines, strict=True) if a != b]
    assert changed == [
        (
            changed[0][0],
            "skills: [skill_fire_bolt, skill_lava_splash]"
            + changed[0][0].split("]", 1)[1],  # 行尾註解保留
        )
    ]
    phase = patch_text(text, [(("phases", 1, "skills"), ("skill_fire_bolt",))])
    assert parse_yaml(phase)["phases"][1]["skills"] == ["skill_fire_bolt"]
    block = (
        "id: x\nphases:\n  - id: a\n  - id: b\n"
        "    skills:\n      - skill_a\n      - skill_b\n    text_zh: 好\n"
    )
    changed_block = patch_text(
        block, [(("phases", 1, "skills"), ("skill_c", "skill_a", "skill_d"))]
    )
    assert changed_block == block.replace(
        "      - skill_a\n      - skill_b\n", "      - skill_c\n      - skill_a\n      - skill_d\n"
    )
    assert patch_text(block, [(("phases", 1, "skills"), ())]) == block.replace(
        "    skills:\n      - skill_a\n      - skill_b\n", "    skills: []\n"
    )
    deleted = patch_text(block, [(("phases", 1, "skills"), None)])  # 刪掉＝沿用上一階段
    assert deleted == block.replace("    skills:\n      - skill_a\n      - skill_b\n", "")
    inserted = patch_text(deleted, [(("phases", 1, "skills"), ("skill_a", "skill_b"))])
    assert parse_yaml(inserted)["phases"][1]["skills"] == ["skill_a", "skill_b"]
    with pytest.raises(PatchError, match="註解"):
        patch_text(
            block.replace("      - skill_b\n", "      # 註\n      - skill_b\n"),
            [(("phases", 1, "skills"), ("skill_c",))],
        )


BUDGET = (CONTENT / "skill_budget.yaml").read_text(encoding="utf-8")


def test_exception_list_add_and_remove_round_trip() -> None:
    added = patch_exception_list(
        BUDGET, {"skill_fire_arrow": "128.1%", "skill_zz_test": "71.0%"}, [], "2026-11-12"
    )
    data = parse_yaml(added)
    assert data["known_budget_exceptions"] == [
        "skill_fire_arrow",
        "skill_summon_elite",
        "skill_zz_test",
    ]
    diff = [x for x in difflib.ndiff(BUDGET.splitlines(), added.splitlines()) if x[:2] in "+ - "]
    plus = [x for x in diff if x.startswith("+ ")]
    assert len(plus) == 3 and len([x for x in diff if x.startswith("- ")]) == 1
    assert "+ " + exception_comment("skill_fire_arrow", "128.1%", "2026-11-12") in plus
    assert exception_comment("skill_fire_arrow", "128.1%", "2026-11-12") == (
        "# 數值工坊 2026-11-12：skill_fire_arrow 比例 128.1%（使用者確認）"
    )
    back = patch_exception_list(added, {}, ["skill_fire_arrow", "skill_zz_test"], "2026-11-13")
    assert back == BUDGET  # 逐位元組回到原樣
    gone = patch_exception_list(BUDGET, {}, ["skill_summon_elite"], "2026-11-12")
    assert parse_yaml(gone)["known_budget_exceptions"] == []
    assert "BAL-14b" in gone  # 手寫的行尾註解不動
    assert patch_exception_list(BUDGET, {}, [], "2026-11-12") == BUDGET
