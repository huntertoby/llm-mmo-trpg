"""大世界的角色成長接點（Phase 5A-6；``docs/phases/Phase5計畫.md`` 第 11 節）。

**重用 roguelite，不搬家**（第 2.2 節）：角色轉成 roguelite 的 ``RunState``（:func:`as_run`），呼叫
:mod:`trpg.roguelite` 的純函式（配點、重配、閃現、溶掉、傳承、升階重配、換技能），再把成長欄位寫回
角色（:func:`from_run`）。roguelite 的函式簽名與原型行為都不改：

- **角色階級照 07 7.6**（1～3 級 1 階、4～7 級 2 階、8～10 級 3 階）：roguelite 從
  ``library.roguelite.offer_tier_by_level`` 查階級，所以大世界一律用 :func:`world_library` 的內容庫
  視圖——只把那張表換成 ``world/rules.yaml`` 的 ``hero_growth.skill_tier_by_level``（同
  ``trpg.sim`` 用 ``dataclasses.replace`` 換內容的做法）。原型照舊用 ``[1,1,2,2,3,3]``。
- **升級共用一個函式**（:func:`gain_xp`）：戰鬥、情境判定（之後的任務）加經驗後立刻判定升級；每級
  屬性點、靈感點（06 6.34.2 大世界每級 2 點）、HP／法力上限同步；跨過 4、8 級時主角技能照新階級重配
  （roguelite ``sync_skill_tier``）。
- **世界動作**：配點、重配、閃現、選閃現、溶掉、傳承、立誓、解除誓約（:func:`apply_growth`）。花靈感
  與重配只在城鎮與營火（06 6.34.2 大世界表、07 7.2；代決 5A6-6）。

確定性：閃現選項、傳承與升階重配的種子是角色技能種子 :func:`skill_seed`
（``fnv1a64("{season_seed}:{character_id}:skills")``，不佔世界亂數串流）；選項存在角色的
``pending_flash``，選擇時不重抽。

**LLM 閃現提議**（6L-2，06 6.34.7）：出題時向生成內容的供應者（:mod:`trpg.world.generated`；API 層的
預先生成暫存區）要這一題的變化提議，題目帶原技能取得地點的界域（:func:`skill_region`，#126）；
拿不到（模型關閉、沒趕上、驗證失敗）就照舊用模板。最後給出的提議連同來源記進日誌，重播只讀日誌、
不呼叫 LLM。
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Mapping
from typing import Final

from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathTable, oath_problems
from trpg.roguelite.attributes import allocate_attributes, respec_attributes
from trpg.roguelite.errors import RunError
from trpg.roguelite.flashes import (
    dissolve,
    flash_request,
    inherit,
    open_flash,
    owned_skills,
    pick_flash,
    problem_of,
)
from trpg.roguelite.growth import set_loadout
from trpg.roguelite.progress import with_hp_change
from trpg.roguelite.retier import sync_skill_tier
from trpg.roguelite.start import recommended_level_up
from trpg.roguelite.state import (
    CampfireNode,
    DissolveChoice,
    FlashChoice,
    FlashLlmRecord,
    FlashPickChoice,
    InheritChoice,
    RunState,
)
from trpg.shared.rng import fnv1a64
from trpg.skillgen.flash_offer import FlashOptionSource, FlashRequest, UsageSource
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.flash_text import VariationText, text_map
from trpg.world.actions import (
    AllocateAction,
    AttributesAllocatedEvent,
    AttributesRespeccedEvent,
    DissolveAction,
    FlashAction,
    FlashOfferedEvent,
    FlashPickAction,
    FlashPickedEvent,
    InheritAction,
    LeveledUpEvent,
    OathReleasedEvent,
    OathSwornEvent,
    ReleaseOathAction,
    RespecAction,
    SkillDissolvedEvent,
    SkillInheritedEvent,
    SkillTierChangedEvent,
    SwearOathAction,
    WorldEvent,
)
from trpg.world.common import here, rules_of
from trpg.world.errors import WorldActionError
from trpg.world.generated import FlashGen, FlashGenRequest, flash_key, supply
from trpg.world.opening_limits import FLASH_ZH
from trpg.world.state import CharacterState, LocationRef, OathState, WorldState

__all__ = [
    "GROWTH_ACTIONS",
    "OPENING_END_LEVEL",
    "GrowthAction",
    "apply_growth",
    "as_run",
    "at_service",
    "char_library",
    "flash_blocked_zh",
    "from_run",
    "gain_xp",
    "hero_tier",
    "loadout_skills",
    "passive_count",
    "skill_region",
    "skill_seed",
    "sync_tier",
    "with_skill_region",
    "world_level_for",
    "world_library",
    "xp_to_level",
]

type GrowthAction = (
    AllocateAction
    | RespecAction
    | FlashAction
    | FlashPickAction
    | DissolveAction
    | InheritAction
    | SwearOathAction
    | ReleaseOathAction
)
GROWTH_ACTIONS: Final = (
    AllocateAction,
    RespecAction,
    FlashAction,
    FlashPickAction,
    DissolveAction,
    InheritAction,
    SwearOathAction,
    ReleaseOathAction,
)

OATH_PASSIVE_SLOTS: Final = 1
"""誓約佔的被動欄位數（06 6.26「佔一格被動欄位」）。"""

_VIEW_CACHE_LIMIT = 8
_views: dict[tuple[int, bool], tuple[ContentLibrary, ContentLibrary]] = {}
"""內容庫 → 大世界視圖的快取（只為了沿用視圖上的重配快取；存著原內容庫本身，``id`` 不會被重用）。"""


# ---------------------------------------------------------------------------
# 內容庫視圖、種子、RunState 轉換
# ---------------------------------------------------------------------------


OPENING_END_LEVEL: Final = 4
"""開局在這一級結束（21.5 #150 第 5、6、9 點「4 級前」：一律看等級）：正式選定過的角色到這一級，
免費重選過期、可以閃現，``opening`` 清成 ``None``
（:func:`trpg.world.opening_reselect.close_opening`）。"""


def flash_blocked_zh(char: CharacterState) -> str | None:
    """不能閃現的原因（#150 第 6 點）：開局還沒結束（``opening`` 非 ``None``）的角色
    :data:`OPENING_END_LEVEL` 級前不能閃現（避免閃過的招被重選收回）；靈感照常累積。已完成開局的
    舊角色不受影響（``None``）。"""
    if char.opening is None or char.level >= OPENING_END_LEVEL:
        return None
    return FLASH_ZH.format(level=OPENING_END_LEVEL)


def world_library(library: ContentLibrary, *, oath: bool = False) -> ContentLibrary:
    """roguelite 成長函式在大世界用的內容庫：只把 ``offer_tier_by_level`` 換成 07 7.6 的主角
    階級表。``oath``：角色有誓約時被動欄位少 1 格（06 6.26「佔一格被動欄位」，5C-3）。"""
    key = (id(library), oath)
    cached = _views.get(key)
    if cached is not None and cached[0] is library:
        return cached[1]
    table = rules_of(library).hero_growth.skill_tier_by_level
    roguelite = library.roguelite.model_copy(update={"offer_tier_by_level": table})
    view = dataclasses.replace(library, roguelite=roguelite)
    if oath:
        core = library.ruleset.core
        slots = core.skill_slots.model_copy(
            update={"passive": max(0, core.skill_slots.passive - OATH_PASSIVE_SLOTS)}
        )
        ruleset = library.ruleset.model_copy(
            update={"core": core.model_copy(update={"skill_slots": slots})}
        )
        view = dataclasses.replace(view, ruleset=ruleset)
    if len(_views) >= _VIEW_CACHE_LIMIT:
        _views.clear()
    _views[key] = (library, view)
    return view


def char_library(library: ContentLibrary, char: CharacterState) -> ContentLibrary:
    """這個角色裝技能時用的內容庫視圖（有誓約時被動欄位少 1 格）。"""
    return world_library(library, oath=char.oath is not None)


def passive_count(library: ContentLibrary, char: CharacterState) -> int:
    """主角裝備中的被動技能數（含生成技能）。"""
    generated = {s.id: s for s in char.generated_skills}
    defs = [generated.get(s) or library.skills.get(s) for s in char.hero.skills]
    return sum(1 for d in defs if d is not None and d.kind == "passive")


def hero_tier(library: ContentLibrary, level: int) -> int:
    """主角在 ``level`` 級的角色階級（07 7.6）。"""
    return rules_of(library).hero_growth.tier_for(level)


def skill_seed(world: WorldState, char: CharacterState) -> int:
    """角色技能種子（閃現選項、傳承、升階重配；代決 5A6-11）。"""
    return fnv1a64(f"{world.season_seed}:{char.character_id}:skills".encode())


_TIER_SUFFIX = re.compile(r"^(.+)_t\d+$")


def skill_region(char: CharacterState, skill_id: str) -> str | None:
    """``skill_id`` 取得地點的區域（6L-2，#126）：先查 ``skill_regions``，查不到就沿著閃現前的原本
    技能（``flash[...].base_id``）與階級重配前的 ID（``<原 ID>_t<階級>``）往回找；都沒有＝``None``
    （中性：創角、舊存檔）。"""
    regions = char.skill_regions
    current = skill_id
    for _ in range(8):
        if current in regions:
            return regions[current]
        state = char.flash.get(current)
        if state is not None and state.base_id != current:
            current = state.base_id
            continue
        found = _TIER_SUFFIX.match(current)
        if found is None:
            return None
        current = found.group(1)
    return None


def with_skill_region(char: CharacterState, skill_id: str, region: str | None) -> CharacterState:
    """記下 ``skill_id`` 的取得區域（``None`` 不記；依 ID 排序）。"""
    if region is None or char.skill_regions.get(skill_id) == region:
        return char
    regions = {**char.skill_regions, skill_id: region}
    return char.model_copy(update={"skill_regions": dict(sorted(regions.items()))})


def as_run(char: CharacterState, *, seed: int = 0) -> RunState:
    """角色轉成 roguelite 的 ``RunState``（成長欄位同名同型別；一輪的進度欄位用空值）。"""
    return RunState(
        seed=seed,
        hero=char.hero,
        origin=char.origin,
        level=char.level,
        xp=char.xp,
        hp=char.hp,
        mana=char.mana,
        stamina=char.stamina,
        source=0,
        generated_skills=char.generated_skills,
        skill_tier=char.skill_tier,
        plan=(),
        insight=char.insight,
        flash=char.flash,
        flash_bases=char.flash_bases,
        pending_flash=char.pending_flash,
        bench=char.bench,
        skill_usage=char.skill_usage,
        attribute_points=char.attribute_points,
        attribute_spent=char.attribute_spent,
        node=CampfireNode(after_battle=0),
    )


def from_run(char: CharacterState, run: RunState) -> CharacterState:
    """把 ``run`` 的成長欄位寫回角色。"""
    return char.model_copy(
        update={
            "hero": run.hero,
            "level": run.level,
            "xp": run.xp,
            "hp": run.hp,
            "mana": run.mana,
            "stamina": run.stamina,
            "generated_skills": run.generated_skills,
            "skill_tier": run.skill_tier,
            "insight": run.insight,
            "flash": run.flash,
            "flash_bases": run.flash_bases,
            "pending_flash": run.pending_flash,
            "bench": run.bench,
            "skill_usage": run.skill_usage,
            "attribute_points": run.attribute_points,
            "attribute_spent": run.attribute_spent,
        }
    )


def at_service(library: ContentLibrary, char: CharacterState) -> bool:
    """在城鎮或營火（``camped_at`` 是目前地點）：換技能、花靈感、重配、立誓的地點（07 7.6）。"""
    at_camp = char.camped_at == LocationRef(region=char.region, location=char.location)
    return at_camp or here(library, char).kind == "town"


def _require_service(library: ContentLibrary, char: CharacterState, what: str) -> None:
    if char.pending_encounter is not None:
        raise WorldActionError(f"還有沒處理的遭遇，不能{what}")
    if not at_service(library, char):
        raise WorldActionError(f"只有城鎮與營火能{what}")


# ---------------------------------------------------------------------------
# 經驗、升級與升階
# ---------------------------------------------------------------------------


def world_level_for(library: ContentLibrary, xp: int) -> int:
    """累計經驗 ``xp`` 對應的等級（``hero_growth.level_thresholds``，5A-SIM2；不套上限）。"""
    return 1 + sum(1 for t in rules_of(library).hero_growth.level_thresholds if xp >= t)


def xp_to_level(library: ContentLibrary, char: CharacterState, level: int) -> int:
    """補到剛好 ``level`` 級還差多少經驗（6F-4 C2，新手鏈每步升 1 級）：已經到了（或門檻表沒有這一
    級）＝0。"""
    thresholds = rules_of(library).hero_growth.level_thresholds
    index = level - 2  # 門檻表第 i 項＝升到第 i＋2 級
    if index < 0 or index >= len(thresholds):
        return 0
    return max(0, thresholds[index] - char.xp)


def gain_xp(
    library: ContentLibrary, world: WorldState, char: CharacterState, xp: int
) -> tuple[CharacterState, list[WorldEvent]]:
    """加經驗並立刻判定升級（所有經驗來源共用）。等級照世界門檻、不超過 ``level_cap``；每級屬性點、
    靈感點、HP／法力上限同步（同 roguelite ``with_hp_change``）；升完後角色階級變了就重配技能。"""
    growth = rules_of(library).hero_growth
    char = char.model_copy(update={"xp": char.xp + xp})
    target = min(world_level_for(library, char.xp), growth.level_cap)
    events: list[WorldEvent] = []
    while char.level < target:
        before = as_run(char)
        leveled = before.model_copy(
            update={
                "level": before.level + 1,
                "attribute_points": before.attribute_points
                + library.roguelite.attribute_points_per_level,
                "insight": before.insight + growth.insight_per_level,
            }
        )
        char = from_run(char, with_hp_change(library, before, leveled))
        events.append(
            LeveledUpEvent(
                level=char.level,
                attribute_points=char.attribute_points,
                insight=char.insight,
                skill_tier=hero_tier(library, char.level),
            )
        )
    if events:
        char, tier_events = sync_tier(library, world, char)
        events += tier_events
        char, allocated = _starter_allocate(library, char)
        events += allocated
    return char, events


def _starter_allocate(
    library: ContentLibrary, char: CharacterState
) -> tuple[CharacterState, list[WorldEvent]]:
    """入門期（#150 第 2 點，``opening.stage == "starter"``）升級的屬性點照推薦配法直接配掉；其他
    角色不變（點數累積，等配點教學）。配法同教學的推薦（:func:`recommended_level_up`，起始兩招）。"""
    if char.opening is None or char.opening.stage != "starter" or char.attribute_points <= 0:
        return char, []
    generated = {s.id: s for s in char.generated_skills}
    skills = [generated.get(s) or library.skills[s] for s in char.hero.skills[:2]]
    allocation = recommended_level_up(
        skills, library.weapons.get(char.hero.weapon), char.hero.attributes, char.attribute_points
    )
    before = as_run(char)
    after = allocate_attributes(before, allocation)
    event = AttributesAllocatedEvent(
        attributes=dict(allocation), attribute_points=after.attribute_points
    )
    return from_run(char, with_hp_change(library, before, after)), [event]


def sync_tier(
    library: ContentLibrary, world: WorldState, char: CharacterState
) -> tuple[CharacterState, list[WorldEvent]]:
    """角色階級和主角技能目前的階級不同時，每招照新階級重配（06 6.34.9；roguelite
    ``sync_skill_tier``）。已同步時不變。"""
    tier = hero_tier(library, char.level)
    if char.skill_tier == tier:
        return char, []
    run = as_run(char, seed=skill_seed(world, char))
    synced = sync_skill_tier(world_library(library), run)
    char = from_run(char, synced)
    event = SkillTierChangedEvent(
        from_tier=run.skill_tier, to_tier=tier, skills=char.hero.skills, bench=char.bench
    )
    return char, [event]


# ---------------------------------------------------------------------------
# 換技能（5A-4 的 loadout 改用 roguelite，生成技能也能換）
# ---------------------------------------------------------------------------


def loadout_skills(
    library: ContentLibrary, char: CharacterState, skills: tuple[str, ...]
) -> CharacterState:
    """新的裝備清單（roguelite ``set_loadout``：擁有的、不重複、欄位上限；沒裝上的進備用）。"""
    try:
        return from_run(char, set_loadout(char_library(library, char), as_run(char), skills))
    except RunError as exc:
        raise WorldActionError(str(exc)) from exc


# ---------------------------------------------------------------------------
# 世界動作
# ---------------------------------------------------------------------------


def apply_growth(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: GrowthAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """套用一個成長動作（不合法拋 :class:`WorldActionError`，狀態不變）。"""
    try:
        if isinstance(action, AllocateAction | RespecAction):
            return _attributes(library, char, action)
        if isinstance(action, SwearOathAction | ReleaseOathAction):
            return _oath(library, char, action, now)
        return _flash(library, world, char, action)
    except RunError as exc:
        raise WorldActionError(str(exc)) from exc


def _attributes(
    library: ContentLibrary, char: CharacterState, action: AllocateAction | RespecAction
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    before = as_run(char)
    event: WorldEvent
    if isinstance(action, AllocateAction):
        if char.pending_encounter is not None:
            raise WorldActionError("還有沒處理的遭遇，不能配點")
        after = allocate_attributes(before, action.attributes)
        event = AttributesAllocatedEvent(
            attributes=dict(action.attributes), attribute_points=after.attribute_points
        )
    else:
        _require_service(library, char, "重配屬性")
        after = respec_attributes(before)
        event = AttributesRespeccedEvent(attribute_points=after.attribute_points)
    return from_run(char, with_hp_change(library, before, after)), (event,)


def _flash(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: FlashAction | FlashPickAction | DissolveAction | InheritAction,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    lib = char_library(library, char)
    run = as_run(char, seed=skill_seed(world, char))
    event: WorldEvent
    if isinstance(action, FlashPickAction):
        pending = run.pending_flash
        if pending is None:
            raise WorldActionError("沒有待選的閃現選項")
        after = pick_flash(lib, run, FlashPickChoice(pick=action.pick, unequip=action.unequip))
        new_skill = _new_skill(run, after, pending.skill)
        event = FlashPickedEvent(
            skill=pending.skill,
            new_skill=new_skill,
            pick=action.pick,
            slot=pending.offer.slot,
        )
        picked = from_run(char, after)
        return with_skill_region(picked, new_skill, skill_region(char, pending.skill)), (event,)
    if isinstance(action, FlashAction):
        blocked = flash_blocked_zh(char)  # OB-3（#150 第 6 點）
        if blocked is not None:
            raise WorldActionError(blocked)
        _require_service(library, char, "閃現")
        choice = FlashChoice(skill=action.skill, slot=action.slot, category=action.category)
        region = skill_region(char, action.skill)
        source, record = _flash_source(lib, char, run, choice, region)
        after = open_flash(lib, run, choice, source=source, region=region)
        assert after.pending_flash is not None
        event = FlashOfferedEvent(
            skill=action.skill,
            slot=action.slot,
            category=action.category,
            cost=run.insight - after.insight,
            options=len(after.pending_flash.offer.options),
            insight=after.insight,
            source=record.source,
        )
    elif isinstance(action, DissolveAction):
        _require_service(library, char, "溶掉技能")
        after = dissolve(lib, run, DissolveChoice(skill=action.skill))
        event = SkillDissolvedEvent(
            skill=action.skill, refund=after.insight - run.insight, insight=after.insight
        )
    else:
        _require_service(library, char, "傳承")
        choice_i = InheritChoice(skill=action.skill, source=action.source, records=action.records)
        after = inherit(lib, run, choice_i)
        new_skill = _new_skill(run, after, action.skill)
        event = SkillInheritedEvent(
            skill=action.skill,
            source=action.source,
            records=action.records,
            new_skill=new_skill,
        )
        inherited = from_run(char, after)
        return with_skill_region(inherited, new_skill, skill_region(char, action.skill)), (event,)
    return from_run(char, after), (event,)


class _RecordedFlash(UsageSource):
    """日誌（或預先生成）記下的變化提議；``make_offer`` 照樣一一驗證，套不上的用模板補。LF-1：
    另給名稱與描述（``texts``），引擎檢查後掛到鍵對得上的選項。"""

    def __init__(
        self, accepted: tuple[Variation, ...], texts: tuple[VariationText, ...] = ()
    ) -> None:
        self.accepted = accepted
        self.by_key = text_map(texts)

    def proposed(
        self, library: ContentLibrary, request: FlashRequest, skill: object
    ) -> list[Variation]:
        return list(self.accepted)

    def texts(self, library: ContentLibrary, request: FlashRequest) -> Mapping[str, VariationText]:
        return self.by_key


def world_flash_request(
    library: ContentLibrary,
    char: CharacterState,
    run: RunState,
    choice: FlashChoice,
    region: str | None,
) -> FlashGenRequest:
    """世界引擎這一次閃現出題的生成請求（API 層預先生成用同一個函式，鍵才會一致）。"""
    request = flash_request(
        library, run, choice.skill, slot=choice.slot, category=choice.category, region=region
    )
    return FlashGenRequest(char.character_id, flash_key(char.character_id, request), request)


def _flash_source(
    library: ContentLibrary,
    char: CharacterState,
    run: RunState,
    choice: FlashChoice,
    region: str | None,
) -> tuple[FlashOptionSource, FlashLlmRecord]:
    """出題前向供應者要變化提議（6L-2）；拿不到＝模板（來源 ``template``）。出題本身不合法（點數
    不足、不能閃）時不要提議，讓 ``open_flash`` 照常拒絕。"""
    template = FlashLlmRecord(tag="", source="template")
    cost = library.flash.pricing.rule(choice.category is not None).cost
    if (
        run.pending_flash is not None
        or run.insight < cost
        or problem_of(library, run, choice.skill, choice.slot) is not None
    ):
        return UsageSource(), template
    try:
        gen = world_flash_request(library, char, run, choice, region)
    except RunError:
        return UsageSource(), template
    fallback = FlashGen(key=gen.key, record=FlashLlmRecord(tag=gen.key, source="template"))
    found = supply(gen, FlashGen, fallback, lambda g: g)
    if not found.record.accepted and not found.record.texts:
        return UsageSource(), found.record
    return _RecordedFlash(found.record.accepted, found.record.texts), found.record


def _new_skill(before: RunState, after: RunState, old: str) -> str:
    """``old`` 換成的新技能 ID（閃現與傳承後的 ID 由變化歷程決定；沒換 ID 時就是 ``old``）。"""
    added = sorted(set(owned_skills(after)) - set(owned_skills(before)))
    return added[0] if added else old


def _oath(
    library: ContentLibrary,
    char: CharacterState,
    action: SwearOathAction | ReleaseOathAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    table = library.world_oaths
    if isinstance(action, ReleaseOathAction):
        if char.oath is None:
            raise WorldActionError("目前沒有誓約")
        default = OathTable.model_fields["cooldown_seconds"].default
        cooldown = default if table is None else table.cooldown_seconds
        until = now + cooldown
        released = OathReleasedEvent(template=char.oath.template, cooldown_until=until)
        cleared = {"oath": None, "oath_cooldown_until": until, "oath_broken_next": False}
        return char.model_copy(update=cleared), (released,)
    _require_service(library, char, "立誓")
    if table is None:
        raise WorldActionError("內容庫沒有誓約模板（world/oaths.yaml）")
    if char.oath is not None:
        raise WorldActionError("同時只能有 1 個誓約，請先解除目前的誓約")
    if now < char.oath_cooldown_until:
        raise WorldActionError("解除誓約後 1 天內不能再立誓")
    problems = oath_problems(table, action.proposal)
    if problems:
        raise WorldActionError("；".join(problems))
    slots = library.ruleset.core.skill_slots.passive
    if passive_count(library, char) + OATH_PASSIVE_SLOTS > slots:
        raise WorldActionError("誓約佔一格被動欄位，先卸下一招被動")
    template = table.template_by_id()[action.proposal.template]
    params = dict(action.proposal.params)
    oath = OathState(
        template=template.id,
        params=params,
        difficulty=template.difficulty_for(params),
        sworn_at=now,
    )
    sworn = char.model_copy(update={"oath": oath, "oath_broken_next": False})
    return sworn, (OathSwornEvent(oath=oath),)
