"""5B-4b 的資料欄位與檢查（``docs/phases/Phase5計畫.md`` 19.2～19.8、19.14）。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.content.test_world_events import _problems, _skeleton, _table
from tests.content.test_world_quests import _quest, _quest_problems, _refs_of
from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_encounters import EncounterTable, encounter_table_problems
from trpg.content.world_events import EventSkeletonDef, SolutionDef
from trpg.content.world_quests import (
    SkillOfferReward,
    SocialTable,
    TalkEntry,
    social_problems,
)


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


# ---------------------------------------------------------------------------
# 雲嶺內容
# ---------------------------------------------------------------------------


def test_town_only_has_non_combat_events(library: ContentLibrary) -> None:
    """玩法 PM 定：城鎮是安全區；霧渡鎮只有骨架 16、22，燈籠隊移到渡口石階與竹林小徑（夜晚）。"""
    table = library.world_event_content.events["cloud_ridge"]
    at_town = sorted(s.number for s in table.skeletons if "mist_ferry" in s.locations)
    assert at_town == [16, 22]
    lantern = table.skeleton_by_id()["lantern_patrol"]
    assert lantern.locations == ("ferry_steps", "bamboo_path")
    assert lantern.day_phase == "night"


def test_combat_skeleton_in_town_rejected(library: ContentLibrary) -> None:
    town = _skeleton(locations=["mist_ferry"], solutions=[{"kind": "combat"}])
    assert any("不能出現在城鎮 mist_ferry" in p for p in _problems(library, _table(town)))
    calm = _skeleton(locations=["mist_ferry"], solutions=[{"kind": "abandon"}])
    assert _problems(library, _table(calm)) == []


def test_granny_past(library: ContentLibrary) -> None:
    skeleton = library.world_event_content.events["cloud_ridge"].skeleton_by_id()["granny_past"]
    assert skeleton.number == 22 and skeleton.unlock_only
    assert skeleton.result_threads() == {"gang_fort_secret_door"}
    templates = library.world_event_content.situations.templates["cloud_ridge"].template_by_id()
    for template_id in ("granny_parley", "granny_notice"):
        template = templates[template_id]
        assert template.base_dc == 8
        assert template.success.rewards.threads == ("gang_fort_secret_door",)
    social = library.world_quests.social["cloud_ridge"]
    secret = next(t for t in social.talk if t.id == "granny_du_secret")
    assert secret.unlocks_skeleton == "granny_past"
    assert "暗門" not in secret.text_zh  # 線頭只由事件結果產生（#85）


def test_ferry_favor_and_endings(library: ContentLibrary) -> None:
    events = library.world_event_content.events["cloud_ridge"]
    ferry = events.skeleton_by_id()["broken_ferry"].solutions[0]
    assert (ferry.kind, ferry.cost_supplies, ferry.waive_thread) == (
        "parley",
        2,
        "peddler_owes_you",
    )
    threads = events.thread_by_id()
    assert threads["scarface_grudge"].on_expire_flag == "scarface_rises"
    assert threads["temple_traitor"].on_expire_flag == "temple_traitor_strikes"
    table = library.world_encounters["cloud_ridge"].location_by_id()
    assert table["cliff_gang_fort"].variant_for(("scarface_rises",)) is not None
    assert table["mist_temple_gate"].variant_for(("temple_traitor_strikes",)) is not None


def test_quest_content_5b4b(library: ContentLibrary) -> None:
    table = library.world_quests.quests["cloud_ridge"]
    assert table.region_keywords == ("wet", "charged", "concealed")
    quests = table.quest_by_id()
    for step in quests["starter_ferry"].steps:
        offer = step.reward.offer
        assert offer is not None and offer.mix is not None
        assert offer.mix.as_tuple() == (1, 0, 2) and offer.min_passive == 1
        assert step.npcs == ("granny_du",)
    mentor = quests["mentor_qingya_trial"]
    assert mentor.kind == "chain" and len(mentor.steps) == 3
    assert all(s.reward.offer is None and s.reward.xp_source is None for s in mentor.steps)
    for quest in quests.values():  # 不再用單筆好感度獎勵（改成 npcs ＋15）
        assert all(not s.reward.affinity for s in quest.steps)
    rules = library.world_quests.affinity
    assert rules is not None
    assert (rules.quest_step_delta, rules.daily_talk_delta) == (15, 3)


def test_quest_texts_hide_unrevealed_places(library: ContentLibrary) -> None:
    """玩法 PM 定：任務說明與入口不寫隱藏地點名，指向已知的鄰近地點。"""
    world_map = library.world_maps["cloud_ridge"]
    hidden = [loc.name_zh for loc in world_map.locations if loc.hidden]
    table = library.world_quests.quests["cloud_ridge"]
    texts = [q.summary_zh for q in table.quests]
    texts += [s.text_zh for q in table.quests for s in q.steps]
    social = library.world_quests.social["cloud_ridge"]
    texts += [t.text_zh for t in social.talk if t.kind == "quest_entry"]
    for text in texts:
        for name in hidden:
            assert name not in text, (name, text)
    elixir = table.quest_by_id()["hidden_elixir_cave"]
    assert "藥師谷的谷底" in elixir.summary_zh


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "abandon", "threads": ["x"]},
        {"kind": "situation", "attributes": ["wis"], "threads": ["x"]},
        {"kind": "combat", "cost_supplies": 1},
        {"kind": "combat", "waive_thread": "x"},
        {"kind": "parley", "threads": ["x", "x"]},
        {"kind": "parley", "threads": ["a", "b", "c"]},
    ],
)
def test_bad_solution_fields(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SolutionDef.model_validate(data)


def test_solution_threads_must_be_own_or_shared() -> None:
    with pytest.raises(ValidationError, match="不是本骨架的線頭"):
        EventSkeletonDef.model_validate(
            _skeleton(solutions=[{"kind": "combat", "threads": ["elsewhere"]}])
        )
    ok = EventSkeletonDef.model_validate(
        _skeleton(
            solutions=[{"kind": "combat", "threads": ["elsewhere"]}], shared_threads=["elsewhere"]
        )
    )
    assert ok.result_threads() == {"elsewhere"}
    with pytest.raises(ValidationError, match="shared_threads 不可列自己的線頭"):
        EventSkeletonDef.model_validate(
            _skeleton(threads=[{"id": "mine", "text_zh": "x"}], shared_threads=["mine"])
        )


def test_unknown_shared_and_waive_threads(library: ContentLibrary) -> None:
    bad = _skeleton(
        shared_threads=["no_thread"],
        solutions=[{"kind": "parley", "waive_thread": "nope"}],
    )
    problems = _problems(library, _table(bad))
    assert any("shared_threads 是未知的線頭 no_thread" in p for p in problems)
    assert any("waive_thread 是未知的線頭 nope" in p for p in problems)


def test_offer_reward_schema() -> None:
    SkillOfferReward.model_validate(
        {"kind": "whiteboard", "mix": {"deepen": 1, "bridge": 0, "new": 2}}
    )
    with pytest.raises(ValidationError, match="合計"):
        SkillOfferReward.model_validate({"kind": "whiteboard", "mix": {"deepen": 1, "new": 2}})
    with pytest.raises(ValidationError, match="只有白板"):
        SkillOfferReward.model_validate({"kind": "complete", "min_passive": 1})


def test_talk_entry_unlocks_only_secret(library: ContentLibrary) -> None:
    with pytest.raises(ValidationError, match="只有 secret"):
        TalkEntry.model_validate(
            {
                "id": "x",
                "npc": "granny_du",
                "rank": "neutral",
                "kind": "rumor",
                "text_zh": "x",
                "unlocks_skeleton": "granny_past",
            }
        )
    social = SocialTable.model_validate(
        {
            "region": "cloud_ridge",
            "talk": [
                {
                    "id": "x",
                    "npc": "granny_du",
                    "rank": "trusted",
                    "kind": "secret",
                    "text_zh": "x",
                    "unlocks_skeleton": "wounded_peddler",
                }
            ],
        }
    )
    problems = social_problems(social, _refs_of(library), None)
    assert any("不是本區只能解鎖" in p for p in problems)


@pytest.mark.parametrize(
    ("step", "match"),
    [
        ({"kind": "win_battle", "skill_keywords": ["healing"]}, "未知關鍵字 healing"),
        ({"kind": "flag", "flag": "x"}, None),
        ({"kind": "growth", "ops": ["flash"]}, None),
        ({"kind": "win_battle", "weather": ["fog"], "group": "temple_traitor"}, None),
    ],
)
def test_new_conditions(library: ContentLibrary, step: dict[str, Any], match: str | None) -> None:
    quest = _quest(steps=[{"id": "s", "text_zh": "x", "when": [step]}])
    problems = _quest_problems(library, quest)
    if match is None:
        assert problems == []
    else:
        assert any(match in p for p in problems)


def test_step_npcs_and_region_keywords_checked(library: ContentLibrary) -> None:
    quest = _quest(
        steps=[
            {
                "id": "s",
                "text_zh": "x",
                "when": [{"kind": "at_location", "location": "ferry_steps"}],
                "npcs": ["nobody"],
            }
        ]
    )
    problems = _quest_problems(library, quest, region_keywords=["healing"])
    assert any("未知 NPC nobody" in p for p in problems)
    assert any("region_keywords：未知關鍵字 healing" in p for p in problems)


def test_growth_needs_ops() -> None:
    with pytest.raises(ValidationError):
        _quest_problems(
            load_library(),
            _quest(steps=[{"id": "s", "text_zh": "x", "when": [{"kind": "growth", "ops": []}]}]),
        )


def test_encounter_variant_checks(library: ContentLibrary) -> None:
    table = library.world_encounters["cloud_ridge"]
    data = table.model_dump()
    for loc in data["locations"]:
        if loc["location"] == "ferry_steps":
            loc["variants"] = [
                {"flag": "f1", "group": "nothing"},
                {
                    "flag": "f2",
                    "group": "bandit_raiders",
                    "elite": {"unit": "mist_wolf", "affix": "nope"},
                },
            ]
    problems = encounter_table_problems(
        EncounterTable.model_validate(data),
        world_map=library.world_maps["cloud_ridge"],
        catalog=library.enemy_catalog(),
    )
    assert any("未知的陣容 nothing" in p for p in problems)
    assert any("f2" in p for p in problems)
