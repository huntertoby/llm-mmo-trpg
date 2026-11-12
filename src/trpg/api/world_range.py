"""主城工坊靶場的畫面資料與沙盒試打（Phase TR-1，#134；規則在 :mod:`trpg.world.opening`）。

- :func:`range_view`：未完成開局的角色在 ``WorldView.opening`` 拿到的資料（開局種子、武器架的大類
  順序、木樁、每大類的示範招、守印人的台詞）。武器清單與關鍵字預覽沿用一輪開局的
  ``GET /api/runs/start-options``、``POST /api/runs/start-preview``（帶這裡的 ``seed``，預覽的招就是
  確定出發會給的招）。
- :func:`open_range_trial`：``POST /api/world/characters/{id}/range/trial``——在戰鬥工作階段表開一場
  沙盒（只綁帳號、**不登記成角色的戰鬥**），所以打完不回寫世界：不寫日誌、不給經驗掉落、不耗 HP
  法力。播放走既有戰鬥畫面。PR-2a 起是 #147 測試模式（``BattleView.practice``）。
- :func:`open_range_practice`（PR-2a）：``POST …/range/practice``——工坊師傅的「靶場試玩」，自己的
  技能與裝備；:func:`close_range_trial`：``DELETE …/range/trial``——離開時刪掉沙盒。一角色同時只有
  一場試打（``WorldStore.close_trial``／``track_trial``），開新的先刪舊的。
- :func:`workshop_view`（PR-2a）：``WorldView.workshop``，工坊師傅選單的資料。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.api.presenter import battle_response
from trpg.api.skill_cards import skill_card
from trpg.api.world_newcomer_view import PRACTICE_SEEN
from trpg.api.world_range_schemas import (
    CLASS_ZH,
    RangeChoiceView,
    RangeDemoView,
    RangeDummyView,
    RangeLineView,
    RangeRecommendResponse,
    RangeReselectView,
    RangeSpeakerView,
    RangeTrialRequest,
    RangeTrialResponse,
    RangeView,
    WorkshopView,
)
from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.content.world_newcomer import NewcomerContent, OpeningLine, RangeContent
from trpg.roguelite.start import start_weapons
from trpg.world.common import capital_name, in_capital
from trpg.world.errors import WorldActionError
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.opening import (
    RangeTrial,
    mentor_town,
    own_practice,
    practice_problem,
    range_content,
    range_trial,
    recommended_keywords,
)
from trpg.world.opening_choice import choice_problem, place_problem
from trpg.world.opening_reselect import (
    reselect_losses,
    reselect_problem,
    reselect_returns,
    reselect_window_problem,
    starter_weapon_held,
)
from trpg.world.state import CharacterState

if TYPE_CHECKING:
    from trpg.api.world import WorldStore

__all__ = [
    "PRACTICE_TITLE_ZH",
    "close_range_trial",
    "open_range_practice",
    "open_range_trial",
    "range_recommend",
    "range_view",
    "workshop_view",
]

PRACTICE_TITLE_ZH = "靶場試玩"
"""工坊師傅入口那場的戰鬥標題前半（「靶場試玩：{武器}」，玩法 PM「PR-2 字串」定稿）。"""


def range_view(library: ContentLibrary, char: CharacterState) -> RangeView | None:
    """未完成開局時的靶場資料；已完成或沒有靶場內容時 ``None``。"""
    if char.opening is None:
        return None
    newcomer = library.world_newcomer
    arena = None if newcomer is None else newcomer.range
    if newcomer is None or arena is None:
        return None
    racks = tuple(
        RangeDemoView(
            weapon_class=cls,
            name_zh=CLASS_ZH[cls],
            skills=tuple(skill_card(library, library.skills[s]) for s in arena.demos[cls]),
            starter_weapon=arena.starters[cls],
            starter_weapon_zh=library.weapons[arena.starters[cls]].name_zh,
            notes_zh={s: arena.demo_notes[s] for s in arena.demos[cls] if s in arena.demo_notes},
            blurbs_zh={s: arena.demo_blurbs[s] for s in arena.demos[cls] if s in arena.demo_blurbs},
        )
        for cls in arena.racks
    )
    return RangeView(
        seed=char.opening.seed,
        stage=char.opening.stage,
        weapon_class=char.opening.weapon_class,
        recommended_keywords=_recommended(library, char),
        reselect=_reselect_view(library, newcomer, arena, char),
        racks=racks,
        dummies=tuple(RangeDummyView(label_zh=d.label_zh) for d in arena.dummies),
        intro=_lines(arena.intro),
        done=_lines(arena.done),
        loan=_lines(arena.loan),
        keeper=_keeper(library, arena),
        capital_zh=capital_name(library),
        choice=_choice_view(library, newcomer, arena, char),
    )


def _lines(lines: tuple[OpeningLine, ...]) -> tuple[RangeLineView, ...]:
    return tuple(RangeLineView(speaker_zh=x.speaker_zh, text_zh=x.text_zh) for x in lines)


def _keeper(library: ContentLibrary, arena: RangeContent) -> RangeSpeakerView | None:
    """守印人的頭像：主城實地地圖上 ``range.keeper_object`` 那個情境物件的外觀。"""
    return _capital_figure(library, arena.keeper_object)


def _capital_figure(library: ContentLibrary, object_id: str | None) -> RangeSpeakerView | None:
    """主城實地地圖上 ``object_id`` 那個情境物件的名字與頭像（守印人、工坊師傅）。"""
    found = library.outdoor_map(CAPITAL_REGION, CAPITAL_REGION)
    if object_id is None or found is None:
        return None
    spot = next((s for s in found.situation_objects if s.id == object_id), None)
    if spot is None:
        return None
    portrait = None if spot.figure is None else spot.figure.portrait
    return RangeSpeakerView(
        name_zh=spot.name_zh or object_id, portrait=portrait, region=CAPITAL_REGION
    )


def workshop_view(
    library: ContentLibrary, char: CharacterState, *, in_battle: bool
) -> WorkshopView | None:
    """``WorldView.workshop``（PR-2a）：主城工坊師傅的選單。人在主城、內容有靶場與師傅選單時才有。
    能不能開「靶場試玩」與原因和端點同一個函式（:func:`~trpg.world.opening.practice_problem`）。"""
    newcomer = library.world_newcomer
    arena = None if newcomer is None else newcomer.range
    menu = None if arena is None else arena.workshop
    if arena is None or menu is None or not in_capital(char):
        return None
    capital = capital_name(library)
    problem = practice_problem(library, char, in_battle=in_battle)
    return WorkshopView(
        title_zh=f"{capital}{menu.title_zh}",
        capital_zh=capital,
        speaker=_capital_figure(library, menu.master_object),
        line=RangeLineView(speaker_zh=menu.line.speaker_zh, text_zh=menu.line.text_zh),
        practice_zh=menu.practice_zh,
        practice_note_zh=menu.practice_note_zh,
        rework_zh=menu.rework_zh,
        rework_note_zh=menu.rework_note_zh,
        footer_zh=menu.footer_zh,
        practice_available=problem is None,
        practice_blocked_zh=problem,
        practice_new=PRACTICE_SEEN not in char.hints_seen,
        seen_id=PRACTICE_SEEN,
    )


def _mentor(library: ContentLibrary, newcomer: NewcomerContent) -> RangeSpeakerView | None:
    """導師（葛蘭）的頭像：新手區人設卡的 ``portrait``。"""
    table = library.world_event_content.npcs.get(newcomer.start_region)
    card = None if table is None else table.npc_by_id().get(newcomer.mentor_npc or "")
    if card is None:
        return None
    return RangeSpeakerView(
        name_zh=card.name_zh, portrait=card.portrait, region=newcomer.start_region
    )


def _choice_view(
    library: ContentLibrary, newcomer: NewcomerContent, arena: RangeContent, char: CharacterState
) -> RangeChoiceView | None:
    """入門期的「正式選定」畫面資料（OB-5）：在主城＝守印人、主城地名；其他＝導師那裡。"""
    if char.opening is None or char.opening.stage != "starter":
        return None
    problem = choice_problem(library, char)
    capital = in_capital(char)
    return RangeChoiceView(
        available=problem is None,
        blocked_zh=problem,
        in_capital=capital,
        place_zh=f"{capital_name(library)}工坊靶場" if capital else arena.choose_place_zh,
        speaker=_keeper(library, arena) if capital else _mentor(library, newcomer),
        lines=_lines(arena.choose_capital if capital else arena.choose),
        done=_lines(arena.choose_capital_done if capital else arena.choose_done),
        npc=None if mentor_town(library) is None else newcomer.mentor_npc,
        objects=arena.choose_objects,
    )


def _recommended(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """推薦的關鍵字（見 ``RangeView.recommended_keywords``）：還不能正式選定時不算。"""
    if choice_problem(library, char) is not None:
        return ()
    return recommended_keywords(library, char, char.hero.weapon)


def _reselect_view(
    library: ContentLibrary, newcomer: NewcomerContent, arena: RangeContent, char: CharacterState
) -> RangeReselectView | None:
    """正式選定之後的免費重選（OB-3 資料；OB-6 加畫面用的地方、台詞與小牌的資格）。"""
    opening = char.opening
    if opening is None or opening.stage != "chosen":
        return None
    problem = reselect_problem(library, char)
    capital = in_capital(char)
    names = {s.id: s.name_zh for s in char.generated_skills}
    returned = tuple(
        names.get(s) or library.skills[s].name_zh
        for s in reselect_returns(char)
        if s in names or s in library.skills
    )
    return RangeReselectView(
        available=problem is None,
        blocked_zh=problem,
        used=opening.reselect_used,
        before_level=OPENING_END_LEVEL,
        weapon=opening.weapon,
        keywords=opening.keywords,
        returned_zh=returned,
        weapon_returned=starter_weapon_held(library, char),
        lost_zh=reselect_losses(library, char),
        window_open=reselect_window_problem(char) is None,
        place_zh=place_problem(library, "重選"),
        in_capital=capital,
        here_zh=f"{capital_name(library)}工坊靶場" if capital else arena.choose_place_zh,
        speaker=_keeper(library, arena) if capital else _mentor(library, newcomer),
        lines=_lines(arena.reselect_capital if capital else arena.reselect),
        done=_lines(arena.reselect_capital_done if capital else arena.reselect_done),
        npc=None if mentor_town(library) is None else newcomer.mentor_npc,
        objects=arena.choose_objects,
    )


def range_recommend(
    library: ContentLibrary, char: CharacterState, weapon: str
) -> RangeRecommendResponse:
    """``GET …/characters/{id}/range/recommend?weapon=``（OB-3）：照 ``weapon`` 算推薦的關鍵字
    （規則與快取在 :func:`trpg.world.opening.recommended_keywords`：同一個角色、同一把武器只算
    一次）。只在可以正式選定或可以重選時回應；其他時候拋 :class:`WorldActionError`（原因是中文）。
    重選時入門招與它們的使用紀錄已經收回，照 21.5 第 4 點算不出第 1 個推薦，所以回空的清單。"""
    range_content(library)  # 沒有靶場時拋錯
    problem = _recommend_problem(library, char)
    if problem is not None:
        raise WorldActionError(f"現在沒有推薦的關鍵字：{problem}")
    if weapon not in start_weapons(library):
        raise WorldActionError(f"靶場沒有這把武器：{weapon}")
    return RangeRecommendResponse(
        weapon=weapon, keywords=recommended_keywords(library, char, weapon)
    )


def _recommend_problem(library: ContentLibrary, char: CharacterState) -> str | None:
    """不能查推薦的原因：要能正式選定（入門期、打完新手第 2 步、人在霧渡鎮或主城）或能重選。"""
    if char.opening is None:
        return "開局已經完成"
    if char.opening.stage == "chosen":
        return reselect_problem(library, char)
    return choice_problem(library, char)


def open_range_trial(
    store: WorldStore, character_id: str, body: RangeTrialRequest, owner: str | None
) -> RangeTrialResponse:
    """開一場靶場試打（沙盒）：不寫日誌、不改角色存檔、不登記成角色的戰鬥。"""
    with store.lock:
        synced = store.sync(character_id)
        if synced.battle is not None:
            raise WorldActionError("戰鬥進行中，先打完這場")
        library = store.library
        range_content(library)  # 沒有靶場時拋錯
        trial = range_trial(library, synced.char, body.weapon, body.keywords)
    weapon_name = library.weapons[body.weapon].name_zh
    title = f"靶場試打：{weapon_name}" if trial.demo else f"看示範：{weapon_name}"
    return _open_trial(store, character_id, trial, title, owner)


def open_range_practice(
    store: WorldStore, character_id: str, owner: str | None
) -> RangeTrialResponse:
    """``POST …/characters/{id}/range/practice``（PR-2a）：工坊師傅的「靶場試玩」——自己的技能與
    裝備打木樁（#147 測試模式）。不能開時拋 :class:`WorldActionError`（原因＝
    :func:`~trpg.world.opening.practice_problem`，和師傅選單上寫的同一句）。和開局試打一樣是沙盒：
    不寫日誌、不改角色存檔、不登記成角色的戰鬥。"""
    with store.lock:
        synced = store.sync(character_id)
        library = store.library
        problem = practice_problem(library, synced.char, in_battle=synced.battle is not None)
        if problem is not None:
            raise WorldActionError(problem)
        trial = own_practice(library, synced.char)
    title = f"{PRACTICE_TITLE_ZH}：{library.weapons[synced.char.hero.weapon].name_zh}"
    return _open_trial(store, character_id, trial, title, owner)


def close_range_trial(store: WorldStore, character_id: str) -> None:
    """``DELETE …/characters/{id}/range/trial``（PR-2a）：刪掉這個角色目前的靶場試打（開局試打或
    靶場試玩）；沒有也不報錯。"""
    with store.lock:
        store.character(character_id)  # 角色不存在時 404
    store.close_trial(character_id)


def _open_trial(
    store: WorldStore, character_id: str, trial: RangeTrial, title: str, owner: str | None
) -> RangeTrialResponse:
    """在戰鬥工作階段表開一場沙盒（一角色一場：先刪同角色的舊場；只給開的人，6S-1）。"""
    store.close_trial(character_id)
    battle, records = store.battles.open(trial.setup, trial.seed)
    battle.owner = owner  # 只給開的人（6S-1）
    store.track_trial(character_id, battle.battle_id)
    with battle.lock:
        out = battle_response(battle, records)
    return RangeTrialResponse(
        title_zh=title,
        demo=trial.demo,
        skills_zh=tuple(s.name_zh for s in trial.skills),
        battle=out,
    )
