"""trpg.content.loader 與 schemas 的測試。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel

from trpg.content.loader import CONTENT_DIR_ENV, default_content_dir, load_content_file
from trpg.content.registry import KNOWN_CONTENT_FILES, load_all_content
from trpg.content.schemas import ElementEntry, ElementTable
from trpg.shared.errors import ContentError
from trpg.shared.types import Element

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ELEMENTS_FILE = PROJECT_ROOT / "content" / "elements.yaml"


def _valid_elements() -> list[dict[str, str]]:
    return [
        {
            "id": e.value,
            "name_zh": e.display_name,
            "description_zh": "說明",
            "resist_group": e.resist_group.value,
        }
        for e in Element
    ]


def _write_yaml(path: Path, data: object) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 實際資料檔
# ---------------------------------------------------------------------------


def test_default_content_dir_points_to_project_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CONTENT_DIR_ENV, raising=False)
    assert default_content_dir() == PROJECT_ROOT / "content"


def test_default_content_dir_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(CONTENT_DIR_ENV, str(tmp_path))
    assert default_content_dir() == tmp_path


def test_elements_yaml_loads() -> None:
    table = load_content_file(ELEMENTS_FILE, ElementTable)
    assert sorted(entry.id.value for entry in table.elements) == sorted(e.value for e in Element)
    assert table.by_id(Element.FIRE).name_zh == "火焰"
    assert all(entry.name_zh and entry.description_zh for entry in table.elements)
    assert table.summary() == "9 種元素"


def test_elements_names_match_enum_display_names() -> None:
    table = load_content_file(ELEMENTS_FILE, ElementTable)
    for entry in table.elements:
        assert entry.name_zh == entry.id.display_name


def test_load_all_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CONTENT_DIR_ENV, raising=False)
    loaded = load_all_content()
    assert [p.name for p, _ in loaded] == [Path(f.relative_path).name for f in KNOWN_CONTENT_FILES]


def test_content_models_are_frozen() -> None:
    table = load_content_file(ELEMENTS_FILE, ElementTable)
    with pytest.raises(ValueError):
        table.elements[0].name_zh = "改名"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 錯誤情境：一律拋出 ContentError 且訊息含路徑
# ---------------------------------------------------------------------------


def _assert_content_error(path: Path, model: type[BaseModel], *fragments: str) -> ContentError:
    with pytest.raises(ContentError) as info:
        load_content_file(path, model)
    message = str(info.value)
    assert str(path) in message
    assert info.value.path == path
    for fragment in fragments:
        assert fragment in message, message
    return info.value


def test_broken_yaml(tmp_path: Path) -> None:
    path = tmp_path / "elements.yaml"
    path.write_text("elements:\n  - id: fire\n    name_zh: [未閉合\n", encoding="utf-8")
    _assert_content_error(path, ElementTable, "YAML")


def test_broken_json(tmp_path: Path) -> None:
    path = tmp_path / "elements.json"
    path.write_text('{"elements": [', encoding="utf-8")
    _assert_content_error(path, ElementTable, "JSON")


def test_extra_field(tmp_path: Path) -> None:
    rows = _valid_elements()
    rows[0]["nmae_zh"] = "拼錯"
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "nmae_zh")


def test_extra_top_level_field(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": _valid_elements(), "extra": 1})
    _assert_content_error(path, ElementTable, "extra")


def test_missing_element(tmp_path: Path) -> None:
    rows = [r for r in _valid_elements() if r["id"] != "shadow"]
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "缺少元素", "shadow")


def test_duplicate_element(tmp_path: Path) -> None:
    dup = {"id": "fire", "name_zh": "火", "description_zh": "重複", "resist_group": "elemental"}
    rows = [*_valid_elements(), dup]
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "重複的元素", "fire")


def test_unknown_element(tmp_path: Path) -> None:
    bad = {"id": "water", "name_zh": "水", "description_zh": "未知", "resist_group": "nature"}
    rows = [*_valid_elements(), bad]
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "elements.9.id")


def test_wrong_resist_group(tmp_path: Path) -> None:
    rows = _valid_elements()
    rows[1]["resist_group"] = "nature"  # fire 應為 elemental
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "resist_group", "elemental")


def test_missing_resist_group(tmp_path: Path) -> None:
    rows = _valid_elements()
    del rows[0]["resist_group"]
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "resist_group")


def test_missing_field(tmp_path: Path) -> None:
    rows = _valid_elements()
    del rows[2]["description_zh"]
    path = _write_yaml(tmp_path / "elements.yaml", {"elements": rows})
    _assert_content_error(path, ElementTable, "description_zh")


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "elements.yaml"
    path.write_text("", encoding="utf-8")
    _assert_content_error(path, ElementTable)


def test_missing_file(tmp_path: Path) -> None:
    _assert_content_error(tmp_path / "nope.yaml", ElementTable, "找不到檔案")


def test_unsupported_suffix(tmp_path: Path) -> None:
    path = tmp_path / "elements.toml"
    path.write_text("x = 1", encoding="utf-8")
    _assert_content_error(path, ElementTable, "副檔名")


def test_not_utf8(tmp_path: Path) -> None:
    path = tmp_path / "elements.yaml"
    path.write_bytes("elements: 火焰".encode("big5"))
    _assert_content_error(path, ElementTable, "UTF-8")


# ---------------------------------------------------------------------------
# 其他格式
# ---------------------------------------------------------------------------


def test_json_and_yml_suffixes(tmp_path: Path) -> None:
    data = {"elements": _valid_elements()}
    json_path = tmp_path / "elements.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    yml_path = _write_yaml(tmp_path / "elements.yml", data)
    assert load_content_file(json_path, ElementTable) == load_content_file(yml_path, ElementTable)


def test_utf8_bom_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "elements.yaml"
    text = yaml.safe_dump({"elements": _valid_elements()}, allow_unicode=True)
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    assert len(load_content_file(path, ElementTable).elements) == len(Element)


def test_element_entry_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        ElementEntry.model_validate(
            {"id": "fire", "name_zh": "", "description_zh": "x", "resist_group": "elemental"}
        )
