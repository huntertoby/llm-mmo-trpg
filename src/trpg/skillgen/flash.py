"""閃現（靈光一閃）的規則核心：套用變化、推出閃現後的技能、出題（Phase 3W-1，
``docs/design/06-技能.md`` 6.34；玩法決定 #69、#70）。

純函式、確定性。資料在 ``content/flash_templates.yaml``
（:class:`~trpg.content.flash_templates.FlashTable`），狀態在 :mod:`trpg.skillgen.flash_state`。

**套用變化**（:func:`apply_variation`）：模板把技能改成草稿（例：範圍 +1），草稿的
``budget_bonus_permille`` 設成這一次閃現後的預算上限加成，再由預算器依新的上限重調強度
（沿用分歧進化的調整器 :func:`trpg.skillgen.evolution.retune`／``finish_draft``）並通過
:func:`~trpg.skillgen.validate.validate_skill` 全部檢查（6.6 硬上限、互斥、稀有度……）。做不出來時
``None``，那個變化就不會出現在選項裡。

**推出技能**（:func:`derive_skill`）：從原本的技能依變化歷程逐筆套用（第 i 次用 +i × 40‰ 的上限、
種子標籤 ``flash/<原技能>/<i>/<該欄重閃次數>``），所以重閃第 k 次時後面的變化會在新的技能上
重新套用；
ID 與名稱由歷程決定（:func:`flashed_identity`）。

**出題**（:func:`make_offer`）：

- 不指定類別：花 ``pricing.open.cost`` 點，出 ``open.options`` 個混合變化，至少涵蓋
  ``open.min_categories`` 類（做得到時）。類別順序由種子洗牌，每類輪流取它排第一的合格變化。
- 指定類別：花 ``pricing.focused.cost`` 點，從該類依排序取 ``focused.options`` 個。
- 第 ``major_flash`` 次（或重閃它）出大變化（加深、橋接）；有合法轉型時轉型一定是選項之一：不指定時
  佔其中一個，指定時另列一個（#70）。
- 每類的候選與排序由 :class:`FlashOptionSource` 提供（可替換：依用法統計排序 3W-2、LLM 提議 3W-7）；
  這裡只放最簡單的 :class:`DataOrderSource`（資料順序）。
- 選項連同套用後的技能一起寫進 :class:`FlashOffer`，選擇時不重抽也不重算（:func:`choose`）。
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.flash_templates import FlashCategory, FlashTable, FlashTemplate
from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.evolution import (
    bridge_keywords,
    budget_power,
    finish_draft,
    retune,
    template_drafts,
    template_prefix,
)
from trpg.skillgen.flash_ops import FLASH_OPS, STRICT_OPS, tuning_extras
from trpg.skillgen.flash_state import (
    COMPLETE_SLOT,
    FlashRecord,
    SkillFlash,
    Variation,
    bonus_permille,
    next_nth,
    seed_tag,
    slot_is_major,
    with_flash,
    with_reflash,
)
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "FLASH_OPS",
    "TRANSFORM_CATEGORY",
    "TRANSFORM_OPS",
    "DataOrderSource",
    "FlashError",
    "FlashOffer",
    "FlashOption",
    "FlashOptionSource",
    "FlashRequest",
    "allowed_categories",
    "apply_variation",
    "choose",
    "derive_skill",
    "flashed_identity",
    "is_support_skill",
    "make_offer",
    "unimplemented_ops",
    "variation_rng",
    "with_budget_bonus",
]

TRANSFORM_CATEGORY = "transform"
"""轉型變化的類別 ID（不是可指定的類別；大變化時保底出現）。"""

type _Draft = tuple[dict[str, Any], list[dict[str, Any]]]
TUNE_ATTEMPTS = 3
"""同一份草稿最多試幾次不同的調整亂數（強度下限讓一次調整失敗的機會變大）。"""
STRICT_MARGIN = Fraction(1, 100)
"""結構不變、只靠重調變強的變化（``STRICT_OPS``）：預算分數至少要比變化前多這麼多點。"""
type TransformOp = Callable[[SkillDef, Variation, ContentLibrary], list[_Draft]]


class FlashError(ValueError):
    """變化歷程無法套用（資料改了、或重閃後後面的變化不再合法）。"""


# ---------------------------------------------------------------------------
# 模板 → 草稿
# ---------------------------------------------------------------------------

TRANSFORM_OPS: dict[str, TransformOp] = {}
"""轉型的改法登錄表（轉型模板 ID → 草稿；3W-3 實作）。空的時候不會出現轉型選項。"""


def unimplemented_ops(table: FlashTable) -> tuple[str, ...]:
    """資料裡用到、但還沒有實作的小變化 ``op``（依名稱排序）。"""
    return tuple(sorted({t.op for t in table.minor} - set(FLASH_OPS)))


# ---------------------------------------------------------------------------
# 套用變化（同階預算 ＋ 閃現加成重調）
# ---------------------------------------------------------------------------


def with_budget_bonus(skill: SkillDef, permille: int) -> SkillDef:
    """把技能的預算上限加成設成 ``permille``（0 ＝ 沒有）；不重調強度。"""
    if permille < 0:
        raise ValueError(f"預算上限加成不可為負，收到 {permille}")
    value = permille or None
    if skill.budget_bonus_permille == value:
        return skill
    return skill.model_copy(update={"budget_bonus_permille": value})


def variation_rng(seed: int, base_id: str, record: FlashRecord) -> Rng:
    """套用一筆變化時調整器用的亂數：``flash/<原技能>/<第幾次>/<重閃次數>`` 再依變化分流。"""
    tag = seed_tag(base_id, record.nth, record.reflashes)
    return Rng(seed).fork(tag).fork(record.variation.key())


def _minor_drafts(skill: SkillDef, variation: Variation, library: ContentLibrary) -> list[_Draft]:
    template = library.flash.minor_template(variation.template)
    op = None if template is None else FLASH_OPS.get(template.op)
    if (
        template is None
        or op is None
        or skill.tier < template.min_tier
        or skill.kind not in _kinds(library.flash, template)
    ):
        return []
    return op(skill, template, variation, library)


def _apply_major(
    skill: SkillDef,
    variation: Variation,
    rng: Rng,
    library: ContentLibrary,
    floor: Fraction | None = None,
) -> SkillDef | None:
    major = library.flash.major_template(variation.template)
    evolution = None if major is None else _evolution_template(library, major.evolution)
    if evolution is None:
        return None
    drafts = template_drafts(evolution, skill, variation.keyword, SkillUsage(), library)
    if variation.shape is not None:
        wanted = variation.shape.model_dump(mode="json", exclude_none=True)
        drafts = [d for d in drafts if d[0].get("shape") == wanted]
    for index, draft in enumerate(drafts):
        done = finish_draft(draft, skill, evolution, rng.fork(str(index)), library, floor=floor)
        if done is not None and _carries(done, variation, library):
            return done
    return None


def _carries(skill: SkillDef, variation: Variation, library: ContentLibrary) -> bool:
    """橋接與「第二個關鍵字」的變化套用後必須真的帶那個關鍵字（專屬規則，同 3-26b）。"""
    if variation.keyword is None or (
        variation.category != "bridge" and variation.template not in _keyword_templates(library)
    ):
        return True
    derived = derive_keywords(skill, library.keywords, exclusive_only=True)
    return variation.keyword in derived.all()


def _evolution_template(library: ContentLibrary, template_id: str) -> Any:
    return next((t for t in library.evolution.templates if t.id == template_id), None)


def _keyword_templates(library: ContentLibrary) -> frozenset[str]:
    """「第二個關鍵字」的小變化模板 ID（套用後必須真的帶那個關鍵字）。"""
    ops = ("keyword_imbue", "keyword_exploit")
    return frozenset(t.id for t in library.flash.minor if t.op in ops)


def power_floor(
    library: ContentLibrary,
    current: SkillDef,
    variation: Variation,
    replaced: Fraction | None = None,
) -> Fraction | None:
    """這一次變化後，預算分數（:func:`~trpg.skillgen.evolution.budget_power`）至少要有多少
    （玩法 PM：閃現後不低於閃現前；重閃不低於換掉之前）。``replaced`` 是重閃時被換掉那一筆的分數；
    結構不變、只靠重調變強的變化（``STRICT_OPS``）再多 :data:`STRICT_MARGIN` 點。轉型是把效果
    縮小掛到別的觸發上（6.34.5），不設下限（3W-3 決定）。"""
    if variation.source == "transform":
        return None
    floor = budget_power(current, library)
    if replaced is not None:
        floor = max(floor, replaced)
    template = library.flash.minor_template(variation.template)
    if variation.source == "minor" and template is not None and template.op in STRICT_OPS:
        floor += STRICT_MARGIN
    return floor


def apply_variation(
    library: ContentLibrary,
    skill: SkillDef,
    variation: Variation,
    *,
    bonus: int,
    rng: Rng,
    replaced: Fraction | None = None,
) -> SkillDef | None:
    """把 ``variation`` 套在 ``skill`` 上，依預算上限加成 ``bonus``（‰）重調強度並驗證；做不出來時
    ``None``。回傳的技能 ID、名稱與原本相同（由 :func:`derive_skill` 統一換）。

    **強度下限**（:func:`power_floor`）：重調後的預算分數不低於套用前（重閃時再不低於
    ``replaced``），
    個別數字可以變小（例：範圍 +1 後傷害骰變小）。"""
    current = with_budget_bonus(skill, bonus)
    floor = power_floor(library, current, variation, replaced)
    if variation.source == "major":
        return _apply_major(current, variation, rng, library, floor)
    if variation.source == "transform":
        op = TRANSFORM_OPS.get(variation.template)
        drafts = [] if op is None else op(current, variation, library)
        tag = ""
    else:
        drafts = _minor_drafts(current, variation, library)
        template = library.flash.minor_template(variation.template)
        tag = "" if template is None else template.op
    for index, (base, effects) in enumerate(drafts):
        extra, knobs = tuning_extras(tag, base, library)
        for attempt in range(TUNE_ATTEMPTS):
            # 第一次的子亂數與 3W-1 相同；強度下限讓調整更容易失敗，所以同一份草稿多試幾次
            fork = str(index) if attempt == 0 else f"{index}.r{attempt}"
            done = retune(
                base,
                effects,
                rng.fork(fork),
                library,
                floor=floor,
                extra=extra,
                extra_knobs=knobs,
            )
            if done is not None and _carries(done, variation, library):
                return done
    return None


def flashed_identity(library: ContentLibrary, base: SkillDef, state: SkillFlash) -> tuple[str, str]:
    """閃現後技能的（ID，名稱）。ID ＝ ``<原 ID>_fl_<歷程雜湊前 10 碼>``；名稱在有大變化或轉型時是
    組合式「{前綴}・{原名}」（取最後一個），只有小變化時沿用原名。"""
    records = [*state.records, *([state.adjustment] if state.adjustment else [])]
    body = json.dumps(
        [r.model_dump(mode="json") for r in records], sort_keys=True, separators=(",", ":")
    )
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:10]
    name = base.name_zh
    for record in records:
        prefix = _big_prefix(library, record.variation)
        if prefix is not None:
            name = f"{prefix}・{base.name_zh}"
    return f"{base.id}_fl_{digest}", name


def _big_prefix(library: ContentLibrary, variation: Variation) -> str | None:
    if variation.source == "transform":
        found = next((t for t in library.flash.transforms if t.id == variation.template), None)
        return None if found is None else found.prefix_zh
    if variation.source == "major":
        major = library.flash.major_template(variation.template)
        evolution = None if major is None else _evolution_template(library, major.evolution)
        return None if evolution is None else template_prefix(evolution, variation.keyword, library)
    return None


def _records(state: SkillFlash) -> list[FlashRecord]:
    return [*state.records, *([state.adjustment] if state.adjustment else [])]


def _record_bonus(library: ContentLibrary, state: SkillFlash, record: FlashRecord) -> int:
    rules = library.flash.rules
    if state.complete:
        return rules.complete.budget_permille
    return rules.budget_bonus_permille(record.nth)


def at_tier(skill: SkillDef, tier: int | None) -> SkillDef:
    """技能改用角色階級 ``tier`` 的預算（#72，6.34.9；``None`` ＝ 沿用技能自己的階級）。「技能的預算
    用角色階級」的完整改法另排 3W-9，這裡先用傳進來的階級重算。"""
    if tier is None or tier == skill.tier:
        return skill
    return skill.model_copy(update={"tier": tier})


def derive_chain(
    library: ContentLibrary,
    base: SkillDef,
    state: SkillFlash,
    seed: int,
    tier: int | None = None,
) -> list[SkillDef]:
    """變化歷程每套完一筆之後的技能（ID、名稱還是原本的；依序，沒有變化時為空）。每一筆都受強度
    下限約束：不低於前一筆，重閃過的那一筆不低於當時被換掉的（``floor_permille``）。``tier`` 是角色
    階級（預算與模板的最低階級都看它）。任何一筆套用不了時拋出 :class:`FlashError`。"""
    skill = with_budget_bonus(at_tier(base, tier), bonus_permille(library.flash.rules, state))
    chain: list[SkillDef] = []
    for record in _records(state):
        rng = variation_rng(seed, state.base_id, record)
        bonus = _record_bonus(library, state, record)
        replaced = Fraction(record.floor_permille, 1000) if record.floor_permille else None
        applied = apply_variation(
            library, skill, record.variation, bonus=bonus, rng=rng, replaced=replaced
        )
        if applied is None:
            raise FlashError(
                f"{base.id} 第 {record.nth} 次的變化 {record.variation.template} 套用不了"
            )
        skill = applied
        chain.append(skill)
    return chain


def derive_skill(
    library: ContentLibrary,
    base: SkillDef,
    state: SkillFlash,
    seed: int,
    tier: int | None = None,
) -> SkillDef:
    """原本的技能依變化歷程逐筆套用後的技能（沒有變化時是 ``base`` 加上預算上限加成）。``tier`` 是
    角色階級。任何一筆套用不了時拋出 :class:`FlashError`。"""
    chain = derive_chain(library, base, state, seed, tier)
    if not chain:
        return with_budget_bonus(at_tier(base, tier), bonus_permille(library.flash.rules, state))
    skill = chain[-1]
    new_id, name = flashed_identity(library, base, state)
    return skill.model_copy(
        update={
            "id": new_id,
            "name_zh": name,
            "provenance": skill.provenance.model_copy(
                update={"origin": "level_up", "parents": (base.id,)}
            ),
        }
    )


# ---------------------------------------------------------------------------
# 類別
# ---------------------------------------------------------------------------


_SUPPORT_TYPES = frozenset({"heal", "shield", "apply_status", "cleanse", "grant_ap"})


def is_support_skill(skill: SkillDef) -> bool:
    """輔助技（「輔助」類用）：沒有傷害類效果，而且有治療、護盾或作用於友方的效果。

    3W-1 的保守判定；3W-2 可改依原語分類。"""
    if any(e.type in ("damage", "delayed_damage") for e in skill.effects):
        return False
    helps = any(e.type in ("heal", "shield") for e in skill.effects)
    buffs = any(e.type in _SUPPORT_TYPES and e.affects == "allies" for e in skill.effects)
    return helps or buffs


def _kinds(table: FlashTable, template: FlashTemplate) -> tuple[str, ...]:
    if template.kinds is not None:
        return template.kinds
    return table.category(template.category).kinds


def _category_ok(category: FlashCategory, skill: SkillDef) -> bool:
    return skill.kind in category.kinds and (not category.support_only or is_support_skill(skill))


def allowed_categories(table: FlashTable, skill: SkillDef, *, major: bool) -> tuple[str, ...]:
    """這招這一次可以出（或指定）的類別（資料順序）。"""
    categories = table.stage_categories("major" if major else "minor")
    return tuple(c.id for c in categories if _category_ok(c, skill))


# ---------------------------------------------------------------------------
# 出題
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FlashRequest:
    """出題的輸入。``slot`` 為 ``None`` 是閃現（下一次），否則是重閃第 ``slot`` 次（完整技能為 0）；
    ``category`` 是指定的類別（``None`` ＝ 不指定）。``held_keywords`` 是持有者其他技能的關鍵字
    分布（橋接用）；``seed`` 是一輪（或角色）的種子。"""

    base: SkillDef
    state: SkillFlash
    usage: SkillUsage
    seed: int
    slot: int | None = None
    category: str | None = None
    held_keywords: Mapping[str, int] = field(default_factory=dict)
    tier: int | None = None
    """角色階級（#72）：模板的最低階級與預算都看它；``None`` ＝ 沿用技能自己的階級。同種子、同階級
    必得同樣的選項。"""

    @property
    def role_tier(self) -> int:
        return self.base.tier if self.tier is None else self.tier

    @property
    def nth(self) -> int:
        return next_nth(self.state) if self.slot is None else self.slot

    @property
    def reflashes(self) -> int:
        """種子標籤的重閃次數：閃現為 0，重閃為「這一欄已重閃次數 ＋ 1」。"""
        if self.slot is None:
            return 0
        old = self.state.record(self.slot)
        return 0 if old is None else old.reflashes + 1


class FlashOptionSource(Protocol):
    """變化候選的來源（可替換）。依類別給出 **排序好的** 候選變化；合不合格、怎麼混合由
    :func:`make_offer` 處理。"""

    def ranked(
        self, library: ContentLibrary, request: FlashRequest, category: str, skill: SkillDef
    ) -> Sequence[Variation]:
        """``category`` 類的候選，排前面的優先。``skill`` 是套用這一次之前的技能。"""
        ...

    def transforms(
        self, library: ContentLibrary, request: FlashRequest, skill: SkillDef
    ) -> Sequence[Variation]:
        """轉型候選（大變化時保底用），排前面的優先。"""
        ...


class DataOrderSource:
    """最簡單的候選來源（3W-1，測試用）：依資料檔順序，不看用法統計。

    - 小變化：該類的模板（技能種類相符、``op`` 已實作）。
    - 加深：每個進化模板一個（``intensify`` 帶這招自己的第一個專屬關鍵字）。
    - 橋接：這招沒有的關鍵字（持有者其他技能多的優先，再依嫁接表順序）× 橋接模板，最多
      ``bridge_keyword_tries`` 個關鍵字。
    """

    def ranked(
        self, library: ContentLibrary, request: FlashRequest, category: str, skill: SkillDef
    ) -> Sequence[Variation]:
        table = library.flash
        if table.category(category).stage == "minor":
            return [
                Variation(source="minor", template=t.id, category=category)
                for t in table.minor
                if t.category == category
                and t.op in FLASH_OPS
                and t.min_tier <= request.role_tier
                and skill.kind in _kinds(table, t)
            ]
        keywords = self._keywords(library, request, skill, category)
        out: list[Variation] = []
        for major in table.major:
            if major.category != category:
                continue
            evolution = _evolution_template(library, major.evolution)
            if evolution is None:
                continue
            needs_keyword = evolution.op in ("intensify", "graft_uses", "graft_makes")
            for keyword in keywords if needs_keyword else [None]:
                out.append(
                    Variation(source="major", template=major.id, category=category, keyword=keyword)
                )
        return out

    @staticmethod
    def _keywords(
        library: ContentLibrary, request: FlashRequest, skill: SkillDef, category: str
    ) -> list[str]:
        own = derive_keywords(skill, library.keywords, exclusive_only=True).all()
        if category == "deepen":
            return list(own[:1])
        everything = set(derive_keywords(skill, library.keywords).all())
        order = list(library.evolution.grafts)
        candidates = [k for k in order if k not in everything]
        candidates.sort(key=lambda k: (-request.held_keywords.get(k, 0), order.index(k)))
        return candidates[: library.evolution.bridge_keyword_tries]

    def transforms(
        self, library: ContentLibrary, request: FlashRequest, skill: SkillDef
    ) -> Sequence[Variation]:
        if skill.kind != "active":
            return []
        return [
            Variation(source="transform", template=t.id, category=TRANSFORM_CATEGORY)
            for t in library.flash.transforms
        ]


_FAR_SHAPES = ("line", "square3")
_NEAR_SHAPES = ("cone", "cross")
_MULTI_TARGETS_PERMILLE = 1500
"""平均目標數達到這個數（‰）視為「常打到多個目標」。"""
_FREQUENT_USES = 6
"""放出次數達到這個數視為常用（輕巧優先）。"""
_KEYWORD_CAP = 6
"""每個「第二個關鍵字」模板最多列幾個關鍵字。"""


class UsageSource(DataOrderSource):
    """依用法統計排序的候選來源（Phase 3W-2，#70：類別內依用法統計排序）。

    - 小變化：每個模板展開成帶參數的變化（換形狀的目標形狀、第二元素、第二個關鍵字），類別內依
      「用法分數」由高到低（同分依資料順序）。用法分數看統計：常打到多個目標 → 範圍 +1；單體用法 →
      換形狀、多打一下；平均距離遠 → 距離 +1；用這招擊倒過敵人 → 擊殺返還；目標身上常有某關鍵字 →
      延長、借勢（利用）該關鍵字；沒有訊號的關鍵字 → 附魔（製造）；常用（≥ 6 次）→ 輕巧。
    - **用法統計少**（放出次數 < ``usage_min_uses``）：先出通用變化（``generic``），其餘依資料順序。
    - 大變化（加深、橋接）沿用 :class:`DataOrderSource`（3W-3 補用法統計）。
    """

    def ranked(
        self, library: ContentLibrary, request: FlashRequest, category: str, skill: SkillDef
    ) -> Sequence[Variation]:
        table = library.flash
        if table.category(category).stage != "minor":
            return super().ranked(library, request, category, skill)
        sparse = request.usage.uses < table.rules.usage_min_uses
        scored: list[tuple[int, int, int, Variation]] = []
        templates = [
            t
            for t in table.minor
            if t.category == category
            and t.op in FLASH_OPS
            and t.min_tier <= request.role_tier
            and skill.kind in _kinds(table, t)
        ]
        for order, template in enumerate(templates):
            for sub, variation in enumerate(self._variants(library, request, template, skill)):
                score = (
                    int(template.generic)
                    if sparse
                    else _usage_score(library, request.usage, template, variation)
                )
                scored.append((-score, order, sub, variation))
        scored.sort(key=lambda item: item[:3])
        return [item[3] for item in scored]

    def _variants(
        self,
        library: ContentLibrary,
        request: FlashRequest,
        template: FlashTemplate,
        skill: SkillDef,
    ) -> list[Variation]:
        base = {"source": "minor", "template": template.id, "category": template.category}
        if template.op == "reshape":
            reach = (
                _FAR_SHAPES
                if request.usage.avg_distance_permille >= (library.evolution.far_distance * 1000)
                else _NEAR_SHAPES
            )
            shapes = sorted(template.shapes, key=lambda s: s.type not in reach)
            return [Variation.model_validate({**base, "shape": s}) for s in shapes]
        if template.op == "dual_scaling":
            attrs = [a.value for a in library.secondary_range(skill) if a != skill.scaling_attr]
            return [Variation.model_validate({**base, "keyword": a}) for a in attrs]
        if template.op == "element":
            own = {e.element.value for e in skill.effects if e.element is not None}
            elements = [e for e in template.elements if e not in own]
            return [Variation.model_validate({**base, "element": e}) for e in elements]
        if template.op in _KEYWORD_OPS:
            keywords = _keyword_candidates(library, request, template, skill)
            return [Variation.model_validate({**base, "keyword": k}) for k in keywords]
        return [Variation.model_validate(base)]


_KEYWORD_OPS = frozenset({"keyword_imbue", "keyword_exploit", "mod_keyword"})


def _keyword_signal(usage: SkillUsage, keyword: str) -> int:
    """這個關鍵字在用法統計裡的訊號：前後搭配的技能與目標身上出現的次數。"""
    return usage.partners().get(keyword, 0) + usage.target_keywords.get(keyword, 0)


def _keyword_candidates(
    library: ContentLibrary, request: FlashRequest, template: FlashTemplate, skill: SkillDef
) -> list[str]:
    """「第二個關鍵字」的候選：這招沒有的關鍵字，用法統計有訊號的優先（沿用橋接的排序），其次是
    持有者其他技能多的，最後依嫁接表順序；模板限定時只留限定的。"""
    own = set(derive_keywords(skill, library.keywords).all())
    grafts = library.evolution.grafts
    signaled = bridge_keywords(library, skill, request.usage, request.held_keywords)
    order = list(grafts)
    rest = sorted(
        (k for k in order if k not in own and k not in signaled),
        key=lambda k: (-request.held_keywords.get(k, 0), order.index(k)),
    )

    def usable(keyword: str) -> bool:
        graft = grafts.get(keyword)
        if graft is None or keyword in own:
            return False
        if template.keywords and keyword not in template.keywords:
            return False
        if template.op == "keyword_imbue":
            return graft.makes is not None
        return graft.uses is not None

    return [k for k in (*signaled, *rest) if usable(k)][:_KEYWORD_CAP]


def _usage_score(
    library: ContentLibrary, usage: SkillUsage, template: FlashTemplate, variation: Variation
) -> int:
    """用法分數（越高越優先）；見 :class:`UsageSource`。"""
    op = template.op
    multi = usage.avg_targets_permille >= _MULTI_TARGETS_PERMILLE
    keyword = variation.keyword
    signal = 0 if keyword is None else _keyword_signal(usage, keyword)
    scores: dict[str, bool | int] = {
        "area": 2 * multi,
        "range": 2 * (usage.avg_distance_permille >= library.evolution.far_distance * 1000),
        "reshape": 2 * (not multi and usage.uses > 0),
        "multi_hit": 2 * (not multi and usage.uses > 0),
        "followup": int(usage.uses > 0),
        "kill_refund": 3 * (usage.kills > 0),
        "extend": 2 * (sum(usage.target_keywords.values()) > 0),
        "charge": int(multi),
        "light": int(usage.uses >= _FREQUENT_USES),
        "keyword_exploit": 3 * (signal > 0),
        "keyword_imbue": int(signal == 0),
        "mod_keyword": 2 * (signal > 0),
    }
    return int(scores.get(op, 0))


class FlashOption(BaseModel):
    """一個選項：變化、套用後的技能（已含新的 ID、名稱與預算上限加成）、一句話說明。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variation: Variation
    skill: SkillDef
    summary_zh: str
    floor_permille: int = Field(default=0, ge=0)
    """重閃時被換掉那一筆的預算分數下限（‰，進位；選擇時寫進 :class:`FlashRecord`）；閃現為 0。"""


