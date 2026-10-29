"""LLM 提議的代價類欄位（Phase 4-L8；06 6.5 代價換強度，共通規則 7「LLM 只能從允許的代價中挑」）。

提議格式沒有 ``cost``（數值由引擎補），代價一律是「選不選」的結構欄位，數值由引擎決定：

- ``cost_penalty``、``cost_overdraft``（3-50，見 :mod:`trpg.skillgen.self_penalty`）；
- ``cost_once_per_battle: true`` → ``cost.uses_per_battle: 1``（每場限一次）；
- ``cost_hp: true`` → ``cost.hp_percent``：引擎取 ``skill_budget.yaml`` 的 HP 代價折抵上限對應的量
  （``allowance.hp_cap ÷ hp_per_permille``，LLM 不選多少）；
- ``cost_on_miss``：失手反噬（3D-7a）的效果列表（1～2 個 ``damage``／``apply_status``，對象固定是
  施放者，數值由補值器補）→ ``cost.on_miss``。

``cost.source``（傳說技能的源力）、``cost.stacks``（施放前要有幾層）是數值：不在提議裡，由補值器
決定（傳說技能補 1 點源力，見 :func:`~trpg.skillgen.proposal_numbers.minimal_filler`）。範圍與上限
（只有主動技能、稀有度、整體 50% 上限）一律由驗證器檢查。
"""

from __future__ import annotations

from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skills import ON_MISS_MIN_RARITY, SkillRarity, rarity_rank
from trpg.skillgen.self_penalty import penalty_choices

__all__ = [
    "COST_DOCS",
    "COST_FLAG_FIELDS",
    "DEFAULT_HP_PERMILLE",
    "ONCE_PER_BATTLE",
    "apply_cost_choices",
    "cost_choices_of",
    "cost_entries",
    "hp_cost_permille",
    "on_miss_allowed",
]

ONCE_PER_BATTLE = 1
""":data:`cost_once_per_battle` 換成的 ``cost.uses_per_battle``。"""
DEFAULT_HP_PERMILLE = 200
"""沒有內容庫時 ``cost_hp`` 換成的 ``cost.hp_percent``（‰；與內建 ``hp_cap`` 200 相同）。"""
COST_FLAG_FIELDS: tuple[str, ...] = ("cost_once_per_battle", "cost_hp", "cost_on_miss")
"""4-L8 新增的提議欄位（``cost_penalty``／``cost_overdraft`` 另見 3-50）。"""
COST_DOCS: dict[str, str] = {
    "cost_penalty": (
        "可省略。用自己的代價換更強的效果：填一個自身負面狀態（施放後自己獲得；stun 暈眩＝自己跳過"
        "下一個回合、silenced 沉默＝只能用在法術技、bleed 流血等）；一招最多一個，數值由遊戲決定"
    ),
    "cost_overdraft": (
        "可省略。填 true＝施放後自己下一個回合少 1 AP（透支）；可以和 cost_penalty 同時使用"
    ),
    "cost_once_per_battle": "可省略。填 true＝每場戰鬥只能用一次（換更強的效果）",
    "cost_hp": "可省略。填 true＝施放時付出自己的一部分最大 HP（數值由遊戲決定）",
    "cost_on_miss": (
        "可省略，只有主動技能可用。失手反噬：攻擊沒命中時施放者自己承受的 1～2 個效果（傷害或"
        "負面狀態），換更強的效果；數值由遊戲決定"
    ),
}
"""提議的代價欄位說明（JSON schema 的 ``description`` 與 prompt ``available`` 的 ``costs``）。"""


def on_miss_allowed(rarity: SkillRarity | None) -> bool:
    """這個稀有度能不能有失手反噬（``None`` ＝ 不篩）。"""
    return rarity is None or rarity_rank(rarity) >= rarity_rank(ON_MISS_MIN_RARITY)


def cost_entries(library: ContentLibrary, rarity: SkillRarity | None) -> list[dict[str, Any]]:
    """prompt ``available`` 的 ``costs``（Phase 4-L8）：主動技能可以挑的代價欄位與說明；
    ``cost_penalty`` 另列這個稀有度能挑的狀態。全部可省略，數值由遊戲決定。"""
    out: list[dict[str, Any]] = [
        {
            "id": "cost_penalty",
            "hint": COST_DOCS["cost_penalty"],
            "choices": list(penalty_choices(library, rarity)),
        }
    ]
    for field in ("cost_overdraft", "cost_once_per_battle", "cost_hp"):
        out.append({"id": field, "hint": COST_DOCS[field]})
    if on_miss_allowed(rarity):
        out.append({"id": "cost_on_miss", "hint": COST_DOCS["cost_on_miss"]})
    return out


def hp_cost_permille(library: ContentLibrary | None) -> int:
    """``cost_hp: true`` 的 HP 代價（最大 HP 的 ‰）：剛好用滿 ``allowance.hp_cap`` 的量。"""
    if library is None:
        return DEFAULT_HP_PERMILLE
    allowance = library.budget.allowance
    if allowance.hp_per_permille <= 0:
        return DEFAULT_HP_PERMILLE
    return max(1, min(999, allowance.hp_cap // allowance.hp_per_permille))


def apply_cost_choices(data: dict[str, Any], library: ContentLibrary | None) -> None:
    """就地把提議的代價欄位換成 ``cost``（:data:`COST_FLAG_FIELDS`）。"""
    cost: dict[str, Any] = dict(data.get("cost") or {})
    if data.pop("cost_once_per_battle", None):
        cost["uses_per_battle"] = ONCE_PER_BATTLE
    if data.pop("cost_hp", None):
        cost["hp_percent"] = hp_cost_permille(library)
    on_miss = data.pop("cost_on_miss", None)
    if on_miss:
        cost["on_miss"] = list(on_miss)
    if cost:
        data["cost"] = cost


def cost_choices_of(skill_cost: dict[str, Any], structure: dict[str, Any]) -> dict[str, Any]:
    """手寫技能的代價 → 提議欄位（往返與 few-shot 用）。``skill_cost`` 是原技能的 ``cost``（含
    數值）；``structure`` 是 :func:`~trpg.skillgen.proposal_numbers.split_numbers` 後的資料，其中
    ``cost.on_miss`` 已去掉數值。回傳要加進提議的欄位（數值本身由補值器放回）。"""
    out: dict[str, Any] = {}
    if skill_cost.get("uses_per_battle") is not None:
        out["cost_once_per_battle"] = True
    if skill_cost.get("hp_percent") is not None:
        out["cost_hp"] = True
    cost = structure.get("cost")
    if isinstance(cost, dict) and cost.get("on_miss"):
        out["cost_on_miss"] = cost.pop("on_miss")
    return out
