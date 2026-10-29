"""閃現（靈光一閃）的狀態與規則（Phase 3W-1，``docs/design/06-技能.md`` 6.34.3；
玩法決定 #69、#70）。

純函式、確定性；不碰亂數以外的任何外部狀態。roguelite（3W-5）與之後的大世界共用：一輪或角色為
每招學會的技能存一個 :class:`SkillFlash`（以 **原本的技能 ID** 為鍵），套用的結果由
:func:`trpg.skillgen.flash.derive_skill` 從原本的技能與變化歷程推出。

- **次數**：每招最多 ``max_flashes`` 次；第 ``major_flash`` 次是大變化。完整技能視為已閃
  ``complete.flashes`` 次，不能再閃，只能重閃它唯一的「調整」欄位（``adjustment``，第 0 次）。
- **先上場用過**：自上次閃現（或取得）後，主動技放出過 1 次；被動、反應、姿態、修正裝備著打完
  一場（:func:`counts_as_used`）。重閃不需要，也不會清掉這個記錄。
- **強度**：預算上限加成 ＝ ``budget_step_permille`` × 次數（完整技能為
  ``complete.budget_permille``）。
- **確定性**：種子標籤 ``flash/<原技能>/<第幾次>/<重閃次數>``（:func:`seed_tag`；出題時另加
  ``/<指定類別>``）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.flash_templates import FlashPricing, FlashRules, PriceRule
from trpg.content.skills import ShapeSpec, SkillKind

__all__ = [
    "COMPLETE_SLOT",
    "FlashRecord",
    "SkillFlash",
    "Variation",
    "acquire",
    "after_battle",
    "bonus_permille",
    "counts_as_used",
    "dissolve_refund",
    "flash_count",
    "flash_problem",
    "next_nth",
    "price",
    "reflash_problem",
    "seed_tag",
    "slot_is_major",
    "with_flash",
    "with_reflash",
]

COMPLETE_SLOT = 0
"""完整技能唯一的重閃欄位的「第幾次」。"""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Variation(_Frozen):
    """一個變化：哪一個模板、帶的參數。結構比整招小（LLM 提議也輸出這個，3W-7）；強度不在這裡，
    套用時由預算器補（守則 3）。

    - ``source``：``minor`` 小變化（``flash_templates.yaml`` 的 ``minor``）、``major`` 大變化
      （``major``，引用進化模板）、``transform`` 轉型（``transforms``）。
    - ``template``：上述模板的 ID；``category``：類別 ID（轉型為 ``transform``）。
    - ``keyword``／``shape``／``element``：模板需要的參數（例：橋接的關鍵字、換形狀的目標形狀、
      第二元素）；同樣的變化套在同樣的技能上必得同樣的結果。
    """

    source: Literal["minor", "major", "transform"]
    template: str = Field(min_length=1)
    category: str = Field(min_length=1)
    keyword: str | None = None
    shape: ShapeSpec | None = None
    element: str | None = None

    def key(self) -> str:
        """穩定的識別字串（子亂數串流的標籤、比對用）。"""
        shape = "-" if self.shape is None else self.shape.model_dump_json(exclude_none=True)
        return "/".join(
            (self.source, self.template, self.keyword or "-", shape, self.element or "-")
        )


class FlashRecord(_Frozen):
    """變化歷程的一筆：第幾次閃現（完整技能的調整為 0）、套用的變化、這一欄被重閃過幾次。"""

    nth: int = Field(ge=0)
    variation: Variation
    reflashes: int = Field(default=0, ge=0)
    floor_permille: int = Field(default=0, ge=0)
    """強度下限（Phase 3W-2）：重閃時，被換掉的那一筆套用後的預算分數（‰，無條件進位）；重調後這一
    筆的預算分數不可低於它（玩法 PM：重閃也不低於換掉之前）。閃現為 0（只比前一筆）。"""


class SkillFlash(_Frozen):
    """一招技能的閃現狀態（以原本的技能 ID 為鍵存放）。"""

    base_id: str = Field(min_length=1)
    records: tuple[FlashRecord, ...] = ()
    """依次序的變化歷程（第 1 次在最前）。"""
    used: bool = False
    """自上次閃現（或取得）後是否已在戰鬥中用過。"""
    complete: bool = False
    """完整技能（6.34.6）：視為已閃 ``complete.flashes`` 次、不能再閃。"""
    adjustment: FlashRecord | None = None
    """完整技能的重閃欄位（``nth`` ＝ :data:`COMPLETE_SLOT`）：換掉一個附帶效果或形狀。"""
    spent: int = Field(default=0, ge=0)
    """這招實際花掉的靈感點（閃現、指定類別多花的、重閃都算；完整技能只有重閃花的；#71）。溶掉時
    依它退回（:func:`dissolve_refund`）。"""

    def record(self, nth: int) -> FlashRecord | None:
        if self.complete and nth == COMPLETE_SLOT:
            return self.adjustment
        return next((r for r in self.records if r.nth == nth), None)


def acquire(base_id: str, *, complete: bool = False) -> SkillFlash:
    """剛取得（或完整技能剛到手）的狀態：沒有變化、還沒用過。"""
    return SkillFlash(base_id=base_id, complete=complete)


def flash_count(rules: FlashRules, state: SkillFlash) -> int:
    """視為閃過幾次（完整技能為 ``complete.flashes``）。"""
    return rules.complete.flashes if state.complete else len(state.records)


def bonus_permille(rules: FlashRules, state: SkillFlash) -> int:
    """這招目前的預算上限加成（‰）。"""
    if state.complete:
        return rules.complete.budget_permille
    return rules.budget_bonus_permille(len(state.records))


def next_nth(state: SkillFlash) -> int:
    return len(state.records) + 1


def slot_is_major(rules: FlashRules, state: SkillFlash, nth: int) -> bool:
    """第 ``nth`` 次（或重閃它）出的是不是大變化。完整技能的調整欄位一律出小變化。"""
    return not (state.complete and nth == COMPLETE_SLOT) and rules.is_major(nth)


def flash_problem(rules: FlashRules, state: SkillFlash) -> str | None:
    """不能閃現的原因（點數另由 :func:`price` 判斷）；可以閃時 ``None``。"""
    if state.complete and not rules.complete.can_flash:
        return "完整技能不能再閃現（可以重閃換掉附帶效果）"
    if flash_count(rules, state) >= rules.max_flashes:
        return f"這招已經閃現 {rules.max_flashes} 次，到上限了"
    if rules.needs_use and not state.used:
        return "這招要先在戰鬥中用過，才能再閃現"
    return None


def reflash_problem(rules: FlashRules, state: SkillFlash, nth: int) -> str | None:
    """不能重閃第 ``nth`` 次變化的原因；可以時 ``None``。"""
    if state.complete:
        if not rules.complete.can_reflash:
            return "完整技能不能重閃"
        if nth != COMPLETE_SLOT:
            return f"完整技能只能重閃調整欄位（第 {COMPLETE_SLOT} 次）"
    elif state.record(nth) is None:
        return f"這招沒有第 {nth} 次的變化可以重閃"
    if rules.reflash_needs_use and not state.used:
        return "這招要先在戰鬥中用過，才能重閃"
    return None


def price(pricing: FlashPricing, *, focused: bool) -> PriceRule:
    """出題的價格與選項數（閃現與重閃同價，#70）。"""
    return pricing.rule(focused)


