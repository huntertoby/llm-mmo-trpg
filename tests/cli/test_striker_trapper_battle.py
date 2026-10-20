"""Phase 2E-3 5.3：``build_striker``、``build_trapper`` 的 AI 戰鬥有層數與陷阱紀錄，重播一致。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trpg.cli.main import main
from trpg.content.library import load_library


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = main(argv)
    return code, capsys.readouterr().out


def test_striker_battle_accumulates_and_consumes_static_charge_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "striker.json"
    argv = ["battle", "--map", "test_flat_6x6", "--ally-build", "build_striker", "--seed", "57"]
    code, out = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0
    assert "施放「雷霆終結」" in out and "的「靜電」消耗：" in out
    data = json.loads(log.read_text(encoding="utf-8"))
    reasons = [e["reason"] for e in data["events"] if e["type"] == "stacks_changed"]
    assert "gained" in reasons and "consumed" in reasons
    code, replayed = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replayed


def test_trapper_battle_places_and_triggers_traps_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "trapper.json"
    argv = ["battle", "--map", "test_flat_6x6", "--ally-build", "build_trapper", "--seed", "1"]
    code, out = _run([*argv, "--log-json", str(log)], capsys)
    assert code == 0
    assert "設下陷阱「" in out and "踩中了" in out
    data = json.loads(log.read_text(encoding="utf-8"))
    types = {e["type"] for e in data["events"]}
    assert {"trap_placed", "trap_triggered"} <= types
    code, replayed = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in replayed


def test_the_new_builds_have_the_specified_skills() -> None:
    lib = load_library()
    builds = lib.builds.by_id()
    striker = builds["build_striker"].hero.skills
    assert {"skill_static_palm", "skill_thunder_finisher"} <= set(striker)
    assert (
        any(lib.skills[s].kind == "passive" for s in striker) and len(striker) == 7
    )  # 3D-6 加血痕疾行、3D-7b 加過載電流、3C-6a 加聚雷、3F-4a 加破甲連擊
    trapper = builds["build_trapper"].hero.skills
    assert {"skill_cinder_mine", "skill_bear_trap"} <= set(trapper)
    assert (
        any(lib.skills[s].skeleton == "control" for s in trapper) and len(trapper) == 7
    )  # 3D-6 加殘影之誓
    assert "skill_raise_skeleton" in trapper  # 3D-4a 的示範召喚技能（3D-4b 再整理到召喚師 build）


def test_the_grid_shows_only_the_player_teams_traps_and_the_unit_table_shows_stacks() -> None:
    from tests.engine.skill_helpers import U1  # noqa: PLC0415
    from tests.engine.test_traps import BEAR, place, scene  # noqa: PLC0415
    from trpg.cli.render import (  # noqa: PLC0415
        render_battle_grid,
        render_legend,
        render_unit_table,
    )
    from trpg.engine.events import StacksChanged, TrapPlaced  # noqa: PLC0415
    from trpg.narrative.events import describe_event  # noqa: PLC0415
    from trpg.shared.types import Team  # noqa: PLC0415

    state = place(scene(), BEAR, (4, 3))
    assert "^" in render_battle_grid(state) and "我方陷阱" in render_legend(state)
    enemy_view = state.clone()
    enemy_view.traps = [t for t in enemy_view.traps if t.team is Team.ENEMY]
    assert "^" not in render_battle_grid(enemy_view) and "我方陷阱" not in render_legend(enemy_view)
    state.units[U1].stacks = {"static_charge": 3}
    assert "靜電×3" in render_unit_table(state)
    placed = TrapPlaced(
        seq=1,
        round=1,
        owner_id=U1,
        team=Team.ALLY,
        pos=state.traps[0].pos,
        skill_id=BEAR,
        trigger="enter",
        rounds=3,
    )
    assert "設下陷阱「" in (describe_event(placed, state) or "")
    changed = StacksChanged(
        seq=2,
        round=1,
        unit_id=U1,
        stack_id="static_charge",
        before=0,
        after=2,
        reason="gained",
    )
    assert "累積：0 → 2 層" in (describe_event(changed, state) or "")
