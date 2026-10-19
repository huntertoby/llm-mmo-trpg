"""戰鬥陣容的組裝（CLI ``trpg battle`` 與網頁 API 共用；Phase 3-2 由 ``trpg.cli.battle`` 搬來）。"""

from __future__ import annotations

from collections.abc import Sequence

from trpg.content.library import ContentLibrary
from trpg.sim.matrix import library_with_builds

__all__ = [
    "DEFAULT_ALLIES",
    "DEFAULT_ENEMIES",
    "TEAM_SIZE",
    "UnknownBuildError",
    "build_allies",
    "default_lineup",
]

DEFAULT_ALLIES = ("hero_fighter", "hero_archer", "hero_mage")
DEFAULT_ENEMIES = ("bandit", "bandit_archer", "bandit_boss")

TEAM_SIZE = 3
"""``--ally-build`` 補齊到的隊伍人數（build 英雄 ＋ 標準隊友，與 sim matrix 相同）。"""


class UnknownBuildError(ValueError):
    """指定了不存在的 build。``unknown`` 為未知的 ID，``known`` 為可用的 ID（排序）。"""

    def __init__(self, unknown: Sequence[str], known: Sequence[str]) -> None:
        self.unknown = tuple(unknown)
        self.known = tuple(known)
        super().__init__(f"未知的 build：{', '.join(unknown)}（可用：{', '.join(known)}）")


def default_lineup(library: ContentLibrary, map_id: str) -> tuple[list[str], list[str]]:
    """地圖的預設陣容（``encounter``）。

    沒有時使用 :data:`DEFAULT_ALLIES`／:data:`DEFAULT_ENEMIES`。
    """
    encounter = library.map(map_id).encounter
    if encounter is None:
        return list(DEFAULT_ALLIES), list(DEFAULT_ENEMIES)
    return list(encounter.allies), list(encounter.enemies)


def build_allies(
    library: ContentLibrary, builds: Sequence[str], *, fill: bool = True
) -> tuple[ContentLibrary, list[str]]:
    """以 build 英雄組成我方：回傳「加入 build 英雄範本的內容庫」與我方單位範本 ID。

    ``fill`` 為真時以標準隊友補齊到 :data:`TEAM_SIZE` 人（``trpg battle --ally-build``）；
    為假時只用 ``builds``。有未知的 build 時拋出 :class:`UnknownBuildError`。
    """
    known = library.builds.by_id()
    unknown = [b for b in builds if b not in known]
    if unknown:
        raise UnknownBuildError(unknown, sorted(known))
    lib = library_with_builds(library)
    if not fill:
        return lib, list(builds)
    allies = [*builds, *library.builds.companions][: max(TEAM_SIZE, len(builds))]
    return lib, allies
