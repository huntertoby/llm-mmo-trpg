"""白板技能的閃現（靈光一閃）設定與模板（``content/flash_templates.yaml``；Phase 3W-1，
``docs/design/06-技能.md`` 6.34；玩法決定 #69、#70）。

這份資料只描述「規則數值」與「有哪些變化模板」；怎麼套用（純函式）在
:mod:`trpg.skillgen.flash_derive`，
閃現狀態（每招次數、變化歷程、先上場用過）在 :mod:`trpg.skillgen.flash_state`。

- ``rules``：次數上限、第幾次是大變化、每次的預算上限加成（‰）、完整技能、靈感點。
- ``pricing``：不指定類別（花 1 點出 4 個混合、至少涵蓋 2 類）與指定類別（花 2 點出 3 個）；
  重閃同價。
- ``categories``：變化的類別（範圍、連段、元素與關鍵字、費用、延長與收割、輔助、觸發；大變化的
  加深、橋接），各自限定可用的技能種類。
- ``minor``：小變化模板（第 1、2、4、5 次）；``op`` 的實作在
  :data:`trpg.skillgen.flash_ops.FLASH_OPS`
  （3W-1 只實作 ``area``、``range``，其餘由 3W-2 補上）。
- ``major``：大變化（第 3 次）沿用 ``skill_evolution.yaml`` 的進化模板（以 ID 引用）。
- ``transforms``：主動 → 被動／反應的轉型模板（3W-3 實作；有合法轉型時一定是選項之一，#70）。

跨檔案檢查（``major`` 引用的進化模板存在且分支相符、轉型的觸發時機存在）在
:mod:`trpg.content.library` 載入時。
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills import ReactionSpec, ShapeSpec, TrapSpec, TriggerSpec

__all__ = [
    "FLASH_KINDS",
    "CompleteSkillRules",
    "ExtraMajorTemplate",
    "FlashCategory",
    "FlashKind",
    "FlashPricing",
    "FlashRules",
    "FlashTable",
    "FlashTemplate",
    "MajorFlashTemplate",
    "PriceRule",
    "TransformTarget",
    "TransformTemplate",
]

type FlashKind = Literal["active", "passive", "reaction", "stance", "modifier"]
FLASH_KINDS: tuple[FlashKind, ...] = ("active", "passive", "reaction", "stance", "modifier")


type CostCutField = Literal["stance_upkeep", "cooldown", "mana", "stamina", "ap_cost"]


class CostCut(ContentModel):
    """完整技能沒有可加的數值時，依序減的一項代價（3W-5b）：``field`` 減 ``step``。"""

    field: CostCutField
    step: int = Field(default=1, ge=1, le=10)


def _ladder(values: tuple[int, ...], name: str) -> tuple[int, ...]:
    if not values or values[0] != _NEUTRAL or list(values) != sorted(set(values)):
        raise ValueError(f"{name} 必須從 1000 開始、嚴格遞增")
    return values


_NEUTRAL = 1000
_MAX_FORM_MAGNITUDE = 2000
"""形態幅度的上限（‰；``enter_form.magnitude_permille`` 的參數上限，BAL-2c）。"""


class CompleteSkillRules(ContentModel):
    """完整技能（6.34.6）：視為「已閃 ``flashes`` 次」、預算上限 +``budget_permille``‰、不能再閃，
    可以重閃換掉一個附帶效果或形狀。

    強度怎麼加上去（3W-5b，06 6.34.6「沒有一般數值可調的結構」）：預算器的強度旋鈕（傷害、治療、
    護盾的骰子或倍率、推拉距離）之外，召喚再加 ``summon_power_steps``（召喚物 HP 與傷害的倍率，
    乘在原本的 ``power_permille`` 上）、姿態再加 ``stance_magnitude_steps``（姿態幅度）一起重調；
    仍然調不上去時，依 ``cost_cuts`` 的順序一次減一格代價，直到預算分數達到 +``budget_permille``‰
    或沒有能減的。"""

    flashes: int = Field(default=3, ge=0, le=9)
    budget_permille: int = Field(default=120, ge=0, le=1000)
    cap_permille: int = Field(default=150, ge=0, le=1000)
    """實際加上去的上限（06 6.34.6，玩法 PM ec73486f）：
    一步會超過時先用較細的旋鈕補，都不行才接受超過。"""
    can_flash: bool = False
    can_reflash: bool = True
    summon_power_steps: tuple[int, ...] = (1000, 1040, 1080, 1120, 1160, 1200, 1250, 1300)
    stance_magnitude_steps: tuple[int, ...] = (1000, 1040, 1080, 1120, 1160, 1200, 1250, 1300)
    cost_cuts: tuple[CostCut, ...] = (
        CostCut(field="stance_upkeep"),
        CostCut(field="cooldown"),
        CostCut(field="mana"),
        CostCut(field="stamina"),
        CostCut(field="ap_cost"),
    )

    @model_validator(mode="after")
    def _check_ladders(self) -> CompleteSkillRules:
        _ladder(self.summon_power_steps, "summon_power_steps")
        _ladder(self.stance_magnitude_steps, "stance_magnitude_steps")
        return self


class FlashRules(ContentModel):
    """閃現的規則數值（6.34.2、6.34.3）。"""

    max_flashes: int = Field(default=5, ge=1, le=9)
    major_flash: int = Field(default=3, ge=1, le=9)
    """第幾次閃現是大變化（加深、橋接、轉型）。"""
    budget_step_permille: int = Field(default=40, ge=0, le=200)
    """每次閃現讓這招的預算上限多幾 ‰（佔同階預算；5 次共 +200‰）。"""
    needs_use: bool = True
    """閃現前這招要自上次閃現（或取得）後在戰鬥中用過（主動技放出 1 次；被動、反應、姿態裝備著
    打完一場）。"""
    reflash_needs_use: bool = False
    """重閃不需要先上場用過。"""
    dissolve_refund_permille: int = Field(default=500, ge=0, le=1000)
    """溶掉一招時退回「花在它身上的靈感點」的比例（‰，無條件捨去；#71：一半）。"""
    insight_per_win: int = Field(default=1, ge=0)
    """roguelite 原型每打贏一場給的靈感點（3W-5 接）。"""
    insight_start: int = Field(default=0, ge=0)
    """開局給的靈感點（BAL-1 經濟旋鈕；預設 0＝現行行為）。"""
    insight_preboss: int = Field(default=0, ge=0)
    """打贏最後一場一般戰鬥（下一場是 Boss）時額外加給的靈感點（BAL-1；預設 0）。"""
    usage_min_uses: int = Field(default=3, ge=0)
    """用法統計要有這麼多次放出才算數（3W-2）；不夠時先出通用變化（``generic``）。"""
    complete: CompleteSkillRules = CompleteSkillRules()
    stance_magnitudes: tuple[int, ...] = (
        1000,
        1040,
        1080,
        1120,
        1160,
        1200,
        1250,
        1300,
        1400,
        1500,
        1600,
        1700,
        1800,
        1900,
        2000,
    )
    """沒有階梯的單一狀態姿態（狂怒、堅壁…，BAL-2b）費用、修正類小變化可換到的姿態幅度（‰，
    ``apply_status.magnitude_permille``）。比完整技能的級距寬：這些姿態是固定點數，角色階級高時
    要靠幅度把預算分數拉進預算窗。"""
    form_magnitudes: tuple[int, ...] = tuple(range(1000, 2001, 50))
    """變身姿態（BAL-2c）修正類小變化與升階重配可換到的形態幅度（‰，``enter_form.magnitude_permille``；
    上限 2000）。比 ``stance_magnitudes`` 細：升階重配把形態拉到接近原本的比例（例如 99%）之後，
    一次閃現的 +40‰ 預算仍要放得下下一格。"""

    @model_validator(mode="after")
    def _check(self) -> FlashRules:
        if self.major_flash > self.max_flashes:
            raise ValueError("major_flash 不可大於 max_flashes")
        _ladder(self.stance_magnitudes, "stance_magnitudes")
        _ladder(self.form_magnitudes, "form_magnitudes")
        if self.form_magnitudes[-1] > _MAX_FORM_MAGNITUDE:
            raise ValueError(f"form_magnitudes 最多 {_MAX_FORM_MAGNITUDE}‰")
        return self

    def budget_bonus_permille(self, flashes: int) -> int:
        """閃了 ``flashes`` 次後的預算上限加成（‰）。"""
        return self.budget_step_permille * max(0, min(flashes, self.max_flashes))

    def is_major(self, nth: int) -> bool:
        return nth == self.major_flash


