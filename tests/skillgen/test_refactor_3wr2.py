"""Phase 3W-R2：旋鈕統一、內容即資料、拆檔前後行為不變的對照。

夾具 ``fixtures/refactor_3wr2.json`` 在重構 **之前** 產生：每個內建技能的完整技能強度
（:func:`~trpg.skillgen.complete.complete_strength`）、升階重配 1→2→3（:func:`retier`）與閃現出題
（固定種子與角色階級，連選 3 次）的 SHA-256。重構後結果必須完全相同。

重產（只在規則真的要改時）：``uv run python -m tests.skillgen.test_refactor_3wr2``。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from functools import cache
from pathlib import Path

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.complete import complete_strength
from trpg.skillgen.flash import FlashRequest, choose, make_offer
from trpg.skillgen.flash_state import SkillFlash, acquire
from trpg.skillgen.skill_tier import retier
from trpg.skillgen.usage import SkillUsage

FIXTURE = Path(__file__).parent / "fixtures" / "refactor_3wr2.json"
FLASH_CASES = ((3, 1), (11, 1), (5, 2))
"""閃現對照的（種子, 角色階級）。"""
FLASH_PICKS = 3
FLASH_SKILLS = 40
"""閃現對照取 ID 排序後等距的約 40 招，控制測試時間。"""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _guarded(fn: Callable[[], str]) -> str:
    """失敗本身也是要對照的行為（記下例外型別）。"""
    try:
        return fn()
    except Exception as exc:
        return f"error:{type(exc).__name__}"


def complete_snapshot(skill_id: str) -> str:
    lib = library()
    return _guarded(lambda: _digest(complete_strength(lib, lib.skills[skill_id]).model_dump_json()))


def retier_snapshot(skill_id: str) -> str:
    lib = library()
    skills: list[SkillDef] = [lib.skills[skill_id]]

    def step(tier: int) -> str:
        skills.append(retier(lib, skills[-1], tier))
        return _digest(skills[-1].model_dump_json())

    return "/".join([_guarded(lambda: step(2)), _guarded(lambda: step(3))])


def flash_snapshot(skill_id: str, seed: int, tier: int) -> str:
    lib = library()
    state: SkillFlash = acquire(skill_id).model_copy(update={"used": True})
    base = lib.skills[skill_id]
    out: list[str] = []
    for pick in range(FLASH_PICKS):
        request = FlashRequest(base, state, SkillUsage(), seed, tier=tier)
        try:
            offer = make_offer(lib, request)
        except Exception as exc:
            out.append(f"error:{type(exc).__name__}")
            break
        out.append(_digest(offer.model_dump_json()))
        if not offer.options:
            break
        state, _ = choose(state, offer, (seed + pick) % len(offer.options))
        state = state.model_copy(update={"used": True})
    return "/".join(out)


def _flash_ids() -> list[str]:
    ids = sorted(library().skills)
    step = max(1, len(ids) // FLASH_SKILLS)
    return ids[::step]


@cache
def _fixture() -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def _generate() -> dict[str, dict[str, str]]:
    ids = sorted(library().skills)
    return {
        "complete": {i: complete_snapshot(i) for i in ids},
        "retier": {i: retier_snapshot(i) for i in ids},
        "flash": {
            f"{i}@{s}@{t}": flash_snapshot(i, s, t) for i in _flash_ids() for s, t in FLASH_CASES
        },
    }


def _keys(kind: str) -> list[str]:
    if not FIXTURE.exists():
        return []
    return sorted(_fixture()[kind])


@pytest.mark.slow
@pytest.mark.parametrize("skill_id", _keys("complete"))
def test_complete_strength_unchanged(skill_id: str) -> None:
    assert complete_snapshot(skill_id) == _fixture()["complete"][skill_id]


@pytest.mark.slow
@pytest.mark.parametrize("skill_id", _keys("retier"))
def test_retier_unchanged(skill_id: str) -> None:
    assert retier_snapshot(skill_id) == _fixture()["retier"][skill_id]


@pytest.mark.slow
@pytest.mark.parametrize("key", _keys("flash"))
def test_flash_offers_unchanged(key: str) -> None:
    skill_id, seed, tier = key.split("@")
    assert flash_snapshot(skill_id, int(seed), int(tier)) == _fixture()["flash"][key]


def test_fixture_covers_every_builtin_skill() -> None:
    assert set(_fixture()["complete"]) == set(library().skills)
    assert set(_fixture()["retier"]) == set(library().skills)


if __name__ == "__main__":
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        json.dumps(_generate(), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
