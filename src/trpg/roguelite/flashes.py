"""一輪裡的靈感點與閃現（Phase 3W-5，``docs/design/06-技能.md`` 6.34；玩法決定 #69～#72）。

純函式（``RunState`` 進、``RunState`` 出），不推進節點；規則核心在
:mod:`trpg.skillgen.flash_offer` 與
:mod:`trpg.skillgen.flash_state`，這裡只把它接到一輪：

- **靈感點**（6.34.2）：每打贏一場 ``insight_per_win`` 點（:func:`after_battle_flash`），可以存。
- **先上場用過**（6.34.3）：戰後依這場的用法統計記下來（主動技放出過；被動、反應、姿態、修正
  裝備著打完一場）。
- **閃現／重閃**（:func:`open_flash` → :func:`pick_flash`）：出題時付點（不指定 1 點出 4 個、指定
  類別 2 點出 3 個；重閃同價），選項連同套用後的技能存進 ``RunState.pending_flash``，選擇時直接取用
  （不重抽、不重算）。閃現後技能換成新的 ID（``<原技能>_fl_<歷程雜湊>``），裝備位置、備用、
  用法統計與閃現狀態跟著過去。轉型讓技能換到已滿的欄位時要指定卸下哪一招（3W-3 ``SlotPlan``）。
- **溶掉**（#71，:func:`dissolve`）：技能消失，退回花在它身上的點的一半（無條件捨去）。
- **傳承**（#72，:func:`inherit`）：還沒閃過的白板帶走舊技能最多 2 個小變化，舊技能消失、不退點。
- **LLM 來源**（3W-7）：``run.llm`` 為真而且外層裝了來源
  （:func:`trpg.roguelite.llm_hook.use_flash_source`）時，出題先請 LLM 提議（失敗退回模板）；紀錄
  寫進 ``RunState.flash_llm_log``。重播與讀檔直接用存下來的選項，不呼叫 LLM。

確定性：選項的種子標籤沿用 ``flash/<原技能>/<第幾次>/<重閃次數>``（一輪的種子）。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.errors import ChoiceError, NodeConflictError
from trpg.roguelite.llm_hook import current_flash_source
from trpg.roguelite.offers import equip_problems, skill_defs
from trpg.roguelite.state import (
    DissolveChoice,
    FlashChoice,
    FlashLlmRecord,
    FlashPickChoice,
    InheritChoice,
    PendingFlash,
    RunState,
)
from trpg.skillgen.candidates import keyword_distribution
from trpg.skillgen.flash_derive import FlashStepError, derive_skill
from trpg.skillgen.flash_major import transform_slot_plan
from trpg.skillgen.flash_offer import (
    FlashOptionSource,
    FlashRequest,
    UsageSource,
    category_counts,
    category_ranking,
    choose,
    make_offer,
)
from trpg.skillgen.flash_state import (
    COMPLETE_SLOT,
    FlashRecord,
    SkillFlash,
    acquire,
    after_battle,
    dissolve_refund,
    flash_problem,
    reflash_problem,
)
from trpg.skillgen.skill_tier import character_tier
from trpg.skillgen.usage import SkillUsage

__all__ = [
    "after_battle_flash",
    "base_def",
    "carryable_records",
    "comparable_run",
    "dissolve",
    "flash_categories",
    "flash_request",
    "focus_order",
    "inherit",
    "inherit_problem",
    "inherit_source_problem",
    "inherit_target_problem",
    "max_carry",
    "open_flash",
    "owned_skills",
    "pick_flash",
    "problem_of",
    "reflash_slots",
    "state_of",
    "with_acquired",
]


def owned_skills(run: RunState) -> tuple[str, ...]:
    """學會的技能（裝備中依技能列順序，再來是備用）。"""
    return (*run.hero.skills, *run.bench)


def state_of(run: RunState, skill_id: str) -> SkillFlash:
    """``skill_id`` 的閃現狀態（沒有記錄 ＝ 剛取得）。"""
    found = run.flash.get(skill_id)
    return acquire(skill_id) if found is None else found


def _require_owned(run: RunState, skill_id: str) -> None:
    if skill_id not in owned_skills(run):
        raise ChoiceError(f"主角沒有學會技能 {skill_id}")


def base_def(library: ContentLibrary, run: RunState, skill_id: str) -> SkillDef:
    """``skill_id`` 閃現前的原本技能（推出閃現後技能的起點）。"""
    state = state_of(run, skill_id)
    if state.base_id == skill_id:
        return skill_defs(library, run, [skill_id])[0]
    if state.base_id in library.skills:
        return library.skills[state.base_id]
    found = next((s for s in run.flash_bases if s.id == state.base_id), None)
    if found is None:
        raise ChoiceError(f"找不到 {skill_id} 閃現前的原本技能 {state.base_id}")
    return found


def flash_request(
    library: ContentLibrary,
    run: RunState,
    skill_id: str,
    *,
    slot: int | None = None,
    category: str | None = None,
) -> FlashRequest:
    """``skill_id`` 這一次閃現（``slot`` 為 ``None``）或重閃第 ``slot`` 次的出題輸入。"""
    _require_owned(run, skill_id)
    others = skill_defs(library, run, [s for s in run.hero.skills if s != skill_id])
    return FlashRequest(
        base=base_def(library, run, skill_id),
        state=state_of(run, skill_id),
        usage=run.skill_usage.get(skill_id, SkillUsage()),
        seed=run.seed,
        slot=slot,
        category=category,
        held_keywords=keyword_distribution(others, library),
        tier=character_tier(library, run.level),
        current=skill_defs(library, run, [skill_id])[0],  # 歷程重推不了時的退路（3W-R1）
    )


def problem_of(
    library: ContentLibrary, run: RunState, skill_id: str, slot: int | None = None
) -> str | None:
    """不能閃現（``slot`` 為 ``None``）或不能重閃第 ``slot`` 次的原因（點數與地點另外檢查）。"""
    if skill_id not in owned_skills(run):
        return f"主角沒有學會技能 {skill_id}"
    rules = library.flash.rules
    state = state_of(run, skill_id)
    if slot is None:
        return flash_problem(rules, state)
    return reflash_problem(rules, state, slot)


def flash_categories(
    library: ContentLibrary, run: RunState, skill_id: str, slot: int | None = None
) -> dict[str, int]:
    """選類別畫面用：每個可指定的類別目前有幾個合法變化（3W-2c；0 個不能選）。"""
    request = flash_request(library, run, skill_id, slot=slot)
    return category_counts(library, request, _source(run, lambda _record: None))


def focus_order(library: ContentLibrary, run: RunState, skill_id: str) -> list[str]:
    """指定類別時的建議順序（3W-8 模擬的 AI 用）：目前有合法變化的類別，依用法排第一的在前。"""
    request = flash_request(library, run, skill_id)
    return category_ranking(library, request, _source(run, lambda _record: None))


# ---------------------------------------------------------------------------
# 戰後：靈感點與先上場用過
# ---------------------------------------------------------------------------


def after_battle_flash(
    library: ContentLibrary, run: RunState, usage: Mapping[str, SkillUsage], *, won: bool
) -> dict[str, Any]:
    """一場戰鬥之後要併入 ``RunState`` 的欄位：打贏加靈感點；裝備中的技能「先上場用過」
    （``usage`` 是這一場的用法統計；``run`` 是戰鬥當時的狀態）。"""
    flash = dict(run.flash)
    for skill in skill_defs(library, run, run.hero.skills):
        state = state_of(run, skill.id)
        stats = usage.get(skill.id)
        casts = 0 if stats is None else stats.uses
        after = after_battle(state, skill.kind, casts=casts, finished_equipped=won)
        if after != state:
            flash[skill.id] = after
    update: dict[str, Any] = {"flash": {k: flash[k] for k in sorted(flash)}}
    if won:
        update["insight"] = run.insight + library.flash.rules.insight_per_win
    return update


# ---------------------------------------------------------------------------
# 閃現與重閃
# ---------------------------------------------------------------------------


def _source(run: RunState, sink: Callable[[BaseModel], None]) -> FlashOptionSource:
    factory = current_flash_source() if run.llm else None
    return UsageSource() if factory is None else factory(sink)


def _llm_record(record: BaseModel) -> FlashLlmRecord:
    return FlashLlmRecord.model_validate(record.model_dump(mode="json"))


def open_flash(library: ContentLibrary, run: RunState, choice: FlashChoice) -> RunState:
    """閃現或重閃出題（呼叫者先檢查地點）：付點，選項存進 ``pending_flash``。不合法或這一次沒有任何
    合法變化時拋出 :class:`ChoiceError`（沒有扣點）。"""
    if run.pending_flash is not None:
        raise NodeConflictError("還有閃現的選項沒有選（flash_pick）")
    problem = problem_of(library, run, choice.skill, choice.slot)
    if problem is not None:
        raise ChoiceError(problem)
    rule = library.flash.pricing.rule(choice.category is not None)
    if run.insight < rule.cost:
        raise ChoiceError(f"靈感點不足：需要 {rule.cost} 點，只有 {run.insight} 點")
    request = flash_request(library, run, choice.skill, slot=choice.slot, category=choice.category)
    records: list[BaseModel] = []
    try:
        offer = make_offer(library, request, _source(run, records.append))
    except ValueError as exc:
        raise ChoiceError(f"{exc}") from exc
    if not offer.options:
        raise ChoiceError("這招這一次沒有合法的變化（沒有扣點）")
    return run.model_copy(
        update={
            "insight": run.insight - offer.cost,
            "pending_flash": PendingFlash(skill=choice.skill, offer=offer),
            "flash_llm_log": (*run.flash_llm_log, *(_llm_record(r) for r in records)),
        }
    )


def pick_flash(library: ContentLibrary, run: RunState, choice: FlashPickChoice) -> RunState:
    """選閃現的選項：技能換成套用後的定義（新的 ID），閃現狀態記下這一筆與花掉的點數。"""
    pending = run.pending_flash
    if pending is None:
        raise NodeConflictError("沒有待選的閃現選項")
    skill_id = pending.skill
    try:
        state, skill = choose(state_of(run, skill_id), pending.offer, choice.pick)
    except ValueError as exc:
        raise ChoiceError(f"{exc}") from exc
    base = base_def(library, run, skill_id)
    replaced = _replace(
        library, run, skill_id, skill, state=state, base=base, unequip=choice.unequip
    )
    return replaced.model_copy(update={"pending_flash": None})


def _slot_moves(
    library: ContentLibrary, run: RunState, old_id: str, new: SkillDef, unequip: str | None
) -> tuple[str, ...]:
    """裝備中的 ``old_id`` 換成 ``new``（轉型可能換欄位）之後要卸下到備用的技能。"""
    if old_id not in run.hero.skills:
        if unequip is not None:
            raise ChoiceError("這招在備用中，不需要卸下別的技能")
        return ()
    equipped = skill_defs(library, run, run.hero.skills)
    plan = transform_slot_plan(equipped, old_id, new, library.ruleset.core.skill_slots)
    if not plan.needs_unequip:
        if unequip is not None:
            raise ChoiceError("這個選項不需要卸下別的技能")
        return ()
    if unequip not in plan.candidates:
        names = "、".join(plan.candidates)
        raise ChoiceError(f"{new.name_zh} 的欄位已滿，請指定要卸下的技能（unequip：{names}）")
    return (unequip,)


def _replace(
    library: ContentLibrary,
    run: RunState,
    old_id: str,
    new: SkillDef,
    *,
    state: SkillFlash,
    base: SkillDef,
    unequip: str | None = None,
) -> RunState:
    """學會的技能 ``old_id`` 換成 ``new``（閃現、重閃、傳承）：裝備位置、備用、用法統計、閃現狀態
    跟著換到新 ID；原本的技能定義記進 ``flash_bases``。"""
    moved = _slot_moves(library, run, old_id, new, unequip)
    skills = tuple(new.id if s == old_id else s for s in run.hero.skills if s not in moved)
    bench = tuple(sorted({*(new.id if s == old_id else s for s in run.bench), *moved}))
    defs = skill_defs(library, run, skills, (new,))
    problems = equip_problems(library, defs)
    if problems:
        raise ChoiceError("；".join(problems))
    flash = {k: v for k, v in run.flash.items() if k != old_id}
    flash[new.id] = state
    usage = dict(run.skill_usage)
    if old_id in usage:
        old = usage.pop(old_id)
        usage[new.id] = old if new.id not in usage else usage[new.id].merged(old)
    bases = {s.id: s for s in run.flash_bases}
    if base.id not in library.skills:
        bases[base.id] = base
    return _rebuild(run, skills, bench, flash=flash, usage=usage, bases=bases, extra=(new,))


def _rebuild(
    run: RunState,
    skills: tuple[str, ...],
    bench: tuple[str, ...],
    *,
    flash: Mapping[str, SkillFlash],
    usage: Mapping[str, SkillUsage],
    bases: Mapping[str, SkillDef],
    extra: Iterable[SkillDef] = (),
) -> RunState:
    """依新的裝備與備用整理生成技能、閃現狀態、用法統計與原本技能（只留學會的技能用得到的）。"""
    keep = {*skills, *bench}
    generated = {s.id: s for s in (*run.generated_skills, *extra) if s.id in keep}
    kept_flash = {k: v for k, v in flash.items() if k in keep}
    used_bases = {v.base_id for v in kept_flash.values()}
    kept_bases = {k: v for k, v in bases.items() if k in used_bases and k not in keep}
    return run.model_copy(
        update={
            "hero": run.hero.model_copy(update={"skills": skills}),
            "bench": bench,
            "generated_skills": tuple(generated[k] for k in sorted(generated)),
            "flash": {k: kept_flash[k] for k in sorted(kept_flash)},
            "skill_usage": {k: usage[k] for k in sorted(usage) if k in keep},
            "flash_bases": tuple(kept_bases[k] for k in sorted(kept_bases)),
        }
    )


def with_acquired(run: RunState, skill_id: str, *, complete: bool = False) -> RunState:
    """剛學會 ``skill_id``（白板或完整技能）：閃現狀態從頭算（完整技能標記為已閃 3 次、不能
    再閃）。"""
    flash = dict(run.flash)
    if complete:
        flash[skill_id] = acquire(skill_id, complete=True)
    else:
        flash.pop(skill_id, None)
    return run.model_copy(update={"flash": {k: flash[k] for k in sorted(flash)}})


# ---------------------------------------------------------------------------
# 溶掉與傳承
# ---------------------------------------------------------------------------


def _without(run: RunState, skill_id: str) -> RunState:
    skills = tuple(s for s in run.hero.skills if s != skill_id)
    bench = tuple(s for s in run.bench if s != skill_id)
    bases = {s.id: s for s in run.flash_bases}
    return _rebuild(run, skills, bench, flash=run.flash, usage=run.skill_usage, bases=bases)


def dissolve(library: ContentLibrary, run: RunState, choice: DissolveChoice) -> RunState:
    """溶掉一招（#71）：技能消失，退回花在它身上的點的一半（無條件捨去）。"""
    _require_owned(run, choice.skill)
    refund = dissolve_refund(library.flash.rules, state_of(run, choice.skill))
    gone = _without(run, choice.skill)
    return gone.model_copy(update={"insight": gone.insight + refund})


