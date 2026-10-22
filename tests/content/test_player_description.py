"""Phase 3E-2e：每個原語都要有給玩家看的說明；武器預設外觀的造型要是外觀清單裡的值。"""

from __future__ import annotations

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.appearance import AppearanceTable
from trpg.content.loader import load_content_file


def test_every_primitive_has_a_player_description() -> None:
    missing = [p.id for p in library().ruleset.primitives.primitives if not p.player_description]
    assert missing == []


def test_weapon_looks_use_known_kinds() -> None:
    table = load_content_file(
        PROJECT_ROOT / "content" / "equipment" / "appearance.yaml", AppearanceTable
    )
    kinds = {k.id for k in table.kinds}
    looks = {w.id: w.look for w in library().weapons.values() if w.look is not None}
    assert looks
    for weapon_id, look in looks.items():
        assert look.kind in kinds, weapon_id
