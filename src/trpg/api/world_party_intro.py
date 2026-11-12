"""隊友加入當下的台詞（OB-7，#154；09 9.6「預設隊友的出場」、18 18.7.1 第 1 步）。

畫面資料 ``WorldView.party_intro``：還沒播的那一段（一次一段，賽倫先、夥伴依加入順序）。

- **賽倫**（``mercenaries.yaml`` 的 ``escort``）：開局還沒結束、已按「確定出發」（``opening.stage``
  不是 ``pick_class``）、他是開局帶來的那一位（:func:`trpg.world.party.is_escort`）而且在隊上。
- **劇情夥伴**（``companions[].join_lines``，阿岳）：開局還沒結束、在隊上。阿岳在新手第 1 步打完才
  入隊（任務的 ``companion_after``），所以第 1 步打完、回到地圖時出現。
- 看過＝``hints_seen`` 有 ``intro:<成員 ID>``；前端播完送既有的 ``hint_seen``（沒有新動作）。
- 已完成開局的角色（``opening is None``）不補播（#154 第 4 點）；面板的來歷照樣顯示。

純顯示：不改規則、不寫日誌。
"""

from __future__ import annotations

from typing import Final

from trpg.api.world_party_schemas import PartyIntroLine, PartyIntroView
from trpg.content.library import ContentLibrary
from trpg.content.world_mercenaries import PartyLine
from trpg.world.party import is_escort
from trpg.world.state import CharacterState

__all__ = ["INTRO_SEEN_PREFIX", "intro_seen_id", "party_intro"]

INTRO_SEEN_PREFIX: Final = "intro:"
"""隊友加入台詞看過的提示旗標前綴（``hints_seen``）。"""


def intro_seen_id(member: str) -> str:
    """``intro:<傭兵或夥伴 ID>``。"""
    return f"{INTRO_SEEN_PREFIX}{member}"


def _view(member: str, name_zh: str, lines: tuple[PartyLine, ...]) -> PartyIntroView:
    return PartyIntroView(
        seen_id=intro_seen_id(member),
        member=member,
        name_zh=name_zh,
        lines=tuple(PartyIntroLine(speaker_zh=x.speaker_zh, text_zh=x.text_zh) for x in lines),
    )


def party_intro(library: ContentLibrary, char: CharacterState) -> PartyIntroView | None:
    """還沒播的隊友加入台詞（見模組說明）；沒有時 ``None``。"""
    table = library.world_mercenaries
    if table is None or char.opening is None:
        return None
    seen = set(char.hints_seen)
    escort = table.escort
    if (
        escort is not None
        and char.opening.stage != "pick_class"
        and escort.mercenary in char.mercenaries
        and is_escort(library, char, escort.mercenary)
        and intro_seen_id(escort.mercenary) not in seen
    ):
        merc = table.by_id()[escort.mercenary]
        return _view(merc.id, merc.name_zh, escort.intro)
    known = table.companion_by_id()
    for companion in char.companions:
        found = known.get(companion)
        if found is None or not found.join_lines or intro_seen_id(companion) in seen:
            continue
        return _view(found.id, found.name_zh, found.join_lines)
    return None
