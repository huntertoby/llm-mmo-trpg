"""技能工坊的「組到一半的技能」（Phase 3F-1）。

草稿就是技能定義（``content/skills/*.yaml`` 的 JSON 形式，:class:`~trpg.content.skills.SkillDef`）
的部分欄位：可以缺任何欄位。:func:`build_skill` 補上 ``id``（由內容雜湊而來，同一份草稿永遠得到
相同 ID）與 ``name_zh`` 後以 schema 驗證，失敗時以中文列出原因。

每一步「完成」的判斷（:func:`step_complete`）只看草稿有沒有填好該步驟的必要欄位；填的值合不合法由
:mod:`trpg.skillgen.options`（選項）與 :mod:`trpg.skillgen.draft_check`（檢查）負責。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skills import SkillDef
from trpg.shared.errors import TrpgError
from trpg.skillgen.option_models import StepId

__all__ = [
    "DEFAULT_NAME_ZH",
    "WORKSHOP_ID_PREFIX",
    "Draft",
    "DraftError",
    "build_skill",
    "draft_id",
    "draft_skeleton",
    "step_complete",
    "validation_messages",
]

type Draft = Mapping[str, Any]
"""組到一半的技能：技能定義 JSON 的部分欄位。"""

WORKSHOP_ID_PREFIX = "skill_ws_"
DEFAULT_NAME_ZH = "工坊技能"


class DraftError(TrpgError):
    """草稿無法組成技能（schema 驗證失敗）；``messages`` 是逐條的中文原因。"""

    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("；".join(messages))


def draft_id(draft: Draft) -> str:
    """草稿的技能 ID：``skill_ws_`` ＋ 內容（不含 ``id``）的 SHA-256 前 10 碼。"""
    body = {k: v for k, v in draft.items() if k != "id"}
    text = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return WORKSHOP_ID_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


_UNION_TAG = re.compile(r"^(?:int|str|float|bool|dict|list|tuple|none|literal\[.*|function-.*|.*\[.*)$")
"""pydantic 聯集（``int | Literal["weapon"]``）的分支標記：不是欄位名，不顯示在位置裡。"""


def _location(loc: tuple[int | str, ...]) -> str:
    parts: list[str] = []
    for item in loc:
        if isinstance(item, str) and _UNION_TAG.match(item):
            continue
        if isinstance(item, int):
            parts.append(f"[{item}]")
        else:
            parts.append(f".{item}" if parts else item)
    return "".join(parts)


def validation_messages(exc: ValidationError) -> list[str]:
    """pydantic 驗證錯誤 → 中文訊息（自訂檢查的訊息本來就是中文；去掉 ``Value error,`` 前綴）。"""
    out: list[str] = []
    for error in exc.errors(include_url=False):
        message = str(error["msg"]).removeprefix("Value error, ")
        where = _location(tuple(error["loc"]))
        out.append(f"{where}：{message}" if where else message)
    return out


def build_skill(draft: Draft, overrides: Mapping[str, Any] | None = None) -> SkillDef:
    """以 schema 驗證草稿（補上 ``id``、``name_zh``；``overrides`` 覆寫個別欄位，例如試算稀有度）。
    失敗時拋出 :class:`DraftError`。"""
    data: dict[str, Any] = {**draft, **(overrides or {})}
    data.setdefault("name_zh", DEFAULT_NAME_ZH)
    data.setdefault("effects", [])  # 修正技能沒有效果原語
    data["id"] = data.get("id") or draft_id(draft)
    try:
        return SkillDef.model_validate(data)
    except ValidationError as exc:
        raise DraftError(validation_messages(exc)) from exc


def draft_skeleton(draft: Draft, library: ContentLibrary) -> SkeletonDef | None:
    """草稿選的骨架（沒有選、或不是啟用的骨架時為 ``None``）。"""
    skeleton = library.skeletons.get(str(draft.get("skeleton")))
    return skeleton if skeleton is not None and skeleton.enabled else None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _basics_complete(draft: Draft, skeleton: SkeletonDef) -> bool:
    kind = draft.get("kind")
    if kind not in skeleton.kinds:
        return False
    needed = ["category", "weapon_req", "scaling_attr", "tier"]
    if kind == "active":
        needed.append("ap_cost")
    if kind == "passive":
        needed.append("trigger")
    if kind == "reaction":
        needed.append("reaction")
    return all(draft.get(name) is not None for name in needed)


def _shape_complete(draft: Draft, library: ContentLibrary) -> bool:
    shape = _mapping(draft.get("shape"))
    definition = library.ruleset.shapes.by_id().get(str(shape.get("type")))
    if definition is None:
        return False
    return all(shape.get(n) is not None for n, p in definition.params.items() if p.required)


def _effects_complete(draft: Draft) -> bool:
    if draft.get("kind") == "modifier":
        return bool(draft.get("modifiers"))
    return bool(draft.get("effects"))


def _condition_complete(draft: Draft, skeleton: SkeletonDef) -> bool:
    if not skeleton.requires_condition:
        return True
    effects = draft.get("effects") or ()
    return draft.get("condition") is not None or any(
        _mapping(e).get("condition") is not None for e in effects
    )


def _followup_complete(draft: Draft, library: ContentLibrary) -> bool:
    follow = _mapping(draft.get("followup"))
    if not follow:
        return True  # 動作段可省略
    shape = _mapping(follow.get("shape"))
    definition = library.ruleset.shapes.by_id().get(str(shape.get("type")))
    if follow.get("skeleton") is None or definition is None or not follow.get("effects"):
        return False
    if follow.get("when") == "delayed" and follow.get("release") is None:
        return False  # 延遲段（3F-4b）要選何時釋放
    return all(shape.get(n) is not None for n, p in definition.params.items() if p.required)


def step_complete(step: StepId, draft: Draft, library: ContentLibrary) -> bool:
    """草稿是否已經填好 ``step`` 的必要欄位（不檢查前面的步驟）。"""
    skeleton = draft_skeleton(draft, library)
    if step == "skeleton" or skeleton is None:
        return skeleton is not None
    checks: dict[StepId, Callable[[], bool]] = {
        "basics": lambda: _basics_complete(draft, skeleton),
        "shape": lambda: _shape_complete(draft, library),
        "effects": lambda: _effects_complete(draft),
        "followup": lambda: _followup_complete(draft, library),
        "condition": lambda: _condition_complete(draft, skeleton),
        "cost": lambda: True,  # 代價全部可省略（主動技能的最低花費由檢查提示，3-48c）
        "rarity": lambda: draft.get("rarity") is not None,
        "variants": lambda: True,  # 戰場變奏全部可省略（Phase 3-25b）
    }
    return checks[step]()
