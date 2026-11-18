"""許願池：現行（自由設計）vs 願望驅動（PK-4）的紙面比較，與閃現借別類候選（PK-4 B）的前後對照。

同一個角色、同一組願望（元素、控制、位移、召喚、高處、護盾、反應、被動、地形、做不到的願望…），
同一個模型各跑一次：

- (a) **現行**：``skill_pick.yaml`` 的 ``wish_enabled`` 關掉——對 1～2 個關鍵字（``wish-match/1``）＋
  把願望放進 ``<player_input>`` 的完整技能自由設計（每份最多 ``llm_cards`` 張）。
- (b) **願望驅動**：開關打開——翻需求標籤（``wish-tags/1``）＋照標籤做候選、挑 3 張並回應願望
  （``wish-pick/1``）。

兩邊都經 API 層的生成函式（``trpg.api.world_pregen.wish_generator``）；拿不到 LLM 版時照世界引擎的
退路算（現行：照關鍵字用組合器；願望驅動：照標籤排序取前 3 名），所以表上的 3 張就是玩家會看到的。

``flash``：PK-3 比較的 10 個閃現情境，每格候選數與借來的別類候選（不呼叫 LLM）。

用法::

    uv run python scripts/wish_compare.py run            # 真模型（先照上手筆記檢查 LM Studio）
    uv run python scripts/wish_compare.py run --mock     # Mock 冒煙（Mock 對字、Mock 命名）
    uv run python scripts/wish_compare.py flash
    uv run python scripts/wish_compare.py report         # 寫 docs/phases/PhasePK-4比較.md 的資料段

量測前查 ``/api/v0/models``（只能載入設定的模型，否則結束碼 3）與生成速度（低於 60 t/s 結束碼 2）；
一次只送一個請求。
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import os
import statistics
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trpg.api.llm_source import LocalLlmProvider, MockLlmProvider
from trpg.api.world_pregen import wish_generator
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef, skill_elements
from trpg.llm import load_llm_config
from trpg.narrative.skills import skill_card
from trpg.roguelite.offers import make_offer
from trpg.roguelite.state import SkillOffer
from trpg.roguelite.wish_offer import make_wish_offer
from trpg.skillgen.flash_offer import flash_slots
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.wish_pick import tag_hits, tag_labels
from trpg.world.generated import WishGen
from trpg.world.growth import world_library
from trpg.world.state import CharacterState, WorldState
from trpg.world.step import new_character
from trpg.world.wish import _wish_run, wish_request

sys.path.insert(0, str(Path(__file__).resolve().parent))
_PC: Any = importlib.import_module("pick_compare")  # LM Studio 檢查（只載入設定的模型、速度門檻）
_FC: Any = importlib.import_module("flash_pick_compare")  # PK-3 的閃現情境

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "phases" / "PK-4資料"
FORMAT = "wish-compare/1"
WISHES: tuple[tuple[str, str, str], ...] = (
    ("W1", "元素組合", "想把敵人凍在火裡"),
    ("W2", "控制＋撞擊", "想把敵人凍住，再一錘敲碎"),
    ("W3", "元素＋範圍", "讓一整片敵人都燒起來的火焰"),
    ("W4", "位移", "能一下子閃到敵人背後的招式"),
    ("W5", "推擊＋高處", "把敵人從高台上推下去"),
    ("W6", "召喚", "召喚一隻狼替我擋刀"),
    ("W7", "高處", "從高處跳下來重重砸在地上"),
    ("W8", "護盾", "幫隊友擋下傷害的護盾"),
    ("W9", "反應", "被打的時候自動反擊回去"),
    ("W10", "被動", "一直帶在身上、讓我越打越強的被動"),
    ("W11", "地形＋毒", "讓毒霧籠罩整個戰場"),
    ("W12", "做不到", "我想要一條會飛的龍載我去月亮"),
)


def _char(library: ContentLibrary) -> CharacterState:
    """比較用的角色：主城、輔助英雄（同 ``tests/world`` 的 ``hero``）、任務幣夠。"""
    build = next(b.hero for b in library.builds.builds if b.id == "build_support")
    made = new_character(library, "pk4", build, region="cloud_ridge")
    return made.model_copy(update={"region": "capital", "location": "capital", "quest_coins": 20})


def _skill_row(library: ContentLibrary, skill: SkillDef) -> dict[str, Any]:
    card = skill_card(library, skill)
    found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    return {
        "id": skill.id,
        "name_zh": skill.name_zh,
        "description_zh": skill.description_zh,
        "kind": card.kind,
        "shape": card.shape,
        "effects": list(card.effects),
        "keywords": [plain_name(k, library) for k in found],
        "elements": sorted(e.display_name for e in skill_elements(skill)) or ["物理"],
    }


def _offer_rows(library: ContentLibrary, offer: SkillOffer) -> list[dict[str, Any]]:
    out = []
    for skill, tag in zip(offer.candidates, offer.tags, strict=True):
        row = _skill_row(library, skill)
        row["source"] = tag.source
        row["pick"] = tag.pick
        row["reply_zh"] = tag.wish_reply_zh
        row["miss_zh"] = tag.wish_miss_zh
        row["llm_codes"] = list(tag.llm.codes) if tag.llm is not None else []
        out.append(row)
    return out


def _old(library: ContentLibrary, provider: Any, char: CharacterState, text: str) -> dict[str, Any]:
    off = dataclasses.replace(
        library, skill_pick=library.skill_pick.model_copy(update={"wish_enabled": False})
    )
    view = world_library(off)
    request = wish_request(off, _world(), char, text)
    start = time.perf_counter()
    gen = wish_generator(provider, view, request)
    seconds = round(time.perf_counter() - start, 2)
    row: dict[str, Any] = {
        "source": gen.source,
        "keywords": [plain_name(k, view) for k in gen.keywords],
        "attempts": gen.attempts,
        "codes": list(gen.codes),
        "seconds": seconds,
    }
    if gen.source == "none":
        row["refused"] = True
        return row
    offer = gen.offer
    if offer is None:  # 引擎的退路：照關鍵字用組合器（同 trpg.world.wish 舊流程）
        offer = make_offer(
            view,
            _wish_run(_world(), char),
            "complete",
            region_keywords=gen.keywords,
            pinned_keyword=gen.keywords[0],
            region=None,
        )
    row["cards"] = _offer_rows(view, offer)
    return row


def _new(library: ContentLibrary, provider: Any, char: CharacterState, text: str) -> dict[str, Any]:
    view = world_library(library)
    request = wish_request(library, _world(), char, text)
    start = time.perf_counter()
    gen: WishGen = wish_generator(provider, view, request)
    seconds = round(time.perf_counter() - start, 2)
    row: dict[str, Any] = {
        "source": gen.source,
        "tags": [] if gen.tags is None else list(tag_labels(view, gen.tags)),
        "attempts": gen.attempts,
        "codes": list(gen.codes),
        "seconds": seconds,
    }
    if gen.source == "none" or gen.tags is None:
        row["refused"] = True
        return row
    offer = gen.offer if gen.source == "llm" else None
    if offer is None:  # 引擎的退路：照標籤排序取前 3 名
        offer = make_wish_offer(view, _wish_run(_world(), char), gen.tags)
    row["cards"] = _offer_rows(view, offer)
    row["hits"] = [len(tag_hits(view, s, gen.tags)[0]) for s in offer.candidates]
    row["tag_count"] = len(tag_labels(view, gen.tags))
    return row


def _world() -> WorldState:
    """比較用的世界（同 ``tests/world/helpers.make_world`` 的種子與開季時刻）。"""
    return WorldState.model_validate(
        {"season_id": "s1", "season_seed": 20261102, "season_start": 1_793_592_000}
    )


def run(args: argparse.Namespace) -> int:
    os.environ["TRPG_LLM_REASONING_EFFORT"] = "none"
    config = load_llm_config()
    meta: dict[str, Any] = {
        "format": FORMAT,
        "mock": args.mock,
        "model": config.model,
        "temperature": config.temperature,
        "max_retries": config.max_retries,
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if not args.mock:
        code = int(_PC._preflight(config))
        if code:
            return code
        meta["speed"] = _PC._LMC.measure_speed(config)
    provider: Any = MockLlmProvider() if args.mock else LocalLlmProvider()
    library = load_library()
    char = _char(library)
    rows = []
    started = time.perf_counter()
    for label, kind, text in WISHES[: args.limit or None]:
        print(f"{label} {text}", flush=True)
        old = _old(library, provider, char, text)
        new = _new(library, provider, char, text)
        rows.append({"label": label, "kind": kind, "wish": text, "old": old, "new": new})
        if time.perf_counter() - started > args.max_minutes * 60:
            print("超過時間上限，停止", flush=True)
            meta["stopped"] = "time"
            break
    meta["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    out = DATA / ("wish_compare_mock.json" if args.mock else "wish_compare.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    text_out = json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=2) + "\n"
    out.write_text(text_out, encoding="utf-8", newline="\n")
    print(f"→ {out}", flush=True)
    return 0


def flash(_args: argparse.Namespace) -> int:
    """PK-4 B：每格候選數（同類／借來的）——PK-3 只有同類那幾個，PK-4 多了借來的。"""
    library = load_library()
    rows = []
    for scenario in _FC.SCENARIOS:
        request = _FC.request_of(library, scenario)
        slots = flash_slots(library, request)
        cells = []
        for slot in slots:
            own = sum(1 for c in slot.candidates if c.variation.category == slot.category)
            cells.append(
                {
                    "category": slot.category,
                    "fixed": slot.fixed,
                    "own": own,
                    "borrowed": len(slot.candidates) - own,
                    "borrowed_categories": sorted(
                        {
                            c.variation.category
                            for c in slot.candidates
                            if c.variation.category != slot.category
                        }
                    ),
                }
            )
        rows.append(
            {
                "label": scenario.label,
                "skill": scenario.skill,
                "flashes": scenario.flashes,
                "category": scenario.category,
                "slot": scenario.slot,
                "cells": cells,
            }
        )
    out = DATA / "flash_borrow.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"format": FORMAT, "rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"→ {out}", flush=True)
    return 0


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def _cards_md(cards: Sequence[dict[str, Any]], *, wish: bool) -> list[str]:
    out = []
    for i, c in enumerate(cards, 1):
        kw = "、".join(c["keywords"]) or "—"
        eff = "；".join(c["effects"])
        made = (
            "LLM 挑選命名"
            if c.get("pick") == "llm"
            else ("LLM 提議" if c["source"] == "llm" else "程式")
        )
        what = f"{c['kind']}／{c['shape']}／{'、'.join(c['elements'])}"
        head = f"  {i}. **{c['name_zh']}**（{what}；關鍵字 {kw}；{made}）"
        out.append(head)
        out.append(f"     - 效果：{eff}")
        if c.get("description_zh"):
            out.append(f"     - 描述：{c['description_zh']}")
        if wish:
            out.append(f"     - 回應願望：{c.get('reply_zh') or '（沒有）'}")
            if c.get("miss_zh"):
                out.append(f"     - 卡上照實寫：{c['miss_zh']}")
    return out


def _side_md(part: dict[str, Any], *, wish: bool) -> list[str]:
    if wish:
        head = f"標籤：{'、'.join(part.get('tags', [])) or '（一個都沒有）'}"
    else:
        head = f"關鍵字：{'、'.join(part.get('keywords', [])) or '—'}"
    head += f"；來源 {part['source']}；{part['seconds']} 秒；對字／標籤 {part['attempts']} 次"
    if part.get("codes"):
        head += f"（{'、'.join(part['codes'])}）"
    lines = [head]
    if part.get("refused"):
        lines.append("  - **被退回**：池子沒聽懂（不扣任務幣）")
        return lines
    return lines + _cards_md(part["cards"], wish=wish)


def _summary(rows: Sequence[dict[str, Any]]) -> list[str]:
    def stat(side: str) -> dict[str, Any]:
        parts = [r[side] for r in rows]
        seconds = [p["seconds"] for p in parts]
        cards = [c for p in parts for c in p.get("cards", [])]
        return {
            "refused": sum(1 for p in parts if p.get("refused")),
            "llm": sum(1 for p in parts if p["source"] == "llm"),
            "partial": sum(1 for p in parts if p["source"] == "partial"),
            "median": round(statistics.median(seconds), 2) if seconds else None,
            "max": max(seconds) if seconds else None,
            "llm_cards": sum(1 for c in cards if c.get("pick") == "llm" or c["source"] == "llm"),
            "cards": len(cards),
            "replies": sum(1 for c in cards if c.get("reply_zh")),
            "miss": sum(1 for c in cards if c.get("miss_zh")),
        }

    old, new = stat("old"), stat("new")
    return [
        "| | 現行（自由設計） | 願望驅動 |",
        "|---|---|---|",
        f"| 願望數 | {len(rows)} | {len(rows)} |",
        f"| 被退回（沒聽懂，不扣錢） | {old['refused']} | {new['refused']} |",
        "| LLM 版（llm）／只有關鍵字或標籤（partial） | "
        f"{old['llm']}／{old['partial']} | {new['llm']}／{new['partial']} |",
        "| LLM 做的卡（提議或挑選命名）／全部卡 | "
        f"{old['llm_cards']}／{old['cards']} | {new['llm_cards']}／{new['cards']} |",
        f"| 卡上有回應願望的一句 | — | {new['replies']}／{new['cards']} |",
        f"| 卡上照實寫「做不到」 | — | {new['miss']}／{new['cards']} |",
        f"| 秒數（中位／最多） | {old['median']}／{old['max']} | {new['median']}／{new['max']} |",
    ]


def _flash_md(data: dict[str, Any]) -> list[str]:
    lines = [
        "| 情境 | 技能 | 已閃 | 指定類別 | 每格候選數（PK-3 同類 → PK-4 全部） | 借來的類別 |",
        "|---|---|---|---|---|---|",
    ]
    own_total = all_total = cells_total = single_before = single_after = borrowed_cells = 0
    for row in data["rows"]:
        cells = [c for c in row["cells"] if not c["fixed"]]
        counts = "、".join(f"{c['own']}→{c['own'] + c['borrowed']}" for c in cells)
        borrowed = sorted({b for c in cells for b in c["borrowed_categories"]})
        lines.append(
            f"| {row['label']} | {row['skill']} | {row['flashes']} | {row['category'] or '—'} | "
            f"{counts} | {'、'.join(borrowed) or '—'} |"
        )
        for c in cells:
            cells_total += 1
            own_total += c["own"]
            all_total += c["own"] + c["borrowed"]
            single_before += c["own"] == 1
            single_after += c["own"] + c["borrowed"] == 1
            borrowed_cells += c["borrowed"] > 0
    lines += [
        "",
        f"- 可挑的格子（不含轉型保底）{cells_total} 格：候選共 {own_total} → {all_total} 個"
        f"（平均 {own_total / max(cells_total, 1):.2f} → {all_total / max(cells_total, 1):.2f}）；"
        f"只有 1 個候選的格子 {single_before} → {single_after}；"
        f"有借別類候選的格子 {borrowed_cells}（{borrowed_cells * 100 // max(cells_total, 1)}%）；"
        f"候選裡借來的占 {(all_total - own_total) * 100 // max(all_total, 1)}%。",
    ]
    return lines


def report(args: argparse.Namespace) -> int:
    name = "wish_compare_mock.json" if args.mock else "wish_compare.json"
    data = json.loads((DATA / name).read_text(encoding="utf-8"))
    rows = data["rows"]
    lines = ["## 摘要數字", "", *_summary(rows), "", "## 每個願望", ""]
    for row in rows:
        lines.append(f"### {row['label']}（{row['kind']}）「{row['wish']}」")
        lines.append("")
        lines.append("- **現行**：" + "\n".join(_side_md(row["old"], wish=False)))
        lines.append("- **願望驅動**：" + "\n".join(_side_md(row["new"], wish=True)))
        lines.append("")
    flash_path = DATA / "flash_borrow.json"
    if flash_path.exists():
        lines += ["## 閃現：不指定類別時借別類候選（B）", ""]
        lines += _flash_md(json.loads(flash_path.read_text(encoding="utf-8")))
    out = DATA / ("wish_compare_mock.md" if args.mock else "wish_compare.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"→ {out}", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--mock", action="store_true")
    p_run.add_argument("--limit", type=int, default=0)
    p_run.add_argument("--max-minutes", type=float, default=30.0)
    p_run.set_defaults(func=run)
    p_flash = sub.add_parser("flash")
    p_flash.set_defaults(func=flash)
    p_report = sub.add_parser("report")
    p_report.add_argument("--mock", action="store_true")
    p_report.set_defaults(func=report)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
