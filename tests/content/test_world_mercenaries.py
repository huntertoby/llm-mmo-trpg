"""系統傭兵名單（Phase 5C-1；``docs/phases/Phase5計畫.md`` 22.2）。"""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_mercenaries import MERCENARY_ROLES, MercenaryTable
from trpg.content.world_quests import QuestDef
from trpg.shared.errors import ContentError

ROSTER = {
    "merc_qingfeng": ("青鋒", "damage", "build_charger"),  # 5C-2 玩法 PM 定 ①：近戰劍士
    "merc_chuanyun": ("珊瑚", "damage", "build_ranged"),
    "merc_chiyan": ("灰燼瑪菈", "damage", "build_fire"),
    "merc_tiebi": ("賽倫", "guardian", "build_tank"),
    "merc_panshi": ("鉚釘", "guardian", "build_guardian"),
    "merc_huichun": ("回春", "support", "build_healer"),
    "merc_qingyin": ("莉瑟", "support", "build_support"),
    "merc_jinglei": ("七號線圈", "control", "build_storm"),
    "merc_fuying": ("鏽牙", "control", "build_trapper"),
}
"""9.6.11 #117 的名單（暫名、定位、底稿）；青鋒的底稿 5C-2 改成近戰力量型劍士。"""


def test_roster_matches_design(library: ContentLibrary) -> None:
    table = library.world_mercenaries
    assert table is not None
    assert table.max_hired == 2  # #97
    assert {m.id: (m.name_zh, m.role, m.build) for m in table.mercenaries} == ROSTER
    counts: Counter[str] = Counter(m.role for m in table.mercenaries)
    assert all(counts[r] >= 2 for r in MERCENARY_ROLES)  # 9.6.8
    builds = library.builds.by_id()
    for merc in table.mercenaries:
        build = builds[merc.build]
        assert not build.blank
        assert not build.reference


def test_qingfeng_is_melee_strength(library: ContentLibrary) -> None:
    """輸出位要有一名近戰（5C-2 玩法 PM 定 ①）：青鋒的底稿拿劍、力量最高。"""
    table = library.world_mercenaries
    assert table is not None
    hero = library.builds.by_id()[table.by_id()["merc_qingfeng"].build].hero
    assert hero.weapon == "one_handed_sword"
    assert max(hero.attributes, key=lambda a: hero.attributes[a]) == "str"


def test_ai_choices_exist(library: ContentLibrary) -> None:
    table = library.world_mercenaries
    assert table is not None
    profiles = library.ai_profiles.by_id()
    assert table.ai_choices
    assert all(p in profiles for p in table.ai_choices)
    assert "idle" not in table.ai_choices
    assert table.shadow_daily_coins >= 1


def _table(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "max_hired": 2,
        "mercenaries": [
            {"id": k, "name_zh": n, "title_zh": "x", "role": r, "build": b}
            for k, (n, r, b) in ROSTER.items()
        ],
    }
    data.update(updates)
    return data


def test_schema_rejects_duplicates_and_missing_roles() -> None:
    MercenaryTable.model_validate(_table())
    dup = _table()
    dup["mercenaries"].append(dict(dup["mercenaries"][0]))
    with pytest.raises(ValidationError, match="重複"):
        MercenaryTable.model_validate(dup)
    few = _table()
    few["mercenaries"] = [m for m in few["mercenaries"] if m["id"] != "merc_fuying"]
    with pytest.raises(ValidationError, match="控制"):
        MercenaryTable.model_validate(few)
    with pytest.raises(ValidationError):
        MercenaryTable.model_validate(_table(max_hired=3))


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    root = tmp_path / "content"
    shutil.copytree(library.root, root)
    return root


def _write(root: Path, data: dict[str, Any]) -> None:
    path = root / "world" / "mercenaries.yaml"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True)


