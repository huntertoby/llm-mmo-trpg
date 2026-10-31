"""目標形狀的 schema：``ParamDef``、``ShapeDef``、``ShapeTable``。"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills.constants import (
    REQUIRED_SHAPES,
    SHAPE_ROLES,
    SHAPE_TO_VALUES,
    SkillCategory,
    SkillRarity,
    Targeting,
    _unique,
)

# ---------------------------------------------------------------------------
# 形狀
# ---------------------------------------------------------------------------


class ParamDef(ContentModel):
    """形狀參數的範圍。``allow_weapon``：可寫成字串 ``"weapon"``（武器射程）。"""

    min: int
    max: int
    required: bool = True
    allow_weapon: bool = False
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）：中性描述，不含世界觀名詞、階段編號與欄位名。"""

    @model_validator(mode="after")
    def _range(self) -> ParamDef:
        if self.min > self.max:
            raise ValueError(f"參數範圍不合理：min {self.min} > max {self.max}")
        return self


class ShapeBudget(ContentModel):
    """形狀倍率（‰，``docs/phases/Phase2B計畫.md`` 4.2）。

    倍率 ＝ ``by_value_permille[參數值]``（有表格時），否則 ``base_permille ＋ per_unit_permille ×
    參數值``（``param`` 為 ``None`` 時只有 ``base_permille``）。

    ``non_power_by_value_permille``（BAL-13d，06 6.5「BAL-13c 定」）：形狀會衰減威力時（連鎖每跳
    −25%），不在 ``power_primitives`` 的效果（狀態、推擊、表面等照常施加的非數值效果）改查這張表
    （連鎖維持衰減前的倍率）；``power_primitives`` 是威力會跟著衰減的原語（傷害、治療、護盾……）。
    """

    base_permille: int = Field(default=1000, ge=1)
    param: str | None = None
    per_unit_permille: int = Field(default=0, ge=0)
    by_value_permille: dict[int, int] | None = None
    non_power_by_value_permille: dict[int, int] | None = None
    power_primitives: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ShapeBudget:
        tables = (self.by_value_permille, self.non_power_by_value_permille)
        if self.param is None and (self.per_unit_permille or any(tables)):
            raise ValueError("設定 per_unit_permille 或 by_value_permille 時必須指定 param")
        if any(table is not None and not table for table in tables):
            raise ValueError("by_value_permille 不可為空")
        if self.non_power_by_value_permille is not None and not self.power_primitives:
            raise ValueError("設定 non_power_by_value_permille 時必須列出 power_primitives")
        return self

    def permille_for(self, values: dict[str, int | str], primitive: str | None = None) -> int:
        """``values`` 是技能形狀已填的參數；表格缺少該值時回傳 ``base_permille``。給了
        ``primitive`` 且它不是威力原語時，有 ``non_power_by_value_permille`` 就查那張表。"""
        if self.param is None:
            return self.base_permille
        raw = values.get(self.param)
        value = raw if isinstance(raw, int) else 0
        table = self.by_value_permille
        if (
            self.non_power_by_value_permille is not None
            and primitive is not None
            and primitive not in self.power_primitives
        ):
            table = self.non_power_by_value_permille
        if table is not None:
            return table.get(value, self.base_permille)
        return self.base_permille + self.per_unit_permille * value


class ShapeCells(ContentModel):
    """形狀影響的格子數（純幾何，不看地圖上的牆壁；區域預算 ``zone`` 用，Phase 3E-1）。

    ``param`` 為 ``None`` 時固定 ``base`` 格；否則依參數值查 ``by_value``（涵蓋參數的整個範圍）。
    數字必須與 ``trpg.engine.skills.shapes`` 的幾何一致（``tests/engine/test_shape_cell_counts.py``
    在空地圖上逐一比對）。
    """

    base: int = Field(default=1, ge=1)
    param: str | None = None
    by_value: dict[int, int] | None = None

    @model_validator(mode="after")
    def _check(self) -> ShapeCells:
        if (self.param is None) != (self.by_value is None):
            raise ValueError("cell_count 的 param 與 by_value 必須一起指定")
        if self.by_value is not None and any(v < 1 for v in self.by_value.values()):
            raise ValueError("cell_count 的 by_value 格數必須 ≥ 1")
        return self

    def count_for(self, values: dict[str, int | str]) -> int:
        """``values`` 是技能形狀已填的參數；參數缺少或表格沒有該值時拋出 :class:`ValueError`。"""
        if self.param is None or self.by_value is None:
            return self.base
        raw = values.get(self.param)
        if not isinstance(raw, int) or raw not in self.by_value:
            raise ValueError(f"cell_count 沒有參數 {self.param} = {raw!r} 的格數")
        return self.by_value[raw]


