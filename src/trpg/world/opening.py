"""開局在主城工坊靶場（Phase TR-1，#134；OB-1，#150；21 21.5、09 9.6.9、07 7.6／7.7、06 6.27.3）。

- 大世界建角只選名字、種族、外觀、出身；角色建好時是 **未完成開局**（``CharacterState.opening``：
  起始技能的種子），手上拿佔位武器（``newcomer.yaml`` 的 ``range.placeholder_weapon``）、沒有技能。
  這段期間（``stage=pick_class``）只能做 :data:`_PICK_CLASS_ALLOWED` 的動作
  （:func:`opening_gate`）；中途離開遊戲，下次回來還是停在靶場。
- **選大類**（#150；世界動作 ``opening_class``，:func:`apply_opening_class`）：給該大類的入門武器
  （``range.starters``）與入門招（``range.demos``），開局點數照推薦配法自動配好，進入入門期
  （``stage=starter``）；入門期升級的屬性點自動配掉（:func:`trpg.world.growth.gain_xp`）。
- **確定出發**（世界動作 ``opening_confirm``，:func:`apply_opening_confirm`）：起始武器＋2 個
  關鍵字，每個關鍵字的技能池各給 1 招（和 roguelite 開局同一套函式
  :func:`~trpg.roguelite.start.new_keyword_run`，屬性照推薦配法，#133）；名字、種族、外觀照建角時的。
  出發之後不能重選（換武器靠掉落與打造）。
- **沙盒試打**（:func:`range_trial`）：在記憶體裡組一場戰鬥（靶場地圖、木樁 3 個），主角拿選的武器，
  技能是普攻＋該大類 2 招示範招，或「看示範」的關鍵字起始技能。只回傳戰鬥設定與種子，**不改角色、
  不寫世界日誌**；API 開在戰鬥工作階段表、不登記成角色的戰鬥，所以打完不回寫：不算勝負、不給經驗與
  掉落、不耗 HP 與法力。

純函式、確定性：不讀時間、不用全域亂數；試打的種子由開局種子與選擇衍生（:func:`trial_seed`）。
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.slots import SlotType
from trpg.content.world_newcomer import RangeContent
from trpg.engine.setup import BattleSetup, UnitSpawn
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.start import (
    apply_allocation,
    links_between,
    new_keyword_run,
    pick_starters,
    recommended_allocation,
    start_hero,
    start_weapons,
    starter_pools,
    starting_skill,
)
from trpg.shared.rng import MASK64, fnv1a64
from trpg.shared.types import Team
from trpg.skillgen.keywords import derive_keywords
from trpg.world.actions import (
    UI_NOTE_ACTIONS,
    ChangeLookAction,
    ChangeRaceAction,
    DissolveAction,
    FightAction,
    FlashAction,
    FlashPickAction,
    HireAction,
    InheritAction,
    LoadoutAction,
    NewsSeenAction,
    OpeningClassAction,
    OpeningClassChosenEvent,
    OpeningConfirmAction,
    OpeningConfirmedEvent,
    ReleaseOathAction,
    ShadowAiAction,
    SwearOathAction,
    WorldAction,
    WorldEvent,
)
from trpg.world.common import max_hp, max_mana
from trpg.world.crafting import find_gear
from trpg.world.crafting_actions import CraftAction, EnhanceAction, ImbueAction, RerollAction
from trpg.world.economy_actions import EquipAction
from trpg.world.errors import WorldActionError
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.opening_limits import FLASH_ZH, fight_problem
from trpg.world.season_events import SeasonBossAction
from trpg.world.state import CharacterState, OpeningStage, OpeningState, WorldState

__all__ = [
    "OPENING_PENDING_ZH",
    "RangeTrial",
    "apply_opening",
    "apply_opening_class",
    "apply_opening_confirm",
    "mentor_town",
    "new_opening",
    "opening_gate",
    "opening_limits",
    "pending_hero",
    "range_content",
    "range_trial",
    "recommended_keywords",
    "starter_skill_ids",
    "trial_seed",
]

OPENING_PENDING_ZH: Final = "先在主城工坊靶場選好大類（近戰、遠程或法器），按「確定出發」"
_DONE_ZH: Final = "開局已經完成，不能重選起始武器與關鍵字（換武器靠掉落與打造）"
_PICK_CLASS_ALLOWED: Final = (
    OpeningClassAction,
    OpeningConfirmAction,  # 舊前端的一次選定；OB-2 起改成分流、OB-5 前端換掉前不能拿掉
    ChangeLookAction,  # #147：未完成開局可以改外觀
    NewsSeenAction,
    *UI_NOTE_ACTIONS,
)
"""``pick_class`` 階段（白名單）能做的動作。"""
_NOT_BEFORE_LEVEL_4: Final = (DissolveAction, InheritAction)
"""開局還沒結束就不能做的動作（21.5 第 9 點「溶掉、傳承 4 級前都不能用」）。"""
_STARTER_BLOCKED: Final[tuple[tuple[tuple[type, ...], str], ...]] = (
    ((OpeningClassAction,), "大類已經選好了：打完新手第 2 步回霧渡鎮再正式選定"),
    # ``opening_confirm``（正式選定，OB-2）不在這裡擋：條件由
    # :func:`trpg.world.opening_choice.choice_problem` 檢查
    ((ChangeRaceAction,), "正式選定武器與關鍵字之前不能換種族"),
    ((FlashAction, FlashPickAction), FLASH_ZH.format(level=OPENING_END_LEVEL)),
    ((LoadoutAction,), "入門期不能換技能"),
    ((HireAction, ShadowAiAction), "入門期不能雇用傭兵"),
    ((LeagueEnterAction, LeagueWithdrawAction), "入門期不能參加聯賽"),
    ((SeasonBossAction,), "入門期不能挑戰賽季 Boss"),
    ((SwearOathAction, ReleaseOathAction), "入門期不能立誓"),
)
"""``starter`` 階段（黑名單）依動作種類擋的（21.5 #150 第 7、9 點）。"""
_ARMOR_SLOT_TYPES: Final[frozenset[SlotType]] = frozenset({"head", "body", "hands", "feet"})
"""入門期能打造、強化的部位（21.5 第 9 點「只限防具」；8.12 的防具欄位）。"""
_MAIN_HAND_ZH: Final = "入門期不能換主手，找葛蘭選定武器後就能換"
_ARMOR_ONLY_ZH: Final = "入門期的打造、強化、附魔只限防具"
_CHOSEN_ZH: Final = "已經正式選定武器與關鍵字了"
_BEFORE_LEVEL_4_ZH: Final = "4 級前不能溶掉技能或傳承"
_LIMIT_ACTIONS: Final[Mapping[str, type]] = {
    "race": ChangeRaceAction,
    "flash": FlashAction,
    "loadout": LoadoutAction,
    "hire": HireAction,
    "league": LeagueEnterAction,
    "season_boss": SeasonBossAction,
    "oath": SwearOathAction,
}
"""畫面上要先標成不可用的系統（:func:`opening_limits` 的鍵）→ 代表它的動作。"""