class PriceRule(ContentModel):
    """一種出題方式的價格與選項數。"""

    cost: int = Field(ge=0)
    """花幾點靈感。"""
    options: int = Field(ge=1, le=6)
    """出幾個選項（不含指定類別時另列的轉型）。"""
    min_categories: int = Field(default=1, ge=1)
    """選項至少涵蓋幾類（做得到時）。"""


class FlashPricing(ContentModel):
    """出題方式（#70）：不指定類別（``open``）與指定類別（``focused``）。重閃和閃現同價。"""

    open: PriceRule = PriceRule(cost=1, options=4, min_categories=2)
    focused: PriceRule = PriceRule(cost=2, options=3)
    reflash_same_price: bool = True
    """重閃的價格與選項數和閃現相同（#70）；之後若要不同價，改成另一組 ``PriceRule``。"""
    allow_focus: bool = True
    """是否允許指定類別（先選方向）。"""
    transform_guaranteed: bool = True
    """大變化時有合法轉型就一定是選項之一（不指定時佔其中一個；指定加深或橋接時另列一個）。"""

    def rule(self, focused: bool) -> PriceRule:
        return self.focused if focused else self.open


class FlashCategory(ContentModel):
    """一個變化類別。``stage``：``minor`` 用在第 1、2、4、5 次，``major`` 用在第 3 次。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    stage: Literal["minor", "major"] = "minor"
    kinds: tuple[FlashKind, ...] = ("active",)
    """可以出這類變化的技能種類。"""
    support_only: bool = False
    """只給輔助技（治療、護盾、增益，沒有傷害；
    見 :func:`trpg.skillgen.flash_category.is_support_skill`）。"""


class FlashTemplate(ContentModel):
    """一個小變化模板。數值欄位依 ``op`` 使用；強度不寫在這裡（套用後由預算器重調）。"""

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    op: str = Field(pattern=ID_PATTERN)
    """改法；實作登錄在 :data:`trpg.skillgen.flash_ops.FLASH_OPS`（沒有實作的模板不會出現）。"""
    kinds: tuple[FlashKind, ...] | None = None
    """限定的技能種類；省略時沿用類別的 ``kinds``。"""
    prefix_zh: str = Field(min_length=1)
    summary_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用 ``summary_zh``。"""
    delta: int | None = Field(default=None, ge=-3, le=3)
    """``area``／``range`` 的增量（格）。"""
    shapes: tuple[ShapeSpec, ...] = ()
    """``reshape`` 的候選形狀（3W-2）。"""
    keywords: tuple[str, ...] = ()
    """限定可用的關鍵字（3W-2；``keyword_*`` 模板，例：輔助技只能加不會傷到友方的關鍵字，像「潮濕」
    「暗影」）；空 ＝ 不限（嫁接表有的都可以）。"""
    min_tier: int = Field(default=1, ge=1, le=3)
    """最低角色階級（#72，6.34.9）：角色階級不到就不出這個模板（1 階基本版、2 階 3×3／接續段／第二
    元素／範圍 +2、3 階整排直線／連鎖跳躍／雙屬性縮放）。第 3 次大變化不受階級限制。"""
    generic: bool = False
    """通用變化（3W-2）：用法統計不夠時（放出次數少於 ``rules.usage_min_uses``）先出這些。"""
    elements: tuple[str, ...] = ()
    """``element`` 模板的候選元素（3W-2）；空 ＝ 不限。"""
    min_cells: int | None = Field(default=None, ge=1)
    max_cells: int | None = Field(default=None, ge=1)
    """``terrain_area`` 的影響格數範圍（3W-2b，#58）：新形狀的格數（``cell_count``）要落在其中
    （2 階 4～6 格、3 階 7 格以上）。"""
    usage_base: int = Field(default=0, ge=0, le=5)
    """基本用法分（BAL-2b）：加在用法分數上。觸發、修正類沒有對應的用法統計（用法統計只記主動技的
    命中與目標），沒有基本分就永遠 0 分、被「全指定」策略排在最後；其他模板省略（0）。"""

    @model_validator(mode="after")
    def _check(self) -> FlashTemplate:
        if self.op in ("area", "range") and not self.delta:
            raise ValueError(f"模板 {self.id}：{self.op} 必須填非 0 的 delta")
        if self.op == "terrain_area" and (not self.shapes or self.min_cells is None):
            raise ValueError(f"模板 {self.id}：terrain_area 必須填 shapes 與 min_cells")
        return self


