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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.flash_templates import FlashCategory, FlashTable, FlashTemplate
from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.engine.skill_levels import grow_shape
from trpg.shared.rng import Rng
from trpg.skillgen.evolution import finish_draft, retune, template_drafts, template_prefix
from trpg.skillgen.flash_major import (
    TRANSFORM_CATEGORY,
    apply_extra,
    extra_prefix,
    extra_summary,
    extra_variations,
    finish_transform,
    is_extra_template,
    meets_floor,
    transform_drafts,
    transform_prefix,
    transform_summary,
    transform_variations,
)
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

type _Draft = tuple[dict[str, Any], list[dict[str, Any]]]
type FlashOp = Callable[[SkillDef, FlashTemplate, Variation, ContentLibrary], list[_Draft]]
type TransformOp = Callable[[SkillDef, Variation, ContentLibrary], list[_Draft]]


class FlashError(ValueError):
    """變化歷程無法套用（資料改了、或重閃後後面的變化不再合法）。"""


# ---------------------------------------------------------------------------
# 模板 → 草稿
# ---------------------------------------------------------------------------


def _base(skill: SkillDef) -> _Draft:
    base = skill.model_dump(mode="json")
    effects: list[dict[str, Any]] = [
        e.model_dump(mode="json", exclude_none=True) for e in skill.effects
    ]
    base.pop("effects")
    return base, effects


def _reshapable(skill: SkillDef) -> bool:
    """形狀可以改（複合技能與陷阱不改形狀，同 5 級小特性的保守做法）。"""
    return skill.kind == "active" and skill.followup is None and skill.trap is None


