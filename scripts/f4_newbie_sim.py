"""6F-4 C1／#128：新手任務鏈 3 場固定戰的自動打摘要（渡口石階、竹林小徑、雨中梯田）。

流程（照實際玩法，全在本機、不開伺服器）：在暫存資料夾建新角色（出生在雲嶺小鎮，跳過主城那段）→
接新手任務 → 用 BFS 一次走一格到下一張圖、走進固定戰那一隊的視野（盡量避開其他隊的視野，碰到照打）
→ 效用 AI 代打主角（:func:`trpg.world.battle.auto_steps`）→ ``fight`` → 三選一跳過 → 下一步。
輸了這個角色就停（後面的場次不算）。

只印摘要表：勝率、主角倒下、先手（敵／無／我）、打完的等級。用法::

    uv run python scripts/f4_newbie_sim.py [每種開局的場數＝20] [只打前幾場＝3]
"""

from __future__ import annotations

import dataclasses
import os
import sys
import tempfile
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from trpg.api import world as api_world
from trpg.api.app import create_app
from trpg.api.world import START_REGION, WorldStore
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_quests import WinBattle
from trpg.shared.types import UnitId
from trpg.world.actions import AcceptQuestAction, FightAction, OfferPickAction
from trpg.world.battle import _run, auto_steps, prepare_battle
from trpg.world.field import field_grid, field_map, placed
from trpg.world.field_actions import WalkAction
from trpg.world.field_enemies import field_enemies
from trpg.world.state import CharacterState

NOON = 12 * 3600
STARTS = {
    "A 火焰法杖 點燃＋帶電": ("fire_staff", ("ignite", "charged")),
    "B 匕首 冰凍＋隱蔽": ("dagger", ("frozen", "concealed")),
    "近戰 巨劍 倒地＋撞擊": ("greatsword", ("prone", "collision")),
    "遠程 弓 標記＋高處": ("bow", ("marked", "high_ground")),
}
FIGHTS = (
    ("ferry_steps", "bandit_raiders"),
    ("bamboo_path", "mist_wolf_pack"),
    ("rain_terraces", "terrace_clash"),
)
ROUTE = {"mist_ferry": "ferry_steps", "ferry_steps": "bamboo_path", "bamboo_path": "rain_terraces"}
type XY = tuple[int, int]


@dataclass
class Tally:
    played: int = 0
    wins: int = 0
    hero_down: int = 0
    enemy_first: int = 0
    none_first: int = 0
    ally_first: int = 0
    other_fights: int = 0
    levels: list[int] = field(default_factory=list)


def _bfs(library: ContentLibrary, char: CharacterState, goals: set[XY], avoid: set[XY]) -> list[XY]:
    assert char.field is not None
    found = field_map(library, char.field.map)
    assert found is not None
    grid = field_grid(library, char, found)
    climb = library.ruleset.core.max_climb_height
    width, height = found.size
    start = (char.field.x, char.field.y)
    prev: dict[XY, XY] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here in goals:
            path = [here]
            while path[-1] != start:
                path.append(prev[path[-1]])
            return path[::-1][1:]
        x, y = here
        for cell in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if cell in seen or (cell in avoid and cell not in goals):
                continue
            if not (0 <= cell[0] < width and 0 <= cell[1] < height):
                continue
            if not grid.can_step(here, cell, climb):
                continue
            seen.add(cell)
            prev[cell] = here
            queue.append(cell)
    return []


def _fight(store: WorldStore, cid: str) -> tuple[bool, bool, str | None, str]:
    """代打這場遭遇：（贏了、主角倒下、先手、陣容）。"""
    library = store.library
    char = store.character(cid)
    encounter = char.pending_encounter
    assert encounter is not None
    contact = encounter.contact
    first = None if contact is None else contact.first
    group = "" if contact is None else contact.group
    steps = auto_steps(library, char)
    state, _ = _run(prepare_battle(library, char), steps)
    hero = state.units[UnitId("unit_0001")]
    store._apply(char, FightAction(steps=steps), NOON)  # 開戰端點之外的捷徑（腳本用）
    if store.character(cid).pending_offers:
        store.act(cid, OfferPickAction(pick=None))
    return state.winner == "ally", hero.hp <= 0, first, group


