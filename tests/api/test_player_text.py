"""工坊說明文字掃描（Phase 3-5c-2 驗收 2）：給玩家看的文字不得含階段編號或程式識別字。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.skillgen.workshop_walks import DISPLACE, MODIFIER, STRIKE, walk_draft
from trpg.api.player_text import IDENTIFIER, PHASE_MARK, clean_text
from trpg.content.library import ContentLibrary
from trpg.skillgen.random_composer import compose_random_skill

TEXT_KEYS = ("name_zh", "description_zh", "notes_zh", "problems")
TRUNCATE = (
    (),
    ("effects", "cost", "rarity", "condition", "followup"),
    ("shape", "effects", "cost", "rarity", "condition", "followup"),
    ("cost", "rarity"),
)


def _texts(node: Any, key: str = "", *, raw: bool = False) -> list[str]:
    """選項樹裡所有給玩家看的字串（說明、備註、名稱、問題）；``raw``：改收開發者原文
    （3-48c：``draft_options`` 已把說明換成玩家版，原文在 ``dev_description_zh``）。"""
    if isinstance(node, str):
        wanted = ("dev_description_zh",) if raw else TEXT_KEYS
        return [node] if key in wanted else []
    if isinstance(node, dict):
        return [t for k, v in node.items() for t in _texts(v, k, raw=raw)]
    if isinstance(node, list):
        return [t for v in node for t in _texts(v, key, raw=raw)]
    return []


def _drafts(library: ContentLibrary) -> list[dict[str, Any]]:
    drafts: list[dict[str, Any]] = [{}]
    walked = [walk_draft(w) for w in (STRIKE, DISPLACE, MODIFIER)]
    for seed, skeleton in enumerate(sorted(library.skeletons), start=1):
        try:
            skill = compose_random_skill(seed, skeleton=skeleton, library=library)
        except Exception:
            continue
        walked.append(skill.model_dump(mode="json", exclude_none=True))
    for full in walked:
        for drop in TRUNCATE:
            drafts.append({k: v for k, v in full.items() if k not in drop})
    return drafts


def test_workshop_texts_have_no_phase_numbers_or_identifiers(
    client: TestClient, library: ContentLibrary
) -> None:
    offenders: dict[str, str] = {}
    for draft in _drafts(library):
        body = client.post("/api/workshop/options", json={"skill": draft}).json()
        for text in _texts(body):
            if PHASE_MARK.search(text) or IDENTIFIER.search(text):
                offenders[text[:60]] = text
    assert not offenders, "\n".join(offenders)


def test_the_scan_catches_the_raw_texts(library: ContentLibrary) -> None:
    """掃描本身有效：過濾前的說明文字（含 Phase 與識別字）會被抓到。"""
    from trpg.skillgen.options import draft_options  # noqa: PLC0415

    raw = [
        t
        for d in _drafts(library)
        for t in _texts(draft_options(d, library).model_dump(mode="json"), raw=True)
    ]
    assert any(PHASE_MARK.search(t) for t in raw)
    assert any(IDENTIFIER.search(t) for t in raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("爆骰（Phase 3D-7b）：擲到最大值", "爆骰：擲到最大值"),
        ("返還 AP（refund_ap、unknown_thing）", "返還 AP"),
        ("見 rules/core.yaml 的 tier_budget", "見"),
        ("用 time_bomb 施加", "用 定時炸彈 施加"),
    ],
)
def test_clean_text_examples(raw: str, expected: str) -> None:
    assert clean_text(raw, {"time_bomb": "定時炸彈"}) == expected
