"""文字風格分區的評估（Phase 6L-1 C9；#126、#127）：可以自動判斷的三項驗收。

1. **非東方區的技能名不帶古風詞**：``style_eval.yaml`` 的 ``neutral_regions``（灰燼荒原、主城）裡，
   LLM 取的技能名不可出現 ``world_shattered.yaml`` ``naming.archaic`` 的古風詞或結尾（「某某訣」）；
   兩段敘事（``concept``、``cast_flavor``，6L-2 定稿）也不可出現古風詞（結尾規則只看名稱）。
   「施主」任何區的技能名都不能用（命名驗證 ``check_archaic`` 擋）；「訣」只有雲嶺可以用。
2. **雲嶺一般人不稱「施主」**：``formal_speakers`` 以外的 NPC 對白不可出現 ``honorifics``。
3. **「X・Y」句式不超過一半**：LLM 取的技能名中含「・」的比例 ≤ ``dot_share_max_permille``。

純函式：輸入是評估輸出的列（技能名、對白），不呼叫 LLM。腳本入口 ``scripts/eval_style.py``。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from trpg.content.world import ArchaicRules, StyleEvalRules

__all__ = [
    "DOT",
    "DialogueRow",
    "NameRow",
    "StyleReport",
    "archaic_hits",
    "is_dot_name",
    "report_lines",
    "style_report",
]

DOT = "・"


@dataclass(frozen=True, slots=True)
class NameRow:
    """一個技能名：取得地點的區域（``None``＝中性）、名稱、來源（``llm``／``fallback``）。"""

    region: str | None
    name: str
    source: str = "llm"
    concept: str = ""
    """技能概念（6L-2：中性區的古風詞檢查也看它；舊 CSV 沒有＝空）。"""
    cast_flavor: str = ""


@dataclass(frozen=True, slots=True)
class DialogueRow:
    """一段 NPC 對白：區域、NPC ID、文字。"""

    region: str
    npc: str
    text: str


def archaic_hits(text: str, rules: ArchaicRules, *, name: bool = True) -> list[str]:
    """``text`` 裡的古風詞（依清單順序、不重複）；``name`` 為真時另檢查結尾（「某某訣」）。"""
    hits = [t for t in dict.fromkeys((*rules.always, *rules.terms)) if t and t in text]
    if name:
        hits += [f"…{s}" for s in rules.suffixes if s and text.endswith(s)]
    return hits


def _row_hits(row: NameRow, rules: ArchaicRules) -> list[str]:
    """名稱（含結尾）與兩段敘事（不看結尾）的古風詞，不重複。"""
    hits = archaic_hits(row.name, rules)
    for text in (row.concept, row.cast_flavor):
        hits += archaic_hits(text, rules, name=False)
    return list(dict.fromkeys(hits))


def is_dot_name(name: str) -> bool:
    """名稱是「X・Y」句式（含「・」）。"""
    return DOT in name


@dataclass(frozen=True, slots=True)
class StyleReport:
    """三項驗收的結果。"""

    neutral_names: int
    neutral_archaic: tuple[tuple[str, str, tuple[str, ...]], ...]
    """（區域, 名稱, 命中的古風詞）。"""
    dialogues: int
    honorific_leaks: tuple[DialogueRow, ...]
    llm_names: int
    dot_names: int
    dot_max_permille: int

    @property
    def dot_permille(self) -> int:
        return self.dot_names * 1000 // self.llm_names if self.llm_names else 0

    @property
    def archaic_ok(self) -> bool:
        return not self.neutral_archaic

    @property
    def honorific_ok(self) -> bool:
        return not self.honorific_leaks

    @property
    def dot_ok(self) -> bool:
        return self.dot_names * 1000 <= self.dot_max_permille * self.llm_names

    @property
    def passed(self) -> bool:
        return self.archaic_ok and self.honorific_ok and self.dot_ok


def style_report(
    names: Sequence[NameRow],
    dialogues: Sequence[DialogueRow],
    rules: StyleEvalRules,
    archaic: ArchaicRules,
) -> StyleReport:
    """依 ``rules`` 判斷三項驗收；只看 LLM 取的名稱（退回的組合式名稱固定是「X・Y」，不算）。"""
    llm = [n for n in names if n.source == "llm"]
    neutral = [n for n in llm if n.region in rules.neutral_regions]
    bad = tuple(
        (str(n.region), n.name, tuple(hits)) for n in neutral if (hits := _row_hits(n, archaic))
    )
    leaks = tuple(
        d
        for d in dialogues
        if d.npc not in rules.formal_speakers.get(d.region, ())
        and any(h in d.text for h in rules.honorifics)
    )
    return StyleReport(
        neutral_names=len(neutral),
        neutral_archaic=bad,
        dialogues=len(dialogues),
        honorific_leaks=leaks,
        llm_names=len(llm),
        dot_names=sum(1 for n in llm if is_dot_name(n.name)),
        dot_max_permille=rules.dot_share_max_permille,
    )


def _mark(ok: bool) -> str:
    return "通過" if ok else "**不通過**"


def report_lines(report: StyleReport) -> list[str]:
    """Markdown 摘要（三項驗收一列一項，後面列出不通過的明細）。"""
    lines = [
        "| 驗收 | 結果 | 數字 |",
        "|---|---|---|",
        f"| 荒原、主城的技能名不帶古風詞 | {_mark(report.archaic_ok)} | "
        f"{len(report.neutral_archaic)}／{report.neutral_names} 個帶古風詞 |",
        f"| 雲嶺一般人的對白不出現「施主」 | {_mark(report.honorific_ok)} | "
        f"{len(report.honorific_leaks)}／{report.dialogues} 段 |",
        f"| 「X・Y」句式不超過一半 | {_mark(report.dot_ok)} | "
        f"{report.dot_names}／{report.llm_names}（{report.dot_permille / 10:.1f}%） |",
    ]
    for region, name, hits in report.neutral_archaic:
        lines.append(f"- 古風詞：{region}「{name}」（{'、'.join(hits)}）")
    for row in report.honorific_leaks:
        lines.append(f"- 稱施主：{row.region} {row.npc}「{row.text[:40]}」")
    return lines
