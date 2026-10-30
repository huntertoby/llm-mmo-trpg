"""閃現（靈光一閃）的推出：套用變化、依變化歷程推出閃現後的技能（Phase 3W-1，
``docs/design/06-技能.md`` 6.34；玩法決定 #69、#70；3W-R2 從 ``flash.py`` 拆出）。

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

出題在 :mod:`trpg.skillgen.flash_offer`，類別判定在 :mod:`trpg.skillgen.flash_category`。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from fractions import Fraction
from typing import Any

from trpg.content.flash_templates import FlashTable
from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.evolution import (
    budget_power,
    evolution_template,
    finish_draft,
    retune,
    template_drafts,
    template_prefix,
)
from trpg.skillgen.flash_category import template_kinds
from trpg.skillgen.flash_major import (
    apply_extra,
    extra_prefix,
    finish_transform,
    fixed_strength,
    is_extra_template,
    transform_drafts,
    transform_prefix,
)
from trpg.skillgen.flash_ops import FIXED_FIRST_OPS, STRICT_OPS, tuning_extras
from trpg.skillgen.flash_state import (
    FlashRecord,
    SkillFlash,
    Variation,
    bonus_permille,
    seed_tag,
)
from trpg.skillgen.flash_trade import MINOR_OPS, TRADES, apply_trade
from trpg.skillgen.skill_tier import retier
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "STRICT_MARGIN",
    "TRANSFORM_OPS",
    "TUNE_ATTEMPTS",
    "FlashError",
    "FlashHistoryError",
    "FlashStepError",
    "TransformOp",
    "apply_variation",
    "at_role_tier",
    "at_tier",
    "derive_chain",
    "derive_on_current",
    "derive_skill",
    "flashed_identity",
    "history_error",
    "history_records",
    "power_floor",
    "unimplemented_ops",
    "variation_rng",
    "with_budget_bonus",
]

type _Draft = tuple[dict[str, Any], list[dict[str, Any]]]
TUNE_ATTEMPTS = 3
"""同一份草稿最多試幾次不同的調整亂數（強度下限讓一次調整失敗的機會變大）。"""
STRICT_MARGIN = Fraction(1, 100)
"""結構不變、只靠重調變強的變化（``STRICT_OPS``）：預算分數至少要比變化前多這麼多點。"""
type TransformOp = Callable[[SkillDef, Variation, ContentLibrary], list[_Draft]]


class FlashError(ValueError):
    """變化套用不了（基底類別；見 :class:`FlashStepError`、:class:`FlashHistoryError`）。"""


class FlashStepError(FlashError):
    """推出技能時，歷程的第 ``nth`` 次變化套用不了（:func:`derive_chain`）。呼叫者依情況解讀：
    正在試的那一個變化 → 「這個變化不合法」；已存的歷程 → :class:`FlashHistoryError`。"""

    def __init__(self, base_id: str, nth: int, template: str) -> None:
        super().__init__(f"{base_id} 第 {nth} 次的變化 {template} 套用不了")
        self.base_id = base_id
        self.nth = nth
        self.template = template


class FlashHistoryError(FlashError):
    """**已存的** 變化歷程在目前的內容無法重推（內容改版、模板拿掉或數值改了；3W-R1）。與「這一次
    試的變化不合法」分開：出題、重閃下限、升階改用存檔裡已推出的定義當起點
    （:attr:`FlashRequest.current`）。
    ``reason_zh`` 是給玩家看的原因。"""

    def __init__(self, step: FlashStepError) -> None:
        self.step = step
        self.reason_zh = (
            f"這招第 {step.nth} 次的變化（{step.template}）在目前的內容版本套用不了，"
            "改用存檔裡的數值當起點"
        )
        super().__init__(self.reason_zh)


# ---------------------------------------------------------------------------
# 模板 → 草稿
# ---------------------------------------------------------------------------

TRANSFORM_OPS: dict[str, TransformOp] = {}
"""轉型的改法登錄表（轉型模板 ID → 草稿；3W-3 實作）。空的時候不會出現轉型選項。"""


def unimplemented_ops(table: FlashTable) -> tuple[str, ...]:
    """資料裡用到、但還沒有實作的小變化 ``op``（依名稱排序）。"""
    return tuple(sorted({t.op for t in table.minor} - set(MINOR_OPS)))


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
    op = None if template is None else MINOR_OPS.get(template.op)
    if (
        template is None
        or op is None
        or skill.tier < template.min_tier
        or skill.kind not in template_kinds(library.flash, template)
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
    if is_extra_template(library, variation.template):
        return apply_extra(library, skill, variation, rng)
    major = library.flash.major_template(variation.template)
    evolution = None if major is None else evolution_template(library, major.evolution)
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
        drafts = (
            transform_drafts(current, variation, library)
            if op is None
            else op(current, variation, library)
        )
        tag = ""
    else:
        drafts = _minor_drafts(current, variation, library)
        template = library.flash.minor_template(variation.template)
        tag = "" if template is None else template.op
        trade = TRADES.get(tag)
        if trade is not None:  # 收回家族（BAL-10d）：拿掉的預算 ＋ 這次的 +40‰ 換成核心數值
            return apply_trade(library, current, drafts, trade, rng, floor=floor)
    if tag in FIXED_FIRST_OPS:  # BAL-10b：先取最小的合格增幅（草稿已按增幅由小到大）
        for base, effects in drafts:
            fixed = fixed_strength(base, effects, library, floor=floor)
            if fixed is not None and _carries(fixed, variation, library):
                return fixed
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
        # 固定強度的種類（召喚、姿態、修正型被動）沒有旋鈕：直接檢查預算窗與強度下限（3W-3）
        fixed = (
            finish_transform(base, effects, rng.fork(f"{index}.fx"), library)
            if variation.source == "transform"
            else fixed_strength(base, effects, library, floor=floor)
        )
        if fixed is not None and _carries(fixed, variation, library):
            return fixed
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
        evolution = None if major is None else evolution_template(library, major.evolution)
        return None if evolution is None else template_prefix(evolution, variation.keyword, library)
    return None


def history_records(state: SkillFlash) -> list[FlashRecord]:
    """變化歷程（依次序；完整技能的調整欄放最後）。"""
    return [*state.records, *([state.adjustment] if state.adjustment else [])]


def _record_bonus(library: ContentLibrary, state: SkillFlash, record: FlashRecord) -> int:
    rules = library.flash.rules
    if state.complete:
        return rules.complete.budget_permille
    return rules.budget_bonus_permille(record.nth)


def at_tier(skill: SkillDef, tier: int | None) -> SkillDef:
    """只把技能的階級換成 ``tier``（``None`` ＝ 沿用），**不重配數值**（測試與比較用）。推出閃現後的
    技能一律用 :func:`at_role_tier`（照角色階級的預算重配數值，3W-9）。"""
    if tier is None or tier == skill.tier:
        return skill
    return skill.model_copy(update={"tier": tier})


def at_role_tier(library: ContentLibrary, skill: SkillDef, tier: int | None) -> SkillDef:
    """技能照角色階級 ``tier`` 的預算重配數值（#72，6.34.9；Phase 3W-9 :func:`retier`）；``None``
    ＝ 沿用技能自己的階級。"""
    if tier is None or tier == skill.tier:
        return skill
    return retier(library, skill, tier)


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
    skill = with_budget_bonus(
        at_role_tier(library, base, tier), bonus_permille(library.flash.rules, state)
    )
    chain: list[SkillDef] = []
    records = history_records(state)
    for index, record in enumerate(records):
        rng = variation_rng(seed, state.base_id, record)
        bonus = _record_bonus(library, state, record)
        replaced = Fraction(record.floor_permille, 1000) if record.floor_permille else None
        if record.variation.source == "transform":
            origin = at_role_tier(library, base, tier)
            applied = _apply_transform(library, origin, records[:index], record, seed, bonus=bonus)
        else:
            applied = apply_variation(
                library, skill, record.variation, bonus=bonus, rng=rng, replaced=replaced
            )
        if applied is None:
            raise FlashStepError(base.id, record.nth, record.variation.template)
        skill = applied
        chain.append(skill)
    return chain


def history_error(
    library: ContentLibrary,
    base: SkillDef,
    state: SkillFlash,
    seed: int,
    tier: int | None = None,
) -> FlashHistoryError | None:
    """已存的歷程 ``state`` 能不能在目前的內容重推；不能時回傳 :class:`FlashHistoryError`。"""
    try:
        derive_chain(library, base, state, seed, tier)
    except FlashStepError as exc:
        return FlashHistoryError(exc)
    return None


def _identify(
    library: ContentLibrary, base: SkillDef, state: SkillFlash, skill: SkillDef
) -> SkillDef:
    """套完變化的技能換上閃現後的 ID、名稱與來源（:func:`flashed_identity`）。"""
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


def derive_skill(
    library: ContentLibrary,
    base: SkillDef,
    state: SkillFlash,
    seed: int,
    tier: int | None = None,
) -> SkillDef:
    """原本的技能依變化歷程逐筆套用後的技能（沒有變化時是 ``base`` 加上預算上限加成）。``tier`` 是
    角色階級。任何一筆套用不了時拋出 :class:`FlashStepError`。"""
    chain = derive_chain(library, base, state, seed, tier)
    if not chain:
        return with_budget_bonus(
            at_role_tier(library, base, tier), bonus_permille(library.flash.rules, state)
        )
    return _identify(library, base, state, chain[-1])


def derive_on_current(
    library: ContentLibrary,
    base: SkillDef,
    current: SkillDef,
    state: SkillFlash,
    variation: Variation,
    *,
    seed: int,
    tier: int | None,
) -> SkillDef:
    """歷程重推失敗時（3W-R1 退路）的新一次閃現：把 ``variation`` 套在存檔裡已推出的定義
    （``current``，出題請求的 ``FlashRequest.current``）上，強度下限照它；轉型照常從原本的技能
    ``base`` 起算（轉型之前套不上的變化省略）。套不上時拋出 :class:`FlashStepError`（＝這個變化
    不合法）。"""
    record = state.records[-1]
    bonus = _record_bonus(library, state, record)
    if variation.source == "transform":
        origin = at_role_tier(library, base, tier)
        applied = _apply_transform(library, origin, state.records[:-1], record, seed, bonus=bonus)
    else:
        rng = variation_rng(seed, state.base_id, record)
        applied = apply_variation(library, current, variation, bonus=bonus, rng=rng)
    if applied is None:
        raise FlashStepError(base.id, record.nth, variation.template)
    return _identify(library, base, state, applied)
