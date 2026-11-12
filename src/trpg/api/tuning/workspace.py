"""草稿內容庫的資料夾（NW-1a A4，規格 5.1）。

- 基底：把 ``content/`` 複製到 ``<save_dir>/tuning/work/<樹雜湊>/base/content/``（同一份內容只
  複製一次）。樹雜湊＝``content/`` 下全部檔案的相對路徑與位元組（:func:`tree_digest`；比內容
  digest 更嚴：連註解改了也算不同，而且不必先載入內容庫）。
- 草稿：``work/<樹雜湊>/d-<改動雜湊>/content/``，從基底以硬連結建出（不能硬連結時改複製），改到的檔
  先刪掉再寫（不會改到基底）；同一份改動只建一次。最多留 :data:`KEEP_DRAFT_DIRS` 份，舊的刪掉。

複本只放在存檔資料夾下，不在 ``content/``、不進 git；不是存檔（0.0：格式可隨段改）。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Final

__all__ = ["KEEP_DRAFT_DIRS", "KEEP_TREES", "Workspace", "tree_digest"]

KEEP_DRAFT_DIRS: Final = 8
KEEP_TREES: Final = 4
_READY: Final = ".ready"


def tree_digest(content_dir: Path) -> str:
    """``content_dir`` 下全部檔案（依相對路徑排序）的 SHA-256。"""
    digest = hashlib.sha256()
    for path in sorted(p for p in content_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(content_dir).as_posix()
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _link_or_copy(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


class Workspace:
    """``<save_dir>/tuning/work/`` 下的內容複本。"""

    def __init__(self, content_dir: Path, root: Path) -> None:
        self.content_dir = content_dir
        self.root = root

    def base(self, digest: str | None = None) -> tuple[str, Path]:
        """目前 ``content/`` 的基底複本：``(樹雜湊, 複本的 content 資料夾)``。"""
        digest = digest or tree_digest(self.content_dir)
        folder = self.root / digest[:16] / "base"
        content = folder / "content"
        if not (folder / _READY).is_file():
            shutil.rmtree(folder, ignore_errors=True)
            shutil.copytree(self.content_dir, content)
            (folder / _READY).write_text(digest, encoding="utf-8")
            self._prune_trees()
        else:
            os.utime(folder / _READY)
        return digest, content

    def _prune_trees(self) -> None:
        """舊內容的複本（寫回後內容變了）最多留 :data:`KEEP_TREES` 份。"""
        trees = sorted(
            (p for p in self.root.glob("*/base") if (p / _READY).is_file()),
            key=lambda p: (p / _READY).stat().st_mtime_ns,
        )
        for old in trees[:-KEEP_TREES]:
            shutil.rmtree(old.parent, ignore_errors=True)

    def draft(self, texts: Mapping[str, str], digest: str | None = None) -> Path:
        """基底套上 ``texts``（相對路徑 → 改後全文）的複本；``texts`` 空時就是基底。"""
        digest, base = self.base(digest)
        if not texts:
            return base
        key = hashlib.sha256(
            json.dumps(sorted(texts.items()), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        folder = self.root / digest[:16] / f"d-{key[:16]}"
        content = folder / "content"
        if not (folder / _READY).is_file():
            shutil.rmtree(folder, ignore_errors=True)
            shutil.copytree(base, content, copy_function=_link_or_copy)
            for rel, text in texts.items():
                target = content / rel
                target.unlink()  # 硬連結：先斷開，才不會改到基底
                target.write_bytes(text.encode("utf-8"))
            (folder / _READY).write_text(key, encoding="utf-8")
        else:
            os.utime(folder / _READY)
        self._prune()
        return content

    def _prune(self) -> None:
        drafts = sorted(
            (p for p in self.root.glob("*/d-*") if (p / _READY).is_file()),
            key=lambda p: (p / _READY).stat().st_mtime_ns,
        )
        for old in drafts[:-KEEP_DRAFT_DIRS]:
            shutil.rmtree(old, ignore_errors=True)
