"""換種族（Phase 6R-1，#138；``docs/design/07-角色成長.md`` 7.7 實作細節第 6 點）。

#138 把狐族改成獸耳族（種族 ID 照舊 ``fox``）：舊狐族角色直接換新規則，**這一季開放一次免費換種族**
（不佔 #108「花任務幣、每季 1 次」的那一次；#108 本身還沒做）。

- 哪一季開放：``world/season.yaml`` 的 ``free_race_change_seasons``（內容資料；第一季 ``s1``）。
- 條件：在主城（#108「在主城重選種族」）、沒有待處理的遭遇、這一季還沒用過免費換種族、新種族存在
  且和目前不同。
- 結果：主角的種族換掉（紙娃娃不動：跟著種族的部件前端照種族預設畫，
  ``client/src/render/appearance.ts``）；
  記下 ``free_race_change_used``（數值類，季末清掉）。只改種族，等級、技能、裝備、屬性都不變。

純函式：不讀時間、不耗亂數。
"""

from __future__ import annotations

from trpg.content.fields import CAPITAL_REGION
from trpg.content.library import ContentLibrary
from trpg.world.actions import ChangeRaceAction, RaceChangedEvent, WorldEvent
from trpg.world.errors import WorldActionError
from trpg.world.state import CharacterState, WorldState

__all__ = ["apply_race_change", "free_race_change_open", "race_change_problem"]


def free_race_change_open(library: ContentLibrary, world: WorldState) -> bool:
    """這一季有沒有開放免費換種族（``world/season.yaml`` 的 ``free_race_change_seasons``）。"""
    season = library.world_season
    return season is not None and world.season_id in season.free_race_change_seasons


def race_change_problem(
    library: ContentLibrary, world: WorldState, char: CharacterState, race: str | None
) -> str | None:
    """不能免費換種族的原因（繁體中文）；可以時 ``None``。``race`` 為 ``None`` 時只檢查「現在能不能
    換」（給畫面顯示按鈕用），不檢查新種族。"""
    problem = _when_problem(library, world, char)
    if problem is not None or race is None:
        return problem
    table = library.ruleset.races
    known = set() if table is None else {r.id for r in table.races}
    if race not in known:
        return f"未知的種族：{race}"
    if race == char.hero.race:
        return "已經是這個種族了"
    return None


def _when_problem(library: ContentLibrary, world: WorldState, char: CharacterState) -> str | None:
    if not free_race_change_open(library, world):
        return "這一季沒有開放免費換種族"
    if char.free_race_change_used:
        return "這一季的免費換種族已經用過了"
    if char.region != CAPITAL_REGION:
        return "只有在主城能換種族"
    if char.pending_encounter is not None:
        return "還有沒處理的遭遇，不能換種族"
    return None


def apply_race_change(
    library: ContentLibrary,
    world: WorldState,
    char: CharacterState,
    action: ChangeRaceAction,
    _now: int,
) -> tuple[CharacterState, tuple[WorldEvent, ...]]:
    """世界動作 ``change_race``（不合法拋 :class:`WorldActionError`，狀態不變）。"""
    problem = race_change_problem(library, world, char, action.race)
    if problem is not None:
        raise WorldActionError(problem)
    before = char.hero.race
    hero = char.hero.model_copy(update={"race": action.race})
    char = char.model_copy(update={"hero": hero, "free_race_change_used": True})
    return char, (RaceChangedEvent(from_race=before, to_race=action.race, free=True),)
