"""提議 ↔ :class:`~trpg.content.skills.SkillDef` 的轉換（補數值、ID 雜湊、組合式名稱）。

自 :mod:`trpg.skillgen.proposal` 拆出（Phase R1d），內容未改。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import (
    BaseModel,
    ValidationError,
)

from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    ICON_PROP_KEY,
    SkillDef,
    skill_elements,
)
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal.models import CALLER_FIELDS, LLM_ID_PREFIX, ProposalContext
from trpg.skillgen.proposal_costs import (
    apply_cost_choices,
    cost_choices_of,
)
from trpg.skillgen.proposal_layouts import (
    skill_layout,
)
from trpg.skillgen.proposal_numbers import (
    NumberFiller,
    split_numbers,
)
from trpg.skillgen.scaling import fit_scaling, grant_dual, retarget_scaling
from trpg.skillgen.self_penalty import penalty_cost, penalty_of_cost


def _skill_id(body: Mapping[str, Any]) -> str:
    text = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return LLM_ID_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _stack_target(effect: Any, library: ContentLibrary) -> Any:
    """累積／消耗層數的效果：``affects`` 由層數的 ``owner`` 決定（累積在自己身上 → ``self``，疊在
    敵人身上 → ``enemies``）；LLM 填的對象不採用。"""
    if not isinstance(effect, dict) or effect.get("type") not in ("add_stack", "consume_stack"):
        return effect
    stack = library.ruleset.stacks.by_id().get(str(effect.get("stack")))
    if stack is None:
        return effect
    if stack.owner == "target":  # 省略時預設就是敵方；有填才改成敵方
        return {**effect, "affects": "enemies"} if "affects" in effect else effect
    return {**effect, "affects": "self"}


def _skill_data(
    proposal: BaseModel,
    ctx: ProposalContext,
    fill: NumberFiller,
    library: ContentLibrary | None = None,
) -> dict[str, Any]:
    data = proposal.model_dump(mode="json", exclude_none=True)
    data.pop("layout", None)
    penalty = data.pop("cost_penalty", None)  # 自己付的代價（3-50）→ cost.self_status／overdraft
    if penalty is not None:
        data["cost"] = {**data.get("cost", {}), **penalty_cost(library, penalty)}
    if data.pop("cost_overdraft", None):  # 透支（3-50b）：不算自身狀態，可以並用
        data["cost"] = {**data.get("cost", {}), "overdraft": 1}
    apply_cost_choices(data, library)  # 每場一次、HP 代價、失手反噬（4-L8）
    if library is not None:  # 層數的對象由層數決定（3-52），LLM 只挑層數
        data["effects"] = [_stack_target(e, library) for e in data.get("effects", [])]
    data["narrative"] = {"concept": data.pop("concept"), "cast_flavor": data.pop("cast_flavor")}
    data.update(tier=ctx.tier, rarity=ctx.rarity, rank=ctx.rank)
    data["provenance"] = {"origin": ctx.origin, "created_by": "llm"}
    data = fill(data)
    data["name_zh"] = _combined_name(data, library)
    data["id"] = _skill_id(data)
    return data


PLACEHOLDER_NAME = "提議技能"
"""結構不合法、算不出組合式名稱時的名稱（轉換會在 ``skill`` 階段報錯，不會出現在遊戲裡）。"""


def combined_skill_name(library: ContentLibrary, skill: SkillDef) -> str:
    """組合式名稱「元素・骨架」（沒有元素就只有骨架；和隨機組合器、4-L7 的退回名稱同一做法）。
    LLM 提議沒有名稱欄位（4-L8）：轉成技能時先用它，命名步驟（``trpg.llm.naming``）再換成
    生成的名稱。"""
    skeleton = plain_name(skill.skeleton, library)
    elements = sorted(e.display_name for e in skill_elements(skill))
    return f"{elements[0]}・{skeleton}" if elements else skeleton


def _combined_name(data: dict[str, Any], library: ContentLibrary | None) -> str:
    if library is None:
        return PLACEHOLDER_NAME
    try:
        probe = SkillDef.model_validate({**data, "name_zh": PLACEHOLDER_NAME, "id": "skill_probe"})
    except ValidationError:
        return PLACEHOLDER_NAME
    return combined_skill_name(library, probe)


def to_skill_def(
    proposal: BaseModel,
    ctx: ProposalContext,
    fill: NumberFiller,
    library: ContentLibrary | None = None,
) -> SkillDef:
    """已驗證的提議（只有結構）→ :class:`SkillDef`：``fill`` 補上數值（骰子、倍率、持續、AP、法力、
    冷卻等；見 :mod:`trpg.skillgen.proposal_numbers`）。ID 由補完數值後的內容雜湊而來；同一份
    提議加同一份數值永遠得到相同 ID。``ctx.hero_attributes`` 有值（且給了 ``library``）時縮放屬性
    改取主角最高的允許屬性（見 :class:`ProposalContext`）。

    schema 層級的錯誤丟 :class:`pydantic.ValidationError`（:func:`evaluate_proposal` 轉成
    ``stage="skill"`` 的錯誤）。"""
    data = _skill_data(proposal, ctx, fill, library)
    skill = SkillDef.model_validate(data)
    if library is None:
        return skill
    # 武器技一律看武器大類的主屬性（3H-6，不看主角屬性）；其他技能跟主角最高屬性（3H-3）；
    # 沒有主角屬性時收進允許範圍（3H-7：在範圍內不動，否則取範圍裡第一個）
    fitted = (
        fit_scaling(skill, library)
        if ctx.hero_attributes is None
        else grant_dual(  # 3I-3：稀有以上、主角第二高與最高差 ≤ 4 時，以 30% 機率加心智第二屬性
            retarget_scaling(skill, ctx.hero_attributes, library), ctx.hero_attributes, library
        )
    )
    attr, second = fitted.scaling_attr, fitted.secondary_scaling_attr
    if attr == skill.scaling_attr and second == skill.secondary_scaling_attr:
        return skill
    data = {k: v for k, v in data.items() if k not in ("id", "secondary_scaling_attr")}
    data["scaling_attr"] = attr.value
    if second is not None:
        data["secondary_scaling_attr"] = second.value
    data["id"] = _skill_id(data)
    return SkillDef.model_validate(data)


_SUPPORTED_SKILL_KEYS = frozenset(
    {
        "id",
        "schema_version",
        "description_zh",
        "tier",
        "rank",
        "rarity",
        "kind",
        "skeleton",
        "category",
        "weapon_req",
        "ap_cost",
        "scaling_attr",
        "element",
        "shape",
        "effects",
        "condition",
        "trigger",
        "cost",
        "cost_penalty",
        "cost_overdraft",
        "cost_once_per_battle",
        "cost_hp",
        "cost_on_miss",
        "reaction",
        "followup",
        "tags",
        "narrative",
        "provenance",
        "variants",
    }
)


def proposal_from_skill(skill: SkillDef, library: ContentLibrary) -> dict[str, Any]:
    """手寫技能 → 提議 JSON（few-shot 範例與結構往返測試用；數值欄位已移除）。用到提議模型沒有的
    欄位時丟 ``ValueError``。要連同數值一起取得時用
    :func:`~trpg.skillgen.proposal_numbers.split_numbers`。"""
    full = skill.model_dump(mode="json", exclude_defaults=True)
    data, _ = split_numbers(full, library)
    data.update(cost_choices_of(full.get("cost") or {}, data))  # 4-L8 的代價欄位
    data.pop("name_zh", None)  # 名稱由命名步驟產生（4-L8），不在提議裡
    data.pop(ICON_PROP_KEY, None)  # 圖示道具只有手寫技能填（IP-1，06 6.36），不進 LLM 範例
    if isinstance(data.get("cost"), dict):  # 自己付的代價（3-50）→ cost_penalty
        penalty, overdraft = penalty_of_cost(data["cost"])
        if penalty is not None:
            data["cost_penalty"] = penalty
        if overdraft:
            data["cost_overdraft"] = True
        if not data["cost"]:
            del data["cost"]
    unsupported = sorted(set(data) - _SUPPORTED_SKILL_KEYS)
    if unsupported:
        raise ValueError(f"{skill.id} 用到提議格式沒有的欄位：{', '.join(unsupported)}")
    for key in CALLER_FIELDS:
        data.pop(key, None)
    narrative = data.pop("narrative", {})
    data["concept"] = narrative.get("concept", "")
    data["cast_flavor"] = narrative.get("cast_flavor", "")
    data["kind"] = skill.kind
    return {"layout": skill_layout(library, skill), **data}
