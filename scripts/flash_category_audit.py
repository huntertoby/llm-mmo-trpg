"""閃現「修正」「觸發」類為什麼沒被選的量測（BAL-2，只量不調；不改任何規則與預設值）。

三部分（輸出 Markdown 到標準輸出，相同參數必得逐字相同的輸出）：

A. 出題端：對內建技能（角色階級 1～3）與白板（1～3 階、各種子），統計每個類別
   「可指定（``category_counts`` > 0）的比例」「不指定時出現在選項裡的次數」；以及
   修正（modifier）、觸發（trigger）類每個模板的「合法／不合法」與不合法原因。
B. 選擇端：``category_ranking``（AI 的 all 策略）面對三種用法統計時，這兩類排第幾、
   用法分數多少（為什麼從不選）。
C. 一輪實際模擬（``trpg sim flash`` 同一套 AI：none／all／mixed × 種子）中，
   這兩類出現在選項與被選的次數，以及被閃現的技能種類。

用法::

    uv run python scripts/flash_category_audit.py --skills skill_a,skill_b --seeds 1 --no-sim
    uv run python scripts/flash_category_audit.py --seeds 3 --sim-seeds 20 --jobs 8
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from trpg.content.flash_templates import FlashTemplate
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite import auto as auto_module
from trpg.roguelite.auto import ALL_FLASH_POLICIES, FLASH_POLICIES, FlashPolicy, auto_play
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.start import default_start, new_keyword_run
from trpg.roguelite.state import FlashChoice, FlashPickChoice
from trpg.sim.parallel import run_tasks
from trpg.skillgen.flash_category import allowed_categories, template_kinds
from trpg.skillgen.flash_derive import (
    _minor_drafts,
    at_role_tier,
    with_budget_bonus,
)
from trpg.skillgen.flash_offer import (
    FlashRequest,
    UsageSource,
    _usage_score,
    category_counts,
    category_ranking,
    make_offer,
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_state import Variation, acquire
from trpg.skillgen.flash_trade import MINOR_OPS
from trpg.skillgen.random_composer import ComposeError, default_library
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.whiteboard import WHITEBOARD_KINDS, compose_whiteboard

FOCUS = ("modifier", "trigger")
"""本次要查的兩個類別。"""
ROLE_TIERS = (1, 2, 3)


# ---------------------------------------------------------------------------
# 受測的（技能, 角色階級）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Subject:
    """一個受測對象：技能、角色階級、來源標記（builtin 或 whiteboard）。"""

    skill: SkillDef
    tier: int
    origin: str

    @property
    def label(self) -> str:
        return f"{self.origin}:{self.skill.id}@T{self.tier}"


def build_subjects(
    library: ContentLibrary, skill_ids: Sequence[str] | None, board_seeds: int
) -> list[Subject]:
    """內建技能 × 角色階級 1～3，加上白板（1～3 階 × 三種類 × 種子）。依標籤排序（確定性）。"""
    out: list[Subject] = []
    ids = sorted(library.skills) if skill_ids is None else list(skill_ids)
    for skill_id in ids:
        out.extend(Subject(library.skills[skill_id], t, "builtin") for t in ROLE_TIERS)
    if skill_ids is None:
        for tier in ROLE_TIERS:
            for kind in WHITEBOARD_KINDS:
                for seed in range(1, board_seeds + 1):
                    try:
                        board = compose_whiteboard(seed, kind=kind, tier=tier, library=library)
                    except ComposeError:
                        continue
                    out.append(Subject(board, tier, "whiteboard"))
    return sorted(out, key=lambda s: s.label)


def request_of(subject: Subject, seed: int, usage: SkillUsage | None = None) -> FlashRequest:
    return FlashRequest(
        base=subject.skill,
        state=acquire(subject.skill.id),
        usage=usage or SkillUsage(),
        seed=seed,
        tier=subject.tier,
    )


# ---------------------------------------------------------------------------
# A. 出題端
# ---------------------------------------------------------------------------


def _why_empty(op: str, skill: SkillDef, template: FlashTemplate, library: ContentLibrary) -> str:
    """``op`` 做不出草稿的具體原因（照 ``flash_ops`` 各改法的判斷；其餘歸「其他」）。"""
    checks: dict[str, Callable[[], str]] = {
        "potency": lambda: "陷阱技" if skill.trap is not None else "其他",
        "trigger_range": lambda: (
            "形狀 self 且無觸發距離上限"
            if skill.trigger is None or skill.trigger.max_distance is None
            else "其他"
        ),
        "trigger_cap": lambda: _why_cap(skill),
        "mod_potency": lambda: "沒有正的傷害／治療幅度或可重調的幅度",
        "mod_duration": lambda: "沒有帶持續回合的命中後效果或可加的召喚持續",
        "mod_stack": lambda: "沒有依空欄位計算的規則（或已達上限）",
        "mod_cooldown": lambda: "沒有命中後冷卻 −1 的規則",
        "mod_cost": lambda: "沒有可減輕的代價規則（或只有一條規則）",
        "stance_enter_light": lambda: "沒有進入代價可減（姿態的進入 AP 固定、沒有冷卻）",
        "followup_potency": lambda: "不是複合技或接續段沒有傷害",
        "followup_area": lambda: "不是複合技或接續段形狀沒有可增大的參數",
        "followup_range": lambda: "不是複合技或接續段沒有固定射程（或已達上限）",
        "followup_element": lambda: "不是複合技、接續段沒有傷害／效果已滿／元素已有",
        "mod_range": lambda: "規則已滿 2 條且沒有可升的射程 +1",
        "mod_keyword": lambda: _why_mod_keyword(skill),
        "mod_relax": lambda: _why_relax(skill),
        "stance_light": lambda: _why_stance(skill, library, "light"),
        "stance_heavy": lambda: _why_stance(skill, library, "heavy"),
        "stance_potency": lambda: _why_stance(skill, library, "potency"),
    }
    check = checks.get(op)
    return "其他" if check is None else check()


def _why_cap(skill: SkillDef) -> str:
    if skill.kind != "passive":
        return "反應技不適用（模板限被動）"
    if skill.trigger is None:
        return "沒有 trigger"
    return "觸發次數上限已達 3"


def _why_mod_keyword(skill: SkillDef) -> str:
    if skill.kind != "modifier":
        return "不是修正型被動"
    if all(r.condition is None for r in skill.modifiers):
        return "規則沒有條件可加「或」"
    if any(r.condition is not None and r.condition.any_of is not None for r in skill.modifiers):
        return "條件已有 any_of"
    return "關鍵字沒有可用的嫁接條件（或與原條件相同）"


def _why_relax(skill: SkillDef) -> str:
    if all(r.condition is None for r in skill.modifiers):
        return "規則沒有條件可放寬"
    if all(r.condition is None or r.condition.any_of is not None for r in skill.modifiers):
        return "條件已有 any_of"
    return "血量門檻已達上限"


def _why_stance(  # noqa: PLR0911 - 依序判斷的原因表
    skill: SkillDef, library: ContentLibrary, which: str
) -> str:
    if skill.kind != "stance":
        return "不是姿態"
    if skill.form_id is not None:
        return "變身姿態沒有進入代價可減（或費用類沒填 cost_fields）"
    stance_effects = [e for e in skill.effects if e.type == "apply_status"]
    if len(stance_effects) != 1:
        return "沒有恰好一個姿態本體效果"
    status = stance_effects[0].status
    if status is None or library.flash.stance_rung(status) is None:
        return "姿態狀態不在階梯上（白板姿態或自訂）"
    if which == "light" and skill.stance_upkeep <= 0:
        return "沒有維持費可減"
    if which == "heavy" and skill.stance_upkeep >= 2:  # noqa: PLR2004 - 維持費上限
        return "維持費已達上限 2"
    return "已在階梯最高級"


def _static_reject(
    library: ContentLibrary, subject: Subject, template: FlashTemplate
) -> str | None:
    """不用套用就知道的原因（模板資料條件）。"""
    if subject.tier < template.min_tier:
        return "illegal:階級不足（模板 min_tier）"
    if subject.skill.kind not in template_kinds(library.flash, template):
        return "illegal:技能種類不符（模板 kinds）"
    if template.op not in MINOR_OPS:
        return "illegal:op 未實作"
    return None


def classify(
    library: ContentLibrary,
    subject: Subject,
    template: FlashTemplate,
    variation: Variation,
    request: FlashRequest,
) -> str:
    """一個（技能, 模板變體）的結果：``legal`` 或 ``illegal:<原因>``。"""
    static = _static_reject(library, subject, template)
    if static is not None:
        return static
    try:
        if try_variation(library, request, variation) is not None:
            return "legal"
        current = with_budget_bonus(
            at_role_tier(library, subject.skill, subject.tier),
            library.flash.rules.budget_bonus_permille(1),
        )
        if not _minor_drafts(current, variation, library):
            return f"illegal:結構不符/{_why_empty(template.op, current, template, library)}"
    except Exception as exc:
        return f"illegal:例外 {type(exc).__name__}"
    return "illegal:預算窗/強度下限（重調失敗）"


def _variants(
    library: ContentLibrary, request: FlashRequest, template: FlashTemplate, skill: SkillDef
) -> list[Variation]:
    source = UsageSource()
    return source._variants(library, request, template, skill)


def audit_templates(
    library: ContentLibrary, subjects: Sequence[Subject]
) -> dict[str, Counter[str]]:
    """修正、觸發類每個模板的結果計數：``{模板 ID: Counter(結果)}``。只算技能種類屬於該類別
    ``kinds`` 的受測對象（其他種類本來就不會看到這個類別）。"""
    table = library.flash
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for subject in subjects:
        request = request_of(subject, 1)
        for template in table.minor:
            if template.category not in FOCUS:
                continue
            if subject.skill.kind not in table.category(template.category).kinds:
                continue
            if subject.skill.kind not in template_kinds(table, template):
                continue  # 模板自己限定的種類（例如姿態不用 mod_*）：本來就不會對它出，不算
            variants = _variants(library, request, template, subject.skill)
            if not variants:
                out[template.id]["illegal:無候選變體（例如沒有可用關鍵字）"] += 1
                continue
            # 一個（技能, 模板）只算一次：任何一個變體合法即合法，否則取第一個變體的原因
            results = [classify(library, subject, template, v, request) for v in variants]
            out[template.id]["legal" if "legal" in results else results[0]] += 1
    return out


def audit_offers(
    library: ContentLibrary, subjects: Sequence[Subject], seeds: int
) -> tuple[dict[str, Counter[str]], dict[str, Counter[str]]]:
    """每個技能種類的類別統計。回傳（可指定次數, 不指定出題的出現次數），鍵為 ``種類/類別``，
    Counter 的 ``pairs`` 是該種類的（技能, 階級）數、``allowed`` 是類別開放數、
    ``focusable`` 是 ``category_counts`` > 0 的數；出題端為出現在選項裡的選項數與有出現的題數。"""
    focus: dict[str, Counter[str]] = defaultdict(Counter)
    offers: dict[str, Counter[str]] = defaultdict(Counter)
    for subject in subjects:
        kind = subject.skill.kind
        focus[kind]["pairs"] += 1
        request = request_of(subject, 1)
        counts = category_counts(library, request)
        for category, n in counts.items():
            focus[f"{kind}/{category}"]["allowed"] += 1
            focus[f"{kind}/{category}"]["focusable"] += int(n > 0)
        for seed in range(1, seeds + 1):
            offer = make_offer(library, request_of(subject, seed))
            offers[kind]["offers"] += 1
            seen = Counter(o.variation.category for o in offer.options)
            for category, n in seen.items():
                offers[f"{kind}/{category}"]["options"] += n
                offers[f"{kind}/{category}"]["offers_with"] += 1
    return focus, offers


# ---------------------------------------------------------------------------
# B. 選擇端
# ---------------------------------------------------------------------------

USAGE_PROFILES: dict[str, SkillUsage] = {
    "無統計": SkillUsage(),
    "單體常用": SkillUsage(
        uses=6, targets=6, distance=12, kills=1, target_keywords={"burning": 3, "wet": 2}
    ),
    "多目標常用": SkillUsage(uses=6, targets=14, distance=6, kills=2),
}


def audit_ranking(library: ContentLibrary, subjects: Sequence[Subject]) -> dict[str, Counter[str]]:
    """``category_ranking`` 的結果：鍵 ``用法/種類``，值為（可排名的題數、修正或觸發排第一的次數、
    排名裡有這兩類的次數、這兩類的最高用法分數總和…）。"""
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for subject in subjects:
        for name, usage in USAGE_PROFILES.items():
            request = request_of(subject, 1, usage)
            ranking = category_ranking(library, request)
            key = f"{name}/{subject.skill.kind}"
            if not ranking:
                out[key]["no_category"] += 1
                continue
            out[key]["ranked"] += 1
            out[key][f"first:{ranking[0]}"] += 1
            for category in FOCUS:
                if category in ranking:
                    out[key][f"has:{category}"] += 1
                    out[key][f"rank_sum:{category}"] += ranking.index(category) + 1
                    out[key][f"len_sum:{category}"] += len(ranking)
    return out


def top_scores(library: ContentLibrary, subjects: Sequence[Subject]) -> dict[str, Counter[str]]:
    """各類別「排第一的變化」的用法分數分布（看修正、觸發類的分數是不是永遠最低）。
    鍵為 ``用法名/類別``，值為 ``{分數: 次數}``。"""
    out: dict[str, Counter[str]] = defaultdict(Counter)
    source = UsageSource()
    for subject in subjects:
        for name, usage in USAGE_PROFILES.items():
            request = request_of(subject, 1, usage)
            before = skill_before(library, request)
            for category in allowed_categories(library.flash, before, major=False):
                ranked = source.ranked(library, request, category, before)
                top = ranked[0] if ranked else None
                template = None if top is None else library.flash.minor_template(top.template)
                if top is None or template is None:
                    continue
                score = _usage_score(library, usage, template, top)
                out[f"{name}/{category}"][str(score)] += 1
    return out


# ---------------------------------------------------------------------------
# C. 一輪實際模擬
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SimStats:
    """一個（策略, 種子）一輪的計數。"""

    policy: str
    seed: int
    offers: int
    options: tuple[tuple[str, int], ...]
    """出現在選項裡的類別計數（依類別排序）。"""
    offers_with: tuple[tuple[str, int], ...]
    picks: tuple[tuple[str, int], ...]
    """AI 選的類別計數（AI 一律選第一個選項）。"""
    flashed_kinds: tuple[tuple[str, int], ...]
    """每次出題時被閃現的技能種類。"""
    held_kinds: tuple[tuple[str, int], ...]
    """每次出題時主角技能列裡各種類的招數總和。"""
    held_offers: tuple[tuple[str, int], ...]
    """每次出題時主角持有至少一招該種類的次數。"""


def simulate(library: ContentLibrary, task: tuple[FlashPolicy, int]) -> SimStats:
    """跑一輪 ``trpg run auto``（AI 閃現策略 policy），攔截每次閃現出題與選擇。只在本行程內
    暫時包住 ``auto.apply_choice``，跑完還原，不改引擎行為。"""
    policy, seed = task
    options: Counter[str] = Counter()
    offers_with: Counter[str] = Counter()
    picks: Counter[str] = Counter()
    flashed: Counter[str] = Counter()
    held: Counter[str] = Counter()
    held_offers: Counter[str] = Counter()
    n_offers = 0
    original = getattr(auto_module, "apply_choice")  # noqa: B009

    def spy(lib: ContentLibrary, run: Any, choice: Any) -> Any:
        nonlocal n_offers
        result = original(lib, run, choice)
        if isinstance(choice, FlashChoice) and result.pending_flash is not None:
            n_offers += 1
            offer = result.pending_flash.offer
            kinds = Counter(str(d.kind) for d in skill_defs(lib, run, run.hero.skills))
            for kind, n in kinds.items():
                held[kind] += n
                held_offers[kind] += 1
            skill_kind = str(skill_defs(lib, run, [result.pending_flash.skill])[0].kind)
            flashed[skill_kind] += 1
            for category in sorted({o.variation.category for o in offer.options}):
                offers_with[category] += 1
            for option in offer.options:
                options[option.variation.category] += 1
        elif isinstance(choice, FlashPickChoice) and run.pending_flash is not None:
            picks[run.pending_flash.offer.options[choice.pick].variation.category] += 1
        return result

    setattr(auto_module, "apply_choice", spy)  # noqa: B010
    try:
        weapon, keywords = default_start(library, seed)
        run0 = new_keyword_run(library, weapon, keywords, seed)
        auto_play(library, run0, flash_policy=policy)
    finally:
        setattr(auto_module, "apply_choice", original)  # noqa: B010
    return SimStats(
        policy=policy,
        seed=seed,
        offers=n_offers,
        options=tuple(sorted(options.items())),
        offers_with=tuple(sorted(offers_with.items())),
        picks=tuple(sorted(picks.items())),
        flashed_kinds=tuple(sorted(flashed.items())),
        held_kinds=tuple(sorted(held.items())),
        held_offers=tuple(sorted(held_offers.items())),
    )


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return [*lines, ""]


def _pct(num: int, den: int) -> str:
    return "-" if den == 0 else f"{num * 100 / den:.1f}%"


def report_templates(library: ContentLibrary, data: dict[str, Counter[str]]) -> list[str]:
    lines = ["## A2. 修正、觸發類每個模板的合法性（每個（技能, 階級）算一次，nth=1）", ""]
    rows: list[list[str]] = []
    reasons: Counter[str] = Counter()
    for template in library.flash.minor:
        if template.category not in FOCUS:
            continue
        counts = data.get(template.id, Counter())
        total = sum(counts.values())
        legal = counts["legal"]
        rows.append(
            [
                template.id,
                template.category,
                "/".join(template_kinds(library.flash, template)),
                str(template.min_tier),
                str(total),
                str(legal),
                _pct(legal, total),
            ]
        )
        for reason, n in counts.items():
            if reason != "legal":
                reasons[f"{template.id} | {reason[8:]}"] += n
    lines += _table(["模板", "類別", "適用種類", "min_tier", "試過", "合法", "合法率"], rows)
    lines += ["### 不合法原因（依次數排序）", ""]
    ordered = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
    lines += _table(["模板 | 原因", "次數"], [[k, str(v)] for k, v in ordered])
    return lines


def report_offers(
    focus: dict[str, Counter[str]], offers: dict[str, Counter[str]], seeds: int
) -> list[str]:
    lines = [f"## A1. 出題端：每個種類 × 類別（每個（技能, 階級）出 {seeds} 次不指定題）", ""]
    rows: list[list[str]] = []
    for key in sorted(focus):
        if "/" not in key:
            continue
        kind, category = key.split("/")
        f = focus[key]
        o = offers.get(key, Counter())
        total_offers = offers[kind]["offers"]
        rows.append(
            [
                kind,
                category,
                str(focus[kind]["pairs"]),
                _pct(f["allowed"], focus[kind]["pairs"]),
                _pct(f["focusable"], f["allowed"]),
                str(o["options"]),
                _pct(o["offers_with"], total_offers),
            ]
        )
    lines += _table(
        [
            "技能種類",
            "類別",
            "受測數",
            "類別開放",
            "可指定（>0）",
            "出現的選項數",
            "有出現的題數比",
        ],
        rows,
    )
    return lines


def report_ranking(rank: dict[str, Counter[str]], scores: dict[str, Counter[str]]) -> list[str]:
    lines = ["## B. 選擇端：`category_ranking`（all 策略）", ""]
    rows: list[list[str]] = []
    for key in sorted(rank):
        c = rank[key]
        usage, kind = key.split("/")
        firsts = {k[6:]: v for k, v in c.items() if k.startswith("first:")}
        top = ", ".join(f"{k}:{v}" for k, v in sorted(firsts.items(), key=lambda kv: -kv[1]))
        extra = []
        for category in FOCUS:
            n = c[f"has:{category}"]
            if n:
                extra.append(
                    f"{category} 平均排第 {c[f'rank_sum:{category}'] / n:.1f}"
                    f"／{c[f'len_sum:{category}'] / n:.1f}"
                )
        rows.append([usage, kind, str(c["ranked"]), top or "-", "；".join(extra) or "-"])
    lines += _table(["用法", "種類", "可排名數", "排第一的類別（次數）", "修正／觸發的名次"], rows)
    lines += ["### 各類別排第一的變化的用法分數分布（分數：次數）", ""]
    srows = [
        [k.split("/")[0], k.split("/")[1], ", ".join(f"{s}:{n}" for s, n in sorted(v.items()))]
        for k, v in sorted(scores.items())
    ]
    lines += _table(["用法", "類別", "分數：次數"], srows)
    return lines


def report_sim(results: Sequence[SimStats]) -> list[str]:
    lines = ["## C. 一輪實際模擬", ""]
    by_policy: dict[str, list[SimStats]] = defaultdict(list)
    for r in results:
        by_policy[r.policy].append(r)
    categories = sorted({c for r in results for c, _ in r.options})
    rows: list[list[str]] = []
    for policy in ALL_FLASH_POLICIES:
        group = by_policy.get(policy)
        if not group:
            continue
        opts, withs, picks = Counter[str](), Counter[str](), Counter[str]()
        for r in group:
            opts.update(dict(r.options))
            withs.update(dict(r.offers_with))
            picks.update(dict(r.picks))
        offers = sum(r.offers for r in group)
        for category in categories:
            rows.append(
                [
                    policy,
                    category,
                    str(len(group)),
                    str(offers),
                    str(opts[category]),
                    _pct(withs[category], offers),
                    str(picks[category]),
                    _pct(picks[category], sum(picks.values())),
                ]
            )
    lines += _table(
        ["策略", "類別", "輪數", "出題數", "選項數", "有出現的題數比", "被選次數", "占選擇比"], rows
    )
    lines += ["### 被閃現的技能種類與主角持有的種類（每次出題）", ""]
    krows: list[list[str]] = []
    for policy in ALL_FLASH_POLICIES:
        group = by_policy.get(policy)
        if not group:
            continue
        flashed, held, held_offers = Counter[str](), Counter[str](), Counter[str]()
        for r in group:
            flashed.update(dict(r.flashed_kinds))
            held.update(dict(r.held_kinds))
            held_offers.update(dict(r.held_offers))
        offers = sum(r.offers for r in group)
        for kind in sorted(set(flashed) | set(held)):
            krows.append(
                [
                    policy,
                    kind,
                    str(flashed[kind]),
                    _pct(flashed[kind], offers),
                    _pct(held_offers[kind], offers),
                ]
            )
    lines += _table(["策略", "種類", "被閃現次數", "占出題比", "出題時主角持有≥1 招的比例"], krows)
    return lines


type Table = dict[str, Counter[str]]


def audit_chunk(library: ContentLibrary, task: tuple[list[Subject], int]) -> tuple[Table, ...]:
    """一批受測對象的全部稽核（平行用）。"""
    subjects, seeds = task
    focus, offers = audit_offers(library, subjects, seeds)
    return (
        focus,
        offers,
        audit_templates(library, subjects),
        audit_ranking(library, subjects),
        top_scores(library, subjects),
    )


def merge(tables: Sequence[Table]) -> Table:
    """把各批的計數表相加（鍵與計數的順序不影響輸出，報表會排序）。"""
    out: Table = defaultdict(Counter)
    for table in tables:
        for key, counts in table.items():
            out[key].update(counts)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skills", help="只測這些內建技能 ID（逗號分隔；給了就不測白板）")
    parser.add_argument("--seeds", type=int, default=3, help="A1 每個對象的不指定出題種子數")
    parser.add_argument("--board-seeds", type=int, default=6, help="每個（階級, 種類）的白板數")
    parser.add_argument("--sim-seeds", type=int, default=20, help="C 每個策略的種子數")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--no-sim", action="store_true", help="略過 C（一輪實際模擬）")
    parser.add_argument(
        "--policies",
        default=",".join(FLASH_POLICIES),
        help="C 的策略（逗號分隔；none 集中、balanced 均衡、all 全指定；預設 none,all,mixed）",
    )
    args = parser.parse_args(argv)
    library = default_library()
    ids = None if args.skills is None else [s for s in args.skills.split(",") if s]
    subjects = build_subjects(library, ids, args.board_seeds)
    print(f"# 閃現「修正」「觸發」類稽核（受測 {len(subjects)} 個（技能, 階級））\n")
    chunks = [subjects[i :: args.jobs * 4] for i in range(args.jobs * 4)]
    parts = run_tasks(audit_chunk, library, [(c, args.seeds) for c in chunks if c], jobs=args.jobs)
    focus, offers, templates, ranking, scores = (merge([p[i] for p in parts]) for i in range(5))
    out = report_offers(focus, offers, args.seeds)
    out += report_templates(library, templates)
    out += report_ranking(ranking, scores)
    if not args.no_sim:
        policies: list[FlashPolicy] = [
            p for p in ALL_FLASH_POLICIES if p in args.policies.split(",")
        ]
        tasks = [(p, s) for p in policies for s in range(1, args.sim_seeds + 1)]
        out += report_sim(run_tasks(simulate, library, tasks, jobs=args.jobs))
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
