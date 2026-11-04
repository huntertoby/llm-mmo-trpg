"""主線劇情技能的 LLM 提議（Phase 6L-2；07 7.6「骨架固定、每人相同；LLM 只依玩家的關鍵字換元素、
名稱、描述（同預算）」；06 6.34.7 #126 名稱與描述照取得地點的界域）。

兩步，都只提議，數值不動（守則 3）：

1. **元素**：玩家的關鍵字對得到的元素選單（:func:`~trpg.skillgen.story_theme.story_elements`）有
   原本以外的元素時，請模型挑一個（:mod:`trpg.llm.prompts.story`，schema 用 ``enum``）；不合格帶錯誤
   重試，最多 ``max_attempts`` 次。換元素由 :func:`~trpg.skillgen.story_theme.retheme` 做（預算必須
   完全相同，否則不換）。
2. **名稱與描述**：交給命名步驟（:func:`~trpg.llm.naming.name_skill`，``region`` 是取得地點的區域，
   雲嶺偏東方）；換了元素時要求文字提到新的元素（``before``）。

任何一步失敗（模型關閉、用盡重試、命名退回組合式名稱）＝整招用內容版（``source="content"``）。
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm.candidate_source import mock_naming_client
from trpg.llm.client import LLMClient, MockLLMClient
from trpg.llm.errors import LLMBadResponse, LLMTimeout, LLMUnavailable
from trpg.llm.naming import name_skill
from trpg.llm.prompts.naming import NAMING_PROMPT_VERSION
from trpg.llm.prompts.story import STORY_PROMPT_VERSION, build_story_messages, story_schema
from trpg.llm.response import clean_response
from trpg.skillgen.story_theme import damage_elements, retheme

__all__ = [
    "DEFAULT_STORY_ATTEMPTS",
    "StoryProposal",
    "StoryProposer",
    "StorySkillRequest",
    "make_story_proposer",
    "mock_story_proposer",
    "propose_story_skill",
]

DEFAULT_STORY_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class StorySkillRequest:
    """``skill`` 是內容版（照角色階級、完整技能強度）；``elements`` 是可換的元素；``keywords`` 是
    玩家的關鍵字分布；``region`` 是取得地點的區域；``taken`` 是角色已有的技能名稱。"""

    skill: SkillDef
    elements: tuple[str, ...]
    keywords: tuple[tuple[str, int], ...]
    region: str | None
    weapon: str | None = None
    taken: Collection[str] = ()


@dataclass(frozen=True, slots=True)
class StoryProposal:
    source: str
    """``llm``＝元素（若有選單）與文字都由模型提議並通過檢查；``content``＝退回內容版。"""
    element: str | None = None
    name_zh: str | None = None
    concept: str | None = None
    cast_flavor: str | None = None
    attempts: int = 0
    codes: tuple[str, ...] = ()
    reason: str = ""
    seconds: float = 0.0

    @property
    def prompt_version(self) -> str:
        return f"{STORY_PROMPT_VERSION}+{NAMING_PROMPT_VERSION}"


type StoryProposer = Callable[[StorySkillRequest], StoryProposal]
type _Clock = Callable[[], float]


def _pick_element(
    client: LLMClient,
    *,
    library: ContentLibrary,
    request: StorySkillRequest,
    options: tuple[str, ...],
    max_attempts: int,
    codes: list[str],
) -> tuple[str | None, int, str]:
    """請模型從 ``options`` 挑元素；回傳（元素或 ``None``, 嘗試次數, 失敗原因）。"""
    names = {k.id: k.name_zh for k in library.keywords.keywords}
    payload = {
        "skill": {"name": request.skill.name_zh, "concept": request.skill.narrative.concept},
        "keywords": [{"id": k, "name": names.get(k, k), "count": n} for k, n in request.keywords],
        "options": [
            {"id": e, "name": library.elements.by_id(e).name_zh}  # type: ignore[arg-type]
            for e in options
        ],
    }
    errors: str | None = None
    reason = ""
    for number in range(1, max_attempts + 1):
        messages = build_story_messages(payload, errors=errors)
        try:
            raw = client.complete(messages, json_schema=story_schema(options))
        except LLMUnavailable as exc:
            codes.append("llm.unavailable")
            return None, number, f"llm.unavailable：{exc}"
        except (LLMTimeout, LLMBadResponse) as exc:
            codes.append("llm.timeout" if isinstance(exc, LLMTimeout) else "llm.bad_response")
            reason = codes[-1]
            continue
        try:
            data = json.loads(clean_response(raw))
        except json.JSONDecodeError:
            data = None
        element = data.get("element") if isinstance(data, dict) else None
        if isinstance(data, dict) and set(data) == {"element"} and element in options:
            return str(element), number, ""
        code = "story.not_json" if data is None else "story.element_not_offered"
        codes.append(code)
        reason = code
        errors = json.dumps(
            {
                "attempt": number,
                "errors": [{"code": code, "message": "element 只能是 options 的 id"}],
            },
            ensure_ascii=False,
        )
    return None, max_attempts, f"用盡 {max_attempts} 次（最後：{reason}）"


def propose_story_skill(
    client: LLMClient,
    library: ContentLibrary,
    request: StorySkillRequest,
    *,
    naming: LLMClient | None = None,
    max_attempts: int = DEFAULT_STORY_ATTEMPTS,
    clock: _Clock = time.perf_counter,
) -> StoryProposal:
    """見模組說明。``naming`` 省略時命名也用 ``client``。"""
    start = clock()
    skill = request.skill
    current = damage_elements(skill)
    options = tuple(e for e in request.elements if (e,) != current)
    codes: list[str] = []
    attempts = 0
    element: str | None = None
    themed = skill
    if options and current:
        element, attempts, reason = _pick_element(
            client,
            library=library,
            request=request,
            options=request.elements,
            max_attempts=max_attempts,
            codes=codes,
        )
        if element is None:
            return StoryProposal("content", attempts=attempts, codes=tuple(codes), reason=reason)
        if (element,) != current:
            changed = retheme(library, skill, element)
            if changed is None:
                return StoryProposal(
                    "content", attempts=attempts, codes=(*codes, "story.budget"), reason="預算不同"
                )
            themed = changed
    outcome = name_skill(
        naming if naming is not None else client,
        library,
        themed,
        taken=request.taken,
        max_attempts=max_attempts,
        before=skill if themed is not skill else None,
        region=request.region,
        weapon=request.weapon,
    )
    attempts += outcome.attempts
    codes += outcome.codes
    seconds = clock() - start
    if outcome.source != "llm":
        reason = outcome.reason or "命名退回"
        return StoryProposal(
            "content", attempts=attempts, codes=tuple(codes), reason=reason, seconds=seconds
        )
    text = outcome.text
    return StoryProposal(
        "llm",
        element=element if themed is not skill else None,
        name_zh=text.name_zh,
        concept=text.concept,
        cast_flavor=text.cast_flavor,
        attempts=attempts,
        codes=tuple(dict.fromkeys(codes)),
        seconds=seconds,
    )


def make_story_proposer(
    client: LLMClient, library: ContentLibrary, *, max_attempts: int = DEFAULT_STORY_ATTEMPTS
) -> StoryProposer:
    """真模型的劇情技能提議器。"""
    return lambda request: propose_story_skill(client, library, request, max_attempts=max_attempts)


def mock_story_proposer(
    library: ContentLibrary, *, max_attempts: int = DEFAULT_STORY_ATTEMPTS
) -> StoryProposer:
    """Mock（不需網路與金鑰）：元素挑選單第一個，名稱用 Mock 命名（確定性）。"""

    def propose(request: StorySkillRequest) -> StoryProposal:
        options = request.elements or ("fire",)
        element_client = MockLLMClient([json.dumps({"element": options[0]})] * max_attempts)
        current = damage_elements(request.skill)
        themed = request.skill
        if (options[0],) != current and current:
            themed = retheme(library, request.skill, options[0]) or request.skill
        return propose_story_skill(
            element_client,
            library,
            request,
            naming=mock_naming_client(library, themed, len(request.skill.id)),
            max_attempts=max_attempts,
        )

    return propose
