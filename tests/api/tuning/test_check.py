"""NW-1a T-A3／T-A4：草稿內容庫與驗證（非法值擋下、中文原因、對到欄位；digest）。"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from trpg.api.tuning import check as check_module
from trpg.api.tuning.check import library_errors, prepare
from trpg.api.tuning.diff import diff_text
from trpg.api.tuning.drafts import Change
from trpg.api.tuning.schemas import TuningChangeIn, TuningCheckResult
from trpg.api.tuning.service import TuningService
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import bundled_content_dir
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.roguelite.save import ruleset_hash
from trpg.shared.errors import ContentError
from trpg.world.save import content_digest

HEART = "units/ashen_heart.yaml"


def _in(path: str, old: int | None, new: int | str | None, file: str = HEART) -> TuningChangeIn:
    return TuningChangeIn(file=file, path=path, old=old, new=new)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (_in("max_hp", 160, 0), "不能小於 1"),
        (_in("speed", 0, -1), "不能小於 0"),
        (_in("attributes.str", 12, "abc"), "要填整數"),
        (_in("phases[1].trigger.permille", 600, 1500), "不能大於 999"),
        (_in("level", None, 0), "不能小於 1"),
        (_in("max_hp", 999, 150), "已經被改過（現在是 160）"),
        (_in("max_mana", 1, 5), "已經被改過（現在是 沒寫）"),
        (_in("name_zh", None, 1), "不開放"),
        (_in("phases[0].trigger.permille", None, 500), "不開放"),  # 開場階段沒有門檻
        (_in("max_hp", 6, 7, file="units/sim_duelist.yaml"), "不在數值工坊可改的範圍"),
        (
            _in("max_hp", 6, 7, file="units/summons/summon_afterimage.yaml"),
            "不在數值工坊可改的範圍",
        ),
    ],
)
def test_illegal_values_are_refused_with_field_reasons(
    read_service: TuningService, change: TuningChangeIn, message: str
) -> None:
    result = read_service.check("current", [change])
    assert not result.ok and not result.page_errors
    assert len(result.field_errors) == 1
    error = result.field_errors[0]
    assert (error.file, error.path) == (change.file, change.path)
    assert message in error.message_zh


def test_cross_field_problem_goes_to_the_page(read_service: TuningService) -> None:
    """後面的階段門檻要比前面低：模型層的錯，對不到單一欄位 → 頁首。"""
    result = read_service.check("current", [_in("phases[2].trigger.permille", 300, 700)])
    assert not result.ok and result.field_errors == []
    assert any("HP 門檻必須比前一個階段低" in e for e in result.page_errors)


def test_valid_draft_passes_the_full_content_check(read_service: TuningService) -> None:
    changes = [_in("max_hp", 160, 150), _in("element_mods.wind", None, 250)]
    result = read_service.check("current", changes)
    assert result.ok, result
    assert result.seconds > 0


def test_library_error_on_a_changed_file_is_attached_to_its_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prepared = prepare(
        bundled_content_dir(),
        TuningService(bundled_content_dir(), tmp_path).table,
        [Change(file=HEART, path="max_hp", old=160, new=150)],
    )

    def boom(root: Path) -> ContentLibrary:
        raise ContentError(root / HEART, "武器引用錯誤")

    monkeypatch.setattr(check_module, "load_checked_library", boom)
    fields, page = library_errors(tmp_path, prepared)
    assert [(e.path, e.message_zh) for e in fields] == [("max_hp", "武器引用錯誤")] and page == []

    def other(root: Path) -> ContentLibrary:
        raise ContentError(root / "maps" / "x.yaml", "地圖壞了")

    monkeypatch.setattr(check_module, "load_checked_library", other)
    assert library_errors(tmp_path, prepared) == ([], ["maps/x.yaml：地圖壞了"])


def _wait_for(ready: Callable[[], bool]) -> None:
    for _ in range(2000):  # 最多約 20 秒
        if ready():
            return
        time.sleep(0.01)
    raise AssertionError("等不到另一個執行緒")


def test_superseded_check_is_dropped(read_service: TuningService) -> None:
    """同一時間只做一個驗證；排隊時又來了新的，舊的那個回 ``superseded``。"""
    results: dict[str, TuningCheckResult] = {}
    start = read_service._generation

    def run(tag: str) -> None:
        results[tag] = read_service.check("current", [_in("max_hp", 160, 0)])

    with read_service._check_lock:  # 前一個驗證還在跑
        first = threading.Thread(target=run, args=("first",))
        first.start()
        _wait_for(lambda: read_service._generation >= start + 1)
        second = threading.Thread(target=run, args=("second",))
        second.start()
        _wait_for(lambda: read_service._generation >= start + 2)
    first.join(30)
    second.join(30)
    assert results["first"].superseded and not results["first"].ok
    assert not results["second"].superseded
    assert results["second"].field_errors[0].message_zh == "不能小於 1"


def test_untouched_copy_has_the_same_digests(
    read_service: TuningService, content_library: ContentLibrary
) -> None:
    """T-A3：複本不套改動時三個 digest 和原資料夾相同；套一筆單位欄位後 ``content_digest`` 與
    ``ruleset_hash`` 變、``hash_ruleset`` 不變（單位範本不在規則包裡）。"""
    base = read_service.workspace.draft({})
    copy = load_library(base)
    assert ruleset_hash(copy) == ruleset_hash(content_library)
    assert content_digest(copy) == content_digest(content_library)
    assert hash_ruleset(copy.ruleset) == hash_ruleset(content_library.ruleset)

    prepared = prepare(
        read_service.content_dir,
        read_service.table,
        [Change(file=HEART, path="max_hp", old=160, new=150)],
    )
    changed = load_library(read_service.workspace.draft(prepared.texts))
    assert changed.unit("ashen_heart").max_hp == 150
    assert content_library.unit("ashen_heart").max_hp == 160
    assert content_digest(changed) != content_digest(content_library)
    assert ruleset_hash(changed) != ruleset_hash(content_library)
    assert hash_ruleset(changed.ruleset) == hash_ruleset(content_library.ruleset)
    assert (base / HEART).read_text(encoding="utf-8") == (bundled_content_dir() / HEART).read_text(
        encoding="utf-8"
    )  # 草稿複本是硬連結：改的檔先斷開，基底不受影響


def test_diff_text_only_has_the_changed_lines(read_service: TuningService) -> None:
    prepared = prepare(
        read_service.content_dir,
        read_service.table,
        [
            Change(file=HEART, path="max_hp", old=160, new=150),
            Change(file=HEART, path="phases[1].trigger.permille", old=600, new=550),
        ],
    )
    text = diff_text(prepared)
    assert "--- a/content/units/ashen_heart.yaml" in text
    assert "-max_hp: 160\n+max_hp: 150\n" in text
    assert "-    trigger: {kind: hp_below, permille: 600}\n" in text
    assert "+    trigger: {kind: hp_below, permille: 550}\n" in text
    body = [
        line for line in text.splitlines() if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]
    assert len(body) == 4
