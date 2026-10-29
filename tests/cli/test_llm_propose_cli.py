"""4-L5：``trpg llm propose``（全部用 Mock，不需網路）。

``--mock -n 3`` 的輸出逐字比對快照 ``snapshots/llm_propose_mock.txt``；刻意改變輸出時以
``UPDATE_CLI_SNAPSHOTS=1 uv run pytest tests/cli/test_llm_propose_cli.py`` 重新產生，並在報告中
說明。
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

from trpg.cli.llm import ProposeArgs, _feasible, cmd_llm_propose, propose_requests
from trpg.cli.main import main
from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.llm import LLMUnavailable, MockLLMClient
from trpg.skillgen.proposal import proposal_from_skill
from trpg.skillgen.random_composer import default_library

SNAPSHOT = Path(__file__).parent / "snapshots" / "llm_propose_mock.txt"


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return default_library()


def test_mock_n3_snapshot(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["llm", "propose", "--mock", "-n", "3", "--seed", "0"]) == 0
    out = capsys.readouterr().out
    if os.environ.get("UPDATE_CLI_SNAPSHOTS") == "1":
        SNAPSHOT.write_text(out, encoding="utf-8", newline="\n")
    assert out == SNAPSHOT.read_text(encoding="utf-8")
    assert "一次通過率" in out and "退回率" in out


def test_requests_rotate_deterministically(library: ContentLibrary) -> None:
    args = ProposeArgs(count=12, seed=4)
    first = propose_requests(library, args)
    assert first == propose_requests(library, args)
    assert {r.rarity for r, _ in first} == {"common", "rare", "epic"}
    assert any(r.skeleton is None for r, _ in first)
    assert any(r.skeleton is not None for r, _ in first)
    fixed = propose_requests(
        library, ProposeArgs(count=3, rarity="rare", skeleton="strike", keywords=("ignite",))
    )
    wanted = ("rare", "strike", ("ignite",))
    assert all((r.rarity, r.skeleton, r.keywords) == wanted for r, _ in fixed)
    with pytest.raises(ValueError, match="未知的關鍵字"):
        propose_requests(library, ProposeArgs(keywords=("nope",)))


def test_injected_client_and_fallback_lines(library: ContentLibrary) -> None:
    skill = library.skills["skill_fire_arrow"]
    good = json.dumps(proposal_from_skill(skill, library), ensure_ascii=False)
    out, err = io.StringIO(), io.StringIO()
    owned = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    args = ProposeArgs(count=1, rarity="common", skeleton="strike", keywords=owned[:1])
    assert cmd_llm_propose(library, args, out, err, client=MockLLMClient([good])) == 0
    assert "｜llm｜嘗試 1｜通過｜" in out.getvalue()
    out = io.StringIO()
    client = MockLLMClient([LLMUnavailable("連不上")])
    assert cmd_llm_propose(library, args, out, err, client=client) == 0
    text = out.getvalue()
    assert "｜composer｜嘗試 1｜llm.unavailable｜" in text
    assert "退回率　　　　100.0%（1）　（提醒：超過 20%）" in text


def test_bad_keyword_and_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["llm", "propose", "--mock", "--keyword", "nope"]) == 1
    assert "未知的關鍵字" in capsys.readouterr().err
    assert main(["llm", "propose", "--mock", "--config", str(tmp_path / "x.toml")]) == 1
    assert "找不到 LLM 設定檔" in capsys.readouterr().err


def test_rotated_requests_are_always_feasible(library: ContentLibrary) -> None:
    """4-L5c：輪替出的題目不會是 select_subset 失敗或三層退回都做不出的題目。"""
    for seed in (0, 1):
        for request, request_seed in propose_requests(library, ProposeArgs(count=6, seed=seed)):
            assert _feasible(library, request, request_seed), (seed, request)


def test_explicit_requests_are_not_replaced(library: ContentLibrary) -> None:
    # 普通稀有度的被動骨架：select_subset 會丟 SubsetError，但全部由參數指定就照跑
    args = ProposeArgs(count=2, rarity="common", skeleton="passive", keywords=("marked",))
    requests = propose_requests(library, args)
    assert all(
        (r.rarity, r.skeleton, r.keywords) == ("common", "passive", ("marked",))
        for r, _ in requests
    )
    assert not _feasible(library, requests[0][0], requests[0][1])
    # 只指定骨架時，其餘依種子換到可行的題目
    partial = propose_requests(library, ProposeArgs(count=4, seed=3, skeleton="passive"))
    assert all(_feasible(library, r, s) for r, s in partial)


def test_naming_flag_adds_generated_names(capsys: pytest.CaptureFixture[str]) -> None:
    """``--naming``（4-L8b）：通過驗證的 LLM 技能再命名（Mock 命名），摘要多一行命名統計；
    不加時名稱是組合式名稱。"""
    assert main(["llm", "propose", "--mock", "-n", "6", "--seed", "0", "--naming"]) == 0
    named = capsys.readouterr().out
    assert "（命名 llm，1 次）" in named
    assert "命名：" in named and "組合式名稱 0" in named
    assert main(["llm", "propose", "--mock", "-n", "6", "--seed", "0"]) == 0
    plain = capsys.readouterr().out
    assert "命名" not in plain


def test_mock_picks_the_lowest_tier_the_keyword_allows(library: ContentLibrary) -> None:
    """3W-9b：``--mock`` 沒指定階級時，每題自動選 Mock 答得出的最低角色階級（召喚物 → 2 階），
    不再因為 1 階還不能用而退回手寫池；指定 ``--tier`` 或不用 Mock 時照舊 1 階。"""
    summon = propose_requests(library, ProposeArgs(count=2, mock=True, keywords=("summon",)))
    assert summon and all(r.tier == 2 for r, _ in summon)
    out, err = io.StringIO(), io.StringIO()
    args = ProposeArgs(count=2, mock=True, keywords=("summon",))
    assert cmd_llm_propose(library, args, out, err) == 0
    assert "2 階／" in out.getvalue() and "來源　　　　　llm 2" in out.getvalue()
    fixed = ProposeArgs(count=2, mock=True, tier=1, keywords=("summon",))
    assert all(r.tier == 1 for r, _ in propose_requests(library, fixed))
    real = ProposeArgs(count=2, keywords=("summon",))
    assert all(r.tier == 1 for r, _ in propose_requests(library, real))
