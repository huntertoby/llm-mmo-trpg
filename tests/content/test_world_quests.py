"""任務、聊天內容、事件好感度、酒館傳聞與好感度規則（Phase 5B-4；Phase5計畫 16.8）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_quests import (
    AffinityRules,
    QuestDef,
    QuestTable,
    SocialTable,
    TalkEntry,
    quest_problems,
    quest_refs,
    social_problems,
)
from trpg.shared.errors import ContentError
from trpg.skillgen.validate import validate_skill


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def quests(library: ContentLibrary) -> QuestTable:
    return library.world_quests.quests["cloud_ridge"]


@pytest.fixture(scope="module")
def social(library: ContentLibrary) -> SocialTable:
    return library.world_quests.social["cloud_ridge"]


def _refs_of(library: ContentLibrary) -> Any:
    keywords = {k.id for k in library.keywords.keywords}
    return quest_refs("cloud_ridge", library.world_maps, library.world_event_content, keywords)


def _quest(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "test_quest",
        "kind": "chain",
        "name_zh": "測試",
        "steps": [
            {
                "id": "s1",
                "text_zh": "走",
                "when": [{"kind": "at_location", "location": "ferry_steps"}],
            }
        ],
    }
    data.update(updates)
    return data


def _quest_problems(library: ContentLibrary, *quests: dict[str, Any], **extra: Any) -> list[str]:
    table = QuestTable.model_validate({"region": "cloud_ridge", "quests": list(quests), **extra})
    return quest_problems(table, _refs_of(library))


# ---------------------------------------------------------------------------
# 雲嶺內容
# ---------------------------------------------------------------------------


def test_cloud_ridge_quests_loaded(quests: QuestTable) -> None:
    kinds = sorted(q.kind for q in quests.quests)
    assert kinds == ["chain", "chain", "hidden", "hidden", "main", "starter"]  # 5B-4b 導師任務鏈
    by_id = quests.quest_by_id()
    assert len(by_id["starter_ferry"].steps) == 3
    assert len(by_id["main_mist_rift"].steps) == 5
    assert 3 <= len(by_id["chain_temple_split"].steps) <= 6  # 9.6.3「3～6 步」
    assert [s.id for s in quests.story_skills] == ["skill_mist_breaker"]
    assert "6 個任務" in quests.summary()


def test_story_skill_not_in_skill_pool(library: ContentLibrary, quests: QuestTable) -> None:
    skill = quests.story_skills[0]
    assert skill.id not in library.skills  # 不進技能池（07 7.6 劇情技能只由主線給）
    assert skill.weapon_req == "any"  # 每人相同
    assert validate_skill(skill, library) == []


def test_social_loaded(social: SocialTable, library: ContentLibrary) -> None:
    npcs = set(library.world_event_content.npcs["cloud_ridge"].npc_by_id())
    rumor_npcs = {t.npc for t in social.talk if t.kind == "rumor"}
    secret_npcs = {t.npc for t in social.talk if t.kind == "secret"}
    assert rumor_npcs == npcs
    assert secret_npcs == npcs
    entries = [t for t in social.talk if t.kind == "quest_entry"]
    assert [(t.npc, t.quest, t.rank) for t in entries] == [
        ("shopkeeper_liu", "hidden_elixir_cave", "friendly")
    ]
    assert len(social.rumors) == 6
    assert "6 條酒館傳聞" in social.summary()


def test_granny_secret_unlocks_secret_door_event(social: SocialTable) -> None:
    secret = next(t for t in social.talk if t.id == "granny_du_secret")
    assert secret.rank == "trusted"
    # 5B-4b（18.7.7）：說出祕密時解鎖骨架 22，暗門的線頭由事件結果給，祕密本身不提暗門
    assert secret.unlocks_skeleton == "granny_past"
    assert "暗門" not in secret.text_zh


def test_affinity_rules(library: ContentLibrary) -> None:
    rules = library.world_quests.affinity
    assert rules is not None
    cases = {-100: "hostile", -50: "hostile", -49: "cold", -10: "cold", -9: "neutral"}
    cases |= {19: "neutral", 20: "friendly", 59: "friendly", 60: "trusted", 100: "trusted"}
    for value, rank in cases.items():
        assert rules.rank_of(value) == rank, value
    assert rules.clamp(150) == 100
    assert rules.clamp(-150) == -100
    assert rules.name_of("friendly") == "友善"


def test_cross_file_clean(library: ContentLibrary, quests: QuestTable, social: SocialTable) -> None:
    refs = _refs_of(library)
    assert quest_problems(quests, refs) == []
    assert social_problems(social, refs, quests) == []


def test_files_listed(library: ContentLibrary) -> None:
    names = {p.relative_to(library.root).as_posix() for p, _ in library.files}
    assert {
        "world/quests/cloud_ridge.yaml",
        "world/social/cloud_ridge.yaml",
        "world/affinity.yaml",
    } <= names


# ---------------------------------------------------------------------------
# 單檔驗證
# ---------------------------------------------------------------------------


def test_minimal_quest_valid(library: ContentLibrary) -> None:
    assert _quest_problems(library, _quest()) == []


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"start": [{"kind": "win_battle", "location": "ferry_steps"}]}, "狀態型"),
        (
            {
                "steps": [
                    {"id": "a", "text_zh": "x", "when": [{"kind": "talk", "npc": "granny_du"}]},
                    {"id": "a", "text_zh": "y", "when": [{"kind": "talk", "npc": "granny_du"}]},
                ]
            },
            "步驟 ID 重複",
        ),
        ({"steps": []}, "steps"),
    ],
)
def test_bad_quest(updates: dict[str, Any], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        QuestDef.model_validate(_quest(**updates))


def test_any_of_rules() -> None:
    one = {"kind": "any_of", "conditions": [{"kind": "talk", "npc": "granny_du"}]}
    with pytest.raises(ValidationError):
        QuestDef.model_validate(_quest(steps=[{"id": "s", "text_zh": "x", "when": [one]}]))
    nested = {"kind": "any_of", "conditions": [one, {"kind": "talk", "npc": "granny_du"}]}
    with pytest.raises(ValidationError):
        QuestDef.model_validate(_quest(steps=[{"id": "s", "text_zh": "x", "when": [nested]}]))


def test_duplicate_quest_ids() -> None:
    with pytest.raises(ValidationError, match="任務 ID 重複"):
        QuestTable.model_validate({"region": "cloud_ridge", "quests": [_quest(), _quest()]})


@pytest.mark.parametrize(
    ("data", "match"),
    [
        ({"kind": "secret", "rank": "friendly"}, "祕密只能是信賴"),
        ({"kind": "quest_entry", "rank": "neutral", "quest": "q"}, "至少要 friendly"),
        ({"kind": "rumor", "rank": "cold"}, "至少要 neutral"),
        ({"kind": "quest_entry", "rank": "friendly"}, "quest_entry 要填 quest"),
        ({"kind": "rumor", "rank": "neutral", "quest": "q"}, "quest_entry 要填 quest"),
    ],
)
def test_bad_talk_entry(data: dict[str, Any], match: str) -> None:
    base = {"id": "t", "npc": "granny_du", "text_zh": "話"}
    with pytest.raises(ValidationError, match=match):
        TalkEntry.model_validate({**base, **data})


def test_bad_affinity_rules() -> None:
    ranks = [
        {"id": "hostile", "name_zh": "敵視", "min": -100},
        {"id": "cold", "name_zh": "冷淡", "min": -49},
        {"id": "neutral", "name_zh": "中立", "min": -9},
        {"id": "friendly", "name_zh": "友善", "min": 20},
        {"id": "trusted", "name_zh": "信賴", "min": 60},
    ]
    AffinityRules.model_validate({"ranks": ranks})
    with pytest.raises(ValidationError, match="依序"):
        AffinityRules.model_validate({"ranks": ranks[::-1]})
    bad = [dict(r) for r in ranks]
    bad[3]["min"] = -20
    with pytest.raises(ValidationError, match="遞增"):
        AffinityRules.model_validate({"ranks": bad})
    first = [dict(r) for r in ranks]
    first[0]["min"] = -90
    with pytest.raises(ValidationError, match="min_value"):
        AffinityRules.model_validate({"ranks": first})


# ---------------------------------------------------------------------------
# 跨檔案
# ---------------------------------------------------------------------------


def _step(*when: dict[str, Any], **reward: Any) -> dict[str, Any]:
    return {"id": "s", "text_zh": "x", "when": list(when), "reward": reward}


@pytest.mark.parametrize(
    ("step", "match"),
    [
        (_step({"kind": "at_location", "location": "nowhere"}), "未知地點 nowhere"),
        (_step({"kind": "win_battle", "location": "nowhere"}), "未知地點 nowhere"),
        (_step({"kind": "hold_thread", "thread": "no_thread"}), "未知線頭 no_thread"),
        (_step({"kind": "affinity", "npc": "nobody", "rank": "friendly"}), "未知 NPC nobody"),
        (_step({"kind": "talk", "npc": "nobody"}), "未知 NPC nobody"),
        (_step({"kind": "situation", "skeleton": "nothing"}), "沒有骨架 nothing"),
        (
            _step(
                {"kind": "situation", "skeleton": "monks_dispute", "templates": ["patrol_track"]}
            ),
            "模板 patrol_track 不屬於骨架",
        ),
        (_step({"kind": "quest_step", "quest": "test_quest", "step": 2}), "只有 1 步"),
        (_step({"kind": "quest_step", "quest": "nope", "step": 1}), "未知任務 nope"),
        (
            _step({"kind": "talk", "npc": "granny_du"}, story_skill="skill_nothing"),
            "未知劇情技能",
        ),
        (
            _step(
                {"kind": "talk", "npc": "granny_du"},
                offer={"kind": "whiteboard", "bias_keywords": ["healing"]},
            ),
            "未知關鍵字 healing",
        ),
        (_step({"kind": "talk", "npc": "granny_du"}, xp_source="gold"), "未知經驗來源 gold"),
        (_step({"kind": "talk", "npc": "granny_du"}, affinity={"nobody": 5}), "未知 NPC nobody"),
    ],
)
def test_quest_cross_file_problems(
    library: ContentLibrary, step: dict[str, Any], match: str
) -> None:
    problems = _quest_problems(library, _quest(steps=[step]))
    assert any(match in p for p in problems), problems


def test_unknown_giver(library: ContentLibrary) -> None:
    assert any("未知 NPC nobody" in p for p in _quest_problems(library, _quest(giver="nobody")))


def test_social_cross_file(library: ContentLibrary, quests: QuestTable) -> None:
    table = SocialTable.model_validate(
        {
            "region": "cloud_ridge",
            "talk": [
                {"id": "a", "npc": "nobody", "rank": "neutral", "kind": "rumor", "text_zh": "x"},
                {
                    "id": "b",
                    "npc": "granny_du",
                    "rank": "friendly",
                    "kind": "quest_entry",
                    "quest": "starter_ferry",
                    "text_zh": "x",
                },
                {
                    "id": "c",
                    "npc": "granny_du",
                    "rank": "friendly",
                    "kind": "quest_entry",
                    "quest": "hidden_elixir_cave",
                    "text_zh": "x",
                },
            ],
            "event_affinity": [
                {"skeleton": "nothing", "outcome": "success", "npc": "granny_du", "delta": 5}
            ],
            "rumors": [{"id": "r", "text_zh": "x", "location": "nowhere"}],
        }
    )
    problems = social_problems(table, _refs_of(library), quests)
    text = "；".join(problems)
    assert "未知 NPC nobody" in text
    assert "starter_ferry 不是本區的隱藏任務" in text
    assert "giver 不是 granny_du" in text
    assert "沒有骨架 nothing" in text
    assert "未知地點 nowhere" in text


# ---------------------------------------------------------------------------
# 檔案層
# ---------------------------------------------------------------------------


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def _edit_yaml(path: Path, edit: Any) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8", newline="\n")


def test_bad_quest_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "quests" / "cloud_ridge.yaml"
    _edit_yaml(path, lambda d: d["quests"][0].update(giver="nobody"))
    with pytest.raises(ContentError, match="nobody"):
        load_library(content)


def test_bad_story_skill_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "quests" / "cloud_ridge.yaml"
    _edit_yaml(path, lambda d: d["story_skills"][0].update(shape={"type": "no_shape"}))
    with pytest.raises(ContentError, match="劇情技能 skill_mist_breaker"):
        load_library(content)


def test_quest_file_name_must_match_region(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    folder = content / "world" / "quests"
    (folder / "cloud_ridge.yaml").rename(folder / "misty.yaml")
    with pytest.raises(ContentError, match="檔名必須與 region 相同"):
        load_library(content)


def test_social_bad_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "social" / "cloud_ridge.yaml"
    _edit_yaml(path, lambda d: d["rumors"][0].update(skeleton="nothing"))
    with pytest.raises(ContentError, match="nothing"):
        load_library(content)


def test_without_quest_files(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    shutil.rmtree(content / "world" / "quests")
    shutil.rmtree(content / "world" / "social")
    (content / "world" / "affinity.yaml").unlink()
    lib = load_library(content)
    assert lib.world_quests.quests == {}
    assert lib.world_quests.social == {}
    assert lib.world_quests.affinity is None
