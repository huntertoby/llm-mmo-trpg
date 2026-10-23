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

from trpg.cli.llm import ProposeArgs, cmd_llm_propose, propose_requests
from trpg.cli.main import main
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
    args = ProposeArgs(count=1, rarity="common", skeleton="strike")
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
