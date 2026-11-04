"""音效參數表（Phase AU-2）：``content/audio/sfx.yaml`` 的 schema、登記與錯誤範例。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT
from trpg.content.audio import LAYER_KINDS, SfxTable
from trpg.content.loader import load_content_file
from trpg.content.registry import KNOWN_CONTENT_FILES
from trpg.shared.errors import ContentError

SFX_FILE = PROJECT_ROOT / "content" / "audio" / "sfx.yaml"


def _table(**layer: Any) -> dict[str, Any]:
    return {"sfx": {"x": {"zh": "測試", "cat": "ui", "layers": [layer]}}}


def test_the_table_loads() -> None:
    table = load_content_file(SFX_FILE, SfxTable)
    ui = [i for i, d in table.sfx.items() if d.cat == "ui"]
    assert len(ui) == 20
    assert len(table.sfx) >= 70
    assert "介面音 20 個" in table.summary()


def test_every_block_is_used() -> None:
    table = load_content_file(SFX_FILE, SfxTable)
    used = {
        next(k for k in LAYER_KINDS if getattr(layer, k, None) is not None)
        for d in table.sfx.values()
        for layer in d.layers
    }
    assert used == set(LAYER_KINDS)


def test_harsh_accents_are_marked() -> None:
    table = load_content_file(SFX_FILE, SfxTable).sfx
    assert table["amb_thunder"].harsh
    assert table["amb_thunder"].track == "ambient"
    assert table["explosion"].harsh
    assert not table["ui_tap"].harsh


def test_registered_for_content_check() -> None:
    assert any(
        f.relative_path == "audio/sfx.yaml" and f.model is SfxTable for f in KNOWN_CONTENT_FILES
    )


@pytest.mark.parametrize(
    "layer",
    [
        {"tone": "sine", "noise": "band", "freq": 440, "dur": 0.1},  # 兩個種類鍵
        {"freq": 440, "dur": 0.1},  # 沒有種類鍵
        {"tone": "sine", "freq": 440},  # 缺 dur
        {"tone": "buzz", "freq": 440, "dur": 0.1},  # 未知波形
        {"tone": "sine", "freq": 30000, "dur": 0.1},  # 頻率超出可聽範圍
        {"tone": "sine", "freq": [440, 5], "dur": 0.1},  # 掃頻終點太低
        {"noise": "band", "dur": 0.1},  # 帶通雜訊沒有 freq
        {"fm": "bell", "freq": 440, "dur": 0.1},  # 缺 ratio、index
        {"pulses": 3, "click": 0.01},  # 缺 every
        {"chord": [], "dur": 0.5},  # 空和弦
        {"tone": "sine", "freq": 440, "dur": 0.1, "env": [0.01]},  # 包絡只有一個數
        {"tone": "sine", "freq": 440, "dur": 20},  # 太長
        {"tone": "sine", "freq": 440, "dur": 0.1, "volume": 3},  # 拼錯欄位
    ],
)
def test_bad_layers_are_rejected(layer: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SfxTable.model_validate(_table(**layer))


def test_bad_entries_are_rejected() -> None:
    ok = {"tone": "sine", "freq": 440, "dur": 0.1}
    with pytest.raises(ValidationError):
        SfxTable.model_validate({"sfx": {"Bad-Id": {"zh": "x", "cat": "ui", "layers": [ok]}}})
    with pytest.raises(ValidationError):
        SfxTable.model_validate({"sfx": {"x": {"zh": "x", "cat": "music", "layers": [ok]}}})
    with pytest.raises(ValidationError):
        SfxTable.model_validate({"sfx": {"x": {"zh": "x", "cat": "ui", "layers": []}}})
    with pytest.raises(ValidationError):
        SfxTable.model_validate(
            {"sfx": {"x": {"zh": "x", "cat": "ui", "harsh": "yes", "layers": [ok]}}}
        )
    with pytest.raises(ValidationError, match="ambient 軌"):
        SfxTable.model_validate(
            {
                "sfx": {
                    "x": {"zh": "x", "cat": "ui", "layers": [ok]},
                    "y": {"zh": "y", "cat": "ambient", "layers": [ok]},
                }
            }
        )
    with pytest.raises(ValidationError, match="種類鍵"):
        SfxTable.model_validate(_table(freq=440, dur=0.1))


def test_bad_file_gives_content_error(tmp_path: Path) -> None:
    path = tmp_path / "sfx.yaml"
    path.write_text(
        "sfx:\n  x: {zh: 測試, cat: ui, layers: [{tone: sine, freq: 440}]}\n", encoding="utf-8"
    )
    with pytest.raises(ContentError, match="dur"):
        load_content_file(path, SfxTable)
