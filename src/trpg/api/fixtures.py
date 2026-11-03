"""前端測試用的內容快照文字（Phase 3E-2e）：匯出腳本與過期檢查共用。"""

from __future__ import annotations

import json

from trpg.api.glossary import build_glossary
from trpg.api.skill_cards import skill_card
from trpg.content.library import ContentLibrary

__all__ = [
    "SKILL_CARD_FIXTURE_IDS",
    "glossary_fixture_text",
    "race_looks_fixture_text",
    "skill_cards_fixture_text",
    "unit_dolls_fixture_text",
]

SKILL_CARD_FIXTURE_IDS = (
    "skill_ash_harvest",
    "skill_gale_kick",
    "skill_counterspell",
    "skill_twin_fang",
    "skill_afterimage_vow",
    "skill_downpour",
)
"""技能卡常駐 3 行的前端測試（6A-1）用的代表技能：法術傷害、武器傷害＋推開、反應技、連打、
傳說（源力、啟動）、表面＋狀態。"""


def glossary_fixture_text(library: ContentLibrary) -> str:
    """``/api/glossary`` 回應的固定格式文字（縮排 1、保留中文、結尾換行）。"""
    data = json.loads(build_glossary(library).model_dump_json())
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def unit_dolls_fixture_text(library: ContentLibrary) -> str:
    """單位範本 ID → ``doll_look``（只列有外觀的範本，依 ID 排序）。"""
    templates = [*library.units.values(), *(s.template for s in library.ruleset.summons.summons)]
    data = {
        t.id: json.loads(t.doll.model_dump_json(exclude_none=True))
        for t in sorted(templates, key=lambda t: t.id)
        if t.doll is not None
    }
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def race_looks_fixture_text(library: ContentLibrary) -> str:
    """種族 ID → 預設外觀 ``look``（依 ID 排序；沒有種族資料時為空物件）。"""
    races = [] if library.races is None else library.races.races
    data = {
        r.id: json.loads(r.look.model_dump_json(exclude_none=True))
        for r in sorted(races, key=lambda r: r.id)
    }
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def skill_cards_fixture_text(library: ContentLibrary) -> str:
    """代表技能的 ``/api/skills/{id}`` 回應（6A-1：含結構化欄位 ``stats``），依上面的順序。"""
    data = {
        sid: json.loads(skill_card(library, library.skills[sid]).model_dump_json())
        for sid in SKILL_CARD_FIXTURE_IDS
    }
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"