def seed_tag(base_id: str, nth: int, reflashes: int, category: str | None = None) -> str:
    """選項的種子標籤 ``flash/<技能>/<第幾次>/<重閃次數>[/<指定類別>]``。"""
    tag = f"flash/{base_id}/{nth}/{reflashes}"
    return tag if category is None else f"{tag}/{category}"


def counts_as_used(kind: SkillKind, *, casts: int, finished_equipped: bool) -> bool:
    """這一場算不算「上場用過」：主動技放出過（不用打中、不用觸發條件）；被動、反應、姿態、修正
    裝備著打完一場。"""
    if kind == "active":
        return casts > 0
    return finished_equipped


def after_battle(
    state: SkillFlash, kind: SkillKind, *, casts: int, finished_equipped: bool
) -> SkillFlash:
    """一場戰鬥之後的狀態（用過就記下；已經記過的不會被清掉）。"""
    if state.used or not counts_as_used(kind, casts=casts, finished_equipped=finished_equipped):
        return state
    return state.model_copy(update={"used": True})


def with_flash(state: SkillFlash, variation: Variation, *, cost: int = 0) -> SkillFlash:
    """閃現一次：加一筆變化、「用過」重新計算、花掉的點數 +``cost``。呼叫者先用
    :func:`flash_problem` 檢查。"""
    record = FlashRecord(nth=next_nth(state), variation=variation)
    return state.model_copy(
        update={
            "records": (*state.records, record),
            "used": False,
            "spent": state.spent + cost,
        }
    )


def with_reflash(
    state: SkillFlash, nth: int, variation: Variation, *, cost: int = 0, floor_permille: int = 0
) -> SkillFlash:
    """重閃第 ``nth`` 次：換掉那一筆的變化、該欄重閃次數 +1、花掉的點數 +``cost``；次數與「用過」
    不變。"""
    old = state.record(nth)
    reflashes = 0 if old is None else old.reflashes + 1
    record = FlashRecord(
        nth=nth, variation=variation, reflashes=reflashes, floor_permille=floor_permille
    )
    spent = state.spent + cost
    if state.complete and nth == COMPLETE_SLOT:
        return state.model_copy(update={"adjustment": record, "spent": spent})
    if old is None:
        raise ValueError(f"沒有第 {nth} 次的變化可以重閃")
    records = tuple(record if r.nth == nth else r for r in state.records)
    return state.model_copy(update={"records": records, "spent": spent})


def dissolve_refund(rules: FlashRules, state: SkillFlash) -> int:
    """溶掉這招退回的靈感點：花在它身上的點 × ``dissolve_refund_permille`` ÷ 1000，無條件捨去
    （#71：一半）。"""
    return state.spent * rules.dissolve_refund_permille // 1000
