"""RG-4 持盾弟子的雲紋碑盾（``kite_shield`` 的 ``sect_great``）與 ``DollGear.emblem``；
RG-5 起兩種大盾開放給玩家。

- RG-4（美術 PM 9.6 決定 2）：大盾先只給敵人（``FormDef.enemy_only``）。
- RG-5（#163，08 8.11；RG樣張 10.8 決定 1、P-3）：``sect_great``（雲紋碑盾）與新形制
  ``molten_shell``（熔殼塔盾）開放給玩家，只配 ``offhand: tower_shield`` 的物品
  （``FormDef.offhands``）。``enemy_only`` 欄位保留（目前沒有形制用它），玩家拿得到形制的
  地方照舊略過它。
- ``emblem`` 只認 ``peak``，沒寫時不輸出（既有 JSON 不變）。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
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
from trpg.content.equipment import ItemDef, ItemTable
from trpg.content.item_gen import _look_base
from trpg.content.library.gear_checks import _check_appearance
from trpg.engine.battle import start_battle
from trpg.engine.setup import build_setup
from trpg.engine.view import project_for
from trpg.shared.errors import ContentError
from trpg.shared.rng import Rng
from trpg.shared.types import Team


def _table() -> AppearanceTable:
    table = library().appearance
    assert table is not None
    return table


def test_great_shields_are_player_tower_shield_forms() -> None:
    kite = _table().kind_by_id()["kite_shield"]
    forms = {f.id: f for f in kite.forms}
    assert [f.id for f in kite.player_forms()] == ["kite", "tower", "sect_great", "molten_shell"]
    assert (forms["sect_great"].name_zh, forms["molten_shell"].name_zh) == ("雲紋碑盾", "熔殼塔盾")
    assert forms["sect_great"].offhands == forms["molten_shell"].offhands == ("tower_shield",)
    assert forms["kite"].offhands is None and forms["tower"].offhands is None
    # 目前沒有任何造型帶 enemy_only：玩家形制清單＝全部形制
    for kind in _table().kinds:
        assert kind.player_forms() == kind.forms, kind.id


def test_enemy_only_and_offhands_defaults_are_not_dumped() -> None:
    dumped = FormDef(id="kite", name_zh="鳶盾").model_dump()
    assert "enemy_only" not in dumped and "offhands" not in dumped
    assert FormDef(id="x", name_zh="x", enemy_only=True).model_dump()["enemy_only"] is True
    assert FormDef(id="x", name_zh="x", offhands=("tower_shield",)).model_dump()["offhands"] == (
        "tower_shield",
    )


def test_client_list_has_the_great_shields_only_for_tower_shields() -> None:
    exported = appearance_export(_table(), library().keywords)
    kinds = {k["id"]: k for k in exported["kinds"]}  # type: ignore[attr-defined]
    forms = {f["id"]: f for f in kinds["kite_shield"]["forms"]}
    assert list(forms) == ["kite", "tower", "sect_great", "molten_shell"]
    assert forms["sect_great"]["offhands"] == forms["molten_shell"]["offhands"] == ["tower_shield"]
    assert "offhands" not in forms["kite"] and "offhands" not in forms["tower"]


def test_client_list_skips_enemy_only_forms() -> None:
    exported = appearance_export(_with_enemy_form_everywhere(), library().keywords)
    assert "enemy_test" not in json.dumps(exported)


def _shield(form: str, offhand: str) -> ItemDef:
    return ItemDef.model_validate(
        {
            "id": "item_x",
            "name_zh": "測試",
            "slot_type": "offhand",
            "offhand": offhand,
            "kind": "kite_shield",
            "form": form,
        }
    )


@pytest.mark.parametrize("form", ["sect_great", "molten_shell"])
def test_great_shield_forms_only_fit_tower_shields(form: str) -> None:
    assert item_appearance_problems(_shield(form, "tower_shield"), _table()) == []
    problems = item_appearance_problems(_shield(form, "round_shield"), _table())
    assert any("只配副手 tower_shield" in p for p in problems), problems


def test_item_with_enemy_only_form_is_reported() -> None:
    problems = item_appearance_problems(
        _shield("enemy_test", "tower_shield"), _with_enemy_form_everywhere()
    )
    assert any("只給敵人" in p for p in problems), problems


def test_unknown_form_offhand_is_a_content_error() -> None:
    lib = library()
    items = ItemTable(items=tuple(lib.items.values()))
    _check_appearance(Path("content"), _table(), items, lib.keywords, lib.offhands)
    with pytest.raises(ContentError, match="tower_shield"):
        _check_appearance(Path("content"), _table(), items, lib.keywords, {"round_shield"})


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
