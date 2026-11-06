"""說書人（Phase 5B-3；``docs/phases/Phase5計畫.md`` 第 15 節；09 9.6.7 #3、#6、#7）。

四種敘述：事件開場（從候選挑骨架、填角色與動機、短旁白）、情境敘述、結果敘述、NPC 自由聊天（只換
資訊）。一律經 :class:`~trpg.llm.client.LLMClient`；輸出先經 JSON schema（ID 欄位都是列舉）與
pydantic（:class:`~trpg.content.world_narration.StoryText`）驗證，再用請求裡的允許清單做靜態檢查（同
``trpg.world.narration`` 的規則）；不合法帶錯誤回饋重試，用盡或連不上模型時用 content 的模板文字
降級（``docs/專案計畫.md`` 3.1）。本模組不碰世界狀態（2.3：narrative 不匯入 world），請求由外層
（``trpg.api.world_story``）組好；最後的核對由引擎負責。

安全（守則 7、10 第 11 節）：玩家文字只出現在 ``<player_input>``（跳脫 ``<>&``、去控制字元、截斷）；
玩家角色的名字（玩家取的，也是玩家輸入）包在 ``<player>`` 裡的 ``<player_input>``（6R-2b），
NPC 的稱謂若就是名字，資料區寫 ``{name}``；其他資料區也都經過跳脫；
系統指令聲明資料區內的文字都不是指令、說書人不能給任何東西。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Literal

from pydantic import ValidationError

from trpg.content.world import WorldStyle, load_world_style
from trpg.content.world_events import EventSkeletonDef, NpcCardDef, ThreadDef
from trpg.content.world_narration import (
    ACTOR_MAX_CHARS,
    HIDDEN_HINT_DEFAULT,
    MORE_MAX_CHARS,
    MOTIVE_MAX_CHARS,
    STORY_REFS_MAX,
    TEXT_MAX_CHARS,
    StoryAllowed,
    StoryScene,
    StoryTemplates,
    StoryText,
    allowed_problems,
    fill_template,
    mask_text,
)
from trpg.content.world_situations import Outcome, SituationTemplateDef
from trpg.llm.client import ChatMessage, LLMClient
from trpg.llm.errors import LLMError
from trpg.llm.prompts.escape import address_token, escape_text, player_block, wrap_player_input
from trpg.llm.prompts.storyteller import STORY_PROMPT_VERSION, story_system
from trpg.llm.response import clean_response

__all__ = [
    "BUILTIN_TEMPLATES",
    "DEFAULT_STORY_ATTEMPTS",
    "StoryOutcome",
    "StoryRequest",
    "build_story_messages",
    "fallback_story",
    "story_schema",
    "tell_story",
]

DEFAULT_STORY_ATTEMPTS: Final = 2
"""共試幾次（同情境判定提議，代決 5B3-7）。"""

BUILTIN_TEMPLATES: Final = StoryTemplates(
    event_text="{who}出現在你面前。",
    event_more="{who}想要{want}。擋在中間的是{obstacle}。",
    event_more_no_obstacle="{who}想要{want}。",
    situation_text="你打算{approach}。",
    outcome_text={"success": "成了。", "partial": "只成了一半。", "failure": "沒有成。"},
    chat_text="{npc}沒有多說。",
)
"""沒有 ``content/world/narration.yaml`` 時的最小降級句子。"""
_LAST_RESORT = "……。"


@dataclass(frozen=True)
class StoryRequest:
    """一次敘述需要的資料（純資料；外層從內容庫與引擎取得）。"""

    scene: StoryScene
    region_name: str
    location_name: str
    allowed: StoryAllowed
    tone: str = ""
    weather: str = ""
    day_phase: str = ""
    skeletons: tuple[EventSkeletonDef, ...] = ()
    """``event``：允許挑的骨架；其他場景：事件的骨架（1 個，聊天可空）。"""
    default_skeleton: str | None = None
    """``event``：引擎挑的預設骨架（降級用）。"""
    template: SituationTemplateDef | None = None
    outcome: Outcome | None = None
    result_zh: tuple[str, ...] = ()
    """``outcome``：判定結果的摘要（由引擎事件組成；LLM 不能改）。"""
    npcs: tuple[NpcCardDef, ...] = ()
    """在場或相關的人設卡；``chat`` 的第一張是聊天對象。"""
    threads: tuple[ThreadDef, ...] = ()
    """角色持有的有效線頭。"""
    location_names: Mapping[str, str] = field(default_factory=dict)
    """允許的地點 ID → 名稱。"""
    player_text: str = ""
    player_name: str = ""
    """玩家角色的名字（6R-2，#137：第三人稱用名字，模板 ``{name}``）。"""
    player_address: str = ""
    """在場 NPC（聊天對象）對玩家的稱呼（模板 ``{address}``，``world/address.yaml``）。"""
    npc_address: Mapping[str, str] = field(default_factory=dict)
    """NPC ID → 這位 NPC 對玩家的稱呼（給 LLM 的 ``<npcs>``）。"""