def range_content(library: ContentLibrary) -> RangeContent:
    """內容裡的靶場；沒有時拋 :class:`WorldActionError`。"""
    newcomer = library.world_newcomer
    if newcomer is None or newcomer.range is None:
        raise WorldActionError("這個世界沒有工坊靶場")
    return newcomer.range


# ---------------------------------------------------------------------------
# 開局閘門（21.5 #150 第 7、9 點；OB-1）
# ---------------------------------------------------------------------------


type _GateRule = Callable[[ContentLibrary, WorldState, CharacterState, WorldAction], str | None]
"""閘門的一條規則：回傳擋下的原因（中文），可以做時 ``None``。"""


def _pick_class_rule(
    _library: ContentLibrary, _world: WorldState, _char: CharacterState, action: WorldAction
) -> str | None:
    return None if isinstance(action, _PICK_CLASS_ALLOWED) else OPENING_PENDING_ZH


def _starter_blocked_rule(
    _library: ContentLibrary, _world: WorldState, _char: CharacterState, action: WorldAction
) -> str | None:
    for kinds, reason in _STARTER_BLOCKED:
        if isinstance(action, kinds):
            return reason
    return None


def _main_hand_rule(
    _library: ContentLibrary, _world: WorldState, char: CharacterState, action: WorldAction
) -> str | None:
    """入門期不能換主手（指定 ``main_hand``，或背包裡的那件是武器）。"""
    if not isinstance(action, EquipAction):
        return None
    item = next((g for g in char.gear if g.id == action.item), None)
    weapon = item is not None and item.slot_type == "weapon"
    return _MAIN_HAND_ZH if weapon or action.slot == "main_hand" else None


