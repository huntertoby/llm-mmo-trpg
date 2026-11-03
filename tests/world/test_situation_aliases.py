"""Phase 5C-3e：別名照玩法 PM 代決改（`docs/phases/Phase5C-3e代決.md`）、往來也認相關線頭。"""

from __future__ import annotations

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_situations import MakeChar, act, at_event, check_of, thread
from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute
from trpg.world.situations import (
    mentions,
    situation_fact_keywords,
    situation_template,
)
from trpg.world.step import world_step

REGION = "cloud_ridge"

# (種類, ID) → 代決後的別名（逐字）
CHANGED: dict[tuple[str, str], list[str]] = {
    ("thread", "peddler_owes_you"): ["欠你人情", "欠我人情", "行商的人情"],
    ("thread", "alchemist_owes_you"): ["煉丹師"],
    ("thread", "ferryman_daughter"): ["渡船夫的女兒", "船夫的女兒"],
    ("thread", "shards_under_den"): ["熊巢下", "熊巢"],
    ("thread", "shards_to_ashen"): ["送往灰燼荒原", "運往荒原", "運到荒原"],
    ("thread", "tavern_rumor"): [],
    ("thread", "frost_chime_we"): ["裂痕裡有我們", "「我們」", "碎晶之主"],
    ("npc", "hunter_ayue"): ["阿岳", "獵戶阿岳"],
    ("npc", "smith_shi"): ["石師傅", "鐵匠"],
    ("weakness", "monk_story_gap"): ["前後矛盾", "說法不一"],
    ("weakness", "hunter_name"): ["喊出他的名字", "叫他的名字"],
    ("weakness", "pursuers_lost_in_fog"): ["霧裡的小路", "霧中小路"],
    ("weakness", "envoy_duty"): ["確認身分", "表明身分"],
}

# (種類, ID) → 拿掉的寬泛詞：單獨出現時不能再命中
REMOVED: dict[tuple[str, str], list[str]] = {
    ("thread", "peddler_owes_you"): ["人情"],
    ("thread", "alchemist_owes_you"): ["人情"],
    ("thread", "ferryman_daughter"): ["女兒"],
    ("thread", "shards_under_den"): ["源晶碎片", "源晶"],
    ("thread", "shards_to_ashen"): ["灰燼荒原"],
    ("thread", "tavern_rumor"): ["傳聞"],
    ("thread", "frost_chime_we"): ["我們"],
    ("npc", "hunter_ayue"): ["獵人"],
    ("npc", "smith_shi"): ["師傅"],
    ("weakness", "monk_story_gap"): ["矛盾"],
    ("weakness", "hunter_name"): ["名字", "阿岳"],
    ("weakness", "pursuers_lost_in_fog"): ["小路"],
    ("weakness", "envoy_duty"): ["身分"],
}


def _entry(library: ContentLibrary, kind: str, item_id: str) -> tuple[str, tuple[str, ...]]:
    """（名稱, 別名）：線頭 ``text_zh``、NPC ``name_zh``、弱點 ``text_zh``。"""
    if kind == "thread":
        t = library.world_event_content.events[REGION].thread_by_id()[item_id]
        return t.text_zh, t.aliases_zh
    if kind == "npc":
        c = library.world_event_content.npcs[REGION].npc_by_id()[item_id]
        return c.name_zh, c.aliases_zh
    table = library.world_event_content.situations.templates[REGION]
    for template in table.templates:
        found = template.weakness_by_id().get(item_id)
        if found is not None:
            return found.text_zh, found.aliases_zh
    raise KeyError(item_id)


@pytest.mark.parametrize(("kind", "item_id"), sorted(CHANGED))
def test_aliases_follow_ruling(library: ContentLibrary, kind: str, item_id: str) -> None:
    name, aliases = _entry(library, kind, item_id)
    assert list(aliases) == CHANGED[(kind, item_id)]
    keywords = (name, *aliases)
    for alias in aliases:
        assert mentions(f"我說：{alias}。", keywords)


@pytest.mark.parametrize(("kind", "item_id"), sorted(REMOVED))
def test_broad_words_no_longer_hit(library: ContentLibrary, kind: str, item_id: str) -> None:
    name, aliases = _entry(library, kind, item_id)
    for word in REMOVED[(kind, item_id)]:
        assert not mentions(word, (name, *aliases)), word


def test_npc_bond_accepts_related_thread_words(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """往來也認相關線頭（``npc`` 等於該 NPC）的文字與別名；沒有 ``npc`` 欄位的線頭不算進去。"""
    world = make_world(threads=(thread("temple_quarrel", "lost_acolyte"),))
    char = at_event(
        make_char(threads=(thread("peddler_owes_you"),)), "monks_dispute", "mist_temple_gate"
    )
    template = situation_template(library, REGION, "monks_persuade")
    words = situation_fact_keywords(library, world, char, template, NOON)
    assert words["npc:acolyte_xiaolian"] == ("小蓮", "道童", "道童提到觀裡在吵架", "吵架")
    assert not any("人情" in w for w in words["npc:acolyte_xiaolian"])

    def counted(text: str) -> bool:
        action = act(
            "monks_persuade",
            attribute=Attribute.WIL,
            method="parley",
            care=(("npc_bond", "npc:acolyte_xiaolian"),),
            text=text,
        )
        check = check_of(world_step(library, world, char, action, NOON).events)
        return check.care[0].counted

    assert counted("他們一直在吵架，我出面勸和")
    assert not counted("商人欠你人情，我出面勸和")