class FlashOffer(BaseModel):
    """一次出題（存進一輪，選擇時不重抽、不重算）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_id: str
    nth: int = Field(ge=0)
    slot: int | None = None
    """重閃的欄位（第幾次）；閃現為 ``None``。"""
    reflashes: int = Field(default=0, ge=0)
    category: str | None = None
    major: bool = False
    cost: int = Field(ge=0)
    options: tuple[FlashOption, ...] = ()


@dataclass(slots=True)
class _Builder:
    """依請求逐個試套用候選變化（延遲計算：只算到需要的數量）。"""

    library: ContentLibrary
    request: FlashRequest
    floor_permille: int = 0
    """重閃時被換掉那一筆的預算分數（‰，進位）；閃現為 0。"""

    def option(self, variation: Variation) -> FlashOption | None:
        request = self.request
        state = (
            with_flash(request.state, variation)
            if request.slot is None
            else with_reflash(
                request.state, request.slot, variation, floor_permille=self.floor_permille
            )
        )
        try:
            skill = derive_skill(self.library, request.base, state, request.seed, request.tier)
        except FlashError:
            return None
        return FlashOption(
            variation=variation,
            skill=skill,
            summary_zh=_summary(self.library, variation),
            floor_permille=self.floor_permille,
        )

    def take(self, variations: Sequence[Variation], count: int) -> list[FlashOption]:
        found: list[FlashOption] = []
        for variation in variations:
            if len(found) >= count:
                break
            option = self.option(variation)
            if option is not None:
                found.append(option)
        return found


def _summary(library: ContentLibrary, variation: Variation) -> str:
    table = library.flash
    if variation.source == "minor":
        template = table.minor_template(variation.template)
        return "" if template is None else template.summary_zh
    if variation.source == "transform":
        found = next((t for t in table.transforms if t.id == variation.template), None)
        return "" if found is None else found.summary_zh
    major = table.major_template(variation.template)
    evolution = None if major is None else _evolution_template(library, major.evolution)
    if evolution is None:
        return ""
    name = next(
        (k.name_zh for k in library.keywords.keywords if k.id == variation.keyword),
        variation.keyword or "",
    )
    return str(evolution.summary_zh).replace("{keyword}", name)


def _replaced_floor(library: ContentLibrary, request: FlashRequest) -> int:
    """重閃時被換掉那一筆的預算分數（‰，進位；強度下限，見 :func:`power_floor`）。閃現為 0。"""
    if request.slot is None:
        return 0
    state = request.state
    try:
        chain = derive_chain(library, request.base, state, request.seed, request.tier)
    except FlashError:
        return 0
    old = state.record(request.slot)
    if old is None:
        skill = with_budget_bonus(
            at_tier(request.base, request.tier), bonus_permille(library.flash.rules, state)
        )
    else:
        skill = chain[[r.nth for r in _records(state)].index(old.nth)]
    return math.ceil(budget_power(skill, library) * 1000)


def _skill_before(library: ContentLibrary, request: FlashRequest) -> SkillDef:
    """套用這一次之前的技能（重閃時只套用到前一筆，用來給候選來源參考）。"""
    state = request.state
    if request.slot is not None and not state.complete:
        state = state.model_copy(
            update={"records": tuple(r for r in state.records if r.nth < request.slot)}
        )
    elif request.slot is not None:
        state = state.model_copy(update={"adjustment": None})
    try:
        return derive_skill(library, request.base, state, request.seed, request.tier)
    except FlashError:
        return request.base


def _mixed(
    rng: Rng, queues: dict[str, list[Variation]], builder: _Builder, count: int
) -> list[FlashOption]:
    """不指定類別：類別順序由種子洗牌，每輪每類取一個合格變化，直到湊滿 ``count``（所以做得到時
    至少涵蓋 ``min(count, 有合格變化的類別數)`` 類）。"""
    order = rng.shuffled(sorted(queues))
    pending = {c: list(queues[c]) for c in order}
    found: list[FlashOption] = []
    while len(found) < count and any(pending.values()):
        for category in order:
            if len(found) >= count:
                break
            queue = pending[category]
            while queue:
                option = builder.option(queue.pop(0))
                if option is not None:
                    found.append(option)
                    break
    return found


def make_offer(
    library: ContentLibrary,
    request: FlashRequest,
    source: FlashOptionSource | None = None,
) -> FlashOffer:
    """出一次題（閃現或重閃；不檢查點數與先上場用過，呼叫者先用 ``flash_state`` 的檢查）。

    指定了不合法的類別時拋出 :class:`ValueError`。可能湊不滿選項數（合格的變化不夠時）。"""
    source = source or UsageSource()
    table = library.flash
    major = slot_is_major(table.rules, request.state, request.nth)
    before = _skill_before(library, request)
    allowed = allowed_categories(table, before, major=major)
    focused = request.category is not None
    if focused and (not table.pricing.allow_focus or request.category not in allowed):
        raise ValueError(f"這一次不能指定類別 {request.category}（可用：{', '.join(allowed)}）")
    rule = table.pricing.rule(focused)
    tag = seed_tag(request.state.base_id, request.nth, request.reflashes, request.category)
    rng = Rng(request.seed).fork(tag)
    builder = _Builder(library, request, _replaced_floor(library, request))
    transform = _transform_option(library, request, source, builder, before) if major else None
    if focused:
        assert request.category is not None
        ranked = source.ranked(library, request, request.category, before)
        options = builder.take(ranked, rule.options)
        if not options:
            raise ValueError(f"類別 {request.category} 這一次沒有合格的變化（沒有扣點）")
        if transform is not None:
            options.append(transform)
    else:
        count = rule.options - (1 if transform is not None else 0)
        queues = {c: list(source.ranked(library, request, c, before)) for c in allowed}
        options = _mixed(rng, queues, builder, count)
        if transform is not None:
            options.insert(rng.randint(0, len(options)), transform)
    return FlashOffer(
        base_id=request.state.base_id,
        nth=request.nth,
        slot=request.slot,
        reflashes=request.reflashes,
        category=request.category,
        major=major,
        cost=rule.cost,
        options=tuple(options),
    )


def _transform_option(
    library: ContentLibrary,
    request: FlashRequest,
    source: FlashOptionSource,
    builder: _Builder,
    before: SkillDef,
) -> FlashOption | None:
    """大變化的轉型保底（#70）：第一個合法的轉型；沒有時 ``None``。"""
    if not library.flash.pricing.transform_guaranteed:
        return None
    taken = builder.take(source.transforms(library, request, before), 1)
    return taken[0] if taken else None