def test_loader_checks_builds(tmp_path: Path, library: ContentLibrary) -> None:
    root = _copy_content(tmp_path, library)
    data = _table()
    data["mercenaries"][0]["build"] = "build_nobody"
    _write(root, data)
    with pytest.raises(ContentError, match="build_nobody"):
        load_library(root)
    blank = next(b.id for b in library.builds.builds if b.blank)
    data["mercenaries"][0]["build"] = blank
    _write(root, data)
    with pytest.raises(ContentError, match="白板"):
        load_library(root)
    data = _table(ai_choices=["brute", "nobody_profile"])
    _write(root, data)
    with pytest.raises(ContentError, match="nobody_profile"):
        load_library(root)
    (root / "world" / "mercenaries.yaml").unlink()
    assert load_library(root).world_mercenaries is None


# ---------------------------------------------------------------------------
# 5C-3：預設傭兵與劇情夥伴
# ---------------------------------------------------------------------------


def test_default_party_and_companion(library: ContentLibrary) -> None:
    table = library.world_mercenaries
    assert table is not None
    assert table.default_party == ("merc_tiebi",)  # #154：開局只帶賽倫（原 5C-3 賽倫＋回春）
    ayue = table.companion_by_id()["companion_ayue"]
    assert (ayue.name_zh, ayue.npc, ayue.build) == ("阿岳", "hunter_ayue", "build_ranged")
    assert (ayue.affinity_per_win, ayue.affinity_daily_cap) == (2, 6)  # 18.7.6
    quests = library.world_quests.quests["cloud_ridge"].quests
    linked = sorted(q.id for q in quests if q.companion == "companion_ayue")
    assert linked == ["main_mist_rift", "starter_ferry"]  # 18.5（代決 5C3-3）
    starter = next(q for q in quests if q.id == "starter_ferry")
    assert starter.companion_after == "ferry_bandits"  # #154：渡口石階打完才入隊


def test_escort_and_companion_lines_follow_design(library: ContentLibrary) -> None:
    """#154 台詞與來歷（09 9.6「預設隊友的出場」、18 18.7.1 第 1 步，玩法 PM 定稿）。"""
    table = library.world_mercenaries
    assert table is not None and table.escort is not None
    escort = table.escort
    assert escort.mercenary == "merc_tiebi"
    assert escort.backstory_zh == "守印人派來的護衛。正式選定後可以在城鎮換人。"
    assert [(x.speaker_zh, x.text_zh) for x in escort.intro] == [
        ("守印人", "一個人上路太險。賽倫，你陪這位旅人去霧渡鎮，等站穩了腳步再說。"),
        ("賽倫", "盾在我手上，你只管往前走。"),
    ]
    ayue = table.companion_by_id()["companion_ayue"]
    assert ayue.backstory_zh == "在渡口一起打退盜賊後同行。任務結束後離隊。"
    assert [(x.speaker_zh, x.text_zh) for x in ayue.join_lines] == [
        ("阿岳", "那幫盜賊是衝著渡船來的……我爹的事還沒查清，順路，我跟你走一段。"),
    ]


def test_schema_rejects_escort_outside_default_party() -> None:
    escort = {
        "mercenary": "merc_huichun",
        "backstory_zh": "x",
        "intro": [{"speaker_zh": "a", "text_zh": "b"}],
    }
    with pytest.raises(ValidationError, match="escort"):
        MercenaryTable.model_validate(_table(default_party=["merc_tiebi"], escort=escort))


def test_quest_companion_after_must_be_own_step(library: ContentLibrary) -> None:
    quests = library.world_quests.quests["cloud_ridge"].quests
    starter = next(q for q in quests if q.id == "starter_ferry").model_dump()
    with pytest.raises(ValidationError, match="companion_after"):
        QuestDef.model_validate({**starter, "companion_after": "no_such_step"})
    with pytest.raises(ValidationError, match="companion_after"):
        QuestDef.model_validate({**starter, "companion": None})


def test_schema_rejects_bad_default_party_and_companions() -> None:
    with pytest.raises(ValidationError, match="default_party"):
        MercenaryTable.model_validate(_table(default_party=["merc_nobody"]))
    with pytest.raises(ValidationError, match="default_party"):
        MercenaryTable.model_validate(_table(default_party=["merc_tiebi", "merc_tiebi"]))
    clash = {"id": "merc_tiebi", "npc": "x", "name_zh": "x", "title_zh": "x", "build": "b"}
    with pytest.raises(ValidationError, match="劇情夥伴"):
        MercenaryTable.model_validate(_table(companions=[clash]))


