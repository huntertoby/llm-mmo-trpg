"""許願池面板的畫面資料（Phase WP-2；``docs/phases/PhaseWP計畫.md`` 第 4 節）。

- :func:`wish_view` → ``WorldView.wish``：人在主城才有；費用、退款、本週剩幾次、能不能許與原因、
  LLM 開不開、選單、願望字數上限、守池人的頭像與一句話。
- :func:`wish_block` 是畫面與等待提示（``pregen/wait`` 的 ``kind: "wish"``）共用的「現在不能許」：
  戰鬥中、待選的閃現與三選一（``world_step`` 先擋的那兩句），再來是規則的
  :func:`~trpg.world.wish.wish_problem`。
"""

from __future__ import annotations

from typing import Final

from trpg.api.world_range import capital_figure
from trpg.api.world_wish_schemas import WishMenuItemView, WishTagGroupView, WishView
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.skill_pick import WISH_TAG_GROUPS
from trpg.skillgen.wish_pick import tag_limits
from trpg.world.common import in_capital
from trpg.world.state import CharacterState, WorldState
from trpg.world.wish import (
    wish_driven,
    wish_menu,
    wish_problem,
    wish_refund,
    wish_rules,
    wish_tier,
    wishes_left,
)

__all__ = [
    "WISH_IN_BATTLE_ZH",
    "WISH_KEEPER_OBJECT",
    "WISH_POOL_OBJECT",
    "wish_block",
    "wish_view",
]

WISH_POOL_OBJECT: Final = "wishing_pool"
"""主城實地地圖上的許願池物件（面板標頭用它的名字）。"""
WISH_KEEPER_OBJECT: Final = "pool_keeper"
"""守池人物件（面板的頭像與一句話）。"""
WISH_IN_BATTLE_ZH: Final = "戰鬥進行中，先打完這場"
"""戰鬥中（同 ``WorldStore`` 擋世界動作的那一句）。"""
_PENDING_FLASH_ZH: Final = "還有閃現的選項沒有選：先選一個"
_PENDING_OFFER_ZH: Final = "還有任務給的技能三選一沒有選：先選一招，或都不拿"
"""同 ``world_step`` 先擋的兩句（送出時被拒的字相同）。"""


def wish_block(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    in_battle: bool = False,
) -> str | None:
    """現在不能許願的原因（和送出 ``wish`` 被拒的字相同）；可以時 ``None``。"""
    if in_battle:
        return WISH_IN_BATTLE_ZH
    if char.pending_flash is not None:
        return _PENDING_FLASH_ZH
    if char.pending_offers:
        return _PENDING_OFFER_ZH
    return wish_problem(library, world, char, now)


def _keeper_line(library: ContentLibrary) -> str | None:
    found = library.outdoor_map(CAPITAL_REGION, CAPITAL_REGION)
    if found is None:
        return None
    spot = next((s for s in found.situation_objects if s.id == WISH_KEEPER_OBJECT), None)
    return None if spot is None else spot.note_zh


def _title(library: ContentLibrary) -> str:
    found = library.outdoor_map(CAPITAL_REGION, CAPITAL_REGION)
    spot = (
        None
        if found is None
        else next((s for s in found.situation_objects if s.id == WISH_POOL_OBJECT), None)
    )
    return "許願池" if spot is None or not spot.name_zh else spot.name_zh


def wish_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    now: int,
    *,
    llm: bool,
    in_battle: bool = False,
) -> WishView | None:
    """``WorldView.wish``：人在主城才有（見模組說明）。``llm`` 是世界的 LLM 開關與健康檢查。"""
    if not in_capital(char):
        return None
    rules = wish_rules(library)
    problem = wish_block(library, world, char, now, in_battle=in_battle)
    names = {k.id: k for k in library.keywords.keywords}
    return WishView(
        tag_groups=_tag_groups(library, wish_tier(library, world, char))
        if wish_driven(library)
        else (),
        title_zh=_title(library),
        speaker=capital_figure(library, WISH_KEEPER_OBJECT),
        line_zh=_keeper_line(library),
        cost=rules.cost_quest_coins,
        refund=wish_refund(library),
        coins=char.quest_coins,
        left=wishes_left(library, world, char, now),
        per_week=rules.per_week,
        available=problem is None,
        blocked_zh=problem,
        llm=llm,
        text_max_chars=rules.text_max_chars,
        max_keywords=rules.max_keywords,
        menu=tuple(
            WishMenuItemView(id=k, name_zh=names[k].name_zh, description_zh=names[k].description_zh)
            for k in wish_menu(library)
        ),
    )


_GROUP_LABELS: Final = {
    "keywords": "關鍵字",
    "elements": "元素",
    "effects": "效果類型",
    "shapes": "形狀",
    "kinds": "種類",
}


def _tag_groups(library: ContentLibrary, tier: int) -> tuple[WishTagGroupView, ...]:
    """PK-4：標籤清單（關鍵字照選單；其他照 ``skill_pick.yaml`` 的 ``wish_tags``）；上限照角色階級
    ``tier``（WC-2：元素 2 階起最多 2 個）。"""
    rules = library.skill_pick.wish_tags
    limits = tag_limits(library, tier)
    names = {k.id: k for k in library.keywords.keywords}
    groups = [
        WishTagGroupView(
            id="keywords",
            label_zh=_GROUP_LABELS["keywords"],
            max=limits["keywords"],
            items=tuple(
                WishMenuItemView(
                    id=k, name_zh=names[k].name_zh, description_zh=names[k].description_zh
                )
                for k in wish_menu(library)
            ),
        )
    ]
    for group in WISH_TAG_GROUPS[1:]:
        groups.append(
            WishTagGroupView(
                id=group,
                label_zh=_GROUP_LABELS[group],
                max=limits[group],
                items=tuple(
                    WishMenuItemView(id=i.id, name_zh=i.name_zh, description_zh="")
                    for i in rules.items(group)
                ),
            )
        )
    return tuple(groups)
