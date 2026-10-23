"""說明整修 3-41a（清單第 2～5 節）：關鍵字分級、標籤中文名、對象後綴、護盾量、狀態與層數、詞條。"""

from __future__ import annotations

import re

import pytest

from tests.engine.helpers import library
from trpg.api.glossary import build_glossary
from trpg.content.affix_names import resolve_affix_name
from trpg.content.equipment import AffixTable
from trpg.content.loader import default_content_dir, load_content_file
from trpg.narrative.skills import skill_card
from trpg.narrative.status_info import stack_rules, status_rules


def _card(skill_id: str):  # type: ignore[no-untyped-def]
    lib = library()
    return skill_card(lib, lib.skills[skill_id])


# --- 2 關鍵字標籤 ------------------------------------------------------------------------------


def test_general_keywords_are_marked_with_a_reason_and_provisional_ones_hidden() -> None:
    """清單 2.1、2.2：通用歸類標 ``general`` 附理由；只由暫定規則推導的不顯示。"""
    cleave = _card("skill_cleave").keywords
    [prone] = [k for k in cleave.uses if k.id == "prone"]
    assert prone.general and prone.reason_zh == "近戰攻擊倒地的目標有優勢"
    assert _card("skill_attack_mastery").keywords.makes == ()  # 只有暫定：不顯示
    assert all(k.id != "collision" for k in _card("skill_bulwark_stance").keywords.uses)
    skeleton = _card("skill_raise_skeleton").keywords
    assert {k.id for k in skeleton.makes} == {"prone", "summon"}
    assert not any(k.general for k in skeleton.makes)


def test_general_rules_need_a_reason() -> None:
    lib = library()
    for keyword in lib.keywords.keywords:
        for rule in (*keyword.makes, *keyword.uses):
            assert (rule.grade == "general") == (rule.reason_zh is not None)


# --- 3 技能卡句子 ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("skill_id", "expected"),
    [
        ("skill_arc_follow_up", "若本回合已施放過帶「雷電」標籤的技能"),
        ("skill_hunt_sigil", "刻下你專屬的「獵紋」"),
        ("skill_overcurrent", "你帶「過載」標籤的技能每層傷害"),
        ("skill_beam_of_mercy", "帶「治療」標籤的技能："),
        ("skill_burning_shove", "帶「推擊」／「控制」標籤的技能："),
        ("skill_lingering_roar", "帶「吶喊」／「範圍」標籤的技能："),
        ("skill_summon_elite", "帶「召喚」標籤的技能："),
        ("skill_ember_ward", "觸發時機：施放帶「火焰」標籤的技能後"),
        ("skill_twin_strike", "觸發時機：每命中 2 次"),
    ],
)
def test_tags_and_runes_use_chinese_names(skill_id: str, expected: str) -> None:
    """清單 3.1～3.4。"""
    card = _card(skill_id)
    texts = [*card.effects, *card.modifiers, card.timing or "", card.condition or ""]
    assert any(expected in t for t in texts), texts


def test_target_suffix_sits_on_the_damage_sentence() -> None:
    """清單 3.5：對象後綴接在傷害句後面；獻祭、放逐、陷阱不加後綴。"""
    [harvest] = _card("skill_ash_harvest").effects
    assert re.match(r"^3d6＋智力加成的火焰傷害（敵方），若這一招讓敵人倒下", harvest)
    assert not _card("skill_glacier_offering").effects[0].endswith("（友方）")
    assert not _card("skill_banish").effects[0].endswith("（自己）")
    assert not _card("skill_bear_trap").effects[0].endswith("（自己）")


def test_shield_cleanse_and_default_durations() -> None:
    """清單 3.6、3.7：護盾寫吸收量；淨化寫移除什麼；沒寫回合數的狀態用預設。"""
    shield = _card("skill_charged_cleave").effects[0]
    assert shield.startswith("護盾（吸收量 1d4＋武器屬性加成，持續 2 回合")
    purify = _card("skill_purify").effects
    assert purify[0].startswith("淨化：移除身上所有不利的狀態")
    assert purify[1] == "狀態「守護」（到帶有者的下回合開始）（友方）"
    assert _card("skill_tailwind").effects[0] == "狀態「加速」 2 回合（友方）"
    assert _card("skill_fury_stance").effects[0] == "狀態「狂怒姿態」（持續到取消）（自己）"