def test_loader_checks_companions(tmp_path: Path, library: ContentLibrary) -> None:
    root = _copy_content(tmp_path, library)
    companion = {
        "id": "companion_ayue",
        "npc": "hunter_ayue",
        "name_zh": "阿岳",
        "title_zh": "獵戶",
        "build": "build_ranged",
    }
    _write(root, _table(companions=[{**companion, "npc": "nobody_npc"}]))
    with pytest.raises(ContentError, match="nobody_npc"):
        load_library(root)
    _write(root, _table(companions=[{**companion, "build": "build_nobody"}]))
    with pytest.raises(ContentError, match="build_nobody"):
        load_library(root)
    _write(root, _table())  # 任務引用的夥伴不在名單
    with pytest.raises(ContentError, match="companion_ayue"):
        load_library(root)


# ---------------------------------------------------------------------------
# RT-4（#131）：五區出身與頭像
# ---------------------------------------------------------------------------

ORIGINS = {
    "merc_tiebi": "crystal_crown",  # 賽倫（盾衛）
    "merc_qingyin": "crystal_crown",  # 莉瑟（祝禱師）
    "merc_qingfeng": "cloud_ridge",  # 青鋒（劍客）
    "merc_huichun": "cloud_ridge",  # 回春（醫者）
    "merc_panshi": "arcane_hub",  # 鉚釘（守護者）
    "merc_jinglei": "arcane_hub",  # 七號線圈（雷水術士）
    "merc_chiyan": "ashen_waste",  # 灰燼瑪菈（火術士）
    "merc_fuying": "ashen_waste",  # 鏽牙（陷阱師）
    "merc_chuanyun": "frost_tide",  # 珊瑚（弓手）
}
"""#131：出身界域（09 9.6.8）。"""

EXTRAS = {
    "merc_tiebi": ("crest",),
    "merc_qingyin": ("circlet",),
    "merc_qingfeng": ("headband",),
    "merc_huichun": ("apron_cross",),
    "merc_panshi": ("goggles", "soot"),
    "merc_jinglei": ("cyber_eye",),
    "merc_chiyan": ("ember_eye", "rune"),
    "merc_fuying": ("bandana", "scar", "earring"),
    "merc_chuanyun": ("coral", "earring"),
}
"""頭像配件（``docs/art/sample/merc-portraits.html`` 的 NEW 表）。"""


def test_origins_cover_five_regions(library: ContentLibrary) -> None:
    table = library.world_mercenaries
    assert table is not None
    assert {m.id: m.origin for m in table.mercenaries} == ORIGINS
    assert library.regions is not None
    assert set(ORIGINS.values()) == {r.id for r in library.regions.regions}  # 五區都有人


def test_portraits_follow_sample(library: ContentLibrary) -> None:
    table = library.world_mercenaries
    assert table is not None
    looks = {}
    for merc in table.mercenaries:
        assert merc.portrait is not None, merc.id
        assert merc.portrait.look is not None, merc.id
        assert "body" in merc.portrait.gear, merc.id
        assert merc.portrait.extras == EXTRAS[merc.id]
        looks[merc.id] = merc.portrait.look
    assert looks["merc_qingyin"].ears == "pointed"  # 精靈
    assert looks["merc_fuying"].tusks  # 獸人
    assert looks["merc_chiyan"].horns == "curved"  # 角魔
    assert looks["merc_panshi"].build == "stout"  # 矮人
    assert looks["merc_jinglei"].pattern == "circuit"  # 晶能義體人


def test_loader_checks_origin(tmp_path: Path, library: ContentLibrary) -> None:
    root = _copy_content(tmp_path, library)
    path = root / "world" / "mercenaries.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["mercenaries"][0]["origin"] = "nowhere_land"
    _write(root, data)
    with pytest.raises(ContentError, match="nowhere_land"):
        load_library(root)
