"""工坊選項的說明與組合規則（Phase 3H-8）：全部由資料產生，不在這裡寫死數字。

- :func:`resource_cost_text`：耗費資源（法力／耐力）的說明，數字取自 ``core.yaml`` 的
  ``resources.stamina_regen``、``roguelite.yaml`` 的 ``refill_after_battle``、``campfire_after``。
- :func:`composition_info`：原語的組合規則（``position``、``sole_effect``、``others_affect``、
  ``max_per_skill``、``active_only``）→ 選項 ``info`` 的標章與說明句。
- :func:`composition_block`：依已填的效果判斷這個原語現在能不能再加，不能時回傳原因（中文）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import PrimitiveDef

__all__ = ["composition_block", "composition_info", "cost_step_text", "resource_cost_text"]

_NAMES: dict[str, str] = {"mana": "法力", "stamina": "耐力"}


def _after_battle(library: ContentLibrary, resource: str, *, regen: int) -> str:
    if resource in library.roguelite.refill_after_battle:
        return "每場打贏後回滿"
    after = "、".join(f"第 {n} 場" for n in library.roguelite.campfire_after)
    only = f"只有營火回滿（{after}之後）"
    return f"戰鬥之間不回復，{only}" if regen else only


def resource_cost_text(library: ContentLibrary, resource: Literal["mana", "stamina"]) -> str:
    """「耗費資源」欄位的說明：回復規則取自設定（3H-5），不寫死。"""
    regen = library.ruleset.core.resources.stamina_regen if resource == "stamina" else 0
    during = f"戰鬥中每回合開始回復 {regen} 點" if regen else "戰鬥中不回復"
    share = "武器技；與格擋共用" if resource == "stamina" else "法術技"
    after = _after_battle(library, resource, regen=regen)
    return f"施放花的{_NAMES[resource]}（{share}）；{during}；{after}"


def cost_step_text(category: object) -> str:
    """「代價」步驟的說明：依類別寫法力或耐力。"""
    resource = {"weapon": "耐力", "spell": "法力"}.get(str(category))
    first = "法力或耐力（武器技花耐力、法術技花法力）" if resource is None else resource
    return f"{first}、冷卻、每場次數、生命、自身狀態、源力；代價越重，可用預算越多"


def composition_info(primitive: PrimitiveDef) -> dict[str, Any]:
    """選項 ``info`` 的組合規則：``composition``（原始規則）、``badges_zh``（短標章）、
    ``rules_zh``（說明句）。沒有任何規則時回傳空 dict。"""
    badges: list[str] = []
    rules: list[str] = []
    # active_only 幾乎每個原語都是：不當標章也不寫說明，種類不符時由 composition_block 標示不可用
    if primitive.sole_effect:
        badges.append("唯一效果")
        rules.append("必須是技能唯一的效果")
    if primitive.position is not None:
        where = "第一個" if primitive.position == "first" else "最後一個"
        order = "最先" if primitive.position == "first" else "最後"
        badges.append(f"必須{where}")
        rules.append(f"必須是技能的{where}效果（一律{order}結算）")
    if primitive.max_per_skill is not None:
        badges.append(f"最多 {primitive.max_per_skill} 個")
        rules.append(f"一個技能最多 {primitive.max_per_skill} 個")
    if primitive.others_affect is not None:
        badges.append("其他效果限自己")
        rules.append("同一技能的其他效果必須只作用在施放者自己")
    if not badges:
        return {}
    return {
        "composition": {
            "position": primitive.position,
            "sole_effect": primitive.sole_effect,
            "others_affect": primitive.others_affect,
            "max_per_skill": primitive.max_per_skill,
            "active_only": primitive.active_only,
        },
        "badges_zh": badges,
        "rules_zh": rules,
    }


def composition_block(
    primitive: PrimitiveDef,
    existing: Sequence[Mapping[str, Any]],
    library: ContentLibrary,
    *,
    kind: object,
    allowed_affects: Sequence[str],
) -> tuple[str | None, str | None]:
    """``(不可用的原因, 必須套用的對象)``：依已填的效果與種類，這個原語現在能不能再加。

    不可用的原因為 ``None`` 表示可以加；第二項是「已有帶 ``others_affect`` 的效果」時，新加的
    其他效果必須使用的 ``affects``。"""
    by_id = library.ruleset.primitives.by_id()
    types = [str(e.get("type")) for e in existing]
    others = [by_id[t] for t in dict.fromkeys(types) if t in by_id and t != primitive.id]
    reason = _own_block(primitive, existing, types, kind)
    for other in others:
        if reason is None and other.sole_effect:
            reason = f"已有「{other.name_zh}」，它必須是技能唯一的效果"
    forced = next((o.others_affect for o in others if o.others_affect is not None), None)
    if reason is None and forced is not None and forced not in allowed_affects:
        reason = "已有要求其他效果只作用在自己的效果，這個效果不能只作用在自己"
    return reason, forced


def _own_block(
    primitive: PrimitiveDef, existing: Sequence[Mapping[str, Any]], types: list[str], kind: object
) -> str | None:
    if primitive.active_only and kind != "active":
        return "只能用在主動技"
    limit = primitive.max_per_skill
    if limit is not None and types.count(primitive.id) >= limit:
        return f"已達上限（一個技能最多 {limit} 個）"
    if primitive.sole_effect and types:
        return "必須是技能唯一的效果；先移除其他效果"
    if primitive.others_affect is not None and any(
        e.get("type") != primitive.id and e.get("affects") != primitive.others_affect
        for e in existing
    ):
        return "先把其他效果的對象改成「自己」"
    return None
