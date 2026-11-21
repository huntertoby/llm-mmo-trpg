"""技能生成：自由設計 vs 挑選模式的紙面比較（Phase PK-1；PK-3 起輸出 PK-3 的檔案、附 PK-2 對照）。

同一組題目（LB 的 20 題＝``scripts/llm_model_compare.py`` 的題目〔``trpg llm propose -n 20``、
seed 0〕，另加幾題）各跑兩條路，輸出原始 JSON 與給裁判看的 markdown：

- (a) **自由設計**：現行流程（``propose_skill`` 重試迴圈＋通過時 ``name_skill``），設定照
  ``config/llm.toml``。
- (b) **挑選模式**：``pick_slate``（組合器多種子→依設計去重→打分→前 K）＋ ``pick_skill``（一次呼叫
  挑選＋命名），同一個模型、``reasoning_effort`` none。

用法::

    uv run python scripts/pick_compare.py run          # 真模型（LM Studio，先照上手筆記檢查）
    uv run python scripts/pick_compare.py run --mock   # 不連模型的冒煙（Mock）
    uv run python scripts/pick_compare.py report       # 只從 JSON 重產 markdown

- 量測前查 ``/api/v0/models``：``state=loaded`` 的只能有一個、而且是設定的模型，否則停（結束碼 3）；
  生成速度低於 ``MIN_TPS``（60 t/s）也停（結束碼 2）。一次只送一個請求。
- 每題的「玩家」是確定性的樣本（3 招手寫技能，其中盡量 1 招帶題目的關鍵字），只給挑選模式打分與
  ``<player>`` 區塊用；自由設計的 prompt 沒有玩家手上技能這一欄（現行如此）。PK-1b 起樣本玩家另有
  確定性的行為紀錄與主屬性（手上技能和 PK-1 相同；行為紀錄用另一條亂數串流）。
- PK-2：挑選模式用加嚴的名稱檢查（``pick_skill(strict=True)``），打分多「這招有沒有料」；每題多
  ``thin``（收下那招的單薄原因）與 ``strict_mismatch``（加嚴詞組判斷的不符條數）。
- ``--baseline``（PK-3 起預設 ``docs/phases/PK-2資料/pick_compare.json``）的指標列在整體
  指標的對照欄。
- PK-3：report 另外併入三選一「每格候選數」（``scripts/pick_slot_stats.py`` 的
  ``slot_stats.json``，PK-2 對照 ``slot_stats_pk2.json``）與閃現比較
  （``scripts/flash_pick_compare.py`` 的 ``flash_compare.json``），檔案在才列。
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from trpg.cli.llm import ProposeArgs, propose_requests
from trpg.content.effect_words import load_effect_words
from trpg.content.library import ContentLibrary, load_library
from trpg.content.player_pool import player_skills
from trpg.content.skills import SkillDef, skill_elements
from trpg.llm import OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import mock_client_for, mock_naming_client
from trpg.llm.client import LLMClient
from trpg.llm.consistency import check_mentions, skill_facts, strict_facts
from trpg.llm.naming import name_skill
from trpg.llm.pick import candidate_card, fit_notes, mock_pick_client, pick_skill
from trpg.llm.propose import propose_skill
from trpg.narrative.skills import skill_card
from trpg.shared.rng import Rng
from trpg.shared.types import Attribute
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.candidates import skill_has_keywords
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.player_text import plain_name
from trpg.skillgen.proposal import ProposalContext
from trpg.skillgen.proposal_fallback import FallbackError
from trpg.skillgen.proposal_subset import ProposalRequest
from trpg.skillgen.skill_pick import design_key, design_label, pick_slate, thin_reasons

_LMC: Any = importlib.import_module("llm_model_compare")  # 同資料夾的 LB-1 量測腳本
MIN_TPS: float = _LMC.MIN_TPS
RecordingTransport: Any = _LMC.RecordingTransport
measure_speed = _LMC.measure_speed

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "phases" / "PK-3資料"
REPORT = ROOT / "docs" / "phases" / "PhasePK-3比較.md"
BASELINE = ROOT / "docs" / "phases" / "PK-2資料" / "pick_compare.json"
BASELINE_LABEL = "PK-2"
SLOT_STATS = ("slot_stats.json", "slot_stats_pk2.json")
FLASH_JSON = "flash_compare.json"
JSON_NAME = "pick_compare.json"
FORMAT = "pick-compare/3"
"""``pick-compare/3``（PK-2）：每題多 ``thin``、``strict_mismatch``（``/2``＝PK-1b：多
``held_in_slate``、樣本玩家多行為紀錄與主屬性）。"""
BEHAVIOR_ACTIONS: tuple[str, ...] = ("aim", "shove", "trip", "vault")
"""樣本玩家行為紀錄會出現的動作（``skill_keywords.yaml`` 有 ``actions`` 的四個）。"""
EXTRA_QUESTIONS: tuple[ProposalRequest, ...] = (
    ProposalRequest(2, "epic", keywords=("ignite",)),
    ProposalRequest(2, "rare", kind="reaction"),
    ProposalRequest(1, "epic", kind="passive", keywords=("fury",)),
    ProposalRequest(3, "rare", keywords=("poisoned",)),
)
"""LB 20 題以外再加的完整技能題（2、3 階、反應、被動＋關鍵字）。"""
EXTRA_SEED_BASE = 7000
PLAYER_SKILLS = 3
SUMMARY_MARK = "<!-- 摘要 -->"
"""markdown 裡手寫白話摘要的前後標記（重產 markdown 時保留兩個標記之間的文字）。"""
SUMMARY_PIECES = 2
BASELINE_NOTE = "PK-2 欄是 PK-2 的原始資料用同一份指標程式重算。"


# ---------------------------------------------------------------------------
# 題目與樣本玩家
# ---------------------------------------------------------------------------


def questions(library: ContentLibrary) -> list[tuple[ProposalRequest, int, str]]:
    """（題目, 種子, 標籤）：LB 的 20 題＋:data:`EXTRA_QUESTIONS`。"""
    out = [
        (request, seed, f"Q{i}")
        for i, (request, seed) in enumerate(
            propose_requests(library, ProposeArgs(count=20, seed=0)), 1
        )
    ]
    for j, request in enumerate(EXTRA_QUESTIONS, 1):
        out.append((request, EXTRA_SEED_BASE + j, f"X{j}"))
    return out


def sample_player(library: ContentLibrary, request: ProposalRequest, seed: int) -> PickPlayer:
    """確定性的樣本玩家：同階級、非傳說的手寫技能 3 招；題目有關鍵字時其中 1 招盡量帶它（同 PK-1）。
    PK-1b 另給行為紀錄（:data:`BEHAVIOR_ACTIONS` 各 0～5 次，``pk1b.behavior`` 串流）與主屬性
    （手上技能最常見的縮放屬性 16、其餘 10）。"""
    rng = Rng(seed).fork("pk1.player")
    pool = sorted(
        (
            s
            for s in player_skills(library).values()
            if s.tier == request.tier and s.rarity != "legendary" and s.kind == "active"
        ),
        key=lambda s: s.id,
    )
    chosen: list[SkillDef] = []
    if request.keywords:
        related = [s for s in pool if skill_has_keywords(s, request.keywords[:1], library)]
        if related:
            chosen.append(rng.choice(related))
    rest = [s for s in pool if s not in chosen]
    chosen += rng.shuffled(rest)[: PLAYER_SKILLS - len(chosen)]
    held = tuple(sorted(chosen, key=lambda s: s.id))
    habit = Rng(seed).fork("pk1b.behavior")
    behavior = {a: n for a in BEHAVIOR_ACTIONS if (n := habit.randint(0, 5))}
    attrs: dict[Attribute, int] = {}
    if held:
        common = Counter(s.scaling_attr for s in held).most_common()
        top = min((a for a, n in common if n == common[0][1]), key=lambda a: a.value)
        attrs = {a: 16 if a == top else 10 for a in Attribute}
    return PickPlayer(held_skills=held, behavior=behavior, hero_attributes=attrs)


def describe(library: ContentLibrary, request: ProposalRequest) -> str:
    keywords = "、".join(plain_name(k, library) for k in request.keywords) or "無關鍵字"
    kind = request.kind or "不限種類"
    return (
        f"{request.tier} 階／{request.rarity}／{kind}／{request.skeleton or '不限骨架'}／{keywords}"
    )


# ---------------------------------------------------------------------------
# 技能卡（兩邊共用）
# ---------------------------------------------------------------------------


def _ratio(library: ContentLibrary, skill: SkillDef) -> int | None:
    try:
        return int(skill_budget(skill, library).ratio * 1000)
    except BudgetError:
        return None


def skill_row(library: ContentLibrary, skill: SkillDef) -> dict[str, Any]:
    """一招的紙面資料：名稱、描述、種類、骨架、效果、關鍵字、元素、預算比例（‰）、設計鍵。"""
    card = skill_card(library, skill)
    found = derive_keywords(skill, library.keywords, exclusive_only=True)
    return {
        "id": skill.id,
        "name_zh": skill.name_zh,
        "concept": skill.narrative.concept,
        "cast_flavor": skill.narrative.cast_flavor,
        "kind": skill.kind,
        "kind_zh": card.kind,
        "skeleton": skill.skeleton,
        "skeleton_zh": card.skeleton_zh,
        "shape": card.shape,
        "cost": list(card.cost),
        "condition": card.condition,
        "timing": card.timing,
        "effects": list(card.effects),
        "effect_types": sorted({e.type for e in skill.effects}),
        "makes": [plain_name(k, library) for k in found.makes],
        "uses": [plain_name(k, library) for k in found.uses],
        "keyword_ids": list(found.all()),
        "elements": sorted(e.value for e in skill_elements(skill)),
        "elements_zh": sorted(e.display_name for e in skill_elements(skill)),
        "budget_permille": _ratio(library, skill),
        "design": design_label(design_key(skill)),
    }


# ---------------------------------------------------------------------------
# 兩條路
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Runner:
    library: ContentLibrary
    client: LLMClient | None
    transport: Any
    attempts: int
    mock: bool
    taken_free: set[str] = field(default_factory=set)
    taken_pick: set[str] = field(default_factory=set)

    def _calls(self) -> list[dict[str, Any]]:
        if self.transport is None:
            return []
        out = []
        for call in self.transport.calls:
            data = {k: getattr(call, k) for k in type(call).__slots__}
            data["seconds"] = round(call.seconds, 3)
            out.append({k: v for k, v in data.items() if v is not None})
        return out

    def _reset(self, step: str) -> None:
        if self.transport is not None:
            self.transport.calls = []
            self.transport.step = step

    def free(self, request: ProposalRequest, seed: int) -> dict[str, Any]:
        """(a) 自由設計：提議（重試）＋通過時命名。"""
        lib = self.library
        self._reset("propose")
        client = self.client or mock_client_for(lib, request, seed, self.attempts)
        start = time.perf_counter()
        try:
            outcome = propose_skill(
                client,
                lib,
                request,
                ProposalContext(request.tier, request.rarity),
                seed=seed,
                max_attempts=self.attempts,
                clock=time.perf_counter,
            )
        except (FallbackError, ValueError) as exc:
            return {"source": "failed", "error": str(exc), "seconds": _since(start)}
        skill = outcome.skill
        row: dict[str, Any] = {
            "source": outcome.source,
            "fallback": outcome.source != "llm",
            "attempts": outcome.attempts,
            "codes": [list(c) for c in outcome.codes],
            "reason": outcome.reason,
            "propose_seconds": _since(start),
        }
        if outcome.source == "llm":
            self._reset("naming")
            namer = self.client or mock_naming_client(lib, skill, seed)
            named = name_skill(namer, lib, skill, taken=self.taken_free, max_attempts=self.attempts)
            skill = skill.model_copy(
                update={
                    "name_zh": named.text.name_zh,
                    "narrative": skill.narrative.model_copy(
                        update={
                            "concept": named.text.concept,
                            "cast_flavor": named.text.cast_flavor,
                        }
                    ),
                }
            )
            row.update(naming_source=named.source, naming_codes=list(named.codes))
        self.taken_free.add(skill.name_zh)
        row["seconds"] = _since(start)
        row["calls"] = self._calls()
        row["skill"] = skill_row(lib, skill)
        row["desc_mismatch"] = _desc_checks(lib, row["skill"], skill)
        return row

    def pick(self, request: ProposalRequest, seed: int, player: PickPlayer) -> dict[str, Any]:
        """(b) 挑選模式：候選池＋打分（CPU）→ 一次 LLM 呼叫挑選＋命名。"""
        lib = self.library
        ctx = ProposalContext(request.tier, request.rarity, keywords=request.keywords)
        self._reset("pick")
        start = time.perf_counter()
        slate = pick_slate(lib, request, ctx, seed=seed, player=player)
        pool_seconds = _since(start)
        client = self.client or mock_pick_client(lib, slate, seed)
        llm_start = time.perf_counter()
        try:
            outcome = pick_skill(
                client,
                lib,
                request,
                ctx,
                seed=seed,
                taken=self.taken_pick,
                player=player,
                slate=slate,
                max_attempts=self.attempts,
                strict=True,
            )
        except FallbackError as exc:
            return {"source": "failed", "error": str(exc), "seconds": _since(start)}
        self.taken_pick.add(outcome.skill.name_zh)
        shown = skill_row(lib, outcome.skill)
        return {
            "source": outcome.source,
            "fallback": outcome.source != "llm",
            "attempts": outcome.attempts,
            "codes": list(outcome.codes),
            "reason": outcome.reason,
            "index": outcome.index,
            "picked": outcome.picked,
            "name_source": outcome.name_source,
            "pool_size": slate.pool_size,
            "seeds_tried": slate.seeds_tried,
            "pool_seconds": pool_seconds,
            "llm_seconds": _since(llm_start),
            "seconds": _since(start),
            "calls": self._calls(),
            "raws": list(outcome.raws),
            "candidates": [
                {
                    "index": i,
                    "source": c.source,
                    "seed": c.seed,
                    "design": design_label(c.key),
                    "score": c.score,
                    "parts": dict(c.parts),
                    "card": candidate_card(
                        lib,
                        c.skill,
                        i,
                        fixed=c.source == "pool",
                        fit=fit_notes(lib, c.skill, player),
                    ),
                }
                for i, c in enumerate(slate.ranked)
            ],
            "skill": shown,
            "desc_mismatch": _desc_checks(lib, shown, outcome.skill),
            "strict_mismatch": _desc_checks(lib, shown, outcome.skill, strict=True),
            "thin": list(
                thin_reasons(
                    outcome.skill, epic_min_effects=lib.skill_pick.weights.thin_epic_min_effects
                )
            ),
            "held_in_slate": sum(
                1
                for c in slate.ranked
                if c.skill.id in {h.id for h in player.held_skills}
                or c.skill.name_zh in {h.name_zh for h in player.held_skills}
            ),
        }


def _since(start: float) -> float:
    return round(time.perf_counter() - start, 3)


# ---------------------------------------------------------------------------
# LM Studio 檢查
# ---------------------------------------------------------------------------


def loaded_models(base_url: str) -> list[str]:
    root = base_url.rstrip("/").removesuffix("/v1")
    payload = httpx.get(f"{root}/api/v0/models", timeout=10).json()
    return sorted(m["id"] for m in payload.get("data", []) if m.get("state") == "loaded")


# ---------------------------------------------------------------------------
# 指標
# ---------------------------------------------------------------------------


def _desc_checks(
    library: ContentLibrary, skill: dict[str, Any], sk: SkillDef, *, strict: bool = False
) -> int:
    """名稱與兩段文字提到、但效果裡沒有的元素／控制／召喚詞（規則判斷；0＝對得上）。``strict``
    （PK-2）：連加嚴詞組（高處、地形、墜落、打擊、形狀、單字元素）一起看。"""
    words = load_effect_words()
    facts = strict_facts(library, sk) if strict else skill_facts(library, sk)
    bad = 0
    for label in ("name_zh", "concept", "cast_flavor"):
        bad += len(check_mentions(label, str(skill[label]), facts, words, strict=strict))
    return bad


def _mentions_element(skill: dict[str, Any]) -> bool | None:
    """技能有元素時，名稱或描述有沒有提到它（元素中文名的第一個字，例「火焰」→「火」）。"""
    elements = [e for e in skill["elements_zh"] if e != "物理"]
    if not elements:
        return None
    text = skill["name_zh"] + skill["concept"] + skill["cast_flavor"]
    return any(e[0] in text for e in elements)


def path_metrics(rows: Sequence[dict[str, Any]], side: str) -> dict[str, Any]:
    done = [r[side] for r in rows if r[side].get("source") != "failed"]
    skills = [r["skill"] for r in done]
    fit = 0
    for row in rows:
        part = row[side]
        if part.get("source") == "failed" or not row["keywords"]:
            continue
        need = set(row["keywords"])
        fit += need <= set(part["skill"]["keyword_ids"])
    elements = Counter(e for s in skills for e in (s["elements"] or ["none"]))
    seconds = [r["seconds"] for r in done]
    mentions = [m for s in skills if (m := _mentions_element(s)) is not None]
    picks = [r.get("index") for r in done if r.get("index") is not None]
    return {
        "questions": len(rows),
        "completed": len(done),
        "no_element": elements.get("none", 0),
        "handwritten": sum(1 for r in done if r.get("name_source") == "handwritten"),
        "index0": sum(1 for i in picks if i == 0),
        "index_counts": dict(sorted(Counter(picks).items())),
        "held_in_slate": sum(r.get("held_in_slate", 0) for r in done),
        "fallback": sum(1 for r in done if r["fallback"]),
        "designs": len({s["design"] for s in skills}),
        "effect_types": len({t for s in skills for t in s["effect_types"]}),
        "skeletons": len({s["skeleton"] for s in skills}),
        "elements": dict(sorted(elements.items())),
        "keyword_fit": fit,
        "keyword_questions": sum(1 for r in rows if r["keywords"]),
        "desc_mismatch": sum(r.get("desc_mismatch", 0) for r in done),
        "strict_mismatch": (
            sum(r.get("strict_mismatch", 0) for r in done)
            if any("strict_mismatch" in r for r in done)
            else "—"
        ),
        "thin_picked": (
            sum(1 for r in done if r.get("thin")) if any("thin" in r for r in done) else "—"
        ),
        "element_mentioned": sum(mentions),
        "element_skills": len(mentions),
        "seconds_median": round(statistics.median(seconds), 2) if seconds else None,
        "seconds_mean": round(statistics.fmean(seconds), 2) if seconds else None,
        "seconds_max": round(max(seconds), 2) if seconds else None,
        "budget_median": statistics.median(
            s["budget_permille"] for s in skills if s["budget_permille"] is not None
        )
        if skills
        else None,
    }


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def _client(args: argparse.Namespace) -> tuple[Any, LLMClient | None, Any]:
    os.environ["TRPG_LLM_REASONING_EFFORT"] = "none"  # 只這一次執行（兩條路都不開思考）
    config = load_llm_config()
    if args.mock:
        return config, None, None
    transport = RecordingTransport()
    return config, OpenAICompatClient(config, transport=transport), transport


def _preflight(config: Any) -> int:
    models = loaded_models(config.base_url)
    print(f"已載入：{models}", flush=True)
    if models != [config.model]:
        print(f"載入的模型不是只有 {config.model}，停止", flush=True)
        return 3
    speed = measure_speed(config)
    print(f"速度：{speed}", flush=True)
    tps = speed["generation_tps"]
    if tps is not None and tps < MIN_TPS:
        print(f"生成速度 {tps} t/s 低於 {MIN_TPS}，停止", flush=True)
        return 2
    return 0


def run(args: argparse.Namespace) -> int:
    config, client, transport = _client(args)
    meta: dict[str, Any] = {
        "format": FORMAT,
        "mock": args.mock,
        "model": config.model,
        "reasoning_effort": config.reasoning_effort,
        "temperature": config.temperature,
        "max_retries": config.max_retries,
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if not args.mock:
        code = _preflight(config)
        if code:
            return code
        meta["speed"] = measure_speed(config)
    library = load_library()
    meta["pick_rules"] = library.skill_pick.model_dump(mode="json")
    runner = Runner(library, client, transport, config.max_retries, args.mock)
    rows: list[dict[str, Any]] = []
    picked = questions(library)[: args.limit or None]
    try:
        if client is not None and not args.no_warmup:  # 暖機（不計入）
            warm_request, warm_seed, _ = picked[0]
            runner.pick(warm_request, warm_seed + 1, PickPlayer())
            runner.taken_pick.clear()
        for request, seed, label in picked:
            rows.append(_question(library, runner, request, seed, label))
    finally:
        if isinstance(client, OpenAICompatClient):
            client.close()
    meta["finished_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    result = {"meta": meta, "rows": rows}
    result["metrics"] = {side: path_metrics(rows, side) for side in ("free", "pick")}
    out = args.out or DATA_DIR / JSON_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"→ {out}", flush=True)
    write_report(result, args.report, _baseline(args.baseline))
    return 0


def _question(
    library: ContentLibrary, runner: Runner, request: ProposalRequest, seed: int, label: str
) -> dict[str, Any]:
    player = sample_player(library, request, seed)
    row: dict[str, Any] = {
        "label": label,
        "seed": seed,
        "request": describe(library, request),
        "keywords": list(request.keywords),
        "player": [s.name_zh for s in player.held_skills],
        "behavior": dict(player.behavior),
    }
    for side in ("free", "pick"):
        part = runner.free(request, seed) if side == "free" else runner.pick(request, seed, player)
        row[side] = part
        print(
            f"{label}｜{side}｜{part.get('source')}｜{part.get('seconds', 0):.1f} 秒｜"
            f"{part.get('skill', {}).get('name_zh', part.get('error', ''))}",
            flush=True,
        )
    return row


# ---------------------------------------------------------------------------
# report（markdown）
# ---------------------------------------------------------------------------


def _skill_md(skill: dict[str, Any]) -> list[str]:
    keywords = "、".join(
        [*(f"製造{k}" for k in skill["makes"]), *(f"利用{k}" for k in skill["uses"])]
    )
    budget = skill["budget_permille"]
    return [
        f"**{skill['name_zh']}**（{skill['kind_zh']}／{skill['skeleton_zh']}／{skill['shape']}）",
        f"- 描述：{skill['concept']}｜{skill['cast_flavor']}",
        f"- 效果：{'；'.join(skill['effects'])}",
        f"- 代價：{'、'.join(skill['cost']) or '—'}"
        + (f"｜條件：{skill['condition']}" if skill["condition"] else "")
        + (f"｜{skill['timing']}" if skill.get("timing") else ""),
        f"- 關鍵字：{keywords or '—'}｜元素：{'、'.join(skill['elements_zh']) or '—'}"
        f"｜強度占預算：{budget / 10 if budget is not None else '—'}%",
    ]


def _side_md(part: dict[str, Any], title: str) -> list[str]:
    if part.get("source") == "failed":
        return [f"#### {title}", f"失敗：{part.get('error')}", ""]
    flag = "退回" if part["fallback"] else "沒有退回"
    head = f"#### {title}（{part['source']}，{flag}，{part['seconds']:.1f} 秒）"
    lines = [head, *_skill_md(part["skill"])]
    if part.get("reason"):
        lines.append(f"- 退回原因：{part['reason']}")
    return [*lines, ""]


def _candidates_md(part: dict[str, Any]) -> list[str]:
    if part.get("source") == "failed" or not part.get("candidates"):
        return []
    picked = part.get("picked")
    lines = [
        f"挑選模式的候選（池 {part['pool_size']} 個設計、抽 {part['seeds_tried']} 個種子、"
        f"CPU {part['pool_seconds']:.1f} 秒、LLM {part['llm_seconds']:.1f} 秒）："
    ]
    for cand in part["candidates"]:
        card = cand["card"]
        mark = "→" if cand["index"] == picked else "　"
        name = f"「{card['fixed_name']}」" if "fixed_name" in card else ""
        parts = "、".join(f"{k}{v:+d}" for k, v in cand["parts"].items() if v)
        timing = f"{card['timing']}／" if card.get("timing") else ""
        lines.append(
            f"- {mark}{cand['index']}{name}：{card['skeleton']}／{card['shape']}／{timing}"
            f"{'；'.join(card['effects'])}（分數 {cand['score']}{'：' + parts if parts else ''}）"
        )
    who = "LLM 選" if part.get("index") is not None else "程式取第一名"
    return [*lines, f"- {who}：{picked}", ""]


def _metrics_md(
    metrics: dict[str, dict[str, Any]], baseline: dict[str, dict[str, Any]] | None = None
) -> list[str]:
    """整體指標：本次的自由設計、挑選模式；有 ``baseline``（PK-1 的指標）時另列 PK-1 兩欄。"""
    columns = [("自由設計", metrics["free"]), ("挑選模式", metrics["pick"])]
    if baseline is not None:
        columns += [
            (f"{BASELINE_LABEL} 自由設計", baseline["free"]),
            (f"{BASELINE_LABEL} 挑選模式", baseline["pick"]),
        ]

    def row(label: str, cell: Callable[[dict[str, Any]], Any]) -> str:
        return f"| {label} | " + " | ".join(str(cell(m)) for _, m in columns) + " |"

    def ratio(a: str, b: str) -> Callable[[dict[str, Any]], Any]:
        return lambda m: f"{m.get(a)}/{m.get(b)}"

    def key(name: str) -> Callable[[dict[str, Any]], Any]:
        return lambda m: m.get(name, "—")

    return [
        "| 指標 | " + " | ".join(t for t, _ in columns) + " |",
        "|---" * (len(columns) + 1) + "|",
        row("完成／題數", ratio("completed", "questions")),
        row("退回（沒有用到 LLM 的設計或名字）", key("fallback")),
        row("不同設計數", key("designs")),
        row("不同效果原語數", key("effect_types")),
        row("不同骨架數", key("skeletons")),
        row("元素分布", key("elements")),
        row("沒有元素的招", key("no_element")),
        row("挑到手寫技能", key("handwritten")),
        row("LLM 挑第 0 號", key("index0")),
        row("LLM 挑的 index 分布", key("index_counts")),
        row("候選裡出現手上已有的技能", key("held_in_slate")),
        row("關鍵字貼合（帶齊題目關鍵字）", ratio("keyword_fit", "keyword_questions")),
        row("名稱與描述提到效果裡沒有的詞（條數，規則判斷）", key("desc_mismatch")),
        row("同上，加嚴詞組（高處、地形、墜落、打擊、形狀、單字元素）", key("strict_mismatch")),
        row("收下的招單薄（只有刻紋／標記、只有條件式非傷害、史詩效果太少）", key("thin_picked")),
        row("有元素的招，名稱或描述提到該元素", ratio("element_mentioned", "element_skills")),
        row("強度占預算（中位，‰）", key("budget_median")),
        row("每題秒數（中位）", key("seconds_median")),
        row("每題秒數（平均）", key("seconds_mean")),
        row("每題秒數（最慢）", key("seconds_max")),
    ]


def _baseline(path: Path | None) -> dict[str, dict[str, Any]] | None:
    """對照（PK-2 起是 PK-1b）的結果用同一份 :func:`path_metrics` 重算指標；檔案不在時為
    ``None``。"""
    source = path or BASELINE
    if not source.exists():
        return None
    old = json.loads(source.read_text(encoding="utf-8"))
    return {side: path_metrics(old["rows"], side) for side in ("free", "pick")}


def _load(name: str) -> dict[str, Any] | None:
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _slots_md() -> list[str]:
    """PK-3：三選一每格的候選數（``pick_slot_stats.py``；PK-2 對照）。"""
    now, old = (_load(n) for n in SLOT_STATS)
    if now is None:
        return []
    columns = [("PK-3", now["summary"])]
    if old is not None:
        columns.append(("PK-2", old["summary"]))
    sizes = sorted({int(k) for _, s in columns for k in s["distribution"]})

    def cell(summary: dict[str, Any], size: int) -> str:
        count = summary["distribution"].get(str(size), summary["distribution"].get(size, 0))
        return f"{count}（{count * 100 // summary['slots']}%）"

    lines = [
        "## 三選一每格的候選數（不請 LLM；同一組 48 份三選一、144 格）",
        "",
        "| | " + " | ".join(t for t, _ in columns) + " |",
        "|---" * (len(columns) + 1) + "|",
    ]
    for size in sizes:
        lines.append(f"| {size} 張 | " + " | ".join(cell(s, size) for _, s in columns) + " |")
    lines += [
        "| 請 LLM 挑的格子（候選 ≥ 2） | "
        + " | ".join(f"{s['ask_llm']}/{s['slots']}" for _, s in columns)
        + " |",
        "| 每格平均候選數 | " + " | ".join(str(s["mean_candidates"]) for _, s in columns) + " |",
        "| 升級白板：請 LLM 的格子 | "
        + " | ".join(
            f"{s['by_reason']['level_up']['ask_llm']}/{s['by_reason']['level_up']['slots']}"
            for _, s in columns
        )
        + " |",
        "| 完整技能：請 LLM 的格子 | "
        + " | ".join(
            f"{s['by_reason']['complete']['ask_llm']}/{s['by_reason']['complete']['slots']}"
            for _, s in columns
        )
        + " |",
        "| 分數第一名的偏離（每份平均／最多） | "
        + " | ".join(f"{s['off_route_top_mean']}／{s['off_route_top_max']}" for _, s in columns)
        + " |",
        "| 出題 CPU 秒數（升級／完整技能，平均） | "
        + " | ".join(
            f"{s['seconds_mean']['level_up']}／{s['seconds_mean']['complete']}" for _, s in columns
        )
        + " |",
        "",
    ]
    return lines


def _flash_option(option: dict[str, Any]) -> str:
    name = option.get("name_zh") or ""
    note = option.get("note_zh") or ""
    tail = "".join(
        [
            f"｜名稱「{name}」" if name else "",
            f"｜「{note}」" if note else "",
            "｜比原本弱" if option.get("weaker") else "",
        ]
    )
    return f"{option['category']}：{option['summary_zh'] or option['key']}{tail}"


def _flash_md() -> list[str]:
    """PK-3：閃現 LF-2 vs 挑選模式（``flash_pick_compare.py``）。"""
    data = _load(FLASH_JSON)
    if data is None:
        return []
    meta = data["meta"]
    lines = [
        "## 閃現：LF-2（LLM 從目錄提議）vs 挑選模式",
        "",
        f"> 模型 `{meta['model']}`、溫度 {meta['temperature']}；"
        f"{'Mock' if meta['mock'] else '真模型'}；{meta['started_utc']}～{meta['finished_utc']}。"
        f"原始資料 `docs/phases/{DATA_DIR.name}/{FLASH_JSON}`。",
        "",
        "| 情境 | 技能 | 第幾次 | LF-2 來源／秒數 | 挑選 來源／秒數 | 挑選每格候選數 |",
        "|---|---|---|---|---|---|",
    ]
    for row in data["rows"]:
        what = (f"重閃第 {row['slot']} 格" if row.get("slot") else f"第 {row['nth']} 次") + (
            f"（指定 {row['category']}）" if row.get("category") else ""
        )
        a, b = row["lf2"], row["pick"]
        lines.append(
            f"| {row['label']} | {row['skill_zh']} | {what} | "
            f"{a['record']['source']}／{a['seconds']} | {b['record']['source']}／{b['seconds']} | "
            f"{b.get('slot_sizes', '—')} |"
        )
    lines.append("")
    for row in data["rows"]:
        lines.append(f"### {row['label']}：{row['skill_zh']}")
        for side, title in (("lf2", "LF-2"), ("pick", "挑選")):
            part = row[side]
            record = part["record"]
            codes = sorted({c for attempt in record.get("codes", []) for c in attempt})
            lines.append(
                f"- **{title}**（{record['source']}，{part['seconds']} 秒，"
                f"呼叫 {record.get('attempts', 0)} 次"
                + (f"，錯誤碼 {'、'.join(codes)}" if codes else "")
                + "）"
            )
            lines += [f"  - {_flash_option(o)}" for o in part["options"]]
        lines.append("")
    return lines


def write_report(
    result: dict[str, Any],
    path: Path | None = None,
    baseline: dict[str, dict[str, Any]] | None = None,
) -> None:
    meta = result["meta"]
    lines = [
        "# PK-3 比較：挑選模式（三選一每格候選、閃現）與自由設計（紙面樣本）",
        "",
        SUMMARY_MARK,
        "",
        f"> 模型 `{meta['model']}`、溫度 {meta['temperature']}、`reasoning_effort` "
        f"{meta['reasoning_effort']}；{'Mock（不是真模型）' if meta['mock'] else '真模型'}；"
        f"{meta['started_utc']}～{meta['finished_utc']}。"
        f"原始資料 `docs/phases/{DATA_DIR.name}/{JSON_NAME}`。"
        + (BASELINE_NOTE if baseline else ""),
        "",
        "## 每題並排",
        "",
    ]
    for row in result["rows"]:
        lines += [
            f"### {row['label']}：{row['request']}",
            f"樣本玩家手上：{'、'.join(row['player']) or '—'}"
            + (f"｜行為紀錄：{row['behavior']}" if row.get("behavior") else ""),
            "",
            *_side_md(row["free"], "(a) 自由設計"),
            *_side_md(row["pick"], "(b) 挑選模式"),
            *_candidates_md(row["pick"]),
        ]
    lines += ["## 整體指標", "", *_metrics_md(result["metrics"], baseline), ""]
    lines += _slots_md()
    lines += _flash_md()
    target = path or REPORT
    old = target.read_text(encoding="utf-8") if target.exists() else ""
    pieces = old.split(SUMMARY_MARK)
    summary = pieces[1] if len(pieces) > SUMMARY_PIECES else ""
    text = "\n".join(lines)
    if summary:  # 保留手寫的白話摘要（兩個標記之間）
        text = text.replace(SUMMARY_MARK, SUMMARY_MARK + summary + SUMMARY_MARK, 1)
    target.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"→ {target}", flush=True)


def report(args: argparse.Namespace) -> int:
    source = args.out or DATA_DIR / JSON_NAME
    result = json.loads(source.read_text(encoding="utf-8"))
    result["metrics"] = {side: path_metrics(result["rows"], side) for side in ("free", "pick")}
    write_report(result, args.report, _baseline(args.baseline))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "report"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--out", type=Path, default=None, help="JSON 路徑")
        cmd.add_argument("--report", type=Path, default=None, help="markdown 路徑")
        cmd.add_argument("--baseline", type=Path, default=None, help="對照的 JSON（預設 PK-1b）")
    run_cmd = sub.choices["run"]
    run_cmd.add_argument("--mock", action="store_true", help="不連模型（Mock 冒煙）")
    run_cmd.add_argument("--limit", type=int, default=0, help="只跑前幾題（0＝全部）")
    run_cmd.add_argument("--no-warmup", action="store_true")
    args = parser.parse_args(argv)
    return run(args) if args.command == "run" else report(args)


if __name__ == "__main__":
    sys.exit(main())
