"""程式需要的骨架（WL-1 b，a 段裁定 4）：程式依 id 寫死的骨架被刪時，內容檢查用中文擋下。

清單是 :data:`trpg.content.library.skill_checks.CODE_REQUIRED_SKELETONS`；其他骨架只靠資料。"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from trpg.content.library import load_library
from trpg.content.library.skill_checks import CODE_REQUIRED_SKELETONS
from trpg.content.loader import CONTENT_DIR_ENV
from trpg.shared.errors import ContentError

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
SRC = ROOT / "src" / "trpg"


def test_every_code_required_skeleton_has_a_data_file() -> None:
    files = {p.stem for p in (CONTENT / "skeletons").glob("*.yaml")}
    assert set(CODE_REQUIRED_SKELETONS) <= files
    assert all(why for why in CODE_REQUIRED_SKELETONS.values())


def test_the_list_covers_every_hard_skeleton_lookup_in_the_code() -> None:
    """``library.skeletons["…"]`` 找不到就丟 ``KeyError``：每個寫死的 id 都要在清單裡。"""
    lookup = re.compile(r"""skeletons\[\s*["'](\w+)["']\s*\]""")
    found = {
        m.group(1)
        for path in sorted(SRC.rglob("*.py"))
        for m in lookup.finditer(path.read_text(encoding="utf-8"))
    }
    assert found  # 掃得到東西（不是空集合造成的假通過）
    assert found <= set(CODE_REQUIRED_SKELETONS), sorted(found - set(CODE_REQUIRED_SKELETONS))


def test_the_form_breath_skeleton_is_listed() -> None:
    """吐息技直接建 ``SkillDef``（骨架驗證失敗就丟例外），它的骨架也要在清單裡。"""
    text = (SRC / "content" / "form_breath.py").read_text(encoding="utf-8")
    found = set(re.findall(r"""skeleton=["'](\w+)["']""", text))
    assert found and found <= set(CODE_REQUIRED_SKELETONS)


@pytest.mark.parametrize("removed", sorted(CODE_REQUIRED_SKELETONS))
def test_removing_a_code_required_skeleton_is_blocked(
    removed: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    (root / "skeletons" / f"{removed}.yaml").unlink()
    monkeypatch.setenv(CONTENT_DIR_ENV, str(root))
    with pytest.raises(ContentError) as info:
        load_library(root)
    message = str(info.value)
    assert "缺少程式需要的骨架" in message
    assert f"{removed}（{CODE_REQUIRED_SKELETONS[removed]}）" in message