def inherit_problem(
    library: ContentLibrary, run: RunState, skill_id: str, source_id: str, records: Iterable[int]
) -> str | None:
    """不能傳承的原因（地點另外檢查）；可以時 ``None``。"""
    owned = owned_skills(run)
    if skill_id not in owned or source_id not in owned:
        return "傳承的兩招都必須是學會的技能"
    if skill_id == source_id:
        return "不能傳承給自己"
    problem = inherit_target_problem(state_of(run, skill_id))
    if problem is not None:
        return problem
    return _carried_problem(library, state_of(run, source_id), list(records))


def inherit_target_problem(target: SkillFlash) -> str | None:
    """這招不能 **接受** 傳承的原因（只看它自己的閃現狀態）；可以時 ``None``。"""
    if target.complete:
        return "完整技能不能接受傳承"
    if target.records:
        return "只有還沒閃過的技能可以接受傳承"
    return None


def carryable_records(library: ContentLibrary, source: SkillFlash) -> tuple[int, ...]:
    """舊技能可以被帶走的變化（第幾次；一筆一筆照 :func:`inherit_problem` 的規則檢查）。"""
    return tuple(
        r.nth for r in source.records if _carried_problem(library, source, [r.nth]) is None
    )


def inherit_source_problem(library: ContentLibrary, run: RunState, skill_id: str) -> str | None:
    """這招不能 **傳承給別招** 的原因（3W-R2，給前端顯示；可以時 ``None``）：沒有可以帶走的
    小變化，或沒有別招可以接受傳承。"""
    if not carryable_records(library, state_of(run, skill_id)):
        return "這招沒有可以帶走的小變化（大變化、轉型、完整技能的調整欄不能傳承）"
    others = (s for s in owned_skills(run) if s != skill_id)
    if all(inherit_target_problem(state_of(run, s)) is not None for s in others):
        return "沒有還沒閃過的新技能可以接受傳承"
    return None


