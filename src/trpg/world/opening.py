"""開局在主城工坊靶場（Phase TR-1，#134；21 21.5、09 9.6.9、07 7.6／7.7、06 6.27.3）。

- 大世界建角只選名字、種族、外觀、出身；角色建好時是 **未完成開局**（``CharacterState.opening``：
  起始技能的種子），手上拿佔位武器（``newcomer.yaml`` 的 ``range.placeholder_weapon``）、沒有技能。
  這段期間只能做 ``opening_confirm`` 與只記畫面紀錄的動作（:func:`opening_gate`）；中途離開遊戲，
  下次回來還是停在靶場。
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

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from trpg.content.battle import UnitTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
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
    NewsSeenAction,
    OpeningConfirmAction,
    OpeningConfirmedEvent,
    WorldAction,
    WorldEvent,
)
from trpg.world.common import max_hp, max_mana
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, OpeningState, WorldState

__all__ = [
    "OPENING_PENDING_ZH",
    "RangeTrial",
    "apply_opening",
    "apply_opening_confirm",
    "new_opening",
    "opening_gate",
    "pending_hero",
    "range_content",
    "range_trial",
    "trial_seed",
]

OPENING_PENDING_ZH: Final = "先在主城工坊靶場選好武器與兩個關鍵字，按「確定出發」"
_DONE_ZH: Final = "開局已經完成，不能重選起始武器與關鍵字（換武器靠掉落與打造）"
_ALLOWED_WHILE_PENDING: Final = (OpeningConfirmAction, NewsSeenAction, *UI_NOTE_ACTIONS)
"""未完成開局時能做的動作：確定出發、看過消息、只記畫面紀錄的動作（提示、開場看過了）。"""


def range_content(library: ContentLibrary) -> RangeContent:
    """內容裡的靶場；沒有時拋 :class:`WorldActionError`。"""
    newcomer = library.world_newcomer
    if newcomer is None or newcomer.range is None:
        raise WorldActionError("這個世界沒有工坊靶場")
    return newcomer.range


def opening_gate(char: CharacterState, action: WorldAction) -> None:
    """未完成開局時擋掉其他動作；已完成時擋掉 ``opening_confirm``（不能重選，21.5）。"""
    if char.opening is not None and not isinstance(action, _ALLOWED_WHILE_PENDING):
        raise WorldActionError(OPENING_PENDING_ZH)
    if char.opening is None and isinstance(action, OpeningConfirmAction):
        raise WorldActionError(_DONE_ZH)


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
