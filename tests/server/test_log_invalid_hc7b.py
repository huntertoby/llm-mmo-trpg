"""HC-7 b.4（HC-4c 裁定 1）：重播與賽程封存讀到 pydantic 驗證失敗的舊紀錄時，給和「雜湊不符」
同一類的中文說明，不把驗證錯誤原文丟給玩家。

「舊格式的紀錄」用 HC-7 a 以前的結構做：紀錄格式版號相同，但內嵌規則包少了 HC-7 a 新增的
必填欄位 ``core.crit_range_floor``（``docs/phases/戰鬥紀錄格式變更.md`` 1.2：結構改變時不升
``LOG_FORMAT``）。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from tests.server.test_league_runner import AFTER, _world
from trpg.cli.main import main
from trpg.content.library import ContentLibrary
from trpg.server.league import LeagueError, LeagueRunner, LeagueStore
from trpg.server.season_archive import _replay_problems

EXPECTED = "紀錄的內容和目前的資料格式對不上"
RAW_PYDANTIC = ("Field required", "validation error", "pydantic")


def _old_structure(log_json: str) -> str:
    """把一份目前的紀錄改成 HC-7 a 以前的規則包結構（少一個必填欄位）。"""
    data = json.loads(log_json)
    del data["setup"]["ruleset"]["core"]["crit_range_floor"]
    return json.dumps(data, ensure_ascii=False)


def _no_raw_error(text: str) -> bool:
    return not any(raw in text for raw in RAW_PYDANTIC)


def test_cli_replay_explains_in_chinese(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "battle.json"
    assert main(["battle", "--map", "test_flat_6x6", "--seed", "7", "--log-json", str(log)]) == 0
    old = tmp_path / "old.json"
    old.write_text(_old_structure(log.read_text(encoding="utf-8")), encoding="utf-8")
    capsys.readouterr()
    assert main(["battle", "replay", str(old)]) == 1
    err = capsys.readouterr().err
    assert "不是有效的戰鬥紀錄" in err and EXPECTED in err and "無法確定重播結果一致" in err
    assert _no_raw_error(err)


@pytest.fixture(scope="module")
def two_entries(library: ContentLibrary) -> ContentLibrary:
    season = library.world_season
    assert season is not None and season.league is not None
    league = season.league.model_copy(update={"maps": ("open_plain",), "seeds": 1, "batch_size": 1})
    return dataclasses.replace(library, world_season=season.model_copy(update={"league": league}))


def test_league_replay_and_archive_explain_in_chinese(
    two_entries: ContentLibrary, tmp_path: Path
) -> None:
    store = LeagueStore(two_entries, tmp_path)
    record = store.start(_world(two_entries, ("build_support", "build_charger")), AFTER)
    assert LeagueRunner(store).run_pending(limit=1) == 1
    done = next(m for m in (store.record() or record).matches if m.status == "done")
    text = store.log_text(done.id)
    path = next(tmp_path.rglob(f"{done.id}.json"))
    path.write_text(_old_structure(text), encoding="utf-8")

    with pytest.raises(LeagueError) as caught:
        store.log(done.id)
    message = str(caught.value)
    assert message.startswith("這一場不能重播：") and EXPECTED in message
    assert _no_raw_error(message)

    log, problems = _replay_problems(path.read_text(encoding="utf-8"))
    assert log is None and len(problems) == 1
    assert EXPECTED in problems[0] and _no_raw_error(problems[0])
