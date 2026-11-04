"""6F-4c 第 6 項：雨中梯田巡邏的陣容掃描（新手第 3 步一路走過去）。

照 ``scripts/f4_newbie_sim.py`` 的玩法（BFS 一次走一格、效用 AI 代打、三選一跳過）：每個角色先打完
新手第 1、2 步，再從竹林小徑一路走到梯田固定戰 ``terrace_clash``。只在記憶體裡把梯田田埂巡邏那個
駐守點（``rain_terraces`` 的 ``sect_patrol`` 巡邏）換成候選陣容；``sect_patrol`` 本身不動
（別處也用）。

每個候選陣容輸出（分母 ＝ 打到第 3 步的角色數）：

- 倒下：第 3 步路上（巡邏或固定戰）主角倒下過的比例（目標 ≤ 40%）；
- 固定戰勝：打贏 ``terrace_clash`` 的比例（目標 ≥ 8/10）；
- 巡邏戰：碰到巡邏的場數、輸給巡邏的場數。

    uv run python scripts/f4c_terrace_sweep.py [每種開局的場數＝5] [--current]

``--current``：只量目前的內容（不換陣容），驗證選定的陣容。
"""

from __future__ import annotations

import dataclasses
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import f4_newbie_sim as sim
from trpg.api import world as api_world
from trpg.api.app import create_app
from trpg.api.world import START_REGION, WorldStore
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_encounters import EncounterGroupDef
from trpg.world.actions import AcceptQuestAction, WalkAction
from trpg.world.field import field_map, placed
from trpg.world.field_enemies import field_enemies

FIELD = "rain_terraces"
PATROLS = ("sect_patrol", "terrace_patrol")
"""梯田田埂巡邏駐守點的陣容（6F-4c 前是 ``sect_patrol``，之後是 ``terrace_patrol``）。"""
SWEEP = "terrace_patrol_sweep"
CANDIDATES: dict[str, tuple[str, ...]] = {
    "原本 4 名（2 雜兵＋劍客＋補師）": (
        *("sect_acolyte", "sect_acolyte"),
        *("sect_swordsman", "sect_alchemist"),
    ),
    "3 名：雜兵＋劍客＋補師": ("sect_acolyte", "sect_swordsman", "sect_alchemist"),
    "3 名：2 雜兵＋劍客": ("sect_acolyte", "sect_acolyte", "sect_swordsman"),
    "3 名：2 雜兵＋補師": ("sect_acolyte", "sect_acolyte", "sect_alchemist"),
    "2 名：雜兵＋劍客": ("sect_acolyte", "sect_swordsman"),
    "2 名：雜兵＋補師": ("sect_acolyte", "sect_alchemist"),
    "2 名：2 雜兵": ("sect_acolyte", "sect_acolyte"),
}


@dataclass
class Step3:
    reached: int = 0
    down: int = 0
    won_fixed: int = 0
    patrol_fights: int = 0
    patrol_losses: int = 0


def _variant(library: ContentLibrary, units: tuple[str, ...]) -> ContentLibrary:
    """記憶體裡加一個陣容 ``SWEEP``，梯田田埂巡邏的駐守點改用它（其他地方的 ``sect_patrol``
    不動）。"""
    table = library.world_encounters["cloud_ridge"]
    group = EncounterGroupDef(id=SWEEP, name_zh="梯田巡邏（掃描）", units=units)
    table = table.model_copy(update={"groups": (*table.groups, group)})
    encounters = {**library.world_encounters, "cloud_ridge": table}
    fields = dict(library.field_maps)
    found = fields[FIELD]
    spawns = tuple(
        s.model_copy(update={"group": SWEEP}) if s.group in PATROLS and s.patrol else s
        for s in found.spawns
    )
    fields[FIELD] = found.model_copy(update={"spawns": spawns})
    return dataclasses.replace(library, world_encounters=encounters, field_maps=fields)


