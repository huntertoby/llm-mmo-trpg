"""NW-3b：數值工坊小項。

- 造牆物件的 HP 提示（玩法 PM 交接 4.1.14）：物件表單上，``create_obstacle`` 會放出的物件的
  「最大 HP」欄位多一行提示（逐字）；其他物件沒有。物件 HP 不進技能預算（不改）。
- ``prefer_far_from_leader`` 下限（NW-3 待決 5）：``AiWeights`` 加 ``ge=0``；工坊表單顯示允許
  下限 0、驗證擋負值；現有內容的值照樣過。
- 單位表單的遭遇護甲提示改字（NW-3 待決 6）：不再寫「NW-3 才開」。

數值一律讀 ``content/`` 的現值（使用者寫回後不必收編）；只寫死欄位路徑、物件與模式 ID。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from trpg.api.tuning.objects import (
    OBSTACLE_NOTICE_ZH,
    object_detail,
    obstacle_objects,
    read_data,
)
from trpg.api.tuning.schemas import TuningChangeIn
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.yaml_patch import MISSING, lookup
from trpg.content.environment import AiWeights
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir
from trpg.content.tuning_fields import parse_path

CONTENT = bundled_content_dir()
AI = "ai_profiles.yaml"
OBJECTS = "objects.yaml"
WALLS_ZH = "造牆技能會放出這個物件。改 HP 會讓那些技能變強或變弱，技能預算不會跟著算。"
"""玩法 PM 交接 4.1.14 的提示字（逐字；測試另寫一份，避免常數被改了測試照樣過）。"""


def _index(file: str, key: str, item_id: str) -> int:
    items = read_data(CONTENT / file)[key]
    return next(i for i, item in enumerate(items) if item["id"] == item_id)


BROOD_FAR = f"profiles[{_index(AI, 'profiles', 'ember_brood')}].weights.prefer_far_from_leader"


def _now(file: str, path: str) -> Any:
    found = lookup(read_data(CONTENT / file), parse_path(path))
    return None if found is MISSING else found


def _raw_obstacle_objects() -> set[str]:
    """直接掃技能檔的原始 YAML：任何層級裡 ``type: create_obstacle`` 的 ``object``。"""

    def walk(node: Any) -> list[str]:
        if isinstance(node, dict):
            found = [str(node["object"])] if node.get("type") == "create_obstacle" else []
            return found + [o for value in node.values() for o in walk(value)]
        if isinstance(node, list):
            return [o for item in node for o in walk(item)]
        return []

    files = sorted((CONTENT / "skills").glob("*.yaml"))
    return {o for path in files for o in walk(read_data(path))}


@pytest.fixture
def read_service(tmp_path: Path, content_library: ContentLibrary) -> TuningService:
    """讀專案內建 ``content/`` 的服務（**不寫回**）。"""
    service = TuningService(bundled_content_dir(), tmp_path / "saves", content_library)
    service.git = None
    return service


# ---------------------------------------------------------------------------
# 造牆物件的 HP 提示（4.1.14）
# ---------------------------------------------------------------------------


def test_the_notice_text_is_verbatim() -> None:
    assert OBSTACLE_NOTICE_ZH == WALLS_ZH


def test_obstacle_objects_come_from_the_skill_files(read_service: TuningService) -> None:
    walls = obstacle_objects(CONTENT, read_service.table, read_service.library)
    assert walls == _raw_obstacle_objects()
    assert {"earth_wall", "ice_wall", "thorn_wall"} <= walls  # 土牆、冰牆、荊棘叢（4.1.14）
    assert "cooling_well" not in walls
    assert obstacle_objects(CONTENT, read_service.table, None) == frozenset()


def test_only_wall_objects_show_the_notice(read_service: TuningService) -> None:
    walls = obstacle_objects(CONTENT, read_service.table, read_service.library)
    data = read_data(CONTENT / OBJECTS)
    detail = read_service.object("object", "objects")
    shown = {f.path: f.notice_zh for f in detail.fields}
    want = {
        f"objects[{i}].max_hp": WALLS_ZH if o["id"] in walls else None
        for i, o in enumerate(data["objects"])
        if o.get("max_hp") is not None
    }
    assert shown == want
    assert sum(v is not None for v in shown.values()) >= 3
    # 欄位說明（?）照舊，提示是另一行
    assert all(f.note_zh and f.note_zh != WALLS_ZH for f in detail.fields)


def test_other_forms_have_no_notice(read_service: TuningService) -> None:
    for kind, object_id in (("ai", "ai_profiles"), ("unit", "ashen_heart")):
        detail = object_detail(CONTENT, read_service.table, kind, object_id, read_service.library)
        assert all(f.notice_zh is None for f in detail.fields)


# ---------------------------------------------------------------------------
# prefer_far_from_leader 下限（NW-3 待決 5）
# ---------------------------------------------------------------------------


def test_schema_refuses_a_negative_weight() -> None:
    assert AiWeights(prefer_far_from_leader=0).prefer_far_from_leader == 0
    with pytest.raises(ValidationError):
        AiWeights(prefer_far_from_leader=-1)


def test_existing_weights_still_load(content_library: ContentLibrary) -> None:
    brood = content_library.ai_profiles.by_id()["ember_brood"]
    assert brood.weights.prefer_far_from_leader == _now(AI, BROOD_FAR) >= 0


def test_form_shows_the_lower_limit(read_service: TuningService) -> None:
    detail = read_service.object("ai", "ai_profiles")
    far = next(f for f in detail.fields if f.path == BROOD_FAR)
    assert (far.limit_min, far.limit_max) == (0, None)


@pytest.mark.parametrize(("new", "ok"), [(-1, False), (0, True)], ids=["negative", "zero"])
def test_check_refuses_a_negative_weight(
    read_service: TuningService, new: int, *, ok: bool
) -> None:
    change = TuningChangeIn(file=AI, path=BROOD_FAR, old=_now(AI, BROOD_FAR), new=new)
    result = read_service.check("current", [change])
    assert result.ok is ok
    if not ok:
        assert [(e.file, e.path) for e in result.field_errors] == [(AI, BROOD_FAR)]
        assert "不能小於 0" in result.field_errors[0].message_zh


# ---------------------------------------------------------------------------
# 遭遇護甲提示改字（NW-3 待決 6）
# ---------------------------------------------------------------------------


def test_armor_note_says_encounter_mods_are_not_open(read_service: TuningService) -> None:
    detail = read_service.object("unit", "ashen_heart")
    armor = [n for n in detail.notes_zh if n.startswith("實戰時另有遭遇護甲調整")]
    assert armor
    assert all(n.endswith("數值工坊還沒開放遭遇的護甲調整）") for n in armor)
    assert not any("NW-3" in n for n in detail.notes_zh)
