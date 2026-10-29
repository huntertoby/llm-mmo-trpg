"""``trpg run`` 的 LLM 生成選項（Phase 4-L6）：``--llm``、``--llm-mock``、退回率摘要。

- ``--llm``：這一輪的候選請本機模型提議（``config/llm.toml`` 的連線設定）。
- ``--llm-mock``：用 Mock 提議器跑（不需網路與金鑰；CI 與本機試跑用）。
- 都沒有時看設定檔的 ``generate``（預設關：沒有本機模型時照舊）。

提議器經 :func:`trpg.roguelite.llm_hook.use_proposer` 裝上；生成的技能與題目存在 run 裡，之後的
重播與讀檔不再呼叫模型。
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from trpg.content.library import ContentLibrary
from trpg.llm import LLMConfig, LLMConfigError, OpenAICompatClient, load_llm_config
from trpg.llm.candidate_source import make_proposer, mock_proposer
from trpg.roguelite.llm_hook import use_proposer
from trpg.roguelite.state import RunState

__all__ = ["LlmArgs", "add_llm_args", "llm_lines", "llm_session"]

DEFAULT_ALERT_PERMILLE = 200


@dataclass(frozen=True, slots=True)
class LlmArgs:
    """命令列的 LLM 生成選項。"""

    llm: bool = False
    mock: bool = False

    @classmethod
    def of(cls, args: argparse.Namespace) -> LlmArgs:
        return cls(getattr(args, "llm", False), getattr(args, "llm_mock", False))


def add_llm_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--llm", action="store_true", help="候選請本機模型提議技能（config/llm.toml；預設關）"
    )
    group.add_argument(
        "--llm-mock", action="store_true", help="候選用 Mock 提議器（不需網路與金鑰；CI 用）"
    )


@contextmanager
def llm_session(
    library: ContentLibrary, args: LlmArgs, *, config_path: Path | None = None
) -> Iterator[bool]:
    """依選項裝上提議器；``yield`` 這一輪是否使用 LLM 生成。``--llm`` 時設定檔不合法丟
    :class:`LLMConfigError`。"""
    try:
        config = load_llm_config(config_path)
    except LLMConfigError:
        if args.llm:
            raise
        config = LLMConfig()  # 沒有指定 --llm 時，壞掉的設定檔不影響原本的流程（開關預設關）
    if args.mock:
        with use_proposer(mock_proposer(library, max_attempts=config.max_retries, naming=True)):
            yield True
        return
    if not (args.llm or config.generate):
        yield False
        return
    client = OpenAICompatClient(config)
    try:
        proposer = make_proposer(client, library, max_attempts=config.max_retries, naming=client)
        with use_proposer(proposer):
            yield True
    finally:
        client.close()


def _alert_permille() -> int:
    try:
        config: LLMConfig = load_llm_config()
    except LLMConfigError:
        return DEFAULT_ALERT_PERMILLE
    return config.fallback_alert_permille


def llm_lines(run: RunState, *, alert_permille: int | None = None) -> list[str]:
    """LLM 提議的摘要（Phase 4-L6，使用者決定 #5）：次數、成功、退回與退回率；退回率超過
    ``fallback_alert_permille``（預設 20%）時提醒。這一輪沒用 LLM 時為空。"""
    total = len(run.llm_log)
    if not run.llm and total == 0:
        return []
    limit = _alert_permille() if alert_permille is None else alert_permille
    failed = run.llm_fallbacks
    permille = failed * 1000 // total if total else 0
    attempts = sum(r.attempts for r in run.llm_log)
    line = (
        f"  LLM 提議：{total} 題，成功 {total - failed}，退回 {failed}"
        f"（{permille / 10:.1f}%），呼叫 {attempts} 次"
    )
    if permille > limit:
        line += f"　〔提醒：退回率超過 {limit / 10:g}%〕"
    lines = [line]
    named = [r for r in run.llm_log if r.name_source is not None]
    if named:
        generated = sum(1 for r in named if r.name_source == "llm")
        lines.append(
            f"  LLM 命名：{len(named)} 個，生成 {generated}，組合式名稱 {len(named) - generated}，"
            f"呼叫 {sum(r.name_attempts for r in named)} 次"
        )
    return lines
