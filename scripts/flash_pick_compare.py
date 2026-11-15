"""閃現：LF-2（LLM 從目錄提議）vs 挑選模式（PK-3）的紙面比較。

同一組閃現情境（不同技能、不指定／指定類別、第 1／2／3 次、重閃），同一個模型各跑一次：

- (a) **LF-2**：``skill_pick.yaml`` 的 ``flash_enabled`` 關掉，``LlmFlashSource``（提議＋命名，同
  ``select_flash_source``）。
- (b) **挑選**：開關打開，同一個來源走 ``pick``（每格挑一個＋取名，``flash-pick/1``）。

輸出 JSON（每個情境的選項：類別、變化、名稱、描述、秒數、來源、錯誤碼；挑選模式另有每格候選數），
由 ``scripts/pick_compare.py report`` 併進 ``docs/phases/PhasePK-3比較.md``。

用法::

    uv run python scripts/flash_pick_compare.py run          # 真模型（先照上手筆記檢查 LM Studio）
    uv run python scripts/flash_pick_compare.py run --mock   # Mock 冒煙

量測前查 ``/api/v0/models``（只能載入設定的模型，否則結束碼 3）與生成速度（低於 60 t/s 結束碼 2）；
一次只送一個請求。
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import os
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trpg.content.library import ContentLibrary, load_library
from trpg.llm import OpenAICompatClient, load_llm_config
from trpg.llm.flash_propose import FlashProposalRecord, LlmFlashSource, mock_flash_source
from trpg.skillgen.flash_offer import FlashOffer, FlashRequest, choose, flash_slots, make_offer
from trpg.skillgen.flash_state import SkillFlash, acquire
from trpg.skillgen.usage import SkillUsage

sys.path.insert(0, str(Path(__file__).resolve().parent))
_PC: Any = importlib.import_module("pick_compare")  # 同資料夾：LM Studio 檢查與錄音 transport

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "phases" / "PK-3資料" / "flash_compare.json"
FORMAT = "flash-pick-compare/1"
SEED = 11


@dataclasses.dataclass(frozen=True, slots=True)
class Scenario:
    label: str
    skill: str
    flashes: int
    """出題前已閃過幾次（每次選第一個）。"""
    category: str | None = None
    slot: int | None = None
    usage: SkillUsage = dataclasses.field(default_factory=SkillUsage)


_MULTI = SkillUsage(uses=8, targets=20, distance=24, kills=2, target_keywords={"ignite": 4})
_SINGLE = SkillUsage(uses=9, targets=9, distance=36, kills=1, target_keywords={"wet": 3})
_SUPPORT = SkillUsage(uses=6, targets=6, distance=6)

SCENARIOS: tuple[Scenario, ...] = (
    Scenario("F1", "skill_fire_bolt", 0, usage=_SINGLE),
    Scenario("F2", "skill_cleave", 1, usage=_MULTI),
    Scenario("F3", "skill_fire_bolt", 2, usage=_SINGLE),
    Scenario("F4", "skill_cleave", 0, category="area", usage=_MULTI),
    Scenario("F5", "skill_radiant_mend", 0, usage=_SUPPORT),
    Scenario("F6", "skill_ember_brand", 0, usage=_SUPPORT),
    Scenario("F7", "skill_cleave", 2, usage=_MULTI),
    Scenario("F8", "skill_fire_bolt", 1, category="element", usage=_SINGLE),
    Scenario("F9", "skill_fire_bolt", 3, slot=1, usage=_SINGLE),
    Scenario("F10", "skill_cleave", 3, slot=3, usage=_MULTI),
)
"""第 1 次、第 2 次、第 3 次大變化、指定類別、輔助技、被動、重閃第 1 格、重閃第 3 格（大變化）。"""


def _state(library: ContentLibrary, scenario: Scenario) -> SkillFlash:
    base = library.skills[scenario.skill]
    state = acquire(scenario.skill).model_copy(update={"used": True})
    for _ in range(scenario.flashes):
        offer = make_offer(library, FlashRequest(base, state, scenario.usage, SEED))
        state, _skill = choose(state, offer, 0)
        state = state.model_copy(update={"used": True})
    return state


def request_of(library: ContentLibrary, scenario: Scenario) -> FlashRequest:
    return FlashRequest(
        library.skills[scenario.skill],
        _state(library, scenario),
        scenario.usage,
        SEED,
        slot=scenario.slot,
        category=scenario.category,
    )


def _options(offer: FlashOffer) -> list[dict[str, Any]]:
    return [
        {
            "category": o.variation.category,
            "source": o.variation.source,
            "key": o.variation.key(),
            "summary_zh": o.summary_zh,
            "skill_name": o.skill.name_zh,
            "name_zh": o.variation.name_zh,
            "note_zh": o.variation.note_zh,
            "weaker": o.weaker,
        }
        for o in offer.options
    ]


def _record(record: FlashProposalRecord | None) -> dict[str, Any]:
    if record is None:
        return {"source": "none"}
    return {
        "source": record.source,
        "prompt_version": record.prompt_version,
        "wanted": record.wanted,
        "attempts": record.attempts,
        "codes": [list(c) for c in record.codes],
        "names": [n.model_dump(mode="json") for n in record.names],
        "picks": list(record.picks),
        "reason": record.reason,
    }


def one(
    library: ContentLibrary, scenario: Scenario, source: LlmFlashSource, records: list[Any]
) -> dict[str, Any]:
    request = request_of(library, scenario)
    records.clear()
    start = time.perf_counter()
    offer = make_offer(library, request, source)
    seconds = round(time.perf_counter() - start, 2)
    found = records[-1] if records else None
    row: dict[str, Any] = {
        "seconds": seconds,
        "major": offer.major,
        "weaker": offer.weaker,
        "options": _options(offer),
        "record": _record(found),
    }
    if library.skill_pick.flash_enabled:
        row["slot_sizes"] = [len(s.candidates) for s in flash_slots(library, request)]
    return row


def run(args: argparse.Namespace) -> int:
    os.environ["TRPG_LLM_REASONING_EFFORT"] = "none"
    config = load_llm_config()
    meta: dict[str, Any] = {
        "format": FORMAT,
        "mock": args.mock,
        "model": config.model,
        "temperature": config.temperature,
        "reasoning_effort": config.reasoning_effort,
        "max_retries": config.max_retries,
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    client: OpenAICompatClient | None = None
    if not args.mock:
        code = int(_PC._preflight(config))
        if code:
            return code
        client = OpenAICompatClient(config)
    on = load_library()
    off = dataclasses.replace(
        on, skill_pick=on.skill_pick.model_copy(update={"flash_enabled": False})
    )
    rows: list[dict[str, Any]] = []
    try:
        for scenario in SCENARIOS[: args.limit or None]:
            row: dict[str, Any] = {
                "label": scenario.label,
                "skill": scenario.skill,
                "skill_zh": on.skills[scenario.skill].name_zh,
                "nth": request_of(on, scenario).nth,
                "category": scenario.category,
                "slot": scenario.slot,
            }
            for side, lib in (("lf2", off), ("pick", on)):
                records: list[Any] = []
                source = (
                    mock_flash_source(lib, sink=records.append, naming=True)
                    if client is None
                    else LlmFlashSource(
                        client, max_attempts=config.max_retries, sink=records.append, naming=client
                    )
                )
                row[side] = one(lib, scenario, source, records)
                print(
                    f"{scenario.label}｜{side}｜{row[side]['record'].get('source')}｜"
                    f"{row[side]['seconds']:.1f} 秒",
                    flush=True,
                )
            rows.append(row)
    finally:
        if client is not None:
            client.close()
    meta["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    out = args.out or OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"meta": meta, "rows": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"→ {out}", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("run")
    cmd.add_argument("--mock", action="store_true")
    cmd.add_argument("--limit", type=int, default=0)
    cmd.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
