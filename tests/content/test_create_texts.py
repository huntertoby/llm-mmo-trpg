"""建角畫面的文字（UI-E1b）：種族一句簡介 ``blurb_zh``、出身短描述 ``tagline_zh``。

文字是玩法 PM 2026-11-04 的定稿；前端建角頁在 build 時匯入同一份 yaml 顯示。
這裡鎖住 schema（必填、不可空、長度上限）與定稿文字。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import default_content_dir, load_content_file
from trpg.content.races import ORIGIN_TAGLINE_MAX, RACE_BLURB_MAX, OriginTable, RaceTable
from trpg.shared.errors import ContentError

# 玩法 PM「建角畫面 v2 的種族與出身文字」第 1、2 節
_BLURBS = {
    "human": "散居五界的多數族群，什麼都學得快。",
    "elf": "長壽的林地一族，眼睛比誰都尖。",
    "fox": "狐耳狐尾的一族，聽得見別人聽不見的腳步聲，也最會說話。",
    "dragonkin": "流著古龍血的一族，一開口就讓人退一步。",
    "dwarf": "住在山腹的工匠一族，站得穩，也懂機關。",
    "cyborg": "身上嵌著晶能零件的人，手比常人更準。",
    "orc": "力氣大的一族，習慣用肩膀解決問題。",
    "fiend": "頭上長角、皮膚帶炎紋的一族，看得懂異象與預兆。",
    "scalefolk": "水邊長大的鱗皮一族，走路幾乎沒有聲音。",
    "seafolk": "在船上長大的人，風浪裡也撐得住。",
}
_TAGLINES = {
    "crystal_crown": "白石與晶光的城邦",
    "cloud_ridge": "雲海上的山城與竹林",
    "arcane_hub": "黃銅與晶能的工坊街",
    "ashen_waste": "焦土上的拾荒聚落",
    "frost_tide": "浮冰與珊瑚的港灣",
}
# 判定加值（9.6.11 #115，situation_rules.yaml 的 race_methods）：建角頁顯示「判定加值：交涉 +1」
_RACE_METHOD_ZH = {
    "human": "學識",
    "elf": "察覺",
    "fox": "交涉",
    "dragonkin": "威嚇",
    "dwarf": "機關",
    "cyborg": "靈巧",
    "orc": "力取",
    "fiend": "異象",
    "scalefolk": "潛行",
    "seafolk": "耐力",
}


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def _raw(name: str) -> dict[str, Any]:
    return yaml.safe_load((default_content_dir() / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _load_bad(tmp_path: Path, data: dict[str, Any], model: type[Any]) -> str:
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError) as info:
        load_content_file(path, model)
    return str(info.value)


def test_bundled_blurbs_match_gameplay_pm_text(library: ContentLibrary) -> None:
    assert library.races is not None
    assert {r.id: r.blurb_zh for r in library.races.races} == _BLURBS


def test_bundled_taglines_match_gameplay_pm_text(library: ContentLibrary) -> None:
    assert library.origins is not None
    assert {o.realm: o.tagline_zh for o in library.origins.origins} == _TAGLINES


def test_every_race_has_a_check_method_shown_on_the_create_page() -> None:
    rules = _raw("world/situation_rules.yaml")
    names = {m["id"]: m["name_zh"] for m in rules["methods"]}
    shown = {race: names[method] for race, method in rules["race_methods"].items()}
    assert shown == _RACE_METHOD_ZH
    assert rules["check"]["race_bonus"] == 1


@pytest.mark.parametrize(
    ("file", "key", "field", "model"),
    [
        ("races.yaml", "races", "blurb_zh", RaceTable),
        ("origins.yaml", "origins", "tagline_zh", OriginTable),
    ],
)
def test_create_text_is_required(
    tmp_path: Path, file: str, key: str, field: str, model: type[Any]
) -> None:
    data = _raw(file)
    del data[key][0][field]
    assert field in _load_bad(tmp_path, data, model)


_CAPS = {"blurb_zh": RACE_BLURB_MAX, "tagline_zh": ORIGIN_TAGLINE_MAX}


@pytest.mark.parametrize(
    ("file", "key", "field", "model"),
    [
        ("races.yaml", "races", "blurb_zh", RaceTable),
        ("origins.yaml", "origins", "tagline_zh", OriginTable),
    ],
)
def test_create_text_length_is_capped(
    tmp_path: Path, file: str, key: str, field: str, model: type[Any]
) -> None:
    data = _raw(file)
    data[key][0][field] = "字" * (_CAPS[field] + 1)
    assert field in _load_bad(tmp_path, data, model)


@pytest.mark.parametrize(
    ("file", "key", "field", "model"),
    [
        ("races.yaml", "races", "blurb_zh", RaceTable),
        ("origins.yaml", "origins", "tagline_zh", OriginTable),
    ],
)
def test_create_text_cannot_be_empty(
    tmp_path: Path, file: str, key: str, field: str, model: type[Any]
) -> None:
    data = _raw(file)
    data[key][0][field] = ""
    assert field in _load_bad(tmp_path, data, model)
