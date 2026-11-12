"""行為一致：Q 版圖示推導表只影響圖示（Phase QI-2a，T-A9；06 6.36）。

推導表 ``content/skill_icon_art.yaml`` 換成空表重新載入整份內容：規則包（戰鬥紀錄雜湊
``hash_ruleset``）不變；同一張地圖、同一組種子，兩份內容庫的規則包對戰的步驟、事件、最終狀態逐筆
相同。另外確認一輪存檔與世界日誌的內容雜湊（``ruleset_hash``、``content_digest``）**會**因表改變——
這是預期（新內容檔進 ``library.files``；報告寫明，使用者重開伺服器後進行中的一輪從頭開始）。
"""

from __future__ import annotations

import shutil

import pytest

from tests.content.test_icon_prop_battle_ip1 import SEEDS, _run, _setup
from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.library import ContentLibrary, load_library
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.roguelite.save import ruleset_hash
from trpg.world.save import content_digest

CONTENT = PROJECT_ROOT / "content"
# icon_prop 改了出手的招與一般招各取幾招（沿用 IP-1 的單位配法）
SKILLS = ("skill_ambush_stab", "skill_ember_bite", "skill_cleave", "skill_air_burst")


@pytest.fixture(scope="module")
def empty_table_library(tmp_path_factory: pytest.TempPathFactory) -> ContentLibrary:
    dest = tmp_path_factory.mktemp("qi2a_art") / "content"
    shutil.copytree(CONTENT, dest)
    (dest / "skill_icon_art.yaml").write_text("{}\n", encoding="utf-8", newline="\n")
    return load_library(dest)


def test_empty_table_keeps_the_ruleset(empty_table_library: ContentLibrary) -> None:
    lib = library()
    assert empty_table_library.icon_art is not None
    assert empty_table_library.icon_art.effect_action == ()
    assert hash_ruleset(empty_table_library.ruleset) == hash_ruleset(lib.ruleset)
    # 預期：內容檔多一份、表不同 → 一輪存檔與世界日誌的雜湊變（不影響戰鬥紀錄）
    assert ruleset_hash(empty_table_library) != ruleset_hash(lib)
    assert content_digest(empty_table_library) != content_digest(lib)


@pytest.mark.parametrize("skill_id", SKILLS)
def test_battles_are_identical_with_an_empty_table(
    empty_table_library: ContentLibrary, skill_id: str
) -> None:
    setup = _setup(library().skills[skill_id])
    other = setup.model_copy(update={"ruleset": empty_table_library.ruleset})
    for seed in SEEDS:
        a, b = _run(setup, seed), _run(other, seed)
        log_a = a.to_log().model_dump(mode="json")
        log_b = b.to_log().model_dump(mode="json")
        for key in ("actions", "events", "final_state"):
            assert log_a[key] == log_b[key], (skill_id, seed, key)
