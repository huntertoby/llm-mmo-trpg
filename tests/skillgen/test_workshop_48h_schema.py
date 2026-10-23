"""Phase 3-48h 5c：schema 錯誤改寫成白話，巢狀欄位的錯誤附「回到第 N 步」且所屬步驟不打勾。

掃描：把「錯誤型別的值」塞進內建技能（陷阱、戰場變奏、複合技能、持續區域……）的每一個欄位，
工坊的選項（`draft_options`）不能崩潰、玩家看得到的文字不能露出英文代號，而且屬於某一步的錯誤都要
附上「回到第 N 步修改」、那一步不打勾。
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator
from typing import Any

import pytest

from tests.engine.helpers import library
from trpg.skillgen.options import draft_options
from trpg.skillgen.player_text import plainify

LIB = library()
SKILLS = (
    "skill_bear_trap",  # 陷阱（trap.*）
    "skill_tidal_spear",  # 戰場變奏（variants.*）
    "skill_armor_break_combo",  # 複合技能（followup.*）
    "skill_fire_wall",  # 持續區域（巢狀 effects）
    "skill_blood_sacrifice",  # 獻祭
)
WRONG: tuple[Any, ...] = ("x", 12345, True, ["a"], {"k": 1}, None)
ENGLISH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]{2,}")
ALLOWED = {"AP", "HP", "MP", "YAML"}
LINK = re.compile(r"（回到第 (\d+) 步修改）")


def _leaves(obj: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _leaves(value, (*path, key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _leaves(value, (*path, index))
    else:
        yield path


def _get(obj: Any, path: tuple[Any, ...]) -> Any:
    for part in path:
        obj = obj[part]
    return obj


def _mutations(skill_id: str) -> Iterator[tuple[tuple[Any, ...], Any, dict[str, Any]]]:
    base = json.loads(LIB.skills[skill_id].model_dump_json(exclude_none=True))
    for key in ("id", "provenance", "narrative", "schema_version"):
        base.pop(key, None)
    for index, path in enumerate(_leaves(base)):
        original = _get(base, path)
        wrong = [w for w in WRONG if type(w) is not type(original) and not isinstance(w, str | dict)] + [
            w for w in WRONG if isinstance(w, dict) and not isinstance(original, dict)
        ]
        if not isinstance(original, str):  # 字串欄位的「錯誤型別」是數字、布林、列表
            wrong += ["x"]
        value = wrong[index % len(wrong)]
        draft = copy.deepcopy(base)
        target = _get(draft, path[:-1]) if path[:-1] else draft
        target[path[-1]] = value
        yield path, value, draft


CASES = [
    pytest.param(sid, path, value, draft, id=f"{sid}-{'.'.join(map(str, path))}")
    for sid in SKILLS
    for path, value, draft in _mutations(sid)
]


def _texts(options: Any) -> list[str]:
    out = list(options.problems)
    for step in options.steps:
        out += step.notes_zh
    return out


@pytest.mark.parametrize(("skill_id", "path", "value", "draft"), CASES)
def test_wrong_typed_fields_read_as_plain_chinese_with_step_links(
    skill_id: str, path: tuple[Any, ...], value: Any, draft: dict[str, Any]
) -> None:
    options = draft_options(draft, LIB)  # 不能崩潰
    where = f"{skill_id} {path} = {value!r}"
    for text in _texts(options):
        leaked = [w for w in ENGLISH.findall(text) if w not in ALLOWED]
        assert not leaked, f"{where}：玩家看得到英文 {leaked}：{text}"
    for step in options.steps:
        for note in step.notes_zh:
            link = LINK.search(note)
            if link is not None:  # 附了「回到第 N 步」：那一步不能打勾
                owner = options.steps[int(link.group(1)) - 1]
                assert not owner.complete, f"{where}：第 {link.group(1)} 步還打勾：{note}"


def test_nested_trap_error_is_linked_to_the_effects_step() -> None:
    """專案 PM 的案例：「陷阱.形狀：必須是文字」要附「回到第 N 步」，「效果」步驟不打勾。"""
    base = json.loads(LIB.skills["skill_bear_trap"].model_dump_json(exclude_none=True))
    for key in ("id", "provenance", "narrative", "schema_version"):
        base.pop(key, None)
    base["trap"]["shape"] = 12345
    options = draft_options(base, LIB)
    rarity = next(s for s in options.steps if s.id == "rarity")
    notes = [n for n in rarity.notes_zh if "陷阱" in n and "必須是文字" in n]
    assert notes, rarity.notes_zh
    number = next(i for i, s in enumerate(options.steps, 1) if s.id == "effects")
    assert f"（回到第 {number} 步修改）" in notes[0]
    assert not options.steps[number - 1].complete
    assert not [w for w in ENGLISH.findall(notes[0]) if w not in ALLOWED]


@pytest.mark.parametrize(
    ("english", "chinese"),
    [
        ("trap.rounds：Extra inputs are not permitted", "不能填"),
        ("effects[0].dice：Input should be a valid dictionary or instance of Dice", "格式不對"),
        ("cost.mana：Input should be a valid integer, unable to parse string as an integer", "必須是整數"),
        ("followup.effects：Input should be a valid list", "必須是列表"),
        ("name_zh：String should have at least 1 character", "至少要 1 個字"),
    ],
)
def test_pydantic_messages_are_rewritten(english: str, chinese: str) -> None:
    text = plainify(english, LIB)
    assert chinese in text
    assert not [w for w in ENGLISH.findall(text) if w not in ALLOWED]
