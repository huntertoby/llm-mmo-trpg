"""主城工坊靶場的畫面資料與沙盒試打（Phase TR-1，#134；規則在 :mod:`trpg.world.opening`）。

- :func:`range_view`：未完成開局的角色在 ``WorldView.opening`` 拿到的資料（開局種子、武器架的大類
  順序、木樁、每大類的示範招、守印人的台詞）。武器清單與關鍵字預覽沿用一輪開局的
  ``GET /api/runs/start-options``、``POST /api/runs/start-preview``（帶這裡的 ``seed``，預覽的招就是
  確定出發會給的招）。
- :func:`open_range_trial`：``POST /api/world/characters/{id}/range/trial``——在戰鬥工作階段表開一場
  沙盒（只綁帳號、**不登記成角色的戰鬥**），所以打完不回寫世界：不寫日誌、不給經驗掉落、不耗 HP
  法力。播放走既有戰鬥畫面。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from trpg.api.presenter import battle_response
from trpg.api.skill_cards import skill_card
from trpg.api.world_range_schemas import (
    CLASS_ZH,
    RangeDemoView,
    RangeDummyView,
    RangeLineView,
    RangeRecommendResponse,
    RangeTrialRequest,
    RangeTrialResponse,
    RangeView,
)
from trpg.content.library import ContentLibrary
from trpg.roguelite.start import start_weapons
from trpg.world.errors import WorldActionError
from trpg.world.opening import range_content, range_trial, recommended_keywords
from trpg.world.opening_choice import choice_problem
from trpg.world.state import CharacterState

if TYPE_CHECKING:
    from trpg.api.world import WorldStore

__all__ = ["open_range_trial", "range_recommend", "range_view"]


def range_view(library: ContentLibrary, char: CharacterState) -> RangeView | None:
    """未完成開局時的靶場資料；已完成或沒有靶場內容時 ``None``。"""
    if char.opening is None:
        return None
    newcomer = library.world_newcomer
    arena = None if newcomer is None else newcomer.range
    if arena is None:
        return None
    racks = tuple(
        RangeDemoView(
            weapon_class=cls,
            name_zh=CLASS_ZH[cls],
            skills=tuple(skill_card(library, library.skills[s]) for s in arena.demos[cls]),
            starter_weapon=arena.starters[cls],
            starter_weapon_zh=library.weapons[arena.starters[cls]].name_zh,
            notes_zh={s: arena.demo_notes[s] for s in arena.demos[cls] if s in arena.demo_notes},
        )
        for cls in arena.racks
    )
    return RangeView(
        seed=char.opening.seed,
        stage=char.opening.stage,
        weapon_class=char.opening.weapon_class,
        recommended_keywords=_recommended(library, char),
        racks=racks,
        dummies=tuple(RangeDummyView(label_zh=d.label_zh) for d in arena.dummies),
        intro=tuple(RangeLineView(speaker_zh=x.speaker_zh, text_zh=x.text_zh) for x in arena.intro),
        done=tuple(RangeLineView(speaker_zh=x.speaker_zh, text_zh=x.text_zh) for x in arena.done),
    )


def _recommended(library: ContentLibrary, char: CharacterState) -> tuple[str, ...]:
    """推薦的關鍵字（見 ``RangeView.recommended_keywords``）：還不能正式選定時不算。"""
    if choice_problem(library, char) is not None:
        return ()
    return recommended_keywords(library, char, char.hero.weapon)


def range_recommend(
    library: ContentLibrary, char: CharacterState, weapon: str
) -> RangeRecommendResponse:
    """``GET …/characters/{id}/range/recommend?weapon=``（OB-3）：照 ``weapon`` 算推薦的關鍵字
    （規則與快取在 :func:`trpg.world.opening.recommended_keywords`：同一個角色、同一把武器只算
    一次）。只在可以正式選定時回應；其他時候拋 :class:`WorldActionError`（原因是中文）。"""
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
    """不能查推薦的原因：要能正式選定（入門期、打完新手第 2 步、人在霧渡鎮或主城）。"""
    if char.opening is None:
        return "開局已經完成"
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
    battle, records = store.battles.open(trial.setup, trial.seed)
    battle.owner = owner  # 只給開的人（6S-1）
    weapon_name = library.weapons[body.weapon].name_zh
    title = f"靶場試打：{weapon_name}" if trial.demo else f"看示範：{weapon_name}"
    with battle.lock:
        out = battle_response(battle, records)
    return RangeTrialResponse(
        title_zh=title,
        demo=trial.demo,
        skills_zh=tuple(s.name_zh for s in trial.skills),
        battle=out,
    )
