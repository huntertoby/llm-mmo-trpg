"""#137 外觀選項（Phase 6R-2）：``races.yaml`` 的 ``look_options``、``LookChoice`` 的驗證與
換種族保留規則。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.battle import DollLook, LookChoice
from trpg.content.library import ContentLibrary
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.races import RaceTable, look_choice_problems, look_for_race
from trpg.shared.errors import ContentError


def _table(library: ContentLibrary) -> RaceTable:
    table = library.ruleset.races
    assert table is not None
    return table


def _raw() -> dict[str, Any]:
    text = (default_content_dir() / "races.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)  # type: ignore[no-any-return]


def test_every_race_has_look_options(library: ContentLibrary) -> None:
    table = _table(library)
    assert len(table.look_eyes) == 6
    for race in table.races:
        assert race.look_options is not None, race.id
        assert look_choice_problems(table, race, LookChoice()) == []


def test_limits_follow_art_table(library: ContentLibrary) -> None:
    races = _table(library).by_id()
    assert races["scalefolk"].options().hair == ("none",)
    assert races["elf"].options().beard == ("none",)
    dwarf = races["dwarf"].options()
    assert dwarf.beard[0] == "full" and "none" in dwarf.beard  # 矮人預設大鬍子、可以選無
    assert races["fox"].options().beast_ears == ("fox", "cat", "wolf", "rabbit")
    assert races["human"].options().beast_ears == ()
    assert "#6a3d1e" in races["human"].options().hair_color  # 人類預設髮色補進清單


def test_default_outside_options_fails(tmp_path: Path) -> None:
    data = _raw()
    data["races"][0]["look_options"]["skin"] = ["#000000"]
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="skin"):
        load_content_file(path, RaceTable)


def test_choice_outside_race_is_rejected(library: ContentLibrary) -> None:
    table = _table(library)
    races = table.by_id()
    ok = LookChoice(hair="ponytail", beard="stubble", face="heart", lashes=True, frame="slim")
    assert look_choice_problems(table, races["human"], ok) == []
    bad = LookChoice(beard="full", hair="ponytail", beast_ears="cat")
    problems = look_choice_problems(table, races["elf"], bad)
    assert len(problems) == 2  # 精靈沒有鬍子、沒有獸耳；馬尾可以
    assert any("鬍子" in p for p in problems)
    assert look_choice_problems(table, races["fox"], LookChoice(beast_ears="rabbit")) == []
    assert look_choice_problems(table, races["scalefolk"], LookChoice(eyes="#103030")) == []
    assert look_choice_problems(table, races["human"], LookChoice(eyes="#103030")) != []


def test_choice_fields_are_closed() -> None:
    with pytest.raises(ValidationError):
        LookChoice.model_validate({"hair": "mohawk"})
    with pytest.raises(ValidationError):
        LookChoice.model_validate({"gender": "f"})  # 不存性別（#137）
    assert "gender" not in LookChoice.model_fields and "sex" not in LookChoice.model_fields


def test_race_change_keeps_shared_options(library: ContentLibrary) -> None:
    table = _table(library)
    races = table.by_id()
    choice = LookChoice(
        face="oval", eye_style="big", lashes=True, frame="broad", hair="bob", beard="stubble"
    )
    kept = look_for_race(table, races["elf"], choice)
    assert kept == LookChoice(face="oval", eye_style="big", lashes=True, frame="broad", hair="bob")
    assert look_for_race(table, races["scalefolk"], LookChoice(hair="bob")) is None
    assert look_for_race(table, races["human"], None) is None


def test_doll_custom_is_optional() -> None:
    assert DollLook().custom is None
    doll = DollLook.model_validate({"custom": {"hair": "twin"}})
    assert doll.custom is not None and doll.custom.hair == "twin"
