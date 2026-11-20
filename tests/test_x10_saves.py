"""X10-3a：數值改版前（沒有記 ``quantity_scale`` 或不相符）的存檔直接拒絕。

三種情況：舊存檔被拒、新存檔可以讀、錯誤訊息的文字；roguelite 存檔（函式、CLI、API）與大世界角色
存檔（函式、API）各測一次。存檔都寫在暫存資料夾。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.world.helpers import NOON
from trpg.api.app import create_app
from trpg.api.world import WorldStore
from trpg.cli.main import main
from trpg.content.library import ContentLibrary
from trpg.roguelite import (
    OLD_UNIT_SAVE_NOTICE,
    RunSave,
    SaveFormatError,
    check_quantity_scale,
    dumps_save,
    loads_save,
    new_run,
    write_save,
)
from trpg.world.errors import WorldSaveFormatError
from trpg.world.save import (
    CHAR_SCALE_KEY,
    OLD_UNIT_CHAR_NOTICE,
    dumps_char,
    dumps_char_save,
    loads_char,
    loads_char_save,
)

RUN_NOTICE = "這是數值改版前的存檔，已經不能使用，請開新一輪。"
CHAR_NOTICE = "這是數值改版前的角色存檔，已經不能使用，請建立新角色。"


def test_notice_texts() -> None:
    assert OLD_UNIT_SAVE_NOTICE == RUN_NOTICE
    assert OLD_UNIT_CHAR_NOTICE == CHAR_NOTICE


def test_content_scale_is_ten(library: ContentLibrary) -> None:
    assert library.ruleset.core.quantity_scale == 10


# ---------------------------------------------------------------------------
# roguelite 存檔
# ---------------------------------------------------------------------------


def _run_save(library: ContentLibrary, scale: int | None) -> RunSave:
    return RunSave(run_id="x10", run=new_run(library, "build_push", 1), quantity_scale=scale)


@pytest.mark.parametrize("scale", [None, 1])
def test_old_run_save_is_rejected(library: ContentLibrary, scale: int | None) -> None:
    loaded = loads_save(dumps_save(_run_save(library, scale)))
    with pytest.raises(SaveFormatError) as caught:
        check_quantity_scale(library, loaded)
    assert str(caught.value) == RUN_NOTICE


def test_run_save_without_the_key_is_old(library: ContentLibrary) -> None:
    raw = json.loads(dumps_save(_run_save(library, 10)))
    del raw["quantity_scale"]
    with pytest.raises(SaveFormatError, match=RUN_NOTICE):
        check_quantity_scale(library, loads_save(json.dumps(raw)))


def test_new_run_save_reads(library: ContentLibrary) -> None:
    save = _run_save(library, 10)
    loaded = check_quantity_scale(library, loads_save(dumps_save(save)))
    assert loaded == save
    assert json.loads(dumps_save(save))["quantity_scale"] == 10


def test_write_save_needs_the_scale(library: ContentLibrary, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="quantity_scale"):
        write_save(tmp_path, _run_save(library, None))
    assert not tmp_path.joinpath("run-x10.json").exists()


def _cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_new_save_records_the_scale_and_old_save_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["run", "new", "--seed", "4", "--build", "build_push", "--attrs", "str=30,con=10"]
    code, _, _ = _cli([*argv, "--save-dir", str(tmp_path)], capsys)
    assert code == 0
    (path,) = tmp_path.glob("run-*.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["quantity_scale"] == 10
    code, shown, _ = _cli(["run", "show", str(path)], capsys)
    assert code == 0 and "build_push" in shown  # 新存檔可以讀
    del raw["quantity_scale"]  # 數值改版前的存檔沒有這個欄位
    path.write_text(json.dumps(raw), encoding="utf-8")
    code, out, err = _cli(["run", "show", str(path)], capsys)
    assert code == 1 and out == ""
    assert err.strip() == f"錯誤：{RUN_NOTICE}"
    code, _, err = _cli(["run", "auto", "--from", str(path)], capsys)
    assert code == 1
    assert err.strip() == f"錯誤：{RUN_NOTICE}"


def test_api_new_save_reads_and_old_save_is_rejected(
    library: ContentLibrary, tmp_path: Path
) -> None:
    saves = tmp_path / "saves"
    body = {"weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}
    with TestClient(create_app(library, save_dir=saves)) as client:
        reply = client.post("/api/runs", json=body)
        assert reply.status_code == 201, reply.text
        run_id = reply.json()["run_id"]
        assert client.post(f"/api/runs/{run_id}/save").status_code == 200
        path = saves / f"run-{run_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["quantity_scale"] == 10
        loaded = client.post("/api/runs/load", json={"run_id": run_id})
        assert loaded.status_code == 200, loaded.text  # 新存檔可以讀
        listed = client.get("/api/runs/saves")
        raw["quantity_scale"] = 1  # 不相符＝數值改版前
        path.write_text(json.dumps(raw), encoding="utf-8")
        rejected = client.post("/api/runs/load", json={"run_id": run_id})
        assert rejected.status_code == 422
        assert rejected.json() == {"detail": RUN_NOTICE}
        after = client.get("/api/runs/saves")  # 存檔列表略過數值改版前的存檔
        assert listed.status_code == after.status_code == 200
        assert run_id in listed.text and run_id not in after.text


# ---------------------------------------------------------------------------
# 大世界角色存檔
# ---------------------------------------------------------------------------

START = {"name": "阿霧", "weapon": "fire_staff", "keywords": ["ignite", "marked"], "seed": 0}


def _world_client(library: ContentLibrary, saves: Path) -> TestClient:
    app = create_app(library, save_dir=saves)
    store = app.state.world
    assert isinstance(store, WorldStore)
    store.clock = lambda: NOON
    return TestClient(app)


def test_world_character_save(calm: ContentLibrary, tmp_path: Path) -> None:
    saves = tmp_path / "saves"
    with _world_client(calm, saves) as first:
        reply = first.post("/api/world/characters", json=START)
        assert reply.status_code == 201, reply.text
        cid = reply.json()["character"]["character_id"]
    path = saves / "world" / "chars" / f"{cid}.json"
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text)
    assert raw[CHAR_SCALE_KEY] == 10  # 新存檔一律記
    char = loads_char_save(text, quantity_scale=10)  # 新存檔可以讀
    assert loads_char(text) == char
    assert dumps_char_save(char, quantity_scale=10) == text
    assert CHAR_SCALE_KEY not in json.loads(dumps_char(char))  # 重播比對用的不帶
    other = dumps_char_save(char, quantity_scale=1)  # 倍率不相符＝數值改版前
    with pytest.raises(WorldSaveFormatError, match=CHAR_NOTICE):
        loads_char_save(other, quantity_scale=10)
    assert loads_char(other) == char  # 季末重置等不檢查倍率的讀法照讀
    with _world_client(calm, saves) as second:  # 重開伺服器、從檔案讀
        assert second.get(f"/api/world/characters/{cid}").status_code == 200
    del raw[CHAR_SCALE_KEY]
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(WorldSaveFormatError) as caught:
        loads_char_save(path.read_text(encoding="utf-8"), quantity_scale=10)
    assert str(caught.value) == CHAR_NOTICE
    with _world_client(calm, saves) as third:
        rejected = third.get(f"/api/world/characters/{cid}")
        assert rejected.status_code == 422
        assert rejected.json() == {"detail": CHAR_NOTICE}
