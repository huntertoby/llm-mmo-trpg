"""大世界成長的顯示資料（Phase 5A-7；``docs/phases/Phase5計畫.md`` 13.2）：主角面板與待選閃現（一輪
格式）、成長與誓約的可用狀態、下一場修正、開場說明（先手、開場狀態、增援）、最近一次戰鬥結果、成長
事件的中文句子。規則一律呼叫 ``trpg.world``，這裡只組裝文字。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from trpg.api.run_presenter import hero_out, pending_flash_out
from trpg.api.run_schemas import HeroOut, PendingFlashOut
from trpg.api.world_schemas import (
    GrowthView,
    HeroStatusView,
    OathCurrentView,
    OathParamView,
    OathTemplateView,
    OathView,
)
from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathTable, OathTemplateDef
from trpg.engine.battle import OPENING_STATUS_MAX_DURATION
from trpg.shared.types import Attribute, Team
from trpg.world.actions import (
    AttributesAllocatedEvent,
    AttributesRespeccedEvent,
    BattleStartedEvent,
    FlashOfferedEvent,
    FlashPickedEvent,
    InsightGainedEvent,
    LeveledUpEvent,
    OathBrokenEvent,
    OathKeptEvent,
    OathReleasedEvent,
    OathSwornEvent,
    SkillDissolvedEvent,
    SkillInheritedEvent,
    SkillTierChangedEvent,
    WorldEvent,
)
from trpg.world.growth import (
    OATH_PASSIVE_SLOTS,
    as_run,
    at_service,
    flash_blocked_zh,
    hero_tier,
    passive_count,
    skill_seed,
    world_library,
)
from trpg.world.opening import opening_limits
from trpg.world.state import CharacterState, LastBattle, NextBattleMod, WorldState

__all__ = [
    "DIFFICULTY_ZH",
    "SERVICE_ZH",
    "STARTER_RESPEC_ZH",
    "UNAVAILABLE_ZH",
    "growth_event_line",
    "growth_view",
    "hero_panel",
    "hero_status_views",
    "last_battle_line",
    "next_battle_lines",
    "oath_view",
    "opening_lines",
    "skill_names",
]

SERVICE_ZH: Final = "閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火（和換技能同一處）"
STARTER_RESPEC_ZH: Final = "入門期可以自己配點，正式選定時會照新武器重配一次。"
"""入門期接在 :data:`SERVICE_ZH` 那一行後面（OB-6，玩法 PM「OB-5b 後補定」；前半句照現在的字）。"""
UNAVAILABLE_ZH: Final = "尚未開放"
SLOT_ZH: Final = "誓約佔 1 格被動欄位（立誓後被動技能最多裝 2 招）"
JUDGE_IN_BATTLE_ZH: Final = "戰鬥中判定：違反時立刻移除加成"
JUDGE_AT_END_ZH: Final = "戰鬥結束時判定（沒達到：破誓帶到下一場開場）"
PERMILLE_ONE: Final = 1000
DIFFICULTY_ZH: Final[dict[str, str]] = {"easy": "易", "medium": "中", "hard": "難"}
_END_REASON_ZH: Final[dict[str, str]] = {"max_rounds": "輪數用完"}


# ---------------------------------------------------------------------------
# 主角面板（一輪格式）
# ---------------------------------------------------------------------------


def hero_panel(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> tuple[HeroOut, PendingFlashOut | None]:
    """一輪格式的主角面板與待選閃現（用大世界的內容庫視圖，角色階級照 07 7.6）。"""
    lib = world_library(library)
    run = as_run(char, seed=skill_seed(world, char))
    return hero_out(lib, run), pending_flash_out(lib, run)


def skill_names(library: ContentLibrary, char: CharacterState) -> dict[str, str]:
    """技能 ID → 中文名（內容庫、生成技能、閃現前的原本技能）。"""
    names = {k: s.name_zh for k, s in library.skills.items()}
    for skill in (*char.flash_bases, *char.generated_skills):
        names[skill.id] = skill.name_zh
    return names


# ---------------------------------------------------------------------------
# 成長與誓約
# ---------------------------------------------------------------------------


def growth_view(library: ContentLibrary, char: CharacterState, *, in_battle: bool) -> GrowthView:
    service = at_service(library, char)
    pending = char.pending_flash is not None
    blocked: str | None = None
    if in_battle:
        blocked = "戰鬥進行中"
    elif pending:
        blocked = "先選完閃現的變化"
    elif char.pending_encounter is not None:
        blocked = "先處理眼前的遭遇"
    elif not service:
        blocked = "這裡不是城鎮或營火"
    free = not in_battle and not pending and char.pending_encounter is None
    flash_blocked = flash_blocked_zh(char)  # OB-3（#150 第 6 點）
    return GrowthView(
        insight=char.insight,
        skill_tier=char.skill_tier or hero_tier(library, char.level),
        at_service=service,
        service_zh=SERVICE_ZH,
        can_allocate=free and char.attribute_points > 0,
        can_spend=free and service,
        blocked_zh=blocked,
        pending=pending,
        can_flash=free and service and flash_blocked is None,
        flash_blocked_zh=flash_blocked,
        starter_note_zh=STARTER_RESPEC_ZH
        if char.opening is not None and char.opening.stage == "starter"
        else None,
    )


def _duration_zh(seconds: int) -> str:
    total = (max(seconds, 0) + 59) // 60
    hours, minutes = divmod(total, 60)
    if hours == 0:
        return f"{minutes} 分鐘"
    return f"{hours} 小時" if minutes == 0 else f"{hours} 小時 {minutes} 分鐘"


def _bonus_zh(library: ContentLibrary, table: OathTable, difficulty: str) -> str:
    """難度檔的加成：〔狀態名〕＋造成／受到的傷害百分比（從狀態的數值算，不寫死）。"""
    status_id = table.bonuses.get(difficulty)  # type: ignore[call-overload]
    if status_id is None:
        return "沒有加成"
    status = library.ruleset.status_def(status_id)
    effect = _permille_zh(status.damage_dealt_permille, status.damage_taken_permille)
    return f"〔{status.name_zh}〕{effect}"


def _permille_zh(dealt: int, taken: int) -> str:
    parts: list[str] = []
    if dealt != PERMILLE_ONE:
        parts.append(f"造成的攻擊傷害 {_signed_percent(dealt)}")
    if taken != PERMILLE_ONE:
        parts.append(f"受到的傷害 {_signed_percent(taken)}")
    return "：" + "、".join(parts) if parts else ""


def _signed_percent(permille: int) -> str:
    delta = permille - PERMILLE_ONE
    sign = "+" if delta > 0 else "−"
    whole, rest = divmod(abs(delta), 10)
    return f"{sign}{whole}%" if rest == 0 else f"{sign}{abs(delta) / 10:g}%"


def _template_bonus_zh(library: ContentLibrary, table: OathTable, template: OathTemplateDef) -> str:
    by = template.difficulty_by
    if by is None:
        return _bonus_zh(library, table, template.difficulty)
    param = template.param_by_id()[by.param]
    return "；".join(
        f"{param.name_zh or param.id} {value}：{_bonus_zh(library, table, level)}"
        for value, level in by.levels.items()
    )


def _judge_zh(template: OathTemplateDef) -> str:
    if template.check is None:
        return ""
    if template.check.at_end:
        return JUDGE_AT_END_ZH
    if template.check.kind == "solo":
        return "開場判定：帶著隊友出戰就違反"
    return JUDGE_IN_BATTLE_ZH


def _templates(library: ContentLibrary, table: OathTable) -> tuple[OathTemplateView, ...]:
    return tuple(
        OathTemplateView(
            id=t.id,
            name_zh=t.name_zh,
            difficulty=t.difficulty,
            difficulty_zh=_difficulty_label(t),
            params=tuple(
                OathParamView(
                    id=p.id,
                    kind=p.kind,
                    choices=p.choices,
                    min=p.min,
                    max=p.max,
                    name_zh=p.name_zh,
                    choice_names_zh=dict(p.choice_names_zh),
                )
                for p in t.params
            ),
            description_zh=t.description_zh,
            bonus_zh=_template_bonus_zh(library, table, t),
            judge_zh=_judge_zh(t),
        )
        for t in table.templates
    )


def _difficulty_label(template: OathTemplateDef) -> str:
    by = template.difficulty_by
    if by is None:
        return DIFFICULTY_ZH[template.difficulty]
    return "／".join(dict.fromkeys(DIFFICULTY_ZH[level] for level in by.levels.values()))


def _penalty_zh(library: ContentLibrary, table: OathTable | None) -> str:
    if table is None or table.penalty_status is None:
        return ""
    status = library.ruleset.status_def(table.penalty_status)
    effect = _permille_zh(status.damage_dealt_permille, status.damage_taken_permille)
    return (
        f"違反：本場加成移除＋〔{status.name_zh}〕{table.penalty_rounds} 回合{effect}；"
        "下一場恢復（戰鬥結束時才判定的誓約，破誓帶到下一場開場）"
    )


def _swear_problem(
    library: ContentLibrary, char: CharacterState, now: int, *, in_battle: bool
) -> str | None:
    """不能立誓的原因（照 ``trpg.world.growth`` 的檢查順序）；可以時 ``None``。"""
    checks: tuple[tuple[bool, str], ...] = (
        (library.world_oaths is None, UNAVAILABLE_ZH),
        (in_battle, "戰鬥進行中"),
        (char.pending_flash is not None, "先選完閃現的變化"),
        (char.pending_encounter is not None, "先處理眼前的遭遇"),
        (not at_service(library, char), "只有城鎮與營火能立誓"),
        (char.oath is not None, "同時只能有 1 個誓約，請先解除目前的誓約"),
        (now < char.oath_cooldown_until, "解除誓約後 1 天內不能再立誓"),
        (
            passive_count(library, char) + OATH_PASSIVE_SLOTS
            > library.ruleset.core.skill_slots.passive,
            "誓約佔一格被動欄位，先卸下一招被動",
        ),
    )
    return next((text for failed, text in checks if failed), None)


def oath_view(
    library: ContentLibrary, char: CharacterState, now: int, *, in_battle: bool
) -> OathView:
    table = library.world_oaths
    current = None
    if char.oath is not None:
        template = None if table is None else table.template_by_id().get(char.oath.template)
        params = char.oath.params
        current = OathCurrentView(
            template=char.oath.template,
            name_zh=template.name_zh if template is not None else char.oath.template,
            difficulty_zh=DIFFICULTY_ZH[char.oath.difficulty],
            params_zh=(
                template.params_zh(params)
                if template is not None
                else "、".join(f"{k}＝{v}" for k, v in params.items())
            ),
            sworn_at=char.oath.sworn_at,
            bonus_zh="" if table is None else _bonus_zh(library, table, char.oath.difficulty),
            judge_zh="" if template is None else _judge_zh(template),
        )
    cooling = now < char.oath_cooldown_until
    problem = _swear_problem(library, char, now, in_battle=in_battle)
    problem = opening_limits(char).get("oath") or problem  # OB-5：入門期不開放誓約
    return OathView(
        available=table is not None,
        unavailable_zh=UNAVAILABLE_ZH if table is None else None,
        current=current,
        cooldown_until=char.oath_cooldown_until,
        cooldown_zh=_duration_zh(char.oath_cooldown_until - now) if cooling else None,
        can_swear=problem is None,
        swear_problem_zh=problem,
        can_release=char.oath is not None and not in_battle and char.pending_flash is None,
        templates=() if table is None else _templates(library, table),
        penalty_zh=_penalty_zh(library, table),
        slot_zh=SLOT_ZH if table is not None else "",
    )


# ---------------------------------------------------------------------------
# 下一場修正、開場說明
# ---------------------------------------------------------------------------


def _opening_rounds(library: ContentLibrary, status: str) -> int | None:
    default = library.ruleset.status_def(status).duration
    return None if default is None else min(default, OPENING_STATUS_MAX_DURATION)


def _rounds_zh(rounds: int | None) -> str:
    return "不倒數" if rounds is None else f"{rounds} 回合"


def next_battle_lines(library: ContentLibrary, mods: tuple[NextBattleMod, ...]) -> tuple[str, ...]:
    """角色身上的下一場修正（每筆一句）。"""
    lines: list[str] = []
    for mod in mods:
        if mod.kind == "reinforce":
            lines.append("下一場：敵人增援 1 名（看陣容時就看得到）。")
            continue
        assert mod.status is not None
        status = library.ruleset.status_def(mod.status)
        tag = "增益" if mod.kind == "buff" else "減益"
        rounds = _rounds_zh(_opening_rounds(library, mod.status))
        lines.append(
            f"下一場開場：主角帶〔{status.name_zh}〕（{tag}，{rounds}）：{status.description_zh}"
        )
    return tuple(lines)


def hero_status_views(
    library: ContentLibrary, statuses: tuple[str, ...]
) -> tuple[HeroStatusView, ...]:
    views: list[HeroStatusView] = []
    for status_id in statuses:
        status = library.ruleset.status_def(status_id)
        views.append(
            HeroStatusView(
                id=status_id,
                name_zh=status.name_zh,
                description_zh=status.description_zh,
                beneficial=status.beneficial,
                rounds=_opening_rounds(library, status_id),
            )
        )
    return tuple(views)


def opening_lines(
    library: ContentLibrary,
    *,
    first_team: Team | None,
    hero_statuses: tuple[str, ...],
    reinforcements: int,
    oath: str | None = None,
    oath_bonus: str | None = None,
) -> tuple[str, ...]:
    """開場說明（5A-6b：先手只影響第 1 輪；開場狀態不擲抵抗、最多 2 回合；代決 5A7-6）。"""
    lines: list[str] = []
    if first_team is Team.ALLY:
        lines.append("我方先手：第 1 輪我方全部先動，第 2 輪起照先攻。")
    elif first_team is Team.ENEMY:
        lines.append("敵方先手：第 1 輪敵人全部先動，第 2 輪起照先攻。")
    for view in hero_status_views(library, hero_statuses):
        lines.append(
            f"開場狀態：主角帶〔{view.name_zh}〕{_rounds_zh(view.rounds)}"
            f"（不擲抵抗）：{view.description_zh}"
        )
    if reinforcements > 0:
        lines.append(f"敵人增援 {reinforcements} 名（已在陣容裡）。")
    line = _oath_opening(library, oath, oath_bonus)
    if line is not None:
        lines.append(line)
    return tuple(lines)


def _oath_opening(
    library: ContentLibrary, template_id: str | None, bonus: str | None
) -> str | None:
    """「誓約「名稱」：主角帶〔誓約之力・中〕：…，違反就移除。」；沒有誓約時 ``None``（5C-3）。"""
    table = library.world_oaths
    if template_id is None or table is None:
        return None
    template = table.template_by_id().get(template_id)
    name = template.name_zh if template is not None else template_id
    if bonus is None:
        return f"誓約「{name}」：主角開場帶誓約之力，違反就移除。"
    status = library.ruleset.status_def(bonus)
    effect = _permille_zh(status.damage_dealt_permille, status.damage_taken_permille)
    return f"誓約「{name}」：主角帶〔{status.name_zh}〕{effect}，違反就移除。"


# ---------------------------------------------------------------------------
# 最近一次戰鬥、成長事件
# ---------------------------------------------------------------------------


def last_battle_line(
    last: LastBattle | None, location_name: Callable[[str, str], str]
) -> str | None:
    """最近一次戰鬥結果的一句話（5A-5 待決 1）；``location_name(region, location)``。"""
    if last is None:
        return None
    where = location_name(last.region, last.location)
    if last.won:
        text = f"最近一次戰鬥（{where}）：打贏了（{last.rounds} 輪），獲得 {last.xp_gained} 經驗"
        if last.level > last.level_before:
            text += f"，升到 {last.level} 級"
        return text + "。"
    reason = _END_REASON_ZH.get(last.end_reason or "", "全滅")
    return f"最近一次戰鬥（{where}）：失敗（{reason}，{last.rounds} 輪）。"


def _attrs_zh(attributes: dict[Attribute, int]) -> str:
    return "、".join(f"{a.display_name} ＋{n}" for a, n in attributes.items() if n > 0)


def _quest_title(library: ContentLibrary, quest: str) -> str:
    """任務 ID → 名稱（6F-1：靈感點提示不露出原始 ID）；找不到為空字串。"""
    for region in sorted(library.world_quests.quests):
        for q in library.world_quests.quests[region].quests:
            if q.id == quest:
                return q.name_zh
    return ""


def _insight_source(library: ContentLibrary, source: str) -> str:
    kind, _, rest = source.partition(":")
    if kind == "quest":
        title = _quest_title(library, rest)
        return f"任務「{title}」" if title else "任務獎勵"
    if kind != "elite":
        return "得到靈感"  # 6F-1：不認得的來源也不露出原始 ID
    unit, _, affix = rest.partition("+")
    catalog = library.enemy_catalog()
    try:
        name = catalog.template(unit).name_zh
    except KeyError:
        name = unit
    if affix:
        try:
            name = f"{name}（{catalog.affix(affix).name_zh}）"
        except KeyError:
            name = f"{name}（{affix}）"
    return f"首次擊敗精英「{name}」"


def _battle_started_line(library: ContentLibrary, event: BattleStartedEvent) -> str | None:
    lines = opening_lines(
        library,
        first_team=event.first_team,
        hero_statuses=event.hero_statuses,
        reinforcements=event.reinforcements,
        oath=event.oath,
    )
    return "開戰：" + "".join(lines) if lines else None


def _level_line(library: ContentLibrary, event: WorldEvent, names: dict[str, str]) -> str | None:
    del names
    if isinstance(event, BattleStartedEvent):
        return _battle_started_line(library, event)
    if isinstance(event, LeveledUpEvent):
        return (
            f"升到 {event.level} 級！（未分配屬性點 {event.attribute_points}、"
            f"靈感點 {event.insight}、角色階級 {event.skill_tier}）"
        )
    if isinstance(event, InsightGainedEvent):
        source = _insight_source(library, event.source)
        return (
            f"{source}：靈感 ＋{event.amount}（共 {event.insight} 點），"
            "可以在成長面板（G）讓技能閃現。"
        )
    if isinstance(event, SkillTierChangedEvent):
        return f"角色升到 {event.to_tier} 階：主角的技能照新階級重配了。"
    return None


def _attribute_line(
    library: ContentLibrary, event: WorldEvent, names: dict[str, str]
) -> str | None:
    del library, names
    if isinstance(event, AttributesAllocatedEvent):
        return f"分配屬性點：{_attrs_zh(event.attributes)}（剩 {event.attribute_points} 點）。"
    if isinstance(event, AttributesRespeccedEvent):
        return f"重配屬性：退回後共有 {event.attribute_points} 點可以重新分配。"
    return None


def _skill_line(library: ContentLibrary, event: WorldEvent, names: dict[str, str]) -> str | None:
    del library

    def name(skill: str) -> str:
        return names.get(skill, skill)

    if isinstance(event, FlashOfferedEvent):
        what = "閃現" if event.slot is None else f"重閃第 {event.slot} 次"
        return (
            f"{what}「{name(event.skill)}」：花 {event.cost} 點靈感，出 {event.options} 個變化"
            f"（剩 {event.insight} 點），一定要選一個。"
        )
    if isinstance(event, FlashPickedEvent):
        old, new = name(event.skill), name(event.new_skill)
        if old == new:
            return f"選好變化：「{old}」換上新的變化。"
        return f"選好變化：「{old}」→「{new}」。"
    if isinstance(event, SkillDissolvedEvent):
        return f"溶掉「{name(event.skill)}」：退回 {event.refund} 點靈感（共 {event.insight} 點）。"
    if isinstance(event, SkillInheritedEvent):
        return f"「{name(event.source)}」的變化傳承給「{name(event.new_skill)}」。"
    return None


def _oath_line(library: ContentLibrary, event: WorldEvent, names: dict[str, str]) -> str | None:
    del names
    table = library.world_oaths
    by_id = {} if table is None else table.template_by_id()

    def oath_name(template: str) -> str:
        found = by_id.get(template)
        return found.name_zh if found is not None else template

    if isinstance(event, OathSwornEvent):
        level = DIFFICULTY_ZH[event.oath.difficulty]
        return f"立誓：「{oath_name(event.oath.template)}」（難度 {level}）。"
    if isinstance(event, OathReleasedEvent):
        return f"解除誓約「{oath_name(event.template)}」：現實 1 天內不能再立誓。"
    if isinstance(event, OathBrokenEvent):
        if event.at_end:
            return (
                f"戰鬥結束：沒有守住誓約「{oath_name(event.template)}」，"
                "破誓 2 回合帶到下一場開場（下一場的誓約加成照常）。"
            )
        return f"違反誓約「{oath_name(event.template)}」：加成移除、陷入破誓；下一場恢復。"
    if isinstance(event, OathKeptEvent):
        return f"守住了誓約「{oath_name(event.template)}」。"
    return None


_GROWTH_LINES = (_level_line, _attribute_line, _skill_line, _oath_line)


def growth_event_line(
    library: ContentLibrary, event: WorldEvent, names: dict[str, str]
) -> str | None:
    """成長事件與開戰的句子（5A-7）；不是這些事件時 ``None``。"""
    for make in _GROWTH_LINES:
        line = make(library, event, names)
        if line is not None:
            return line
    return None
