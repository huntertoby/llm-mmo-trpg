"""只給敵人的狀態（Phase 5F-5c；玩法 PM 2026-11-03 代決）。

熔核爆裂、寒燼爆裂（與殼縫熔核）承載荒原敵人的傷害倍率（5F-5b ×2.25／×1.5），不能給玩家、影子、
傭兵，也不能進技能池（生成器、候選、閃現、工坊、LLM 可選清單）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trpg.content.library import (
    ContentLibrary,
    load_library,
    player_template_enemy_only_problems,
    skill_reference_problems,
)
from trpg.shared.errors import ContentError
from trpg.skillgen.proposal import budget_statuses, rarity_statuses

ENEMY_ONLY = ("frost_ember_burst", "heart_ember_burst", "molten_burst")
CONTENT = Path(__file__).resolve().parents[2] / "content"


def test_the_burst_statuses_are_enemy_only(library: ContentLibrary) -> None:
    rules = library.ruleset
    assert sorted(rules.enemy_only_statuses()) == list(ENEMY_ONLY)
    for sid in ENEMY_ONLY:
        assert rules.status_def(sid).budget_points is None


def test_enemy_only_statuses_never_reach_a_skill_list(library: ContentLibrary) -> None:
    for rarity in ("common", "rare", "epic", "legendary"):
        assert not set(ENEMY_ONLY) & set(rarity_statuses(library, rarity))
    assert not set(ENEMY_ONLY) & set(budget_statuses(library))


def test_a_skill_that_uses_an_enemy_only_status_is_rejected(library: ContentLibrary) -> None:
    skill = next(
        s
        for s in sorted(library.skills.values(), key=lambda s: s.id)
        if any(e.status is not None for e in s.effects)
    )
    effects = tuple(
        e.model_copy(update={"status": "molten_burst"}) if e.status is not None else e
        for e in skill.effects
    )
    bad = skill.model_copy(update={"effects": effects})
    problems = skill_reference_problems(bad, library.ruleset, library.skills)
    assert any("molten_burst 只給敵人" in p for p in problems)
    assert not skill_reference_problems(skill, library.ruleset, library.skills)


def _copy_content(tmp_path: Path) -> Path:
    dest = tmp_path / "content"
    shutil.copytree(CONTENT, dest)
    return dest


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, path
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_loader_rejects_a_skill_with_an_enemy_only_status(tmp_path: Path) -> None:
    """5F-R1：載入時驗證（原本是比對 YAML 文字）——內容庫的技能施加 enemy_only 狀態＝資料錯誤。"""
    root = _copy_content(tmp_path)
    _edit(root / "skills" / "skill_fire_bolt.yaml", "status: burning", "status: molten_burst")
    with pytest.raises(ContentError, match="molten_burst 只給敵人"):
        load_library(root)


def test_loader_rejects_enemy_only_opening_status_on_player_side(tmp_path: Path) -> None:
    """build 英雄（主角、影子、傭兵、劇情夥伴的底稿）開場帶 enemy_only 狀態＝資料錯誤。"""
    root = _copy_content(tmp_path)
    _edit(
        root / "sim" / "builds.yaml",
        "      skills: [skill_fire_bolt,",
        "      opening_statuses: [{status: molten_burst}]\n      skills: [skill_fire_bolt,",
    )
    with pytest.raises(ContentError, match="開場狀態 molten_burst 只給敵人"):
        load_library(root)


def test_loader_rejects_enemy_only_league_opening_status(
    tmp_path: Path, library: ContentLibrary
) -> None:
    season = library.world_season
    assert season is not None and season.league is not None
    league = (*season.league.opening_statuses, *season.league.first_opening_statuses)
    assert league and not set(ENEMY_ONLY) & set(league)
    root = _copy_content(tmp_path)
    _edit(root / "world" / "season.yaml", league[0], "molten_burst")
    with pytest.raises(ContentError, match="循環賽的開場狀態 molten_burst"):
        load_library(root)


def test_player_side_templates_have_no_enemy_only_status(library: ContentLibrary) -> None:
    """現有內容：玩家這一邊的範本都通過（傭兵與劇情夥伴的底稿都是 build）。"""
    templates = {b.id: b.hero for b in library.builds.builds}
    for uid, template in sorted(templates.items()):
        assert not player_template_enemy_only_problems(
            uid, template, library.skills, library.ruleset
        )
    mercs = library.world_mercenaries
    assert mercs is not None
    builds = set(templates)
    assert {m.build for m in mercs.mercenaries} <= builds
    assert {c.build for c in mercs.companions} <= builds
