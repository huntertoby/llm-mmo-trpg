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
    new_keyword_run,
    pick_starters,
    recommended_allocation,
    start_hero,
    start_weapons,
)
from trpg.shared.rng import MASK64, fnv1a64
from trpg.shared.types import Team
from trpg.world.actions import (
    UI_NOTE_ACTIONS,
    ChangeLookAction,
    ChangeRaceAction,
    DissolveAction,
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
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.season_events import SeasonBossAction
from trpg.world.state import CharacterState, OpeningStage, OpeningState, WorldState

__all__ = [
    "OPENING_PENDING_ZH",
    "RangeTrial",
    "apply_opening",
    "apply_opening_class",
    "apply_opening_confirm",
    "new_opening",
    "opening_gate",
    "pending_hero",
    "range_content",
    "range_trial",
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
    ((OpeningConfirmAction,), "還不能正式選定：打完新手第 2 步，回霧渡鎮找葛蘭"),
    ((ChangeRaceAction,), "入門期不能換種族，找葛蘭選定武器後就能換"),
    ((FlashAction, FlashPickAction), "入門期不能閃現"),
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
_CHOSEN_NOT_YET_ZH: Final = "這個階段還沒有開放"


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


def _before_level_4_rule(
    _library: ContentLibrary, _world: WorldState, _char: CharacterState, action: WorldAction
) -> str | None:
    return "4 級前不能溶掉技能或傳承" if isinstance(action, _NOT_BEFORE_LEVEL_4) else None


def _chosen_rule(
    _library: ContentLibrary, _world: WorldState, _char: CharacterState, action: WorldAction
) -> str | None:
    """``chosen`` 階段 OB-1 還到不了；OB-2 接上正式選定之前，開局動作一律不收。"""
    return (
        _CHOSEN_NOT_YET_ZH
        if isinstance(action, OpeningClassAction | OpeningConfirmAction)
        else None
    )


_STAGE_RULES: Final[Mapping[OpeningStage, tuple[_GateRule, ...]]] = {
    "pick_class": (_pick_class_rule,),
    "starter": (
        _starter_blocked_rule,
        _main_hand_rule,
        _armor_only_rule,
        _before_level_4_rule,
    ),
    "chosen": (_chosen_rule, _before_level_4_rule),
}
"""每個階段依序檢查的規則（OB-2 改 ``_chosen_rule``、加閃現限制；OB-4 在 ``starter`` 加戰鬥閘）。"""


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
