"""武器擴充第一批（Phase 3-24a1）的 CLI 驗收：持新武器的白板主角打整場，`--log-json` 的紀錄
重播一致，而且武器特性真的在整場戰鬥裡發動。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from trpg.cli.main import main

type Events = list[dict[str, Any]]


def _axe_breaks_armor(events: Events) -> bool:
    return any(e["type"] == "status_applied" and e["status_id"] == "armor_broken" for e in events)


def _hammer_pushes_after_a_hit(events: Events) -> bool:
    """主角（unit_0001）的普攻傷害之後緊接著目標被強制位移。"""
    for i, e in enumerate(events):
        by_hero = e["type"] == "damage_dealt" and e["source_id"] == "unit_0001"
        pushed = any(
            x["type"] == "unit_moved" and x["mode"] == "forced" for x in events[i + 1 : i + 3]
        )
        if by_hero and e["cause"] == "attack" and pushed:
            return True
    return False


def _priest_heals(events: Events) -> bool:
    return any(e["type"] == "healed" and e["cause"] == "heal" for e in events)


def _attacks(events: Events) -> bool:
    return any(e["type"] == "attack_rolled" and e["attacker_id"] == "unit_0001" for e in events)


# 種子 0 的 open_plain：每個特性都在整場戰鬥中發動（矛與圖騰杖沒有命中特性，只驗證能打整場與重播）
_BUILDS: list[tuple[str, Callable[[Events], bool]]] = [
    ("build_blank_axe", _axe_breaks_armor),
    ("build_blank_hammer", _hammer_pushes_after_a_hit),
    ("build_blank_spear", _attacks),
    ("build_blank_priest", _priest_heals),
    ("build_blank_totemist", _attacks),
]


@pytest.mark.parametrize(("build", "fired"), _BUILDS, ids=[b for b, _ in _BUILDS])
def test_blank_weapon_heroes_play_a_whole_battle_and_replay_exactly(
    build: str,
    fired: Callable[[Events], bool],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "weapon.json"
    argv = ["battle", "--map", "open_plain", "--seed", "0", "--ally-build", build]
    assert main([*argv, "--log-json", str(log)]) == 0
    capsys.readouterr()
    data = json.loads(log.read_text(encoding="utf-8"))
    assert fired(data["events"]), f"{build} 沒有發動武器特性"
    assert main(["battle", "replay", str(log)]) == 0
    assert "重播驗證通過" in capsys.readouterr().out


@pytest.mark.parametrize(
    "build",
    ["build_blank_axe", "build_blank_hammer", "build_blank_spear", "build_blank_priest"],
)
def test_weapon_heroes_replay_on_an_obstacle_map(
    build: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """有物件與高度差的地圖（ruined_fort）：拋射與觸及的視線與藉機攻擊判斷，重播也一致。"""
    log = tmp_path / "fort.json"
    argv = ["battle", "--map", "ruined_fort", "--seed", "1", "--ally-build", build]
    assert main([*argv, "--log-json", str(log)]) == 0
    capsys.readouterr()
    assert main(["battle", "replay", str(log)]) == 0
    assert "重播驗證通過" in capsys.readouterr().out