def _armor_only_rule(
    _library: ContentLibrary, world: WorldState, char: CharacterState, action: WorldAction
) -> str | None:
    """入門期打造、強化（連同附魔台的重骰、指定詞條）只限防具；找不到目標時交給動作本身報錯。"""
    slot_type: SlotType | None = None
    if isinstance(action, CraftAction):
        slot_type = action.slot_type
        if action.code is not None:
            record = world.recipe_of(action.code.lower())
            slot_type = None if record is None else record.recipe.slot_type
    elif isinstance(action, EnhanceAction | RerollAction | ImbueAction):
        item = find_gear(char, action.item)
        slot_type = None if item is None else item.slot_type
    return None if slot_type is None or slot_type in _ARMOR_SLOT_TYPES else _ARMOR_ONLY_ZH


def _fight_rule(
    library: ContentLibrary, _world: WorldState, char: CharacterState, action: WorldAction
) -> str | None:
    """入門期的戰鬥閘（OB-4）：只打新手任務前兩步的固定戰（:mod:`trpg.world.opening_limits`）。"""
    return fight_problem(library, char) if isinstance(action, FightAction) else None


def _before_level_4_rule(
    _library: ContentLibrary, _world: WorldState, _char: CharacterState, action: WorldAction
) -> str | None:
    return _BEFORE_LEVEL_4_ZH if isinstance(action, _NOT_BEFORE_LEVEL_4) else None


def _chosen_rule(
    _library: ContentLibrary, _world: WorldState, _char: CharacterState, action: WorldAction
) -> str | None:
    """``chosen`` 階段（正式選定之後，OB-2）：開局動作不再收（4 級前的免費重選是另一個動作，
    OB-3）；入門期的其他限制解除。"""
    return _CHOSEN_ZH if isinstance(action, OpeningClassAction | OpeningConfirmAction) else None


_STAGE_RULES: Final[Mapping[OpeningStage, tuple[_GateRule, ...]]] = {
    "pick_class": (_pick_class_rule,),
    "starter": (
        _starter_blocked_rule,
        _main_hand_rule,
        _armor_only_rule,
        _fight_rule,
        _before_level_4_rule,
    ),
    "chosen": (_chosen_rule, _before_level_4_rule),
}
"""每個階段依序檢查的規則（OB-3 在 ``chosen`` 加閃現限制；OB-4 在 ``starter`` 加戰鬥閘）。"""


def opening_gate(
    library: ContentLibrary, world: WorldState, char: CharacterState, action: WorldAction
) -> None:
    """依開局階段擋動作（只看 ``char.opening``：已完成開局的角色只擋開局動作，不能重選，21.5）。"""
    if char.opening is None:
        if isinstance(action, OpeningConfirmAction | OpeningClassAction):
            raise WorldActionError(_DONE_ZH)
        return
    for rule in _STAGE_RULES[char.opening.stage]:
        problem = rule(library, world, char, action)
        if problem is not None:
            raise WorldActionError(problem)


