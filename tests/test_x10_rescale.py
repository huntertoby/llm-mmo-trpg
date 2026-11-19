"""``scripts/x10/rescale.py``（X10-1）：照欄位清單改寫 YAML。

都在 ``tmp_path`` 的小內容上跑，不碰 ``content/``；真內容只跑 dry-run（不寫檔）。
"""

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "x10" / "rescale.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("x10_rescale_apply", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["x10_rescale_apply"] = module
    spec.loader.exec_module(module)
    return module


rs = _load()

_FIELDS = """\
groups:
  - files: units/*.yaml
    scale:
      - max_hp
      - attributes.*
      - effects[type=damage].flat
    keep:
      - speed
      - effects[type=heal].flat
  - files: rules.yaml
    scale:
      - base
    keep:
      - shared_keep
"""

_UNIT = (
    "# 敵人：註解要保留\r\n"
    "id: grunt\r\n"
    "max_hp: 18   # 行尾註解\r\n"
    "speed: 5\r\n"
    "attributes: {str: 12, dex: -3}\r\n"
    "effects:\r\n"
    "  - {type: damage, flat: 2}\r\n"
    "  - {type: heal, flat: 2}\r\n"
)

_RULES = "﻿base: &b 10\nshared_keep: 4\nname_zh: 規則\n"


def _setup(tmp_path: Path) -> tuple[Path, list[Any]]:
    content = tmp_path / "content"
    (content / "units").mkdir(parents=True)
    (content / "units" / "grunt.yaml").write_bytes(_UNIT.encode("utf-8"))
    (content / "rules.yaml").write_bytes(_RULES.encode("utf-8"))
    fields = tmp_path / "fields.yaml"
    fields.write_text(_FIELDS, encoding="utf-8")
    return content, rs.load_fields(fields)


def _plan(tmp_path: Path) -> tuple[Path, list[Any]]:
    content, groups = _setup(tmp_path)
    return content, rs.plan(rs.classify(groups, content))


def test_plan_lists_only_scale_fields(tmp_path: Path) -> None:
    _content, changes = _plan(tmp_path)
    rows = [(c.file, c.path, c.old, c.new) for c in changes]
    assert rows == [
        ("rules.yaml", "base", "10", "100"),
        ("units/grunt.yaml", "max_hp", "18", "180"),
        ("units/grunt.yaml", "attributes.str", "12", "120"),
        ("units/grunt.yaml", "attributes.dex", "-3", "-30"),
        ("units/grunt.yaml", "effects[0].flat", "2", "20"),
    ]


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    content, changes = _plan(tmp_path)
    texts = rs.rewrite(changes, content)
    assert set(texts) == {"rules.yaml", "units/grunt.yaml"}
    assert (content / "units" / "grunt.yaml").read_bytes() == _UNIT.encode("utf-8")


def test_apply_keeps_comments_newlines_and_bom(tmp_path: Path) -> None:
    content, changes = _plan(tmp_path)
    assert rs.apply(changes, content) == ["rules.yaml", "units/grunt.yaml"]
    unit = (content / "units" / "grunt.yaml").read_bytes().decode("utf-8")
    assert unit == (
        rs.MARKER + "\r\n"
        "# 敵人：註解要保留\r\n"
        "id: grunt\r\n"
        "max_hp: 180   # 行尾註解\r\n"
        "speed: 5\r\n"
        "attributes: {str: 120, dex: -30}\r\n"
        "effects:\r\n"
        "  - {type: damage, flat: 20}\r\n"
        "  - {type: heal, flat: 2}\r\n"
    )
    rules = (content / "rules.yaml").read_bytes().decode("utf-8")
    assert rules == "﻿" + rs.MARKER + "\nbase: &b 100\nshared_keep: 4\nname_zh: 規則\n"


def test_second_run_is_refused(tmp_path: Path) -> None:
    content, changes = _plan(tmp_path)
    rs.apply(changes, content)
    before = {p: p.read_bytes() for p in content.rglob("*.yaml")}
    groups = rs.load_fields(tmp_path / "fields.yaml")
    again = rs.plan(rs.classify(groups, content))
    with pytest.raises(rs.RescaleError, match="已經換算過"):
        rs.apply(again, content)
    assert {p: p.read_bytes() for p in content.rglob("*.yaml")} == before


def test_quoted_number_is_refused(tmp_path: Path) -> None:
    content, groups = _setup(tmp_path)
    for value in ("1.5", "0x10"):
        (content / "rules.yaml").write_text(f"base: {value}\nshared_keep: 4\n", encoding="utf-8")
        with pytest.raises(rs.RescaleError, match="十進位整數"):
            rs.plan(rs.classify(groups, content))


def test_unlisted_field_blocks_plan(tmp_path: Path) -> None:
    content, groups = _setup(tmp_path)
    (content / "rules.yaml").write_text("base: 10\nshared_keep: 4\nnew_thing: 3\n", "utf-8")
    with pytest.raises(rs.RescaleError, match="new_thing"):
        rs.plan(rs.classify(groups, content))


def test_alias_shared_with_keep_is_refused(tmp_path: Path) -> None:
    content, groups = _setup(tmp_path)
    (content / "rules.yaml").write_text("base: &b 10\nshared_keep: *b\n", encoding="utf-8")
    with pytest.raises(rs.RescaleError, match="錨點"):
        rs.plan(rs.classify(groups, content))


def test_alias_scaled_once(tmp_path: Path) -> None:
    content, groups = _setup(tmp_path)
    unit = _UNIT.replace("max_hp: 18", "max_hp: &hp 7").replace("str: 12", "str: *hp")
    (content / "units" / "grunt.yaml").write_bytes(unit.encode("utf-8"))
    changes = rs.plan(rs.classify(groups, content))
    rs.apply(changes, content)
    text = (content / "units" / "grunt.yaml").read_bytes().decode("utf-8")
    assert "max_hp: &hp 70   #" in text
    assert "attributes: {str: *hp, dex: -30}" in text


def test_csv_columns(tmp_path: Path) -> None:
    _content, changes = _plan(tmp_path)
    out = io.StringIO()
    rs.write_csv(changes, out)
    rows = list(csv.reader(io.StringIO(out.getvalue())))
    assert rows[0] == ["file", "path", "old", "new"]
    assert rows[1] == ["rules.yaml", "base", "10", "100"]


def test_real_content_dry_run() -> None:
    """真的 content/：清單完整、每一筆都能改寫、而且沒有任何一個檔已經換算過。"""
    changes = rs.plan()
    texts = rs.rewrite(changes)
    assert changes
    assert len(texts) == len({c.file for c in changes})
    assert not rs.marked_files()
