"""玩家看得到的檢查文字：把欄位名、ID、列舉值換成中文（3-48，玩法決定 #44：不露代號）。

``validate_skill`` 等規則檢查的訊息同時給 CLI、模擬與內容驗證用（開發者要看欄位名），所以不改來源，
在給工坊玩家看之前才過 :func:`plainify`：先換固定的片語與 pydantic 的英文訊息，
再把內容資料裡的 ID（骨架、效果原語、形狀、狀態、條件、關鍵字……）與列舉值換成中文名。
查不到的詞原樣保留（``tests/skillgen/test_player_text.py`` 掃過各種違規草稿，確認不再露出英文詞）。
"""

from __future__ import annotations

import re
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.shared.types import Attribute

__all__ = ["CHANGE_TEXT", "plain_name", "plainify"]

CHANGE_TEXT: dict[str, str] = {
    "damage_permille": "傷害 ±‰",
    "hit_bonus": "命中 ±",
    "cooldown_delta": "命中後冷卻 −1／−2",
    "push_distance_delta": "推擊距離 +1／+2",
    "ap_delta": "AP 成本 ±1",
    "range_delta": "射程 −1～＋2",
    "add_element": "傷害獲得元素",
    "add_tags": "技能獲得標籤",
    "on_hit_effects": "命中後附加效果",
    "grant_pierce": "獲得穿透",
    "area_delta": "範圍 +1",
    "shape_to": "形狀轉換",
    "allow_self_target": "範圍包含自己",
    "heal_permille": "治療量 ±‰",
    "summon_hp_permille": "召喚物最大 HP +‰",
    "summon_attack_dice": "召喚物攻擊 +1 顆傷害骰",
    "summon_limit_delta": "召喚物同時上限 ±1",
    "summon_duration_delta": "召喚物持續 +輪數",
    "summon_damage_permille": "召喚物傷害 +‰",
}

_INDEXED = re.compile(r"\b(effects|modifiers|variants)\[(\d+)\]")
_LIST_ZH = {"effects": "效果", "modifiers": "修正規則", "variants": "變奏"}
_WORD = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_MODIFIER = re.compile(r"\bmodifier\.([A-Za-z_]+)")
_VARIANT_PATH = re.compile(r"\bvariants\.[A-Za-z0-9_]+\.")

# 片語（含空白或標點，先換）
_PHRASES: tuple[tuple[str, str], ...] = (
    ("stance: true", "姿態狀態"),
    ("kind: stance", "姿態技能"),
    ("category:", "類別："),
    ("weapon_req:", "武器需求："),
    ("cost.source", "特殊代價"),
    ("trigger.target", "觸發對象"),
    ("Field required", "必填"),
    ("Input should be a valid integer", "必須是整數"),
    ("Input should be a valid string", "必須是文字"),
    ("Input should be a valid boolean", "必須是是／否"),
)
_PYDANTIC = (
    (re.compile(r"Input should be less than or equal to (\d+)"), r"不能大於 \1"),
    (re.compile(r"Input should be greater than or equal to (\d+)"), r"不能小於 \1"),
    (re.compile(r"Input should be less than (\d+)"), r"必須小於 \1"),
    (re.compile(r"Input should be greater than (\d+)"), r"必須大於 \1"),
    (re.compile(r"Input should be [^。；]*"), "不在可選範圍內"),
)
# 單字（欄位名與列舉值）
_WORDS_ZH = {
    "secondary_scaling_attr": "第二縮放屬性",
    "scaling_attr": "縮放屬性",
    "uses_per_battle": "每場次數",
    "weapon_req": "武器需求",
    "control_group": "控制類型",
    "ap_cost": "AP",
    "cooldown": "冷卻",
    "duration": "持續時間",
    "affects": "對象",
    "category": "類別",
    "skeleton": "骨架",
    "mastery": "專精",
    "element": "元素",
    "rounds": "輪數",
    "total": "點數",
    "shape": "形狀",
    "cost": "費用",
    "kind": "種類",
    "tier": "階級",
    "rarity": "稀有度",
    "variants": "變奏",
    "modifier": "修正",
    "problems": "問題清單",
    "beneficial": "有益",
    "harmful": "有害",
    "null": "空",
    "YAML": "YAML",
    "range": "射程",
    "replace_effect": "替換效果",
    "range_delta": "射程調整",
    "element_heals_allies": "元素治療友方",
    "push_any_object": "推動任何物件",
    "pass_through_apply": "經過時施加狀態",
    "on_downed_spawn": "倒下時生成分身",
    "self": "自己",
    "enemies": "敵方",
    "allies": "友方",
    "tiles": "格子",
    "melee": "近戰武器",
    "ranged": "遠程武器",
    "focus": "法器",
    "any": "任何武器",
    "weapon": "武器技",
    "spell": "法術技",
    "active": "主動技",
    "passive": "被動",
    "reaction": "反應技",
    "stance": "姿態",
    "common": "普通",
    "rare": "稀有",
    "epic": "史詩",
    "legendary": "傳說",
}


def _key(value: Any) -> str:
    return str(getattr(value, "value", value))


def _tables(library: ContentLibrary) -> dict[str, str]:
    """ID → 中文名：內容資料裡有 ``id`` 與 ``name_zh`` 的各種定義。後面的覆蓋前面的。"""
    rules = library.ruleset
    names: dict[str, str] = {}
    for attr in Attribute:
        names[attr.value] = attr.display_name
    names.update(CHANGE_TEXT)
    groups: list[Any] = [
        library.elements.elements,
        rules.surfaces.surfaces,
        rules.statuses.statuses,
        rules.reactions.reactions,
        rules.reactions.events,
        rules.conditions.conditions,
        rules.skill_triggers.triggers,
        rules.stacks.stacks,
        rules.rule_changes.rule_changes,
        rules.keywords.keywords,
        rules.skill_tags.tags,
        rules.shapes.shapes,
        rules.primitives.primitives,
        library.weapons.values(),
        library.skeletons.values(),
    ]
    for group in groups:
        for item in group:
            if hasattr(item, "name_zh"):
                names[_key(item.id)] = item.name_zh
    names.update(_WORDS_ZH)  # 固定用語優先（例：melee 一律是「近戰武器」）
    return names


def plain_name(identifier: str, library: ContentLibrary) -> str:
    """單一 ID 的中文名（查不到就原樣）。"""
    names = _tables(library)
    return names.get(identifier.removeprefix("modifier."), identifier)


def plainify(text: str, library: ContentLibrary) -> str:
    """把一段檢查文字裡的欄位名、ID、列舉值換成中文。"""
    names = _tables(library)
    out = _VARIANT_PATH.sub("變奏：", text)
    out = _MODIFIER.sub(lambda m: names.get(m.group(1), m.group(1)), out)
    out = _INDEXED.sub(lambda m: f"第 {int(m.group(2)) + 1} 個{_LIST_ZH[m.group(1)]}", out)
    for phrase, zh in _PHRASES:
        out = out.replace(phrase, zh)
    for pattern, zh in _PYDANTIC:
        out = pattern.sub(zh, out)
    return _WORD.sub(lambda m: _word(m.group(0), names), out)


def _word(token: str, names: dict[str, str]) -> str:
    if token in names:
        return names[token]
    if "." in token:
        return ".".join(names.get(part, part) for part in token.split("."))
    return token