def opening_limits(char: CharacterState) -> dict[str, str]:
    """畫面用（OB-5）：開局還沒結束的角色現在不開放的系統 → 原因。文字和 :func:`opening_gate` 擋
    動作時回的是同一份（同一張表），所以面板標的原因和送出動作被拒的原因一定相同。鍵：``race``
    換種族、``flash`` 閃現、``loadout`` 換技能、``hire`` 雇傭兵、``league`` 聯賽、``season_boss``
    賽季 Boss、``oath`` 誓約、``main_hand`` 換主手、``smith`` 打造強化只限防具、``dissolve`` 溶掉與
    傳承。只讀狀態，不改任何東西；已完成開局或還在選大類（整頁是靶場）時空。"""
    opening = char.opening
    if opening is None or opening.stage == "pick_class":
        return {}
    out: dict[str, str] = {}
    if opening.stage == "starter":
        for key, kind in _LIMIT_ACTIONS.items():
            for kinds, reason in _STARTER_BLOCKED:
                if issubclass(kind, kinds):
                    out[key] = reason
        out["main_hand"] = _MAIN_HAND_ZH
        out["smith"] = _ARMOR_ONLY_ZH
    elif char.level < OPENING_END_LEVEL:
        out["flash"] = FLASH_ZH.format(level=OPENING_END_LEVEL)
    out["dissolve"] = _BEFORE_LEVEL_4_ZH
    return out


def pending_hero(library: ContentLibrary, base: UnitTemplate | None = None) -> UnitTemplate:
    """未完成開局的主角：佔位武器、沒有技能、沒有配點（``base`` 給了就沿用它的名字、種族、
    外觀）。"""
    hero = start_hero(library, range_content(library).placeholder_weapon, ())
    if base is None:
        return hero
    return hero.model_copy(update={"name_zh": base.name_zh, "race": base.race, "doll": base.doll})


def apply_opening(
    library: ContentLibrary, char: CharacterState, weapon: str, keywords: Sequence[str]
) -> tuple[CharacterState, tuple[SkillDef, ...]]:
    """依開局種子給起始武器與技能（06 6.27.3），回傳完成開局的角色與給的技能（依關鍵字順序）。
    名字、種族、外觀照角色目前的；HP 與法力回滿。選擇不合法時拋
    :class:`~trpg.roguelite.errors.ChoiceError`。"""
    if char.opening is None:
        raise ChoiceError(_DONE_ZH)
    if weapon not in start_weapons(library):
        raise ChoiceError(f"靶場沒有這把武器：{weapon}")
    run = new_keyword_run(library, weapon, keywords, char.opening.seed, "recommended")
    base = char.hero
    hero = run.hero.model_copy(
        update={"name_zh": base.name_zh, "race": base.race, "doll": base.doll}
    )
    done = char.model_copy(
        update={"hero": hero, "generated_skills": run.generated_skills, "opening": None}
    )
    done = done.model_copy(update={"hp": max_hp(library, done), "mana": max_mana(library, done)})
    generated = {s.id: s for s in run.generated_skills}
    given = tuple(generated.get(s) or library.skills[s] for s in hero.skills)
    return done, given


