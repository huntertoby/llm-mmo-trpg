"""NW-2a R1／R2（使用者 2026-11-12「照建議」）。

- R1（T-A7）：招式組低於 #149 下限 → 警告、不勾「我確定」409、勾了寫回且 commit 內文有「#149 例外」
  （假 repo）；判定函式搬到 ``trpg.content.enemy_moves`` 後 ``test_enemy_skill_count_149.py`` 照過。
- R2：技能表單頂端的升階重算提示與實戰用升階版的單位。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.api.tuning.conftest import git
from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.objects import RETIER_NOTE_ZH
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.writeback import WritebackError
from trpg.content.enemy_moves import move_shortfalls
from trpg.content.library import ContentLibrary

HEART = "units/ashen_heart.yaml"
PHASE2 = ("skill_heart_inhale", "skill_heart_exhale", "skill_fire_bolt")


def test_no_builtin_unit_is_below_the_floor(content_library: ContentLibrary) -> None:
    assert move_shortfalls(content_library) == []


def test_below_the_floor_needs_confirmation(repo: Path, repo_service: TuningService) -> None:
    before = (repo_service.content_dir / HEART).read_bytes()
    repo_service.drafts.put(
        Draft(
            name="current",
            changes=(Change(file=HEART, path="phases[1].skills", old=PHASE2, new=PHASE2[:2]),),
        )
    )
    check = repo_service.check("current")
    assert check.ok
    [flag] = check.needs_confirm_min_moves
    assert flag.unit_id == "ashen_heart" and flag.shortfalls == ["ashen_heart/breath=2"]
    assert "低於 #149 的招數下限" in flag.message_zh
    with pytest.raises(WritebackError, match="#149"):
        repo_service.apply("current")
    with pytest.raises(WritebackError, match="不符"):
        repo_service.apply("current", [], ["rift_shard_lord"])
    assert (repo_service.content_dir / HEART).read_bytes() == before
    done = repo_service.apply("current", [], ["ashen_heart"])
    body = git(repo, "log", "-1", "--format=%B")
    assert done.commit in git(repo, "rev-parse", "HEAD")
    assert "#149 例外：ashen_heart（ashen_heart/breath=2）" in body


def test_skill_form_shows_the_retier_note(read_service: TuningService) -> None:
    detail = read_service.object("skill", "skill_rift_flicker")
    assert detail.notes_zh[0] == RETIER_NOTE_ZH
    assert "碎晶之主（rift_shard_lord，3 階）" in detail.notes_zh[1]
    lord = next(u for u in detail.used_by if u.id == "rift_shard_lord")
    assert lord.tier == 3 and lord.where_zh == ["第 3 階段"]
    # OB-7b：渡口不再有新手弓手（bandit_archer_rookie 不在任何遭遇，沒有階），改看符籙師的冰鎖
    rookie = read_service.object("skill", "skill_frost_shackle")
    tiers = {u.id: u.tier for u in rookie.used_by}
    assert tiers["thunder_talisman_caster"] is not None and tiers["thunder_talisman_caster"] > 1
    assert tiers["sect_talisman_caster"] == 1  # 1 階照原樣，不列進升階名單
    assert "sect_talisman_caster" not in rookie.notes_zh[1]
