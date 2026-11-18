"""``scripts/wait_scan.py``（TL-2）：交接文件「誰在等誰」掃描。只用測試內產生的小 markdown。"""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wait_scan.py"


@pytest.fixture(scope="module")
def ws() -> dict[str, Any]:
    return runpy.run_path(str(SCRIPT), run_name="wait_scan_under_test")


def _scan(ws: dict[str, Any], text: str) -> list[Any]:
    return list(ws["scan_text"](text, "x.md"))


@pytest.mark.parametrize(
    ("line", "owner"),
    [
        ("- 模型與 config 等使用者選", "使用者"),
        ("- 下一個大段等專案 PM 問使用者", "專案 PM"),
        ("- PK-4 待決 2～6 一次轉玩法", "玩法 PM"),
        ("- LW-2 那行加底色仍等美術答覆", "美術 PM"),
        ("- 美術手上無事，等開發交件驗收", "開發 PM"),
        ("- 等 PB-1e 交件", "開發 PM"),
        ("- 多格頭目等試玩 C 後再議", "未知"),
        ("- 門檻待玩法 PM", "玩法 PM"),
    ],
)
def test_owner_guess(ws: dict[str, Any], line: str, owner: str) -> None:
    hits = _scan(ws, line)
    assert len(hits) == 1
    assert hits[0].owner == owner
    assert hits[0].closed is False


@pytest.mark.parametrize(
    "line",
    [
        "- 角色等級提升",  # 等級
        "- 傷害等於攻擊力",  # 等於
        "- A、B 等",  # 列舉的等
        "- 待辦：補圖",  # 待辦
        "- 平衡待查第 27 條",  # 待查
        "- R5、R6 待排",  # 待排
        "- 報告寫「待 PM 決定」",  # 流程用語
        "- 等通知，不要輪詢",  # 流程守則
        "- 等待動畫：羽毛筆",  # 美術名詞
        "- 打不過就練等 #81",
        "- 待決 3 拿矛：照現況",  # 帶編號的待決是條目代號
        "- 「傷害」等玩法 PM 定字",  # 」後面的等是列舉
    ],
)
def test_noise_is_not_a_hit(ws: dict[str, Any], line: str) -> None:
    assert _scan(ws, line) == []


@pytest.mark.parametrize(
    "line",
    [
        "- PB-1 已 push，原本等開發交件",
        "- RG-4 結案，等開發交件",
        "- (e3y) 已完成（GB-4d）。原：下一段等美術答覆",
        "- 目前 **沒有** 待使用者決定的題",
        "- 目前沒有等使用者的題目",
    ],
)
def test_closed_is_marked(ws: dict[str, Any], line: str) -> None:
    hits = _scan(ws, line)
    assert hits, line
    assert all(h.closed for h in hits)


def test_closed_marker_only_affects_its_own_sentence(ws: dict[str, Any]) -> None:
    hits = _scan(ws, "- **RG-4 結案**；**K2 過審**，等開發交件")
    assert len(hits) == 1
    assert hits[0].closed is False
    assert hits[0].owner == "開發 PM"


def test_section_line_and_headings_skipped(ws: dict[str, Any]) -> None:
    text = "\n".join(
        [
            "# 交接",
            "## 5. 待使用者決定",  # 標題本身不算
            "",
            "- 第一件等美術答覆",
            "```",
            "等使用者回話（程式碼區塊不算）",
            "```",
            "### 等開發",
            "| 段 | 狀態 |",
            "|---|---|",
            "| PB-1e | 等開發交件 |",
        ]
    )
    hits = _scan(ws, text)
    assert [(h.line, h.section, h.owner) for h in hits] == [
        (4, "5. 待使用者決定", "美術 PM"),
        (11, "等開發", "開發 PM"),
    ]


def test_one_hit_per_sentence_and_split_sentences(ws: dict[str, Any]) -> None:
    hits = _scan(ws, "- 等使用者決定、還在等使用者。另一件待玩法 PM 回覆")
    assert [h.owner for h in hits] == ["使用者", "玩法 PM"]


def test_snippet_is_truncated(ws: dict[str, Any]) -> None:
    line = "- " + "前" * 100 + "等美術答覆" + "後" * 100
    hits = list(ws["scan_text"](line, "x.md", 20))
    assert len(hits) == 1
    snip = hits[0].snippet
    assert "等美術" in snip
    assert snip.startswith("…") and snip.endswith("…")
    assert len(snip) == 22


