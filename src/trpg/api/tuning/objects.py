"""數值工坊的對象與欄位（NW-1a；技能對象 NW-2a）：白名單 × 磁碟上的檔 → 畫面用的清單與表單資料。

值一律讀**磁碟上**的 ``content/``（寫回後不重開伺服器也看到新值）；唯讀提示（遭遇護甲調整、技能的
使用者與預算）讀伺服器啟動時載入的內容庫。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import Any, Final, Literal

from trpg.api.tuning.schemas import (
    TuningFieldView,
    TuningObjectDetail,
    TuningObjectSummary,
    TuningSkillFacets,
    TuningSkillUser,
    TuningUnitSkills,
)
from trpg.api.tuning.shape_usage import unused_base_note
from trpg.api.tuning.yaml_patch import MISSING, PatchError, lookup
from trpg.content.battle import PhaseGrowSurface, UnitTemplate
from trpg.content.composer_rules import StructureRules
from trpg.content.equipment import loadout_held
from trpg.content.library import ContentLibrary
from trpg.content.loader import load_content_file, parse_yaml
from trpg.content.schemas import ContentModel, field_bounds
from trpg.content.skill_pick import SkillPickRules
from trpg.content.skill_rules import BudgetRules
from trpg.content.skills import SkillDef, weapon_problem
from trpg.content.skills.primitives import PrimitiveTable
from trpg.content.skills.shapes import ShapeTable
from trpg.content.skills.specs import SkillCost
from trpg.content.tuning_fields import (
    TABLE_KINDS,
    PathPart,
    TuningField,
    TuningFields,
    TuningTarget,
    format_path,
    parse_path,
    target_files,
)
from trpg.llm.prompts.wish_pick import count_zh
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import obstacle_candidates

_PERMILLE: Final = 1000

__all__ = [
    "AI_NAME_ZH",
    "AI_NOTES_ZH",
    "OBSTACLE_NOTICE_ZH",
    "TABLE_NAMES_ZH",
    "TABLE_NOTES_ZH",
    "ObjectNotFoundError",
    "ai_notes",
    "concrete_fields",
    "field_limits",
    "field_value",
    "list_objects",
    "object_detail",
    "object_file",
    "obstacle_objects",
    "primitive_names",
    "read_data",
    "retier_note_zh",
    "retier_notes",
    "skill_facets",
    "skill_ranged",
    "skill_users",
    "table_notes",
    "unit_levels",
    "unit_skill_picker",
]


def _schema_default_zh(model: type[ContentModel], name: str) -> str:
    """「沒寫＝<schema 預設值>」（HC-6b：照 pydantic 欄位的預設值組字，不另外寫一份）。"""
    return f"沒寫＝{model.model_fields[name].default}"


_DEFAULTS_ZH: Final = {
    "armor_bonus": _schema_default_zh(UnitTemplate, "armor_bonus"),
    "level": _schema_default_zh(UnitTemplate, "level"),
    "max_mana": "沒寫＝依武器大類",
    "stamina": "沒寫＝依武器大類",
    "cost.stamina": _schema_default_zh(SkillCost, "stamina"),
    "cost.mana": _schema_default_zh(SkillCost, "mana"),
    "cost.cooldown": "沒寫＝沒有冷卻",
    "stance_upkeep": _schema_default_zh(SkillDef, "stance_upkeep"),
    "phases[*].skills": "沒寫＝沿用上一階段",
    "parts[*].on_break[*].rounds": "沒寫＝永久封住",
}

_PART_DEFAULT_ZH: Final = "沒寫＝和本體相同"
"""部位的護甲、抗性、元素修正沒寫時（PB-1n）。"""

_STAT_ZH: Final = {
    "move": "移動下降（格）",
    "armor": "護甲下降（點）",
    "hit": "命中下降（點）",
    "resist.physical": "物理抗性下降（‰）",
    "resist.elemental": "元素抗性下降（‰）",
    "resist.nature": "自然抗性下降（‰）",
    "resist.spirit": "靈性抗性下降（‰）",
    "damage_dealt": "之後造成傷害的倍率（‰；750＝−25%）",
}
"""``stat_down`` 的數量欄位標籤（依 ``stat``；PB-1n）。"""

_BREAK_FIELD_TYPES: Final = {"amount": "stat_down", "rounds": "seal_skill"}
"""``parts[*].on_break[*].<欄位>`` 只展開到這種破壞效果（PB-1n 數量；GB-2 限時封招的回合數）。"""

_SITE_WORDS: Final = {
    "effects": "效果",
    "followup": "第二段",
    "variants": "變奏",
    "add_effect": "追加效果",
    "replace_effect": "替換效果",
    "then": "之後",
    "on_kill": "擊殺時",
    "win": "成功時",
    "lose": "失敗時",
}

type Value = int | str | list[str] | None


class ObjectNotFoundError(LookupError):
    """沒有這個對象（或不在白名單內）。"""


def read_data(path: Path) -> Any:
    return parse_yaml(path.read_bytes().decode("utf-8").removeprefix("﻿"))


def object_file(content_dir: Path, target: TuningTarget, object_id: str) -> Path:
    for path in target_files(content_dir, target):
        if path.stem == object_id:
            return path
    raise ObjectNotFoundError(f"數值工坊沒有這個對象：{target.kind}/{object_id}")


AI_NAME_ZH: Final = "AI 估值表（全體共用）"
"""``ai_profiles.yaml`` 在清單上的名字（PB-1n）。"""

TABLE_NAMES_ZH: Final = {
    "ai": AI_NAME_ZH,
    "rules": "核心戰鬥規則（全體共用）",
    "budget": "技能預算表（全體共用）",
    "object": "格子物件（全體共用）",
    "pick": "技能挑選模式的權重（全體共用）",
    "skill_triggers": "被動觸發時機（全體共用）",
    "skill_composer": "技能組合器的附帶配方（全體共用）",
    "skill_conditions": "技能條件的預算倍率（全體共用）",
    "skill_synergies": "技能協同係數（全體共用）",
    "forms": "形態（全體共用）",
    "equipment": "裝備規則（全體共用）",
    "item_gen": "物品生成（全體共用）",
    "skill_evolution": "技能分歧進化（全體共用）",
    "flash": "閃現規則與計價（全體共用）",
    "surface": "地面表面（全體共用）",
    "world_rules": "大世界規則：戰鬥、成長、許願池、實地地圖（全體共用）",
    "world_economy": "大世界經濟（全體共用）",
    "world_trade": "大世界交易與郵寄（全體共用）",
    "world_season": "賽季：今日目標、頭目、循環賽（全體共用）",
}
"""全體共用的表（:data:`TABLE_KINDS`）在清單上的名字（BS-1 加 ``rules``、``budget``；NW-3 加
``object``；PK-1 加 ``pick``；SK-5 加 ``skill_triggers``、``skill_composer``；HC-B 加
``skill_conditions``、``skill_synergies``；HC-W2 加 ``forms``、``equipment``、``item_gen``；
HC-4b2 加 ``skill_evolution``；HC-4b3 加 ``flash``；HC-4d 加大世界的 ``world_rules``、
``world_economy``、``world_trade``、``world_season``）。"""

TABLE_NOTES_ZH: Final = {
    "rules": (
        "這份是敵我全體共用的核心戰鬥規則（rules/core.yaml）：改一個值會影響所有戰鬥，不只一隻單位。",
        "目前只開放背刺與潛行偷襲的加成（BS-1）；其他規則數值之後再開。",
    ),
    "budget": (
        "這份是全體共用的技能預算表（skill_budget.yaml）：改了會讓相關技能的預算比例跟著變，"
        "超出合格區間的技能會在驗證時列出。",
        "HC-B 起計價全部在這裡，依分組收合：原語、狀態、表面的點數，形狀倍率，各種係數，"
        "召喚、代價折抵、特殊效果、修正技能……",
        "階級預算與武器基準傷害在「核心戰鬥規則」；條件的個別倍率、協同係數、被動觸發時機各有一張表。"
        "依參數值查表的形狀倍率（錐形依長度、十字依臂長、環形依半徑、連鎖依跳數）"
        "HC-W2 起也在「形狀」組。",
    ),
    "object": (
        "這份是全體共用的格子物件表（objects.yaml）：改一種物件的值，所有地圖上的這種物件一起變。",
        "目前只開放已寫的最大 HP（NW-3）；沒寫最大 HP 的物件打不破，不在這裡開。"
        "爆炸、漏出等其他欄位之後再開。",
    ),
    "pick": (
        "這份是技能生成「挑選模式」的打分權重與候選池大小（skill_pick.yaml，PK-1）：程式先做出一批"
        "合法候選，依這些權重排出前幾名交給本機模型挑一個並取名。",
        "分數只比「適不適合這位玩家」（協同、打法、屬性路線、多樣性），不比強弱；"
        "挑選模式目前要在 LLM 設定打開才會用到（預設是自由設計）。",
    ),
    "skill_triggers": (
        "這份是全體共用的被動觸發時機表（skill_triggers.yaml）：每種時機的預算係數決定用這個時機的"
        "被動能有多強（係數越大，同階級的被動效果越強）。",
        "改了係數，所有用這個時機的被動技能（手寫、組合器、LLM、裝備詞條）的預算比例跟著變，"
        "超出合格區間的技能會在驗證時列出。",
    ),
    "skill_composer": (
        "這份是技能組合器的抽選機率（skill_composer.yaml）：決定隨機組合器多常加上某種附帶配方"
        "（鉤、吸收表面、疾病擴散、被利用時、重擲、自身周圍、層數、召喚物、吸血）。",
        "改任何一個值都會改變「種子 → 技能」的對應：同一個種子之後組出來的招可能不同，"
        "已經發給玩家的技能不受影響。",
        "只開放這幾個機率與吸血的千分比（SK-5）；結構性的清單（例如吸血可用的骨架）不開。",
    ),
    "skill_conditions": (
        "這份是技能條件表（skill_conditions.yaml）：條件的預算倍率平常照嚴苛度（技能預算表的"
        "「條件的預算倍率」），這裡是個別條件的覆寫。",
        "只展開已經寫了覆寫的條件（HC-B）；沒寫的條件要改嚴苛度的倍率。",
    ),
    "skill_synergies": (
        "這份是技能協同係數表（skill_synergies.yaml）：技能同時帶有一條規則的全部機制標籤時，"
        "總點數乘上該係數（符合多條時全部相乘）。",
        "越大，帶這組機制的招算得越貴、其他效果越弱（HC-B）。標籤組合是結構，不開。",
    ),
    "forms": (
        "這份是全體共用的形態表（forms.yaml）：改一個值，敵我所有會變身的單位一起變。",
        "開放維持費、冷卻，以及每個形態的天生武器、形態中的效果與進入時的獎勵（HC-W2）；"
        "只展開已經寫的數值，沒寫的機制不能從這裡加。形態技能的預算不看這些數字。",
    ),
    "equipment": (
        "這份是全體共用的裝備規則（rules/equipment.yaml）：同名詞條的遞減與全身的硬上限，"
        "所有角色的裝備一起套用。",
        "總減傷上限要和核心戰鬥規則的元素修正下限一致，這裡不開（HC-W2）。",
    ),
    "item_gen": (
        "這份是物品產生器的係數（item_gen.yaml）：稀有度、預算、詞條單價與代價型的計價。"
        "改了只影響之後產生的物品（掉落、傭兵、重骰、打造），已經在背包裡的不變。",
        "條件詞條的成立率分類、可用類別、必選詞條、獨特與暫緩的詞條清單是結構，不開；"
        "產生器的重試次數也不開（HC-W2）。",
    ),
    "skill_evolution": (
        "這份是全體共用的技能分歧進化表（skill_evolution.yaml）：改了之後所有召喚技的加深、數量型"
        "進化一起變（已經學會的進化技能不變）。",
        "目前只開召喚技進化的兩個幅度（HC-4b2）；一般進化的模板、關鍵字嫁接、數量型一次幾隻是結構，不開。",
    ),
    "flash": (
        "這份是全體共用的閃現規則（flash_templates.yaml）：改了之後所有技能的閃現、重閃、完整技能"
        "一起變（價格、選項數、次數、預算加成）。",
        "只開出題價格與規則數值（HC-4b3）；幅度階梯、模板、類別、轉型是結構，不開。"
        "閃現的蓄力、輕巧、伴生、護主幅度在技能預算表的「閃現」組。",
    ),
    "surface": (
        "這份是全體共用的地面表面表（surfaces.yaml）：改一種表面的值，所有地圖上的這種表面一起變。",
        "目前只開放冰面的滑倒 DC（KD-1）；表面的效果、持續、元素互動是結構，不開。",
    ),
    "world_rules": (
        "這份是全體共用的大世界規則（world/rules.yaml）：改了之後所有角色的大世界戰鬥回寫、成長、"
        "許願池與實地地圖一起變。",
        "HC-4d 只開代表性的幾格（初值、未經模擬）；遇敵機率、天氣、時段表、地圖大小建議等"
        "其他數值之後再開。",
    ),
    "world_economy": (
        "這份是全體共用的大世界經濟（world/economy.yaml）：改了之後所有角色的背包、賣價與戰鬥金幣"
        "一起變。",
        "HC-4d 只開代表性的幾格（初值、未經模擬）；商店價格、疊放上限、任務幣等之後再開。",
    ),
    "world_trade": (
        "這份是全體共用的交易與郵寄規則（world/trade.yaml）：改了之後所有角色的寄信、領信與稽核"
        "報表一起變。",
        "HC-4d 只開代表性的幾格（初值、未經模擬）；稅率、可交易種類、郵差等之後再開。",
    ),
    "world_season": (
        "這份是全體共用的賽季設定（world/season.yaml）：改了之後今日目標、賽季頭目與影子循環賽一起變。",
        "HC-4d 只開代表性的幾格（初值、未經模擬）；日程、世界事件、懸賞、各季覆寫是結構"
        "或內容，不開。",
    ),
}
"""全體共用的表單頂端的唯讀提示（BS-1；``ai`` 用 :data:`AI_NOTES_ZH`）。"""

_N_HITS_PATH: Final = re.compile(r"\.budget_by_n_permille\.(\d+)$")


def _n_hits_note(target: TuningTarget) -> str:
    """被動觸發時機表的第 3 行：「每命中 n 次」開了哪幾個 n（HC-6b：照白名單的欄位組字）。"""
    ns = [m.group(1) for f in target.all_fields() if (m := _N_HITS_PATH.search(f.path))]
    listed = "、".join(ns)
    return f"只開放係數（SK-5）；「每命中 n 次」依 n 查的係數 HC-B 起也開了（n＝{listed} 各一格）。"


def ai_notes(target: TuningTarget) -> tuple[str, ...]:
    """AI 估值表表單頂端的唯讀提示（PB-1n；HC-6b：部位的欄位數照白名單數）。"""
    parts = sum(1 for f in target.all_fields() if f.path.startswith("parts."))
    return (
        AI_NOTES_ZH[0],
        f"目前開放頭目部位（parts）的 {parts} 個值（含巨型頭目的護面與站位，GB-3）、「無聲留背」"
        "（facing.silent_behind，BS-2）與殼縫蟲群的「追離頭目遠的人」（GB-3），全部是占位；"
        "其他行為模式權重還沒開。",
        *AI_NOTES_ZH[1:],
    )


def table_notes(kind: str, target: TuningTarget) -> list[str]:
    """全體共用的表單頂端的唯讀提示（BS-1；``ai`` 見 :func:`ai_notes`）。"""
    if kind == "ai":
        return list(ai_notes(target))
    notes = list(TABLE_NOTES_ZH[kind])
    if kind == "skill_triggers":
        notes.append(_n_hits_note(target))
    return notes


AI_NOTES_ZH: Final = (
    "這份是敵我全體共用的 AI 估值表：改一個值會影響所有戰鬥裡的 AI，不只一隻頭目。",
    "HC-4c 另開分組的 AI 規則數值（改寫與源力、召喚、區域與陷阱、姿態與代價、戰術指令、跑步與"
    "基本動作、種族技、共用評分），都是原本的初值、未經模擬。",
    "「打部位」與「繞背」的值給玩家方隊友 AI 用（決定要不要瞄準部位、要不要站到頭目背後）；"
    "護背扣分與快破門檻給頭目用。",
)
"""AI 估值表表單頂端的唯讀提示裡固定的幾行（PB-1n；部位那行由 :func:`ai_notes` 組）。"""


OBSTACLE_NOTICE_ZH: Final = (
    "造牆技能會放出這個物件。改 HP 會讓那些技能變強或變弱，技能預算不會跟著算。"
)
"""物件表單上、會被技能放出來的物件的「最大 HP」欄位提示（NW-3b；玩法 PM 交接 4.1.14 逐字）。"""


def obstacle_objects(
    content_dir: Path, table: TuningFields, library: ContentLibrary | None
) -> frozenset[str]:
    """造牆技能會放出的物件 ID（NW-3b；NW-3c 擴大，玩法 PM 交接 4.1.14、4.1.15「由資料推」）。

    兩個來源的聯集：

    - 手寫技能：工坊技能對象的檔案清單（``skills/*.yaml``，同 :func:`unit_skill_picker`），每招的
      所有效果層級（第二段、變奏、反噬、修正規則的命中後效果）裡 ``create_obstacle`` 的物件；
    - 組合器的造牆候選：:func:`~trpg.skillgen.composer_parts.obstacle_candidates`（組合器抽物件用
      的同一個函式，所以排除清單裡的冷卻井不在內）。

    閃現的延伸效果只把原技能既有的 ``create_obstacle`` 延長，物件來自原技能，不另算（4.1.15
    第 2 點）。沒有內容庫時是空集合（不顯示提示）。"""
    skills_target = table.target("skill")
    if library is None or skills_target is None:
        return frozenset()
    found: set[str] = set(obstacle_candidates(library))
    for path in target_files(content_dir, skills_target):
        skill = library.skills.get(path.stem)
        if skill is None:
            continue
        for spec in skill.iter_effects(
            include_followup=True,
            include_variants=True,
            include_backlash=True,
            include_modifiers=True,
        ):
            if spec.type == "create_obstacle" and spec.object is not None:
                found.add(spec.object)
    return frozenset(found)


def _field_notice(data: Any, path: str, walls: frozenset[str]) -> str | None:
    """欄位的提示行（NW-3b）：物件表裡會被造牆技能放出來的物件的 ``max_hp``。"""
    parts = parse_path(path)
    if parts[:1] != ("objects",) or parts[-1] != "max_hp" or not isinstance(parts[1], int):
        return None
    entry = (data.get("objects") or [])[parts[1]]
    return OBSTACLE_NOTICE_ZH if entry.get("id") in walls else None


def _category(data: Any, kind: str) -> Literal["boss", "enemy", "skill", "ai", "rules", "object"]:
    if kind == "skill":
        return "skill"
    if kind == "ai":
        return "ai"
    if kind == "object":
        return "object"
    if kind in TABLE_KINDS:
        return "rules"
    tags = data.get("tags") or ()
    return "boss" if "boss" in tags else "enemy"


# ---------------------------------------------------------------------------
# 路徑展開
# ---------------------------------------------------------------------------


def _phase_label(data: Any, index: int) -> str:
    phase = (data.get("phases") or [])[index]
    return f"第 {index + 1} 階段「{phase.get('name_zh') or phase.get('id')}」"


_ENTRY_WORDS: Final[dict[str, str]] = {
    "profiles": "行為模式",
    "objects": "物件",
    "surfaces": "表面",
    "triggers": "觸發時機",
    "conditions": "條件",
    "synergies": "協同",
    "forms": "形態",
    "total_budget": "全身預算",
}
"""全體共用表裡的清單項目（NW-3：AI 的行為模式、物件表的物件；SK-5：觸發時機表的時機；HC-W2：
形態表的形態、物品生成的全身預算表）在標籤前的稱呼。"""

_COLON_ENTRIES: Final = frozenset({"profiles", "forms", "total_budget"})
"""標籤前綴後面加「：」的清單（欄位名不是接在名字後面讀的）。"""

_ELEMENT_ZH: Final = {
    "physical": "物理",
    "fire": "火焰",
    "ice": "冰霜",
    "lightning": "雷電",
    "poison": "毒素",
    "wind": "風",
    "earth": "大地",
    "holy": "神聖",
    "shadow": "暗影",
    "chosen": "所選元素",
}
"""標籤裡的 ``{element}`` 換成的中文（HC-W2：形態的「受到某元素傷害的倍率」；``chosen``＝進入
形態時選的元素）。"""


_MECHANIC_ZH: Final = {
    "damage": "傷害",
    "heal": "治療",
    "area": "範圍",
    "displace": "位移",
    "control": "控制",
    "debuff": "削弱",
    "dot": "持續傷害",
    "surface": "表面",
    "terrain": "地形",
}
"""協同規則的機制標籤（``skill_synergies.yaml``）在標籤裡的中文（HC-B）。"""


def _entry_label(data: Any, parts: Sequence[PathPart]) -> str:
    """清單項目欄位的標籤前綴（NW-3），例「行為模式「殼縫蟲群」：」「物件「冷卻井」」。"""
    index = parts[1]
    assert isinstance(index, int)
    entry = (data.get(str(parts[0])) or [])[index]
    title = entry.get("name_zh") or entry.get("id")
    if title is None and entry.get("tags"):  # HC-B：協同規則沒有名字，用機制標籤
        title = "＋".join(_MECHANIC_ZH.get(str(t), str(t)) for t in entry["tags"])
    if title is None and "level" in entry:  # HC-W2：全身預算表依物品等級
        title = f"等級 {entry['level']}"
    name = f"{_ENTRY_WORDS[str(parts[0])]}「{title}」"
    return f"{name}：" if parts[0] in _COLON_ENTRIES else name


def _with_element(label: str, data: Any, parts: Sequence[PathPart]) -> str:
    """標籤裡的 ``{element}`` 換成路徑上最深、有 ``element`` 的那一層的元素中文（HC-W2）。"""
    if "{element}" not in label:
        return label
    element = ""
    for end in range(len(parts) - 1, 0, -1):
        try:
            node = lookup(data, parts[:end])
        except PatchError:
            break
        if isinstance(node, dict) and "element" in node:
            element = _ELEMENT_ZH.get(str(node["element"]), str(node["element"]))
            break
    return label.replace("{element}", element)


def _part_group(data: Any, path: str) -> str | None:
    """部位欄位的分組標題（PB-1n 待決 2：表單按部位分組），例「部位 1「拂塵」」；HC-W2 起形態表
    依形態分組，例「形態「熊」」；其他欄位 ``None``。"""
    parts = parse_path(path)
    index = parts[1] if parts[1:] else None
    if not isinstance(index, int) or parts[0] not in ("forms", "parts"):
        return None
    entry = (data.get(str(parts[0])) or [])[index]
    title = entry.get("name_zh") or entry.get("id")
    return f"形態「{title}」" if parts[0] == "forms" else f"部位 {index + 1}「{title}」"


def _part_label(data: Any, parts: Sequence[PathPart], field: TuningField) -> str:
    """部位欄位的標籤（PB-1n）：「部位「拂塵」血量（‰）」；破壞效果的數量依 ``stat`` 換成
    「部位「長劍」破掉後：之後造成傷害的倍率（‰；750＝−25%）」。"""
    index = parts[1]
    assert isinstance(index, int)
    part = (data.get("parts") or [])[index]
    label = f"部位「{part.get('name_zh') or part.get('id')}」"
    if len(parts) > 3 and parts[2] == "on_break" and isinstance(parts[3], int):  # noqa: PLR2004
        effects = part.get("on_break") or []
        effect = effects[parts[3]]
        which = f"第 {parts[3] + 1} 個效果" if len(effects) > 1 else ""
        if parts[-1] == "rounds":  # GB-2：限時封招
            return f"{label}破掉後{which}：封住「{effect.get('skill')}」的回合數"
        stat = str(effect.get("stat") or "")
        return f"{label}破掉後{which}：{_STAT_ZH.get(stat, field.label_zh)}"
    return label + field.label_zh.removeprefix("部位")


def _part_skipped(field: TuningField, data: Any, parts: Sequence[PathPart]) -> bool:
    """``parts[*].on_break[*].*`` 只展開到對應的破壞效果（:data:`_BREAK_FIELD_TYPES`：數量只給
    ``stat_down``，PB-1n；回合數只給 ``seal_skill``，GB-2）。"""
    if len(parts) < 4 or parts[0] != "parts" or parts[2] != "on_break":  # noqa: PLR2004
        return False
    try:
        effect = lookup(data, parts[:4])
    except PatchError:
        return True
    wanted = _BREAK_FIELD_TYPES.get(str(parts[-1]))
    return not (isinstance(effect, dict) and effect.get("type") == wanted)


def _phase_skipped(field: TuningField, phase: Any) -> bool:
    """``phases[*]`` 的欄位不展開到這個階段：開場階段（沒有 ``trigger``；schema 規定開場階段不能有
    改動，NW-1b 起 ``mana_restore``、NW-2a 起 ``skills`` 也照這條）；``phases[*].trigger.*`` 另外
    只展開 ``hp_below``。"""
    trigger = (phase or {}).get("trigger") if isinstance(phase, dict) else None
    if not trigger:
        return True
    return field.path.startswith("phases[*].trigger.") and trigger.get("kind") != "hp_below"


def _expand(data: Any, parts: Sequence[PathPart]) -> list[tuple[PathPart, ...]]:
    """把每個 ``*`` 換成清單的每個索引（清單不存在就沒有）。"""
    if "*" not in parts:
        return [tuple(parts)]
    star = list(parts).index("*")
    try:
        items = lookup(data, parts[:star])
    except PatchError:
        return []
    out: list[tuple[PathPart, ...]] = []
    for i in range(len(items) if isinstance(items, list) else 0):
        out += _expand(data, (*parts[:star], i, *parts[star + 1 :]))
    return out


def _effect_type(data: Any, parts: Sequence[PathPart]) -> str | None:
    """路徑上最深、而且有 ``type`` 鍵的那一層的 ``type``（效果的原語）。"""
    for end in range(len(parts) - 1, 0, -1):
        try:
            node = lookup(data, parts[:end])
        except PatchError:
            return None
        if isinstance(node, dict) and "type" in node:
            return str(node["type"])
    return None


def _present(data: Any, parts: Sequence[PathPart]) -> bool:
    try:
        found = lookup(data, parts)
    except PatchError:
        return False
    return found is not MISSING and found is not None


def _keep(data: Any, field: TuningField, parts: Sequence[PathPart]) -> bool:
    phase = parts[1] if parts[:1] == ("phases",) and len(parts) > 1 else None
    if isinstance(phase, int) and _phase_skipped(field, (data.get("phases") or [])[phase]):
        return False
    if _part_skipped(field, data, parts):
        return False
    if field.kinds and str(data.get("kind") or "active") not in field.kinds:
        return False
    if field.existing_only and not _present(data, parts):
        return False
    return not field.effect_types or _effect_type(data, parts) in field.effect_types


@cache
def _primitive_names_of(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    table = load_content_file(path, PrimitiveTable)
    names = {p.id: p.name_zh for p in table.primitives}
    names |= {p.id: p.name_zh for p in table.nested_only_effects}
    return names


def primitive_names(content_dir: Path) -> dict[str, str]:
    """原語 ID → 中文名（效果欄位的標籤用）。"""
    return _primitive_names_of(content_dir / "skill_primitives.yaml")


def _site_label(data: Any, parts: Sequence[PathPart], primitives: dict[str, str]) -> str:
    """效果欄位的前綴（例「效果 2（傷害）：」「第二段效果 1（推擊）：」）。"""
    words: list[str] = []
    for part in parts:
        if isinstance(part, int):
            if words:
                words[-1] += f" {part + 1}"
        elif part in _SITE_WORDS:
            words.append(_SITE_WORDS[part])
    kind = _effect_type(data, parts)
    name = primitives.get(kind or "", kind or "")
    return "".join(words) + (f"（{name}）" if name else "") + "："


def concrete_fields(
    data: Any, target: TuningTarget, primitives: dict[str, str] | None = None
) -> list[tuple[TuningField, str, str]]:
    """這個對象實際可改的欄位：``(白名單欄位, 具體路徑, 中文標籤)``。

    ``*`` 展開成每個索引；``phases[*]`` 不展開開場階段、``phases[*].trigger.*`` 只展開
    ``hp_below``（:func:`_phase_skipped`）；``kinds``、``existing_only``、``effect_types`` 照白名單
    篩（NW-2a）。效果層級的欄位標籤前面加效果位置與原語中文名。"""
    names = primitives if primitives is not None else {}
    effect_paths = {f"{s}.{f.path}" for s in target.effect_sites for f in target.effect_fields}
    out: list[tuple[TuningField, str, str]] = []
    for field in target.all_fields():
        for parts in _expand(data, parse_path(field.path)):
            if not _keep(data, field, parts):
                continue
            label = field.label_zh
            if parts[:1] == ("phases",) and len(parts) > 1 and isinstance(parts[1], int):
                label = f"{_phase_label(data, parts[1])}{field.label_zh}"
            elif parts[:1] == ("parts",) and len(parts) > 1 and isinstance(parts[1], int):
                label = _part_label(data, parts, field)
            elif parts[:1] in tuple((w,) for w in _ENTRY_WORDS) and len(parts) > 1:
                label = f"{_entry_label(data, parts)}{field.label_zh}"
            elif field.path in effect_paths:
                label = f"{_site_label(data, parts, names)}{field.label_zh}"
            label = _with_element(_numbered(label, parts), data, parts)
            out.append((field, format_path(parts), label))
    return out


def _numbered(label: str, parts: Sequence[PathPart]) -> str:
    """標籤裡的 ``{n}`` 換成最後一個清單索引 ＋ 1（HC-B：純數字清單，例「持續 {n} 回合」）。"""
    if "{n}" not in label:
        return label
    index = next((p for p in reversed(parts) if isinstance(p, int)), None)
    return label.replace("{n}", "?" if index is None else str(index + 1))


def field_value(data: Any, path: str) -> Value:
    """磁碟上的現值（整數、骰子字串、ID 清單；沒寫＝``None``）。"""
    try:
        found = lookup(data, parse_path(path))
    except PatchError:
        return None
    if found is MISSING or found is None or isinstance(found, bool):
        return None
    if isinstance(found, int | str):
        return found
    if isinstance(found, list) and all(isinstance(x, str) for x in found):
        return list(found)
    return None


# ---------------------------------------------------------------------------
# 技能的分類與使用者
# ---------------------------------------------------------------------------


def _has_condition(skill: SkillDef) -> bool:
    return skill.condition is not None or any(e.condition is not None for e in skill.effects)


def skill_ranged(skill: SkillDef) -> bool:
    """工坊篩選的「遠程」：要遠程武器，或形狀射程 2 格以上（貼身 1 格以外）；清單與分組改共用
    這一份。"""
    shape_range = skill.shape.range
    return skill.weapon_req == "ranged" or (isinstance(shape_range, int) and shape_range > 1)


def _single_damage(skill: SkillDef) -> bool:
    return skill.shape.type == "single" and any(e.type == "damage" for e in skill.effects)


def skill_facets(skill: SkillDef, library: ContentLibrary | None) -> TuningSkillFacets:
    """清單篩選用的分類；``library`` 有時另算 1 階預算比例。"""
    ratio: int | None = None
    if library is not None:
        ratio = _ratio_permille(skill, library)
    return TuningSkillFacets(
        tier=skill.tier,
        category=skill.category,
        weapon_req=skill.weapon_req,
        ap_cost=skill.ap_cost,
        kind=skill.kind,
        enemy_only=skill.enemy_only,
        has_condition=_has_condition(skill),
        shape=skill.shape.type,
        ranged=skill_ranged(skill),
        tags=list(skill.tags),
        single_damage=skill.shape.type == "single"
        and any(e.type == "damage" for e in skill.effects),
        budget_ratio_permille=ratio,
    )


def _ratio_permille(skill: SkillDef, library: ContentLibrary) -> int | None:
    try:
        report = skill_budget(skill, library)
    except BudgetError:
        return None
    return int((report.ratio * 1000 * 2 + 1) // 2)


def unit_levels(library: ContentLibrary) -> dict[str, set[int]]:
    """大世界裡單位（範本或變體 ID）會出現的等級（R2 提示用）：遭遇表各地點的 ``level_min``
    （陣容、固定精英、加人）、懸賞的等級、賽季頭目的等級。等級另有區域加成（世界事件 +1），
    這裡不算。"""
    levels: dict[str, set[int]] = {}

    def add(name: str, level: int | None) -> None:
        if level is not None:
            levels.setdefault(name, set()).add(level)

    for region in sorted(library.world_encounters):
        table = library.world_encounters[region]
        lmap = library.location_map(region)
        places = lmap.location_by_id() if lmap is not None else {}
        groups = {g.id: g for g in table.groups}
        for loc in table.locations:
            place = places.get(loc.location)
            level = None if place is None else place.level_min
            for weight in loc.groups:
                for name in groups[weight.group].all_units if weight.group in groups else ():
                    add(name, level)
            if loc.elite is not None:
                add(loc.elite.unit, level)
    season = library.world_season
    if season is not None:
        for bounty in season.bounties:
            add(bounty.elite.unit, bounty.level)
        if season.season_boss is not None:
            for name in season.season_boss.units:
                add(name, season.season_boss.level)
    return levels


def _equips(template: UnitTemplate, skill_id: str) -> list[str]:
    where = ["開場"] if skill_id in template.skills else []
    where += [
        f"第 {i + 1} 階段"
        for i, phase in enumerate(template.phases)
        if phase.skills is not None and skill_id in phase.skills
    ]
    return where


def _battle_tier(library: ContentLibrary, levels: dict[str, set[int]], unit_id: str) -> int | None:
    rules = library.world_rules
    found = levels.get(unit_id)
    if rules is None or not found:
        return None
    return max(rules.enemy_growth.tier_for(level) for level in found)


def skill_users(library: ContentLibrary | None, skill_id: str) -> list[TuningSkillUser]:
    """裝了這招的單位（開場或某個階段；``tier`` 是大世界實戰會用的最高階級）與模擬用的 build
    （依 ID 排序）。"""
    if library is None:
        return []
    levels = unit_levels(library)
    out: list[TuningSkillUser] = []
    for unit_id in sorted(library.units):
        unit = library.units[unit_id]
        where = _equips(unit, skill_id)
        if where:
            out.append(
                TuningSkillUser(
                    kind="unit",
                    id=unit_id,
                    name_zh=unit.name_zh,
                    where_zh=where,
                    tier=_battle_tier(library, levels, unit_id),
                )
            )
    catalog = library.enemy_catalog()
    for name in sorted(set(levels) - set(library.units)):  # 變體（world/enemies.yaml）
        try:
            template = catalog.template(name)
        except (KeyError, ValueError):
            continue
        where = _equips(template, skill_id)
        if where:
            out.append(
                TuningSkillUser(
                    kind="unit",
                    id=name,
                    name_zh=template.name_zh,
                    where_zh=where,
                    tier=_battle_tier(library, levels, name),
                )
            )
    for build in sorted(library.builds.builds, key=lambda b: b.id):
        if skill_id in build.hero.skills:
            out.append(
                TuningSkillUser(kind="build", id=build.id, name_zh=build.name_zh, where_zh=[])
            )
    return out


# ---------------------------------------------------------------------------
# 清單與表單
# ---------------------------------------------------------------------------


def list_objects(
    content_dir: Path, table: TuningFields, library: ContentLibrary | None = None
) -> list[TuningObjectSummary]:
    out: list[TuningObjectSummary] = []
    for target in table.targets:
        for path in target_files(content_dir, target):
            data = read_data(path)
            facets = None
            if target.kind == "skill":
                facets = skill_facets(SkillDef.model_validate(data), library)
            out.append(
                TuningObjectSummary(
                    kind=target.kind,
                    id=path.stem,
                    name_zh=TABLE_NAMES_ZH[target.kind]
                    if target.kind in TABLE_KINDS
                    else str(data.get("name_zh") or path.stem),
                    category=_category(data, target.kind),
                    file=path.relative_to(content_dir).as_posix(),
                    skill=facets,
                )
            )
    return out


def _armor_notes(library: ContentLibrary | None, unit_id: str) -> list[str]:
    if library is None:
        return []
    notes: list[str] = []
    for region in sorted(library.world_encounters):
        for loc in library.world_encounters[region].locations:
            mods = loc.armor_mods
            if mods is not None and mods.unit == unit_id:
                notes.append(
                    f"實戰時另有遭遇護甲調整（{region}／{loc.location}，"
                    f"{mods.min_total:+d}～{mods.max_total:+d}，依劇情旗標；"
                    "數值工坊還沒開放遭遇的護甲調整）"
                )
    return notes


@cache
def _tables(content_dir: Path) -> tuple[PrimitiveTable | None, ShapeTable | None]:
    prim = content_dir / "skill_primitives.yaml"
    shapes = content_dir / "skill_shapes.yaml"
    return (
        load_content_file(prim, PrimitiveTable) if prim.is_file() else None,
        load_content_file(shapes, ShapeTable) if shapes.is_file() else None,
    )


_WISH_CARDS_TOKENS: Final = ("{wish_cards}", "{wish_cards_zh}")


def note_text(note: str, content_dir: Path) -> str:
    """欄位說明裡的 ``{wish_cards}``（「挑 3 張」）、``{wish_cards_zh}``（「三選一」）換成這份內容的
    ``skill_pick.yaml`` ``pool.wish_cards``（HC-6a 裁定 1、HC-6b：工坊改了張數，相鄰兩格的說明
    跟著變）。
    中文數字的寫法同許願提示詞（:func:`~trpg.llm.prompts.wish_pick.count_zh`）。"""
    if not any(token in note for token in _WISH_CARDS_TOKENS):
        return note
    cards = load_content_file(content_dir / "skill_pick.yaml", SkillPickRules).pool.wish_cards
    return note.replace("{wish_cards}", str(cards)).replace("{wish_cards_zh}", count_zh(cards))


def _note_zh(
    field: TuningField, path: str, content_dir: Path, library: ContentLibrary | None
) -> str:
    """欄位說明（:func:`note_text`）；形狀「沒填參數時」的基礎倍率沒有招用到時，接一句「目前沒有招用到，
    改了暫時沒效果。」（HC-W2 裁定 1，由資料算：:mod:`trpg.api.tuning.shape_usage`）。"""
    note = note_text(field.note_zh, content_dir)
    extra = unused_base_note(path, library)
    return note if extra is None else f"{note}{extra}"


def _default_zh(field: TuningField) -> str | None:
    if field.path in _DEFAULTS_ZH:
        return _DEFAULTS_ZH[field.path]
    if field.path.startswith("parts[*].") and field.path != "parts[*].hp_permille":
        return _PART_DEFAULT_ZH
    return _DEFAULTS_ZH.get(field.path)


def _part_limits(data: Any, parts: Sequence[PathPart]) -> tuple[int | None, int | None]:
    """部位欄位擋的範圍（schema：``content/parts.py``）。"""
    leaf = parts[-1]
    if leaf == "hp_permille":
        return 1, 1000
    if parts[2:3] == ("resist",):  # PartDef 的驗證：-1000～1000‰
        return -_PERMILLE, _PERMILLE
    if leaf == "amount":  # StatDownBreak 的驗證：damage_dealt 是倍率‰，要小於 1000
        effect = lookup(data, parts[:4])
        return (1, _PERMILLE - 1) if effect.get("stat") == "damage_dealt" else (1, None)
    if leaf == "rounds":  # GB-2：SealSkillBreak.rounds（ge=1）
        return 1, None
    return None, None


def _schema_limits(parts: Sequence[PathPart]) -> tuple[int | None, int | None] | None:
    """schema 寫死的範圍（不靠原語、形狀表）；不是這幾種欄位 ``None``。"""
    if parts[-2:] == ("grow_surface", "max_rows"):  # GB-2：PhaseGrowSurface.max_rows
        return field_bounds(PhaseGrowSurface, "max_rows")
    if parts[:1] == ("objects",) and parts[-1] == "max_hp":  # NW-3：ObjectDef.max_hp（ge=1）
        return 1, None
    if parts[:1] == ("profiles",) and parts[-1] == "prefer_far_from_leader":  # NW-3b：ge=0
        return 0, None
    return _sk5_limits(parts)


def _sk5_limits(parts: Sequence[PathPart]) -> tuple[int | None, int | None] | None:
    """SK-5 的兩張表：觸發時機的係數（``ge=1``）、組合器的機率（0～1000）與吸血比例（1～500）。"""
    if parts[:1] == ("triggers",) and parts[-1] == "budget_coefficient_permille":
        return 1, None
    if parts[-1] == "lifesteal_amount_permille":  # StructureRules（原語上限）
        return field_bounds(StructureRules, "lifesteal_amount_permille")
    if parts[:1] in (("structure",), ("passive",)) and str(parts[-1]).endswith("_permille"):
        return 0, 1000  # StructureRules／PassiveRules
    return None


def field_limits(
    content_dir: Path, data: Any, field: TuningField, path: str
) -> tuple[int | None, int | None]:
    """原語或形狀表上的範圍（擋的範圍；畫面只顯示）。"""
    parts = parse_path(path)
    if parts[:1] == ("parts",) and len(parts) > 1:
        if isinstance(parts[1], int):
            return _part_limits(data, parts)
        return (0, 1000) if parts[-1] == "near_break_permille" else (0, None)  # AI 估值表
    fixed = _schema_limits(parts)
    if fixed is not None:
        return fixed
    prims, shapes = _tables(content_dir)
    leaf = parts[-1]
    if field.effect_types and prims is not None:
        kind = _effect_type(data, parts)
        defs = {p.id: p.params for p in prims.primitives}
        defs |= {p.id: p.params for p in prims.nested_only_effects}
        spec = defs.get(kind or "", {}).get(str(leaf))
        return (spec.min, spec.max) if spec is not None else (None, None)
    if len(parts) >= 2 and parts[-2] == "shape" and shapes is not None:  # noqa: PLR2004
        shape = lookup(data, parts[:-1])
        found = next((s for s in shapes.shapes if s.id == shape.get("type")), None)
        if found is not None:
            spec2 = {**found.params, **found.content_params}.get(str(leaf))
            if spec2 is not None:  # 工坊改的是內建內容：上限照 content_max（GB-2b）
                return spec2.min, spec2.top(builtin=True)
    return None, None


def retier_note_zh(budget: BudgetRules) -> str:
    """R2（使用者 2026-11-12「照建議」）：維持現行升階規則（``retier``），只在表單頂端提示；
    夾的區間照 ``skill_budget.yaml`` 的合格區間（HC-6b）。"""
    low = f"{budget.min_ratio_permille / 10:g}"
    high = f"{budget.max_ratio_permille / 10:g}"
    return f"這招在 2 階以上會依預算比例重算（夾在 {low}～{high}%），超出的部分只在 1 階有效"


@cache
def _budget_rules(content_dir: Path) -> BudgetRules:
    return load_content_file(content_dir / "skill_budget.yaml", BudgetRules)


def retier_notes(
    skill: SkillDef, users: Sequence[TuningSkillUser], budget: BudgetRules
) -> list[str]:
    """技能表單頂端的唯讀提示：升階重算（R2）＋實戰會用升階版的單位（等級→階級）。"""
    notes = [retier_note_zh(budget)]
    upgraded = [u for u in users if u.kind == "unit" and u.tier is not None and u.tier > skill.tier]
    if upgraded:
        names = "、".join(f"{u.name_zh}（{u.id}，{u.tier} 階）" for u in upgraded)
        notes.append(f"實戰會用升階版（_t<階>）的單位：{names}；改 1 階的數字對它們可能沒有影響")
    else:
        notes.append("目前沒有單位在大世界實戰用這招的升階版（玩家角色升階時另依比例重算）")
    return notes


def _readonly(field: TuningField, value: Value) -> str | None:
    if field.kind == "range" and value == "weapon":
        return "武器射程：改成數字會改變技能和武器的綁定，屬結構，不在數值工坊改"
    return None


_CLASS_ZH: Final = {"melee": "近戰", "ranged": "遠程", "focus": "法器"}


def unit_skill_picker(
    content_dir: Path, table: TuningFields, template: UnitTemplate, library: ContentLibrary | None
) -> TuningUnitSkills | None:
    """招式組編輯器用（NW-2b B5）：單位的武器、欄位上限，以及數值工坊開放的技能裡哪些和這個單位
    的武器不相容（同載入檢查的 ``weapon_problem``；欄位上限、敵人專用招由整包驗證擋）。"""
    skills_target = table.target("skill")
    if library is None or skills_target is None:
        return None
    weapon = library.weapons.get(template.weapon)
    if weapon is None:
        return None
    try:
        held = loadout_held(weapon, library.loadout_of(template))
    except ValueError:
        held = loadout_held(weapon, None)
    problems: dict[str, str] = {}
    for path in target_files(content_dir, skills_target):
        skill = library.skills.get(path.stem)
        if skill is None:
            continue
        problem = weapon_problem(skill, weapon.weapon_class, held)
        if problem is not None:
            problems[path.stem] = problem
    slots = library.ruleset.core.skill_slots
    return TuningUnitSkills(
        weapon_zh=f"{weapon.name_zh}（{_CLASS_ZH.get(weapon.weapon_class, weapon.weapon_class)}）",
        slots_zh=(
            f"主動 {slots.active}、被動 {slots.passive}、反應 {slots.reaction}、姿態 {slots.stance}"
        ),
        problems=problems,
    )


def _skill_names_in_label(label: str, library: ContentLibrary | None) -> str:
    """標籤裡的「skill_xxx」換成技能中文名（GB-2b：限時封招的標籤；沒有內容庫或找不到就照舊）。"""
    if library is None or "「skill_" not in label:
        return label
    for skill_id in sorted(re.findall(r"「(skill_[a-z0-9_]+)」", label)):
        skill = library.skills.get(skill_id)
        if skill is not None:
            label = label.replace(f"「{skill_id}」", f"「{skill.name_zh}」")
    return label


def object_detail(
    content_dir: Path,
    table: TuningFields,
    kind: str,
    object_id: str,
    library: ContentLibrary | None = None,
) -> TuningObjectDetail:
    target = table.target(kind)
    if target is None:
        raise ObjectNotFoundError(f"數值工坊沒有這類對象：{kind}")
    path = object_file(content_dir, target, object_id)
    data = read_data(path)
    primitives = primitive_names(content_dir)
    walls = obstacle_objects(content_dir, table, library) if kind == "object" else frozenset()
    fields: list[TuningFieldView] = []
    for field, concrete, raw_label in concrete_fields(data, target, primitives):
        label = _skill_names_in_label(raw_label, library)
        value = field_value(data, concrete)
        low, high = field_limits(content_dir, data, field, concrete)
        fields.append(
            TuningFieldView(
                path=concrete,
                pattern=field.path,
                label_zh=label,
                kind=field.kind,
                value=value,
                default_zh=_default_zh(field) if value is None else None,
                hint_min=field.hint_min,
                hint_max=field.hint_max,
                limit_min=low,
                limit_max=high,
                readonly_zh=_readonly(field, value),
                note_zh=_note_zh(field, concrete, content_dir, library),
                notice_zh=_field_notice(data, concrete, walls),
                group_zh=field.group_zh or _part_group(data, concrete),
            )
        )
    if kind == "skill":
        skill = SkillDef.model_validate(data)
        users = skill_users(library, skill.id)
        return TuningObjectDetail(
            kind=kind,
            id=object_id,
            name_zh=skill.name_zh,
            category="skill",
            file=path.relative_to(content_dir).as_posix(),
            fields=fields,
            notes_zh=retier_notes(
                skill, users, _budget_rules(content_dir) if library is None else library.budget
            ),
            skill=skill_facets(skill, library),
            used_by=users,
        )
    if kind in TABLE_KINDS:
        return TuningObjectDetail(
            kind=kind,
            id=object_id,
            name_zh=TABLE_NAMES_ZH[kind],
            category=_category(data, kind),
            file=path.relative_to(content_dir).as_posix(),
            fields=fields,
            notes_zh=table_notes(kind, target),
        )
    template = UnitTemplate.model_validate(data)
    notes = ["大世界的敵人另依遭遇等級成長（grow_enemy），這裡改的是單位檔的基礎值。"]
    notes += _armor_notes(library, template.id)
    return TuningObjectDetail(
        kind=kind,
        id=object_id,
        name_zh=template.name_zh,
        category=_category(data, kind),
        file=path.relative_to(content_dir).as_posix(),
        fields=fields,
        notes_zh=notes,
        unit_skills=unit_skill_picker(content_dir, table, template, library),
    )