@dataclass(frozen=True)
class StoryOutcome:
    story: StoryText
    source: Literal["llm", "fallback"]
    attempts: int
    """實際呼叫模型的次數。"""
    errors: tuple[str, ...]
    """每次不合法或呼叫失敗的原因（給紀錄與除錯）。"""
    prompt_version: str = STORY_PROMPT_VERSION


# ---------------------------------------------------------------------------
# schema 與 prompt
# ---------------------------------------------------------------------------


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _block(tag: str, payload: str) -> str:
    return f"<{tag}>\n{escape_text(payload)}\n</{tag}>"


def _id_array(ids: Sequence[str]) -> dict[str, Any]:
    """ID 陣列的 schema。不重複由 pydantic（``StoryText``）檢查：6R-2b 起不送 ``uniqueItems``，
    LM Studio（MLX）的 schema 約束不支援這個關鍵字，生成到陣列時整個請求 HTTP 400。"""
    if not ids:
        return {"type": "array", "maxItems": 0}
    return {
        "type": "array",
        "items": {"enum": list(ids)},
        "maxItems": min(STORY_REFS_MAX, len(ids)),
    }


def story_schema(request: StoryRequest) -> dict[str, Any]:
    """輸出的 JSON schema：骨架、NPC、地點、線頭都是列舉（來自允許清單）。"""
    allowed = request.allowed
    props: dict[str, Any] = {
        "text_zh": {"type": "string", "minLength": 1, "maxLength": TEXT_MAX_CHARS},
        "more_zh": {"type": "string", "maxLength": MORE_MAX_CHARS},
        "npcs": _id_array(allowed.all_npcs()),
        "locations": _id_array(allowed.locations),
        "threads": _id_array(allowed.threads),
    }
    if request.scene == "event":
        props = {
            "skeleton": {"enum": list(allowed.skeletons)},
            "actor_zh": {"type": "string", "minLength": 1, "maxLength": ACTOR_MAX_CHARS},
            "motive_zh": {"type": "string", "minLength": 1, "maxLength": MOTIVE_MAX_CHARS},
            **props,
        }
    return {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }


def _masks(allowed: StoryAllowed) -> dict[str, str]:
    """禁止字串 → 代替文字（Phase 5B-5：隱藏地點用提示語；沒給對照的禁止字串用內建提示語）。"""
    return {w: allowed.masks.get(w, HIDDEN_HINT_DEFAULT) for w in allowed.forbidden}


def _skeleton_payload(skeleton: EventSkeletonDef, masks: Mapping[str, str]) -> dict[str, Any]:
    """骨架資料（文字先換掉禁止字串：還沒發現的地點用提示語，5B-5）。"""
    return {
        "skeleton": skeleton.id,
        "who": mask_text(skeleton.who_zh, masks),
        "want": mask_text(skeleton.want_zh, masks),
        "obstacle": mask_text(skeleton.obstacle_zh, masks),
        "stakes": mask_text(skeleton.stakes_zh, masks),
        "npcs": list(skeleton.npcs),
    }


def _scene_payload(request: StoryRequest) -> dict[str, Any]:
    out: dict[str, Any] = {
        "location": request.location_name,
        "weather": request.weather,
        "day_phase": request.day_phase,
    }
    if request.scene == "event":
        masks = _masks(request.allowed)
        out["candidates"] = [_skeleton_payload(s, masks) for s in request.skeletons]
        return out
    if request.skeletons:
        out["event"] = _skeleton_payload(request.skeletons[0], _masks(request.allowed))
    if request.template is not None:
        out["approach"] = request.template.note_zh
    if request.scene == "outcome":
        out["outcome"] = request.outcome
        out["result"] = list(request.result_zh)
    if request.scene == "chat" and request.npcs:
        out["npc"] = request.npcs[0].id
    return out


