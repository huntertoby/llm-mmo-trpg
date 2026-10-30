"""武器擴充第一批遠程（Phase 3-24a2）的 CLI 驗收：持弩、火槍的白板主角打整場，`--log-json` 的紀錄
重播一致，而且武器特性真的在整場戰鬥裡發動（火槍空膛後裝填、弩一箭射中多名敵人）。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from trpg.cli.main import main

type Events = list[dict[str, Any]]


def _longgun_reloads(events: Events) -> bool:
    return any(e["type"] == "weapon_reloaded" and e["unit_id"] == "unit_0001" for e in events)


def _hero_attacks(events: Events) -> bool:
    return any(e["type"] == "attack_rolled" and e["attacker_id"] == "unit_0001" for e in events)


def _fires_at_most_once_between_reloads(events: Events) -> bool:
    """主角每次普攻之間（彈匣 1 發）一定有一次裝填。"""
    fired_since_reload = 0
    for e in events:
        if e["type"] == "attack_rolled" and e["attacker_id"] == "unit_0001":
            fired_since_reload += 1
            if fired_since_reload > 1:
                return False
        elif e["type"] == "weapon_reloaded" and e["unit_id"] == "unit_0001":
            fired_since_reload = 0
    return True


_BUILDS: list[tuple[str, Callable[[Events], bool]]] = [
    ("build_blank_longgun", _longgun_reloads),
    ("build_blank_crossbow", _hero_attacks),
]


@pytest.mark.parametrize(("build", "fired"), _BUILDS, ids=[b for b, _ in _BUILDS])
def test_blank_ranged_heroes_play_a_whole_battle_and_replay_exactly(
    build: str,
    fired: Callable[[Events], bool],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "ranged.json"
    argv = ["battle", "--map", "open_plain", "--seed", "0", "--ally-build", build]
    assert main([*argv, "--log-json", str(log)]) == 0
    capsys.readouterr()
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data["format"] == "trpg-battle-log/90"
    assert fired(data["events"]), f"{build} 沒有發動武器特性"
    assert main(["battle", "replay", str(log)]) == 0
    assert "重播驗證通過" in capsys.readouterr().out


def test_longgun_never_fires_twice_without_reloading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "gun.json"
    argv = ["battle", "--map", "open_plain", "--seed", "1", "--ally-build", "build_blank_longgun"]
    assert main([*argv, "--log-json", str(log)]) == 0
    capsys.readouterr()
    events = json.loads(log.read_text(encoding="utf-8"))["events"]
    assert _hero_attacks(events)
    assert _fires_at_most_once_between_reloads(events)


@pytest.mark.parametrize("build", ["build_blank_longgun", "build_blank_crossbow"])
@pytest.mark.parametrize("map_id", ["ruined_fort", "narrow_halls"])
def test_ranged_heroes_replay_on_obstacle_maps(
    build: str, map_id: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """有物件、牆與高度差的地圖：直射的視線、半掩護、穿透的直線，重播也一致。"""
    log = tmp_path / "ranged.json"
    argv = ["battle", "--map", map_id, "--seed", "2", "--ally-build", build]
    assert main([*argv, "--log-json", str(log)]) == 0
    capsys.readouterr()
    assert main(["battle", "replay", str(log)]) == 0
    assert "重播驗證通過" in capsys.readouterr().out
