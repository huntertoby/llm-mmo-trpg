"""技能卡不外露英文代號（Phase 3-41a 驗收：217 張技能卡全部重新產生，掃描英文片段）。"""

from __future__ import annotations

import re
from collections.abc import Iterator

from tests.engine.helpers import library
from trpg.narrative.skills import SkillCard, skill_card

_CODE = re.compile(r"[A-Za-z_]{3,}")
WHITELIST = frozenset({"Boss"})
"""允許出現的英文片段：「Boss」是遊戲內的稱呼（狀態說明、放逐的「Boss 免疫」）。"""


def _texts(card: SkillCard) -> Iterator[str]:
    """技能卡上玩家看得到的文字（不含給前端用的 ``*_id`` 代碼與圖示資料）。"""
    yield from (card.name_zh, card.rarity, card.kind, card.category, card.weapon_req)
    yield from (card.scaling, card.shape, card.skeleton_zh, *card.cost, *card.effects)
    yield from card.modifiers
    for text in (card.condition, card.timing, card.activation, card.mastery, card.followup):
        if text is not None:
            yield text
    for ref in (*card.keywords.makes, *card.keywords.uses):
        yield from (ref.name_zh, ref.description_zh, ref.reason_zh or "")
    for variant in card.variants:
        yield from (variant.name_zh, variant.condition, variant.change)
    for info in card.summons:
        yield from (info.name_zh, info.hp_note, info.move, info.defense, info.attack)
        yield from (*info.innate, *info.behavior, info.infusion)


def test_no_skill_card_shows_english_codes() -> None:
    lib = library()
    found: dict[str, list[str]] = {}
    for skill_id in sorted(lib.skills):
        card = skill_card(lib, lib.skills[skill_id])
        for text in _texts(card):
            for word in _CODE.findall(text):
                if word not in WHITELIST:
                    found.setdefault(word, []).append(skill_id)
    assert found == {}
    assert len(lib.skills) >= 217


def test_every_skill_tag_has_a_chinese_name() -> None:
    lib = library()
    names = lib.ruleset.skill_tags.names()
    used = {tag for skill in lib.skills.values() for tag in skill.tags}
    assert sorted(used - set(names)) == []


def test_skill_cards_show_the_skeleton_name() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_raise_skeleton"])
    assert card.skeleton == "summon" and card.skeleton_zh == lib.skeletons["summon"].name_zh
