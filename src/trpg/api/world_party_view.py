"""大世界隊伍、系統傭兵與影子的顯示資料（Phase 5C-1、5C-2；``docs/phases/Phase5計畫.md`` 22.6、
23.8）。

規則一律呼叫 :mod:`trpg.world.party`、:mod:`trpg.world.shadows`，這裡只組裝文字。
"""

from __future__ import annotations

from collections import Counter

from trpg.api.account_schemas import TitlesOf, no_titles
from trpg.api.world_party_schemas import (
    AiChoiceView,
    MercenaryView,
    MyShadowView,
    PartyMemberView,
    PartyView,
    ShadowView,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_mercenaries import MERCENARY_ROLES, MercenaryDef
from trpg.world.actions import (
    CompanionJoinedEvent,
    CompanionLeftEvent,
    PartyChangedEvent,
    ShadowAiChangedEvent,
    ShadowSavedEvent,
    WorldEvent,
)
from trpg.world.calendar import day_of
from trpg.world.common import world_map_of
from trpg.world.companions import companion_defs, free_slots, wanted_companions
from trpg.world.errors import WorldError
from trpg.world.narration import location_name_for
from trpg.world.opening import HIRE_PANEL_ZH, opening_limits
from trpg.world.party import hire_problem, party_mercenaries, season_boss_problem, slot_capped
from trpg.world.shadows import shadow_level, shadow_role_zh, shadow_tier
from trpg.world.state import CharacterState, ShadowReport, ShadowSnapshot, WorldState

__all__ = [
    "ai_choice_views",
    "ai_zh",
    "allies_line",
    "my_shadow_view",
    "party_event_line",
    "party_view",
    "shadow_role_zh",
]

SOLO_ZH = "獨行"
COMPANION_NOTE_ZH = "劇情夥伴：任務結束後離隊"
DEFAULT_AI_ZH = "預設"
REPORTS_SHOWN = 20


def _title(merc: MercenaryDef) -> str:
    return f"{merc.title_zh}・{MERCENARY_ROLES[merc.role]}"


def _ai_name(library: ContentLibrary, profile: str | None) -> str | None:
    if profile is None:
        return None
    found = library.ai_profiles.by_id().get(profile)
    return found.name_zh if found is not None else profile


def _ai_zh(library: ContentLibrary, chosen: str | None, default: str | None) -> str:
    """「守衛」或「預設（守衛）」；預設也沒有指定時「預設」。"""
    if chosen is not None:
        return _ai_name(library, chosen) or chosen
    name = _ai_name(library, default)
    return DEFAULT_AI_ZH if name is None else f"{DEFAULT_AI_ZH}（{name}）"


ai_zh = _ai_zh
"""AI 打法的中文（循環賽的報名也用，5F-4）。"""


def ai_choice_views(library: ContentLibrary) -> tuple[AiChoiceView, ...]:
    """可選的 AI 打法（``mercenaries.yaml`` 的 ``ai_choices``）。"""
    table = library.world_mercenaries
    profiles = library.ai_profiles.by_id()
    choices = () if table is None else table.ai_choices
    return tuple(
        AiChoiceView(
            id=p,
            name_zh=profiles[p].name_zh,
            description_zh=profiles[p].player_description_zh,
        )
        for p in choices
        if p in profiles
    )


def _mercenary_view(library: ContentLibrary, merc: MercenaryDef, hired: bool) -> MercenaryView:
    build = library.builds.by_id()[merc.build]
    hero = slot_capped(library, build.hero)  # 技能照欄位上限（玩法 PM 定 ②）
    skills = tuple(library.skills[s].name_zh if s in library.skills else s for s in hero.skills)
    return MercenaryView(
        id=merc.id,
        name_zh=merc.name_zh,
        title_zh=merc.title_zh,
        role=merc.role,
        role_zh=MERCENARY_ROLES[merc.role],
        theme_zh=build.theme_zh,
        skills_zh=skills,
        skill_ids=tuple(hero.skills),
        hired=hired,
        origin=merc.origin,
        portrait=merc.portrait,
    )


def _location_name(library: ContentLibrary, region: str, location: str) -> str:
    try:
        found = world_map_of(library, region).location_by_id().get(location)
    except WorldError:  # 舊存檔的區域被移除時只顯示 ID
        return location
    return found.name_zh if found is not None else location


_role_zh = shadow_role_zh
"""影子的定位（5F-4b 搬到 :func:`trpg.world.shadows.shadow_role_zh`，編年史也用）。"""


def _shadow_skill_names(library: ContentLibrary, snapshot: ShadowSnapshot) -> tuple[str, ...]:
    names = {s.id: s.name_zh for s in snapshot.skills}
    return tuple(
        names.get(s) or (library.skills[s].name_zh if s in library.skills else s)
        for s in snapshot.hero.skills
    )


def _shadow_view(
    library: ContentLibrary,
    char: CharacterState,
    snapshot: ShadowSnapshot,
    titles: TitlesOf = no_titles,
) -> ShadowView:
    level = shadow_level(snapshot, char.level)
    tier = shadow_tier(library, snapshot, char.level)
    capped = level < snapshot.level
    hired = any(s.owner == snapshot.owner for s in char.shadows)
    return ShadowView(
        owner=snapshot.owner,
        name_zh=snapshot.hero.name_zh,
        level=snapshot.level,
        role_zh=_role_zh(library, snapshot),
        skills_zh=_shadow_skill_names(library, snapshot),
        skill_ids=tuple(snapshot.hero.skills),
        borrowed_level=level,
        borrowed_tier=tier,
        capped=capped,
        cap_zh=f"借用時壓到 Lv {level}・技能 {tier} 階（你的上限）" if capped else None,
        hired=hired,
        # 朋友的影子存的地點：看的人還沒發現的隱藏地點用提示語（5C-3f）
        saved_zh=location_name_for(library, char, snapshot.region, snapshot.location),
        titles=titles(snapshot.owner),
    )


def _members(library: ContentLibrary, char: CharacterState) -> list[PartyMemberView]:
    builds = library.builds.by_id()
    members = [PartyMemberView(name_zh=char.hero.name_zh, title_zh="主角", level=char.level)]
    members += [
        PartyMemberView(
            name_zh=m.name_zh,
            title_zh=_title(m),
            level=char.level,
            mercenary=m.id,
            ai_zh=_ai_zh(library, char.party_ai.get(m.id), builds[m.build].hero.ai_profile),
        )
        for m in party_mercenaries(library, char)
    ]
    members += [
        PartyMemberView(
            name_zh=f"{s.hero.name_zh}的影子",
            title_zh=f"影子・{_role_zh(library, s)}",
            level=shadow_level(s, char.level),
            shadow=s.owner,
            ai_zh=_ai_zh(library, char.party_ai.get(s.owner), s.ai_profile or s.hero.ai_profile),
        )
        for s in char.shadows
    ]
    members += [
        PartyMemberView(
            name_zh=c.name_zh,
            title_zh=f"{c.title_zh}・劇情夥伴",
            level=char.level,
            companion=c.id,
            ai_zh=_ai_zh(library, None, c.ai_profile or builds[c.build].hero.ai_profile),
            note_zh=COMPANION_NOTE_ZH,
        )
        for c in companion_defs(library, char)
    ]
    return members


def companion_line(library: ContentLibrary, char: CharacterState) -> str | None:
    """夥伴在隊時的說明（見 ``PartyView.companion_zh``）；沒有夥伴時 ``None``。"""
    if not char.companions:
        return None
    quests = dict(wanted_companions(library, char))
    names: list[str] = []
    for c in companion_defs(library, char):
        quest = quests.get(c.id)
        found = None if quest is None else _quest_name(library, quest)
        names.append(c.name_zh if found is None else f"{c.name_zh}（{found}）")
    count = len(names)
    return f"{'、'.join(names)}跟著你，佔 {count} 個隊友位；任務結束後離隊"


def _quest_name(library: ContentLibrary, quest: str) -> str | None:
    for table in library.world_quests.quests.values():
        for q in table.quests:
            if q.id == quest:
                return q.name_zh
    return None


def party_view(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    *,
    in_battle: bool,
    titles: TitlesOf = no_titles,
) -> PartyView:
    """隊伍面板與雇用清單（見模組說明）。``titles``：影子主人的帳號稱號（5F-3c 玩家名片）。"""
    problem = "戰鬥中" if in_battle else hire_problem(library, char)
    if "hire" in opening_limits(char):  # OB-5／OB-6：入門期不開放雇傭兵（面板與被拒同一句）
        problem = HIRE_PANEL_ZH
    table = library.world_mercenaries
    roster = () if table is None else table.mercenaries
    boss = season_boss_problem(char)
    return PartyView(
        members=tuple(_members(library, char)),
        max_hired=0 if table is None else table.max_hired,
        can_hire=problem is None,
        hire_problem_zh=problem,
        mercenaries=tuple(_mercenary_view(library, m, m.id in char.mercenaries) for m in roster),
        shadows=tuple(
            _shadow_view(library, char, s.snapshot, titles)
            for s in world.shadows
            if s.snapshot.owner != char.character_id
        ),
        ai_choices=ai_choice_views(library),
        ai=dict(char.party_ai),
        season_boss_ok=boss is None,
        season_boss_zh=boss,
        free_slots=free_slots(library, char),
        companion_zh=companion_line(library, char),
    )


def _foes_zh(library: ContentLibrary, foes: tuple[str, ...]) -> str:
    catalog = library.enemy_catalog()
    names: list[str] = []
    for unit in foes:
        try:
            names.append(catalog.template(unit).name_zh)
        except KeyError:  # 內容改了找不到單位時顯示 ID
            names.append(unit)
    counts = Counter(names)
    ordered = list(dict.fromkeys(names))
    return "、".join(n if counts[n] == 1 else f"{n} ×{counts[n]}" for n in ordered)


def report_line(
    library: ContentLibrary, report: ShadowReport, season_start: int, viewer: CharacterState
) -> str:
    """一則戰報（例「第 3 天：你的影子幫小美在竹林小徑打倒了霧狼 ×3（+1 任務幣）」；天數從賽季開始
    那天算第 1 天，早上 6 點刷新）。地點是朋友打的：看的人（影子主人 ``viewer``）還沒發現的隱藏地點
    用提示語（5C-3f）。"""
    day = max(1, report.day - day_of(library, season_start) + 1)
    where = location_name_for(library, viewer, report.region, report.location)
    coins = f"（+{report.coins} 任務幣）" if report.coins else ""
    if report.won:
        foes = _foes_zh(library, report.foes) or "敵人"
        what = f"幫{report.borrower_name}在{where}打倒了{foes}"
    else:
        what = f"陪{report.borrower_name}在{where}奮戰，可惜落敗"
    return f"第 {day} 天：你的影子{what}{coins}"


def my_shadow_view(
    library: ContentLibrary, world: WorldState, char: CharacterState, *, in_battle: bool
) -> MyShadowView:
    """自己的影子：等級、存的地點、預設打法、累計任務幣、被借用的戰報（新的在前）。"""
    record = world.shadow_of(char.character_id)
    can_set = not in_battle and hire_problem(library, char) is None
    can_set = can_set and "hire" not in opening_limits(char)  # OB-5：入門期不能改影子打法
    ai_zh = _ai_zh(library, char.shadow_ai, char.hero.ai_profile)
    if record is None:
        return MyShadowView(saved=False, ai=char.shadow_ai, ai_zh=ai_zh, can_set_ai=can_set)
    snap = record.snapshot
    reports = tuple(
        report_line(library, r, world.season_start, char) for r in reversed(record.reports)
    )
    return MyShadowView(
        saved=True,
        level=snap.level,
        saved_zh=f"{_location_name(library, snap.region, snap.location)}・Lv {snap.level}",
        ai=char.shadow_ai,
        ai_zh=ai_zh,
        can_set_ai=can_set,
        coins=record.coins,
        reports_zh=reports[:REPORTS_SHOWN],
    )


def allies_line(library: ContentLibrary, char: CharacterState, hero_hp: int) -> str:
    """遇敵面板的我方說明（例「主角（開場 HP 30）＋青鋒、阿霧的影子」；沒有隊友「・獨行」）。"""
    hero = f"主角（開場 HP {hero_hp}{'，疲憊' if char.fatigued else ''}）"
    names = [m.name_zh for m in party_mercenaries(library, char)]
    names += [f"{s.hero.name_zh}的影子" for s in char.shadows]
    names += [c.name_zh for c in companion_defs(library, char)]
    if names:
        return f"{hero}＋{'、'.join(names)}"
    return f"{hero}・{SOLO_ZH}"


def _companion_event_line(
    library: ContentLibrary, event: CompanionJoinedEvent | CompanionLeftEvent
) -> str:
    table = library.world_mercenaries
    known = {} if table is None else table.companion_by_id()
    name = known[event.companion].name_zh if event.companion in known else event.companion
    if isinstance(event, CompanionJoinedEvent):
        swap = f"（替下{event.replaced_name}）" if event.replaced_name else ""
        return f"{name}加入隊伍{swap}：劇情夥伴，任務結束後離隊。"
    back = f"，{event.restored_name}回到隊上" if event.restored_name else ""
    return f"{name}離開隊伍{back}。"


def party_event_line(library: ContentLibrary, _region: str, event: WorldEvent) -> str | None:
    """``party_changed``、``shadow_saved``、``shadow_ai_changed``、夥伴加入與離隊的句子。"""
    if isinstance(event, CompanionJoinedEvent | CompanionLeftEvent):
        return _companion_event_line(library, event)
    if isinstance(event, ShadowSavedEvent):
        return f"已把目前的配置存成影子（Lv {event.level}）。"
    if isinstance(event, ShadowAiChangedEvent):
        name = _ai_name(library, event.profile) or DEFAULT_AI_ZH
        return f"影子的預設打法：{name}。"
    if not isinstance(event, PartyChangedEvent):
        return None
    if not event.mercenaries and not event.shadows:
        return f"隊伍：{SOLO_ZH}（只帶主角）。"
    known = {} if library.world_mercenaries is None else library.world_mercenaries.by_id()
    parts: list[str] = []
    if event.mercenaries:
        names = [known[m].name_zh if m in known else m for m in event.mercenaries]
        parts.append(f"雇用{'、'.join(names)}")
    if event.shadow_names:
        parts.append(f"借用{'、'.join(f'{n}的影子' for n in event.shadow_names)}")
    return f"隊伍：{'；'.join(parts)}（免費）。"
