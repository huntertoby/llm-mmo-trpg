"""閃現 LLM 提議的多樣性量測（只量不調）。

跑法::

    uv run python scripts/eval_flash_diversity.py --mock --csv out.csv        # Mock，不需網路
    uv run python scripts/eval_flash_diversity.py --real --csv out.csv        # 真模型（需本機模型）
    uv run python scripts/eval_flash_diversity.py --from-csv out.csv          # 只重新彙整既有 CSV

選技能時涵蓋所有技能類型（主動武器／法術／召喚／輔助／接續、陷阱、被動、反應、修正型被動、姿態、
變身姿態），再加「先轉型再閃」的技能（元素姿態、召喚、陷阱、反應、被動、修正）；每招依角色階級 1～3
各跑一遍；情境為：不指定類別、指定類別、第 3 次大變化、第 3 次大變化指定加深／橋接。

每題一列 CSV：目錄（套得上）的模板、LLM 提出的模板、被退回的模板、最後呈現給玩家的選項與其來源
（``llm`` 模型提的、``filler`` 資料補位、``transform`` 轉型保底）。彙整輸出模板與類別的
「套得上 vs 提出」表、轉型專節、退回率與補位率。腳本不改任何設定、不自動調參，建議由 PM 決定。
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.llm import OpenAICompatClient, load_llm_config
from trpg.llm.flash_propose import (
    FlashProposalRecord,
    LlmFlashSource,
    mock_flash_source,
)
from trpg.shared.rng import Rng
from trpg.skillgen.flash_catalog import build_catalog
from trpg.skillgen.flash_category import is_support_skill
from trpg.skillgen.flash_derive import FlashError, derive_skill
from trpg.skillgen.flash_major import transform_variations
from trpg.skillgen.flash_offer import (
    FlashRequest,
    UsageSource,
    choose,
    make_offer,
    skill_before,
    try_variation,
)
from trpg.skillgen.flash_state import SkillFlash, acquire, next_nth, slot_is_major, with_flash
from trpg.skillgen.usage import SkillUsage

COLUMNS = [
    "group",
    "skill",
    "kind",
    "role_tier",
    "scenario",
    "requested_category",
    "major",
    "catalog",
    "catalog_categories",
    "proposed",
    "rejected",
    "source",
    "attempts",
    "codes",
    "final",
    "origins",
    "names",
    "seconds",
    "error",
]

PREFER_RATIO = 2
POSITION_MIN_CATALOG = 6
"""提出占比 ÷ 套得上占比超過這個數視為偏好。"""

SCENARIOS = ("open", "focused", "major", "major_focused")


# ---------------------------------------------------------------------------
# 取樣
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Sample:
    group: str
    skill_id: str
    role_tier: int
    state: SkillFlash
    seed: int


def _group_of(library: ContentLibrary, skill: SkillDef) -> str:  # noqa: PLR0911
    effects = {e.type for e in skill.effects}
    if skill.kind == "stance":
        return "stance_form" if "enter_form" in effects else "stance_basic"
    if skill.kind != "active":
        support = "_support" if is_support_skill(skill, library.flash) else ""
        return f"{skill.kind}{support}"
    if skill.trap is not None:
        return "active_trap"
    if skill.followup is not None:
        return "active_followup"
    if "summon" in effects:
        return "active_summon"
    if is_support_skill(skill, library.flash):
        return "active_support"
    return f"active_{skill.category}"


def _pick(ids: Sequence[str], count: int, seed: int) -> list[str]:
    ordered = sorted(ids)
    if len(ordered) <= count:
        return ordered
    return sorted(Rng(seed).fork("pick").shuffled(ordered)[:count])


def _used(state: SkillFlash) -> SkillFlash:
    return state.model_copy(update={"used": True})


def _advance(
    library: ContentLibrary, skill_id: str, tier: int, seed: int, flashes: int
) -> SkillFlash:
    """用預設來源閃 ``flashes`` 次（模擬前面的小變化），回到「下一次」的狀態。"""
    state = _used(acquire(skill_id))
    for _ in range(flashes):
        request = FlashRequest(library.skills[skill_id], state, SkillUsage(), seed, tier=tier)
        offer = make_offer(library, request, UsageSource())
        if not offer.options:
            break
        state, _skill = choose(state, offer, 0)
        state = _used(state)
    return state


def _transformed(
    library: ContentLibrary, skill_id: str, template: str, tier: int, seed: int
) -> SkillFlash | None:
    """前兩次小變化後，第 3 次選轉型 ``template``；這招轉不了時回傳 ``None``。"""
    base = library.skills[skill_id]
    state = _advance(library, skill_id, tier, seed, 2)
    request = FlashRequest(base, state, SkillUsage(), seed, tier=tier)
    before = skill_before(library, request)
    rng = Rng(seed).fork("transform-probe")
    found = [v for v in transform_variations(library, before, tier=tier, rng=rng)]
    variation = next((v for v in found if v.template == template), None)
    if variation is None:
        return None
    after = _used(with_flash(state, variation))
    try:
        derive_skill(library, base, after, seed, tier)
    except FlashError:
        return None
    return after


def build_samples(
    library: ContentLibrary, per_group: int, seed: int, per_transform: int
) -> list[Sample]:
    groups: dict[str, list[str]] = {}
    for skill in sorted(library.skills.values(), key=lambda s: s.id):
        groups.setdefault(_group_of(library, skill), []).append(skill.id)
    samples: list[Sample] = []
    index = 0
    for group in sorted(groups):
        for skill_id in _pick(groups[group], per_group, seed + len(group)):
            skill = library.skills[skill_id]
            for tier in range(max(skill.tier, 1), 4):
                run_seed = seed + index
                index += 1
                state = _used(acquire(skill_id))
                samples.append(Sample(group, skill_id, tier, state, run_seed))
    plain = [s for s in groups.get("active_weapon", []) + groups.get("active_spell", [])]
    for template in [t.id for t in library.flash.transforms]:
        wanted = 0
        for skill_id in _pick(plain, len(plain), seed + len(template)):
            if wanted >= per_transform:
                break
            run_seed = seed + index
            after = _transformed(library, skill_id, template, 3, run_seed)
            if after is None:
                continue
            wanted += 1
            index += 1
            samples.append(Sample(f"after_{template}", skill_id, 3, after, run_seed))
    return samples


# ---------------------------------------------------------------------------
# 跑題
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Task:
    sample: Sample
    scenario: str
    category: str | None
    state: SkillFlash


def _usable_categories(
    library: ContentLibrary, sample: Sample, state: SkillFlash, *, major: bool
) -> tuple[str, ...]:
    """這一次真的有套得上變化的類別（指定類別只挑這些，不浪費題目在空類別上）。"""
    request = FlashRequest(
        library.skills[sample.skill_id], state, SkillUsage(), sample.seed, tier=sample.role_tier
    )
    catalog = build_catalog(
        library,
        request,
        skill_before(library, request),
        major=major,
        applicable=lambda v: try_variation(library, request, v) is not None,
    )
    return catalog.categories


def build_tasks(library: ContentLibrary, samples: Sequence[Sample], focused_per: int) -> list[Task]:
    tasks: list[Task] = []
    for number, sample in enumerate(samples):
        post = sample.group.startswith("after_")
        # 轉型後的技能（已有 3 筆歷程）只出第 4 次的小變化；其他先閃兩次再出第 3 次大變化
        minor = sample.state if post else _used(acquire(sample.skill_id))
        minors = _usable_categories(library, sample, minor, major=False)
        tasks.append(Task(sample, "open", None, minor))
        for step in range(min(focused_per, len(minors))):
            category = minors[(number + step) % len(minors)]
            tasks.append(Task(sample, "focused", category, minor))
        if post:
            continue
        third = _advance(library, sample.skill_id, sample.role_tier, sample.seed, 2)
        if not slot_is_major(library.flash.rules, third, next_nth(third)):
            continue  # 前兩次閃不出來（沒有合法變化），到不了第 3 次
        majors = _usable_categories(library, sample, third, major=True)
        tasks.append(Task(sample, "major", None, third))
        if majors:
            category = majors[number % len(majors)]
            tasks.append(Task(sample, "major_focused", category, third))
    return tasks


def _join(values: Iterable[str]) -> str:
    return "|".join(values)


def run_task(
    library: ContentLibrary,
    task: Task,
    make_source: Callable[[Callable[[FlashProposalRecord], None]], LlmFlashSource],
) -> dict[str, object]:
    sample = task.sample
    base = library.skills[sample.skill_id]
    request = FlashRequest(
        base, task.state, SkillUsage(), sample.seed, category=task.category, tier=sample.role_tier
    )
    row: dict[str, object] = {
        "group": sample.group,
        "skill": sample.skill_id,
        "kind": base.kind,
        "role_tier": sample.role_tier,
        "scenario": task.scenario,
        "requested_category": task.category or "",
    }
    records: list[FlashProposalRecord] = []
    source = make_source(records.append)
    before = skill_before(library, request)
    major = slot_is_major(library.flash.rules, task.state, request.nth)
    row["major"] = int(major)
    catalog = build_catalog(
        library,
        request,
        before,
        major=major,
        applicable=lambda v: try_variation(library, request, v) is not None,
    )
    row["catalog"] = _join(catalog.templates())
    row["catalog_categories"] = _join(catalog.categories)
    try:
        offer = make_offer(library, request, source)
    except ValueError as exc:
        row["error"] = str(exc)[:60]
        return row
    record = records[-1] if records else None
    accepted = record.accepted if record is not None else ()
    proposed_keys = {v.key() for v in accepted}
    origins = []
    for option in offer.options:
        variation = option.variation
        if variation.source == "transform":
            origins.append("transform")
        elif variation.key() in proposed_keys:
            origins.append("llm")
        else:
            origins.append("filler")
    row["proposed"] = _join(v.template for v in accepted)
    row["rejected"] = _join(record.rejected) if record is not None else ""
    row["source"] = record.source if record is not None else "none"
    row["attempts"] = record.attempts if record is not None else 0
    row["codes"] = _join(dict.fromkeys(c for cs in (record.codes if record else ()) for c in cs))
    row["final"] = _join(o.variation.template for o in offer.options)
    row["origins"] = _join(origins)
    row["names"] = _join(o.skill.name_zh for o in offer.options)
    row["seconds"] = f"{record.seconds:.2f}" if record is not None else "0"
    row["error"] = ""
    return row


def run_all(
    library: ContentLibrary,
    tasks: Sequence[Task],
    make_source: Callable[[Callable[[FlashProposalRecord], None]], LlmFlashSource],
    *,
    workers: int,
    csv_path: Path | None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    lock = threading.Lock()
    started = time.perf_counter()
    handle = None
    writer = None
    if csv_path is not None:
        handle = csv_path.open("w", encoding="utf-8", newline="")
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, restval="")
        writer.writeheader()

    def work(task: Task) -> None:
        row = run_task(library, task, make_source)
        with lock:
            rows.append(row)
            if writer is not None and handle is not None:
                writer.writerow(row)
                handle.flush()
            if len(rows) % 20 == 0:
                spent = time.perf_counter() - started
                print(f"  {len(rows)}/{len(tasks)}　{spent / 60:.1f} 分", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, tasks))
    if handle is not None:
        handle.close()
    return rows


# ---------------------------------------------------------------------------
# 彙整
# ---------------------------------------------------------------------------


def _split(value: object) -> list[str]:
    text = str(value or "")
    return text.split("|") if text else []


def _ok(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [r for r in rows if not r.get("error")]


def _table(head: Sequence[str], body: Iterable[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    lines += ["| " + " | ".join(str(c) for c in line) + " |" for line in body]
    return lines


def _pct(part: float, whole: float) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "-"


def _flag(ratio: float | None, avail: int, minimum: int) -> str:
    if ratio is None or avail < minimum:
        return "樣本少" if avail else "無機會"
    if ratio > PREFER_RATIO:
        return "偏好"
    if ratio < 1 / 3:
        return "冷落"
    return ""


def stats_by(
    rows: Sequence[dict[str, object]], key_of: Callable[[str], str]
) -> dict[str, dict[str, float]]:
    """依 ``key_of``（模板 → 分組鍵）累計：套得上場次、提出、退回、呈現、隨機期望。"""
    out: dict[str, Counter[str]] = {}

    def cell(key: str) -> Counter[str]:
        return out.setdefault(key, Counter())

    for row in _ok(rows):
        catalog = _split(row["catalog"])
        proposed = _split(row["proposed"])
        groups_in_catalog = {key_of(t) for t in catalog}
        for key in groups_in_catalog:
            cell(key)["avail"] += 1
        for key in {key_of(t) for t in catalog}:
            # 隨機期望：這題提出幾個，平均分給目錄內的各模板（分組時按該組模板數計）
            share = sum(1 for t in catalog if key_of(t) == key) / max(len(catalog), 1)
            cell(key)["_expected_milli"] += int(1000 * share * len(proposed))
        for template in proposed:
            cell(key_of(template))["proposed"] += 1
        for template in _split(row["rejected"]):
            cell(key_of(template))["rejected"] += 1
        for template, origin in zip(_split(row["final"]), _split(row["origins"]), strict=False):
            cell(key_of(template))["shown"] += 1
            cell(key_of(template))[f"shown_{origin}"] += 1
    return {k: {kk: float(vv) for kk, vv in v.items()} for k, v in out.items()}


def ratio_table(
    rows: Sequence[dict[str, object]],
    key_of: Callable[[str], str],
    keys: Sequence[str],
    *,
    label: Callable[[str], str] = lambda k: k,
    minimum: int = 5,
) -> tuple[list[str], list[str], list[str]]:
    """回傳（表格行, 偏好清單, 冷落清單）。"""
    stats = stats_by(rows, key_of)
    total_avail = sum(s.get("avail", 0) for s in stats.values())
    total_prop = sum(s.get("proposed", 0) for s in stats.values())
    body: list[list[object]] = []
    prefer: list[str] = []
    neglect: list[str] = []
    for key in keys:
        s = stats.get(key, {})
        avail = int(s.get("avail", 0))
        prop = int(s.get("proposed", 0))
        avail_share = avail / total_avail if total_avail else 0.0
        prop_share = prop / total_prop if total_prop else 0.0
        ratio = prop_share / avail_share if avail_share else None
        expected = s.get("_expected_milli", 0) / 1000
        flag = _flag(ratio, avail, minimum)
        if flag == "偏好":
            prefer.append(label(key))
        elif flag == "冷落":
            neglect.append(label(key))
        body.append(
            [
                label(key),
                avail,
                prop,
                _pct(avail, total_avail),
                _pct(prop, total_prop),
                "-" if ratio is None else f"{ratio:.2f}",
                f"{expected:.1f}",
                int(s.get("rejected", 0)),
                int(s.get("shown", 0)),
                flag,
            ]
        )
    head = [
        "項目",
        "套得上場次",
        "LLM 提出",
        "套得上占比",
        "提出占比",
        "提出÷套得上",
        "隨機期望",
        "被退回",
        "玩家看到",
        "標記",
    ]
    return _table(head, body), prefer, neglect


def header_section(rows: Sequence[dict[str, object]], ok: Sequence[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    lines.append(f"總題數 {len(rows)}（有結果 {len(ok)}，無法出題 {len(rows) - len(ok)}）")
    llm_rows = [r for r in ok if r["source"] != "none"]
    sources = Counter(str(r["source"]) for r in llm_rows)
    lines.append(
        "提議來源（模型湊滿／部分補位／全部退回）："
        + "、".join(f"{k} {v}（{_pct(v, len(llm_rows))}）" for k, v in sorted(sources.items()))
    )
    attempts = [int(str(r["attempts"])) for r in llm_rows]
    lines.append(f"平均嘗試次數 {sum(attempts) / max(len(attempts), 1):.2f}")
    seconds = [float(str(r["seconds"])) for r in llm_rows]
    lines.append(f"平均每題耗時 {sum(seconds) / max(len(seconds), 1):.1f} 秒")
    codes: Counter[str] = Counter()
    for r in llm_rows:
        codes.update(_split(r["codes"]))
    lines.append("錯誤代碼：" + ("、".join(f"{k} {v}" for k, v in codes.most_common()) or "（無）"))
    # 補位：最後選項裡 filler 的比例
    origins: Counter[str] = Counter()
    for r in ok:
        origins.update(_split(r["origins"]))
    total_opts = sum(origins.values())
    lines.append(
        "最後選項來源："
        + "、".join(f"{k} {v}（{_pct(v, total_opts)}）" for k, v in sorted(origins.items()))
    )
    # 重複：同一組選項裡同一個模板出現兩次以上（只差關鍵字等參數）；名稱要等命名步驟才會不同，
    # 這支腳本不跑命名，所以改用模板重複衡量
    dup_offers = 0
    distinct = 0
    for r in ok:
        templates = _split(r["final"])
        dup_offers += len(templates) != len(set(templates))
        distinct += len(set(templates))
    lines.append(
        f"一組選項內同模板重複：{dup_offers} 組（{_pct(dup_offers, len(ok))}）；"
        f"平均每組不同模板 {distinct / max(len(ok), 1):.2f} 種"
    )
    lines.append("")
    return lines


def summarize(library: ContentLibrary, rows: Sequence[dict[str, object]]) -> str:
    table = library.flash
    ok = _ok(rows)
    lines = header_section(rows, ok)
    lines += spread_section(ok)
    lines.append("")

    kinds = {t.id: ("minor", t.category) for t in table.minor}
    kinds |= {t.id: ("major", t.category) for t in table.major}
    kinds |= {t.id: ("major", t.category) for t in table.extra_major}
    templates = [t for t in kinds]
    cats = [c.id for c in table.categories]
    cat_of = {t: kinds[t][1] for t in kinds}
    lines.append("## 各類別")
    cat_lines, cat_pref, cat_neglect = ratio_table(ok, lambda t: cat_of.get(t, "transform"), cats)
    lines += cat_lines
    lines.append("")
    lines.append(
        f"偏好類別：{'、'.join(cat_pref) or '（無）'}；"
        f"冷落類別：{'、'.join(cat_neglect) or '（無）'}"
    )
    lines.append("")
    lines.append("## 各模板")
    tpl_lines, tpl_pref, tpl_neglect = ratio_table(
        ok, lambda t: t, templates, label=lambda t: f"{t}（{cat_of[t]}）"
    )
    lines += tpl_lines
    lines.append("")
    lines.append(f"偏好模板：{'、'.join(tpl_pref) or '（無）'}")
    lines.append(f"冷落模板：{'、'.join(tpl_neglect) or '（無）'}")
    lines.append("")
    lines += transform_section(library, ok)
    lines.append("")
    lines += group_section(ok)
    return "\n".join(lines)


def transform_section(library: ContentLibrary, ok: Sequence[dict[str, object]]) -> list[str]:
    ids = [t.id for t in library.flash.transforms]
    majors = [r for r in ok if r["major"] == 1 or str(r["major"]) == "1"]
    in_catalog = sum(1 for r in majors for t in _split(r["catalog"]) if t in ids)
    proposed = sum(1 for r in majors for t in _split(r["proposed"]) if t in ids)
    tried = sum(1 for r in ok for t in _split(r["rejected"]) if t in ids)
    with_transform = [r for r in majors if "transform" in _split(r["origins"])]
    options = sum(len(_split(r["final"])) for r in majors)
    transform_opts = sum(_split(r["origins"]).count("transform") for r in majors)
    llm_transform = sum(
        1
        for r in majors
        for t, o in zip(_split(r["final"]), _split(r["origins"]), strict=False)
        if t in ids and o == "llm"
    )
    shown = Counter(t for r in majors for t in _split(r["final"]) if t in ids)
    lines = ["## 轉型"]
    lines.append(f"大變化題數 {len(majors)}；目錄內的轉型條目 {in_catalog}")
    lines.append(f"LLM 提出轉型（通過）{proposed}；LLM 嘗試提轉型被退回 {tried}")
    lines.append(
        f"玩家看到的大變化選項共 {options} 個，其中轉型 {transform_opts} 個"
        f"（{_pct(transform_opts, options)}）：LLM 提的 {llm_transform}、"
        f"引擎補的 {transform_opts - llm_transform}"
    )
    share = _pct(len(with_transform), len(majors))
    lines.append(f"含轉型選項的大變化題 {len(with_transform)}／{len(majors)}（{share}）")
    lines.append("")
    by_kind: Counter[str] = Counter()
    for r in majors:
        by_kind[str(r["kind"]) + "|" + ("有轉型" if r in with_transform else "無轉型")] += 1
    lines += _table(["技能種類|轉型", "題數"], [[k, v] for k, v in sorted(by_kind.items())])
    lines.append("")
    lines += tier_transform_table(majors, ids)
    lines.append("")
    lines += _table(
        ["轉型模板", "玩家看到次數", "占轉型選項"],
        [[t, shown[t], _pct(shown[t], transform_opts)] for t in ids],
    )
    return lines


def tier_transform_table(majors: Sequence[dict[str, object]], ids: Sequence[str]) -> list[str]:
    """主動技的大變化題，依角色階級看轉型保底補上的轉型種類（沒有的列「無」）。"""
    body: list[list[object]] = []
    for tier in ("1", "2", "3"):
        rows = [r for r in majors if r["kind"] == "active" and str(r["role_tier"]) == tier]
        shown = Counter(t for r in rows for t in _split(r["final"]) if t in ids)
        none = sum(1 for r in rows if not any(t in ids for t in _split(r["final"])))
        body.append([tier, len(rows), none, *(shown[t] for t in ids)])
    return _table(["角色階級", "主動技大變化題", "無轉型", *ids], body)


def _entropy(counts: Iterable[float]) -> float:
    values = [c for c in counts if c > 0]
    total = sum(values)
    return -sum(c / total * math.log2(c / total) for c in values) if total else 0.0


def spread_section(ok: Sequence[dict[str, object]]) -> list[str]:
    """整體分散度與位置偏好：提出的模板有多分散、是不是偏愛目錄前面（或後面）的條目。"""
    proposed: Counter[str] = Counter()
    available: Counter[str] = Counter()
    for r in ok:
        proposed.update(_split(r["proposed"]))
        available.update(set(_split(r["catalog"])))
    total = sum(proposed.values())
    top = proposed.most_common(5)
    lines = ["## 整體分散度"]
    lines.append(
        f"目錄裡出現過的模板 {len(available)} 種；LLM 至少提出一次的 {len(proposed)} 種；"
        f"共提出 {total} 次"
    )
    lines.append(
        "最常提出的前五名："
        + "、".join(f"{t} {n}（{_pct(n, total)}）" for t, n in top)
        + f"；第一名占 {_pct(top[0][1], total) if top else '-'}"
    )
    # 熵：提出 vs 「套得上」的熵（越接近代表越照目錄的分布）
    lines.append(
        f"提出分布的熵 {_entropy(proposed.values()):.2f} bit，"
        f"套得上分布的熵 {_entropy(available.values()):.2f} bit"
    )
    thirds = Counter[str]()
    first_pick = Counter[str]()
    for r in ok:
        catalog = _split(r["catalog"])
        if len(catalog) < POSITION_MIN_CATALOG:
            continue
        for template in _split(r["proposed"]):
            if template in catalog:
                part = catalog.index(template) * 3 // len(catalog)
                thirds[("前段", "中段", "後段")[part]] += 1
        picks = _split(r["proposed"])
        if picks and picks[0] in catalog:
            first_pick[("前段", "中段", "後段")[catalog.index(picks[0]) * 3 // len(catalog)]] += 1
    n = sum(thirds.values())
    lines.append(
        f"位置偏好（目錄 ≥ {POSITION_MIN_CATALOG} 條時，提出的模板落在目錄的前／中／後三段；"
        "各 33.3% ＝ 無偏好）："
        + "、".join(f"{k} {_pct(thirds[k], n)}" for k in ("前段", "中段", "後段"))
        + f"；回應中第一個提出的：{_pct(first_pick['前段'], sum(first_pick.values()))}"
        f"／{_pct(first_pick['中段'], sum(first_pick.values()))}"
        f"／{_pct(first_pick['後段'], sum(first_pick.values()))}"
    )
    return lines


def group_section(ok: Sequence[dict[str, object]]) -> list[str]:
    stats: dict[str, Counter[str]] = {}
    for r in ok:
        cell = stats.setdefault(str(r["group"]), Counter())
        cell["tasks"] += 1
        cell["skills"] += 0
        proposed = _split(r["proposed"])
        cell["proposed"] += len(proposed)
        cell["distinct"] += 0
        origins = _split(r["origins"])
        cell["llm"] += origins.count("llm")
        cell["filler"] += origins.count("filler")
        cell["transform"] += origins.count("transform")
        if r["source"] == "template":
            cell["fallback"] += 1
        elif r["source"] == "partial":
            cell["partial"] += 1
    body = [
        [
            g,
            c["tasks"],
            c["proposed"],
            _pct(c["fallback"], c["tasks"]),
            _pct(c["partial"], c["tasks"]),
            _pct(c["filler"], c["llm"] + c["filler"]),
        ]
        for g, c in sorted(stats.items())
    ]
    distinct: dict[str, set[str]] = {}
    for r in ok:
        distinct.setdefault(str(r["group"]), set()).update(_split(r["proposed"]))
    for line in body:
        line.insert(3, len(distinct.get(str(line[0]), set())))
    return [
        "## 各技能類型",
        *_table(
            [
                "技能類型",
                "題數",
                "LLM 提出",
                "用到的模板種類",
                "退回率",
                "補位率(題)",
                "補位占選項",
            ],
            body,
        ),
    ]


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(r) for r in csv.DictReader(handle)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--per-group", type=int, default=3, help="每個技能類型取幾招（預設 3）")
    parser.add_argument("--per-transform", type=int, default=3, help="每個轉型模板取幾招（預設 3）")
    parser.add_argument("--focused-per", type=int, default=2, help="每個樣本指定類別幾題（預設 2）")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8, help="平行請求數（最多 8）")
    parser.add_argument("--max-tasks", type=int, default=0, help="只跑前 N 題（0 ＝ 全部）")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--real", action="store_true", help="用 config/llm.toml 的本機模型")
    mode.add_argument("--mock", action="store_true", help="Mock（預設）")
    parser.add_argument("--csv", type=Path, default=None, help="每題明細（邊跑邊寫）")
    parser.add_argument("--from-csv", type=Path, nargs="+", default=None, help="不跑題，只彙整 CSV")
    parser.add_argument("--report", type=Path, default=None, help="彙整表另存")
    args = parser.parse_args(argv)
    library = load_library()
    if args.from_csv is not None:
        rows = [r for path in args.from_csv for r in read_csv(path)]
    else:
        config = load_llm_config()
        if args.real:
            client = OpenAICompatClient(config)

            def make_source(sink):  # type: ignore[no-untyped-def]
                return LlmFlashSource(client, max_attempts=config.max_retries, sink=sink)

        else:

            def make_source(sink):  # type: ignore[no-untyped-def]
                return mock_flash_source(library, max_attempts=config.max_retries, sink=sink)

        samples = build_samples(library, args.per_group, args.seed, args.per_transform)
        tasks = build_tasks(library, samples, args.focused_per)
        if args.max_tasks:
            tasks = tasks[: args.max_tasks]
        print(f"樣本 {len(samples)}，題目 {len(tasks)}", file=sys.stderr)
        rows = run_all(library, tasks, make_source, workers=min(args.workers, 8), csv_path=args.csv)
    text = summarize(library, rows)
    print(text)
    if args.report is not None:
        args.report.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
