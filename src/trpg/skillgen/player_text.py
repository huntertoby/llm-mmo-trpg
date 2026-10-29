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

__all__ = ["change_text", "plain_name", "plainify"]


def change_text(library: ContentLibrary, kind: str) -> str:
    """修正規則改變種類的玩家名稱（``modifier_changes.yaml`` 的 ``name_zh``；Phase 3T-1）。"""
    return library.modifier_changes.by_id()[kind].name_zh


_INDEXED = re.compile(r"\b(effects|modifiers|variants)\[(\d+)\]")
_LIST_ZH = {"effects": "效果", "modifiers": "修正規則", "variants": "變奏"}
_WORD = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_MODIFIER = re.compile(r"\bmodifier\.([A-Za-z_]+)")
_VARIANT_PATH = re.compile(r"\bvariants\.[A-Za-z0-9_]+\.")
_VARIANT_ID = re.compile(r"變奏 [A-Za-z0-9_]+")

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
_PYDANTIC_PHRASES: tuple[tuple[str, str], ...] = (
    (", unable to parse string as an integer", ""),
    (", unable to interpret input", ""),
    ("Extra inputs are not permitted", "這個欄位在這裡不能填"),
    ("Input should be a valid number", "必須是數字"),
    ("Input should be a valid decimal", "必須是數字"),
    ("Input should be a valid list", "必須是列表"),
    ("Input should be a valid array", "必須是列表"),
    ("Input should be a valid tuple", "必須是列表"),
    ("Input should be a valid dictionary", "格式不對"),
    ("Input should be None", "這裡不能填"),
    ("Unable to extract tag using discriminator", "缺少類型 "),
    ("Input should be a valid", "格式不對"),
)
"""pydantic 的英文錯誤訊息（先於 :data:`_PYDANTIC` 換，3-48h）。"""
_DICT_OR_INSTANCE = re.compile(r"Input should be a valid dictionary or instance of \w+")
_PYDANTIC = (
    (
        re.compile(
            r"Input tag '[^']*' found using '[^']*' does not match any of the expected tags[^；。]*"
        ),
        "類型不在可選範圍內",
    ),
    (re.compile(r"String should have at least (\d+) characters?"), r"至少要 \1 個字"),
    (re.compile(r"String should have at most (\d+) characters?"), r"最多 \1 個字"),
    (re.compile(r"String should match pattern [^；。]*"), "格式不對"),
    (re.compile(r"(?:Tuple|List|Set) should have at least (\d+) items?[^；。]*"), r"至少要 \1 項"),
    (re.compile(r"(?:Tuple|List|Set) should have at most (\d+) items?[^；。]*"), r"最多 \1 項"),
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
    "then": "消耗後的效果",
    "win": "成功時",
    "lose": "失敗時",
    "dice": "骰子",
    "type": "類型",
    "damage_multiplier": "傷害倍率",
    "self_damage_of_hit": "反噬自傷",
    "refund_ap": "返還 AP",
    "refund_cooldown": "重置本技能冷卻",
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


_FIELD_ZH: dict[str, str] = {
    "actions": "基本動作",
    "activation": "啟動方式",
    "add_effect": "加一個效果",
    "all": "敵我雙方",
    "all_attacks": "所有攻擊",
    "all_skills": "所有技能",
    "amount": "數量",
    "anchor": "錨點",
    "applies_to": "套用對象",
    "bound": "綁定",
    "by": "依據",
    "cap_permille": "上限",
    "cast_flavor": "施放描述",
    "caster_adjacent_blocker": "施放者身旁有牆",
    "caster_high_ground": "施放者居高",
    "caster_surface": "施放者所在表面",
    "chance_permille": "成功率",
    "change": "改變",
    "collision_dice": "撞擊骰",
    "concept": "概念",
    "condition": "條件",
    "count": "顆數",
    "created_by": "建立者",
    "crit_range": "暴擊範圍",
    "stance_upkeep": "姿態維持費",
    "damage_multiplier_permille": "傷害倍率",
    "description_zh": "說明",
    "distance": "距離",
    "effect": "效果",
    "effects": "效果",
    "empty_slots_cap": "空欄位上限",
    "event": "時機",
    "exclusive_group": "互斥群組",
    "explode": "爆骰",
    "followup": "第二段",
    "form_bonus_permille": "形態加成",
    "hp_percent": "生命代價",
    "hp_permille": "生命比例",
    "id": "代號",
    "include_caster": "包含施放者",
    "index": "順序",
    "infusion": "灌注",
    "jump_range": "跳躍距離",
    "jumps": "跳躍次數",
    "k": "取高顆數",
    "knock_prone": "擊倒",
    "landing": "落點",
    "lifesteal_permille": "吸血",
    "magnitude_permille": "幅度",
    "mana": "法力",
    "max_distance": "最大距離",
    "max_hp_permille": "最大生命比例",
    "max_per_round": "每輪上限",
    "modifiers": "修正規則",
    "multiplier_permille": "倍率",
    "n": "次數",
    "name_zh": "名稱",
    "narrative": "敘述",
    "object": "物件",
    "on_hit": "命中後",
    "on_kill": "擊殺時",
    "on_miss": "失手時",
    "origin": "來源",
    "owner_id": "擁有者",
    "parents": "親代",
    "per_stack_permille": "每層加成",
    "per_step_permille": "每步加成",
    "per_turn_limit": "每回合上限",
    "permille": "比例",
    "pierce": "穿透",
    "power_permille": "威力",
    "provenance": "出處",
    "radius": "半徑",
    "rank": "等第",
    "release": "釋放時機",
    "resource": "資源",
    "rule": "規則",
    "scale": "倍率來源",
    "scaling": "縮放",
    "schema_version": "資料版本",
    "scope": "範圍",
    "self_damage_permille_of_hit": "反噬自傷",
    "self_status": "自身狀態",
    "overdraft": "透支",
    "sides": "面數",
    "size": "大小",
    "skill": "技能",
    "skill_tags": "技能標籤",
    "source": "源力",
    "speed": "速度",
    "splash": "波及",
    "split_heal": "聖光雙效",
    "spread": "擴散格數",
    "stack": "層數",
    "stacks": "層數",
    "stamina": "耐力",
    "status": "狀態",
    "weapon_skills": "武器技",
    "surface": "表面",
    "tag": "標籤",
    "tags": "標籤",
    "target": "目標",
    "target_surface": "目標點所在表面",
    "tradeable": "可交易",
    "trait": "特性",
    "trap": "陷阱",
    "trigger": "觸發",
    "unit": "單位",
    "form": "形態",
    "form_category": "形態類別",
    "when": "時機",
    "which": "範圍",
    "name": "名稱",
    "hp": "生命",
    "max": "最大",
    "min": "最小",
    "weapon": "武器",
    "caster": "施放者",
    "moving": "移動",
    "fixed": "固定",
    "tile": "格子",
    "delay": "延遲",
    "enter": "踩到時",
}
"""技能定義的欄位名 → 中文（schema 錯誤訊息的位置用；3-48h：不露欄位代號）。修正規則的改變種類
（``change`` 的欄位）不在這裡：一律用 ``modifier_changes.yaml`` 的 ``name_zh``（3T-1）。"""


def _key(value: Any) -> str:
    return str(getattr(value, "value", value))


def _tables(library: ContentLibrary) -> dict[str, str]:
    """ID → 中文名：內容資料裡有 ``id`` 與 ``name_zh`` 的各種定義。後面的覆蓋前面的。"""
    rules = library.ruleset
    names: dict[str, str] = {}
    for attr in Attribute:
        names[attr.value] = attr.display_name
    names.update({c.id: c.name_zh for c in library.modifier_changes.changes})
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
    for key, zh in _FIELD_ZH.items():
        names.setdefault(key, zh)  # 欄位名（schema 錯誤的位置用）：不蓋掉 ID 的中文名
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
    out = _VARIANT_ID.sub("這個變奏", out)  # 型態代碼玩家模式自動產生、不顯示（3-48h）
    out = out.replace("NdM", "「顆數d面數」")
    out = _MODIFIER.sub(lambda m: names.get(m.group(1), m.group(1)), out)
    out = _INDEXED.sub(lambda m: f"第 {int(m.group(2)) + 1} 個{_LIST_ZH[m.group(1)]}", out)
    for phrase, zh in _PHRASES:
        out = out.replace(phrase, zh)
    out = _DICT_OR_INSTANCE.sub("格式不對", out)
    for phrase, zh in _PYDANTIC_PHRASES:
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
