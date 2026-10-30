"""閃現變化提議的評估（4-L9 加項，Phase 3W-7）：通過率、退回率、各類別與模板命中、名稱抽樣。

:func:`evaluate_flash` 對一批技能出三種題目（第 1 次不指定、指定第一個可用類別、第 3 次大變化），
用給定的選項來源（Mock 或真模型）請它提議，累積成提議統計；
大變化的選項另請命名步驟取名，供抽樣檢查名稱品質。**真模型評估需要使用者先啟動本機模型**，腳本入口
``scripts/eval_flash_llm.py``（預設用 Mock，不需網路）；調整建議（``llm_hint``、題目）由 PM 決定。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from trpg.content.library import ContentLibrary
from trpg.llm.client import LLMClient
from trpg.llm.flash_propose import (
    FlashProposalRecord,
    FlashProposalStats,
    LlmFlashSource,
    name_offer,
)
from trpg.skillgen.flash_category import allowed_categories
from trpg.skillgen.flash_offer import (
    FlashRequest,
    UsageSource,
    choose,
    make_offer,
    skill_before,
)
from trpg.skillgen.flash_state import SkillFlash, acquire
from trpg.skillgen.usage import SkillUsage

__all__ = ["FlashEval", "evaluate_flash", "pick_skills"]

type NamingFactory = Callable[[str, int], LLMClient]
"""（技能 ID，種子）→ 命名用的 client。"""


@dataclass(slots=True)
class FlashEval:
    """評估結果：統計與每題一列的明細（CSV 用）。"""

    stats: FlashProposalStats
    rows: list[tuple[str, str, str, int, str, str]] = field(default_factory=list)
    """（技能, 題目種類, 來源, 嘗試次數, 錯誤代碼, 提議的模板）。"""

    def csv_lines(self) -> list[str]:
        head = "skill,scenario,source,attempts,codes,templates"
        return [head, *(",".join(str(c) for c in row) for row in self.rows)]


def pick_skills(library: ContentLibrary, count: int) -> list[str]:
    """評估用的技能：1 階、主動、沒有接續段與陷阱的手寫技能（依 ID 排序取前 ``count`` 個）。"""
    found = [
        s.id
        for s in sorted(library.skills.values(), key=lambda s: s.id)
        if s.kind == "active" and s.tier == 1 and s.followup is None and s.trap is None
    ]
    return found[:count]


def _used(state: SkillFlash) -> SkillFlash:
    return state.model_copy(update={"used": True})


def _third(library: ContentLibrary, skill_id: str, seed: int) -> SkillFlash:
    """用預設來源閃兩次，回到「下一次是第 3 次大變化」的狀態。"""
    state = _used(acquire(skill_id))
    for _ in range(2):
        request = FlashRequest(library.skills[skill_id], state, SkillUsage(), seed)
        offer = make_offer(library, request, UsageSource())
        if not offer.options:
            break
        state, _skill = choose(state, offer, 0)
        state = _used(state)
    return state


def evaluate_flash(
    library: ContentLibrary,
    source: LlmFlashSource,
    skills: Sequence[str],
    *,
    seed: int = 0,
    naming: NamingFactory | None = None,
    alert_permille: int = 200,
) -> FlashEval:
    """對 ``skills`` 逐一出三種題目並累積統計。``source`` 的 ``sink`` 會被換成評估自己的收集器。"""
    stats = FlashProposalStats(alert_permille=alert_permille)
    result = FlashEval(stats)
    taken: set[str] = {s.name_zh for s in library.skills.values()}
    last: list[FlashProposalRecord] = []
    source.sink = last.append
    for index, skill_id in enumerate(skills):
        base = library.skills[skill_id]
        run_seed = seed + index
        fresh = _used(acquire(skill_id))
        third = _third(library, skill_id, run_seed)
        first_category = next(iter(allowed_categories(library.flash, base, major=False)), None)
        scenarios = [
            ("open", fresh, None),
            ("focused", fresh, first_category),
            ("major", third, None),
        ]
        for scenario, state, category in scenarios:
            request = FlashRequest(base, state, SkillUsage(), run_seed, category=category)
            last.clear()
            try:
                offer = make_offer(library, request, source)
            except ValueError:
                continue
            for record in last:
                stats.add(record)
                codes = "|".join(dict.fromkeys(c for cs in record.codes for c in cs))
                templates = "|".join(v.template for v in record.accepted)
                row = (skill_id, scenario, record.source, record.attempts, codes, templates)
                result.rows.append(row)
            if naming is not None and offer.major:
                named, _names = name_offer(
                    offer,
                    naming(skill_id, run_seed),
                    library,
                    seed=run_seed,
                    taken=taken,
                    before=skill_before(library, request),
                )
                stats.add_names(o.skill for o in named.options if o.variation.source != "minor")
    return result
