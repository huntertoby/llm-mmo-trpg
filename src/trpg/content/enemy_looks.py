"""一般敵人依單位 id 挑外觀（Phase QK-6a，#137 第 4 點；``docs/art/外觀變化方案.md`` 第 4 節）。

- 範本寫了 ``look_range``（:class:`~trpg.content.battle.LookRange`）的**一般敵人**（敵方、人形、
  非召喚、非頭目）開戰建立單位時，依「戰鬥初始種子＋範本 ID＋單位 ID＋欄位名」的 FNV-1a 64 位元
  雜湊在每一項範圍裡挑一個值，寫進 ``DollLook.custom``（前端疊在範本外觀之後畫）。
- 確定性：不用內建 ``hash()``、不用 ``random``、不耗戰鬥亂數；同一場（同種子）的同一個單位每次、
  每次重播都一樣；單位 ID 每場從同一組編號開始，種子進鍵讓不同場的同範本長得不一樣。
- 身分特徵保留：範本是髮髻或光頭時不換髮型，範本有大鬍子時不換鬍子，骷髏不變。
- 只在畫面：不影響數值與結算。

純函式。
"""

from __future__ import annotations

from typing import Final

from trpg.content.battle import BOSS_TAG, DollLook, LookChoice, LookRange, UnitTemplate
from trpg.content.races import RaceTable
from trpg.shared.rng import fnv1a64
from trpg.shared.types import Team

__all__ = [
    "IDENTITY_HAIR",
    "is_ordinary_enemy",
    "look_range_problems",
    "ordinary_enemy_doll",
    "pick_look",
]

IDENTITY_HAIR: Final[frozenset[str]] = frozenset({"bun", "none"})
"""範本的這些髮型是身分特徵（道士的髮髻、武僧的光頭），不被範圍覆蓋。"""

_RANGE_FIELDS: Final[tuple[str, ...]] = ("skin", "hair", "hair_color", "beard")


def _index(seed: int, template_id: str, unit_id: str, name: str, size: int) -> int:
    key = f"{seed}|{template_id}|{unit_id}|{name}".encode()
    return fnv1a64(key) % size


def pick_look(seed: int, template_id: str, unit_id: str, look_range: LookRange) -> LookChoice:
    """在範圍裡挑一組外觀（``seed``＝戰鬥的初始種子；每一項各自雜湊；空的範圍不挑）。"""
    picked: dict[str, object] = {}
    for name in _RANGE_FIELDS:
        options: tuple[object, ...] = getattr(look_range, name)
        if options:
            picked[name] = options[_index(seed, template_id, unit_id, name, len(options))]
    return LookChoice.model_validate(picked)


def is_ordinary_enemy(template: UnitTemplate, team: Team) -> bool:
    """一般敵人：敵方、非召喚、非頭目、人形（紙娃娃、沒有 ``creature``）。"""
    doll = template.doll
    return (
        team == Team.ENEMY
        and not template.summon
        and BOSS_TAG not in template.tags
        and doll is not None
        and doll.creature is None
        and not doll.skull
    )


def ordinary_enemy_doll(
    template: UnitTemplate, unit_id: str, team: Team, seed: int
) -> DollLook | None:
    """單位的紙娃娃外觀：一般敵人且範本有 ``look_range`` 時，依戰鬥初始種子與 id 挑一組寫進
    ``custom``；其他照範本。範本的身分特徵（髮髻、光頭、大鬍子）與已寫的 ``custom`` 保留。"""
    doll = template.doll
    look_range = template.look_range
    if look_range is None or doll is None or doll.custom is not None:
        return doll
    if not is_ordinary_enemy(template, team):
        return doll
    choice = pick_look(seed, template.id, unit_id, look_range)
    keep: dict[str, object] = {}
    if doll.hair in IDENTITY_HAIR:
        keep["hair"] = None
    if doll.beard:
        keep["beard"] = None
    if keep:
        choice = choice.model_copy(update=keep)
    if choice.is_empty():
        return doll
    return doll.model_copy(update={"custom": choice})


def look_range_problems(table: RaceTable | None, look_range: LookRange) -> list[str]:
    """範圍不在參照種族 ``look_options`` 內的地方（繁體中文；載入內容庫時檢查）。"""
    if table is None:
        return ["沒有 races.yaml，不能寫 look_range"]
    race = table.by_id().get(look_range.race)
    if race is None:
        return [f"look_range 的種族不存在：{look_range.race}"]
    options = race.options()
    problems: list[str] = []
    for name in _RANGE_FIELDS:
        allowed: tuple[object, ...] = getattr(options, name)
        bad = [v for v in getattr(look_range, name) if v not in allowed]
        if bad:
            listed = ", ".join(map(str, bad))
            problems.append(f"look_range.{name} 不在{race.name_zh}的 look_options 內：{listed}")
    return problems
