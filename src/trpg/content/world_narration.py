"""說書人敘述的 schema 與降級模板（Phase 5B-3；``docs/phases/Phase5計畫.md`` 第 14 節）。

- :class:`StoryText`：說書人（LLM 或降級模板）的輸出，純資料。``trpg.narrative`` 產生、
  ``trpg.world`` 核對（2.3：world 不匯入 narrative／llm，兩邊都從這裡匯入）。只有文字與
  「從允許清單挑 ID」，沒有任何能改數值、給東西的欄位（守則 3；09 9.6.7 #3、#6）。
- :func:`story_problems`：不看世界狀態的靜態檢查（場景與欄位是否相符），兩邊共用。
- :class:`StoryTemplates`（``content/world/narration.yaml``）：模型不可用或輸出一直不合法時的
  降級文字（``docs/專案計畫.md`` 3.1），以及各區的說書語氣（09 9.6.10 #107）。
"""

from __future__ import annotations

import re
import string
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.loader import load_content_file
from trpg.content.schemas import ContentModel
from trpg.content.world_situations import OUTCOMES, Outcome
from trpg.shared.errors import ContentError

__all__ = [
    "ACTOR_MAX_CHARS",
    "MORE_MAX_CHARS",
    "MOTIVE_MAX_CHARS",
    "STORY_REFS_MAX",
    "STORY_SCENES",
    "STORY_SENTENCES_MAX",
    "STORY_TEMPLATES_FILE",
    "TEMPLATE_FIELDS",
    "TEXT_MAX_CHARS",
    "StoryAllowed",
    "StoryScene",
    "StoryTemplates",
    "StoryText",
    "allowed_problems",
    "fill_template",
    "load_story_templates",
    "sentence_count",
    "story_problems",
    "story_template_problems",
]

STORY_TEMPLATES_FILE: Final = "world/narration.yaml"

StoryScene = Literal["event", "situation", "outcome", "chat"]
"""``event``＝事件開場（挑骨架＋角色＋動機＋旁白）；``situation``＝情境判定前的情境敘述；
``outcome``＝情境判定的結果敘述；``chat``＝NPC 自由聊天的回話。"""
STORY_SCENES: Final[tuple[StoryScene, ...]] = ("event", "situation", "outcome", "chat")

TEXT_MAX_CHARS: Final = 150
"""短旁白／回話的長度上限（09 9.6.7 #7「約 1～3 句」；代決 5B3-6）。"""
STORY_SENTENCES_MAX: Final = 3
MORE_MAX_CHARS: Final = 400
"""「多講一點」的長度上限。"""
ACTOR_MAX_CHARS: Final = 24
MOTIVE_MAX_CHARS: Final = 60
STORY_REFS_MAX: Final = 4
"""每種引用（NPC、地點、線頭）最多幾個。"""

_SENTENCE_END = re.compile(r"[。！？!?]+[」』）)]*")


def sentence_count(text: str) -> int:
    """句數：以 ``。！？!?`` 結尾的句子數；最後一段沒有句號也算一句；空字串為 0。"""
    stripped = text.strip()
    if not stripped:
        return 0
    ends = len(_SENTENCE_END.findall(stripped))
    trailing = _SENTENCE_END.split(stripped)[-1].strip() != ""
    return ends + (1 if trailing else 0)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _check_ids(ids: tuple[str, ...]) -> tuple[str, ...]:
    if len(set(ids)) != len(ids):
        raise ValueError("引用的 ID 不可重複")
    return ids


_Ref = Field(default=(), max_length=STORY_REFS_MAX)