class ShapeDef(ContentModel):
    """一種目標形狀。``targeting`` 決定 ``UseSkill`` 需要哪個欄位：

    ``unit``＝``target_id`` 或 ``target_object_id``、``tile``＝``target_pos``、
    ``direction``＝``direction``、``self``／``none``＝不需要。

    ``min_rarity``：使用此形狀的最低稀有度；``budget``：預算的形狀倍率（2B-2）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    targeting: Targeting
    llm_hint: str = ""
    """給 LLM 看的一句話說明（Phase 4-L3）。"""
    params: dict[str, ParamDef] = Field(default_factory=dict)
    min_rarity: SkillRarity = "common"
    budget: ShapeBudget = Field(default_factory=ShapeBudget)
    cell_count: ShapeCells | None = None
    """影響的格子數（沒有固定格數的形狀，例如連鎖，為 ``None``）。"""

    @model_validator(mode="after")
    def _check_cells(self) -> ShapeDef:
        cells = self.cell_count
        if cells is None or cells.param is None:
            return self
        spec = self.params.get(cells.param)
        if spec is None:
            raise ValueError(f"形狀 {self.id}：cell_count.param {cells.param!r} 不是這個形狀的參數")
        assert cells.by_value is not None
        missing = [v for v in range(spec.min, spec.max + 1) if v not in cells.by_value]
        if missing:
            raise ValueError(f"形狀 {self.id}：cell_count.by_value 缺少參數值 {missing}")
        return self

    @model_validator(mode="after")
    def _check_budget(self) -> ShapeDef:
        param = self.budget.param
        if param is None:
            return self
        spec = self.params.get(param)
        if spec is None:
            raise ValueError(f"形狀 {self.id}：budget.param {param!r} 不是這個形狀的參數")
        for table in (self.budget.by_value_permille, self.budget.non_power_by_value_permille):
            if table is not None:
                missing = [v for v in range(spec.min, spec.max + 1) if v not in table]
                if missing:
                    raise ValueError(f"形狀 {self.id}：by_value_permille 缺少參數值 {missing}")
        return self

    def summary(self) -> str:
        return self.name_zh


class ShapeConversion(ContentModel):
    """一種允許的形狀轉換（修正規則的 ``shape_to``，Phase 3D-3）：``from_shape`` 的技能轉成 ``to``。

    ``params``：轉換後固定的參數（例：直線 ``size: 3``）；``keep``：從原形狀帶過來的參數名稱
    （例：單體 → 連鎖保留 ``range``，直線 → 錐形保留 ``size``），超出新形狀的參數範圍時截斷到範圍內
    （原形狀的 ``range`` 為 ``"weapon"`` 時取施放者的武器射程）。只有表列的組合能轉換，其餘不轉。
    """

    from_shape: str = Field(pattern=ID_PATTERN)
    to: str = Field(pattern=ID_PATTERN)
    params: dict[str, int] = Field(default_factory=dict)
    keep: tuple[str, ...] = ()


class ShapeTable(ContentModel):
    """``content/skill_shapes.yaml``。"""

    shapes: tuple[ShapeDef, ...] = Field(min_length=1)
    conversions: tuple[ShapeConversion, ...] = ()
    """允許的形狀轉換（Phase 3D-3）。"""
    shape_roles: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """形狀的用途清單（Phase 3E-2f）：鍵必須是 :data:`SHAPE_ROLES`，值是存在的形狀 ID。"""

    @model_validator(mode="after")
    def _check(self) -> ShapeTable:
        _unique((s.id for s in self.shapes), "形狀")
        ids = {s.id for s in self.shapes}
        missing = [s for s in REQUIRED_SHAPES if s not in ids]
        if missing:
            raise ValueError(f"缺少引擎實作的形狀：{', '.join(missing)}")
        unknown = sorted(ids - set(REQUIRED_SHAPES))
        if unknown:
            raise ValueError(f"引擎尚未實作的形狀：{', '.join(unknown)}")
        self._check_conversions()
        self._check_roles(ids)
        return self

    def _check_roles(self, ids: set[str]) -> None:
        if not self.shape_roles:
            return
        unknown_roles = sorted(set(self.shape_roles) - set(SHAPE_ROLES))
        missing_roles = [r for r in SHAPE_ROLES if r not in self.shape_roles]
        if unknown_roles or missing_roles:
            raise ValueError(
                f"shape_roles 的用途必須是 {'、'.join(SHAPE_ROLES)}"
                f"（未知：{unknown_roles or '無'}；缺少：{missing_roles or '無'}）"
            )
        for role, role_ids in sorted(self.shape_roles.items()):
            bad = sorted(set(role_ids) - ids)
            if bad or not role_ids:
                raise ValueError(
                    f"shape_roles.{role}：形狀必須存在且至少一個（未知：{bad or '無'}）"
                )

    def _check_conversions(self) -> None:
        by_id = self.by_id()
        seen: set[tuple[str, str]] = set()
        for conv in self.conversions:
            where = f"conversions {conv.from_shape}→{conv.to}"
            source, target = by_id.get(conv.from_shape), by_id.get(conv.to)
            if source is None or target is None:
                raise ValueError(f"{where}：形狀不存在")
            if conv.to not in SHAPE_TO_VALUES:
                raise ValueError(f"{where}：目標形狀必須是 {'、'.join(SHAPE_TO_VALUES)}")
            if (conv.from_shape, conv.to) in seen:
                raise ValueError(f"{where}：重複的轉換")
            seen.add((conv.from_shape, conv.to))
            if set(conv.params) & set(conv.keep):
                raise ValueError(f"{where}：params 與 keep 不可有相同的參數")
            for name in conv.keep:
                if name not in source.params:
                    raise ValueError(f"{where}：keep {name} 不是 {conv.from_shape} 的參數")
            for name, value in conv.params.items():
                spec = target.params.get(name)
                if spec is None or not spec.min <= value <= spec.max:
                    raise ValueError(f"{where}：params {name}={value} 超出 {conv.to} 的範圍")
            given = {*conv.params, *conv.keep}
            required = {n for n, spec in target.params.items() if spec.required}
            if not required <= given:
                missing_params = "、".join(sorted(required - given))
                raise ValueError(f"{where}：缺少 {conv.to} 的必要參數 {missing_params}")
            if not given <= set(target.params):
                raise ValueError(f"{where}：{conv.to} 沒有這些參數")
        missing_targets = [
            v for v in SHAPE_TO_VALUES if not any(c.to == v for c in self.conversions)
        ]
        if self.conversions and missing_targets:
            raise ValueError(f"conversions 缺少目標形狀：{'、'.join(missing_targets)}")

    def by_id(self) -> dict[str, ShapeDef]:
        return {s.id: s for s in self.shapes}

    def summary(self) -> str:
        return f"{len(self.shapes)} 種目標形狀"


# ---------------------------------------------------------------------------
# 效果原語
# ---------------------------------------------------------------------------


class RequiredWhen(ContentModel):
    """參數「依情況才必填」的條件（Phase 4-L3，取代原本寫死在驗證器裡的 ``_filled_by_category``）。

    只能和 ``required: true`` 並用，且恰好填一種：``category`` ＝ 只有技能類別是這個才必填
    （例如武器技的傷害骰來自武器，法術技才要填）；``unless_filled`` ＝ 同一技能內同類型的效果
    只要有任何一個填了指定的另一個參數，這個參數就不必填（例如符文填了標籤就可以省略元素）。
    """

    category: SkillCategory | None = None
    unless_filled: str | None = Field(default=None, pattern=ID_PATTERN)

    @model_validator(mode="after")
    def _one(self) -> RequiredWhen:
        if (self.category is None) == (self.unless_filled is None):
            raise ValueError("required_when 必須恰好填 category 或 unless_filled 其中一種")
        return self

    def applies(self, *, category: str, sibling_filled: Callable[[str], bool]) -> bool:
        """條件成立（＝這個參數必填）。"""
        if self.category is not None:
            return category == self.category
        assert self.unless_filled is not None
        return not sibling_filled(self.unless_filled)
