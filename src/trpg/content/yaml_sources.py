"""schema 在匯入時就需要的清單，直接讀 ``content/`` 的 YAML（Phase 3E-2f，唯一來源）。

形狀的用途清單（``skill_shapes.yaml`` 的 ``shape_roles``）、聖光雙效可用的骨架
（``skill_primitives.yaml`` 的 ``damage.params.split_heal.allowed_skeletons``）、原語固定施加的
狀態 ID（``status``）與技能機制使用的狀態（``mechanic_statuses``）。

這些清單是 :mod:`trpg.content.skills` 的模組常數，而 schema 驗證當下還沒有載入完整的規則包，所以
這裡只做最小的原始讀取（固定讀專案內建的 ``content/``，不受 ``TRPG_CONTENT_DIR`` 影響；
:func:`skeleton_ids` 例外，見該函式）。完整的
形狀、原語表驗證仍由 ``ShapeTable``、``PrimitiveTable`` 與 :class:`~trpg.content.library.Ruleset`
負責（用途清單的形狀存在、狀態 ID 存在等）。
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

from trpg.content.loader import (
    CONTENT_DIR_ENV,
    bundled_content_dir,
    default_content_dir,
    parse_yaml,
)
from trpg.shared.errors import ContentError

__all__ = [
    "mechanic_status",
    "primitive_status",
    "shape_role",
    "skeleton_ids",
    "split_heal_skeletons",
]


@cache
def _raw(name: str) -> dict[str, Any]:
    path: Path = bundled_content_dir() / name
    try:
        data = parse_yaml(path.read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError) as exc:
        raise ContentError(path, f"無法讀取：{exc}") from exc
    if not isinstance(data, dict):
        raise ContentError(path, "頂層必須是對應表")
    return cast("dict[str, Any]", data)


def _missing(name: str, what: str) -> ContentError:
    return ContentError(bundled_content_dir() / name, f"缺少 {what}")


def shape_role(role: str) -> tuple[str, ...]:
    """``skill_shapes.yaml`` 的 ``shape_roles.<role>``（形狀 ID，依檔案順序）。"""
    roles = _raw("skill_shapes.yaml").get("shape_roles") or {}
    ids = roles.get(role)
    if not ids:
        raise _missing("skill_shapes.yaml", f"shape_roles.{role}")
    return tuple(str(i) for i in ids)


def _primitive(primitive_id: str) -> dict[str, Any]:
    for entry in _raw("skill_primitives.yaml").get("primitives") or ():
        if entry.get("id") == primitive_id:
            return cast("dict[str, Any]", entry)
    raise _missing("skill_primitives.yaml", f"原語 {primitive_id}")


def primitive_status(primitive_id: str) -> str:
    """原語固定施加的狀態 ID（原語的 ``status`` 欄位）。"""
    status = _primitive(primitive_id).get("status")
    if not status:
        raise _missing("skill_primitives.yaml", f"原語 {primitive_id} 的 status")
    return str(status)


def mechanic_status(name: str) -> str:
    """技能機制使用的狀態 ID（``mechanic_statuses.<name>``）。"""
    status = (_raw("skill_primitives.yaml").get("mechanic_statuses") or {}).get(name)
    if not status:
        raise _missing("skill_primitives.yaml", f"mechanic_statuses.{name}")
    return str(status)


def split_heal_skeletons() -> tuple[str, ...]:
    """``split_heal``（聖光雙效）可以使用的骨架 ID。"""
    params = _primitive("damage").get("params") or {}
    skeletons = (params.get("split_heal") or {}).get("allowed_skeletons")
    if not skeletons:
        raise _missing("skill_primitives.yaml", "damage.params.split_heal.allowed_skeletons")
    return tuple(str(s) for s in skeletons)


def skeleton_ids() -> tuple[str, ...]:
    """目前內容資料夾的骨架 ID（Phase WL-1：``skeletons/`` 資料夾的檔案就是骨架清單）。

    依各檔的 ``order`` 由小到大（同值依 ID）。和本模組其他清單不同，這份跟著
    :func:`~trpg.content.loader.default_content_dir`（``TRPG_CONTENT_DIR``）走，就像
    ``EffectSpec`` 的範圍表：加一種骨架只要在內容資料夾多一個檔，schema 驗證就認得。
    每個資料夾只讀一次。``order`` 重複、缺少等錯誤由載入器（:class:`SkeletonDef`、
    ``_check_skill_rules``）回報，這裡只做最小的讀取。"""
    return _skeleton_ids_of(os.environ.get(CONTENT_DIR_ENV) or "")


@cache
def _skeleton_ids_of(override: str) -> tuple[str, ...]:
    """``override`` 是 ``TRPG_CONTENT_DIR`` 的值（只當快取鍵；位置照 ``default_content_dir``）。"""
    directory = default_content_dir() / "skeletons"
    if not directory.is_dir():  # 沒有骨架資料夾的內容由載入器自己報錯
        return ()
    keyed: list[tuple[int, str]] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = parse_yaml(path.read_text(encoding="utf-8-sig"))
        except (OSError, yaml.YAMLError) as exc:
            raise ContentError(path, f"無法讀取：{exc}") from exc
        order = data.get("order") if isinstance(data, dict) else None
        keyed.append((order if isinstance(order, int) else 0, path.stem))
    return tuple(stem for _, stem in sorted(keyed))