def _step3(store: WorldStore, cid: str, tally: Step3) -> None:
    """從目前位置走到梯田固定戰；路上碰到的每一場都打（記倒下、巡邏勝負）。"""
    library = store.library
    tally.reached += 1
    down = False
    for _ in range(400):
        char = placed(library, store.character(cid))
        assert char.field is not None
        here = char.field.map
        enemies = field_enemies(library, store.world(), char, sim.NOON)
        avoid = {c for e in enemies for c in e.sight if e.spawn.group != "terrace_clash"}
        if here == FIELD:
            goals = {c for e in enemies if e.spawn.group == "terrace_clash" for c in e.sight}
            if not goals:
                break
        else:
            found = field_map(library, here)
            assert found is not None
            goals = {c for e in found.exits if e.to == sim.ROUTE[here] for c in e.at}
        path = sim._bfs(library, char, goals, avoid) or sim._bfs(library, char, goals, set())
        if not path:
            break
        store.act(cid, WalkAction(path=(path[0],)))
        if store.character(cid).pending_encounter is None:
            continue
        won, hero_down, _, group = sim._fight(store, cid)
        down = down or hero_down
        if group == "terrace_clash":
            tally.won_fixed += won
            break
        tally.patrol_fights += 1
        if not won:
            tally.patrol_losses += 1
            break
    tally.down += down


def _run(library: ContentLibrary, runs: int, per: dict[str, Step3] | None = None) -> Step3:
    """所有開局合計；給了 ``per`` 就另外記每種開局的。"""
    tally = Step3()
    for name, (weapon, keywords) in sim.STARTS.items():
        own = Step3()
        for i in range(runs):
            with tempfile.TemporaryDirectory() as tmp:
                store = create_app(library, save_dir=Path(tmp)).state.world
                store.clock = lambda: sim.NOON
                cid = store.create(f"s{i}", weapon, keywords, seed=1000 + i).character_id
                store.act(cid, AcceptQuestAction(quest="starter_ferry"))
                scratch = sim.Tally()
                if not all(sim._play(store, cid, m, g, scratch) for m, g in sim.FIGHTS[:2]):
                    continue
                _step3(store, cid, own)
        for key in ("reached", "down", "won_fixed", "patrol_fights", "patrol_losses"):
            setattr(tally, key, getattr(tally, key) + getattr(own, key))
        if per is not None:
            per[name] = own
    return tally


def _sum(items: Iterable[Step3]) -> Step3:
    total = Step3()
    for t in items:
        for key in ("reached", "down", "won_fixed", "patrol_fights", "patrol_losses"):
            setattr(total, key, getattr(total, key) + getattr(t, key))
    return total


def _pct(n: int, d: int) -> str:
    return f"{n}/{d}（{n * 100 // max(1, d)}%）"


def main() -> None:
    numbers = [a for a in sys.argv[1:] if a.isdigit()]
    runs = int(numbers[0]) if numbers else 5
    base = load_library()
    api_world.spawn_region = lambda _library: START_REGION  # type: ignore[assignment]  # 跳過主城
    print(f"每種開局 {runs} 個角色（4 種開局）；分母＝打到第 3 步的角色數")
    print("| 梯田巡邏陣容 | 倒下（≤40%） | 固定戰勝（≥80%） | 巡邏戰 | 輸給巡邏 |")
    print("|---|---|---|---|---|")
    only_current = "--current" in sys.argv
    if only_current:  # 只量目前內容（不換陣容）
        per: dict[str, Step3] = {}
        _run(base, runs, per)
        for name, t in [*per.items(), ("合計", _sum(per.values()))]:
            print(
                f"| {name} | {_pct(t.down, t.reached)} | {_pct(t.won_fixed, t.reached)} "
                f"| {t.patrol_fights} | {t.patrol_losses} |"
            )
        return
    for name, units in CANDIDATES.items():
        t = _run(_variant(base, units), runs)
        print(
            f"| {name} | {_pct(t.down, t.reached)} | {_pct(t.won_fixed, t.reached)} "
            f"| {t.patrol_fights} | {t.patrol_losses} |",
            flush=True,
        )


if __name__ == "__main__":
    main()