class MajorFlashTemplate(ContentModel):
    """大變化模板：引用 ``skill_evolution.yaml`` 的進化模板（``evolution``），類別是加深或橋接。"""

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    evolution: str = Field(pattern=ID_PATTERN)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用進化模板的說明。"""


type TransformTarget = Literal["passive", "reaction", "summon", "trap", "stance", "modifier"]


class TransformTemplate(ContentModel):
    """主動技轉型（6.34.5、#73）：把這招轉成別種技能。

    - ``to``：新種類。``passive``／``reaction`` 把效果縮小後掛到觸發（``trigger``）或反應
      （``reaction``）上；``summon`` 召喚一隻幫你打的召喚物（``units``）；``trap`` 放置陷阱
      （``trap``）；``stance`` 進入姿態（``stances``）；``modifier`` 修正型被動（持續改變你的
      同元素技能）。
    - ``min_tier``：最低角色階級（#73：1 階被動、反應；2 階起召喚、陷阱、姿態；3 階起修正型被動）。
    - 強度不寫在這裡：轉型後照新種類的預算由預算器重調（``scale_permille`` 只是起點的提示，
      被動／反應的數值最後仍以預算為準）。
    """

    id: str = Field(pattern=ID_PATTERN)
    to: TransformTarget
    min_tier: int = Field(default=1, ge=1, le=3)
    prefix_zh: str = Field(min_length=1)
    summary_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用 ``summary_zh``。"""
    trigger: TriggerSpec | None = None
    reaction: ReactionSpec | None = None
    scale_permille: int = Field(default=500, ge=100, le=1000)
    units: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """``summon``：技能元素（``any`` ＝ 沒有元素或沒列到時）→ 候選召喚物（依序試）。"""
    summon_duration: int = Field(default=2, ge=1, le=6)
    summon_boosts: tuple[dict[str, int], ...] = ()
    """``summon``：角色階級高、預算變大時，依序加試的強化（``summon`` 效果的 ``duration``、
    ``max_hp_permille``、``count``、``power_permille``）；先試不強化的版本。"""
    trap: TrapSpec | None = None
    stances: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """``stance``：``offense``（原招有傷害）、``defense``（沒有傷害）→ 候選姿態狀態 ID（依序試，第一
    個落在預算窗內的）。原招有傷害時先試 :attr:`FlashTable.stance_ladders` 的同元素元素姿態。"""
    damage_permille_steps: tuple[int, ...] = ()
    """``modifier``：「傷害 +n‰」候選（由大到小，第一個落在預算窗內的）。"""

    @model_validator(mode="after")
    def _check(self) -> TransformTemplate:
        needs = {
            "passive": ("trigger", self.trigger is not None),
            "reaction": ("reaction", self.reaction is not None),
            "summon": ("units", bool(self.units)),
            "trap": ("trap", self.trap is not None),
            "stance": ("stances", bool(self.stances)),
            "modifier": ("damage_permille_steps", bool(self.damage_permille_steps)),
        }
        for kind, (field, present) in needs.items():
            if (self.to == kind) != present:
                raise ValueError(f"轉型 {self.id}：轉成 {kind} 時必須（且只有 {kind}）填 {field}")
        return self


