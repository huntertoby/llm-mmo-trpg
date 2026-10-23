"""刻印技能的關鍵字推導（Phase 3-48e）：卡片上每個關鍵字都要有來源，通用歸類要帶理由。

使用者的工坊技能（物理刻印＋對友方上 ``rallied``）：製造「標記」是專屬規則（刻印是標記，之後由
``on_own_rune``／``detonate_runes`` 讀取）；利用「召喚物」是 **通用歸類**（對友方生效的效果，
召喚物也算友方），卡片以通用樣式顯示並附理由——這是 6.27.1 的既有設計，不是推導錯誤。
"""

from __future__ import annotations

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID
from trpg.narrative.skills import skill_card_keywords

_SHAPE = {"type": "square3", "range": 5}
_INSCRIBE = {"type": "inscribe", "affects": "tiles", "element": "physical", "duration": 4}
_RALLY = {"type": "apply_status", "affects": "allies", "status": "rallied", "duration": 3}


def test_physical_inscribe_makes_only_marked_and_has_no_element_keyword() -> None:
    card = skill_card_keywords(library(), make_skill(SID, _SHAPE, [_INSCRIBE]))
    assert [k.id for k in card.makes] == ["marked"]
    assert [k.id for k in card.uses] == []


def test_general_summon_use_is_hidden_when_the_skill_has_an_exclusive_keyword() -> None:
    """玩法決定 #54：有專屬關鍵字（標記）時不顯示通用歸類（召喚物）。"""
    card = skill_card_keywords(library(), make_skill(SID, _SHAPE, [_INSCRIBE, _RALLY]))
    assert [k.id for k in card.makes] == ["marked"]
    assert card.uses == ()
    assert not card.basic


def test_ally_buff_alone_shows_summon_use_as_general_with_a_reason() -> None:
    """沒有專屬關鍵字時，通用歸類照舊標灰並附理由。"""
    card = skill_card_keywords(library(), make_skill(SID, _SHAPE, [_RALLY]))
    assert card.makes == ()
    (use,) = card.uses
    assert (use.id, use.general) == ("summon", True)
    assert use.reason_zh  # 通用歸類一定要寫理由，client 才能說明為什麼出現
    assert not card.basic


def test_elemental_inscribe_also_makes_its_element_keyword() -> None:
    fire = {**_INSCRIBE, "element": "fire"}
    card = skill_card_keywords(library(), make_skill(SID, _SHAPE, [fire]))
    assert [k.id for k in card.makes] == ["ignite", "marked"]
