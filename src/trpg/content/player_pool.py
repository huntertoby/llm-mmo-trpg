"""玩家技能池（Phase 5F-3b，玩法 PM 2026-11-03 代決）。

內容庫的手寫技能有一部分只給敵人（``SkillDef.enemy_only``：霧鎖千山、霧遁、碎晶之主與源晶柱的
技能）。所有「玩家拿得到的技能」的入口——生成器與候選（關鍵字池、通用池、白板）、閃現的出題與
轉型、工坊與 LLM 提議的可選清單、mock 提議——一律經過 :func:`player_skills` 取池，不各自過濾。
``tests/test_architecture.py`` 檢查這些模組沒有直接走訪 ``library.skills``。

敵人範本、單位卡、名字對照、重播等「依 ID 查技能」的地方照舊用 ``library.skills``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trpg.content.library import ContentLibrary
    from trpg.content.skills import SkillDef

__all__ = ["is_player_skill", "player_skills"]


def is_player_skill(skill: SkillDef) -> bool:
    """技能可以進玩家技能池（不是只給敵人的）。"""
    return not skill.enemy_only


def player_skills(library: ContentLibrary) -> dict[str, SkillDef]:
    """玩家技能池：內容庫手寫技能中不是 ``enemy_only`` 的，依 ID 排序（鍵＝技能 ID）。"""
    return {
        k: library.skills[k] for k in sorted(library.skills) if is_player_skill(library.skills[k])
    }