def reflash_slots(library: ContentLibrary, state: SkillFlash) -> tuple[int, ...]:
    """這招可以重閃的欄（完整技能只有調整欄 0；一般技能是已有的各次變化；點數與地點另外檢查）。"""
    rules = library.flash.rules
    slots = (COMPLETE_SLOT,) if state.complete else tuple(r.nth for r in state.records)
    return tuple(s for s in slots if reflash_problem(rules, state, s) is None)


def _carried_problem(library: ContentLibrary, source: SkillFlash, picked: list[int]) -> str | None:
    if len(set(picked)) != len(picked):
        return "同一個變化不能帶兩次"
    if len(picked) > max_carry(library):
        return f"最多帶走 {max_carry(library)} 個小變化"
    for nth in picked:
        record = None if source.complete else source.record(nth)
        if record is None:
            return f"舊技能沒有第 {nth} 次的變化"
        if record.variation.source != "minor":
            return "大變化、轉型、完整技能的調整欄不能傳承"
        if library.flash.minor_template(record.variation.template) is None:
            return _stale_text(nth, record.variation.template)
    return None


def _stale_text(nth: int, template: str) -> str:
    """舊技能的某一筆變化在目前的內容版本已經沒有了（內容改版；3W-R1，與「對這招不合法」分開）。"""
    return f"舊技能第 {nth} 次的變化（{template}）在目前的內容版本已經沒有了，不能帶走"


