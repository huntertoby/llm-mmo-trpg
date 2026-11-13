"""RG-4 持盾弟子的雲紋碑盾：敵人專用形制 ``sect_great``（``FormDef.enemy_only``）
與 ``DollGear.emblem``。

美術 PM 決定（docs/art/RG樣張.md 9.6 第 2 條、9.8 第 2 條）：大盾先只給敵人——
玩家的裝備生成、前端外觀清單都略過，物品寫了算錯誤；``emblem`` 只認 ``peak``，
沒寫時不輸出（既有 JSON 不變）。
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.appearance import (
    AppearanceTable,
    FormDef,
    appearance_export,
    item_appearance_problems,
)
from trpg.content.battle import DollGear
from trpg.content.equipment import ItemDef
from trpg.content.item_gen import _look_base
from trpg.engine.battle import start_battle
from trpg.engine.setup import build_setup
from trpg.engine.view import project_for
from trpg.shared.rng import Rng
from trpg.shared.types import Team


def _table() -> AppearanceTable:
    table = library().appearance
    assert table is not None
    return table


def test_sect_great_is_an_enemy_only_kite_shield_form() -> None:
    kite = _table().kind_by_id()["kite_shield"]
    forms = {f.id: f for f in kite.forms}
    assert forms["sect_great"].enemy_only
    assert [f.id for f in kite.player_forms()] == ["kite", "tower"]
    # 其他造型都沒有 enemy_only：玩家形制清單和改前逐項相同
    for kind in _table().kinds:
        if kind.id != "kite_shield":
            assert kind.player_forms() == kind.forms, kind.id


def test_enemy_only_default_is_not_dumped() -> None:
    assert "enemy_only" not in FormDef(id="kite", name_zh="鳶盾").model_dump()
    assert FormDef(id="x", name_zh="x", enemy_only=True).model_dump()["enemy_only"] is True


def test_client_list_skips_enemy_only_forms() -> None:
    exported = appearance_export(_table(), library().keywords)
    kinds = {k["id"]: k for k in exported["kinds"]}  # type: ignore[attr-defined]
    assert [f["id"] for f in kinds["kite_shield"]["forms"]] == ["kite", "tower"]
    assert "sect_great" not in json.dumps(exported)


def test_item_with_enemy_only_form_is_reported() -> None:
    item = ItemDef.model_validate(
        {
            "id": "item_x",
            "name_zh": "測試",
            "slot_type": "offhand",
            "kind": "kite_shield",
            "form": "sect_great",
        }
    )
    problems = item_appearance_problems(item, _table())
    assert any("只給敵人" in p for p in problems), problems


def test_kind_needs_a_player_form() -> None:
    raw: dict[str, Any] = json.loads(json.dumps(_table().model_dump(mode="json")))
    kite = next(k for k in raw["kinds"] if k["id"] == "kite_shield")
    for form in kite["forms"]:
        form["enemy_only"] = True
    with pytest.raises(ValidationError, match="enemy_only"):
        AppearanceTable.model_validate(raw)


def _with_enemy_form_everywhere() -> AppearanceTable:
    """每個造型最後都多一個 enemy_only 形制。"""
    raw: dict[str, Any] = json.loads(json.dumps(_table().model_dump(mode="json")))
    for kind in raw["kinds"]:
        kind["forms"].append({"id": "enemy_test", "name_zh": "敵人專用", "enemy_only": True})
    return AppearanceTable.model_validate(raw)


@pytest.mark.parametrize("slot_type", ["head", "body", "hands"])
def test_item_gen_never_picks_enemy_only_and_keeps_the_same_draws(slot_type: str) -> None:
    lib = library()
    patched = dataclasses.replace(lib, appearance=_with_enemy_form_everywhere())
    for seed in range(200):
        before = _look_base(lib, Rng(seed), slot_type)  # type: ignore[arg-type]
        after = _look_base(patched, Rng(seed), slot_type)  # type: ignore[arg-type]
        assert after.form != "enemy_test"
        assert (after.kind, after.form, after.material) == (
            before.kind,
            before.form,
            before.material,
        )


def test_doll_gear_emblem() -> None:
    plain = DollGear(kind="shield_kite", material="wood")
    assert "emblem" not in plain.model_dump()
    assert "emblem" not in plain.model_dump(mode="json")
    shield = DollGear.model_validate({"kind": "shield_kite", "material": "wood", "emblem": "peak"})
    assert shield.model_dump()["emblem"] == "peak"
    with pytest.raises(ValidationError):
        DollGear.model_validate({"kind": "shield_kite", "material": "wood", "emblem": "taiji"})


def test_sect_shield_disciple_carries_the_great_shield_to_the_view() -> None:
    lib = library()
    doll = lib.units["sect_shield_disciple"].doll
    assert doll is not None
    off = doll.gear["off_hand"]
    assert (off.kind, off.form, off.color, off.trim, off.emblem) == (
        "shield_kite",
        "sect_great",
        "#5f8f8a",
        "#dfe4e2",
        "peak",
    )
    state = start_battle(
        build_setup(lib, "test_flat_6x6", ["gear_tester"], ["sect_shield_disciple"]), 1
    )
    view = project_for(state, Team.ENEMY)
    unit = next(u for u in view.units if u.template_id == "sect_shield_disciple")
    assert unit.doll_look is not None
    dumped = unit.model_dump(mode="json")["doll_look"]["gear"]
    assert dumped["off_hand"]["emblem"] == "peak"
    assert "emblem" not in dumped["body"]
