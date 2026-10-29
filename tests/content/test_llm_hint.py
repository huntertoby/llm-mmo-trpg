"""Phase 4-L3：每個原語、形狀、條件、觸發與其參數都有給 LLM 看的一句話說明（``llm_hint``）。"""

from __future__ import annotations

import re

from tests.engine.helpers import library

WORLD_WORDS = ("碎界", "源晶", "界域", "頻率")
"""世界觀名詞：說明要中性，名詞與語氣由 prompt 負責。"""
IDENTIFIER = re.compile(r"[A-Za-z]+_[A-Za-z_]+|Phase|\d[A-Z]-\d")
"""欄位名（snake_case）與階段編號。"""


def _entries() -> list[tuple[str, str]]:
    """（位置, llm_hint）：原語、形狀、條件、觸發各一筆，加上它們的每個參數。"""
    ruleset = library().ruleset
    out: list[tuple[str, str]] = []
    groups = (
        ("原語", ruleset.primitives.primitives),
        ("只能巢狀的效果", ruleset.primitives.nested_only_effects),
        ("形狀", ruleset.shapes.shapes),
        ("條件", ruleset.conditions.conditions),
        ("觸發", ruleset.skill_triggers.triggers),
    )
    for label, items in groups:
        for item in items:
            out.append((f"{label} {item.id}", item.llm_hint))
            for name, spec in item.params.items():
                out.append((f"{label} {item.id}.{name}", spec.llm_hint))
    return out


def test_every_entry_and_param_has_a_hint() -> None:
    entries = _entries()
    assert len(entries) > 150
    assert [where for where, hint in entries if not hint.strip()] == []


def test_hints_are_one_neutral_chinese_sentence() -> None:
    problems: list[str] = []
    for where, hint in _entries():
        if not hint.endswith("。") or hint.count("。") != 1:
            problems.append(f"{where}：必須是以句號結尾的一句話")
        if IDENTIFIER.search(hint):
            problems.append(f"{where}：不可含欄位名或階段編號")
        if any(word in hint for word in WORLD_WORDS):
            problems.append(f"{where}：不可含世界觀名詞")
        if len(hint) > 60:
            problems.append(f"{where}：太長（{len(hint)} 字）")
    assert problems == []
