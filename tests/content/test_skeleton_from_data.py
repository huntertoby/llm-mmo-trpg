"""骨架清單從資料讀（Phase WL-1）：加一種骨架只要在 ``content/skeletons/`` 多一個檔。

測試把正式內容複製一份，只寫資料（一個骨架檔、一個用它的手寫技能），再用 ``TRPG_CONTENT_DIR``
指過去：載入、技能驗證、隨機組合器、工坊選單都認得新骨架，不用改程式。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import CONTENT_DIR_ENV
from trpg.content.skills import SkillDef, skeleton_ids
from trpg.shared.errors import ContentError
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.validate import validate_skill

CONTENT = Path(__file__).resolve().parents[2] / "content"
NEW = "test_burst"
NEW_SKILL = "skill_test_burst"


def _write(path: Path, data: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _content_with_new_skeleton(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    skeleton = yaml.safe_load((root / "skeletons" / "strike.yaml").read_text(encoding="utf-8"))
    skeleton.update(
        id=NEW, order=999, name_zh="測試爆發", description_zh="測試用的骨架，結構同打擊。"
    )
    _write(root / "skeletons" / f"{NEW}.yaml", skeleton)
    skill = yaml.safe_load(
        (root / "skills" / "skill_armor_piercing_arrow.yaml").read_text(encoding="utf-8")
    )
    skill.update(id=NEW_SKILL, skeleton=NEW, name_zh="測試爆發箭")
    _write(root / "skills" / f"{NEW_SKILL}.yaml", skill)
    return root


@pytest.fixture
def new_library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ContentLibrary:
    root = _content_with_new_skeleton(tmp_path)
    monkeypatch.setenv(CONTENT_DIR_ENV, str(root))
    return load_library(root)


def test_the_bundled_skeleton_order_comes_from_the_data_files() -> None:
    ids = skeleton_ids()
    files = {p.stem for p in (CONTENT / "skeletons").glob("*.yaml")}
    assert set(ids) == files and len(ids) == len(files)
    assert ids[:5] == ("strike", "area", "control", "displace", "builder_finisher")


def test_a_new_skeleton_loads_and_sorts_by_order(new_library: ContentLibrary) -> None:
    assert NEW in new_library.skeletons
    assert skeleton_ids()[-1] == NEW
    assert new_library.skills[NEW_SKILL].skeleton == NEW


def test_a_skill_on_the_new_skeleton_validates(new_library: ContentLibrary) -> None:
    assert validate_skill(new_library.skills[NEW_SKILL], new_library) == []


def test_the_composer_builds_a_skill_on_the_new_skeleton(new_library: ContentLibrary) -> None:
    skill = compose_random_skill(7, skeleton=NEW, library=new_library)
    assert isinstance(skill, SkillDef) and skill.skeleton == NEW
    assert validate_skill(skill, new_library) == []


def test_the_workshop_lists_the_new_skeleton_last(new_library: ContentLibrary) -> None:
    steps = draft_options({}, new_library).steps
    values = [c.value for s in steps for f in s.fields if f.field == "skeleton" for c in f.choices]
    assert values[-1] == NEW


def test_without_the_content_dir_the_new_skeleton_is_unknown(tmp_path: Path) -> None:
    root = _content_with_new_skeleton(tmp_path)
    with pytest.raises(ContentError, match="未知的骨架 'test_burst'"):
        load_library(root)


def test_duplicate_orders_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _content_with_new_skeleton(tmp_path)
    path = root / "skeletons" / f"{NEW}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["order"] = yaml.safe_load((root / "skeletons" / "strike.yaml").read_text("utf-8"))["order"]
    _write(path, data)
    monkeypatch.setenv(CONTENT_DIR_ENV, str(root))
    with pytest.raises(ContentError, match="骨架的 order 重複：strike、test_burst"):
        load_library(root)
