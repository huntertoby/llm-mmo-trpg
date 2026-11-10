"""PERF-4 R2：C 解析器與純 Python 解析器對全部內容檔的結果相同，且一律是 safe loader。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel

from trpg.content.loader import bundled_content_dir, load_content_file, parse_yaml
from trpg.shared.errors import ContentError
from trpg.skillgen.skill_yaml import skill_from_yaml

_HAS_C_LOADER = hasattr(yaml, "CSafeLoader")


def _content_files() -> list[Path]:
    root = bundled_content_dir()
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in {".yaml", ".yml"})


@pytest.mark.skipif(not _HAS_C_LOADER, reason="沒有 libyaml")
def test_every_content_file_parses_the_same_with_both_loaders() -> None:
    files = _content_files()
    assert len(files) > 600  # 確定真的掃到內容資料夾
    different = []
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        # repr 比 == 嚴格：連鍵的順序、1／1.0／True 的差別都算
        if repr(yaml.load(text, Loader=yaml.CSafeLoader)) != repr(
            yaml.load(text, Loader=yaml.SafeLoader)
        ):
            different.append(path)
    assert different == []


@pytest.mark.skipif(not _HAS_C_LOADER, reason="沒有 libyaml")
def test_parse_yaml_uses_the_c_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    real = yaml.load

    def spy(text: str, **kwargs: Any) -> Any:
        seen.append(kwargs["Loader"])
        return real(text, **kwargs)

    monkeypatch.setattr(yaml, "load", spy)
    assert parse_yaml("a: 1") == {"a": 1}
    assert seen == [yaml.CSafeLoader]


def test_parse_yaml_falls_back_to_the_python_safe_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(yaml, "CSafeLoader", raising=False)
    assert parse_yaml("a: [1, 2]") == {"a": [1, 2]}


def test_parse_yaml_is_safe() -> None:
    with pytest.raises(yaml.constructor.ConstructorError):
        parse_yaml("!!python/object/apply:os.getcwd []")


def test_syntax_error_is_still_a_yaml_error() -> None:
    with pytest.raises(yaml.YAMLError):
        parse_yaml("a: [1, 2")


def test_load_content_file_reports_syntax_errors(tmp_path: Path) -> None:
    class _Model(BaseModel):
        a: int

    bad = tmp_path / "bad.yaml"
    bad.write_text("a: [1, 2", encoding="utf-8")
    with pytest.raises(ContentError, match="YAML 格式錯誤"):
        load_content_file(bad, _Model)


def test_skill_from_yaml_rejects_python_tags() -> None:
    with pytest.raises(yaml.YAMLError):
        skill_from_yaml("!!python/object/apply:os.getcwd []")