class ExtraMajorTemplate(ContentModel):
    """大變化的補充模板（3W-3）：進化模板做不出來的輔助技、召喚技能用的加深與橋接。

    ``op`` 的實作在 :mod:`trpg.skillgen.flash_major`；``only`` 是適用的對象。
    """

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=ID_PATTERN)
    op: str = Field(pattern=ID_PATTERN)
    only: Literal["support", "summon", "shield"]
    """適用對象：輔助技（治療、護盾、增益）、召喚技能或護盾類（有護盾效果，3W-2b）。"""
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    """``only: shield`` 的加深／橋接：護盾改用的狀態（``statuses.yaml`` 的 ``shielded_*``）。"""
    keyword: str | None = Field(default=None, pattern=ID_PATTERN)
    """``only: shield`` 的橋接：這個模板橋接到的關鍵字（持有者持有越多越優先）。"""
    needs_held: bool = False
    """``only: shield`` 的橋接：true ＝ 持有者必須持有 ``keyword`` 才會出現（3W-2c，帶電）。"""
    prefix_zh: str = Field(min_length=1)
    summary_zh: str = Field(min_length=1)
    llm_hint: str = ""
    """給 LLM 提議看的一句話說明（3W-7）；空 ＝ 用 ``summary_zh``。"""


class SupportSkillRule(ContentModel):
    """「輔助技」的判定（「輔助」類 ``support_only`` 用；3W-R2 從程式移到資料）：沒有
    ``harm_effects``，而且有 ``help_effects``，或有作用於友方（``affects: allies``）的
    ``ally_effects``。見 :func:`trpg.skillgen.flash_category.is_support_skill`。"""

    harm_effects: tuple[str, ...] = ("damage", "delayed_damage")
    help_effects: tuple[str, ...] = ("heal", "shield")
    ally_effects: tuple[str, ...] = ("heal", "shield", "apply_status", "cleanse", "grant_ap")


