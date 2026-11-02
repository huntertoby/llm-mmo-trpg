"""誓約模板（``content/world/oaths.yaml``，Phase 5A-6 接點；06 6.26、09 9.6.10 #106、18 18.6）。

大世界的立誓（主城、小鎮、營火，同時 1 個；一直有效到自己解除，解除後現實 1 天內不能再立）由
:mod:`trpg.world.growth` 的世界動作處理。本模組只定義資料：

- :class:`OathTemplateDef`：一種誓約模板（難度檔＝易／中／難，加成由引擎查表）與它的參數。
- :class:`OathProposal`：LLM（或選單）提議的「模板＋參數」（pydantic；``trpg.llm`` 與 ``trpg.world``
  共用，同 5B-2 的 ``SituationProposal``）。:func:`oath_problems` 是靜態合法性檢查。

18.6 的 15 種模板內容、戰鬥中的加成與違反判定在 5C-3（代決 5A6-9）；``world/oaths.yaml`` 不存在時
內容庫的 ``world_oaths`` 為 ``None``，立誓一律被拒。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = [
    "OATH_TEXT_LIMIT",
    "OathDifficulty",
    "OathParamDef",
    "OathProposal",
    "OathTable",
    "OathTemplateDef",
    "oath_problems",
]

OATH_TEXT_LIMIT = 200
"""玩家誓言文字的上限（只存紀錄；給 LLM 時包在 ``<player_input>``）。"""

type OathDifficulty = Literal["easy", "medium", "hard"]
"""難度檔（06 6.26「依條件難度分 3 檔」；18.6 的易／中／難）。"""


class OathParamDef(ContentModel):
    """模板的一個參數：``choice``（從 ``choices`` 挑）或 ``int``（``min``～``max``）。"""

    id: str = Field(pattern=ID_PATTERN)
    kind: Literal["choice", "int"]
    choices: tuple[str, ...] = ()
    min: int = 0
    max: int = 0

    @model_validator(mode="after")
    def _check(self) -> OathParamDef:
        if self.kind == "choice":
            if not self.choices or len(set(self.choices)) != len(self.choices):
                raise ValueError(f"參數 {self.id}：choice 要有不重複的 choices")
        elif self.choices or self.min > self.max:
            raise ValueError(f"參數 {self.id}：int 不設 choices，且 min ≤ max")
        return self


class OathTemplateDef(ContentModel):
    """一種誓約模板（18.6）：難度檔決定加成（引擎查表，5C-3）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    difficulty: OathDifficulty
    params: tuple[OathParamDef, ...] = ()

    @model_validator(mode="after")
    def _unique_params(self) -> OathTemplateDef:
        ids = [p.id for p in self.params]
        if len(set(ids)) != len(ids):
            raise ValueError(f"誓約 {self.id}：參數重複")
        return self


class OathTable(ContentModel):
    """``content/world/oaths.yaml``。"""

    cooldown_seconds: int = Field(default=86400, ge=0)
    """解除後多久不能再立（#106「現實 1 天」）。"""
    templates: tuple[OathTemplateDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> OathTable:
        ids = [t.id for t in self.templates]
        if len(set(ids)) != len(ids):
            raise ValueError("誓約模板 ID 重複")
        return self

    def template_by_id(self) -> dict[str, OathTemplateDef]:
        return {t.id: t for t in self.templates}

    def summary(self) -> str:
        return f"{len(self.templates)} 種誓約模板、解除冷卻 {self.cooldown_seconds} 秒"


class OathProposal(BaseModel):
    """立誓的提議：模板與參數（LLM 只能從白名單模板挑、從允許值填，06 6.26 安全流程第 2 步）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    template: str = Field(pattern=ID_PATTERN)
    params: dict[str, str | int] = Field(default_factory=dict)


def oath_problems(table: OathTable, proposal: OathProposal) -> list[str]:
    """提議的靜態合法性（繁體中文；空＝合法）：模板存在、參數齊全且在允許值內、沒有多餘參數。"""
    template = table.template_by_id().get(proposal.template)
    if template is None:
        return [f"沒有誓約模板 {proposal.template}"]
    problems: list[str] = []
    defs = {p.id: p for p in template.params}
    extra = sorted(set(proposal.params) - set(defs))
    if extra:
        problems.append(f"誓約 {template.id} 沒有這些參數：{', '.join(extra)}")
    for param in template.params:
        value = proposal.params.get(param.id)
        if value is None:
            problems.append(f"誓約 {template.id} 缺少參數 {param.id}")
        elif param.kind == "choice":
            if value not in param.choices:
                problems.append(f"參數 {param.id} 必須是 {'、'.join(param.choices)} 之一")
        elif not isinstance(value, int) or not param.min <= value <= param.max:
            problems.append(f"參數 {param.id} 必須是 {param.min}～{param.max} 的整數")
    return problems
