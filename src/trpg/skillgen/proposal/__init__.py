"""LLM 技能提議模型（Phase 3E-2g 原型；設計見 ``docs/phases/Phase4-LLM技能提議設計.md``）。

LLM 不直接寫 :class:`~trpg.content.skills.SkillDef`（扁平的 ``EffectSpec`` 有約 40 個選填欄位，
LLM 容易填錯又難以定位），而是填「提議」：效果、形狀、條件、觸發都是以 ``type``（觸發為 ``event``）
區分的 discriminated union，每一支只有該原語自己的參數，範圍與可用值取自內容資料
（``skill_primitives.yaml`` 的 ``params``、``skill_shapes.yaml``、``skill_conditions.yaml``、
``skill_triggers.yaml`` 與各 ID 表）。

流程：:func:`build_proposal_models` 由內容庫產生模型與 JSON Schema → :func:`evaluate_proposal`
依序做「提議驗證（``proposal``）→ 轉成 ``SkillDef``（``skill``）→ 跨檔案驗證與預算（``rules``）」，
任一階段失敗就回傳結構化的 :class:`ProposalError`（路徑、代碼、中文原因、可用值），給 LLM 重試。

**提議不含數值**（Phase 4-L3，使用者決定 #3）：骰子、倍率、持續回合、距離、AP、法力、冷卻、條件門檻
等一律不在模型裡，只留結構與列舉選擇（見 :mod:`trpg.skillgen.proposal_numbers`）。轉成 ``SkillDef``
時由 :data:`~trpg.skillgen.proposal_numbers.NumberFiller` 補數值（預設是保守的最小補值，正式流程由
4-L5 的預算器補）。模型的說明文字取自內容資料的 ``llm_hint``。

ID、稀有度、階級、來源由呼叫端（:class:`ProposalContext`）決定，LLM 不能填。原型不涵蓋的部分
（複合技能第二段、反應、陷阱、修正規則、非原語的巢狀效果等）見設計文件。

子模組（Phase R1d 自單一檔案拆出，內容未改；外部一律從本套件匯入）：

- :mod:`~trpg.skillgen.proposal.models`：常數、錯誤／情境／結果／模型容器與型別組合小工具。
- :mod:`~trpg.skillgen.proposal.params`：原語參數 → 欄位型別、可用 ID、效果欄位分支、可用狀態。
- :mod:`~trpg.skillgen.proposal.builder`：效果、形狀、條件、觸發、變奏、反應的模型（``_Builder``）。
- :mod:`~trpg.skillgen.proposal.build`：頂層版型分支與 :func:`build_proposal_models`。
- :mod:`~trpg.skillgen.proposal.convert`：提議 ↔ ``SkillDef`` 的轉換。
- :mod:`~trpg.skillgen.proposal.evaluate`：驗證與錯誤回饋。
"""

from __future__ import annotations

from trpg.skillgen.proposal.build import (
    ACTIVE_ONLY_FIELDS as ACTIVE_ONLY_FIELDS,
)
from trpg.skillgen.proposal.build import (
    CATEGORIES as CATEGORIES,
)
from trpg.skillgen.proposal.build import (
    LAYOUT_SPLITS as LAYOUT_SPLITS,
)
from trpg.skillgen.proposal.build import (
    WEAPON_REQ_BY_CATEGORY as WEAPON_REQ_BY_CATEGORY,
)
from trpg.skillgen.proposal.build import (
    WEAPON_REQ_DOC as WEAPON_REQ_DOC,
)
from trpg.skillgen.proposal.build import (
    build_proposal_models as build_proposal_models,
)
from trpg.skillgen.proposal.build import (
    composite_allowed as composite_allowed,
)
from trpg.skillgen.proposal.build import (
    kind_choices as kind_choices,
)
from trpg.skillgen.proposal.builder import (
    reaction_events as reaction_events,
)
from trpg.skillgen.proposal.convert import (
    PLACEHOLDER_NAME as PLACEHOLDER_NAME,
)
from trpg.skillgen.proposal.convert import (
    combined_skill_name as combined_skill_name,
)
from trpg.skillgen.proposal.convert import (
    proposal_from_skill as proposal_from_skill,
)
from trpg.skillgen.proposal.convert import (
    to_skill_def as to_skill_def,
)
from trpg.skillgen.proposal.evaluate import (
    _proposal_path as _proposal_path,
)
from trpg.skillgen.proposal.evaluate import (
    _pydantic_errors as _pydantic_errors,
)
from trpg.skillgen.proposal.evaluate import (
    _rule_error as _rule_error,
)
from trpg.skillgen.proposal.evaluate import (
    _skill_path as _skill_path,
)
from trpg.skillgen.proposal.evaluate import (
    _topic_errors as _topic_errors,
)
from trpg.skillgen.proposal.evaluate import (
    _unheld_errors as _unheld_errors,
)
from trpg.skillgen.proposal.evaluate import (
    evaluate_proposal as evaluate_proposal,
)
from trpg.skillgen.proposal.evaluate import (
    feedback_payload as feedback_payload,
)
from trpg.skillgen.proposal.models import (
    CALLER_FIELDS as CALLER_FIELDS,
)
from trpg.skillgen.proposal.models import (
    CLOSED_SKELETONS as CLOSED_SKELETONS,
)
from trpg.skillgen.proposal.models import (
    LLM_ID_PREFIX as LLM_ID_PREFIX,
)
from trpg.skillgen.proposal.models import (
    NESTED_EFFECT_TYPES as NESTED_EFFECT_TYPES,
)
from trpg.skillgen.proposal.models import (
    PROPOSAL_KINDS as PROPOSAL_KINDS,
)
from trpg.skillgen.proposal.models import (
    ProposalContext as ProposalContext,
)
from trpg.skillgen.proposal.models import (
    ProposalError as ProposalError,
)
from trpg.skillgen.proposal.models import (
    ProposalModels as ProposalModels,
)
from trpg.skillgen.proposal.models import (
    ProposalResult as ProposalResult,
)
from trpg.skillgen.proposal.models import (
    Stage as Stage,
)
from trpg.skillgen.proposal.params import (
    COUNT_CHOICES as COUNT_CHOICES,
)
from trpg.skillgen.proposal.params import (
    EXACTLY_ONE_PARAMS as EXACTLY_ONE_PARAMS,
)
from trpg.skillgen.proposal.params import (
    TOP_ONLY_DAMAGE_PARAMS as TOP_ONLY_DAMAGE_PARAMS,
)
from trpg.skillgen.proposal.params import (
    ZONE_AFFECTS as ZONE_AFFECTS,
)
from trpg.skillgen.proposal.params import (
    _Refs as _Refs,
)
from trpg.skillgen.proposal.params import (
    budget_statuses as budget_statuses,
)
from trpg.skillgen.proposal.params import (
    grantable_skills as grantable_skills,
)
from trpg.skillgen.proposal.params import (
    rarity_statuses as rarity_statuses,
)
from trpg.skillgen.proposal_numbers import NumberFiller as NumberFiller

__all__ = [
    "LLM_ID_PREFIX",
    "NumberFiller",
    "ProposalContext",
    "ProposalError",
    "ProposalModels",
    "ProposalResult",
    "budget_statuses",
    "build_proposal_models",
    "combined_skill_name",
    "composite_allowed",
    "evaluate_proposal",
    "feedback_payload",
    "kind_choices",
    "proposal_from_skill",
    "rarity_statuses",
    "reaction_events",
    "to_skill_def",
]