def choose(state: SkillFlash, offer: FlashOffer, index: int) -> tuple[SkillFlash, SkillDef]:
    """選第 ``index`` 個選項：回傳新的閃現狀態（花掉的點數加上題目的 ``cost``）與套用後的技能
    （直接取出題時算好的結果）。點數夠不夠由呼叫者先檢查。"""
    if offer.base_id != state.base_id:
        raise ValueError(f"題目屬於 {offer.base_id}，不是 {state.base_id}")
    if not 0 <= index < len(offer.options):
        raise ValueError(f"選項 {index} 不存在（共 {len(offer.options)} 個）")
    option = offer.options[index]
    if offer.slot is None:
        if offer.nth != next_nth(state):
            raise ValueError("題目已過期（閃現次數已改變）")
        return with_flash(state, option.variation, cost=offer.cost), option.skill
    record = state.record(offer.slot)
    current = -1 if record is None else record.reflashes
    if offer.slot != COMPLETE_SLOT and record is None:
        raise ValueError(f"沒有第 {offer.slot} 次的變化可以重閃")
    if (0 if record is None else current + 1) != offer.reflashes:
        raise ValueError("題目已過期（這一欄的重閃次數已改變）")
    return (
        with_reflash(
            state,
            offer.slot,
            option.variation,
            cost=offer.cost,
            floor_permille=option.floor_permille,
        ),
        option.skill,
    )
