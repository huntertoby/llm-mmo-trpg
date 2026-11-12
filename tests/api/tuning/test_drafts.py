"""NW-1a A2：改動單與草稿（:mod:`trpg.api.tuning.drafts`）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from trpg.api.tuning.drafts import Change, Draft, DraftStore, merge, normalize, reverse

HP = "units/ashen_heart.yaml"


def _c(path: str, old: int | None, new: int | None, file: str = HP) -> Change:
    return Change(file=file, path=path, old=old, new=new)


def test_normalize_sorts_dedupes_and_keeps_the_first_old() -> None:
    out = normalize(
        [
            _c("speed", 0, 1),
            _c("max_hp", 160, 150),
            _c("max_hp", 150, 140),  # 同欄位：新值取後到的、舊值留最早的
            _c("armor_bonus", 5, 5),  # 改回原值：去掉
            _c("max_hp", 1, 2, file="units/ash_hound.yaml"),
        ]
    )
    assert [(c.file, c.path, c.old, c.new) for c in out] == [
        ("units/ash_hound.yaml", "max_hp", 1, 2),
        (HP, "max_hp", 160, 140),
        (HP, "speed", 0, 1),
    ]


def test_merge_and_reverse() -> None:
    draft = (_c("max_hp", 160, 150), _c("speed", None, 2))
    assert reverse(draft) == (_c("max_hp", 150, 160), _c("speed", 2, None))
    assert merge(draft, reverse(draft)) == ()  # 改了又改回去＝沒有改動
    assert merge(draft, [_c("max_hp", 160, 170)]) == (_c("max_hp", 160, 170), _c("speed", None, 2))


def test_store_round_trip(tmp_path: Path) -> None:
    store = DraftStore(tmp_path / "drafts")
    assert store.names() == [] and store.get("current").changes == ()
    saved = store.put(Draft(name="current", changes=(_c("speed", 0, 1), _c("max_hp", 160, 150))))
    assert [c.path for c in saved.changes] == ["max_hp", "speed"]
    assert store.get("current") == saved
    assert store.names() == ["current"]
    raw = json.loads((tmp_path / "drafts" / "current.json").read_text(encoding="utf-8"))
    assert raw["format"].startswith("trpg-tuning-draft/")
    assert store.delete("current") and not store.delete("current")


@pytest.mark.parametrize("name", ["../x", "a/b", "", "UPPER", "x" * 41])
def test_bad_draft_names_are_refused(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValidationError):
        DraftStore(tmp_path).get(name)


def test_change_file_must_be_a_relative_yaml_path() -> None:
    for bad in ("../units/x.yaml", "/abs.yaml", "units\\x.yaml", "units/x.json"):
        with pytest.raises(ValidationError):
            Change(file=bad, path="max_hp", old=1, new=2)
