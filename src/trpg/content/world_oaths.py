"""誓約模板（``content/world/oaths.yaml``；5A-6 接點、5C-3 內容；06 6.26、#106、18 18.6）。

大世界的立誓（主城、小鎮、營火，同時 1 個；一直有效到自己解除，解除後現實 1 天內不能再立）由
:mod:`trpg.world.growth` 的世界動作處理。本模組只定義資料：

- :class:`OathTemplateDef`：一種誓約模板（難度檔＝易／中／難，加成由引擎查表）與它的參數。
- :class:`OathProposal`：LLM（或選單）提議的「模板＋參數」（pydantic；``trpg.llm`` 與 ``trpg.world``
  共用，同 5B-2 的 ``SituationProposal``）。:func:`oath_problems` 是靜態合法性檢查。

5C-3 起：

- :class:`OathCheck`：模板的 **判定**（引擎 :mod:`trpg.engine.oaths` 看戰鬥事件判定違反；18.6 的 15
  種模板對到 14 種判定）；參數經 ``bind`` 填進判定的欄位（:func:`resolve_check`）。
- 加成依難度查表（``OathTable.bonuses``：難度 → 狀態 ID，06 6.26「數值由引擎查表」）；違反＝移除
  加成＋``penalty_status`` ``penalty_rounds`` 回合（#27）。

``world/oaths.yaml`` 不存在時內容庫的 ``world_oaths`` 為 ``None``，立誓一律被拒。跨檔案檢查（狀態、
標籤、元素、中文名）在 :mod:`trpg.content.library`。
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = [
    "AT_END_CHECKS",
    "OATH_CHECK_FIELDS",
    "OATH_TEXT_LIMIT",
    "OathCheck",
    "OathCheckKind",
    "OathDifficulty",
    "OathDifficultyBy",
    "OathParamDef",
    "OathProposal",
    "OathTable",
    "OathTemplateDef",
    "oath_problems",
    "resolve_check",
]

OATH_TEXT_LIMIT = 200
"""玩家誓言文字的上限（只存紀錄；給 LLM 時包在 ``<player_input>``）。"""

type OathDifficulty = Literal["easy", "medium", "hard"]
"""難度檔（06 6.26「依條件難度分 3 檔」；18.6 的易／中／難）。"""

type OathCheckKind = Literal[
    "forbid_skill_tag",
    "forbid_skill_category",
    "forbid_skill_tag_until_hp",
    "no_retreat",
    "attack_each_turn",
    "end_turn_high",
    "end_turn_off_surface",
    "forbid_reaction",
    "damage_element_only",
    "protect_allies",
    "no_move_first_turn",
    "solo",
    "min_melee_kills",
    "min_status_applied",
]
"""引擎判定得了的誓約條件（5C-3；新增模板只要組合這些種類，不改引擎）。"""

AT_END_CHECKS: Final = frozenset({"min_melee_kills", "min_status_applied"})
"""只能在戰鬥結束時判定的種類（「每場至少……」）；其他都在戰鬥中判定。"""

type OathCheckField = Literal["category", "element", "status", "count"]
"""模板參數能填進的判定欄位。"""

OATH_CHECK_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "forbid_skill_tag": ("tags",),
    "forbid_skill_category": ("category",),
    "forbid_skill_tag_until_hp": ("tags",),
    "damage_element_only": ("element",),
    "min_melee_kills": ("count",),
    "min_status_applied": ("status", "count"),
}
"""各判定種類必填的欄位（沒列的種類不需要欄位）。"""


class OathCheck(ContentModel):
    """誓約的判定（引擎 :mod:`trpg.engine.oaths`）。欄位只在對應的種類有意義（見
    :data:`OATH_CHECK_FIELDS`）；模板的參數由 ``bind`` 在立誓時填進來（:func:`resolve_check`）。"""

    kind: OathCheckKind
    tags: tuple[str, ...] = ()
    """技能標籤（``forbid_skill_tag``／``forbid_skill_tag_until_hp``：帶任一個就算）。"""
    category: Literal["spell", "weapon"] | None = None
    """技能類別（``forbid_skill_category``）：法術／武器技。"""
    element: str | None = Field(default=None, pattern=ID_PATTERN)
    """只准造成這個元素的傷害（``damage_element_only``）。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    """要施加的狀態（``min_status_applied``）。"""
    count: int = Field(default=0, ge=0)
    """次數門檻（``min_melee_kills``、``min_status_applied``）。"""
    hp_permille: int = Field(default=500, ge=1, le=1000)
    """``forbid_skill_tag_until_hp``：HP 低於最大 HP 的這個千分比之前不能用（18.6「低於一半」）。"""

    @property
    def at_end(self) -> bool:
        """只能在戰鬥結束時判定。"""
        return self.kind in AT_END_CHECKS

    def missing(self) -> list[str]:
        """必填但沒填的欄位。"""
        return [
            name
            for name in OATH_CHECK_FIELDS.get(self.kind, ())
            if getattr(self, name) in (None, (), 0)
        ]


