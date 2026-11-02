"""大世界隊伍與系統傭兵的顯示資料（Phase 5C-1；``docs/phases/Phase5計畫.md`` 21.6）。

規則一律呼叫 :mod:`trpg.world.party`，這裡只組裝文字。
"""

from __future__ import annotations

from trpg.api.world_party_schemas import MercenaryView, PartyMemberView, PartyView
from trpg.content.library import ContentLibrary
from trpg.content.world_mercenaries import MERCENARY_ROLES, MercenaryDef
from trpg.world.actions import PartyChangedEvent, WorldEvent
from trpg.world.party import hire_problem, party_mercenaries
from trpg.world.state import CharacterState

__all__ = ["allies_line", "party_event_line", "party_view"]

STANDARD_ZH = "標準隊友"


def _title(merc: MercenaryDef) -> str:
    return f"{merc.title_zh}・{MERCENARY_ROLES[merc.role]}"


def _mercenary_view(library: ContentLibrary, merc: MercenaryDef, hired: bool) -> MercenaryView:
    build = library.builds.by_id()[merc.build]
    skills = tuple(
        library.skills[s].name_zh if s in library.skills else s for s in build.hero.skills
    )
    return MercenaryView(
        id=merc.id,
        name_zh=merc.name_zh,
        title_zh=merc.title_zh,
        role=merc.role,
        role_zh=MERCENARY_ROLES[merc.role],
        theme_zh=build.theme_zh,
        skills_zh=skills,
        hired=hired,
    )


def party_view(library: ContentLibrary, char: CharacterState, *, in_battle: bool) -> PartyView:
    """隊伍面板與雇用清單（見模組說明）。"""
    members = [PartyMemberView(name_zh=char.hero.name_zh, title_zh="主角", level=char.level)]
    hired = party_mercenaries(library, char)
    if hired:
        members += [
            PartyMemberView(name_zh=m.name_zh, title_zh=_title(m), level=char.level, mercenary=m.id)
            for m in hired
        ]
    else:
        members += [
            PartyMemberView(name_zh=library.unit(c).name_zh, title_zh=STANDARD_ZH, level=char.level)
            for c in library.roguelite.companions
        ]
    problem = "戰鬥中" if in_battle else hire_problem(library, char)
    table = library.world_mercenaries
    roster = () if table is None else table.mercenaries
    return PartyView(
        members=tuple(members),
        max_hired=0 if table is None else table.max_hired,
        can_hire=problem is None,
        hire_problem_zh=problem,
        mercenaries=tuple(_mercenary_view(library, m, m.id in char.mercenaries) for m in roster),
    )


def allies_line(library: ContentLibrary, char: CharacterState, hero_hp: int) -> str:
    """遇敵面板的我方說明（例「主角（開場 HP 30）＋青鋒、回春」）。"""
    hero = f"主角（開場 HP {hero_hp}{'，疲憊' if char.fatigued else ''}）"
    hired = party_mercenaries(library, char)
    if hired:
        return f"{hero}＋{'、'.join(m.name_zh for m in hired)}"
    return f"{hero}＋ {len(library.roguelite.companions)} 名{STANDARD_ZH}"


def party_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """``party_changed`` 的句子。"""
    if not isinstance(event, PartyChangedEvent):
        return None
    if not event.mercenaries:
        return f"隊伍：不帶傭兵（開戰用{STANDARD_ZH}）。"
    known = {} if library.world_mercenaries is None else library.world_mercenaries.by_id()
    names = [known[m].name_zh if m in known else m for m in event.mercenaries]
    return f"隊伍：雇用{'、'.join(names)}（免費）。"