def _op_area(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[_Draft]:
    """範圍 +delta：形狀第一個可增加的大小參數（``size``／``radius``），不超過形狀上限（6.6）。"""
    if not _reshapable(skill):
        return []
    grown = grow_shape(library.ruleset, skill.shape, template.delta or 0)
    if grown == skill.shape:
        return []
    base, effects = _base(skill)
    base["shape"] = grown.model_dump(mode="json", exclude_none=True)
    return [(base, effects)]


def _op_range(
    skill: SkillDef, template: FlashTemplate, _v: Variation, library: ContentLibrary
) -> list[_Draft]:
    """距離 +delta：固定射程（整數）加 delta，不超過形狀上限；武器射程與沒有射程的形狀不適用。"""
    shape = skill.shape
    if not _reshapable(skill) or not isinstance(shape.range, int) or shape.range < 1:
        return []
    param = library.ruleset.shape_def(shape.type).params.get("range")
    if param is None:
        return []
    value = min(shape.range + (template.delta or 0), param.max)
    if value == shape.range or value < 1:
        return []
    base, effects = _base(skill)
    base["shape"] = shape.model_copy(update={"range": value}).model_dump(
        mode="json", exclude_none=True
    )
    return [(base, effects)]


FLASH_OPS: dict[str, FlashOp] = {"area": _op_area, "range": _op_range}
"""小變化的改法登錄表（``op`` → 草稿）。3W-2 在這裡補上其餘類別；資料裡 ``op`` 沒有登錄的模板不會
出現（:func:`unimplemented_ops` 列出）。"""

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
    if template is None or op is None or skill.kind not in _kinds(library.flash, template):
        return []
    return op(skill, template, variation, library)


def _apply_major(
    skill: SkillDef, variation: Variation, rng: Rng, library: ContentLibrary
) -> SkillDef | None:
    if is_extra_template(library, variation.template):
        return apply_extra(library, skill, variation, rng)
    major = library.flash.major_template(variation.template)
    evolution = None if major is None else _evolution_template(library, major.evolution)
    if evolution is None:
        return None
    drafts = template_drafts(evolution, skill, variation.keyword, SkillUsage(), library)
    if variation.shape is not None:
        wanted = variation.shape.model_dump(mode="json", exclude_none=True)
        drafts = [d for d in drafts if d[0].get("shape") == wanted]
    for index, draft in enumerate(drafts):
        done = finish_draft(draft, skill, evolution, rng.fork(str(index)), library)
        if (
            done is not None
            and _carries(done, variation, library)
            and meets_floor(skill, done, library)
        ):
            return done
    return None


def _carries(skill: SkillDef, variation: Variation, library: ContentLibrary) -> bool:
    """橋接的變化套用後必須真的帶那個關鍵字（專屬規則，同 3-26b）。"""
    if variation.category != "bridge" or variation.keyword is None:
        return True
    derived = derive_keywords(skill, library.keywords, exclusive_only=True)
    return variation.keyword in derived.all()


def _evolution_template(library: ContentLibrary, template_id: str) -> Any:
    return next((t for t in library.evolution.templates if t.id == template_id), None)


def apply_variation(
    library: ContentLibrary,
    skill: SkillDef,
    variation: Variation,
    *,
    bonus: int,
    rng: Rng,
) -> SkillDef | None:
    """把 ``variation`` 套在 ``skill`` 上，依預算上限加成 ``bonus``（‰）重調強度並驗證；做不出來時
    ``None``。回傳的技能 ID、名稱與原本相同（由 :func:`derive_skill` 統一換）。"""
    current = with_budget_bonus(skill, bonus)
    if variation.source == "major":
        return _apply_major(current, variation, rng, library)
    is_transform = variation.source == "transform"
    if is_transform:
        op = TRANSFORM_OPS.get(variation.template)
        drafts = (
            transform_drafts(current, variation, library)
            if op is None
            else op(current, variation, library)
        )
    else:
        drafts = _minor_drafts(current, variation, library)
    for index, (base, effects) in enumerate(drafts):
        child = rng.fork(str(index))
        done = (
            finish_transform(base, effects, child, library)
            if is_transform
            else retune(base, effects, child, library)
        )
        if done is not None:
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
        return transform_prefix(library, variation)
    if variation.source == "major" and is_extra_template(library, variation.template):
        return extra_prefix(library, variation)
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


def _substitute(
    library: ContentLibrary, skill: SkillDef, old: Variation, *, bonus: int, rng: Rng
) -> SkillDef | None:
    """``old``（轉型前的小變化）在新種類上不合法時，換成同類別、資料順序第一個合法的小變化。"""
    for template in library.flash.minor:
        if template.category != old.category or template.id == old.template:
            continue
        candidate = old.model_copy(update={"template": template.id})
        done = apply_variation(library, skill, candidate, bonus=bonus, rng=rng.fork(template.id))
        if done is not None:
            return done
    return None


def _apply_transform(
    library: ContentLibrary,
    base: SkillDef,
    earlier: Sequence[FlashRecord],
    record: FlashRecord,
    seed: int,
    *,
    bonus: int,
) -> SkillDef | None:
    """轉型（6.34.5、#73）：從 **原本的技能** 轉成新種類（預算照新種類重算），再把轉型之前的小變化
    逐筆套在新技能上——對新種類合法的保留、不合法的換成同類別的合法變化（都不合法就省略）。
    重套的變化都用轉型這一次的預算加成，所以最後的加成與轉型同次。"""
    rng = variation_rng(seed, base.id, record)
    skill = apply_variation(library, base, record.variation, bonus=bonus, rng=rng)
    if skill is None:
        return None
    for old in earlier:
        sub_rng = variation_rng(seed, base.id, old).fork("transform")
        done = apply_variation(library, skill, old.variation, bonus=bonus, rng=sub_rng)
        if done is None and old.variation.source == "minor":
            done = _substitute(library, skill, old.variation, bonus=bonus, rng=sub_rng)
        if done is not None:
            skill = done
    return skill


def derive_skill(library: ContentLibrary, base: SkillDef, state: SkillFlash, seed: int) -> SkillDef:
    """原本的技能依變化歷程逐筆套用後的技能（沒有變化時是 ``base`` 加上預算上限加成）。任何一筆
    套用不了時拋出 :class:`FlashError`。"""
    skill = with_budget_bonus(base, bonus_permille(library.flash.rules, state))
    records = _records(state)
    if not records:
        return skill
    for index, record in enumerate(records):
        rng = variation_rng(seed, state.base_id, record)
        bonus = _record_bonus(library, state, record)
        if record.variation.source == "transform":
            applied = _apply_transform(library, base, records[:index], record, seed, bonus=bonus)
        else:
            applied = apply_variation(library, skill, record.variation, bonus=bonus, rng=rng)
        if applied is None:
            raise FlashError(
                f"{base.id} 第 {record.nth} 次的變化 {record.variation.template} 套用不了"
            )
        skill = applied
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
    - 補充（3W-3）：進化模板之外適用的輔助類、召喚類大變化排在後面。
    - 轉型（3W-3）：依 ``tier``（角色階級，預設 1 階）開放的轉型，種類由種子洗牌。
    """

    def __init__(self, tier: int = 1) -> None:
        self.tier = tier

    def ranked(
        self, library: ContentLibrary, request: FlashRequest, category: str, skill: SkillDef
    ) -> Sequence[Variation]:
        table = library.flash
        if table.category(category).stage == "minor":
            return [
                Variation(source="minor", template=t.id, category=category)
                for t in table.minor
                if t.category == category and t.op in FLASH_OPS and skill.kind in _kinds(table, t)
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
        return out + extra_variations(library, skill, category, support=is_support_skill(skill))

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
        tag = seed_tag(request.state.base_id, request.nth, request.reflashes)
        rng = Rng(request.seed).fork(f"{tag}/transform")
        return transform_variations(library, skill, tier=self.tier, rng=rng)


class FlashOption(BaseModel):
    """一個選項：變化、套用後的技能（已含新的 ID、名稱與預算上限加成）、一句話說明。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    variation: Variation
    skill: SkillDef
    summary_zh: str


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

    def option(self, variation: Variation) -> FlashOption | None:
        request = self.request
        state = (
            with_flash(request.state, variation)
            if request.slot is None
            else with_reflash(request.state, request.slot, variation)
        )
        try:
            skill = derive_skill(self.library, request.base, state, request.seed)
        except FlashError:
            return None
        return FlashOption(
            variation=variation, skill=skill, summary_zh=_summary(self.library, variation)
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
        return transform_summary(library, variation)
    if is_extra_template(library, variation.template):
        return extra_summary(library, variation)
    major = table.major_template(variation.template)
    evolution = None if major is None else _evolution_template(library, major.evolution)
    if evolution is None:
        return ""
    name = next(
        (k.name_zh for k in library.keywords.keywords if k.id == variation.keyword),
        variation.keyword or "",
    )
    return str(evolution.summary_zh).replace("{keyword}", name)


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
        return derive_skill(library, request.base, state, request.seed)
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
    source = source or DataOrderSource()
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
    builder = _Builder(library, request)
    transform = _transform_option(library, request, source, builder, before) if major else None
    if focused:
        assert request.category is not None
        ranked = source.ranked(library, request, request.category, before)
        options = builder.take(ranked, rule.options)
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
    return with_reflash(state, offer.slot, option.variation, cost=offer.cost), option.skill