class OathParamDef(ContentModel):
    """模板的一個參數：``choice``（從 ``choices`` 挑）或 ``int``（``min``～``max``）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = ""
    """參數的中文名（例「元素」；5C-3 起內容檔必填，``library`` 檢查）。"""
    kind: Literal["choice", "int"]
    choices: tuple[str, ...] = ()
    choice_names_zh: dict[str, str] = Field(default_factory=dict)
    """``choice`` 每個值的中文名（鍵＝``choices``；5C-3 起內容檔必填）。"""
    min: int = 0
    max: int = 0

    @model_validator(mode="after")
    def _check(self) -> OathParamDef:
        if self.kind == "choice":
            if not self.choices or len(set(self.choices)) != len(self.choices):
                raise ValueError(f"參數 {self.id}：choice 要有不重複的 choices")
            extra = sorted(set(self.choice_names_zh) - set(self.choices))
            if extra:
                raise ValueError(f"參數 {self.id}：choice_names_zh 有不在 choices 的值：{extra}")
        elif self.choices or self.choice_names_zh or self.min > self.max:
            raise ValueError(f"參數 {self.id}：int 不設 choices，且 min ≤ max")
        return self

    def values(self) -> tuple[str | int, ...]:
        """所有允許值（``int`` 依序）。"""
        if self.kind == "choice":
            return self.choices
        return tuple(range(self.min, self.max + 1))

    def value_zh(self, value: str | int) -> str:
        """值的中文（``choice`` 查 ``choice_names_zh``，沒有就原樣）。"""
        return self.choice_names_zh.get(str(value), str(value))


class OathDifficultyBy(ContentModel):
    """依某個參數的值決定難度（18.6 模板 6：N＝1 易、N＝2 中）。"""

    param: str = Field(pattern=ID_PATTERN)
    levels: dict[str, OathDifficulty]
    """參數值（字串）→ 難度；要剛好涵蓋所有允許值。"""


class OathTemplateDef(ContentModel):
    """一種誓約模板（18.6）：難度檔決定加成（引擎查表，5C-3）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = ""
    difficulty: OathDifficulty
    difficulty_by: OathDifficultyBy | None = None
    params: tuple[OathParamDef, ...] = ()
    check: OathCheck | None = None
    """判定（5C-3 起內容檔必填）；``None``＝不判定（只有測試樣本）。"""
    bind: dict[str, OathCheckField] = Field(default_factory=dict)
    """參數 ID → 填進判定的哪個欄位。"""

    @model_validator(mode="after")
    def _check_template(self) -> OathTemplateDef:
        ids = [p.id for p in self.params]
        if len(set(ids)) != len(ids):
            raise ValueError(f"誓約 {self.id}：參數重複")
        unknown = sorted(set(self.bind) - set(ids))
        if unknown:
            raise ValueError(f"誓約 {self.id}：bind 引用了不存在的參數 {unknown}")
        if self.check is not None:
            wanted = OATH_CHECK_FIELDS.get(self.check.kind, ())
            stray = sorted(f for f in self.bind.values() if f not in wanted)
            if stray:
                raise ValueError(f"誓約 {self.id}：判定 {self.check.kind} 沒有欄位 {stray}")
            bound = set(self.bind.values())
            missing = [m for m in self.check.missing() if m not in bound]
            if missing:
                raise ValueError(f"誓約 {self.id}：判定 {self.check.kind} 缺少 {missing}")
        self._check_difficulty_by()
        return self

    def _check_difficulty_by(self) -> None:
        by = self.difficulty_by
        if by is None:
            return
        param = next((p for p in self.params if p.id == by.param), None)
        if param is None:
            raise ValueError(f"誓約 {self.id}：difficulty_by 的參數 {by.param} 不存在")
        values = {str(v) for v in param.values()}
        if set(by.levels) != values:
            raise ValueError(f"誓約 {self.id}：difficulty_by 要剛好涵蓋 {sorted(values)}")

    def difficulty_for(self, params: dict[str, str | int]) -> OathDifficulty:
        """這組參數的難度（有 ``difficulty_by`` 時依參數值）。"""
        by = self.difficulty_by
        if by is not None and by.param in params:
            return by.levels.get(str(params[by.param]), self.difficulty)
        return self.difficulty

    def param_by_id(self) -> dict[str, OathParamDef]:
        return {p.id: p for p in self.params}

    def params_zh(self, params: dict[str, str | int]) -> str:
        """參數的中文（例「元素：火焰」；依模板的參數順序，沒有參數時空字串）。"""
        return "、".join(
            f"{p.name_zh or p.id}：{p.value_zh(params[p.id])}"
            for p in self.params
            if p.id in params
        )


class OathTable(ContentModel):
    """``content/world/oaths.yaml``。"""

    cooldown_seconds: int = Field(default=86400, ge=0)
    """解除後多久不能再立（#106「現實 1 天」）。"""
    templates: tuple[OathTemplateDef, ...] = Field(min_length=1)
    bonuses: dict[OathDifficulty, str] = Field(default_factory=dict)
    """難度 → 加成狀態（``statuses.yaml``；06 6.26「持續加成，依條件難度分 3 檔」）。"""
    penalty_status: str | None = Field(default=None, pattern=ID_PATTERN)
    """違反時施加的 debuff（#27「本場加成移除＋debuff 2 回合」）。"""
    penalty_rounds: int = Field(default=2, ge=1, le=2)
    """debuff 的回合數（#27：2 回合）。"""

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


def resolve_check(template: OathTemplateDef, params: dict[str, str | int]) -> OathCheck | None:
    """把參數填進模板的判定（``bind``）；沒有判定的模板回 ``None``。參數要先過
    :func:`oath_problems`。"""
    if template.check is None:
        return None
    update: dict[str, object] = {}
    for param_id, field_name in sorted(template.bind.items()):
        value = params[param_id]
        update[field_name] = int(value) if field_name == "count" else str(value)
    return template.check.model_copy(update=update)