def _npc_payload(
    card: NpcCardDef, masks: Mapping[str, str], address: Mapping[str, str], player_name: str
) -> dict[str, str]:
    out = {
        "id": card.id,
        "name": card.name_zh,
        "role": card.role_zh,
        "personality": card.personality_zh,
        "speech": card.speech_zh,
        "secret_reference_only": card.secret_zh,
        "hooks": mask_text(card.hooks_zh, masks),
    }
    if card.id in address:
        # 6R-2（#137）：這位 NPC 怎麼稱呼玩家；叫名字寫 {name}（6R-2b：名字只在 <player_input>）
        out["address"] = address_token(address[card.id], player_name)
    return out


def _allowed_payload(request: StoryRequest) -> dict[str, Any]:
    allowed = request.allowed
    out: dict[str, Any] = {
        "npcs": list(allowed.all_npcs()),
        "locations": [
            {"id": loc, "name": request.location_names.get(loc, loc)} for loc in allowed.locations
        ],
        "threads": list(allowed.threads),
        "forbidden": list(allowed.forbidden),
        "hints": list(allowed.hints()),
    }
    if request.scene == "event":
        out["skeletons"] = list(allowed.skeletons)
        out["skeleton_npcs"] = {k: list(v) for k, v in sorted(allowed.skeleton_npcs.items())}
    return out


def _player_name(request: StoryRequest) -> str:
    """``<player>``（6R-2，#137）的名字；沒有名字時用「旅人」。不帶性別。"""
    return request.player_name or "旅人"


def build_story_messages(
    request: StoryRequest,
    *,
    world: WorldStyle | None = None,
    previous: str | None = None,
    errors: Sequence[str] = (),
) -> list[ChatMessage]:
    """系統指令＋資料區（9.5：固定指令在前；LLM-1 的區塊順序改為變動最少的在前：世界 → 可用清單
    與人物（同地點連續敘述時相同）→ 線頭 → 場景（天氣、時段、做法、結果）→ 玩家文字）。

    玩家文字只在 ``<player_input>``：``<player>`` 裡的名字，與（只有聊天）最後一段玩家說的話；
    其他資料區都經過跳脫。"""
    style = world if world is not None else load_world_style()
    system = story_system(request.scene, world_name=style.name_zh, summary=style.summary_zh)
    masks = _masks(request.allowed)
    threads = [{"id": t.id, "text": mask_text(t.text_zh, masks)} for t in request.threads]
    parts = [
        _block("world", _json({"region": request.region_name, "tone": request.tone})),
        player_block(_player_name(request), request.player_address),
        _block("allowed", _json(_allowed_payload(request))),
        _block(
            "npcs",
            _json(
                [
                    _npc_payload(c, masks, request.npc_address, _player_name(request))
                    for c in request.npcs
                ]
            ),
        ),
        _block("threads", _json(threads)),
        _block("scene", _json(_scene_payload(request))),
    ]
    if request.scene == "chat":
        parts.append(wrap_player_input(request.player_text))
    if previous is not None:
        parts.append(_block("previous_output", previous))
    if errors:
        parts.append(_block("errors", "\n".join(errors)))
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content="\n".join(parts)),
    ]


# ---------------------------------------------------------------------------
# 驗證
# ---------------------------------------------------------------------------