def _reach_and_fight(
    store: WorldStore, cid: str, target_map: str, group: str, tally: Tally
) -> tuple[bool, bool, str | None] | None:
    """一次走一格：先到 ``target_map``，再走進 ``group`` 的視野。"""
    library = store.library
    for _ in range(400):
        char = placed(library, store.character(cid))
        assert char.field is not None
        here_map = char.field.map
        enemies = field_enemies(library, store.world(), char, NOON)
        avoid = {c for e in enemies for c in e.sight if e.spawn.group != group}
        if here_map == target_map:
            goals = {c for e in enemies if e.spawn.group == group for c in e.sight}
            if not goals:
                return None
        else:
            found = field_map(library, here_map)
            assert found is not None
            goals = {c for e in found.exits if e.to == ROUTE[here_map] for c in e.at}
        path = _bfs(library, char, goals, avoid) or _bfs(library, char, goals, set())
        if not path:
            return None
        store.act(cid, WalkAction(path=(path[0],)))
        if store.character(cid).pending_encounter is None:
            continue
        won, down, first, fought = _fight(store, cid)
        if fought == group:
            return won, down, first
        tally.other_fights += 1
        if not won:
            return None
    return None


def _play(store: WorldStore, cid: str, target_map: str, group: str, tally: Tally) -> bool:
    """走到固定戰、打完、記一筆；回傳贏了沒（輸了這個角色就停）。"""
    reached = _reach_and_fight(store, cid, target_map, group, tally)
    if reached is None:
        return False
    won, down, first = reached
    tally.played += 1
    tally.wins += won
    tally.hero_down += down
    if first == "enemy":
        tally.enemy_first += 1
    elif first == "ally":
        tally.ally_first += 1
    else:
        tally.none_first += 1
    tally.levels.append(store.character(cid).level)
    return won


def _pct(n: int, d: int) -> str:
    return f"{n}/{d}（{n * 100 // max(1, d)}%）"


def _print(table: dict[tuple[str, str], Tally], runs: int) -> None:
    print(f"每種開局 {runs} 場；先手＝敵方／沒有／我方")
    print("| 開局 | 地點 | 勝 | 主角倒下 | 先手 | 打完等級 | 路上其他戰 |")
    print("|---|---|---|---|---|---|---|")
    for (name, place), t in table.items():
        first = f"{t.enemy_first}/{t.none_first}/{t.ally_first}"
        levels = "、".join(str(x) for x in sorted(set(t.levels)))
        cells = [name, place, _pct(t.wins, t.played), _pct(t.hero_down, t.played), first, levels]
        print("| " + " | ".join([*cells, str(t.other_fights)]) + " |")


def _fixed_only(library: ContentLibrary) -> ContentLibrary:
    """記憶體裡把新手任務各步的 ``win_battle`` 加上固定戰的陣容（只算固定戰，巡邏不算）。"""
    groups = dict(FIGHTS)
    table = library.world_quests.quests["cloud_ridge"]
    quests = []
    for quest in table.quests:
        if quest.id == "starter_ferry":
            steps = []
            for step in quest.steps:
                when = tuple(
                    c.model_copy(update={"group": groups[c.location]})
                    if isinstance(c, WinBattle) and c.location in groups
                    else c
                    for c in step.when
                )
                steps.append(step.model_copy(update={"when": when}))
            quests.append(quest.model_copy(update={"steps": tuple(steps)}))
            continue
        quests.append(quest)
    tables = {
        **library.world_quests.quests,
        "cloud_ridge": table.model_copy(update={"quests": tuple(quests)}),
    }
    content = dataclasses.replace(library.world_quests, quests=tables)
    return dataclasses.replace(library, world_quests=content)


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    fights = FIGHTS[: int(sys.argv[2])] if len(sys.argv) > 2 else FIGHTS  # noqa: PLR2004
    library = load_library()
    # 調數值用（只改記憶體裡的範本）：F4_UNITS="bandit_rookie.max_hp=20,bandit_rookie.speed=4"
    for item in filter(None, os.environ.get("F4_UNITS", "").split(",")):
        key, value = item.split("=")
        unit, attr = key.split(".")
        typed: object = int(value) if value.isdigit() else value
        library.units[unit] = library.units[unit].model_copy(update={attr: typed})
    api_world.spawn_region = lambda _library: START_REGION  # type: ignore[assignment]  # 跳過主城
    if os.environ.get("F4_FIXED_ONLY") == "1":  # 試算：新手各步只有打贏固定戰才算（待 PM 決定）
        library = _fixed_only(library)
    table: dict[tuple[str, str], Tally] = {}
    for name, (weapon, keywords) in STARTS.items():
        for i in range(runs):
            with tempfile.TemporaryDirectory() as tmp:
                store = create_app(library, save_dir=Path(tmp)).state.world
                store.clock = lambda: NOON
                cid = store.create(f"s{i}", weapon, keywords, seed=1000 + i).character_id
                store.act(cid, AcceptQuestAction(quest="starter_ferry"))
                for target_map, group in fights:
                    tally = table.setdefault((name, target_map), Tally())
                    if not _play(store, cid, target_map, group, tally):
                        break
    _print(table, runs)


if __name__ == "__main__":
    main()
