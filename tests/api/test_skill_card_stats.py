"""Phase 6A-1：技能卡另外提供「數字＋單位＋類別」的結構化欄位（``stats``），舊句子欄位不變。"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.engine.helpers import library
from trpg.api.skill_cards import card_stats, skill_card
from trpg.narrative import skills as narrative


def _effects(skill_id: str) -> list[tuple[Any, ...]]:
    lib = library()
    stats = card_stats(lib, lib.skills[skill_id])
    return [(e.category, e.label, e.unit, e.element, e.name_zh) for e in stats.effects]


@pytest.mark.parametrize(
    ("skill_id", "expected"),
    [
        # 法術傷害：範圍（X10-3b：3d6 × 10）＋元素
        ("skill_ash_harvest", [("damage", "30–180", None, "fire", None)]),
        # 武器傷害：倍率；推開：格數
        (
            "skill_gale_kick",
            [("damage", "×0.4", None, None, None), ("move", "2", "格", None, None)],
        ),
        # 表面與狀態：回合＋名稱
        (
            "skill_downpour",
            [("surface", None, None, None, "水"), ("status", "1", "回合", None, "緩速")],
        ),
        # 護盾：範圍（2d6 × 10）
        ("skill_reflex_ward", [("shield", "20–120", None, None, None)]),
        # 層數
        (
            "skill_sunder_strike",
            [("damage", "×0.6", None, None, None), ("stack", "1", "層", None, "破甲印")],
        ),
    ],
)
def test_effect_stats_table(skill_id: str, expected: list[tuple[Any, ...]]) -> None:
    assert _effects(skill_id) == expected


@pytest.mark.parametrize(
    ("skill_id", "chips", "kinds"),
    [
        # (AP、冷卻、射程、武器射程、時機)
        ("skill_ash_harvest", (2, 2, 5, False, None), ["ap", "mana", "cooldown"]),
        ("skill_gale_kick", (1, 2, None, True, None), ["ap", "stamina", "cooldown"]),
        ("skill_counterspell", (None, 1, 6, False, "reaction"), ["mana", "cooldown"]),
        ("skill_afterimage_vow", (1, None, None, False, "activation"), ["ap", "source"]),
    ],
)
def test_cost_and_chip_stats_table(skill_id: str, chips: tuple[Any, ...], kinds: list[str]) -> None:
    lib = library()
    stats = card_stats(lib, lib.skills[skill_id])
    assert (stats.ap, stats.cooldown, stats.range, stats.range_weapon, stats.timing) == chips
    assert [c.kind for c in stats.costs] == kinds


def test_mana_is_the_ally_cost_like_the_sentence() -> None:
    lib = library()
    skill = lib.skills["skill_ash_harvest"]
    card = skill_card(lib, skill)
    mana = next(c for c in card.stats.costs if c.kind == "mana")
    assert card.cost[mana.index] == f"法力 {mana.value}"
    assert mana.value == lib.ruleset.core.mana_cost(skill.cost.mana)


def test_delayed_followup_has_the_delay_timing() -> None:
    lib = library()
    delayed = [s for s in lib.skills.values() if s.followup and s.followup.release is not None]
    assert delayed
    for skill in delayed:
        assert card_stats(lib, skill).timing == "delayed"


def test_every_skill_lines_up_with_the_sentences() -> None:
    """全部技能：``stats.costs``、``stats.effects`` 和舊句子欄位一一對應，句子欄位和敘事層相同。"""
    lib = library()
    for skill in lib.skills.values():
        card = skill_card(lib, skill)
        old = narrative.skill_card(lib, skill)
        assert card.model_dump(exclude={"stats"}) == old.model_dump(), skill.id
        assert [c.index for c in card.stats.costs] == list(range(len(card.cost))), skill.id
        assert [e.index for e in card.stats.effects] == list(range(len(card.effects))), skill.id
        assert [e.type for e in card.stats.effects] == list(card.effect_ids), skill.id
        for c in card.stats.costs:
            if c.value is not None and c.kind not in ("hp_percent", "self_status"):
                assert str(c.value) in card.cost[c.index], (skill.id, c)


def test_skill_endpoint_returns_stats(client: TestClient) -> None:
    body = client.get("/api/skills/skill_ash_harvest").json()
    assert body["cost"]  # 舊句子欄位還在
    assert body["stats"]["effects"][0]["label"] == "30–180"
    assert body["stats"]["effects"][0]["dice"] == "3d6"
    assert body["stats"]["effects"][0]["element"] == "fire"


def test_range_stacks_the_owner_attribute_bonus() -> None:
    """X10-3b：有持有者時，法術傷害的範圍疊上目前的屬性加成（和「傷害算法」的目前值同一個算法）；
    武器傷害照舊寫倍率。"""
    lib = library()
    owner = narrative.CardOwner(attr_get=lambda _a: 140)
    bonus = 140 * lib.ruleset.core.spell_attr_multiplier_permille // 1000
    spell = card_stats(lib, lib.skills["skill_ash_harvest"], owner=owner)
    assert spell.effects[0].label == f"{30 + bonus}–{180 + bonus}"
    shield = card_stats(lib, lib.skills["skill_reflex_ward"], owner=owner)
    assert shield.effects[0].label == f"{20 + bonus}–{120 + bonus}"
    weapon = card_stats(lib, lib.skills["skill_gale_kick"], owner=owner)
    assert weapon.effects[0].label == "×0.4"


def test_no_card_label_writes_dice() -> None:
    """X10-3b：卡片的效果數字一律不寫「NdM」。"""
    lib = library()
    for skill in lib.skills.values():
        for e in card_stats(lib, skill).effects:
            assert e.label is None or "d" not in e.label, (skill.id, e.label)


def test_no_card_text_writes_dice() -> None:
    """X10-3b：卡片上的句子（效果、算法、召喚物資訊、形態）都寫範圍，只有結構化的 ``dice`` 欄位
    保留資料原樣。"""
    lib = library()
    pattern = re.compile(r"\d+d\d+")
    for skill in lib.skills.values():
        card = skill_card(lib, skill).model_dump(exclude={"stats", "icon"})
        assert not pattern.search(json.dumps(card, ensure_ascii=False)), skill.id