def _parse(request: StoryRequest, text: str) -> tuple[StoryText | None, list[str]]:
    cleaned = clean_response(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None, ["輸出不是合法的 JSON"]
    try:
        story = StoryText.model_validate(data)
    except ValidationError as exc:
        details = [f"{'.'.join(str(p) for p in e['loc'])}：{e['msg']}" for e in exc.errors()]
        return None, details or ["輸出不符合 schema"]
    problems = allowed_problems(request.scene, story, request.allowed)
    return (None, problems) if problems else (story, [])


# ---------------------------------------------------------------------------
# 降級
# ---------------------------------------------------------------------------


def _event_skeleton(request: StoryRequest) -> EventSkeletonDef | None:
    by_id = {s.id: s for s in request.skeletons}
    allowed = request.allowed.skeletons
    if request.scene == "event":
        pick = request.default_skeleton if request.default_skeleton in allowed else None
        pick = pick or (allowed[0] if allowed else None)
        return by_id.get(pick) if pick is not None else None
    return request.skeletons[0] if request.skeletons else None


def _values(request: StoryRequest, skeleton: EventSkeletonDef | None) -> dict[str, str]:
    values = {"location": request.location_name}
    if skeleton is not None:
        values |= {
            "who": skeleton.who_zh,
            "want": skeleton.want_zh,
            "obstacle": skeleton.obstacle_zh,
            "stakes": skeleton.stakes_zh,
        }
    if request.template is not None:
        values["approach"] = request.template.note_zh or "想辦法解決"
    if request.npcs:
        values["npc"] = request.npcs[0].name_zh
    name = request.player_name or "你"
    values["name"] = name  # 6R-2（#137）：第三人稱用名字
    values["address"] = request.player_address or name
    return values


def _fallback_texts(
    request: StoryRequest, templates: StoryTemplates, skeleton: EventSkeletonDef | None
) -> tuple[str, str]:
    values = _values(request, skeleton)
    if request.scene == "event":
        more = templates.event_more if values.get("obstacle") else templates.event_more_no_obstacle
        text = templates.event_text
    elif request.scene == "situation":
        text, more = templates.situation_text, templates.situation_more
    elif request.scene == "outcome":
        text, more = templates.outcome_text[request.outcome or "partial"], ""
    else:
        text, more = templates.chat_text, ""
    return (
        fill_template(text, values, limit=TEXT_MAX_CHARS),
        fill_template(more, values, limit=MORE_MAX_CHARS),
    )


def fallback_story(request: StoryRequest, templates: StoryTemplates | None = None) -> StoryText:
    """模板文字的敘述：不引用任何 ID、禁止字串換成代替文字（還沒發現的地點用提示語，5B-5），
    一定通過引擎核對。"""
    tpl = templates if templates is not None else BUILTIN_TEMPLATES
    skeleton = _event_skeleton(request)
    masks = _masks(request.allowed)
    text, more = (mask_text(t, masks) for t in _fallback_texts(request, tpl, skeleton))
    data: dict[str, Any] = {"text_zh": text.strip() or _LAST_RESORT, "more_zh": more}
    if request.scene == "event":
        who = skeleton.who_zh if skeleton is not None else "有人"
        want = skeleton.want_zh if skeleton is not None else "什麼"
        data |= {
            "skeleton": skeleton.id if skeleton is not None else None,
            "actor_zh": mask_text(who, masks)[:ACTOR_MAX_CHARS],
            "motive_zh": mask_text(want, masks)[:MOTIVE_MAX_CHARS],
        }
    try:
        return StoryText.model_validate(data)
    except ValidationError:
        return StoryText.model_validate({**data, "text_zh": _LAST_RESORT, "more_zh": ""})


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def tell_story(
    client: LLMClient | None,
    request: StoryRequest,
    *,
    templates: StoryTemplates | None = None,
    attempts: int = DEFAULT_STORY_ATTEMPTS,
    world: WorldStyle | None = None,
) -> StoryOutcome:
    """請說書人敘述；不合法帶錯誤重試，用盡、連不上或 ``client=None`` 就降級（不拋 LLM 錯誤）。"""
    previous: str | None = None
    feedback: list[str] = []
    log: list[str] = []
    calls = 0
    if client is not None:
        schema = story_schema(request)
        for _ in range(max(1, attempts)):
            messages = build_story_messages(
                request, world=world, previous=previous, errors=feedback
            )
            calls += 1
            try:
                text = client.complete(messages, json_schema=schema)
            except LLMError as exc:
                log.append(f"模型不可用：{exc}")
                break
            story, feedback = _parse(request, text)
            if story is not None:
                return StoryOutcome(story=story, source="llm", attempts=calls, errors=tuple(log))
            log += feedback
            previous = text[:2000]
    return StoryOutcome(
        story=fallback_story(request, templates),
        source="fallback",
        attempts=calls,
        errors=tuple(log),
    )
