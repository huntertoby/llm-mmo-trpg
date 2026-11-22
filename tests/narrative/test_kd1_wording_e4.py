"""E4 第 6 項：KD-1 驗收的兩件用字（玩法 PM 2026-11-22）。

1. 「倒地」的說明框一條規則一行，照 6 行寫；「1 AP」「一半」從資料組字（跟著工坊的值走）。
2. 彈射卡上同名的招只寫一次、後面加次數（「鉤爪 ×2」）。
"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.glossary import build_glossary
from trpg.engine.attack_shapes import _counted_names
from trpg.narrative.status_info import _prone_lines, status_rules

PRONE_LINES = [
    "不能使用反應（格擋、藉機攻擊、反擊）。",
    "倒地後的第一個自己回合少 1 AP。",
    "近戰攻擊你有優勢，遠程攻擊你有劣勢。",
    "不能衝鋒、跳躍、瞬步、攀跳。",
    "花一半移動點數站起來，或讓相鄰隊友扶起。",
    "站起來後會「站穩」，到下一個自己回合結束前不會再倒地。",
]


def test_prone_rules_match_the_six_lines_word_for_word() -> None:
    lib = library()
    assert list(status_rules(lib.ruleset.status_def("prone"), lib)) == PRONE_LINES


def test_prone_lines_follow_the_workshop_values() -> None:
    core = library().ruleset.core
    lines = _prone_lines(
        core.model_copy(update={"prone_ap_loss": 2, "prone_stand_up_move_permille": 300})
    )
    assert "倒地後的第一個自己回合少 2 AP。" in lines
    assert "花 30% 的移動點數站起來，或讓相鄰隊友扶起。" in lines
    assert len(lines) == 6


def test_glossary_marks_prone_as_rules_only() -> None:
    glossary = build_glossary(library())
    prone = next(s for s in glossary.statuses if s.id == "prone")
    assert prone.rules_only and list(prone.rules_zh) == PRONE_LINES
    others = [s for s in glossary.statuses if s.id != "prone"]
    assert not any(s.rules_only for s in others)
    assert "rules_only" not in others[0].model_dump()  # 預設值不輸出


def test_same_named_skills_are_written_once_with_a_count() -> None:
    names = ["破城衝撞", "颶風踢", "鉤爪", "鉤爪"]
    assert _counted_names(names) == "破城衝撞、颶風踢、鉤爪 ×2"
    assert _counted_names(["火球"]) == "火球"
