"""``.env`` 解析器（Phase 5E-2b；``docs/phases/Phase5計畫.md`` 32.3）。"""

from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from trpg.bot.envfile import EnvFileError, parse_env_text, read_env_file


def test_key_value_comments_and_blank_lines() -> None:
    text = "# 註解\n\nA=1\n  B = two words  \n# C=3\nEMPTY=\n"
    assert parse_env_text(text) == {"A": "1", "B": "two words", "EMPTY": ""}


def test_quotes_are_stripped_without_escapes() -> None:
    text = 'A="hello world"\nB=\'single\'\nC="has # hash"\nD="x\\ny"\nE="q" # 註解\n'
    assert parse_env_text(text) == {
        "A": "hello world",
        "B": "single",
        "C": "has # hash",
        "D": "x\\ny",
        "E": "q",
    }


def test_inline_comment_only_after_whitespace() -> None:
    assert parse_env_text("A=abc # 我的 token\nB=a#b\n") == {"A": "abc", "B": "a#b"}


def test_bom_crlf_and_last_one_wins() -> None:
    assert parse_env_text("﻿A=1\r\nA=2\r\n") == {"A": "2"}


@pytest.mark.parametrize(
    "line",
    ["NO_EQUALS", "1BAD=x", "export A=x", "=x", 'A="unterminated', 'A="x" trailing', "A B=x"],
)
def test_bad_line_reports_line_number_not_content(line: str) -> None:
    secret = secrets.token_urlsafe(16)
    with pytest.raises(EnvFileError) as info:
        parse_env_text(f"OK=1\n{line}{secret}\n", source="my.env")
    message = str(info.value)
    assert "my.env 第 2 行" in message
    assert secret not in message


def test_read_env_file(tmp_path: Path) -> None:
    assert read_env_file(tmp_path / "missing.env") == {}
    path = tmp_path / ".env"
    path.write_text("TRPG_DISCORD_GUILD_ID=123\n", encoding="utf-8")
    assert read_env_file(path) == {"TRPG_DISCORD_GUILD_ID": "123"}
