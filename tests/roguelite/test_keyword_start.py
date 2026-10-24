"""新開局：起始武器 ＋ 2 個關鍵字、開發者起始包、行為紀錄（Phase 3-24b2，06 6.27.3、6.27.6）。"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from tests.roguelite.helpers import library
from trpg.content.skills import weapon_problem
from trpg.engine.actions import EndTurn, Move, Shove, Step, Trip
from trpg.roguelite import (
    ChoiceError,
    RunSave,
    auto_play,
    dumps_save,
    loads_save,
    new_dev_run,
    new_keyword_run,
)
from trpg.roguelite.progress import add_behavior
from trpg.roguelite.start import (
    default_start,
    start_weapons,
    starter_pools,
    starting_skill,
)
from trpg.roguelite.state import LevelUpNode
from trpg.shared.types import Attribute, Pos, UnitId
from trpg.skillgen.keywords import is_starter_skill, pool_skills


def test_every_weapon_is_offered() -> None:
    lib = library()
    assert start_weapons(lib) == tuple(
        sorted(w for w, d in lib.weapons.items() if not d.summon_only)
    )
    assert {"one_handed_sword", "longgun", "totem_staff", "scepter"} <= set(start_weapons(lib))


def test_starter_pools_use_exclusive_rules_and_have_three_each() -> None:
    """PM 決定：開局技能池只看專屬規則；每池至少 3 招 1 階起始技能。"""
    lib = library()
    pools = starter_pools(lib)
    assert set(pools) == set(lib.keywords.ids())
    for keyword, ids in pools.items():
        if keyword == "poisoned":
            # 3-53：中毒池只有 1 招起始技能（荊棘牆），等 3-54c 毒種子技能補；補齊後刪掉例外。
            assert len(ids) == 1, keyword
        else:
            assert len(ids) >= 3, keyword
        assert all(is_starter_skill(lib.skills[i]) for i in ids)
    assert "skill_cleave" not in pools["prone"]  # 近戰武器技只靠通用規則利用倒地


def test_keyword_start_is_deterministic_and_gives_one_skill_per_pool() -> None:
    lib = library()
    pools = starter_pools(lib)
    run = new_keyword_run(lib, "fire_staff", ("ignite", "marked"), 7)
    assert run == new_keyword_run(lib, "fire_staff", ("ignite", "marked"), 7)
    assert run.start is not None and run.build_id is None
    assert run.start.weapon == "fire_staff" and run.start.keywords == ("ignite", "marked")
    first, second = run.hero.skills
    assert first in pools["ignite"] and second in pools["marked"] and first != second
    assert run.hero.weapon == "fire_staff" and run.level == 1
    assert run.hero.attributes[Attribute.INT] == 14  # 預設配點：武器的縮放屬性
    assert run.hp == run.max_hp_in(lib.ruleset.core) and run.mana == run.max_mana_in(
        lib.ruleset.core
    )
    seeds = {
        new_keyword_run(lib, "fire_staff", ("ignite", "marked"), s).hero.skills for s in range(12)
    }
    assert len(seeds) > 1


def test_every_keyword_pool_gives_a_starter_for_some_weapon() -> None:
    """各池給招：每個（武器, 關鍵字）組合，給的技能都在該池裡、與武器相容、可當起始技能；
    湊不到時為 None（前端標成不可選）。每個關鍵字至少有一把武器拿得到。"""
    lib = library()
    pools = starter_pools(lib)
    reachable: dict[str, int] = dict.fromkeys(lib.keywords.ids(), 0)
    for weapon in start_weapons(lib):
        weapon_class = lib.weapons[weapon].weapon_class
        for keyword in lib.keywords.ids():
            skill = starting_skill(lib, weapon, keyword, 3, pools=pools)
            if skill is None:
                continue
            reachable[keyword] += 1
            held = {weapon: lib.weapons[weapon].name_zh}
            assert weapon_problem(skill, weapon_class, held) is None  # 含限定武器（3I-5）
            assert is_starter_skill(skill)
            if skill.id in lib.skills:
                assert skill.id in pools[keyword]
    assert all(n > 0 for n in reachable.values()), reachable


def test_second_keyword_never_repeats_the_first_skill() -> None:
    lib = library()
    for seed in range(10):
        run = new_keyword_run(lib, "lightning_staff", ("wet", "charged"), seed)
        assert len(set(run.hero.skills)) == 2


@pytest.mark.parametrize(
    ("weapon", "keywords", "match"),
    [
        ("fire_staff", ("ignite",), "2 個不同"),
        ("fire_staff", ("ignite", "ignite"), "2 個不同"),
        ("fire_staff", ("ignite", "nope"), "未知的關鍵字"),
        ("nope", ("ignite", "marked"), "未知的武器"),
    ],
)
def test_bad_starts_are_rejected(weapon: str, keywords: tuple[str, ...], match: str) -> None:
    with pytest.raises(ChoiceError, match=match):
        new_keyword_run(library(), weapon, keywords, 1)


def test_bow_can_start_with_wet_thanks_to_any_weapon_skills() -> None:
    """3-24c 4b：不限武器的潮濕 1 階技能讓遠程開局也能選潮濕。"""
    run = new_keyword_run(library(), "bow", ("wet", "marked"), 1)
    assert len(set(run.hero.skills)) == 2


def test_a_pool_without_compatible_starters_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # 組合器碰巧能做出弓用的潮濕技能時結果會隨種子變動：這裡只測「池裡沒有」的路徑
    monkeypatch.setattr("trpg.roguelite.start._composed_starter", lambda *args, **kw: None)
    lib = library()
    starters = {s.id for s in pool_skills(lib, "wet", exclusive_only=True)}
    kept = {i: s for i, s in lib.skills.items() if i not in starters or s.weapon_req == "focus"}
    poor = replace(lib, skills=kept)
    with pytest.raises(ChoiceError, match="沒有弓能用的起始技能"):
        new_keyword_run(poor, "bow", ("wet", "marked"), 1)


def test_allocation_is_checked() -> None:
    with pytest.raises(ChoiceError, match="必須分配"):
        new_keyword_run(library(), "bow", ("marked", "ignite"), 1, {Attribute.DEX: 1})
    run = new_keyword_run(library(), "bow", ("marked", "ignite"), 1, {Attribute.CON: 4})
    assert run.hero.attributes[Attribute.CON] == 14


def test_dev_packs_all_start_and_stay_out_of_the_player_start() -> None:
    lib = library()
    packs = lib.dev_starters.packs
    assert len(packs) == 28
    labels = {p.label_zh for p in packs}
    assert labels == {"烈焰", "潮雷", "霜寒", "撼地", "鐵壁", "影刃"} | {
        "鷹眼",
        "聖光",
        "喚靈",
        "機關",
        "念動",
        "血怒",
        "喚靈（保證召喚）",  # 3-33b：指定起始技能的對照組
        "喚靈（骷髏）",
        # 3-33e1：召喚物（一）的對照組
        "火靈包",
        "冰靈包",
        "雷靈包",
        "水精包",
        "影魅包",
        "鷹隼包",
        # 3-33e2a：構造體與野獸
        "傀儡包",
        "石像包",
        "土牆包",
        "戰狼包",
        # 3-33e2b
        "藤蔓包",
        "守護靈包",
        "吸引圖騰包",
        "高台圖騰包",
    }
    for pack in packs:
        run = new_dev_run(lib, pack.id, 0)
        assert run.start is not None and run.start.dev_pack == pack.id
        assert run.start.keywords == pack.keywords and run.hero.weapon == pack.weapon
        assert len(run.hero.skills) == 2
        # 一般開局同樣的武器與關鍵字得到同樣的主角（起始包只是捷徑）
        plain = new_keyword_run(lib, pack.weapon, pack.keywords, 0)
        if pack.skills:  # 指定起始技能的對照組：技能固定，其餘（武器、關鍵字）同一般開局
            assert run.hero.skills == pack.skills
        else:
            assert plain.hero == run.hero
        # 主角名稱沒有流派名
        assert all(label not in run.hero.name_zh for label in labels)
    with pytest.raises(ChoiceError, match="未知的開發者起始包"):
        new_dev_run(lib, "dev_nobody", 0)


def test_dev_pack_with_fixed_skills_is_validated() -> None:
    lib = library()
    pack = lib.dev_starters.by_id()["dev_blaze"]
    fixed = pack.model_copy(update={"skills": ("skill_fire_bolt", "skill_hex_bolt")})
    run = new_keyword_run(lib, fixed.weapon, fixed.keywords, 0, skills=fixed.skills)
    assert run.hero.skills == ("skill_fire_bolt", "skill_hex_bolt")
    with pytest.raises(ChoiceError, match="不在"):
        new_keyword_run(lib, fixed.weapon, fixed.keywords, 0, skills=("skill_hex_bolt",) * 2)


def test_default_start_is_deterministic_and_valid() -> None:
    lib = library()
    seen = set()
    for seed in range(20):
        weapon, keywords = default_start(lib, seed)
        assert (weapon, keywords) == default_start(lib, seed)
        new_keyword_run(lib, weapon, keywords, seed)  # 不會拋出
        seen.add(weapon)
    assert len(seen) > 3


def test_behavior_counts_the_heros_actions() -> None:
    hero, other = UnitId("u1"), UnitId("u2")
    steps: list[Step] = [
        Move(unit_id=hero, path=(Pos(x=0, y=0), Pos(x=0, y=1))),
        Shove(unit_id=hero, target_id=other),
        Trip(unit_id=other, target_id=hero),
        EndTurn(unit_id=hero),
    ]
    assert add_behavior({"shove": 2}, steps, hero) == {"move": 1, "shove": 3}


def test_a_keyword_run_plays_and_records_behavior_and_offer_tags() -> None:
    lib = library()
    run = new_keyword_run(
        lib, "one_handed_sword", ("prone", "collision"), 1
    )  # 3-33e2a 合併：種子 2 的提案換成召喚技，改 1

    def stop(r: object, battle: object) -> bool:
        return isinstance(getattr(r, "node", None), LevelUpNode)

    leveled, _ = auto_play(lib, run, stop=stop)
    assert isinstance(leveled.node, LevelUpNode)
    assert leveled.behavior and all(v > 0 for v in leveled.behavior.values())
    assert "end_turn" not in leveled.behavior
    offer = leveled.node.offer
    assert [t.kind for t in offer.tags] == ["deepen", "bridge", "new"]
    assert offer.tags[0].keywords[0] in ("prone", "collision")
    # 存檔來回一致（trpg-run/6）
    again = loads_save(dumps_save(RunSave(run_id="k", run=leveled))).run
    assert again == leveled
    raw = json.loads(dumps_save(RunSave(run_id="k", run=leveled)))
    assert raw["format"] == "trpg-run/6" and raw["run"]["start"]["weapon"] == "one_handed_sword"