class FlashTable(ContentModel):
    """``content/flash_templates.yaml``。"""

    rules: FlashRules = FlashRules()
    pricing: FlashPricing = FlashPricing()
    categories: tuple[FlashCategory, ...] = ()
    minor: tuple[FlashTemplate, ...] = ()
    major: tuple[MajorFlashTemplate, ...] = ()
    extra_major: tuple[ExtraMajorTemplate, ...] = ()
    transforms: tuple[TransformTemplate, ...] = ()
    support: SupportSkillRule = SupportSkillRule()
    """輔助技的判定（``support_only`` 類別用）。"""
    stance_ladders: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    """元素姿態的階梯（3W-2b）：元素 ID（``physical`` 也有）→ 由弱到強的姿態狀態 ID。轉型優先
    轉成同元素的姿態；姿態的「費用」「修正」類小變化在同一階梯上換級（維持費 ±1 搭配效果升降）。"""

    @model_validator(mode="after")
    def _check(self) -> FlashTable:
        ids = [c.id for c in self.categories]
        templates = [t.id for t in self.minor]
        templates += [t.id for t in self.major]
        templates += [t.id for t in self.extra_major]
        templates += [t.id for t in self.transforms]
        for label, values in (("類別", ids), ("模板", templates)):
            dup = sorted(k for k, n in Counter(values).items() if n > 1)
            if dup:
                raise ValueError(f"{label} ID 重複：{', '.join(dup)}")
        stages = {c.id: c.stage for c in self.categories}
        for template in self.minor:
            if stages.get(template.category) != "minor":
                raise ValueError(
                    f"小變化模板 {template.id} 的類別 {template.category} 不是小變化類別"
                )
        for major in self.major:
            if stages.get(major.category) != "major":
                raise ValueError(f"大變化模板 {major.id} 的類別 {major.category} 不是大變化類別")
        for extra in self.extra_major:
            if stages.get(extra.category) != "major":
                raise ValueError(
                    f"大變化補充模板 {extra.id} 的類別 {extra.category} 不是大變化類別"
                )
        return self

    def category(self, category_id: str) -> FlashCategory:
        for category in self.categories:
            if category.id == category_id:
                return category
        raise KeyError(f"未知的閃現類別：{category_id}")

    def stage_categories(self, stage: Literal["minor", "major"]) -> tuple[FlashCategory, ...]:
        return tuple(c for c in self.categories if c.stage == stage)

    def minor_template(self, template_id: str) -> FlashTemplate | None:
        return next((t for t in self.minor if t.id == template_id), None)

    def major_template(self, template_id: str) -> MajorFlashTemplate | None:
        return next((t for t in self.major if t.id == template_id), None)

    def extra_template(self, template_id: str) -> ExtraMajorTemplate | None:
        return next((t for t in self.extra_major if t.id == template_id), None)

    def stance_rung(self, status_id: str) -> tuple[tuple[str, ...], int] | None:
        """``status_id`` 所在的元素姿態階梯與它的位置；不在任何階梯上時 ``None``。"""
        for ladder in self.stance_ladders.values():
            if status_id in ladder:
                return ladder, ladder.index(status_id)
        return None

    def transform_template(self, template_id: str) -> TransformTemplate | None:
        return next((t for t in self.transforms if t.id == template_id), None)
