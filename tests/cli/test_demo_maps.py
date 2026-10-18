"""四張示範地圖與 1B 的 CLI 選項（Phase 1 6.1-14、6.2-7；Phase 1C 3.6、4-5）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from trpg.cli.main import main

DEMOS = {
    # 地圖：戰鬥紀錄中應出現的環境互動（種子見 SEEDS；AI 或內容改動後種子會漂移，依需要重選）
    "oil_depot": ("爆炸了", "的油變成了火焰"),
    "bridge_chasm": ("木橋", "掉進了深淵", "命中 −2：矮牆掩護"),
    "swamp": ("傳導雷電", "天氣 ×", "盜賊盾衛"),
    "ruined_fort": ("半掩護 -2", "命中 −2：矮牆掩護"),
}


# 2A-2 起敵方有技能，種子 42 的吊橋戰沒有半掩護的畫面；2B-2 的預算校準調整了示範技能數值，
# 種子 42 的沼澤戰在第一個環境回合前就結束，改用種子 1；2C-4 的掩護判定只算射程內的敵人，
# 軌跡改變，吊橋戰改用種子 7（2C-4 的環境權重再次改變軌跡）、廢墟要塞改用種子 1；其餘仍用 42
SEEDS = {"bridge_chasm": 7, "swamp": 1, "ruined_fort": 1}


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.mark.parametrize("map_id", sorted(DEMOS))
def test_demo_map_battle_has_winner_and_interactions(
    map_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    seed = SEEDS.get(map_id, 42)
    code, out, _ = _run(["battle", "--map", map_id, "--seed", str(seed)], capsys)
    assert code == 0
    verdict = out.split("勝方：")[1].splitlines()[0]
    assert "勝利" in verdict
    for fragment in DEMOS[map_id]:
        assert fragment in out, fragment
    if map_id != "ruined_fort":  # 廢墟要塞沒有會變化的環境（沒有預告）
        assert "～ 環境回合 ～" in out and "環境預告：" in out


def test_demo_map_show(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["map", "show", "oil_depot"], capsys)
    assert code == 0
    assert "& 油桶" in out and "o 油" in out and "地圖事件：第 3 輪結束時 援軍" in out
    code, out, _ = _run(["map", "show", "swamp"], capsys)
    assert "天氣：rain" in out and "預設陣容：我方 hero_fighter,hero_archer,hero_stormcaller" in out
    code, out, _ = _run(["map", "show", "ruined_fort"], capsys)
    assert code == 0
    assert "@ 牆壁" in out and "_ 矮牆" in out and "[ 木箱" in out and "- 倒木" in out


@pytest.mark.parametrize("map_id", sorted(DEMOS))
def test_demo_maps_have_walls_and_half_cover(map_id: str) -> None:
    from tests.engine.helpers import library  # noqa: PLC0415

    lib = library()
    map_def = lib.map(map_id)
    rs = lib.ruleset
    assert "wall" in {map_def.tile_terrain(x, y) for y in range(10) for x in range(10)}
    assert any(rs.object_def(o.kind).has_tag("half_cover") for o in map_def.objects)


def test_shieldbearer_uses_guard_profile_and_appears_on_a_demo_map() -> None:
    from tests.engine.helpers import library  # noqa: PLC0415

    lib = library()
    shield = lib.unit("bandit_shieldbearer")
    assert shield.ai_profile == "guard"
    assert shield.armor_bonus > lib.unit("bandit").armor_bonus
    assert shield.reactions is not None
    assert any(
        r.reaction == "block" and r.when.event == "targeted_by_attack" for r in shield.reactions
    )
    users = [m for m in sorted(DEMOS) if "bandit_shieldbearer" in (lib.map(m).encounter.enemies)]  # type: ignore[union-attr]
    assert users


def test_demo_log_replays(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "depot.json"
    code, _, _ = _run(
        ["battle", "--map", "oil_depot", "--seed", "42", "--log-json", str(log)], capsys
    )
    assert code == 0
    code, out, _ = _run(["battle", "replay", str(log)], capsys)
    assert code == 0 and "重播驗證通過" in out


def test_simple_ai_weather_and_deploy_options(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(
        [
            "battle",
            "--map",
            "test_flat_6x6",
            "--seed",
            "1",
            "--ai",
            "simple",
            "--weather",
            "fog",
            "--deploy",
            "1,5;0,4",
        ],
        capsys,
    )
    assert code == 0 and "勝方：" in out
    assert "戰士：HP 60/60 法力 20/20 耐力 30 位置 (1, 5)" in out
    code, _, err = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "1", "--deploy", "5,5"], capsys
    )
    assert code == 2 and "不在我方起始區" in err
    code, _, err = _run(
        ["battle", "--map", "test_flat_6x6", "--seed", "1", "--deploy", "x"], capsys
    )
    assert code == 2 and "--deploy" in err