def test_markdown_groups_and_hides_closed(ws: dict[str, Any]) -> None:
    hits = _scan(ws, "- 等使用者選\n- 等開發交件\n- 已 push，等開發交件\n- 等試玩再說")
    md = ws["render_markdown"](hits)
    assert "未結 3 筆" in md and "已結案 1 筆" in md
    assert md.index("## 等使用者（1）") < md.index("## 等開發 PM（1）") < md.index("## 等未知（1）")
    assert "已 push" not in md
    assert "已 push" in ws["render_markdown"](hits, show_closed=True)


def test_json_output(ws: dict[str, Any]) -> None:
    hits = _scan(ws, "## 現況\n- 等使用者選\n- 已 push，等開發交件")
    data = json.loads(ws["render_json"](hits))
    assert data["total"] == 2 and data["open"] == 1 and data["closed"] == 1
    assert data["groups"] == {"使用者": 1}
    assert data["hits"][0] == {
        "file": "x.md",
        "line": 2,
        "section": "現況",
        "snippet": "等使用者選",
        "owner": "使用者",
        "rule": "等某人",
        "closed": False,
    }


def test_main_reads_files_and_globs(
    ws: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "a交接.md").write_text("## 甲\n- 等美術答覆\n", encoding="utf-8")
    (tmp_path / "b交接.md").write_text("## 乙\n- 待使用者決定\n", encoding="utf-8")
    assert ws["main"]([str(tmp_path / "*交接.md"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["groups"] == {"使用者": 1, "美術 PM": 1}
    assert ws["main"]([str(tmp_path / "none*.md")]) == 2


_SECTIONED = "\n".join(
    [
        "## 1. 角色與守則",
        "- 守則裡等使用者回話",
        "### 1.1 細節",  # 上層是守則，整節不掃
        "- 子節等美術答覆",
        "## 2. 現況",
        "- 現況等開發交件",
        "### 2.1 被推翻或作廢的方向",
        "- 作廢節等玩法 PM 回覆",
        "### 2.2 待轉開發 PM（玩法 PM 已定案，照這節轉）",  # 括號裡的字不算
        "- 待轉節等專案 PM 轉達",
        "## 3. 歸檔",
        "- 歸檔節等使用者決定",
        "## 4. 舊稿（`docs/archive/`）",
        "- 括號裡的 archive 不算，等美術答覆",
    ]
)


def test_skip_sections_by_title_and_parent(ws: dict[str, Any]) -> None:
    hits = _scan(ws, _SECTIONED)
    assert [(h.line, h.owner) for h in hits] == [(6, "開發 PM"), (10, "專案 PM"), (14, "美術 PM")]


def test_all_sections_flag_scans_everything(ws: dict[str, Any]) -> None:
    hits = list(ws["scan_text"](_SECTIONED, "x.md", 60, True))
    assert [h.line for h in hits] == [2, 4, 6, 8, 10, 12, 14]


@pytest.mark.parametrize(
    "line",
    [
        "- 使用者原話：「我等你們收尾就會叫他們做」",
        "- 開工時機：「等美術做完」",
        "- 不傳「還在等」這類告知",
        "- 原話「外層『等使用者』內層」之後",
        "- 沒收尾的「等開發交件",
    ],
)
def test_quotes_are_skipped_by_default(ws: dict[str, Any], line: str) -> None:
    assert _scan(ws, line) == []
    hits = list(ws["scan_text"](line, "x.md", 60, False, True))
    assert len(hits) == 1


def test_quote_only_hides_hits_inside_it(ws: dict[str, Any]) -> None:
    hits = _scan(ws, "- 「等」字以外：LW-2 那行仍等美術答覆")
    assert [h.owner for h in hits] == ["美術 PM"]


def test_main_flags(ws: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "c交接.md"
    f.write_text("## 流程\n- 等使用者回話\n## 現況\n- 原話「等美術答覆」\n", encoding="utf-8")
    assert ws["main"]([str(f), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 0
    assert ws["main"]([str(f), "--json", "--all-sections", "--include-quotes"]) == 0
    assert json.loads(capsys.readouterr().out)["groups"] == {"使用者": 1, "美術 PM": 1}