def apply_opening_confirm(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: OpeningConfirmAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """世界動作 ``opening_confirm``（不合法拋 :class:`WorldActionError`，狀態不變）。"""
    del world, now
    try:
        done, given = apply_opening(library, char, action.weapon, action.keywords)
    except ChoiceError as exc:
        raise WorldActionError(str(exc)) from exc
    event = OpeningConfirmedEvent(
        weapon=action.weapon,
        keywords=tuple(action.keywords),
        skills=tuple(s.id for s in given),
        skill_names=tuple(s.name_zh for s in given),
    )
    return done, (event,)


def apply_opening_class(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: OpeningClassAction,
    now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """世界動作 ``opening_class``（#150 第 1 點）：入門武器、入門招、開局點數照推薦配法，HP 與法力
    回滿，進入入門期。入門招一律讀 ``range.demos``（資料，#148 未定案）。"""
    del world, now
    assert char.opening is not None  # opening_gate 擋掉了已完成開局的角色
    arena = range_content(library)
    weapon_class = action.weapon_class
    weapon = arena.starters[weapon_class]
    skills = tuple(library.skills[s] for s in arena.demos[weapon_class])
    opening = char.opening.model_copy(update={"stage": "starter", "weapon_class": weapon_class})
    equipped = char.model_copy(
        update={"hero": _trial_hero(library, char, weapon, skills), "opening": opening}
    )
    done = equipped.model_copy(
        update={"hp": max_hp(library, equipped), "mana": max_mana(library, equipped)}
    )
    event = OpeningClassChosenEvent(
        weapon_class=weapon_class,
        weapon=weapon,
        skills=tuple(s.id for s in skills),
        skill_names=tuple(s.name_zh for s in skills),
    )
    return done, (event,)


def new_opening(seed: int) -> OpeningState:
    """新角色的「未完成開局」狀態。"""
    return OpeningState(seed=seed)


# ---------------------------------------------------------------------------
# 入門招與關鍵字推薦（#150 第 4 點；OB-2）
# ---------------------------------------------------------------------------

_TIER_SUFFIX: Final = re.compile(r"^(.+)_t\d+$")
"""升階重配後的技能 ID（``<原 ID>_t<階級>``，同 :func:`trpg.world.growth.skill_region`）。"""


def _base_id(skill_id: str) -> str:
    found = _TIER_SUFFIX.match(skill_id)
    return skill_id if found is None else found.group(1)


def starter_skill_ids(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """入門期角色身上的入門招（裝備中與備用；含升階重配後改名的），依 ``range.demos`` 的順序。
    入門招一律讀資料（#148 未定案）；不在入門期＝空。"""
    opening = char.opening
    if opening is None or opening.stage != "starter" or opening.weapon_class is None:
        return ()
    newcomer = library.world_newcomer
    if newcomer is None or newcomer.range is None:
        return ()
    demos = newcomer.range.demos.get(opening.weapon_class, ())
    owned = (*char.hero.skills, *char.bench)
    return tuple(s for demo in demos for s in owned if _base_id(s) == demo)


def _own_keywords(library: ContentLibrary, char: CharacterState, skill_id: str) -> tuple[str, ...]:
    """一招的專屬關鍵字（06 6.27.2）：製造的在前、利用的在後，各照關鍵字表的順序，不重複。"""
    generated = {s.id: s for s in char.generated_skills}
    skill = generated.get(skill_id) or library.skills.get(skill_id)
    if skill is None:
        return ()
    found = derive_keywords(skill, library.keywords, exclusive_only=True)
    return tuple(dict.fromkeys((*found.makes, *found.uses)))


def _first_keyword_candidates(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """第 1 個推薦關鍵字的候選：入門招依「用過的次數多 → 少」（同次數取資料裡前面那招），每招的
    專屬關鍵字製造優先；只留開局可選的關鍵字。"""
    starters = starter_skill_ids(library, char)
    usage = char.skill_usage
    ranked = sorted(
        range(len(starters)),
        key=lambda i: (-(usage[starters[i]].uses if starters[i] in usage else 0), i),
    )
    allowed = set(library.keywords.start_ids())
    found: dict[str, None] = {}
    for index in ranked:
        for keyword in _own_keywords(library, char, starters[index]):
            if keyword in allowed:
                found[keyword] = None
    return tuple(found)


def recommended_keywords(
    library: ContentLibrary, char: CharacterState, weapon: str
) -> tuple[str, ...]:
    """正式選定時標「推薦」的關鍵字（#150 第 4 點與第 9 點細節；只標示、不強制）。純函式。

    - 第 1 個：入門期用過最多次的入門招的專屬關鍵字（:func:`_first_keyword_candidates`）；``weapon``
      沒有該關鍵字的起始技能就順延下一個候選。
    - 第 2 個：照關鍵字表順序，第一個「和第 1 個一起選時，這把武器實際給的起始兩招之間有觸發關係」
      的關鍵字（#129，:func:`~trpg.roguelite.start.links_between`；起始技能照開局種子，和預覽、
      正式選定給的招相同）；沒有該關鍵字起始技能的順延；都沒有就只推薦第 1 個。
    - 兩招都沒有專屬關鍵字、不在入門期、或 ``weapon`` 不在靶場：不推薦（空）。"""
    if char.opening is None or weapon not in start_weapons(library):
        return ()
    candidates = _first_keyword_candidates(library, char)
    if not candidates:
        return ()
    key = (id(library), char.opening.seed, weapon, candidates)
    cached = _recommended.get(key)
    if cached is not None and cached[0] is library:
        return cached[1]
    found = _recommend(library, char.opening.seed, weapon, candidates)
    if len(_recommended) >= _RECOMMENDED_CACHE_LIMIT:
        _recommended.clear()
    _recommended[key] = (library, found)
    return found


def _recommend(
    library: ContentLibrary, seed: int, weapon: str, candidates: Sequence[str]
) -> tuple[str, ...]:
    pools = _starter_pools(library)
    for first in candidates:
        # 和 ``pick_starters``（預覽、正式選定）同一組參數：第 1 招不帶 ``prefer_uses``
        one = starting_skill(library, weapon, first, seed, pools=pools)
        if one is None:
            continue  # 這把武器沒有這個關鍵字的起始技能：順延
        for second in library.keywords.start_ids():
            if second == first:
                continue
            two = starting_skill(
                library, weapon, second, seed, taken=[one.id], pools=pools, prefer_uses=first,
                first=one,
            )  # fmt: skip
            if two is not None and links_between(library, one, two):
                return (first, second)
        return (first,)
    return ()


_pools: dict[int, tuple[ContentLibrary, dict[str, tuple[str, ...]]]] = {}
"""內容庫 → 起始技能池的快取（:func:`~trpg.roguelite.start.starter_pools` 是內容的純函式；存著
內容庫本身，``id`` 不會被重用）。"""
_POOLS_CACHE_LIMIT: Final = 8
_recommended: dict[
    tuple[int, int, str, tuple[str, ...]], tuple[ContentLibrary, tuple[str, ...]]
] = {}
"""（內容庫, 開局種子, 武器, 第 1 個關鍵字的候選）→ 推薦的快取：:func:`_recommend` 只看這四項，
一把武器最多要試 11 個關鍵字的起始技能（約 0.5 秒），畫面每次重畫不該重算。只影響速度。"""
_RECOMMENDED_CACHE_LIMIT: Final = 512


def _starter_pools(library: ContentLibrary) -> dict[str, tuple[str, ...]]:
    cached = _pools.get(id(library))
    if cached is not None and cached[0] is library:
        return cached[1]
    if len(_pools) >= _POOLS_CACHE_LIMIT:
        _pools.clear()
    pools = starter_pools(library)
    _pools[id(library)] = (library, pools)
    return pools


def mentor_town(library: ContentLibrary) -> tuple[str, str] | None:
    """駐堂導師（葛蘭）所在的（區域, 地點）；沒有設定＝``None``。"""
    newcomer = library.world_newcomer
    if newcomer is None or newcomer.mentor_npc is None:
        return None
    table = library.world_event_content.npcs.get(newcomer.start_region)
    card = None if table is None else table.npc_by_id().get(newcomer.mentor_npc)
    return None if card is None else (newcomer.start_region, card.location)


# ---------------------------------------------------------------------------
# 沙盒試打
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RangeTrial:
    """一場靶場試打的設定（呼叫端在戰鬥工作階段表開，不登記成角色的戰鬥）。"""

    setup: BattleSetup
    seed: int
    skills: tuple[SkillDef, ...]
    """這場能用的技能（普攻之外；示範招或關鍵字的起始技能）。"""
    demo: bool
    """``True``＝該大類的示範招；``False``＝關鍵字的起始技能（看示範）。"""


MAX_TRIAL_KEYWORDS: Final = 2


def trial_seed(opening_seed: int, weapon: str, keywords: Sequence[str]) -> int:
    """試打的戰鬥種子：開局種子＋武器＋關鍵字衍生（同一組選擇每次都一樣）。"""
    label = f"range|{opening_seed}|{weapon}|{','.join(keywords)}"
    return fnv1a64(label.encode("utf-8")) & MASK64


def _trial_skills(
    library: ContentLibrary, arena: RangeContent, weapon: str, keywords: Sequence[str], seed: int
) -> tuple[tuple[SkillDef, ...], bool]:
    if not keywords:
        weapon_class = library.weapons[weapon].weapon_class
        demos = arena.demos.get(weapon_class)
        if not demos:
            raise WorldActionError(f"靶場沒有{weapon_class}的示範招")
        return tuple(library.skills[s] for s in demos), True
    if len(keywords) > MAX_TRIAL_KEYWORDS or len(set(keywords)) != len(keywords):
        raise WorldActionError(f"看示範最多 {MAX_TRIAL_KEYWORDS} 個不同的關鍵字")
    unknown = sorted(set(keywords) - set(library.keywords.ids()))
    if unknown:
        raise WorldActionError(f"未知的關鍵字：{', '.join(unknown)}")
    try:
        return tuple(pick_starters(library, weapon, keywords, seed)), False
    except ChoiceError as exc:
        raise WorldActionError(str(exc)) from exc


def _trial_hero(
    library: ContentLibrary, char: CharacterState, weapon: str, skills: Sequence[SkillDef]
) -> UnitTemplate:
    """試打的主角：選的武器＋這場的技能，屬性照推薦配法（和確定出發的配法相同）；名字、種族、外觀
    照角色。"""
    points = library.roguelite.start_free_points
    allocation = recommended_allocation(list(skills), library.weapons[weapon], points)
    hero = apply_allocation(start_hero(library, weapon, [s.id for s in skills]), allocation)
    base = char.hero
    return hero.model_copy(update={"name_zh": base.name_zh, "race": base.race, "doll": base.doll})


def range_trial(
    library: ContentLibrary, char: CharacterState, weapon: str, keywords: Sequence[str] = ()
) -> RangeTrial:
    """靶場試打（沙盒）：``keywords`` 空＝普攻＋該大類 2 招示範招；給了＝依序給的起始技能（看示範，
    最多 2 個）。只有未完成開局的角色能試（之後回靶場試自己的技能與裝備是原本規劃的靶場試玩，還沒
    開放）。不改角色、不碰世界。"""
    arena = range_content(library)
    if char.opening is None:
        raise WorldActionError("開局已經完成：靶場的開局試打只在選武器之前開放")
    if weapon not in start_weapons(library):
        raise WorldActionError(f"靶場沒有這把武器：{weapon}")
    skills, demo = _trial_skills(library, arena, weapon, keywords, char.opening.seed)
    hero = _trial_hero(library, char, weapon, skills)
    extra = [s for s in skills if s.id not in library.skills]
    units = [
        UnitSpawn(
            template=hero,
            weapon=library.weapon_of(hero),
            team=Team.ALLY,
            position=arena.hero_at,
        )
    ]
    for dummy in arena.dummies:
        template = library.unit(dummy.unit)
        units.append(
            UnitSpawn(
                template=template,
                weapon=library.weapon_of(template),
                equipment=library.loadout_of(template),
                team=Team.ENEMY,
                position=dummy.at,
            )
        )
    setup = BattleSetup(
        map=library.maps[arena.map],
        ruleset=library.ruleset.with_skills(extra),
        units=tuple(units),
        max_rounds=arena.max_rounds,
        first_team=Team.ALLY,
    )
    return RangeTrial(
        setup=setup,
        seed=trial_seed(char.opening.seed, weapon, keywords),
        skills=skills,
        demo=demo,
    )
