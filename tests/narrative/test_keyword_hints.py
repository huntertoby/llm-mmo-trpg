"""Phase 3-51：基礎技能標示、關鍵字顯示規則（#54）與工坊建議（#55）。"""

from __future__ import annotations

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID
from trpg.narrative.keyword_hints import draft_keyword_hints, keyword_hints
from trpg.narrative.skills import draft_card_keywords, skill_card_keywords
from trpg.skillgen.keywords import derive_draft_keywords

_SHAPE = {"type": "single", "range": 4}
_PLAIN = {"type": "damage", "dice": "1d6", "element": "physical"}


def test_a_skill_without_keywords_is_marked_basic() -> None:
    card = skill_card_keywords(library(), make_skill(SID, _SHAPE, [_PLAIN]))
    assert card.basic and card.makes == () and card.uses == ()


def test_a_skill_with_a_keyword_is_not_basic() -> None:
    fire = {**_PLAIN, "element": "fire"}
    card = skill_card_keywords(library(), make_skill(SID, _SHAPE, [fire]))
    assert not card.basic and [k.id for k in card.makes] == ["ignite"]


def test_the_shipped_basic_skills_are_all_marked_basic_on_their_cards() -> None:
    lib = library()
    basic = [s for s in lib.skills.values() if skill_card_keywords(lib, s).basic]
    assert basic  # Phase 3-51 移除暫定規則後出現的基礎技能
    for skill in basic:
        card = skill_card_keywords(lib, skill)
        assert card.makes == () and card.uses == ()


def test_hints_cover_the_keywords_the_draft_does_not_have_yet() -> None:
    lib = library()
    hints = keyword_hints(lib, derive_draft_keywords({}, lib.keywords))
    by_id = {h.id: h for h in hints}
    assert set(by_id) == set(lib.keywords.ids())  # 空草稿：每個關鍵字都有建議
    ignite = by_id["ignite"]
    assert any("施加狀態" in w and "燃燒" in w for w in ignite.makes)
    assert any("目標" in w for w in ignite.uses)
    assert all(len(h.makes) <= 4 and len(h.uses) <= 4 for h in hints)


def test_hints_drop_what_the_draft_already_makes_and_uses() -> None:
    lib = library()
    fire = {"effects": [{**_PLAIN, "element": "fire"}], "shape": _SHAPE}
    have = draft_card_keywords(lib, fire)
    assert [k.id for k in have.makes] == ["ignite"]
    hints = {h.id: h for h in draft_keyword_hints(lib, fire)}
    assert hints["ignite"].makes == () and hints["ignite"].uses != ()  # 已製造點燃，還能建議利用
    assert hints["wet"].makes != ()


def test_hints_are_generated_from_the_exclusive_rules_only() -> None:
    lib = library()
    general_reasons = {
        r.reason_zh for k in lib.keywords.keywords for r in (*k.makes, *k.uses) if r.reason_zh
    }
    for hint in keyword_hints(lib, derive_draft_keywords({}, lib.keywords)):
        for way in (*hint.makes, *hint.uses):
            assert way not in general_reasons
            assert way.startswith(("效果「", "條件「", "被動觸發「", "形狀「"))
