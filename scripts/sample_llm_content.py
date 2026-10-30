"""AI 生成內容樣本（4-L9 後續）：用真模型產生一小批升級技能與閃現大變化，附白話效果與名稱統計。

用法::

    uv run python scripts/sample_llm_content.py --mock                         # Mock（不需網路）
    uv run python scripts/sample_llm_content.py --out docs/phases/4-L9/AI生成樣本.md   # 真模型

只讀評估工具的出題方式，不改任何遊戲程式。真模型需先由使用者啟動本機模型（``config/llm.toml``）。
Markdown 的「品質觀察」段落由人手寫，腳本以占位文字標示。
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.llm import OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import mock_client_for, mock_naming_client
from trpg.llm.client import LLMClient
from trpg.llm.flash_eval import _third, pick_skills
from trpg.llm.flash_propose import LlmFlashSource, mock_flash_source, name_offer
from trpg.llm.naming import apply_naming, name_skill
from trpg.llm.propose import propose_skill
from trpg.llm.skill_eval import EvalItem, upgrade_items
from trpg.narrative.skills import skill_card
from trpg.skillgen.flash_offer import FlashRequest, make_offer, skill_before
from trpg.skillgen.usage import SkillUsage

WORLD_TERMS = ("源晶", "晶", "頻", "頻率", "晶頻")
"""世界觀詞（名稱裡含這些字串算重複用詞；「源晶」「頻率」「晶頻」都含「晶」或「頻」）。"""
WEAPON_EXAMPLES = "武器屬性看手上的武器："
"""卡片沒有持有者時另列的武器屬性例子（3-55）；樣本裡另起一行，不接在算法後面。"""
CSV_DIR = Path(__file__).resolve().parents[1] / "docs" / "phases" / "4-L9"
NATURE_BASE = 1000

type NamingFor = Callable[[SkillDef, int], LLMClient]


@dataclass(slots=True)
class Sample:
    """一個通過的升級技能樣本。"""

    item: EvalItem
    skill: SkillDef
    name_source: str
    retries: int = 0
    """命名時因一致性或世界觀詞檢查（4-L11）不過而重試的次數。"""


@dataclass(slots=True)
class FlashSample:
    """一個閃現大變化樣本。"""

    base_name: str
    skill: SkillDef
    template: str
    source: str
    summary: str
    retries: int = 0


@dataclass(slots=True)
class Gathered:
    upgrades: list[Sample] = field(default_factory=list)
    flashes: list[FlashSample] = field(default_factory=list)
    pool_names: list[str] = field(default_factory=list)
    """所有通過的升級技能名稱（含沒被選進清單的）。"""
    tried: int = 0
    nature_tried: int = 0
    nature_passed: int = 0


def card_lines(library: ContentLibrary, skill: SkillDef) -> dict[str, str]:
    """技能卡片的白話內容（不含原語代碼）。"""
    card = skill_card(library, skill)
    parts = [f"代價：{'、'.join(card.cost) or '無'}", f"範圍：{card.shape}"]
    if card.condition:
        parts.append(f"條件：{card.condition}")
    if card.timing:
        parts.append(f"時機：{card.timing}")
    effects = [*card.effects, *card.modifiers]
    formula = [f for f in card.formula_lines if not f.startswith(WEAPON_EXAMPLES)]
    examples = [f for f in card.formula_lines if f.startswith(WEAPON_EXAMPLES)]
    if card.followup:
        effects.append(f"接續：{card.followup}")
    if card.activation:
        effects.append(card.activation)
    return {
        "meta": f"{card.rarity}／{card.kind}／{card.category}／{card.element or '無元素'}",
        "cost": "；".join(parts),
        "effects": "；".join(effects),
        "formula": "；".join(formula),
        "weapon": "；".join(e.removeprefix(WEAPON_EXAMPLES) for e in examples),
        "keywords": "、".join(k.name_zh for k in (*card.keywords.makes, *card.keywords.uses)),
    }


def _run_upgrade(
    library: ContentLibrary,
    item: EvalItem,
    client: LLMClient,
    naming_for: NamingFor,
    attempts: int,
) -> Sample | None:
    outcome = propose_skill(
        client, library, item.request, item.ctx, seed=item.seed, max_attempts=attempts
    )
    if outcome.source != "llm":
        return None
    named = name_skill(
        naming_for(outcome.skill, item.seed),
        library,
        outcome.skill,
        theme=item.request.theme,
        max_attempts=attempts,
    )
    skill = apply_naming(outcome.skill, named.text) if named.source == "llm" else outcome.skill
    return Sample(item, skill, named.source, named.consistency_retries)


def select_diverse(samples: Sequence[Sample], want: int) -> list[Sample]:
    """先放自然主題（至多 4 招），再讓每個（階級, 骨架）組合各出現一次，最後依序補滿。"""
    chosen: list[Sample] = []
    seen: set[tuple[int, str]] = set()

    def take(sample: Sample) -> None:
        if sample not in chosen and len(chosen) < want:
            chosen.append(sample)
            seen.add((sample.skill.tier, sample.skill.skeleton))

    nature = [s for s in samples if s.item.request.theme == "nature"]
    for sample in nature[:4]:
        take(sample)
    for sample in samples:
        if (sample.skill.tier, sample.skill.skeleton) not in seen:
            take(sample)
    for sample in samples:
        take(sample)
    return sorted(chosen, key=lambda s: (s.skill.tier, s.skill.skeleton))


def _nature_items(library: ContentLibrary, count: int, seed: int) -> list[EvalItem]:
    return [
        EvalItem(
            i.suite, NATURE_BASE + n, replace(i.request, theme="nature", keywords=()), i.ctx, i.seed
        )
        for n, i in enumerate(upgrade_items(library, count, seed=seed + 7))
    ]


def gather(
    library: ContentLibrary,
    *,
    mock: bool,
    seed: int,
    pool: int,
    nature: int,
    flashes: int,
    workers: int,
    want: int,
) -> Gathered:
    config = load_llm_config()
    attempts = config.max_retries
    items = [*upgrade_items(library, pool, seed=seed), *_nature_items(library, nature, seed)]
    shared = None if mock else OpenAICompatClient(config)

    def upgrade(item: EvalItem) -> Sample | None:
        if shared is None:
            return _run_upgrade(
                library,
                item,
                mock_client_for(library, item.request, item.seed, attempts),
                lambda skill, s: mock_naming_client(library, skill, s),
                attempts,
            )
        return _run_upgrade(library, item, shared, lambda _skill, _s: shared, attempts)

    out = Gathered(tried=len(items), nature_tried=nature)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        results = list(ex.map(upgrade, items))
    print(f"升級 {len(items)} 題 {time.perf_counter() - started:.0f} 秒", file=sys.stderr)
    passed = [r for r in results if r is not None]
    out.nature_passed = sum(r.item.request.theme == "nature" for r in passed)
    out.pool_names = [r.skill.name_zh for r in passed if r.name_source == "llm"]
    out.upgrades = select_diverse([r for r in passed if r.name_source == "llm"], want)

    def flash(index_skill: tuple[int, str]) -> FlashSample | None:
        index, skill_id = index_skill
        return _flash_one(library, skill_id, seed + index, shared, attempts)

    skills = pick_skills(library, flashes)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        out.flashes = [r for r in ex.map(flash, enumerate(skills)) if r is not None]
    return out


def _flash_one(
    library: ContentLibrary,
    skill_id: str,
    seed: int,
    shared: OpenAICompatClient | None,
    attempts: int,
) -> FlashSample | None:
    base = library.skills[skill_id]
    request = FlashRequest(base, _third(library, skill_id, seed), SkillUsage(), seed)
    source = (
        mock_flash_source(library, max_attempts=attempts)
        if shared is None
        else LlmFlashSource(shared, max_attempts=attempts)
    )
    try:
        offer = make_offer(library, request, source)
    except ValueError:
        return None
    if not offer.major:
        return None
    naming = shared or mock_naming_client(library, base, seed)
    taken = {s.name_zh for s in library.skills.values()}
    named, records = name_offer(
        offer, naming, library, seed=seed, taken=taken, before=skill_before(library, request)
    )
    majors = [o for o in named.options if o.variation.source != "minor"]
    if not majors:
        return None
    option = majors[0]
    return FlashSample(
        base.name_zh,
        option.skill,
        option.variation.template,
        option.variation.source,
        option.summary_zh,
        records[0].consistency_retries if records else 0,
    )


# ---------------------------------------------------------------------------
# 名稱統計
# ---------------------------------------------------------------------------


def csv_names(path: Path) -> list[str]:
    """既有 CSV 裡由 LLM 命名的升級技能名稱（``name_source`` 為 ``llm``）。"""
    with path.open(encoding="utf-8", newline="") as f:
        return [r["skill_name"] for r in csv.DictReader(f) if r["name_source"] == "llm"]


def name_stats(names: Sequence[str]) -> dict[str, int]:
    stats = {"總數": len(names)}
    for term in WORLD_TERMS:
        stats[term] = sum(term in n for n in names)
    stats["含晶或頻"] = sum(("晶" in n or "頻" in n) for n in names)
    return stats


def _pct(part: int, total: int) -> str:
    return f"{part}（{part * 100 / total:.0f}%）" if total else "—"


def stats_table(groups: Mapping[str, Sequence[str]]) -> list[str]:
    rows = {label: name_stats(names) for label, names in groups.items()}
    lines = ["| 詞 | " + " | ".join(groups) + " |", "|---|" + "---:|" * len(groups)]
    for key in ["總數", *WORLD_TERMS, "含晶或頻"]:
        cells = [str(r[key]) if key == "總數" else _pct(r[key], r["總數"]) for r in rows.values()]
        lines.append(f"| {key} | " + " | ".join(cells) + " |")
    return lines


def head_lines(groups: Mapping[str, Sequence[str]], top: int = 5) -> list[str]:
    lines = []
    for label, names in groups.items():
        heads = Counter(n[:2] for n in names)
        text = "、".join(f"{h}×{c}" for h, c in heads.most_common(top))
        lines.append(f"- {label}：{text or '（無）'}")
    return lines


# ---------------------------------------------------------------------------
# 報表
# ---------------------------------------------------------------------------


def _entry(library: ContentLibrary, skill: SkillDef, retries: int) -> list[str]:
    info = card_lines(library, skill)
    return [
        f"- 概念：{skill.narrative.concept}",
        f"- 施放敘事：{skill.narrative.cast_flavor}",
        f"- 效果：{info['effects']}",
        f"- 數值：{info['cost']}" + (f"；{info['formula']}" if info["formula"] else ""),
        *([f"- 武器屬性（看手上的武器）：{info['weapon']}"] if info["weapon"] else []),
        *([f"- 協同關鍵字：{info['keywords']}"] if info["keywords"] else []),
        f"- 一致性檢查重試次數：{retries}",
        "",
    ]


def render(library: ContentLibrary, data: Gathered, *, model: str, mock: bool, seed: int) -> str:
    lines = [
        "# AI 生成樣本",
        "",
        f"- 模型：{model}；日期：{date.today().isoformat()}；種子 {seed}。"
        + ("（Mock：非真模型內容）" if mock else ""),
        f"- 產生方式：`uv run python scripts/sample_llm_content.py`，用 4-L9 評估工具的出題方式"
        f"（升級候選 {data.tried} 題，其中 {data.nature_tried} 題另加自然主題），"
        "提議與命名各重試到設定次數。",
        "- 只放通過驗證、且名稱由 LLM 取的升級技能（退回保底的不放）；"
        "效果文字取自技能卡片，不含原語代碼。",
        "- 閃現大變化：第 3 次閃現，取選單裡第一個大變化選項。",
        "- 一致性檢查重試次數：命名時因敘事與效果不一致、或世界觀詞超過上限（4-L11）而重試的次數。",
        "",
        f"## 升級技能（{len(data.upgrades)} 招）",
        "",
    ]
    for n, s in enumerate(data.upgrades, start=1):
        info = card_lines(library, s.skill)
        theme = s.item.request.theme or "—"
        kws = "、".join(s.item.request.keywords) or "—"
        lines += [
            f"### {n}. {s.skill.name_zh}",
            "",
            f"- 階級 {s.skill.tier}／{info['meta']}／題目主題 {theme}／題目關鍵字 {kws}",
            *_entry(library, s.skill, s.retries),
        ]
    chosen_nature = sum(s.item.request.theme == "nature" for s in data.upgrades)
    lines += [
        f"自然主題：{data.nature_tried} 題自然主題題目中通過 {data.nature_passed} 題，"
        f"本清單選入 {chosen_nature} 招"
        + ("。" if data.nature_passed else "（沒有通過的自然主題技能）。"),
        "",
        f"## 閃現大變化（{len(data.flashes)} 個）",
        "",
    ]
    for n, f in enumerate(data.flashes, start=1):
        lines += [
            f"### {n}. {f.base_name} → {f.skill.name_zh}",
            "",
            f"- 變化來源：{f.source}／模板 {f.template}；{f.summary}",
            *_entry(library, f.skill, f.retries),
        ]
    mine = [s.skill.name_zh for s in data.upgrades]
    groups = {
        "4-L9（修正前）": csv_names(CSV_DIR / "skills.csv"),
        "4-L10 重跑": csv_names(CSV_DIR / "skills_rerun_4L10.csv"),
        f"本次樣本（{len(mine)} 招）": mine,
        "本次全部通過": data.pool_names,
        f"本次閃現（{len(data.flashes)}）": [f.skill.name_zh for f in data.flashes],
    }
    lines += ["## 名稱重複統計", "", "名稱含該字串的比例（只算 LLM 取的名稱）。", ""]
    lines += [*stats_table(groups), "", "### 最常見的 5 個詞頭（名稱前 2 字）", ""]
    lines += [*head_lines(groups), "", "## 品質觀察", "", "（待人工填寫）", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--mock", action="store_true", help="用 Mock（不需網路）")
    parser.add_argument("--pool", type=int, default=45, help="一般升級題數")
    parser.add_argument("--nature", type=int, default=12, help="另加的自然主題題數")
    parser.add_argument("--want", type=int, default=20, help="放進清單的升級技能數")
    parser.add_argument("--flashes", type=int, default=20)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    library = load_library()
    config = load_llm_config()
    data = gather(
        library,
        mock=args.mock,
        seed=args.seed,
        pool=args.pool,
        nature=args.nature,
        flashes=args.flashes,
        workers=min(args.workers, 8),
        want=args.want,
    )
    model = "Mock" if args.mock else f"{config.model}（{config.base_url}）"
    text = render(library, data, model=model, mock=args.mock, seed=args.seed)
    if args.out is None:
        print(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"已寫入 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
