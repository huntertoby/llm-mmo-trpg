"""灰燼荒原骨架 3「異象」的說明卡（玩法 PM 定稿，PNL-4 時改；TXT-1 待決 1）。"""

from __future__ import annotations

from trpg.content.library import ContentLibrary


def test_ashen_vision_hint_wording(library: ContentLibrary) -> None:
    found = [
        (s.note_zh, s.hint_zh)
        for s in (
            sol
            for skeleton in library.world_event_content.events["ashen_waste"].skeletons
            for sol in skeleton.solutions
        )
        if s.note_zh == "異象"
    ]
    assert found == [("異象", "向聖火求指引，角魔主角判定 +1")]