# --- 4 狀態 ----------------------------------------------------------------------------------


def test_status_rules_come_from_the_status_table() -> None:
    """清單 4.1～4.4：抵抗屬性、控制遞減、Boss 轉換、持續傷害骰值、破甲依武器。"""
    lib = library()
    rules = lib.ruleset
    slow = status_rules(rules.status_def("slow"), lib)
    assert any("目標以敏捷對抗" in line for line in slow)
    assert any(line.startswith("控制遞減（移動類）") and "×1.5" in line for line in slow)
    stun = status_rules(rules.status_def("stun"), lib)
    assert stun[-1] == "對 Boss：改為施加「緩速」（持續時間不變）"
    burning = rules.status_def("burning")
    assert status_rules(burning, lib)[0] == "回合開始時受到 1d6 火焰傷害"
    assert not re.search(r"\d", burning.description_zh)
    assert status_rules(rules.status_def("armor_broken"), lib) == (
        "防禦值降低的幅度依武器：斧 10%（1 回合）",
    )
    for status in rules.statuses.statuses:
        assert not re.search(r"[A-Za-z_]{3,}", status.description_zh.replace("Boss", ""))


def test_glossary_carries_status_and_stack_rules() -> None:
    glossary = build_glossary(library())
    frozen = next(s for s in glossary.statuses if s.id == "frozen")
    assert "受到火焰傷害時立即解除" in frozen.rules_zh
    surge = next(s for s in glossary.stacks if s.id == "overload_surge")
    assert "overcurrent" not in (surge.description_zh or "")
    assert any("帶「過載」標籤" in line for line in surge.rules_zh)


def test_stack_cap_depends_on_the_source() -> None:
    """清單 5.5、5.6：層數說明寫「上限依來源」，不點名特定技能。"""
    lib = library()
    static = lib.ruleset.stack_def("static_charge")
    assert stack_rules(static, lib)[0].startswith("上限依來源")
    assert "雷霆終結" not in static.description_zh


# --- 5 裝備詞條 ------------------------------------------------------------------------------


def test_affix_names_fill_numbers_and_names_from_fields() -> None:
    """清單 5.1～5.4、7.1 的詞條名：數字與名稱由欄位填，規則改變類和技能卡同一句。"""
    affixes = library().affixes
    assert affixes["affix_charge_fury"].name_zh == (
        "受傷時累積 1 層怒氣（上限 4）；花 4 層：獲得「激昂」1 回合"
    )
    assert affixes["affix_charge_static"].name_zh.endswith("對目標造成 3d6 雷電傷害")
    assert affixes["affix_rule_bleeding_wake"].name_zh == (
        "規則改變「血痕」：你步行經過敵人的相鄰格時，對他施加「流血」2 回合（每次移動每個敵人一次）"
    )
    assert affixes["affix_cost_blood"].name_zh == "回合開始時失去 2 HP（不會致死）；技能冷卻 −1"
    assert affixes["affix_trig_summon_blast"].name_zh.startswith(
        "召喚物倒下時：原地爆炸，對 1 格內的敵人造成 1d8 火焰傷害"
    )
    assert (
        affixes["affix_act_grapple"].name_zh
        == "解鎖「鉤爪」：1 AP、冷卻 3，把 4 格內的目標拉近 2 格"
    )
    assert affixes["affix_kw_shock_area"].name_zh == "雷電技能範圍 +1"
    assert affixes["affix_trait_longgun_pointblank"].name_zh == "火槍的貼臉懲罰減半"
    assert all(
        "長槍" not in a.name_zh and "{" not in a.name_zh.replace("{n}", "")
        for a in affixes.values()
    )


def test_affix_template_follows_the_data() -> None:
    """改資料時文字跟著變：同一個模板換掉欄位值，代入的數字也跟著換。"""
    lib = library()
    raw = load_content_file(default_content_dir() / "affixes.yaml", AffixTable).by_id()
    static = raw["affix_charge_static"].model_copy(update={"max_stacks": 4, "cost_stacks": 4})
    assert "（上限 4）；花 4 層" in resolve_affix_name(static, lib.ruleset).name_zh
    broken = raw["affix_kw_shock_area"].model_copy(update={"name_zh": "範圍 +{nope}"})
    with pytest.raises(ValueError, match="不認得的欄位"):
        resolve_affix_name(broken, lib.ruleset)