def inherit(library: ContentLibrary, run: RunState, choice: InheritChoice) -> RunState:
    """傳承（#72）：新技能帶走舊技能的小變化（算已閃次數），舊技能消失、不退點。"""
    problem = inherit_problem(library, run, choice.skill, choice.source, choice.records)
    if problem is not None:
        raise ChoiceError(problem)
    source = state_of(run, choice.source)
    target = state_of(run, choice.skill)
    carried = tuple(
        FlashRecord(nth=i, variation=rec.variation)
        for i, nth in enumerate(choice.records, 1)
        if (rec := source.record(nth)) is not None
    )
    # 「先上場用過」（used）照接受傳承的白板自己的狀態，不沿用舊技能的（3W-6b，06 6.34）
    state = target.model_copy(update={"records": carried, "used": target.used})
    base = base_def(library, run, choice.skill)
    try:
        skill = derive_skill(library, base, state, run.seed, character_tier(library, run.level))
    except FlashStepError as exc:
        nth = choice.records[exc.nth - 1]  # 帶走的第 i 筆 ＝ 舊技能的第 records[i-1] 次
        raise ChoiceError(
            f"舊技能第 {nth} 次的變化（{exc.template}）對 {base.name_zh} 不合法，請改帶別的變化"
        ) from exc
    gone = _without(run, choice.source)
    return _replace(library, gone, choice.skill, skill, state=state, base=base)


# ---------------------------------------------------------------------------
# 比對
# ---------------------------------------------------------------------------


def comparable_run(run: RunState) -> dict[str, Any]:
    """逐位元比對一輪用的 JSON（3W-7 待決：排除 LLM 提議紀錄的耗時 ``seconds``）。"""
    data = run.model_dump(mode="json")
    for record in data.get("flash_llm_log", []):
        record.pop("seconds", None)
    return data


def max_carry(library: ContentLibrary) -> int:
    """傳承時最多帶走幾個小變化：第 ``major_flash`` 次是大變化，所以是它 − 1。"""
    return library.flash.rules.major_flash - 1
