"""規則包（:class:`~trpg.content.library.Ruleset`）的內容雜湊（Phase 3T-2）。

戰鬥紀錄內嵌規則包，重播前用它確認內嵌的規則包沒有被改過、也沒有因為資料結構改變而與紀錄時
不同。策略見 ``docs/phases/戰鬥紀錄格式變更.md``。這和 :func:`trpg.roguelite.save.ruleset_hash`
（內容資料夾全部檔案的雜湊）不同：這裡只看規則包本身。
"""

from __future__ import annotations

import hashlib
import json

from trpg.content.library import Ruleset

__all__ = ["hash_ruleset"]


def hash_ruleset(ruleset: Ruleset) -> str:
    """規則包的穩定 SHA-256（排序鍵、無多餘空白的 JSON；不用內建 ``hash()``）。"""
    text = json.dumps(
        ruleset.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