class StoryText(_Strict):
    """說書人的一段敘述（LLM 輸出或降級模板）。"""

    skeleton: str | None = Field(default=None, pattern=ID_PATTERN)
    """只有 ``event``：從允許的候選骨架挑一個（09 9.6.7 #6）。"""
    actor_zh: str = Field(default="", max_length=ACTOR_MAX_CHARS)
    """只有 ``event``：填角色（例：「一名腿上帶傷的行商」）。"""
    motive_zh: str = Field(default="", max_length=MOTIVE_MAX_CHARS)
    """只有 ``event``：動機。"""
    text_zh: str = Field(min_length=1, max_length=TEXT_MAX_CHARS)
    """短旁白／回話：1～3 句（9.6.7 #7）。"""
    more_zh: str = Field(default="", max_length=MORE_MAX_CHARS)
    """「多講一點」（可空）。"""
    npcs: tuple[str, ...] = _Ref
    locations: tuple[str, ...] = _Ref
    threads: tuple[str, ...] = _Ref

    @field_validator("npcs", "locations", "threads")
    @classmethod
    def _unique(cls, ids: tuple[str, ...]) -> tuple[str, ...]:
        for item in ids:
            if not re.fullmatch(ID_PATTERN, item):
                raise ValueError(f"ID 格式不正確：{item!r}")
        return _check_ids(ids)

    @field_validator("text_zh")
    @classmethod
    def _short(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("旁白不可空白")
        count = sentence_count(text)
        if count > STORY_SENTENCES_MAX:
            raise ValueError(f"旁白最多 {STORY_SENTENCES_MAX} 句（目前 {count} 句）")
        return text

    def texts(self) -> tuple[str, ...]:
        """所有文字欄位（禁止文字的檢查用）。"""
        return (self.actor_zh, self.motive_zh, self.text_zh, self.more_zh)


def story_problems(scene: StoryScene, story: StoryText) -> list[str]:
    """靜態檢查：``event`` 必須有骨架、角色、動機；其他場景不可有。"""
    problems: list[str] = []
    if scene == "event":
        if story.skeleton is None:
            problems.append("事件敘述必須挑一個骨架（skeleton）")
        if not story.actor_zh.strip():
            problems.append("事件敘述必須填角色（actor_zh）")
        if not story.motive_zh.strip():
            problems.append("事件敘述必須填動機（motive_zh）")
    else:
        if story.skeleton is not None:
            problems.append(f"{scene} 敘述不可挑骨架")
        if story.actor_zh or story.motive_zh:
            problems.append(f"{scene} 敘述不可填角色或動機")
    return problems


@dataclass(frozen=True)
class StoryAllowed:
    """一次敘述允許引用的東西（全部排序）。``trpg.world.narration.story_choices`` 依世界狀態算，
    外層拿去餵說書人、引擎拿來核對，兩邊同一份規則（:func:`allowed_problems`）。"""

    skeletons: tuple[str, ...] = ()
    """``event``：可以挑的骨架；其他場景為空。"""
    npcs: tuple[str, ...] = ()
    """不看骨架就允許的 NPC。"""
    skeleton_npcs: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    """``event``：挑了某個骨架後另外允許的 NPC（該骨架的 ``npcs``）。"""
    locations: tuple[str, ...] = ()
    """角色看得到的地點。"""
    threads: tuple[str, ...] = ()
    """角色持有的有效線頭。"""
    forbidden: tuple[str, ...] = ()
    """不可出現在文字裡的字串（未發現的隱藏地點名、NPC 祕密原文）。"""

    def npcs_for(self, skeleton: str | None) -> tuple[str, ...]:
        extra = self.skeleton_npcs.get(skeleton, ()) if skeleton is not None else ()
        return tuple(sorted({*self.npcs, *extra}))

    def all_npcs(self) -> tuple[str, ...]:
        """所有可能允許的 NPC（JSON schema 的列舉用）。"""
        extra = {n for ids in self.skeleton_npcs.values() for n in ids}
        return tuple(sorted({*self.npcs, *extra}))


def allowed_problems(scene: StoryScene, story: StoryText, allowed: StoryAllowed) -> list[str]:
    """:func:`story_problems`＋引用都在允許清單＋文字不含禁止字串（14.3、14.5）。"""
    problems = story_problems(scene, story)
    if scene == "event" and story.skeleton not in allowed.skeletons:
        problems.append(f"骨架 {story.skeleton} 不在可挑的候選裡（{'、'.join(allowed.skeletons)}）")
    npcs = set(allowed.npcs_for(story.skeleton))
    problems += [f"不能提到 NPC {n}" for n in story.npcs if n not in npcs]
    problems += [f"不能提到地點 {loc}" for loc in story.locations if loc not in allowed.locations]
    problems += [f"不能提到沒有持有的線頭 {t}" for t in story.threads if t not in allowed.threads]
    texts = story.texts()
    problems += [f"文字不可提到「{w}」" for w in allowed.forbidden if any(w in s for s in texts)]
    return problems


# ---------------------------------------------------------------------------
# 降級模板
# ---------------------------------------------------------------------------

TEMPLATE_FIELDS: Final[Mapping[str, frozenset[str]]] = {
    "event_text": frozenset({"who", "location"}),
    "event_more": frozenset({"who", "want", "obstacle", "stakes", "location"}),
    "event_more_no_obstacle": frozenset({"who", "want", "stakes", "location"}),
    "situation_text": frozenset({"who", "approach", "location"}),
    "situation_more": frozenset({"who", "stakes", "approach", "location"}),
    "outcome_text": frozenset({"who", "approach", "location"}),
    "chat_text": frozenset({"name", "location"}),
}
"""各模板可用的佔位符（載入時檢查）。"""


def _placeholders(text: str) -> list[str]:
    try:
        return [name for _, name, _, _ in string.Formatter().parse(text) if name is not None]
    except ValueError as exc:
        raise ValueError(f"模板格式錯誤：{text!r}（{exc}）") from exc


class StoryTemplates(ContentModel):
    """``content/world/narration.yaml``：降級文字與各區語氣。"""

    tones: dict[str, str] = Field(default_factory=dict)
    """區域 → 說書語氣（09 9.6.10 #107；給 LLM 的系統指令）。"""
    event_text: str = Field(min_length=1)
    event_more: str = Field(min_length=1)
    event_more_no_obstacle: str = Field(min_length=1)
    situation_text: str = Field(min_length=1)
    situation_more: str = ""
    outcome_text: dict[Outcome, str]
    chat_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> StoryTemplates:
        problems = story_template_problems(self)
        if problems:
            raise ValueError("；".join(problems))
        return self

    def summary(self) -> str:
        return f"說書降級模板（{len(self.tones)} 區語氣）"


def story_template_problems(templates: StoryTemplates) -> list[str]:
    """佔位符只能用 :data:`TEMPLATE_FIELDS` 規定的名稱；結果三段都要有。"""
    problems: list[str] = []
    fields: list[tuple[str, str, str]] = [
        (name, name, str(getattr(templates, name)))
        for name in (
            "event_text",
            "event_more",
            "event_more_no_obstacle",
            "situation_text",
            "situation_more",
            "chat_text",
        )
    ]
    fields += [(f"outcome_text.{k}", "outcome_text", v) for k, v in templates.outcome_text.items()]
    for label, kind, text in fields:
        try:
            names = _placeholders(text)
        except ValueError as exc:
            problems.append(f"{label}：{exc}")
            continue
        unknown = sorted(set(names) - TEMPLATE_FIELDS[kind])
        if unknown:
            problems.append(f"{label} 有不認得的佔位符：{'、'.join(unknown)}")
    missing = [o for o in OUTCOMES if o not in templates.outcome_text]
    if missing:
        problems.append(f"outcome_text 缺少：{'、'.join(missing)}")
    for region, tone in templates.tones.items():
        if not re.fullmatch(ID_PATTERN, region):
            problems.append(f"tones 的區域 ID 格式不正確：{region!r}")
        if not tone.strip():
            problems.append(f"tones 的 {region} 不可空白")
    return problems


def fill_template(text: str, values: Mapping[str, str], *, limit: int) -> str:
    """格式化模板（缺少的佔位符填空字串），超過 ``limit`` 字時截斷。"""
    names = set(_placeholders(text))
    filled = text.format_map({n: values.get(n, "") for n in names})
    return filled[:limit]


def load_story_templates(path: Path, *, regions: Collection[str]) -> StoryTemplates:
    """讀 ``narration.yaml``；``tones`` 的區域必須有地點圖。"""
    templates = load_content_file(path, StoryTemplates)
    unknown = sorted(set(templates.tones) - set(regions))
    if unknown:
        raise ContentError(path, f"tones 的區域沒有地點圖：{'、'.join(unknown)}")
    return templates
