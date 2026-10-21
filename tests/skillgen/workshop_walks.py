"""技能工坊測試共用的「一步步組技能」（打擊、位移、修正各一個合法技能；Phase 3F-1）。"""

from __future__ import annotations

from typing import Any

__all__ = ["DISPLACE", "MODIFIER", "STRIKE", "Walk", "walk_draft"]

type Walk = list[tuple[str, dict[str, Any]]]
"""依序：(這一步的步驟 ID, 這一步填的欄位)。"""

STRIKE: Walk = [
    ("skeleton", {"skeleton": "strike"}),
    (
        "basics",
        {
            "name_zh": "震地重擊",
            "kind": "active",
            "ap_cost": 2,
            "category": "weapon",
            "weapon_req": "melee",
            "scaling_attr": "str",
            "tier": 1,
        },
    ),
    ("shape", {"shape": {"type": "single", "range": 1}}),
    (
        "effects",
        {"effects": [{"type": "damage", "multiplier_permille": 1000}, {"type": "knock_prone"}]},
    ),
    ("condition", {}),
    ("cost", {}),
    ("rarity", {"rarity": "rare"}),
]

DISPLACE: Walk = [
    ("skeleton", {"skeleton": "displace"}),
    (
        "basics",
        {
            "name_zh": "衝鋒擊退",
            "kind": "active",
            "ap_cost": 2,
            "category": "weapon",
            "weapon_req": "melee",
            "scaling_attr": "str",
            "tier": 2,
        },
    ),
    ("shape", {"shape": {"type": "single", "range": 4}}),
    (
        "effects",
        {
            "effects": [
                {"type": "dash"},
                {"type": "damage", "multiplier_permille": 1000},
                {"type": "push", "distance": 2},
            ]
        },
    ),
    ("condition", {}),
    ("cost", {"cost": {"cooldown": 2}}),
    ("rarity", {"rarity": "rare"}),
]

MODIFIER: Walk = [
    ("skeleton", {"skeleton": "modifier"}),
    (
        "basics",
        {
            "name_zh": "重手",
            "kind": "modifier",
            "category": "weapon",
            "weapon_req": "melee",
            "scaling_attr": "str",
            "tier": 2,
        },
    ),
    ("shape", {"shape": {"type": "self"}}),
    (
        "effects",
        {
            "modifiers": [
                {
                    "applies_to": {"actions": ["attack"]},
                    "condition": {"type": "target_has_status", "status": "burning"},
                    "change": {"damage_permille": 200},
                }
            ]
        },
    ),
    ("condition", {}),
    ("cost", {}),
    ("rarity", {"rarity": "epic"}),
]


def walk_draft(walk: Walk) -> dict[str, Any]:
    """走完 ``walk`` 的技能定義（JSON）。"""
    draft: dict[str, Any] = {}
    for _step_id, picks in walk:
        draft.update(picks)
    return draft
