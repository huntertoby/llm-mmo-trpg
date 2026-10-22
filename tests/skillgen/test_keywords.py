"""關鍵字推導、技能池與組合器指定關鍵字（Phase 3-24b1，``docs/design/06-技能.md`` 6.27）。"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.engine.helpers import library
from tests.skillgen.workshop_walks import MODIFIER, STRIKE, walk_draft
from trpg.content.library import load_library
from trpg.content.skill_keywords import KeywordRule
from trpg.content.skills import SkillDef
from trpg.engine.actions import BASIC_ACTION_TYPES
from trpg.narrative.skills import draft_card_keywords, skill_card
from trpg.shared.errors import ContentError
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.keywords import (
    derive_draft_keywords,
    derive_keywords,
    is_starter_skill,
    keyword_pools,
    pool_skills,
    skills_without_keywords,
)
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill

KEYWORDS = (
    "ignite",
    "wet",
    "charged",
    "frozen",
    "prone",
    "collision",
    "marked",
    "high_ground",
    "concealed",
    "summon",
)
NAMES = ("點燃", "潮濕", "帶電", "冰凍", "倒地", "撞擊", "標記", "高處", "隱蔽", "召喚物")


def _skill(**fields: Any) -> SkillDef:
    """測試用主動技能骨架（不經過驗證器）；``effects``／``condition`` 等欄位由呼叫端給。"""
    data: dict[str, Any] = {
        "id": "skill_t_kw",
        "name_zh": "測試",
        "tier": 1,
        "rarity": "rare",
        "kind": "active",
        "skeleton": "strike",
        "category": "spell",
        "weapon_req": "focus",
        "ap_cost": 1,
        "scaling_attr": "int",
        "shape": {"type": "single", "range": 4},
        "effects": [{"type": "damage", "dice": "1d6", "element": "physical"}],
    }
    data.update(fields)
    return SkillDef.model_validate(data)


def _keywords(**fields: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    found = derive_keywords(_skill(**fields), library().keywords)
    return found.makes, found.uses


# ---------------------------------------------------------------------------
# 推導表本身
# ---------------------------------------------------------------------------


def test_table_has_the_ten_keywords_in_order() -> None:
    table = library().keywords
    assert table.ids() == KEYWORDS
    assert tuple(k.name_zh for k in table.keywords) == NAMES


def test_no_keyword_is_a_school_or_theme() -> None:
    """遊戲不定義流派：推導表與介面文字裡沒有任何流派名稱。"""
    schools = (
        "烈焰",
        "潮雷",
        "霜寒",
        "撼地",
        "鐵壁",
        "影刃",
        "鷹眼",
        "聖光",
        "喚靈",
        "機關",
        "念動",
        "血怒",
    )
    blob = Path(library().root / "skill_keywords.yaml").read_text(encoding="utf-8")
    body = "\n".join(line.split("#", 1)[0] for line in blob.splitlines())
    assert not [s for s in schools if s in body]


# (關鍵字, 製造或利用, 技能欄位, 預期) 的正例與反例：每個關鍵字至少一個製造正例與一個利用正例
POSITIVE: list[tuple[str, str, dict[str, Any]]] = [
    (
        "ignite",
        "makes",
        {"effects": [{"type": "apply_status", "status": "burning", "duration": 1}]},
    ),
    ("ignite", "makes", {"effects": [{"type": "damage", "dice": "1d6", "element": "fire"}]}),
    ("ignite", "makes", {"effects": [{"type": "create_surface", "surface": "oil"}]}),
    (
        "ignite",
        "uses",
        {
            "effects": [
                {
                    "type": "damage",
                    "dice": "1d6",
                    "element": "physical",
                    "condition": {"type": "target_has_status", "status": "burning"},
                }
            ]
        },
    ),
    (
        "ignite",
        "uses",
        {
            "effects": [
                {
                    "type": "consume_status",
                    "status": "burning",
                    "then": [{"type": "damage", "dice": "2d6", "element": "fire"}],
                }
            ]
        },
    ),
    ("wet", "makes", {"effects": [{"type": "create_surface", "surface": "water"}]}),
    (
        "wet",
        "uses",
        {
            "effects": [
                {
                    "type": "damage",
                    "dice": "1d6",
                    "element": "physical",
                    "condition": {"type": "target_on_surface", "surface": "water"},
                }
            ]
        },
    ),
    ("charged", "makes", {"effects": [{"type": "damage", "dice": "1d6", "element": "lightning"}]}),
    ("charged", "uses", {"shape": {"type": "chain", "range": 4, "jumps": 2, "jump_range": 2}}),
    ("frozen", "makes", {"effects": [{"type": "apply_status", "status": "frozen", "duration": 1}]}),
    ("frozen", "makes", {"effects": [{"type": "create_surface", "surface": "ice"}]}),
    (
        "frozen",
        "uses",
        {"condition": {"type": "target_has_status", "status": "frozen"}},
    ),
    ("prone", "makes", {"effects": [{"type": "knock_prone"}]}),
    ("prone", "makes", {"effects": [{"type": "topple"}], "shape": {"type": "single", "range": 3}}),
    (
        "prone",
        "uses",
        {
            "effects": [
                {
                    "type": "damage",
                    "dice": "1d6",
                    "element": "physical",
                    "condition": {"type": "target_has_status", "status": "prone"},
                }
            ]
        },
    ),
    ("collision", "makes", {"effects": [{"type": "push", "distance": 1}]}),
    ("collision", "makes", {"effects": [{"type": "pull", "distance": 1}]}),
    (
        "collision",
        "uses",
        {
            "kind": "passive",
            "skeleton": "passive",
            "ap_cost": None,
            "shape": {"type": "self"},
            "trigger": {"event": "on_collision", "target": "other"},
            "effects": [{"type": "apply_status", "status": "bleed", "affects": "enemies"}],
        },
    ),
    ("marked", "makes", {"effects": [{"type": "apply_status", "status": "marked", "duration": 1}]}),
    ("marked", "makes", {"effects": [{"type": "reveal", "duration": 2}]}),
    ("marked", "uses", {"condition": {"type": "target_has_status", "status": "marked"}}),
    ("marked", "uses", {"effects": [{"type": "detonate_runes", "dice": "2d6", "element": "fire"}]}),
    ("high_ground", "makes", {"effects": [{"type": "raise_terrain"}]}),
    ("high_ground", "uses", {"condition": {"type": "height_advantage"}}),
    (
        "concealed",
        "makes",
        {"effects": [{"type": "apply_status", "status": "concealed", "affects": "self"}]},
    ),
    ("concealed", "makes", {"effects": [{"type": "create_surface", "surface": "smoke"}]}),
    ("concealed", "uses", {"condition": {"type": "self_concealed"}}),
    (
        "summon",
        "makes",
        {
            "shape": {"type": "ground_tile", "range": 4},
            "effects": [{"type": "summon", "unit": "summon_skeleton_warrior", "duration": 2}],
        },
    ),
    ("summon", "uses", {"condition": {"type": "adjacent_ally"}}),
]


@pytest.mark.parametrize(
    ("keyword", "role", "fields"),
    POSITIVE,
    ids=[f"{k}-{r}-{i}" for i, (k, r, _) in enumerate(POSITIVE)],
)
def test_derivation_positive_examples(keyword: str, role: str, fields: dict[str, Any]) -> None:
    found = derive_keywords(_skill(**fields), library().keywords)
    assert keyword in getattr(found, role)


def test_every_keyword_has_a_positive_example_for_makes_and_uses() -> None:
    covered = {(k, r) for k, r, _ in POSITIVE}
    for keyword in KEYWORDS:
        assert (keyword, "makes") in covered and (keyword, "uses") in covered, keyword


def test_every_keyword_is_made_and_used_by_shipped_skills() -> None:
    lib = library()
    seen: dict[str, set[str]] = {k: set() for k in KEYWORDS}
    for skill in lib.skills.values():
        found = derive_keywords(skill, lib.keywords)
        for k in found.makes:
            seen[k].add("makes")
        for k in found.uses:
            seen[k].add("uses")
    assert all(roles == {"makes", "uses"} for roles in seen.values()), seen


def test_plain_physical_damage_has_no_keyword() -> None:
    """反例：沒有元素、狀態、條件的法術傷害不製造也不利用任何關鍵字。"""
    assert _keywords() == ((), ())


def test_weapon_skills_use_prone_or_high_ground_by_their_weapon() -> None:
    """近戰武器傷害技利用倒地（近戰打倒地者有優勢）、遠程武器傷害技利用高處（高打低命中 +2）。"""
    melee = _keywords(
        category="weapon",
        weapon_req="melee",
        scaling_attr="str",
        effects=[{"type": "damage", "multiplier_permille": 1000}],
    )
    ranged = _keywords(
        category="weapon",
        weapon_req="ranged",
        scaling_attr="dex",
        effects=[{"type": "damage", "multiplier_permille": 1000}],
    )
    assert melee == ((), ("prone",))
    assert ranged == ((), ("high_ground",))


def test_modifier_rules_are_read_too() -> None:
    lib = library()
    fire = lib.skills["skill_burning_shove"]
    assert derive_keywords(fire, lib.keywords).makes == ("ignite",)
    scar = lib.skills["skill_searing_scar"]  # 對燃燒中目標傷害 +10%
    assert derive_keywords(scar, lib.keywords).uses == ("ignite",)
    avatar = lib.skills["skill_war_avatar"]  # 無條件的 damage_permille 不會被有條件的規則誤判
    assert derive_keywords(avatar, lib.keywords).uses == ()
    assert derive_keywords(avatar, lib.keywords).makes == ("marked",)


def test_derivation_is_deterministic_and_ordered_by_the_table() -> None:
    lib = library()
    skill = lib.skills["skill_ember_trail"]  # 火印：點燃＋標記
    first = derive_keywords(skill, lib.keywords)
    assert first == derive_keywords(skill, lib.keywords)
    assert first.makes == ("ignite", "marked")  # 依推導表的順序，不依規則出現順序


# ---------------------------------------------------------------------------
# 每招技能至少一個關鍵字
# ---------------------------------------------------------------------------


def test_every_shipped_skill_has_at_least_one_keyword() -> None:
    lib = library()
    missing = skills_without_keywords(lib.skills.values(), lib.keywords)
    assert [s.id for s in missing] == []


def test_every_shipped_skill_passes_the_validator_including_keywords() -> None:
    lib = library()
    bad = {s.id: validate_skill(s, lib) for s in lib.skills.values()}
    assert {k: v for k, v in bad.items() if v} == {}


@pytest.mark.parametrize("seed", range(50))
def test_composer_seeds_0_to_49_all_have_a_keyword(seed: int) -> None:
    lib = library()
    skill = compose_random_skill(seed, library=lib)
    assert derive_keywords(skill, lib.keywords)
    assert validate_skill(skill, lib) == []


def test_a_keywordless_skill_is_rejected_by_the_validator() -> None:
    lib = library()
    plain = _skill(
        id="skill_t_plain",
        cost={"mana": 6},
        effects=[{"type": "damage", "dice": "2d6", "element": "physical"}],
    )
    rules = {v.rule for v in validate_skill(plain, lib)}
    assert "keyword.required" in rules


def test_workshop_marks_a_keywordless_complete_draft_illegal() -> None:
    lib = library()
    draft = walk_draft(STRIKE)
    ok = check_draft(draft, lib)
    assert ok.legal, ok.problems  # 擊倒製造倒地、近戰武器技利用倒地
    plain = copy.deepcopy(draft)
    plain["category"], plain["weapon_req"] = "spell", "focus"
    plain["scaling_attr"] = "int"
    plain["effects"] = [{"type": "damage", "dice": "2d6", "element": "physical"}]
    result = check_draft(plain, lib)
    assert not result.legal
    assert any(p.rule == "keyword.required" for p in result.problems)


def test_workshop_draft_keywords_appear_as_the_draft_grows() -> None:
    lib = library()
    keywords = lib.keywords
    assert not derive_draft_keywords({}, keywords)
    partial = {"skeleton": "strike", "shape": {"type": "single", "range": 4}}
    assert not derive_draft_keywords(partial, keywords)
    with_effects = {**partial, "effects": [{"type": "apply_status", "status": "burning"}]}
    assert derive_draft_keywords(with_effects, keywords).makes == ("ignite",)
    broken = {**partial, "effects": [{"type": "no_such"}, {"type": "knock_prone"}]}
    assert derive_draft_keywords(broken, keywords).makes == ("prone",)  # 解析不了的略過
    card = draft_card_keywords(lib, with_effects)
    assert [(k.id, k.name_zh) for k in card.makes] == [("ignite", "點燃")]
    modifier = walk_draft(MODIFIER)
    assert derive_draft_keywords(modifier, keywords).uses == ("ignite",)


def test_skill_card_carries_the_keywords_with_names() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_cinder_burst"])
    assert [k.name_zh for k in card.keywords.makes] == ["點燃"]
    assert [k.name_zh for k in card.keywords.uses] == ["點燃"]
    dump = card.model_dump(mode="json")
    [made] = dump["keywords"]["makes"]
    assert (made["id"], made["name_zh"]) == ("ignite", "點燃") and made["description_zh"]


# ---------------------------------------------------------------------------
# 技能池
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", KEYWORDS)
def test_each_pool_has_at_least_three_tier_one_starter_skills(keyword: str) -> None:
    lib = library()
    pool = pool_skills(lib, keyword)
    assert len(pool) >= 3, [s.id for s in pool]
    assert all(s.tier == 1 and s.rarity != "legendary" and is_starter_skill(s) for s in pool)
    for skill in pool:
        assert keyword in derive_keywords(skill, lib.keywords).all()
        assert validate_skill(skill, lib) == []  # 過預算


def test_a_skill_can_be_in_several_pools_and_the_pools_are_derived_not_listed() -> None:
    lib = library()
    pools = keyword_pools(lib)
    hex_bolt = "skill_hex_bolt"  # 暗影傷害＋標記：隱蔽池與標記池
    assert hex_bolt in pools["concealed"] and hex_bolt in pools["marked"]
    # 沒有任何地方手寫池的名單：每個池成員都能由推導重現
    for keyword, ids in pools.items():
        for skill_id in ids:
            assert keyword in derive_keywords(lib.skills[skill_id], lib.keywords).all()


def test_pool_listing_is_sorted_and_deterministic() -> None:
    lib = library()
    first = keyword_pools(lib, starter_only=True)
    assert first == keyword_pools(lib, starter_only=True)
    assert all(list(ids) == sorted(ids) for ids in first.values())


def test_added_pool_skills_exist_and_belong_to_the_expected_pools() -> None:
    lib = library()
    expected = {
        "skill_kindling_strike": "ignite",
        "skill_flash_freeze": "frozen",
        "skill_shatter_ice": "frozen",
        "skill_downpour": "wet",
        "skill_holy_water": "wet",
    }
    for skill_id, keyword in expected.items():
        assert skill_id in keyword_pools(lib, starter_only=True)[keyword]


# ---------------------------------------------------------------------------
# 組合器指定關鍵字
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", KEYWORDS)
def test_composer_can_require_each_keyword(keyword: str) -> None:
    lib = library()
    for seed in range(3):
        skill = compose_random_skill(seed, library=lib, keyword=keyword)
        assert keyword in derive_keywords(skill, lib.keywords).all()
        assert validate_skill(skill, lib) == []
        assert skill.id == f"skill_rand_{seed}" and skill.name_zh.endswith(f"#{seed}")


def test_composer_with_a_keyword_is_deterministic_and_leaves_plain_seeds_alone() -> None:
    first = compose_random_skill(7, keyword="marked")
    assert first == compose_random_skill(7, keyword="marked")
    assert compose_random_skill(7) == compose_random_skill(7, keyword=None)
    assert first.model_dump() != compose_random_skill(7, keyword="summon").model_dump()


def test_composer_rejects_an_unknown_keyword() -> None:
    with pytest.raises(ComposeError, match="未知的關鍵字"):
        compose_random_skill(1, keyword="no_such_keyword")


def test_composer_keyword_works_with_other_constraints() -> None:
    lib = library()
    skill = compose_random_skill(3, library=lib, keyword="ignite", tier=2, category="spell")
    assert skill.tier == 2 and skill.category == "spell"
    assert "ignite" in derive_keywords(skill, lib.keywords).all()


# ---------------------------------------------------------------------------
# 推導表的載入檢查
# ---------------------------------------------------------------------------


def _copy_content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(library().root, root)
    return root


def _edit_table(root: Path, edit: Any) -> None:
    path = root / "skill_keywords.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_a_rule_referencing_an_unknown_status_is_rejected(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    _edit_table(
        root,
        lambda d: d["keywords"][0]["makes"].append({"effect": "apply_status", "status": "no_such"}),
    )
    with pytest.raises(ContentError, match="未知的 status"):
        load_library(root)


def test_a_rule_referencing_an_unknown_primitive_is_rejected(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    _edit_table(root, lambda d: d["keywords"][1]["uses"].append({"effect": "no_such_primitive"}))
    with pytest.raises(ContentError, match="未知的effect"):
        load_library(root)


def test_a_rule_needs_exactly_one_source() -> None:
    with pytest.raises(ValueError, match="恰好指定一種來源"):
        KeywordRule.model_validate({"effect": "damage", "condition": "first_round"})
    with pytest.raises(ValueError, match="恰好指定一種來源"):
        KeywordRule.model_validate({"status": "burning"})


def test_duplicate_keyword_ids_are_rejected(tmp_path: Path) -> None:
    root = _copy_content(tmp_path)
    _edit_table(root, lambda d: d["keywords"].append(copy.deepcopy(d["keywords"][0])))
    with pytest.raises(ContentError, match="重複"):
        load_library(root)


# ---------------------------------------------------------------------------
# Phase 3-24b2：規則種類（專屬／通用／暫定）與只看專屬規則的推導
# ---------------------------------------------------------------------------


def test_rule_grades_are_data_and_match_the_comments() -> None:
    """推導表的「通用」「暫定」註解改成資料欄位 grade：行尾註解寫通用或暫定的規則都有對應的
    grade。"""
    text = (Path(library().root) / "skill_keywords.yaml").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- {"):
            continue
        if "# 通用" in stripped:
            assert "grade: general" in stripped, stripped
        if "# 暫定" in stripped:
            assert "grade: provisional" in stripped, stripped
    rules = [r for k in library().keywords.keywords for r in (*k.makes, *k.uses)]
    grades = {g: sum(1 for r in rules if r.grade == g) for g in ("general", "provisional")}
    assert grades == {"general": 26, "provisional": 16}


def test_exclusive_only_derivation_drops_general_and_provisional_rules() -> None:
    lib = library()
    cleave = lib.skills["skill_cleave"]  # 近戰武器技：只靠通用規則利用倒地
    assert "prone" in derive_keywords(cleave, lib.keywords).all()
    assert not derive_keywords(cleave, lib.keywords, exclusive_only=True)
    hush = lib.skills["skill_hush"]  # 沉默：暫定規則製造標記
    assert "marked" in derive_keywords(hush, lib.keywords).makes
    assert "marked" not in derive_keywords(hush, lib.keywords, exclusive_only=True).makes
    fire = lib.skills["skill_fire_bolt"]
    assert derive_keywords(fire, lib.keywords, exclusive_only=True) == derive_keywords(
        fire, lib.keywords
    )
    pools = keyword_pools(lib, starter_only=True, exclusive_only=True)
    assert all(len(ids) >= 3 for ids in pools.values())
    assert len(pools["prone"]) < len(keyword_pools(lib, starter_only=True)["prone"])


def test_keyword_actions_are_basic_actions() -> None:
    for keyword in library().keywords.keywords:
        assert set(keyword.actions) <= set(BASIC_ACTION_TYPES), keyword.id
    assert library().keywords.by_id()["high_ground"].actions == ("vault",)
